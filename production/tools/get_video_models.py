#!/usr/bin/env python3
"""Download the local video pilot's models (research 18 Oct 2026; Lati approved). Run with ComfyUI's venv python.

Big diffusion models go to /mnt/models/claudia-models (ComfyUI reads them via extra_model_paths.yaml); the rest to
~/ComfyUI/models. Each file lands in a staging folder on the same drive, then is moved into place.
"""
import os
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download

SSD = Path.home() / "ComfyUI/models"
DATA = Path("/mnt/models/claudia-models")
C21, C22 = "Comfy-Org/Wan_2.1_ComfyUI_repackaged", "Comfy-Org/Wan_2.2_ComfyUI_Repackaged"
FILES = [  # repo, path in repo, root, subfolder
    (C21, "split_files/text_encoders/umt5_xxl_fp16.safetensors", SSD, "text_encoders"),
    (C21, "split_files/vae/wan_2.1_vae.safetensors", SSD, "vae"),
    ("lightx2v/Wan2.2-Distill-Loras", "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors", SSD, "loras"),
    ("lightx2v/Wan2.2-Distill-Loras", "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors", SSD, "loras"),
    ("Kijai/wav2vec2_safetensors", "wav2vec2-chinese-base_fp16.safetensors", SSD, "audio_encoders"),
    ("Kijai/WanVideo_comfy", "Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors", SSD, "loras"),
    (C21, "split_files/clip_vision/clip_vision_h.safetensors", SSD, "clip_vision"),
    (C21, "split_files/model_patches/wan2.1_infiniteTalk_single_fp16.safetensors", DATA, "model_patches"),
    ("Kijai/WanVideo_comfy_fp8_scaled", "I2V/Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ.safetensors", DATA, "diffusion_models"),
    (C22, "split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", DATA, "diffusion_models"),
    (C22, "split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", DATA, "diffusion_models"),
]
for repo, path, root, sub in FILES:
    dest = root / sub / Path(path).name
    if dest.exists():
        print("have", dest); continue
    stage = root / ".staging"
    p = hf_hub_download(repo, path, local_dir=stage, token=os.environ.get("HF_TOKEN"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(p, dest)
    print("got ", dest, f"{dest.stat().st_size/1e9:.2f} GB", flush=True)
for root in (SSD, DATA):
    shutil.rmtree(root / ".staging", ignore_errors=True)
print("done")
