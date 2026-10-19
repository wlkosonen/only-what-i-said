#!/usr/bin/env python3
"""Timed words and the ear check (wiki/toolkit, "5. Timed words and the ear check").

    media/cache/listen-venv/bin/python production/tools/listen/align.py a1 [--lyrics production/lyrics/v2.md]
        [--whisper turbo] [--redo]

In: the vocal stem (run stems.py first) and the lyric sheet. Out, in media/song/analysis/<take>/:
  words.json     every sheet word with t0, t1, conf and src (w2v | whisper | interp | manual), per formats.md
  earcheck.json  the flagged words, most urgent first, with reasons and the second aligner's opinion, plus at most
                 five 10-20 s spots to play to a person
  sung.json      what the take really sings, line by line against the sheet (ok/spelling/changed/extra/missing/
                 not heard), from Whisper. Advice only: never apply a change nobody has heard.
  report.md      the "align" block
  cache: emissions-w2v.npy, emissions-mms.npy, whisper.json (delete or --redo to recompute)

How (constants from the spec):
  1. Forced alignment: facebook/wav2vec2-large-960h-lv60-self gives character log-probabilities every 20 ms; a CTC
     Viterbi pass walks the sheet's characters through them. conf = mean probability over the word's frames.
  2. A second aligner, torchaudio's MMS_FA, run the same way; it is only a witness (agree within 0.3 s = keep).
  3. Whisper (openai-whisper, word timestamps) for what is heard. Merge per word:
     conf >= 0.5 keep w2v; else Whisper's end (and start, moved to the first 10 ms frame over 0.3 x the word's vocal
     peak for words over 0.45 s, unless w2v's start falls inside the word); else an even share of the gap between
     placed neighbours in the line; else unplaced.
  4. Flags, most urgent first: letters, missing, order, gap, verylow, length, lowconf.

Manual word fixes go in production/song/listen/<take>.json as {"words": [{"i", "w", "t0", "t1", "note"}]} and
survive re-runs; "name_map": {"heard": ["sheet", "words"]} maps names Whisper spells its own way.
"""

import argparse
import difflib
import json
import time

import common

FRAME = 0.02            # wav2vec2 / MMS frame, s
KEEP_CONF = 0.5         # w2v confidence kept without question
LONG_WORD = 0.45        # Whisper words longer than this get their start moved to the vocal onset
ONSET_FRAC = 0.3        # ... the first 10 ms frame over this fraction of the word's vocal peak
AGREE = 0.3             # two aligners within this many seconds agree
GAP_LINE = 1.0          # gap flag: silence inside one line
GAP_VOCAL = 2.0         # vocal gaps listed for instrumental shots
FLAGS = ["letters", "missing", "order", "gap", "verylow", "length", "lowconf"]
REASONS = {
    "letters": "the sheet line has no letters (the sheet is wrong)",
    "missing": "no time",
    "order": "starts more than 0.05 s before the previous word",
    "gap": "more than 1 s after the previous word of its line (delay throw, echo or the wrong repeat?)",
    "verylow": "confidence under 0.1 (the flag that mattered most on ESCAPE VELOCITY)",
    "length": "longer than 1.2 s (swallowed a pause or a neighbour's slot?)",
    "lowconf": "confidence under 0.5, or a time from Whisper or interpolation",
}


# ---- emissions ---------------------------------------------------------------------------------------------------

def chunked(model_fn, audio, chunk_s=20.0, ctx_s=2.0, sr=16000):
    """Run a 20 ms-frame CTC model over long audio in overlapping chunks; returns [T, V] log-probs."""
    import numpy as np
    torch = common.torch_cpu()
    hop = int(FRAME * sr)
    chunk, ctx = int(chunk_s * sr) // hop * hop, int(ctx_s * sr) // hop * hop
    n_frames = len(audio) // hop
    out = None
    for c in range(0, len(audio), chunk):
        s0, s1 = max(0, c - ctx), min(len(audio), c + chunk + ctx)
        seg = torch.from_numpy(audio[s0:s1].copy())[None]
        with torch.no_grad():
            lp = torch.log_softmax(model_fn(seg), dim=-1)[0].numpy()
        if out is None:
            out = np.full((n_frames, lp.shape[1]), -1e4, dtype=np.float32)
            out[:, 0] = 0.0
        g0 = s0 // hop
        lo, hi = c // hop, min(n_frames, (c + chunk) // hop)
        take = lp[lo - g0: hi - g0]
        out[lo: lo + len(take)] = take
    return out


def w2v_emissions(audio, name):
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    proc = Wav2Vec2Processor.from_pretrained(name)
    model = Wav2Vec2ForCTC.from_pretrained(name).eval()

    def run(seg):
        seg = (seg - seg.mean()) / (seg.std() + 1e-7)
        return model(seg).logits

    vocab = proc.tokenizer.get_vocab()
    labels = [None] * len(vocab)
    for k, v in vocab.items():
        labels[v] = k
    return chunked(run, audio), labels, proc.tokenizer.pad_token_id


def mms_emissions(audio):
    import torchaudio
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=False).eval()
    labels = list(bundle.get_labels(star=None))

    def run(seg):
        return model(seg)[0]

    return chunked(run, audio), labels, 0


# ---- CTC Viterbi -------------------------------------------------------------------------------------------------

def viterbi(lp, tokens, blank):
    """Best CTC path of `tokens` through log-probs lp [T, V]. Returns the state index per frame (2k+1 = token k)."""
    import numpy as np
    T = lp.shape[0]
    ext = np.full(2 * len(tokens) + 1, blank)
    ext[1::2] = tokens
    S = len(ext)
    emit = lp[:, ext]
    skip = np.zeros(S, bool)
    skip[2:] = (ext[2:] != blank) & (ext[2:] != ext[:-2])
    alpha = np.full(S, -np.inf, np.float32)
    alpha[0], alpha[1] = emit[0, 0], emit[0, 1]
    back = np.zeros((T, S), np.int8)
    ninf = np.float32(-np.inf)
    for t in range(1, T):
        a1 = np.concatenate(([ninf], alpha[:-1]))
        a2 = np.concatenate(([ninf, ninf], alpha[:-2]))
        a2[~skip] = ninf
        stack = np.stack([alpha, a1, a2])
        b = stack.argmax(0)
        back[t] = b
        alpha = stack[b, np.arange(S)] + emit[t]
    s = S - 1 if alpha[S - 1] >= alpha[S - 2] else S - 2
    path = np.empty(T, np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= int(back[t, s])
    return path, emit[np.arange(T), path]


def align_words(lp, labels, blank, words, delim=None):
    """Force-align sheet words; returns per word (t0, t1, conf) or None when the word has no usable letters."""
    import numpy as np
    index = {l: i for i, l in enumerate(labels) if l is not None}
    upper = any(l and l.isupper() for l in labels)
    tokens, owner = [], []
    for wi, w in enumerate(words):
        letters = "".join(common.spoken(w["w"]))
        ids = [index[c] for c in (letters.upper() if upper else letters) if c in index]
        if not ids:
            continue
        if delim is not None and tokens:
            tokens.append(index[delim])
            owner.append(-1)
        tokens += ids
        owner += [wi] * len(ids)
    path, score = viterbi(lp, np.array(tokens), blank)
    is_tok = path % 2 == 1
    tok_of_frame = np.where(is_tok, path // 2, -1)
    owner = np.array(owner)
    frame_word = np.where(is_tok, owner[np.clip(tok_of_frame, 0, None)], -1)
    out = [None] * len(words)
    prob = np.exp(score)
    for wi in range(len(words)):
        f = np.nonzero(frame_word == wi)[0]
        if len(f):
            out[wi] = (f[0] * FRAME, (f[-1] + 1) * FRAME, float(prob[f].mean()))
    return out


# ---- Whisper and matching ----------------------------------------------------------------------------------------

def run_whisper(audio, size):
    import whisper
    model = whisper.load_model(size, device="cpu", download_root=str(common.CACHE / "whisper"))
    res = model.transcribe(audio, language="en", word_timestamps=True, fp16=False,
                           condition_on_previous_text=False, verbose=False)
    words = []
    for seg in res["segments"]:
        for w in seg.get("words", []):
            words.append({"w": w["word"].strip(), "t0": float(w["start"]), "t1": float(w["end"]),
                          "p": float(w.get("probability", 0.0))})
    return {"model": size, "text": res["text"], "words": words}


def norm(w):
    return w.replace("'", "").replace("-", "")


def heard_tokens(whisper_words, name_map):
    """Clean the heard words: digits spelled out, hand-mapped names; one heard word may become several."""
    out = []
    for h in whisper_words:
        c = common.clean_word(h["w"])
        if not c:
            continue
        parts = name_map.get(c) or common.spoken(c)
        n = len(parts)
        for k, p in enumerate(parts):
            d = (h["t1"] - h["t0"]) / n
            out.append({"w": norm(common.clean_word(p)), "raw": h["w"], "t0": h["t0"] + k * d,
                        "t1": h["t0"] + (k + 1) * d, "p": h["p"]})
    return out


def match(sheet, heard):
    """Global alignment of heard words to sheet words. Returns pairs (sheet_i | None, heard_j | None, kind) in order,
    kind in ok / spelling / changed / extra / missing. A heard word equal to 2-4 sheet words joined counts for all."""
    S = [norm(w["w"]) for w in sheet]
    H = [h["w"] for h in heard]
    n, m = len(S), len(H)
    NEG = -1e9
    score = [[NEG] * (m + 1) for _ in range(n + 1)]
    move = [[None] * (m + 1) for _ in range(n + 1)]
    score[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            cur = score[i][j]
            if cur == NEG:
                continue
            cands = []
            if i < n and j < m:
                if S[i] == H[j]:
                    cands.append((i + 1, j + 1, 2.0, "ok"))
                else:
                    r = difflib.SequenceMatcher(None, S[i], H[j]).ratio()
                    cands.append((i + 1, j + 1, 1.0 if r >= 0.75 else -0.5, "spelling" if r >= 0.75 else "changed"))
                for k in range(2, 5):
                    if i + k <= n and "".join(S[i:i + k]) == H[j]:
                        cands.append((i + k, j + 1, 2.0 * k, f"split{k}"))
            if i < n:
                cands.append((i + 1, j, -1.0, "missing"))
            if j < m:
                cands.append((i, j + 1, -1.0, "extra"))
            for ni, nj, s, kind in cands:
                if cur + s > score[ni][nj]:
                    score[ni][nj] = cur + s
                    move[ni][nj] = (i, j, kind)
    pairs, i, j = [], n, m
    while i or j:
        pi, pj, kind = move[i][j]
        if kind.startswith("split"):
            k = int(kind[5:])
            for q in range(k - 1, -1, -1):
                pairs.append((pi + q, pj, "ok"))
        elif kind == "missing":
            pairs.append((pi, None, kind))
        elif kind == "extra":
            pairs.append((None, pj, kind))
        else:
            pairs.append((pi, pj, kind))
        i, j = pi, pj
    return pairs[::-1]


# ---- merge, flags, report ----------------------------------------------------------------------------------------

def vocal_onset(env, t0, t1):
    i0, i1 = int(t0 / 0.01), max(int(t0 / 0.01) + 1, int(t1 / 0.01))
    seg = env[i0:i1]
    if not len(seg):
        return t0
    above = (seg >= ONSET_FRAC * seg.max()).nonzero()[0]
    return t0 + (above[0] if len(above) else 0) * 0.01


def merge(words, w2v, mms, heard, pairs, env, manual):
    heard_of = {}
    for si, hj, kind in pairs:
        if si is not None and hj is not None and kind in ("ok", "spelling"):
            heard_of[si] = heard[hj]
    out = []
    for w in words:
        i = w["i"]
        rec = {"i": i, "w": w["w"], "line": w["line"], "t0": None, "t1": None, "conf": 0.0, "src": None}
        a = w2v[i]
        if a:
            rec["conf"] = a[2]
            rec["w2v"] = [a[0], a[1]]
        if mms[i]:
            rec["mms"] = [mms[i][0], mms[i][1], round(mms[i][2], 3)]
        h = heard_of.get(i)
        if h:
            rec["whisper"] = [h["t0"], h["t1"]]
        if a and a[2] >= KEEP_CONF:
            rec.update(t0=a[0], t1=a[1], src="w2v")
        elif h:
            t1 = h["t1"]
            if a and h["t0"] <= a[0] < t1:
                t0 = a[0]
            elif t1 - h["t0"] > LONG_WORD:
                t0 = vocal_onset(env, h["t0"], t1)
            else:
                t0 = h["t0"]
            rec.update(t0=t0, t1=t1, src="whisper")
        out.append(rec)
    # interpolation inside a line
    k = 0
    while k < len(out):
        if out[k]["src"] is None:
            j = k
            while j < len(out) and out[j]["src"] is None and out[j]["line"] == out[k]["line"]:
                j += 1
            prev = out[k - 1] if k and out[k - 1]["line"] == out[k]["line"] and out[k - 1]["src"] else None
            nxt = out[j] if j < len(out) and out[j]["line"] == out[k]["line"] and out[j]["src"] else None
            if prev and nxt:
                span = (nxt["t0"] - prev["t1"]) / (j - k)
                for q in range(k, j):
                    out[q].update(t0=prev["t1"] + (q - k) * span, t1=prev["t1"] + (q - k + 1) * span, src="interp")
            k = j
        else:
            k += 1
    for fix in manual:
        r = out[fix["i"]] if 0 <= fix["i"] < len(out) else None
        if not r or r["w"] != common.clean_word(fix["w"]):
            print(f"manual fix for word {fix['i']} ({fix['w']!r}) no longer matches the sheet; skipped")
            continue
        r.update(t0=fix["t0"], t1=fix["t1"], src="manual", note=fix.get("note", ""))
    return out


def flag(words, lines):
    flags = {w["i"]: [] for w in words}
    letters_lines = {ln["line"] for ln in lines if not any(common.spoken(w) for w in ln["words"])}
    prev = None
    for w in words:
        f = flags[w["i"]]
        if w["src"] == "manual":
            continue
        if w["line"] in letters_lines:
            f.append("letters")
        if w["t0"] is None:
            f.append("missing")
            continue
        if prev and w["t0"] < prev["t0"] - 0.05:
            f.append("order")
        if prev and prev["line"] == w["line"] and w["t0"] - prev["t1"] > GAP_LINE:
            f.append("gap")
        if w["conf"] < 0.1:
            f.append("verylow")
        if w["t1"] - w["t0"] > 1.2:
            f.append("length")
        if w["conf"] < KEEP_CONF or w["src"] in ("whisper", "interp"):
            f.append("lowconf")
        prev = w
    return flags


def second_opinion(w):
    """How far the MMS witness is from the chosen start, or None."""
    if w["t0"] is None or "mms" not in w:
        return None
    return w["mms"][0] - w["t0"]


def spots(items, max_spots=5):
    """Group the most urgent flags into at most five 10-20 s windows to play to a person."""
    chosen = []
    for it in items:
        t = it["t0"] if it["t0"] is not None else it.get("near")
        if t is None:
            continue
        for s in chosen:
            if s["t0"] <= t <= s["t1"] - 2:
                s["words"].append(it["i"])
                break
        else:
            if len(chosen) < max_spots:
                chosen.append({"t0": max(0.0, t - 5), "t1": t + 10, "words": [it["i"]],
                               "why": f"{it['w']!r}: {', '.join(it['flags'])}"})
    return sorted(chosen, key=lambda s: s["t0"])


def sung_report(lines, sheet, heard, pairs):
    """What the take really sings, line by line."""
    by_line = {ln["line"]: [] for ln in lines}
    last_line = lines[0]["line"]
    for si, hj, kind in pairs:
        if si is not None:
            last_line = sheet[si]["line"]
        # a heard word that matches nothing is counted against the line before it
        by_line[last_line].append((si, hj, kind))
    out = []
    for ln in lines:
        ps = by_line[ln["line"]]
        kinds = [k for _, _, k in ps]
        heard_txt = " ".join(heard[hj]["raw"] for _, hj, _ in ps if hj is not None)
        if all(k == "ok" for k in kinds):
            verdict = "ok"
        elif all(k == "missing" for k in kinds if k != "extra") and "ok" not in kinds:
            verdict = "not heard"
        elif "changed" in kinds:
            verdict = "changed"
        elif "missing" in kinds:
            verdict = "missing"
        elif "extra" in kinds:
            verdict = "extra"
        else:
            verdict = "spelling"
        ts = [heard[hj]["t0"] for _, hj, _ in ps if hj is not None]
        out.append({"line": ln["line"], "verdict": verdict, "sheet": ln["text"], "heard": heard_txt,
                    "t0": min(ts) if ts else None})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("take")
    ap.add_argument("--lyrics", default=str(common.LYRICS))
    ap.add_argument("--w2v", default="facebook/wav2vec2-large-960h-lv60-self")
    ap.add_argument("--whisper", default="turbo", help="openai-whisper model name (turbo, medium, large-v3, ...)")
    ap.add_argument("--redo", action="store_true", help="recompute the cached emissions and transcript")
    args = ap.parse_args()

    import numpy as np
    d = common.out_dir(args.take)
    cfg = common.settings(args.take)
    lines, sections = common.read_lyrics(args.lyrics)
    words = common.sheet_words(lines)
    audio, sr = common.load(common.stem_path(args.take, "vocals"), sr=16000)
    env = common.envelope(audio, sr)
    timings = {}

    t = time.time()
    cache = d / "emissions-w2v.npy"
    if cache.exists() and not args.redo:
        lp_w2v = np.load(cache)
        from transformers import Wav2Vec2Processor
        vocab = Wav2Vec2Processor.from_pretrained(args.w2v).tokenizer.get_vocab()
        labels = [None] * len(vocab)
        for k, v in vocab.items():
            labels[v] = k
        blank = vocab["<pad>"]
    else:
        lp_w2v, labels, blank = w2v_emissions(audio, args.w2v)
        np.save(cache, lp_w2v)
    w2v = align_words(lp_w2v, labels, blank, words, delim="|")
    timings["wav2vec2"] = time.time() - t

    t = time.time()
    cache = d / "emissions-mms.npy"
    import torchaudio
    mms_labels = list(torchaudio.pipelines.MMS_FA.get_labels(star=None))
    if cache.exists() and not args.redo:
        lp_mms = np.load(cache)
    else:
        lp_mms, mms_labels, _ = mms_emissions(audio)
        np.save(cache, lp_mms)
    mms = align_words(lp_mms, mms_labels, 0, words)
    timings["mms"] = time.time() - t

    t = time.time()
    cache = d / "whisper.json"
    if cache.exists() and not args.redo:
        wh = json.loads(cache.read_text())
    else:
        wh = run_whisper(audio, args.whisper)
        cache.write_text(json.dumps(wh, indent=1, ensure_ascii=False))
    timings["whisper"] = time.time() - t

    heard = heard_tokens(wh["words"], cfg.get("name_map", {}))
    pairs = match(words, heard)
    out = merge(words, w2v, mms, heard, pairs, env, cfg.get("words", []))
    flags = flag(out, lines)

    # lines and vocal gaps
    line_recs = []
    for ln in lines:
        ws = [w for w in out if w["line"] == ln["line"] and w["t0"] is not None]
        line_recs.append({"line": ln["line"], "text": ln["text"], "section": sections[ln["section"]]["name"],
                          "t0": min((w["t0"] for w in ws), default=None),
                          "t1": max((w["t1"] for w in ws), default=None)})
    placed = sorted((w for w in out if w["t0"] is not None), key=lambda w: w["t0"])
    gaps = []
    if placed and placed[0]["t0"] >= GAP_VOCAL:
        gaps.append({"t0": 0.0, "t1": placed[0]["t0"], "after_word": None})
    for a, b in zip(placed, placed[1:]):
        if b["t0"] - a["t1"] >= GAP_VOCAL:
            gaps.append({"t0": a["t1"], "t1": b["t0"], "after_word": a["i"]})
    dur = len(audio) / sr
    if placed and dur - placed[-1]["t1"] >= GAP_VOCAL:
        gaps.append({"t0": placed[-1]["t1"], "t1": dur, "after_word": placed[-1]["i"]})

    common.write_json(d / "words.json", {"words": out, "lines": line_recs, "gaps": gaps})

    # ear check
    items = []
    for w in out:
        f = flags[w["i"]]
        if not f:
            continue
        delta = second_opinion(w)
        near = None
        if w["t0"] is None:
            near = (w.get("w2v") or w.get("mms") or [None])[0]
        items.append({"i": w["i"], "w": w["w"], "line": w["line"], "t0": w["t0"], "t1": w["t1"],
                      "conf": round(w["conf"], 3), "src": w["src"], "flags": f, "near": near,
                      "reasons": [REASONS[x] for x in f], "mms_delta": None if delta is None else round(delta, 3),
                      "mms_agrees": None if delta is None else abs(delta) <= AGREE,
                      "whisper_heard": "whisper" in w, "line_text": lines[w["line"]]["text"],
                      "status": "open", "note": ""})
    items.sort(key=lambda it: (FLAGS.index(it["flags"][0]), it["mms_agrees"] is True, it["conf"]))
    sung = sung_report(lines, words, heard, pairs)
    common.write_json(d / "earcheck.json", {"items": items, "spots": spots(items)})
    common.write_json(d / "sung.json", {"whisper_model": wh["model"], "lines": sung})

    # report
    n = len(out)
    by_src = {s: sum(1 for w in out if w["src"] == s) for s in ("w2v", "whisper", "interp", "manual", None)}
    confs = [w["conf"] for w in out if "w2v" in w]
    both = [w for w in out if "w2v" in w and "mms" in w]
    within = sum(1 for w in both if abs(w["w2v"][0] - w["mms"][0]) <= 0.10)
    agree = sum(1 for w in both if abs(w["w2v"][0] - w["mms"][0]) <= AGREE)
    wh_pairs = [w for w in out if "w2v" in w and "whisper" in w]
    wh_err = [w["whisper"][0] - w["w2v"][0] for w in wh_pairs if w["conf"] >= KEEP_CONF]
    count = {f: sum(1 for it in items if f in it["flags"]) for f in FLAGS}
    verdicts = {}
    for s in sung:
        verdicts[s["verdict"]] = verdicts.get(s["verdict"], 0) + 1
    md = ["## Timed words and the ear check", "",
          f"{n} sheet words in {len(lines)} lines. Placed: {by_src['w2v']} by wav2vec2 (conf >= 0.5), "
          f"{by_src['whisper']} from Whisper, {by_src['interp']} interpolated, {by_src['manual']} manual; "
          f"{by_src[None]} unplaced.",
          f"Mean wav2vec2 confidence {np.mean(confs):.2f} (spec: 0.64 and 0.75 on the gallery's sung takes).",
          f"Second aligner (MMS_FA) starts within 0.10 s of wav2vec2 for {100 * within / max(1, len(both)):.1f}% of "
          f"words, within 0.3 s for {100 * agree / max(1, len(both)):.1f}%. This is agreement between two models, "
          f"not accuracy: only a person's ear gives that.",
          f"Whisper heard {len(wh_pairs)} of the sheet words; its starts run {np.mean(wh_err) if wh_err else 0:+.2f} s "
          f"from confident wav2vec2 starts (spec: -0.33 s).",
          f"Timings on CPU ({common.THREADS} threads): " +
          ", ".join(f"{k} {v:.0f} s" for k, v in timings.items()) + " (cached steps show load time only).", "",
          f"**Ear check:** {len(items)} words flagged: " + ", ".join(f"{count[f]} {f}" for f in FLAGS if count[f]) +
          ". Most urgent first; `earcheck.json` has them all, with a status and note to fill in.", "",
          "| # | t0 | word | line | flags | conf | src | MMS delta |", "|---|---|---|---|---|---|---|---|"]
    for it in items[:25]:
        md.append(f"| {it['i']} | {common.fmt_t(it['t0'])} | {it['w']} | {it['line']} | {' '.join(it['flags'])} | "
                  f"{it['conf']:.2f} | {it['src'] or '-'} | "
                  f"{'-' if it['mms_delta'] is None else f'{it['mms_delta']:+.2f}'} |")
    md += ["", "**Spots to play to Lati** (say ok, early or late for each):", ""]
    for s in spots(items):
        md.append(f"- {common.fmt_t(s['t0'])}-{common.fmt_t(s['t1'])}: {s['why']} "
                  f"({len(s['words'])} flagged word(s) inside)")
    md += ["", "**What the take sings** (Whisper vs the sheet; advice only, never apply a change nobody has heard): " +
           ", ".join(f"{v} {k}" for k, v in sorted(verdicts.items())), "",
           "| line | at | verdict | sheet | heard |", "|---|---|---|---|---|"]
    for s in sung:
        if s["verdict"] != "ok":
            md.append(f"| {s['line']} | {common.fmt_t(s['t0'])} | {s['verdict']} | {s['sheet']} | {s['heard']} |")
    common.update_report(args.take, "align", "\n".join(md))
    print("\n".join(md[:8]))


if __name__ == "__main__":
    main()
