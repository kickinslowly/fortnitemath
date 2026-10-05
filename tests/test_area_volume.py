"""area-volume cartridge: golden misconception values, an independent re-check of every baked answer,
the manifest bounds walked step by step on baked.json, and value-distinct choices.

The independent check below parses each prompt with its own regexes and computes with
``fractions.Fraction`` -- it never calls the generator's ``solve``.
"""
import json
import re
from collections import Counter
from fractions import Fraction as F

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "area-volume"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked wrong values per misconception (value, or (value, unit) in T4)
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    ("Rectangle: length 6, width 4. Area?", 24, {"PERIMETER": 20, "ADD_SIDES": 10}),
    ("Square: side 7. Area?", 49, {"PERIMETER": 28, "ADD_SIDES": 14}),
    ("Parallelogram: base 8, side 6, height 5. Area?", 40,
     {"SLANT_SIDE": 48, "PERIMETER": 28, "ADD_SIDES": 13}),
    ("Parallelogram: base 8, height 5, side 6. Area?", 40, {"SLANT_SIDE": 48}),
    ("Triangle: base 10, height 6. Area?", 30, {"NO_HALF": 60, "ADD_SIDES": 16}),
    ("Triangle: base 8, side 7, height 6. Area?", 24, {"SLANT_SIDE": 28, "NO_HALF": 48}),
    ("Right triangle: legs 6 and 8. Area?", 24, {"NO_HALF": 48, "ADD_SIDES": 14}),
    ("Cut a 6 by 4 rectangle corner to corner. Area of each half?", 12, {"NO_HALF": 24}),
    ("Trapezoid: bases 4 and 6, height 5. Area?", 25, {"NO_AVERAGE": 50, "ONE_BASE": 30}),
    ("Rectangle: area 48, width 6. Length?", 8, {"SUBTRACTED": 42, "MULTIPLIED": 288}),
    ("Parallelogram: area 30, base 6. Height?", 5, {"SUBTRACTED": 24, "MULTIPLIED": 180}),
    ("Triangle: area 12, base 6. Height?", 4, {"NO_HALF": 2, "SUBTRACTED": 6}),
    ("Box 2 by 3 by 4. Volume?", (24, "cu"),
     {"ADDED_EDGES": (9, "cu"), "MISSED_EDGE": (6, "cu"), "SQUARE_UNITS": (24, "sq")}),
    ("Box 4 by 3 by 1/2. Volume?", (6, "cu"),
     {"MISSED_EDGE": (12, "cu"), "ADDED_EDGES": (F(15, 2), "cu"), "SQUARE_UNITS": (6, "sq")}),
    ("How many cubes of edge 1/2 fill a 2 by 1 by 1 box?", 16,
     {"COUNTED_UNITS": 2, "DOUBLED_ONCE": 4, "HALVED_COUNT": 1}),
    ("Cube, edge 3. Surface area?", 54, {"VOLUME_FOR_SA": 27, "ONE_FACE": 9, "FOUR_FACES": 36}),
    ("Box 2 by 3 by 4. Surface area?", 52, {"VOLUME_FOR_SA": 24, "THREE_FACES": 26, "ONE_FACE": 6}),
    ("Square pyramid: base edge 4, slant height 5. Surface area?", 56, {"NO_BASE": 40, "NO_HALF": 96}),
]


def _vu(x):
    return (F(x[0]), x[1]) if isinstance(x, tuple) else (F(x), None)


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(prompt, correct, wrong):
    sol = G.solve(prompt)
    assert (sol["correct"], sol["unit"]) == _vu(correct)
    got = {lab: (v, u) for lab, v, u in sol["wrong"]}
    for label, v in wrong.items():
        assert got[label] == _vu(v), label


def test_every_misconception_has_a_golden_case():
    covered = {lab for _, _, w in GOLDEN for lab in w}
    assert covered == set(BAKED["misconceptions"])


def test_student_text_fits():
    for k, m in BAKED["misconceptions"].items():
        assert m["teacher"] and 0 < len(m["student"]) <= 80, k


# ---------------------------------------------------------------------------------------------
# Independent solver + bounds walker (own regexes, Fraction arithmetic)
# ---------------------------------------------------------------------------------------------
def L(s):
    return F(1, 2) if s == "1/2" else F(int(s))


def halving_ok(a, b, bad, what):
    """a × b ÷ 2 in the times tables: an even length of 4+ halves first, or a product <= 20 halves."""
    if (a * b) % 2:
        bad.append(f"{what}: {a} × {b} is odd, half is not whole")
    elif not (any(x % 2 == 0 and x >= 4 for x in (a, b)) or a * b <= 20):
        bad.append(f"{what}: half of {a} × {b} needs a ÷ outside the tables")


def mul_ok(a, b, bad):
    if not (1 <= a <= 10 and 1 <= b <= 10):
        bad.append(f"× step {a} × {b} has a factor outside 1-10")


def independent(prompt):
    """(value, unit, [violations]) computed from the prompt text alone."""
    bad = []
    nums = [L(x) for x in re.findall(r"1/2|\d+", prompt)]
    given_lengths = nums
    unit = None
    if m := re.fullmatch(r"Rectangle: length (\d+), width (\d+)\. Area\?", prompt):
        a, b = map(int, m.groups())
        mul_ok(a, b, bad)
        v = F(a * b)
    elif m := re.fullmatch(r"Square: side (\d+)\. Area\?", prompt):
        a = int(m[1])
        mul_ok(a, a, bad)
        v = F(a * a)
    elif m := re.fullmatch(r"Parallelogram: base (\d+), (?:side (\d+), height (\d+)|height (\d+), side (\d+))\. Area\?",
                           prompt):
        b = int(m[1])
        side, h = (int(m[2]), int(m[3])) if m[2] else (int(m[5]), int(m[4]))
        if side <= h:
            bad.append("slanted side must be longer than the height")
        mul_ok(b, h, bad)
        v = F(b * h)
    elif m := re.fullmatch(r"(?:Triangle: base (\d+),(?: side \d+,)? height (\d+)(?:, side \d+)?"
                           r"|Right triangle: legs (\d+) and (\d+)"
                           r"|Cut an? (\d+) by (\d+) rectangle corner to corner)\. Area(?: of each half)?\?",
                           prompt):
        a, b = [int(x) for x in m.groups() if x]
        if sm := re.search(r"side (\d+)", prompt):
            if int(sm[1]) <= b:
                bad.append("slanted side must be longer than the height")
        halving_ok(a, b, bad, "triangle")
        v = F(a * b, 2)
    elif m := re.fullmatch(r"Trapezoid: bases (\d+) and (\d+), height (\d+)\. Area\?", prompt):
        a, b, h = map(int, m.groups())
        if a == b:
            bad.append("trapezoid bases equal")
        avg = F(a + b, 2)
        if avg.denominator != 1 or not 2 <= avg <= 10:
            bad.append(f"base sum {a + b} ÷ 2 is not a 2-10 quotient")
        mul_ok(avg, h, bad)
        v = avg * h
    elif m := re.fullmatch(r"(?:Rectangle: area (\d+), width|Parallelogram: area (\d+), base) (\d+)\. (?:Length|Height)\?",
                           prompt):
        area, known = int(m[1] or m[2]), int(m[3])
        given_lengths = [F(known)]
        v = F(area, known)
        if v.denominator != 1 or not (2 <= known <= 10 and 2 <= v <= 10) or area > 100:
            bad.append(f"{area} ÷ {known} not a times-table fact")
    elif m := re.fullmatch(r"Triangle: area (\d+), base (\d+)\. Height\?", prompt):
        area, b = int(m[1]), int(m[2])
        given_lengths = [F(b)]
        half = F(b, 2)
        v = area / half
        if b % 2 or half < 2 or v.denominator != 1 or not 2 <= v <= 10:
            bad.append(f"{area} ÷ ({b} ÷ 2) not a times-table fact")
    elif m := re.fullmatch(r"Box (\d+|1/2) by (\d+|1/2) by (\d+|1/2)\. Volume\?", prompt):
        e = [L(x) for x in m.groups()]
        unit = "cu"
        v = e[0] * e[1] * e[2]
        whole = [int(x) for x in e if x != F(1, 2)]
        if len(whole) == 2:
            halving_ok(whole[0], whole[1], bad, "half-edge volume")
        elif len(whole) == 3:
            if not any(x * y <= 10 for x, y in ((e[0], e[1]), (e[0], e[2]), (e[1], e[2]))):
                bad.append("no pair of edges multiplies to 10 or less: a × step leaves the tables")
        else:
            bad.append("more than one 1/2 edge")
    elif m := re.fullmatch(r"How many cubes of edge 1/2 fill a (\d+) by (\d+) by (\d+) box\?", prompt):
        a, b, c = map(int, m.groups())
        given_lengths = [F(a), F(b), F(c)]
        vol = a * b * c
        if vol > 10:
            bad.append(f"{vol} × 8 leaves the tables")
        v = F(8 * vol)
    elif m := re.fullmatch(r"Cube, edge (\d+)\. Surface area\?", prompt):
        e = int(m[1])
        if e * e > 10:
            bad.append(f"6 × {e * e} leaves the tables")
        v = F(6 * e * e)
    elif m := re.fullmatch(r"Box (\d+) by (\d+) by (\d+)\. Surface area\?", prompt):
        a, b, c = map(int, m.groups())
        if a == b == c:
            bad.append("a cube written as a box")
        three = a * b + a * c + b * c
        if three > 50:
            bad.append(f"three faces sum {three} > 50")
        v = F(2 * three)
    elif m := re.fullmatch(r"Square pyramid: base edge (\d+), slant height (\d+)\. Surface area\?", prompt):
        s, h = int(m[1]), int(m[2])
        if 2 * h <= s:
            bad.append("slant height too short for the base")
        halving_ok(s, h, bad, "pyramid face")
        face = F(s * h, 2)
        if face > 10:
            bad.append(f"4 × {face} leaves the tables")
        v = s * s + 4 * face
    else:
        raise AssertionError(f"unknown prompt shape {prompt!r}")
    for x in given_lengths:
        if x != F(1, 2) and not 1 <= x <= 10:
            bad.append(f"length {x} outside 1-10")
        if x == F(1, 2) and "Volume" not in prompt and "cubes of edge" not in prompt:
            bad.append("a 1/2 length outside T4")
    if v.denominator != 1 or not 1 <= v <= 100:
        bad.append(f"answer {v} is not a whole number 1-100")
    return v, unit, bad


def parse_choice(c):
    """'7 1/2 cu units' -> (Fraction(15, 2), 'cu'); '24' -> (24, None)."""
    m = re.fullmatch(r"(\d+)(?: (\d+)/(\d+))?(?: (cu|sq) units)?|(\d+)/(\d+)(?: (cu|sq) units)?", c)
    assert m, f"unparseable choice {c!r}"
    if m[5]:
        return F(int(m[5]), int(m[6])), m[7]
    v = F(int(m[1]))
    if m[2]:
        v += F(int(m[2]), int(m[3]))
    return v, m[4]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    v, unit, _ = independent(item["prompt"])
    assert parse_choice(item["choices"][item["answer"]]) == (v, unit)
    assert f"= {v}" in item["explanation"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    _, _, bad = independent(item["prompt"])
    assert bad == [], item["prompt"]
    for c in item["choices"]:
        assert 0 < parse_choice(c)[0] <= 999


@pytest.mark.parametrize("prompt,expect_bad", [
    ("Rectangle: length 7, width 6. Area?", False),
    ("Rectangle: length 12, width 6. Area?", True),            # length over 10
    ("Triangle: base 7, height 5. Area?", True),               # 17 1/2, not whole
    ("Triangle: base 7, height 6. Area?", False),              # 6 ÷ 2 = 3, 3 × 7
    ("Triangle: base 9, height 2. Area?", False),              # 9 × 2 = 18, 18 ÷ 2 = 9
    ("Triangle: base 9, height 3. Area?", True),               # 27 is odd
    ("Triangle: base 5, height 6. Area?", False),              # 6 ÷ 2 = 3, 3 × 5
    ("Triangle: base 7, height 2, side 9. Area?", False),
    ("Triangle: base 7, height 4, side 3. Area?", True),       # side shorter than the height
    ("Trapezoid: bases 9 and 10, height 4. Area?", True),      # odd base sum
    ("Trapezoid: bases 9 and 7, height 9. Area?", False),
    ("Box 4 by 5 by 3. Volume?", True),                        # 12 × 5: no pair within the tables
    ("Box 1/2 by 3 by 5. Volume?", True),                      # 7 1/2 cubic units
    ("Cube, edge 4. Surface area?", True),                     # 6 × 16
    ("Box 5 by 4 by 3. Surface area?", False),                 # 20 + 15 + 12 = 47, 94
    ("Box 6 by 4 by 3. Surface area?", True),                  # three faces 54 > 50
    ("How many cubes of edge 1/2 fill a 3 by 2 by 2 box?", True),  # 12 × 8
    ("Square pyramid: base edge 2, slant height 1. Surface area?", True),
    ("Triangle: area 21, base 6. Height?", False),
    ("Triangle: area 21, base 7. Height?", True),              # odd base: 7 ÷ 2
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(independent(prompt)[2]) == expect_bad, prompt


def test_bounds_checker_rejects_something():
    """Disproof: the checker can fail."""
    assert independent("Rectangle: length 12, width 6. Area?")[2]
    assert independent("Cube, edge 4. Surface area?")[2]


# ---------------------------------------------------------------------------------------------
# Choices: never two right doors; labels honest; shape of the content
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_distinct_in_value(item):
    vals = [parse_choice(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert len(item["choices"]) == 4


def test_choice_value_parser_sees_equal_values():
    assert parse_choice("7 1/2 cu units") == parse_choice("15/2 cu units")
    assert parse_choice("24 cu units") != parse_choice("24 sq units")


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    sol = G.solve(item["prompt"])
    produced = {lab: (v, u) for lab, v, u in sol["wrong"]}
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one misconception distractor"
    assert (sol["correct"], sol["unit"]) not in produced.values(), "a wrong rule lands on the answer"
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        if m == "ARITH":
            assert parse_choice(c) not in produced.values(), f"ARITH {c} is really a misconception value"
        else:
            assert produced[m] == parse_choice(c), (m, c)


def test_arith_share_overall_at_most_a_third():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 1 / 3


def test_units_only_on_volume_items():
    for it in ITEMS:
        has_units = any("units" in c for c in it["choices"])
        assert has_units == it["prompt"].endswith("Volume?"), it["prompt"]


def test_tier_shapes():
    t1 = Counter(it["prompt"].split(":")[0] for it in by_tier(1))
    assert t1["Parallelogram"] >= 15 and t1["Rectangle"] and t1["Square"]
    t2 = [it["prompt"] for it in by_tier(2)]
    assert all(re.search(r"[Tt]riangle|corner to corner", p) for p in t2)
    assert sum("side" in p for p in t2) >= 10
    t3 = [it["prompt"] for it in by_tier(3)]
    assert sum(p.startswith("Trapezoid") for p in t3) >= 12
    assert sum(p.endswith(("Length?", "Height?")) for p in t3) >= 20
    t4 = [it["prompt"] for it in by_tier(4)]
    assert sum("1/2 by" in p or "by 1/2." in p for p in t4) >= 8
    assert sum(p.startswith("How many cubes") for p in t4) >= 6
    t5 = [it["prompt"] for it in by_tier(5)]
    assert all(p.endswith("Surface area?") for p in t5)
    assert any(p.startswith("Cube") for p in t5) and sum(p.startswith("Square pyramid") for p in t5) >= 6
    used5 = Counter(m for it in by_tier(5) for m in it["misconceptions"] if m)
    for key in ("VOLUME_FOR_SA", "ONE_FACE", "FOUR_FACES", "THREE_FACES", "NO_BASE"):
        assert used5[key], key
    used4 = Counter(m for it in by_tier(4) for m in it["misconceptions"] if m)
    assert used4["SQUARE_UNITS"] >= 30 and used4["ADDED_EDGES"] >= 20


def test_bounds_string_declared():
    assert "1-10" in BAKED["bounds"] and "100" in BAKED["bounds"]
