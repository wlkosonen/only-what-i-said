#!/usr/bin/env python3
"""Audio references for Seedance clips, cut from the locked take's stems (claudia.gallery wiki/seedance, "Inputs").

    media/cache/listen-venv/bin/python production/tools/clipaudio.py vocal OUT.wav T0 T1 --keep K0 K1
    media/cache/listen-venv/bin/python production/tools/clipaudio.py inst  OUT.wav T0 T1

vocal: the vocal stem from T0 to T1, everything outside [K0, K1] (her words) muted with 10 ms fades, mono, peak
       normalised to -1 dBFS. The window should start 0.3-0.7 s before the first word and never end inside a word.
inst:  drums + bass + other (the song without the vocal), mono, normalised: rhythm for a motion clip, nothing that
       tempts her mouth.
"""

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
STEMS = ROOT / "media/song/analysis/a1/stems"


def load(name, t0, t1):
    info = sf.info(STEMS / f"{name}.wav")
    sr = info.samplerate
    x, _ = sf.read(STEMS / f"{name}.wav", start=int(t0 * sr), stop=int(t1 * sr), always_2d=True)
    return x.mean(axis=1), sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["vocal", "inst"])
    ap.add_argument("out")
    ap.add_argument("t0", type=float)
    ap.add_argument("t1", type=float)
    ap.add_argument("--keep", type=float, nargs=2, help="song times of the first word's start and the last word's end")
    a = ap.parse_args()
    if a.kind == "vocal":
        x, sr = load("vocals", a.t0, a.t1)
        if a.keep:
            k0, k1 = (int((k - a.t0) * sr) for k in a.keep)
            fade = int(0.01 * sr)
            g = np.zeros_like(x)
            g[max(0, k0 - fade):k1 + fade] = 1.0
            ramp = np.linspace(0, 1, fade)
            if k0 - fade >= 0:
                g[k0 - fade:k0] = ramp
            g[k1:k1 + fade] = ramp[::-1][: len(g[k1:k1 + fade])]
            x = x * g
    else:
        x = sum(load(n, a.t0, a.t1)[0] for n in ("drums", "bass", "other"))
        sr = sf.info(STEMS / "drums.wav").samplerate
    peak = np.abs(x).max() or 1.0
    x = x / peak * 10 ** (-1 / 20)
    sf.write(a.out, x.astype(np.float32), sr, subtype="PCM_16")
    print(a.out, f"{len(x) / sr:.2f} s", sr, "Hz mono")


if __name__ == "__main__":
    main()
