#!/usr/bin/env python3
"""The clip book for local video: 15 sung windows (InfiniteTalk) and 2 motion clips (Wan 2.2), and an overnight runner.

    python3 production/tools/clipbook.py build                  # board.json -> production/motion/clipbook.json + audio
    python3 production/tools/clipbook.py first V1S=SEED[,flip]  # pick a sung clip's first frame from its ff- renders
    python3 production/tools/clipbook.py run [--only V1S,P1B]   # render what's missing, shortest first

Sung windows span their shots (0.05 s before the first cut to 0.10 s after the last), so the lips follow every word
heard on screen. The audio is the vocal stem with everything outside "keep" muted: the whole window, except the two
pre-choruses, where the "something sweet" draft stays muted and she only says "But the true one goes: I don't know"
(the film's thought-vs-said device). Motion clips start from the shot's picked plate.

The runner restarts ComfyUI between clips: on this card a long session ends in a ROCm illegal-memory-access crash.
Each finished clip is logged by video.py to production/motion/local-runs.jsonl; a clip counts as done when its MP4 is
in media/clips/local/ under its book id.
"""

import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / "production/motion/clipbook.json"
AUDIO = ROOT / "media/clips/audio"
FIRST = ROOT / "media/clips/first"
LISTEN_PY = ROOT / "media/cache/listen-venv/bin/python"
COMFY = Path.home() / "ComfyUI"
COMFY_ARGS = ["--listen", "127.0.0.1", "--port", "8188", "--use-pytorch-cross-attention", "--reserve-vram", "1.5",
              "--output-directory", str(ROOT / "media/plates")]
# keep starts at this word: the pre-choruses mute the "something sweet" draft; the outro whispers keep only their own
# words, so a louder tail of the previous line can't set the level and drown the whisper (OU0's failed sync, 19 Oct)
KEEP_FROM = {"P1B": "but", "P2B": "but", "OU0": "the", "OU1": "save", "OU2": "i", "FCH": "i"}  # FCH: "ahead" ends s057's thought line
# keep ends before this word: a line that continues on a closed-mouth shot is muted here, so no line is half lip-synced
# (Lati, 19 Oct): "Somebody made" belongs to s011 (being made), "You asked" to s014 (the remembered question)
KEEP_TO = {"S010": "somebody", "V1S": "you"}
# She sings in every window: sung, not performed (Lati, 19 Oct: V2B read as "awkward explanation" when told "speaks")
LEAD = 0.3  # s of unseen lead-in before every sung window: the mouth needs a few frames to catch the audio
TAIL = 0.3  # and unseen tail after it: near the end of its audio the mouth closes early (P1B's held 'know', 20 Oct)
MANNER = {"V1S": "softly and close", "V2W": "softly and close", "V2B": "softly and close", "BR1": "softly and close",
          "P1B": "softly, unsure", "P2B": "softly, unsure", "OU0": "quietly, almost a whisper",
          "OU1": "quietly, almost a whisper", "OU2": "quietly, almost a whisper",
          "FCH": "firmly and plainly, resolute, stating a fact, her head held still and level",
          "C1D": "firmly and plainly, her head held still and level, only her lips and eyes moving",
          "FC3": "firmly and plainly, her mouth opening fully on the long held notes, lips rounding and holding the "
                 "shape of each vowel"}  # default: firmly and plainly (choruses)
LOOK = ("A woman in her late twenties with pale skin, light freckles across her nose and an angular adult face with "
        "defined cheekbones and a strong jaw, a glossy black blunt bob, heavy bangs and one thin clay-orange streak, a small "
        "star hair clip and a thin headset microphone, wearing a fitted white shirt with short puffed sleeves and thin "
        "black suspender straps")
LOOK_FULL = (LOOK + ", long matte black gloves above the elbow, a short black pleated skirt, black knee socks and tall "
             "black boots")
MOTION = {
    "M007": ("{look}, long black gloves, a short black pleated skirt and tall black boots. Her eyes are closed, then she "
             "opens them and looks straight into the lens, calm and curious, head upright and level. The camera slowly "
             "pulls back. Black void, soft light from below. Cinematic 35mm film, fine grain."),
    "M039": ("{look}, long black gloves, a short black pleated skirt, black knee socks and tall black boots. She steps up "
             "onto the top terracotta tablet of a low flight of steps, one deliberate step, then stands still and level, "
             "calm. Locked camera. Black void, top light. Cinematic 35mm film, fine grain."),
}


def board():
    return json.loads((ROOT / "production/board/board.json").read_text())


def words():
    return [w for w in json.loads((ROOT / "media/song/analysis/a1/words.json").read_text())["words"] if w["t1"]]


def setting_of(prompt):
    """The light and set sentences of a board prompt, after her action sentence."""
    cut = max(prompt.find(" in shot. "), prompt.find(" out of shot. "))
    body = prompt[cut:].split(". ", 1)[1].split("Fashion editorial")[0]
    sentences = [s.strip() for s in body.split(". ") if s.strip()]
    return ". ".join(sentences[1:]).rstrip(".")


def build():
    b = board()
    S = {s["id"]: s for s in b["shots"]}
    picks = json.loads((ROOT / "production/board/picks.json").read_text())
    old = {c["id"]: c for c in json.loads(BOOK.read_text())} if BOOK.exists() else {}
    mbook = json.loads((ROOT / "production/motion/motionbook.json").read_text())
    W = words()
    # Whisper clocks a sung "I" at 0.02 s, late: the singer is already on it when the previous word ends, and holds it
    # to the next word (S021, S041, FCH's "I only", 20 Oct). Short words span from the previous word's end (at most
    # 0.3 s early) to the next word's start; longer words keep whisper's times.
    START = {id(w): (max(W[i - 1]["t1"] if i else 0, w["t0"] - 0.3) if w["t1"] - w["t0"] < 0.1 else w["t0"])
             for i, w in enumerate(W)}
    SPANS = [(START[id(w)], W[i + 1]["t0"] if w["t1"] - w["t0"] < 0.1 and i + 1 < len(W) else w["t1"])
             for i, w in enumerate(W)]
    book = []
    AUDIO.mkdir(parents=True, exist_ok=True)
    for c in b["clips"]:
        if done(c["id"]) and c["id"] in old:  # a rendered clip's entry is frozen (the rough cut times it by its t0);
            book.append(old[c["id"]])         # move its file out of media/clips/local/ to rebuild it
            continue
        shots = [S[i] for i in c["shots"]]
        s0 = float(shots[0]["t0"])
        held = [a for a, z in SPANS if a < s0 < z - 0.03 and s0 - a < 1.5]  # a word sounding at the cut is this clip's
        t0 = round(min([float(c["t0"]), s0 - 0.05] + [a - 0.05 for a in held]) - LEAD, 3)
        s1 = float(shots[-1]["t1"])
        t1 = round(max([s1 + 0.10] + [z + 0.05 for a, z in SPANS if a < s1 < z]) + TAIL, 3)
        e = {"id": c["id"], "kind": c["kind"], "shots": c["shots"], "t0": t0, "t1": t1, "seconds": round(t1 - t0, 3)}
        if c["kind"] == "sung":
            keep = [t0, t1]
            if c["id"] in KEEP_FROM:
                w = next(w for w in W if w["w"] == KEEP_FROM[c["id"]] and t0 <= w["t0"] <= t1)
                keep = [round(START[id(w)] - 0.02, 3), t1]
            if c["id"] in KEEP_TO:
                w = next(w for w in W if w["w"] == KEEP_TO[c["id"]] and keep[0] <= w["t0"] <= t1)
                keep[1] = round(w["t0"] - 0.04, 3)
            e["keep"] = keep
            e["words"] = " ".join(w["w"] for w in W if w["t0"] >= keep[0] and w["t1"] <= keep[1] + 0.3)
            p = shots[0]["prompt"]
            mb = mbook.get(shots[0]["id"], {})
            manner = mb.get("manner") or MANNER.get(c["id"], "firmly and plainly")
            look = LOOK_FULL if mb.get("full") else LOOK
            setting = mb.get("setting") or setting_of(p)
            e["prompt"] = (f"{look}, sings {manner} straight into the camera, meaning every word, breathing with the "
                           f"phrase, a quiet feeling in her eyes, a serious composed face, lips relaxed between words, her head mostly "
                           f"steady, no dramatic gestures, "
                           f"singing to one person. {setting}. Cinematic 35mm film, fine grain"
                           f"{'' if mb.get('full') else ', intimate close shot'}.")
            e["audio"] = str((AUDIO / f"{c['id']}.wav").relative_to(ROOT))
            subprocess.run([str(LISTEN_PY), str(ROOT / "production/tools/clipaudio.py"), "vocal", str(ROOT / e["audio"]),
                            str(t0), str(t1), "--keep", str(keep[0]), str(keep[1])], check=True, stdout=subprocess.DEVNULL)
            for k in ("image", "first_src", "first_flip"):  # set by `first`
                if k in old.get(c["id"], {}):
                    e[k] = old[c["id"]][k]
            e.setdefault("image", (picks.get(shots[0]["plate"]) or {}).get("file"))  # new sung shots: the board pick
        else:
            mb = mbook.get(shots[0]["id"])
            text = mb["prompt"] if mb else MOTION[c["id"]]
            e["prompt"] = text.format(look=LOOK, full=LOOK_FULL) + ("" if mb is None or text.rstrip().endswith("grain.")
                                                                     else " Cinematic 35mm film, fine grain.")
            e["image"] = (picks.get(shots[0]["plate"]) or {}).get("file")  # inserts need their plate rendered first
        book.append(e)
    BOOK.write_text(json.dumps(book, indent=1) + "\n")
    secs = sum(e["seconds"] for e in book if e["kind"] == "sung")
    print(f"{len(book)} clips, {secs:.1f} s of sung windows -> {BOOK.relative_to(ROOT)}")


def first(sets):
    from PIL import Image, ImageOps  # ComfyUI venv
    book = json.loads(BOOK.read_text())
    FIRST.mkdir(parents=True, exist_ok=True)
    for s in sets:
        cid, rest = s.split("=", 1)
        seed, *flag = rest.split(",")
        src = sorted(glob.glob(str(ROOT / f"media/plates/ff-{cid}_*_s{seed}_*.png")))
        if not src:
            raise SystemExit(f"no ff-{cid} render with seed {seed}")
        im = Image.open(src[-1])
        dst = FIRST / f"{cid}.png"
        (ImageOps.mirror(im) if flag == ["flip"] else im).save(dst)
        for e in book:
            if e["id"] == cid:
                e["image"], e["first_src"], e["first_flip"] = (str(dst.relative_to(ROOT)),
                                                               str(Path(src[-1]).relative_to(ROOT)), flag == ["flip"])
    BOOK.write_text(json.dumps(book, indent=1) + "\n")
    print("first frames set:", ", ".join(s.split("=")[0] for s in sets))


def comfy_pids():
    out = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
    return [int(l.split()[0]) for l in out.splitlines() if "main.py --listen 127.0.0.1 --port 8188" in l
            and "venv/bin/python" in l]


def comfy_restart(log):
    for pid in comfy_pids():
        os.kill(pid, signal.SIGTERM)
    time.sleep(6)
    for pid in comfy_pids():
        os.kill(pid, signal.SIGKILL)
    env = dict(os.environ, HIP_VISIBLE_DEVICES="0")
    subprocess.Popen([str(COMFY / "venv/bin/python"), "main.py", *COMFY_ARGS], cwd=COMFY, env=env,
                     stdout=open(ROOT / "media/cache/comfy.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(3)
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=3)
            print(time.strftime("%H:%M"), "ComfyUI up", file=log, flush=True)
            return
        except OSError:
            pass
    raise SystemExit("ComfyUI did not come up")


def black(cid):
    """A render can finish with every frame black (NaNs in sampling: C1D, 20 Oct). Sample three frames; if all are
    black, move the file aside so the clip counts as missing and the next attempt re-renders it."""
    f = sorted(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4")))[-1]
    means = []
    for t in (0.2, 1.0, 2.0):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", f, "-frames:v", "1", "-vf",
                              "scale=64:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        if raw:
            means.append(sum(raw) / len(raw))
    if means and max(means) < 2:
        (ROOT / "media/clips/local/black").mkdir(exist_ok=True)
        os.rename(f, ROOT / "media/clips/local/black" / Path(f).name)
        return True
    return False


def done(cid):
    return bool(glob.glob(str(ROOT / f"media/clips/local/{cid}-*.mp4")))


def run(only):
    book = json.loads(BOOK.read_text())
    todo = [e for e in book if (not only or e["id"] in only) and not done(e["id"])]
    missing = [e["id"] for e in todo if not e.get("image")]
    if missing:
        raise SystemExit(f"no first frame for {missing}: run `first`")
    todo.sort(key=lambda e: (e["kind"] != "sung", e["seconds"]))
    log = open(ROOT / "media/cache/clips-run.log", "a")
    for e in todo:
        e = next(x for x in json.loads(BOOK.read_text()) if x["id"] == e["id"])  # pick up first frames changed mid-run
        for attempt in (1, 2):
            comfy_restart(log)
            cmd = [sys.executable, str(ROOT / "production/tools/video.py"), e["kind"], "--id", e["id"],
                   "--image", str(ROOT / e["image"]), "--prompt", e["prompt"], "--seconds", str(e["seconds"])]
            if e["kind"] == "sung":
                cmd += ["--audio", str(ROOT / e["audio"])]
            else:
                cmd += ["--variant", "fast", "--size", "960x544"]
            print(time.strftime("%H:%M"), "start", e["id"], f"{e['seconds']} s", f"attempt {attempt}", file=log,
                  flush=True)
            r = subprocess.run(cmd, capture_output=True, text=True)
            print(time.strftime("%H:%M"), "end", e["id"], "exit", r.returncode, (r.stdout + r.stderr)[-600:], file=log,
                  flush=True)
            if r.returncode == 0 and black(e["id"]):
                print(time.strftime("%H:%M"), "black", e["id"], "(moved to media/clips/local/black/)", file=log, flush=True)
            elif r.returncode == 0:
                break
    print(time.strftime("%H:%M"), "run finished", file=log, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "first", "run"])
    ap.add_argument("sets", nargs="*")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "first":
        first(a.sets)
    else:
        run(set(filter(None, a.only.split(","))))


if __name__ == "__main__":
    main()
