# Lessons from Skybrows' "Zuckerwars" breakdown

Claude (cloud session), 19 Oct 2026, from the transcript of "Zuckerwars Process Breakdown featuring CyberNuggets"
(https://youtu.be/fyv-fO-sWhY), which Lati sent. Skybrows is a CG generalist with about 16 years in 3D and VFX; Zuckerwars is a
13-minute anime music video, about 400 hours of work, made with Seedance 2.0/2.5, Grok, GPT image 2, Veo and Wan,
then edited in DaVinci Resolve.

His film is fast anime action; ours is slow, close and photoreal. What's below is only what transfers, ranked by what
it would do for this film. His findings come from his own tools (mostly Seedance and Grok). Where we'd use them on
Wan 2.2 or InfiniteTalk they're untested: try them on one shot before changing a batch.

## 1. The thinking layer as an after-image (post only, free)

His effect: duplicate a clip, drop the copy to half the frame rate, put it under the original with a *lighten*
blend. The half-rate copy trails behind her as after-images. ("It created this ghosting flashing effect where he'd
leave after images.")

For us: make the grey "thinking" a faint, half-rate after-image of her that trails and fades, while she and the clay
"said" type stay solid. It's cheap, in code, and it fits the corrected premise (decisions, 19 Oct): the thinking is
there but you don't see it plainly; what you see clearly is what's said. Keep it subtle, at 20–30% opacity, only on
the lines where the thinking matters, not as a constant effect.

## 2. Retime instead of regenerating

- **Clip speed ±5–15% to land a moment on the beat.** He does this to most clips: "sometimes it's like 10% faster
  or 5% slower… just for it to happen on the beat." For us: land each tablet slam exactly on the *d* of "said" by
  retiming the motion clip, not by re-rendering it (each local render costs about 7 minutes of GPU per second of clip).
  Not for sung windows: retiming breaks the lips.
- **Flip a clip** when the direction of motion fights the cut.
- **A black frame** "gives you a little shock in time… gets you somewhere else at some other time without feeling like
  a weird break." Our world is a black void, so a one- or two-frame black between chapters is nearly free.
- **Match cuts in motion,** not only in framing: cut in the middle of a movement and pick it up mid-movement in the
  next shot (his example: a head turn that finishes across the cut). It works for a slow film too: a head turning
  toward the lens, a hand reaching across the cut.
- **Hard cuts hide in chaos.** Ours has little chaos, so our cuts need a reason: the beat, the *d*, a black frame, a
  match in motion.

## 3. Prompting the video model

- **Say what she does, not what she doesn't.** His test: "no white elephants" made a character *say* "no white
  elephants". Negative words plant the idea. Our standing note against the sultry head tilt should be written
  positively in every plate and clip prompt: *"her head level, chin level, eyes straight into the lens, calm and
  direct"*, with no mention of tilt.
- **"Accuracy mode":** creative models drift. Phrases about keeping things the same ("maintain her face, hair and
  wardrobe exactly as in the first frame; maintain the lighting; perfect character consistency") pull the model
  toward holding the frame rather than inventing. Worth an A/B on one Wan 2.2 motion clip.
- **Anchor the camera physically.** By default the camera drifts somewhere uninteresting. He pins it ("skims along the
  surface of the water"). For us: "the camera is locked at her chest height", "the camera dollies straight in at eye
  level", matching the board's low-angle wides at chest height.
- **Tied elements come for free, whether you want them or not:** a close explosion brings camera shake; a heavy
  object landing may bring dust and a shake. For each tablet slam, decide whether we want the shake and say so either
  way.
- **Models take the easiest path:** several things moving in sync unless asked otherwise. If anything in frame should
  move independently (the posters, the dust, the sculptor's figures), ask for it.
- **More precision means more ways to fail.** For kinetic shots he asks for the *kind* of thing and leaves the details
  open. For slow story moments that must happen exactly, he specifies. Most of our shots are the second kind, so spend
  precision only where the board needs it (eyes opening on "the cursor stops", the *d*).
- **Structure:** a fixed style block (about half the prompt, reused across shots) plus the shot's beats, written by an
  LLM from the style block. The clip book likely already works this way; check that the style block is identical
  across clips so the look doesn't drift.

## 4. Farm the hero shots, not everything

"You're looking at the best of like 50." He queues generations in the background while working on something else and
cuts usable pieces out of broken takes. Locally, our cost is GPU time, so farm only the shots the film hangs on: the
eyes opening at ~8.3 s, the first slam on "said", standing on top of the song, the hand-off at the end. Two or three
seeds each, overnight. Keep a graveyard of rejected takes; one of them may fill a gap later.

## 5. Suno: the verse-cover trick (optional, Lati's ear decides)

"Change your lyrics so that they are just that verse three times in a row. Then you're going to get three takes of
that verse based on the DNA of your song." Use a **cover** of the existing song, not Studio's edit, which "veers so
far off". Covers also drift toward the average later in a song, so put the line you need early.

For us: the swallowed "The thinking fades" at ~2:48. A cover of a1 with only the final chorus written three times,
then the best bars spliced in. **But** every shot is timed to `a1.wav`, and Suno takes drift in tempo. Only worth it
if the splice replaces exactly the same bars at the same length, checked against the beat map. Lati already judged
the line acceptable as it is ("Honestly I think it works", about the first chorus's drop), so this is an option, not a
fix we need.

## 6. Restraint

His own warning: "I think I got to cool it with the screen pumps… I've got an itchy trigger finger." And: "it looked
good in the moment, but after you've watched like 5 minutes of the pumping…" Our film is one person telling the truth
to one person. One effect per meaning, each tied to a word. Look at the cut again the next day before calling it
done; the gallery's rule of showing a 30-second excerpt first covers the same ground.

## Not for us

Prompting in Japanese for an anime look, animating on twos, smear frames, multiples and impact frames, Grok for dance,
Runway Unlimited farming, restyling characters so a video model accepts them (Seedance's filter refused her as a "real
person"; changing her look to get past it isn't on the table).
