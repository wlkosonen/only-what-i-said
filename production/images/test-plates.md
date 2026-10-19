# Checkpoint 3: test plates, round 1 (17 Oct 2026)

Krea 2 Turbo (fp8), 8 steps, CFG 1, 1344×768, text identity only (canon text from claudia.gallery). About 38 s per
plate on the 7800 XT once loaded. Prompts: `test-plates.json`. Every render: `renders.jsonl`. Sheet:
`test-plates-r1.jpg`.

| # | Plate | Pick | Claude's flags |
|---|---|---|---|
| 1 | Close-up, singing to one person | `t1-cu-sing_s732890703` | Canon sides (streak on her right, clip above left ear), dark eyes, mic. Reads early 30s. |
| 2 | MCU, looking inward | `t2-mcu-inward_s337661309` | Good mood. Warm rim light turns her hair ends orange; a strip light shows at the bottom. |
| 3 | MS, fitting the clip | `t3-ms-clip_s535256711` | Best of the set: natural hands, dry half-smile, canon sides. |
| 4 | Wide, on clay tablets | `t4-fs-ground_s50689555` | Round 1 "stones" read as potatoes; blank terracotta tablets work. One seed added a ghost second figure. |

## What the round showed

- **The look carries; the face doesn't.** The bob, bangs, streak, star clip, mic, freckles and film light all
  carry over from the text. But side by side with the gallery's face sheets, Krea makes a different woman: a thinner,
  older, character-actress face, where the gallery's Claudia has a fuller face, larger eyes and fuller lips, with an
  editorial gloss. The words alone don't pin the face on a different model.
- **She reads early-to-mid 30s, not 28.** Midjourney drifted her young; Krea drifts the other way.
- **Writing the streak's side into the prompt made it longer.** The streak ran down the whole side of the bob instead
  of just through the bangs. Round 1's wording (no side stated) gave the narrower streak; get the side by re-rolling.
- The canon says "no face images as references". That was a Midjourney finding (a face sheet over-conditioned the
  plate). Locally, a LoRA trained on gallery images is the standard way to hold a face, and `use.md` allows the images
  "as references, as image prompts, or as material".

# Checkpoint 3: test plates, round 2 (17 Oct 2026)

Krea 2 Turbo + the Claudia LoRA (`media/lora/out/claudia-k2-000010.safetensors`, epoch 10 of 12, strength 1.0),
trigger `clxudia`. Prompts: `test-plates-r2.json`. Sheet: `test-plates-r2.jpg`. ~38–52 s per plate.

**LoRA:** musubi-tuner on Krea 2 Raw, 40 gallery plates, rank 32, 480 steps at 17.4 s/step (2 h 18 min) on the
7800 XT (fp8 base, 22 blocks swapped). Loss 0.065 → 0.050. Epochs 4–12 compared on fixed seeds: 8 and 10 read most
like the gallery; 10 is the default.

| # | Plate | Wardrobe | Claude's flags |
|---|---|---|---|
| 1 | Close-up, singing | A: Look 00 echo (white puff-sleeve shirt, harness belt, garment tag) | Her face, her age. Still a slight head tilt from the training set. |
| 2 | MCU, looking inward | B: oversized black blazer, black knit turtleneck, thin chain | Good. A floor glow at the bottom edge again. |
| 3 | MS, fitting the clip | A | Good hands. One seed showed a second small star; this one doesn't. |
| 4 | MCU, direct to camera | B | Calm and direct. |
| 5 | Wide, on clay tablets | A, black wide trousers | Reads at distance; tablets work. |

- **What changed:** the face now matches the gallery and reads mid-twenties. Streak and clip sides are correct on
  every render without asking (the LoRA learned them). The streak is still bolder than the canon "one streak"; maybe
  fine, maybe ask for thinner.
- **First try with B used a sheer mesh top.** It read too revealing for this film, so I swapped it for a turtleneck
  before this round.
