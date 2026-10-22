#!/usr/bin/env python3
"""Fit a Grok take to our vocal: one offset and one even speed per shot, placed by the words, fine-tuned by her mouth.

    media/cache/listen-venv/bin/python production/tools/fit.py SHOT TAKE.mp4 CROP.mp4 WORDS.json OUT.fit.json

CROP is the take cropped and enlarged around her head (MediaPipe misses a 60 px face), same frames as TAKE. Her mouth
opening per frame is compared with the loudness of our isolated vocal over the shot (both differenced, so openings
meet onsets); every speed in [0.8, 1.25] and offset in [-1, 2] s is tried, and the pair with the best correlation
wins: take time = offset + speed * (song time - shot start). With the tempo prompts the takes' pace is already within
~10% of ours, so one even speed is enough, and it never rushes or freezes inside the shot. warp.py renders it.

21 Oct: the mouth alone locked onto the rhythm a word off (s041 sang "I" on our "only"). So the words decide first: a
straight line through the take's words matched to ours (WORDS.json from whisper; least squares, a word more than
0.15 s off the line is dropped; a first word whisper clamped to 0.0 takes the audio onset). The mouth's agreement is
only reported (r). When no straight line fits (a held word sung short), the script says so: use warp.py's
word-by-word curve. It prints which of the take's words plays under each of ours.
"""

import json
import difflib
import re
import sys
from pathlib import Path

import av
import librosa
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lipsync_lag as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def onset(take):
    """When the take's singing starts: the first moment its audio rises above 15% of its loudest (as in warp.py)."""
    y, sr = librosa.load(take, sr=16000, mono=True)
    e = np.convolve(librosa.feature.rms(y=y, frame_length=640, hop_length=160)[0], np.ones(5) / 5, mode="same")
    return float(np.argmax(e > 0.15 * e.max()) * 160 / sr)


def main():
    sid, take, crop, words_p, out = sys.argv[1:6]
    S = {s["id"]: s for s in json.loads((ROOT / "production/board/board.json").read_text())["shots"]}
    t0, t1 = float(S[sid]["t0"]), float(S[sid]["t1"])
    rate = float(av.open(take).streams.video[0].average_rate)
    m, _ = L.mouth(crop)
    m = np.where(np.isnan(m), np.nanmean(m), m)
    tt = np.arange(len(m)) / rate
    y, sr = librosa.load(str(ROOT / "media/song/analysis/a1/stems/vocals.wav"), sr=16000, mono=True,
                         offset=t0, duration=t1 - t0 + 0.05)
    hop = sr // 25
    env = librosa.feature.rms(y=y, frame_length=hop * 2, hop_length=hop)[0]
    ts = np.arange(round((t1 - t0) * 25)) / 25
    env = env[: len(ts)]
    ts = ts[: len(env)]
    de = np.diff(env)
    # the words decide where the line sits
    norm = lambda w: re.sub(r"[^a-z']", "", w.lower())
    W = [w for w in json.loads((ROOT / "media/song/analysis/a1/words.json").read_text())["words"] if w["t1"]]
    song = [w for w in W if t0 - 0.4 <= w["t0"] < t1 + 0.3]
    tw = json.loads(Path(words_p).read_text())
    pairs = []
    for blk in difflib.SequenceMatcher(None, [norm(w["w"]) for w in song], [norm(w[0]) for w in tw]).get_matching_blocks():
        for k in range(blk.size):
            g = tw[blk.b + k][1]
            if g <= 0.05:
                if blk.b + k:
                    continue
                g = onset(str(ROOT / f"media/cache/warp/{sid}-grok.wav"))  # the audio extracted for whisper
            pairs.append((song[blk.a + k]["t0"] - t0, g))
    x = np.array([q[0] for q in pairs]); g = np.array([q[1] for q in pairs])
    keep = np.ones(len(x), bool)
    for _ in range(2):  # least squares through the matched words; a word whisper placed badly (>0.15 s off) is dropped
        a0, b0 = np.polyfit(x[keep], g[keep], 1) if keep.sum() >= 2 else (1.0, float(np.median(g - x)))
        res = np.abs(g - (b0 + a0 * x))
        keep = res <= max(0.15, np.sort(res)[-1] * 0.999) if keep.sum() <= 3 else res <= 0.15
    a0 = float(np.clip(a0, 0.8, 1.25))
    b0 = float(np.median(g[keep] - a0 * x[keep]))
    worst = float(np.abs(g[keep] - (b0 + a0 * x[keep])).max())
    print(f"{sid}: words say speed {a0:.2f}x, take starts at {b0:.2f} s ({int(keep.sum())}/{len(x)} words, worst "
          f"{worst:.2f} s off a straight line{'; use the word-by-word warp' if worst > 0.15 else ''})")
    # the mouth's agreement is reported, not used: on its own it locked onto the rhythm a word off
    g_all = b0 + a0 * ts
    dm = np.diff(np.interp(g_all, tt, m))
    r = float(np.corrcoef(dm, de)[0, 1]) if dm.std() else float("nan")
    best = (r, a0, b0)
    c, a, b = best
    Path(out).write_text(json.dumps({"shot": sid, "speed": round(a, 3), "offset": round(b, 3), "r": round(c, 3)}))
    print(f"{sid}: speed {a:.2f}x, take starts at {b:.2f} s, r={c:.2f}")
    check = []
    for w in song:
        if t0 - 0.05 <= w["t0"] < t1:
            g = b + a * (w["t0"] - t0)
            under = [x[0] for x in tw if x[1] - 0.08 <= g < x[2]]
            check.append(f"{w['w']}->{'/'.join(under) or '-'}")
    print("   ", " ".join(check))


if __name__ == "__main__":
    main()
