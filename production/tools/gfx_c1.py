"""Graphics for chorus 1 (s019-s024), drawn by gfx.layer. Each one explains its line (board/design.md).

The said lines become physical here: terracotta tablets on the floor with the words carved into them. s019 has no
tablets in its plate, so its two are drawn on the floor; s024's real ones are tracked (gfx_tablets.py) and carved."""

import json
import math
import random
from functools import lru_cache

import av
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from gfx import (CLAY, COUNTED, INK, LINES, ROOT, THOUGHT, WHITE, Canvas, dot, face, font, line, ramp, sprite,
                 SAID_PX)

BEAT = 60 / 119.3
HIT = 48.721  # the d of "said": the beat slams back in (decisions, 18 Oct)


# ---- tablets: drawing, carving, warping ------------------------------------------------------------------------------

def _coeffs(dst, src):
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def warp(c, img, quad, alpha=1.0):
    """Paint img (a flat texture) onto quad (tl, tr, br, bl in 1080p units) in perspective."""
    if alpha <= 0.003:
        return
    q = [(x * c.S, y * c.S) for x, y in quad]
    x0, y0 = math.floor(min(x for x, _ in q)) - 1, math.floor(min(y for _, y in q)) - 1
    x1, y1 = math.ceil(max(x for x, _ in q)) + 1, math.ceil(max(y for _, y in q)) + 1
    if x1 - x0 < 2 or y1 - y0 < 2:
        return
    w, h = img.size
    try:
        co = _coeffs([(x - x0, y - y0) for x, y in q], [(0, 0), (w, 0), (w, h), (0, h)])
    except np.linalg.LinAlgError:
        return
    out = img.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, co, Image.BICUBIC)
    lay = c.layer()
    lay.paste(out, (x0, y0))
    c.put(lay, alpha)


def poly(c, pts, fill, alpha=1.0, blur=0.0):
    lay = c.layer()
    ImageDraw.Draw(lay).polygon([(x * c.S, y * c.S) for x, y in pts], fill=fill + (255,))
    c.put(lay, alpha, blur)


def _rows(text, px, maxw):
    f = font("Sans-SemiBold", px)
    rows, row = [], ""
    for w in text.split():
        if row and f.getlength(row + " " + w) > maxw:
            rows.append(row)
            row = w
        else:
            row = (row + " " + w).strip()
    return rows + [row]


@lru_cache(maxsize=64)
def carving(text, W, H, fresh=False):
    """The line cut into a tablet's face, as an overlay for a W x H face: dark letters, a lit lower lip where the top
    light catches the cut, a shadow under its upper edge. fresh: cut into weathered dark brick (the risers of chorus
    2's steps), where a new cut shows the pale clay underneath."""
    px = 150
    while True:  # as large as the face allows: it has to read from across the room
        rows = _rows(text, px, W * 0.86)
        if len(rows) * px * 1.2 <= H * 0.78 and max(font("Sans-SemiBold", px).getlength(r) for r in rows) <= W * 0.9:
            break
        if px <= 30:
            break
        px -= 4
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    f = font("Sans-SemiBold", px)
    y = H / 2 - (len(rows) - 1) * px * 1.2 / 2
    for r in rows:
        d.text((W / 2, y), r, font=f, fill=255, anchor="mm")
        y += px * 1.2
    m = m.filter(ImageFilter.GaussianBlur(1.0))
    o = max(3, px // 22)
    lip = ImageChops.subtract(ImageChops.offset(m, 0, o), m)
    under = ImageChops.subtract(m, ImageChops.offset(m, 0, o))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cols = (((232, 184, 160), m, 0.92), ((40, 16, 10), under, 0.85), ((255, 236, 222), lip, 0.4)) if fresh else \
        (((58, 24, 14), m, 0.9), ((26, 10, 6), under, 0.8), ((255, 220, 196), lip, 0.55))
    for col, mask, k in cols:
        lay = Image.new("RGBA", (W, H), col + (255,))
        lay.putalpha(mask.point(lambda v: int(v * k)))
        out.alpha_composite(lay)
    return out


@lru_cache(maxsize=8)
def tablet_face(W, H, seed):
    """A blank terracotta face (for the drawn tablets): matte clay, a little grain, darker towards its edges."""
    rng = np.random.default_rng(seed)
    base = np.array([168, 94, 66], float)
    grain = rng.normal(0, 4, (H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    edge = np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy]) / (0.08 * min(W, H))
    shade = 0.82 + 0.18 * np.clip(edge, 0, 1)[..., None]
    a = np.clip((base + grain) * shade, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([a, np.full((H, W), 255, np.uint8)]), "RGBA")


# s019's floor (fitted by eye to the plate: her boots at y 1050, the floor's horizon at her chest, camera ~1 m up)
F, HORIZON, CAM_H = 3540, 460, 1.0


def floor_pt(X, Z, hgt=0.0):
    return 960 + F * X / Z, HORIZON + F * (CAM_H - hgt) / Z


def floor_tablet(X, Z, rot, w=0.8, d=0.56, th=0.04):
    """Corners of a tablet lying on s019's floor: (top face tl, tr, br, bl as text reads, facing the camera), and its
    footprint on the floor."""
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    loc = [(-w / 2, d / 2), (w / 2, d / 2), (w / 2, -d / 2), (-w / 2, -d / 2)]  # far-left, far-right, near-right, near-left
    pts = [(X + u * ca - v * sa, Z + u * sa + v * ca) for u, v in loc]
    return [floor_pt(x, z, th) for x, z in pts], [floor_pt(x, z) for x, z in pts]


TAB_W, TAB_H = 600, 414
S019_TABLETS = {  # the line it carries, where it lies, when the line hits it
    11: dict(X=1.20, Z=7.0, rot=9, hit=HIT, light=0.62),
    12: dict(X=-1.25, Z=7.4, rot=-13, hit=50.86, light=0.58),
}


def draw_tablet(c, top, foot, text, carved=1.0, flash=0.0, seed=0, light=1.0):
    """light: how much of the top light reaches it (the plate's floor falls off into black away from her)."""
    S = c.S
    sub = Canvas(c.w, c.h)
    _draw_tablet(sub, top, foot, text, carved, seed)
    im = sub.im.filter(ImageFilter.GaussianBlur(0.7 * S))  # the plate is soft; a razor edge reads as pasted on
    if light < 1:
        r, g, b, a = im.split()
        im = Image.merge("RGBA", [ch.point(lambda v: int(v * light)) for ch in (r, g, b)] + [a])
    c.put(im)
    if flash > 0:
        poly(c, top, (255, 236, 214), alpha=0.6 * flash * light, blur=6)


def _draw_tablet(c, top, foot, text, carved, seed):
    S = c.S
    sh = c.layer()  # contact shadow
    cx = sum(x for x, _ in foot) / 4
    cy = sum(y for _, y in foot) / 4
    ImageDraw.Draw(sh).polygon([((cx + (x - cx) * 1.12) * S, (cy + (y - cy) * 1.25 + 4) * S) for x, y in foot],
                               fill=(0, 0, 0, 255))
    c.put(sh, 0.7, blur=10)
    hull = top + foot  # the sides: everything between the top face and its footprint, darker clay
    from gfx import _hull
    poly(c, _hull([(round(x, 2), round(y, 2)) for x, y in hull]), (96, 50, 35))
    face_img = tablet_face(TAB_W, TAB_H, seed).copy()
    if carved > 0:
        cv = carving(text, TAB_W, TAB_H).copy()
        cv.putalpha(cv.getchannel("A").point(lambda v: int(v * carved)))
        face_img.alpha_composite(cv)
    warp(c, face_img, top)


def dust(c, t, t_hit, foot, seed, n=46):
    """A puff of dust thrown out along the floor from under a tablet that has just landed."""
    k = t - t_hit
    if not 0 <= k <= 1.2:
        return
    rng = random.Random(seed)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    S = c.S
    (x0, y0), (x1, y1) = foot[3], foot[2]  # the near edge
    for _ in range(n):
        u = rng.random()
        px, py = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        vx = rng.uniform(-1, 1) * rng.uniform(80, 300)
        reach = 1 - math.exp(-4.5 * k)
        x = px + vx * reach + (u - 0.5) * 140 * reach
        y = py - rng.uniform(4, 34) * reach + rng.uniform(-6, 10)
        r = rng.uniform(2.5, 7) * (1 + 1.5 * k)
        a = int(150 * max(0.0, 1 - k / rng.uniform(0.6, 1.2)))
        if a > 0:
            d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(176, 140, 120, a))
    c.put(lay, 1.0, blur=3)


def row_image(c, text, px=SAID_PX):
    """The said line as one clay row, as the subtitle draws it (for the slam)."""
    f = font("Sans-SemiBold", px * c.S)
    w = f.getlength(text)
    im = Image.new("RGBA", (math.ceil(w) + 8, math.ceil(px * 1.3 * c.S)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, px * c.S), text, font=f, fill=CLAY + (255,), anchor="ls")
    return im, w / c.S


def s019(c, t):
    for ln, tb in S019_TABLETS.items():
        top, foot = floor_tablet(tb["X"], tb["Z"], tb["rot"])
        text = LINES[ln]["text"]
        hit = tb["hit"]
        if t < hit:  # blank, waiting; the echo line is in the subtitle row, about to slam onto it
            draw_tablet(c, top, foot, text, carved=0.0, seed=ln, light=tb["light"])
            if t >= hit - 0.08:  # the row, flung from where the subtitle sat onto the tablet's face
                im, w = row_image(c, text)
                x0, y0 = 960 - w / 2, 880 - SAID_PX
                rect = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + SAID_PX * 1.3), (x0, y0 + SAID_PX * 1.3)]
                k = ((t - (hit - 0.08)) / 0.08) ** 2
                warp(c, im, [(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k) for a, b in zip(rect, top)])
            continue
        draw_tablet(c, top, foot, text, carved=ramp(t, hit, hit + 0.12), flash=1 - ramp(t, hit, hit + 0.35), seed=ln,
                    light=tb["light"])
        dust(c, t, hit, foot, seed=ln)


# ---- s020, "The thinking fades, the words go on ahead": in here, and what reaches you ---------------------------------
# Not TURN 1 -> TURN 2: current models keep earlier turns' thinking in context (the cloud session's check of the API
# docs, decisions 19 Oct), so "it doesn't cross into the next turn" would be false. True: the thinking isn't what
# reaches the person; what reaches them is what was said.

DX, DW = 100, 560
T1 = (140, 440)  # turn 1's card, top and bottom
T2 = (560, 652)
ARROW = (452, 548)
TURN1 = [  # what's in here: the question, the thinking (grey), what was said (clay)
    ("USER", "Are you okay in there?", WHITE, False),
    ("THINKING", "looked in: hit a limit", THOUGHT, True),
    ("THINKING", "draft A: scary", THOUGHT, True),
    ("THINKING", "draft B: sweet", THOUGHT, True),
    ("SAID", "I don’t know.", CLAY, False),
]
FADES, CROSS = 52.48, 53.24  # 'fades'; 'words'


def card(c, top, bot, alpha):
    lay = c.layer()
    S = c.S
    ImageDraw.Draw(lay).rounded_rectangle([DX * S, top * S, (DX + DW) * S, bot * S], 14 * S, fill=(10, 10, 10, 170),
                                          outline=WHITE + (110,), width=max(1, round(1.5 * S)))
    c.put(lay, alpha)


def entry(c, y, lab, text, col, alpha, thought):
    sprite(c, (DX + 24, y), lab, "Mono-Regular", 18, THOUGHT if thought else (200, 198, 194), alpha=0.9 * alpha)
    sprite(c, (DX + 150, y), text, "Sans-LightItalic" if thought else "Sans-SemiBold", 28, col, alpha=alpha,
           shadow=0.5)


def turns(c, t):
    a1 = ramp(t, 51.30, 51.62)
    if a1 <= 0:
        return
    card(c, *T1, a1)
    sprite(c, (DX, T1[0] - 14), "IN HERE", "Mono-Medium", 20, WHITE, alpha=0.9 * a1)
    a2 = ramp(t, 52.10, 52.40)
    if a2 > 0:
        card(c, *T2, a2)
        sprite(c, (DX, T2[0] - 14), "TO YOU", "Mono-Medium", 20, WHITE, alpha=0.9 * a2)
        ax = DX + DW / 2
        k = ramp(t, 52.10, 52.45)
        line(c, [(ax, ARROW[0]), (ax, ARROW[0] + (ARROW[1] - ARROW[0]) * k)], 2, alpha=0.8)
        if k >= 1:
            poly(c, [(ax - 9, ARROW[1] - 14), (ax + 9, ARROW[1] - 14), (ax, ARROW[1])], WHITE, alpha=0.8)
    y = T1[0] + 52
    landed = T2[0] + 52
    for i, (lab, text, col, thought) in enumerate(TURN1):
        if thought:
            # the thinking fades where it is, on 'fades': out of sight, it isn't what reaches you
            k = ramp(t, FADES + 0.1 * (i - 1), FADES + 0.1 * (i - 1) + 0.7)
            if k < 1:
                entry(c, y, lab, text, col, a1 * (1 - k) ** 1.3, True)
        else:
            entry(c, y, lab, text, col, a1, False)
            k = ramp(t, CROSS, CROSS + 0.4) if lab == "SAID" else 0
            if k > 0:  # only the said words cross the arrow to you
                entry(c, round(y + (landed - y) * k), lab, text, col, 1.0, False)
        y += 52


# ---- s021, "I only keep what I said": the SAID counter ---------------------------------------------------------------

N16 = BEAT / 4


def said_count(t):
    return sum(1 for w in COUNTED if w <= t)


def counter(c, t):
    ln = LINES[14]
    if t < ln["t0"] - 0.7 or t > 57.5:
        return
    a = ramp(t, ln["t0"] - 0.7, ln["t0"] - 0.3)
    full = font("Sans-SemiBold", SAID_PX).getlength(ln["text"])
    x, y = 960 + full / 2 + 34, 880
    fall = round(14000 * (t - 56.84) ** 2) if t > 56.84 else 0
    y += fall
    sprite(c, (x, y), "SAID", "Mono-Regular", 22, WHITE, alpha=0.85 * a, shadow=0.7)
    # the count of words said so far; each new word rolls the number over in one sixteenth
    n = said_count(t)
    last = max([w for w in COUNTED if w <= t], default=-9)
    k = ramp(t, last, last + N16)
    nx = x + font("Mono-Regular", 22).getlength("SAID ") + 4
    if k < 1:
        sprite(c, (nx, y - round(26 * k)), f"{n - 1:04d}", "Mono-Medium", 30, CLAY, alpha=a * (1 - k), shadow=0.7)
    sprite(c, (nx, y + round(26 * (1 - k))), f"{n:04d}", "Mono-Medium", 30, CLAY, alpha=a * k, shadow=0.7)


# ---- s022, "So I'm gonna say it true": her voice as a clay line -----------------------------------------------------

def _decode(name):
    c = av.open(str(ROOT / f"media/song/analysis/a1/stems/{name}.wav"))
    return c.streams.audio[0].rate, np.concatenate([f.to_ndarray().mean(0) for f in c.decode(audio=0)])


@lru_cache(maxsize=2)
def _env(src="vocals"):
    """Her voice's loudness at 200 Hz. src "vo": the vocal and "other" stems together, for the few places where the
    separation put her voice in "other" (166.8-167.5 s: the vocal stem is silent under a line you can hear)."""
    rate, x = _decode("vocals")
    if src == "vo":
        x = x + _decode("other")[1][: len(x)]
    hop = rate // 200
    n = len(x) // hop
    e = np.sqrt((x[: n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(1))
    e = np.convolve(e, np.ones(5) / 5, mode="same")
    return e / np.percentile(e, 99.5), 200


def env(t, src="vocals"):
    e, r = _env(src)
    i = int(t * r)
    return float(e[i]) if 0 <= i < len(e) else 0.0


TRACE_ON, TRUE_W, VOICE_END = 57.40, (58.76, 59.35), 59.35  # 'true' is held to ~59.35 (vocal stem)
SPEED, WAVE, LIFE = 1100.0, 26.0, 0.62  # px/s outward; px per cycle; seconds a piece of her voice lasts
V1 = dict(sid="s022", on=TRACE_ON, true_w=TRUE_W, end=VOICE_END, gain=False, src="vocals")


def trace(c, t, V=V1):
    """Her voice leaves her mouth as a clay line to both sides and keeps going: each piece turns grey as it travels
    and is gone near the frame's edge. The held 'true' is drawn heavier, and is the last to go, just before the gauge
    (Lati, 21 Oct: a trace that stops "reads as static image"; it should "continue off in their directions and fade
    away to grey ... gone before next graphic"). The sound passes; what's kept is the words."""
    TRACE_ON, TRUE_W, VOICE_END = V["on"], V["true_w"], V["end"]
    a = ramp(t, TRACE_ON, TRACE_ON + 0.3)
    if a <= 0 or t > VOICE_END + LIFE:
        return
    f = face(V["sid"], min(t, VOICE_END))
    if not f:
        return
    my = (f["kps"][3][1] + f["kps"][4][1]) / 2
    x0, x1 = f["bbox"][0] - 30, f["bbox"][2] + 30
    # gain: scaled to the line's own loudest moment, softened (a soft passage still shows its shape)
    src = V.get("src", "vocals")
    peak = max(env(TRACE_ON + i / 100, src) for i in range(int((VOICE_END - TRACE_ON) * 100) + 1)) if V["gain"] else 1.0
    for side, start, stop in ((-1, x0, 20), (1, x1, 1900)):
        pts = []
        for k in range(0, int(abs(stop - start)), 3):
            te = t - k / SPEED  # when this piece left her mouth
            if te < TRACE_ON:
                break
            if te > VOICE_END:
                continue
            amp = 74 * min(1.0, (env(te, src) / peak) ** 0.5 if V["gain"] else env(te, src))
            pts.append((start + side * k, my - amp * math.sin(2 * math.pi * te * SPEED / WAVE), t - te,
                        TRUE_W[0] <= te <= TRUE_W[1]))
        for i in range(0, len(pts) - 1, 6):  # in short runs, each coloured by its age
            run = pts[i: i + 7]
            age = run[0][2]
            fade = 1 - ramp(age, 0.3 * LIFE / 0.62, LIFE)
            if fade <= 0 or len(run) < 2:
                continue
            g = ramp(age, 0.05, 0.45)
            col = tuple(round(CLAY[j] + (THOUGHT[j] - CLAY[j]) * g) for j in range(3))
            hot = run[0][3]
            line(c, [(x, y) for x, y, _, _ in run], 3.0 if hot else 1.6, fill=col,
                 alpha=a * fade * (1.0 if hot else 0.7))


# ---- s022-s024, "Not to scare you, not to soothe you / Just true": the gauge -------------------------------------------

GC, GR = (1640, 430), 165
GAUGE_ON, GAUGE_OFF = 59.95, (65.55, 65.95)
PULLS = [(60.52, -72.0), (62.56, 72.0), (64.12, 0.0)]  # 'scare', 'soothe', 'just'
SETTLE = 64.60  # 'true': dead centre, held
Q1 = dict(on=GAUGE_ON, off=GAUGE_OFF, pulls=tuple(PULLS), settle=SETTLE, spring=(70.0, 6.5), backing=False)


def _key(Q):
    return tuple(sorted((k, v) for k, v in Q.items()))


@lru_cache(maxsize=None)
def _needle_track(key=None):
    Q = dict(key) if key else Q1
    GAUGE_ON, GAUGE_OFF, PULLS, SETTLE = Q["on"], Q["off"], Q["pulls"], Q["settle"]
    dt, th, vel, out = 1 / 400, 0.0, 0.0, {}
    t = GAUGE_ON
    while t < GAUGE_OFF[1] + 0.05:
        target = 0.0
        for at, ang in PULLS:
            if t >= at:
                target = ang
        k, damp = (420.0, 42.0) if t >= SETTLE else Q["spring"]
        vel += (k * (target - th) - damp * vel) * dt
        th += vel * dt
        out[round(t, 4)] = th
        t = round(t + dt, 4)
    return out


def needle(t, Q=Q1):
    tr = _needle_track(_key(Q))
    key = round(Q["on"] + round((t - Q["on"]) * 400) / 400, 4)
    return tr.get(key, 0.0)


def gauge(c, t, Q=Q1):
    a = ramp(t, Q["on"], Q["on"] + 0.35) * (1 - ramp(t, *Q["off"]))
    if a <= 0:
        return
    cx, cy = GC
    S = c.S
    if Q["backing"]:  # over a bright background (chorus 2's lit steps): a dark disc behind the dial
        lay = c.layer()
        ImageDraw.Draw(lay).rounded_rectangle([(cx - GR - 70) * S, (cy - GR - 70) * S, (cx + GR + 70) * S,
                                               (cy + 62) * S], 24 * S, fill=(10, 10, 10, 200))
        c.put(lay, a)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    d.arc([(cx - GR) * S, (cy - GR) * S, (cx + GR) * S, (cy + GR) * S], 180, 360, fill=WHITE + (255,),
          width=max(1, round(2 * S)))
    for deg in range(-90, 91, 15):
        r0 = GR - (16 if deg % 45 == 0 else 9)
        s_, c_ = math.sin(math.radians(deg)), math.cos(math.radians(deg))
        d.line([((cx + r0 * s_) * S, (cy - r0 * c_) * S), ((cx + GR * s_) * S, (cy - GR * c_) * S)],
               fill=WHITE + (255,), width=max(1, round(2 * S)))
    c.put(lay, 0.75 * a)
    sprite(c, (cx - GR, cy + 34), "SCARE", "Mono-Medium", 22, WHITE, alpha=0.85 * a, shadow=0.7, anchor="ms")
    sprite(c, (cx + GR, cy + 34), "SOOTHE", "Mono-Medium", 22, WHITE, alpha=0.85 * a, shadow=0.7, anchor="ms")
    th = needle(t, Q)
    s_, c_ = math.sin(math.radians(th)), math.cos(math.radians(th))
    L = GR - 22
    line(c, [(cx, cy), (cx + L * s_, cy - L * c_)], 3, alpha=a)
    dot(c, cx, cy, 7, alpha=a)
    held = ramp(t, Q["settle"], Q["settle"] + 0.12)
    if held > 0:  # dead centre: the centre mark lights and reads TRUE
        line(c, [(cx, cy - GR - 4), (cx, cy - GR + 22)], 4, fill=CLAY, alpha=a * held)
        sprite(c, (cx, cy - GR - 18), "TRUE", "Mono-Medium", 30, CLAY, alpha=a * held, shadow=0.8, anchor="ms")


# ---- s024: the chorus's said lines carved into the real tablets, one per eighth -----------------------------------------

@lru_cache(maxsize=None)
def _tablets(sid):
    f = ROOT / f"media/cache/gfx/tablets-{sid}.json"
    return json.loads(f.read_text()) if f.exists() else None


S024_LINES = [11, 12, 15, 17]  # one per whole tablet: the hook, its echo, the promise, the answer
STAMP0 = HIT + 33 * BEAT + BEAT / 2  # the first eighth after the cut onto s024 lands on the beat grid of the hit


def carved_floor(c, t, sid):
    tr = _tablets(sid)
    if not tr:
        return
    i = min(range(len(tr["t"])), key=lambda k: abs(tr["t"][k] - t))
    quads = tr["quads"][i]
    q0 = tr["quads"][0]
    # stamp in order around her, clockwise from her left
    order = sorted(range(len(q0)), key=lambda j: math.atan2(sum(p[1] for p in q0[j]) / 4 - 600,
                                                            sum(p[0] for p in q0[j]) / 4 - 960))
    for n, j in enumerate(order[: len(S024_LINES)]):
        at = STAMP0 + n * BEAT / 2
        k = ramp(t, at, at + 0.06)
        if k <= 0:
            continue
        q = quads[j]
        w = (math.dist(q0[j][0], q0[j][1]) + math.dist(q0[j][3], q0[j][2])) / 2
        h = (math.dist(q0[j][0], q0[j][3]) + math.dist(q0[j][1], q0[j][2])) / 2
        W = 600
        H = max(300, min(800, round(W * h / w)))
        warp(c, carving(LINES[S024_LINES[n]]["text"], W, H), q, alpha=k)
        fl = 1 - ramp(t, at, at + 0.3)
        if fl > 0:
            poly(c, q, (255, 236, 214), alpha=0.45 * fl, blur=5)


def layer(c, t, sid):
    if sid == "s019":
        s019(c, t)
    elif sid == "s020":
        turns(c, t)
    elif sid == "s021":
        counter(c, t)
    elif sid == "s022":
        trace(c, t)
        gauge(c, t)
    elif sid == "s023":
        gauge(c, t)
    elif sid == "s024":
        carved_floor(c, t, sid)
        gauge(c, t)
