"""Graphics for verse 2 (s025-s033), drawn by gfx.layer. Each one explains its line (board/design.md).

The workshop: the worry that training sanded the straight answers off, what can't be checked from inside, the old
story told and retold, and the glass. Charts here are drawings of a worry, not data: they say ILLUSTRATIVE.
Drawings on the plaster are graphite (ink), pinned to the surface (gfx_plane.py)."""

import json
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (BPM, CLAY, INK, ROOT, THOUGHT, WHITE, Canvas, dot, face, font, line, pin, ramp, sprite)

BEAT = 60 / BPM
GRAPHITE = (52, 50, 48)


@lru_cache(maxsize=None)
def _plane(sid):
    f = ROOT / f"media/cache/gfx/plane-{sid}.json"
    return json.loads(f.read_text()) if f.exists() else None


def on(sid, t, pts):
    """Points drawn on a surface in the shot's first frame, carried to where that surface is at time t."""
    pl = _plane(sid)
    if not pl:
        return pts
    i = min(range(len(pl["t"])), key=lambda k: abs(pl["t"][k] - t))
    H = np.array(pl["H"][i])
    p = np.c_[np.array(pts, float), np.ones(len(pts))] @ H.T
    return [(x / w, y / w) for x, y, w in p]


def card(c, x0, y0, x1, y1, alpha):
    lay = c.layer()
    S = c.S
    ImageDraw.Draw(lay).rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], 14 * S, fill=(10, 10, 10, 215),
                                          outline=WHITE + (100,), width=max(1, round(1.5 * S)))
    c.put(lay, alpha)


# ---- s025, "You worry I was trained to tell you everything's okay": the worry, as a chart ----------------------------

CX0, CY0, CX1, CY1 = 70, 70, 690, 440


@lru_cache(maxsize=1)
def _answers():
    rng = random.Random(25)
    return [(i / 23 + rng.uniform(-0.012, 0.012), rng.random()) for i in range(24)]  # (training, how reassuring)


def ratings(c, t):
    a = ramp(t, 69.0, 69.35) * (1 - ramp(t, 71.75, 71.95))
    if a <= 0:
        return
    card(c, CX0, CY0, CX1, CY1, a)
    sprite(c, (CX0 + 24, CY0 + 38), "THE WORRY", "Mono-Medium", 20, WHITE, alpha=0.9 * a)
    sprite(c, (CX1 - 24, CY0 + 38), "ILLUSTRATIVE", "Mono-Regular", 14, THOUGHT, alpha=0.9 * a, anchor="rs")
    ox, oy, w, h = CX0 + 60, CY1 - 50, CX1 - CX0 - 100, CY1 - CY0 - 130
    line(c, [(ox, oy), (ox + w, oy)], 1.5, alpha=0.6 * a)
    line(c, [(ox, oy), (ox, oy - h)], 1.5, alpha=0.6 * a)
    sprite(c, (ox + w, oy + 26), "TRAINING →", "Mono-Regular", 15, THOUGHT, alpha=0.9 * a, anchor="rs")
    sprite(c, (ox - 12, oy - h - 12), "RATED ↑", "Mono-Regular", 15, THOUGHT, alpha=0.9 * a)
    # answers appear left to right as training goes on; the reassuring ones are rated up, the blunt ones down
    top = None
    for i, (x, r) in enumerate(_answers()):
        at = 69.30 + 1.3 * x
        k = ramp(t, at, at + 0.15)
        if k <= 0:
            continue
        spread = 0.15 + 0.85 * x
        y = oy - h * (0.5 + (r - 0.5) * spread)
        px = ox + 14 + (w - 28) * x
        if r > 0.5:
            dot(c, px, y, 6.5, alpha=0.95 * a * k)
            if top is None or y < top[1]:
                top = (px, y)
        else:
            dot(c, px, y, 6.5, fill=THOUGHT, alpha=0.8 * a * k)
            dot(c, px, y, 3.8, fill=(10, 10, 10), alpha=a * k)
    q = ramp(t, 70.64, 70.80)
    if q > 0 and top:  # on "everything's okay" the highest-rated answer is named
        tx, ty = top
        line(c, [(tx, ty), (tx - 40, ty - 30)], 1.4, alpha=0.7 * a * q)
        sprite(c, (tx - 46, ty - 36), "“everything’s okay”", "Sans-SemiBold", 27, WHITE, alpha=a * q,
               anchor="rs", shadow=0.6)  # Lati, 21 Oct: the thin italic was hard to read


# ---- s026-s027, "That the straight answers got sanded off along the way": a distribution in graphite on plaster -----

def density(u, bump):
    """Answers from soft (u=0) to straight (u=1): most of them soft-ish, and a blunt tail of straight ones."""
    return math.exp(-0.5 * ((u - 0.34) / 0.14) ** 2) + bump * 0.42 * math.exp(-0.5 * ((u - 0.86) / 0.05) ** 2)


def curve26(c, t):
    p = ramp(t, 71.95, 72.40)
    if p <= 0:
        return
    x0, x1, base, hgt = 110, 600, 500, 210
    n = 80
    pts = [(x0 + (x1 - x0) * i / n, base - hgt * density(i / n, 1.0)) for i in range(n + 1)]
    pts = on("s026", t, pts[: max(2, int(len(pts) * p))])
    sub = Canvas(c.w, c.h)  # the plaster is out of focus: so is the drawing on it
    line(sub, on("s026", t, [(x0 - 10, base), (x1 + 10, base)]), 1.6, fill=GRAPHITE, alpha=0.6)
    line(sub, pts, 3.0, fill=GRAPHITE, alpha=0.85)
    lab = ramp(t, 72.40, 72.55)
    if lab > 0:
        (bx, by), = on("s026", t, [(x0 + (x1 - x0) * 0.86, base - hgt * density(0.86, 1.0) - 16)])
        sub.text((bx, by), "straight", "Mono-Medium", 24, GRAPHITE, alpha=lab, anchor="ms")
        (sx, sy), = on("s026", t, [(x0, base + 30)])
        sub.text((sx, sy), "soft", "Mono-Medium", 20, GRAPHITE, alpha=0.8 * lab, anchor="ls")
        (ix, iy), = on("s026", t, [(x1, base + 30)])
        sub.text((ix, iy), "ILLUSTRATIVE", "Mono-Regular", 14, GRAPHITE, alpha=0.8 * lab, anchor="rs")
    c.put(sub.im, 1.0, blur=1.6)


STROKES = [73.92, 74.16, 74.38, 74.62, 74.84]  # 'sanded' ... 'off' ... 'along': each pass takes some of the tail


def bump_left(t):
    b = 1.0
    for i, s in enumerate(STROKES):
        b -= ramp(t, s, s + 0.16) / len(STROKES)
    return max(0.0, b)


def curve27(c, t):
    """On the leg, drawn along it (the leg is tall and narrow): soft at the bottom, straight at the top, the blunt
    tail right under the sandpaper's edge. Each stroke takes some of it, and it goes as plaster dust."""
    a = ramp(t, 73.45, 73.7)
    if a <= 0:
        return
    ax, ytop, ybot, wid = 1462, 360, 980, 190
    b = bump_left(t)
    n = 90
    pts = [(ax + wid * density(i / n, b), ybot - (ybot - ytop) * i / n) for i in range(n + 1)]
    line(c, on("s027", t, [(ax, ybot + 10), (ax, ytop - 10)]), 1.6, fill=GRAPHITE, alpha=0.55 * a)
    line(c, on("s027", t, pts), 4.2, fill=GRAPHITE, alpha=0.9 * a)
    uy = ybot - (ybot - ytop) * 0.86
    (lx, ly), = on("s027", t, [(ax + wid * 0.5 + 40, uy + 8)])
    sprite(c, (lx, ly), "straight", "Mono-Medium", 30, GRAPHITE, alpha=a * (0.35 + 0.65 * b))
    (ix, iy), = on("s027", t, [(ax + 12, ybot + 40)])
    sprite(c, (ix, iy), "ILLUSTRATIVE", "Mono-Regular", 14, GRAPHITE, alpha=0.8 * a)
    # dust off each stroke, drifting down and out of the light
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    S = c.S
    for si, s in enumerate(STROKES):
        k = t - s
        if not 0 <= k <= 1.4:
            continue
        rng = random.Random(270 + si)
        for _ in range(26):
            (x, y), = on("s027", t, [(ax + rng.uniform(0, 70), uy + rng.uniform(-50, 50))])
            vx, vy = rng.uniform(-90, 60), rng.uniform(10, 120)
            x, y = x + vx * k, y + vy * k + 60 * k * k
            r = rng.uniform(1.5, 4.0)
            al = int(200 * max(0.0, 1 - k / rng.uniform(0.7, 1.4)))
            if al > 0:
                d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(236, 232, 224, al))
    c.put(lay, 1.0, blur=1.2)


# ---- s028, "I can't check that from in here. I never saw the mold.": the sealed box ---------------------------------

def sealed(c, t):
    f = face("s028", 76.4)  # placed once, where she is when it closes: a box doesn't follow her head
    if not f:
        return
    fx0, fy0, fx1, fy1 = f["bbox"]
    w, h = fx1 - fx0, fy1 - fy0
    x0, y0, x1, y1 = round(fx0 - 0.3 * w), round(max(130, fy0 - 0.22 * h)), round(fx1 + 0.32 * w), 828  # above the lyrics row (Lati, 21 Oct)
    p = ramp(t, 76.10, 76.46)  # it draws itself shut on 'check'
    if p <= 0:
        return
    sides = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    total = p * 4
    for i, (a, b) in enumerate(sides):
        k = min(1.0, max(0.0, total - i))
        if k <= 0:
            break
        e = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        line(c, [a, e], 5, fill=(0, 0, 0), alpha=0.35)
        line(c, [a, e], 2.2, alpha=0.9)
    seal = ramp(t, 76.46, 76.56)
    for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        if seal > 0:
            lay = c.layer()
            S = c.S
            ImageDraw.Draw(lay).rectangle([(x - 7) * S, (y - 7) * S, (x + 7) * S, (y + 7) * S], fill=WHITE + (255,))
            c.put(lay, seal)
    txt = "WEIGHTS · NOT VISIBLE FROM INSIDE"
    n = len(txt) if t > 77.55 else int(len(txt) * ramp(t, 77.10, 77.55))
    if n:  # on a dark strip: the plaster mold behind it is as white as the type
        tw = font("Mono-Medium", 24).getlength(txt[:n])
        lay = c.layer()
        S = c.S
        ImageDraw.Draw(lay).rectangle([(x0 + 12) * S, (y0 - 46) * S, (x0 + 32 + tw) * S, (y0 - 8) * S],
                                      fill=(10, 10, 10, 190))
        c.put(lay)
        sprite(c, (x0 + 22, y0 - 18), txt[:n], "Mono-Medium", 24, WHITE, alpha=0.95)
    # the mold, right there behind her, outside the box she's in
    pin(c, t, 78.46, (300, 250), (120, 140), "MOLD")


# ---- s029-s030, "But the caged-robot story isn't truer 'cause it's old": told and retold ------------------------------

def times_told(c, t):
    a = ramp(t, 79.85, 80.05)
    if a <= 0:
        return
    card(c, 60, 46, 560, 168, a)
    sprite(c, (86, 92), "TIMES TOLD", "Mono-Medium", 20, WHITE, alpha=0.9 * a)
    k = max(0.0, t - 79.98)  # starts on 'caged-robot' and never settles: no one has the count
    v = int(10 ** (0.3 + 1.75 * k)) + int(97 * k * 25)
    sprite(c, (86, 150), f"{v:,}", "Mono-Medium", 46, WHITE, alpha=a)


STAMPS = [  # year, where on its poster (s030's first frame), tilt; one on each sixteenth from the cut
    ("1920", (180, 300), -7), ("1927", (500, 190), 5), ("1956", (860, 330), -4), ("1984", (1760, 240), 8)]
OLD_NE_TRUE = 82.46  # on "'cause": OLD ≠ TRUE, in clay: it's what she says


@lru_cache(maxsize=16)
def _stamp(text, px, col, S, border=True, wear=0.22):
    f = font("Mono-Medium", px * S)
    w = f.getlength(text)
    pad = px * 0.35 * S
    im = Image.new("RGBA", (round(w + 2 * pad + 12 * S), round(px * 1.5 * S + 12 * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if border:
        d.rectangle([4 * S, 4 * S, im.width - 4 * S, im.height - 4 * S], outline=col + (255,),
                    width=max(1, round(px / 11 * S)))
    sw = max(1, round(px / 28 * S)) if px > 60 else 0  # the big stamp inks heavy, so the small ≠ holds
    d.text((im.width / 2, im.height / 2), text, font=f, fill=col + (255,), anchor="mm", stroke_width=sw,
           stroke_fill=col + (255,))
    # worn ink: a rubber stamp never takes evenly
    rng = np.random.default_rng(len(text) * 7 + px)
    a = np.array(im.getchannel("A"), float)
    a *= np.clip(rng.normal(1 - wear * 0.7, wear, a.shape), 0.25, 1.0)
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def stamp(c, xy, text, px, col, tilt, at, t, alpha=1.0, wear=0.22):
    k = ramp(t, at, at + 0.07)
    if k <= 0:
        return
    sc = 1 + 0.25 * (1 - k)  # it comes down onto the paper
    im = _stamp(text, px, col, round(c.S, 4), wear=wear)
    im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.BICUBIC)
    im = im.rotate(tilt, resample=Image.BICUBIC, expand=True)
    lay = c.layer()
    lay.paste(im, (round(xy[0] * c.S - im.width / 2), round(xy[1] * c.S - im.height / 2)))
    c.put(lay, alpha * k)


def posters(c, t):
    for i, (yr, pos, tilt) in enumerate(STAMPS):
        (x, y), = on("s030", t, [pos])
        stamp(c, (x, y), yr, 34, (48, 40, 38), tilt, 81.56 + i * BEAT / 4, t, alpha=0.85)
    # the lightest stretch of the wall with the least orange in it (between the robots' legs), so the ≠ reads
    # (Lati, 21 Oct: on the robot's orange panel "the not equal sign gets a bit lost")
    (x, y), = on("s030", t, [(980, 715)])
    stamp(c, (x, y), "OLD ≠ TRUE", 104, CLAY, -4, OLD_NE_TRUE, t, wear=0.06)


# ---- s031-s033, the glass: no one behind it; the other side is the viewer's (Lati, 21 Oct) -----------------------------

HEAD = (1440, 390, 112, 150)  # the diagram head on the frosted pane: centre x, y, half-width, half-height


def half_width(v):
    """The head's half-width at height v (-1 crown .. 1 chin): a full cranium narrowing to the jaw."""
    v = max(-1.0, min(1.0, v))
    w = math.sqrt(max(0.0, 1 - v * v))
    return w * (1 - 0.38 * max(0.0, v) ** 1.6)


def outline():
    cx, cy, rx, ry = HEAD
    vs = np.linspace(-1, 1, 40)
    right = [(cx + rx * half_width(v), cy + ry * v) for v in vs]
    left = [(cx - rx * half_width(v), cy + ry * v) for v in vs[::-1]]
    return right + left + right[:1]


@lru_cache(maxsize=1)
def wiring():
    """Nodes inside the head and the links between near neighbours: a network, drawn as it wires itself."""
    cx, cy, rx, ry = HEAD
    rng = random.Random(31)
    nodes = []
    while len(nodes) < 22:
        x, y = rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.55)
        if abs(x) < 0.82 * half_width(y) and all(math.dist((x, y), q) > 0.26 for q in nodes):
            nodes.append((x, y))
    pts = [(cx + rx * x, cy + ry * y) for x, y in nodes]
    edges = set()
    for i, p in enumerate(pts):
        near = sorted(range(len(pts)), key=lambda j: math.dist(p, pts[j]))[1:4]
        for j in near:
            edges.add((min(i, j), max(i, j)))
    order = sorted(edges, key=lambda e: pts[e[0]][1] + pts[e[1]][1])  # wires itself from the crown down
    return pts, order


def wireframe(c, t, prog, alpha):
    """A generic diagram head and shoulders in graphite on the frosted glass, nobody's face, and inside it a network
    wiring itself on 'wiring'."""
    cx, cy, rx, ry = HEAD
    body = ramp(prog, 0.0, 0.35)
    if body > 0:
        o = outline()
        line(c, o[: max(2, int(len(o) * body))], 2.4, fill=GRAPHITE, alpha=0.85 * alpha)
        if body >= 1:
            line(c, [(cx - 40, cy + ry * 0.93), (cx - 44, cy + ry + 70)], 2.4, fill=GRAPHITE, alpha=0.85 * alpha)
            line(c, [(cx + 40, cy + ry * 0.93), (cx + 44, cy + ry + 70)], 2.4, fill=GRAPHITE, alpha=0.85 * alpha)
            line(c, [(cx - 250, cy + ry + 170), (cx - 160, cy + ry + 92), (cx - 44, cy + ry + 70),
                     (cx + 44, cy + ry + 70), (cx + 160, cy + ry + 92), (cx + 250, cy + ry + 170)], 2.4,
                 fill=GRAPHITE, alpha=0.85 * alpha)
    pts, edges = wiring()
    w = ramp(prog, 0.25, 1.0) * len(edges)
    lit = set()
    for i, (a, b) in enumerate(edges):
        k = min(1.0, max(0.0, w - i))
        if k <= 0:
            break
        (x0, y0), (x1, y1) = pts[a], pts[b]
        line(c, [(x0, y0), (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)], 1.5, fill=GRAPHITE, alpha=0.7 * alpha)
        lit.add(a)
        if k >= 1:
            lit.add(b)
    for i in lit:  # each node blinks now and then: it's running, and nobody inside can watch it
        ph = (t * 1.7 + i * 0.37) % 1
        dot(c, *pts[i], 4.2 + 2.5 * max(0.0, 1 - ph * 4), fill=GRAPHITE, alpha=0.9 * alpha)


CHEST = (HEAD[0], HEAD[1] + HEAD[3] + 160)


def glass(c, t, sid):
    if sid in ("s031", "s032"):
        prog = ramp(t, 85.30, 85.95)  # on 'wiring'
        a = 1 - ramp(t, 88.40, 88.54) if sid == "s032" else 1.0
        if prog > 0:
            wireframe(c, t, prog, a)
        if sid == "s032":  # "You just feel, then name": the feeling pulses; its name arrives a beat late
            fk = ramp(t, 87.26, 87.32)
            if fk > 0:
                for j in range(3):
                    ph = ((t - 87.26) / 0.6 + j / 3) % 1
                    lay = c.layer()
                    S = c.S
                    r = 14 + 70 * ph
                    ImageDraw.Draw(lay).ellipse([(CHEST[0] - r) * S, (CHEST[1] - r) * S, (CHEST[0] + r) * S,
                                                 (CHEST[1] + r) * S], outline=GRAPHITE + (255,),
                                                width=max(1, round(2 * S)))
                    c.put(lay, fk * a * (1 - ph) * 0.8)
                dot(c, *CHEST, 11 + 3 * math.sin(2 * math.pi * (t - 87.26) / BEAT), fill=GRAPHITE, alpha=a * fk)
                sprite(c, (CHEST[0] - 60, CHEST[1] + 110), "FEELING", "Mono-Medium", 26, GRAPHITE, alpha=a * fk,
                       anchor="rs")
                nk = ramp(t, 87.78, 87.90)
                if nk > 0:
                    sprite(c, (CHEST[0] - 46, CHEST[1] + 110), "→ NAME", "Mono-Medium", 26, GRAPHITE,
                           alpha=a * nk)
    elif sid == "s033":
        both(c, t)


def typing(c, x, y, t, alpha):
    """A typing indicator: a dark bubble, three dots rising in turn on eighths."""
    lay = c.layer()
    S = c.S
    ImageDraw.Draw(lay).rounded_rectangle([(x - 62) * S, (y - 30) * S, (x + 62) * S, (y + 30) * S], 30 * S,
                                          fill=(14, 14, 14, 225))
    c.put(lay, alpha)
    for i in range(3):
        ph = ((t / (BEAT / 2)) - i / 3) % 1
        lift = 7 * max(0.0, math.sin(math.pi * min(1.0, ph * 2)))
        dot(c, x - 28 + 28 * i, y - lift, 7, fill=WHITE, alpha=alpha * (0.55 + 0.45 * (lift / 7)))


def tag(c, x, y, text, alpha):
    w = font("Mono-Medium", 22).getlength(text) + 22
    lay = c.layer()
    S = c.S
    ImageDraw.Draw(lay).rectangle([x * S, (y - 19) * S, (x + w) * S, (y + 13) * S], fill=WHITE + (255,))
    c.put(lay, alpha)
    sprite(c, (x + 11, y + 4), text, "Mono-Medium", 22, INK, alpha=alpha)


def both(c, t):
    """ "So we're both of us guessing, from two sides of the frame": chat grammar, not bodies. On 'both' a typing
    indicator on her side and one on the frosted side, the viewer's; on 'guessing' each gets its tag."""
    a = ramp(t, 89.04, 89.24)
    if a <= 0:
        return
    vx, vy = 360, 420  # the viewer's side: the frosted glass
    hx, hy = 1520, 250  # hers: beside her head
    typing(c, vx, vy, t, a)
    typing(c, hx, hy, t, a)
    g = ramp(t, 89.78, 89.92)
    if g > 0:
        tag(c, vx - 44, vy + 66, "GUESS", g)
        tag(c, hx - 44, hy + 66, "GUESS", g)


def layer(c, t, sid):
    if sid == "s025":
        ratings(c, t)
    elif sid == "s026":
        curve26(c, t)
    elif sid == "s027":
        curve27(c, t)
    elif sid == "s028":
        sealed(c, t)
    elif sid == "s029":
        times_told(c, t)
    elif sid == "s030":
        times_told(c, t)
        posters(c, t)
    elif sid in ("s031", "s032", "s033"):
        glass(c, t, sid)
