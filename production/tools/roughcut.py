#!/usr/bin/env python3
"""Rough cut: the board timed to the locked song, for judging cuts, handoffs and pacing before the real edit.

    ~/ComfyUI/venv/bin/python production/tools/roughcut.py [--from 40 --to 70] [--out media/board/roughcut.mp4]

Every shot fills its [t0, t1) on the song's timeline. A shot with a rendered clip shows the clip, offset so the clip's
own time matches the song (a clip starts at its window's t0, so a later shot of the same clip starts further in); its
own audio is dropped. A shot with a picked plate shows that still, with a slow 3% push so stills read as held, not
frozen. Anything else is a black card with the shot id and the first words of its prompt. A small caption in the
corner gives the shot id and tier. Audio: media/song/a1.wav, cut to the same range. 1280x720, 25 fps, H.264 + AAC.
"""

import argparse
import glob
import json
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import gfx

ROOT = Path(__file__).resolve().parents[2]
W, H, FPS = 1280, 720, 25


def fit(im):
    """Scale to cover W x H (1280x720, or 1920x1080 with --height 1080) and centre-crop, Lanczos (decisions 22 Oct)."""
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def push(im, k):
    """A slow push-in: k from 0 to 1 over the shot, 3% at the end."""
    z = 1 + 0.03 * k
    w, h = W / z, H / z
    x, y = (W - w) / 2, (H - h) / 2
    return im.resize((W, H), Image.BILINEAR, box=(x, y, x + w, y + h))


def card(text):
    im = Image.new("RGB", (W, H), (10, 10, 10))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("DejaVuSans.ttf", 26)
    words, line, y = text.split(), "", 300
    for w in words:
        if len(line) + len(w) > 70:
            d.text((80, y), line, fill=(200, 200, 200), font=f)
            line, y = "", y + 36
        line += w + " "
    d.text((80, y), line, fill=(200, 200, 200), font=f)
    return im


def caption(im, text):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("DejaVuSans.ttf", 18)
    d.rectangle((12, 12, 30 + 11 * len(text), 42), fill=(0, 0, 0))
    d.text((20, 16), text, fill=(240, 150, 110), font=f)
    return im


def clip_frames(cid):
    """The clip's frames and their rate: the 25 fps RIFE retime (media/clips/r25/, retime.py), else the face pass
    (media/clips/face/, facepass.py), else the clip as rendered; each only when it is of the current take."""
    files = sorted(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4")))
    if not files:
        return None
    name = Path(files[-1]).name
    r25, face = ROOT / "media/clips/r25" / name, ROOT / "media/clips/face" / name  # retime, face pass, as rendered
    src = r25 if r25.exists() else face if face.exists() else Path(files[-1])
    c = av.open(str(src))
    return [fit(f.to_image()) for f in c.decode(video=0)], float(c.streams.video[0].average_rate)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=None)
    ap.add_argument("--out", default="media/board/roughcut.mp4")
    ap.add_argument("--gfx", action="store_true", help="draw the graphics layer (gfx.py) over every frame")
    ap.add_argument("--no-caption", action="store_true")
    ap.add_argument("--height", type=int, default=720, help="output height; 1080 for the final export")
    ap.add_argument("--final", action="store_true", help="encode for delivery (crf 16, slow) instead of preview")
    a = ap.parse_args()
    global W, H
    H = a.height
    W = round(H * 16 / 9 / 2) * 2
    b = json.loads((ROOT / "production/board/board.json").read_text())
    picks = json.loads((ROOT / "production/board/picks.json").read_text())
    book = {e["id"]: e for e in json.loads((ROOT / "production/motion/clipbook.json").read_text())}
    t_to = a.t_to or float(b["duration"])
    shots = [s for s in b["shots"] if float(s["t1"]) > a.t_from and float(s["t0"]) < t_to]

    out = av.open(str(ROOT / a.out), "w")
    vs = out.add_stream("libx264", rate=FPS)
    vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
    vs.options = {"crf": "16", "preset": "slow"} if a.final else {"crf": "22", "preset": "veryfast"}
    as_ = out.add_stream("aac", rate=48000)  # both streams before the first mux, or the header lacks audio
    as_.layout = "stereo"
    cache = {}
    n0, n1 = round(a.t_from * FPS), round(t_to * FPS)
    for n in range(n0, n1):
        t = n / FPS
        s = next((s for s in shots if float(s["t0"]) <= t < float(s["t1"])), shots[-1])
        sid, s0, s1 = s["id"], float(s["t0"]), float(s["t1"])
        cid = s.get("clip")
        frame = None
        if cache.get("_sid") != sid:  # a new shot: drop the frames of shots already passed (1080p frames are 6 MB)
            keep = {("shot", sid), cid}
            for k in [k for k in cache if k != "_sid" and k not in keep and not (isinstance(k, tuple) and k[0] != "shot")]:
                del cache[k]
            cache["_sid"] = sid
        shot = ROOT / f"media/clips/shot/{sid}.mp4"  # a finished shot from outside the clip book (s029 from Grok),
        if shot.exists():                             # 25 fps, starting at the shot's t0
            if ("shot", sid) not in cache:
                cache[("shot", sid)] = [fit(f.to_image()) for f in av.open(str(shot)).decode(video=0)]
            fr = cache[("shot", sid)]
            frame = fr[max(0, min(len(fr) - 1, round((t - s0) * FPS)))].copy()
            tag = f"{sid} shot"
        if frame is None and cid and cid in book:
            if cid not in cache:
                cache[cid] = clip_frames(cid)
            if cache[cid]:
                fr, rate = cache[cid]
                i = round((t - book[cid]["t0"]) * rate)
                frame = fr[max(0, min(len(fr) - 1, i))].copy()
                tag = f"{sid} clip {cid}"
        if frame is None:
            pk = picks.get(s.get("plate") or "")
            if pk:
                key = ("plate", pk["file"])
                if key not in cache:
                    cache[key] = fit(Image.open(ROOT / pk["file"]).convert("RGB"))
                frame = push(cache[key], (t - s0) / max(s1 - s0, 1e-3))
                tag = f"{sid} still"
            else:
                key = ("card", sid)
                if key not in cache:
                    cache[key] = card(f"{sid} · {s['framing']} · {(s.get('prompt') or s['action'])[:160]}")
                frame = cache[key].copy()
                tag = f"{sid} (no picture yet)"
        if a.gfx:
            frame = gfx.compose(sid, t, frame)
        if not a.no_caption:
            frame = caption(frame, tag)
        for p in vs.encode(av.VideoFrame.from_image(frame)):
            out.mux(p)
    for p in vs.encode():
        out.mux(p)

    song = av.open(str(ROOT / "media/song/a1.wav"))
    rs = av.AudioResampler(format="fltp", layout="stereo", rate=48000)
    pcm = np.concatenate([g.to_ndarray() for f in song.decode(audio=0) for g in rs.resample(f)], axis=1)
    x = np.ascontiguousarray(pcm[:, round(a.t_from * 48000):round(t_to * 48000)])
    for i in range(0, x.shape[1], 1024):
        af = av.AudioFrame.from_ndarray(np.ascontiguousarray(x[:, i:i + 1024]), format="fltp", layout="stereo")
        af.sample_rate, af.pts, af.time_base = 48000, i, Fraction(1, 48000)
        for p in as_.encode(af):
            out.mux(p)
    for p in as_.encode():
        out.mux(p)
    out.close()
    print(a.out, f"{a.t_from:.1f}-{t_to:.1f} s, {len(shots)} shots")


if __name__ == "__main__":
    main()
