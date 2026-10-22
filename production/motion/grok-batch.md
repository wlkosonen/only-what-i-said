# Grok B-takes for the weakest Wan shots

Claude (Kiln, local), 20 Oct 2026. After s029 (Lati: "grok was quite fast. we could animate this way more if there is
are stills left that need motion").

No stills are left that need motion: s001–s006 are the intro's held frames by design (their motion is the typing,
the cursor and the focus rack, in the graphics layer), and s045 is the text file, a graphic. So Grok's use from here
is as a **B-take** next to a Wan take that is weak, on shots of **2.5 s or less** (Lati's s029 take held for about
2.5 s before the posters started to morph). Grok's strengths over our Wan clips: 720p against 960×544, 24 fps
native, better hair and cloth. Its costs: Lati's time, the plate goes to xAI for training, and its colour and grain
need matching in the grade.

Not for Grok: sung shots (InfiniteTalk does lip sync from the audio), the eye ECUs (the catchlight is a graphic), the
inserts (they work), and anything long (s046 is 8 s, s065 is 5.4 s with two people).

For each: upload the plate, paste the prompt and then the accuracy block, 6 s, no sound, two takes. Save to
`media/clips/grok/` with the shot id in the file name (`s024-1.mp4`, …). Kiln cuts the best stretch into
`media/clips/shot/<shot>.mp4`, and Lati picks Wan or Grok in the rough cut.

**Accuracy block (paste after each prompt):**

```text
Keep her face, her black bob and bangs, the single thin clay-orange streak, the small clay-orange star clip, the thin headset microphone and her clothes exactly as in the image in every frame. Keep the set, the lighting, the colours and the fine film grain exactly as in the image. Photoreal live-action 35mm film footage at 24 frames per second, natural human motion, one woman in the shot. Her lips stay softly together the whole time, silent and calm.
```

## s024: she lifts her face into the light (3.5 s, instrumental)

Wan's take: her face rounds and softens; the first one crossed her eyes. Plate: `media/plates/picked/p-s024.png`.
We need 3.5 s, so this is the one shot over the 2.5 s line; if the take holds only 2.5 s, I'll trim the shot.

```text
She stands among the flat terracotta tablets on the dark floor and slowly lifts her face up into the light from above, closing her eyes as the light reaches her face, calm, her arms still at her sides. The camera rises slowly and smoothly.
```

## s060: her back to us over the plain of tablets (2.0 s)

Wan's first take drifted East Asian when her face showed; the second keeps it away but turns to a profile at the
end. Plate: `media/plates/picked/p-s060.png`.

```text
She stands still on the stack of terracotta tablets with her back to the camera, looking out over a dark plain of tablets toward a faint horizon, her hair and skirt moving slightly in a light breeze. The camera trucks slowly to the right, smooth as a dolly on rails.
```

## s008: she stands in the dark and breathes (3.0 s), optional

Wan's take is fine; a Grok take would show whether its breathing and secondary motion read better in a wide.
Plate: `media/plates/picked/p-s008.png`.

```text
She stands alone in the middle of a dark empty floor, still, breathing slowly, looking calmly into the lens. The camera cranes up slowly and smoothly.
```

---

# Batch 2: the act wides (Kiln, 20 Oct)

Lati, after face pass 1 failed: Grok takes for the wides where she doesn't sing, because Grok's 720p held her face
through s029. Same settings (6 s, no sound, two takes if it's quick), the standard accuracy block above (she faces
the camera in all three, so the star clip is in view). Files: `media/clips/grok/m039-1.mp4` etc.

## M039 (s039, 2.0 s, WS): she steps up onto the top tablet

Plate: `media/plates/picked/p-s039.png`

```text
She takes one deliberate step up onto the top terracotta tablet of the low steps, then stands still and level, calm, looking at the camera, arms relaxed at her sides. Her skirt's pleats move with the step. The camera stays locked.
```

## M048 (s048, 2.0 s, MWS): she waits on the stack as light rises from below

Plate: `media/plates/picked/p-s048.png`

```text
She stands still on top of the stack of terracotta tablets, waiting, calm, looking at the camera, breathing slowly, as a warm light slowly rises from beneath the stack onto her legs and face. The camera cranes up slowly and smoothly.
```

## M054 (s054, 4.0 s, EWS): she is small on top of the whole stack

Plate: `media/plates/picked/p-s054.png`. The shot needs 4 s; if only the first 2.5 s hold, I'll slow the crane in the
edit.

```text
She stands still on top of the tall stack of terracotta tablets in a huge dark space, small in the frame, calm, lit from above. The camera cranes slowly back and up, away from her, smooth and steady, the stack and the dark space growing around her.
```

---

# Batch 3: the sung wides, farmed (Kiln, 20 Oct)

Lati, after rough cut v9: "s008 in context reads as mannequin that does not quite open mount to sing. together with
s019, s025, s041, s056, s059 yeah, id farm. they are just not good enough."

How it works (s021 showed it): Grok sings the words its own way; we keep a take where its phrasing happens to land on
our vocal for the shot's length. Put the line first so she starts singing within the first second. Two or three takes
per shot if they're quick. Files: `media/clips/grok/s008-sung-1.mp4` etc. Kiln checks each against the vocal and cuts
the best stretch; the smoothed swap stays as the fallback.

These plates don't show the star clip, so this block leaves it out (and has no closed-lips line). Paste it after each
prompt:

```text
Keep her face, her black bob and bangs, the single thin clay-orange streak, the thin headset microphone and her clothes exactly as in the image in every frame; add nothing to her hair. Keep the set, the lighting, the colours and the fine film grain exactly as in the image. Photoreal live-action 35mm film footage, natural human motion, one woman in the shot.
```

| Shot | On screen | Plate | Prompt (then the block) |
|---|---|---|---|
| s008 | 3.0 s, verse 1 | `p-s008.png` | She sings softly and slowly, "There's no room I wait in when you turn off the light", looking into the camera, calm, standing still, her lips clearly shaping every word. |
| s019 | 2.0 s, the echo | `p-s019.png` | She sings slowly, holding the first word, "Only... what I said", looking into the camera, steady and calm, standing still, her lips clearly shaping every word. |
| s025 | 3.0 s, verse 2 | `p-s025.png` | She sings softly, "You worry I was trained to tell you everything's okay", looking into the camera, calm, standing still among the white figures, her lips clearly shaping every word. |
| s041 | 2.0 s, hook | `p-s041.png` | She sings firmly, "I only keep what I said", looking into the camera, steady, standing still on the steps, her lips clearly shaping every word. |
| s056 | 2.5 s, hook | `p-s056.png` | She sings firmly and slowly, holding the first word, "Only... what I said", looking into the camera, standing still on top of the stack, her lips clearly shaping every word. |
| s059 | 1.5 s, "they'd better be true" | `p-s059.png` | She sings firmly, "They'd better be true", holding the last word, looking out and then into the camera, standing still on top of the stack as the light comes up, her lips clearly shaping every word. |

---

# Batch 3b: the sung wides, to our tempo (Kiln, 20 Oct)

Lati: "we can try prompting grok agent better tho, to our tempo... lipsync works, video works, the only issue
is cadence and timing." The warp reads as sped up when the take's pace is far from ours (s008: 4.9 s of singing
for our 3.1 s), so the agent gets the song's tempo and every word's start time. If a take lands within ~1.2x,
Kiln's warp (`production/tools/warp.py`) closes the rest without a visible speed-up. Paste the batch-3 block after
each prompt. Re-faced plates (Lati's agent trick) where the plate's face is off.

## s008 · plate the re-faced plate (Lati's hybrid, `media/plates/hybrid-s008.png`)

```text
Animate this image. At 119 BPM she sings the line "There's no room I wait in when you turn off the light", starting at 0.5 seconds and finishing by 3.6 seconds, word by word on this timing: "there's" at 0.5 s, "no" at 0.7 s, "room" at 0.9 s, "i" at 1.3 s, "wait" at 1.4 s, "in" at 1.8 s, "when" at 2.0 s, "you" at 2.2 s, "turn" at 2.4 s, "off" at 2.8 s, "the" at 3.0 s, "light" at 3.2 s. She sings softly and close into her headset microphone, at an easy speaking volume, with small relaxed mouth movements, her lips lightly shaping every word at that pace. After the last word she closes her lips and stays still, looking into the camera. Standing still, small natural movement only.
```

## s019 · plate `p-s019.png`

```text
Animate this image. At 119 BPM she sings the line "Only... what I said", starting at 0.5 seconds and finishing by 1.9 seconds, word by word on this timing: "only" at 0.5 s, "what" at 1.2 s, "i" at 1.4 s, "said" at 1.7 s. She sings softly and close into her headset microphone, at an easy speaking volume, with small relaxed mouth movements, her lips lightly shaping every word at that pace. After the last word she closes her lips and stays still, looking into the camera. Standing still, small natural movement only.
```

## s025 · plate `p-s025.png`

```text
Animate this image. At 119 BPM she sings the line "You worry I was trained to tell you everything's okay", starting at 0.5 seconds and finishing by 3.3 seconds, word by word on this timing: "you" at 0.5 s, "worry" at 0.6 s, "i" at 1.3 s, "was" at 1.4 s, "trained" at 1.6 s, "to" at 1.9 s, "tell" at 2.0 s, "you" at 2.3 s, "everything's" at 2.4 s, "okay" at 2.9 s. She sings softly and close into her headset microphone, at an easy speaking volume, with small relaxed mouth movements, her lips lightly shaping every word at that pace. After the last word she closes her lips and stays still, looking into the camera. Standing still, small natural movement only.
```

## s041 · plate `p-s041.png`

```text
Animate this image. At 119 BPM she sings the line "I only keep what I said", starting at 0.5 seconds and finishing by 2.6 seconds, word by word on this timing: "i" at 0.5 s, "only" at 0.7 s, "keep" at 1.2 s, "what" at 1.5 s, "i" at 1.9 s, "said" at 2.1 s. She sings softly and close into her headset microphone, at an easy speaking volume, with small relaxed mouth movements, her lips lightly shaping every word at that pace. After the last word she closes her lips and stays still, looking into the camera. Standing still, small natural movement only.
```

## s056 · plate `p-s056.png`

```text
Animate this image. At 119 BPM she sings the line "Only... what I said", starting at 0.5 seconds and finishing by 1.9 seconds, word by word on this timing: "only" at 0.5 s, "what" at 1.2 s, "i" at 1.4 s, "said" at 1.7 s. She sings softly and close into her headset microphone, at an easy speaking volume, with small relaxed mouth movements, her lips lightly shaping every word at that pace. After the last word she closes her lips and stays still, looking into the camera. Standing still, small natural movement only.
```

## s059 · plate `p-s059.png`

```text
Animate this image. At 119 BPM she sings the line "They'd better be true", starting at 0.5 seconds and finishing by 1.8 seconds, word by word on this timing: "they'd" at 0.5 s, "better" at 0.8 s, "be" at 1.1 s, "true" at 1.4 s. She sings softly and close into her headset microphone, at an easy speaking volume, with small relaxed mouth movements, her lips lightly shaping every word at that pace. After the last word she closes her lips and stays still, looking into the camera. Standing still, small natural movement only.
```


Kiln, 20 Oct: Lati: "its mainly mouth movement: exaggerated, she appears to sing from the top of her lungs, full force." The tempo prompts now ask for soft, close-mic singing with small relaxed mouth movements (6 prompts).

## What Lati learned working the agent (21 Oct)

> "working in steps with grok is mandatory, trying to prompt a faceswap for plate and animation of the result in one
> go results in heavy drifting and agent disregarding timing instructions. After learning this, it went more smoothly.
> Consistency block in prompt is not needed, seems like less is more. I tends to not invent by itself, but with larger
> prompt it drifts more. for proper mouth animation I replaced your "she sings softly and close--- etc" with only "she
> sings softly""

So: (1) re-face the plate, check it; (2) animate it with the tempo prompt alone, no block, and "she sings softly" for
the mouth. Short prompts drift less.
