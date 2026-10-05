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
    # ×/÷ magnitude misconceptions (hand-checked)
    ("−12 ÷ 3",           -4,  {"MUL_FOR_DIV": -36, "SIGN_RULE_PRODUCT": 4}),
    ("20 ÷ (−10)",        -2,  {"MUL_FOR_DIV": -200, "SIGN_RULE_PRODUCT": 2}),
    ("−18 ÷ (−6)",        3,   {"MUL_FOR_DIV": 108, "SIGN_RULE_PRODUCT": -3}),
    ("−6 × 4",            -24, {"ADD_FOR_MUL": -2, "SIGN_RULE_PRODUCT": 24}),
    ("10 × (−3)",         -30, {"ADD_FOR_MUL": 7, "SIGN_RULE_PRODUCT": 30}),
    ("−9 × (−4)",         36,  {"ADD_FOR_MUL": -13, "SIGN_RULE_PRODUCT": -36}),
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
    ("12 ÷ 3", "MUL_FOR_DIV"),       # no negative in the quotient
    ("−12 × 3", "MUL_FOR_DIV"),      # a product, not a quotient
    ("4 × 6", "ADD_FOR_MUL"),        # no negative factor
    ("−5 × 5", "ADD_FOR_MUL"),       # sum would be 0: not offered
    ("−12 ÷ 3", "ADD_FOR_MUL"),      # a quotient, not a product
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
            assert (b == 2 and 2 <= abs(a) <= 10) or (b == 3 and 2 <= abs(a) <= 4), \
                f"power {a}^{b} out of range"
            return a ** b
    raise AssertionError(f"unexpected node {ast.dump(node)}")


def show(n: int) -> str:
    return f"−{-n}" if n < 0 else str(n)


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_answer_independent(item):
    value = safe_eval(ast.parse(to_python(item["prompt"]), mode="eval"))
    assert -100 <= value <= 100
    for c in item["choices"]:
        assert -999 <= int(c.replace(M, "-")) <= 999  # wrong choices keep the 999 ceiling
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
            # §4a, signs as the concept: T1/T2 literals <= 12; T3 factors/divisors <= 10 and a
            # dividend <= 20
            assert all(n <= (12 if t < 3 else 20) for n in nums(it["prompt"]))
            if t == 3 and "×" in it["prompt"]:
                assert all(n <= 10 for n in nums(it["prompt"])), it["prompt"]
    for it in by_tier(1) + by_tier(3):
        assert M in it["prompt"]
    for it in by_tier(2):  # at least one negative, or the answer crosses zero
        assert M in it["prompt"] or it["choices"][it["answer"]].startswith(M)
    t5 = by_tier(5)
    neg_form = [it for it in t5 if re.search(r"(^|\()−\d+\^", it["prompt"])]
    paren_form = [it for it in t5 if re.search(r"\(−\d+\)\^", it["prompt"])]
    assert len(neg_form) + len(paren_form) >= 12 and neg_form and paren_form


# ---------------------------------------------------------------------------------------------
# v1.1: ×/÷ misconceptions cut T3's generic distractors; no zero intermediates in T4/T5
# ---------------------------------------------------------------------------------------------
def arith_share(tier):
    c = Counter(m for it in by_tier(tier) for m in it["misconceptions"] if m)
    return c["ARITH"] / sum(c.values())


def test_t3_arith_share_below_half():
    assert arith_share(3) < 0.5


def test_t3_uses_the_new_misconceptions_on_their_own_operation():
    for it in by_tier(3):
        labels = set(it["misconceptions"])
        if "×" in it["prompt"]:
            assert "MUL_FOR_DIV" not in labels, it["prompt"]
        else:
            assert "ADD_FOR_MUL" not in labels, it["prompt"]
    used = Counter(m for it in by_tier(3) for m in it["misconceptions"] if m)
    assert used["MUL_FOR_DIV"] >= 10 and used["ADD_FOR_MUL"] >= 10


def test_new_misconceptions_declared():
    for key in ("MUL_FOR_DIV", "ADD_FOR_MUL"):
        m = BAKED["misconceptions"][key]
        assert m["student"] and m["teacher"] and len(m["student"]) <= 80


def _internal_values(node):
    """Correct value of every non-leaf node (root included), by Python's ast -- independent of
    the generator."""
    if isinstance(node, ast.Expression):
        yield from _internal_values(node.body)
    elif isinstance(node, ast.BinOp):
        yield safe_eval(node)
        yield from _internal_values(node.left)
        yield from _internal_values(node.right)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.operand, ast.Constant):  # −a^n: an internal node, not a literal
            yield safe_eval(node)
        yield from _internal_values(node.operand)


@pytest.mark.parametrize("item", by_tier(4) + by_tier(5),
                         ids=[it["id"] for it in by_tier(4) + by_tier(5)])
def test_no_zero_intermediate_in_t4_t5(item):
    tree = ast.parse(to_python(item["prompt"]), mode="eval")
    assert 0 not in list(_internal_values(tree)), item["prompt"]


def test_zero_intermediate_detector():
    assert G.has_zero_intermediate("(−10 + 10) × (−6)")
    assert G.has_zero_intermediate("3 × (−4) + 12")  # the whole expression is 0
    assert G.has_zero_intermediate("−3^2 + 9 − 4 × 2")
    assert not G.has_zero_intermediate("(−10 + 7) × (−6)")
    assert not G.has_zero_intermediate("−3^2 + 4")


# ---------------------------------------------------------------------------------------------
# PROTOCOL §4a, signs as the concept: every correct step of every baked item, walked through the
# generator's own parse tree (values computed here)
# ---------------------------------------------------------------------------------------------
from fractions import Fraction  # noqa: E402

_MUL, _DIV = "×", "÷"


def _is_lit(n):
    return isinstance(n, int) or (isinstance(n, G.Neg) and isinstance(n.x, int))


def _lit(n):
    return n if isinstance(n, int) else -n.x


def bounds_violations(prompt, tier):
    tree = G.parse(prompt, G.RULES["CORRECT"])
    bad = []
    addsub_hi, addsub_lo = (12, 1) if tier <= 2 else (10, 2)
    dividend_hi = 20 if tier == 3 else 100

    def lit(n, lo, hi, what):
        if _is_lit(n) and not lo <= abs(_lit(n)) <= hi:
            bad.append(f"{what} literal {_lit(n)} outside size {lo}..{hi}")

    def walk(n):
        if _is_lit(n):
            return Fraction(_lit(n))
        if isinstance(n, G.Neg):  # −a^n
            v = -walk(n.x)
        elif isinstance(n, G.Pow):
            base, e = walk(n.base), n.exp
            if not ((e == 2 and 2 <= abs(base) <= 10) or (e == 3 and 2 <= abs(base) <= 4)):
                bad.append(f"power ({base})^{e} outside squares 2..10 / cubes 2..4")
            v = base ** e
        else:
            a, b = walk(n.l), walk(n.r)
            s = f"{a} {n.op} {b}"
            if n.op == _MUL:
                if abs(a) > 10 or abs(b) > 10:
                    bad.append(f"× operand over 10: {s}")
                if a == 0 or b == 0:
                    bad.append(f"× operand is 0: {s}")
                lit(n.l, 2, 10, "factor")
                lit(n.r, 2, 10, "factor")
                v = a * b
            elif n.op == _DIV:
                if b == 0 or (a / b).denominator != 1:
                    bad.append(f"inexact ÷: {s}")
                    return Fraction(0)
                v = a / b
                if not (2 <= abs(b) <= 10 and 2 <= abs(v) <= 10):
                    bad.append(f"÷ divisor/quotient outside 2..10: {s}")
                lit(n.l, 4, dividend_hi, "dividend")
                lit(n.r, 2, 10, "divisor")
            else:
                lit(n.l, addsub_lo, addsub_hi, n.op)
                lit(n.r, addsub_lo, addsub_hi, n.op)
                v = a + b if n.op == "+" else a - b
        if v.denominator != 1 or abs(v) > 100:
            bad.append(f"intermediate {v} outside −100..100")
        return v

    walk(tree)
    if tier >= 4:  # T4/T5 leaves 2..10 wherever they sit, except a bare dividend
        def leaves(n, parent_div_left=False):
            if _is_lit(n):
                if not parent_div_left and not 2 <= abs(_lit(n)) <= 10:
                    bad.append(f"leaf {_lit(n)} outside size 2..10")
            elif isinstance(n, G.Neg):
                leaves(n.x)
            elif isinstance(n, G.Pow):
                leaves(n.base)
            else:
                leaves(n.l, n.op == _DIV)
                leaves(n.r)
        leaves(tree)
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_concept_over_arithmetic_bounds(item):
    assert bounds_violations(item["prompt"], item["tier"]) == [], item["prompt"]
    ans = G.evaluate(item["prompt"])
    assert -100 <= ans <= 100


@pytest.mark.parametrize("prompt,tier,expect_bad", [
    ("−12 + 5", 1, False),
    ("−13 + 5", 1, True),
    ("−12 × 3", 3, True),          # factor 12
    ("−20 ÷ (−2)", 3, False),
    ("−6^3 + 4 × 2", 5, True),     # cube of 6 = 216
    ("(−4)^3 + 2", 5, False),
    ("(−8 + 2) × (−3)", 4, False),
    ("(−8 − 5) × 2", 4, True),     # group −13 under ×
    ("−60 ÷ 3 + 2", 4, True),      # quotient 20
    ("12 + (−3) × 2", 4, True),    # leaf 12 in T4
    ("(−5 + 5) × 3 + 2", 4, True),  # a group worth 0 under ×
    ("(−5 + 6) × 3 + 2", 4, False), # a group worth 1 under × is fine
])
def test_bounds_checker_catches(prompt, tier, expect_bad):
    assert bool(bounds_violations(prompt, tier)) == expect_bad, prompt
