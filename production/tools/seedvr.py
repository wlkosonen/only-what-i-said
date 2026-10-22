#!/usr/bin/env python3
"""SeedVR2 video upscaling on this machine's AMD card: its own CLI (~/tools/SeedVR2/inference_cli.py), run unchanged,
with PyTorch's native GPU allocator: the CLI asks for cudaMallocAsync, which segfaults on ROCm at the first allocation
(22 Oct, traced with -X faulthandler). MIOpen stays OFF, as ComfyUI does on AMD. Never turn it on for this: on 22 Oct
SeedVR2's VAE through MIOpen ("No suitable algorithm ... unspecified launch failure") wedged the GPU, the driver reset
it, and Lati's desktop crashed with it. With MIOpen off a too-big job fails cleanly with a Python out-of-memory error.

    media/cache/seedvr-venv/bin/python production/tools/seedvr.py IN.mp4 --output OUT.mp4 [inference_cli args]

media/cache/seedvr-venv shares ComfyUI's ROCm torch through a .pth file and adds SeedVR2's own requirements.
"""

import os
import runpy
import sys
from pathlib import Path

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "backend:native"  # before torch: the CLI only sets it if unset
os.environ["PYTORCH_HIP_ALLOC_CONF"] = "backend:native"

import torch  # noqa: E402

torch.backends.cudnn.enabled = False  # MIOpen wedged the GPU and took the desktop down (22 Oct)

ROOT = Path(__file__).resolve().parents[2]
CLI = Path.home() / "tools/SeedVR2/inference_cli.py"

if "--model_dir" not in sys.argv:
    sys.argv += ["--model_dir", str(ROOT / "media/cache/models/seedvr2")]
args = sys.argv[1:]  # the CLI runs from its own folder: make the input and --output absolute first
for i, v in enumerate(args):
    if i == 0 or (i > 0 and args[i - 1] == "--output"):
        args[i] = str(Path(v).resolve())
sys.argv = [str(CLI)] + args
os.chdir(CLI.parent)
sys.path.insert(0, str(CLI.parent))
runpy.run_path(str(CLI), run_name="__main__")
