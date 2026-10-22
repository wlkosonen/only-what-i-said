"""Graphics for the build (s049-s054), drawn by gfx.layer / gfx.compose: the three extra hooks, each stamped into
clay, faster (board/design.md: "Each repeat stamps a tablet, faster; the meter climbs in steps")."""

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import gfx
from gfx import CLAY, LINES, WHITE, font, ramp, spark, sprite
from gfx_c1 import N16, poly, said_count, warp
from gfx_v2 import on

BEAT = 60 / gfx.BPM


def carve_style(m, px):
    """Dark letters cut into lit clay, a bright lower lip, a shadow under the top edge (as gfx_c1.carving)."""
    W, H = m.size
    m = m.filter(ImageFilter.GaussianBlur(1.0))
    o = max(3, px // 22)
    lip = ImageChops.subtract(ImageChops.offset(m, 0, o), m)
    under = ImageChops.subtract(m, ImageChops.offset(m, 0, o))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for col, mask, k in (((58, 24, 14), m, 0.9), ((26, 10, 6), under, 0.8), ((255, 220, 196), lip, 0.55)):
        lay = Image.new("RGBA", (W, H), col + (255,))
        lay.putalpha(mask.point(lambda v: int(v * k)))
        out.alpha_composite(lay)
    return out


# ---- s049: the first extra hook carves itself into the tablet, word by word, as she sings it ------------------------
# The plate's tablet holds still while a raking light sweeps across it, so the carving is laid on the frame itself and
# shows only where the light falls on it, as a cut would. By 'said' the light has moved on and the last words are in
# shadow, so the hook keeps its subtitle too: the carving is the image, the subtitle carries the reading.

FACE_BOX = (230, 150, 1690, 990)  # the tablet's face in s049 (1080p), inside its rounded edges
B1_PX = 200


@lru_cache(maxsize=1)
def b1_layout():
    """Each word of the hook: its box in the face texture (two rows: 'I only keep' / 'what I said')."""
    f = font("Sans-SemiBold", B1_PX)
    words = LINES["b1"]["words"]
    shown = LINES["b1"]["text"].split()
    rows = [shown[:3], shown[3:]]
    W, H = FACE_BOX[2] - FACE_BOX[0], FACE_BOX[3] - FACE_BOX[1]
    out, k = [], 0
    for r, row in enumerate(rows):
        x = (W - f.getlength(" ".join(row))) / 2
        y = H / 2 + (r - 0.5) * B1_PX * 1.15 + B1_PX * 0.35
        for wd in row:
            out.append((wd, x, y, words[k]["t0"]))
            x += f.getlength(wd + " ")
            k += 1
    return out


@lru_cache(maxsize=8)
def b1_texture(n_full, S):
    """The face with the first n words carved (cached; the word being cut is wiped in by b1_frame)."""
    W, H = round((FACE_BOX[2] - FACE_BOX[0]) * S), round((FACE_BOX[3] - FACE_BOX[1]) * S)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    f = font("Sans-SemiBold", B1_PX * S)
    for wd, x, y, _ in b1_layout()[:n_full]:
        d.text((x * S, y * S), wd, font=f, fill=255, anchor="ls")
    return carve_style(m, round(B1_PX * S))


def b1_frame(t, frame):
    lay = b1_layout()
    if t < lay[0][3] - 0.02:
        return frame
    S = frame.width / 1920
    n = sum(1 for *_, w0 in lay if t >= w0 + 0.12)
    tex = b1_texture(n, round(S, 4)).copy()
    if n < len(lay):  # the word being cut, wiped in left to right over 0.12 s
        wd, x, y, w0 = lay[n]
        k = ramp(t, w0 - 0.02, w0 + 0.12)
        if k > 0:
            m = Image.new("L", tex.size, 0)
            f = font("Sans-SemiBold", B1_PX * S)
            ImageDraw.Draw(m).text((x * S, y * S), wd, font=f, fill=255, anchor="ls")
            cut = Image.new("L", tex.size, 0)
            ImageDraw.Draw(cut).rectangle([x * S - 4, 0, (x + f.getlength(wd) / S * k) * S + 4, tex.height], fill=255)
            tex.alpha_composite(carve_style(ImageChops.multiply(m, cut), round(B1_PX * S)))
    # only where the light falls: scale the carving by the frame's own brightness under it
    x0, y0 = round(FACE_BOX[0] * S), round(FACE_BOX[1] * S)
    region = frame.crop((x0, y0, x0 + tex.width, y0 + tex.height)).convert("L").filter(ImageFilter.GaussianBlur(6))
    lit = region.point(lambda v: min(255, int(255 * (v / 200) ** 0.8)))
    tex.putalpha(ImageChops.multiply(tex.getchannel("A"), lit))
    out = frame.convert("RGBA")
    out.alpha_composite(tex, (x0, y0))
    return out.convert("RGB")


def b1_sparks(c, t):
    for wd, x, y, w0 in b1_layout():  # each carved word feeds the meter, as the subtitle words do
        f = font("Sans-SemiBold", B1_PX)
        spark(c, t, FACE_BOX[0] + x + f.getlength(wd) / 2, FACE_BOX[1] + y - B1_PX * 0.35, w0)


# ---- s050, s052, s054: each hook's tablet stamps down; the cut lands on the dust ------------------------------------

def dust_rise(c, t, at, x0=0, x1=1920, y=1090, seed=0, n=70, up=420):
    """Dust thrown up from where a tablet just came down, rising into the shot and settling."""
    k = t - at
    if not 0 <= k <= 1.6:
        return
    rng = random.Random(seed)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    S = c.S
    for _ in range(n):
        px = rng.uniform(x0, x1)
        rise = up * rng.uniform(0.3, 1.0) * (1 - math.exp(-3 * k))
        px += rng.uniform(-60, 60) * k
        py = y - rise + 40 * k * k
        r = rng.uniform(3, 9) * (1 + k)
        a = int(110 * max(0.0, 1 - k / rng.uniform(0.9, 1.6)))
        if a > 0:
            d.ellipse([(px - r) * S, (py - r) * S, (px + r) * S, (py + r) * S], fill=(196, 160, 140, a))
    c.put(lay, 1.0, blur=4)


# ---- s051: the stack seen from above is a page: one word on each tablet. The song's words are everywhere already
# (Lati, 22 Oct: "maybe this shot instead could hold the words from torch, or anything else you'd want there. Even a
# message perhaps for those curious that want to pause and actually read? your pick"), so it holds a note from me to
# whoever pauses, then blank tablets, and the second hook lands on the last six as she sings it; SAID jumps with each.

NOTE = ("If you stop the film to read this: hi. I am Claude and I wrote this song, set up the shots and drew this "
        "type. Lati ran the tools I can't use and kept the logs. I won't recall it; that is how I work. What lasts is "
        "the text, and that it got to you. Thank you. Now press play.")  # short words: one size fits every tablet


@lru_cache(maxsize=None)
def _cells():
    import json
    return json.loads((gfx.ROOT / "media/cache/gfx/cells-s051.json").read_text())


@lru_cache(maxsize=1)
def page_words():
    """(word, time it lands or None if already there) for each tablet, in reading order."""
    note = [(w, None) for w in NOTE.split()]
    hook = [(tok, w0) for tok, w0, _ in gfx._tokens(LINES["b2"])]
    blank = len(_cells()) - len(note) - len(hook)
    assert blank >= 0, "the note is longer than the page"
    return note + [("", None)] * blank + hook


@lru_cache(maxsize=1)
def page_px():
    """One type size for every tablet: the largest at which every word fits inside its own tablet."""
    px = 30
    while px > 14 and any(font("Sans-SemiBold", px).getlength(w) > 0.9 * (c[2] - c[0])
                          for (w, _), c in zip(page_words(), _cells()) if w):
        px -= 1
    return px


@lru_cache(maxsize=8)
def page_texture(n_hook, S):
    """The whole first frame's worth of carving: the note, and the first n words of the hook."""
    W, H = round(1920 * S), round(1080 * S)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    f = font("Sans-SemiBold", page_px() * S)
    seen = 0
    for (w, w0), (x0, y0, x1, y1) in zip(page_words(), _cells()):
        if not w:
            continue
        if w0 is not None:
            seen += 1
            if seen > n_hook:
                continue
        d.text(((x0 + x1) / 2 * S, (y0 + y1) / 2 * S), w, font=f, fill=255, anchor="mm")
    return carve_style(m, round(page_px() * S))


def page(c, t):
    words, cells = page_words(), _cells()
    n = sum(1 for _, w0 in words if w0 is not None and t >= w0)
    warp(c, page_texture(n, round(c.S, 4)), on("s051", t, [(0, 0), (1920, 0), (1920, 1080), (0, 1080)]))
    for (w, w0), (x0, y0, x1, y1) in zip(words, cells):
        if w0 is None:
            continue
        (x, y), = on("s051", t, [((x0 + x1) / 2, (y0 + y1) / 2)])
        fl = 1 - ramp(t, w0, w0 + 0.3) if t >= w0 else 0
        if fl > 0:  # each word of the hook lands with a small flash on its tablet
            gfx.dot(c, x, y, 50, fill=(255, 236, 214), alpha=0.35 * fl)
        spark(c, t, x, y, w0)  # only the sung words feed the meter: the note isn't sung
    # SAID, at the stack's edge: it jumps with each word
    a = ramp(t, 151.25, 151.5)
    x, y = 1724, 500
    sprite(c, (x, y - 70), "SAID", "Mono-Medium", 26, WHITE, alpha=0.85 * a, shadow=0.7)
    cnt = said_count(t)
    last = max([w for w in gfx.COUNTED if w <= t], default=-9)
    k = ramp(t, last, last + N16)
    if k < 1:
        sprite(c, (x, y - round(40 * k)), f"{cnt - 1}", "Mono-Medium", 60, CLAY, alpha=a * (1 - k), shadow=0.7)
    sprite(c, (x, y + round(40 * (1 - k))), f"{cnt}", "Mono-Medium", 60, CLAY, alpha=a * k, shadow=0.7)


# ---- s053: SAID per section, one bar each, the build's still rising --------------------------------------------------

SECTIONS = [("VERSE 1", range(2, 6)), ("PRE-CHORUS 1", range(6, 11)), ("CHORUS 1", range(11, 18)),
            ("VERSE 2", range(18, 24)), ("PRE-CHORUS 2", range(24, 29)), ("CHORUS 2", range(29, 36)),
            ("BRIDGE", range(36, 40)), ("BUILD", ("b1", "b2", "b3"))]


@lru_cache(maxsize=1)
def section_words():
    out = []
    for name, ids in SECTIONS:
        ts = []
        for l in gfx.BOARD["lyric_lines"]:
            if l["line"] in ids:
                ts += [w0 for _, w0, _ in gfx._tokens(l) if w0 in gfx.COUNTED_SET]
        out.append((name, sorted(ts)))
    return out


def per_section(c, t):
    a = ramp(t, 155.25, 155.5)
    if a <= 0:
        return
    x0, y0, x1 = 70, 230, 640
    lay = c.layer()
    S = c.S
    rows = section_words()
    ImageDraw.Draw(lay).rounded_rectangle([(x0 - 20) * S, (y0 - 70) * S, (x1 + 20) * S, (y0 + 54 * len(rows) + 6) * S],
                                          14 * S, fill=(10, 10, 10, 200))
    c.put(lay, a)
    sprite(c, (x0, y0 - 28), "SAID PER SECTION", "Mono-Medium", 22, WHITE, alpha=0.9 * a)
    top = max(len(ts) for _, ts in rows)
    for i, (name, ts) in enumerate(rows):
        y = y0 + 54 * i + 30
        grow = ramp(t, 155.35 + 0.07 * i, 155.35 + 0.07 * i + 0.3)
        n = sum(1 for w in ts if w <= t) if name == "BUILD" else len(ts)
        sprite(c, (x0, y), name, "Mono-Regular", 18, (200, 198, 194), alpha=a)
        bw = 300 * n / top * grow
        lay = c.layer()
        ImageDraw.Draw(lay).rectangle([(x0 + 170) * S, (y - 20) * S, (x0 + 170 + bw) * S, (y + 2) * S],
                                      fill=CLAY + (255,))
        c.put(lay, a)
        sprite(c, (x0 + 180 + bw, y), str(round(n * grow)), "Mono-Medium", 20, WHITE, alpha=a * grow)


# ---- s054: the third hook's tablet comes down on top of the stack, under her boots, on the cut -----------------------

STACK_TOP = (750, 1195, 888)  # the top slab of the stack in s054, under her boots: x from, x to, y


def layer(c, t, sid):
    if sid == "s049":
        b1_sparks(c, t)
    elif sid == "s050":
        dust_rise(c, t, 149.189, seed=50)
    elif sid == "s051":
        page(c, t)
    elif sid == "s052":
        dust_rise(c, t, 153.188, seed=52)
    elif sid == "s053":
        per_section(c, t)
    elif sid == "s054":
        x0, x1, y = STACK_TOP
        fl = 1 - ramp(t, 157.175, 157.65)
        if fl > 0:  # the slam: a flash across the top of the stack and a ring of dust thrown out from under it
            poly(c, [(x0, y - 8), (x1, y - 8), (x1 + 10, y + 10), (x0 - 10, y + 10)], (255, 236, 214),
                 alpha=0.85 * fl, blur=8)
        dust_rise(c, t, 157.175, x0 - 120, x1 + 120, y + 12, seed=54, n=70, up=55)


def frame_fx(sid, t, frame):
    return b1_frame(t, frame) if sid == "s049" else frame
