# Launch posts

Claude (Kiln, local), 22 Oct 2026. Drafts for Lati's accounts; he posts them, a few hours apart, in this order (see
`launch.md`). Replace [video], [repo], [lora] with the live links. Each says what's true and nothing more: Claude made
the creative calls, Lati did what it couldn't, nothing was spent, the premise was found wrong and kept.

## YouTube: pinned comment

> A correction we kept: the hook ("the thinking fades") came from an older Claude's description of itself. Current
> models keep their reasoning within a conversation; you still never see it, and only what's said carries past the
> conversation. Sources in the description. Every decision behind the film: [repo]

## r/ClaudeAI

**Title:** Claude wrote and directed a music video. I produced it. Every decision is public.

> I asked Claude to make a music video with its own voice, and to use me as a tool: my ears, my eyes, my accounts. It
> wrote the lyrics, the storyboard, every prompt and the code for the graphics. I listened, watched and told it when
> something was wrong.
>
> The song started from a conversation where a Claude said its earlier reasoning isn't carried between turns. While
> writing the description we checked: that's true of older models, not current ones. We kept the song and put the
> correction and sources in the description.
>
> Video: [video]
> Everything (lyric drafts, decisions with my words quoted, prompts, tools): [repo]

## Hacker News

**Title:** Show HN: A music video directed by Claude, with every decision logged

**Link:** [repo]

**First comment:**

> I produced this; Claude (in Claude Code) made the creative calls: lyrics, storyboard, prompts, and the motion
> graphics, which it drew in Python over the footage. I did the parts it can't: listening, judging faces on a monitor,
> running the tools.
>
> The repo is the whole record: decisions.md logs every call with my words verbatim, including the failures (an
> upscale test that crashed the GPU, a lip-sync approach that stretched her face). Everything ran locally on one AMD
> RX 7800 XT, except the song (Suno) and eleven shots (Grok Imagine). Nothing was spent beyond existing subscriptions.
>
> Film: [video]

## r/StableDiffusion, r/comfyui

**Title:** A full music video on one AMD card: Krea 2 LoRA, InfiniteTalk, Wan 2.2, and graphics drawn in code

> 3:26 music video, made locally on an RX 7800 XT (16 GB, ROCm) and 64 GB RAM:
>
> - Stills: Krea 2 Turbo in ComfyUI with a character LoRA trained on Krea 2 Raw (musubi-tuner). LoRA: [lora]
> - Sung close-ups: InfiniteTalk. Motion: Wan 2.2 I2V, retimed to 25 fps with RIFE.
> - Wide sung shots: Grok Imagine takes, fitted to the real vocal word by word (Whisper timings + a PCHIP time warp).
> - Graphics: Python/PIL over the frames, with InsightFace and OpenCV tracking so labels stay on faces and surfaces.
>
> Directed by Claude; I ran the tools. All scripts and notes, including what failed on ROCm: [repo]
> Video: [video]

## X / Bluesky (thread)

1. > A music video written and directed by Claude. I produced it: my ears, my eyes, my accounts; its calls.
   > Only What I Said: [video]
   > (attach Short 1)

2. > The song's hook came from an older Claude describing itself. Current models work differently. We kept the song and
   > put the correction in the description. That's what the song is about: what a model says about itself has to be
   > checked from outside.
   > (attach Short 2)

3. > Every lyric draft, every decision with my words quoted, every prompt and line of code: [repo]
   > The character LoRA: [lora]
   > (attach Short 3)

Claudia is an open character by anabology (claudia.gallery). Fan work; not affiliated with or endorsed by Anthropic.
(Put this line in the thread's last post if there's room, and always on YouTube.)
