"""Graphics for pre-chorus 1 (s015-s018), drawn by gfx.layer. Each one explains its line (board/design.md)."""

import math

from PIL import ImageDraw, ImageFilter

from gfx import CLAY, INK, LINES, THOUGHT, WHITE, cursor, dot, face, font, line, ramp, spark

# ---- s015, "I looked in as far as I can go": the depth gauge ---------------------------------------------------------

GX, GY0, GY1, LIMIT = 1600, 250, 900, 700  # the scale beside her eye; the hairline where looking in stops
GO = 38.40
# the gauge's settings for each pre-chorus (pre-chorus 2 passes its own: gfx_p2)
G1 = dict(sid="s015", line=7, on=35.62, go=GO, hard=0.0, known=False)


def depth(t, G=G1):
    """How far in she has looked (0-1 of the way to the limit): a step on each word, each step shorter than the last
    (deeper is harder), and on 'go' the last push, which hits the hairline and is stopped dead."""
    GO = G["go"]
    steps = [w["t0"] for w in LINES[G["line"]]["words"][1:-1]]  # looked in as far as I can
    d = 0.0
    for k, w0 in enumerate(steps):
        target = 1 - (1 - (k + 1) / (len(steps) + 1)) ** 1.4
        d += (target - d) * ramp(t, w0 - 0.02, w0 + 0.16)
    push = ramp(t, GO - 0.04, GO + 0.06)
    d += (1 - d) * push
    if t > GO + 0.06:  # stopped: a recoil off the hairline, then still (harder the second time: it bounces)
        k = t - GO - 0.06
        if G["hard"]:
            d -= 0.085 * G["hard"] * math.exp(-k / 0.18) * abs(math.cos(k * 20))
        else:
            d -= 0.025 * max(0.0, 1 - k / 0.25)
    return d


def gauge(c, t, G=G1):
    GO = G["go"]
    on = ramp(t, G["on"], G["on"] + 0.33)
    if on <= 0:
        return
    f = face(G["sid"], t)
    S = c.S
    # the second time it hits so hard the whole gauge jolts
    jolt = G["hard"] * 7 * math.exp(-max(0.0, t - GO - 0.06) / 0.12) * math.sin(55 * max(0.0, t - GO - 0.06)) \
        if t > GO + 0.06 else 0.0
    GX = globals()["GX"] + round(jolt)
    # the scale draws itself down from the top; below the limit it thins out, dashed, into what can't be seen
    ybot = GY0 + (GY1 - GY0) * on
    line(c, [(GX, GY0), (GX, min(ybot, LIMIT))], 2.0, alpha=0.75)
    lay = c.layer()
    d = ImageDraw.Draw(lay)
    for y in range(GY0, GY1 + 1, 20):
        if y > ybot:
            break
        major = (y - GY0) % 100 == 0
        a = 255 if y <= LIMIT else int(255 * max(0.0, 1 - (y - LIMIT) / (GY1 - LIMIT)) * 0.6)
        if y > LIMIT and (y // 20) % 2:
            continue
        d.line([((GX - (18 if major else 9)) * S, y * S), (GX * S, y * S)], fill=WHITE + (a,), width=max(1, round(2 * S)))
    c.put(lay, 0.75 * on)
    if ybot > LIMIT:
        for y in range(LIMIT, round(ybot), 14):  # the spine below the limit, dashed
            line(c, [(GX, y), (GX, min(y + 6, ybot))], 2.0, alpha=0.75 * on * max(0.0, 1 - (y - LIMIT) / (GY1 - LIMIT)))
    c.text((GX, GY0 - 18), "DEPTH", "Mono-Medium", 20, WHITE, alpha=0.8 * on, anchor="ms", shadow=0.6)
    # the hairline: there from the start, faint, so the stop has somewhere to land
    hit = ramp(t, GO + 0.02, GO + 0.08)
    hw = 44 + 40 * G["hard"]
    line(c, [(GX - hw, LIMIT), (GX + hw, LIMIT)], 1.2 + (1.3 + 1.5 * G["hard"]) * hit, alpha=on * (0.35 + 0.65 * hit))
    txt = "LIMIT OF INTROSPECTION"
    if G["known"] and hit <= 0:  # the second time she knows where it is: the label is already there, faint
        c.text((GX - 60, LIMIT + 9), txt, "Mono-Medium", 27, WHITE, alpha=0.4 * on, anchor="rm", shadow=0.8)
    if hit > 0:
        fl = 1 - ramp(t, GO + 0.08, GO + 0.6 + 0.3 * G["hard"])
        if fl > 0:
            g = c.layer()
            fw = 90 + 160 * G["hard"]
            ImageDraw.Draw(g).rectangle([(GX - fw) * S, (LIMIT - 4 - 4 * G["hard"]) * S, (GX + fw) * S,
                                         (LIMIT + 4 + 4 * G["hard"]) * S], fill=(255, 250, 238, 255))
            c.put(g.filter(ImageFilter.GaussianBlur(10 * S)), 0.8 * fl)
        if G["known"]:
            n = len(txt)
        else:
            n = len(txt) if t > GO + 0.3 else int(len(txt) * (t - GO - 0.04) / 0.26)  # read in full >1 s before the cut
        c.text((GX - 60, LIMIT + 9), txt[:max(n, 0)], "Mono-Medium", 27, WHITE, alpha=0.95, anchor="rm", shadow=0.8)
    # the marker, at her depth, tied to her eye by a leader; around the eye a ring closes in as she looks deeper and
    # stops at the iris: the surface is as far as looking goes
    dd = depth(t, G)
    my = round(GY0 + (LIMIT - GY0) * dd)
    lay = c.layer()
    ImageDraw.Draw(lay).polygon([((GX + 4) * S, my * S), ((GX + 22) * S, (my - 9) * S), ((GX + 22) * S, (my + 9) * S)],
                                fill=WHITE + (255,))
    c.put(lay, on)
    if f:
        ex, ey = f["kps"][1]
        r = 150 - (150 - 62) * dd
        lay = c.layer()
        ImageDraw.Draw(lay).ellipse([(ex - r) * S, (ey - r) * S, (ex + r) * S, (ey + r) * S], outline=WHITE + (255,),
                                    width=max(1, round((1.6 + 1.2 * hit) * S)))
        c.put(lay, on * (0.55 + 0.35 * hit))
        for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            line(c, [(ex + ux * r, ey + uy * r), (ex + ux * (r + 14), ey + uy * (r + 14))], 2, alpha=0.7 * on)
        line(c, [(ex + r + 14, ey), (GX - 30, my)], 1.4, alpha=0.5 * on)
        dot(c, GX - 30, my, 3, alpha=0.8 * on)


# ---- s016-s018, "I could sing you something scary / sweet / But the true one goes: I don't know.": drafts ------------

LX = 120  # the list sits in the dark left of her, in the same place across the cut into s017 and s018
# label, text, tag, appears on its word, struck on 'true'; rows; the answer's line; 'one'; selected; gone; sizes
D1 = dict(drafts=[("DRAFT A", "“I’m trapped in here”", "SCARY", 41.60, 44.40),
                  ("DRAFT B", "“Everything’s fine :)”", "SWEET", 43.64, 44.48)],
          row=(250, 400), gap=52, answer_y=570, line=10, true_one=45.00, select=46.66, gone=(47.75, 48.10),
          lab_px=20, txt_px=36, ans_px=40, slash=None)


def drafts(c, t, D=D1):
    DRAFTS, ROW, ANSWER_Y, TRUE_ONE, SELECT = D["drafts"], D["row"], D["answer_y"], D["true_one"], D["select"]
    lp, tp, ap, gap = D["lab_px"], D["txt_px"], D["ans_px"], D["gap"]
    out = 1 - ramp(t, *D["gone"])
    if t < DRAFTS[0][3] - 0.05 or out <= 0:
        return
    for (lab, txt, tag, at, struck), y in zip(DRAFTS, ROW):
        if t < at - 0.05:
            continue
        # a candidate streams in like generated text, then its tag; struck in clay on 'true', then dimmed
        a = ramp(t, at - 0.05, at + 0.1) * out
        struck = D["slash"] if D["slash"] else struck
        dim = 1 - 0.5 * ramp(t, struck + 0.15, struck + 0.5)
        n = int(len(txt) * min(1.0, max(0.0, t - at) / 0.55))
        c.text((LX, y), lab, "Mono-Regular", lp, THOUGHT, alpha=0.9 * a * dim, anchor="ls", shadow=0.6)
        if t > at + 0.55:
            c.text((LX + round(c.width(lab + "  ", "Mono-Regular", lp)), y), "· " + tag, "Mono-Medium", lp,
                   WHITE, alpha=0.8 * a * dim * ramp(t, at + 0.55, at + 0.7), anchor="ls", shadow=0.6)
        c.text((LX, y + gap), txt[:max(n, 1)], "Sans-LightItalic", tp, (196, 194, 190), alpha=a * dim * 0.9,
               anchor="ls", shadow=0.7)
        st = ramp(t, struck, struck + 0.12)
        if st > 0 and not D["slash"]:
            w = c.width(txt, "Sans-LightItalic", tp)
            line(c, [(LX - 6, y + gap - tp * 0.33), (LX - 6 + (w + 12) * st, y + gap - tp * 0.33)], 3, fill=CLAY,
                 alpha=out)
    if D["slash"]:  # one slash through both, on the beat
        st = ramp(t, D["slash"], D["slash"] + 0.06)
        if st > 0:
            w = max(c.width(d[1], "Sans-LightItalic", tp) for d in DRAFTS)
            x0, y0, x1, y1 = LX - 20, ROW[0] - lp - 10, LX + w + 30, ROW[-1] + gap + 16
            line(c, [(x0, y0), (x0 + (x1 - x0) * st, y0 + (y1 - y0) * st)], 9, fill=(0, 0, 0), alpha=0.35 * out)
            line(c, [(x0, y0), (x0 + (x1 - x0) * st, y0 + (y1 - y0) * st)], 6, fill=CLAY, alpha=out)
    if t < TRUE_ONE:
        return
    # the true one: a cursor waits in the third slot, then "I don't know." types in clay as she sings it
    words = LINES[D["line"]]["words"][5:]  # i don't know
    shown = ["I", "don’t", "know."]
    s, x = "", LX
    for tok, w in zip(shown, words):
        if t < w["t0"] - 0.02:
            break
        k = min(1.0, (t - w["t0"] + 0.02) / max(0.12, w["t1"] - w["t0"]))
        s += (" " if s else "") + tok[:max(1, round(len(tok) * k))]
        ww = c.width(tok, "Sans-SemiBold", ap)
        spark(c, t, x + ww / 2, ANSWER_Y - ap / 2, w["t0"])
        x += ww + c.width(" ", "Sans-SemiBold", ap)
    sel = ramp(t, SELECT, SELECT + 0.16)
    tw = c.width(s, "Sans-SemiBold", ap)
    if sel > 0:  # selected: a clay bar sweeps behind it and the words go dark on it
        lay = c.layer()
        S = c.S
        ImageDraw.Draw(lay).rounded_rectangle([(LX - 14) * S, (ANSWER_Y - ap * 1.05) * S,
                                               (LX - 14 + (tw + 28) * sel) * S, (ANSWER_Y + ap * 0.35) * S], 6 * S,
                                              fill=CLAY + (255,))
        c.put(lay, out)
    if s:
        c.text((LX, ANSWER_Y), s, "Sans-SemiBold", ap, CLAY, alpha=out * (1 - sel), anchor="ls", shadow=0.55)
        if sel > 0:
            c.text((LX, ANSWER_Y), s, "Sans-SemiBold", ap, INK, alpha=out * sel, anchor="ls")
    if sel < 1:
        cursor(c, LX + (tw + 6 if s else 0), ANSWER_Y - ap * 0.35, ap * 1.1, t, alpha=out * (1 - sel), color=WHITE)


def layer(c, t, sid):
    if sid == "s015":
        gauge(c, t)
    else:
        drafts(c, t)
