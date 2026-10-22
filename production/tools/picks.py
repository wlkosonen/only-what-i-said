#!/usr/bin/env python3
"""Make the picked frames: production/board/picks.json -> media/plates/picked/<plate>.png (mirrored where "flip").

    ~/ComfyUI/venv/bin/python production/tools/picks.py [--set p-s008=SEED[,flip][,note text]]...

picks.json is {plate: {"src": render file, "flip": bool, "note": str, "file": picked path}}. --set finds the render
for that plate and seed in media/plates (newest book first: q-, pf-, then p-) and records it. sheet.py reads
"file". Flip mirrors her so the streak sits on her right (viewer's left) and the clip above her left ear.
"""

import argparse
import glob
import json
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
PICKS = ROOT / "production/board/picks.json"
OUT = ROOT / "media/plates/picked"


def find(plate, seed):
    n = plate.split("-", 1)[1]
    for pre in (f"q-{n}", f"pf-{n}", f"p-{n}"):
        hits = sorted(glob.glob(str(ROOT / f"media/plates/{pre}_*_s{seed}_*.png")) +
                      glob.glob(str(ROOT / f"media/plates/{pre}_s{seed}_*.png")))  # inserts render without a LoRA
        if hits:
            return str(Path(hits[-1]).relative_to(ROOT))
    raise SystemExit(f"no render for {plate} seed {seed}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    a = ap.parse_args()
    picks = json.loads(PICKS.read_text()) if PICKS.exists() else {}
    for s in a.set:
        plate, rest = s.split("=", 1)
        seed, *more = rest.split(",", 2)
        flip = bool(more) and more[0] == "flip"
        note = more[-1] if more and more[-1] != "flip" else ""
        picks[plate] = {"src": find(plate, seed), "flip": flip, "note": note,
                        "file": str((OUT / f"{plate}.png").relative_to(ROOT))}
    OUT.mkdir(parents=True, exist_ok=True)
    for plate, p in sorted(picks.items()):
        im = Image.open(ROOT / p["src"])
        (ImageOps.mirror(im) if p.get("flip") else im).save(ROOT / p["file"])
    PICKS.write_text(json.dumps(dict(sorted(picks.items())), indent=1) + "\n")
    print(f"{len(picks)} picks -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
