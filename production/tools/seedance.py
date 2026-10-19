#!/usr/bin/env python3
"""Seedance 2.5 through OpenRouter: submit clips from a clip book, poll, download, and log every paid call.

    python3 production/tools/seedance.py production/motion/pilot.json [--only C1B] [--dry-run]

The clip book is a JSON list of clips: {"id", "kind": "sung"|"motion", "duration", "resolution", "prompt",
"image": local PNG, "audio": local WAV (sung only)}. Per the gallery (wiki/seedance, "Providers and filters"):
  - sung clips go in reference mode: the plate as an image reference, the vocal window as an audio reference
    (on OpenRouter a first frame silently drops the audio);
  - motion clips use the plate as the first frame and are silent;
  - audio must be a public HTTPS URL (no data: URIs), so references are uploaded to a public host first
    (production/motion/host.json says which; every upload is listed in the ledger and deleted after the batch).

Spending gate: production/motion/budget.json holds the approved dollars. A submission is refused if the money already
spent (ledger) plus this clip's estimate (seconds x price x 2, the CLAUDE.md rule) would go over it. Ledger:
production/motion/ledger.jsonl, one line per paid call, with OpenRouter's reported cost.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://openrouter.ai/api/v1/videos"
MODEL = "bytedance/seedance-2.5"
PRICE = {"720p": 0.23, "480p": 0.1028}  # $/s; the pilot reads the real cost from the job
LEDGER = ROOT / "production/motion/ledger.jsonl"
BUDGET = ROOT / "production/motion/budget.json"
HOST = ROOT / "production/motion/host.json"
OUT = ROOT / "media/clips"


def env():
    for line in (ROOT / ".env").read_text().splitlines():
        k, _, v = line.partition("=")
        if k and v and k not in os.environ:
            os.environ[k.strip()] = v.strip()


def spent():
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        r = json.loads(line)
        total += r.get("cost_usd") if r.get("cost_usd") is not None else r.get("estimate_usd", 0)
    return total


def log(rec):
    rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with LEDGER.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def req(method, url, body=None, auth=True):
    h = {"Content-Type": "application/json"}
    if auth:
        h["Authorization"] = "Bearer " + os.environ["OPENROUTER_API_KEY"]
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} from {url}: {e.read().decode()[:1500]}")


def host_upload(path, batch):
    """Upload one reference file to the public host named in host.json; return its HTTPS URL."""
    cfg = json.loads(HOST.read_text())
    if cfg["kind"] == "hf-dataset":
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ["HF_TOKEN"])
        dest = f"{batch}/{Path(path).name}"
        api.upload_file(path_or_fileobj=str(path), path_in_repo=dest, repo_id=cfg["repo"], repo_type="dataset")
        return f"https://huggingface.co/datasets/{cfg['repo']}/resolve/main/{dest}"
    raise SystemExit(f"unknown host kind {cfg['kind']}")


def submit(clip, batch, dry):
    res = clip.get("resolution", "720p")
    est = round(clip["duration"] * PRICE[res] * 2, 2)
    budget = json.loads(BUDGET.read_text())["approved_usd"]
    if spent() + est > budget + 1e-9:
        raise SystemExit(f"REFUSED {clip['id']}: spent {spent():.2f} + estimate {est:.2f} > approved {budget:.2f}")
    body = {"model": MODEL, "prompt": clip["prompt"], "duration": clip["duration"], "resolution": res,
            "aspect_ratio": "16:9"}
    if dry:
        print(f"[dry] {clip['id']} {clip['kind']} {clip['duration']} s {res}, estimate ${est}")
        return None
    img = host_upload(ROOT / clip["image"], batch)
    if clip["kind"] == "sung":
        aud = host_upload(ROOT / clip["audio"], batch)
        body["input_references"] = [{"type": "image_url", "image_url": {"url": img}},
                                    {"type": "audio_url", "audio_url": {"url": aud}}]
    else:
        body["generate_audio"] = False
        body["frame_images"] = [{"type": "image_url", "image_url": {"url": img}, "frame_type": "first_frame"}]
    job = req("POST", API, body)
    log({"clip": clip["id"], "job": job.get("id"), "kind": clip["kind"], "duration": clip["duration"],
         "resolution": res, "estimate_usd": est, "cost_usd": None, "status": "submitted", "batch": batch})
    print(f"submitted {clip['id']} -> job {job.get('id')} (estimate ${est})")
    return job


def wait(job, clip, batch):
    cur = job
    for _ in range(120):
        st = cur.get("status")
        if st == "completed":
            break
        if st in ("failed", "cancelled", "expired"):
            log({"clip": clip["id"], "job": job["id"], "status": st, "error": cur.get("error"), "estimate_usd": 0,
                 "cost_usd": (cur.get("usage") or {}).get("cost"), "batch": batch})
            print(f"{clip['id']}: {st}: {cur.get('error')}")
            return None
        time.sleep(20)
        url = cur.get("polling_url") or f"{API}/{job['id']}"
        cur = req("GET", url if url.startswith("http") else "https://openrouter.ai" + url)
    else:
        print(f"{clip['id']}: still not done; poll later: {job['id']}")
        return None
    dest = OUT / batch / f"{clip['id']}-{job['id'][:8]}.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = (cur.get("unsigned_urls") or [None])[0] or f"{API}/{job['id']}/content?index=0"
    h = {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]} if url.startswith(API) else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300) as r:
        dest.write_bytes(r.read())
    cost = (cur.get("usage") or {}).get("cost")
    log({"clip": clip["id"], "job": job["id"], "status": "completed", "estimate_usd": 0, "cost_usd": cost,
         "file": str(dest.relative_to(ROOT)), "batch": batch, "usage": cur.get("usage")})
    print(f"{clip['id']}: saved {dest.relative_to(ROOT)}, cost {cost}")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--only", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    env()
    clips = json.loads(Path(a.book).read_text())
    only = set(filter(None, a.only.split(",")))
    batch = Path(a.book).stem
    jobs = [(c, submit(c, batch, a.dry_run)) for c in clips if not only or c["id"] in only]
    for c, j in jobs:
        if j:
            wait(j, c, batch)
    print(f"spent so far (ledger): ${spent():.2f}")


if __name__ == "__main__":
    main()
