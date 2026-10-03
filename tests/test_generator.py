"""Order-of-ops generator: golden misconception values and per-tier constraints."""
import re
from collections import Counter

import pytest

from fnm.profiles import render

GOLDEN = [
    ("3 + 4 × 2", {"CORRECT": 11, "ADD_FIRST": 14}),
    ("2 × 3 + 4 × 5", {"CORRECT": 26, "LTR": 50, "ADD_FIRST": 70}),
    ("2 × 3^2", {"CORRECT": 18, "EXP_AFTER_MULT": 36, "EXP_AS_MULT": 12}),
    ("(3 + 4) × 2", {"CORRECT": 14, "IGNORE_PARENS": 11}),
    ("12 ÷ 2 × 3", {"CORRECT": 18, "M_BEFORE_D": 2}),
    ("24 ÷ 4 × 2", {"CORRECT": 12, "M_BEFORE_D": 3, "LTR": 12, "ADD_FIRST": 12}),
    ("10 − 3 + 2", {"CORRECT": 9, "A_BEFORE_S": 5, "LTR": 9, "ADD_FIRST": 9}),
    ("(8 + 16) ÷ 4 × 2", {"CORRECT": 12, "M_BEFORE_D": 3, "IGNORE_PARENS": 16}),
    ("20 − (6 − 2) + 3", {"CORRECT": 19, "A_BEFORE_S": 13, "IGNORE_PARENS": 15}),
    ("(1 + 2)^2", {"CORRECT": 9, "IGNORE_PARENS": 5}),
]


@pytest.mark.parametrize("text,expected", GOLDEN)
def test_golden(gen, text, expected):
    for rule, value in expected.items():
        assert gen.evaluate(text, rule) == value, (text, rule)


COMPOUND_GOLDEN = [
    # (text, (a, b), value, label)
    ("(1 + 2) × 3^2", ("EXP_AS_MULT", "IGNORE_PARENS"), 13, "EXP_AS_MULT"),
    ("10 − (2 + 3) × 2", ("IGNORE_PARENS", "LTR"), 22, "IGNORE_PARENS"),
    ("40 ÷ 2 × 2 − 3 + 2", ("M_BEFORE_D", "A_BEFORE_S"), 5, "M_BEFORE_D"),
]


@pytest.mark.parametrize("text,pair,value,label", COMPOUND_GOLDEN)
def test_compound_golden(gen, text, pair, value, label):
    assert pair in gen.COMPOUNDS
    assert gen.evaluate(text, gen.compound_rule(*pair)) == value
    assert gen.compound_label(*pair) == label


def test_compounds_only_declared_keys(baked, gen):
    declared = set(baked["misconceptions"])
    for a, b in gen.COMPOUNDS:
        assert a in declared and b in declared


def _label_values(gen, prompt, label):
    """Every value a distractor labelled ``label`` may legitimately carry: the single rule, or any
    compound whose label it is."""
    vals = {gen.evaluate(prompt, label)}
    for pair in gen.COMPOUNDS:
        if gen.compound_label(*pair) == label:
            vals.add(gen.evaluate(prompt, gen.compound_rule(*pair)))
    return vals


def test_display_format(gen):
    assert gen.render(("×", ("+", 3, 4), 2)) == "(3 + 4) × 2"
    assert gen.render(("^", ("+", 1, 2), 2)) == "(1 + 2)^2"
    assert gen.render(("×", 2, ("^", 3, 2))) == "2 × 3^2"
    assert gen.render(("−", 10, ("−", 3, 2))) == "10 − (3 − 2)"


def test_label_priority_on_collision(gen):
    # 2 × 3^2: LTR gives (2 × 3)^2 = 36 too; EXP_AFTER_MULT outranks LTR.
    labels = dict(gen.misconception_values("2 × 3^2", set(gen.LABEL_PRIORITY)))
    assert labels["EXP_AFTER_MULT"] == 36
    assert "LTR" not in labels


def _ops(prompt):
    return sum(prompt.count(o) for o in "+−×÷^")


def test_items_shape(baked, gen):
    declared = set(baked["misconceptions"])
    for it in baked["items"]:
        assert len(it["choices"]) == 4, it["id"]
        labels = [m for m in it["misconceptions"] if m not in (None, "ARITH")]
        assert labels, f"{it['id']} has no misconception distractor"
        assert set(labels) <= declared
        for c in it["choices"]:
            assert 0 <= int(c) <= 999
        assert len(render(it["explanation"], "unicode")) <= 160
        # Each labelled distractor really is that rule's (or one of its compounds') value.
        for c, m in zip(it["choices"], it["misconceptions"]):
            if m not in (None, "ARITH"):
                assert int(c) in _label_values(gen, it["prompt"], m), (it["id"], m)
        nums = [int(n) for n in re.findall(r"\d+", it["prompt"])]
        assert all(n <= 100 for n in nums), it["id"]


def test_tier_rules(baked, gen):
    for it in baked["items"]:
        p, t = it["prompt"], it["tier"]
        c = gen.evaluate(p)
        n = _ops(p)
        if t == 1:
            assert n == 2 and "(" not in p and "^" not in p
            # LTR differs (precedence item) OR a literal-PEMDAS reading differs (same-level item)
            assert any(gen.evaluate(p, r) not in (None, c)
                       for r in ("LTR", "M_BEFORE_D", "A_BEFORE_S")), it["id"]
        elif t == 2:
            assert 2 <= n <= 3 and p.count("(") == 1 and "^" not in p
            assert gen.evaluate(p, "IGNORE_PARENS") != c
        elif t == 3:
            assert 2 <= n <= 3 and p.count("^") == 1 and "(" not in p
        elif t == 4:
            assert "^" in p and "(" in p and 2 <= n <= 4
        elif t == 5:
            assert 4 <= n <= 5 and "÷" in p and "^" in p


def test_intermediates_and_powers(baked, gen):
    for it in baked["items"]:
        for op, a, b, v in gen.trace(it["prompt"]):
            assert v.denominator == 1 and 0 <= v <= 999, it["id"]
            if op == "^":
                assert 2 <= a <= 10 and b in (2, 3) and v <= 1000, it["id"]


def test_answer_balance_exact(baked):
    for t in range(1, 6):
        cnt = Counter(it["answer"] for it in baked["items"] if it["tier"] == t)
        assert cnt == {0: 10, 1: 10, 2: 10, 3: 10}


@pytest.mark.parametrize("text,expected", [
    ("9 × 12 + 8^2", "8^2 = 64, then 9 × 12 = 108, then 108 + 64 = 172."),
    ("11 + (12 − 11) × 9^2", "12 − 11 = 1, then 9^2 = 81, then 1 × 81 = 81, then 11 + 81 = 92."),
    ("5^3 − (136 ÷ (10 + 7) − 6)",
     "10 + 7 = 17, then 136 ÷ 17 = 8, then 8 − 6 = 2, then 5^3 = 125, then 125 − 2 = 123."),
    ("3 + 4 × 2", "4 × 2 = 8, then 3 + 8 = 11."),
])
def test_explanation_follows_taught_order(gen, text, expected):
    # parentheses (innermost first), then ^, then × ÷, then + −, left to right
    assert gen.explanation(text) == expected


def test_explanation_identical_subexpressions(gen):
    assert gen.explanation("2 × 3 + 2 × 3") == "2 × 3 = 6, then 2 × 3 = 6, then 6 + 6 = 12."


# --- Baked content mix (v1.1.0): literal-PEMDAS coverage and ARITH share --------------------------
def _count(baked, label, tier=None):
    return sum(m == label for it in baked["items"] if tier in (None, it["tier"])
               for m in it["misconceptions"])


def _carries_same_level(it):
    return bool({"M_BEFORE_D", "A_BEFORE_S"} & set(it["misconceptions"]))


def test_same_level_misconceptions_present(baked):
    assert _count(baked, "M_BEFORE_D") >= 8
    assert _count(baked, "A_BEFORE_S") >= 8


def test_arith_share(baked):
    wrong = sum(m is not None for it in baked["items"] for m in it["misconceptions"])
    assert _count(baked, "ARITH") / wrong <= 0.45


def test_t1_same_level_items(baked, gen):
    # Same-level item: both ops on one precedence level, so LTR is right and only the
    # literal-PEMDAS reading (a ÷ (b × c), a − (b + c)) is wrong.
    same = [it for it in baked["items"] if it["tier"] == 1
            and gen.evaluate(it["prompt"], "LTR") == gen.evaluate(it["prompt"])]
    assert len(same) >= 8
    assert all(_carries_same_level(it) for it in same)


@pytest.mark.parametrize("tier,minimum", [(2, 6), (5, 4)])
def test_same_level_distractors_per_tier(baked, tier, minimum):
    assert sum(_carries_same_level(it) for it in baked["items"] if it["tier"] == tier) >= minimum
