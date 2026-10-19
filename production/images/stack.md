# Image stack

Claude, 17 October 2026. Researched by a subagent, then key facts checked against the Hugging Face API, GitHub and
the license pages the same day. Models change fast: re-check before relying on this months from now.

## The machine (checked 17 Oct 2026)

- Ubuntu, RX 7800 XT (gfx1101, 16 GB), about 60 GB RAM, 118 GB free on `/`.
- ROCm 7.2.4. ComfyUI's venv: PyTorch `2.14.0.dev20260620+rocm7.2`, torchvision `0.29.0.dev20260621+rocm7.2`,
  torchaudio `2.11.0.dev20260621+rocm7.2`, GPU visible. Python 3.14.
- ComfyUI at `v0.25.0-31-g0d8b7510` (20 Jun 2026), clean tree. The latest release is v0.41.0 (15 Oct 2026).
- Installed models: DreamShaper 8 (SD 1.5, obsolete for this), NewBie-Image-Exp0.1 + Gemma 3 4B (anime, and
  non-commercial, so unusable here).

## Decision: one step at a time

**Phase 1, test plates: Krea 2 Turbo.** A 12.9B model, 8 steps at CFG 1, native in ComfyUI, ungated, and the only
candidate with a report from someone running it on this exact card (ComfyUI issue #16502: a 7800 XT running the
fp8_scaled file). Following the gallery method, the four test plates use text identity only, so checkpoint 3 ("is this
her?") tests the words before we add any tools.

| File (repo `Comfy-Org/Krea-2`) | Size | Goes in |
|---|---|---|
| `diffusion_models/krea2_turbo_fp8_scaled.safetensors` | 13.14 GB | `models/diffusion_models/` |
| `text_encoders/qwen3vl_4b_bf16.safetensors` | 8.88 GB | `models/text_encoders/` |
| `vae/qwen_image_vae.safetensors` | 0.25 GB | `models/vae/` |

Total: 22.3 GB. The fp8 file is only how the weights are stored; RDNA3 computes in bf16.

**Phase 2, keeping her the same face: decided after checkpoint 3.** Candidates:

1. **FLUX 3 Image Klein** (released 14 Oct 2026): one 11.1 GB model that does text-to-image, editing and up to 10
   reference images. On paper it's the best fit for "same face in every shot". Against it: it's three days old, there
   are no ROCm reports yet, BFL measured 31 GB peak VRAM in its own reference code (ComfyUI offloads, but untested
   here), and the repo is gated, so Lati needs a Hugging Face account, has to accept the terms, and needs a token kept
   in `.env`.
2. **Qwen-Image-Edit-2511** (Apache-2.0): proven, but the bf16 file is about 40 GB, so it needs a GGUF quantization and
   the ComfyUI-GGUF custom node, and GGUF reportedly underuses this card.
3. **A LoRA** trained with musubi-tuner on Krea 2 Raw (block swap, `--sdpa`), using an identity set made in step 1
   or 2. Hours of training; ROCm recipes exist but none tested on RDNA3.

**Fallback if Krea 2 misbehaves on this card:** Z-Image Turbo (Apache-2.0, `Comfy-Org/z_image_turbo`, 12.3 + 8.0 +
0.3 GB).

## Licenses (for a released video)

- **Krea 2 Community License:** you own the outputs. Commercial use only while total annual revenue (including
  affiliates) is under US$1M. No attribution required on outputs.
- **FLUX Kommunity v1.0:** commercial use of outputs allowed under US$5M revenue. Fine-tuning and distribution are not
  covered by that exception.
- **Avoid:** Qwen-Image 2.1 (research licence, non-commercial) and NewBie-Image (NC).

## Updating ComfyUI safely

Krea 2 support arrived after this checkout. The plan:

1. Write `pip freeze` to `media/cache/comfyui-freeze-before.txt` and note the commit (`0d8b7510`).
2. `git fetch --tags && git checkout v0.41.0`.
3. `pip install -r requirements.txt -c constraints.txt`, where the constraints file pins torch, torchvision and
   torchaudio to the versions above, so pip can't replace the working ROCm build.
4. Start it once with `--use-pytorch-cross-attention` and read the log.

To undo: `git checkout 0d8b7510`, then reinstall from the freeze file.

## ROCm notes to try if it's slow or broken

- Later images get slower than the first on gfx1101 (#16502, still open): call `POST /free` between batches, or
  restart ComfyUI.
- `COMFYUI_ENABLE_MIOPEN=1` may be faster. Test with and without. `MIOPEN_FIND_MODE=2` shortens first-run tuning.
- Use VAE Decode (Tiled) at 2K; add `--fp32-vae` if images come out black. Don't use `--fast`.
