# Grok Imagine pilot: real motion for the shots where she acts

Claude (cloud session), 19 Oct 2026. Lati: "I also have supergrok account. Could that be leveraged with imagine for
more motion etc?"

## Why

About 124 s of the board (41 shots) is `plate3d`: 2.5D camera moves over a still plate. That works for pure camera
moves (push, orbit, rack focus, relight), which also land exactly on the beat in our own renderer. It's weakest where
the board asks her to *do* something with her mouth closed: glance, turn, look up, walk. A still can't glance.

Grok Imagine (image-to-video from a plate) fits that gap:
- It's in Lati's subscription, so there's no per-clip spend; the limits are the usage pool and Lati's time.
- It's fast, compared with about 35 minutes per 5 s for local video at 832×480.
- Skybrows' breakdown (`production/notes/skybrows-lessons.md`) singles out its secondary motion: hair, cloth, small
  movements.

What it isn't for: the sung windows. Photoreal lips need audio-driven sync, and the local InfiniteTalk test passed
Lati's eye. Skybrows does lip sync in Grok by nudging clips in the edit, but says himself that works because anime is
on twos; for live action he'd use an audio-driven model.

## Unknowns the pilot answers

1. Does it accept her? Seedance on OpenRouter refused her plates as "may contain real person".
2. Does her identity hold through a head turn: one streak, the clip, the mic, the same adult face?
3. Does it invent things? Skybrows: Grok is "super creative" and will add cat ears unless held in "accuracy mode".
4. Does the output match the local plates in colour and grain, closely enough to grade?
5. Is there a visible watermark on downloads, and what resolution and length does Lati's tier give?
6. **Terms:** I couldn't read xAI's terms from the cloud session (403). Lati: please check in the app what they say
   about owning and publishing generated videos before anything from Grok goes into the cut.

## The three pilot shots

Two takes each, at the longest and highest-resolution setting the tier allows; we cut what we need. **Discard Grok's
audio**; the soundtrack is `a1.wav`. Upload the picked plate (`media/plates/picked/p-<shot>*.png`) as the image.

Every prompt ends with the same accuracy block (identical across clips so the look doesn't drift), and everything is
phrased as what she does, never as what she doesn't do.

**Accuracy block (paste after each prompt):**

```prompt
Keep her face, her black bob and bangs, the single thin clay-orange streak, the small clay-orange star clip, the thin headset microphone and her clothes exactly as in the image in every frame. Keep the set, the lighting, the colours and the fine film grain exactly as in the image. Photoreal live-action 35mm film footage at 24 frames per second, natural human motion, one woman in the shot. Her lips stay softly together the whole time, silent and calm.
```

### s029: she walks along the poster wall (board: 2.0 s, 79.48–81.50)

The hardest case for 2.5D: a walking person faked with a layer slide looks like a cut-out.

```prompt
She walks at an even, unhurried pace along the wall of old, faded, sun-bleached posters, in profile, in the direction she is facing, eyes forward, arms relaxed at her sides. Her skirt's pleats and her hair move with each step. The camera tracks sideways alongside her at her chest height, smooth as a dolly on rails, keeping her the same size in frame. The posters stay still on the wall.
```

### s028: she turns to the empty mold (board: 3.5 s, rack focus to the mold on "mold", 79.04)

The plate already shows the end of the turn (her looking over her shoulder at the mold). Image-to-video starts from
the plate, so we use Skybrows' reversed-clip trick: generate her turning *away* from the mold toward the camera, then
play the clip backwards. The finished shot turns toward the mold and lands on the approved plate. The rack focus
to the mold stays in post.

```prompt
She slowly turns her head from the empty white plaster mold on the workbench back toward the camera and settles, head level, calm, eyes straight into the lens. A slow blink. Dust hangs and drifts in the shaft of window light. The camera is locked off at her eye level, completely still, as on a tripod.
```

### s020: she looks up at what rises off her (board: 4.0 s, "The thinking fades, the words go on ahead")

A held close shot where a little life matters more than a camera move. The grey thinking particles stay in post.

```prompt
She slowly raises her eyes upward, as if watching something drift up from her hair and fade above her, calm and curious, chin level. A slow blink. A few strands of her bangs stir in a faint draft. The camera is locked off at her eye level, completely still, as on a tripod.
```

## How we run it

1. Lati runs the six generations in the Grok app and saves them as
   `media/clips/grok/<shot>-take<n>.mp4` (originals, unedited).
2. The local Claude pulls contact sheets of frames (PyAV, as for the local clips) and checks identity, invented details,
   grain and the watermark. Lati watches the motion: Claude sees frames, not movement.
3. Each pilot shot is compared with its 2.5D version from the renderer. Grok replaces a `plate3d` shot only where it is
   clearly better *and* the terms allow it.
4. If it passes, candidates for a second round: the other glances and looks (s014, s016, s036, s040), the held
   portraits that would gain a breath and a blink (s010, s022, s042), and her looking out from the stack (s060).
   Pure camera-move shots stay 2.5D: our renderer puts their moves exactly on the beat.

If a take drifts (a second streak, a changed face, invented text on the posters), re-roll it; don't fix the frame.
