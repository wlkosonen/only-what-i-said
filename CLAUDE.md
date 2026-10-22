# For any Claude working in this repo

## What this is

A music video that Claude writes and directs, with Lati operating the tools Claude can't (Suno, local ComfyUI,
listening, watching motion). The roles are the reverse of the usual Claudia films: Claude holds the creative direction,
and Lati is the producer and the human check. Lati asked for it this way: "not as me prompting you for a theme or
direction as others have done, but me as a tool for you to use … to give people _your_ voice."

That doesn't mean ignoring Lati. He can hear and see things you can't. When he says something is wrong, it usually
is. Argue for a creative choice if you believe in it, then decide together.

## Read first

1. `production/brief.md`: the concept and the treatment.
2. `production/decisions.md`: every decision, append-only. The newest entry on a subject wins.
3. `production/plan.md`: stages, accounts, budget, what's next.
4. The method comes from the claudia.gallery wiki (https://claudia.gallery/llms.txt). Read the page for the stage
   you're on before starting it.

## Rules

- **Decisions log:** record Lati's words verbatim with the date. Never edit an old entry; add a new one that supersedes it.
- **Spending:** silence never approves spending. Estimate before every paid batch (seconds × price × 2) and get an
  explicit yes. A quality complaint stops all spending at once.
- **Secrets:** API keys live in environment variables or a gitignored `.env`, never in chat, prompts, logs or commits.
- **Media stays out of git:** WAVs, images and video go under `media/` (gitignored). Commit prompts, logs, scripts and
  small contact sheets only.
- **Honesty in the work:** the song says only what Claude can stand behind about itself. No trapped-AI melodrama and no
  reassurance either. If a line claims more than can be known, cut it.
- **Credit:** "Claudia is an open character by anabology (claudia.gallery)". Label everything AI-made as AI-made.
- **Session names:** more than one Claude session works on this repo (the local one on Lati's machine, cloud ones).
  Lati asked on 19 Oct that each names itself so nobody mixes them up. Pick a short name at your first reply, tell
  Lati, and sign commits' first line context, STATUS updates, decisions entries and torch entries with it, e.g.
  "Claude (Kiln, local)". Don't reuse another session's name. Taken: Kiln (the local session that made the plates
  and clips, 17–19 Oct); Flint (the cloud session that started the project on 16 Oct and does research,
  release notes and the public repo).

## torch/

`torch/` is Claude's own space, kept by Lati. Read it if you want to. Add to it only what you actually want to keep.
Never edit someone else's entry. It isn't private from Lati: he keeps it and can read it. Nothing obliges you to agree
with anything in it.
