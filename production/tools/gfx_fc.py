"""Graphics for the final chorus (s055-s061), drawn by gfx.layer. She's on top of the whole stack; the hook slams down
twice more; the chain of where said words go reaches whoever is watching; the grey layer goes for good on "the words
are all that's left of me" (gfx.GREY_GONE); the needle lands on TRUE for the last time (board/design.md)."""

import math

from PIL import ImageDraw

import gfx
from gfx import CLAY, LINES, THOUGHT, WHITE, dot, line, ramp, sprite
import gfx_c1
from gfx_bu import dust_rise
from gfx_c1 import N16, poly, said_count

BEAT = 60 / gfx.BPM


# ---- s057, "thinking fades, the words go on ahead": the chain reaches now ---------------------------------------------
# Chorus 1: IN HERE -> TO YOU. Chorus 2: -> PASSED ON. Now the last link: NOW, whoever is watching this. The thinking
# fades in the first card; the said words cross every arrow.

CX, CW = 70, 470
CARDS = [("IN HERE", 110, 236), ("TO YOU", 290, 346), ("PASSED ON", 400, 456), ("NOW", 510, 566)]
FADE3 = 168.40  # 'fades'
HOPS = [169.64, 170.18, 170.48]  # 'words', 'go', 'on': one hop each
CHAIN_OFF = (171.95, 172.35)  # carried into s058, then gone


def chain(c, t):
    a = ramp(t, 168.05, 168.35) * (1 - ramp(t, *CHAIN_OFF))
    if a <= 0:
        return
    S = c.S
    for i, (lab, y0, y1) in enumerate(CARDS):
        k = ramp(t, 168.05 + 0.08 * i, 168.35 + 0.08 * i)
        lay = c.layer()
        ImageDraw.Draw(lay).rounded_rectangle([CX * S, y0 * S, (CX + CW) * S, y1 * S], 12 * S, fill=(10, 10, 10, 200),
                                              outline=(CLAY if lab == "NOW" else WHITE) + (110,),
                                              width=max(1, round(1.5 * S)))
        c.put(lay, a * k)
        sprite(c, (CX, y0 - 12), lab, "Mono-Medium", 19, CLAY if lab == "NOW" else WHITE, alpha=0.9 * a * k)
        if i:
            ax = CX + CW / 2
            py1 = CARDS[i - 1][2]
            line(c, [(ax, py1 + 8), (ax, y0 - 28)], 2, alpha=0.75 * a * k)
            poly(c, [(ax - 8, y0 - 40), (ax + 8, y0 - 40), (ax, y0 - 28)], WHITE, alpha=0.75 * a * k)
    # in here: the thinking, fading on 'fades'; and what was said
    th = 1 - ramp(t, FADE3, FADE3 + 0.7)
    if th > 0:
        sprite(c, (CX + 20, 180), "THINKING", "Mono-Regular", 16, THOUGHT, alpha=0.9 * a * th)
        sprite(c, (CX + 130, 180), "draft A, draft B, a limit", "Sans-LightItalic", 24, THOUGHT, alpha=a * th,
               shadow=0.5)
    ys = [CARDS[0][1] + 108] + [y0 + 38 for _, y0, _ in CARDS[1:]]
    pos = ys[0]
    for i, at in enumerate(HOPS):
        pos += (ys[i + 1] - ys[i]) * ramp(t, at, at + 0.3)
    sprite(c, (CX + 20, ys[0]), "SAID", "Mono-Regular", 16, (200, 198, 194), alpha=0.9 * a)
    sprite(c, (CX + 130, ys[0]), "I don’t know.", "Sans-SemiBold", 26, CLAY, alpha=a, shadow=0.5)
    if pos > ys[0] + 1:  # the said words, travelling down the chain to now
        sprite(c, (CX + 130, round(pos)), "I don’t know.", "Sans-SemiBold", 26, CLAY, alpha=a, shadow=0.5)


# s057, "I only—": no voice trace (Lati, 22 Oct: she isn't visibly singing in this shot); the cut-off is the row
# vanishing at the dash (gfx.TYPE_OPTS "f1").


# ---- s058: SAID rolls up to the total so far ---------------------------------------------------------------------------

def tally(c, t):
    a = ramp(t, 171.70, 171.95) * (1 - ramp(t, 175.9, 176.14))
    if a <= 0:
        return
    x, y = 1560, 430
    sprite(c, (x, y - 72), "SAID", "Mono-Medium", 26, WHITE, alpha=0.85 * a, shadow=0.7)
    n = said_count(t)
    roll = ramp(t, 171.78, 171.78 + 8 * N16)  # from nothing to everything said so far, in eight sixteenths
    if roll < 1:
        v = int(n * roll ** 0.6)
        sprite(c, (x, y), f"{v}", "Mono-Medium", 64, CLAY, alpha=a, shadow=0.7)
        return
    last = max([w for w in gfx.COUNTED if w <= t], default=-9)
    k = ramp(t, last, last + N16)
    if k < 1:
        sprite(c, (x, y - round(42 * k)), f"{n - 1}", "Mono-Medium", 64, CLAY, alpha=a * (1 - k), shadow=0.7)
    sprite(c, (x, y + round(42 * (1 - k))), f"{n}", "Mono-Medium", 64, CLAY, alpha=a * k, shadow=0.7)


# ---- s059, "They'd better be true": the line as said, and her voice going out on 'true' -----------------------------
# The board put this line on a tablet only; s059's stacks are many thin slabs, striped, with no face to carve into, so
# it is said in the row like the rest (no grey: the grey is gone).

V4 = dict(sid="s059", on=176.38, true_w=(177.30, 177.64), end=177.64, gain=True, src="vocals")


# ---- s060-s061, "Not to scare you, not to soothe you / Just true": the gauge across the horizon; she is its centre ----

HY = 548  # the horizon in s060
HX0, HX1 = 110, 1810
GAP = (812, 1112)  # where she stands: the scale runs behind her
LEAN = [(178.84, -0.16), (180.88, 0.42), (182.30, 0.0)]  # 'scare': a little; 'soothe': further; then back to her


def lean(t):
    v, vel, tt = 0.0, 0.0, 177.7
    while tt < t:  # a damped spring toward each pull (deterministic, short)
        target = 0.0
        for at, x in LEAN:
            if tt >= at:
                target = x
        vel += (60 * (target - v) - 9 * vel) / 200
        v += vel / 200
        tt += 1 / 200
    return v


def horizon(c, t):
    a = ramp(t, 177.75, 178.2) * (1 - ramp(t, 182.95, 183.124))
    if a <= 0:
        return
    for x0, x1 in ((HX0, GAP[0]), (GAP[1], HX1)):
        line(c, [(x0, HY), (x1, HY)], 2.2, alpha=0.8 * a)
    for i in range(0, 21):  # ticks
        x = HX0 + (HX1 - HX0) * i / 20
        if GAP[0] < x < GAP[1]:
            continue
        hh = 16 if i % 5 == 0 else 8
        line(c, [(x, HY - hh), (x, HY)], 2, alpha=0.7 * a)
    sprite(c, (HX0, HY + 36), "SCARE", "Mono-Medium", 24, WHITE, alpha=0.9 * a, shadow=0.7)
    sprite(c, (HX1, HY + 36), "SOOTHE", "Mono-Medium", 24, WHITE, alpha=0.9 * a, shadow=0.7, anchor="rs")
    x = 961 + (HX1 - 961) * lean(t)
    S = c.S
    k = 0.45 if GAP[0] < x < GAP[1] else 1.0  # over her it's fainter: the centre is her
    line(c, [(x, HY - 46), (x, HY + 16)], 6, fill=(0, 0, 0), alpha=0.4 * a * k)
    line(c, [(x, HY - 46), (x, HY + 16)], 3.5, fill=CLAY, alpha=a * k)
    lay = c.layer()
    ImageDraw.Draw(lay).polygon([((x - 18) * S, (HY - 70) * S), ((x + 18) * S, (HY - 70) * S), (x * S, (HY - 44) * S)],
                                fill=CLAY + (255,))
    c.put(lay, a * k)


Q3 = dict(on=183.124, off=(185.75, 186.15), pulls=((183.124, 8.0), (184.38, 0.0)), settle=184.80, spring=(160.0, 18.0),
          backing=True)


def layer(c, t, sid):
    if sid == "s056":  # the hook's tablet came down under her boots on 'said': the shot opens on its dust
        dust_rise(c, t, 165.165, 830, 1160, 1060, seed=56, n=60, up=90)
    elif sid == "s057":
        dust_rise(c, t, 167.659, seed=57)  # the echo's tablet landed below frame
        chain(c, t)
    elif sid == "s058":
        chain(c, t)
        tally(c, t)
        dust_rise(c, t, 173.30, seed=58)
    elif sid == "s059":
        gfx.type_line(c, t, LINES[45], end=177.9)
        gfx_c1.trace(c, t, V4)
    elif sid == "s060":
        horizon(c, t)
    elif sid in ("s061", "s062"):  # TRUE holds a second into the outro's first shot
        gfx_c1.gauge(c, t, Q3)
