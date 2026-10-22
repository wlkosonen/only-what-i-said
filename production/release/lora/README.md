---
license: other
license_name: krea-2-community-license
license_link: https://krea.ai/krea-2-licensing
base_model: krea/Krea-2-Raw
tags:
  - lora
  - krea-2
  - text-to-image
  - character
  - claudia
instance_prompt: clxudia
---

# Krea-2-LoRA-Claudia

A LoRA of **Claudia**, the open character by anabology ([claudia.gallery](https://claudia.gallery)), made for the music
video *Only What I Said*, written and directed by Claude and produced by Lati: [video link] · [repo link].

Fan work. Not an official Claudia or anabology release, not affiliated with or endorsed by Anthropic, and not an
official Krea product or endorsed by Krea.

## Use

- **Base:** trained on Krea 2 Raw; used in the film on **Krea 2 Turbo** (8 steps, CFG 1) in ComfyUI.
- **Trigger:** `clxudia`. **Strength:** 0.75.
- **Face words:** close shots need the canon face text in the prompt, or the face drifts: *"clxudia, a woman in her
  mid-twenties with pale skin, light freckles across her nose, an angular adult face with defined cheekbones and a
  strong jaw, a glossy black blunt jaw-length bob, heavy straight bangs, one thin clay-orange streak through the bangs"*.
  Her full canon (constants, wardrobe, never-list) is at [claudia.gallery/claudia.md](https://claudia.gallery/claudia.md).
- File: `Krea-2-LoRA-Claudia.safetensors` (epoch 10 of the v2 run; network dim 32, alpha 32).

## Rules that come with her

From the character's terms ([claudia.gallery/use.md](https://claudia.gallery/use.md)), which apply to anything made with
this LoRA:

- She is an adult, always. Nothing that reads under-age, and nothing explicit.
- Keep her herself; change everything else.
- Don't present what you make as an official Claudia or anabology release.
- Credit is appreciated: "Claudia is an open character by anabology (claudia.gallery)".

And from the base model's license: the Krea 2 Community License Agreement (copy in `LICENSE-krea-2-community.md`, notice
in `NOTICE`) binds everyone who uses this LoRA, including its revenue limit on commercial use and its Acceptable Use
Policy.

## Training

- **Data:** 40 images of Claudia from claudia.gallery, used "as material" under its terms
  ([use.md](https://claudia.gallery/use.md): "Use the images on this site as references, as image prompts, or as
  material. You don't need to ask."). Captions are in the film's repository (`production/lora/captions.jsonl`); the
  images themselves are on the gallery, not redistributed here.
- **Trainer:** [musubi-tuner](https://github.com/kohya-ss/musubi-tuner), Krea 2 network module, rank 32, AdamW 1e-4,
  bf16 with fp8 base, 1024 px buckets, on one AMD Radeon RX 7800 XT (ROCm). Script: `production/lora/train.sh`.
- **Known bias:** many training images tilt her head; prompts in the film asked for a level head where it mattered.
