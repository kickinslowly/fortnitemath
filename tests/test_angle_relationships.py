"""angle-relationships cartridge: golden misconception values, an independent re-check of every baked answer,
the manifest bounds walked on baked.json, and value-distinct choices.

The independent check below parses each prompt with its own regexes and finds every answer WITHOUT the
generator's solver: closed forms for the one-step angle facts, and for every equation prompt a brute-force
search over x = 1..180 on a Python expression built from the prompt text. It never calls ``G.solve``.
"""
import copy
import json
import random
import re
from collections import Counter
from fractions import Fraction as F

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "angle-relationships"
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
# Golden cases: hand-worked wrong values per misconception rule. None = no whole-number value; a negative value
# is what the rule gives raw (the generator never offers it as a door).
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    ("Complement of an angle of 30 degrees?", 60,
     {"COMP_SUPP_SWAP": 150, "ADDED_NOT_SUB": 120, "USED_360": 330}),
    ("Supplement of an angle of 70 degrees?", 110,
     {"COMP_SUPP_SWAP": 20, "ADDED_NOT_SUB": 250, "USED_360": 290}),
    ("Supplement of an angle of 130 degrees?", 50, {"COMP_SUPP_SWAP": 40, "USED_360": 230}),
    ("Lines cross. One angle is 40 degrees. Its vertical angle?", 40,
     {"SUPP_FOR_VERT": 140, "COMP_FOR_VERT": 50}),
    ("Vertical angles: one is 120 degrees. The other?", 120, {"SUPP_FOR_VERT": 60, "COMP_FOR_VERT": 30}),
    ("Lines cross. One angle is 40 degrees. The angle next to it?", 140,
     {"VERT_FOR_ADJ": 40, "COMP_FOR_SUPP": 50}),
    ("Adjacent angles on a line: one is 130 degrees. The other?", 50,
     {"VERT_FOR_ADJ": 130, "COMP_FOR_SUPP": 40}),
    ("Two angles that add to 90 are?", "Complementary",
     {"COMP_SUPP_SWAP": "Supplementary", "POSITION_WORD_FOR_SUM": "Vertical"}),
    ("Angles of 40 and 140 degrees are?", "Supplementary",
     {"COMP_SUPP_SWAP": "Complementary", "POSITION_WORD_FOR_SUM": "Vertical"}),
    ("Complementary angles add to how many degrees?", 90, {"COMP_SUPP_SWAP": 180, "USED_360": 360}),
    ("A straight angle measures how many degrees?", 180, {"COMP_SUPP_SWAP": 90, "USED_360": 360}),
    ("A right angle is split into 20, 30 and x degrees. x?", 40,
     {"FORGOT_ONE": 70, "WRONG_TOTAL": 130, "ADDED_PARTS": 50}),
    ("Angles 50, 60 and x make a straight line. x in degrees?", 70,
     {"FORGOT_ONE": 130, "WRONG_TOTAL": -20, "ADDED_PARTS": 110}),
    ("x and 2x are supplementary. x?", 60,
     {"ANGLE_NOT_X": 120, "NO_DIVIDE": 180, "WRONG_TOTAL": 30, "SPLIT_EVENLY": 90}),
    ("Angles 4x and 5x make a right angle. x?", 10,
     {"ANGLE_NOT_X": 50, "NO_DIVIDE": 90, "WRONG_TOTAL": 20, "SPLIT_EVENLY": 45}),
    ("x + 20 and 50 are complementary. x?", 20,
     {"FORGOT_ONE": 40, "SIGN_SLIP": 60, "WRONG_TOTAL": 110, "ADDED_PARTS": 70}),
    ("2x and 50 are complementary. x?", 20, {"NO_DIVIDE": 40, "WRONG_TOTAL": 65, "DIVIDED_ONE_TERM": -5}),
    ("4x and 20 are supplementary. x?", 40, {"NO_DIVIDE": 160, "WRONG_TOTAL": None, "DIVIDED_ONE_TERM": 25}),
    ("Vertical angles: 2x + 10 and 70. x?", 30,
     {"SUPP_FOR_VERT": 50, "ANGLE_NOT_X": 70, "SIGN_SLIP": 40, "NO_DIVIDE": 60}),
    ("4x and 2x form a straight line. Larger angle?", 120,
     {"GAVE_X": 30, "OTHER_ANGLE": 60, "WRONG_TOTAL": 60}),
    ("Complementary angles: 3x and 6x. Smaller angle?", 30,
     {"GAVE_X": 10, "OTHER_ANGLE": 60, "WRONG_TOTAL": 60}),
    ("Lines cross. Adjacent angles: 2x and 100. x?", 40,
     {"VERT_FOR_ADJ": 50, "COMP_FOR_SUPP": -5, "NO_DIVIDE": 80}),
    ("2x + 10 and 50 are supplementary. x?", 60,
     {"FORGOT_ONE": 65, "SIGN_SLIP": 70, "NO_DIVIDE": 120, "WRONG_TOTAL": 15}),
    ("x, 2x and 3x make a straight line. Largest angle?", 90,
     {"GAVE_X": 30, "OTHER_ANGLE": 60, "WRONG_TOTAL": 45}),
]
# word items with two wrong values under one label: checked as (label, value) pairs
GOLDEN_PAIRS = [
    ("Angles across from each other where lines cross are?", "Vertical",
     [("VERT_ADJ_SWAP", "Adjacent"), ("SUM_WORD_FOR_POSITION", "Supplementary"),
      ("SUM_WORD_FOR_POSITION", "Complementary")]),
    ("Angles that share a side and a vertex are?", "Adjacent",
     [("VERT_ADJ_SWAP", "Vertical"), ("SUM_WORD_FOR_POSITION", "Supplementary"),
      ("SUM_WORD_FOR_POSITION", "Complementary")]),
    ("Vertical angles are always?", "Equal",
     [("SUPP_FOR_VERT", "Supplementary"), ("COMP_FOR_VERT", "Complementary"), ("VERT_ADJ_SWAP", "Adjacent")]),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(prompt, correct, wrong):
    sol = G.solve(prompt)
    assert sol["correct"] == correct
    got = dict(sol["wrong"])
    for label, v in wrong.items():
        assert got[label] == v, label


@pytest.mark.parametrize("prompt,correct,pairs", GOLDEN_PAIRS, ids=[g[0] for g in GOLDEN_PAIRS])
def test_golden_pairs(prompt, correct, pairs):
    sol = G.solve(prompt)
    assert sol["correct"] == correct
    assert sol["wrong"] == pairs


def test_every_misconception_has_a_golden_case():
    covered = {lab for _, _, w in GOLDEN for lab in w} | {lab for _, _, p in GOLDEN_PAIRS for lab, _ in p}
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
WORD_PROMPTS = {
    "Two angles that add to 90 are?": "Complementary",
    "Two angles make a right angle together. They are?": "Complementary",
    "Two angles that add to 180 are?": "Supplementary",
    "Two angles make a straight line together. They are?": "Supplementary",
    "Angles across from each other where lines cross are?": "Vertical",
    "Angles that share a side and a vertex are?": "Adjacent",
    "Vertical angles are always?": "Equal",
}
FACT_PROMPTS = {
    "Complementary angles add to how many degrees?": 90,
    "Supplementary angles add to how many degrees?": 180,
    "A straight angle measures how many degrees?": 180,
    "A right angle measures how many degrees?": 90,
}
TWO = (r"^(?:Angles )?(?P<a>[^,]+?) and (?P<b>[^,]+?) "
       r"(?:are (?P<w>supplementary|complementary)|(?:make|form) a (?P<s>straight line|right angle))"
       r"\. (?P<ask>x|Larger angle|Smaller angle)\?$")
TWO_NAMED = (r"^(?P<w>Supplementary|Complementary) angles(?: are|:) (?P<a>[^,]+?) and (?P<b>[^,]+?)"
             r"\. (?P<ask>x|Larger angle|Smaller angle)\?$")
VERTICAL = r"^(?:Lines cross\. )?Vertical angles(?::| are) (?P<a>[^,]+?) and (?P<b>[^,]+?)(?: degrees)?\. x\?$"
ADJACENT = r"^(?:Lines cross\. Adjacent angles|Adjacent angles on a line): (?P<a>.+?) and (?P<b>.+?)\. x\?$"
THREE = r"^(?:Straight line: )?(?P<a>\d*x), (?P<b>\d*x) and (?P<c>\d*x)(?: make a straight line)?\. Largest angle\?$"


def expr_fn(expr):
    """'2x + 10' -> a function of x. The text is digits, x, + and spaces only (checked)."""
    assert re.fullmatch(r"[0-9x+ ]+", expr), expr
    py = re.sub(r"(\d*)x", lambda m: f"({m.group(1) or '1'}*x)", expr)
    return lambda x: eval(py, {"__builtins__": {}}, {"x": x})


def solve_equation(exprs, relation, total):
    """-> (x, [expr values at x], coef, k) by brute force; asserts exactly one whole solution in 1..180."""
    fns = [expr_fn(e) for e in exprs]
    if relation == "sum":
        f = lambda x: sum(fn(x) for fn in fns) - total  # noqa: E731
    else:
        f = lambda x: fns[0](x) - fns[1](x)  # noqa: E731
    sols = [x for x in range(1, 181) if f(x) == 0]
    assert len(sols) == 1, (exprs, sols)
    x = sols[0]
    return x, [fn(x) for fn in fns], f(1) - f(0), f(0)


def independent(prompt):
    """(answer, [violations]) computed from the prompt text alone."""
    bad = []
    nums = [int(n) for n in re.findall(r"(\d+)(?!\d|x)", prompt)]  # angle literals: digits not before an x
    for n in nums:
        if not (n % 10 == 0 and 10 <= n <= 180):
            bad.append(f"angle literal {n} is not a multiple of 10 in 10-180")
    for c in re.findall(r"(\d+)x", prompt):
        if not 2 <= int(c) <= 9:
            bad.append(f"coefficient {c} outside 2-9")

    if m := re.fullmatch(r"Complement of an angle of (\d+) degrees\?|Angles (\d+) and x are complementary\. x in degrees\?|"
                         r"Two angles are complementary\. One is (\d+) degrees\. The other\?", prompt):
        a = int(next(g for g in m.groups() if g))
        ans = 90 - a
        if a >= 90:
            bad.append("a complement needs an angle under 90")
    elif m := re.fullmatch(r"Supplement of an angle of (\d+) degrees\?|Angles (\d+) and x are supplementary\. x in degrees\?|"
                           r"Two angles are supplementary\. One is (\d+) degrees\. The other\?", prompt):
        a = int(next(g for g in m.groups() if g))
        ans = 180 - a
        if a == 90 or a >= 180:
            bad.append("a supplement of 90 is 90; 180 leaves nothing")
    elif m := re.fullmatch(r"Lines cross\. One angle is (\d+) degrees\. Its vertical angle\?|"
                           r"Vertical angles: one is (\d+) degrees\. The other\?|"
                           r"Angle A is (\d+) degrees\. Its vertical angle B is\?", prompt):
        a = int(next(g for g in m.groups() if g))
        ans = a
        if a == 90:
            bad.append("vertical angle of 90: the supplement distractor is the answer")
    elif m := re.fullmatch(r"Lines cross\. One angle is (\d+) degrees\. (?:The angle next to it|An adjacent angle)\?|"
                           r"Adjacent angles on a line: one is (\d+) degrees\. The other\?", prompt):
        a = int(next(g for g in m.groups() if g))
        ans = 180 - a
        if a == 90:
            bad.append("adjacent angle of 90: the vertical distractor is the answer")
    elif prompt in WORD_PROMPTS:
        ans = WORD_PROMPTS[prompt]
    elif prompt in FACT_PROMPTS:
        ans = FACT_PROMPTS[prompt]
    elif m := re.fullmatch(r"Angles of (\d+) and (\d+) degrees are\?", prompt):
        s = int(m[1]) + int(m[2])
        ans = {90: "Complementary", 180: "Supplementary"}.get(s)
        if ans is None:
            bad.append(f"{m[1]} + {m[2]} is neither 90 nor 180")
        if m[1] == m[2]:
            bad.append("equal angles: vertical is possible")
    elif m := re.fullmatch(r"A (right|straight) angle is split into (\d+), (\d+) and x degrees\. x\?|"
                           r"Angles (\d+), (\d+) and x make a (right angle|straight line)\. x in degrees\?", prompt):
        g = m.groups()
        total = 90 if "right" in (g[0] or g[5]) else 180
        a, b = int(g[1] or g[3]), int(g[2] or g[4])
        ans = total - a - b
        if ans < 10:
            bad.append(f"the parts leave {ans}")
    elif (m := re.fullmatch(TWO, prompt)) or (m := re.fullmatch(TWO_NAMED, prompt)):
        d = m.groupdict()
        total = 180 if (d.get("w") or "").lower().startswith("supp") or d.get("s") == "straight line" else 90
        ans, bad = solved_equation(prompt, [d["a"], d["b"]], "sum", total, d["ask"], bad)
    elif m := re.fullmatch(VERTICAL, prompt):
        ans, bad = solved_equation(prompt, [m["a"], m["b"]], "equal", None, "x", bad)
    elif m := re.fullmatch(ADJACENT, prompt):
        ans, bad = solved_equation(prompt, [m["a"], m["b"]], "sum", 180, "x", bad)
    elif m := re.fullmatch(THREE, prompt):
        ans, bad = solved_equation(prompt, [m["a"], m["b"], m["c"]], "sum", 180, "Largest angle", bad)
    else:
        raise AssertionError(f"unknown prompt shape {prompt!r}")
    if isinstance(ans, int) and not (ans % 10 == 0 and 10 <= ans <= 180):
        bad.append(f"answer {ans} is not a multiple of 10 in 10-180")
    return ans, bad


def solved_equation(prompt, exprs, relation, total, ask, bad):
    bad = list(bad)
    try:
        x, values, coef, k = solve_equation(exprs, relation, total)
    except AssertionError as e:
        return None, bad + [f"no single whole solution: {e}"]
    if not (x % 10 == 0 and 10 <= x <= 170 and (x <= 90 or abs(coef) == 1)):
        bad.append(f"x = {x} is not a multiple of 10 in 10-170 (10-90 once it has a coefficient)")
    if not (1 <= abs(coef) <= 9):
        bad.append(f"x total coefficient {coef} outside 1-9")
    if abs(k) % 10 or abs(k) > 180:
        bad.append(f"constant part {k} is not a tens fact within 180")
    if any(not (v % 10 == 0 and 10 <= v <= 180) for v in values):
        bad.append(f"an angle is {values}")
    if len(set(values)) != len(values) and ask != "x":
        bad.append("a larger/smaller question about equal angles")
    if ask == "x":
        return x, bad
    if ask.startswith("Larger") or ask.startswith("Largest"):
        return max(values), bad
    return min(values), bad


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
    ("Complement of an angle of 30 degrees?", False),
    ("Complement of an angle of 35 degrees?", True),                      # not a multiple of 10
    ("Complement of an angle of 100 degrees?", True),                     # no complement
    ("Supplement of an angle of 90 degrees?", True),                      # 90: complement distractor collides
    ("Supplement of an angle of 190 degrees?", True),                     # over 180
    ("Lines cross. One angle is 90 degrees. Its vertical angle?", True),
    ("Angles of 40 and 50 degrees are?", False),
    ("Angles of 40 and 60 degrees are?", True),                      # adds to 100
    ("Angles of 90 and 90 degrees are?", True),                      # equal: could be vertical
    ("A right angle is split into 50, 50 and x degrees. x?", True),  # nothing left
    ("A straight angle is split into 60, 70 and x degrees. x?", False),
    ("x and 2x are supplementary. x?", False),
    ("x and 3x are supplementary. x?", True),                        # x = 45
    ("Angles 5x and 5x make a straight line. x?", True),             # 10x = 180, x = 18
    ("Angles 3x and 20 make a right angle. x?", True),               # 3x = 70
    ("x + 100 and 100 are supplementary. x?", True),                 # x = -20: no solution in 1-180
    ("Vertical angles: 2x + 15 and 75. x?", True),                   # 15 is not a multiple of 10
    ("Vertical angles: 12x + 10 and 130. x?", True),                 # coefficient 12
    ("Vertical angles: 2x + 10 and 70. x?", False),
    ("Lines cross. Adjacent angles: 3x and 150. x?", False),
    ("Lines cross. Adjacent angles: 4x and 120. x?", True),          # 4x = 60, x = 15
    ("x, 2x and 3x make a straight line. Largest angle?", False),
    ("x, 2x and 4x make a straight line. Largest angle?", True),     # 7x = 180
    ("Supplementary angles: 2x and x. Larger angle?", False),
    ("3x and 3x form a straight line. Larger angle?", True),         # equal angles
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(independent(prompt)[1]) == expect_bad, prompt


def test_bounds_checker_rejects_something():
    """Disproof: the checker can fail, and the answer check can catch a wrong baked answer."""
    assert independent("Complement of an angle of 35 degrees?")[1]
    assert independent("Angles 3x and 20 make a right angle. x?")[1]
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
    assert len(vals) in (3, 4)
    assert len({type(v) for v in vals}) == 1, "numbers and words mixed in one item"


def test_choice_value_parser_sees_equal_values():
    assert val("60") == val("60") and val("60") != val("160") and val("Equal") != val("Vertical")


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
    for t in (1, 2, 4, 5):
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


def test_no_grade_8_drift_or_charset_traps():
    banned = ["parallel", "transversal", "triangle", "slope", "Pythagor", "degree sign", "°", "≈", "½", "^", "√"]
    for it in ITEMS:
        text = " ".join([it["prompt"], it["explanation"], *it["choices"]])
        assert not any(b in text for b in banned), it["prompt"]
    for m in BAKED["misconceptions"].values():
        assert "°" not in m["student"] + m["teacher"]


def test_tier_shapes():
    t1 = [it["prompt"] for it in by_tier(1)]
    assert sum("omplement" in p and "upplement" not in p for p in t1) == 14
    assert sum("upplement" in p for p in t1) == 26
    t2 = [it["prompt"] for it in by_tier(2)]
    assert sum("ertical" in p for p in t2) == 20
    assert sum("djacent" in p or "next to it" in p for p in t2) == 20
    t3 = by_tier(3)
    assert sum(len(it["choices"]) == 3 for it in t3) == 9
    assert sum("split" in it["prompt"] or "make a" in it["prompt"] for it in t3) >= 24
    assert any(it["answer"] is not None and it["choices"][it["answer"]] == "Equal" for it in t3)
    t4 = [it["prompt"] for it in by_tier(4)]
    assert all("x" in p for p in t4)
    assert sum(p.startswith(("x +", "Supplementary angles are x +", "Complementary angles are x +")) for p in t4) >= 10
    assert sum(bool(re.search(r"\dx and \d+(?!\d|x)", p)) for p in t4) >= 10
    t5 = [it["prompt"] for it in by_tier(5)]
    assert sum("Vertical angles" in p for p in t5) == 10
    assert sum(p.endswith(("Larger angle?", "Smaller angle?")) for p in t5) == 10
    assert sum("Adjacent angles" in p for p in t5) == 8
    assert sum(p.endswith("Largest angle?") for p in t5) == 6
    used5 = Counter(m for it in by_tier(5) for m in it["misconceptions"] if m)
    for key in ("GAVE_X", "OTHER_ANGLE", "SIGN_SLIP", "NO_DIVIDE", "SUPP_FOR_VERT", "VERT_FOR_ADJ"):
        assert used5[key], key


def test_facts_are_varied_within_a_tier():
    """Distinct facts first: a repeat of the same numbers (in other words) only when the facts run out."""
    t1 = [it["prompt"] for it in by_tier(1)]
    kinds = {(("c" if "omplement" in p else "s"), re.findall(r"\d+", p)[0]) for p in t1}
    assert len(kinds) == 24  # 8 complements + 16 supplements
    t2 = [it["prompt"] for it in by_tier(2)]
    for word in ("ertical", "djacent|next to it"):
        angles = {re.findall(r"\d+", p)[0] for p in t2 if re.search(word, p)}
        assert len(angles) >= 14, word
    t3 = [it["prompt"] for it in by_tier(3) if re.search(r"\d+, \d+", it["prompt"])]
    assert len({tuple(re.findall(r"\d+", p)) + (("r" if "right" in p else "s"),) for p in t3}) == len(t3)


def test_bounds_string_declared():
    b = BAKED["bounds"]
    assert "multiple of 10" in b and "180" in b and "90" in b and "tens" in b


def test_generate_is_deterministic():
    m = {k: BAKED[k] for k in ("items_per_tier", "tiers")}
    a = G.generate(m, random.Random(BAKED["seed"]))
    b = G.generate(m, random.Random(BAKED["seed"]))
    assert a == b
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == a


def test_every_template_matches_exactly_one_handler():
    for it in ITEMS:
        G.solve(it["prompt"])  # raises when 0 or 2+ templates match
