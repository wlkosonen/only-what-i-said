#!/usr/bin/env python3
"""Where her face is, frame by frame, for the graphics that attach to her (leader lines, the face matte, labels).

    media/cache/face-venv/bin/python production/tools/gfx_track.py s011 s012 ...

For each shot it reads exactly the frames the cut shows (roughcut.py's choice: a finished shot in media/clips/shot/,
else the clip's 25 fps retime, face pass or render, offset by the clip's window start) and finds her face with
InsightFace (detector, 5 key points, 106 landmarks; a 2x upscale for small faces; a black border round a face too
close to be found). Coordinates are converted to the
graphics' 1080p frame (the cut scales each source to cover 16:9 and centre-crops), smoothed over time, and written to
media/cache/gfx/track-<shot>.json as {"t": [...], "bbox": [...], "kps": [...], "lmk": [...]} (None where no face).
"""

import glob
import json
import sys
from pathlib import Path

import av
import cv2
import numpy as np
from insightface.app import FaceAnalysis

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "media/cache/gfx"
FPS = 25


def source(sid, shot, book):
    sp = ROOT / f"media/clips/shot/{sid}.mp4"
    if sp.exists():
        return str(sp), float(shot["t0"])
    cid = shot.get("clip")
    files = sorted(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4"))) if cid else []
    if not files:
        return None, None
    name = Path(files[-1]).name
    for d in ("media/clips/r25", "media/clips/face"):
        if (ROOT / d / name).exists():
            return str(ROOT / d / name), book[cid]["t0"]
    return files[-1], book[cid]["t0"]


def main():
    board = json.loads((ROOT / "production/board/board.json").read_text())
    S = {s["id"]: s for s in board["shots"]}
    book = {e["id"]: e for e in json.loads((ROOT / "production/motion/clipbook.json").read_text())}
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"],
                       allowed_modules=["detection", "landmark_2d_106"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    OUT.mkdir(parents=True, exist_ok=True)
    for sid in sys.argv[1:]:
        shot = S[sid]
        path, t_src0 = source(sid, shot, book)
        if not path:
            print(sid, "no moving source")
            continue
        c = av.open(path)
        rate = float(c.streams.video[0].average_rate)
        frames = [f.to_ndarray(format="bgr24") for f in c.decode(video=0)]
        h, w = frames[0].shape[:2]
        sc = max(1920 / w, 1080 / h)
        ox, oy = (w * sc - 1920) / 2, (h * sc - 1080) / 2
        to = lambda p: [[float(x * sc - ox), float(y * sc - oy)] for x, y in p]
        res = {"t": [], "bbox": [], "kps": [], "lmk": []}
        prev = None
        n = round((float(shot["t1"]) - float(shot["t0"])) * FPS)
        for k in range(n):
            t = float(shot["t0"]) + k / FPS
            i = max(0, min(len(frames) - 1, round((t - t_src0) * rate)))
            img = frames[i]
            up = 2 if w < 1500 else 1
            fs = app.get(cv2.resize(img, None, fx=up, fy=up) if up > 1 else img)
            pad = 0
            if not fs:  # an extreme close-up (s015: eyes and bangs, chin out of frame): give the face room to be a face
                pad = w // 2
                fs = app.get(cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0)))
                up = 1
            res["t"].append(round(t, 3))
            if not fs:
                for key in ("bbox", "kps", "lmk"):
                    res[key].append(None)
                continue
            f = max(fs, key=lambda q: (q.bbox[2] - q.bbox[0]) * (q.bbox[3] - q.bbox[1]))
            cur = np.vstack([f.bbox.reshape(2, 2), f.kps, f.landmark_2d_106]) / up - pad
            prev = cur if prev is None or np.abs(cur - prev).max() > 0.2 * (cur[1, 0] - cur[0, 0]) else 0.6 * prev + 0.4 * cur
            p = to(prev)
            res["bbox"].append(p[0] + p[1])
            res["kps"].append(p[2:7])
            res["lmk"].append(p[7:])
        (OUT / f"track-{sid}.json").write_text(json.dumps(res))
        found = sum(1 for b in res["bbox"] if b)
        print(sid, f"face in {found}/{n} frames", Path(path).name)


if __name__ == "__main__":
    main()
