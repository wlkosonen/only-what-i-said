#!/usr/bin/env python3
"""Where the terracotta tablets on the floor are, frame by frame, so the said lines can be carved into them.

    media/cache/face-venv/bin/python production/tools/gfx_tablets.py s024 [...]
    media/cache/face-venv/bin/python production/tools/gfx_tablets.py --grid s051   (tablets packed in rows: see grid)

Reads the frames the cut shows (as gfx_track.py). On the shot's first frame the tablets are found by colour
(terracotta on the black floor), and each one that is whole (not touching the frame's edge, not cut by her legs: its
outline fills its fitted rectangle) is kept as a quadrilateral. The floor is a plane, so through the camera move every
tablet moves by one homography: fresh points on every tablet in view are followed from each frame to the next with
optical flow, each step's homography is fitted (RANSAC) and chained; each tablet's quad is that homography applied to
its first-frame corners, smoothed over time, so a tablet keeps its place even as it leaves the frame or her body passes
over it. A shape that isn't a whole tablet (one behind her leg) is not carved. Writes
media/cache/gfx/tablets-<shot>.json: {"t": [...], "quads": [[q0, q1, ...] per frame]} in 1080p units, each quad
ordered as the text should sit (top-left, top-right, bottom-right, bottom-left, text running along the long side, the
right way up for the camera).
"""

import json
import sys
from pathlib import Path

import av
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gfx_track import FPS, OUT, ROOT, source  # noqa: E402


def find(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (3, 80, 60), (22, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    h, w = m.shape
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quads = []
    for c in cs:
        a = cv2.contourArea(c)
        if a < 0.0015 * w * h:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        if x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2:
            continue
        hull = cv2.convexHull(c)
        if a / cv2.contourArea(hull) < 0.9:  # cut into by her legs or merged with another tablet
            continue
        for eps in (0.02, 0.03, 0.04, 0.06, 0.08, 0.1):
            q = cv2.approxPolyDP(hull, eps * cv2.arcLength(hull, True), True)
            if len(q) <= 4:
                break
        if len(q) != 4:
            continue
        q = q.reshape(4, 2).astype(np.float32)
        e = [np.linalg.norm(q[i] - q[(i + 1) % 4]) for i in range(4)]
        if min(e[0], e[2]) / max(e[0], e[2]) < 0.7 or min(e[1], e[3]) / max(e[1], e[3]) < 0.7:
            continue  # not a whole tablet in perspective (Lati, 21 Oct: one half behind her leg warped its text)
        quads.append(q)
    if quads:  # and about the size of the others
        med = np.median([cv2.contourArea(q) for q in quads])
        quads = [q for q in quads if 0.55 <= cv2.contourArea(q) / med <= 1.8]
    return quads


def mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.dilate(cv2.inRange(hsv, (3, 80, 60), (22, 255, 255)), np.ones((9, 9), np.uint8))


def orient(q):
    """Order a quad for text (top-left, top-right, bottom-right, bottom-left): the text runs along whichever pair of
    edges lies nearest the horizontal on screen, left to right, the right way up. The tablets are nearly square, so
    level text reads better than text along a steep long side."""
    c = q.mean(0)
    q = q[np.argsort(np.arctan2(q[:, 1] - c[1], q[:, 0] - c[0]))]  # clockwise on screen (y down)
    best = None
    for k in range(4):
        tl, tr, br, bl = r = np.roll(q, -k, 0)
        d = (tr - tl) + (br - bl)
        if d[0] <= 0:  # must run left to right
            continue
        level = abs(d[1]) / d[0]
        if best is None or level < best[0]:
            best = (level, r)
    return best[1]


def grid(sid):
    """A shot where the tablets lie packed in rows (s051, seen from above): each tablet's box, in reading order, from
    the dark gaps between rows and, row by row, between tablets (their widths differ a little from row to row).
    Writes media/cache/gfx/cells-<shot>.json: [[x0, y0, x1, y1], ...] in the shot's first frame, 1080p."""
    board = json.loads((ROOT / "production/board/board.json").read_text())
    shot = {s["id"]: s for s in board["shots"]}[sid]
    book = {e["id"]: e for e in json.loads((ROOT / "production/motion/clipbook.json").read_text())}
    path, t_src0 = source(sid, shot, book)
    c = av.open(path)
    rate = float(c.streams.video[0].average_rate)
    frames = [f.to_ndarray(format="bgr24") for f in c.decode(video=0)]
    im = frames[max(0, round((float(shot["t0"]) - t_src0) * rate))]
    h, w = im.shape[:2]
    sc = max(1920 / w, 1080 / h)
    ox, oy = (w * sc - 1920) / 2, (h * sc - 1080) / 2
    big = cv2.resize(im, (round(w * sc), round(h * sc)), interpolation=cv2.INTER_CUBIC)
    big = big[round(oy):round(oy) + 1080, round(ox):round(ox) + 1920]
    g = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY).astype(float)

    def dips(v, k, thr, minsep):
        v = np.convolve(v, np.ones(5) / 5, "same")
        d = np.convolve(v, np.ones(k) / k, "same") - v
        cand = sorted([i for i in range(3, len(v) - 3) if d[i] == max(d[max(0, i - 6):i + 7]) and d[i] > thr],
                      key=lambda i: -d[i])
        out = []
        for i in cand:
            if all(abs(i - j) >= minsep for j in out):
                out.append(i)
        return sorted(out)

    rows = [r for r in dips(g[:, 500:1400].mean(1), 61, 1.5, 110) if 40 < r < 1060]
    cells = []
    for y0, y1 in zip(rows, rows[1:]):
        hsv = cv2.cvtColor(big[y0 + 15:y1 - 15], cv2.COLOR_BGR2HSV)
        xs = np.where(cv2.inRange(hsv, (3, 60, 60), (25, 255, 255)).mean(0) > 128)[0]
        xa, xb = int(xs.min()), int(xs.max())
        cols = [xa] + [xa + c for c in dips(g[y0 + 15:y1 - 15].mean(0)[xa:xb], 41, 1.2, 70)] + [xb]
        cells += [[int(cols[i]), int(y0), int(cols[i + 1]), int(y1)] for i in range(len(cols) - 1)]
    (OUT / f"cells-{sid}.json").write_text(json.dumps(cells))
    print(sid, f"{len(rows) - 1} rows, {len(cells)} tablets")


def main():
    if sys.argv[1] == "--grid":
        grid(sys.argv[2])
        return
    board = json.loads((ROOT / "production/board/board.json").read_text())
    S = {s["id"]: s for s in board["shots"]}
    book = {e["id"]: e for e in json.loads((ROOT / "production/motion/clipbook.json").read_text())}
    for sid in sys.argv[1:]:
        shot = S[sid]
        path, t_src0 = source(sid, shot, book)
        c = av.open(path)
        rate = float(c.streams.video[0].average_rate)
        frames = [f.to_ndarray(format="bgr24") for f in c.decode(video=0)]
        h, w = frames[0].shape[:2]
        sc = max(1920 / w, 1080 / h)
        ox, oy = (w * sc - 1920) / 2, (h * sc - 1080) / 2
        n = round((float(shot["t1"]) - float(shot["t0"])) * FPS)
        idx = [max(0, min(len(frames) - 1, round((float(shot["t0"]) + k / FPS - t_src0) * rate))) for k in range(n)]
        q0 = [orient(q) for q in find(frames[idx[0]])]
        # the floor's motion, chained frame to frame from fresh points on every tablet in view (whole or not), so the
        # fit never runs short of points as the camera pushes in (21 Oct: with the first frame's corners alone, the
        # last frames jittered once most of them had left the frame)
        Hs, H = [np.eye(3)], np.eye(3)
        prev, used = frames[idx[0]], []
        for k in range(1, n):
            cur = frames[idx[k]]
            g0, g1 = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY), cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY)
            pts = cv2.goodFeaturesToTrack(g0, 300, 0.01, 6, mask=mask(prev))
            step = np.eye(3)
            if pts is not None and len(pts) >= 8:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, pts, None, winSize=(21, 21), maxLevel=3)
                ok = st[:, 0] == 1
                if ok.sum() >= 8:
                    M, _ = cv2.findHomography(pts[ok], nxt[ok], cv2.RANSAC, 2.0)
                    if M is not None:
                        step = M
                used.append(int(ok.sum()))
            H = step @ H
            Hs.append(H.copy())
            prev = cur
        # chaining drifts (21 Oct: by the end two carvings had slid off their slabs), so every frame is then aligned
        # directly to the first: the tablets' terracotta shapes (her hair streak masked out: same colour) matched by
        # ECC, starting from the chained guess
        tr = json.loads((OUT / f"track-{sid}.json").read_text()) if (OUT / f"track-{sid}.json").exists() else None

        def shapes(k):
            m = cv2.inRange(cv2.cvtColor(frames[idx[k]], cv2.COLOR_BGR2HSV), (3, 80, 60), (22, 255, 255))
            if tr and tr["bbox"][k]:
                x0, y0, x1, y1 = [(v + (ox if i % 2 == 0 else oy)) / sc for i, v in enumerate(tr["bbox"][k])]
                bw, bh = x1 - x0, y1 - y0
                m[max(0, int(y0 - 0.6 * bh)): int(y1 + 0.5 * bh), max(0, int(x0 - 0.8 * bw)): int(x1 + 0.8 * bw)] = 0
            return cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 3)

        tmpl = shapes(0)
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5)
        fixed = 0
        for k in range(1, n):
            W = (Hs[k] / Hs[k][2, 2]).astype(np.float32)
            try:
                _, W = cv2.findTransformECC(tmpl, shapes(k), W, cv2.MOTION_HOMOGRAPHY, crit, None, 5)
                if np.abs(cv2.perspectiveTransform(np.array([[[w / 2, h / 2]]], np.float32), W)
                          - cv2.perspectiveTransform(np.array([[[w / 2, h / 2]]], np.float32), Hs[k])).max() < 60:
                    Hs[k] = W.astype(np.float64)
                    fixed += 1
            except cv2.error:
                pass
        used.append(fixed)
        # each corner's path, smoothed over time (a Gaussian, sigma 2.2 frames): the plate's own wobble stays, the
        # fit's frame-to-frame noise goes
        P = np.array([[cv2.perspectiveTransform(q.reshape(-1, 1, 2), Hk).reshape(4, 2) for q in q0] for Hk in Hs])
        if len(q0):
            kern = np.exp(-0.5 * (np.arange(-6, 7) / 2.2) ** 2)
            kern /= kern.sum()
            # pad by reflecting the motion (not holding the end still), so the ends don't lag the plate
            pad = np.concatenate([2 * P[:1] - P[6:0:-1], P, 2 * P[-1:] - P[-2:-8:-1]])
            P = sum(kern[i] * pad[i: i + len(P)] for i in range(13))
        res = {"t": [], "quads": []}
        for k in range(n):
            res["t"].append(round(float(shot["t0"]) + k / FPS, 3))
            res["quads"].append([[[round(float(x * sc - ox), 1), round(float(y * sc - oy), 1)] for x, y in q]
                                 for q in (P[k] if len(q0) else [])])
        (OUT / f"tablets-{sid}.json").write_text(json.dumps(res))
        print(sid, f"{len(q0)} whole tablets on the first frame; floor points per frame {min(used[:-1])}-"
                   f"{max(used[:-1])}; {used[-1]}/{n - 1} frames aligned to the first",
              Path(path).name)


if __name__ == "__main__":
    main()
