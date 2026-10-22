#!/usr/bin/env python3
"""The film's graphics layer, drawn over each frame of the cut (roughcut.py --gfx calls layer() per frame).

Design (Kiln, 21 Oct; board/design.md is the spec, this is the build):
- One family, IBM Plex (open licence): Sans SemiBold for what she says, Sans Light Italic for thinking, Mono for the
  meter and labels, Serif for the bridge letter. Plain and generic; nothing from a real chat product.
- Clay #D97757 only for what is said (the said words, the meter). Everything else is white or grey.
- Thinking comes before saying: a line's grey thinking copy appears just before she sings it; as each word is sung its
  clay copy lands and the grey word drifts up and dissolves. "The thinking fades, the words go on ahead" is the
  grammar of the whole film, not just its line.
- Sizes are in 1080p pixels and scale to the output (S = width / 1920).
"""

import json
import math
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "media/cache/fonts"
CLAY = (217, 119, 87)
WHITE = (244, 242, 238)
GREY = (190, 188, 184)
INK = (24, 24, 24)
BPM = 119.3
EIGHTH = 60 / BPM / 2
N32 = 60 / BPM / 8

BOARD = json.loads((ROOT / "production/board/board.json").read_text())
SHOTS = {s["id"]: s for s in BOARD["shots"]}
LINES = {l["line"]: l for l in BOARD["lyric_lines"]}


@lru_cache(maxsize=None)
def font(name, px):
    return ImageFont.truetype(str(FONTS / f"IBMPlex{name}.ttf"), max(6, round(px)))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    """0 before a, 1 after b, smooth in between."""
    return ease((t - a) / max(b - a, 1e-6))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h, self.S = w, h, w / 1920
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def layer(self):
        return Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def put(self, lay, alpha=1.0, blur=0.0):
        if blur > 0.05:
            lay = lay.filter(ImageFilter.GaussianBlur(blur * self.S))
        if alpha < 0.999:
            a = lay.getchannel("A").point(lambda v: int(v * max(alpha, 0)))
            lay.putalpha(a)
        self.im.alpha_composite(lay)

    def text(self, xy, s, face, px, fill, alpha=1.0, anchor="la", blur=0.0, glow=0.0, shadow=0.0):
        lay = self.layer()
        d = ImageDraw.Draw(lay)
        f = font(face, px * self.S)
        x, y = xy[0] * self.S, xy[1] * self.S
        if shadow:  # a soft dark halo so a clay word holds over white shirts and bright light
            sh = self.layer()
            ImageDraw.Draw(sh).text((x, y + 2 * self.S), s, font=f, fill=(0, 0, 0, 255), anchor=anchor)
            self.put(sh.filter(ImageFilter.GaussianBlur(5 * self.S)), alpha * shadow)
        d.text((x, y), s, font=f, fill=fill + (255,), anchor=anchor)
        if glow:
            g = lay.filter(ImageFilter.GaussianBlur(glow * self.S))
            self.put(g, alpha * 0.8)
        self.put(lay, alpha, blur)

    def width(self, s, face, px):
        return font(face, px * self.S).getlength(s) / self.S


@lru_cache(maxsize=512)
def _text_sprite(s, face, px, fill, S, shadow):
    f = font(face, px * S)
    pad = round(16 * S) + 4
    l, t_, r, b = f.getbbox(s, anchor="ls")
    im = Image.new("RGBA", (r - l + 2 * pad, b - t_ + 2 * pad), (0, 0, 0, 0))
    org = (pad - l, pad - t_)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((org[0], org[1] + 2 * S), s, font=f, fill=(0, 0, 0, 255), anchor="ls")
        sh = sh.filter(ImageFilter.GaussianBlur(5 * S))
        sh.putalpha(sh.getchannel("A").point(lambda v: int(v * shadow)))
        im.alpha_composite(sh)
    ImageDraw.Draw(im).text(org, s, font=f, fill=fill + (255,), anchor="ls")
    return im, org, (r - l)


def sprite(c, xy, s, face, px, fill, alpha=1.0, shadow=0.0, anchor="ls"):
    """Text that moves: drawn once and placed on whole pixels, so its letters never re-space (Lati, 21 Oct)."""
    if not s or alpha <= 0.003:
        return
    im, (ox, oy), w = _text_sprite(s, face, round(px, 2), fill, round(c.S, 4), round(shadow, 2))
    x = xy[0] * c.S - (w / 2 if anchor[0] == "m" else w if anchor[0] == "r" else 0)
    lay = c.layer()
    lay.paste(im, (round(x) - ox, round(xy[1] * c.S) - oy))
    c.put(lay, alpha)


# ---- the context meter ------------------------------------------------------------------------------------------------

def _counted_words():
    """Start times of the words the meter counts: every sung word from line 2 on (the board's rule), minus the
    board's unsung words, ending on 'song'."""
    ws, k = [], 0
    for l in BOARD["lyric_lines"]:
        for w in l["words"]:
            if l["line"] not in (0, 1) and k not in BOARD["unsung_words"]:
                ws.append(w["t0"])
            k += 1
    return sorted(ws)


COUNTED = _counted_words()
COUNTED_SET = set(COUNTED)
METER_ON = 12.308


def meter_value(t):
    n = sum(1 for w in COUNTED if w <= t)
    return 100 if n >= len(COUNTED) else math.floor(100 * n / len(COUNTED))


def meter_bar(shot):
    """The bar's thickness from the board's words for this shot ("a hairline", "2 px", ...): it thickens through the
    film. Lati, 21 Oct: the meter "will go unnoticed as it is now", so it spans the frame's whole width."""
    p = next((d["params"] for d in shot.get("devices", []) if d["kind"] == "meter"), {})
    txt = str(p.get("bar", "a hairline"))
    px = re.search(r"(\d+(?:\.\d+)?)\s*px", txt)
    return 3.0 + 2.0 * (float(px.group(1)) if px else 1.0)


METER_X0, METER_X1, METER_Y = 24, 1920 - 24, 1080 - 26
METER_FULL = 189.34  # "The window's nearly full": from 'full' on, the meter is the thing in frame
METER_INK = ("s065",)  # shots on a white set: the meter in ink


def meter_head(v):
    return METER_X0 + (METER_X1 - METER_X0) * v / 100


def meter(c, t, shot):
    if t < METER_ON - 0.01:
        return
    a = ramp(t, METER_ON, METER_ON + 0.5)
    v = meter_value(t)
    big = ramp(t, METER_FULL - 0.14, METER_FULL + 0.16)
    ink = shot["id"] in METER_INK
    th = meter_bar(shot) + 5 * big
    base = INK if ink else WHITE
    col = tuple(round(base[i] + (CLAY[i] - base[i]) * big) for i in range(3))
    # the last jump flares briefly, so the eye catches the window filling
    last = max([w for w in COUNTED if w <= t], default=-9)
    flare = 1 - ramp(t, last + 0.45, last + 0.9) if t - last < 0.9 else 0
    c.text((METER_X0, METER_Y - th - 12), f"CONTEXT {v}%", "Mono-Medium", 24 + 26 * big, col, alpha=(0.85 + 0.15 * big) * a,
           anchor="ls", shadow=0.0 if ink else 0.95 * big)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    S = c.S
    d.rectangle([METER_X0 * S, (METER_Y - th) * S, METER_X1 * S, METER_Y * S], fill=base + (40,))
    d.rectangle([METER_X0 * S, (METER_Y - th) * S, meter_head(v) * S, METER_Y * S], fill=CLAY + (255,))
    if flare > 0:
        g = c.layer()
        hx = meter_head(v)
        ImageDraw.Draw(g).ellipse([(hx - 10) * S, (METER_Y - th / 2 - 10) * S, (hx + 10) * S, (METER_Y - th / 2 + 10) * S],
                                  fill=CLAY + (255,))
        c.put(g.filter(ImageFilter.GaussianBlur(8 * S)), a * flare)
    c.put(lay, a)


def spark(c, t, x, y, w0):
    """A said word, as it lands, drops a small clay spark into the meter: what's said is what fills the window."""
    k = (t - w0 - 0.05) / 0.55
    if not 0 <= k <= 1 or w0 < METER_ON or w0 not in COUNTED_SET:
        return
    tx, ty = meter_head(meter_value(w0 + 0.01)), METER_Y
    e = k * k  # accelerates down
    px, py = x + (tx - x) * e, y + (ty - y) * e - 60 * math.sin(math.pi * k)
    lay = c.layer()
    r = 5 * (1 - 0.5 * k)
    ImageDraw.Draw(lay).ellipse([(px - r) * c.S, (py - r) * c.S, (px + r) * c.S, (py + r) * c.S], fill=CLAY + (255,))
    c.put(lay.filter(ImageFilter.GaussianBlur(1.2 * c.S)), 0.9 * (1 - 0.3 * k))


# ---- thinking and said ------------------------------------------------------------------------------------------------

SAID_PX, THINK_PX = 40, 30


def _tokens(line):
    """The line's display words (original case and punctuation) paired with their sung timings."""
    shown = line["text"].split()
    sung = line["words"]
    if len(shown) != len(sung):  # fall back to the sung words if the sheet and the singing differ
        shown = [w["w"] for w in sung]
    return [(s, w["t0"], w["t1"]) for s, w in zip(shown, sung)]


def _wrap(tokens, face, px, c, maxw):
    rows, row, wid = [], [], 0
    sp = c.width(" ", face, px)
    for tok in tokens:
        tw = c.width(tok[0], face, px)
        if row and wid + sp + tw > maxw:
            rows.append(row)
            row, wid = [], 0
        row.append(tok)
        wid += (sp if wid else 0) + tw
    if row:
        rows.append(row)
    return rows


THOUGHT = (150, 148, 144)
GREY_GONE = 174.02  # "The words are all that's left of me": from this line on there is no grey thinking type at all


def type_line(c, t, line, y_said=880, x_center=960, end=None, words=None, drop=None, g=2600, hand=None, start=None,
              cut=False):
    """One sung line, one row of words (Lati, 21 Oct: two rows "read as two lyric subtitles at the same time"). The
    line appears in place as grey thinking just before she sings it; as each word is sung it turns clay where it
    stands, and its grey copy peels off upward, lingering and dissolving over ~2.5 s. The said words hold until `end`
    (or 0.7 s after the last word). Grey is mid-grey with a dark halo so it reads on white shirts and on black.
    `words` keeps only the line's first n words (a device carries the rest); from `drop` on, the said row falls out
    of the bottom of the frame (accelerating at g px/s^2); from `hand` on, a device carries the said row instead.
    `start` is when the row may first appear (the line before it has to be gone: one row at a time). `cut`: the row
    vanishes at `end` instead of fading ("I only—")."""
    toks = _tokens(line)[:words]
    t_first, t_last = toks[0][1], toks[-1][2]
    end = end if end is not None else t_last + 0.7
    start = t_first - 0.7 if start is None else start
    if t < start or t > max(end + 0.45, t_last + 2.8):
        return
    shown = ramp(t, start, start + 0.15)
    grey = t_first < GREY_GONE
    out = (0.0 if t >= end else 1.0) if cut else 1 - ramp(t, end, end + 0.45)
    face, px = "Sans-SemiBold", SAID_PX
    fall = round(g * (t - drop) ** 2) if drop is not None and t > drop else 0
    rows = _wrap(toks, face, px, c, 1500)
    for r, row in enumerate(rows):
        wsum = sum(c.width(k[0], face, px) for k in row) + c.width(" ", face, px) * (len(row) - 1)
        x = x_center - wsum / 2
        y0 = y_said - (len(rows) - 1 - r) * 54
        y = y0 + fall
        for tok, w0, w1 in row:
            ww = c.width(tok, face, px)
            land = ramp(t, w0 - 0.02, w0 + 0.1)
            pre = ramp(t, start, start + 0.4)
            if grey and land < 0.99 and pre > 0.01:  # the thought, waiting in place
                c.text((x, y), tok, face, px, THOUGHT, alpha=0.55 * pre * (1 - land) * out, anchor="ls", shadow=0.4)
            if land > 0.01:  # said: clay, stays
                if hand is None or t < hand:
                    c.text((x, y - 6 * (1 - land)), tok, face, px, CLAY, alpha=land * out * shown, anchor="ls",
                           shadow=0.55)
                k = (t - w0) / 2.6  # the thought peels off and drifts up, slowly
                if grey and 0 < k < 1:
                    c.text((x, y0 - 120 * ease(k) ** 0.8), tok, face, px, THOUGHT, alpha=0.5 * (1 - k) ** 1.5,
                           anchor="ls", blur=3.5 * k, shadow=0.3 * (1 - k))
                spark(c, t, x + ww / 2, y0 - px / 2, w0)
            x += ww + c.width(" ", face, px)


TYPE_OPTS = {
    10: {"words": 5},  # "I don't know." types into the drafts list instead (gfx_p1)
    # the hook: on the d of "said" (the beat slams back in) the said line slams down onto a tablet (gfx_c1)
    11: {"drop": 48.74, "g": 14000, "end": 49.4},  # s018: out of the bottom of the frame; s019 opens on the tablet
    12: {"hand": 50.78},  # s019: the echo line slams onto the second tablet
    14: {"drop": 56.84, "g": 14000, "end": 57.5},  # s021: out of the frame again, the SAID counter with it
    # pre-chorus 2 and chorus 2 (gfx_p2, gfx_c2)
    28: {"words": 5},  # "I don't know." types into the drafts list
    29: {"drop": 109.16, "g": 14000, "end": 109.8},  # s038: the bass lands on 'said', the line slams out of frame
    32: {"hand": 117.16},  # s041: the hook slams onto the top riser of the steps
    # final chorus (gfx_fc): the hook slams out on 'said' twice more
    40: {"drop": 164.92, "g": 14000, "end": 165.5},  # s055 -> s056 opens on the dust at her boots
    43: {"drop": 173.14, "g": 14000, "end": 173.7},  # s058: its tablet lands below the frame
    "f1": {"end": 168.02, "cut": True},  # "I only—": cut off at the dash, the row with it
}


def type_layer(c, t, shot):
    """The shot's sung lines, from the board's type entries (subtitle mode; the tablets' 'stack' mode is drawn by
    the chorus devices)."""
    seen = set()
    for e in shot.get("type", []):
        if e["mode"] != "subtitle" or e["line"] in seen or e["line"] in INTRO_TYPED:
            continue
        seen.add(e["line"])
        opts = dict(TYPE_OPTS.get(e["line"], {}))
        opts.pop("end", None)
        if opts.pop("skip", False):
            continue
        type_line(c, t, LINES[e["line"]], end=_line_end(e["line"]), start=_line_start(e["line"]), **opts)


def _by_time():
    return sorted(LINES, key=lambda k: LINES[k]["t0"])


def _next(n):
    order = _by_time()
    i = order.index(n)
    return LINES[order[i + 1]] if i + 1 < len(order) else None


def _prev(n):
    order = _by_time()
    i = order.index(n)
    return order[i - 1] if i > 0 else None


def _line_end(n):
    o = TYPE_OPTS.get(n, {})
    if "end" in o:
        return o["end"]
    line = LINES[n]
    nxt = _next(n)  # in sung order: the build's hooks and "I only—" sit between numbered lines
    return max(min(line["t1"] + 0.7, (nxt["t0"] - 0.2) if nxt else 1e9), line["t1"] + 0.15)


def _line_start(n):
    """A line's grey waits in place from 0.7 s before she sings it, but only once the line before has left the row
    (21 Oct: lines 0.06 s apart overprinted each other; 22 Oct: in sung order, not by number)."""
    t0 = LINES[n]["t0"] - 0.7
    p = _prev(n)
    if p is None:
        return t0
    o = TYPE_OPTS.get(p, {})
    gone = o["drop"] + 0.15 if "drop" in o else o["hand"] if "hand" in o else \
        _line_end(p) if o.get("cut") else _line_end(p) + 0.45
    return max(t0, gone)


# ---- the intro: the white box (s001-s007) ----------------------------------------------------------------------------

QUESTION = "Are you okay in there?"
TYPE_START = 4.00  # the first letter lands on 'typed'
INTRO_TYPED = set()  # lines whose words are carried by the chat UI instead of subtitles (none: both run)


def typed(t):
    n = int(max(0.0, t - TYPE_START) / N32) + 1 if t >= TYPE_START else 0
    return QUESTION[: min(n, len(QUESTION))]


def box(c, cx, cy, w, h, alpha=1.0, glow=True, fill=WHITE, r=22):
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    S = c.S
    d.rounded_rectangle([(cx - w / 2) * S, (cy - h / 2) * S, (cx + w / 2) * S, (cy + h / 2) * S], r * S,
                        fill=fill + (255,))
    if glow:
        c.put(lay.filter(ImageFilter.GaussianBlur(38 * S)), alpha * 0.55)
    c.put(lay, alpha)


def cursor(c, x, y, h, t, stop=None, alpha=1.0, color=INK):
    on = True if (stop is not None and t >= stop) else (int(t / EIGHTH) % 2 == 0)
    if on:
        lay = c.layer()
        ImageDraw.Draw(lay).rectangle([x * c.S, (y - h / 2) * c.S, (x + 3) * c.S, (y + h / 2) * c.S], fill=color + (255,))
        c.put(lay, alpha)


def send_arrow(c, x, y, lit, alpha=1.0):
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    S, r = c.S, 26
    col = CLAY if lit else (200, 198, 194)
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=col + (255,))
    d.line([(x * S, (y + 11) * S), (x * S, (y - 11) * S)], fill=WHITE + (255,), width=max(1, round(3.4 * S)))
    d.line([((x - 9) * S, (y - 2) * S), (x * S, (y - 11) * S), ((x + 9) * S, (y - 2) * S)], fill=WHITE + (255,),
           width=max(1, round(3.4 * S)), joint="curve")
    c.put(lay, alpha)


@lru_cache(maxsize=32)
def _bubble_sprite(s, px, S):
    """The quoted bubble, drawn once: re-drawing text at fractional positions re-spaces its letters (Lati, 21 Oct:
    "distance between letters shifts, jarring")."""
    f = font("Sans-Regular", px * S)
    w = f.getlength(s) + 2 * px * S
    h = px * 2.2 * S
    im = Image.new("RGBA", (round(w) + 4, round(h) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, 2 + w, 2 + h], h / 2, fill=(236, 234, 230, 255))
    d.text((2 + w / 2, 2 + h / 2), s, font=f, fill=INK + (255,), anchor="mm")
    return im


def bubble(c, cx, cy, s, px, alpha=1.0):
    sp = _bubble_sprite(s, px, round(c.S, 4))
    lay = c.layer()
    lay.alpha_composite(sp, (round(cx * c.S - sp.width / 2), round(cy * c.S - sp.height / 2)))
    c.put(lay, alpha)


def intro(c, t, sid):
    if sid == "s001":  # an empty box rises under her chin on the 1.122 beat, cursor blinking on eighths
        k = ramp(t, 1.122, 1.122 + 0.45)
        cy = 1080 + 120 - 260 * k
        box(c, 960, cy, 980, 108, alpha=k)
        cursor(c, 960 - 980 / 2 + 44, cy, 46, t, alpha=k)
    elif sid == "s002":  # the box fills the frame; the question starts typing on 'typed'
        box(c, 960, 540, 1500, 230, glow=True)
        s = typed(t)
        twitch = 1 if 3.62 <= t < 3.70 else 0
        c.text((960 - 690, 540), s, "Sans-Regular", 64, INK, anchor="lm")
        cursor(c, 960 - 690 + c.width(s, "Sans-Regular", 64) + 6 + 4 * twitch, 540, 74, t)
        send_arrow(c, 960 + 690, 540, lit=False)
    elif sid in ("s003", "s004"):  # the question on the glass in front of her face
        s = typed(t)
        rack = ramp(t, 6.709, 6.709 + 0.35) if sid == "s004" else 0
        lift = ramp(t, 7.73, 7.73 + 0.55) if sid == "s004" else 0
        y = 470 - 520 * lift ** 1.6
        if lift < 0.02:
            # a frosted strip of glass in front of her face, so the question reads over hair, skin or light
            fw = c.width(QUESTION, "Sans-Regular", 66) + 120
            box(c, 960, y, fw, 118, alpha=0.42, glow=False, fill=(250, 249, 246), r=24)
            c.text((960 - fw / 2 + 60, y), s, "Sans-Regular", 66, INK, alpha=0.9, anchor="lm", blur=5 * rack)
            if sid == "s003" and len(s) < len(QUESTION):
                cursor(c, 960 - fw / 2 + 60 + c.width(s, "Sans-Regular", 66) + 6, y, 72, t)
        else:
            bubble(c, 960, y, QUESTION, 44, alpha=1 - ramp(t, 7.73 + 0.3, 7.73 + 0.55))
        if sid == "s004":
            send_arrow(c, 1700, 470, lit=t >= 7.73, alpha=1 - lift)
    elif sid == "s005":  # the sent bubble hangs above her head, small, quoted
        bubble(c, 960, 120, QUESTION, 34, alpha=ramp(t, 8.237, 8.237 + 0.3))
    elif sid == "s006":  # the empty reply field; the cursor blinks and stops on 'stops'
        box(c, 960, 540, 1500, 230, glow=True)
        c.text((960 - 690, 540), "Reply", "Sans-Regular", 52, (178, 176, 172), anchor="lm", alpha=0.0)
        cursor(c, 960 - 690, 540, 74, t, stop=11.72)


# ---- her face, tracked (gfx_track.py), and drawing helpers -------------------------------------------------------

@lru_cache(maxsize=None)
def _track(sid):
    f = ROOT / f"media/cache/gfx/track-{sid}.json"
    return json.loads(f.read_text()) if f.exists() else None


def face(sid, t):
    """Her face at time t in 1080p units: {'bbox': [x0, y0, x1, y1], 'kps': 5 points, 'lmk': 106 points} or None."""
    tr = _track(sid)
    if not tr:
        return None
    i = min(range(len(tr["t"])), key=lambda k: abs(tr["t"][k] - t))
    if tr["bbox"][i] is None:
        return None
    return {"bbox": tr["bbox"][i], "kps": tr["kps"][i], "lmk": tr["lmk"][i]}


def line(c, pts, w=2.0, fill=WHITE, alpha=1.0):
    lay = c.layer()
    ImageDraw.Draw(lay).line([(x * c.S, y * c.S) for x, y in pts], fill=fill + (255,), width=max(1, round(w * c.S)))
    c.put(lay, alpha)


def dot(c, x, y, r, fill=WHITE, alpha=1.0):
    lay = c.layer()
    ImageDraw.Draw(lay).ellipse([(x - r) * c.S, (y - r) * c.S, (x + r) * c.S, (y + r) * c.S], fill=fill + (255,))
    c.put(lay, alpha)


def pin(c, t, at, target, lab, text, px=24, alpha=1.0):
    """A leader line from a feature on her to its label: the line draws, then the label types in."""
    k = ramp(t, at, at + 0.18)
    if k <= 0 or alpha <= 0.01:
        return
    tx, ty = target
    lx, ly = min(max(lab[0], 60), 1860), min(max(lab[1], 70), 1000)  # labels stay inside the frame
    dot(c, tx, ty, 4.5, alpha=0.95 * alpha)
    line(c, [(tx, ty), (tx + (lx - tx) * k, ty + (ly - ty) * k)], 1.8, alpha=0.8 * alpha)
    n = len(text) if t - at > 0.45 else int(len(text) * max(0.0, (t - at - 0.18) / 0.27))
    if n:
        right = lx >= tx
        c.text((lx + (10 if right else -10), ly + 8), text[:n], "Mono-Medium", px, WHITE, alpha=0.92 * alpha,
               anchor="ls" if right else "rs", shadow=0.7)


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def face_matte(sid, t, w, h, grow=1.12):
    """A soft matte of her face (the hull of its 106 landmarks, grown a little) at time t, at output size."""
    f = face(sid, t)
    if not f:
        return None
    S = w / 1920
    pts = [(x * S, y * S) for x, y in f["lmk"]]
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    pts = [(cx + (x - cx) * grow, cy + (y - cy) * grow) for x, y in pts]
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(_hull(pts), fill=255)
    return m.filter(ImageFilter.GaussianBlur(10 * S))


# ---- per shot -----------------------------------------------------------------------------------------------------------

def layer(sid, t, w, h):
    """The graphics over shot `sid` at song time t, as an RGBA image of the output size."""
    c = Canvas(w, h)
    shot = SHOTS[sid]
    if sid in ("s001", "s002", "s003", "s004", "s005", "s006"):
        intro(c, t, sid)
    elif sid in ("s008", "s009", "s010", "s011", "s012", "s013", "s014"):
        import gfx_v1
        gfx_v1.layer(c, t, sid)
    elif sid in ("s015", "s016", "s017", "s018"):
        import gfx_p1
        gfx_p1.layer(c, t, sid)
    elif sid in ("s019", "s020", "s021", "s022", "s023", "s024"):
        import gfx_c1
        gfx_c1.layer(c, t, sid)
    elif sid in ("s025", "s026", "s027", "s028", "s029", "s030", "s031", "s032", "s033"):
        import gfx_v2
        gfx_v2.layer(c, t, sid)
    elif sid in ("s034", "s035", "s036", "s037", "s038"):
        import gfx_p2
        gfx_p2.layer(c, t, sid)
    elif sid in ("s039", "s040", "s041", "s042", "s043", "s044"):
        import gfx_c2
        gfx_c2.layer(c, t, sid)
    elif sid in ("s045", "s046", "s047", "s048"):
        import gfx_br
        gfx_br.layer(c, t, sid)
    elif sid in ("s049", "s050", "s051", "s052", "s053", "s054"):
        import gfx_bu
        gfx_bu.layer(c, t, sid)
    elif sid in ("s055", "s056", "s057", "s058", "s059", "s060", "s061"):
        import gfx_fc
        gfx_fc.layer(c, t, sid)
    elif sid in ("s062", "s063", "s064", "s065"):
        import gfx_out
        gfx_out.layer(c, t, sid)
    type_layer(c, t, shot)
    meter(c, t, shot)
    return c.im


def background(sid):
    """Shots that are graphics only (no plate): a black void."""
    return sid in ("s002", "s006", "s045")


def compose(sid, t, frame):
    """The whole graphics pass for one frame of the cut: frame-level effects, then the overlay."""
    if background(sid):
        frame = Image.new("RGB", frame.size, (6, 6, 6))
    if sid in ("s008", "s009", "s010", "s011", "s012", "s013", "s014"):
        import gfx_v1
        frame = gfx_v1.frame_fx(sid, t, frame)
    if sid == "s049":
        import gfx_bu
        frame = gfx_bu.frame_fx(sid, t, frame)
    out = Image.alpha_composite(frame.convert("RGBA"), layer(sid, t, frame.width, frame.height)).convert("RGB")
    if sid == "s065":  # the white box the film opened with becomes the white screen that ends it: over everything
        import gfx_out
        k = ramp(t, *gfx_out.WHITE_OUT)
        if k > 0:
            out = Image.blend(out, Image.new("RGB", out.size, (250, 249, 246)), k)
    return out
