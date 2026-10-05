"""rational-numbers cartridge: golden misconception cases, an independent re-check of every baked
answer, the manifest's bounds asserted on baked.json, and no two choices equal in value.

The independent check parses each prompt with its own regexes and computes the answer with
``fractions.Fraction`` here -- it never calls the generator's builders.
"""
import json
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "rational-numbers"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M = "−"  # U+2212
NUM = r"−?\d+(?:\.5)?"


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def val(s: str) -> Fraction:
    """Display number -> Fraction: '−7', '2.5', '−1/7', '−$12'."""
    return Fraction(s.replace(M, "-").replace("$", ""))


def show(v) -> str:
    v = Fraction(v)
    if v.denominator == 1:
        s = str(abs(v.numerator))
    else:
        assert v.denominator == 2
        s = f"{abs(v.numerator) // 2}.5"
    return f"{M}{s}" if v < 0 else s


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked prompts, each misconception's wrong value
# ---------------------------------------------------------------------------------------------
def wrongs(built):
    return {(lab, txt) for lab, txt in built[2]}


GOLDEN = [
    # (builder call, prompt, answer, {(label, wrong choice)})
    (lambda: G.make_opposite(-7), "Opposite of −7?", "7",
     {("SAME_NUMBER", "−7"), ("RECIPROCAL", "−1/7"), ("RECIPROCAL", "1/7")}),
    (lambda: G.make_opposite(Fraction(5, 2), True), "What is the opposite of 2.5?", "−2.5",
     {("SAME_NUMBER", "2.5"), ("RECIPROCAL", "2/5"), ("RECIPROCAL", "−2/5")}),
    (lambda: G.make_context(0, 8, 5, True), "Owe $8, then earn $5. As integers?", "−8 and 5",
     {("WRONG_SIGN_CONTEXT", "8 and −5"), ("WRONG_SIGN_CONTEXT", "8 and 5"),
      ("WRONG_SIGN_CONTEXT", "−8 and −5")}),
    (lambda: G.make_move(2, 4, True), "Start at 2 and move 4 left. Where are you?", "−2",
     {("WRONG_DIRECTION", "6"), ("FROM_ZERO", "−4"), ("OFF_BY_ONE", "−1")}),
    (lambda: G.make_move(-3, 5, False), "Start at −3 and move 5 right. Where are you?", "2",
     {("WRONG_DIRECTION", "−8"), ("FROM_ZERO", "5"), ("OFF_BY_ONE", "1")}),
    (lambda: G.make_abs(-3, "+", 4), "|−3| + |4| = ?", "7",
     {("KEEPS_SIGN", "1"), ("OPPOSITE_FOR_ABS", "−1"), ("ARITH", "8")}),
    (lambda: G.make_abs(-9, "−", 4), "|−9| − |4| = ?", "5",
     {("KEEPS_SIGN", "−13"), ("OPPOSITE_FOR_ABS", "13"), ("ARITH", "6")}),
    (lambda: G.make_abs(-3, "+", -4), "|−3| + |−4| = ?", "7",  # opposite rule = right answer
     {("KEEPS_SIGN", "−7"), ("ARITH", "8"), ("ARITH", "6")}),
    (lambda: G.make_debt([-5, 15, -12]), "Biggest debt: −$5, $15 or −$12?", "−$12",
     {("NEG_SIZE", "−$5"), ("POSITIVE_DEBT", "$15")}),
    (lambda: G.make_less(3, 5, 1, 2), "Which number is less than −3?", "−5",
     {("NEG_SIZE", "−1"), ("ZERO_LEAST", "0"), ("ABS_ORDER", "2")}),
    (lambda: G.make_order([-2, 3, -7]), "Order from least to greatest: −2, 3, −7", "−7, −2, 3",
     {("NEG_SIZE", "−2, −7, 3"), ("ABS_ORDER", "−2, 3, −7"), ("GREATEST_FIRST", "3, −2, −7")}),
    (lambda: G.make_least([-8, -3, 2], 0), "Coldest: −8, −3 or 2 degrees?", "−8",
     {("NEG_SIZE", "−3"), ("ABS_ORDER", "2")}),
    (lambda: G.make_quadrant(-3, 4), "(−3, 4) is in which quadrant?", "II",
     {("CLOCKWISE", "IV"), ("SIGN_MISREAD", "I"), ("SIGN_MISREAD", "III")}),
    (lambda: G.make_reflect(2, -5, "x"), "Reflect (2, −5) over the x-axis. New point?", "(2, 5)",
     {("WRONG_AXIS", "(−2, −5)"), ("BOTH_FLIPPED", "(−2, 5)"), ("SWAPPED_XY", "(5, 2)")}),
    (lambda: G.make_reflect_quadrant(-3, 4, "y"), "Reflect (−3, 4) over the y-axis. Which quadrant?",
     "I", {("WRONG_AXIS", "III"), ("BOTH_FLIPPED", "IV"), ("NO_MOVE", "II")}),
    (lambda: G.make_distance((-3, 2), (4, 2)), "Distance from (−3, 2) to (4, 2)?", "7",
     {("SUBTRACTED_SIZES", "1"), ("NEG_DISTANCE", "−7"), ("OFF_BY_ONE", "8")}),
    (lambda: G.make_distance((5, -6), (5, -2)), "Distance from (5, −6) to (5, −2)?", "4",
     {("ADDED_SIZES", "8"), ("NEG_DISTANCE", "−4"), ("OFF_BY_ONE", "5")}),
    (lambda: G.make_story(0, 9, -4), "A bird is at 9 m and a fish at −4 m. How far apart?", "13",
     {("SUBTRACTED_SIZES", "5"), ("NEG_DISTANCE", "−13"), ("OFF_BY_ONE", "14")}),
    (lambda: G.make_reflect_distance(3, -4, "x"), "How far is (3, −4) from its x-axis reflection?",
     "8", {("TO_AXIS", "4"), ("WRONG_COORD", "6"), ("NEG_DISTANCE", "−8")}),
]


@pytest.mark.parametrize("build,prompt,answer,wrong", GOLDEN, ids=[g[1] for g in GOLDEN])
def test_golden(build, prompt, answer, wrong):
    b = build()
    assert b[0] == prompt
    assert b[1] == answer
    assert wrongs(b) == wrong


def test_every_declared_misconception_has_a_golden_case_and_is_used():
    golden_labels = {lab for g in GOLDEN for lab, _ in g[3]} - {"ARITH"}
    declared = set(BAKED["misconceptions"])
    assert golden_labels == declared
    used = {m for it in ITEMS for m in it["misconceptions"] if m} - {"ARITH"}
    assert used == declared


# ---------------------------------------------------------------------------------------------
# Independent answer check
# ---------------------------------------------------------------------------------------------
NEG_WORDS = ("owe", "lose", "below", "withdraw", "down")
POS_WORDS = ("earn", "gain", "above", "deposit", "up", "win")


def _signed_phrase(phrase: str) -> int:
    words = re.findall(r"[a-z]+", phrase.lower())
    n = int(re.search(r"\d+", phrase).group())
    neg = any(w in NEG_WORDS for w in words)
    pos = any(w in POS_WORDS for w in words)
    assert neg != pos, phrase
    return -n if neg else n


def _quad(x, y):
    return {(True, True): "I", (False, True): "II", (False, False): "III",
            (True, False): "IV"}[(x > 0, y > 0)]


def _pt(s):
    return tuple(val(v) for v in s.strip("()").split(", "))


def solve(prompt: str, choices: list):
    """Independent answer: returns (expected answer text, list of hidden step values)."""
    m = re.fullmatch(rf"(?:Opposite of|What is the opposite of) ({NUM})\?", prompt)
    if m:
        n = val(m[1])
        return show(-n), [n, -n]
    m = re.fullmatch(r"(.+), then (.+)\. As integers\?", prompt)
    if m:
        x, y = _signed_phrase(m[1]), _signed_phrase(m[2])
        return f"{show(x)} and {show(y)}", [x, y]
    m = re.fullmatch(rf"Start at ({NUM}) and move (\d+) (left|right)\. Where are you\?", prompt)
    if m:
        s, k = val(m[1]), int(m[2])
        e = s - k if m[3] == "left" else s + k
        return show(e), [s, k, e]
    m = re.fullmatch(rf"\|({NUM})\| ([+−]) \|({NUM})\| = \?", prompt)
    if m:
        a, b = abs(val(m[1])), abs(val(m[3]))
        r = a + b if m[2] == "+" else a - b
        return show(r), [val(m[1]), val(m[3]), a, b, r]
    m = re.fullmatch(r"Biggest debt: (−?\$\d+), (−?\$\d+) or (−?\$\d+)\?", prompt)
    if m:
        vals = [val(v) for v in m.groups()]
        debts = [v for v in vals if v < 0]
        big = max(debts, key=abs)
        return f"{M}${-big}", vals
    m = re.fullmatch(rf"Which (?:number is less than|is to the left of) ({NUM})\?", prompt)
    if m:
        r = val(m[1])
        hits = [c for c in choices if val(c) < r]
        assert len(hits) == 1, (prompt, choices)  # exactly one right door
        return hits[0], [r] + [val(c) for c in choices]
    m = re.fullmatch(rf"Order from least to greatest: ({NUM}), ({NUM}), ({NUM})", prompt)
    if m:
        vals = sorted(val(v) for v in m.groups())
        return ", ".join(show(v) for v in vals), vals
    m = re.fullmatch(rf"(?:Coldest|Lowest score|Least|Lowest point): ({NUM}), ({NUM}) or ({NUM})"
                     r"(?: degrees| m)?\?", prompt)
    if m:
        vals = [val(v) for v in m.groups()]
        return show(min(vals)), vals
    m = re.fullmatch(rf"\(({NUM}), ({NUM})\) is in which quadrant\?", prompt)
    if m:
        x, y = val(m[1]), val(m[2])
        return _quad(x, y), [x, y]
    m = re.fullmatch(rf"Reflect \(({NUM}), ({NUM})\) over the ([xy])-axis\. (New point|Which quadrant)\?",
                     prompt)
    if m:
        x, y = val(m[1]), val(m[2])
        ix, iy = (x, -y) if m[3] == "x" else (-x, y)
        if m[4] == "New point":
            return f"({show(ix)}, {show(iy)})", [x, y]
        return _quad(ix, iy), [x, y]
    m = re.fullmatch(rf"Distance from (\({NUM}, {NUM}\)) to (\({NUM}, {NUM}\))\?", prompt)
    if m:
        p, q = _pt(m[1]), _pt(m[2])
        assert (p[0] == q[0]) != (p[1] == q[1]), prompt  # exactly one shared coordinate
        d = abs(p[1] - q[1]) if p[0] == q[0] else abs(p[0] - q[0])
        return show(d), [*p, *q, d]
    m = re.fullmatch(rf"(?:A \w+ is at ({NUM}) m and a \w+ at ({NUM}) m\. How far apart"
                     rf"|Floors ({NUM}) and ({NUM}) \(below ground is −\)\. Floors apart"
                     rf"|It was ({NUM}) degrees, then ({NUM}) degrees\. Degrees apart)\?", prompt)
    if m:
        u, v = [val(g) for g in m.groups() if g is not None]
        return show(abs(u - v)), [u, v, abs(u - v)]
    m = re.fullmatch(rf"How far is \(({NUM}), ({NUM})\) from its ([xy])-axis reflection\?", prompt)
    if m:
        x, y = val(m[1]), val(m[2])
        d = 2 * abs(y) if m[3] == "x" else 2 * abs(x)
        return show(d), [x, y, d]
    raise AssertionError(f"unrecognised prompt {prompt!r}")


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    expected, _ = solve(item["prompt"], item["choices"])
    assert item["choices"][item["answer"]] == expected
    assert expected in item["explanation"]


# ---------------------------------------------------------------------------------------------
# No two choices equal in value (never two right doors)
# ---------------------------------------------------------------------------------------------
def canon(choice: str):
    c = choice.strip()
    if c in ("I", "II", "III", "IV"):
        return ("quadrant", c)
    m = re.fullmatch(r"\((.+), (.+)\)", c)
    if m:
        return ("point", val(m[1]), val(m[2]))
    m = re.fullmatch(r"(.+) and (.+)", c)
    if m:
        return ("pair", val(m[1]), val(m[2]))
    if ", " in c:
        return ("seq",) + tuple(val(v) for v in c.split(", "))
    return ("num", val(c))


def test_canon_sees_equal_values():
    assert canon("1/2") == canon("0.5")
    assert canon("2/4") == canon("1/2")
    assert canon("−$5") == canon("−5")
    assert canon("(−2, 4)") != canon("(4, −2)")


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_distinct_in_value(item):
    vals = [canon(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert len({v[0] for v in vals}) == 1, item["choices"]  # one kind of choice per item


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"), asserted on baked.json by re-deriving every step from the prompt
# ---------------------------------------------------------------------------------------------
def bounds_violations(prompt: str, choices: list) -> list:
    bad = []
    nums = [Fraction(s.replace(M, "-")) for s in re.findall(r"−?\d+(?:\.\d+)?", prompt)]
    for n in nums:
        if n.denominator not in (1, 2):
            bad.append(f"{n} is not an integer or half")
        if abs(n) > 20:
            bad.append(f"{n} has size > 20")
    for x, y in re.findall(rf"\(({NUM}), ({NUM})\)", prompt):
        for c in (val(x), val(y)):
            if c.denominator != 1 or not 1 <= abs(c) <= 10:
                bad.append(f"coordinate {c} outside integer size 1..10")
    for c in choices:
        m = re.fullmatch(r"−?(\d+)/(\d+)", c)
        if m and not 2 <= int(m[2]) <= 12:
            bad.append(f"reciprocal {c} denominator outside 2..12")
    m = re.fullmatch(rf"\|({NUM})\| [+−] \|({NUM})\| = \?", prompt)
    if m and not all(1 <= abs(val(g)) <= 12 for g in m.groups()):
        bad.append("absolute value operand > 12")
    m = re.search(r"move (\d+)", prompt)
    if m and not 1 <= int(m[1]) <= 10:
        bad.append(f"move {m[1]} > 10")
    try:
        answer, steps = solve(prompt, choices)
    except AssertionError as e:
        return bad + [f"unsolvable: {e}"]
    for s in steps:
        if abs(s) > 20 or Fraction(s).denominator not in (1, 2):
            bad.append(f"step value {s} outside the bounds")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"], item["choices"]) == [], item["prompt"]


@pytest.mark.parametrize("prompt,choices,expect_bad", [
    ("Distance from (−3, 2) to (4, 2)?", ["7", "1", "−7", "8"], False),
    ("Distance from (−12, 2) to (4, 2)?", ["16", "8", "−16", "17"], True),   # coordinate 12
    ("Opposite of −2.25?", ["2.25", "−2.25"], True),                         # not a half
    ("|−12| + |11| = ?", ["23", "−1", "1", "24"], True),                     # answer 23
    ("|−13| − |4| = ?", ["9", "−17", "17", "10"], True),                     # operand 13
    ("Start at 9 and move 12 right. Where are you?", ["21", "−3", "12", "20"], True),
    ("Opposite of −7?", ["7", "−7", "−1/7", "1/7"], False),
    ("Opposite of −0.5?", ["0.5", "−0.5", "−2", "2"], False),
    ("Opposite of 13?", ["−13", "13", "1/13", "−1/13"], True),               # denominator 13
])
def test_bounds_checker_catches(prompt, choices, expect_bad):
    assert bool(bounds_violations(prompt, choices)) == expect_bad, prompt


# ---------------------------------------------------------------------------------------------
# Labels are honest; content shape
# ---------------------------------------------------------------------------------------------
def test_every_item_has_a_misconception_distractor():
    for it in ITEMS:
        assert any(m not in (None, "ARITH") for m in it["misconceptions"]), it["prompt"]


def test_arith_only_on_absolute_value_items_and_rare():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.15
    for it in ITEMS:
        if "ARITH" in it["misconceptions"]:
            assert it["prompt"].startswith("|"), it["prompt"]


def test_less_than_items_have_exactly_one_right_door():
    for it in ITEMS:
        m = re.fullmatch(rf"Which (?:number is less than|is to the left of) ({NUM})\?", it["prompt"])
        if m:
            r = val(m[1])
            assert sum(val(c) < r for c in it["choices"]) == 1


def test_no_hyphen_minus_in_display_strings():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in re.sub(r"[xy]-(axis|values)", "", s), s


def test_tiers_cover_their_standards():
    t = {k: [it["prompt"] for it in by_tier(k)] for k in range(1, 6)}
    assert sum("opposite" in p.lower() for p in t[1]) >= 10
    assert sum("As integers" in p for p in t[1]) >= 10
    assert sum(p.startswith("|") for p in t[2]) >= 20
    assert sum("debt" in p for p in t[2]) >= 10
    assert sum("Order" in p for p in t[3]) >= 10
    assert sum("quadrant" in p for p in t[4]) >= 20
    assert sum("Distance" in p for p in t[5]) >= 20
    assert any("." in p for p in t[3])  # halves appear when comparing


def test_no_absolute_value_answer_is_negative():
    # Grade 6: |a| − |b| always puts the bigger size first; subtracting into negatives is 7.NS.
    # (T2 debt answers such as −$18 are balances, the 6.NS.C.7d concept, not arithmetic results.)
    abs_items = [it for it in by_tier(2) if it["prompt"].startswith("|")]
    assert len(abs_items) >= 20
    for it in abs_items:
        assert val(it["choices"][it["answer"]]) >= 0, it["prompt"]
