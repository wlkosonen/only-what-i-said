#!/usr/bin/env python3
"""Stems: split the master into vocals, drums, bass and other with htdemucs (wiki/toolkit, "4. Stems").

    media/cache/listen-venv/bin/python production/tools/listen/stems.py a1 [--shifts 1]

Reads media/song/<take>.wav, writes media/song/analysis/<take>/stems/{vocals,drums,bass,other}.wav at the model's
44.1 kHz, float32 stereo. CPU only. The spec measured about 64 s on 8 threads for a 5-minute song, 2.7 GB peak; the
weights (84 MB) download once to media/cache/listen-models/torch and carry no explicit licence.

The stems feed: vocals -> align; drums -> beatmap and kicks; bass and other -> impacts, risers, section energy.
"""

import argparse
import resource
import time

import common


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("take")
    ap.add_argument("--model", default="htdemucs")
    ap.add_argument("--shifts", type=int, default=1, help="random-shift passes averaged (more = slower, cleaner)")
    args = ap.parse_args()

    torch = common.torch_cpu()
    import numpy as np
    import soundfile as sf
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    t_start = time.time()
    model = get_model(args.model)
    model.eval()
    sr = model.samplerate
    x, _ = common.load(common.master_path(args.take), sr=sr, mono=False)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    wav = torch.from_numpy(x.T.copy())
    ref = wav.mean(0)
    mean, std = ref.mean(), ref.std()
    with torch.no_grad():
        out = apply_model(model, ((wav - mean) / std)[None], device="cpu", shifts=args.shifts, split=True,
                          overlap=0.25, progress=True, num_workers=0)[0]
    out = out * std + mean

    dest = common.stem_path(args.take, "vocals").parent
    dest.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, src in zip(model.sources, out):
        a = src.numpy().T
        sf.write(str(dest / f"{name}.wav"), a, sr, subtype="FLOAT")
        rms = float(np.sqrt((a ** 2).mean()))
        lines.append(f"| {name} | {20 * np.log10(rms + 1e-9):.1f} dBFS |")
    secs = time.time() - t_start
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
    dur = len(x) / sr
    print(f"{args.model}: {dur:.1f} s of audio in {secs:.1f} s on {common.THREADS} CPU threads, peak {peak_gb:.1f} GB")
    common.update_report(args.take, "stems", "\n".join([
        "## Stems", "",
        f"{args.model}, shifts={args.shifts}: {dur:.1f} s of audio split in {secs:.0f} s on {common.THREADS} CPU "
        f"threads, peak RSS {peak_gb:.1f} GB. Files in `stems/`.", "",
        "| stem | RMS |", "|---|---|", *lines]))


if __name__ == "__main__":
    main()
