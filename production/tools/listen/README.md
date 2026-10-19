# Listening tools

Stems, timed words with an ear-check list, the beat map, sections and hits, and display tokens for the picked Suno
take. Built to the claudia.gallery spec (wiki/toolkit 4-8, file formats from wiki/formats). Everything runs on the
CPU: `common.py` hides the GPU before torch loads, so these tools can run while the GPU trains.

Dry run so far: `a1` only (17 Oct 2026), before Lati picked a take. Nobody has listened to any of the output yet.

## Setup (once)

```bash
python3 -m venv media/cache/listen-venv
media/cache/listen-venv/bin/pip install --no-deps -r production/tools/listen/requirements.txt
```

The venv is about 2.5 GB. Models download on first use to `media/cache/listen-models/` (about 5 GB):
htdemucs (Hugging Face), `facebook/wav2vec2-large-960h-lv60-self` (Apache-2.0), torchaudio MMS_FA, and Whisper
`large-v3-turbo`.

## Run on the picked take

Put the take at `media/song/<take>.wav` (e.g. `a3`), then, from the repo root:

```bash
PY=media/cache/listen-venv/bin/python
T=a3                                                # the picked take
$PY production/tools/listen/stems.py    $T          # ~1 min: stems/{vocals,drums,bass,other}.wav
$PY production/tools/listen/align.py    $T          # ~3 min: words.json, earcheck.json, sung.json
$PY production/tools/listen/beatmap.py  $T          # ~10 s: beats.json (beats, downbeats, tempo curve)
$PY production/tools/listen/sections.py $T          # ~10 s: sections into beats.json, hits.json
$PY production/tools/listen/display.py  $T          # instant: display.json; exits 1 if a line doesn't fit
```

Order matters: align needs the vocal stem; sections needs words.json and beats.json. Output goes to
`media/song/analysis/<take>/` (gitignored). Read `report.md` there first: one block per tool, the ear-check table,
the spots to play to Lati, what the take really sings against the sheet, and the energy per bar.

Other options: `align.py --lyrics <file>` for a different sheet, `--whisper medium` for a smaller model, `--redo` to
recompute the cached emissions and transcript; `beatmap.py --tempo-range 110 125 --downbeat-phase 0..3`;
`display.py --display production/lyrics/display.txt`; `LISTEN_THREADS=8` sets the CPU threads.

## Overrides that survive re-runs

`production/song/listen/<take>.json` (create it when needed; small text, goes in git):

```json
{"tempo_range": [112, 126],
 "downbeat_phase": 0,
 "hits": {"add": [[170.7, 0.8]], "drop": [146.2]},
 "name_map": {"claw": ["claude"]},
 "words": [{"i": 337, "w": "the", "t0": 167.10, "t1": 167.30, "note": "Lati: early by a hair, 18 Oct"}]}
```

A manual word becomes `src: manual` with its note, is skipped if the sheet word at that index changed, and is never
flagged again. Rule from the spec: if the take sings something else, fix the sheet; if it sings the sheet, fix the
times. Never edit the audio, and never apply a change from `sung.json` that nobody has heard.

## The ear check

`earcheck.json` lists every flagged word, most urgent first (letters, missing, order, gap, verylow, length,
lowconf), with the MMS second aligner's opinion (`mms_delta`; within 0.3 s counts as agreement) and whether Whisper
heard it. Each item has `status` and `note` to fill in: kept, moved (add it to `words` above) or asked. `spots` holds at
most five 10-20 s windows to play to Lati with the words on screen: "ok, early or late for each". Done when every
flag is kept, moved or asked about, with a note, before the board.

## Files

| file | what |
|---|---|
| `common.py` | paths, CPU-only torch, audio loading, the lyric parser, onset helpers, JSON and report writing |
| `stems.py` | htdemucs, four stems |
| `align.py` | wav2vec2 CTC Viterbi alignment, MMS_FA witness, Whisper fallback and transcript, flags |
| `beatmap.py` | windowed tempo fit on the drum stem, beats snapped to the kick, downbeat votes |
| `sections.py` | sections from the lyric's tags + segment changes, energy per bar, kicks/snares/hats, impacts, risers, fills, vocal entries, 24 fps envelopes |
| `display.py` | display tokens timed on the words; fails loudly if a line doesn't consume exactly its words |
| `requirements.txt` | the frozen venv |
