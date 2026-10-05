"""fraction-division cartridge: golden misconception rules, an independent re-check of every baked item,
and the PROTOCOL §4b bounds walked on baked.json.

The independent check reads each prompt with this file's own regexes, computes the quotient with
``fractions.Fraction`` and reads each choice with its own parser -- never the generator's solver.
"""
import json
import re
from fractions import Fraction
from math import gcd

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "fraction-division"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Independent prompt reader: (dividend, divisor, unit, is_story) with operands as (num, den)
# ---------------------------------------------------------------------------------------------
OP = r"\d+(?:/\d+)?"
PATTERNS = [
    # (regex, unit, story?)  named groups x = dividend, y = divisor
    (rf"^(?P<x>{OP}) ÷ (?P<y>{OP})$", "", False),
    (r"^How many (?P<y>1/\d+)s are in (?P<x>\d+)\?$", "", False),
    (rf"^Split (?P<x>{OP}) into (?P<y>\d+) equal parts\. How big is each\?$", "", False),
    (rf"^(?P<x>{OP}) cups of rice, (?P<y>{OP}) cup per bowl\. How many bowls\?$", "", True),
    (rf"^An? (?P<x>{OP}) m rope is cut into (?P<y>{OP}) m pieces\. How many pieces\?$", "", True),
    (rf"^(?P<x>{OP}) lb of trail mix split into (?P<y>{OP}) lb bags\. How many bags\?$", "", True),
    (rf"^(?P<x>{OP}) hours of practice, (?P<y>{OP}) hour per drill\. How many drills\?$", "", True),
    (rf"^(?P<x>{OP}) cup of flour, (?P<y>{OP}) cup per batch\. How many batches\?$", "", True),
    (rf"^How many (?P<y>{OP}) mi laps make a (?P<x>{OP}) mi run\?$", "", True),
    (rf"^(?P<x>{OP}) lb of fudge shared equally by (?P<y>\d+) kids\. Lb each\?$", "lb", True),
    (rf"^(?P<y>\d+) friends split (?P<x>{OP}) of a pizza equally\. How much each\?$", "", True),
    (rf"^(?P<x>{OP}) gal of paint covers (?P<y>\d+) walls equally\. Gal per wall\?$", "gal", True),
    (rf"^(?P<y>{OP}) of a bag of dog food weighs (?P<x>{OP}) lb\. Whole bag\?$", "lb", True),
    (rf"^Rectangle: area (?P<x>{OP}) sq ft, width (?P<y>{OP}) ft\. Length\?$", "ft", True),
]


def operand(s):
    if "/" in s:
        n, d = s.split("/")
        return (int(n), int(d))
    return (int(s), 1)


def read_prompt(prompt):
    for rx, unit, story in PATTERNS:
        m = re.match(rx, prompt)
        if m:
            return operand(m["x"]), operand(m["y"]), unit, story
    raise AssertionError(f"unreadable prompt {prompt!r}")


def read_choice(text, unit):
    if unit:
        assert text.endswith(" " + unit), (text, unit)
        text = text[: -len(unit) - 1]
    m = re.fullmatch(r"(?:(\d+) )?(\d+)/(\d+)|(\d+)", text)
    assert m, f"unreadable choice {text!r}"
    if m[4]:
        return Fraction(int(m[4]))
    w = int(m[1]) if m[1] else 0
    return w + Fraction(int(m[2]), int(m[3]))


def canonical(text, unit):
    """True when the text is simplest form: n, a/b (a < b) or w a/b (w >= 1, a < b), gcd(a, b) = 1."""
    if unit:
        text = text[: -len(unit) - 1]
    m = re.fullmatch(r"(?:([1-9]\d*) )?(\d+)/(\d+)|([1-9]\d*)", text)
    if not m:
        return False
    if m[4]:
        return True
    a, b = int(m[2]), int(m[3])
    return 1 <= a < b and gcd(a, b) == 1


def q(op):
    return Fraction(op[0], op[1])


# ---------------------------------------------------------------------------------------------
# Golden cases: each misconception's wrong value on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # x,      y,      correct,          {label: wrong value}
    ((4, 1), (1, 3), Fraction(12),     {"DIVIDED_WHOLE": Fraction(4, 3), "FLIPPED_ANSWER": Fraction(1, 12)}),
    ((1, 2), (4, 1), Fraction(1, 8),   {"FLIPPED_ANSWER": Fraction(8), "MULT_WHOLE": Fraction(2),
                                         "ADDED_TO_DENOM": Fraction(1, 6)}),
    ((3, 4), (1, 4), Fraction(3),      {"FLIP_FIRST": Fraction(1, 3), "NO_FLIP": Fraction(3, 16),
                                         "KEEP_DENOM": Fraction(3, 4)}),
    ((6, 8), (3, 8), Fraction(2),      {"KEEP_DENOM": Fraction(1, 4), "FLIP_FIRST": Fraction(1, 2)}),
    ((2, 3), (3, 4), Fraction(8, 9),   {"FLIP_FIRST": Fraction(9, 8), "NO_FLIP": Fraction(1, 2),
                                         "FLIP_BOTH": Fraction(2), "IGNORED_NUMERATOR": Fraction(8, 3)}),
    ((6, 1), (3, 4), Fraction(8),      {"WRONG_ORDER": Fraction(1, 8), "NO_FLIP": Fraction(9, 2),
                                         "IGNORED_NUMERATOR": Fraction(24)}),
    ((3, 4), (3, 1), Fraction(1, 4),   {"WRONG_ORDER": Fraction(4), "MULT_WHOLE": Fraction(9, 4)}),
]


@pytest.mark.parametrize("x,y,correct,wrong", GOLDEN, ids=[f"{g[0]}÷{g[1]}" for g in GOLDEN])
def test_golden_rule_values(x, y, correct, wrong):
    assert G.rule_value("CORRECT", x, y) == correct
    for label, v in wrong.items():
        assert G.rule_value(label, x, y) == v, label


@pytest.mark.parametrize("x,y,label", [
    ((4, 1), (2, 3), "DIVIDED_WHOLE"),      # divisor not a unit fraction
    ((4, 1), (1, 3), "NO_FLIP"),            # that is DIVIDED_WHOLE
    ((1, 2), (1, 3), "MULT_WHOLE"),         # divisor not a whole
    ((5, 8), (3, 8), "KEEP_DENOM"),         # 5 ÷ 3 not a whole number
    ((2, 3), (3, 4), "KEEP_DENOM"),         # different denominators
    ((4, 1), (1, 3), "IGNORED_NUMERATOR"),  # unit divisor: same as the right rule
    ((1, 2), (4, 1), "FLIP_BOTH"),          # whole divisor
])
def test_rule_does_not_fire_where_it_does_not_apply(x, y, label):
    assert G.rule_value(label, x, y) is None


def test_every_label_declared_and_text_fits():
    cat = BAKED["misconceptions"]
    for labels in G.TIER_LABELS.values():
        for lab in labels:
            assert lab in cat
    for key, m in cat.items():
        assert len(m["student"]) <= 80, key


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked item
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    x, y, unit, _ = read_prompt(item["prompt"])
    value = q(x) / q(y)
    assert len(item["choices"]) == 4
    got = read_choice(item["choices"][item["answer"]], unit)
    assert got == value, (item["prompt"], item["choices"])
    assert canonical(item["choices"][item["answer"]], unit)
    want = item["choices"][item["answer"]]
    assert item["explanation"].endswith(f"{want}."), item["explanation"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(item):
    _, _, unit, _ = read_prompt(item["prompt"])
    vals = [read_choice(c, unit) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert all(v > 0 for v in vals)
    assert all(canonical(c, unit) for c in item["choices"]), item["choices"]  # form never gives it away


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    x, y, unit, _ = read_prompt(item["prompt"])
    produced = {lab: G.rule_value(lab, x, y) for lab in G.ALL_LABELS}
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one misconception distractor"
    tier_labels = G.TIER_LABELS[item["tier"]]
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        v = read_choice(c, unit)
        if m == "ARITH":
            assert v not in produced.values(), f"ARITH {c} is really a misconception value"
        else:
            assert m in tier_labels
            assert produced[m] == v
            for lab in tier_labels[:tier_labels.index(m)]:
                assert produced[lab] != v, f"{c}: {lab} outranks {m}"


def test_tier_shapes():
    for it in by_tier(1):
        x, y, _, _ = read_prompt(it["prompt"])
        assert x[1] == 1 and y[0] == 1
    for it in by_tier(2):
        x, y, _, _ = read_prompt(it["prompt"])
        assert x[1] > 1 and y[1] == 1
    for it in by_tier(3):
        x, y, _, _ = read_prompt(it["prompt"])
        assert x[1] == y[1] > 1
    for it in by_tier(4):
        x, y, _, _ = read_prompt(it["prompt"])
        assert y[1] > 1 and x[1] != y[1]
    for it in by_tier(5):
        assert read_prompt(it["prompt"])[3], it["prompt"]
    # the tier-defining misconceptions are present
    assert all("DIVIDED_WHOLE" in it["misconceptions"] for it in by_tier(1))
    assert all("WRONG_ORDER" in it["misconceptions"] for it in by_tier(5))
    assert sum("KEEP_DENOM" in it["misconceptions"] for it in by_tier(3)) >= 20


def test_arith_share_at_most_a_third():
    labels = [m for it in ITEMS for m in it["misconceptions"] if m]
    assert labels.count("ARITH") <= len(labels) / 3


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds", PROTOCOL §4b) walked independently on baked.json
# ---------------------------------------------------------------------------------------------
STORY_DENS = {2, 3, 4, 6, 8}


def bounds_violations(prompt):
    x, y, _, story = read_prompt(prompt)
    bad = []
    for op in (x, y):
        n, d = op
        if d == 1:
            if not 2 <= n <= 10:
                bad.append(f"whole {n} outside 2..10")
        else:
            if not (2 <= d <= 10 and 1 <= n <= 9 and n < d):
                bad.append(f"fraction {n}/{d} not proper with numerator 1..9, denominator 2..10")
            if story and d not in STORY_DENS:
                bad.append(f"story denominator {d} not in {sorted(STORY_DENS)}")
    # correct steps: multiply by the reciprocal of y
    rn, rd = y[1], y[0]
    for a, b in ((x[0], rn), (x[1], rd)):
        if a > 10 or b > 10 or a * b > 100:
            bad.append(f"product {a} × {b} not a times-table fact")
    ans = q(x) / q(y)
    if ans.denominator == 1:
        if not 1 <= ans <= 100:
            bad.append(f"whole answer {ans} outside 1..100")
    else:
        if ans.denominator > 12:
            bad.append(f"answer denominator {ans.denominator} > 12")
        if ans.numerator // ans.denominator > 10:
            bad.append(f"answer whole part {ans.numerator // ans.denominator} > 10")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]


@pytest.mark.parametrize("prompt,expect_bad", [
    ("4 ÷ 1/3", False),
    ("12 ÷ 1/3", True),                 # whole 12
    ("3/4 ÷ 2/11", True),               # denominator 11
    ("1/5 ÷ 3", True),                  # answer 1/15
    ("9/10 ÷ 1/10", False),
    ("10/12 ÷ 5/12", True),             # numerator 10, denominator 12
    ("5/4 ÷ 1/2", True),                # improper prompt fraction
    ("1/3 ÷ 1/8", False),               # 2 2/3
    ("9 ÷ 1/10", False),                # 90
    ("2/5 cup of flour, 1/5 cup per batch. How many batches?", True),  # fifths in a story
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, prompt


def test_generator_bounds_agree_with_checker_on_samples():
    for prompt in ("12 ÷ 1/3", "1/5 ÷ 3", "4 ÷ 1/3"):
        x, y, _, _ = read_prompt(prompt)
        assert G.bounds_ok(x, y) == (not bounds_violations(prompt))
