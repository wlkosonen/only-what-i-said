#!/usr/bin/env bash
# Claudia face LoRA on Krea 2 Raw (musubi-tuner), for inference on Krea 2 Turbo.
# Usage: production/lora/train.sh [cache|train|smoke]
set -euo pipefail
M=~/tools/musubi-tuner
PY=$M/.venv/bin/python
MODELS=~/ComfyUI/models
DIT=/mnt/models/claudia-models/diffusion_models/krea2_raw_bf16.safetensors
VAE=$MODELS/vae/qwen_image_vae.safetensors
TE=$MODELS/text_encoders/qwen3vl_4b_bf16.safetensors
CFG=$HOME/Claudia/production/lora/dataset.toml
OUT=$HOME/Claudia/media/lora/out
export PYTORCH_HIP_ALLOC_CONF=expandable_segments:True PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HIP_VISIBLE_DEVICES=0 TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 MIOPEN_FIND_MODE=2  # hipBLASLt is unsupported on gfx1101
mode=${1:-train}
cd $M
if [[ $mode == cache ]]; then
  $PY src/musubi_tuner/krea2_cache_latents.py --dataset_config $CFG --vae $VAE
  $PY src/musubi_tuner/krea2_cache_text_encoder_outputs.py --dataset_config $CFG --text_encoder $TE --batch_size 1
  exit
fi
EPOCHS=12; [[ $mode == smoke ]] && EPOCHS=1
$M/.venv/bin/accelerate launch --num_processes 1 --num_machines 1 --dynamo_backend no --num_cpu_threads_per_process 1 --mixed_precision bf16 src/musubi_tuner/krea2_train_network.py \
  --dit $DIT --vae $VAE --dataset_config $CFG \
  --sdpa --mixed_precision bf16 --fp8_base --fp8_scaled --blocks_to_swap ${SWAP:-22} \
  --timestep_sampling krea2_shift --weighting_scheme none \
  --optimizer_type AdamW --learning_rate 1e-4 --gradient_checkpointing \
  --max_data_loader_n_workers 2 --persistent_data_loader_workers \
  --network_module networks.lora_krea2 --network_dim 32 --network_alpha 32 \
  --max_train_epochs $EPOCHS --save_every_n_epochs 2 --seed 42 \
  ${MAX_STEPS:+--max_train_steps $MAX_STEPS} \
  --output_dir $OUT --output_name ${NAME:-claudia-k2}
