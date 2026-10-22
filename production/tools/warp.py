#!/usr/bin/env python3
"""Lip sync by time warp: a Grok take where she sings our words on her own timing, re-timed word by word onto our
vocal (Lati's idea, 20 Oct: "since movements are very small, apart from lipsync, can that be sped up to match our
vocal?").

    1. media/cache/listen-venv/bin/python -c ...   (whisper word times of the take's own audio -> WORDS.json)
    2. HIP_VISIBLE_DEVICES=0 ~/ComfyUI/venv/bin/python production/tools/warp.py SHOT TAKE.mp4 WORDS.json OUT.mp4

The take's words are matched to the song's words (media/song/analysis/a1/words.json) inside the shot's span, in order.
Each matched pair (song time, take time) is an anchor; a monotone curve through the anchors (PCHIP) maps every
output frame time of the shot to a time in the take, so each word's mouth lands on its word and the speed changes
smoothly between words. Frames between the take's own frames are RIFE 4.9 in-betweens (retime.py's model). Before the
first anchor and after the last, the take runs at real speed (clamped to the take). A first word whisper
couldn't place takes the take's audio onset; anchors that force a speed outside 0.5x-2x are dropped.
Output: the shot's exact frame count at 25 fps, ready for media/clips/shot/. With a .fit.json from fit.py
instead of word times, the map is one even speed and offset fitted to her mouth (the usual case once the
takes are prompted to our tempo).
"""

import difflib
import json
import re
import sys
from pathlib import Path

import av
import numpy as np
import torch
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from retime import model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FPS = 25


def norm(w):
    return re.sub(r"[^a-z']", "", w.lower())


def onset(take):
    """When the take's singing starts: the first moment its audio rises above 15% of its loudest (smoothed)."""
    c = av.open(take)
    rs = av.AudioResampler(format="flt", layout="mono", rate=16000)
    y = np.concatenate([g.to_ndarray().ravel() for f in c.decode(audio=0) for g in rs.resample(f)])
    hop = 160
    e = np.sqrt(np.convolve(y[: len(y) // hop * hop].reshape(-1, hop).__pow__(2).mean(axis=1), np.ones(5) / 5, "same"))
    return float(np.argmax(e > 0.15 * e.max()) * hop / 16000)


def prune(pairs, lo=0.5, hi=2.0):
    """Whisper's word times on singing are rough; an anchor that forces a speed outside [lo, hi] between its
    neighbours is almost always its error. Drop the worst one until every segment is inside the range."""
    pairs = sorted(pairs)
    while len(pairs) > 2:
        sp = [(pairs[i + 1][1] - pairs[i][1]) / max(pairs[i + 1][0] - pairs[i][0], 1e-3) for i in range(len(pairs) - 1)]
        bad = [i for i, v in enumerate(sp) if not lo <= v <= hi]
        if not bad:
            break
        i = max(bad, key=lambda i: abs(np.log(max(sp[i], 1e-3))))
        # drop the end of the offending segment that isn't the first or last anchor, preferring the inner one
        j = i + 1 if i + 1 < len(pairs) - 1 else i
        if j == 0:
            j = 1
        print(f"  drop anchor {pairs[j][2]} (speed {sp[i]:.2f}x)")
        pairs.pop(j)
    return pairs


def anchors(shot, take_words, take=None):
    words = [w for w in json.loads((ROOT / "media/song/analysis/a1/words.json").read_text())["words"] if w["t1"]]
    song = [w for w in words if shot["t0"] - 0.4 <= w["t0"] < shot["t1"]]
    a = [norm(w["w"]) for w in song]
    b = [norm(w[0]) for w in take_words]
    pairs = []
    for blk in difflib.SequenceMatcher(None, a, b).get_matching_blocks():
        for k in range(blk.size):
            t = take_words[blk.b + k][1]
            if t <= 0.05:  # whisper clamps an onset it can't find to 0.0: use the take's audio onset, if it's the first
                if blk.b + k != 0 or take is None:
                    continue
                t = onset(take)
            pairs.append((song[blk.a + k]["t0"], t, song[blk.a + k]["w"]))
    last = song[-1], take_words[-1]
    if norm(last[0]["w"]) == norm(last[1][0]):
        pairs.append((last[0]["t1"], last[1][2], "end of " + last[0]["w"]))
    return pairs


def main():
    sid, take, words_p, out_p = sys.argv[1:5]
    S = {s["id"]: s for s in json.loads((ROOT / "production/board/board.json").read_text())["shots"]}
    shot = {"t0": float(S[sid]["t0"]), "t1": float(S[sid]["t1"])}
    if words_p.endswith(".fit.json"):  # one even speed and offset, fitted to her mouth (fit.py)
        fit = json.loads(Path(words_p).read_text())
        xs = np.array([shot["t0"], shot["t1"]])
        ys = fit["offset"] + fit["speed"] * (xs - shot["t0"])
        curve = lambda t: fit["offset"] + fit["speed"] * (t - shot["t0"])
    else:
        pairs = prune(anchors(shot, json.loads(Path(words_p).read_text()), take))
        for p in pairs:
            print(f"  song {p[0]:7.2f}  take {p[1]:5.2f}  {p[2]}")
        xs, ys = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
        curve = PchipInterpolator(xs, ys, extrapolate=False)
    lo_rate = hi_rate = 1.0  # before the first word and after the last, the take runs at its own speed

    src = av.open(take)
    rate = float(src.streams.video[0].average_rate)
    frames = [f.to_ndarray(format="rgb24") for f in src.decode(video=0)]
    h, w = frames[0].shape[:2]
    m = model()
    ph, pw = (32 - h % 32) % 32, (32 - w % 32) % 32
    t = lambda a: torch.nn.functional.pad(torch.from_numpy(a).permute(2, 0, 1)[None].float().div(255),
                                          (0, pw, 0, ph), mode="replicate").half().cuda()
    n = round((shot["t1"] - shot["t0"]) * FPS)
    out = av.open(out_p, "w")
    vs = out.add_stream("libx264", rate=FPS)
    vs.width, vs.height, vs.pix_fmt, vs.options = w, h, "yuv420p", {"crf": "14", "preset": "slow"}
    speeds = []
    with torch.inference_mode():
        for k in range(n):
            ts = shot["t0"] + k / FPS
            g = float(curve(ts)) if xs[0] <= ts <= xs[-1] else \
                (ys[0] + (ts - xs[0]) * lo_rate if ts < xs[0] else ys[-1] + (ts - xs[-1]) * hi_rate)
            p = min(max(g * rate, 0), len(frames) - 1)
            i, f = int(p), p - int(p)
            if f < 1e-3 or i + 1 >= len(frames):
                img = frames[i]
            else:
                mid = m(t(frames[i]), t(frames[i + 1]), timestep=f, scale_list=[8, 4, 2, 1], training=False,
                        fastmode=True, ensemble=False)
                img = mid[0, :, :h, :w].clamp(0, 1).float().mul(255).round().byte().permute(1, 2, 0).cpu().numpy()
            speeds.append(g)
            for pk in vs.encode(av.VideoFrame.from_ndarray(np.ascontiguousarray(img), format="rgb24")):
                out.mux(pk)
    for pk in vs.encode():
        out.mux(pk)
    out.close()
    d = np.diff(speeds) * FPS
    print(f"{sid}: {n} frames, take {speeds[0]:.2f}-{speeds[-1]:.2f} s, speed {d.min():.2f}x-{d.max():.2f}x")


if __name__ == "__main__":
    main()
