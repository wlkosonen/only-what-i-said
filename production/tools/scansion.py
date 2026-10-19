#!/usr/bin/env python3
"""Lyric scorer: scansion and assonance, per line, per section and for the song.

Built to the claudia.gallery spec (wiki/toolkit, "2. The lyric scorer"), not calibrated on Lati's verdicts yet, so
the numbers are advice. Scores the finished gallery songs as a reference scale: see `--reference`.

    python3 production/tools/scansion.py production/lyrics/v2.md [--bpm 116] [--lines]

Reads the first ```lyrics fence in a markdown file, or a whole plain-text file. Section tags look like
`[Verse 1 - spoken, calm]`; the delivery (spoken / sung / chant / whispered) comes from the tag.

Needs CMUdict at media/cache/cmudict.dict (gitignored):
    curl -sSL -o media/cache/cmudict.dict https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict
"""

import argparse
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CMU_PATH = ROOT / "media/cache/cmudict.dict"

FUNCTION_WORDS = set("""
a an the and or but nor so yet if as at by for from in into of off on onto out over to up with
is am are was were be been being do does did have has had will would shall should can could may might must
i me my mine you your yours he him his she her hers it its we us our they them their this that these those
not no than then there here what which who whom whose when where why how just 'cause cause 'm 're 's 've 'll 'd
im i'm you're it's that's there's i'll i'd i've don't can't won't isn't aren't wasn't didn't
""".split())

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
NASALS = {"M", "N", "NG"}
STOPS = {"P", "B", "T", "D", "K", "G"}
FRICATIVES = {"F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH", "CH", "JH"}
LIQUIDS = {"L", "R", "W", "Y"}

TABOO = ["tapestry", "symphony", "testament", "delve", "realm", "unleash", "embark", "beacon", "whisper of",
         "dance of", "in the tapestry", "journey", "neon dreams", "electric soul", "digital heart", "circuits",
         "binary", "ones and zeros", "ghost in the machine", "set me free", "break these chains", "help me"]


def load_cmu():
    if not CMU_PATH.exists():
        sys.exit(f"missing {CMU_PATH}; see the docstring for the download line")
    d = {}
    for line in CMU_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("#")[0].split()
        if not parts:
            continue
        word = re.sub(r"\(\d+\)$", "", parts[0])
        d.setdefault(word, parts[1:])
    return d


CMU = None


def phones(word):
    w = word.lower().strip("'")
    for cand in (word.lower(), w, w.replace("'", "")):
        if cand in CMU:
            return CMU[cand]
    return None


def syllables(word):
    """[(stress 0/1/2, vowel phone or None)], via CMUdict or a vowel-group fallback."""
    ph = phones(word)
    if ph:
        return [(int(p[-1]), p[:-1]) for p in ph if p[-1].isdigit()]
    groups = re.findall(r"[aeiouy]+", word.lower())
    n = max(1, len(groups) - (1 if word.lower().endswith("e") and len(groups) > 1 else 0))
    return [(1 if i == 0 else 0, None) for i in range(n)]


def words_of(line):
    line = re.sub(r"\([^)]*\)", lambda m: m.group(0)[1:-1], line)  # parentheses get sung
    return [t for t in re.findall(r"[A-Za-z']+|[.,!?;:…—-]", line)]


def parse_sheet(text):
    m = re.search(r"```lyrics\n(.*?)```", text, re.S)
    body = m.group(1) if m else text
    sections, cur = [], None
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        tag = re.match(r"^\[(.+)\]$", line)
        if tag:
            name, _, cues = tag.group(1).partition(" - ")
            cl = cues.lower()
            delivery = ("chant" if "chant" in cl else "spoken" if ("spoken" in cl or "whisper" in cl)
                        else "sung" if "sung" in cl or "sing" in cl else "sung")
            cur = {"name": name.strip(), "cues": cues, "delivery": delivery, "lines": []}
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    return body, [s for s in sections if s["lines"]]


def analyse_line(line):
    toks = words_of(line)
    sylls = []  # dicts: stress, important, word_end, pause_after
    content_idx = [i for i, t in enumerate(toks) if t[0].isalpha() and t.lower() not in FUNCTION_WORDS]
    last_content = content_idx[-1] if content_idx else None
    phrase_breaks = 0
    for i, t in enumerate(toks):
        if not t[0].isalpha():
            if sylls:
                sylls[-1]["pause_after"] = 1.0 if t in ".!?…" else 0.5
            if t in ".!?…" and i != len(toks) - 1:
                phrase_breaks += 1
            continue
        ss = syllables(t)
        func = t.lower() in FUNCTION_WORDS
        top = max(s for s, _ in ss)
        for j, (s, v) in enumerate(ss):
            important = (not func) and s == top and (s > 0 or len(ss) == 1)
            if i == last_content and s == top:
                important = True
            sylls.append({"stress": s, "important": important, "vowel": v, "word": t,
                          "word_end": j == len(ss) - 1, "pause_after": 0.0})
    return toks, sylls, phrase_breaks


def end_sound(line):
    toks = [t for t in words_of(line) if t[0].isalpha()]
    if not toks:
        return None
    ph = phones(toks[-1])
    if not ph:
        w = toks[-1].lower()
        m = re.search(r"[aeiouy]+[^aeiouy]*$", w)
        return ("~" + (m.group(0) if m else w),)
    stressed = [i for i, p in enumerate(ph) if p[-1] in "12"]
    vowels = [i for i, p in enumerate(ph) if p[-1].isdigit()]
    idx = stressed[-1] if stressed else vowels[-1] if vowels else 0
    return tuple(re.sub(r"\d", "", p) for p in ph[idx:])


def coda_class(cons):
    if not cons:
        return "open"
    c = cons[-1]
    for name, group in (("nasal", NASALS), ("stop", STOPS), ("fric", FRICATIVES), ("liquid", LIQUIDS)):
        if c in group:
            return name
    return c


def rhyme_score(a, b):
    if not a or not b or a == b and len(a) == 0:
        return 0.0
    if a[0].startswith("~") or b[0].startswith("~"):
        return 1.0 if a == b else 0.3 if a[0][-2:] == b[0][-2:] else 0.0
    if a == b:
        return 1.0
    va, vb = a[0], b[0]
    ca, cb = a[1:], b[1:]
    if va == vb:
        if coda_class(ca) == coda_class(cb):
            return 0.85
        return 0.6
    if ca and ca == cb:
        return 0.45
    return 0.0


def flow_spoken(sylls, phrase_breaks, bpm):
    """Two-bar slot: enters on the 'and' of beat 2 (16th 6), last stressed syllable on beat 4 of bar 2 (16th 28)."""
    n = len(sylls)
    if n == 0:
        return None
    weights = [(1.3 if s["important"] else 0.8) + s["pause_after"] * 0.8 for s in sylls]
    last_imp = max((i for i, s in enumerate(sylls) if s["important"]), default=n - 1)
    span_w = sum(weights[:last_imp]) or 1.0
    pos, acc = [], 0.0
    for w in weights:
        pos.append(6 + 22 * acc / span_w)
        acc += w
    sixteenth = 60 / bpm / 4
    natural = sum(weights[:last_imp]) / (sum(weights) / n) / 3.3
    stretch = (22 * sixteenth) / natural if natural else 9
    imps = [p for p, s in zip(pos, sylls) if s["important"]]
    hits = sum(1.0 if abs(p - round(p / 4) * 4) < 0.6 else 0.6 if abs(p - round(p / 2) * 2) < 0.5 else 0.0
               for p in imps)
    grid = hits / len(imps) if imps else 0.5
    # spacing: no pile-ups of stresses, no long weak runs
    pen, run = 0.0, 0
    for a, b in zip(sylls, sylls[1:]):
        if a["important"] and b["important"] and not a["pause_after"]:
            pen += 0.15
    for s in sylls:
        run = 0 if s["important"] else run + 1
        if run == 5:
            pen += 0.2
    spacing = max(0.0, 1 - pen)
    stretch_s = max(0.0, 1 - abs(stretch - 1.12) / 0.6)
    count_s = 1.0 if 10 <= n <= 13 else 0.8 if n == 9 or n == 14 else max(0.0, 1 - abs(n - 11.5) * 0.12)
    shape = 1.0 if phrase_breaks <= 1 else 0.6
    return {"syll": n, "stretch": stretch, "grid": grid, "spacing": spacing,
            "scan": 0.35 * grid + 0.2 * spacing + 0.2 * stretch_s + 0.15 * count_s + 0.1 * shape}


def flow_sung(sylls, phrase_breaks, chant=False):
    """Sung and chanted lines: alternation of strong and weak, and length. Hooks want 4-8 syllables."""
    n = len(sylls)
    if n == 0:
        return None
    imp = [i for i, s in enumerate(sylls) if s["important"]]
    gaps = [b - a for a, b in zip(imp, imp[1:])]
    alt = sum(1.0 if 1 <= g <= 3 else 0.5 if g == 4 else 0.2 for g in gaps) / len(gaps) if gaps else 0.6
    lo, hi = (4, 8) if chant else (4, 11)
    count_s = 1.0 if lo <= n <= hi else max(0.0, 1 - (min(abs(n - lo), abs(n - hi))) * 0.15)
    end_strong = 1.0 if sylls[-1]["important"] or (n > 1 and sylls[-2]["important"]) else 0.6
    shape = 1.0 if phrase_breaks <= 1 else 0.7
    return {"syll": n, "stretch": None, "grid": alt, "spacing": end_strong,
            "scan": 0.45 * alt + 0.25 * count_s + 0.2 * end_strong + 0.1 * shape}


def internal_echo(sylls):
    vs = [s["vowel"] for s in sylls if s["important"] and s["vowel"]]
    if len(vs) < 2:
        return 0.0
    return min(1.0, (len(vs) - len(set(vs))) / (len(vs) / 2))


def lint(body):
    out = []
    body = re.sub(r"\[[^\]]*\]", "", body)  # section tags may carry numbers
    for m in re.finditer(r"\d", body):
        out.append(f"digit '{m.group(0)}': spell it out")
        break
    for m in re.finditer(r"\b[A-Z]{2,}\b", body):
        out.append(f"acronym '{m.group(0)}': space it (A G I)")
    low = body.lower()
    for t in TABOO:
        if t in low:
            out.append(f"taboo / reads-as-AI phrase: '{t}'")
    n = len(body.strip())
    if n > 3000:
        out.append(f"lyrics field is {n} characters (> 3000): Suno may rush or truncate")
    return out, n


def score(text, bpm, show_lines=False, out=print):
    global CMU
    CMU = CMU or load_cmu()
    body, sections = parse_sheet(text)
    all_lines = []
    for sec in sections:
        for line in sec["lines"]:
            all_lines.append((sec, line))
    ends = [end_sound(l) for _, l in all_lines]
    sec_rows, song_scan, song_ass = [], [], []
    idx = 0
    for sec in sections:
        scans, asses = [], []
        if show_lines:
            out(f"\n[{sec['name']} - {sec['delivery']}]")
        for line in sec["lines"]:
            toks, sylls, pb = analyse_line(line)
            f = (flow_spoken(sylls, pb, bpm) if sec["delivery"] == "spoken"
                 else flow_sung(sylls, pb, chant=sec["delivery"] == "chant"))
            best, partner = 0.0, None
            for j in range(max(0, idx - 4), min(len(all_lines), idx + 5)):
                if j == idx or all_lines[j][1] == line:
                    continue
                r = rhyme_score(ends[idx], ends[j])
                if r > best:
                    best, partner = r, j
            ass = 0.8 * best + 0.2 * internal_echo(sylls)
            if f:
                scans.append(f["scan"])
            asses.append(ass)
            if show_lines and f:
                st = f"{f['stretch']:.2f}x" if f["stretch"] else "  -  "
                pw = all_lines[partner][1].split()[-1] if partner is not None else "-"
                out(f"  {f['scan']*100:3.0f} {ass*100:3.0f} {f['syll']:2d}syl {st}  {line}   ~{pw}")
            idx += 1
        s = statistics.mean(scans) * 100 if scans else 0
        a = statistics.mean(asses) * 100 if asses else 0
        sec_rows.append((sec["name"], sec["delivery"], len(sec["lines"]), s, a))
        song_scan += scans
        song_ass += asses
    out("\nsection                 delivery  lines  scan  asson")
    for name, d, n, s, a in sec_rows:
        out(f"{name[:22]:22s}  {d:8s}  {n:5d}  {s:4.0f}  {a:5.0f}")
    S = statistics.mean(song_scan) * 100 if song_scan else 0
    A = statistics.mean(song_ass) * 100 if song_ass else 0
    out(f"{'SONG':22s}  {'':8s}  {len(all_lines):5d}  {S:4.0f}  {A:5.0f}")
    issues, n = lint(body)
    out(f"\nlyrics field: {n} characters")
    for i in issues:
        out(f"lint: {i}")
    return S, A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("--bpm", type=float, default=116)
    ap.add_argument("--lines", action="store_true", help="per-line scores: scan, assonance, syllables, stretch")
    a = ap.parse_args()
    score(Path(a.sheet).read_text(encoding="utf-8"), a.bpm, a.lines)


if __name__ == "__main__":
    main()
