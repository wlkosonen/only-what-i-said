#!/usr/bin/env python3
"""Face pass for the wides: her face is a few dozen pixels there, too few for the video models to hold her, so it
drifts to their default face. This puts her canon face back, frame by frame, from her close-up plates.

    media/cache/face-venv/bin/python production/tools/facepass.py ID [ID ...] [--out media/clips/face]

Method 1 of 2 (decisions 20 Oct): InsightFace (buffalo_l detector + inswapper_128, a non-commercial licence; this film
is released non-commercially). The source identity is the mean embedding of her face on the close-up references below,
so no single plate's expression or light is copied. Every frame of the clip's current take is swapped and pasted back
with InsightFace's own feathered mask; frames with no face found pass through unchanged. CPU (ONNX Runtime).
"""

import argparse
import glob
import sys
from pathlib import Path

import av
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

ROOT = Path(__file__).resolve().parents[2]
SMOOTH = 0.6  # weight of the previous frame's key points (a cut or a big move resets it)
REFS = ["media/clips/first/FCH.png", "media/plates/picked/p-s010.png", "media/plates/picked/p-s042.png",
        "media/plates/picked/p-s022.png"]


def canon(app):
    embs, best = [], None
    for r in REFS:
        img = cv2.imread(str(ROOT / r))
        faces = app.get(img) if img is not None else []
        if not faces:
            print("no face in", r, file=sys.stderr)
            continue
        f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        embs.append(f.normed_embedding)
        best = best or f
    e = np.mean(embs, axis=0)
    best.embedding = e / np.linalg.norm(e) * np.linalg.norm(best.embedding)
    return best


def run(app, swap, src, path, out):
    inp = av.open(path)
    rate = inp.streams.video[0].average_rate
    o = av.open(str(out), "w")
    vs = None
    hit = n = 0
    prev = None  # the previous frame's key points: on small faces the detector's eye points wander a pixel or two
                 # per frame and the swap follows them (S021's lagging left eye, 20 Oct), so they are smoothed
    for fr in inp.decode(video=0):
        img = fr.to_ndarray(format="bgr24")
        if vs is None:
            vs = o.add_stream("libx264", rate=rate)
            vs.width, vs.height, vs.pix_fmt, vs.options = img.shape[1], img.shape[0], "yuv420p", {"crf": "14"}
        # detect on a 2x upscale so the small faces in wides are found, then map boxes back
        big = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        faces = app.get(big)
        n += 1
        if faces:
            f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            if prev is not None and np.abs(f.kps - prev).max() < 0.15 * (f.bbox[2] - f.bbox[0]):
                f.kps = (SMOOTH * prev + (1 - SMOOTH) * f.kps).astype(np.float32)
            prev = f.kps.copy()
            big = swap.get(big, f, src, paste_back=True)
            img = cv2.resize(big, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_AREA)
            hit += 1
        for p in vs.encode(av.VideoFrame.from_ndarray(img, format="bgr24")):
            o.mux(p)
    for p in vs.encode():
        o.mux(p)
    o.close()
    return hit, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--out", default="media/clips/face")
    a = ap.parse_args()
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    swap = get_model(str(ROOT / "media/cache/models/face/inswapper_128.onnx"), providers=["CPUExecutionProvider"])
    src = canon(app)
    outdir = ROOT / a.out
    outdir.mkdir(parents=True, exist_ok=True)
    for cid in a.ids:
        files = sorted(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4")))
        if not files:
            print(cid, "no clip")
            continue
        hit, n = run(app, swap, src, files[-1], outdir / Path(files[-1]).name)
        print(cid, f"face swapped in {hit}/{n} frames", flush=True)


if __name__ == "__main__":
    main()
