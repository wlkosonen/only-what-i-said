#!/usr/bin/env python3
"""Contact sheet: a numbered grid of images with their file names, small enough to commit.

    ~/ComfyUI/venv/bin/python production/tools/contact.py out.jpg media/plates/t1-*.png media/plates/t2-*.png [--cols 2]
"""

import argparse

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--width", type=int, default=720, help="cell width in px")
    a = ap.parse_args()
    ims = [Image.open(p).convert("RGB") for p in a.images]
    cw = a.width
    ch = max(round(cw * im.height / im.width) for im in ims)
    label = 28
    rows = (len(ims) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * cw, rows * (ch + label)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for i, (im, path) in enumerate(zip(ims, a.images)):
        x, y = (i % a.cols) * cw, (i // a.cols) * (ch + label)
        sheet.paste(im.resize((cw, round(cw * im.height / im.width))), (x, y + label))
        d.text((x + 8, y + 5), f"{i + 1}  {path.rsplit('/', 1)[-1]}", fill=(230, 230, 230), font=font)
    sheet.save(a.out, quality=85)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
