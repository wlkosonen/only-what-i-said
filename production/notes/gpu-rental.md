# Renting GPU time (research, 19 Oct 2026)

Cloud session, for Lati ("prioritized with cost and easy setup", plus about $27 in USDC). Prices are snapshots from
the pages linked in the chat that day; check before use. Every paid batch still needs an estimate and Lati's explicit
yes (CLAUDE.md).

| # | Service | What it is | Price | Setup | Pays with |
|---|---|---|---|---|---|
| 1 | **Comfy Cloud** (comfy.org) | ComfyUI hosted by its makers; RTX 6000 Pro Blackwell, 96 GB | Creator $35/mo (own LoRAs from Hugging Face/CivitAI; Standard $20 can't); "a 5-second video uses about 11 credits"; runs capped at 30 min (Pro: 1 h) | Easiest: nothing to install. Our LoRA would need to be on Hugging Face | Card (Stripe) |
| 2 | **RunPod** | Rent a GPU pod; first-party ComfyUI template | RTX 4090 from ~$0.34/h, RTX 5090 ~$0.69/h, H100 ~$1.99/h; per-second billing | Medium: start the template, download models on the pod | Card or **crypto** via processors, KYC first; credits non-refundable |
| 3 | **Vast.ai** | Marketplace of hosts' GPUs | RTX 5090 roughly $0.40–0.87/h | Medium-hard: hosts vary, no uptime guarantee | Card, **BitPay or Crypto.com** |
| 4 | **RunComfy** | Hosted ComfyUI, custom models and nodes allowed | 24 GB $1.75/h, 48 GB $2.50/h, H100 $7.49/h (Pro $19.99/mo lowers rates) | Easy | Not stated |
| 5 | **Clore.ai** | Crypto-native marketplace | RTX 4090 median ~$0.375/h | Hard-ish, least polished | BTC, USDT, **USDC** |

Fit for this film: 720p InfiniteTalk/Wan 2.2 runs out of memory on the 16 GB 7800 XT. Any 32 GB+ card avoids that;
96 GB (Comfy Cloud) certainly does. Our video workflow uses ComfyUI's built-in nodes, which should help on hosted
ComfyUI; test one clip first.
