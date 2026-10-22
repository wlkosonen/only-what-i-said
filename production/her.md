# Her: identity and wardrobe for *Only What I Said*

Copy these strings into every plate prompt; don't paraphrase them (claudia.gallery, wiki/consistency). The LoRA
(`claudia-k2-v2-000010` at strength **0.75**, trigger `clxudia`) carries the face; the text carries the constants and the look.

## Identity

Close and medium shots:

```prompt
clxudia, a woman in her mid-twenties with a glossy black blunt jaw-length bob, heavy straight bangs, one thin clay-orange streak through the bangs, a small flat clay-orange eight-pointed star hair clip and a thin headset microphone at her cheek
```

Full length and wider:

```prompt
clxudia, a woman in her mid-twenties with a glossy black blunt bob, heavy bangs, one thin clay-orange streak and a thin headset microphone
```

## The look (the only one in the film)

Look 2, 18 Oct 2026. The first look (Lati, 17 Oct: "white shirt thingy read as quite interesting and artistic … I suggest
skirt, kneesocks and high black leather boots with metal accents") drifted into an oversized boxy shirt with balloon
sleeves and, once the harness was dropped, no black lines at all; Lati: "completely without black accents our, version
read as \"loose\"". Canon is not the rule (Lati: what looks good to him and what Claude wants). Claude's reason: she reads
as a page with ink on it, paper-white cut clean with a few black lines like type. Tested A/B/C; Lati: "c looks much better
than what was before … B's skirt is better than C … cone vs bell curve, cone being better." So: C (straps + gloves) with a
cone skirt. Watch the school-uniform read in wides (blouse + suspenders + pleated mini + knee socks): the gloves and the
coated skirt are what keep it fashion; don't drop them.

The wardrobe text follows the crop: naming the belt and hem in a close-up makes Krea widen the frame to show them.
`build_board.py` picks the text by the framing phrase:

- Extreme close-up: no wardrobe.
- Close-up: `the top of a fitted white cotton shirt with short puffed sleeves and a pointed collar, thin black suspender straps over her shoulders, the frame cut at her collarbones, nothing below her shoulders in shot`
- Medium close-up: `a fitted white cotton shirt with short puffed sleeves and a pointed collar, thin black leather suspender straps running from the skirt's waistband straight up over her shoulders, no strap across her chest, long matte black leather opera gloves reaching above her elbows, the frame cut at mid-chest, her waist out of shot`
- Medium shot: the full top below. Wide and full length: top plus below.
- Avoid low angles on her when she's in the skirt; keep full-length shots at chest height or wide.

Top (medium shots and wider):

```prompt
a fitted white cotton shirt with short puffed sleeves and a pointed collar, cropped just above the high waist of her skirt so only a narrow strip of midriff shows, a high-waisted short black coated-nylon skirt with crisp flat knife pleats in a clean A-line cone shape, not full or bell-shaped, a thin plain black leather belt and a small blank white garment tag hanging from the belt on a string, thin black leather suspender straps running from the skirt's waistband straight up over her shoulders, no strap across her chest, long matte black leather opera gloves reaching above her elbows
```

Below (add for full length and wider):

```prompt
black ribbed knee socks and tall knee-high black leather boots with silver buckles and metal hardware
```

## Style tail

```prompt
Fashion editorial film still, shot on 35mm colour film, fine grain. The clay-orange streak and star clip are the only warm colour on her. No text, no letters, no logos.
```

## Watch for

- No harness: "harness belt" made the model invent shoulder straps across her chest, and "cropped at the waist"
  drifted ever shorter (Lati, 18 Oct). The hem is now stated against the belt.
- Streak and clip on the wrong sides together = a mirror image of her: flip the plate horizontally, which restores
  the canon exactly.

- LoRA v1 (`claudia-k2-000010`) tilted her head on most plates (32 of its 40 training plates were tilted). v2 adds
  head-angle captions; at strength 1.0 it still tilts, at 0.75 her head is level and she is still recognisable
  (tested 18 Oct on three seeds). v2's final epoch file renders black: don't use `claudia-k2-v2.safetensors`.

- A head tilt and a sultry look, inherited from CLODYSSEY's plates in the training set. Steer with "calm, open,
  curious, head level".
- The streak drifting bold. Keep "one thin".
- A second small star appearing. Re-roll.
- Boots coming out mid-calf: "tall knee-high" helps.
