"""Graphics for pre-chorus 2 (s034-s038), drawn by gfx.layer: pre-chorus 1 again, escalated (board/design.md: "the
gauge hits its limit harder; the drafts are larger; the strike-through is a single slash on the beat")."""

from gfx import QUESTION, bubble, face, ramp
import gfx_p1

# s035: she knows where the limit is now: LIMIT OF INTROSPECTION is printed there from the start, and the marker
# slams into it so hard the gauge jolts
G2 = dict(sid="s035", line=25, on=95.65, go=98.86, hard=1.0, known=True)

# s036-s038: the drafts, larger; one slash through both on the beat; the answer typed into the third slot
D2 = dict(drafts=[("DRAFT A", "“I’m trapped in here”", "SCARY", 102.08, None),
                  ("DRAFT B", "“Everything’s fine :)”", "SWEET", 104.08, None)],
          row=(240, 440), gap=68, answer_y=660, line=28, true_one=105.46, select=107.10, gone=(108.30, 108.65),
          lab_px=26, txt_px=50, ans_px=54, slash=105.129)


def layer(c, t, sid):
    if sid == "s034":  # "You asked if I'm okay in there": the question returns, larger, beside her bowed head
        f = face(sid, 93.1)
        x = 470 if not f else round(f["bbox"][0] - 340)
        bubble(c, x, 170, QUESTION, 46, alpha=ramp(t, 93.06, 93.36))
    elif sid == "s035":
        gfx_p1.gauge(c, t, G2)
    else:
        gfx_p1.drafts(c, t, D2)
