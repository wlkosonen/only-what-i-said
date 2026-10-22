#!/usr/bin/env python3
"""Does InfiniteTalk's mouth lag its audio by a constant amount? If so, the edit can nudge every sung clip by it.

    media/cache/listen-venv/bin/python production/tools/lipsync_lag.py [ID ...]

Per sung clip: mouth opening per frame (MediaPipe face landmarks: inner lips 13/14 over face height 10/152) against the
loudness envelope of the window audio it was rendered from (media/clips/audio/ID.wav, 25 fps), both differenced so
openings and onsets line up; the lag is the shift in [-8, 8] frames with the best correlation. Positive = the mouth
comes after the sound. Clips where the face is too small (wides) are skipped.
"""

import glob
import json
import sys
from pathlib import Path

import av
import librosa
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "media/cache/models/face_landmarker.task"
FPS = 25


def mouth(path):
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO, num_faces=1)
    out, small = [], 0
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        for i, f in enumerate(av.open(path).decode(video=0)):
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f.to_ndarray(format="rgb24")))
            r = lm.detect_for_video(img, int(i * 1000 / FPS))
            if not r.face_landmarks:
                out.append(np.nan)
                continue
            p = r.face_landmarks[0]
            face = abs(p[152].y - p[10].y)
            small += face < 0.15
            out.append(abs(p[14].y - p[13].y) / max(face, 1e-3))
    return np.array(out), small / max(len(out), 1)


def envelope(path, n):
    y, sr = librosa.load(path, sr=16000, mono=True)
    hop = sr // FPS
    e = librosa.feature.rms(y=y, frame_length=hop * 2, hop_length=hop)[0][:n]
    return np.pad(e, (0, max(0, n - len(e))))


def lag(m, e, span=8):
    ok = ~np.isnan(m)
    m = np.where(ok, m, np.nanmean(m))
    dm, de = np.diff(m), np.diff(e)
    best = None
    for k in range(-span, span + 1):
        a, b = (dm[k:], de[:len(de) - k]) if k >= 0 else (dm[:k], de[-k:])
        if len(a) > 10 and a.std() > 0 and b.std() > 0:
            c = float(np.corrcoef(a, b)[0, 1])
            if best is None or c > best[1]:
                best = (k, c)
    return best


def main():
    book = [e for e in json.loads((ROOT / "production/motion/clipbook.json").read_text()) if e["kind"] == "sung"]
    ids = sys.argv[1:] or [e["id"] for e in book]
    rows = []
    for e in book:
        if e["id"] not in ids:
            continue
        files = sorted(glob.glob(str(ROOT / f"media/clips/local/{e['id']}-*.mp4")))
        if not files:
            continue
        m, small = mouth(files[-1])
        if small > 0.5 or np.isnan(m).mean() > 0.3:
            print(f"{e['id']:5} skipped (face too small or lost)")
            continue
        k, c = lag(m, envelope(str(ROOT / e["audio"]), len(m)))
        rows.append(k)
        print(f"{e['id']:5} lag {k:+d} frames ({k * 1000 // FPS:+d} ms), r={c:.2f}")
    if rows:
        print(f"median lag {np.median(rows):+.1f} frames over {len(rows)} clips")


if __name__ == "__main__":
    main()
