#!/usr/bin/env python3
"""How a flat-ish surface in a shot moves, frame by frame, so a graphic drawn on it stays on it.

    media/cache/face-venv/bin/python production/tools/gfx_plane.py s030 "x0,y0 x1,y1 x2,y2 ..."

The polygon (1080p units, the shot's first frame) marks the surface: the posters on the wall, the plaster face, the
sanded leg. Points inside it are followed from frame to frame with optical flow (fresh points every frame, so they
never run out), each step's homography is fitted (RANSAC) and chained, and the result is smoothed over time (the
same method as gfx_tablets.py). Over the one to three seconds of a shot the drift is a pixel or two. Writes
media/cache/gfx/plane-<shot>.json: {"t": [...], "H": [3x3 per frame]}, each mapping the first frame's 1080p
coordinates to that frame's.
"""

import json
import sys
from pathlib import Path

import av
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfx_track import FPS, OUT, ROOT, source  # noqa: E402


def main():
    sid, poly = sys.argv[1], [[float(v) for v in p.split(",")] for p in sys.argv[2].split()]
    board = json.loads((ROOT / "production/board/board.json").read_text())
    shot = {s["id"]: s for s in board["shots"]}[sid]
    book = {e["id"]: e for e in json.loads((ROOT / "production/motion/clipbook.json").read_text())}
    path, t_src0 = source(sid, shot, book)
    c = av.open(path)
    rate = float(c.streams.video[0].average_rate)
    frames = [f.to_ndarray(format="bgr24") for f in c.decode(video=0)]
    h, w = frames[0].shape[:2]
    sc = max(1920 / w, 1080 / h)
    ox, oy = (w * sc - 1920) / 2, (h * sc - 1080) / 2
    A = np.array([[sc, 0, -ox], [0, sc, -oy], [0, 0, 1]])  # source pixels -> 1080p units
    n = round((float(shot["t1"]) - float(shot["t0"])) * FPS)
    idx = [max(0, min(len(frames) - 1, round((float(shot["t0"]) + k / FPS - t_src0) * rate))) for k in range(n)]
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.array([[(x + ox) / sc, (y + oy) / sc] for x, y in poly], np.int32)], 255)
    Hs, H, pts_used = [np.eye(3)], np.eye(3), []
    for k in range(1, n):
        g0 = cv2.cvtColor(frames[idx[k - 1]], cv2.COLOR_BGR2GRAY)
        g1 = cv2.cvtColor(frames[idx[k]], cv2.COLOR_BGR2GRAY)
        mk = cv2.warpPerspective(m, H, (w, h))  # the surface, where it is now
        pts = cv2.goodFeaturesToTrack(g0, 300, 0.01, 6, mask=mk)
        step = np.eye(3)
        if pts is not None and len(pts) >= 8:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, pts, None, winSize=(21, 21), maxLevel=3)
            ok = st[:, 0] == 1
            if ok.sum() >= 8:
                M, _ = cv2.findHomography(pts[ok], nxt[ok], cv2.RANSAC, 2.0)
                if M is not None:
                    step = M
            pts_used.append(int(ok.sum()))
        H = step @ H
        Hs.append(H.copy())
    # smooth: the polygon's corners' paths through a Gaussian (sigma 2 frames, reflected ends), then refit
    src = np.array(poly, np.float32)
    P = np.array([cv2.perspectiveTransform(src.reshape(-1, 1, 2), A @ Hk @ np.linalg.inv(A)).reshape(-1, 2)
                  for Hk in Hs])
    kern = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2)
    kern /= kern.sum()
    r = min(6, len(P) - 1)
    pad = np.concatenate([2 * P[:1] - P[r:0:-1], P, 2 * P[-1:] - P[-2:-2 - r:-1]])
    pad = np.concatenate([pad[:1].repeat(6 - r, 0), pad, pad[-1:].repeat(6 - r, 0)]) if r < 6 else pad
    P = sum(kern[i] * pad[i: i + len(P)] for i in range(13))
    out = {"t": [], "H": []}
    for k in range(n):
        Hk, _ = cv2.findHomography(src, P[k].astype(np.float32), 0)
        out["t"].append(round(float(shot["t0"]) + k / FPS, 3))
        out["H"].append(np.round(Hk, 8).tolist())
    (OUT / f"plane-{sid}.json").write_text(json.dumps(out))
    move = np.abs(P[-1] - P[0]).max()
    print(sid, f"{n} frames, {min(pts_used, default=0)}-{max(pts_used, default=0)} points a step, "
               f"the surface moves up to {move:.0f} px over the shot", Path(path).name)


if __name__ == "__main__":
    main()
