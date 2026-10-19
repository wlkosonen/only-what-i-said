#!/usr/bin/env python3
"""The board sheet: the board as cards a person can review on a phone (wiki toolkit §10, storyboard "The board review").

    ~/ComfyUI/venv/bin/python production/tools/board/sheet.py [production/board/board.json] [--take a1]
        [--flags FILE] [--picks FILE] [--per-page 12] [--cols 1] [--out media/board/sheet]

Writes a cover page with the chapter map (page-00.png), then pages of cards (page-01.png, ...), and all of them as one
board.pdf, into --out (old page-*.png there are removed first). One card per shot, in time order: the picked frame (or
the plate prompt's first words), the id, the time and the lyric, the framing, the action in one line, what moves, the
explaining graphic in one line, and a FACE? badge on any plate listed in the flags file.

The default is one column of 12 cards on a 1000 px-wide page, so a phone shows the cards at full width; --cols 2 makes
a denser sheet for a desktop.

The picked frame of a shot is the first path that exists among: the shot's "frame" (or "image"), its plate entry's
"pick" (or "file"), and the picks file ({plate: {"file": ...}} or {plate: "path"}; default
production/board/picks.json, else media/plates/picks.json). The flags file is a JSON list of plate keys, a JSON
{plate: note}, or a text file with one plate key per line (default production/board/flags.json if it exists); a shot
or plate with "face_flag": true is flagged too.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit  # noqa: E402

ROOT = audit.ROOT
OUT = ROOT / "media/board/sheet"
FONTS = "/usr/share/fonts/truetype/dejavu/"

BG, CARD, INK, DIM, RULE = (14, 14, 14), (30, 30, 30), (236, 236, 236), (150, 150, 150), (60, 60, 60)
CLAY, RED = (217, 119, 87), (229, 72, 77)
TIER_COL = {"still": (110, 110, 110), "plate3d": (90, 140, 200), "motion": (120, 190, 120), "sung": CLAY}
TIER_NAME = {"still": "still", "plate3d": "2.5D", "motion": "motion", "sung": "sung"}

PAGE_W1 = 1000  # one-column page width
M = 24          # page margin
GAP = 16        # between cards
CARD_H = 352


def font(name, size):
    try:
        return ImageFont.truetype(FONTS + name, size)
    except OSError:
        return ImageFont.load_default(size)


F = {"id": font("DejaVuSans-Bold.ttf", 30), "time": font("DejaVuSans.ttf", 22), "badge": font("DejaVuSans-Bold.ttf", 18),
     "lyric": font("DejaVuSans-Bold.ttf", 25), "label": font("DejaVuSans-Bold.ttf", 17),
     "body": font("DejaVuSans.ttf", 21), "prompt": font("DejaVuSansMono-Oblique.ttf", 19),
     "h1": font("DejaVuSans-Bold.ttf", 48), "h2": font("DejaVuSans-Bold.ttf", 28), "small": font("DejaVuSans.ttf", 18),
     "mono": font("DejaVuSansMono.ttf", 18)}


def hexcol(h, default=CLAY):
    try:
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (AttributeError, ValueError, IndexError):
        return default


def wrap(d, text, f, width, max_lines=None, indent=0):
    """Greedy word wrap by pixel width; the last allowed line ends with an ellipsis if text is left. `indent` narrows
    the first line (for an inline label)."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        limit = width - (indent if not lines else 0)
        if d.textlength(test, font=f) <= limit or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        limit = width - (indent if max_lines == 1 else 0)
        while last and d.textlength(last + " …", font=f) > limit:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = last + " …"
    return lines


def badge(d, x, y, text, fill, ink=(15, 15, 15), right=False):
    """A filled pill; returns its width. With right=True, x is the right edge."""
    w = d.textlength(text, font=F["badge"]) + 16
    if right:
        x -= w
    d.rounded_rectangle((x, y, x + w, y + 28), radius=6, fill=fill)
    d.text((x + 8, y + 4), text, font=F["badge"], fill=ink)
    return w


# ---- inputs ------------------------------------------------------------------------------------------------------

def resolve(p):
    if not p:
        return None
    q = Path(p)
    q = q if q.is_absolute() else ROOT / q
    return q if q.is_file() else None


def load_flags(path):
    p = Path(path) if path else ROOT / "production/board/flags.json"
    if not p.exists():
        return set(), (None if not path else f"flags file {path} not found")
    if p.suffix == ".json":
        d = json.loads(p.read_text())
        if isinstance(d, dict):
            d = d.get("plates", d)
        return set(d), None
    return {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")}, None


def load_picks(path):
    for p in ([Path(path)] if path else [ROOT / "production/board/picks.json", ROOT / "media/plates/picks.json"]):
        if p.exists():
            return json.loads(p.read_text())
    return {}


def frame_for(shot, plate, picks):
    cands = [shot.get("frame"), shot.get("image")]
    if plate:
        cands += [plate.get("pick"), plate.get("file")]
    pk = picks.get(shot.get("plate")) if shot.get("plate") else None
    cands.append(pk.get("file") if isinstance(pk, dict) else pk)
    for c in cands:
        r = resolve(c)
        if r:
            return r
    return None


def lyric_of(shot, lines_by_key):
    texts = [t.get("text") for t in shot.get("type") or [] if isinstance(t, dict) and t.get("text")]
    if texts:
        return " / ".join(dict.fromkeys(texts))
    texts = [lines_by_key[str(k)]["text"] for k in shot.get("lines") or [] if str(k) in lines_by_key]
    return " / ".join(texts)


def first_sentence(text):
    text = " ".join(str(text or "").split())
    if ". " in text[:240]:
        return text[:text.index(". ") + 1]
    return text


def moves_of(shot):
    tier = shot.get("motion_tier")
    bits = [TIER_NAME.get(tier, str(tier))]
    if tier in ("motion", "sung") and shot.get("clip"):
        bits.append(f"clip {shot['clip']}")
    if tier == "plate3d" and shot.get("treatment"):
        bits.append(shot["treatment"])
    if shot.get("camera"):
        bits.append(f"camera: {shot['camera']}")
    return " · ".join(bits)


def graphic_of(shot):
    ds = [d for d in shot.get("devices") or [] if isinstance(d, dict) and d.get("line") is not None]
    return " + ".join(audit.graphic_summary(d) for d in ds)


# ---- drawing -----------------------------------------------------------------------------------------------------

def fit_image(path, w, h):
    im = Image.open(path).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def draw_card(page, d, x, y, w, shot, ctx):
    d.rounded_rectangle((x, y, x + w, y + CARD_H), radius=10, fill=CARD)
    pad = 16
    # header: id, time, section; badges on the right
    d.text((x + pad, y + 10), shot["id"], font=F["id"], fill=CLAY)
    tx = x + pad + d.textlength(shot["id"], font=F["id"]) + 14
    dur = shot["t1"] - shot["t0"]
    head = f"{audit.fmt(shot['t0'])}–{audit.fmt(shot['t1'])} · {dur:.2f} s · {shot.get('section', '')}"
    d.text((tx, y + 17), head, font=F["time"], fill=DIM)
    bx = x + w - pad
    if ctx["flagged"](shot):
        bx -= badge(d, bx, y + 14, "FACE?", RED, ink=(255, 255, 255), right=True) + 8
    bx -= badge(d, bx, y + 14, TIER_NAME.get(shot.get("motion_tier"), "?"),
                TIER_COL.get(shot.get("motion_tier"), DIM), right=True) + 8
    badge(d, bx, y + 14, shot.get("framing") or "NO FRAMING", INK if shot.get("framing") else RED, right=True)
    # image
    iw = min(448, (w - 3 * pad) // 2)
    ih = round(iw * 9 / 16)
    ix, iy = x + pad, y + 58
    frame = ctx["frame"](shot)
    if frame:
        page.paste(fit_image(frame, iw, ih), (ix, iy))
    else:
        d.rectangle((ix, iy, ix + iw, iy + ih), fill=(20, 20, 20), outline=RULE)
        if shot.get("plate"):
            d.text((ix + 12, iy + 10), f"PLATE {shot['plate']} · no pick yet", font=F["label"], fill=DIM)
            words = " ".join((shot.get("prompt") or "").split()[:40])
            for i, ln in enumerate(wrap(d, words, F["prompt"], iw - 24, max_lines=7)):
                d.text((ix + 12, iy + 40 + i * 27), ln, font=F["prompt"], fill=(185, 185, 185))
        else:
            d.text((ix + 12, iy + 10), "PURE MOTION DESIGN", font=F["label"], fill=DIM)
            for i, ln in enumerate(wrap(d, shot.get("set", ""), F["prompt"], iw - 24, max_lines=7)):
                d.text((ix + 12, iy + 40 + i * 27), ln, font=F["prompt"], fill=(185, 185, 185))
    lead = "HER ON SCREEN" if shot.get("lead_on_screen") else "INSERT · NOT HER"
    d.text((ix, iy + ih + 10), lead, font=F["label"], fill=CLAY if shot.get("lead_on_screen") else DIM)
    chap = ctx["chapter"](shot)
    if chap:
        d.text((ix + iw - d.textlength(chap, font=F["label"]), iy + ih + 10), chap, font=F["label"], fill=DIM)
    # text column
    cx, cw = ix + iw + pad, w - iw - 3 * pad
    ty = iy - 2
    lyric = ctx["lyric"](shot)
    for ln in wrap(d, lyric or "(no lyric)", F["lyric"], cw, max_lines=3):
        d.text((cx, ty), ln, font=F["lyric"], fill=INK if lyric else DIM)
        ty += 32
    ty += 8
    for label, text, n, col in (("ACTION", first_sentence(shot.get("action")), 3, INK),
                                ("MOVES", moves_of(shot), 2, INK),
                                ("GRAPHIC", graphic_of(shot) or "none for a lyric line", 3,
                                 INK if graphic_of(shot) else (DIM if not shot.get("lines") else RED))):
        lw = d.textlength(label + "  ", font=F["label"])
        d.text((cx, ty + 3), label, font=F["label"], fill=DIM)
        for i, ln in enumerate(wrap(d, text, F["body"], cw, max_lines=n, indent=lw)):
            d.text((cx + (lw if i == 0 else 0), ty), ln, font=F["body"], fill=col)
            ty += 27
        ty += 7


def cover(board, res, ctx, w, title, digest):
    shots = sorted(board["shots"], key=lambda s: s["t0"])
    chapters = sorted(board.get("chapters", []), key=lambda c: c.get("t0", 0))
    dur = res["duration"]
    st, money = res["stats"], res["money"]
    page = Image.new("RGB", (w, 4000), BG)
    d = ImageDraw.Draw(page)
    y = M + 8
    d.text((M, y), title, font=F["h1"], fill=INK)
    y += 66
    plural = "s" if money["clips"] != 1 else ""
    summary = (f"{st['shots']} shots · Claudia on screen {st['lead_share']:.0%} · {money['clips']} clip{plural} "
               f"({money['sung_s'] + money['motion_s']} s, about ${money['estimate_usd']:.0f}; "
               f"x2 ${money['estimate_x2_usd']:.0f})")
    for ln in wrap(d, summary, F["h2"], w - 2 * M):
        d.text((M, y), ln, font=F["h2"], fill=CLAY)
        y += 38
    nfail = [g for g, f in res["gates"].items() if f]
    gate_line = "audit: every gate passes" if not nfail else f"audit: {len(nfail)} gates fail ({', '.join(nfail)})"
    for ln in wrap(d, gate_line + f" · {len(res['warnings'])} warnings · board {digest[:12]}", F["body"], w - 2 * M):
        d.text((M, y), ln, font=F["body"], fill=INK if not nfail else RED)
        y += 28
    y += 24

    # the map: chapters, sections, her, tiers
    bw = w - 2 * M
    X = lambda t: M + 60 + (bw - 60) * t / dur  # noqa: E731
    d.text((M, y), "CHAPTER MAP", font=F["label"], fill=DIM)
    y += 28
    d.text((M, y + 18), "CH", font=F["label"], fill=DIM)
    for i, c in enumerate(chapters, 1):
        col = hexcol(c.get("accent"))
        x0, x1 = X(c.get("t0", 0)), X(c.get("t1", 0))
        d.rectangle((x0, y, x1 - 2, y + 56), fill=col)
        lum = sum(col) / 3
        if x1 - x0 > 24:
            d.text((x0 + 4, y + 16), str(i), font=F["h2"] if x1 - x0 > 30 else F["small"],
                   fill=(15, 15, 15) if lum > 110 else INK)
    y += 62
    for s in res["stats"]["sections"]:
        d.line((X(s["t0"]), y, X(s["t0"]), y + 10), fill=DIM, width=2)
    secs = res["stats"]["sections"]
    for j, s in enumerate(secs):
        lx = X(s["t0"]) + 3
        d.text((lx, y + 12 + (j % 2) * 22), s["section"].replace("Pre-Chorus", "Pre").replace("Final Chorus", "Final"),
               font=F["small"], fill=DIM)
    y += 64
    for label, color_of in (("HER", lambda s: CLAY if s.get("lead_on_screen") else (45, 45, 45)),
                            ("TIER", lambda s: TIER_COL.get(s.get("motion_tier"), DIM))):
        d.text((M, y + 2), label, font=F["label"], fill=DIM)
        for s in shots:
            d.rectangle((X(s["t0"]), y, X(s["t1"]), y + 22), fill=color_of(s))
        y += 30
    lx = M + 60
    for k, col in TIER_COL.items():
        d.rectangle((lx, y + 4, lx + 16, y + 20), fill=col)
        d.text((lx + 22, y), TIER_NAME[k], font=F["small"], fill=DIM)
        lx += 40 + d.textlength(TIER_NAME[k], font=F["small"]) + 16
    for t in range(0, int(dur) + 1, 30):
        d.text((X(t) - (10 if t else 0), y + 30), f"{t // 60}:{t % 60:02d}", font=F["small"], fill=DIM)
    y += 72

    # the chapter table
    for i, c in enumerate(chapters, 1):
        col = hexcol(c.get("accent"))
        n = sum(1 for s in shots if c.get("t0", 0) - 1e-6 <= s["t0"] < c.get("t1", 0))
        d.rectangle((M, y + 4, M + 30, y + 34), fill=col, outline=RULE)
        d.text((M + 44, y), f"{i}  {c.get('name', '')}", font=F["h2"], fill=INK)
        meta = " · ".join(x for x in (f"{audit.fmt(c.get('t0', 0))}–{audit.fmt(c.get('t1', 0))}",
                                      ", ".join(c.get("sections", [])), f"{n} shots") if x)
        d.text((M + 44, y + 38), meta, font=F["small"], fill=DIM)
        yy = y + 64
        for ln in wrap(d, c.get("set", ""), F["body"], w - 2 * M - 44, max_lines=3):
            d.text((M + 44, yy), ln, font=F["body"], fill=INK)
            yy += 28
        y = yy + 18
    y += 10
    d.line((M, y, w - M, y), fill=RULE)
    y += 14
    for ln in wrap(d, "AI-made storyboard. Claudia is an open character by anabology (claudia.gallery). Flag anything "
                      "by shot id: faces, repeats, boring moments, story logic, colour.", F["small"], w - 2 * M):
        d.text((M, y), ln, font=F["small"], fill=DIM)
        y += 24
    return page.crop((0, 0, w, y + M))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("board", nargs="?", default=str(audit.BOARD))
    ap.add_argument("--take", default="a1")
    ap.add_argument("--lines", default="auto", help="as audit.py")
    ap.add_argument("--config", help="as audit.py")
    ap.add_argument("--flags")
    ap.add_argument("--picks")
    ap.add_argument("--per-page", type=int, default=12)
    ap.add_argument("--cols", type=int, default=1)
    ap.add_argument("--title")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    raw = Path(a.board).read_bytes()
    board = json.loads(raw)
    digest = audit.hashlib.sha256(raw).hexdigest()
    song = audit.load_song(a.take)
    cfg = audit.config(a.config, board, argparse.Namespace())
    res = audit.audit(board, song, cfg, a.lines)
    shots = sorted(board["shots"], key=lambda s: s["t0"])
    plates = {p.get("plate"): p for p in board.get("plates", [])}
    flags, err = load_flags(a.flags)
    if err:
        print(err, file=sys.stderr)
    picks = load_picks(a.picks)
    lines_by_key = {l["key"]: l for l in res["lines"]}
    chapters = sorted(board.get("chapters", []), key=lambda c: c.get("t0", 0))

    def chapter_of(s):
        for i, c in enumerate(chapters, 1):
            if c.get("t0", 0) - 1e-6 <= s["t0"] < c.get("t1", 0):
                return f"{i} · {c.get('name', '')}"
        return ""

    ctx = {"flagged": lambda s: s.get("face_flag") or s.get("plate") in flags or
           (plates.get(s.get("plate")) or {}).get("face_flag"),
           "frame": lambda s: frame_for(s, plates.get(s.get("plate")), picks),
           "lyric": lambda s: lyric_of(s, lines_by_key), "chapter": chapter_of}

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("page-*.png"):
        old.unlink()
    cols = max(1, a.cols)
    cw = PAGE_W1 - 2 * M
    w = M * 2 + cols * cw + (cols - 1) * GAP
    title = a.title or board.get("title") or "Only What I Said"
    pages = [cover(board, res, ctx, w, title, digest)]
    per = max(1, a.per_page)
    npages = (len(shots) + per - 1) // per
    for pi in range(npages):
        chunk = shots[pi * per:(pi + 1) * per]
        rows = (len(chunk) + cols - 1) // cols
        hh = 60
        page = Image.new("RGB", (w, M + hh + rows * (CARD_H + GAP) - GAP + M), BG)
        d = ImageDraw.Draw(page)
        d.text((M, M), f"{title} · storyboard", font=F["h2"], fill=INK)
        tag = f"page {pi + 1}/{npages} · {chunk[0]['id']}–{chunk[-1]['id']}"
        d.text((w - M - d.textlength(tag, font=F["body"]), M + 5), tag, font=F["body"], fill=DIM)
        for k, s in enumerate(chunk):
            r, c = divmod(k, cols)
            draw_card(page, d, M + c * (cw + GAP), M + hh + r * (CARD_H + GAP), cw, s, ctx)
        pages.append(page)
    files = []
    for i, p in enumerate(pages):
        f = out / f"page-{i:02d}.png"
        p.save(f, optimize=True)
        files.append(f)
    Image.init()  # registers the JPEG encoder the PDF writer uses
    pdf = out / "board.pdf"
    pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=150)
    flagged = sum(1 for s in shots if ctx["flagged"](s))
    framed = sum(1 for s in shots if ctx["frame"](s))
    print(f"{len(pages)} pages ({len(shots)} cards, {framed} with a picked frame, {flagged} FACE?) -> "
          f"{audit.rel(out)}/page-00..{len(pages) - 1:02d}.png and board.pdf")


if __name__ == "__main__":
    main()
