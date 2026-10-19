#!/usr/bin/env python3
"""Display tokens: what the viewer reads, timed on the sung words (wiki/toolkit, "8. Display tokens").

    media/cache/listen-venv/bin/python production/tools/listen/display.py a1 [--display production/lyrics/display.txt]

One display line per lyric line (same parser: blank lines and lines starting with '[' are skipped). `TEXT|n` shows
TEXT for the next n sung words, from the first word's start to the last word's end; `|0` rides on the next token.
In a line without any `|`, every word is its own `|1` token. In a line with `|`, each token is the text since the
previous `|n`; words left after the last `|n` are one-word tokens. Markers: *x* accent, ~x~ strike, _x_ mono.

Without a display file the sheet's own lines are used (every word shows as sung), which only checks the plumbing.
Writes media/song/analysis/<take>/display.json and exits non-zero, naming the line, if any line does not consume
exactly its aligned words.
"""

import argparse
import json
import re
import sys

import common

MARKS = {"*": "accent", "~": "strike", "_": "mono"}


def tokens(line):
    if "|" not in line:
        return [(w, 1) for w in line.split()]
    out, pos = [], 0
    for m in re.finditer(r"(.*?)\|(\d+)", line):
        out.append((m.group(1).strip(), int(m.group(2))))
        pos = m.end()
    out += [(w, 1) for w in line[pos:].split()]
    return out


def style(text):
    for ch, name in MARKS.items():
        if len(text) > 2 and text[0] == ch and text[-1] == ch:
            return text[1:-1], name
    return text, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("take")
    ap.add_argument("--display", default=str(common.ROOT / "production/lyrics/display.txt"))
    ap.add_argument("--lyrics", default=str(common.LYRICS))
    args = ap.parse_args()

    d = common.out_dir(args.take)
    words = json.loads((d / "words.json").read_text())["words"]
    lines, _ = common.read_lyrics(args.lyrics)
    try:
        disp = [s.strip() for s in open(args.display, encoding="utf-8")
                if s.strip() and not s.strip().startswith("[")]
        source = args.display
    except FileNotFoundError:
        disp = [ln["text"] for ln in lines]
        source = "the lyric sheet itself (no display file yet)"

    errors = []
    if len(disp) != len(lines):
        errors.append(f"{len(disp)} display lines for {len(lines)} lyric lines")
    out = []
    for ln, text in zip(lines, disp):
        ws = [w for w in words if w["line"] == ln["line"]]
        toks, k, pending = [], 0, []
        for raw, n in tokens(text):
            body, st = style(raw)
            if n == 0:
                pending.append((body, st))
                continue
            span = ws[k:k + n]
            k += n
            placed = [w for w in span if w["t0"] is not None]
            t0 = min((w["t0"] for w in placed), default=None)
            t1 = max((w["t1"] for w in placed), default=None)
            for pb, ps in pending:
                toks.append({"text": pb, "style": ps, "t0": t0, "t1": t1, "words": [], "rides": True})
            pending = []
            toks.append({"text": body, "style": st, "t0": t0, "t1": t1, "words": [w["i"] for w in span]})
            if len(placed) < len(span):
                errors.append(f"line {ln['line']} token {body!r}: {len(span) - len(placed)} word(s) without a time")
        if k != len(ws) or pending:
            errors.append(f"line {ln['line']} consumes {k} words, the sheet has {len(ws)}: {text!r} / {ln['text']!r}")
        out.append({"line": ln["line"], "display": text, "tokens": toks})
    common.write_json(d / "display.json", {"source": source, "lines": out})
    md = ["## Display tokens", "", f"From {source}: {len(out)} lines, "
          f"{sum(len(l['tokens']) for l in out)} tokens. " +
          ("All lines consume exactly their aligned words." if not errors else f"**{len(errors)} problem(s):**")]
    md += [f"- {e}" for e in errors]
    common.update_report(args.take, "display", "\n".join(md))
    print("\n".join(md))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
