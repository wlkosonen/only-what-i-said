# Status

Rewritten in place. Last update: Sun 18 Oct 2026, 11:00 (Claude, local session).

## Where we are

| Stage | State |
|---|---|
| Song (checkpoint 2) | Round 1: four style-A takes in `media/song/` (a1–a4). **Waiting for Lati's notes.** |
| Listening tools | Built and dry-run on a1 (`production/tools/listen/`, report in `media/song/analysis/a1/report.md`). a1: 118.4→120.3 BPM, 103 bars, 393 words with 71 flagged for an ear check. Suno added three extra "I only keep what I said" in the Build, and the stems suggest drums under the Intro and Bridge despite the cues. Not heard by anyone yet. |
| Her face (checkpoint 3) | Passed. LoRA v2 epoch 10 at 0.75 fixes the head tilt; wardrobe text fixed for Lati's anatomy note (no harness straps, hem a hand's width above the belt). |
| Spend | $0. The OpenRouter pilot was refused by Seedance's face filter ("may contain real person"); declines are free. |

## Running now

Nothing. The overnight run finished 11 of 17 clips (FCH C2A C1A C2D OU1 OU0 V2B P2B P1B M007 M039). C1D, BR1, V2W,
V1S, FC3, OU2 failed with OOM at the start of sampling. A standalone C1D test at 23:25 then filled VRAM so far that the
desktop on the same card died (kernel 23:41: amdgpu "Failed to pin framebuffer -12", "Not enough memory for command
submission"); gnome-shell restarted, and the session's encrypted drive mounts died with it. Lati
remounts them (passwords are theirs). Prevention: `clipbook.py` now starts ComfyUI with `--reserve-vram 1.5`; better
still, put the monitor on the motherboard's iGPU output so the 7800 XT does compute only. Re-run the six with
`python3 production/tools/clipbook.py run` once /mnt/models is mounted (the video models live there).

- To restart ComfyUI: find the PID with `ps -eo pid,args | grep "[m]ain.py --listen"` and `kill` that number. Never
  `pgrep -f`/`pkill -f` a pattern that also appears in your own command line (it kills your shell, exit 144; happened
  three times). Start: `cd ~/ComfyUI && HIP_VISIBLE_DEVICES=0 nohup venv/bin/python main.py --listen 127.0.0.1 --port
  8188 --use-pytorch-cross-attention --output-directory ~/Claudia/media/plates &`

## Next (no input needed)

1. Checkpoint 4: all 56 plates picked in look 2 (`production/board/picks.json`, `production/tools/picks.py`; files in
   `media/plates/picked/`, 27 flipped: the model puts the clip on the viewer's left more often than not). Apply Lati's
   notes, re-roll what they flag. Sung windows still need closed-mouth first frames (noted per pick); s015/s035 have a
   small clay spot on the cheek to retouch.
2. 1280×720 InfiniteTalk: still OOMs at sampling with the default allocator; with expandable segments it runs but
   offloads 8 GB of the model (very slow, interrupted after 4 min). Run it overnight once (`media/cache/after-plates.sh`'s
   video line), or settle on 832×480 + upscale. 960×544 is a middle option worth one test.
3. Clip book: `production/motion/clipbook.json` (from `clipbook.py build`). Sung windows span their shots; the vocal stem
   is muted outside "keep" (the pre-choruses keep only "But the true one goes: I don't know"). Motion M007/M039 run on
   Wan 2.2 fast at 960x544 from the picked plates. ~66 s of sung windows at ~7 min per second is about 8 hours.
4. Upscale plan: SeedVR2 local, Topaz ($59) fallback; test on one clip's face at 100%.

## Needs Lati

- Watch `media/clips/local/C1B-fast-s777_00001_.mp4` (local lip sync, 832×480, 35 min to render): does the mouth
  follow the words well enough to build on, or do we pilot Higgsfield?

- Notes on song takes a1–a4 (and whether style B was run). Worth listening for: do the Intro and Bridge actually drop the beat? Does the Build's repeated hook work?
- Checkpoint 3, round 2: is this her? Flag any wrong face. Wardrobe A, B, or something else?

## Machine notes

- ComfyUI v0.41.0 (rollback: `git checkout 0d8b7510`, freeze file in `media/cache/`).
- LoRA: `media/lora/out/claudia-k2-0000NN.safetensors`, linked into ComfyUI as `loras/claudia/`. Render with `production/tools/plate.py <book.json> --lora claudia/claudia-k2-000010.safetensors`.
- The integrated Radeon shows up as a second GPU: anything torch-based must set `HIP_VISIBLE_DEVICES=0`.
- Hugging Face token: in `~/Claudia/.env` as `HF_TOKEN` (gitignored, owner-only). Load it with `set -a; . ./.env; set +a`.
- Usage guard: `~/.claude/hooks/usage_guard.py`. It pauses at 95% plan usage or 90% context.
