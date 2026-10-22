#!/usr/bin/env python3
"""Local video through ComfyUI's built-in nodes: InfiniteTalk lip sync (Wan 2.1) and Wan 2.2 I2V motion.

    python3 production/tools/video.py sung   --image PLATE.png --audio VOCAL.wav --prompt "..." --id C1B [--variant fast|hq]
    python3 production/tools/video.py motion --image PLATE.png --prompt "..." --id M007 [--seconds 5] [--variant fast|hq]

Graphs follow ComfyUI's own templates (video_wan2_1_infinitetalk, video_wan2_2_14B_i2v), single speaker, no custom
nodes. Inputs are copied into ComfyUI's input folder; the MP4 lands in media/clips/local/. Each run is logged to
production/motion/local-runs.jsonl with its settings and wall time.

fast: InfiniteTalk 832x480, 6 steps with the lightx2v distill LoRA; Wan 2.2 1280x720, 4 steps with the lightx2v LoRAs.
hq:   InfiniteTalk 1280x720, same sampler; Wan 2.2 1280x720, 20 steps, CFG 3.5, no speed LoRA (the template's default).
"""

import argparse
import json
import random
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMFY = Path.home() / "ComfyUI"
URL = "http://127.0.0.1:8188"
OUT = ROOT / "media/clips/local"
OUTDIRS = [ROOT / "media/plates", COMFY / "output"]  # ComfyUI runs with --output-directory media/plates
LOG = ROOT / "production/motion/local-runs.jsonl"
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，"
       "多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")


def post(path, body):
    r = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    b = urllib.request.urlopen(r).read()
    return json.loads(b) if b.strip() else {}


def get(path):
    return json.load(urllib.request.urlopen(URL + path))


def stage(path):
    dest = COMFY / "input" / Path(path).name
    shutil.copy(path, dest)
    return dest.name


def sung_graph(image, audio, prompt, seed, variant, frames, prefix, size=None):
    w, h = size or ((832, 480) if variant == "fast" else (1280, 720))
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ.safetensors",
                                                     "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "strength_model": 1.0,
              "lora_name": "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"}},
        "3": {"class_type": "ModelPatchLoader", "inputs": {"name": "wan2.1_infiniteTalk_single_fp16.safetensors"}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp16.safetensors", "type": "wan",
                                                     "device": "default"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 0]}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "8": {"class_type": "AudioEncoderLoader", "inputs": {"audio_encoder_name": "wav2vec2-chinese-base_fp16.safetensors"}},
        "9": {"class_type": "LoadAudio", "inputs": {"audio": audio}},
        "10": {"class_type": "AudioEncoderEncode", "inputs": {"audio_encoder": ["8", 0], "audio": ["9", 0]}},
        "11": {"class_type": "LoadImage", "inputs": {"image": image}},
        "12": {"class_type": "WanInfiniteTalkToVideo", "inputs": {
            "mode": "single_speaker", "model": ["2", 0], "model_patch": ["3", 0], "positive": ["5", 0],
            "negative": ["6", 0], "vae": ["7", 0], "width": w, "height": h, "length": frames,
            "audio_encoder_output_1": ["10", 0], "start_image": ["11", 0], "motion_frame_count": 9, "audio_scale": 1.0}},
        "13": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "14": {"class_type": "BasicScheduler", "inputs": {"model": ["12", 0], "scheduler": "normal", "steps": 6,
                                                          "denoise": 1.0}},
        "15": {"class_type": "CFGGuider", "inputs": {"model": ["12", 0], "positive": ["12", 1], "negative": ["12", 2],
                                                     "cfg": 1.0}},
        "16": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "17": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["16", 0], "guider": ["15", 0],
               "sampler": ["13", 0], "sigmas": ["14", 0], "latent_image": ["12", 3]}},
        # plain VAEDecode: on OOM ComfyUI retries tiled with sizes that fit (a fixed 512/32 tiling OOMs at 832x480
        # while the InfiniteTalk patch is still resident)
        "18": {"class_type": "VAEDecode", "inputs": {"samples": ["17", 0], "vae": ["7", 0]}},
        "19": {"class_type": "CreateVideo", "inputs": {"images": ["18", 0], "audio": ["9", 0], "fps": 25.0}},
        "20": {"class_type": "SaveVideo", "inputs": {"video": ["19", 0], "filename_prefix": prefix, "format": "mp4",
                                                     "codec": "h264"}},
    }


def extend(g, frames, seed, chunk=81, motion=9):
    """Multi-pass InfiniteTalk for clips past ~121 frames (more OOMs on 16 GB at 832x480): pass 1 makes `chunk` frames;
    each next pass continues from everything made so far (the node offsets the audio by len(previous_frames) - motion
    and re-makes the last `motion` frames, which are trimmed), as in ComfyUI's video_wan2_1_infinitetalk template.
    OU2's 190 frames failed as 81 + 121, so no pass is longer than `chunk`. Passes are equal: S055 (157 frames) as
    81 + 81 + 13 OOMed in the final decode three times, so it runs as 61 + 61 + 53."""
    passes = -(-(frames - chunk) // (chunk - motion)) + 1
    chunk = (-(-(frames + (passes - 1) * motion - 1) // passes) + 3) // 4 * 4 + 1
    g["12"]["inputs"]["length"] = chunk
    have, acc, n = chunk, ["18", 0], 0
    while have < frames:
        n += 1
        k = 100 + 10 * n
        length = min(chunk, ((frames - have + motion - 1 + 3) // 4) * 4 + 1)
        g[str(k)] = {"class_type": "WanInfiniteTalkToVideo", "inputs": dict(g["12"]["inputs"], length=length,
                                                                            previous_frames=acc)}
        g[str(k + 1)] = {"class_type": "CFGGuider", "inputs": {"model": [str(k), 0], "positive": [str(k), 1],
                                                               "negative": [str(k), 2], "cfg": 1.0}}
        g[str(k + 2)] = {"class_type": "BasicScheduler", "inputs": {"model": [str(k), 0], "scheduler": "normal",
                                                                    "steps": 6, "denoise": 1.0}}
        g[str(k + 3)] = {"class_type": "RandomNoise", "inputs": {"noise_seed": seed + n}}
        g[str(k + 4)] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": [str(k + 3), 0],
                         "guider": [str(k + 1), 0], "sampler": ["13", 0], "sigmas": [str(k + 2), 0],
                         "latent_image": [str(k), 3]}}
        g[str(k + 5)] = {"class_type": "VAEDecode", "inputs": {"samples": [str(k + 4), 0], "vae": ["7", 0]}}
        g[str(k + 6)] = {"class_type": "ImageFromBatch", "inputs": {"image": [str(k + 5), 0], "batch_index": motion,
                                                                    "length": length - motion}}
        g[str(k + 7)] = {"class_type": "ImageBatch", "inputs": {"image1": acc, "image2": [str(k + 6), 0]}}
        acc, have = [str(k + 7), 0], have + length - motion
    g["19"]["inputs"]["images"] = acc
    return g


def motion_graph(image, prompt, seed, variant, frames, prefix, size=None):
    mw, mh = size or (1280, 720)
    fast = variant == "fast"
    steps, cfg, split = (4, 1.0, 2) if fast else (20, 3.5, 10)
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                                                     "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
                                                     "weight_dtype": "default"}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp16.safetensors", "type": "wan",
                                                     "device": "default"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 0]}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "11": {"class_type": "LoadImage", "inputs": {"image": image}},
        "12": {"class_type": "WanImageToVideo", "inputs": {"positive": ["5", 0], "negative": ["6", 0], "vae": ["7", 0],
               "width": mw, "height": mh, "length": frames, "batch_size": 1, "start_image": ["11", 0]}},
    }
    hi, lo = ["1", 0], ["2", 0]
    if fast:
        g["21"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": hi, "strength_model": 1.0,
                   "lora_name": "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors"}}
        g["22"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": lo, "strength_model": 1.0,
                   "lora_name": "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors"}}
        hi, lo = ["21", 0], ["22", 0]
    g["23"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": hi, "shift": 5.0}}
    g["24"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": lo, "shift": 5.0}}
    common = {"positive": ["12", 0], "negative": ["12", 1], "steps": steps, "cfg": cfg, "sampler_name": "euler",
              "scheduler": "simple"}
    g["25"] = {"class_type": "KSamplerAdvanced", "inputs": dict(common, model=["23", 0], latent_image=["12", 2],
               add_noise="enable", noise_seed=seed, start_at_step=0, end_at_step=split,
               return_with_leftover_noise="enable")}
    g["26"] = {"class_type": "KSamplerAdvanced", "inputs": dict(common, model=["24", 0], latent_image=["25", 0],
               add_noise="disable", noise_seed=0, start_at_step=split, end_at_step=10000,
               return_with_leftover_noise="disable")}
    g["27"] = {"class_type": "VAEDecode", "inputs": {"samples": ["26", 0], "vae": ["7", 0]}}
    g["28"] = {"class_type": "CreateVideo", "inputs": {"images": ["27", 0], "fps": 16.0}}
    g["29"] = {"class_type": "SaveVideo", "inputs": {"video": ["28", 0], "filename_prefix": prefix, "format": "mp4",
                                                     "codec": "h264"}}
    return g


def run(graph, meta):
    t0 = time.time()
    pid = post("/prompt", {"prompt": graph})["prompt_id"]
    while True:
        time.sleep(10)
        h = get(f"/history/{pid}")
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                err = next((m[1] for m in st.get("messages", []) if m[0] == "execution_error"), {})
                raise SystemExit(f"ComfyUI error in {err.get('node_type')}: {err.get('exception_type')}: "
                                 f"{str(err.get('exception_message', ''))[:800]}")
            if st.get("completed"):
                break
    files = []
    for o in h[pid]["outputs"].values():
        for key in ("images", "videos", "gifs"):
            for f in o.get(key, []):
                src = next((d / f.get("subfolder", "") / f["filename"] for d in OUTDIRS
                            if (d / f.get("subfolder", "") / f["filename"]).exists()), None)
                if src is None:
                    continue
                if src.suffix == ".mp4":
                    OUT.mkdir(parents=True, exist_ok=True)
                    dst = OUT / src.name
                    shutil.copy(src, dst)
                    files.append(str(dst.relative_to(ROOT)))
    meta.update(seconds=round(time.time() - t0, 1), files=files, at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    with LOG.open("a") as f:
        f.write(json.dumps(meta) + "\n")
    print(json.dumps(meta))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["sung", "motion"])
    ap.add_argument("--image", required=True)
    ap.add_argument("--audio")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--variant", default="fast", choices=["fast", "hq"])
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--size", default=None, help="WxH override, e.g. 960x544")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randrange(2**31)
    size = tuple(int(v) for v in a.size.split('x')) if a.size else None
    img = stage(a.image)
    prefix = f"local/{a.id}-{a.variant}{('-' + a.size) if a.size else ''}-s{seed}"
    if a.kind == "sung":
        frames = int(a.seconds * 25) // 4 * 4 + 1
        g = sung_graph(img, stage(a.audio), a.prompt, seed, a.variant, frames, prefix, size)
        if frames > 121:
            g = extend(g, frames, seed)
    else:
        frames = int(a.seconds * 16) // 4 * 4 + 1
        g = motion_graph(img, a.prompt, seed, a.variant, frames, prefix, size)
    run(g, {"id": a.id, "kind": a.kind, "variant": a.variant, "seed": seed, "frames": frames, "prompt": a.prompt,
            "image": a.image, "audio": a.audio})


if __name__ == "__main__":
    main()
