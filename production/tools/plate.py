#!/usr/bin/env python3
"""Render plates with Krea 2 Turbo through a local ComfyUI (http://127.0.0.1:8188).

    python3 production/tools/plate.py production/images/test-plates.json [--only id1,id2] [--seeds 2]

The JSON holds a list of plates: {"id", "prompt", "w", "h", "seed"?}. Images land in ComfyUI's output directory
(start ComfyUI with --output-directory media/plates) as <id>_s<seed>_00001_.png. Each render is logged to
production/images/renders.jsonl with its prompt, seed and timing. Prompts are used as written: no prompt enhancer.
"""

import argparse
import json
import random
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:8188"
LOG = ROOT / "production/images/renders.jsonl"


def graph(prompt, w, h, seed, prefix, steps=8, lora=None, lora_strength=1.0):
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors",
                                                     "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_bf16.safetensors", "type": "krea2",
                                                     "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0],
                                                   "latent_image": ["6", 0], "seed": seed, "steps": steps, "cfg": 1.0,
                                                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["7", 0], "vae": ["3", 0], "tile_size": 512,
                                                         "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }
    if lora:
        g["10"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": lora,
                                                                  "strength_model": lora_strength}}
        g["7"]["inputs"]["model"] = ["10", 0]
    return g


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    body = urllib.request.urlopen(req).read()
    return json.loads(body) if body.strip() else {}


def get(path):
    return json.load(urllib.request.urlopen(URL + path))


def render(p, seed, lora=None, lora_strength=1.0):
    tag = f"_{lora.rsplit('/', 1)[-1].rsplit('.', 1)[0]}x{lora_strength:g}" if lora else ""
    prefix = f"{p['id']}{tag}_s{seed}"
    t0 = time.time()
    pid = post("/prompt", {"prompt": graph(p["prompt"], p.get("w", 1344), p.get("h", 768), seed, prefix,
                                     lora=lora, lora_strength=lora_strength)})["prompt_id"]
    while True:
        time.sleep(2)
        h = get(f"/history/{pid}")
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st.get("messages", []))[:2000])
            if st.get("completed"):
                files = [i["filename"] for o in h[pid]["outputs"].values() for i in o.get("images", [])]
                break
    dt = time.time() - t0
    with LOG.open("a") as f:
        f.write(json.dumps({"id": p["id"], "seed": seed, "w": p.get("w", 1344), "h": p.get("h", 768),
                            "model": "krea2_turbo_fp8_scaled", "steps": 8,
                            "lora": lora, "lora_strength": lora_strength if lora else None, "seconds": round(dt, 1),
                            "files": files, "prompt": p["prompt"], "at": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
    return files, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--only", default="")
    ap.add_argument("--seeds", type=int, default=1, help="renders per plate")
    ap.add_argument("--lora", help="LoRA file name in ComfyUI models/loras")
    ap.add_argument("--lora-strength", type=float, default=1.0)
    ap.add_argument("--free", action="store_true", help="POST /free between plates (gfx1101 slowdown workaround)")
    a = ap.parse_args()
    plates = json.loads(Path(a.book).read_text())
    only = set(filter(None, a.only.split(",")))
    for p in plates:
        if only and p["id"] not in only:
            continue
        seeds = [p["seed"]] if "seed" in p and a.seeds == 1 else [random.randrange(2**31) for _ in range(a.seeds)]
        for s in seeds:
            files, dt = render(p, s, a.lora, a.lora_strength)
            print(f"{p['id']}  seed {s}  {dt:5.1f}s  {files}", flush=True)
        if a.free:
            post("/free", {"unload_models": False, "free_memory": True})


if __name__ == "__main__":
    main()
