#!/usr/bin/env python3
"""The beat map: every beat and bar line of this take (wiki/toolkit, "6. The beat map").

    media/cache/listen-venv/bin/python production/tools/listen/beatmap.py a1 [--tempo-range 110 122]
        [--downbeat-phase 0..3]

In: the drum, bass and other stems. Out: media/song/analysis/<take>/beats.json (formats.md) and the "beatmap" block of
report.md. Never one BPM: Suno takes drift like live music.

How (constants from the spec):
  1. Onset strength (spectral flux) of the drum stem, in 4 ms frames.
  2. Local tempo on 20 s windows every 5 s: BPM in 0.05 steps, phase in 4 ms steps, inside a tempo range. The
     weakest 20% of windows (breakdowns) are dropped and filled from their neighbours.
  3. Smooth the tempo curve, step beats along it, snap each beat to a real drum onset within +-30 ms, preferring a
     kick: the grid sits on the kick, not the hats (BLISS's first grid sat on the hats, 0.214 s early).
  4. Downbeat phase with two votes per 32-beat block: kick energy, and harmony change (chroma of bass + other). The
     chord vote wins when it holds at least half the blocks and changes at least 1.5x more than the other phases;
     otherwise the kick decides. A manual phase in production/song/listen/<take>.json or --downbeat-phase wins.
  5. Half or double time: pin the range ("tempo_range": [lo, hi] in the settings file, or --tempo-range).
"""

import argparse
import json
import time

import common

WIN, STEP = 20.0, 5.0       # tempo windows, s
BPM_STEP = 0.05
DROP_WEAKEST = 0.2
SNAP = 0.030                # snap beats to a drum onset within this, s
RELOCK = 0.080              # after 4 unsnapped beats, re-lock to a kick within this, s
BLOCK = 32                  # beats per downbeat vote block


def fit_window(flux, t0, lo, hi):
    """Best (score, bpm, phase_s) for flux frames in [t0, t0 + WIN) over bpm in lo..hi (0.05 steps), 4 ms phases."""
    import numpy as np
    fps = common.ONSET_SR / common.ONSET_HOP
    f0, f1 = int(t0 * fps), min(len(flux), int((t0 + WIN) * fps))
    seg = flux[f0:f1]
    # tolerate one frame of jitter
    seg = np.maximum(seg, np.maximum(np.roll(seg, 1), np.roll(seg, -1)))
    best = (-1.0, None, None)
    for bpm in np.arange(lo, hi + 1e-9, BPM_STEP):
        period = 60.0 / bpm * fps
        n = int((len(seg) - period) / period)
        if n < 4:
            continue
        phases = np.arange(int(period))
        idx = (phases[:, None] + np.arange(n)[None, :] * period).astype(int)
        scores = seg[idx].mean(axis=1)
        k = scores.argmax()
        if scores[k] > best[0]:
            best = (float(scores[k]), float(bpm), t0 + phases[k] / fps)
    return best


def smooth(values, k=3):
    import numpy as np
    from scipy.signal import medfilt
    v = medfilt(np.asarray(values, float), 2 * k - 1 if len(values) >= 2 * k - 1 else 1)
    kernel = np.ones(k) / k
    pad = np.pad(v, (k // 2, k // 2), mode="edge")
    return np.convolve(pad, kernel, mode="valid")[: len(v)]


def step_beats(anchor, tempo_t, tempo_bpm, duration, kicks, onsets):
    """Step beats forward and back from an anchor along the tempo curve, snapping to kicks first, then any onset."""
    import numpy as np

    def nearest(arr, t, tol):
        if not len(arr):
            return None
        j = np.searchsorted(arr, t)
        best = None
        for q in (j - 1, j):
            if 0 <= q < len(arr) and abs(arr[q] - t) <= tol and (best is None or abs(arr[q] - t) < abs(best - t)):
                best = arr[q]
        return best

    def walk(direction):
        out, t, misses = [], anchor, 0
        while 0 <= t <= duration:
            period = 60.0 / np.interp(t, tempo_t, tempo_bpm)
            t = t + direction * period
            if not 0 <= t <= duration:
                break
            s = nearest(kicks, t, SNAP)
            if s is None:
                s = nearest(onsets, t, SNAP)
            if s is None and misses >= 4:
                s = nearest(kicks, t, RELOCK)
            if s is None:
                misses += 1
            else:
                t, misses = float(s), 0
            out.append((t, s is not None))
        return out

    back = walk(-1)[::-1]
    fwd = walk(+1)
    s = nearest(kicks, anchor, SNAP) or nearest(onsets, anchor, SNAP)
    return back + [(float(s) if s else anchor, s is not None)] + fwd


def beat_values(curve, beats, reduce="max", win=0.03):
    """Sample a flux curve at each beat (max within +-win), as a numpy array."""
    import numpy as np
    fps = common.ONSET_SR / common.ONSET_HOP
    out = []
    for b in beats:
        i0, i1 = max(0, int((b - win) * fps)), min(len(curve), int((b + win) * fps) + 1)
        out.append(curve[i0:i1].max() if i1 > i0 else 0.0)
    return np.array(out)


def chroma_changes(take, beats):
    """Harmony change at each beat: 1 - cosine between the mean chroma of the beat before and the beat after."""
    import librosa
    import numpy as np
    bass, sr = common.load(common.stem_path(take, "bass"), sr=common.ONSET_SR)
    other, _ = common.load(common.stem_path(take, "other"), sr=common.ONSET_SR)
    hop = 512
    C = librosa.feature.chroma_stft(y=bass + other, sr=sr, hop_length=hop)
    frames = (np.asarray(beats) * sr / hop).astype(int)
    sync = []
    for a, b in zip(frames, list(frames[1:]) + [C.shape[1]]):
        sync.append(C[:, a:max(a + 1, b)].mean(axis=1))
    sync = np.array(sync)
    sync /= np.linalg.norm(sync, axis=1, keepdims=True) + 1e-9
    change = np.zeros(len(beats))
    change[1:] = 1 - (sync[1:] * sync[:-1]).sum(axis=1)
    return change


def vote(values, n_beats, active=None):
    """Per 32-beat block, the phase 0..3 with the most `values` at its beats. Returns the list of block winners and
    the mean value per phase over the whole song."""
    import numpy as np
    winners = []
    for b0 in range(0, n_beats, BLOCK):
        sl = np.arange(b0, min(n_beats, b0 + BLOCK))
        if active is not None and active[sl].mean() < 0.5:
            continue
        per = [values[sl[sl % 4 == p]].mean() if (sl % 4 == p).any() else 0 for p in range(4)]
        winners.append(int(np.argmax(per)))
    per_phase = [float(values[np.arange(n_beats) % 4 == p].mean()) for p in range(4)]
    return winners, per_phase


def verdict(kick, snare, chord):
    """One honest line on the done-when check."""
    out = []
    flat = (max(kick) - min(kick)) / (sum(kick) / 4) < 0.1
    out.append("Kick about equal on all four beats (four on the floor), so the kick vote can't find beat 1."
               if flat else ("Kick heavier on 1 and 3." if kick[0] + kick[2] > kick[1] + kick[3]
                             else "Kick heavier on 2 and 4: the phase may be off by one beat."))
    out.append("Snare/clap band heavier on 2 and 4." if snare[1] + snare[3] > snare[0] + snare[2]
               else "Snare/clap band heavier on 1 and 3, not 2 and 4: ask Lati to count a bar by ear.")
    out.append("Harmony changes on 1." if chord[0] == max(chord) else "Harmony does not change most on 1.")
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("take")
    ap.add_argument("--tempo-range", type=float, nargs=2)
    ap.add_argument("--downbeat-phase", type=int, choices=range(4))
    args = ap.parse_args()

    import librosa
    import numpy as np
    t_start = time.time()
    cfg = common.settings(args.take)
    d = common.out_dir(args.take)
    drums, sr = common.load(common.stem_path(args.take, "drums"), sr=common.ONSET_SR)
    duration = len(drums) / sr
    freqs, S, fps = common.spectrum(drums)
    flux = common.band_flux(freqs, S, 30, 11000)
    kick_flux = common.band_flux(freqs, S, 30, 150)
    kicks = common.pick(kick_flux, fps, delta=0.2, wait_s=0.1, floor=common.KICK_FLOOR)
    onsets = common.pick(flux, fps, delta=0.15, wait_s=0.05)

    # tempo range: settings > flag > a global estimate +-7%
    rng = args.tempo_range or cfg.get("tempo_range")
    est = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=flux, sr=sr, hop_length=common.ONSET_HOP,
                                                    start_bpm=116))[0])
    if not rng:
        rng = [round(est * 0.93, 1), round(est * 1.07, 1)]
    lo, hi = rng

    # local tempos
    starts = np.arange(0, max(STEP, duration - WIN + STEP), STEP)
    fits = [fit_window(flux, t0, lo, hi) for t0 in starts]
    scores = np.array([f[0] for f in fits])
    keep = scores >= np.quantile(scores, DROP_WEAKEST)
    centers = starts + WIN / 2
    bpm_raw = np.array([f[1] or np.nan for f in fits])
    good = keep & ~np.isnan(bpm_raw)
    bpm_filled = np.interp(centers, centers[good], bpm_raw[good])
    bpm_smooth = smooth(bpm_filled)

    anchor_w = int(np.argmax(np.where(good, scores, -1)))
    anchor = fits[anchor_w][2]
    grid = step_beats(anchor, centers, bpm_smooth, duration, kicks, onsets)
    beats = np.array([t for t, _ in grid])
    snapped = np.array([s for _, s in grid])

    # downbeats
    kick_at = beat_values(kick_flux, beats)
    change = chroma_changes(args.take, beats)
    active = beat_values(flux, beats) > 0.15
    kick_votes, kick_per = vote(kick_at, len(beats), active)
    chord_votes, chord_per = vote(change, len(beats))
    def majority(v):
        return max(range(4), key=lambda p: v.count(p)) if v else 0
    chord_p, kick_p = majority(chord_votes), majority(kick_votes)
    chord_share = chord_votes.count(chord_p) / max(1, len(chord_votes))
    kick_share = kick_votes.count(kick_p) / max(1, len(kick_votes))
    others = [c for p, c in enumerate(chord_per) if p != chord_p]
    chord_ratio = chord_per[chord_p] / (np.mean(others) + 1e-9)
    manual = args.downbeat_phase if args.downbeat_phase is not None else cfg.get("downbeat_phase")
    if manual is not None:
        phase, method = int(manual), "manual"
    elif chord_share >= 0.5 and chord_ratio >= 1.5:
        phase, method = chord_p, "harmony"
    else:
        phase, method = kick_p, "kick"
    downbeats = beats[phase::4]

    # check: kicks on 1 and 3, snares/claps on 2 and 4, harmony on 1
    snare_flux = common.band_flux(freqs, S, 1500, 5000)   # above most of the kick's spill
    snare_at = beat_values(snare_flux, beats)
    pos = (np.arange(len(beats)) - phase) % 4
    def by_pos(v):
        return [float(v[(pos == p) & active].mean()) if ((pos == p) & active).any() else 0.0 for p in range(4)]
    kick_pos, snare_pos, chord_pos = by_pos(kick_at), by_pos(snare_at), by_pos(change)

    # drift
    ibi = np.diff(beats)
    tempo = [{"t": float(t), "bpm": float(b)} for t, b in zip(centers - WIN / 2, bpm_smooth)]
    dense = [(t, b) for t, b in zip(centers, bpm_smooth)]
    mean_bpm = 60.0 / np.median(ibi[(ibi > 60 / hi * 0.8) & (ibi < 60 / lo * 1.2)])
    fixed = beats[0] + np.arange(len(beats)) * 60.0 / mean_bpm
    worst_off = float(np.max(np.abs(fixed - beats)) / (60.0 / mean_bpm))

    old = json.loads((d / "beats.json").read_text()) if (d / "beats.json").exists() else {}
    common.write_json(d / "beats.json", {
        "duration": duration, "beats": [float(b) for b in beats], "downbeats": [float(b) for b in downbeats],
        "tempo": tempo, "downbeat_phase": phase, "downbeat_method": method,
        "sections": old.get("sections", []),
        "tempo_range": [lo, hi], "tempo_raw": [None if np.isnan(b) or not k else float(b)
                                               for b, k in zip(bpm_raw, keep)],
        "snapped": [bool(s) for s in snapped],
        "votes": {"kick": kick_votes, "chord": chord_votes, "kick_share": kick_share, "chord_share": chord_share,
                  "chord_ratio": float(chord_ratio)}})
    secs = time.time() - t_start

    first, last = bpm_smooth[good][0] if good.any() else bpm_smooth[0], bpm_smooth[good][-1]
    md = ["## The beat map", "",
          f"Tempo search {lo}-{hi} BPM ({'pinned' if (args.tempo_range or cfg.get('tempo_range')) else f'auto: global estimate {est:.1f} +-7%'}). "
          f"{len(fits)} windows of 20 s every 5 s, {int((~keep).sum())} weakest dropped.",
          f"**Tempo:** {first:.2f} BPM at the start, {last:.2f} at the end; range {bpm_smooth.min():.2f}-"
          f"{bpm_smooth.max():.2f}; median beat {mean_bpm:.2f} BPM. A fixed grid at {mean_bpm:.2f} would be "
          f"{worst_off:.2f} beats off at its worst.",
          f"{len(beats)} beats, {int(snapped.sum())} snapped to a drum onset within 30 ms "
          f"({100 * snapped.mean():.0f}%; unsnapped beats are in drumless passages), {len(downbeats)} bars.",
          f"**Downbeat:** phase {phase} by {method}. Kick vote {kick_share:.0%} of {len(kick_votes)} blocks for phase "
          f"{kick_p}; chord vote {chord_share:.0%} of {len(chord_votes)} blocks for phase {chord_p}, changing "
          f"{chord_ratio:.2f}x the other phases (needs >= 50% and >= 1.5x to win).",
          "", "Check (beat 1..4 of the bar, drum passages only; want kicks on 1 and 3, snares/claps on 2 and 4, "
          "harmony changing on 1):", "",
          "| | 1 | 2 | 3 | 4 |", "|---|---|---|---|---|",
          "| kick | " + " | ".join(f"{v:.2f}" for v in kick_pos) + " |",
          "| snare/clap 1.5-5 kHz | " + " | ".join(f"{v:.2f}" for v in snare_pos) + " |",
          "| harmony change | " + " | ".join(f"{v:.3f}" for v in chord_pos) + " |",
          "", verdict(kick_pos, snare_pos, chord_pos),
          "", "Tempo curve (smoothed, at window centres):", "",
          "`" + " ".join(f"{common.fmt_t(t)[:-3]}={b:.1f}" for t, b in dense[::4]) + "`",
          "", f"Ran in {secs:.0f} s on CPU."]
    common.update_report(args.take, "beatmap", "\n".join(md))
    print("\n".join(md[2:6]))
    print("kick", [round(v, 2) for v in kick_pos], "snare", [round(v, 2) for v in snare_pos],
          "chord", [round(v, 3) for v in chord_pos])


if __name__ == "__main__":
    main()
