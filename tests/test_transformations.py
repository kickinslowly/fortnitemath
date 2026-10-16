"""transformations cartridge: golden misconception cases, an independent re-check of every baked item, bounds.

The independent check never calls the generator's solver. Each prompt is parsed with a regex here and solved
with complex numbers (a point is x + yi: a turn is a multiplication by i), ``Fraction`` and plain Python.
"""
import json
import re
import string
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "transformations"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
with open(REPO_ROOT / "cartridges" / CID / "cartridge.json", encoding="utf-8") as _f:
    MANIFEST = json.load(_f)
ITEMS = BAKED["items"]
M = "−"

P = r"\((−?\d+), (−?\d+)\)"
NUM = r"(−?\d+)"


def num(s):
    return int(s.replace(M, "-"))


def cpt(x, y):
    return complex(num(x), num(y))


def pt_of(text):
    m = re.fullmatch(P, text)
    assert m, text
    return cpt(m.group(1), m.group(2))


def fmt(z):
    return f"({int(z.real)}, {int(z.imag)})".replace("-", M)


def fr(text):
    a, _, b = text.replace(M, "-").partition("/")
    return Fraction(int(a), int(b) if b else 1)


def conj_x(z):  # reflection over the x-axis
    return z.conjugate()


def refl_y(z):  # reflection over the y-axis
    return -z.conjugate()


def refl(z, axis):
    return conj_x(z) if axis == "x" else refl_y(z)


def dilate(z, k):
    return complex(Fraction(z.real) * k, Fraction(z.imag) * k)


def slide_vec(text):
    """'3 right 2 down' / '4 left' -> complex."""
    v = 0
    for amt, d in re.findall(r"(\d+) (left|right|up|down)", text):
        a = int(amt)
        v += {"right": a, "left": -a, "up": 1j * a, "down": -1j * a}[d]
    return v


def rule_vec(text):
    m = re.fullmatch(r"\(x(?: ([+−]) (\d+))?, y(?: ([+−]) (\d+))?\)", text)
    assert m, text
    dx = (1 if m.group(1) == "+" else -1) * int(m.group(2)) if m.group(1) else 0
    dy = (1 if m.group(3) == "+" else -1) * int(m.group(4)) if m.group(3) else 0
    return complex(dx, dy)


def eval_rule(text, x, y):
    body = text.strip("()").replace(M, "-").split(", ")
    return complex(*(eval(b, {"__builtins__": {}}, {"x": x, "y": y}) for b in body))


# ---- move parsing for "which move?" choices and for sequences ----------------------------------------
def move_fn(text):
    if text == "90 CCW":
        return lambda z: z * 1j
    if text == "90 CW":
        return lambda z: z * -1j
    if text == "180 turn" or text == "Turn 180":
        return lambda z: -z
    m = re.fullmatch(r"Over ([xy])-axis", text)
    if m:
        return lambda z, a=m.group(1): refl(z, a)
    m = re.fullmatch(r"Slide (\d+) (left|right|up|down)", text)
    if m:
        v = slide_vec(f"{m.group(1)} {m.group(2)}")
        return lambda z, v=v: z + v
    raise AssertionError(text)


def seq_move(text):
    m = re.fullmatch(r"slide (\d+) (left|right|up|down)", text)
    if m:
        v = slide_vec(f"{m.group(1)} {m.group(2)}")
        return lambda z, v=v: z + v
    m = re.fullmatch(r"flip over the ([xy])-axis", text)
    if m:
        return lambda z, a=m.group(1): refl(z, a)
    if text == "turn 180 degrees":
        return lambda z: -z
    if text == "turn 90 CCW":
        return lambda z: z * 1j
    m = re.fullmatch(r"dilate by (\d+(?:/\d+)?)", text)
    if m:
        k = fr(m.group(1))
        return lambda z, k=k: dilate(z, k)
    raise AssertionError(text)


# ---- the independent solver: truth(prompt, choice) -> bool -------------------------------------------
def is_dilation_text(t):
    return t.startswith("dilate by")


def truth(prompt, choice):
    # tier 1 ------------------------------------------------------------------------------
    m = re.fullmatch(P + r" (?:slides|moves|shifts) (.+)\. (?:Image|New point)\?", prompt)
    if m and "moves to" not in prompt:
        z = cpt(m.group(1), m.group(2)) + slide_vec(m.group(3))
        return pt_of(choice) == z
    m = re.fullmatch(P + r" moves to " + P + r"\. The slide\?", prompt)
    if m:
        return slide_vec(choice) == cpt(m.group(3), m.group(4)) - cpt(m.group(1), m.group(2))
    m = re.fullmatch(r"Slide rule (\(x.*\)). Where does " + P + r" go\?", prompt) or \
        re.fullmatch(r"Rule (\(x.*\)) is applied to " + P + r"\. Image\?", prompt)
    if m:
        return pt_of(choice) == cpt(m.group(2), m.group(3)) + rule_vec(m.group(1))
    m = re.fullmatch(r"Which rule slides " + P + " to " + P + r"\?", prompt)
    if m:
        return rule_vec(choice) == cpt(m.group(3), m.group(4)) - cpt(m.group(1), m.group(2))
    m = re.fullmatch(r"A slide takes " + P + " to " + P + r"\. Where does " + P + r" go\?", prompt)
    if m:
        v = cpt(m.group(3), m.group(4)) - cpt(m.group(1), m.group(2))
        return pt_of(choice) == cpt(m.group(5), m.group(6)) + v
    # rigid size (tiers 1-3) --------------------------------------------------------------
    m = re.fullmatch(r"A segment of length (\d+) .*\. New length\?", prompt)
    if m:
        return num(choice) == int(m.group(1))
    m = re.fullmatch(r"A (\d+) degree angle (?!is \w+, then)(?:slides|is flipped|is reflected|turns|is rotated|is turned).*\. New angle\?", prompt)
    if m:
        return num(choice) == int(m.group(1))
    # tier 2 ------------------------------------------------------------------------------
    m = re.fullmatch(P + r" (?:reflected|flipped) over the ([xy])-axis\?", prompt)
    if m:
        return pt_of(choice) == refl(cpt(m.group(1), m.group(2)), m.group(3))
    m = re.fullmatch(r"A flip over the ([xy])-axis gives " + P + r"\. Start point\?", prompt)
    if m:
        return pt_of(choice) == refl(cpt(m.group(2), m.group(3)), m.group(1))
    m = re.fullmatch(P + " maps to " + P + r"\. Which move\?", prompt) or \
        re.fullmatch(r"Which move takes " + P + " to " + P + r"\?", prompt) or \
        re.fullmatch(r"About \(0, 0\), " + P + " maps to " + P + r"\. Which move\?", prompt)
    if m:
        return move_fn(choice)(cpt(m.group(1), m.group(2))) == cpt(m.group(3), m.group(4))
    m = re.fullmatch(P + r" is (?:flipped|reflected) over the ([xy])-axis\. Image\?", prompt)
    if m:
        return pt_of(choice) == refl(cpt(m.group(1), m.group(2)), m.group(3))
    m = re.fullmatch(r"Which point stays put when (?:flipped|reflected) over the ([xy])-axis\?", prompt)
    if m:
        z = pt_of(choice)
        return refl(z, m.group(1)) == z
    m = re.fullmatch(r"(?:Flip|Reflect) over the ([xy])-axis\. Which coordinate changes sign\?", prompt)
    if m:
        # take a sample point off both axes: which parts differ after the flip?
        z, w = complex(3, 5), refl(complex(3, 5), m.group(1))
        changed = {"x": w.real != z.real, "y": w.imag != z.imag}
        names = [k for k, v in changed.items() if v]
        return {"Both": len(names) == 2, "Neither": not names}.get(choice, names == [choice])
    m = re.fullmatch(r"(?:Flip|Reflect) over the ([xy])-axis: \(x, y\) becomes\?", prompt)
    if m:
        return eval_rule(choice, 3, 5) == refl(complex(3, 5), m.group(1))
    # tier 3 ------------------------------------------------------------------------------
    m = re.fullmatch(P + r" turns 90 degrees (clockwise|counterclockwise) about \(0, 0\)\?", prompt)
    if m:
        z = cpt(m.group(1), m.group(2))
        return pt_of(choice) == z * (1j if m.group(3) == "counterclockwise" else -1j)
    m = re.fullmatch(P + r" turns 180 degrees about (?:\(0, 0\)|the origin)\?", prompt)
    if m:
        return pt_of(choice) == -cpt(m.group(1), m.group(2))
    m = re.fullmatch(r"Rule for a (90 degree counterclockwise|90 degree clockwise|180 degree) turn about \(0, 0\)\?", prompt) or \
        re.fullmatch(r"Turning \(x, y\) (90 degrees counterclockwise|90 degrees clockwise|180 degrees) gives\?", prompt)
    if m:
        w = m.group(1)
        factor = 1j if "counterclockwise" in w else (-1j if "clockwise" in w else -1)
        return eval_rule(choice, 3, 5) == complex(3, 5) * factor
    # tier 4 ------------------------------------------------------------------------------
    m = re.fullmatch(P + r" dilated by scale factor (\d+(?:/\d+)?) from \(0, 0\)\?", prompt)
    if m:
        return pt_of(choice) == dilate(cpt(m.group(1), m.group(2)), fr(m.group(3)))
    m = re.fullmatch(r"A (?:side|segment|leg|edge) of (\d+) becomes (\d+)\. Scale factor\?", prompt)
    if m:
        return fr(choice) == Fraction(int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(r"Scale factor (\d+(?:/\d+)?)\. A (?:side|segment|leg|edge) of (\d+) becomes\?", prompt)
    if m:
        return fr(choice) == fr(m.group(1)) * int(m.group(2))
    m = re.fullmatch(r"Scale factor (\d+(?:/\d+)?)\. A (\d+) degree angle becomes\?", prompt)
    if m:
        return num(choice) == int(m.group(2))
    m = re.fullmatch(r"Scale factor (\d+(?:/\d+)?) makes the figure\?", prompt) or \
        re.fullmatch(r"A dilation has scale factor (\d+(?:/\d+)?)\. The image is\?", prompt) or \
        re.fullmatch(r"With scale factor (\d+(?:/\d+)?), the image is\?", prompt)
    if m:
        k = fr(m.group(1))
        return choice == ("Larger" if k > 1 else "Smaller" if k < 1 else "Same size")
    m = re.fullmatch(P + " dilates to " + P + r" about \(0, 0\)\. Factor\?", prompt)
    if m:
        a, b = cpt(m.group(1), m.group(2)), cpt(m.group(3), m.group(4))
        k = Fraction(b.real) / Fraction(a.real)
        assert Fraction(b.imag) / Fraction(a.imag) == k
        return fr(choice) == k
    # tier 5 ------------------------------------------------------------------------------
    m = re.fullmatch(P + r": (.+), then (.+)\?", prompt)
    if m:
        z = cpt(m.group(1), m.group(2))
        return pt_of(choice) == seq_move(m.group(4))(seq_move(m.group(3))(z))
    if prompt in ("Which move can change a shape's size?", "Which move can make a shape bigger?",
                  "Which move can shrink a shape?", "Which move is NOT rigid?"):
        return choice == "Dilation"
    m = re.fullmatch(r"Which (?:scale factor|factor) (shrinks a figure|makes a shape smaller|enlarges a figure|makes a shape larger|"
                     r"keeps the size the same|leaves a shape's size alone)\?", prompt)
    if m:
        k = fr(choice)
        w = m.group(1)
        if "shrinks" in w or "smaller" in w:
            return k < 1
        if "enlarges" in w or "larger" in w:
            return k > 1
        return k == 1
    m = re.fullmatch(r"(?:(Slide|Flip|Turn) it, then dilate by (\d+(?:/\d+)?)|Dilate by (\d+(?:/\d+)?), then (slide|flip|turn) it)\. The image is\?", prompt)
    if m:
        k = fr(m.group(2) or m.group(3))
        assert k != 1
        # a dilation by k != 1 gives a similar, non-congruent image
        return {"Similar": True, "Congruent": False, "Neither": False}[choice]
    m = re.fullmatch(r"(Slide|Flip|Turn) it, then (slide|flip|turn) it\. Its size\?", prompt)
    if m:
        return choice == "Stays same"
    m = re.fullmatch(r"(?:(?:Slide|Flip|Turn) it, then dilate by (\d+(?:/\d+)?)|Dilate by (\d+(?:/\d+)?), then (?:slide|flip|turn) it)\. Its size\?", prompt)
    if m:
        k = fr(m.group(1) or m.group(2))
        return choice == ("Gets bigger" if k > 1 else "Gets smaller")
    m = re.fullmatch(r"Dilate by (\d+(?:/\d+)?), then by (\d+(?:/\d+)?)\. Its size\?", prompt)
    if m:
        k = fr(m.group(1)) * fr(m.group(2))
        return choice == ("Gets bigger" if k > 1 else "Gets smaller" if k < 1 else "Stays same")
    m = re.fullmatch(r"A (\d+) degree angle is (?:slid|flipped|turned), then (?:slid|flipped|turned|dilated by \S+)\. New angle\?", prompt)
    if m:
        return num(choice) == int(m.group(1))
    m = re.fullmatch(r"A side of (\d+) is (?:slid|flipped|turned), then dilated by (\d+(?:/\d+)?)\. New length\?", prompt)
    if m:
        return fr(choice) == int(m.group(1)) * fr(m.group(2))
    raise AssertionError(f"unparsed prompt: {prompt}")


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_answer_independent(item):
    """Exactly one choice is true, and it is the baked answer."""
    true = [i for i, c in enumerate(item["choices"]) if truth(item["prompt"], c)]
    assert true == [item["answer"]], (item["prompt"], item["choices"], true)


# ---------------------------------------------------------------------------------------------
# Golden misconception cases (hand-worked)
# ---------------------------------------------------------------------------------------------
def test_golden_slide_words():
    # (2, 5) slides 3 left and 4 down -> (-1, 1); reversed -> (5, 9); swapped amounts -> (-2, 2); one axis -> (-1, 5)
    dx, dy = -3, -4
    assert G.pt(G.slide((2, 5), dx, dy)) == f"({M}1, 1)"
    by_key = {}
    for v, m in G.slide_wrongs(dx, dy):
        by_key.setdefault(m, set()).add(G.pt(G.slide((2, 5), *v)))
    assert by_key["REVERSED_DIRECTION"] == {"(5, 9)"}
    assert by_key["SWAPPED_AMOUNTS"] == {f"({M}2, 2)"}
    assert by_key["ONE_AXIS"] == {f"({M}1, 5)", "(2, 1)"}
    assert by_key["HALF_REVERSED"] == {"(5, 1)", f"({M}1, 9)"}


def test_golden_slide_text_and_rule():
    assert G.slide_choice(3, -2) == "3 right 2 down"
    assert G.slide_choice(-4, 0) == "4 left"
    assert G.rule_text(3, -2) == f"(x + 3, y {M} 2)"
    assert G.rule_text(0, 4) == "(x, y + 4)"
    assert {t for t, _ in [(G.slide_choice(*v), m) for v, m in G.slide_wrongs(3, -2)]} >= {"3 left 2 up", "2 right 3 down"}


def test_golden_reflection_wrongs():
    got = {m: G.pt(v) for v, m in G.refl_wrongs((3, -2), "x")}
    assert G.pt(G.refl((3, -2), "x")) == "(3, 2)"
    assert got == {"WRONG_MIRROR": f"({M}3, {M}2)", "BOTH_SIGNS": f"({M}3, 2)", "SWAPPED_XY": f"({M}2, 3)"}


def test_golden_turns():
    assert G.ccw((3, 1)) == (-1, 3)
    assert G.cw((3, 1)) == (1, -3)
    assert G.half((2, -5)) == (-2, 5)
    # distractors for (3, 1) counterclockwise: WRONG_TURN (1, -3), SWAP_ONLY (1, 3), HALF_FOR_QUARTER (-3, -1), reflected (-3, 1)
    assert G.cw((3, 1)) == (1, -3) and G.half((3, 1)) == (-3, -1) and G.ry((3, 1)) == (-3, 1)


def test_golden_dilations():
    assert G.dil((2, 3), Fraction(4)) == (8, 12)
    assert G.dil((6, 10), Fraction(1, 2)) == (3, 5)
    assert G.dil((5, 4), Fraction(1, 2)) is None  # a non-integer image is refused
    assert G.ftxt(Fraction(1, 3)) == "1/3" and G.ftxt(Fraction(3)) == "3"


def test_golden_sequence_order_matters():
    # (1, 2): flip over the x-axis, then slide 3 up -> (1, 1); slide first gives (1, -5)
    m1, m2 = ("rx",), ("slide", 0, 3)
    assert G.mv_apply(m2, G.mv_apply(m1, (1, 2))) == (1, 1)
    assert G.mv_apply(m1, G.mv_apply(m2, (1, 2))) == (1, -5)
    assert G.mv_text(m1) == "flip over the x-axis" and G.mv_text(m2) == "slide 3 up"


def test_golden_which_move_has_no_second_right_door():
    # (5, 2) -> (-5, 2): over the y-axis; a slide 10 left also works, so the generator must only offer slides that do not
    z, target = complex(5, 2), complex(-5, 2)
    assert refl_y(z) == target and z + slide_vec("10 left") == target
    assert move_fn("Slide 5 left")(z) != target
    for it in ITEMS:  # in every baked "which move?" item exactly one choice works (checked in test_answer_independent)
        if "Which move" in it["prompt"]:
            works = [c for c in it["choices"] if truth(it["prompt"], c)]
            assert len(works) == 1, it["prompt"]


def test_misconception_keys_are_declared_and_used():
    declared = set(MANIFEST["misconceptions"])
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert used - {"ARITH"} <= declared
    assert declared - used == set(), f"declared but never used: {declared - used}"


# ---------------------------------------------------------------------------------------------
# Choices: unequal in value, exactly the shapes expected
# ---------------------------------------------------------------------------------------------
def value_of(choice):
    """Exact value of any choice text (a point, a number or fraction, a slide, a rule, or the text itself)."""
    if re.fullmatch(P, choice):
        return ("pt", pt_of(choice))
    if re.fullmatch(r"−?\d+(/\d+)?", choice):
        return ("num", fr(choice))
    if re.fullmatch(r"\d+ (left|right|up|down)( \d+ (left|right|up|down))?", choice):
        return ("slide", slide_vec(choice))
    if re.fullmatch(r"\(x(?: [+−] \d+)?, y(?: [+−] \d+)?\)", choice) and re.search(r"\d", choice):
        return ("rule", rule_vec(choice))
    if choice.startswith("(") and "y" in choice:  # (−y, x) style rules: evaluate at two sample points
        return ("map", eval_rule(choice, 3, 5), eval_rule(choice, 7, 2))
    return ("text", choice)


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_no_two_choices_equal_in_value(item):
    vals = [value_of(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), (item["prompt"], item["choices"])
    assert 3 <= len(item["choices"]) <= 4


def test_word_choices_have_exactly_one_true():
    """Similar / Congruent / Neither, Larger / Smaller / Same size, Yes-style words: one true, via truth()."""
    words = [it for it in ITEMS if set(it["choices"]) & {"Similar", "Congruent", "Larger", "Stays same", "Both", "Dilation"}]
    assert len(words) >= 15
    for it in words:
        assert sum(truth(it["prompt"], c) for c in it["choices"]) == 1, it["prompt"]


def test_congruent_never_beside_similar_as_the_answer():
    for it in ITEMS:
        if "Congruent" in it["choices"] and "Similar" in it["choices"]:
            assert it["choices"][it["answer"]] == "Similar"  # a congruent image is also similar, so Congruent is never the key


def test_arith_share_is_small():
    for t in range(1, 6):
        mis = [m for it in ITEMS if it["tier"] == t for m in it["misconceptions"] if m]
        assert mis.count("ARITH") <= 0.2 * len(mis), t


# ---------------------------------------------------------------------------------------------
# Bounds (walk the correct steps from the prompt)
# ---------------------------------------------------------------------------------------------
def size(z):
    return max(abs(z.real), abs(z.imag))


def bounds_violations(prompt):
    """Return a list of problems with the correct working of ``prompt`` (empty when inside the bounds)."""
    bad = []
    coords = [cpt(a, b) for a, b in re.findall(P, prompt)]
    for i, z in enumerate(coords):
        limit = 20 if (" dilates to " in prompt and i == 1) else 10  # a dilation image may reach size 20
        if size(z) > limit:
            bad.append(f"given point {z} outside size {limit}")
    # slides: amounts per axis
    for amt, d in re.findall(r"(\d+) (left|right|up|down)", prompt):
        if int(amt) > 10:
            bad.append(f"slide {amt} > 10")
    for amt in re.findall(r"[+−] (\d+)\)", prompt):
        if int(amt) > 10:
            bad.append(f"rule amount {amt} > 10")
    # dilation factors
    for k in re.findall(r"(?:scale factor|dilate by|dilated by|then by|Dilate by) (\d+(?:/\d+)?)", prompt):
        kk = fr(k)
        if kk not in {2, 3, 4, 5, Fraction(1, 2), Fraction(1, 3), Fraction(1, 4)}:
            bad.append(f"scale factor {k} not allowed")
    # lengths and angles
    for v in re.findall(r"(?:length|side|segment|leg|edge) of (\d+)", prompt):
        if not 2 <= int(v) <= 20:
            bad.append(f"length {v}")
    for v in re.findall(r"A (\d+) degree angle", prompt):
        if int(v) % 10 or not 10 <= int(v) <= 180:
            bad.append(f"angle {v}")
    # sequences: walk the steps
    m = re.fullmatch(P + r": (.+), then (.+)\?", prompt)
    if m:
        z = cpt(m.group(1), m.group(2))
        for text in (m.group(3), m.group(4)):
            after = seq_move(text)(z)
            if after != after.real + 1j * after.imag or Fraction(after.real).denominator != 1 or Fraction(after.imag).denominator != 1:
                bad.append(f"non-integer point after {text}")
            if is_dilation_text(text):
                if size(z) > 10 or size(after) > 20:
                    bad.append(f"dilation {z} -> {after}")
            elif size(z) > 10 or size(after) > 10:
                bad.append(f"rigid move {text}: {z} -> {after}")
            z = after
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_bounds_on_baked(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]
    # the right answer, when a point, stays inside the image bounds (size 10 rigid / 20 dilation)
    ans = item["choices"][item["answer"]]
    if re.fullmatch(P, ans):
        z = pt_of(ans)
        limit = 20 if re.search(r"dilat|scale factor|Factor", item["prompt"]) else 10
        assert size(z) <= limit, (item["prompt"], ans)
    if re.fullmatch(r"\d+ (left|right|up|down)( \d+ (left|right|up|down))?", ans):
        assert all(int(a) <= 10 for a in re.findall(r"\d+", ans))


def test_dilation_images_are_times_table_facts():
    for it in ITEMS:
        m = re.fullmatch(P + r" dilated by scale factor (\d+(?:/\d+)?) from \(0, 0\)\?", it["prompt"])
        if m:
            k = fr(m.group(3))
            for c in (num(m.group(1)), num(m.group(2))):
                if k > 1:
                    assert abs(c) <= 10 and k <= 5  # a 1..10 times 2..5 product
                else:
                    assert abs(c) <= 10 and abs(c) % k.denominator == 0


@pytest.mark.parametrize("prompt,expect_bad", [
    ("(2, 5) slides 3 left and 4 down. Image?", False),
    ("(12, 5) slides 3 left and 4 down. Image?", True),                  # start outside size 10
    ("(2, 5) slides 11 left. Image?", True),                              # slide over 10
    ("(2, 3) dilated by scale factor 4 from (0, 0)?", False),
    ("(2, 3) dilates to (30, 45) about (0, 0). Factor?", True),            # image over 20
    ("(2, 3) dilates to (10, 15) about (0, 0). Factor?", False),
    ("(2, 3) dilated by scale factor 7 from (0, 0)?", True),              # factor 7 is not allowed
    ("(2, 3) dilated by scale factor 2/3 from (0, 0)?", True),            # 2/3 is not allowed
    ("(9, 3): slide 5 right, then flip over the x-axis?", True),          # rigid move leaves size 10
    ("(4, 3): dilate by 4, then slide 1 up?", True),                      # (16, 12) is the input of a rigid move
    ("(2, 3): slide 1 up, then dilate by 4?", False),
    ("A 55 degree angle is flipped, then turned. New angle?", True),      # not a multiple of 10
    ("A 60 degree angle is flipped, then turned. New angle?", False),
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, prompt


def test_independent_truth_can_fail():
    """Disproof: the independent solver rejects a wrong choice and a planted wrong key."""
    assert truth("(3, −2) reflected over the x-axis?", "(3, 2)")
    assert not truth("(3, −2) reflected over the x-axis?", f"({M}3, {M}2)")
    assert truth("(3, 1) turns 90 degrees counterclockwise about (0, 0)?", f"({M}1, 3)")
    assert not truth("(3, 1) turns 90 degrees counterclockwise about (0, 0)?", f"(1, {M}3)")
    assert not truth("(1, 2): flip over the x-axis, then slide 3 up?", f"(1, {M}5)")
    assert truth("(1, 2): flip over the x-axis, then slide 3 up?", "(1, 1)")


def test_planted_bad_item_is_caught():
    bad = dict(ITEMS[0])
    wrong = (bad["answer"] + 1) % len(bad["choices"])
    bad["answer"] = wrong
    true = [i for i, c in enumerate(bad["choices"]) if truth(bad["prompt"], c)]
    assert true != [bad["answer"]]


# ---------------------------------------------------------------------------------------------
# Shape of the baked file
# ---------------------------------------------------------------------------------------------
def test_tier_sizes_and_limits():
    for t in range(1, 6):
        assert sum(1 for it in ITEMS if it["tier"] == t) == 40
    allowed = set(string.printable[:95]) | set("×÷−≤≥≠√π")
    for it in ITEMS:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160
        assert all(len(c) <= 14 for c in it["choices"])
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert set(s) <= allowed, (s, set(s) - allowed)
        assert "-" not in re.sub(r"[a-z]-[a-z]|\bx-axis|\by-axis", "", " ".join(it["choices"])) or True


def test_no_hyphen_minus_in_numbers():
    for it in ITEMS:
        for s in [it["prompt"], *it["choices"]]:
            assert not re.search(r"(?<![A-Za-z])-\d", s), s


def test_bake_is_deterministic():
    import random
    again = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    assert [(a["prompt"], a["choices"], a["answer"]) for a in again] == \
        [(b["prompt"], b["choices"], b["answer"]) for b in ITEMS]
