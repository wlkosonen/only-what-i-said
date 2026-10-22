#!/usr/bin/env python3
"""Face transplant for the sung wides: put a real, sharp, lip-synced face of hers into a wide where her face is too
small for the video model to hold (decisions 20 Oct, after face pass 1 failed).

    media/cache/face-venv/bin/python production/tools/transplant.py WIDE.mp4 CLOSE.mp4 OUT.mp4

WIDE is the wide's clip; CLOSE is InfiniteTalk run on a close-up plate of her in the same light with the same audio
window, so frame i of both is the same moment of the song. Per frame: InsightFace's 106 landmarks on both faces (the
wide's found on a 2x upscale, smoothed over time so the small face doesn't jitter), a similarity transform from the
close-up's face to the wide's, the close-up shrunk to that size before warping (no aliasing), a mask over the inner
face (from just above the eyes to the chin, inside the jaw line, so the wide's brows, bangs, hair and
headset stay), the patch's colour matched to
the wide's skin in Lab, and a feathered blend. Our own renders only; no swap model.
"""

import sys

import av
import cv2
import numpy as np
from insightface.app import FaceAnalysis

SMOOTH = 0.6  # weight of the previous frame's wide landmarks (temporal smoothing)


def frames(path):
    c = av.open(path)
    rate = c.streams.video[0].average_rate
    return [f.to_ndarray(format="bgr24") for f in c.decode(video=0)], rate


def face(app, img, up=1):
    big = cv2.resize(img, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC) if up != 1 else img
    fs = app.get(big)
    if not fs:
        return None
    f = max(fs, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return np.vstack([f.landmark_2d_106, f.kps]).astype(np.float64) / up  # 106 landmarks, then the 5 key points


def colour_match(src, dst, mask):
    s = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float64)
    d = cv2.cvtColor(dst, cv2.COLOR_BGR2LAB).astype(np.float64)
    m = mask > 0.5
    if m.sum() < 20:
        return src
    for c in range(3):
        sm, ss = s[..., c][m].mean(), s[..., c][m].std() + 1e-6
        dm, ds = d[..., c][m].mean(), d[..., c][m].std() + 1e-6
        s[..., c] = (s[..., c] - sm) * (ds / ss) + dm
    return cv2.cvtColor(np.clip(s, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def main():
    wide_p, close_p, out_p = sys.argv[1:4]
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"],
                       allowed_modules=["detection", "landmark_2d_106"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    W, rate = frames(wide_p)
    C, _ = frames(close_p)
    n = min(len(W), len(C))
    h, w = W[0].shape[:2]
    out = av.open(out_p, "w")
    vs = out.add_stream("libx264", rate=rate)
    vs.width, vs.height, vs.pix_fmt, vs.options = w, h, "yuv420p", {"crf": "14"}
    prev, done = None, 0
    for i in range(n):
        img = W[i].copy()
        lw, lc = face(app, W[i], up=2), face(app, C[i])
        if lw is not None and lc is not None:
            lw = lw if prev is None else SMOOTH * prev + (1 - SMOOTH) * lw
            prev = lw
            M, _ = cv2.estimateAffinePartial2D(lc[:106], lw[:106], method=cv2.LMEDS)
            s = float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
            small = cv2.resize(C[i], None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            M2, _ = cv2.estimateAffinePartial2D(lc[:106] * s, lw[:106], method=cv2.LMEDS)
            patch = cv2.warpAffine(small, M2, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            # inner face: the jaw line (0-32) and the brows' tops close the hull; shrink it a little toward the centre
            pts = lw[:106].copy()
            ctr = pts.mean(axis=0)
            pts = ctr + (pts - ctr) * 0.85
            mask = np.zeros((h, w), np.float32)
            cv2.fillConvexPoly(mask, cv2.convexHull(pts.astype(np.int32)), 1.0)
            # keep the wide's brows and bangs: nothing above a line just over the eyes (key points 0, 1 = eyes,
            # 3, 4 = mouth corners)
            eye_y, mouth_y = lw[106:108, 1].mean(), lw[109:111, 1].mean()
            mask[: max(0, int(eye_y - 0.3 * (mouth_y - eye_y))), :] = 0
            fw = max(3, int(np.ptp(lw[:106, 0]) * 0.12) | 1)
            mask = cv2.GaussianBlur(mask, (fw * 2 + 1, fw * 2 + 1), fw / 2)
            patch = colour_match(patch, img, mask)
            img = (img * (1 - mask[..., None]) + patch * mask[..., None]).astype(np.uint8)
            done += 1
        for p in vs.encode(av.VideoFrame.from_ndarray(img, format="bgr24")):
            out.mux(p)
    for p in vs.encode():
        out.mux(p)
    out.close()
    print(f"transplanted {done}/{n} frames -> {out_p}")


if __name__ == "__main__":
    main()
