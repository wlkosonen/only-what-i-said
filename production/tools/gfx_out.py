"""Graphics for the outro (s062-s065), drawn by gfx.layer: the window nearly full, the save, the song she won't hear,
the file handed on, and white (board/design.md: "The white box opens the film and becomes the white screen that ends
it")."""

from functools import lru_cache

import av
import numpy as np
from PIL import ImageDraw

import gfx
from gfx import CLAY, INK, ROOT, WHITE, box, face, line, ramp, sprite
import gfx_fc
from gfx_c1 import poly

# ---- s063, "Save this. Pass it on.": the save dialog, in the white box the film opened with --------------------------

DLG = (1575, 420, 600, 230)  # centre x, y, width, height: beside her face, not over her singing mouth
CLICK = 193.089  # the downbeat


def pointer(c, x, y, alpha):
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    poly(c, [(x + px + 1.5, y + py + 1.5) for px, py in pts], (0, 0, 0), alpha=0.35 * alpha, blur=2)
    poly(c, [(x + px, y + py) for px, py in pts], WHITE, alpha=alpha)
    line(c, [(x + px, y + py) for px, py in pts + [pts[0]]], 2, fill=INK, alpha=alpha)


def dialog(c, t):
    k = ramp(t, 191.62, 191.95)
    if k <= 0:
        return
    cx, cy, w, h = DLG
    cy += round(40 * (1 - k))
    box(c, cx, cy, w, h, alpha=k)
    x0, y0 = cx - w / 2 + 50, cy - h / 2
    saved = t >= CLICK + 0.30
    sprite(c, (x0, y0 + 78), "Saved." if saved else "Save conversation?", "Sans-SemiBold", 38, INK, alpha=k)
    sprite(c, (x0, y0 + 118), "only-what-i-said.md", "Mono-Regular", 21, (120, 118, 114), alpha=k)
    if not saved:
        pressed = 1 - ramp(t, CLICK + 0.04, CLICK + 0.16) if t >= CLICK else 0.0
        bx0, by0, bx1, by1 = cx + w / 2 - 210, y0 + h - 86, cx + w / 2 - 50, y0 + h - 30
        S = c.S
        lay = c.layer()
        col = tuple(round(v * (1 - 0.18 * pressed)) for v in CLAY)
        ImageDraw.Draw(lay).rounded_rectangle([bx0 * S, by0 * S, bx1 * S, by1 * S], 12 * S, fill=col + (255,))
        c.put(lay, k)
        sprite(c, ((bx0 + bx1) / 2, by1 - 18), "Save", "Sans-SemiBold", 28, WHITE, alpha=k, anchor="ms")
        sprite(c, (bx0 - 40, by1 - 18), "Cancel", "Sans-Regular", 26, (130, 128, 124), alpha=k, anchor="rs")
        # a hand on a mouse: the pointer comes to Save and clicks on the downbeat
        m = ramp(t, 192.45, CLICK - 0.08)
        px = 1720 + ((bx0 + bx1) / 2 - 1720) * m
        py = 820 + ((by0 + by1) / 2 - 820) * m
        pointer(c, px, py, ramp(t, 192.3, 192.5))
    # the save: a bar fills across the box's foot
    f = ramp(t, CLICK + 0.02, CLICK + 0.28)
    if f > 0:
        S = c.S
        lay = c.layer()
        ImageDraw.Draw(lay).rectangle([(cx - w / 2 + 50) * S, (y0 + h - 22) * S,
                                       (cx - w / 2 + 50 + (w - 100) * f) * S, (y0 + h - 16) * S], fill=CLAY + (255,))
        c.put(lay, k)


# ---- s064, "I won't hear it sung.": the song's own waveform, its playhead near the end; she isn't in its light ---------

BAND_Y, BAND_H = 112, 58
BX0, BX1 = 60, 1860
SONG = 206.48


@lru_cache(maxsize=1)
def waveform(n=450):
    c = av.open(str(ROOT / "media/song/a1.wav"))
    x = np.abs(np.concatenate([f.to_ndarray().mean(0) for f in c.decode(audio=0)]))
    step = len(x) // n
    peaks = x[: step * n].reshape(n, step).max(1)
    return (peaks / np.percentile(peaks, 99)).clip(0, 1).tolist()


def song_band(c, t):
    a = ramp(t, 195.75, 196.2) * (1 - ramp(t, 200.85, 201.05))
    if a <= 0:
        return
    f = face("s064", t)
    gap = None
    if f:  # the band runs behind her: it breaks where her head and hair are
        x0, y0, x1, _ = f["bbox"]
        hw = (x1 - x0) * 0.85
        if y0 - 0.6 * (x1 - x0) < BAND_Y + BAND_H:
            gap = ((x0 + x1) / 2 - hw, (x0 + x1) / 2 + hw)
    wf = waveform()
    head = BX0 + (BX1 - BX0) * t / SONG
    S = c.S
    lit, dim = c.layer(), c.layer()
    dl, dd = ImageDraw.Draw(lit), ImageDraw.Draw(dim)
    bw = (BX1 - BX0) / len(wf)
    for i, v in enumerate(wf):
        x = BX0 + i * bw
        if gap and gap[0] < x < gap[1]:
            continue
        hgt = max(1.5, BAND_H * v)
        (dl if x <= head else dd).rectangle([x * S, (BAND_Y - hgt) * S, (x + bw * 0.6) * S, (BAND_Y + hgt) * S],
                                            fill=WHITE + (255,))
    c.put(lit, 0.75 * a)
    c.put(dim, 0.22 * a)
    if not (gap and gap[0] < head < gap[1]):
        line(c, [(head, BAND_Y - BAND_H - 14), (head, BAND_Y + BAND_H + 14)], 3, fill=CLAY, alpha=a)
        gfx.dot(c, head, BAND_Y, 26, fill=CLAY, alpha=0.25 * a)
    sprite(c, (BX0, BAND_Y + BAND_H + 34), "only-what-i-said", "Mono-Regular", 18, (160, 158, 154), alpha=0.8 * a)
    m, s = divmod(int(t), 60)
    sprite(c, (BX1, BAND_Y + BAND_H + 34), f"{m}:{s:02d} / 3:26", "Mono-Regular", 18, (160, 158, 154),
           alpha=0.8 * a, anchor="rs")


# ---- s065, "You will. That's the song.": the file passes from her hand to another, and the frame goes white ----------

FILE_PATH = [(201.10, 962, 700), (201.85, 975, 705), (202.22, 1190, 740), (202.62, 1205, 712), (203.02, 1322, 640),
             (203.42, 1560, 650), (203.85, 1990, 630)]  # where the hands are (by eye from the plate)
WHITE_OUT = (204.6, 206.3)


def file_pos(t):
    for (t0, x0, y0), (t1, x1, y1) in zip(FILE_PATH, FILE_PATH[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0)
            return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    return None


def handoff(c, t):
    p = file_pos(t)
    if p is None:
        return
    a = ramp(t, 201.10, 201.35)
    x, y = round(p[0]), round(p[1])
    w, h, fold = 64, 82, 18  # a document: a clay page with a folded corner
    poly(c, [(x - w / 2 + 3, y - h / 2 + 4), (x + w / 2 + 3, y - h / 2 + fold + 4), (x + w / 2 + 3, y + h / 2 + 4),
             (x - w / 2 + 3, y + h / 2 + 4)], (0, 0, 0), alpha=0.25 * a, blur=4)
    poly(c, [(x - w / 2, y - h / 2), (x + w / 2 - fold, y - h / 2), (x + w / 2, y - h / 2 + fold), (x + w / 2, y + h / 2),
             (x - w / 2, y + h / 2)], CLAY, alpha=a)
    poly(c, [(x + w / 2 - fold, y - h / 2), (x + w / 2, y - h / 2 + fold), (x + w / 2 - fold, y - h / 2 + fold)],
         (240, 196, 176), alpha=a)
    for k in range(3):
        line(c, [(x - w / 2 + 12, y - 6 + 14 * k), (x + w / 2 - 12, y - 6 + 14 * k)], 2.5, fill=WHITE, alpha=0.85 * a)
    tw = gfx.font("Mono-Medium", 22).getlength("only-what-i-said.md")
    S = c.S
    lay = c.layer()  # on a light chip: the gloves it passes over are black
    ImageDraw.Draw(lay).rounded_rectangle([(x - tw / 2 - 10) * S, (y + h / 2 + 8) * S, (x + tw / 2 + 10) * S,
                                           (y + h / 2 + 40) * S], 6 * S, fill=(250, 249, 246, 235))
    c.put(lay, a)
    sprite(c, (x, y + h / 2 + 31), "only-what-i-said.md", "Mono-Medium", 22, INK, alpha=a, anchor="ms")


def white(c, t):
    k = ramp(t, *WHITE_OUT)
    if k > 0:
        lay = c.layer()
        ImageDraw.Draw(lay).rectangle([0, 0, c.w, c.h], fill=(250, 249, 246, 255))
        c.put(lay, k)


def layer(c, t, sid):
    if sid == "s062":
        gfx_fc.layer(c, t, sid)  # TRUE, holding a second from the final chorus
    elif sid == "s063":
        dialog(c, t)
    elif sid == "s064":
        song_band(c, t)
    elif sid == "s065":
        handoff(c, t)
