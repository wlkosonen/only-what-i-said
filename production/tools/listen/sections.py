#!/usr/bin/env python3
"""Sections and hits: what the track does, where (wiki/toolkit, "7. Sections and hits").

    media/cache/listen-venv/bin/python production/tools/listen/sections.py a1 [--lyrics production/lyrics/v2.md]

Needs stems.py, align.py and beatmap.py first. Writes the sections into media/song/analysis/<take>/beats.json, the
events into hits.json (formats.md), and the "sections" block of report.md: the sections against the lyric's tags,
every vocal gap of 2 s or more, each stem's energy per bar on a 0-9 scale with one line per section, and the impacts.

Sections: the lyric's tags give the names and order; each tagged section starts at the downbeat that owns its first
sung line (pickup rule: a line starting less than 0.8 s before a downbeat belongs to it), moved to a harmony/timbre
change within 4 bars before it if there is one. Tags with no lines (an instrumental build) sit between their
neighbours. Changes the segmenter finds that no tag explains are listed, not invented into sections.

Hits (spec constants): kick 30-150 Hz; snare 150 Hz-5 kHz minus anything within 45 ms of a kick; hat 6-16 kHz minus
kick-coincident; impact = jump of the next 0.6 s over the previous 1.5 s, score max(mix, 0.9 drums, 0.7 bass) >= 0.22,
snapped to a downbeat within 0.65 s, merged within 2 s; risers = other/bass rising (level or brightness) for >= 1 s
and the hit each lands on; fills = the beat before a strong hit, and bars whose last half breaks the drum pattern;
vocal entries after >= 1 s of vocal silence; drum/vocal/bass envelopes at 24 fps, 0-1.
Manual hits: "hits": {"add": [[t, score]], "drop": [t]} in production/song/listen/<take>.json.
"""

import argparse
import json
import time

import common

PICKUP = 0.8
KICK_TOL = 0.045
IMPACT_MIN = 0.22
IMPACT_SNAP = 0.65
IMPACT_MERGE = 2.0
RISER_MIN = 1.0
VOCAL_SILENCE = 1.0
FPS = 24


def norm_env(x, sr, hop_s):
    """RMS envelope scaled 0-1 by its 99.5th percentile."""
    import numpy as np
    e = common.envelope(x, sr, hop_s)
    return np.clip(e / (np.percentile(e, 99.5) + 1e-9), 0, 1)


def not_near(a, b, tol):
    import numpy as np
    if not len(b):
        return a
    j = np.searchsorted(b, a)
    keep = []
    for t, k in zip(a, j):
        d = min(abs(t - b[q]) for q in (k - 1, k) if 0 <= q < len(b))
        keep.append(d > tol)
    return a[np.array(keep, bool)]


def jumps(env, hop_s):
    """Mean of the next 0.6 s minus the mean of the previous 1.5 s, per frame."""
    import numpy as np
    c = np.concatenate(([0], np.cumsum(env)))
    n, a, b = len(env), int(0.6 / hop_s), int(1.5 / hop_s)
    i = np.arange(n)
    nxt = (c[np.minimum(n, i + a)] - c[i]) / np.maximum(1, np.minimum(n, i + a) - i)
    prv = (c[i] - c[np.maximum(0, i - b)]) / np.maximum(1, i - np.maximum(0, i - b))
    out = nxt - prv
    out[:b] = 0
    return out


def nearest(arr, t):
    import numpy as np
    j = int(np.clip(np.searchsorted(arr, t), 1, len(arr) - 1))
    return arr[j - 1] if abs(arr[j - 1] - t) <= abs(arr[j] - t) else arr[j]


def bar_of(downbeats, t):
    import numpy as np
    return int(np.clip(np.searchsorted(downbeats, t + 1e-6) - 1, 0, len(downbeats) - 1))


def novelty_bars(take, downbeats, duration):
    """Harmony + timbre change per bar line: a checkerboard kernel over a bar-synchronous self-similarity matrix."""
    import librosa
    import numpy as np
    mix, sr = common.load(common.master_path(take), sr=22050)
    hb, _ = common.load(common.stem_path(take, "bass"), sr=22050)
    ho, _ = common.load(common.stem_path(take, "other"), sr=22050)
    hop = 512
    chroma = librosa.feature.chroma_stft(y=hb + ho, sr=sr, hop_length=hop)
    mfcc = librosa.feature.mfcc(y=mix, sr=sr, hop_length=hop, n_mfcc=13)[1:]
    edges = list((np.asarray(downbeats) * sr / hop).astype(int)) + [int(duration * sr / hop)]
    feats = []
    for a, b in zip(edges, edges[1:]):
        b = max(a + 1, b)
        c = chroma[:, a:b].mean(1)
        m = mfcc[:, a:b].mean(1)
        feats.append(np.concatenate([c / (np.linalg.norm(c) + 1e-9), m / 50.0]))
    F = np.array(feats)
    F = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    ssm = F @ F.T
    k = 4
    g = np.outer(np.r_[-np.ones(k), np.ones(k)], np.r_[-np.ones(k), np.ones(k)])   # +1 within, -1 across
    nov = np.zeros(len(F))
    pad = np.pad(ssm, k, mode="edge")
    for i in range(len(F)):
        nov[i] = (pad[i:i + 2 * k, i:i + 2 * k] * g).sum()
    nov = np.maximum(0, nov)
    nov /= nov.max() + 1e-9
    peaks = [i for i in range(1, len(nov) - 1) if nov[i] >= nov[i - 1] and nov[i] > nov[i + 1] and nov[i] > 0.3]
    return nov, peaks


def bar_levels(take, downbeats, duration):
    """RMS per bar per stem and the mix, and the 0-9 digits (each stem scaled by its own loudest bar)."""
    import numpy as np
    out = {}
    for name in ("mix",) + common.STEMS:
        path = common.master_path(take) if name == "mix" else common.stem_path(take, name)
        x, sr = common.load(path, sr=22050)
        edges = list((np.asarray(downbeats) * sr).astype(int)) + [len(x)]
        rms = np.array([np.sqrt((x[a:max(a + 1, b)] ** 2).mean()) for a, b in zip(edges, edges[1:])])
        out[name] = rms
    digits = {k: np.clip(np.round(9 * v / (v.max() + 1e-9)), 0, 9).astype(int) for k, v in out.items()}
    return out, digits


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("take")
    ap.add_argument("--lyrics", default=str(common.LYRICS))
    args = ap.parse_args()

    import numpy as np
    t_start = time.time()
    take = args.take
    d = common.out_dir(take)
    cfg = common.settings(take)
    beats_doc = json.loads((d / "beats.json").read_text())
    words_doc = json.loads((d / "words.json").read_text())
    beats = np.array(beats_doc["beats"])
    downbeats = np.array(beats_doc["downbeats"])
    duration = beats_doc["duration"]
    lines, tags = common.read_lyrics(args.lyrics)
    line_t = {ln["line"]: ln for ln in words_doc["lines"]}
    words = words_doc["words"]

    # ---- hits ----
    drums, sr = common.load(common.stem_path(take, "drums"), sr=44100)
    freqs, S, fps = common.spectrum(drums, sr)
    kick = common.pick(common.band_flux(freqs, S, 30, 150), fps, delta=0.2, wait_s=0.1, floor=common.KICK_FLOOR)
    snare = not_near(common.pick(common.band_flux(freqs, S, 150, 5000), fps, 0.15, 0.05), kick, KICK_TOL)
    hat = not_near(common.pick(common.band_flux(freqs, S, 6000, 16000), fps, 0.15, 0.03), kick, KICK_TOL)

    hop_s = 0.01
    env = {}
    for name in ("mix", "drums", "bass", "other", "vocals"):
        path = common.master_path(take) if name == "mix" else common.stem_path(take, name)
        x, xsr = common.load(path, sr=22050)
        env[name] = norm_env(x, xsr, hop_s)
    n = min(len(v) for v in env.values())
    env = {k: v[:n] for k, v in env.items()}
    score = np.maximum.reduce([jumps(env["mix"], hop_s), 0.9 * jumps(env["drums"], hop_s),
                               0.7 * jumps(env["bass"], hop_s)])
    cand = [i for i in range(1, n - 1) if score[i] >= IMPACT_MIN and score[i] >= score[i - 1]
            and score[i] > score[i + 1]]
    hits = []
    for i in sorted(cand, key=lambda i: -score[i]):
        t = i * hop_s
        db = nearest(downbeats, t)
        if abs(db - t) <= IMPACT_SNAP:
            t = float(db)
        if all(abs(t - h["t"]) > IMPACT_MERGE for h in hits):
            hits.append({"t": t, "score": float(score[i]), "src": "auto"})
    man = cfg.get("hits", {})
    hits = [h for h in hits if all(abs(h["t"] - x) > 0.3 for x in man.get("drop", []))]
    hits += [{"t": float(t), "score": float(s), "src": "manual"} for t, s in man.get("add", [])]
    hits.sort(key=lambda h: h["t"])
    hit_times = np.array([h["t"] for h in hits]) if hits else np.array([duration + 10])

    # risers: other+bass level or the other stem's brightness rising for >= 1 s
    import librosa
    ox, osr = common.load(common.stem_path(take, "other"), sr=22050)
    cent = librosa.feature.spectral_centroid(y=ox, sr=osr, hop_length=int(osr * hop_s))[0][:n]
    k = int(0.5 / hop_s)
    sm = lambda v: np.convolve(v, np.ones(k) / k, mode="same")
    level = sm(0.5 * (env["other"] + env["bass"]))
    bright = sm(np.log(cent + 1))
    risers = []
    for curve, need, kind in ((level, 0.15, "level"), (bright, np.log(1.4), "brightness")):
        up = np.diff(curve, prepend=curve[0]) > 0
        i = 0
        while i < n:
            if up[i]:
                j = i
                while j < n and (up[j] or (j + 5 < n and up[j:j + 5].mean() > 0.6)):
                    j += 1
                if (j - i) * hop_s >= RISER_MIN and curve[min(j, n - 1)] - curve[i] >= need:
                    t0, t1 = i * hop_s, j * hop_s
                    after = hit_times[(hit_times >= t1 - 0.3) & (hit_times <= t1 + 1.0)]
                    land = float(after[0]) if len(after) else float(nearest(downbeats, t1))
                    if not any(r["t0"] <= t1 and t0 <= r["t1"] for r in risers):
                        risers.append({"t0": t0, "t1": t1, "land": land, "kind": kind})
                i = j
            i += 1
    risers.sort(key=lambda r: r["t0"])

    # fills: the beat before a strong hit, and bars whose last half breaks the pattern
    fills = []
    for h in hits:
        if h["score"] >= 0.35:
            b = beats[beats < h["t"] - 0.05]
            if len(b):
                fills.append({"t0": float(b[-1]), "t1": h["t"], "why": "beat before a hit"})
    dflux = common.band_flux(freqs, S, 30, 16000)
    pat = []
    for a, b in zip(downbeats, list(downbeats[1:]) + [duration]):
        slots = a + (b - a) * np.arange(16) / 16
        pat.append([dflux[max(0, int((s - 0.02) * fps)):int((s + 0.02) * fps) + 1].max(initial=0) for s in slots])
    pat = np.array(pat)
    for i in range(len(pat)):
        ref = np.median(pat[max(0, i - 8):i + 8, :8], axis=0)
        ref_last = np.median(pat[max(0, i - 8):i + 8, 8:], axis=0)
        busy = pat[i, :8].sum() + ref.sum()
        if busy < 2:
            continue
        dist = np.abs(pat[i, 8:] - ref_last).sum() / (ref_last.sum() + pat[i, 8:].sum() + 1e-9)
        first = np.abs(pat[i, :8] - ref).sum() / (ref.sum() + pat[i, :8].sum() + 1e-9)
        if dist > 0.35 and dist > 2 * first:
            end = downbeats[i + 1] if i + 1 < len(downbeats) else duration
            fills.append({"t0": float((downbeats[i] + end) / 2), "t1": float(end),
                          "why": f"bar {i} breaks the pattern"})
    fills.sort(key=lambda f: f["t0"])

    # vocal entries: after >= 1 s of vocal silence
    v = env["vocals"]
    quiet = v < 0.05
    entries, run = [], 0
    for i in range(n):
        if quiet[i]:
            run += 1
        else:
            if run * hop_s >= VOCAL_SILENCE or (i > 0 and run == i):
                entries.append(i * hop_s)
            run = 0
    entries = [t for t in entries if v[int(t / hop_s):int(t / hop_s) + 20].max() > 0.15]

    env24 = {}
    for name in ("drums", "vocals", "bass"):
        step = 1 / FPS / hop_s
        idx = (np.arange(int(n * hop_s * FPS)) * step).astype(int)
        e = np.array([env[name][i:i + max(1, int(step))].max() for i in idx])
        env24[name] = [round(float(x), 3) for x in e / (e.max() + 1e-9)]

    common.write_json(d / "hits.json", {"kick": [float(x) for x in kick], "snare": [float(x) for x in snare],
                                         "hat": [float(x) for x in hat], "hits": hits, "risers": risers,
                                         "fills": fills, "vocal_entries": entries, "env24": env24})

    # ---- sections ----
    nov, peaks = novelty_bars(take, downbeats, duration)
    levels, digits = bar_levels(take, downbeats, duration)
    boundaries = set(peaks)
    used = set()
    secs = []
    for s in tags:
        if s["name"].lower() == "end":
            continue
        sung = [line_t[i] for i in range(s["line0"], s["line1"]) if line_t[i]["t0"] is not None]
        secs.append({"name": s["name"], "tag": s["tag"], "first": sung[0]["t0"] if sung else None,
                     "last": max(x["t1"] for x in sung) if sung else None})
    prev_last = 0.0
    for s in secs:
        if s["first"] is None:
            continue
        bar = int(np.searchsorted(downbeats, s["first"] - PICKUP))   # the first downbeat >= t - 0.8 s
        bar = min(bar, len(downbeats) - 1)
        # a segment change up to 4 bars earlier, but never inside the previous section's words
        near = [b for b in boundaries if bar - 4 <= b <= bar and downbeats[b] >= prev_last - 0.3]
        prev_last = s["last"]
        if near:
            bar = max(near, key=lambda b: nov[b])
            used.add(bar)
        s["bar0"] = bar
    if secs and "bar0" not in secs[0]:
        secs[0]["bar0"] = 0
    secs[0]["bar0"] = 0
    for k, s in enumerate(secs):
        if "bar0" in s:
            continue
        # an instrumental tag: after the previous section's last word, at a segment change if there is one
        prev_last = next((x["last"] for x in reversed(secs[:k]) if x["last"]), 0.0)
        nxt = next((x["bar0"] for x in secs[k + 1:] if "bar0" in x), len(downbeats))
        lo = bar_of(downbeats, prev_last) + 1
        cands = [b for b in boundaries if lo <= b < nxt]
        s["bar0"] = max(cands, key=lambda b: nov[b]) if cands else min(lo, nxt)
        used.update(cands[:1])
        s["placed"] = "segment change" if cands else "after the last word"
    out_secs = []
    for k, s in enumerate(secs):
        b0 = s["bar0"]
        b1 = secs[k + 1]["bar0"] if k + 1 < len(secs) else len(downbeats)
        t0 = 0.0 if k == 0 else float(downbeats[b0])
        t1 = float(downbeats[b1]) if b1 < len(downbeats) else duration
        energy = float(levels["mix"][b0:max(b0 + 1, b1)].mean() / levels["mix"].max())
        out_secs.append({"name": s["name"], "t0": t0, "t1": t1, "energy": round(energy, 2), "bar0": b0,
                         "bar1": b1, "source": "lyrics-tag"})
    beats_doc["sections"] = out_secs
    beats_doc["segment_changes"] = [{"bar": b, "t": float(downbeats[b]), "novelty": round(float(nov[b]), 2)}
                                    for b in sorted(boundaries)]
    common.write_json(d / "beats.json", beats_doc)

    # ---- report ----
    def word_before(t):
        ws = [w for w in words if w["t1"] is not None and w["t1"] <= t]
        return f"after '{ws[-1]['w']}'" if ws else "before the first word"

    def describe(s, prev):
        b0, b1 = s["bar0"], max(s["bar0"] + 1, s["bar1"])
        lv = {k: digits[k][b0:b1].mean() for k in common.STEMS}
        parts = [f"{k} {lv[k]:.0f}" for k in common.STEMS]
        notes = []
        if prev:
            pb0, pb1 = prev["bar0"], max(prev["bar0"] + 1, prev["bar1"])
            for k in ("drums", "bass"):
                p = digits[k][pb0:pb1].mean()
                if p >= 3 and lv[k] < 1.5:
                    notes.append(f"the {k} drop out")
                elif p < 1.5 and lv[k] >= 3:
                    notes.append(f"the {k} come in")
        dr = digits["drums"]
        for b in range(b0 + 1, b1):
            if dr[b - 1] >= 4 and dr[b] <= 1:
                notes.append(f"the beat stops at bar {b} {word_before(downbeats[b])}")
            if dr[b - 1] <= 1 and dr[b] >= 4:
                notes.append(f"the beat comes back at bar {b}")
        return ", ".join(parts) + (": " + "; ".join(notes) if notes else "")

    md = ["## Sections and hits", "",
          f"{len(out_secs)} sections from the lyric's tags (Suno's [End] tag skipped), snapped to downbeats. "
          f"Segmenter changes used: {len(used)}; the others, which no tag explains, are listed below.", "",
          "| section | start | end | bars | energy | what the track does (stem levels 0-9) |",
          "|---|---|---|---|---|---|"]
    for k, s in enumerate(out_secs):
        note = secs[k].get("placed")
        md.append(f"| {s['name']}{' (' + note + ')' if note else ''} | {common.fmt_t(s['t0'])} | "
                  f"{common.fmt_t(s['t1'])} | {s['bar0']}-{s['bar1']} | {s['energy']:.2f} | "
                  f"{describe(s, out_secs[k - 1] if k else None)} |")
    others = [b for b in sorted(boundaries) if b not in used]
    md += ["", "Other segment changes (bar, time, novelty): " +
           (", ".join(f"{b} {common.fmt_t(downbeats[b])} {nov[b]:.2f}" for b in others) or "none")]
    md += ["", "**Vocal gaps of 2 s or more** (instrumental shots and title cards go here):", ""]
    for g in words_doc["gaps"]:
        md.append(f"- {common.fmt_t(g['t0'])}-{common.fmt_t(g['t1'])} ({g['t1'] - g['t0']:.1f} s)")
    md += ["", "**Energy per bar** (0-9, each stem against its own loudest bar; one character per bar, sections "
           "split by `|`):", "", "```"]
    for name in ("mix",) + common.STEMS:
        row = "|".join("".join(str(x) for x in digits[name][s["bar0"]:s["bar1"]]) for s in out_secs)
        md.append(f"{name:7s}{row}")
    md += ["```", "", f"**Hits:** {len(kick)} kicks, {len(snare)} snares, {len(hat)} hats, {len(hits)} impacts, "
           f"{len(risers)} risers, {len(fills)} fills, {len(entries)} vocal entries.", "",
           "| impact | score | bar | mix level of its bar (0-9) | on a downbeat |", "|---|---|---|---|---|"]
    quiet_hits = 0
    for h in hits:
        b = bar_of(downbeats, h["t"])
        lvl = digits["mix"][b]
        quiet_hits += lvl < 6
        on = min(abs(downbeats - h["t"])) < 0.01
        md.append(f"| {common.fmt_t(h['t'])} | {h['score']:.2f} | {b} | {lvl}{'  (quiet: check)' if lvl < 6 else ''}"
                  f" | {'yes' if on else 'no'} |")
    md += ["", f"Done-when check: {len(hits) - quiet_hits} of {len(hits)} impacts sit in a loud bar (mix 6-9)."]
    # verse entries on beat 1
    on1 = 0
    starts = [ln["t0"] for ln in words_doc["lines"] if ln["t0"] is not None]
    for t in starts:
        b = nearest(beats, t)
        i = int(np.where(beats == b)[0][0])
        on1 += (i - beats_doc["downbeat_phase"]) % 4 == 0
    md.append(f"Line starts nearest beat 1: {on1} of {len(starts)} (chance is 1 in 4). Section starts are on "
              f"downbeats by construction.")
    md += ["", "Risers: " + (", ".join(f"{common.fmt_t(r['t0'])}-{common.fmt_t(r['t1'])} ({r['kind']}) lands "
                                       f"{common.fmt_t(r['land'])}" for r in risers) or "none")]
    md += ["", f"Ran in {time.time() - t_start:.0f} s on CPU."]
    common.update_report(take, "sections", "\n".join(md))
    print("\n".join(md[:5 + len(out_secs)]))
    print(md[-6] if len(md) > 6 else "")


if __name__ == "__main__":
    main()
