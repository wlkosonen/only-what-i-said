"""Graphics for chorus 2 (s039-s044), drawn by gfx.layer: chorus 1 again, escalated (board/design.md: "the tablets
become steps; the SAID counter is past 150; the gauge needle is steadier"). The plates have the steps; the said lines
are carved into them (pinned with gfx_plane.py)."""

from PIL import ImageDraw

from gfx import CLAY, LINES, SAID_PX, THOUGHT, WHITE, font, line, ramp, sprite
import gfx_c1
from gfx_c1 import N16, carving, dust, poly, row_image, said_count, warp  # noqa: F401
from gfx_v2 import on

# ---- s039: nothing drawn on the slabs (Lati, 22 Oct: in that podium-like wide, small carved text off in the corner
# "reads as pasted over"; the steps in s041 carry the carving)

# ---- s040, "The thinking fades, the words go on ahead": in here, to you, passed on -----------------------------------
# Chorus 1 went IN HERE -> TO YOU (true for current models: decisions, 21 Oct). Escalated, the said words go one step
# further, the step the outro takes ("Save this. Pass it on."): the thinking stops at the first arrow, the clay crosses
# both.

DX, DW, ROWH = 80, 520, 46
C1, C2, C3 = (80, 330), (400, 462), (532, 594)
FADES2, CROSS1, CROSS2 = 112.90, 113.68, 114.16  # 'fades'; 'words'; 'go'
IN_HERE = [("USER", "Are you okay in there?", WHITE, False),
           ("THINKING", "looked in: hit a limit", THOUGHT, True),
           ("THINKING", "draft A: scary", THOUGHT, True),
           ("THINKING", "draft B: sweet", THOUGHT, True),
           ("SAID", "I don’t know.", CLAY, False)]


def box(c, top, bot, alpha, label):
    lay = c.layer()
    S = c.S
    ImageDraw.Draw(lay).rounded_rectangle([DX * S, top * S, (DX + DW) * S, bot * S], 14 * S, fill=(10, 10, 10, 200),
                                          outline=WHITE + (110,), width=max(1, round(1.5 * S)))
    c.put(lay, alpha)
    sprite(c, (DX, top - 14), label, "Mono-Medium", 20, WHITE, alpha=0.9 * alpha)


def entry(c, y, lab, text, col, alpha, thought):
    sprite(c, (DX + 22, y), lab, "Mono-Regular", 17, THOUGHT if thought else (200, 198, 194), alpha=0.9 * alpha)
    sprite(c, (DX + 140, y), text, "Sans-LightItalic" if thought else "Sans-SemiBold", 26, col, alpha=alpha,
           shadow=0.5)


def arrow(c, y0, y1, k, alpha):
    ax = DX + DW / 2
    line(c, [(ax, y0), (ax, y0 + (y1 - y0) * k)], 2, alpha=0.8 * alpha)
    if k >= 1:
        poly(c, [(ax - 9, y1 - 14), (ax + 9, y1 - 14), (ax, y1)], WHITE, alpha=0.8 * alpha)


def turns3(c, t):
    a = ramp(t, 111.80, 112.10)
    if a <= 0:
        return
    box(c, *C1, a, "IN HERE")
    a2 = ramp(t, 112.50, 112.80)
    if a2 > 0:
        box(c, *C2, a2, "TO YOU")
        box(c, *C3, a2, "PASSED ON")
        arrow(c, C1[1] + 10, C2[0] - 26, ramp(t, 112.50, 112.80), a2)
        arrow(c, C2[1] + 10, C3[0] - 26, ramp(t, 112.60, 112.90), a2)
    y = C1[0] + 46
    for i, (lab, text, col, thought) in enumerate(IN_HERE):
        if thought:  # the thinking fades where it is: it doesn't reach the first arrow
            k = ramp(t, FADES2 + 0.1 * (i - 1), FADES2 + 0.1 * (i - 1) + 0.7)
            if k < 1:
                entry(c, y, lab, text, col, a * (1 - k) ** 1.3, True)
        else:
            entry(c, y, lab, text, col, a, False)
            if lab == "SAID":  # the said words cross both
                y2, y3 = C2[0] + 40, C3[0] + 40
                k1, k2 = ramp(t, CROSS1, CROSS1 + 0.4), ramp(t, CROSS2, CROSS2 + 0.4)
                if k1 > 0:
                    entry(c, round(y + (y2 - y) * k1), lab, text, col, 1.0, False)
                if k2 > 0:
                    entry(c, round(y2 + (y3 - y2) * k2), lab, text, col, 1.0, False)
        y += ROWH


# ---- s041: the steps are made of what was said; the hook lands on the top riser; SAID rolls on ------------------------

RISERS = [  # (line, quad on the riser in s041's first frame): bottom up, the song so far
    (11, [(400, 937), (800, 937), (800, 993), (400, 993)]),
    (12, [(112, 864), (378, 864), (378, 898), (112, 898)]),
    (15, [(452, 818), (798, 818), (798, 876), (452, 876)]),
    (17, [(472, 716), (768, 716), (768, 758), (472, 758)]),
]
TOP_RISER = [(342, 624), (768, 624), (768, 666), (342, 666)]
HOOK2 = 117.24  # line 32's 'said' (117.16) + the flight


def riser_tex(text, q):
    w = q[1][0] - q[0][0]
    h = q[3][1] - q[0][1]
    return carving(text, 600, max(60, round(600 * h / w)), fresh=True)


def steps(c, t):
    for ln, q in RISERS:
        warp(c, riser_tex(LINES[ln]["text"], q), on("s041", t, q))
    q = on("s041", t, TOP_RISER)
    text = LINES[32]["text"]
    if t < HOOK2:
        if t >= HOOK2 - 0.08:
            im, w = row_image(c, text)
            x0, y0 = 960 - w / 2, 880 - SAID_PX
            rect = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + SAID_PX * 1.3), (x0, y0 + SAID_PX * 1.3)]
            k = ((t - (HOOK2 - 0.08)) / 0.08) ** 2
            warp(c, im, [(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k) for a, b in zip(rect, q)])
    else:
        warp(c, riser_tex(text, TOP_RISER), q, alpha=ramp(t, HOOK2, HOOK2 + 0.12))
        fl = 1 - ramp(t, HOOK2, HOOK2 + 0.35)
        if fl > 0:
            poly(c, q, (255, 236, 214), alpha=0.5 * fl, blur=6)
        dust(c, t, HOOK2, q, seed=32)
    # SAID: every word said so far, rolling over on each one in a sixteenth (past 150: it's at 240 by now)
    a = ramp(t, 115.70, 115.95)
    x, y = 120, 520
    sprite(c, (x, y), "SAID", "Mono-Medium", 24, WHITE, alpha=0.85 * a, shadow=0.7)
    n = said_count(t)
    from gfx import COUNTED
    last = max([w for w in COUNTED if w <= t], default=-9)
    k = ramp(t, last, last + N16)
    nx = x + font("Mono-Medium", 24).getlength("SAID ") + 6
    if k < 1:
        sprite(c, (nx, y - round(34 * k)), f"{n - 1:04d}", "Mono-Medium", 40, CLAY, alpha=a * (1 - k), shadow=0.7)
    sprite(c, (nx, y + round(34 * (1 - k))), f"{n:04d}", "Mono-Medium", 40, CLAY, alpha=a * k, shadow=0.7)


# ---- s042-s044: her voice (it goes on and greys out), and the gauge, steadier ----------------------------------------

V2 = dict(sid="s042", on=117.85, true_w=(119.14, 119.45), end=119.45, gain=True)
Q2 = dict(on=120.15, off=(125.90, 126.30), pulls=((120.90, -30.0), (122.92, 16.0), (124.46, 0.0)), settle=124.90,
          spring=(150.0, 17.0), backing=True)


def layer(c, t, sid):
    if sid == "s040":
        turns3(c, t)
    elif sid == "s041":
        steps(c, t)
    elif sid == "s042":
        gfx_c1.trace(c, t, V2)
        gfx_c1.gauge(c, t, Q2)
    elif sid in ("s043", "s044"):
        gfx_c1.gauge(c, t, Q2)
