#!/usr/bin/env python3
"""Retime Wan's 16 fps motion clips to the film's 25 fps with RIFE 4.9 (in-between frames, not frame repeats).

    HIP_VISIBLE_DEVICES=0 ~/ComfyUI/venv/bin/python production/tools/retime.py [ID ...]   # default: every motion clip

Output frame k sits at source position k * 16/25; whole positions copy the source frame, the rest are RIFE in-betweens
of the two neighbours at that fraction. Writes media/clips/r25/<same name>.mp4 (H.264, crf 16) and skips clips already
done. RIFE's network code comes from ComfyUI-Frame-Interpolation (cloned to ~/tools/cfi, not installed into ComfyUI);
the weights are media/cache/models/rife/rife49.pth, loaded weights-only. Run it with ComfyUI stopped or idle.
"""

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path.home() / "ComfyUI"), str(Path.home() / "tools/cfi")]

import av  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from vfi_models.rife.rife_arch import IFNet  # noqa: E402

SRC, DST = 16, 25
OUT = ROOT / "media/clips/r25"


def model():
    m = IFNet(arch_ver="4.7")  # rife49 uses the 4.7 architecture (CKPT_NAME_VER_DICT in the node)
    m.load_state_dict(torch.load(ROOT / "media/cache/models/rife/rife49.pth", weights_only=True))
    return m.eval().half().to("cuda")


def retime(m, path):
    frames = [f.to_ndarray(format="rgb24") for f in av.open(path).decode(video=0)]
    h, w = frames[0].shape[:2]
    ph, pw = (32 - h % 32) % 32, (32 - w % 32) % 32  # RIFE wants sides divisible by 32
    t = lambda a: torch.nn.functional.pad(torch.from_numpy(a).permute(2, 0, 1)[None].float().div(255),
                                          (0, pw, 0, ph), mode="replicate").half().cuda()
    n_out = int((len(frames) - 1) * DST / SRC) + 1
    out = av.open(str(OUT / Path(path).name), "w")
    vs = out.add_stream("libx264", rate=DST)
    vs.width, vs.height, vs.pix_fmt, vs.options = w, h, "yuv420p", {"crf": "16", "preset": "slow"}
    with torch.inference_mode():
        for k in range(n_out):
            p = k * SRC / DST
            i, f = int(p), p - int(p)
            if f < 1e-3 or i + 1 >= len(frames):
                img = frames[min(i, len(frames) - 1)]
            else:
                mid = m(t(frames[i]), t(frames[i + 1]), timestep=f, scale_list=[8, 4, 2, 1], training=False,
                        fastmode=True, ensemble=False)
                img = (mid[0, :, :h, :w].clamp(0, 1).float().mul(255).round().byte().permute(1, 2, 0).cpu().numpy())
            for pk in vs.encode(av.VideoFrame.from_ndarray(np.ascontiguousarray(img), format="rgb24")):
                out.mux(pk)
    for pk in vs.encode():
        out.mux(pk)
    out.close()
    return len(frames), n_out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    book = json.loads((ROOT / "production/motion/clipbook.json").read_text())
    ids = sys.argv[1:] or [e["id"] for e in book if e["kind"] == "motion"]
    m = model()
    for cid in ids:
        files = sorted(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4")))
        if not files or (OUT / Path(files[-1]).name).exists():
            continue
        face = ROOT / "media/clips/face" / Path(files[-1]).name  # retime the face-passed take when there is one
        a, b = retime(m, str(face) if face.exists() else files[-1])
        print(cid, f"{a} -> {b} frames", flush=True)


if __name__ == "__main__":
    main()
