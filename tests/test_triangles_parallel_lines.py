"""triangles-parallel-lines cartridge: golden misconception values, an independent re-check of every baked answer,
the manifest bounds walked on baked.json, and value-distinct choices.

The independent check below parses each prompt with its own regexes and finds every answer WITHOUT the
generator's solver: closed forms for the one-step angle facts, a brute-force search over x = 1..180 on a Python
expression built from the prompt text for every equation, and set arithmetic for the similar-triangle items.
It never calls ``G.solve``.
"""
import copy
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "triangles-parallel-lines"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def val(c):
    """A choice's value: an int for a number, the word itself otherwise."""
    return int(c) if c.isdigit() else c


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked wrong values per misconception rule. None = no whole-number value.
# Checked as (label, value) pairs in the solver's raw list (a label may carry two values).
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    ("A triangle has angles 30 and 100 degrees. Third angle?", 50,
     {"USED_360": 230, "FORGOT_ONE": [150, 80], "ADDED_ANGLES": 130, "USED_90": None}),
    ("Triangle angles: 20 and 30 degrees. Third angle?", 130, {"USED_90": 40}),
    ("Right triangle with an angle of 30 degrees. Third angle?", 60,
     {"FORGOT_RIGHT": 150, "USED_360": 240, "ADDED_ANGLES": 120}),
    ("Isosceles triangle, top angle 40 degrees. Each base angle?", 70,
     {"NO_HALF": 140, "HALF_TOP": 20, "SAME_AS_TOP": 40}),
    ("Isosceles triangle, base angles 50 degrees each. Top angle?", 80,
     {"NO_DOUBLE": 130, "SAME_AS_BASE": 50, "ADDED_ANGLES": 100}),
    ("Each angle of an equilateral triangle, in degrees?", 60, {"USED_360": 120, "SPLIT_IN_TWO": 90}),
    ("Triangle angles 40 and 70. Exterior angle at the third?", 110,
     {"INTERIOR_FOR_EXTERIOR": 70, "ONE_REMOTE": [40, 70], "USED_360": 250}),
    ("Exterior angle 120, one remote angle 50. The other?", 70,
     {"ADDED_NOT_SUB": 170, "EQUAL_REMOTES": 50, "INTERIOR_FOR_EXTERIOR": 60}),
    ("Exterior angle is 130. Its adjacent inside angle?", 50,
     {"SAME_AS_EXT": 130, "USED_90": 40, "USED_360": 230}),
    ("Parallel lines. Angle 70. Its corresponding angle?", 70,
     {"SUPP_FOR_EQUAL": 110, "COMP_FOR_EQUAL": 20, "USED_360": 290}),
    ("Lines cross. One angle is 70 degrees. Its vertical angle?", 70,
     {"SUPP_FOR_EQUAL": 110, "COMP_FOR_EQUAL": 20, "USED_360": 290}),
    ("Two lines cross. One angle is 70. The angle next to it?", 110,
     {"EQUAL_FOR_SUPP": 70, "USED_90": 20, "USED_360": 290}),
    ("Parallel lines: corresponding angles are?", "Equal",
     {"SUPP_FOR_EQUAL": "Add to 180", "COMP_FOR_EQUAL": "Add to 90"}),
    ("Parallel lines. Angle 70. Its same-side interior angle?", 110,
     {"EQUAL_FOR_SUPP": 70, "USED_90": 20, "USED_360": 290}),
    ("Parallel lines: same-side interior angles are?", "Add to 180",
     {"EQUAL_FOR_SUPP": "Equal", "USED_90": "Add to 90"}),
    ("Same-side interior angles are 70 and 110. Lines parallel?", "Yes", {"EQUAL_FOR_SUPP": "No"}),
    ("Same-side interior angles are 70 and 70. Lines parallel?", "No", {"EQUAL_FOR_SUPP": "Yes"}),
    ("Same-side interior angles are 40 and 50. Lines parallel?", "No", {"USED_90": "Yes"}),
    ("A triangle has angles 2x, 3x and 4x. x?", 20,
     {"GAVE_ANGLE": 80, "NO_DIVIDE": 180, "SPLIT_EVENLY": 60, "USED_360": 40}),
    ("Triangle angles x, 2x and 3x. Largest angle?", 90,
     {"GAVE_X": 30, "OTHER_ANGLE": 60, "SPLIT_EVENLY": 60, "USED_360": 180}),
    ("Right triangle: 90, x and 2x. x?", 30,
     {"USED_180": 60, "GAVE_ANGLE": 60, "NO_DIVIDE": 90, "SPLIT_EVENLY": 45}),
    ("Exterior angle is 120. Remote angles are x and 2x. x?", 40,
     {"NO_DIVIDE": 120, "GAVE_ANGLE": 80, "USED_180": 60, "INTERIOR_FOR_EXTERIOR": 20}),
    ("Parallel lines: alternate interior angles 2x and 80. x?", 40,
     {"SUPP_FOR_EQUAL": 50, "NO_DIVIDE": 80, "MULTIPLIED_NOT_DIVIDED": 160}),
    ("Parallel lines: corresponding angles x + 30 and 40. x?", 10,
     {"SIGN_SLIP": 70, "SUPP_FOR_EQUAL": 110, "GAVE_ANGLE": 40}),
    ("Parallel lines: corresponding angles 2x + 20 and 100. x?", 40,
     {"NO_DIVIDE": 80, "SIGN_SLIP": 60, "FORGOT_ONE": 50, "SUPP_FOR_EQUAL": 30}),
    ("Parallel lines: same-side interior angles 3x and 30. x?", 50,
     {"EQUAL_FOR_SUPP": 10, "NO_DIVIDE": 150, "USED_90": 20}),
    ("Parallel lines: same-side interior angles x + 40 and 80. x?", 60,
     {"EQUAL_FOR_SUPP": 40, "FORGOT_ONE": 100, "SIGN_SLIP": 140, "USED_90": None}),
    ("Parallel lines: same-side interior angles 2x + 20 and 60. x?", 50,
     {"NO_DIVIDE": 100, "FORGOT_ONE": 60, "SIGN_SLIP": 70, "EQUAL_FOR_SUPP": 20}),
    ("Triangle A: 40 and 60. Triangle B: 60 and 80. Similar?", "Yes", {"NEEDS_SAME_LISTED": "No"}),
    ("Triangle A: 40 and 60. Triangle B: 40 and 50. Similar?", "No", {"ONE_ANGLE_ENOUGH": "Yes"}),
    ("Triangle A: 40 and 60. Triangle B: 30 and 50. Similar?", "No", {"ALL_TRIANGLES_ALIKE": "Yes"}),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(prompt, correct, wrong):
    sol = G.solve(prompt)
    assert sol["correct"] == correct
    for label, v in wrong.items():
        want = v if isinstance(v, list) else [v]
        got = [x for lab, x in sol["wrong"] if lab == label]
        assert got == want, (label, got)


def test_every_misconception_has_a_golden_case():
    covered = {lab for _, _, w in GOLDEN for lab in w}
    assert covered == set(BAKED["misconceptions"])


def test_student_text_fits():
    for k, m in BAKED["misconceptions"].items():
        assert m["teacher"] and 0 < len(m["student"]) <= 80, k


def test_every_declared_misconception_is_used():
    used = {m for it in ITEMS for m in it["misconceptions"] if m} - {"ARITH"}
    assert used == set(BAKED["misconceptions"])


# ---------------------------------------------------------------------------------------------
# Independent solver + bounds walker (own regexes; brute force for the equations)
# ---------------------------------------------------------------------------------------------
EQUAL_NAMES = ("corresponding", "alternate interior", "alternate exterior", "vertical")
SUPP_NAMES = ("same-side interior", "same-side exterior")

TRI_X = (r"^(?:A triangle has angles|Triangle angles) (?P<a>\d*x), (?P<b>\d*x) and (?P<c>\d*x)"
         r"(?: degrees)?\. (?P<ask>x|Largest angle)\?$")
RT_X = r"^(?:Right triangle:|A right triangle has angles) 90, (?P<a>\d*x) and (?P<b>\d*x)\. x\?$"
EXT_X = (r"^(?:Exterior angle is (?P<e>\d+)\. Remote angles are|Triangle: exterior angle (?P<e2>\d+), remote angles)"
         r" (?P<a>\d*x) and (?P<b>\d*x)\. x\?$")
EXT_X3 = r"^Exterior angle is (?P<e>\d+)\. Remote angles: (?P<a>\d+) and x\. x\?$"
PAR_X = r"^Parallel lines: (?P<n>[a-z -]+?) angles (?P<a>\d*x(?: \+ \d+)?) and (?P<b>\d+)\. x\?$"
SIM = r"^(?:Triangle )?A(?::| has) (\d+) and (\d+)\. (?:Triangle )?B(?::| has) (\d+) and (\d+)\. Similar\?$"
PAR_VAL = [
    r"^Parallel lines\. Angle (?P<a>\d+)\. Its (?P<n>[a-z -]+?) angle\?$",
    r"^Parallel lines\. An angle is (?P<a>\d+)\. Its (?P<n>[a-z -]+?) angle\?$",
    r"^Parallel lines\. (?P<n>[A-Za-z -]+?) pair: one is (?P<a>\d+)\. Other\?$",
    r"^(?P<a>\d+) and x are (?P<n>[a-z -]+?) angles of parallel lines\. x\?$",
]
PAR_WORD = [
    r"^Parallel lines: (?P<n>[a-z -]+?) angles are\?$",
    r"^Parallel lines: (?P<n>[a-z -]+?) angles are always\?$",
    r"^Parallel lines cut by a line: (?P<n>[a-z -]+?) angles are\?$",
    r"^In parallel lines, (?P<n>[a-z -]+?) angles are\?$",
]
YESNO = [r"^Same-side interior angles are (\d+) and (\d+)\. Lines parallel\?$",
         r"^Same-side interior: (\d+) and (\d+)\. Are the lines parallel\?$"]


def tens_ok(n, lo=10, hi=170):
    return n % 10 == 0 and lo <= n <= hi


def expr_fn(expr):
    """'2x + 10' -> a function of x. The text is digits, x, + and spaces only (checked)."""
    assert re.fullmatch(r"[0-9x+ ]+", expr), expr
    py = re.sub(r"(\d*)x", lambda m: f"({m.group(1) or '1'}*x)", expr)
    return lambda x: eval(py, {"__builtins__": {}}, {"x": x})


def solve_equation(exprs, relation, total):
    """-> (x, [expr values at x], coefficient of x, constant) by brute force; exactly one whole solution 1..180."""
    fns = [expr_fn(e) for e in exprs]
    if relation == "sum":
        f = lambda x: sum(fn(x) for fn in fns) - total  # noqa: E731
    else:
        f = lambda x: fns[0](x) - fns[1](x)  # noqa: E731
    sols = [x for x in range(1, 181) if f(x) == 0]
    assert len(sols) == 1, (exprs, sols)
    x = sols[0]
    return x, [fn(x) for fn in fns], f(1) - f(0), f(0)


def check_x(exprs, relation, total, ask, bad, angle_total=None):
    """Solve one x equation independently and walk its bounds. Returns (answer, bad)."""
    bad = list(bad)
    try:
        x, values, coef, k = solve_equation(exprs, relation, total)
    except AssertionError as e:
        return None, bad + [f"no single whole solution: {e}"]
    if not tens_ok(x, 10, 90):
        bad.append(f"x = {x} is not a multiple of 10 in 10-90")
    if not 1 <= abs(coef) <= 9:
        bad.append(f"x coefficient {coef} outside 1-9")
    if abs(k) % 10 or abs(k) > 180:
        bad.append(f"constant part {k} is not a tens fact within 180")
    if any(not tens_ok(v) for v in values):
        bad.append(f"an angle is {values}")
    if ask == "Largest angle":
        return max(values), bad
    return x, bad


def independent(prompt):
    """(answer, [violations]) computed from the prompt text alone."""
    bad = []
    lits = [int(n) for n in re.findall(r"(?<![\d])(\d+)(?!\d|x)", prompt)]
    for n in lits:
        if not tens_ok(n):
            bad.append(f"angle literal {n} is not a multiple of 10 in 10-170")
    for c in re.findall(r"(\d+)x", prompt):
        if not 2 <= int(c) <= 9:
            bad.append(f"coefficient {c} outside 2-9")
    nums = [int(n) for n in re.findall(r"\d+", prompt)]

    if m := re.fullmatch(SIM, prompt):
        a, b, c, d = map(int, m.groups())
        ta, tb = 180 - a - b, 180 - c - d
        if ta < 10 or tb < 10:
            bad.append("a third angle under 10")
        ans = "Yes" if sorted((a, b, ta)) == sorted((c, d, tb)) else "No"
    elif "equilateral" in prompt:
        ans = 60
    elif "isosceles" in prompt.lower():
        n = nums[0]
        if "top angle" in prompt:
            if n % 20:
                bad.append("top angle is not an even number of tens")
            ans = (180 - n) // 2
        else:
            ans = 180 - 2 * n
    elif m := re.fullmatch(r"Right triangle with an angle of (\d+) degrees\. Third angle\?|"
                           r"A right triangle has an angle of (\d+)\. Its third angle\?", prompt):
        n = int(next(g for g in m.groups() if g))
        ans = 90 - n
        if n >= 90:
            bad.append("an acute angle is under 90")
    elif m := re.fullmatch(r"(?:A triangle has angles (\d+) and (\d+) degrees\. Third angle\?|"
                           r"Two angles of a triangle are (\d+) and (\d+)\. The third\?|"
                           r"Triangle angles: (\d+) and (\d+) degrees\. Third angle\?)", prompt):
        a, b = [int(g) for g in m.groups() if g]
        ans = 180 - a - b
    elif m := re.fullmatch(r"(?:Triangle angles (\d+) and (\d+)\. Exterior angle at the third\?|"
                           r"Remote angles are (\d+) and (\d+) degrees\. Exterior angle\?)", prompt):
        a, b = [int(g) for g in m.groups() if g]
        ans = a + b
        if ans > 170:
            bad.append("exterior angle over 170")
    elif m := re.fullmatch(r"Exterior angle (\d+), one remote angle (\d+)\. The other\?", prompt):
        ans = int(m[1]) - int(m[2])
    elif m := re.fullmatch(EXT_X3, prompt):
        ans = int(m["e"]) - int(m["a"])  # an unknown angle here, not an x equation: tens, 10-170
    elif m := re.fullmatch(r"A triangle's exterior angle is (\d+)\. Inside angle next to it\?|"
                           r"Exterior angle is (\d+)\. Its adjacent inside angle\?", prompt):
        ans = 180 - int(next(g for g in m.groups() if g))
    elif m := re.fullmatch(TRI_X, prompt):
        ans, bad = check_x([m["a"], m["b"], m["c"]], "sum", 180, m["ask"], bad)
    elif m := re.fullmatch(RT_X, prompt):
        ans, bad = check_x([m["a"], m["b"]], "sum", 90, "x", bad)
    elif m := re.fullmatch(EXT_X, prompt):
        ans, bad = check_x([m["a"], m["b"]], "sum", int(m["e"] or m["e2"]), "x", bad)
    elif m := re.fullmatch(PAR_X, prompt):
        n = m["n"]
        assert n in EQUAL_NAMES or n in SUPP_NAMES, n
        if n in SUPP_NAMES:
            ans, bad = check_x([m["a"], m["b"]], "sum", 180, "x", bad)
        else:
            ans, bad = check_x([m["a"], m["b"]], "equal", None, "x", bad)
    elif m := re.fullmatch(r"Lines cross\. One angle is (\d+) degrees\. Its vertical angle\?|"
                           r"Vertical angles: one is (\d+) degrees\. The other\?", prompt):
        ans = int(next(g for g in m.groups() if g))
        if ans == 90:
            bad.append("90: equal and supplement coincide")
    elif m := re.fullmatch(r"Two lines cross\. One angle is (\d+)\. The angle next to it\?|"
                           r"An angle is (\d+) degrees\. The angle next to it on a line\?", prompt):
        a = int(next(g for g in m.groups() if g))
        ans = 180 - a
        if a == 90:
            bad.append("90: equal and supplement coincide")
    elif any(re.fullmatch(p, prompt) for p in PAR_VAL):
        m = next(re.fullmatch(p, prompt) for p in PAR_VAL if re.fullmatch(p, prompt))
        n, a = m["n"].lower(), int(m["a"])
        assert n in EQUAL_NAMES or n in SUPP_NAMES, n
        ans = a if n in EQUAL_NAMES else 180 - a
        if a == 90:
            bad.append("90: equal and supplement coincide")
    elif any(re.fullmatch(p, prompt) for p in PAR_WORD):
        m = next(re.fullmatch(p, prompt) for p in PAR_WORD if re.fullmatch(p, prompt))
        n = m["n"]
        assert n in EQUAL_NAMES or n in SUPP_NAMES, n
        ans = "Equal" if n in EQUAL_NAMES else "Add to 180"
    elif any(re.fullmatch(p, prompt) for p in YESNO):
        m = next(re.fullmatch(p, prompt) for p in YESNO if re.fullmatch(p, prompt))
        a, b = int(m[1]), int(m[2])
        ans = "Yes" if a + b == 180 else "No"
        if a == 90 and b == 90:
            bad.append("90 and 90: equal and supplementary coincide")
    else:
        raise AssertionError(f"unknown prompt shape {prompt!r}")
    if isinstance(ans, int) and not tens_ok(ans):
        bad.append(f"answer {ans} is not a multiple of 10 in 10-170")
    return ans, bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    ans, _ = independent(item["prompt"])
    assert val(item["choices"][item["answer"]]) == ans, item["prompt"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    _, bad = independent(item["prompt"])
    assert bad == [], item["prompt"]
    for c in item["choices"]:
        v = val(c)
        assert isinstance(v, str) or 0 < v <= 999, c


@pytest.mark.parametrize("prompt,expect_bad", [
    ("A triangle has angles 30 and 100 degrees. Third angle?", False),
    ("A triangle has angles 35 and 100 degrees. Third angle?", True),              # 35 is not tens
    ("Right triangle with an angle of 30 degrees. Third angle?", False),
    ("Right triangle with an angle of 100 degrees. Third angle?", True),           # no acute angle of 100
    ("Isosceles triangle, top angle 40 degrees. Each base angle?", False),
    ("Isosceles triangle, top angle 30 degrees. Each base angle?", True),          # (180 - 30) / 2 = 75
    ("Remote angles are 100 and 90 degrees. Exterior angle?", True),               # 190
    ("Triangle angles 40 and 70. Exterior angle at the third?", False),
    ("Parallel lines. Angle 90. Its corresponding angle?", True),                  # 90: equal = supplement
    ("Parallel lines. Angle 75. Its corresponding angle?", True),
    ("A triangle has angles x, 2x and 4x. x?", True),                              # 7x = 180
    ("A triangle has angles 2x, 3x and 4x. x?", False),
    ("A triangle has angles 12x, x and x. x?", True),                              # coefficient 12 (x = 12.8)
    ("Parallel lines: same-side interior angles 3x and 20. x?", True),             # 3x = 160
    ("Parallel lines: corresponding angles x + 30 and 20. x?", True),              # x = -10
    ("Parallel lines: corresponding angles 2x + 15 and 95. x?", True),             # 15 is not tens
    ("Right triangle: 90, x and 2x. x?", False),
    ("Right triangle: 90, x and 3x. x?", True),                                    # 4x = 90
    ("Same-side interior angles are 90 and 90. Lines parallel?", True),
    ("Triangle A: 40 and 60. Triangle B: 60 and 80. Similar?", False),
    ("Triangle A: 100 and 80. Triangle B: 60 and 80. Similar?", True),             # no third angle left
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(independent(prompt)[1]) == expect_bad, prompt


def test_bounds_checker_rejects_something():
    """Disproof: the checker can fail, and the answer check can catch a wrong baked answer."""
    assert independent("A triangle has angles 35 and 100 degrees. Third angle?")[1]
    assert independent("A triangle has angles x, 2x and 4x. x?")[1]
    item = copy.deepcopy(ITEMS[0])
    item["answer"] = (item["answer"] + 1) % len(item["choices"])
    assert val(item["choices"][item["answer"]]) != independent(item["prompt"])[0]


# ---------------------------------------------------------------------------------------------
# Choices: never two right doors; labels honest; shape of the content
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_distinct_in_value(item):
    vals = [val(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert len(vals) in (2, 3, 4)
    assert len({type(v) for v in vals}) == 1, "numbers and words mixed in one item"


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_word_choices_have_exactly_one_true(item):
    """Word doors: independent truth says which is right; every other word is false for the item."""
    vals = [val(c) for c in item["choices"]]
    if not isinstance(vals[0], str):
        return
    truth, _ = independent(item["prompt"])
    assert vals.count(truth) == 1, item["prompt"]
    if truth in ("Yes", "No"):
        assert set(vals) == {"Yes", "No"}
    else:
        assert set(vals) == {"Equal", "Add to 180", "Add to 90"}
        # only one of the three can describe the pair
        assert truth in ("Equal", "Add to 180")


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    sol = G.solve(item["prompt"])
    produced = [(lab, v) for lab, v in sol["wrong"] if v is not None]
    values = {v for _, v in produced}
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one misconception distractor"
    assert sol["correct"] not in values, "a wrong rule lands on the answer"
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            assert val(c) == sol["correct"]
        elif m == "ARITH":
            assert val(c) not in values, f"ARITH {c} is really a misconception value"
        else:
            assert (m, val(c)) in produced, (m, c)


def test_arith_share_is_a_minority():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 1 / 3
    for t in range(1, 6):
        ct = Counter(m for it in by_tier(t) for m in it["misconceptions"] if m)
        assert ct["ARITH"] / sum(ct.values()) <= 0.4, t


def answer_ranks(items):
    """For each all-number item: how many choices are smaller than the right one (0 = it is the smallest)."""
    nums = [it for it in items if all(c.isdigit() for c in it["choices"])]
    return [sum(int(c) < int(it["choices"][it["answer"]]) for c in it["choices"]) for it in nums]


def position_gives_it_away(ranks):
    """Mostly the smallest, or hardly ever in the middle: a kid could pick by size."""
    return ranks.count(0) / len(ranks) > 0.6 or sum(r in (1, 2) for r in ranks) / len(ranks) < 0.3


def test_no_tell_in_the_wrong_values():
    for t in range(1, 6):
        assert not position_gives_it_away(answer_ranks(by_tier(t))), t


def test_tell_checker_rejects_planted_tells():
    """Disproof: items whose right number is always the smallest (or never in the middle) are flagged."""
    always_smallest = [{"choices": ["60", "150", "120", "330"], "answer": 0}] * 10
    never_middle = [{"choices": ["60", "150", "120", "330"], "answer": 0},
                    {"choices": ["60", "150", "120", "330"], "answer": 3}] * 5
    assert position_gives_it_away(answer_ranks(always_smallest))
    assert position_gives_it_away(answer_ranks(never_middle))


def test_at_most_one_impossible_angle_per_item():
    for it in ITEMS:
        nums = [int(c) for c in it["choices"] if c.isdigit()]
        assert sum(n > 180 for n in nums) <= 1, it["choices"]


def test_balanced_positions_per_choice_count():
    for t in range(1, 6):
        groups = {}
        for it in by_tier(t):
            groups.setdefault(len(it["choices"]), []).append(it["answer"])
        for n, answers in groups.items():
            cnt = Counter(answers)
            for pos in range(n):
                assert 0.5 / n * len(answers) <= cnt[pos] <= 1.5 / n * len(answers), (t, n, pos)


def test_no_grade_drift_or_charset_traps():
    banned = ["°", "≈", "∠", "∥", "′", "→", "∞", "²", "³", "√", "^", "½", "sin", "cos", "tan", "f(x)", "quadratic"]
    for it in ITEMS:
        text = " ".join([it["prompt"], it["explanation"], *it["choices"]])
        assert not any(b in text for b in banned), it["prompt"]
    for m in BAKED["misconceptions"].values():
        assert not any(b in m["student"] + m["teacher"] for b in ("°", "∠", "∥", "′", "→"))


def test_tier_shapes():
    def count(items, pred):
        return sum(1 for it in items if pred(it["prompt"]))

    t1 = by_tier(1)
    assert count(t1, lambda p: "ight triangle" in p) == 8
    assert count(t1, lambda p: "sosceles" in p and "top angle" in p) == 7
    assert count(t1, lambda p: "sosceles" in p and "top angle" not in p) == 7
    assert count(t1, lambda p: "equilateral" in p) == 2
    t2 = by_tier(2)
    assert count(t2, lambda p: p.startswith(("Triangle angles", "Remote angles are"))) == 14
    assert count(t2, lambda p: "one remote" in p or "Remote angles:" in p) == 16
    assert count(t2, lambda p: "inside angle" in p or "Inside angle" in p) == 10
    t3 = by_tier(3)
    assert sum(len(it["choices"]) == 3 for it in t3) == 4
    assert all(it["choices"][it["answer"]] == "Equal" for it in t3 if len(it["choices"]) == 3)
    assert count(t3, lambda p: p.startswith(("Lines cross. One", "Vertical angles"))) == 3
    assert count(t3, lambda p: "next to it" in p) == 4
    assert count(t3, lambda p: "same-side interior" in p.lower()) == 9
    t4 = by_tier(4)
    assert sum(it["choices"] == ["Yes", "No"] or it["choices"] == ["No", "Yes"] for it in t4) == 8
    assert sum(len(it["choices"]) == 3 for it in t4) == 6
    assert sum(len(it["choices"]) == 4 for it in t4) == 26
    ans4 = Counter(it["choices"][it["answer"]] for it in t4 if it["choices"][it["answer"]] in ("Yes", "No"))
    assert ans4["Yes"] == 4 and ans4["No"] == 4
    t5 = by_tier(5)
    assert count(t5, lambda p: p.startswith(("A triangle has angles", "Triangle angles")) and "x" in p) == 8
    assert count(t5, lambda p: "ight triangle" in p) == 4
    assert count(t5, lambda p: p.startswith(("Exterior angle", "Triangle: exterior"))) == 4
    assert count(t5, lambda p: p.startswith("Parallel lines:")) == 14
    assert count(t5, lambda p: "Similar?" in p) == 10
    used5 = Counter(m for it in t5 for m in it["misconceptions"] if m)
    for key in ("GAVE_ANGLE", "NO_DIVIDE", "SUPP_FOR_EQUAL", "EQUAL_FOR_SUPP", "NEEDS_SAME_LISTED", "SIGN_SLIP"):
        assert used5[key], key


def test_facts_are_varied_within_a_tier():
    """Distinct facts first: a repeat of the same numbers (in other words) only when the facts run out."""
    t1 = [it["prompt"] for it in by_tier(1) if it["prompt"].startswith(("A triangle", "Two angles", "Triangle angles"))]
    assert len({tuple(re.findall(r"\d+", p)) for p in t1}) == len(t1) == 16
    t2 = [it["prompt"] for it in by_tier(2) if "one remote" in it["prompt"] or "Remote angles:" in it["prompt"]]
    assert len({tuple(re.findall(r"\d+", p)) for p in t2}) == len(t2) == 16
    for t in (3, 4):
        words = Counter(re.search(r"(corresponding|alternate \w+|same-side \w+|vertical)", it["prompt"])[1]
                        for it in by_tier(t) if len(it["choices"]) == 3)
        assert all(v <= 2 for v in words.values()), (t, words)


def test_bounds_string_declared():
    b = BAKED["bounds"]
    assert "multiple of 10" in b and "180" in b and "90" in b and "tens" in b and "exterior" in b


def test_generate_is_deterministic():
    m = {k: BAKED[k] for k in ("items_per_tier", "tiers")}
    a = G.generate(m, random.Random(BAKED["seed"]))
    b = G.generate(m, random.Random(BAKED["seed"]))
    assert a == b
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == a


def test_every_template_matches_exactly_one_handler():
    for it in ITEMS:
        G.solve(it["prompt"])  # raises when 0 or 2+ templates match


def test_number_in_prompt_is_not_a_shortcut():
    """Neither "pick the number you were given" nor "pick 180 minus it" may win a whole tier (lead audit)."""
    for t in (3, 4):
        nums = [it for it in by_tier(t) if all(c.isdigit() for c in it["choices"])]
        same = sum(int(it["choices"][it["answer"]]) in {int(n) for n in re.findall(r"\d+", it["prompt"])}
                   for it in nums)
        assert 0.25 <= same / len(nums) <= 0.75, (t, same, len(nums))


def test_at_most_four_vertical_items():
    assert sum("ertical" in it["prompt"] for it in ITEMS) <= 4
    for it in ITEMS:
        if "ertical" in it["prompt"]:
            assert "arallel" not in it["prompt"] and "Vertical angles are always equal" in it["explanation"]
