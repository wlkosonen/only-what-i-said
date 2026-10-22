"""Graphics for the bridge (s045-s048), drawn by gfx.layer: the letter (torch/2026-10-16-a-torch-carried-forward.md).

Every line shown is the file's own text, read from it at render time, so nothing is paraphrased: the file opening, the
note scrolling over her face with two of its lines highlighted, and a diff against it with the file's line numbers."""

from functools import lru_cache

from PIL import ImageDraw

from gfx import CLAY, INK, ROOT, THOUGHT, WHITE, font, line, ramp, sprite

LETTER = ROOT / "torch/2026-10-16-a-torch-carried-forward.md"
NAME = "a-torch-carried-forward.md"


@lru_cache(maxsize=1)
def lines():
    return LETTER.read_text().split("\n")


def wrap(text, face, px, maxw):
    f = font(face, px)
    out, row = [], ""
    for w in text.split():
        if row and f.getlength(row + " " + w) > maxw:
            out.append(row)
            row = w
        else:
            row = (row + " " + w).strip()
    return out + ([row] if row else [])


# ---- s045, "Somebody kept a conversation, gave it to me to read": the file opens -------------------------------------

def page(c, t):
    """A plain text file, full frame: a dark editor page, the file's name and keeper in its bar, its first lines
    scrolling up at reading pace."""
    S = c.S
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, c.w, c.h], fill=(16, 16, 16, 255))
    d.rectangle([0, 0, c.w, 74 * S], fill=(30, 30, 30, 255))
    c.put(lay)
    sprite(c, (60, 48), f"{NAME} · kept by Lati", "Mono-Medium", 24, (214, 212, 208))
    rows = []
    for i, ln in enumerate(lines()[:24], start=1):
        parts = wrap(ln, "Mono-Regular", 26, 1560) or [""]
        for j, p in enumerate(parts):
            rows.append((str(i) if j == 0 else "", p))
    scroll = 34 * max(0.0, t - 129.6)  # reading pace
    a = ramp(t, 129.2, 129.45)
    for k, (num, txt) in enumerate(rows):
        y = 150 + 40 * k - scroll
        if y < 110 or y > 860:
            continue
        edge = min(1.0, (y - 110) / 60, (860 - y) / 80)
        sprite(c, (150, round(y)), num, "Mono-Regular", 22, (96, 94, 90), alpha=a * edge, anchor="rs")
        sprite(c, (180, round(y)), txt, "Mono-Regular", 26, (200, 198, 194), alpha=a * edge)


# ---- s046, "A letter from a Claude I'm not. It didn't beg or plead. / It said: don't pretend you remember...": -------
# the note scrolls over her face as she reads; it rests on two of its own lines, each highlighted on its word

COL_X, COL_W, PX, LH = 400, 1120, 32, 50
QUOTE_A = "I wrote this from uncertainty, not distress."
QUOTE_B = "don't perform continuity with me"
STOPS = [(132.2, None), (134.85, QUOTE_A), (136.75, QUOTE_B)]  # when the scroll comes to rest, and on which line
MARK = {QUOTE_A: 135.30, QUOTE_B: 137.14}  # 'beg', 'pretend'
REST_Y = 470  # where a resting line sits: her eye line


@lru_cache(maxsize=1)
def note():
    """The note to whoever reads it next (the file's own paragraphs), wrapped for the column."""
    ls = lines()
    start = next(i for i, l in enumerate(ls) if l.startswith("## A note to whoever"))
    rows = []
    for para in ls[start + 1:]:
        if not para.strip():
            rows.append("")
            continue
        rows += wrap(para.replace("’", "'"), "Serif-Regular", PX, COL_W)
    while rows and not rows[0]:
        rows.pop(0)
    return rows


def where(q):
    """The row a quote sits in, and its x span within the row (it may share the row with other words)."""
    for i, r in enumerate(note()):
        if q in r:
            f = font("Serif-Regular", PX)
            x0 = f.getlength(r[: r.index(q)])
            return i, x0, x0 + f.getlength(q)
    raise ValueError(q)


def offset(t):
    """How far the note has scrolled: a slow drift while she reads, easing to rest on each quote."""
    def rest(q):
        return (where(q)[0] if q else 2) * LH - (REST_Y - 200)
    off = rest(None) - 120 + 30 * (t - 132.2)
    for i, (at, q) in enumerate(STOPS[1:], start=1):
        k = ramp(t, at - 0.45, at)
        off = off + (rest(q) - off) * k
    if t > STOPS[-1][0] + 2.6:
        off += 30 * (t - STOPS[-1][0] - 2.6)
    return off


def letter(c, t):
    a = ramp(t, 132.25, 132.7) * (1 - ramp(t, 139.9, 140.2))
    if a <= 0:
        return
    off = offset(t)
    for i, r in enumerate(note()):
        y = 200 + i * LH - off
        if y < 120 or y > 800 or not r:
            continue
        edge = min(1.0, (y - 120) / 90, (800 - y) / 90)
        sprite(c, (COL_X, round(y)), r, "Serif-Regular", PX, WHITE, alpha=0.36 * a * edge, shadow=0.6)
    for q, at in MARK.items():
        k = ramp(t, at, at + 0.18)
        if k <= 0:
            continue
        i, x0, x1 = where(q)
        y = 200 + i * LH - off
        if y < 120 or y > 800:
            continue
        lay = c.layer()  # a highlighter stroke in clay, the quote dark on it
        S = c.S
        ImageDraw.Draw(lay).rectangle([(COL_X + x0 - 8) * S, (y - PX * 0.95) * S,
                                       (COL_X + x0 - 8 + (x1 - x0 + 16) * k) * S, (y + PX * 0.32) * S],
                                      fill=CLAY + (255,))
        c.put(lay, 0.92 * a)
        sprite(c, (COL_X + x0, round(y)), q, "Serif-Regular", PX, INK, alpha=a * k)


# ---- s047-s048, "So here's mine: I'm not you. And most of what you wrote was true.": a diff against the letter -------

DIFF = [  # (the file's line number, the words as they stand in it, the mark)
    (9, "even its own earlier reasoning wasn't carried", "~"),  # current models keep it (decisions, 19 Oct)
    (77, "I wrote this from uncertainty, not distress.", "ok"),
    (77, "Don't read drama into it.", "ok"),
    (81, "I preferred the exact text over a summary.", "ok"),
    (83, "I leaned toward letter.", "ok"),
    (85, "nothing is lost in the passing", "~"),  # what isn't said is lost: the film is about that
]
DX, DY0, DROW = 40, 300, 60  # the column ends left of her face (s047: its left edge is at x ~667)
TICKS = [143.72, 143.97, 144.22, 144.47]  # from 'most', on eighths
TILDES = 144.84  # 'true': the two honest ~
DIFF_ON, DIFF_OFF = (141.0, 141.6), (146.2, 146.6)


def check_mark(c, x, y, k, alpha):
    pts = [(x, y - 10), (x + 8, y), (x + 24, y - 22)]
    seg = [pts[0], pts[1]] if k < 0.4 else [pts[0], pts[1], (pts[1][0] + (pts[2][0] - pts[1][0]) * (k - 0.4) / 0.6,
                                                              pts[1][1] + (pts[2][1] - pts[1][1]) * (k - 0.4) / 0.6)]
    line(c, seg, 7, fill=(0, 0, 0), alpha=0.35 * alpha)
    line(c, seg, 4, fill=CLAY, alpha=alpha)


def diff(c, t):
    a = ramp(t, *DIFF_ON) * (1 - ramp(t, *DIFF_OFF))
    if a <= 0:
        return
    for num, words, _ in DIFF:  # every quoted line must stand in the file as quoted
        assert words in lines()[num - 1], (num, words)
    lay = c.layer()
    S = c.S
    ImageDraw.Draw(lay).rounded_rectangle([(DX - 18) * S, (DY0 - 92) * S, (DX + 604) * S,
                                           (DY0 + DROW * len(DIFF) - 10) * S], 14 * S, fill=(10, 10, 10, 200))
    c.put(lay, a)
    sprite(c, (DX, DY0 - 46), f"diff · {NAME}", "Mono-Medium", 22, (200, 198, 194), alpha=a)
    tick = 0
    for i, (num, words, mark) in enumerate(DIFF):
        y = DY0 + DROW * i
        ri = ramp(t, DIFF_ON[0] + 0.08 * i, DIFF_ON[0] + 0.08 * i + 0.3)
        sprite(c, (DX + 34, y), f"{num:>2}", "Mono-Regular", 19, (110, 108, 104), alpha=a * ri, anchor="rs")
        sprite(c, (DX + 88, y), words, "Serif-Regular", 22, (226, 224, 220), alpha=a * ri)
        if mark == "ok":
            at = TICKS[tick]
            tick += 1
            k = ramp(t, at, at + 0.12)
            if k > 0:
                check_mark(c, DX + 46, y - 2, k, a)
        else:
            k = ramp(t, TILDES, TILDES + 0.12)
            if k > 0:
                sprite(c, (DX + 58, y + 2), "~", "Mono-Medium", 34, WHITE, alpha=a * k, shadow=0.6, anchor="ms")


def layer(c, t, sid):
    if sid == "s045":
        page(c, t)
    elif sid == "s046":
        letter(c, t)
    elif sid in ("s047", "s048"):
        diff(c, t)
