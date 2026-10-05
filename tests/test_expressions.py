"""expressions cartridge: golden misconceptions, an independent re-check of every baked item, the
§4a/§4b bounds walked on baked.json, and value-distinct choices.

The independent check never calls the generator's value engine: prompts are read with regexes,
expressions are rewritten to Python and evaluated with ``ast`` + ``fractions.Fraction`` here.
"""
import ast
import json
import math
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "expressions"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
WORDS = {"sum", "difference", "product", "quotient"}


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Golden cases: every misconception key yields its hand-worked wrong choice
# ---------------------------------------------------------------------------------------------
def wrongs(built):
    out = {}
    for lab, text in built["wrong"]:
        out.setdefault(lab, []).append(text)
    return out


GOLDEN = [
    # (builder call, expected answer, {label: expected wrong text})
    (lambda: G.t1_less_than("n", 5), "n − 5", {"ORDER_SUB": "5 − n", "WRONG_OP": "n + 5"}),
    (lambda: G.t1_divided_by("n", 3), "n ÷ 3", {"SWAP_DIV": "3 ÷ n", "WRONG_OP": "3n"}),
    (lambda: G.t1_times_sum("n", 4, 3), "3(n + 4)",
     {"MISSING_PARENS": "3n + 4", "SWAPPED_NUMS": "4(n + 3)"}),
    (lambda: G.t1_more_than_product("n", 3, 2), "2n + 3",
     {"EXTRA_PARENS": "2(n + 3)", "SWAPPED_NUMS": "3n + 2"}),
    (lambda: G.t2_coefficient("x", 7, 3), "7",
     {"COEF_CONST_MIX": "3", "TERM_FOR_COEF": "7x", "VARIABLE_FOR_NUMBER": "x"}),
    (lambda: G.t2_hidden_one("y", 8, ("x", 3)), "1",
     {"HIDDEN_ONE": "0", "OTHER_VARIABLE": "3", "COEF_CONST_MIX": "8"}),
    (lambda: G.t2_constant("a", 4, 9), "9", {"VARIABLE_TERM": "4a"}),
    (lambda: G.t2_count_terms([(3, "a"), (2, "b")], 5), "3",
     {"COUNTS_VARIABLES": "2", "COUNTS_PIECES": "5"}),
    (lambda: G.t2_name(G.NAME_FORMS[0], "x", 5, 2), "product",
     {"INNER_OP": "sum", "LAST_STEP": "difference"}),
    (lambda: G.t3_linear("x", 3, 4, 5), "19", {"CONCAT": "39", "ORDER": "27", "ADD_COEF": "12"}),
    (lambda: G.t3_coef_square("a", 2, 3), "18", {"SQUARE_PRODUCT": "36", "EXP_AS_TIMES": "12"}),
    (lambda: G.t3_power_plus("x", 2, 3, 4), "19", {"EXP_AS_TIMES": "11", "ORDER": "49"}),
    (lambda: G.t3_group("x", 5, "−", 2, 6), "20", {"PARENS_SKIPPED": "28", "ADD_COEF": "9"}),
    (lambda: G.t4_expand("x", 3, 1, 4), "3x + 12",
     {"PARTIAL_DIST": "3x + 4", "ADD_FOR_MUL": "3x + 7", "UNLIKE_COMBINED": "15x"}),
    (lambda: G.t4_expand("x", 3, 1, 4, "−"), "3x − 12", {"SIGN_DROP": "3x + 12"}),
    (lambda: G.t4_factor("x", 3, 2, 3), "3(2x + 3)",
     {"PARTIAL_FACTOR": "3(2x + 9)", "SUB_FOR_DIV": "3(3x + 6)", "X_FROM_BOTH": "3x(2 + 3)"}),
    (lambda: G.t5_dist_plus_terms("x", 2, 3, 1), "3x + 6",
     {"PARTIAL_DIST": "3x + 3", "UNLIKE_COMBINED": "9x", "DROPPED_TERM": "2x + 6"}),
    (lambda: G.t5_repeat_add("x", 3), "3x", {"POWER_FOR_SUM": "x^3"}),
    (lambda: G.t5_like_terms("a", 5, 3), "8a", {"MULT_COEF": "15a", "POWER_FOR_SUM": "8a^2"}),
    (lambda: G.t5_like_terms("x", 5, 1, "−"), "4x", {"HIDDEN_ONE": "5x", "SIGN_DROP": "6x"}),
    (lambda: G.t5_repeat_mul("y", 2), "y^2", {"SUM_FOR_POWER": "2y"}),
]


@pytest.mark.parametrize("case", GOLDEN, ids=[str(i) for i in range(len(GOLDEN))])
def test_golden(case):
    call, answer, expected = case
    built = call()
    assert built["answer"] == answer
    got = wrongs(built)
    for lab, text in expected.items():
        assert text in got.get(lab, []), (lab, text, got)


def test_every_declared_key_has_a_golden_case_and_is_used():
    golden_keys = {lab for _, _, exp in GOLDEN for lab in exp}
    declared = set(BAKED["misconceptions"])
    assert declared == golden_keys, declared ^ golden_keys
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert declared <= used, declared - used


# ---------------------------------------------------------------------------------------------
# Independent evaluator (Python ast + Fraction)
# ---------------------------------------------------------------------------------------------
def to_python(text: str) -> str:
    s = text.replace("−", "-").replace("×", "*").replace("÷", "/").replace("^", "**")
    # implicit multiplication: 3x, 2(, x(, )(, rt
    return re.sub(r"(?<=[\dA-Za-z)])(?=[A-Za-z(])", "*", s)


def ev(node, env):
    if isinstance(node, ast.Expression):
        return ev(node.body, env)
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return Fraction(node.value)
    if isinstance(node, ast.Name):
        return Fraction(env[node.id])
    if isinstance(node, ast.BinOp):
        a, b = ev(node.left, env), ev(node.right, env)
        op = type(node.op)
        if op is ast.Add:
            return a + b
        if op is ast.Sub:
            return a - b
        if op is ast.Mult:
            return a * b
        if op is ast.Div:
            return a / b
        if op is ast.Pow:
            return a ** b
    raise AssertionError(f"unexpected node {ast.dump(node)}")


ENVS = [{L: Fraction(v) for L, v in zip("abcdefghijklmnopqrstuvwxyzLWPA", vals)}
        for vals in ([(i * 7 + 2) % 53 + 2 for i in range(30)],
                     [(i * 11 + 5) % 61 + 3 for i in range(30)],
                     [(i * 13 + 1) % 67 + 4 for i in range(30)],
                     [(i * 17 + 9) % 71 + 2 for i in range(30)],
                     [(i * 19 + 4) % 73 + 5 for i in range(30)])]


def sig(text: str):
    """Value signature of a choice: words by text, expressions by value at 5 assignments."""
    if text in WORDS:
        return ("word", text)
    tree = ast.parse(to_python(text), mode="eval")
    out = []
    for env in ENVS:
        try:
            out.append(ev(tree, env))
        except ZeroDivisionError:
            out.append("div0")
    return ("value", tuple(out))


def same_value(a: str, b: str) -> bool:
    return sig(a) == sig(b)


def test_evaluator_sanity():
    assert to_python("2a^2") == "2*a**2"
    assert to_python("8t(7 − 1)") == "8*t*(7 - 1)"
    assert same_value("3x + 6", "6 + 3x") and same_value("3(x + 2)", "3x + 6")
    assert not same_value("n − 5", "5 − n") and not same_value("n ÷ 3", "3 ÷ n")
    assert not same_value("2(x + 3)", "2x + 3")


# ---------------------------------------------------------------------------------------------
# Every choice value-distinct; exactly one right door
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_distinct_in_value(item):
    sigs = [sig(c) for c in item["choices"]]
    assert len(set(sigs)) == len(sigs), item["choices"]
    assert len(item["choices"]) == 4


# ---------------------------------------------------------------------------------------------
# Independent answer check per tier
# ---------------------------------------------------------------------------------------------
T1_PATTERNS = [
    (r"^(?P<k>\d+) less than (?P<v>[a-z])$", "{v} - {k}"),
    (r"^Subtract (?P<v>[a-z]) from (?P<k>\d+)$", "{k} - {v}"),
    (r"^(?P<v>[a-z]) divided by (?P<k>\d+)$", "{v} / {k}"),
    (r"^The quotient of (?P<v>[a-z]) and (?P<k>\d+)$", "{v} / {k}"),
    (r"^(?P<a>\d+) more than the product of (?P<b>\d+) and (?P<v>[a-z])$", "{b}*{v} + {a}"),
    (r"^(?P<a>\d+) less than the product of (?P<b>\d+) and (?P<v>[a-z])$", "{b}*{v} - {a}"),
    (r"^(?P<b>\d+) times the sum of (?P<v>[a-z]) and (?P<a>\d+)$", "{b}*({v} + {a})"),
    (r"^(?P<b>\d+) times the difference of (?P<v>[a-z]) and (?P<a>\d+)$", "{b}*({v} - {a})"),
    (r"^Divide the sum of (?P<v>[a-z]) and (?P<a>\d+) by (?P<b>\d+)$", "({v} + {a}) / {b}"),
]


def py_sig(py: str):
    tree = ast.parse(py, mode="eval")
    return ("value", tuple(ev(tree, env) for env in ENVS))


def t1_expected(prompt):
    for pat, tmpl in T1_PATTERNS:
        m = re.match(pat, prompt)
        if m:
            return py_sig(tmpl.format(**m.groupdict()))
    raise AssertionError(f"unrecognised T1 prompt {prompt!r}")


def split_terms(expr):
    return [t.strip() for t in expr.split(" + ")]


def last_step_word(expr: str) -> str:
    """Name an expression by the operation done last: top-level (depth 0) + or − beats ÷/×."""
    depth, top = 0, []
    for i, ch in enumerate(expr):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch in "+−÷" and expr[i - 1] == " ":
            top.append(ch)
    if "+" in top or "−" in top:
        return "sum" if [c for c in top if c in "+−"][-1] == "+" else "difference"
    if "÷" in top:
        return "quotient"
    return "product"


def t2_expected(prompt):
    m = re.match(r"^Coefficient of ([a-z]) in (.+)\?$", prompt)
    if m:
        v, e = m.groups()
        for t in split_terms(e):
            mm = re.fullmatch(rf"(\d*){v}", t)
            if mm:
                return mm.group(1) or "1"
        raise AssertionError(prompt)
    m = re.match(r"^Constant term in (.+)\?$", prompt)
    if m:
        consts = [t for t in split_terms(m.group(1)) if t.isdigit()]
        assert len(consts) == 1
        return consts[0]
    m = re.match(r"^How many terms in (.+)\?$", prompt)
    if m:
        return str(len(split_terms(m.group(1))))
    m = re.match(r"^What kind of expression is (.+)\?$", prompt)
    if m:
        return last_step_word(m.group(1))
    raise AssertionError(f"unrecognised T2 prompt {prompt!r}")


def t3_parse(prompt):
    """-> (expression text, {letter: value})."""
    m = re.match(r"^Find (.+) when (.+)$", prompt)
    if m:
        expr, assigns = m.groups()
    else:
        m = re.match(r"^([A-Za-z]) = (.+)\. Find \1 when (.+)$", prompt)
        assert m, prompt
        _, expr, assigns = m.groups()
    env = {}
    for a in assigns.split(", "):
        k, v = a.split(" = ")
        env[k] = int(v)
    return expr, env


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    p, ch, ans = item["prompt"], item["choices"], item["choices"][item["answer"]]
    t = item["tier"]
    if t == 1:
        exp = t1_expected(p)
        matches = [c for c in ch if sig(c) == exp]
        assert matches == [ans], (p, ch)
    elif t == 2:
        assert ans == t2_expected(p), p
    elif t == 3:
        expr, env = t3_parse(p)
        v = ev(ast.parse(to_python(expr), mode="eval"), env)
        assert v.denominator == 1 and ans == str(int(v)), (p, ans, v)
        assert all(c.isdigit() for c in ch)
    else:
        m = re.match(r"^(Distribute|Factor out the GCF|Simplify): (.+)$", p)
        assert m, p
        kind, expr = m.groups()
        target = sig(expr)
        matches = [c for c in ch if sig(c) == target]
        assert matches == [ans], (p, ch)
        if kind == "Distribute":
            assert "(" not in ans
        elif kind == "Factor out the GCF":
            nums = [int(n) for n in re.findall(r"\d+", expr)]
            g = math.gcd(*nums)
            mm = re.fullmatch(r"(\d+)\((\d*)([a-z]) [+−] (\d+)\)", ans)
            assert mm, ans
            assert int(mm.group(1)) == g, (p, ans)
            assert math.gcd(int(mm.group(2) or 1), int(mm.group(4))) == 1
        else:  # simplified: no ( ), at most one term per power of the variable
            assert "(" not in ans
            powers = [re.sub(r"^\d*", "", tt) for tt in re.split(r" [+−] ", ans)]
            assert len(powers) == len(set(powers)), ans
    assert item["explanation"].rstrip(".").endswith(ans.rstrip(".")) or ans in item["explanation"]


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"; PROTOCOL §4a/§4b), walked on every baked prompt
# ---------------------------------------------------------------------------------------------
def t3_violations(prompt):
    expr, env = t3_parse(prompt)
    bad = []

    def leaf(n):
        return isinstance(n, (ast.Constant, ast.Name))

    def walk(n):
        if isinstance(n, ast.Expression):
            return walk(n.body)
        if isinstance(n, ast.Constant):
            return Fraction(n.value)
        if isinstance(n, ast.Name):
            return Fraction(env[n.id])
        a, b = walk(n.left), walk(n.right)
        op = type(n.op)
        if op is ast.Mult:
            if not (2 <= a <= 10 and 2 <= b <= 10):
                bad.append(f"× step {a} × {b} not a times-table fact")
            v = a * b
        elif op is ast.Pow:
            if not ((b == 2 and 2 <= a <= 10) or (b == 3 and 2 <= a <= 4)):
                bad.append(f"power {a}^{b} out of range")
            v = a ** b
        elif op in (ast.Add, ast.Sub):
            for side, val in ((n.left, a), (n.right, b)):
                if leaf(side) and not 1 <= val <= 20:
                    bad.append(f"added number {val} outside 1..20")
            v = a + b if op is ast.Add else a - b
        else:
            bad.append(f"unexpected op {op.__name__}")
            return Fraction(0)
        if v.denominator != 1 or not 0 <= v <= 100:
            bad.append(f"step value {v} outside 0..100")
        return v

    walk(ast.parse(to_python(expr), mode="eval"))
    return bad


def poly_violations(expr):
    """T4/T5 prompt walked symbolically (one variable): every constant × poly is a times-table
    fact on every coefficient; every combined coefficient/constant size <= 100; combined variable
    coefficients <= 20; added literals 1..20 unless they are a coefficient product (factor
    prompts are checked through their answer)."""
    bad = []

    def walk(n):
        if isinstance(n, ast.Expression):
            return walk(n.body)
        if isinstance(n, ast.Constant):
            return {0: n.value}
        if isinstance(n, ast.Name):
            return {1: 1}
        a, b = walk(n.left), walk(n.right)
        op = type(n.op)
        if op is ast.Mult:
            if set(a) == {0} or set(b) == {0}:
                c, other = (a[0], b) if set(a) == {0} else (b[0], a)
                if not 2 <= c <= 10 or any(not 1 <= abs(v) <= 10 for v in other.values()):
                    bad.append(f"{c} × {other} not times-table facts")
            out = {}
            for ea, ca in a.items():
                for eb, cb in b.items():
                    out[ea + eb] = out.get(ea + eb, 0) + ca * cb
            return out
        if op in (ast.Add, ast.Sub):
            s = 1 if op is ast.Add else -1
            out = dict(a)
            for e, c in b.items():
                out[e] = out.get(e, 0) + s * c
            for e, c in out.items():
                if not abs(c) <= 100:  # a subtracted term inside ( ) is negative
                    bad.append(f"coefficient {c} outside 0..100")
            if 1 in a and 1 in b and out.get(1, 0) > 20:
                bad.append(f"combined coefficient {out[1]} over 20")
            return out
        bad.append(f"unexpected op {op.__name__}")
        return {0: 0}

    walk(ast.parse(to_python(expr), mode="eval"))
    return bad


def prompt_number_violations(prompt, tier):
    bad = []
    if tier in (1, 2):
        for n in re.findall(r"\d+", prompt):
            if not 1 <= int(n) <= 20:
                bad.append(f"number {n} outside 1..20")
        for n in re.findall(r"(\d+)(?=[a-z(])", prompt) + re.findall(r"÷ (\d+)", prompt) + \
                re.findall(r"(?:divided by|product of|quotient of [a-z] and|by) (\d+)", prompt) + \
                re.findall(r"(\d+) times", prompt):
            if not 2 <= int(n) <= 10:
                bad.append(f"multiplier/divisor {n} outside 2..10")
    return bad


def bounds_violations(item):
    p, t = item["prompt"], item["tier"]
    bad = prompt_number_violations(p, t)
    if t == 3:
        bad += t3_violations(p)
    elif t >= 4:
        kind, expr = p.split(": ", 1)
        if kind == "Factor out the GCF":
            ans = item["choices"][item["answer"]]
            g, pc, q = re.fullmatch(r"(\d+)\((\d*)[a-z] [+−] (\d+)\)", ans).groups()
            if not all(2 <= int(x) <= 10 for x in (g,)) or not all(
                    1 <= int(x or 1) <= 10 for x in (pc, q)):
                bad.append(f"factor parts {g}, {pc}, {q} not times-table facts")
        else:
            bad += poly_violations(expr)
            for n in re.findall(r"(?<![\d^])(\d+)(?![\d(a-z])", expr):
                if not 1 <= int(n) <= 20:
                    bad.append(f"added number {n} outside 1..20")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item) == [], item["prompt"]


def _fake(prompt, tier, answer="0"):
    return {"prompt": prompt, "tier": tier, "choices": [answer], "answer": 0}


@pytest.mark.parametrize("prompt,tier,answer,expect_bad", [
    ("Find 3x + 4 when x = 5", 3, "19", False),
    ("Find 12x + 4 when x = 5", 3, "64", True),       # × operand 12
    ("Find x^2 + 30 when x = 4", 3, "46", True),      # added 30
    ("Find 2a^2 when a = 4", 3, "32", True),          # 2 × 16
    ("Find x^3 + 1 when x = 5", 3, "126", True),      # cube of 5, over 100
    ("Find 7x − y when x = 2, y = 20", 3, "0", True),  # 14 − 20 < 0
    ("Distribute: 3(x + 4)", 4, "3x + 12", False),
    ("Distribute: 12(x + 3)", 4, "12x + 36", True),   # multiplier 12
    ("Distribute: 3(4x + 11)", 4, "12x + 33", True),  # 3 × 11
    ("Simplify: 9x + 15x", 5, "24x", True),           # combined coefficient 24
    ("Factor out the GCF: 6x + 9", 4, "3(2x + 3)", False),
    ("Factor out the GCF: 24x + 36", 4, "12(2x + 3)", True),  # GCF 12
    ("25 less than n", 1, "n − 25", True),
    ("3 times the sum of n and 4", 1, "3(n + 4)", False),
    ("12 times the sum of n and 4", 1, "12(n + 4)", True),
])
def test_bounds_checker_catches(prompt, tier, answer, expect_bad):
    assert bool(bounds_violations(_fake(prompt, tier, answer))) == expect_bad, prompt


# ---------------------------------------------------------------------------------------------
# Shape and balance
# ---------------------------------------------------------------------------------------------
def test_arith_share_at_most_quarter():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.25
    for t in range(1, 6):
        ct = Counter(m for it in by_tier(t) for m in it["misconceptions"] if m)
        assert ct["ARITH"] / sum(ct.values()) <= 0.34, t


def test_every_item_has_a_real_misconception():
    for it in ITEMS:
        assert any(m and m != "ARITH" for m in it["misconceptions"]), it["id"]


def test_no_hyphen_minus_and_no_negative_numbers():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in s, s
        for c in it["choices"]:
            assert not c.startswith("−"), c


def test_answer_positions_balanced():
    for t in range(1, 6):
        c = Counter(it["answer"] for it in by_tier(t))
        assert all(8 <= c[p] <= 12 for p in range(4)), (t, c)
