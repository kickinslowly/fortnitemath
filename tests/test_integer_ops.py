"""integer-ops cartridge: golden misconception rules + an independent re-check of every baked item.

The independent check rewrites each prompt to Python and evaluates it with Python's own parser
(``ast``) and a tiny safe evaluator written here -- never the generator's evaluator.
"""
import ast
import json
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "integer-ops"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
M = "−"  # U+2212


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Golden cases: one per misconception rule (value under the faulty rule, and the label it gets)
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt,             correct, {label: wrong value}
    ("−3 + (−5)",         -8,  {"NEG_NEG_ADD": 8}),
    ("−7 + 3",            -4,  {"ADD_SIZES": -10, "WRONG_SIGN": 4}),
    ("4 − (−6)",          10,  {"SUB_NEG": -2, "WRONG_SIGN": -10}),
    ("−4 × 6",            -24, {"SIGN_RULE_PRODUCT": 24}),
    ("−24 ÷ (−6)",        4,   {"SIGN_RULE_PRODUCT": -4}),
    ("−3^2",              -9,  {"NEG_POWER": 9}),
    ("(−3)^2",            9,   {"NEG_POWER": -9}),
    ("−2 + 3 × (−4)",     -14, {"ORDER": -4}),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_rule_values(prompt, correct, wrong):
    assert G.evaluate(prompt) == correct
    for label, v in wrong.items():
        assert G.evaluate(prompt, label) == v, label


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_labels_after_collision_priority(prompt, correct, wrong):
    got = dict((v, lab) for lab, v in G.misconception_values(prompt, set(G.LABEL_PRIORITY)))
    for label, v in wrong.items():
        assert got[v] == label


def test_collision_neg_neg_add_beats_wrong_sign():
    # −3 + (−5): NEG_NEG_ADD and WRONG_SIGN both give 8; the more specific label wins.
    assert G.evaluate("−3 + (−5)", "WRONG_SIGN") == 8
    assert G.misconception_values("−3 + (−5)", set(G.LABEL_PRIORITY)) == [("NEG_NEG_ADD", 8)]


@pytest.mark.parametrize("prompt,label", [
    ("4 − 6", "SUB_NEG"),            # nothing negative is subtracted
    ("−3 + 5 × 2", "NEG_NEG_ADD"),   # no negative + negative step
    ("−3 + (−5)", "ADD_SIZES"),      # signs do not differ
    ("4 × 6", "SIGN_RULE_PRODUCT"),  # no negative factor
    ("−4 × 6", "WRONG_SIGN"),        # last step is a product, not a sum/difference
    ("(−2)^3", "NEG_POWER"),         # odd exponent: (−2)^3 = −2^3, no distinct value
])
def test_rule_does_not_fire_where_it_does_not_apply(prompt, label):
    assert G.evaluate(prompt, label) in (None, G.evaluate(prompt))


def test_rendering_rules():
    assert G.render(G.Bin("+", 5, -9)) == "5 + (−9)"
    assert G.render(G.Bin("−", 4, -6)) == "4 − (−6)"
    assert G.render(G.Bin("×", -4, -6)) == "−4 × (−6)"
    assert G.render(G.Bin("+", -7, 3)) == "−7 + 3"
    assert G.render(G.Pow(-3, 2)) == "(−3)^2"
    assert G.render(G.Neg(G.Pow(3, 2))) == "−3^2"
    assert G.render(G.Bin("×", G.Bin("+", -2, 5), 3)) == "(−2 + 5) × 3"
    assert G.num(-12) == "−12" and G.num(0) == "0"


# ---------------------------------------------------------------------------------------------
# Independent answer check (Python ast, not the generator)
# ---------------------------------------------------------------------------------------------
def test_python_power_binds_tighter_than_unary_minus():
    # Python's -3**2 is -(3**2) = -9: the SAME convention as the cartridge's −3^2 = −9.
    # The independent check relies on this. Do not "fix" it.
    assert -3**2 == -9
    assert eval("-3**2") == -9
    assert eval("(-3)**2") == 9


def to_python(prompt: str) -> str:
    return prompt.replace("−", "-").replace("×", "*").replace("÷", "//").replace("^", "**")


def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -safe_eval(node.operand)
    if isinstance(node, ast.BinOp):
        a, b = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.FloorDiv):
            assert b != 0, "division by zero"
            assert a % b == 0, f"inexact division {a} ÷ {b}"
            return a // b
        if isinstance(node.op, ast.Pow):
            assert 2 <= b <= 3 and 2 <= abs(a) <= 6, f"power {a}^{b} out of range"
            return a ** b
    raise AssertionError(f"unexpected node {ast.dump(node)}")


def show(n: int) -> str:
    return f"−{-n}" if n < 0 else str(n)


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_answer_independent(item):
    value = safe_eval(ast.parse(to_python(item["prompt"]), mode="eval"))
    assert -999 <= value <= 999
    assert item["choices"][item["answer"]] == show(value)
    assert item["explanation"].endswith(f"{show(value)}.")
    assert len(item["choices"]) == 4


# ---------------------------------------------------------------------------------------------
# Labels are honest, content shape matches the brief
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_labels_are_produced_by_their_rule(item):
    produced = {lab: G.evaluate(item["prompt"], lab) for lab in G.LABEL_PRIORITY}
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one misconception distractor"
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        v = int(c.replace("−", "-"))
        if m == "ARITH":
            assert v not in produced.values(), f"ARITH {c} is really a misconception value"
        else:
            assert produced[m] == v
            # priority: no higher-priority rule produced the same value
            for lab in G.LABEL_PRIORITY[:G.LABEL_PRIORITY.index(m)]:
                assert produced[lab] != v


def test_arith_share_overall_at_most_half():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.5


def test_no_hyphen_minus_in_display_strings():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in s, s


def test_negative_after_operator_is_parenthesised():
    for it in ITEMS:
        assert not re.search(r"[+−×÷] −", it["prompt"]), it["prompt"]
        assert not re.search(r"[+−×÷] \(−\d+\^", it["prompt"]), it["prompt"]  # −a^n only leads


def test_tier_shapes():
    nums = lambda p: [int(x) for x in re.findall(r"\d+", p)]
    for t, op_pat in ((1, r" \+ "), (2, r" − "), (3, r" [×÷] ")):
        for it in by_tier(t):
            assert len(re.findall(r" [+−×÷] ", it["prompt"])) == 1
            assert re.search(op_pat, it["prompt"]), it["prompt"]
            assert all(n <= 20 for n in nums(it["prompt"]))
    for it in by_tier(1) + by_tier(3):
        assert M in it["prompt"]
    for it in by_tier(2):  # at least one negative, or the answer crosses zero
        assert M in it["prompt"] or it["choices"][it["answer"]].startswith(M)
    t5 = by_tier(5)
    neg_form = [it for it in t5 if re.search(r"(^|\()−\d+\^", it["prompt"])]
    paren_form = [it for it in t5 if re.search(r"\(−\d+\)\^", it["prompt"])]
    assert len(neg_form) + len(paren_form) >= 12 and neg_form and paren_form
