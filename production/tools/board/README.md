# Board tools

The audit and the review sheet for the storyboard (claudia.gallery wiki: toolkit §9–10, storyboard "The audit" and
"The board review", formats "The board"). The board is `production/board/board.json`; the song is the locked take's
analysis in `media/song/analysis/a1/`.

```bash
# the audit: a readable report; exit 0 only when every gate passes (1 = a gate fails, 2 = the board can't be read)
python3 production/tools/board/audit.py                      # production/board/board.json, take a1
python3 production/tools/board/audit.py path/to/board.json --lines words --all --json media/cache/audit.json
python3 production/tools/board/audit.py --config my-caps.json --banned "chains,help me" --lead-min 0.7

# the sheet: cover page with the chapter map, then pages of 12 cards, as PNGs and one PDF in media/board/sheet/
~/ComfyUI/venv/bin/python production/tools/board/sheet.py
~/ComfyUI/venv/bin/python production/tools/board/sheet.py --flags production/board/flags.json --picks media/plates/picks.json
~/ComfyUI/venv/bin/python production/tools/board/sheet.py --cols 2      # denser, for a desktop
```

The report's first line has the board's sha256. Record approvals against it: any later edit to the board makes it stale.

## Which lyric lines get checked

The "words typed" and "graphics" gates need the lines as they're **sung**, which isn't the sheet in a1's final chorus
("I only—" replaces "The", "If" isn't sung) or Build (three extra "I only keep what I said" that `words.json` doesn't
have). `--lines` picks the source:

| `--lines` | Source |
|---|---|
| `auto` (default) | the board's `lyric_lines` if it has them, else `words` |
| `board` | the board's top-level `lyric_lines` |
| `words` | the sheet as aligned in `words.json` (minus the board's `unsung_words`) |
| a file | a words.json-shaped file, a display.json-shaped file (lines with timed `tokens`), or `{"lines": [...]}` in the `lyric_lines` shape |

A `lyric_lines` entry is `{"line": <id>, "text": "…"}` plus its timing, one of:

- nothing more, when `line` is a sheet line number: its timed words from `words.json`;
- `"t0"`, `"t1"`: for a sheet line, only its words in that span; for a line not on the sheet (an id like `"b1"`), the line
  counts as one held word from t0 to t1;
- `"sheet_words": [i0, i1]`: those `words.json` word indices (inclusive), e.g. a Build hook that the aligner filed under
  another line;
- `"words": [{"w", "t0", "t1"}, …]` (or bare start times): explicit timing.

`"drop": [i, …]` on an entry, or top-level `"unsung_words": [337, 351]`, removes sheet words that aren't sung. The ids
are what the shots' `type[].line` and `devices[].line` refer to, so they can be ints (sheet lines) or strings (added
lines). When the list isn't the plain sheet, the audit warns about timed sheet words that no line covers.

## The gates

| Gate | Fails when |
|---|---|
| schema | a required field is missing, an enum is wrong (framing, motion_tier, type mode, device key), an id repeats, the shots aren't in time order, a section isn't in the beat map, a non-still shot has no plate (added gate) |
| tile | a gap, an overlap, a zero-length shot, or the ends aren't 0 and the song's duration |
| cuts | a cut more than 0.03 s from a beat, and not a hit in `hits.json`, the board's `hits`, or the shot's own `hit` |
| words typed | a sung word starts in a shot whose `type` doesn't list its line, or a word held across a cut isn't typed in both shots |
| graphics | a lyric line with no device whose `line` names it |
| lead share | `lead_on_screen` seconds under `lead_min` (0.70) of the song |
| motion budget | the estimate x2 over `budget_usd` ($350), or over any of `clip_s_max`, `sung_s_max`, `motion_s_max`, `max_clips` |
| clip windows | a sung window outside 4–8 s or starting inside a word, its listed words not matching the window; a motion clip outside 4–12 s; a window not covering its shots |
| plates unique | one plate on two shots that aren't adjacent (or chained with `continues`); two clips with one start frame |
| banned | a banned word anywhere in shots, chapters, plates, clips or lyric_lines (not `notes`) |
| treatments | a 2.5D shot without a treatment; the same treatment on two 2.5D shots in a row |
| to do | TODO / TBD / FIXME / XXX / ??? / `<PLACEHOLDER>` / lorem ipsum anywhere; no framing; an empty set, action, camera or transition_in; a plate with no prompt |

Warnings, which don't fail: a sung prompt with a hand, mic or hair over her mouth; her share above 85%; the same
non-cut transition twice in a row; an unused plate; a declared clip no shot plays; and also a stretch without her
longer than two bars, a shot straddling a section change, a shot's `section` or `lines` disagreeing with its time, a
prompt not ending "no text, no letters, no logos", fewer than six graphic kinds or one kind on three lines in a row,
a section's mean shot outside design.md's cut-rhythm target, a sung clip with no listed words, a declared hit not in
`hits.json`, and chapters that don't tile the song.

**Clips.** A motion or sung shot's `clip` id groups shots into clips. The window is the shot's `window: [t0, t1]`, or
a top-level `clips` entry, else the span of its shots ("derived"). A derived sung window under 4 s fails, with a
suggested window, because a sung clip's audio reference must be declared. Each clip is billed in whole seconds,
minimum 4. Estimate = (sung s x 1.6 for covers + motion s) x $0.23/s (720p), then x2 per CLAUDE.md. A clip's start
frame is its `start` (or the shot's `start_frame`), else its first shot's plate.

**Config.** Defaults are `DEFAULTS` in audit.py (budget $350 from plan.md, banned words from the brief's "What it
isn't", pace targets from design.md). `--config FILE` overrides them with a flat JSON of the same keys, or with a
project.json (`banned`, `board.lead_min`, `board.max_clips`, `budget.motion_s` → `clip_s_max`). A board's own
`banned` list adds to the defaults. `--banned`, `--lead-min`, `--budget-usd` and `--max-clips` override everything.

## board.json fields

As formats.md "The board". Top level: `{"version", "duration", "chapters", "shots", "plates"}`. A chapter is
`{id, name, t0, t1, sections, accent, set}`, a plate is `{plate, set, prompt, aspect, used_by}`.

| Field | Checked |
|---|---|
| `id` | required, `s001` style, unique, in time order |
| `t0`, `t1` | required numbers; tile the song; on beats or declared hits |
| `section` | required; a beat-map section name; warned if it isn't the section at the shot's middle |
| `lines` | required list; warned if it differs from the lines whose words start in the shot |
| `set`, `action`, `camera`, `transition_in` | required, non-empty, no placeholders |
| `lead_on_screen` | required bool; the lead share |
| `framing` | required: ECU · CU · MCU · MS · MWS · WS · FS · EWS · OTS |
| `motion_tier` | required: still · plate3d · motion · sung |
| `plate` | required; null only for a still (pure motion design) |
| `clip` | for motion and sung shots (missing → audited as its own clip, warned) |
| `prompt` | required; non-empty when there's a plate; should end "no text, no letters, no logos" |
| `type` | required list of `{line, mode, text, placement}`; mode: subtitle · coverline · masthead · stack · mass |
| `devices` | required list of `{kind, anchor, params, key, line}`; key: W · B · H · F · T; one with `line` is the explaining graphic |
| `treatment` | required on plate3d shots; never the same twice in a row |
| `chrome`, `accent`, `hit`, `notes` | optional; `hit` lets a cut sit on a declared hit; `notes` is skipped by the banned check |

Fields these tools add (all optional):

| Where | Field | Use |
|---|---|---|
| top | `title` | the sheet's title |
| top | `lyric_lines`, `unsung_words` | the as-sung line list (above) |
| top | `hits` | extra declared hit times (numbers or `{t}`) |
| top | `banned` | words added to the banned list |
| top | `clips` | `[{id, kind, t0, t1, words, start}]`: declared clip windows, words and start frames |
| shot | `window` | `[t0, t1]` of the shot's clip |
| shot | `clip_words` | the exact words of its sung window |
| shot | `start_frame` | its clip's start frame, e.g. `plates/cands/x/2.jpg` or `last:W03` |
| shot | `continues` | the id of an earlier shot it continues, so they may share a plate |
| shot / plate | `face_flag` | true puts FACE? on the card |
| shot | `frame` (or `image`) | the picked frame for the card; also a plate's `pick` (or `file`) |
| device | `desc` (or `label`, `text`, `title`, in it or its params) | the graphic's one line on the card |

## Not done

- Graded frames on the sheet: the film has no grade yet.
- The writer commands of toolkit §9 (set fields with checks, refuse placeholders): the board is written by hand.
- Device anchors, params and timing keys beyond the key letter aren't validated, and plate prompts aren't checked
  for her identity text.
