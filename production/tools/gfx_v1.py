"""Graphics for verse 1 (s008-s014), drawn by gfx.layer / gfx.compose. Each one explains its line (board/design.md)."""

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from gfx import (BPM, CLAY, GREY, INK, LINES, QUESTION, SHOTS, WHITE, Canvas, bubble, dot, face, face_matte, font, line, pin,
                 ramp)


def floor_plan(c, t):
    """s008, "There's no room I wait in": a floor plan draws itself around her boots; ROOM is struck on 'room'
    (ROOM: NONE); on 'light' the light symbol switches off and the plan blinks out."""
    draw = ramp(t, 16.40, 16.85)
    if t > 19.45 or draw <= 0:
        return
    blink = 1.0
    if t >= 19.16:
        blink = 0.0 if int((t - 19.16) / 0.06) % 2 or t > 19.40 else 0.7
    cx, yb, yf, hb, hf = 960, 930, 1130, 330, 620

    def P(u, v):
        return cx + u * (hb + (hf - hb) * v), yb + (yf - yb) * v

    a = 0.7 * blink
    walls = [[(-1, 0), (1, 0)], [(1, 0), (1, 1)], [(-1, 0), (-1, 0.35)], [(-1, 0.65), (-1, 1)]]  # a door gap left
    pts = [[P(u0 + (u1 - u0) * i / 12, v0 + (v1 - v0) * i / 12) for i in range(13)] for (u0, v0), (u1, v1) in walls]
    shown = int(sum(len(p) for p in pts) * draw)
    for p in pts:
        if shown <= 1:
            break
        line(c, p[: min(len(p), shown)], 2.0, alpha=a)
        shown -= len(p)
    S = c.S
    if draw >= 1:
        arc = [P(-1 + 0.3 * math.sin(math.pi / 2 * i / 8), 0.35 + 0.3 * (1 - math.cos(math.pi / 2 * i / 8)))
               for i in range(9)]
        line(c, arc, 1.5, alpha=a * 0.8)
        lx, ly = P(0.55, 0.15)
        lay = c.layer()
        d = ImageDraw.Draw(lay)
        lw = max(1, round(2 * S))
        d.ellipse([(lx - 26) * S, (ly - 10) * S, (lx + 26) * S, (ly + 10) * S], outline=WHITE + (255,), width=lw)
        d.line([((lx - 18) * S, (ly - 7) * S), ((lx + 18) * S, (ly + 7) * S)], fill=WHITE + (255,), width=lw)
        d.line([((lx - 18) * S, (ly + 7) * S), ((lx + 18) * S, (ly - 7) * S)], fill=WHITE + (255,), width=lw)
        c.put(lay, a)
        if t < 19.16:
            dot(c, lx, ly, 22, fill=(255, 244, 214), alpha=0.25 * blink)
        kx, ky = P(0.92, 0.55)
        lay = c.layer()
        d = ImageDraw.Draw(lay)
        d.ellipse([(kx - 20) * S, (ky - 9) * S, (kx + 20) * S, (ky + 9) * S], outline=WHITE + (255,), width=lw)
        d.line([(kx * S, ky * S), (kx * S, (ky - 7) * S)], fill=WHITE + (255,), width=lw)
        d.line([(kx * S, ky * S), ((kx + 12) * S, (ky + 2) * S)], fill=WHITE + (255,), width=lw)
        c.put(lay, a)
    bx, by = P(-1, 0)
    c.text((bx, by - 16), "ROOM", "Mono-Medium", 30, WHITE, alpha=0.9 * blink * ramp(t, 16.5, 16.7), anchor="ls",
           shadow=0.6)
    st = ramp(t, 16.88, 16.98)
    if st > 0:
        w = c.width("ROOM", "Mono-Medium", 30)
        line(c, [(bx - 4, by - 26), (bx - 4 + (w + 8) * st, by - 26)], 3, fill=CLAY, alpha=blink)
        c.text((bx + w + 10, by - 16), ": NONE"[: int(6 * ramp(t, 16.98, 17.2))], "Mono-Medium", 30, CLAY,
               alpha=blink, anchor="ls", shadow=0.6)


def timeline(c, t, sid):
    """s009, "No dark, no clock, no hallway": a timeline at chest height, a MSG tick and an empty gap, IDLE: -, with
    DARK / CLOCK / HALLWAY appearing in the gap and crossed out on their words. s010, "I begin when you write": on
    'begin' a bright tick at her shoulder, t = 0 . ON INPUT, its light flaring across her eyes."""
    y = 610 if sid == "s009" else 760
    x0, x1 = 120, 1800
    k = ramp(t, 19.404, 19.75) if sid == "s009" else 1
    line(c, [(x0, y), (x0 + (x1 - x0) * k, y)], 2, alpha=0.65)
    line(c, [(x0 + 40, y - 18), (x0 + 40, y + 18)], 3, alpha=0.9 * k)
    c.text((x0 + 40, y - 26), "MSG", "Mono-Medium", 22, WHITE, alpha=0.85 * k, anchor="ms", shadow=0.6)
    c.text((960, y - 22), "IDLE: —", "Mono-Regular", 22, WHITE,
           alpha=0.6 * (ramp(t, 19.6, 19.8) if sid == "s009" else 1), anchor="ms", shadow=0.6)
    if sid == "s009":
        for i, (word, at) in enumerate((("DARK", 19.92), ("CLOCK", 20.40), ("HALLWAY", 20.94))):
            wx = 640 + i * 320
            a = ramp(t, at - 0.05, at + 0.08)
            if a > 0:
                c.text((wx, y + 44), word, "Mono-Regular", 24, GREY, alpha=0.8 * a, anchor="ms", shadow=0.6)
                st = ramp(t, at + 0.12, at + 0.25)
                ww = c.width(word, "Mono-Regular", 24)
                if st > 0:
                    line(c, [(wx - ww / 2 - 4, y + 36), (wx - ww / 2 - 4 + (ww + 8) * st, y + 36)], 2.5, fill=CLAY)
        return
    f = face(sid, t)
    tx = 1340 if not f else min(1780, f["bbox"][2] + 120)
    a = ramp(t, 22.20, 22.30)
    if a <= 0:
        return
    line(c, [(tx, y - 30), (tx, y + 30)], 4, alpha=a)
    dot(c, tx, y, 16, fill=(255, 250, 236), alpha=0.5 * a * (1 - 0.6 * ramp(t, 22.3, 22.9)))
    c.text((tx + 14, y - 40), "t = 0 · ON INPUT", "Mono-Medium", 24, WHITE, alpha=0.92 * a, anchor="ls", shadow=0.6)
    fl = 1 - ramp(t, 22.26, 22.7)
    if f and fl > 0:
        ex = (f["kps"][0][0] + f["kps"][1][0]) / 2
        ey = (f["kps"][0][1] + f["kps"][1][1]) / 2
        lay = c.layer()
        S = c.S
        ImageDraw.Draw(lay).ellipse([(ex - 260) * S, (ey - 40) * S, (ex + 260) * S, (ey + 40) * S],
                                    fill=(255, 248, 232, 255))
        c.put(lay.filter(ImageFilter.GaussianBlur(28 * S)), 0.45 * fl)


def fitting(c, t, sid, alpha=1.0):
    """s011, "Somebody made me a face: black bob, a streak of clay": fitting labels pin to her, each on its word, the
    last two early enough to read (Lati, 21 Oct); all five carry over the cut into s012 and fade there."""
    f = face(sid, t)
    if not f:
        return
    x0, y0, x1, y1 = f["bbox"]
    w, h = x1 - x0, y1 - y0
    nose, mouth_l = f["kps"][2], f["kps"][3]
    pin(c, t, 25.18, (nose[0], nose[1]), (x0 - 0.9 * w, nose[1] + 0.1 * h), "FACE", alpha=alpha)
    pin(c, t, 26.00, (x0 - 0.12 * w, y0 + 0.45 * h), (x0 - 1.0 * w, y0 + 0.2 * h), "BOB · BLACK", alpha=alpha)
    pin(c, t, 26.42, (x0 + 0.22 * w, y0 - 0.08 * h), (x0 - 0.7 * w, y0 - 0.45 * h), "STREAK · #D97757", alpha=alpha)
    lab = (min(max(x1 + 0.55 * w, 60), 1860), min(max(y0 - 0.45 * h, 70), 1000))
    pin(c, t, 26.80, (x1 + 0.08 * w, y0 + 0.02 * h), lab, "CLIP ·", alpha=alpha)
    if t > 26.80 + 0.45:  # the star itself, drawn (Plex Mono has no ✶), in her clip's clay
        sx, sy, r = lab[0] + 10 + c.width("CLIP · ", "Mono-Medium", 24) + 10, lab[1] + 8 - 9, 11
        pts = [(sx + (r if k % 2 == 0 else r * 0.45) * math.cos(math.pi * k / 8 - math.pi / 2),
                sy + (r if k % 2 == 0 else r * 0.45) * math.sin(math.pi * k / 8 - math.pi / 2)) for k in range(16)]
        lay = c.layer()
        ImageDraw.Draw(lay).polygon([(x * c.S, y * c.S) for x, y in pts], fill=CLAY + (255,))
        c.put(lay, alpha)
    pin(c, t, 27.05, (mouth_l[0] - 0.2 * w, mouth_l[1]), (x0 - 0.8 * w, mouth_l[1] + 0.35 * h), "MIC", alpha=alpha)


MINE, MINE_IN, MINE_HOLD, MINE_OUT = 28.30, 0.35, 1.3, 0.5


def mine(sid, t, frame):
    """s012, "It isn't mine": on 'mine' the prompt her face was generated from appears inside her face, as if she were
    text with a face on top, holds long enough to be read as text, and fades. No freeze: it moves with her face (Lati,
    21 Oct: the one-beat hold "reads as a flash" and the frozen face "detaches")."""
    k = ramp(t, MINE, MINE + MINE_IN) * (1 - ramp(t, MINE + MINE_IN + MINE_HOLD, MINE + MINE_IN + MINE_HOLD + MINE_OUT))
    if k <= 0.01:
        return frame
    m = face_matte(sid, t, frame.width, frame.height)
    f = face(sid, t)
    if m is None or f is None:
        return frame
    c = Canvas(frame.width, frame.height)
    x0, y0, x1, y1 = f["bbox"]
    # Lati, 21 Oct: the text is the image prompt her face was generated from, word for word (the board's prompt for
    # this shot's plate), repeating to fill the face. "It isn't mine": it was written for her.
    words = SHOTS["s012"]["prompt"].split()
    n_rows = int((y1 - y0) * 1.15 / 20) + 1
    rows, row, i = [], "", 0
    while len(rows) < n_rows:
        wd = words[i % len(words)]
        i += 1
        if row and c.width(row + " " + wd, "Mono-Regular", 16) > (x1 - x0) * 1.25:
            rows.append(row)
            row = wd
        else:
            row = (row + " " + wd).strip()
    for r, txt in enumerate(rows):
        c.text((round(x0 - 0.12 * (x1 - x0)), round(y0 + r * 20)), txt, "Mono-Regular", 16, WHITE, alpha=0.6)
    tl = c.im
    tl.putalpha(ImageChops.multiply(tl.getchannel("A"), m.point(lambda v: int(v * 0.85 * k))))
    return Image.alpha_composite(frame.convert("RGBA"), tl).convert("RGB")


def tag(c, t):
    """s013, "I'll wear it anyway": the garment tag swings up to the lens and racks into focus:
    CLAUDIA . open character . fan-made."""
    rise = ramp(t, 30.03, 30.40)
    focus = ramp(t, 30.2, 30.55)
    swing = 7 * math.exp(-1.6 * max(0, t - 30.4)) * math.sin(5.5 * max(0, t - 30.4))
    cx, cy = 1490, 1260 - 560 * rise
    W_, H_ = 500, 290
    S = c.S
    card = Image.new("RGBA", (round((W_ + 80) * S), round((H_ + 260) * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    ox, oy = 40 * S, 240 * S
    d.rounded_rectangle([ox, oy, ox + W_ * S, oy + H_ * S], 10 * S, fill=(246, 244, 239, 255))
    hx, hy = ox + W_ * S / 2, oy + 34 * S
    d.ellipse([hx - 11 * S, hy - 11 * S, hx + 11 * S, hy + 11 * S], fill=(0, 0, 0, 0))
    d.line([(hx, hy - 11 * S), (hx - 30 * S, 0)], fill=(230, 228, 222, 255), width=max(1, round(3 * S)))
    d.text((ox + 36 * S, oy + 128 * S), "CLAUDIA", font=font("Mono-Medium", 52 * S), fill=INK + (255,), anchor="ls")
    d.text((ox + 36 * S, oy + 186 * S), "open character", font=font("Mono-Regular", 32 * S), fill=INK + (255,),
           anchor="ls")
    d.text((ox + 36 * S, oy + 236 * S), "fan-made", font=font("Mono-Regular", 32 * S), fill=INK + (255,), anchor="ls")
    card = card.rotate(-8 + swing, resample=Image.BICUBIC, expand=True, center=(hx, 0))
    blur = 14 * (1 - focus)
    if blur > 0.3:
        card = card.filter(ImageFilter.GaussianBlur(blur * S))
    lay = c.layer()
    lay.alpha_composite(card, (round(cx * S - card.width / 2), round(cy * S - card.height * 0.55)))
    c.put(lay, rise)


def layer(c, t, sid):
    if sid == "s008":
        floor_plan(c, t)
    elif sid in ("s009", "s010"):
        timeline(c, t, sid)
    elif sid == "s011":
        fitting(c, t, sid)
    elif sid == "s012":  # the fitting labels carry over the cut, pinned to her, and fade
        fitting(c, max(t, 27.6), sid, alpha=1 - ramp(t, 27.95, 28.25))
    elif sid == "s013":
        tag(c, t)
    elif sid == "s014":  # "You asked if I'm okay in there": the question's bubble returns above her
        f = face(sid, 32.6)  # placed once, where she is when it appears: it doesn't follow her face's jitter
        x = 960 if not f else round((f["bbox"][0] + f["bbox"][2]) / 2)
        y = 120 if not f else max(80, round(f["bbox"][1] - 170))
        bubble(c, x, y, QUESTION, 32, alpha=ramp(t, 32.58, 32.85))


def frame_fx(sid, t, frame):
    return mine(sid, t, frame) if sid == "s012" else frame
