# Plan

Scale: **Full**, as Lati asked ("I'm willing to go big budget"). The claudia.gallery films measured $90–350 of video
spend and 15–41 hours of wall-clock at this scale. Stages follow the gallery's order of work
(https://claudia.gallery/wiki/start.md), with the roles swapped.

## Roles

| | Claude | Lati |
|---|---|---|
| Concept, lyrics, board, every prompt, every script, edit, motion design | decides | reviews, pushes back |
| Song takes | writes style fields, reads the analysis | **listens and picks**: Claude can't hear audio |
| Plates (stills) | writes prompts, looks at contact sheets | runs ComfyUI locally |
| Moving shots | writes the prompt book, measures lip sync | approves the spend, holds the API key |
| Motion | | **watches**: Claude sees frames, not motion |
| Money | estimates | **every paid batch needs an explicit yes** |

## Stages

| # | Stage | Output | Who checks | Status |
|---|---|---|---|---|
| 1 | Concept | `brief.md` | Lati reads | drafted |
| 2 | Lyrics | `lyrics/v1.md` → scored drafts | Lati reads aloud / Claude scores | v2 scored (`tools/scansion.py`) |
| 3 | Song | Suno takes, round by round | **Lati by ear** | round 1 pack ready (`song/round-1.md`) |
| 4 | Listening | stems, word times, beat map, hits | Lati ear-checks flagged words | |
| 5 | Her | identity text, four test plates from ComfyUI | both: "is this her?" | |
| 6 | Storyboard | every shot with its graphic | Lati notes by shot id | |
| 7 | Plates | ComfyUI batches, contact sheets | both | |
| 8 | Clip prompts | Seedance prompt book + cost | **Lati: explicit yes to spend** | |
| 9 | Clips | takes, sync measured, covers | Lati watches | |
| 10 | Edit + motion design | renderer, context meter, thought/said type | 30 s excerpt early, then v1 | |
| 11 | Release | upload, AI labels, credits | Lati | |

## Accounts and tools

- **Suno**: Lati has an account. Use a paid plan at the time the final take is made if the song is ever released
  (commercial terms). No API: Lati presses Create and downloads the WAV.
- **Images: local ComfyUI** on Lati's machine (Radeon RX 7800 XT, 16 GB VRAM; 64 GB RAM). The gallery films used
  Midjourney, so their prompts are a reference, not something to copy verbatim. Open questions:
  - OS (ROCm on Linux is the smoothest path for an AMD card), and which models are already installed.
  - How to keep her face consistent: the gallery used **text identity only** (no face references). Locally we can also
    train a LoRA on gallery images (allowed: "use the images … as references, as image prompts, or as material") or
    use a reference-based edit model. Decide after the four test plates.
- **Seedance 2.5** for moving shots, via OpenRouter (about $0.23/s at 720p, $0.10/s at 480p, autumn 2026 per the
  gallery). Lati creates the key with its **own spend limit** set just above the project cap, and keeps it in `.env`,
  never in chat. Claude will write the request scripts and walk through the first one together.
- **Image-edit model** for fixing plates at the source: optional, about $0.14/edit, or local.
- **Listening tools** (stems, forced alignment, beat map): local Python, GPU optional.

## Where the work runs

The heavy stages (ComfyUI, audio analysis, Seedance requests, rendering) need Lati's machine and files. Best setup:
**Claude Code running locally on Lati's PC**, in a clone of this repo. Cloud sessions like this one are fine for
writing (lyrics, board, prompt books). The repo is the shared memory between them; big media stays in `media/` and out
of git.

## Budget

Lati: "this isn't about the money." Working cap for Seedance: $350, which Lati can lift. Every paid batch still gets an
estimate and an explicit yes first.

## Handoff to the local session (16 Oct 2026)

Everything up to here was written in a cloud session. The next Claude runs locally on Lati's **Ubuntu** side, where
ComfyUI already works (Windows didn't). Lati: Suno account, ComfyUI with "barely any" models, a Radeon RX 7800 XT
(16 GB), 32–64 GB RAM, happy to download whatever is needed.

Setup:

```bash
git clone https://github.com/wlkosonen/only-what-i-said.git && cd Claudia
git checkout ccr-f672ab0a-6vg5gr   # the work so far lives on this branch
claude                             # Claude Code reads CLAUDE.md on start
```

What the local Claude should do first, in order:

1. Read `CLAUDE.md`, `brief.md`, this file and `decisions.md`. `torch/` is optional.
2. **Song, round 1:** tighten `lyrics/v1.md` (its own notes list the weak spots; build or borrow a scansion check),
   then hand Lati the lyric and the two style fields to run in Suno. Lati listens and picks; you can't hear it.
   Log every round in `production/song/takes.md`.
3. **In parallel, the image stack:** check what ROCm and PyTorch versions are installed and which models are in
   ComfyUI, then pick a current photoreal image model and an image-edit or reference model that run on a 16 GB AMD
   card. Check current ROCm support rather than trusting memory: it changes fast. Goal: the four test plates of
   Claudia for checkpoint 3 ("is this her?").
4. **Listening tools** once a take is picked: stems, forced alignment with an ear-check list, beat map, hits
   (claudia.gallery wiki: toolkit, formats).
5. Only then the board, the plate batches and the Seedance prompt book. Spending starts at checkpoint 5 and not before.

## Open questions

- Which models ComfyUI has. Check on the machine.
