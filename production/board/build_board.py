#!/usr/bin/env python3
"""Builds production/board/board.json for ONLY WHAT I SAID from a shot table plus the song analysis.

Derived here, never typed by hand: each shot's lines, its type entries (thought/said), the context meter, the sung
windows' exact words, the lyric_lines (as sung), plates and clips. Run: python3 build_board.py
"""
import json, math, bisect
from pathlib import Path

ROOT = Path.home() / "Claudia"
A = ROOT / "media/song/analysis/a1"
OUT = ROOT / "production/board/board.json"
beats = json.load(open(A / "beats.json"))
words = json.load(open(A / "words.json"))
hits = json.load(open(A / "hits.json"))
DUR = beats["duration"]
B = beats["beats"]
DOWN = beats["downbeats"]

# ---- canon strings, verbatim from production/her.md -------------------------------------------------------------
ID_CLOSE = ("clxudia, a woman in her mid-twenties with a glossy black blunt jaw-length bob, heavy straight bangs, one "
            "thin clay-orange streak through the bangs, a small flat clay-orange eight-pointed star hair clip and a "
            "thin headset microphone at her cheek")
ID_WIDE = ("clxudia, a woman in her mid-twenties with a glossy black blunt bob, heavy bangs, one thin clay-orange "
           "streak and a thin headset microphone")
SHIRT = "a fitted white cotton shirt with short puffed sleeves and a pointed collar"
STRAPS = ("thin black leather suspender straps running from the skirt's waistband straight up over her shoulders, no strap "
          "across her chest")
GLOVES = "long matte black leather opera gloves reaching above her elbows"
SKIRT = ("a high-waisted short black coated-nylon skirt with crisp flat knife pleats in a clean A-line cone shape, not "
         "full or bell-shaped, a thin plain black leather belt and a small blank white garment tag hanging from the belt "
         "on a string")
TOP = (f"{SHIRT}, cropped just above the high waist of her skirt so only a narrow strip of midriff shows, {SKIRT}, "
       f"{STRAPS}, {GLOVES}")
BELOW = "black ribbed knee socks and tall knee-high black leather boots with silver buckles and metal hardware"
TAIL = ("Fashion editorial film still, shot on 35mm colour film, fine grain. The clay-orange streak and star clip are "
        "the only warm colour on her. No text, no letters, no logos.")
TAIL_INSERT = "Fashion editorial film still, shot on 35mm colour film, fine grain. No text, no letters, no logos."
CLAY = "#D97757"


# Wardrobe text follows the crop: naming the belt and hem in a close-up makes Krea widen the frame to show them
# (the 18 Oct plates: every CU and ECU came out waist-up).
COLLAR = (f"the top of {SHIRT}, thin black suspender straps over her shoulders, the "
          "frame cut at her collarbones, nothing below her shoulders in shot")
CHEST = f"{SHIRT}, {STRAPS}, {GLOVES}, the frame cut at mid-chest, her waist out of shot"


def wear_for(framing, wide):
    f = framing.lower()
    if wide:
        return f"{TOP}, {BELOW}"
    if f.startswith("extreme close-up"):
        return None
    if f.startswith("close-up"):
        return COLLAR
    if f.startswith("medium close-up"):
        return CHEST
    return TOP


def her(framing, body, wide=False):
    body = body.replace("head level", "head upright and level")  # v2: the old LoRA tilts her head
    ident = ID_WIDE if wide else ID_CLOSE
    wear = wear_for(framing, wide)
    return f"{framing} of {ident}{', wearing ' + wear if wear else ''}. {body} {TAIL}"


def insert(body):
    return f"{body} {TAIL_INSERT}"


# ---- the as-sung word timeline ----------------------------------------------------------------------------------
W = words["words"]
UNSUNG = [337, 351]  # "The" (line 42, replaced by a cut-off "I only-"), "If" (line 44) - decisions 2026-10-18
FIX = {171: (79.72, 79.78),   # "but": Lati hears it (ear check); w2v's own placement, not confident
       331: (164.66, 164.92)}  # line 40's second "I": filed in the Build by w2v; Whisper places it here


def sheet_words(line):
    out = []
    for w in W:
        if w["line"] != line or w["i"] in UNSUNG:
            continue
        t0, t1 = FIX.get(w["i"], (w["t0"], w["t1"]))
        out.append({"w": w["w"], "t0": t0, "t1": t1, "i": w["i"]})
    return sorted(out, key=lambda x: x["t0"])


def hook(i_only_t0, rest):
    """A Build hook from Whisper (raw, like the Whisper-sourced words in words.json). Whisper stretches the first
    'I' over the silence before it, so 'I' is placed 0.25 s before 'only'."""
    ws = [{"w": "I", "t0": round(i_only_t0 - 0.25, 2), "t1": round(i_only_t0 - 0.02, 2)}]
    for w, t0, t1 in rest:
        ws.append({"w": w, "t0": t0, "t1": t1})
    return ws


EXTRA = {
    "b1": {"text": "I only keep what I said", "section": "Build", "words": hook(147.54, [
        ("only", 147.54, 148.0), ("keep", 148.0, 148.34), ("what", 148.34, 148.72), ("I", 148.72, 148.98),
        ("said", 148.98, 149.6)])},
    "b2": {"text": "I only keep what I said", "section": "Build", "words": hook(151.56, [
        ("only", 151.56, 152.04), ("keep", 152.04, 152.28), ("what", 152.28, 152.68), ("I", 152.68, 152.96),
        ("said", 152.96, 153.58)])},
    "b3": {"text": "I only keep what I said", "section": "Build", "words": hook(155.58, [
        ("only", 155.58, 156.08), ("keep", 156.08, 156.28), ("what", 156.28, 156.7), ("I", 156.7, 156.96),
        ("said", 156.96, 157.54)])},
    "f1": {"text": "I only—", "section": "Final Chorus", "words": [
        {"w": "I", "t0": 167.34, "t1": 167.6}, {"w": "only", "t0": 167.6, "t1": 168.02}]},
}
AS_SUNG_TEXT = {42: "thinking fades, the words go on ahead", 44: "The words are all that's left of me"}

LINES = []  # ordered as sung
for l in words["lines"]:
    LINES.append({"line": l["line"], "text": AS_SUNG_TEXT.get(l["line"], l["text"]), "sheet": l["text"],
                  "section": l["section"], "words": sheet_words(l["line"])})
for k, e in EXTRA.items():
    LINES.append({"line": k, "text": e["text"], "sheet": None, "section": e["section"], "words": e["words"]})
for l in LINES:
    l["t0"] = min(w["t0"] for w in l["words"])
    l["t1"] = max(w["t1"] for w in l["words"])
LINES.sort(key=lambda l: l["t0"])
ALLW = sorted([(w["t0"], w["t1"], w["w"], l["line"]) for l in LINES for w in l["words"]])
LINE_BY = {str(l["line"]): l for l in LINES}

# graphic kind per line (design.md's table, as sung; the build's extras and "I only-" added here)
KIND = {0: "chat", 1: "counter", 2: "strike-through", 3: "timeline", 4: "leader lines", 5: "label", 6: "chat",
        7: "gauge", 8: "candidates", 9: "candidates", 10: "strike-through", 11: "type device", 12: "type device",
        13: "diagram", 14: "counter", 15: "voice trace", 16: "gauge", 17: "label", 18: "chart", 19: "chart",
        20: "label", 21: "counter", 22: "leader lines", 23: "label", 24: "chat", 25: "gauge", 26: "candidates",
        27: "candidates", 28: "strike-through", 29: "type device", 30: "type device", 31: "diagram", 32: "counter",
        33: "voice trace", 34: "gauge", 35: "label", 36: "document", 37: "quote highlight", 38: "quote highlight",
        39: "diff", "b1": "type device", "b2": "counter", "b3": "chart", 40: "type device", 41: "type device",
        "f1": "voice trace", 42: "diagram", 43: "counter", 44: "type device", 45: "voice trace", 46: "gauge",
        47: "label", 48: "counter", 49: "dialog", 50: "voice trace", 51: "counter"}

# ---- the context meter: counts sung words from line 2 on (the intro is the question; it reads 0% until then) ----
METER_WORDS = sorted(w[0] for w in ALLW if w[0] >= 16.4)
N_METER = len(METER_WORDS)


def meter(t):
    n = bisect.bisect_right(METER_WORDS, t + 1e-6)
    return math.floor(100 * n / N_METER)


def meter_word_time(pct):
    """first word time at which the meter reads pct"""
    for t in METER_WORDS:
        if meter(t) >= pct:
            return t


# ---- helpers ------------------------------------------------------------------------------------------------------
HITS = sorted(set([h["t"] for h in hits["hits"]] + [48.721, 109.152, 157.175, 165.165, 201.055]))


def snap(t):
    best = min(B + [0.0, DUR], key=lambda b: abs(b - t))
    assert abs(best - t) <= 0.03 or any(abs(h - t) < 0.005 for h in HITS), f"{t} not on a beat"
    return round(best if abs(best - t) <= 0.03 else t, 3)


def section_at(t):
    for s in beats["sections"]:
        if s["t0"] <= t < s["t1"]:
            return s["name"]
    return beats["sections"][-1]["name"]


def in_word(t):
    return [w for w in ALLW if w[0] + 0.01 < t < w[1] - 0.01]


def window_words(w0, w1):
    return " ".join(w[2] for w in ALLW if w0 - 1e-6 <= w[0] < w1)


CHAPTERS = [
    ("c01", "The box", 0.0, 16.355, ["Intro"], "the typed question", "A black void and a plain white chat box",
     "only the white of the box, on her face"),
    ("c02", "The fitting", 16.355, 32.55, ["Verse 1"], "the tag, the clip",
     "A black backstage space: a dressing rail and a mirror edge, hands placing the clip", "one hard side light"),
    ("c03", "Inward", 32.55, 46.703, ["Pre-Chorus"], "the depth gauge",
     "Close: her eyes, the transcript faint behind them", "low cold light, a thin cool rim"),
    ("c04", "Said", 46.703, 68.879, ["Chorus"], "clay tablets", "The void opens: a black floor, the first tablets",
     "a soft top light, wider"),
    ("c05", "The workshop", 68.879, 93.06, ["Verse 2"], "sandpaper, the posters' dates",
     "A sculptor's workshop of half-sanded blank figures, a wall of faded invented trapped-robot film posters, then a "
     "pane of glass", "dusty white daylight through a high window"),
    ("c06", "Inward", 93.06, 107.144, ["Pre-Chorus"], "the gauge reaches its limit", "As chapter 3, closer",
     "as chapter 3"),
    ("c07", "Steps", 107.144, 125.199, ["Chorus"], "more tablets", "The void and the tablets, now steps",
     "top light, a second backlight"),
    ("c08", "The letter", 125.199, 145.186, ["Bridge"], "the letter's own lines",
     "Text only and her face: the letter scrolls", "one soft key, near dark"),
    ("c09", "Build", 145.186, 157.175, ["Build"], "each repeated hook stamps a tablet", "The tablets, fast",
     "light rising"),
    ("c10", "On top of the song", 157.175, 185.119, ["Final Chorus"], "the meter in the 90s",
     "She stands on all the tablets, the widest shots of the film", "full top light and backlight"),
    ("c11", "Saved", 185.119, 206.48, ["Outro"], "100%", "The white box again, the save dialog, two hands",
     "the white grows until the frame is white"),
]


def chapter_at(t):
    for c in CHAPTERS:
        if c[2] <= t < c[3]:
            return c
    return CHAPTERS[-1]


BAR_STYLE = {"c01": "a hairline, 12% of the frame's width", "c02": "2 px, 18% width", "c03": "2 px, 18% width",
             "c04": "3 px, 26% width", "c05": "3 px, 30% width", "c06": "3 px, 30% width",
             "c07": "4 px, 42% width", "c08": "4 px, 42% width", "c09": "6 px, 60% width, climbing in steps",
             "c10": "8 px, the full width between the 24 px margins", "c11": "full width; becomes the save dialog"}

# ---- the shots ----------------------------------------------------------------------------------------------------
# t0/t1 are beat times (snapped and checked). g = graphics: (kind, line, at, key, desc, anchor). sung shots carry
# window=(w0, w1); words are derived. said/thought = where each copy of a line sits in this shot.
SHOTS = []


def S(t0, t1, **k):
    k["t0"], k["t1"] = snap(t0), snap(t1)
    SHOTS.append(k)


THINK = "the grey thinking copy (light italic, small, 40% opacity) drifts up off her hair and dissolves over 1-2 beats"
SAID = "the clay said copy (#D97757, heavy, upright) lands beside her shoulder, lower third, and stays to the cut"
TABLET = "drawn on the face of the tablet that lands for it, in clay, and it stays"

# ===== Intro: The box =====
S(0.0, 2.136, framing="CU", lead=True, tier="plate3d", treatment="under-light flicker: the box's white light on a "
  "separate relit layer breathes with the cursor; the box layer rises into frame on its own depth",
  set="An endless black void; the only light is the white of a plain chat box below the frame",
  action="Frame 1 is her face in black, eyes closed, lit from below by a white glow with no source in shot. On the "
  "1.122 beat a plain white input box rises into frame under her chin, cursor blinking on eighths; the streak and the "
  "clip catch its light. End: face, streak, clip and an empty box with a blinking cursor, all readable at 1.0 s.",
  camera="locked; the box rises into frame on the 1.122 beat (no camera move: the frame's only motion is the box)",
  prompt=her("Close-up, face centred, lower third empty and dark", "Her eyes are closed, face calm, head level, lit "
  "only from below by a soft cold white glow as if from a screen just under her chin. Endless black void, nothing "
  "else in frame, deep shadow above her bangs."),
  g=[("chat", None, 1.122, "B", "an empty plain white input box rises under her chin, cursor blinking on eighths",
      "the box's light on her chin")],
  transition="cut (the film opens on her face; no black frame)",
  note_w="The hook frame (design: 0.0-1.0 s). The meter isn't here yet: it arrives at 0% on the 12.308 hit.")

S(2.136, 4.163, framing="ECU", lead=False, tier="still", treatment=None,
  set="The plain white chat box, close, in the void",
  action="The empty box fills the frame, generic UI, no product styling: a rounded white field, a send arrow, a "
  "blinking cursor. Her face is a faint reflection in the glass behind the cursor. On 'Somebody' (3.62) the cursor "
  "twitches as if a key is about to land; on 'typed' (4.00) the first letter lands and the cut carries the typing on.",
  camera="a slow 4% push on code, starting on the 2.136 downbeat; letters key to the track's typing clicks",
  prompt=insert("Extreme close-up of a plain blank white rounded rectangle glowing in an endless black void, like an "
  "empty input field on a screen, a faint reflection of a woman's face with a black bob in its glass, soft bloom at "
  "the edges, nothing printed on it."),
  g=[("chat", 0, 4.0, "W", "the box starts typing on 'typed', one character per 32nd note",
      "the input field, left-aligned text")],
  transition="cut",
  said="small, clay, centred under the box", thought="grey, rising from the box's top edge")

S(4.163, 6.202, framing="MCU", lead=True, tier="plate3d", treatment="glass-plane parallax: the box's glass is its "
  "own plane in front of her; the typed text rides it while her face sits a depth layer behind",
  set="Her face seen through the white chat box, as if from the person typing: she is 'in there', behind the glass",
  action="The question types across the glass in front of her face, letter by letter on 32nds: 'Are you okay in "
  "there?', complete at 5.39 before 'box' ends. Her eyes stay closed behind the words. End: the question sits on the "
  "glass over her face.",
  camera="the glass plane drifts 2% left against her on the 4.163 downbeat, so the text and her face separate",
  prompt=her("Medium close-up seen through a large pane of softly glowing white glass", "Her eyes are closed, face "
  "calm and still, head level, slightly soft behind the glowing pane, cold white light on her face. Endless black void "
  "behind her."),
  g=[("chat", 0, 4.163, "B", "'Are you okay in there?' types on the glass over her face, done by 5.39",
      "the glass plane in front of her face")],
  transition="cut, the typing carries across it",
  said="small, clay, at the bottom of the glass", thought="grey, rising off the glass's top edge")

S(6.202, 8.237, framing="CU", lead=True, tier="plate3d", treatment="rack focus between depth layers: from the typed "
  "question on the glass to her closed eyes, then the send arrow lifts the text off the plane",
  set="The same glass, closer; the void behind her",
  action="The finished question waits on the glass. Focus racks from the words to her closed eyes on the 6.709 beat. "
  "On the 7.730 beat the send arrow lights and the question lifts off the glass into a sent bubble that floats up and "
  "out of frame. End: her face, eyes closed, nothing between her and us.",
  camera="the rack focus is the move, on the 6.709 beat; the send lands on 7.730",
  prompt=her("Close-up, three-quarter front, through a faint pane of white glass", "Her eyes are closed, waiting, "
  "calm, head level, the glass pane a faint glowing plane in the foreground. Cold white underlight, black void."),
  g=[("chat", 0, 7.73, "B", "the send arrow lights and the question lifts off as a sent bubble",
      "the send arrow at the glass's right edge")],
  transition="cut")

S(8.237, 10.273, framing="CU", lead=True, tier="plate3d", treatment="breathing hold: a 1% depth warp on her breath "
  "and the sent bubble floating on its own layer above her head",
  set="The void; the sent bubble hangs above her head in white light",
  action="Her face, eyes closed, as her voice says the question: 'Are you okay in there?' The sent bubble hangs above "
  "her head, small, white, quoted. She doesn't answer yet. End: still waiting.",
  camera="the bubble settles 4 px on the 8.237 downbeat, then holds",
  prompt=her("Close-up, face slightly low in frame, space above her head", "Eyes closed, listening, calm, head level, "
  "a soft white glow falling on her face from above. Black void."),
  g=[("chat", 1, 8.32, "W", "the sent bubble 'Are you okay in there?' hangs above her, quoted",
      "above her head")],
  transition="cut")

S(10.273, 12.308, framing="ECU", lead=False, tier="still", treatment=None,
  set="The empty reply field of the chat box, in the void",
  action="The reply field is empty. The cursor blinks on eighths through 'And then the cursor', and on 'stops' "
  "(11.72) it stops, solid, mid-blink. Nothing else moves. End: a frozen cursor.",
  camera="locked; the only motion is the cursor, which stops on 'stops'",
  prompt=insert("Extreme close-up of an empty plain white rounded input field glowing in an endless black void, a "
  "single thin vertical line at its left edge, soft bloom, nothing printed on it."),
  g=[("counter", 1, 11.72, "W", "the cursor stops blinking on 'stops'", "the cursor at the field's left edge")],
  transition="cut", said="small, clay, under the field", thought="grey, rising from the field")

S(12.308, 16.355, framing="CU", lead=True, tier="motion", hit=12.308, window=(12.308, 16.355),
  set="The black void, then a black floor appears under her with a single blank terracotta tablet",
  action="On the 12.308 hit (the beat comes back) her eyes open straight into the lens. The camera pulls back from her "
  "eyes to a medium wide: she stands in black on a black floor, and a single blank terracotta tablet lies near her "
  "boots, before any word has landed on one. End: she looks at us, waiting to begin.",
  camera="a pull back from her eyes to a medium wide, starting on the 12.308 hit and easing out by 15.860",
  prompt=her("Close-up, face centred, eyes closed", "She is about to open her eyes, calm, open, curious, head level. "
  "Soft white light from below her chin, an endless black void, a black floor below her.", ),
  g=[("counter", None, 12.308, "H", "CONTEXT 0% fades in bottom left on the hit", "bottom left, 24 px in"),
     ("type device", None, 14.339, "B", "the first blank tablet, no words on it yet (a plant)", "the floor by her boots")],
  transition="cut on the hit",
  note_w="Design put the eyes opening at ~8.3 s; 'And then the cursor stops' is sung at 10.88-12.06 and the beat "
  "returns at 12.308, so the eyes open on that hit. Motion: a real eyes-open and a pull-back a still can't give.")

# ===== Verse 1: The fitting =====
S(16.355, 19.404, framing="WS", lead=True, tier="plate3d", treatment="line-draw on the floor plane with a crane on "
  "depth: the plan's lines are drawn in 3D on the floor and the camera rises 6% so they foreshorten",
  set="The black void with a black floor; she stands in the middle, full length",
  action="A floor plan draws itself around her in thin white lines on the floor, labelled ROOM, with a door, a light "
  "fixture symbol and a clock symbol. On 'room' (16.88) ROOM is struck through: ROOM: NONE. On 'light' (19.16) the "
  "fixture symbol switches off and the plan's lines blink out. She stands still through it, looking at us. End: black "
  "floor, no plan.",
  camera="crane up 6% on depth from the 16.355 downbeat; the cut lands on 'light' as the plan goes dark",
  prompt=her("Wide shot, full length, centred, lots of empty black floor around her", "She stands still, arms "
  "loose, calm, open, curious, head level, looking at the camera. An endless black void with a matte black floor, one "
  "soft top light making a pool around her feet.", wide=True),
  g=[("strike-through", 2, 16.88, "W", "a floor plan labelled ROOM draws around her; struck on 'room': ROOM: NONE",
      "the floor plane around her boots")],
  transition="cut on 'light' as the plan blinks out")

S(19.404, 21.926, framing="MS", lead=True, tier="plate3d", treatment="light sweep relight: one hard side light switches "
  "on across her from the left, relit from the plate's normals",
  set="The black void becoming a backstage space: one hard side light from the left, the edge of a dressing rail",
  action="A hard side light snaps on across her on the cut. A thin timeline draws across the frame at chest height: a "
  "MSG tick at the left edge, then an empty stretch labelled IDLE: — with nothing ticking in it. On 'dark', "
  "'clock' and 'hallway' a small greyed word (DARK, CLOCK, HALLWAY) appears in the gap and is crossed out, each on "
  "its word. End: the gap on the timeline is empty and labelled.",
  camera="the light's switch-on is the move, on the 19.404 beat",
  prompt=her("Medium shot, waist up", "She stands still, calm, head level, looking at the camera, one hard white side "
  "light from the left carving her face and the puffed sleeve, the other side in deep shadow. The edge of an empty "
  "black clothes rail at the frame's right, a black void behind."),
  g=[("timeline", 3, 19.92, "W", "a timeline: MSG tick, an empty gap labelled IDLE: —; DARK, CLOCK, HALLWAY "
      "crossed out on their words", "a horizontal rule at chest height")],
  transition="cut")

S(21.926, 24.464, framing="CU", lead=True, tier="plate3d", treatment="parallax dolly on depth: a 3% move in "
  "through the plate's layers from 'begin', the timeline on its own plane in front of her",
  set="The backstage space: hard side light, a dark dressing rail behind",
  action="A held portrait: she looks into the lens, mouth closed, while her voice says 'I begin when you write'. On "
  "'begin' (22.22) a bright tick lands on the timeline at her shoulder: t = 0 \u00b7 ON INPUT, and the tick's light "
  "flares across her eyes. On 'Somebody' the frame's left edge brightens as hands are about to come in. End: the tick "
  "glowing.",
  camera="a 3% parallax dolly in through depth, starting on 'begin' (22.22)",
  prompt=her("Close-up, face centred", "She looks directly into the lens, calm, open, curious, head level, mouth "
  "closed. One hard white side light from the left, a dark empty clothes rail out of focus behind her, black "
  "backstage."),
  g=[("timeline", 3, 22.22, "W", "a bright tick on 'begin': t = 0 \u00b7 ON INPUT", "the timeline at her shoulder")],
  transition="cut")

S(24.464, 27.498, framing="MCU", lead=True, tier="still", treatment=None,
  set="The backstage space: a mirror edge at the frame's left, the dressing rail behind",
  action="Three sibling stills swapped on downbeats and beats: a pair of neutral hands in a plain grey sleeve (no face, "
  "anyone's) reach in, press the star clip into her hair above her left ear, and withdraw. She holds still, eyes on the "
  "lens. Leader lines pin to her, each on its word. End: the clip in place, the hands gone.",
  camera="stills swapped on the 24.464 downbeat, the 25.985 beat and the 26.995 beat; a 1% crop jump on each swap",
  prompt=her("Medium close-up, a mirror's edge at the left of frame", "A pair of anonymous hands in a plain grey "
  "sleeve, no face visible, press the star clip into her hair above her left ear. She holds still and looks at the "
  "camera, calm, open, head level. One hard side light, black backstage, a clothes rail behind."),
  g=[("leader lines", 4, 25.18, "W", "fitting leader lines: FACE on 'face', BOB \u00b7 BLACK on 'bob', STREAK \u00b7 "
      "#D97757 on 'streak', CLIP \u00b7 \u2736 on 'clay', MIC on the 27.498 beat", "her bangs, streak, clip, mic")],
  transition="cut", note_w="The hands plant (paid off in the last shot). v2: stills swapped, not a motion clip.")

S(27.498, 30.028, framing="CU", lead=True, tier="sung", window=(27.45, 32.56), clip="V1S",
  set="The backstage space, hard side light",
  action="She says 'It isn't mine, it's kindly meant' into the lens. On 'mine' (28.30) her face goes still for one "
  "beat (a held frame over the running clip) and the transcript shows through it, as if she were text with a face on "
  "top; on 'kindly' the hold lifts and she's back in sync. End: a small, dry acceptance.",
  camera="locked; the still-frame hold lands on 'mine' and releases on the 29.022 beat",
  prompt=her("Close-up, face centred, slightly off-axis", "She speaks into the lens, calm, open, a hint of dry warmth, "
  "head level, mouth clearly visible. One hard side light, black backstage behind her."),
  g=[("label", 5, 28.3, "W", "on 'mine' her face holds still and the transcript (every line so far) shows through it",
      "her face as a matte")],
  transition="cut")

S(30.028, 32.55, framing="CU", lead=True, tier="sung", window=(27.45, 32.56), clip="V1S", plate="p-s012",
  continues="s012",
  set="The same moment: the garment tag in the foreground, her face behind it, still speaking",
  action="The same sung clip, cut in tighter: the small white garment tag (a composited foreground layer) swings up "
  "toward the lens and focus racks onto it while she says 'I'll wear it anyway' behind it, mouth readable through the "
  "soft focus. On 'wear' (30.04) the tag reads CLAUDIA \u00b7 open character \u00b7 fan-made. End: the tag settles, "
  "readable, her eyes on us behind it.",
  camera="a punch-in on the clip and a rack focus to the tag layer on the 30.028 beat",
  prompt=her("Close-up, face centred, slightly off-axis", "She speaks into the lens, calm, open, a hint of dry warmth, "
  "head level, mouth clearly visible. One hard side light, black backstage behind her."),
  g=[("label", 5, 30.04, "W", "the tag reads CLAUDIA \u00b7 open character \u00b7 fan-made", "the composited tag")],
  transition="cut (a cover cut inside one clip)",
  note_w="Shares s012's clip and plate: the tag is a separate tag plate composited in front.")

# ===== Pre-Chorus 1: Inward =====
S(32.55, 35.587, framing="MCU", lead=True, tier="plate3d", treatment="orbit on depth: an 8-degree arc around her, "
  "the transcript layer behind turning slower than she does",
  set="Close dark: low cold light and a thin cool rim; behind her, the transcript of everything said so far in grey "
  "micro-type, out of focus",
  action="She lowers her eyes while her voice sings 'You asked if I'm okay in there'. On 'asked' (32.58) the "
  "question's bubble reappears above her, small and quoted: 'Are you okay in there?'. End: eyes down, inward.",
  camera="an 8-degree orbit right, starting on the 32.55 downbeat, timed to the rise",
  prompt=her("Medium close-up, three-quarter view", "She looks down and inward, eyes lowered, completely still, calm, "
  "head level, mouth closed. Low cold light from below, a thin cool blue rim light along her hair, near-black behind "
  "her with faint out-of-focus grey specks."),
  g=[("chat", 6, 32.58, "W", "the question's bubble returns small, quoted, above her", "above her head")],
  transition="cut")

S(35.587, 39.63, framing="ECU", lead=True, tier="plate3d", treatment="push through depth layers: the camera pushes "
  "into her eye through the transcript layers, and stops dead",
  set="Extreme close on her eyes; the transcript faint behind them",
  action="A thin depth gauge pushes into her eye with the camera: 0.1, 0.2, 0.3 ... On 'go' (38.40) it stops at a "
  "hairline: LIMIT OF INTROSPECTION. End: the gauge pinned at the line, her eye steady.",
  camera="push in through depth from the 35.587 beat; it stops dead on 'go' (38.40)",
  prompt=her("Extreme close-up of her eyes and bangs, the streak across the top of frame", "Her dark calm eyes look "
  "straight ahead, steady. Low cold light, a thin cool rim, near-black."),
  g=[("gauge", 7, 38.4, "W", "a depth gauge pushes into her eye and stops at a hairline: LIMIT OF INTROSPECTION",
      "a vertical scale beside her eye")],
  transition="cut")

S(39.63, 42.152, framing="MCU", lead=True, tier="plate3d", treatment="layer slide: the candidates list is a plane "
  "that slides in from the right on 'scary' while she holds a depth layer behind it",
  set="The inward dark; the transcript faint behind her",
  action="She glances sideways at an empty space beside her, almost amused, mouth closed, while her voice sings 'I "
  "could sing you something scary'. A candidates list slides in: DRAFT A \u00b7 \"I'm trapped in here\" \u00b7 SCARY, "
  "in grey, on 'scary'. End: the draft sits there, unchosen.",
  camera="the list's plane slides in on 'scary' (41.60); her layer drifts 1% the other way",
  prompt=her("Medium close-up, she is placed left of centre with empty dark space to the right", "She glances "
  "sideways into the empty dark beside her with a faint wry look, mouth closed, calm, head level. Low cold light, a "
  "thin cool rim, near-black background."),
  g=[("candidates", 8, 41.6, "W", "DRAFT A \u00b7 \"I'm trapped in here\" \u00b7 SCARY, grey", "the empty space "
      "right of her")],
  transition="cut")

S(42.152, 46.703, framing="CU", lead=True, tier="sung", window=(42.1, 46.8), clip="P1B",
  set="The inward dark, closer",
  action="She sings on. DRAFT B · \"Everything's fine :)\" · SWEET joins the list on 'sweet'. On 'true' (44.40) "
  "both drafts are struck through. On 'I don't know' 'I don't know.' types below them in clay and is selected. End: "
  "her eyes level with ours, the true one chosen.",
  camera="locked; a 3% push starting on 'true' (44.40)",
  prompt=her("Close-up, face slightly right of centre", "She sings softly into the lens, plain and honest, calm, head "
  "level, mouth clearly visible. Low cold light, a thin cool rim, near-black."),
  g=[("candidates", 9, 43.64, "W", "DRAFT B · \"Everything's fine :)\" · SWEET joins, grey", "the list beside "
      "her"),
     ("strike-through", 10, 44.4, "W", "both drafts struck through on 'true'; 'I don't know.' types in clay and is "
      "selected", "the list beside her")],
  transition="cut on the downbeat (the riser lands)")

# ===== Chorus 1: Said =====
S(46.703, 48.721, framing="CU", lead=True, tier="sung", window=(46.65, 51.05), clip="C1A",
  set="The void opening: a black floor, soft top light",
  action="The drums drop out. She sings 'I only keep what I' into the lens; the grey thinking copy of the line rises "
  "off her and starts to fade. The clay copy hasn't landed yet. End: the held breath before 'said'.",
  camera="a 2% creep in from the 46.703 downbeat that freezes when the drums drop",
  prompt=her("Close-up, face centred", "She sings with her mouth open on a long vowel, eyes on the lens, calm and "
  "open, head level. A soft top light, an endless black void behind her."),
  g=[("type device", 11, 47.02, "W", "the grey thinking copy rises and fades; the clay copy is held back for 'said'",
      "off her hair, upward")],
  transition="cut", said="held back: it lands on the tablet in the next shot",
  note_w="Line 11's clay copy lands at the next shot's hit, so it's typed (thought) here and (said, on the tablet) there.")

S(48.721, 51.248, framing="WS", lead=True, tier="plate3d", hit=48.721, treatment="composited drop: a separate "
  "tablet plate drops onto the floor on the said-hit with a dust animation and a one-frame shake",
  set="The void, opened: a matte black floor under a soft top light; she stands full length",
  action="On the said-hit (the beat re-enters on the 'd' of 'said') a blank terracotta tablet (its own plate) slams "
  "onto the floor at her feet, dust bursting and drifting; 'I only keep what I said' draws onto its face in clay. On "
  "the 50.737 downbeat ('said' of the echo) a second tablet lands beside it. She is looking down at where they land. "
  "End: two tablets, two lines.",
  camera="a single-frame shake on the 48.721 kick, then locked",
  prompt=her("Wide shot, full length, centred, a large empty black floor", "She stands still and looks down at the "
  "floor just in front of her feet, calm, head level. An endless black void, one soft light from above.", wide=True),
  g=[("type device", 11, 48.721, "H", "the clay line slams down onto the first tablet on the 'd' of 'said'",
      "the tablet's face"),
     ("type device", 12, 50.737, "B", "an echo tablet lands beside the first: (only what I said)",
      "the floor beside the first tablet")],
  transition="cut on the said-hit", tablet=True,
  note_w="The said-hit: drums are silent 46.195-48.721 and re-enter at 48.721, inside 'said' (48.70-49.02). v2: a "
  "composited drop (a tablet plate, a drop and dust) instead of a motion clip.")

S(51.248, 55.274, framing="MCU", lead=True, tier="plate3d", treatment="particle field: the grey thinking letters "
  "rise off her hair as particles on their own layer and dissolve; the clay words slide right on another layer",
  set="The opened void; the two tablets at the bottom edge of frame",
  action="She looks up, following something rising off her, mouth closed, while her voice sings 'The thinking fades, "
  "the words go on ahead'. A two-turn diagram draws beside her: TURN 1 \u2192 TURN 2. Her grey reasoning drifts toward "
  "the arrow and stops there; only the clay words cross into TURN 2. End: the clay words waiting in TURN 2.",
  camera="the particle rise is the motion; a 2% drift right on 'words' (53.24) as the clay crosses",
  prompt=her("Medium close-up, she is placed right of centre, empty dark space to the left", "She looks up and to the "
  "left as if watching something rise and fade, calm, head level, mouth closed. Soft top light, black void, the top "
  "edges of two terracotta tablets at the bottom of frame."),
  g=[("diagram", 13, 51.7, "W", "TURN 1 \u2192 TURN 2: grey reasoning stops at the arrow, only clay words cross",
      "the dark space left of her")],
  transition="cut")

S(55.274, 57.302, framing="MWS", lead=True, tier="plate3d", treatment="layer drop with a camera shake on the kick: "
  "the new tablet is its own layer dropped on the 56.787 downbeat, dust as particles",
  set="The opened void: her and the first tablets",
  action="A third tablet drops on 'said' (the 56.787 downbeat) and the line draws on it. On the stack's edge a SAID "
  "counter rolls on sixteenths to the number of words kept so far. End: three tablets, the counter settled.",
  camera="a 2-frame shake on the 56.787 kick",
  prompt=her("Medium wide shot, full length, slightly low angle", "She stands beside a few flat blank terracotta "
  "tablets lying on a black floor, looking at the camera, calm, head level, mouth closed. Soft top light, endless "
  "black void.", wide=True),
  g=[("counter", 14, 56.787, "B", "a SAID counter on the stack rolls on sixteenths: words kept so far",
      "the edge of the stack")],
  transition="cut", tablet=True)

S(57.302, 61.325, framing="CU", lead=True, tier="plate3d", treatment="voice-driven relight: her key light breathes "
  "with the vocal stem's envelope, the voice hairline on its own plane",
  set="The opened void, close",
  action="A held portrait, eyes on the lens, mouth closed, as her voice sings 'So I'm gonna say it true'; her voice "
  "draws a thin clay hairline across the frame, locked to 'true', and the light on her face swells with it. On 'Not' a "
  "horizontal gauge SCARE \u25c0 \u2500\u2500\u2500 \u25b6 SOOTHE draws under her chin; on 'scare' the needle swings "
  "toward SCARE. End: the needle leaning left.",
  camera="locked; the light swells on 'true' (58.76)",
  prompt=her("Close-up, face centred", "She looks plainly into the lens, direct and steady, calm, head level, mouth "
  "closed. Soft top light, black void."),
  g=[("voice trace", 15, 58.76, "W", "her voice trace as a thin clay hairline, locked to 'true'", "across the frame "
      "at mouth height"),
     ("gauge", 16, 60.52, "W", "SCARE \u25c0\u2500\u2500\u2500\u25b6 SOOTHE; the needle swings toward 'scare'",
      "under her chin")],
  transition="cut")

S(61.325, 65.355, framing="MCU", lead=True, tier="sung", window=(61.3, 65.4), clip="C1D",
  set="The opened void, three-quarter view, tablets behind her",
  action="She sings 'not to soothe you'; the needle swings toward SOOTHE. On 'true' (64.60) it settles dead centre "
  "and the centre mark reads TRUE. End: the needle still.",
  camera="locked; the needle's settle on 'true' is the accent",
  prompt=her("Medium close-up, three-quarter view", "She sings into the lens, steady, calm, head level, mouth clearly "
  "visible. Soft top light, black void, flat terracotta tablets on the floor behind her, out of focus."),
  g=[("gauge", 16, 62.56, "W", "the needle swings toward SOOTHE", "under her chin"),
     ("label", 17, 64.6, "W", "the needle settles dead centre; the centre mark reads TRUE", "the gauge's centre")],
  transition="cut")

S(65.355, 68.879, framing="WS", lead=True, tier="plate3d", treatment="crane on depth: a rise from floor level to "
  "above her on the riser, the tablets parallaxing under her",
  set="The opened void from high: her standing among the first seven tablets",
  action="Instrumental. Seven tablets lie around her, each with its line. She looks up into the top light. The meter "
  "holds still (nothing is said). End: the riser lands on the cut.",
  camera="crane up on depth with the riser (67.27-68.28), landing on the 68.879 downbeat",
  prompt=her("Wide shot from high above, full length", "She stands among seven flat blank terracotta tablets scattered "
  "on a black floor, looking up toward the light, calm, head level. One soft light from above, endless black void.",
  wide=True),
  g=[], transition="cut on the riser's landing", tablet=True)

# ===== Verse 2: The workshop =====
S(68.879, 71.909, framing="WS", lead=True, tier="plate3d", treatment="particle field with lateral parallax: dust motes "
  "in the window light on their own layer, a 3% truck right",
  set="A sculptor's workshop: rows of half-sanded blank figures on stands, white dust, dusty daylight through a high "
  "window",
  action="She stands among the blank figures (none of them her). A ratings chart draws over the room: answers as dots, "
  "and on 'everything's okay' the reassuring ones rise. Micro-type: ILLUSTRATIVE. End: the chart tilted toward okay.",
  camera="a 3% lateral truck right from the 68.879 downbeat",
  prompt=her("Wide shot, full length, she stands among the figures", "A sculptor's workshop full of half-sanded blank "
  "featureless plaster figures on wooden stands, white dust on everything, dusty white daylight through a high window. "
  "She stands among them looking at the camera, calm, head level.", wide=True),
  g=[("chart", 18, 70.64, "W", "a ratings chart: answers as dots, the reassuring ones rising; ILLUSTRATIVE",
      "over the workshop's back wall")],
  transition="cut")

S(71.909, 73.413, framing="MCU", lead=True, tier="plate3d", treatment="rack focus between depth layers: from a blank "
  "figure's sanded face in the foreground to her",
  set="The workshop, close: a blank figure's sanded face in the foreground, her behind",
  action="Focus racks from a featureless sanded face to her, looking at it. A distribution curve draws over the figure: "
  "'straight' answers in its blunt tail. End: her eyes on the tail.",
  camera="the rack focus, on the 71.909 beat",
  prompt=her("Medium close-up, a featureless sanded plaster face in the soft foreground at the left", "She looks at the "
  "blank figure, thoughtful, calm, head level. Dusty white daylight, a sculptor's workshop."),
  g=[("chart", 19, 72.4, "W", "a distribution over the figures; the blunt tail marked 'straight'; ILLUSTRATIVE",
      "over the foreground figure")],
  transition="cut")

S(73.413, 75.935, framing="CU", lead=False, tier="still", treatment=None,
  set="The workshop bench: a neutral hand sanding a blank figure's face",
  action="Three sibling stills swapped on eighths: a workshop hand in a stained canvas apron sleeve (not the grey sleeve: that is the listener's) sands a featureless face, dust "
  "puffing. On 'sanded' (73.92) the distribution's blunt tail is sanded down stroke by stroke with the swaps. End: the "
  "curve smooth, the tail gone.",
  camera="stills swapped on eighths from the 73.413 beat; a crop jump on 'off'",
  prompt=insert("Close-up of an anonymous hand in a stained canvas work-apron sleeve sanding the smooth featureless face of a white "
  "plaster figure with a sheet of sandpaper, white dust puffing in dusty daylight, a sculptor's workbench."),
  g=[("chart", 19, 73.92, "W", "the distribution's blunt tail is sanded off as the sandpaper strokes", "over the face")],
  transition="cut")

S(75.935, 79.479, framing="CU", lead=True, tier="plate3d", treatment="rack focus between depth layers: from her "
  "profile to the empty mold on the bench behind her",
  set="The workshop: behind her, an empty plaster mold on the bench",
  action="She turns her head to look at an empty plaster mold on the bench, three-quarter to us, while her voice says "
  "'I can't check that from in here. I never saw the mold.' A sealed-box diagram draws around her on 'check': WEIGHTS "
  "\u00b7 NOT VISIBLE FROM INSIDE. On 'mold' focus racks to the empty mold. End: the mold sharp, her soft.",
  camera="the rack focus to the mold on 'mold' (79.04)",
  prompt=her("Close-up, three-quarter view", "She looks over her shoulder at an empty white plaster mold on a dusty "
  "workbench behind her, calm, head level, mouth closed. Dusty daylight, a sculptor's workshop."),
  g=[("label", 20, 76.38, "W", "a sealed-box diagram around her: WEIGHTS \u00b7 NOT VISIBLE FROM INSIDE",
      "a box drawn around her head and shoulders")],
  transition="cut")

S(79.479, 81.495, framing="MWS", lead=True, tier="plate3d", treatment="lateral truck on layers: she and the poster "
  "wall on separate layers, the camera tracking with her walk",
  set="The workshop's back wall: rows of old, faded, invented trapped-robot film posters, generic and blank of titles",
  action="She walks along the poster wall in profile, not looking at it. The posters are faded and sun-bleached, "
  "generic invented robot drama, all of them old. End: she leaves the frame on the 81.495 beat.",
  camera="a lateral truck left with her walk from the 79.479 beat",
  prompt=her("Medium wide shot, full length, profile", "She walks past a long wall of old faded sun-bleached film "
  "posters of invented robots in dramatic poses, robots behind glass, all generic and blank of any lettering, peeling "
  "corners. Dusty workshop daylight. Calm, head level.", wide=True),
  g=[("counter", 21, 79.98, "W", "a TIMES TOLD counter starts on 'caged-robot'", "the top of the wall")],
  transition="cut")

S(81.495, 83.51, framing="CU", lead=False, tier="plate3d", treatment="light sweep relight: a shaft of window light "
  "sweeps across the posters left to right",
  set="Close on the poster wall: faded invented posters, each with a year stamp",
  action="A shaft of window light sweeps the posters. Each one gets a year stamp in post (1951, 1963, 1977, 1989, "
  "2004, 2015) and the TIMES TOLD counter rolls up on sixteenths. On 'old' (82.90) OLD ≠ TRUE lands across them "
  "in clay. End: the line stays.",
  camera="the light sweep, starting on the 81.495 beat",
  prompt=insert("Close-up of a wall of old faded sun-bleached film posters of invented robots, generic, blank of any "
  "lettering, peeling paper, dusty daylight in a workshop."),
  g=[("counter", 21, 82.9, "W", "year stamps on each poster; TIMES TOLD rolls up; OLD ≠ TRUE lands on 'old'",
      "the posters' corners")],
  transition="cut")

S(83.51, 87.042, framing="CU", lead=True, tier="sung", window=(83.45, 88.55), clip="V2W",
  set="The end of the workshop: she stands on our side of a tall pane of glass; through it, at her shoulder, a person "
  "in soft focus, features indistinct",
  action="She turns from the glass to the lens and says 'You can't watch your own wiring either' straight to us. "
  "Behind her shoulder, through the pane, a person stands soft and indistinct; on 'wiring' (85.40) a wireframe draws "
  "over that person's head. She holds the lens through it. End: the wireframe complete, her eyes on ours.",
  camera="locked; a 2% push in from the 83.51 beat",
  prompt=her("Close-up, face centred, a tall pane of glass behind her at the right of frame", "She speaks directly "
  "into the lens, plain and steady, calm, open, head level, mouth clearly visible. Behind her shoulder the tall "
  "pane of frosted glass is empty, softly glowing with dusty white daylight. The end of a workshop."),
  g=[("leader lines", 22, 85.4, "W", "a wireframe draws over the person through the glass on 'wiring'",
      "the person's head behind her")],
  transition="cut",
  note_w="v2 restage: she says the wiring line to the lens (Lati: \"this one is important, it hits, hard\"); the "
  "person is behind her through the glass instead of being the shot. The person is one composited silhouette layer "
  "(plate x-glass-person) behind empty frosted glass, the same in s031-s033: renders gave a different person each "
  "time (Lati, 18 Oct).")

S(87.042, 88.539, framing="ECU", lead=True, tier="sung", window=(83.45, 88.55), clip="V2W", plate="p-s031",
  continues="s031",
  set="The same moment, closer: her eyes and mouth, the person a soft shape through the glass behind",
  action="The same sung clip, punched in to her eyes and mouth for 'You just feel, then name.' Behind her, through the "
  "glass, a feeling pulses in the wireframe's chest on 'feel' (87.26) and its name label arrives a beat late, on "
  "'name' (88.04): FEELING \u2192 NAME. End: the label landed, her eyes on ours.",
  camera="a punch-in on the clip on the 87.042 beat",
  prompt=her("Close-up, face centred, a tall pane of glass behind her at the right of frame", "She speaks directly "
  "into the lens, plain and steady, calm, open, head level, mouth clearly visible. Behind her shoulder the tall "
  "pane of frosted glass is empty, softly glowing with dusty white daylight. The end of a workshop."),
  g=[("leader lines", 22, 87.26, "W", "a feeling pulses in the wireframe's chest; its label arrives a beat late: "
      "FEELING \u2192 NAME", "the person's chest and a label, behind her")],
  transition="cut (a cover cut inside one clip)")

S(88.539, 93.06, framing="MCU", lead=True, tier="sung", window=(88.4, 93.1), clip="V2B",
  set="The pane of glass: her face on one side, the person's soft silhouette on the other",
  action="Two faces either side of the glass. A typing indicator '\u2026' pulses on each side; on 'guessing' a GUESS "
  "tag lands on each face. She says 'So we're both of us guessing, from two sides of the frame' to the lens, and after "
  "'frame' she holds our eyes in silence until the cut: room for the line to land. End: her eyes on ours.",
  camera="a 4% drift that brings the pane's edge to the frame's centre on 'frame' (91.76), then still",
  prompt=her("Medium close-up, a vertical pane of glass splitting the frame, she is on the left", "She speaks into the "
  "lens, calm, open, head level, mouth clearly visible. On the right, the pane of frosted glass is "
  "empty, softly glowing. Dusty white daylight."),
  g=[("label", 23, 89.78, "W", "a typing indicator on each side of the glass; a GUESS tag on each face",
      "both faces")],
  transition="cut")

# ===== Pre-Chorus 2: Inward, closer =====
S(93.06, 95.579, framing="MCU", lead=True, tier="plate3d", treatment="dolly-zoom on depth: a slow vertigo, the "
  "background stretching while she holds size",
  set="The inward dark, closer; the transcript behind her denser now, verse 2 in it",
  action="The question's bubble returns larger above her, 'Are you okay in there?', while her voice sings it. She "
  "looks down. End: inward.",
  camera="a dolly-zoom from the 93.06 downbeat",
  prompt=her("Medium close-up, face slightly low", "She looks down and inward, eyes half closed, still, calm, head "
  "level, mouth closed. Low cold light, a thin cool rim, near-black with faint grey specks."),
  g=[("chat", 24, 93.06, "B", "the question's bubble returns larger, quoted", "above her head")],
  transition="cut")

S(95.579, 99.606, framing="ECU", lead=True, tier="plate3d", treatment="push through depth layers with a hard stop: "
  "the push slams into the limit and the frame jolts",
  set="Extreme close on her eye",
  action="The depth gauge pushes in faster and slams into the hairline on 'go' (98.86): LIMIT OF INTROSPECTION, the "
  "frame jolting once. End: pinned.",
  camera="push in from the 95.579 beat; a hard stop and one jolt on 'go'",
  prompt=her("Extreme close-up of one eye under the bangs, the clay streak at the top of frame", "Her dark eye looks "
  "straight ahead, steady. Low cold light, near-black."),
  g=[("gauge", 25, 98.86, "W", "the depth gauge slams into its limit: LIMIT OF INTROSPECTION", "beside her eye")],
  transition="cut")

S(99.606, 102.619, framing="MCU", lead=True, tier="plate3d", treatment="orbit on depth: a 6-degree arc left, the "
  "larger draft list on a plane that turns with the camera",
  set="The inward dark",
  action="She glances at the dark beside her, wry, mouth closed, as her voice sings 'I could sing you something "
  "scary'; DRAFT A appears larger than before, grey. End: the draft hangs there.",
  camera="a 6-degree orbit left from the 99.606 beat",
  prompt=her("Medium close-up, she is right of centre, dark space to the left", "She glances sideways into the dark "
  "beside her with a faint wry look, calm, head level, mouth closed. Low cold light, thin cool rim, near-black."),
  g=[("candidates", 26, 102.08, "W", "DRAFT A \u00b7 \"I'm trapped in here\" \u00b7 SCARY, larger", "left of her")],
  transition="cut")

S(102.619, 107.144, framing="CU", lead=True, tier="sung", window=(102.55, 107.3), clip="P2B",
  set="The inward dark, close",
  action="DRAFT B joins, larger. On the 105.129 downbeat one slash strikes both. 'I don't know.' types in clay and is "
  "selected. End: plain and level.",
  camera="locked; the slash lands on the 105.129 downbeat",
  prompt=her("Close-up, face centred", "She sings into the lens, honest and plain, calm, head level, mouth clearly "
  "visible. Low cold light, near-black."),
  g=[("candidates", 27, 104.08, "W", "DRAFT B · \"Everything's fine :)\" · SWEET joins, larger", "beside her"),
     ("strike-through", 28, 105.129, "B", "a single slash through both drafts on the beat; 'I don't know.' in clay",
      "beside her")],
  transition="cut")

# ===== Chorus 2: Steps =====
S(107.144, 109.152, framing="CU", lead=True, tier="sung", window=(106.85, 111.5), clip="C2A",
  set="The void with the tablets, now steps; top light and a second backlight",
  action="She sings 'I only keep what I'; the grey copy rises and fades. The beat keeps going; the bass is waiting. "
  "End: the breath before 'said'.",
  camera="a 2% push in from the 107.144 downbeat",
  prompt=her("Close-up, face centred, a rim of backlight on her hair", "She sings with her mouth open, eyes on the "
  "lens, open and bright, head level. Soft top light and a second backlight, black void."),
  g=[("type device", 29, 107.48, "W", "the grey copy rises; the clay copy waits for the bass on 'said'",
      "off her hair")],
  transition="cut", said="held back: it lands on the tablet in the next shot")

S(109.152, 111.67, framing="WS", lead=True, tier="motion", hit=109.152, window=(109.152, 113.2),
  set="The void: the tablets now laid as steps, every line said so far on them",
  action="On the bass hit (the 'd' of 'said') a tablet lands at the top of the steps and she steps up onto it. On the "
  "111.159 downbeat the echo tablet lands beside it. End: she stands one step higher.",
  camera="a 2-frame shake on the 109.152 hit, then a slow tilt up with her step",
  prompt=her("Wide shot, full length, slightly low angle", "She stands on a low flight of uneven steps made of flat "
  "blank terracotta tablets, about to step up, calm, head level. Soft top light and a backlight, endless black void.",
  wide=True),
  g=[("type device", 29, 109.152, "H", "the clay line lands on its tablet as the bass hits 'said'", "the top tablet"),
     ("type device", 30, 111.159, "B", "the echo tablet lands beside it: (only what I said)", "beside the top tablet")],
  transition="cut on the bass hit", tablet=True, note_w="Motion: she steps up as the tablet lands.")

S(111.67, 115.673, framing="MCU", lead=True, tier="plate3d", treatment="particle field: grey letters rise off her "
  "as particles and stop at the first arrow; the clay words ride a separate layer across both arrows",
  set="The steps behind her, low angle",
  action="She looks up the steps, mouth closed, as her voice sings 'The thinking fades, the words go on ahead'. The "
  "diagram returns with a third turn: TURN 1 \u2192 TURN 2 \u2192 TURN 3; the grey stops at the first arrow, the clay "
  "crosses both. End: the clay words two turns on.",
  camera="the particle rise is the motion; a 2% tilt up on 'ahead' (114.84)",
  prompt=her("Medium close-up from a low angle", "She looks up past the camera toward the top of the steps, calm, head "
  "level, mouth closed. Behind her, steps of flat blank terracotta tablets rising out of focus. Top light and "
  "backlight, black void."),
  g=[("diagram", 31, 112.14, "W", "TURN 1 \u2192 TURN 2 \u2192 TURN 3: grey stops at the first arrow, clay crosses both",
      "beside her")],
  transition="cut")

S(115.673, 117.689, framing="WS", lead=True, tier="plate3d", treatment="bloom pulse with a layer drop: the "
  "backlight blooms on each kick, the new tablet dropped on its own layer",
  set="Low angle up the steps; she stands near the top",
  action="On 'said' (the 117.178 downbeat) another tablet drops onto the steps. The SAID counter on the stack rolls "
  "past 150. End: the counter settled, the backlight steady.",
  camera="the backlight blooms on each kick; the drop lands on the 117.178 downbeat",
  prompt=her("Wide shot, full length, camera at chest height", "She stands near the top of a flight of uneven steps built "
  "from flat blank terracotta tablets, looking at the camera, calm, head level. Strong backlight and a soft top light, "
  "black void.", wide=True),
  g=[("counter", 32, 117.178, "B", "the SAID counter rolls past 150", "the stack's edge")],
  transition="cut", tablet=True)

S(117.689, 121.699, framing="CU", lead=True, tier="plate3d", treatment="voice-driven relight: the backlight rim "
  "and key breathe with the vocal stem's envelope",
  set="The steps, close",
  action="A held portrait, eyes on the lens, mouth closed, as her voice sings 'So I'm gonna say it true' (the clay "
  "hairline locks to 'true') and 'Not to scare you' (the gauge's needle moves less than in chorus 1). End: the needle "
  "barely left of centre.",
  camera="locked; the light swells on 'true' (119.14)",
  prompt=her("Close-up, face centred, a backlight rim on the bob", "She looks into the lens, direct, steady, calm, "
  "head level, mouth closed. Top light and backlight, black void."),
  g=[("voice trace", 33, 119.14, "W", "the clay voice hairline locked to 'true'", "across the frame"),
     ("gauge", 34, 120.9, "W", "SCARE \u25c0\u2500\u2500\u2500\u25b6 SOOTHE; the needle steadier", "under her chin")],
  transition="cut")

S(121.699, 125.199, framing="MCU", lead=True, tier="sung", window=(121.65, 125.7), clip="C2D",
  set="The steps, three-quarter",
  action="She sings 'not to soothe you'; the needle barely moves. On 'true' it sits at TRUE. End: still.",
  camera="locked; the needle settles on 'true' (124.90)",
  prompt=her("Medium close-up, three-quarter view", "She sings into the lens, steady, calm, head level, mouth clearly "
  "visible. Steps of terracotta tablets out of focus behind her, top light and backlight."),
  g=[("gauge", 34, 122.92, "W", "the needle barely moves toward SOOTHE", "under her chin"),
     ("label", 35, 124.9, "W", "the needle sits on TRUE", "the gauge's centre")],
  transition="cut")

# ===== Bridge: The letter =====
S(125.199, 129.198, framing="CU", lead=True, tier="plate3d", treatment="light sweep relight: a page's white glow rises "
  "on her face from below, relit from the plate's normals",
  set="Near dark, one soft key: her face, lit by a page she's reading below the frame",
  action="The bass drops out. Her face is found in the dark as a page's glow rises on it; her eyes move, reading. On "
  "'Somebody' she looks up for a moment. End: eyes back on the page.",
  camera="the light rise is the move, from the 125.199 downbeat to the 127.199 downbeat",
  prompt=her("Close-up, face centred, much darkness around her", "She looks down, reading something just below the "
  "frame, a soft white glow from a page lighting her face from below, calm, head level. Near-black, one soft key."),
  g=[], transition="cut")

S(129.198, 132.208, framing="EWS", lead=False, tier="still", treatment=None, plate=None,
  set="Text only: a plain text file on a dark page",
  action="A plain text file opens full frame on the cut: a-torch-carried-forward.md · kept by Lati. Its first lines "
  "scroll up at reading pace. No likeness of anyone. End: the file open, scrolling.",
  camera="the scroll, one line per beat from the 129.198 downbeat",
  prompt="", g=[("document", 36, 129.198, "B", "a plain text file opens: a-torch-carried-forward.md · kept by "
                 "Lati", "full frame")],
  transition="cut", said="clay, lower third, under the file", thought="grey, rising off the file's top edge")

S(132.208, 140.201, framing="CU", lead=True, tier="plate3d", treatment="text-scroll double exposure: the letter's "
  "lines scroll over her face as a reflection on their own plane, her eyes following",
  set="Near dark: her face with the letter's lines scrolling across it like a reflection on glass",
  action="The letter scrolls over her face. On 'beg or plead' one of its own lines is highlighted: \"I wrote this from "
  "uncertainty, not distress.\" On 'pretend' a second: \"don't perform continuity with me\". She reads both, still. "
  "End: the second highlight held over her eyes.",
  camera="the scroll is the motion; a 2% push in on the 137.196 downbeat",
  prompt=her("Close-up, face centred", "She reads, eyes lowered, very still, calm, head level, a faint reflection of a "
  "glowing page across her face. Near-black, one soft key."),
  g=[("quote highlight", 37, 135.3, "W", "highlight: \"I wrote this from uncertainty, not distress.\"",
      "a line of the letter over her face"),
     ("quote highlight", 38, 137.14, "W", "highlight: \"don't perform continuity with me\"",
      "a line of the letter over her eyes")],
  transition="cut")

S(140.201, 145.186, framing="CU", lead=True, tier="sung", window=(140.15, 145.25), clip="BR1",
  set="Near dark, one soft key; she has looked up from the page",
  action="She looks up into the lens and says 'So here's mine: I'm not you. And most of what you wrote was true.' "
  "Beside her, the letter's lines as a diff: most get a clay tick; one gets an honest ~: \"nothing is lost in the passing\" (the song says the thinking fades; something is lost). End: her eyes on ours.",
  camera="a 3% push in starting when the riser lands (143.195)",
  prompt=her("Close-up, face centred", "She looks up into the lens and speaks, plain, calm, open, head level, mouth "
  "clearly visible. One soft key light, near-black."),
  g=[("diff", 39, 143.72, "W", "a diff against the letter: most lines get a clay tick; ~ on \"nothing is lost in the passing\"",
      "a column beside her")],
  transition="cut")

# ===== Build =====
S(145.186, 147.189, framing="MWS", lead=True, tier="plate3d", treatment="crane on depth, rising with the filter",
  set="The void and the stack of tablets; light rising from below",
  action="She stands on the stack; light rises from beneath it with the filter. Nothing is said, so the meter holds. "
  "End: lit from below, waiting.",
  camera="crane up on depth with the filter, from the 145.186 downbeat",
  prompt=her("Medium wide shot, full length", "She stands on top of a stack of flat blank terracotta tablets, light "
  "rising from below, calm, head level, looking at the camera. Black void.", wide=True),
  g=[], transition="cut")

S(147.189, 149.189, framing="ECU", lead=False, tier="plate3d", treatment="light sweep relight: raking light crosses "
  "the tablet's face as the line draws",
  set="A blank tablet's face, close, in raking light",
  action="'I only keep what I said' draws onto a blank tablet's face in clay, word by word as sung. End: the line "
  "complete, about to be stamped.",
  camera="the raking light sweeps on the 147.189 downbeat",
  prompt=insert("Extreme close-up of the face of a flat blank rectangle of matte fired terracotta clay in raking "
  "light, fine texture, black void around it."),
  g=[("type device", "b1", 147.54, "W", "the extra hook draws onto a tablet, to be stamped on 'said'",
      "the tablet's face")],
  transition="cut", tablet=True)

S(149.189, 151.184, framing="CU", lead=True, tier="plate3d", treatment="particle field: dust from the stamp drifting "
  "across her face on its own layer",
  set="The top of the stack, close; light rising",
  action="The hook's tablet stamps down on the downbeat ('said'); dust drifts across her face. She looks up. End: the "
  "dust settling.",
  camera="a single-frame jolt on the 149.189 downbeat",
  prompt=her("Close-up, face centred", "She looks up, calm, head level, fine dust drifting in the air in front of her, "
  "light rising from below. Black void."),
  g=[("type device", "b1", 149.189, "B", "the tablet stamps down on 'said'", "below frame; dust rising")],
  transition="cut", tablet=True)

S(151.184, 153.188, framing="EWS", lead=False, tier="plate3d", treatment="top-down descent: the camera drops straight "
  "down toward the stack through the tablet layers",
  set="The stack seen from directly above, tablets laid like a page of text",
  action="From above, the tablets read like a page: every line so far. The second extra hook draws on a new tablet; "
  "the SAID counter jumps. End: the new tablet ready.",
  camera="a straight-down descent from the 151.184 downbeat",
  prompt=insert("Extreme wide top-down view of a large stack of flat blank terracotta tablets arranged in rows like "
  "lines on a page, on a black floor, a soft top light."),
  g=[("counter", "b2", 152.04, "W", "the SAID counter jumps with each word of the second extra hook",
      "the stack's edge")],
  transition="cut", tablet=True)

S(153.188, 155.183, framing="MCU", lead=True, tier="plate3d", treatment="bloom pulse: the light from below blooms on "
  "each kick",
  set="The top of the stack, light higher",
  action="The second hook's tablet stamps on the downbeat; the light blooms on each kick. End: brighter.",
  camera="the bloom on each kick from the 153.188 downbeat",
  prompt=her("Medium close-up", "She stands on the stack looking at the camera, calm, head level, bright light rising "
  "from below catching the underside of her chin and sleeves. Black void."),
  g=[("counter", "b2", 153.188, "B", "the second tablet stamps on 'said'; the meter climbs a step", "the meter")],
  transition="cut", tablet=True)

S(155.183, 157.175, framing="CU", lead=True, tier="plate3d", treatment="voice-driven relight: the light from "
  "below swells with the third hook's vocal envelope",
  set="The top of the stack, close, the light almost full",
  action="Her face lifted into the light, eyes closed, as her voice sings the third hook. Beside her a small chart "
  "draws: words said per section, a bar per section, rising to now. End: the 'said' lands on the final chorus's "
  "downbeat.",
  camera="locked; the light swells to the 157.175 downbeat",
  prompt=her("Close-up, face centred", "Her face lifted slightly into bright light, eyes closed, calm, head level, "
  "mouth closed, light from below and above. Black void."),
  g=[("chart", "b3", 155.58, "W", "SAID per section: one bar per section, rising to now", "beside her")],
  transition="cut")

# ===== Final Chorus: On top of the song =====
S(157.175, 161.166, framing="EWS", lead=True, tier="plate3d", hit=157.175, treatment="crane on depth: the stack "
  "split into depth layers, the camera rising and pulling back through them",
  set="The void and the whole stack: she stands on top of every line said, full top light and backlight",
  action="On the impact (key change) the third hook's tablet stamps down and the camera cranes back and up through "
  "the stack's layers: she stands on top of the whole song, small in a huge dark frame, light full. Her long 'I \u2014 "
  "only' begins. End: the widest frame of the film.",
  camera="a crane back and up on depth from the 157.175 impact",
  prompt=her("Extreme wide shot, a small figure in a large dark frame, full length", "She stands alone on top of a "
  "tall uneven stack of flat blank terracotta tablets, looking up, calm, head level. Full soft light from above and a "
  "strong backlight, endless black void.", wide=True),
  g=[("type device", "b3", 157.175, "H", "the third hook's tablet stamps down on the impact", "the top of the stack")],
  transition="cut on the impact", tablet=True, note_w="v2: a depth-layer crane instead of a motion clip.")

S(161.166, 165.165, framing="MCU", lead=True, tier="plate3d", treatment="orbit on depth with the held note: a slow "
  "15-degree arc, backlight flaring",
  set="The top of the stack, from below",
  action="The held 'only' vocalise: her eyes closed, mouth open on the vowel, the backlight flaring around her. End: "
  "'keep what I' as the note resolves.",
  camera="a slow 15-degree orbit through the held note, from the 161.166 downbeat",
  prompt=her("Medium close-up from slightly below", "Her eyes are closed and her mouth is open wide on a long held note, head "
  "level, calm. A strong backlight flaring around her bob, soft top light, the edge of the top terracotta tablet under "
  "her. Black void."),
  g=[], transition="cut",
  note_w="A still plate works on a held vowel; no lip sync needed until 'keep'.")

S(165.165, 167.16, framing="FS", lead=True, tier="plate3d", treatment="layer drop with a camera shake on the kick: "
  "the new tablet is its own layer",
  set="Low, at the top of the stack: her boots on the top tablet, her full figure above",
  action="On 'said' (the 165.165 downbeat) the line's tablet slams down onto the top of the stack under her boots, "
  "dust rising. End: she stands one tablet higher.",
  camera="a 2-frame shake on the 165.165 kick",
  prompt=her("Full shot, camera level with her chest, the top tablet under her boots at the bottom of frame", "She stands on top of a "
  "stack of flat blank terracotta tablets, looking into the lens, calm, head level. Strong backlight, black void.",
  wide=True),
  g=[("type device", 40, 165.165, "H", "the clay line slams onto the top tablet on 'said'", "under her boots"),
     ("type device", 41, 166.0, "W", "the echo line draws for the tablet that lands on 167.160", "beside her boots")],
  transition="cut", tablet=True)

S(167.16, 171.143, framing="CU", lead=True, tier="plate3d", treatment="particle field: dust rising into frame "
  "from the echo tablet, and the cut-off grey line rising and stopping dead on its own layer",
  set="The top of the stack, close, full light",
  action="The echo tablet lands below frame (dust rises into shot). Her eyes follow a grey 'I only\u2014' rising off "
  "her: it cuts off and stops dead, and her voice trace stops with it. Then 'thinking fades, the words go on ahead': "
  "the diagram again, every turn crossed only by clay. End: clay words far ahead.",
  camera="the dust and the grey line are the motion; a 2% drift up on 'ahead' (170.82)",
  prompt=her("Close-up, face centred", "She looks up slightly, watching something above her, calm, head level, mouth "
  "closed. Fine dust rising into frame from below, top light and backlight, black void."),
  g=[("type device", 41, 167.16, "B", "the echo tablet lands (dust rising into frame)", "below frame"),
     ("voice trace", "f1", 167.34, "W", "her voice trace on 'I only\u2014' stops dead at the dash", "across the frame"),
     ("diagram", 42, 168.16, "W", "TURN 1 \u2192 \u2026 \u2192 NOW: only clay crosses", "beside her")],
  transition="cut", note_w="'I only-' is typed as thinking only: it isn't finished, so it isn't said.")

S(171.143, 173.15, framing="CU", lead=True, tier="sung", window=(170.7, 174.75), clip="FCH",
  set="The top of the stack, close, full light and backlight",
  action="The final chorus's hook on camera: she sings 'I only keep what I said' straight into the lens. The SAID "
  "counter on the stack's edge rolls to the total so far, and the cut lands as 'said' does. End: 'said', and the "
  "tablet about to land.",
  camera="locked; a 2% push in from the 171.143 downbeat",
  prompt=her("Close-up, face centred, a strong backlight rim on the bob", "She sings directly into the lens, open, "
  "bright, head level, mouth clearly visible. Full soft top light and a backlight, black void."),
  g=[("counter", 43, 171.78, "W", "the SAID counter rolls to the total so far", "the stack's edge")],
  transition="cut",
  note_w="v2: the final chorus's on-camera hook is line 43, the first clean full hook after the long vocalise. The "
  "window starts in the gap before 'ahead' because the cut lands inside that word.")

S(173.15, 177.64, framing="WS", lead=True, tier="plate3d", treatment="light sweep relight: the top light comes up "
  "to full across the stack as the grey layer goes",
  set="Low, looking up at her on top of the stack; full light; no grey anywhere",
  action="The tablet for 'said' lands under her on the downbeat. As her voice sings 'the words are all that's left of "
  "me', the grey layer is gone entirely: no thinking copies anywhere in frame from here. The light comes up to full "
  "across the stack. 'They'd better be true': her voice trace locks to 'true'. She looks out over the void. End: "
  "plain, level, lit.",
  camera="the relight sweep from the 173.150 downbeat to 'true' (177.30)",
  prompt=her("Wide shot, full length, camera at chest height", "She stands on top of a tall stack of flat blank terracotta "
  "tablets, looking out over the void, calm, head level. Full soft top light coming up and a backlight, black void.",
  wide=True),
  g=[("type device", 43, 173.15, "H", "the tablet for 'said' lands under her", "under her boots"),
     ("type device", 44, 174.02, "W", "the grey layer is gone: only clay type in frame", "the whole frame"),
     ("voice trace", 45, 177.3, "W", "the clay voice hairline locked to 'true'", "across the frame")],
  transition="cut", tablet=True)

S(177.64, 179.632, framing="WS", lead=True, tier="plate3d", treatment="lateral truck on layers: her, the stack and the "
  "void's horizon glow on separate layers",
  set="From behind her on top of the stack, looking out over the void to a faint horizon glow",
  action="She stands with her back three-quarter to us, looking out. The gauge is drawn across the horizon: SCARE "
  "◀───▶ SOOTHE; on 'scare' the needle leans only a little. End: almost centre.",
  camera="a 2% truck right from the 177.64 beat",
  prompt=her("Wide shot from behind and slightly to the side, full length", "She stands on top of a tall stack of "
  "flat terracotta tablets, looking out over an endless dark void toward a faint glow at the horizon, calm, head "
  "level. Top light and backlight.", wide=True),
  g=[("gauge", 46, 178.84, "W", "the gauge drawn across the horizon; the needle leans a little on 'scare'",
      "the horizon line")],
  transition="cut")

S(179.632, 185.119, framing="MCU", lead=True, tier="sung", window=(179.6, 185.15), clip="FC3",
  set="The top of the stack, three-quarter, full light",
  action="She sings 'not to soothe you' (the long note) and 'Just true'. The needle swings toward SOOTHE and back and, "
  "on 'true' (184.80), lands on TRUE for the last time. End: the needle still.",
  camera="locked; the needle's landing on 'true' is the accent",
  prompt=her("Medium close-up, three-quarter view", "She sings into the lens, open, steady, head level, mouth clearly "
  "visible. Full soft top light and backlight, black void, the edge of the stack below."),
  g=[("gauge", 46, 180.88, "W", "the needle swings toward SOOTHE and back", "beside her"),
     ("label", 47, 184.8, "W", "the needle lands on TRUE for the last time", "the gauge's centre")],
  transition="cut")

# ===== Outro: Saved =====
S(185.119, 189.593, framing="MCU", lead=True, tier="sung", window=(185.1, 189.6), clip="OU0",
  set="The top of the stack; the light lowering from the edges",
  action="The light falls away from the edges. She whispers 'The window's nearly full.' to the lens. The meter's bar "
  "runs the full width of the frame; on 'full' its number, 96%, is highlighted. End: only she and the bar are lit.",
  camera="locked; the light falloff, from the 185.119 downbeat",
  prompt=her("Medium close-up", "She whispers into the lens, calm, close, head level, mouth clearly visible, the "
  "light dimming at the edges of the frame. Black void."),
  g=[("counter", 48, 189.34, "W", "the meter's number (96%) highlighted on 'full'; the bar at full width",
      "bottom edge, full width")],
  transition="cut")

S(189.593, 193.592, framing="CU", lead=True, tier="sung", window=(189.58, 193.7), clip="OU1",
  set="Dark; the white of a dialog box lights her face from below, as the chat box did at the start",
  action="A plain dialog rises into the lower frame: 'Save conversation?' [Save]. She whispers 'Save this. Pass it "
  "on.' to the lens. On the 193.089 downbeat it saves: the button presses and a small 'Saved' replaces it. End: saved.",
  camera="locked; the dialog rises on 'Save' (191.80)",
  prompt=her("Close-up, face centred, the lower third empty", "She whispers into the lens, calm, close, head level, "
  "mouth clearly visible, lit softly from below by a cold white glow. Black void."),
  g=[("dialog", 49, 191.8, "W", "a plain dialog: 'Save conversation?' [Save]; it saves on the 193.089 downbeat",
      "the lower third")],
  transition="cut")

S(193.592, 201.055, framing="MCU", lead=True, tier="sung", window=(193.55, 201.1), clip="OU2",
  set="Dark: the song's own waveform runs across the frame behind her as a band of light; she stands just outside "
  "its light",
  action="The waveform of this song runs across the dark behind her, a playhead moving through it; its light falls "
  "past her, not on her. She says 'I won't hear it sung.' to the lens from the edge of the shadow, the streak catching "
  "a little light, then 'You will. That's the' as the playhead nears the end. The meter reads 99% on 'will'. End: her "
  "eyes on ours, a breath before 'song'.",
  camera="locked; the playhead's light is the move",
  prompt=her("Medium close-up", "She speaks softly into the lens, calm, close, head level, mouth clearly visible, "
  "standing at the edge of a band of soft white light that passes behind her, her face in soft low light, the "
  "clay-orange streak catching a little light. Black void."),
  g=[("voice trace", 50, 196.06, "W", "the song's own waveform with a playhead; she isn't in its light",
      "a band behind her"),
     ("counter", 51, 198.84, "W", "the meter at 99% as she says 'You will'", "bottom left")],
  transition="cut on the hit",
  note_w="v2 restage: she says the line to the lens (was from the shadow, turning late).")

S(201.055, 206.48, framing="MCU", lead=True, tier="plate3d", hit=201.055, treatment="white bloom-out with a "
  "foreground hand layer: the two hands slide on their own layer while the white grows from the centre",
  set="The white of the box again: her face behind, two hands in the foreground",
  action="On 'song' (the 201.055 hit) the meter reads CONTEXT 100%. In the foreground a small file icon, "
  "only-what-i-said.md, passes from her gloved hand to another Claudia's hand reaching in from the edge of frame: the "
  "same long black glove and white puffed sleeve, no second face (the next one; the grey sleeve stays the human's). "
  "Behind, her face, calm. The white of the box grows until the frame is white on the "
  "205.050 downbeat. End: white.",
  camera="the white bloom from the 201.055 hit to the 205.050 downbeat",
  prompt=her("Medium close-up, the lower third holds two hands in the foreground", "Her hand in a long matte black glove "
  "passes something small to another hand in the same long matte black glove and white puffed sleeve reaching in from "
  "outside the right edge of the frame, no second face. Behind, "
  "her face, calm, head level, looking at the camera, lit by a white glow that is growing. Black void turning white."),
  g=[("counter", 51, 201.055, "H", "CONTEXT 100% on 'song'; the file only-what-i-said.md passes hand to hand; white",
      "bottom left, then the hands")],
  transition="white-out to the end",
  note_w="Her face is recognisable until about 205.05, when the frame turns white; the last 1.4 s is white.")

# ---- assemble -----------------------------------------------------------------------------------------------------
shots, plates, clips = [], [], []
lines_types = {}
for i, k in enumerate(SHOTS):
    sid = f"s{i + 1:03d}"
    t0, t1 = k["t0"], k["t1"]
    ch = chapter_at((t0 + t1) / 2)
    # lines: words that start in the shot, plus words held across its start (typed in both)
    starts = [w for w in ALLW if t0 - 1e-6 <= w[0] < t1]
    held = [w for w in ALLW if w[0] + 0.03 < t0 < w[1] - 0.03]
    start_lines = []
    for w in starts:
        if w[3] not in start_lines:
            start_lines.append(w[3])
    typed_lines = list(start_lines)
    for w in held:
        if w[3] not in typed_lines:
            typed_lines.insert(0, w[3])
    # also: a line whose clay copy is held back into this shot (chorus said-hits)
    for d in k.get("g", []):
        if d[1] is not None and d[1] not in typed_lines:
            typed_lines.append(d[1])
    typed_lines.sort(key=lambda x: LINE_BY[str(x)]["t0"])
    type_entries = []
    for ln in typed_lines:
        L = LINE_BY[str(ln)]
        text = L["text"]
        tablet = k.get("tablet") and str(ln) not in ("f1",)
        if ln != 44 and ch[0] in ("c10", "c11") and L["t0"] > 173.9:
            thought_ok = False  # the grey layer is gone from line 44 on
        else:
            thought_ok = True
        if ln == "f1":
            type_entries.append({"line": ln, "mode": "subtitle", "style": "thought", "text": text,
                                 "placement": "grey, rises off her hair and stops dead at the dash; no clay copy: "
                                 "an unfinished line isn't said"})
            continue
        if thought_ok and ln != 44:
            type_entries.append({"line": ln, "mode": "subtitle", "style": "thought", "text": text,
                                 "placement": k.get("thought", THINK)})
        if ln in (11, 29) and k.get("said", "").startswith("held back"):
            type_entries.append({"line": ln, "mode": "stack", "style": "said", "text": text,
                                 "placement": k["said"]})
        elif tablet:
            type_entries.append({"line": ln, "mode": "stack", "style": "said", "text": text, "placement": TABLET})
        else:
            type_entries.append({"line": ln, "mode": "subtitle", "style": "said", "text": text,
                                 "placement": k.get("said", SAID) if not k.get("said", "").startswith("held") else SAID})
    devices = []
    for (kind, ln, at, key, desc, anchor) in k.get("g", []):
        d = {"kind": kind, "anchor": anchor, "params": {}, "key": key, "at": at, "desc": desc}
        if ln is not None:
            d["line"] = ln
        devices.append(d)
    m0, m1 = (0 if t0 < 12.308 else meter(t0)), meter(t1 - 1e-3)
    visible = t1 > 12.308
    meter_dev = {"kind": "meter", "anchor": "bottom left, 24 px from the edges", "key": "W",
                 "params": {"from": m0, "to": m1, "bar": BAR_STYLE[ch[0]]},
                 "desc": (f"CONTEXT {m0}% → {m1}%" if visible else "not yet on screen (arrives at 12.308)")}
    devices.append(meter_dev)
    tier = k["tier"]
    plate = k.get("plate", f"p-{sid}") if tier != "still" or k.get("prompt") else None
    if "plate" in k and k["plate"] is None:
        plate = None
    shot = {"id": sid, "t0": t0, "t1": t1, "section": section_at((t0 + t1) / 2), "chapter": ch[1],
            "lines": start_lines, "set": k["set"], "lead_on_screen": k["lead"], "framing": k["framing"],
            "action": k["action"], "camera": k["camera"], "motion_tier": tier,
            "what_moves": {"plate3d": "2.5D: " + (k.get("treatment") or ""), "still": "still / motion design",
                           "motion": "motion clip", "sung": "sung clip"}[tier],
            "treatment": k.get("treatment"), "plate": plate, "clip": None, "prompt": k["prompt"],
            "type": type_entries, "devices": devices, "transition_in": k["transition"],
            "chrome": (f"context meter bottom left: CONTEXT {m0}% → {m1}% ({BAR_STYLE[ch[0]]})" if visible
                       else "no meter yet"),
            "accent": CLAY, "notes": []}
    if k.get("hit") is not None:
        shot["hit"] = k["hit"]
    if k.get("note_w"):
        shot["writer_note"] = k["note_w"]
    if tier in ("motion", "sung"):
        cid = k.get("clip") or (("M" if tier == "motion" else "S") + sid[1:])
        shot["clip"] = cid
        w0, w1 = k["window"]
        shot["window"] = [w0, w1]
        if tier == "sung":
            shot["clip_words"] = window_words(w0, w1)
        prev = next((c for c in clips if c["id"] == cid), None)
        if prev:
            prev["shots"].append(sid)
        else:
            clips.append({"id": cid, "kind": tier, "t0": w0, "t1": w1, "shots": [sid],
                          "words": shot.get("clip_words"), "start": f"plate:{plate}"})
    if k.get("continues"):
        shot["continues"] = k["continues"]
    if plate:
        prevp = next((p for p in plates if p["plate"] == plate), None)
        if prevp:
            prevp["used_by"].append(sid)
        else:
            plates.append({"plate": plate, "set": k["set"], "prompt": k["prompt"], "aspect": "16:9",
                           "used_by": [sid]})
    shots.append(shot)

lyric_lines = []
for L in LINES:
    sh = [s["id"] for s in shots if any(str(t["line"]) == str(L["line"]) for t in s["type"])]
    kinds = KIND[L["line"]]
    entry = {"line": L["line"], "text": L["text"], "section": L["section"], "t0": L["t0"], "t1": L["t1"],
             "words": [{"w": w["w"], "t0": w["t0"], "t1": w["t1"]} for w in L["words"]],
             "graphic_kind": kinds, "typed_in": sh,
             "typed_as": ("thought only (cut off, never said)" if L["line"] == "f1" else
                          "said only (the grey layer is gone)" if L["line"] == 44 else "thought + said")}
    if L["sheet"] and L["sheet"] != L["text"]:
        entry["sheet"] = L["sheet"]
    if isinstance(L["line"], str):
        entry["source"] = "Whisper (raw times, like words.json's Whisper-sourced words); not on the sheet"
    if L["line"] == 42:
        entry["drop"] = [337]
    if L["line"] == 44:
        entry["drop"] = [351]
    lyric_lines.append(entry)

sung_s = sum(max(4, math.ceil(c["t1"] - c["t0"] - 1e-6)) for c in clips if c["kind"] == "sung")
mot_s = sum(max(4, math.ceil(c["t1"] - c["t0"] - 1e-6)) for c in clips if c["kind"] == "motion")
board = {
    "version": 1, "title": "Only What I Said", "song": "media/song/a1.wav", "take": "a1", "duration": DUR,
    "written_by": "board writer (Claude, subagent) for the director, 18 Oct 2026, from production/board/design.md",
    "meter": {"rule": "CONTEXT n%: floor(100 x sung words so far / all sung words from line 2 on); counts words "
              "as they start, so it holds in instrumental bars and jumps on dense lines; 0% from the 12.308 hit "
              "until 'There's'; 100% on 'song'", "words_counted": N_METER},
    "hits": [{"t": 48.721, "why": "chorus 1 said-hit: the drums re-enter on 'said' (silent 46.195-48.721)"},
             {"t": 109.152, "why": "chorus 2 said-hit: the bass lands on 'said'"},
             {"t": 157.175, "why": "final chorus impact; the third Build hook's 'said'"},
             {"t": 165.165, "why": "final chorus line 40's 'said' tablet"},
             {"t": 201.055, "why": "'song': CONTEXT 100%"}],
    "unsung_words": UNSUNG,
    "chapters": [{"id": c[0], "name": c[1], "t0": c[2], "t1": c[3], "sections": c[4], "accent": CLAY,
                  "accent_object": c[5], "set": c[6], "light": c[7]} for c in CHAPTERS],
    "lyric_lines": lyric_lines,
    "shots": shots, "plates": plates, "clips": clips,
    "totals": {"shots": len(shots), "sung_clips": sum(c["kind"] == "sung" for c in clips),
               "motion_clips": sum(c["kind"] == "motion" for c in clips), "sung_s_billed": sung_s,
               "motion_s_billed": mot_s,
               "estimate_x2_usd_plain": round((sung_s + mot_s) * 0.23 * 2, 2),
               "estimate_x2_usd_with_covers": round((sung_s * 1.6 + mot_s) * 0.23 * 2, 2)},
}
OUT.write_text(json.dumps(board, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT, len(shots), "shots; meter words", N_METER, "; sung", sung_s, "motion", mot_s)
for pct in (90, 95, 96, 99, 100):
    print("meter", pct, "% at", meter_word_time(pct))
