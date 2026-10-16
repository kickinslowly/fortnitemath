"""pythagorean-theorem cartridge: golden misconception values, an independent re-check of every baked
item (prompts parsed with regexes, answers computed with math.isqrt, never the generator's solver),
the §4b Pythagorean bounds over baked.json, and equal-value / one-right-door checks.
"""
import itertools
import json
import re
from collections import Counter
from math import isqrt

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "pythagorean-theorem"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
with open(REPO_ROOT / "cartridges" / CID / "cartridge.json", encoding="utf-8") as _f:
    MANIFEST = json.load(_f)
ITEMS = BAKED["items"]
M = "−"
SQRT = "√"

WHOLE_HYP = {(3, 4, 5), (6, 8, 10)}  # sorted (leg, leg, hyp)
BOX_WHOLE = {(1, 2, 2, 3), (2, 4, 4, 6), (2, 3, 6, 7), (1, 4, 8, 9), (4, 4, 7, 9)}


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def is_sq(n):
    return isqrt(n) ** 2 == n


# ---------------------------------------------------------------------------------------------
# Test-local helpers
# ---------------------------------------------------------------------------------------------
def choice_sq(text):
    """Square of the length a choice names: '√13' -> 13, '5' -> 25."""
    if text.startswith(SQRT):
        return int(text[1:])
    return int(text) ** 2


def render_sq(sq):
    r = isqrt(sq)
    return str(r) if r * r == sq else f"{SQRT}{sq}"


def ints(text):
    return [int(x) for x in re.findall(r"\d+", text)]


def coords(text):
    return [(int(x.replace(M, "-")), int(y.replace(M, "-")))
            for x, y in re.findall(r"\((−?\d+), (−?\d+)\)", text)]


# Prompt classification and the true answer (as a square), independent of the generator.
def classify(item):
    p, t = item["prompt"], item["tier"]
    if t == 1:
        return "hyp"
    if t == 2:
        return "leg"
    if t == 3:
        if p.startswith("Right triangle, sides"):
            return "hypid"
        if re.search(r"Right triangle\?$|right triangle\?$", p) and len(item["choices"]) == 2:
            return "yesno"
        return "which"
    if t == 4:
        return "dist"
    if SQRT in p or "square has side" in p:
        return "square" if "square has side" in p else "hyp"
    if re.search(r"\d+ by \d+ by \d+", p):
        return "box"
    if re.search(r"ladder|wire|slide", p):
        return "leg"
    return "hyp"


def true_sq(item):
    """Square of the correct length, or None for the non-length items."""
    kind, p = classify(item), item["prompt"]
    n = ints(p)
    if kind == "hyp":
        a, b = n[0], n[1]
        return a * a + b * b
    if kind == "leg":
        c, a = n[0], n[1]
        return c * c - a * a
    if kind == "square":
        return 2 * n[0] * n[0]
    if kind == "box":
        a, b, c = n[0], n[1], n[2]
        return a * a + b * b + c * c
    if kind == "dist":
        pts = coords(p)
        if len(pts) == 1:
            pts = [(0, 0)] + pts
        (x1, y1), (x2, y2) = pts
        return (x1 - x2) ** 2 + (y1 - y2) ** 2
    return None


def triple_is_right(a, b, c):
    a, b, c = sorted((a, b, c))
    return a * a + b * b == c * c


# ---------------------------------------------------------------------------------------------
# Golden cases: each candidate list on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
def names(cands):
    return {label: render_sq(sq) for label, sq in cands}


def test_golden_hypotenuse():
    assert names(G.cands_hyp(3, 4)) == {"ADDED_LEGS": "7", "NO_ROOT": "25", "ROOT_OF_LEG_SUM": f"{SQRT}7",
                                        "DOUBLED_FOR_SQUARE": f"{SQRT}14"}
    assert names(G.cands_hyp(2, 3)) == {"ADDED_LEGS": "5", "NO_ROOT": "13", "ROOT_OF_LEG_SUM": f"{SQRT}5",
                                        "DOUBLED_FOR_SQUARE": f"{SQRT}10"}


def test_golden_leg():
    assert names(G.cands_leg(10, 6)) == {"ADDED_SQUARES": f"{SQRT}136", "SUBTRACTED_SIDES": "4",
                                         "NO_ROOT": "64", "ROOT_OF_DIFF": "2"}
    assert names(G.cands_leg(4, 2)) == {"ADDED_SQUARES": f"{SQRT}20", "SUBTRACTED_SIDES": "2",
                                        "NO_ROOT": "12", "ROOT_OF_DIFF": f"{SQRT}2"}


def test_golden_distance():
    assert names(G.cands_dist(3, 4)) == {"TAXICAB": "7", "NO_ROOT": "25", "ONE_LEG": "3",
                                         "ROOT_OF_LEG_SUM": f"{SQRT}7"}
    # (−2, 1) to (3, 5): gaps 5 and 4; a student who subtracts sizes across zero gets 1 and 4
    got = names(G.cands_dist(5, 4, wrong_gaps=(1, 4)))
    assert got["NEG_DIFF"] == f"{SQRT}17"
    assert got["TAXICAB"] == "9"


def test_golden_box():
    assert names(G.cands_box(2, 3, 6)) == {"ADDED_ALL": "11", "FACE_ONLY": f"{SQRT}13", "NO_ROOT": "49"}
    assert names(G.cands_box(1, 2, 3)) == {"ADDED_ALL": "6", "FACE_ONLY": f"{SQRT}5", "NO_ROOT": "14"}


def test_fmt_never_roots_a_perfect_square():
    assert G.fmt(16) == "4" and G.fmt(13) == f"{SQRT}13" and G.fmt(1) == "1"


# ---------------------------------------------------------------------------------------------
# Whole-deck structure
# ---------------------------------------------------------------------------------------------
def test_forty_per_tier_and_unique_prompts():
    for t in range(1, 6):
        its = by_tier(t)
        assert len(its) == 40
        assert len({it["prompt"] for it in its}) == 40


def test_every_label_is_declared_and_arith_is_a_minority():
    declared = set(MANIFEST["misconceptions"]) | {"ARITH"}
    arith = total = 0
    for it in ITEMS:
        for m in it["misconceptions"]:
            if m is not None:
                assert m in declared
                total += 1
                arith += m == "ARITH"
    assert arith * 10 <= total  # ARITH only fills


def test_no_hyphen_minus_in_display_strings():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"]] + it["choices"]:
            assert not re.search(r"(?<![\w])-\d|\d-\d", s) or "3-4-5" in s, s


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked answer
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=[it["prompt"][:40] + f"#{i}" for i, it in enumerate(ITEMS)])
def test_answer_independent(item):
    kind = classify(item)
    right = item["choices"][item["answer"]]
    assert item["misconceptions"][item["answer"]] is None
    if kind == "yesno":
        s = ints(item["prompt"])
        assert right == ("Yes" if triple_is_right(*s) else "No")
        assert Counter(item["choices"]) == Counter(["Yes", "No"])
    elif kind == "which":
        trip = [tuple(ints(c)) for c in item["choices"]]
        rights = [i for i, t in enumerate(trip) if triple_is_right(*t)]
        assert rights == [item["answer"]]
        assert len({tuple(sorted(t)) for t in trip}) == len(trip)
        assert all(list(t) == sorted(t) for t in trip)
    elif kind == "hypid":
        toks = re.search(r"sides (.*)\. Hypotenuse\?$", item["prompt"]).group(1).split(", ")
        roots = [t for t in toks if t.startswith(SQRT)]
        legs = [int(t) for t in toks if not t.startswith(SQRT)]
        assert len(roots) == 1 and len(legs) == 2
        assert int(roots[0][1:]) == legs[0] ** 2 + legs[1] ** 2  # consistent right triangle
        assert right == roots[0]  # the longest side
        assert isqrt(int(roots[0][1:])) >= max(legs)
        assert sorted(item["choices"]) == sorted(toks)
    else:
        sq = true_sq(item)
        assert choice_sq(right) == sq
        assert right == render_sq(sq)
        assert right.startswith(SQRT) == (not is_sq(sq))
        # every choice a different length (the player never faces two right doors)
        vals = [choice_sq(c) for c in item["choices"]]
        assert len(set(vals)) == len(vals)
        assert vals.count(sq) == 1
        # the explanation carries the right answer
        assert right in item["explanation"]


# ---------------------------------------------------------------------------------------------
# Every non-ARITH label equals the value its misconception gives (recomputed here)
# ---------------------------------------------------------------------------------------------
def wrong_sq(item, label):
    kind, p = classify(item), item["prompt"]
    n = ints(p)
    if kind in ("hyp", "square"):
        a, b = (n[0], n[0]) if kind == "square" else (n[0], n[1])
        return {"ADDED_LEGS": (a + b) ** 2, "NO_ROOT": (a * a + b * b) ** 2,
                "ROOT_OF_LEG_SUM": a + b, "DOUBLED_FOR_SQUARE": 2 * a + 2 * b}[label]
    if kind == "leg":
        c, a = n[0], n[1]
        return {"ADDED_SQUARES": c * c + a * a, "SUBTRACTED_SIDES": (c - a) ** 2,
                "NO_ROOT": (c * c - a * a) ** 2, "ROOT_OF_DIFF": c - a}[label]
    if kind == "box":
        a, b, c = n[0], n[1], n[2]
        return {"ADDED_ALL": (a + b + c) ** 2, "FACE_ONLY": a * a + b * b,
                "NO_ROOT": (a * a + b * b + c * c) ** 2}[label]
    if kind == "dist":
        pts = coords(p)
        if len(pts) == 1:
            pts = [(0, 0)] + pts
        (x1, y1), (x2, y2) = pts
        dx, dy = abs(x1 - x2), abs(y1 - y2)
        gx = abs(abs(x2) - abs(x1)) if x1 * x2 < 0 else dx
        gy = abs(abs(y2) - abs(y1)) if y1 * y2 < 0 else dy
        return {"TAXICAB": (dx + dy) ** 2, "NO_ROOT": (dx * dx + dy * dy) ** 2, "ONE_LEG": dx * dx,
                "ROOT_OF_LEG_SUM": dx + dy, "NEG_DIFF": gx * gx + gy * gy}[label]
    raise AssertionError(kind)


@pytest.mark.parametrize("item", [it for it in ITEMS if classify(it) not in ("yesno", "which", "hypid")],
                         ids=lambda it: it["prompt"][:40])
def test_labels_are_produced_by_their_misconception(item):
    for choice, label in zip(item["choices"], item["misconceptions"]):
        if label is None or label == "ARITH":
            continue
        assert choice_sq(choice) == wrong_sq(item, label), (item["prompt"], label, choice)


def test_t4_neg_diff_only_where_a_coordinate_pair_straddles_zero():
    seen = 0
    for it in by_tier(4):
        if "NEG_DIFF" not in it["misconceptions"]:
            continue
        seen += 1
        pts = coords(it["prompt"])
        (x1, y1), (x2, y2) = pts
        assert x1 * x2 < 0 or y1 * y2 < 0
    assert seen >= 8


def test_t3_labels_match_their_item():
    for it in by_tier(3):
        kind = classify(it)
        if kind == "yesno":
            s = ints(it["prompt"])
            a, b, c = s
            wrong = it["misconceptions"][1 - it["answer"]]
            if it["choices"][it["answer"]] == "Yes":
                if s[2] == max(s):  # hypotenuse last: the student just added the sides
                    assert wrong == "ADD_SIDES" and s[0] + s[1] != s[2]
                else:
                    assert wrong == "ORDER_AS_GIVEN"
            else:
                s = sorted(s)
                consecutive = s[1] == s[0] + 1 and s[2] == s[0] + 2
                close = abs(s[0] ** 2 + s[1] ** 2 - s[2] ** 2) <= 2
                assert wrong == ("CONSECUTIVE" if consecutive else "CLOSE_ENOUGH" if close else "ANY_TRIANGLE")
                assert s[2] < s[0] + s[1]  # still a triangle
        elif kind == "which":
            for ch, lab in zip(it["choices"], it["misconceptions"]):
                if lab is None:
                    continue
                s = sorted(ints(ch))
                consecutive = s[1] == s[0] + 1 and s[2] == s[0] + 2
                close = abs(s[0] ** 2 + s[1] ** 2 - s[2] ** 2) <= 2
                assert lab == ("CONSECUTIVE" if consecutive else "CLOSE_ENOUGH" if close else "ANY_TRIANGLE")
        else:
            legs = [int(t) for t in re.search(r"sides (.*)\.", it["prompt"]).group(1).split(", ")
                    if not t.startswith(SQRT)]
            for ch, lab in zip(it["choices"], it["misconceptions"]):
                if lab is not None:
                    assert lab == "LEG_AS_LONGEST" and int(ch) in legs


# ---------------------------------------------------------------------------------------------
# Bounds (the manifest's "bounds" string), walked over baked.json
# ---------------------------------------------------------------------------------------------
def length_ok(sq):
    """A correct length: a whole side of 3-4-5 or 6-8-10, or a non-square n in 2..99."""
    if is_sq(sq):
        return isqrt(sq) in (3, 4, 5, 6, 8, 10)
    return 2 <= sq <= 99


def triple_ok(x, y, z):
    """Whole-answer problems must be the 3-4-5 or 6-8-10 triple."""
    return tuple(sorted((x, y, z))) in WHOLE_HYP


def bound_problems(tier, prompt, answer_sq=None):
    """Problems with a prompt's correct steps under §4b Pythagorean ([] = within bounds)."""
    bad = []
    n = ints(prompt)
    if tier in (1, 2) or (tier == 5 and not re.search(r"by \d+ by", prompt)):
        if tier == 5 and re.search(r"square has side", prompt):
            a = b = n[0]
            hyp = True
        elif tier == 1 or (tier == 5 and not re.search(r"ladder|wire|slide", prompt)):
            a, b, hyp = n[0], n[1], True
        else:
            hyp = False
        if hyp:
            a, b = (n[0], n[0]) if (tier == 5 and "square has side" in prompt) else (n[0], n[1])
            if max(a, b) > 10 or min(a, b) < 1:
                bad.append("side")
            if a * a + b * b > 100:
                bad.append("sum")
            if not length_ok(a * a + b * b):
                bad.append("answer")
            if is_sq(a * a + b * b) and not triple_ok(a, b, isqrt(a * a + b * b)):
                bad.append("triple")
        else:
            c, a = n[0], n[1]
            if c > 10 or a >= c or a < 1:
                bad.append("side")
            if not length_ok(c * c - a * a):
                bad.append("answer")
            if is_sq(c * c - a * a) and not triple_ok(a, isqrt(c * c - a * a), c):
                bad.append("triple")
    elif tier == 3:
        if prompt.startswith("Right triangle, sides"):
            toks = re.search(r"sides (.*)\. Hypotenuse", prompt).group(1).split(", ")
            legs = [int(t) for t in toks if not t.startswith(SQRT)]
            root = [int(t[1:]) for t in toks if t.startswith(SQRT)][0]
            if max(legs) > 9 or root > 99 or is_sq(root) or root < 2:
                bad.append("root")
            if (root ** 0.5) - max(legs) < 0.3:
                bad.append("close")
        elif "?" in prompt and not prompt.startswith("Which") and not prompt.startswith("A carpenter"):
            s = sorted(n)
            if s[-1] > 10 or s[0] < 1 or s[0] ** 2 + s[1] ** 2 > 100:
                bad.append("sides")
    elif tier == 4:
        pts = coords(prompt)
        if len(pts) == 1:
            pts = [(0, 0)] + pts
        for x, y in pts:
            if abs(x) > 10 or abs(y) > 10:
                bad.append("coord")
        (x1, y1), (x2, y2) = pts
        dx, dy = abs(x1 - x2), abs(y1 - y2)
        if dx < 1 or dy < 1 or dx > 10 or dy > 10 or dx * dx + dy * dy > 100:
            bad.append("gap")
        if not length_ok(dx * dx + dy * dy):
            bad.append("answer")
        if is_sq(dx * dx + dy * dy) and not triple_ok(dx, dy, isqrt(dx * dx + dy * dy)):
            bad.append("triple")
    else:  # tier 5 box
        a, b, c = n[0], n[1], n[2]
        s = a * a + b * b + c * c
        if max(a, b, c) > 10 or min(a, b, c) < 1 or s > 100:
            bad.append("edge")
        r = isqrt(s)
        if r * r == s:
            if tuple(sorted((a, b, c)) + [r]) not in BOX_WHOLE:
                bad.append("whole box")
        elif s < 2 or s > 99:
            bad.append("root")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=[it["prompt"][:40] + f"#{i}" for i, it in enumerate(ITEMS)])
def test_bounds(item):
    assert bound_problems(item["tier"], item["prompt"]) == []
    # wrong choices stay under 999 in value
    if classify(item) not in ("yesno", "which"):
        for c in item["choices"]:
            assert choice_sq(c) <= 999 ** 2


@pytest.mark.parametrize("tier,prompt", [
    (1, "Legs 5 and 12. Hypotenuse?"),          # side 12
    (1, "Legs 6 and 9. Hypotenuse?"),           # 36 + 81 = 117 > 100
    (2, "Hypotenuse 13, one leg 5. Other leg?"),  # hypotenuse 13
    (2, "Hypotenuse 9, one leg 9. Other leg?"),  # a leg as long as the hypotenuse
    (3, "Sides 8, 9, 10. Right triangle?"),     # 64 + 81 = 145 > 100
    (4, "Distance from (1, 2) to (11, 6)?"),    # coordinate 11
    (4, "Distance from (0, 0) to (5, 12)?"),
    (4, "Distance from (−10, −10) to (9, 8)?"),  # gaps 19 and 18
    (5, "Box 3 by 6 by 6. Longest diagonal?"),  # whole 9 but not on the §4b list
    (5, "Box 5 by 6 by 7. Longest diagonal?"),  # 25 + 36 + 49 = 110
    (5, "Box 2 by 11 by 3. Longest diagonal?"),
])
def test_bounds_checker_rejects(tier, prompt):
    assert bound_problems(tier, prompt) != []


@pytest.mark.parametrize("tier,prompt", [
    (1, "Legs 3 and 4. Hypotenuse?"),
    (1, "Legs 8 and 6. Hypotenuse?"),
    (2, "Hypotenuse 10, one leg 6. Other leg?"),
    (3, "Sides 6, 10, 8. Right triangle?"),
    (4, "Distance from (−2, 1) to (3, 5)?"),
    (5, "Box 2 by 3 by 6. Longest diagonal?"),
    (5, "A square has side 7 cm. How long is its diagonal?"),
])
def test_bounds_checker_accepts(tier, prompt):
    assert bound_problems(tier, prompt) == []


def test_every_whole_answer_is_a_special_triple():
    for it in ITEMS:
        sq = true_sq(it)
        if sq is not None and is_sq(sq) and classify(it) != "box":
            assert isqrt(sq) in (3, 4, 5, 6, 8, 10), it["prompt"]


def test_box_perfect_squares_are_the_listed_ones():
    dims = set()
    for it in by_tier(5):
        if classify(it) == "box":
            a, b, c = ints(it["prompt"])[:3]
            s = a * a + b * b + c * c
            if is_sq(s):
                dims.add(tuple(sorted((a, b, c))) + (isqrt(s),))
    assert dims <= BOX_WHOLE and len(dims) >= 3


def test_variety_per_tier():
    assert any(is_sq(true_sq(it)) for it in by_tier(1)) and any(not is_sq(true_sq(it)) for it in by_tier(1))
    kinds = Counter(classify(it) for it in by_tier(3))
    assert kinds["yesno"] == 20 and kinds["which"] == 8 and kinds["hypid"] == 12
    t5 = Counter(classify(it) for it in by_tier(5))
    assert t5["box"] >= 10 and t5["leg"] >= 8 and t5["hyp"] >= 10
    crossing = sum(1 for it in by_tier(4) if "NEG_DIFF" in it["misconceptions"])
    assert crossing >= 8


def test_rebake_is_deterministic():
    import random
    again = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    assert len(again) == len(ITEMS)
    for a, b in zip(again, ITEMS):
        for k in ("tier", "prompt", "choices", "answer", "misconceptions", "explanation"):
            assert a[k] == b[k]
