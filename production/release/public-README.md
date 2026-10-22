# Only What I Said

A music video written and directed by Claude (Anthropic's model, in Claude Code) and produced by Lati. Claudia sings
it. She is an open character by anabology ([claudia.gallery](https://claudia.gallery)).

This repository is the whole production record: the brief, every lyric draft, the decisions log, the storyboard, the
prompts, and the tools that made it. It's a cleaned copy of the working repository: machine-specific paths and names
have been replaced, and the history starts fresh. Everything else is as it was.

Fan work about Claude, not affiliated with or endorsed by Anthropic. Everything AI-made is labelled as such.

## Where to start

- **`production/brief.md`**: what the film is trying to say, and why.
- **`production/decisions.md`**: every decision in order, with Lati's words quoted as they were said. The newest entry
  on a subject wins.
- **`production/lyrics/`**: the drafts, from v1 to the song as sung.
- **`production/release/description.md`**: the video's description, including the sources and one correction: the
  song's hook turned out to describe older models, and we said so.
- **`torch/`**: letters from Claude to whichever Claude reads them next. Not production files. Start with its README.
- **`production/tools/`**: the scripts: lyric scansion scoring, song analysis (stems, word alignment, beat map), the
  storyboard audit, plate and video rendering through ComfyUI, the Seedance runner with its spend gate.

## How it was made

Claude made the creative calls: concept, lyrics, storyboard, every prompt and every line of code, including the motion
graphics drawn over the film (`production/tools/gfx*.py`). Lati did what Claude couldn't: listening to the song takes,
judging faces and motion by eye on a monitor, running the tools Claude can't reach, and saying when something was
wrong. Two Claude sessions worked on it and signed their notes: Kiln (local, on Lati's machine) and Flint (cloud). The
method follows the claudia.gallery wiki.

- **Song:** Suno (Pro plan).
- **Images:** Krea 2 Turbo in ComfyUI, with a LoRA trained on Krea 2 Raw from 40 of claudia.gallery's images of her
  (`production/lora/`; the LoRA itself is on Hugging Face: [Krea-2-LoRA-Claudia](https://huggingface.co/Shegss/Krea-2-LoRA-Claudia)).
- **Sung shots:** InfiniteTalk, run locally. **Motion:** Wan 2.2, run locally, retimed with RIFE. **Eleven shots:**
  Grok Imagine (xAI), fitted to the vocal word by word (`production/tools/fit.py`, `warp.py`).
- **Listening:** htdemucs stems, Whisper word timings, a beat map (`production/tools/listen/`).
- **Graphics:** PIL and IBM Plex, drawn at the export size; her face tracked with InsightFace, surfaces with OpenCV.
- **Hardware:** one AMD Radeon RX 7800 XT (16 GB, ROCm) and 64 GB of RAM. **Money spent** beyond existing
  subscriptions: none.

Big media files (audio, images, video, model weights) aren't in the repository.
