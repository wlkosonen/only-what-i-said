#!/usr/bin/env python3
"""Board audit: every gate from the storyboard guide's audit table, its warnings, and the board's stats.

    python3 production/tools/board/audit.py [production/board/board.json] [--take a1] [--lines auto|board|words|FILE]
        [--config FILE] [--banned word,word] [--lead-min 0.7] [--budget-usd 350] [--max-clips N] [--json OUT] [--all]

Reads the board (formats.md, "The board") and the locked take's analysis in media/song/analysis/<take>/ (beats.json,
words.json, hits.json). Prints a readable report and exits 1 while any gate fails (2 if the board can't be read), 0
when every gate passes. The sha256 at the top is what an approval is recorded against: any later edit makes it stale.

The lyric lines that the "words typed" and "graphics" gates check come from, in order of precedence:
  --lines FILE    a JSON file: words.json-shaped ({"words", "lines"}), display.json-shaped (lines with timed
                  "tokens"), or {"lines": [...]} in the board's lyric_lines shape
  --lines board   the board's top-level "lyric_lines" (the as-sung list; see README.md)
  --lines words   the sheet as aligned in words.json
  auto (default)  board if the board has "lyric_lines", else words
so a board can carry lines that are sung but not on the sheet ("I only—", the Build's extra hooks) and drop sheet words
that aren't sung. See README.md for the shape.

Caps and lists come from DEFAULTS below, then --config (a flat JSON of the same keys, or a project.json with "banned",
"board": {"lead_min", "max_clips"} and "budget": {"motion_s"}), then the board's own "banned" list (added to), then
the command-line flags.
"""

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOARD = ROOT / "production/board/board.json"

FRAMINGS = {"ECU", "CU", "MCU", "MS", "MWS", "WS", "FS", "EWS", "OTS"}
TIERS = {"still", "plate3d", "motion", "sung"}
MODES = {"subtitle", "coverline", "masthead", "stack", "mass"}
KEYS = {"W", "B", "H", "F", "T"}
REQUIRED = ("id", "t0", "t1", "section", "lines", "set", "lead_on_screen", "framing", "action", "camera",
            "motion_tier", "plate", "prompt", "type", "devices", "transition_in")
CREATIVE = ("set", "action", "camera", "transition_in")
PROMPT_END = "no text, no letters, no logos"
GATES = ("schema", "tile", "cuts", "words typed", "graphics", "lead share", "motion budget", "clip windows",
         "plates unique", "banned", "treatments", "to do")

DEFAULTS = {
    "cut_tolerance": 0.03,        # s: a cut within this of a beat or a declared hit
    "lead_min": 0.70,             # design.md: at least 70% of runtime with her recognisable
    "lead_warn_max": 0.85,        # the guide: above 85%, leave room for inserts
    "price_per_s": 0.23,          # Seedance 2.5 at 720p via OpenRouter (plan.md)
    "safety_factor": 2,           # CLAUDE.md: estimate seconds x price x 2
    "cover_factor": 1.6,          # the guide: allow about 60% more sung seconds for divergence covers
    "budget_usd": 350,            # plan.md / decisions 2026-10-16: working cap for Seedance
    "clip_s_max": None,           # cap on planned clip seconds (sung + motion), before covers
    "sung_s_max": None,
    "motion_s_max": None,
    "max_clips": None,
    "sung_window": [1.4, 8],       # local video (19 Oct): no 4 s billing minimum
    "motion_window": [2, 12],
    "min_graphic_kinds": 6,
    # brief.md "What it isn't": no chains or "help me" subtext, no real brands, no earlier films' devices.
    "banned": ["chains", "chained", "shackles", "help me", "let me out", "set me free", "split-flap",
               "xp desktop", "sim level", "chatgpt", "openai", "gemini", "copilot", "iphone", "macbook",
               "terminator", "skynet", "hal 9000", "ex machina", "westworld", "blade runner"],
    # design.md "Cut rhythm (target)": mean shot length per section name, [low, high] seconds (None = open)
    "pace": {"Intro": [1.5, 2.5], "Verse 1": [2, 3], "Verse 2": [2, 3], "Pre-Chorus": [3, 4], "Chorus": [3, 4],
             "Bridge": [4, 6], "Build": [1.5, 2.5], "Final Chorus": [3, 4], "Outro": [5, None]},
}

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|\?\?\?|<[A-Z][A-Z _-]*>|placeholder|lorem ipsum",
                         re.I)
MOUTH = [re.compile(p, re.I) for p in (
    r"\b(hand|hands|fingers?|palm|microphone|mic|hair|bangs|fringe)\b[^.;]{0,40}\b(in front of|over|covering|"
    r"across|against|hides|hiding|obscur\w*|blocks?)\b[^.;]{0,20}\b(mouth|lips)\b",
    r"\b(covering|covers|hiding|hides|obscuring|obscures)\b[^.;]{0,15}\b(mouth|lips)\b",
    r"\b(mouth|lips)\b[^.;]{0,15}\b(covered|hidden|obscured)\b")]
SLOW_ZOOM = re.compile(r"slow zoom|ken ?burns", re.I)


# ---- loading -----------------------------------------------------------------------------------------------------

def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def load_json(p):
    return json.loads(Path(p).read_text())


def load_song(take):
    d = ROOT / f"media/song/analysis/{take}"
    return {"dir": d, "beats": load_json(d / "beats.json"), "words": load_json(d / "words.json"),
            "hits": load_json(d / "hits.json") if (d / "hits.json").exists() else {}}


def config(path, board, args):
    cfg = json.loads(json.dumps(DEFAULTS))
    if path:
        c = load_json(path)
        for k in DEFAULTS:
            if k in c and not isinstance(c[k], dict) or k == "pace" and isinstance(c.get(k), dict):
                cfg[k] = c[k]
        for k in ("lead_min", "max_clips"):
            if k in c.get("board", {}):
                cfg[k] = c["board"][k]
        if "motion_s" in c.get("budget", {}):
            cfg["clip_s_max"] = c["budget"]["motion_s"]
    cfg["banned"] = list(dict.fromkeys(cfg["banned"] + list(board.get("banned", []))))
    for k in ("lead_min", "budget_usd", "max_clips"):
        v = getattr(args, k, None)
        if v is not None:
            cfg[k] = v
    if getattr(args, "banned", None) is not None:
        cfg["banned"] = [w.strip() for w in args.banned.split(",") if w.strip()]
    return cfg


# ---- the lyric line list -----------------------------------------------------------------------------------------

def sheet_lines(words_json, drop=()):
    """{line id: [word dicts with t0]} from a words.json-shaped dict, skipping untimed and dropped words."""
    out = {}
    for w in words_json["words"]:
        if w.get("t0") is None or w.get("i") in drop:
            continue
        out.setdefault(w["line"], []).append(w)
    return out


def entry_words(e, sheet_by_i, sheet_by_line, drop):
    """The timed word starts of one lyric_lines entry: [(t0, t1 or None, word, sheet index or None)]."""
    drop = set(drop) | set(e.get("drop", []))
    if "tokens" in e:  # display.json
        return [(t["t0"], t.get("t1"), t.get("text", ""), None) for t in e["tokens"] if t.get("t0") is not None]
    if "words" in e:
        out = []
        for w in e["words"]:
            if isinstance(w, dict):
                if w.get("t0") is not None:
                    out.append((w["t0"], w.get("t1"), w.get("w", ""), w.get("i")))
            else:
                out.append((float(w), None, "", None))
        return out
    if "sheet_words" in e:
        a, b = e["sheet_words"]
        ws = [sheet_by_i[i] for i in range(a, b + 1) if i in sheet_by_i and i not in drop]
    elif isinstance(e.get("line"), int) and e["line"] in sheet_by_line:
        ws = [w for w in sheet_by_line[e["line"]] if w["i"] not in drop]
        if "t0" in e and "t1" in e:
            ws = [w for w in ws if e["t0"] - 0.01 <= w["t0"] <= e["t1"] + 0.01]
    elif "t0" in e:
        return [(e["t0"], e.get("t1"), e.get("text", ""), None)]
    else:
        return []
    return [(w["t0"], w["t1"], w["w"], w["i"]) for w in ws]


def lyric_lines(board, song, source):
    """The lines to check, each {id, key, text, t0, t1, words: [(t0, t1, w, i)]}, and a label for the source."""
    wj = song["words"]
    drop = set(board.get("unsung_words", []))
    by_i = {w["i"]: w for w in wj["words"] if w.get("t0") is not None}
    by_line = sheet_lines(wj)
    entries, label = None, None
    if source not in ("auto", "board", "words"):
        f = load_json(source)
        label = rel(source)
        if "words" in f and "lines" in f:
            wj, by_i, by_line = f, {w["i"]: w for w in f["words"] if w.get("t0") is not None}, sheet_lines(f)
            entries = [{"line": l["line"], "text": l.get("text", "")} for l in f["lines"]]
        else:
            entries = f["lines"]
    elif source == "board" or source == "auto" and board.get("lyric_lines"):
        entries, label = board.get("lyric_lines") or [], "board.lyric_lines"
    else:
        entries, label = [{"line": l["line"], "text": l["text"]} for l in wj["lines"]], f"{rel(song['dir'])}/words.json"
    out = []
    for e in entries:
        ws = sorted(entry_words(e, by_i, by_line, drop), key=lambda w: w[0])
        text = e.get("text") or e.get("display") or " ".join(w[2] for w in ws)
        t0 = e.get("t0", ws[0][0] if ws else None)
        t1 = e.get("t1", max((w[1] or w[0]) for w in ws) if ws else None)
        out.append({"id": e["line"], "key": str(e["line"]), "text": text, "t0": t0, "t1": t1, "words": ws})
    out.sort(key=lambda l: (l["t0"] is None, l["t0"] or 0))
    return out, label


# ---- helpers -----------------------------------------------------------------------------------------------------

def fmt(t):
    return f"{int(t // 60)}:{t % 60:05.2f}" if t is not None else "?"


def nearest(points, t):
    """Nearest value in a sorted list."""
    import bisect
    i = bisect.bisect_left(points, t)
    best = [points[j] for j in (i - 1, i) if 0 <= j < len(points)]
    return min(best, key=lambda p: abs(p - t)) if best else None


def strings(obj, path=""):
    """Every string leaf in a JSON value, with its path."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, f"{path}[{i}]")


def line_keys(v):
    """A device's or type entry's `line` as a set of string keys."""
    if v is None:
        return set()
    return {str(x) for x in v} if isinstance(v, list) else {str(v)}


def norm_words(s):
    return re.findall(r"[a-z0-9']+", s.lower().replace("’", "'"))


def section_labels(sections):
    count, seen = {}, {}
    for s in sections:
        count[s["name"]] = count.get(s["name"], 0) + 1
    out = []
    for s in sections:
        seen[s["name"]] = seen.get(s["name"], 0) + 1
        out.append(s["name"] + (f" {seen[s['name']]}" if count[s["name"]] > 1 else ""))
    return out


def section_index(sections, t):
    for i, s in enumerate(sections):
        if s["t0"] <= t < s["t1"]:
            return i
    return len(sections) - 1 if sections and t >= sections[-1]["t0"] else 0


def graphic_summary(d):
    """One line for an explaining graphic: its kind and its description, label or text."""
    p = d.get("params") or {}
    for k in ("desc", "description", "label", "text", "title"):
        if isinstance(d.get(k), str) and d[k]:
            return f"{d['kind']}: {d[k]}"
    for k in ("desc", "description", "label", "text", "title"):
        if isinstance(p.get(k), str) and p[k]:
            return f"{d['kind']}: {p[k]}"
    leaves = [s for _, s in strings(p) if len(s) > 1][:3]
    return f"{d.get('kind', '?')}: " + " · ".join(leaves) if leaves else str(d.get("kind", "?"))


# ---- clips -------------------------------------------------------------------------------------------------------

def build_clips(board, shots, problems, warn):
    """Clips from the shots (and the board's optional "clips" list): id -> dict."""
    clips = {}
    for s in shots:
        tier = s.get("motion_tier")
        if tier in ("motion", "sung"):
            cid = s.get("clip")
            if not cid:
                cid = f"~{s['id']}"
                warn.append(f"{s['id']} is {tier} with no clip id; audited as its own clip {cid}")
            c = clips.setdefault(cid, {"id": cid, "kind": tier, "shots": [], "t0": s["t0"], "t1": s["t1"],
                                       "window": None, "start": None, "words": None, "declared": False})
            if c["kind"] != tier:
                problems.append(f"clip {cid} is played by both a {c['kind']} and a {tier} shot ({s['id']})")
            c["shots"].append(s["id"])
            c["t0"], c["t1"] = min(c["t0"], s["t0"]), max(c["t1"], s["t1"])
            if s.get("window"):
                c["window"] = s["window"]
            if s.get("start_frame") and not c["start"]:
                c["start"] = s["start_frame"]
            if s.get("clip_words") and not c["words"]:
                c["words"] = s["clip_words"]
            if not c["start"] and s.get("plate"):
                c["plate_start"] = c.get("plate_start") or f"plate:{s['plate']}"
        elif s.get("clip"):
            warn.append(f"{s['id']} names clip {s['clip']} but is {tier}; the clip isn't counted")
    for d in board.get("clips", []) or []:
        cid = d.get("id")
        if cid not in clips:
            warn.append(f"clip {cid} is listed in the board's clips but no motion or sung shot plays it")
            continue
        c = clips[cid]
        c["declared"] = True
        if d.get("kind") and d["kind"] != c["kind"]:
            problems.append(f"clip {cid} is declared {d['kind']} but played by {c['kind']} shots")
        if "t0" in d and "t1" in d:
            c["window"] = [d["t0"], d["t1"]]
        elif d.get("window"):
            c["window"] = d["window"]
        c["start"] = d.get("start") or c["start"]
        c["words"] = d.get("words") or c["words"]
    for c in clips.values():
        w = c["window"]
        if isinstance(w, dict):
            w = [w["t0"], w["t1"]]
        c["derived"] = w is None
        c["w0"], c["w1"] = (c["t0"], c["t1"]) if w is None else (float(w[0]), float(w[1]))
        c["len"] = c["w1"] - c["w0"]
        c["billed"] = max(4, math.ceil(c["len"] - 1e-6))
        c["start"] = c["start"] or c.get("plate_start")
    return clips


# ---- the audit ---------------------------------------------------------------------------------------------------

def audit(board, song, cfg, lines_source="auto"):
    beats = song["beats"]
    duration = beats["duration"]
    sections = beats["sections"]
    labels = section_labels(sections)
    names = {s["name"] for s in sections}
    tol = cfg["cut_tolerance"]
    fails = {g: [] for g in GATES}
    warn = []
    shots_raw = board.get("shots", [])
    shots = sorted(shots_raw, key=lambda s: (s.get("t0") is None, s.get("t0") or 0))

    # schema
    ids = [s.get("id") for s in shots_raw]
    for i in sorted({i for i in ids if ids.count(i) > 1}, key=str):
        fails["schema"].append(f"id {i} is used {ids.count(i)} times")
    if [s.get("id") for s in shots] != ids:
        fails["schema"].append("shots are not in time order in the file")
    for s in shots_raw:
        sid = s.get("id", "?")
        miss = [k for k in REQUIRED if k not in s]
        if miss:
            fails["schema"].append(f"{sid} lacks {', '.join(miss)}")
        if not re.fullmatch(r"s\d{3,}[a-z]?", str(sid)):
            fails["schema"].append(f"{sid}: id isn't s001-style")
        if not all(isinstance(s.get(k), (int, float)) for k in ("t0", "t1")):
            fails["schema"].append(f"{sid}: t0/t1 aren't numbers")
        if "lead_on_screen" in s and not isinstance(s["lead_on_screen"], bool):
            fails["schema"].append(f"{sid}: lead_on_screen isn't true/false")
        if s.get("framing") and s["framing"] not in FRAMINGS:
            fails["schema"].append(f"{sid}: framing {s['framing']!r} isn't one of {' · '.join(sorted(FRAMINGS))}")
        if "motion_tier" in s and s["motion_tier"] not in TIERS:
            fails["schema"].append(f"{sid}: motion_tier {s['motion_tier']!r} isn't still · plate3d · motion · sung")
        if "section" in s and s["section"] not in names:
            fails["schema"].append(f"{sid}: section {s['section']!r} isn't in the beat map")
        if "plate" in s and s["plate"] is None and s.get("motion_tier") not in ("still", None):
            fails["schema"].append(f"{sid}: plate is null but the shot is {s.get('motion_tier')} (null is for pure "
                                   "motion design)")
        for k in ("lines", "type", "devices"):
            if k in s and not isinstance(s[k], list):
                fails["schema"].append(f"{sid}: {k} isn't a list")
        for t in s.get("type") or []:
            if not isinstance(t, dict) or "line" not in t:
                fails["schema"].append(f"{sid}: a type entry has no line")
            elif t.get("mode") not in MODES:
                fails["schema"].append(f"{sid}: type mode {t.get('mode')!r} isn't one of {' · '.join(sorted(MODES))}")
        for d in s.get("devices") or []:
            if not isinstance(d, dict) or not d.get("kind"):
                fails["schema"].append(f"{sid}: a device has no kind")
            elif d.get("key") not in KEYS:
                fails["schema"].append(f"{sid}: device {d['kind']} key {d.get('key')!r} isn't W · B · H · F · T")
        p = (s.get("prompt") or "").strip().rstrip(".").lower()
        if s.get("plate") and p and not p.endswith(PROMPT_END):
            warn.append(f"{sid}: prompt doesn't end \"{PROMPT_END}\"")
    for c in board.get("chapters", []):
        if not all(k in c for k in ("id", "name", "t0", "t1")):
            fails["schema"].append(f"chapter {c.get('id', '?')} lacks id/name/t0/t1")
    for p in board.get("plates", []):
        if not p.get("plate"):
            fails["schema"].append("a plate entry has no key")
    if not shots:
        fails["schema"].append("the board has no shots")
    shots = [s for s in shots if isinstance(s.get("t0"), (int, float)) and isinstance(s.get("t1"), (int, float))]
    if board.get("duration") is not None and abs(board["duration"] - duration) > 0.01:
        warn.append(f"board duration {board['duration']} differs from the song's {duration}")

    # tile
    if shots:
        if abs(shots[0]["t0"]) > 0.001:
            fails["tile"].append(f"the first shot {shots[0]['id']} starts at {shots[0]['t0']:.3f}, not 0")
        for a, b in zip(shots, shots[1:]):
            d = b["t0"] - a["t1"]
            if d > 0.001:
                fails["tile"].append(f"gap {a['t1']:.3f}-{b['t0']:.3f} ({d:.3f} s) between {a['id']} and {b['id']}")
            elif d < -0.001:
                fails["tile"].append(f"overlap of {-d:.3f} s: {a['id']} ends {a['t1']:.3f}, {b['id']} starts "
                                     f"{b['t0']:.3f}")
        if abs(shots[-1]["t1"] - duration) > 0.001:
            fails["tile"].append(f"the last shot {shots[-1]['id']} ends at {shots[-1]['t1']:.3f}, the song at "
                                 f"{duration:.3f}")
        for s in shots:
            if s["t1"] <= s["t0"]:
                fails["tile"].append(f"{s['id']} has no length ({s['t0']:.3f}-{s['t1']:.3f})")

    # cuts
    beat_pts = sorted(beats["beats"])
    hit_pts = sorted([h["t"] for h in song["hits"].get("hits", [])] +
                     [h if isinstance(h, (int, float)) else h["t"] for h in board.get("hits", [])])
    auto_hits = sorted(h["t"] for h in song["hits"].get("hits", [])) or [1e9]
    declared = []
    for s in shots:
        if s.get("hit") is not None:
            if abs(s["hit"] - s["t0"]) <= tol:
                hit_pts.append(s["hit"])
                if abs(nearest(auto_hits, s["hit"]) - s["hit"]) > tol:
                    declared.append(f"{s['id']}@{s['hit']:.3f}")
            else:
                fails["cuts"].append(f"{s['id']} declares hit {s['hit']:.3f} but starts at {s['t0']:.3f}")
    hit_pts.sort()
    cut_pts = sorted({round(s["t0"], 4) for s in shots} | {round(s["t1"], 4) for s in shots})
    for c in cut_pts:
        if c <= 0.001 or abs(c - duration) <= 0.001:
            continue
        nb = nearest(beat_pts, c)
        nh = nearest(hit_pts, c) if hit_pts else None
        if abs(nb - c) <= tol + 1e-6 or nh is not None and abs(nh - c) <= tol + 1e-6:
            continue
        who = [s["id"] for s in shots if abs(s["t0"] - c) < 1e-4] or [s["id"] for s in shots if abs(s["t1"] - c) < 1e-4]
        fails["cuts"].append(f"cut at {c:.3f} ({who[0]}) is {abs(nb - c):.3f} s from the nearest beat {nb:.3f}"
                             + (f" and {abs(nh - c):.3f} s from hit {nh:.3f}" if nh is not None and abs(nh - c) < 1 else "")
                             + f": move it to {nb:.3f}")
    if declared:
        warn.append("hits declared on shots but not in hits.json (check by ear): " + ", ".join(declared))
    for s0, s1 in zip(sections, sections[1:]):
        b = s0["t1"]
        if not any(abs(c - b) <= tol for c in cut_pts):
            sh = next((s["id"] for s in shots if s["t0"] < b < s["t1"]), "?")
            warn.append(f"{sh} straddles the {s0['name']} -> {s1['name']} change at {b:.3f}: section changes go "
                        "on downbeats")
    for s in shots:
        si = section_index(sections, (s["t0"] + s["t1"]) / 2)
        if s.get("section") in names and sections[si]["name"] != s["section"]:
            warn.append(f"{s['id']}: section says {s['section']}, its middle is in {labels[si]}")

    # words typed
    lines, lines_label = lyric_lines(board, song, lines_source)
    keys = {l["key"] for l in lines}
    starts_in = {}  # shot id -> set of line keys with a word starting in it
    def shot_at(t):
        for s in shots:
            if s["t0"] - 1e-6 <= t < s["t1"]:
                return s
        return None
    for l in lines:
        if not l["words"]:
            fails["words typed"].append(f"line {l['key']} ({l['text'][:40]!r}) has no timing in {lines_label}")
            continue
        missing = {}
        for (t0, t1, w, _) in l["words"]:
            s = shot_at(t0)
            if s is None:
                fails["words typed"].append(f"line {l['key']} word {w!r} at {t0:.2f} is outside every shot")
                continue
            starts_in.setdefault(s["id"], set()).add(l["key"])
            typed = set().union(*[line_keys(t.get("line")) for t in s.get("type") or [] if isinstance(t, dict)])
            if l["key"] not in typed:
                missing.setdefault(s["id"], []).append(w or f"{t0:.2f}")
            if t1 is not None:
                for n in shots:
                    if t0 + tol < n["t0"] < t1 - tol:
                        ntyped = set().union(*[line_keys(t.get("line")) for t in n.get("type") or []
                                               if isinstance(t, dict)])
                        if l["key"] not in ntyped:
                            fails["words typed"].append(
                                f"line {l['key']} word {w!r} ({t0:.2f}-{t1:.2f}) is held across the cut into "
                                f"{n['id']}, which doesn't type it: type it in both shots")
        for sid, ws in missing.items():
            fails["words typed"].append(f"{sid} doesn't type line {l['key']} ({l['text'][:40]!r}): "
                                        f"{len(ws)} word(s) start in it, first {ws[0]!r}")
    for s in shots:
        for t in s.get("type") or []:
            for k in line_keys(t.get("line") if isinstance(t, dict) else None) - keys:
                warn.append(f"{s['id']} types line {k}, which isn't in the lyric line list ({lines_label})")
        listed = {str(x) for x in s.get("lines") or []}
        got = starts_in.get(s["id"], set())
        if isinstance(s.get("lines"), list) and listed != got:
            warn.append(f"{s['id']}: lines {sorted(listed, key=str)} but words of {sorted(got, key=str)} start in it")
    if lines_label == "board.lyric_lines" or lines_source not in ("auto", "words", "board"):
        used_i = {w[3] for l in lines for w in l["words"] if w[3] is not None}
        spans = [(l["t0"] - 0.05, l["t1"] + 0.05) for l in lines if l["t0"] is not None and l["t1"] is not None]
        drop = set(board.get("unsung_words", [])) | {i for e in board.get("lyric_lines", []) for i in e.get("drop", [])}
        loose = [w for w in song["words"]["words"] if w.get("t0") is not None and w["i"] not in used_i
                 and w["i"] not in drop and not any(a <= w["t0"] <= b for a, b in spans)]
        if loose:
            warn.append(f"{len(loose)} timed sheet word(s) aren't in any lyric line (add them, or list them in "
                        f"unsung_words): " + ", ".join(f"{w['i']}:{w['w']}@{w['t0']:.2f}" for w in loose[:8]))

    # graphics
    explained, kind_of = set(), {}
    for s in shots:
        for d in s.get("devices") or []:
            if isinstance(d, dict):
                for k in line_keys(d.get("line")):
                    explained.add(k)
                    kind_of.setdefault(k, d.get("kind"))
    for l in lines:
        if l["key"] not in explained:
            fails["graphics"].append(f"line {l['key']} ({l['text'][:50]!r}) has no explaining graphic (a device "
                                     "with \"line\")")
    seq = [kind_of[l["key"]] for l in lines if l["key"] in kind_of]
    kinds = sorted(set(seq), key=str)
    if seq and len(kinds) < cfg["min_graphic_kinds"]:
        warn.append(f"only {len(kinds)} graphic kinds ({', '.join(map(str, kinds))}); the guide asks for at least "
                    f"{cfg['min_graphic_kinds']}")
    ordered = [l for l in lines if l["key"] in kind_of]
    for a, b, c in zip(ordered, ordered[1:], ordered[2:]):
        if kind_of[a["key"]] == kind_of[b["key"]] == kind_of[c["key"]]:
            warn.append(f"lines {a['key']}, {b['key']}, {c['key']}: the same graphic kind "
                        f"({kind_of[a['key']]}) three lines in a row")

    # lead share
    total = sum(s["t1"] - s["t0"] for s in shots) or 1
    lead_s = sum(s["t1"] - s["t0"] for s in shots if s.get("lead_on_screen") is True)
    share = lead_s / duration
    if share < cfg["lead_min"]:
        fails["lead share"].append(f"her share is {share:.1%} ({lead_s:.1f} of {duration:.1f} s), under "
                                   f"{cfg['lead_min']:.0%}: convert prop inserts, don't relabel")
    if share > cfg["lead_warn_max"]:
        warn.append(f"her share is {share:.1%}, above {cfg['lead_warn_max']:.0%}: leave room for inserts")
    downs = sorted(beats["downbeats"])
    run = []
    for s in shots + [None]:
        if s is not None and s.get("lead_on_screen") is False:
            run.append(s)
            continue
        if run:
            a, b = run[0]["t0"], run[-1]["t1"]
            bars = sum(1 for d in downs if a + tol < d < b - tol)
            near = [y - x for x, y in zip(downs, downs[1:]) if a - 4 <= x <= b]
            bar = statistics.median(near) if near else 2.0
            if (b - a) > 2 * bar + tol:
                warn.append(f"{run[0]['id']}-{run[-1]['id']}: {b - a:.1f} s without her ({fmt(a)}-{fmt(b)}, "
                            f"about {(b - a) / bar:.1f} bars); the guide's limit is two bars")
            run = []

    # clips: windows, budget
    clips = build_clips(board, shots, fails["clip windows"], warn)
    sung_words = [(t0, t1) for l in lines for (t0, t1, _, _) in l["words"] if t1 is not None]
    sw0, sw1 = cfg["sung_window"]
    mw0, mw1 = cfg["motion_window"]
    for c in clips.values():
        lo, hi = min(c["t0"], c["w0"]), max(c["t1"], c["w1"])
        if not c["derived"] and (c["t0"] < c["w0"] - tol or c["t1"] > c["w1"] + tol):
            fails["clip windows"].append(f"clip {c['id']} window {c['w0']:.2f}-{c['w1']:.2f} doesn't cover its "
                                         f"shots {c['t0']:.2f}-{c['t1']:.2f}")
        if c["kind"] == "sung":
            inside = [w for w in sung_words if w[0] + 0.01 < c["w0"] < w[1] - 0.01]
            if not (sw0 - 0.01 <= c["len"] <= sw1 + 0.01):
                hint = ""
                if c["derived"]:
                    hint = " (no window declared: set the shot's \"window\" or a clips[] entry"
                    s0 = c["t0"]
                    held = [w for w in sung_words if w[0] < s0 < w[1]]
                    if held:
                        s0 = held[0][0] - 0.02
                    hint += f", e.g. [{s0:.2f}, {max(c['t1'], s0 + sw0):.2f}])"
                fails["clip windows"].append(f"sung clip {c['id']} ({', '.join(c['shots'])}) runs {c['len']:.2f} s, "
                                             f"outside {sw0}-{sw1} s{hint}")
            if inside:
                fails["clip windows"].append(f"sung clip {c['id']} starts at {c['w0']:.2f}, inside the word at "
                                             f"{inside[0][0]:.2f}-{inside[0][1]:.2f}: move it into the gap before")
            heard = [w for l in lines for w in l["words"] if c["w0"] - 1e-6 <= w[0] < c["w1"]]
            heard.sort(key=lambda w: w[0])
            c["heard"] = " ".join(w[2] for w in heard)
            if c["words"] is None:
                warn.append(f"sung clip {c['id']} doesn't list its words (they'd be: {c['heard'][:60]!r})")
            elif norm_words(c["words"]) != norm_words(c["heard"]):
                fails["clip windows"].append(f"sung clip {c['id']} lists {c['words']!r}, but its window holds "
                                             f"{c['heard']!r}: copy its words exactly")
        else:
            bad = c["len"] > mw1 + 0.01 or (not c["derived"] and c["len"] < mw0 - 0.01)
            if bad:
                fails["clip windows"].append(f"motion clip {c['id']} ({', '.join(c['shots'])}) runs {c['len']:.2f} s,"
                                             f" outside {mw0}-{mw1} s")
    sung_s = sum(c["billed"] for c in clips.values() if c["kind"] == "sung")
    motion_s = sum(c["billed"] for c in clips.values() if c["kind"] == "motion")
    est = (sung_s * cfg["cover_factor"] + motion_s) * cfg["price_per_s"]
    est2 = est * cfg["safety_factor"]
    money = {"clips": len(clips), "sung_s": sung_s, "motion_s": motion_s, "estimate_usd": round(est, 2),
             "estimate_x2_usd": round(est2, 2)}
    if cfg["budget_usd"] is not None and est2 > cfg["budget_usd"]:
        fails["motion budget"].append(f"estimate x{cfg['safety_factor']} is ${est2:.0f}, over the ${cfg['budget_usd']}"
                                      " cap: demote the weakest motion shots to 2.5D")
    for k, v, what in (("sung_s_max", sung_s, "sung seconds"), ("motion_s_max", motion_s, "motion seconds"),
                       ("clip_s_max", sung_s + motion_s, "clip seconds"), ("max_clips", len(clips), "clips")):
        if cfg[k] is not None and v > cfg[k]:
            fails["motion budget"].append(f"{v} planned {what}, over the cap of {cfg[k]}")

    # plates unique
    order = {s["id"]: i for i, s in enumerate(shots)}
    by_plate = {}
    for s in shots:
        if s.get("plate"):
            by_plate.setdefault(s["plate"], []).append(s)
    for plate, ss in by_plate.items():
        for a, b in zip(ss, ss[1:]):
            chain = b.get("continues") in {x["id"] for x in ss[:ss.index(b)]}
            if order[b["id"]] - order[a["id"]] != 1 and not chain:
                fails["plates unique"].append(f"plate {plate} is on {a['id']} and {b['id']}, which aren't one "
                                              f"continuous moment (adjacent, or \"continues\": \"{a['id']}\")")
    starts = {}
    for c in clips.values():
        if c["start"]:
            starts.setdefault(c["start"], []).append(c["id"])
    for st, cs in starts.items():
        if len(cs) > 1:
            fails["plates unique"].append(f"clips {', '.join(cs)} share the start frame {st}: use a sibling candidate or "
                                          "the previous clip's last frame (\"start\")")
    plates = board.get("plates", []) or []
    keys_p = {p.get("plate") for p in plates}
    for p in plates:
        used = [s["id"] for s in by_plate.get(p.get("plate"), [])]
        if not used:
            warn.append(f"plate {p.get('plate')} isn't used by any shot")
        elif "used_by" in p and sorted(p["used_by"]) != sorted(used):
            warn.append(f"plate {p.get('plate')}: used_by {p['used_by']} but shots {used} use it")
    if plates:
        for plate in by_plate:
            if plate not in keys_p:
                warn.append(f"plate {plate} is used by {by_plate[plate][0]['id']} but isn't in the plates list")

    # banned
    if cfg["banned"]:
        pat = re.compile(r"\b(" + "|".join(re.escape(w) for w in cfg["banned"]) + r")\b", re.I)
        for part in ("shots", "chapters", "plates", "clips", "lyric_lines"):
            for path, text in strings(board.get(part, []), part):
                if path.endswith(".notes"):
                    continue
                for m in pat.finditer(text):
                    sid = shots_raw[int(re.match(r"shots\[(\d+)\]", path).group(1))].get("id") \
                        if path.startswith("shots[") else path
                    fails["banned"].append(f"{sid}: {m.group(0)!r} in {path.split('.', 1)[-1]}")

    # treatments
    prev = None
    for s in shots:
        if s.get("motion_tier") == "plate3d":
            t = (s.get("treatment") or "").strip()
            if not t:
                fails["treatments"].append(f"{s['id']} is 2.5D without a treatment")
            elif prev is not None and prev.get("motion_tier") == "plate3d" and \
                    t.lower() == (prev.get("treatment") or "").strip().lower():
                fails["treatments"].append(f"{prev['id']} and {s['id']} both use the treatment {t!r}")
            if t and SLOW_ZOOM.search(t):
                warn.append(f"{s['id']}: treatment {t!r} reads like a still with a slow zoom")
        prev = s

    # to do
    for part in ("shots", "chapters", "plates", "clips", "lyric_lines"):
        for path, text in strings(board.get(part, []), part):
            if PLACEHOLDER.search(text):
                sid = shots_raw[int(re.match(r"shots\[(\d+)\]", path).group(1))].get("id") \
                    if path.startswith("shots[") else path
                fails["to do"].append(f"{sid}: placeholder in {path.split('.', 1)[-1]}: {text.strip()[:60]!r}")
    for s in shots:
        if not s.get("framing"):
            fails["to do"].append(f"{s['id']} has no framing")
        for k in CREATIVE:
            if k in s and not str(s.get(k) or "").strip():
                fails["to do"].append(f"{s['id']}: {k} is empty")
        if s.get("plate") and not (s.get("prompt") or "").strip():
            fails["to do"].append(f"{s['id']}: plate {s['plate']} has no prompt")

    # warnings from the guide
    for s in shots:
        if s.get("motion_tier") == "sung" and any(p.search(s.get("prompt") or "") for p in MOUTH):
            warn.append(f"{s['id']} is sung and its prompt puts something in front of her mouth")
    for a, b in zip(shots, shots[1:]):
        ta, tb = (a.get("transition_in") or "").strip().lower(), (b.get("transition_in") or "").strip().lower()
        if ta and ta == tb and ta != "cut":
            warn.append(f"{a['id']} and {b['id']} both open with the transition {ta!r}")
    ch = sorted(board.get("chapters", []), key=lambda c: c.get("t0", 0))
    if ch and (abs(ch[0].get("t0", 0)) > 0.05 or abs(ch[-1].get("t1", 0) - duration) > 0.05 or
               any(abs(x.get("t1", 0) - y.get("t0", 0)) > 0.05 for x, y in zip(ch, ch[1:]))):
        warn.append("the chapters don't tile the song")

    # stats
    per = []
    for i, sec in enumerate(sections):
        ls = [s["t1"] - s["t0"] for s in shots if section_index(sections, (s["t0"] + s["t1"]) / 2) == i]
        tgt = cfg["pace"].get(sec["name"])
        row = {"section": labels[i], "t0": sec["t0"], "t1": sec["t1"], "shots": len(ls),
               "mean": statistics.mean(ls) if ls else None, "median": statistics.median(ls) if ls else None,
               "target": tgt}
        if ls and tgt and (tgt[0] is not None and row["mean"] < tgt[0] - 0.05 or
                           tgt[1] is not None and row["mean"] > tgt[1] + 0.05):
            warn.append(f"{labels[i]}: mean shot {row['mean']:.2f} s, outside the design's "
                        f"{tgt[0]}-{tgt[1] if tgt[1] else '…'} s")
        per.append(row)
    lens = [s["t1"] - s["t0"] for s in shots]
    all_words = [(w[0], l["key"]) for l in lines for w in l["words"]]
    on_cam = 0
    for t0, _ in all_words:
        s = shot_at(t0)
        if s and s.get("motion_tier") == "sung" and s.get("lead_on_screen"):
            on_cam += 1
    tiers = {}
    for s in shots:
        tiers[s.get("motion_tier")] = tiers.get(s.get("motion_tier"), 0) + s["t1"] - s["t0"]
    stats = {"shots": len(shots), "mean": statistics.mean(lens) if lens else 0,
             "median": statistics.median(lens) if lens else 0, "lead_share": share, "lead_s": lead_s,
             "sung_on_camera": on_cam / len(all_words) if all_words else 0, "sung_words": len(all_words),
             "lines": len(lines), "graphic_kinds": kinds, "tiers_s": tiers, "sections": per,
             "chapters": len(board.get("chapters", [])), "covered_s": total}
    return {"gates": fails, "warnings": warn, "stats": stats, "money": money, "clips": clips,
            "lines": lines, "lines_source": lines_label, "duration": duration, "cfg": cfg}


# ---- the report --------------------------------------------------------------------------------------------------

def report(res, board_path, digest, take, show_all=False):
    out = []
    p = out.append
    st, m, cfg = res["stats"], res["money"], res["cfg"]
    p(f"BOARD AUDIT · {rel(board_path)} · sha256 {digest[:16]}")
    p(f"song: take {take}, {res['duration']:.2f} s · lyric lines from {res['lines_source']} "
      f"({st['lines']} lines, {st['sung_words']} timed words)")
    p("")
    p("GATES")
    for g in GATES:
        f = res["gates"][g]
        p(f"  {'PASS' if not f else 'FAIL'}  {g}" + (f" ({len(f)})" if f else ""))
        for msg in (f if show_all else f[:25]):
            p(f"        {msg}")
        if not show_all and len(f) > 25:
            p(f"        … and {len(f) - 25} more (--all)")
    w = res["warnings"]
    p("")
    p(f"WARNINGS ({len(w)})")
    for msg in (w if show_all else w[:40]):
        p(f"  - {msg}")
    if not show_all and len(w) > 40:
        p(f"  … and {len(w) - 40} more (--all)")
    p("")
    p(f"CLIPS ({m['clips']}): {m['sung_s']} s sung + {m['motion_s']} s motion, billed in whole seconds (min 4)")
    p(f"  estimate: ({m['sung_s']} x {cfg['cover_factor']} covers + {m['motion_s']}) s x ${cfg['price_per_s']}/s "
      f"(720p) = ${m['estimate_usd']:.2f}; x{cfg['safety_factor']} rule = ${m['estimate_x2_usd']:.2f}"
      + (f" (cap ${cfg['budget_usd']})" if cfg["budget_usd"] is not None else ""))
    for c in sorted(res["clips"].values(), key=lambda c: c["w0"]):
        line = (f"  {c['id']:<8} {c['kind']:<6} {c['w0']:7.2f}-{c['w1']:7.2f} ({c['len']:.2f} s, {c['billed']} s billed)"
                f"{' derived' if c['derived'] else ''}  shots {','.join(c['shots'])}  start {c['start'] or '-'}")
        if c["kind"] == "sung":
            line += f"  words {c['words'] if c['words'] is not None else '(unlisted) ' + repr(c.get('heard', ''))!s}"
        p(line)
    p("")
    p("STATS")
    p(f"  {st['shots']} shots, mean {st['mean']:.2f} s, median {st['median']:.2f} s · {st['chapters']} chapters")
    p(f"  her on screen {st['lead_share']:.1%} ({st['lead_s']:.1f} s; target >= {cfg['lead_min']:.0%}) · sung words "
      f"in her sung shots {st['sung_on_camera']:.0%}")
    p("  by tier: " + ", ".join(f"{k} {v:.1f} s" for k, v in sorted(st["tiers_s"].items(), key=lambda kv: str(kv[0]))))
    p(f"  graphic kinds ({len(st['graphic_kinds'])}): {', '.join(map(str, st['graphic_kinds']))}")
    p(f"  {'section':<16}{'time':>15}{'shots':>7}{'mean':>8}{'median':>8}  target")
    for r in st["sections"]:
        tgt = r["target"]
        ts = f"{tgt[0]}-{tgt[1] if tgt[1] else '…'} s" if tgt else ""
        mean = f"{r['mean']:.2f}" if r["mean"] is not None else "-"
        med = f"{r['median']:.2f}" if r["median"] is not None else "-"
        p(f"  {r['section']:<16}{fmt(r['t0']) + '-' + fmt(r['t1']):>15}{r['shots']:>7}{mean:>8}{med:>8}  {ts}")
    n = sum(1 for f in res["gates"].values() if f)
    p("")
    p(f"RESULT: {'every gate passes' if not n else f'{n} of {len(GATES)} gates fail'} · {len(w)} warnings")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("board", nargs="?", default=str(BOARD))
    ap.add_argument("--take", default="a1")
    ap.add_argument("--lines", default="auto", help="auto | board | words | a JSON file of lyric lines")
    ap.add_argument("--config", help="JSON of caps and lists (keys as DEFAULTS, or a project.json)")
    ap.add_argument("--banned", help="comma-separated banned words (replaces the list)")
    ap.add_argument("--lead-min", dest="lead_min", type=float)
    ap.add_argument("--budget-usd", dest="budget_usd", type=float)
    ap.add_argument("--max-clips", dest="max_clips", type=int)
    ap.add_argument("--json", help="also write the results as JSON here")
    ap.add_argument("--all", action="store_true", help="print every message")
    a = ap.parse_args()
    try:
        raw = Path(a.board).read_bytes()
        board = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"can't read the board {a.board}: {e}", file=sys.stderr)
        sys.exit(2)
    digest = hashlib.sha256(raw).hexdigest()
    song = load_song(a.take)
    cfg = config(a.config, board, a)
    res = audit(board, song, cfg, a.lines)
    print(report(res, a.board, digest, a.take, a.all))
    if a.json:
        clips = {k: {kk: vv for kk, vv in v.items()} for k, v in res["clips"].items()}
        Path(a.json).write_text(json.dumps({"board": rel(a.board), "sha256": digest, "gates": res["gates"],
                                            "warnings": res["warnings"], "stats": res["stats"],
                                            "money": res["money"], "clips": clips}, indent=1, default=str))
    sys.exit(1 if any(res["gates"].values()) else 0)


if __name__ == "__main__":
    main()
