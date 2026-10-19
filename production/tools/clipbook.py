#!/usr/bin/env python3
"""The clip book for local video: 15 sung windows (InfiniteTalk) and 2 motion clips (Wan 2.2), and an overnight runner.

    python3 production/tools/clipbook.py build                  # board.json -> production/motion/clipbook.json + audio
    python3 production/tools/clipbook.py first V1S=SEED[,flip]  # pick a sung clip's first frame from its ff- renders
    python3 production/tools/clipbook.py run [--only V1S,P1B]   # render what's missing, shortest first

Sung windows span their shots (0.05 s before the first cut to 0.10 s after the last), so the lips follow every word
heard on screen. The audio is the vocal stem with everything outside "keep" muted: the whole window, except the two
pre-choruses, where the "something sweet" draft stays muted and she only says "But the true one goes: I don't know"
(the film's thought-vs-said device). Motion clips start from the shot's picked plate.

The runner restarts ComfyUI between clips: on this card a long session ends in a ROCm illegal-memory-access crash.
Each finished clip is logged by video.py to production/motion/local-runs.jsonl; a clip counts as done when its MP4 is
in media/clips/local/ under its book id.
"""

import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "production/motion/clipbook.json"
AUDIO = ROOT / "media/clips/audio"
FIRST = ROOT / "media/clips/first"
LISTEN_PY = ROOT / "media/cache/listen-venv/bin/python"
COMFY = Path.home() / "ComfyUI"
COMFY_ARGS = ["--listen", "127.0.0.1", "--port", "8188", "--use-pytorch-cross-attention", "--reserve-vram", "1.5",
              "--output-directory", str(ROOT / "media/plates")]
DRAFT_MUTED = {"P1B": "but", "P2B": "but"}  # keep starts at this word
VERB = {"sings": "sings", "speaks": "speaks", "whispers": "whispers"}
LOOK = ("A woman in her late twenties with a glossy black blunt bob, heavy bangs and one thin clay-orange streak, a small "
        "star hair clip and a thin headset microphone, wearing a fitted white shirt with short puffed sleeves and thin "
        "black suspender straps")
MOTION = {
    "M007": ("{look}, long black gloves, a short black pleated skirt and tall black boots. Her eyes are closed, then she "
             "opens them and looks straight into the lens, calm and curious, head upright and level. The camera slowly "
             "pulls back. Black void, soft light from below. Cinematic 35mm film, fine grain."),
    "M039": ("{look}, long black gloves, a short black pleated skirt, black knee socks and tall black boots. She steps up "
             "onto the top terracotta tablet of a low flight of steps, one deliberate step, then stands still and level, "
             "calm. Locked camera. Black void, top light. Cinematic 35mm film, fine grain."),
}


def board():
    return json.loads((ROOT / "production/board/board.json").read_text())


def words():
    return [w for w in json.loads((ROOT / "media/song/analysis/a1/words.json").read_text())["words"] if w["t1"]]


def setting_of(prompt):
    """The light and set sentences of a board prompt, after her action sentence."""
    cut = max(prompt.find(" in shot. "), prompt.find(" out of shot. "))
    body = prompt[cut:].split(". ", 1)[1].split("Fashion editorial")[0]
    sentences = [s.strip() for s in body.split(". ") if s.strip()]
    return ". ".join(sentences[1:]).rstrip(".")


def build():
    b = board()
    S = {s["id"]: s for s in b["shots"]}
    picks = json.loads((ROOT / "production/board/picks.json").read_text())
    old = {c["id"]: c for c in json.loads(BOOK.read_text())} if BOOK.exists() else {}
    W = words()
    book = []
    AUDIO.mkdir(parents=True, exist_ok=True)
    for c in b["clips"]:
        shots = [S[i] for i in c["shots"]]
        t0 = round(float(shots[0]["t0"]) - 0.05, 3)
        t1 = round(float(shots[-1]["t1"]) + 0.10, 3)
        e = {"id": c["id"], "kind": c["kind"], "shots": c["shots"], "t0": t0, "t1": t1, "seconds": round(t1 - t0, 3)}
        if c["kind"] == "sung":
            keep = [t0, t1]
            if c["id"] in DRAFT_MUTED:
                w = next(w for w in W if w["w"] == DRAFT_MUTED[c["id"]] and t0 <= w["t0"] <= t1)
                keep = [round(w["t0"] - 0.04, 3), t1]
            e["keep"] = keep
            e["words"] = " ".join(w["w"] for w in W if w["t0"] >= keep[0] and w["t1"] <= keep[1] + 0.3)
            p = shots[0]["prompt"]
            verb = next((v for v in VERB if f"She {v}" in p or f"and {v[:-1]}" in p), "sings")
            e["prompt"] = (f"{LOOK}, {verb} softly and calmly straight into the camera, head upright and level, small "
                           f"natural head movements, singing to one person. {setting_of(p)}. Cinematic 35mm film, fine "
                           f"grain, intimate close shot.")
            e["audio"] = str((AUDIO / f"{c['id']}.wav").relative_to(ROOT))
            subprocess.run([str(LISTEN_PY), str(ROOT / "production/tools/clipaudio.py"), "vocal", str(ROOT / e["audio"]),
                            str(t0), str(t1), "--keep", str(keep[0]), str(keep[1])], check=True, stdout=subprocess.DEVNULL)
            e["image"] = old.get(c["id"], {}).get("image")  # set by `first`
        else:
            e["prompt"] = MOTION[c["id"]].format(look=LOOK)
            e["image"] = picks[shots[0]["plate"]]["file"]
        book.append(e)
    BOOK.write_text(json.dumps(book, indent=1) + "\n")
    secs = sum(e["seconds"] for e in book if e["kind"] == "sung")
    print(f"{len(book)} clips, {secs:.1f} s of sung windows -> {BOOK.relative_to(ROOT)}")


def first(sets):
    from PIL import Image, ImageOps  # ComfyUI venv
    book = json.loads(BOOK.read_text())
    FIRST.mkdir(parents=True, exist_ok=True)
    for s in sets:
        cid, rest = s.split("=", 1)
        seed, *flag = rest.split(",")
        src = sorted(glob.glob(str(ROOT / f"media/plates/ff-{cid}_*_s{seed}_*.png")))
        if not src:
            raise SystemExit(f"no ff-{cid} render with seed {seed}")
        im = Image.open(src[-1])
        dst = FIRST / f"{cid}.png"
        (ImageOps.mirror(im) if flag == ["flip"] else im).save(dst)
        for e in book:
            if e["id"] == cid:
                e["image"], e["first_src"], e["first_flip"] = (str(dst.relative_to(ROOT)),
                                                               str(Path(src[-1]).relative_to(ROOT)), flag == ["flip"])
    BOOK.write_text(json.dumps(book, indent=1) + "\n")
    print("first frames set:", ", ".join(s.split("=")[0] for s in sets))


def comfy_pids():
    out = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
    return [int(l.split()[0]) for l in out.splitlines() if "main.py --listen 127.0.0.1 --port 8188" in l
            and "venv/bin/python" in l]


def comfy_restart(log):
    for pid in comfy_pids():
        os.kill(pid, signal.SIGTERM)
    time.sleep(6)
    for pid in comfy_pids():
        os.kill(pid, signal.SIGKILL)
    env = dict(os.environ, HIP_VISIBLE_DEVICES="0")
    subprocess.Popen([str(COMFY / "venv/bin/python"), "main.py", *COMFY_ARGS], cwd=COMFY, env=env,
                     stdout=open(ROOT / "media/cache/comfy.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(3)
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=3)
            print(time.strftime("%H:%M"), "ComfyUI up", file=log, flush=True)
            return
        except OSError:
            pass
    raise SystemExit("ComfyUI did not come up")


def done(cid):
    return bool(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4")))


def run(only):
    book = json.loads(BOOK.read_text())
    todo = [e for e in book if (not only or e["id"] in only) and not done(e["id"])]
    missing = [e["id"] for e in todo if not e.get("image")]
    if missing:
        raise SystemExit(f"no first frame for {missing}: run `first`")
    todo.sort(key=lambda e: (e["kind"] != "sung", e["seconds"]))
    log = open(ROOT / "media/cache/clips-run.log", "a")
    for e in todo:
        e = next(x for x in json.loads(BOOK.read_text()) if x["id"] == e["id"])  # pick up first frames changed mid-run
        for attempt in (1, 2):
            comfy_restart(log)
            cmd = [sys.executable, str(ROOT / "production/tools/video.py"), e["kind"], "--id", e["id"],
                   "--image", str(ROOT / e["image"]), "--prompt", e["prompt"], "--seconds", str(e["seconds"])]
            if e["kind"] == "sung":
                cmd += ["--audio", str(ROOT / e["audio"])]
            else:
                cmd += ["--variant", "fast", "--size", "960x544"]
            print(time.strftime("%H:%M"), "start", e["id"], f"{e['seconds']} s", f"attempt {attempt}", file=log,
                  flush=True)
            r = subprocess.run(cmd, capture_output=True, text=True)
            print(time.strftime("%H:%M"), "end", e["id"], "exit", r.returncode, (r.stdout + r.stderr)[-600:], file=log,
                  flush=True)
            if r.returncode == 0:
                break
    print(time.strftime("%H:%M"), "run finished", file=log, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "first", "run"])
    ap.add_argument("sets", nargs="*")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "first":
        first(a.sets)
    else:
        run(set(filter(None, a.only.split(","))))


if __name__ == "__main__":
    main()
