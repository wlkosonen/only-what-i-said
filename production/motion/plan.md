# Motion plan

Claude, 18 Oct 2026, after a research pass (sources checked that day; full notes in the session) and the gallery's
`wiki/seedance`. Nothing is spent until Lati gives an explicit yes to a specific estimate.

## Update, 18 Oct: local

Seedance via OpenRouter refused her ("may contain real person", even the wide shot; declines are free). The local
InfiniteTalk test (832×480, 6 steps, 35 min for 5 s) passed Lati's eye: "I cant see any errors that would read as
mis-synced or weird." So the 15 sung windows and 2 motion clips render locally for $0; Higgsfield is the fallback for
a window that fails three times. 1280×720 ran out of VRAM at decode; next try decodes in tiles.

## Decision (proposed, superseded above)

- **Seedance 2.5 for all 32 clips** (27 sung, 5 motion), at **720p**. Sung clips in reference mode with the clean
  vocal as the audio reference (on OpenRouter a first-frame image silently drops the audio); motion clips from the
  plate as first frame.
- **No local lip sync.** The open options (InfiniteTalk/MultiTalk, Wan2.2-S2V, LTX audio-to-video) aren't reliable for
  close-up singing, and the gallery already rejected re-lipping ("forced and glitchy").
- **Local video for the 5 motion clips is not worth it:** it would save $3–6 against hours of GPU time and a visible
  quality step down. Kept as an optional free side test (Wan 2.2 I2V or LTX-2.5) only.
- **Upscale 720p → 1080p locally with SeedVR2 3B** at low strength, overnight. Fallback: one month of Topaz Video ($59)
  on the Windows boot (it supports AMD there; the Linux beta is NVIDIA-only). Not 480p → 1080p: close-ups risk waxy skin
  and shot-to-shot identity drift, and there is no cheap way to re-render a 480p draft at 720p with the same motion.

## Cost (CLAUDE.md rule: seconds × price × 2)

| | Seconds | List at $0.23/s | Estimate ×2 |
|---|---|---|---|
| Sung, with 60% covers | 220.8 | $50.78 | $101.57 |
| Motion | 25 | $5.75 | $11.50 |
| **All clips** | 245.8 | **$56.53** | **$113.07** |

OpenRouter's page lists "from $0.1028/s" (480p); the 720p rate of $0.23/s is the gallery's measured rate and matches
Replicate. The pilot reads the real cost from `usage.cost`.

## The big risk

In CLODYSSEY, OpenRouter's face filter declined most photoreal close-ups. Higgsfield accepted them at about $1.14/s
(1080p): this board would be about $280 list, $560 by the ×2 rule, over the $350 cap. The pilot tests this first.

## Pilot (needs Lati's yes)

1. One sung window, ~6 s, 720p, reference mode (a chorus close-up).
2. One motion clip, 5 s, 720p, first frame (the chorus 1 tablet slam, s019).

11 s × $0.23 = $2.53 list, **$5.06 by the ×2 rule.** It answers: does the face filter accept her; is the sync good
(measured with the gallery's cross-correlation check); does reference mode keep her identity; what does 720p really
cost; and (locally, free) SeedVR2 vs Topaz on the sung clip's face at 100%.

## What Lati sets up first

An OpenRouter account and API key with its **own spend limit** set just above what's approved (e.g. $10 for the
pilot), the key pasted into `~/Claudia/.env` as `OPENROUTER_API_KEY=...` by Lati, never in chat.
