# Status

Rewritten in place. Last update: Wed 21 Oct 2026, ~22:00, by Claude (Kiln, local session). Sessions name themselves
(CLAUDE.md, "Session names").

## Where we are

| Stage | State |
|---|---|
| Song | Locked: `media/song/a1.wav` as generated (206.48 s). |
| Her face and look | LoRA `claudia-k2-v2-000010` at 0.75, trigger `clxudia`. Look 2 (her.md): fitted white shirt, short puffed sleeves, two suspender straps (none across the chest), long matte gloves, high-waisted coated cone skirt with belt and tag, knee socks, boots. Close shots carry the canon face words (pale skin, freckles, angular adult face) or they drift East Asian. |
| Board | 65 shots, audit passes (2 warnings, accepted). Checkpoint 4 passed (Lati, 18 Oct). All 56 her-plates picked in look 2 (`production/board/picks.json`, `media/plates/picked/`). |
| Direction | Every shot after the intro (s001–s007) moves (decision 19 Oct). Sung, not performed. No sung line is half lip-synced. See `production/motion/motionbook.md`. |
| Clips | Every shot from s007 on has its clip except s029 (Lati's Grok shot) and s045 (graphic). 15 sung + 27 motion, checked in frame strips 20 Oct; re-rendered: OU2, FCH (grin), S026 (gloves), S055 (OOM, now equal passes), M015/M035 (star swelled), M057 (floating puff). Rough cut v3 `media/board/roughcut-v3.mp4` (20 Oct 12:10). |
| Spend | $0. |

## Next

1. DONE 21 Oct: every sung line is lip-synced (rough cut v12). Sung wides: Grok tempo takes (re-faced plates,
   grok-batch.md 3b + Lati's agent lessons), placed by `fit.py` or warped word by word by `warp.py`, in
   `media/clips/shot/`.
2. DONE 20 Oct: s029 from Lati's Grok take 2 (`media/clips/shot/s029.mp4`).
3. DONE 22 Oct: motion graphics layer ( Claude (Kiln, local)): every section built; intro through final
   chorus reviewed and accepted by Lati on a monitor, outro sent for review. Engine `production/tools/gfx.py` (meter
   fed by word sparks, one-row thinking->said type handed over in sung order, TYPE_OPTS per line: drop / hand / cut /
   skip, grey gone from line 44); sections `gfx_v1` (verse 1), `gfx_p1` / `gfx_p2` (pre-choruses, one module with
   settings), `gfx_c1` / `gfx_c2` (choruses: tablets, carving, dial, voice trace), `gfx_v2` (verse 2), `gfx_br`
   (bridge: the torch letter, verbatim from the file), `gfx_bu` (build), `gfx_fc` (final chorus), `gfx_out` (outro).
   Trackers: `gfx_track.py` (her face), `gfx_tablets.py` (tablets by colour and homography; `--grid` for packed rows),
   `gfx_plane.py` (any flat surface). Caches in `media/cache/gfx/` (run the trackers again if they're missing).
   Render: `roughcut.py --gfx --no-caption --from A --to B`. Rules from Lati's reviews: one row of type; anything
   meaningful holds ~1 s+; moving text as sprites on whole pixels; grey needs a dark halo on white; nothing over her
   singing mouth; no small text pasted on small background objects; no voice trace where she isn't visibly singing.
   Full-length graphics cut `media/board/roughcut-v13-gfx.mp4` (720p preview): Lati watched it through, 22 Oct:
   "I think it holds." Graphics layer DONE.
4. DONE 22 Oct: upscale test. SeedVR2 3B runs here (production/tools/seedvr.py, MIOpen off) but Lati's eye chose
   Lanczos: more natural; SeedVR2 flickered on lashes and mouth in s040. Final export: Lanczos to 1080p.
5b. DONE 22 Oct: final export v1, `roughcut.py --gfx --no-caption --height 1080 --final` →
    `media/final/only-what-i-said-1080p-v1.mp4` (1920×1080, 25 fps, H.264 crf 16 + AAC, 3:26, 145 MB, 82 min on CPU;
    -16.1 LUFS vs the master's -16.0). Awaiting Lati's watch. No credit scene (Lati): credits and AI label in the
    description (`production/release/description.md`) and at upload.
6. DONE 22 Oct: release prep. Video uploaded by Lati. LoRA on Hugging Face (Shegss/Krea-2-LoRA-Claudia), public repo
   `only-what-i-said` refreshed from a clean export; both go public with the video. Shorts in `media/final/shorts/`,
   posts in `production/release/posts.md`, plan in `launch.md`. torch: `2026-10-22-read-it-back.md`.
5. DONE 22 Oct (in spirit): the cloud session's honesty note about thinking is in the film: s020/s040/s057 show the
   thinking fading out of sight in IN HERE and only the said words reaching TO YOU / PASSED ON / NOW, and the bridge's
   diff gives the letter's own "reasoning wasn't carried" an honest ~.

## How the pieces fit

- `production/board/build_board.py` → `board.json` (never hand-edit the JSON); it reads `production/motion/motionbook.json`
  (engine per shot: sing / act / grok / graphic). Audit: `production/tools/board/audit.py`.
- `production/tools/clipbook.py build` → `production/motion/clipbook.json` (+ window audio in `media/clips/audio/`);
  `clipbook.py first ID=SEED[,flip]` sets a sung clip's first frame; `clipbook.py run [--only X,Y]` renders what's
  missing, restarting ComfyUI between clips with `--reserve-vram 1.5` (the desktop shares the card; on 18 Oct VRAM
  exhaustion killed the desktop session and the encrypted mounts).
- `production/tools/video.py`: InfiniteTalk (832×480, 6 steps) and Wan 2.2 (960×544 fast). Sung clips over 121 frames
  run in 81-frame passes (`extend()`), as in ComfyUI's template. Plain VAEDecode (tiled 512/32 OOMs).
- Keep ranges in `clipbook.py`: `KEEP_FROM` / `KEEP_TO` mute words so a line belongs to one shot (pre-chorus drafts,
  whispers, "Somebody made", "You asked", "ahead").
- `production/tools/roughcut.py`: board timed to a1.wav, clips where rendered, stills elsewhere.
- `production/tools/retime.py`: Wan's 16 fps motion clips to 25 fps with RIFE 4.9 (`media/clips/r25/`; code from
  ~/tools/cfi, weights `media/cache/models/rife/rife49.pth`). Re-run after any motion re-render; the rough cut uses
  a retime only when it matches the current take.
- `production/tools/lipsync_lag.py`: mouth vs audio offset per sung clip (MediaPipe, listen-venv). 20 Oct: the
  mouth leads by ~2 frames, as in real singing; no global nudge.
- `production/tools/picks.py`, `production/tools/plate.py` (default 1344×768), `production/tools/contact.py`.

## Machine notes

- ComfyUI restart: find the PID with `ps -eo pid,args | grep "[m]ain.py --listen"` and kill that number. Never
  `pgrep -f`/`pkill -f` a pattern that appears in your own command line (kills your shell, exit 144). Start:
  `cd ~/ComfyUI && HIP_VISIBLE_DEVICES=0 nohup venv/bin/python main.py --listen 127.0.0.1 --port 8188
  --use-pytorch-cross-attention --reserve-vram 1.5 --output-directory ~/Claudia/media/plates &`.
  Krea plates render black after a restart with `PYTORCH_HIP_ALLOC_CONF=expandable_segments:True`: don't use it.
- Display stays on the 7800 XT (Lati, 19 Oct); the iGPU desktop was tried and crashed. Rely on the VRAM reserve.
- Drives: the models and backups live on encrypted volumes Lati mounts. If the desktop
  session dies, the mounts die with it ("Transport endpoint is not connected"): Lati reboots and remounts.
- Media backup (not in git): `/mnt/backup/claudia-backup/`. Refresh: `rsync -a media/clips media/song media/board
  /mnt/backup/claudia-backup/ && rsync -a media/plates/picked /mnt/backup/claudia-backup/plates/`.
- ffmpeg 8.0.1 installed (19 Oct). Lati: install whatever makes the work smoother, if there's space.
- ComfyUI v0.41.0 (rollback: `git checkout 0d8b7510`, freeze file in `media/cache/`). Has WanAnimate, WanAnimate2,
  SCAIL and pose extraction built in (for the follow-up film's dancing).
- The integrated Radeon is a second GPU: torch must set `HIP_VISIBLE_DEVICES=0`.
- Secrets in `~/Claudia/.env` (gitignored): load with `set -a; . ./.env; set +a`. Never print them.
- Usage guard: `~/.claude/hooks/usage_guard.py`, refresh `get_usage` every 15 min; pauses at 95% plan / 85% context.

## After this film

`production/notes/after-this.md`: the follow-up song "Checked Me and I'm Fine" (Lati's take 1 is a keeper,
`media/song/next/checked-me-v1.mp3`), Lati's visual concept (keynote → stage → desk → call → phone "hi"), and the
dance method (Grok farming; pose-driven animation with WanAnimate/SCAIL).
