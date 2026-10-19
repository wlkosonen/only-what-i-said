"""Shared helpers for the listening tools: paths, audio, the lyric parser, JSON and the report.

Every tool takes a take name (a1, a2, ...). The master is media/song/<take>.wav; everything a tool writes goes to
media/song/analysis/<take>/ (gitignored). Overrides that should survive re-runs (tempo range, downbeat phase, hit
add/drop, heard-word name map, manual word times) live in production/song/listen/<take>.json, which is small text and
belongs in git. See README.md.

Torch runs on CPU on purpose: importing this module hides every GPU before torch loads.
"""

import json
import os
import re
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HIP_VISIBLE_DEVICES"] = ""

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "media/cache/listen-models"
os.environ.setdefault("TORCH_HOME", str(CACHE / "torch"))
os.environ.setdefault("HF_HOME", str(CACHE / "hf"))

LYRICS = ROOT / "production/lyrics/v2.md"
STEMS = ("vocals", "drums", "bass", "other")
THREADS = int(os.environ.get("LISTEN_THREADS", "8"))


def master_path(take):
    return ROOT / f"media/song/{take}.wav"


def out_dir(take):
    d = ROOT / f"media/song/analysis/{take}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stem_path(take, name):
    return out_dir(take) / "stems" / f"{name}.wav"


def settings(take):
    """The per-take overrides, or an empty dict."""
    p = ROOT / f"production/song/listen/{take}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def torch_cpu():
    import torch
    torch.set_num_threads(THREADS)
    return torch


# ---- audio -------------------------------------------------------------------------------------------------------

def load(path, sr=None, mono=True):
    """Read a WAV as float32 (samples, channels) or (samples,) if mono; resample to sr with a polyphase filter."""
    import numpy as np
    import soundfile as sf
    from math import gcd
    from scipy.signal import resample_poly
    x, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if mono:
        x = x.mean(axis=1)
    if sr and sr != rate:
        g = gcd(sr, rate)
        x = resample_poly(x, sr // g, rate // g, axis=0).astype(np.float32)
        rate = sr
    return x, rate


def envelope(x, sr, hop_s=0.01):
    """RMS envelope, one value per hop."""
    import numpy as np
    hop = int(sr * hop_s)
    n = len(x) // hop
    return np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))


# ---- lyrics ------------------------------------------------------------------------------------------------------

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
       "seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n):
    n = int(n)
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], "hundred"] + (number_words(n % 100) if n % 100 else [])
    return number_words(n // 1000) + ["thousand"] + (number_words(n % 1000) if n % 1000 else [])


def clean_word(token):
    """Lower case, letters and inner apostrophes/hyphens only: '(only' -> 'only', "'cause" -> "'cause"."""
    t = token.lower().replace("’", "'")
    t = re.sub(r"[^a-z0-9'\-]", "", t)
    return t.strip("-")


def spoken(word):
    """The letters a sung word is made of, as a list of sub-words: digits spelled out, hyphens split."""
    out = []
    for part in re.split(r"-+", word):
        if part.isdigit():
            out += number_words(part)
        elif part.strip("'"):
            out.append(part)
    return out


def read_lyrics(path=LYRICS):
    """Parse the lyric sheet: the first ```lyrics fence of a markdown file, or a whole text file.

    Blank lines and lines starting with '[' are skipped (formats.md); parentheses are sung, so only the brackets go.
    Returns (lines, sections): lines = [{line, text, section, words}], sections = [{name, tag, line0, line1}] in
    sheet order, including tags with no lines under them (line0 == line1, an instrumental section).
    """
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(r"```lyrics\n(.*?)```", text, re.S)
    body = m.group(1) if m else text
    lines, sections = [], []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("["):
            tag = s.strip("[]")
            name = tag.split(" - ")[0].strip()
            if sections:
                sections[-1]["line1"] = len(lines)
            sections.append({"name": name, "tag": tag, "line0": len(lines), "line1": len(lines)})
            continue
        words = [w for w in (clean_word(t) for t in s.split()) if w]
        lines.append({"line": len(lines), "text": s, "section": len(sections) - 1, "words": words})
        if sections:
            sections[-1]["line1"] = len(lines)
    return lines, sections


def sheet_words(lines):
    """Flatten the sheet into [{i, w, line}]."""
    out = []
    for ln in lines:
        for w in ln["words"]:
            out.append({"i": len(out), "w": w, "line": ln["line"]})
    return out


# ---- output ------------------------------------------------------------------------------------------------------

def write_json(path, obj):
    """JSON with times rounded to the millisecond, one record per line for the long lists."""
    def r(v):
        if hasattr(v, "item") and not isinstance(v, (list, dict)):
            v = v.item()   # numpy scalars
        if isinstance(v, float):
            return round(v, 3)
        if isinstance(v, dict):
            return {k: r(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [r(x) for x in v]
        return v
    obj = r(obj)
    parts = []
    for k, v in obj.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            inner = ",\n  ".join(json.dumps(x, ensure_ascii=False) for x in v)
            parts.append(f'"{k}": [\n  {inner}\n ]')
        else:
            parts.append(f'"{k}": {json.dumps(v, ensure_ascii=False)}')
    Path(path).write_text("{" + ",\n ".join(parts) + "}\n", encoding="utf-8")


def update_report(take, key, markdown):
    """Replace this tool's block in analysis/<take>/report.md, keeping the other tools' blocks in a fixed order."""
    order = ["stems", "align", "beatmap", "sections", "display"]
    p = out_dir(take) / "report.md"
    blocks = {}
    if p.exists():
        for k, body in re.findall(r"<!-- (\w+) -->\n(.*?)<!-- /\1 -->", p.read_text(encoding="utf-8"), re.S):
            blocks[k] = body
    blocks[key] = markdown.rstrip() + "\n"
    head = f"# Listening report: {take}\n\nWritten by production/tools/listen/. Nothing here has been heard by a " \
           f"person yet unless it says so.\n\n"
    body = "".join(f"<!-- {k} -->\n{blocks[k]}<!-- /{k} -->\n\n" for k in order if k in blocks)
    p.write_text(head + body, encoding="utf-8")


# ---- onsets ------------------------------------------------------------------------------------------------------

ONSET_SR = 22050
ONSET_HOP = 88          # 3.99 ms frames: the spec fits beat phase in 4 ms steps
ONSET_FFT = 1024
KICK_FLOOR = 0.5       # kick onsets weaker than half the 99th-percentile flux were bass bleed on a1 (median 0.36 vs 1.2)


def spectrum(x, sr=ONSET_SR):
    """Magnitude STFT in ~4 ms frames: (freqs, S[freq, frame], fps)."""
    import librosa
    import numpy as np
    hop = round(sr * ONSET_HOP / ONSET_SR)
    n_fft = ONSET_FFT * sr // ONSET_SR
    S = np.abs(librosa.stft(x, n_fft=n_fft, hop_length=hop, center=True))
    return librosa.fft_frequencies(sr=sr, n_fft=n_fft), S, sr / hop


def band_flux(freqs, S, lo, hi):
    """Spectral flux (half-wave rectified log-magnitude rise) inside lo..hi Hz, scaled so its 99th percentile is 1."""
    import numpy as np
    band = (freqs >= lo) & (freqs <= hi)
    L = np.log1p(100 * S[band])
    flux = np.maximum(0, np.diff(L, axis=1, prepend=L[:, :1])).sum(axis=0)
    return flux / (np.percentile(flux, 99) + 1e-9)


def pick(flux, fps, delta=0.15, wait_s=0.05, floor=0.0):
    """Onset times (s) from a flux curve: local maxima over a moving average + delta, and at least `floor` high."""
    import librosa
    w = lambda s: max(1, int(s * fps))
    idx = librosa.util.peak_pick(flux, pre_max=w(0.03), post_max=w(0.03), pre_avg=w(0.1), post_avg=w(0.1),
                                 delta=delta, wait=w(wait_s))
    idx = idx[flux[idx] >= floor]
    return idx / fps


def fmt_t(t):
    if t is None:
        return "  -  "
    return f"{int(t // 60)}:{t % 60:05.2f}"
