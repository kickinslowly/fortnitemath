"""equations-inequalities cartridge: golden misconceptions, an independent re-check of every baked item,
and the cartridge's content bounds asserted on baked.json.

The independent check never calls the generator's solver: it rewrites each prompt to a Python
expression, plugs every choice in with ``fractions.Fraction``, and requires that exactly the answer
choice makes the statement true. Story items (tier 4) are modelled from the words by this file's own
regexes; word inequalities (tier 5) by its own phrase table.
"""
import json
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "equations-inequalities"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M, X, D, LE, GE = "−", "×", "÷", "≤", "≥"


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Independent evaluator: display text -> Python truth value with a value plugged in
# ---------------------------------------------------------------------------------------------
TOKEN = re.compile(r"\s*(\d+|[a-z]|[+\-*/()]|==|<=|>=|<|>)")


def to_python(text: str) -> str:
    s = (text.replace(M, "-").replace(X, "*").replace(D, "/")
         .replace(LE, "<=").replace(GE, ">="))
    s = re.sub(r"(?<![<>=])=(?!=)", "==", s)
    s = re.sub(r"(\d)([a-z])", r"\1*\2", s)  # 4x -> 4*x
    return s


def truth(statement: str, value) -> bool:
    py = to_python(statement)
    var = set(re.findall(r"[a-z]", py))
    assert len(var) == 1, statement
    v = var.pop()
    pos, out = 0, []
    while pos < len(py):  # whitelist tokens, then wrap numbers in Fraction
        m = TOKEN.match(py, pos)
        assert m, (statement, py[pos:])
        tok = m.group(1)
        if tok.isdigit():
            out.append(f"F({tok})")
        elif tok == v:
            out.append(f"F({Fraction(value).numerator}, {Fraction(value).denominator})")
        else:
            out.append(tok)
        pos = m.end()
    return bool(eval(" ".join(out), {"F": Fraction, "__builtins__": {}}))


def solve_one_step(eq: str):
    """Solution of a one-step equation in one variable, solved here (not by the generator).
    'a ÷ x = b' is the only non-linear shape; everything else is linear: f(x) = lhs − rhs."""
    m = re.fullmatch(rf"(\d+) {D} ([a-z]) = (\d+)", eq)
    if m:
        return Fraction(int(m.group(1)), int(m.group(3)))
    lhs, rhs = to_python(eq).split("==")
    var = re.findall(r"[a-z]", eq)[0]

    def f(x):
        env = {"F": Fraction, "__builtins__": {}}
        e = re.sub(r"\d+", lambda t: f"F({t.group(0)})", f"({lhs}) - ({rhs})")
        return eval(e.replace(var, f"F({x})"), env)

    f0, f1 = f(0), f(1)
    assert f1 != f0, eq
    return -f0 / (f1 - f0)


def test_independent_evaluator_disproof():
    assert truth("x + 6 = 14", 8) and not truth("x + 6 = 14", 20)
    assert truth("4k = 28", 7) and not truth("4k = 28", 112)
    assert truth("24 ÷ n = 6", 4) and not truth("24 ÷ n = 6", 144)
    assert truth("12 ≥ y", 12) and not truth("12 ≥ y", 13)
    assert truth("3m > 12", 5) and not truth("3m > 12", 4)
    assert solve_one_step("x − 4 = 9") == 13
    assert solve_one_step("x = 3 ÷ 4") == Fraction(3, 4)
    assert solve_one_step("20x = 4") == Fraction(1, 5)
    assert solve_one_step("4 ÷ x = 3") == Fraction(4, 3)


# ---------------------------------------------------------------------------------------------
# Golden misconception cases (hand-worked)
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("form,a,b,expected", [
    ("add", 7, 15, {"SAME_OP": 22, "VALUE_SHOWN": 15}),     # x + 7 = 15 -> 8
    ("sub", 4, 9, {"SAME_OP": 5, "VALUE_SHOWN": 9}),        # x − 4 = 9 -> 13
    ("rsub", 15, 9, {"SAME_OP": 24}),                       # 15 − x = 9 -> 6
    ("mul", 4, 28, {"SAME_OP": 112, "SUBTRACTED": 24}),     # 4x = 28 -> 7
    ("div", 5, 6, {"ADDED": 11, "VALUE_SHOWN": 6}),         # x ÷ 5 = 6 -> 30
    ("div", 2, 8, {"SAME_OP": 4, "ADDED": 10}),             # x ÷ 2 = 8 -> 16
    ("rdiv", 24, 6, {"SAME_OP": 144}),                      # 24 ÷ x = 6 -> 4
])
def test_golden_one_step(form, a, b, expected):
    got = G._one_step_wrongs(form, a, b)
    for label, v in expected.items():
        assert (label, v) in got, (form, label)


def _t4_wrongs(kind, a, b):
    _, cands = G.T4_FORMS[kind]
    out = {}
    for label, form, swap in cands:
        wa, wb = (b, a) if swap else (a, b)
        out.setdefault(label, []).append(G.eq_text(form, "x", wa, wb))
    return out


@pytest.mark.parametrize("kind,a,b,label,text", [
    ("add", 6, 15, "WRONG_OP", f"x {M} 6 = 15"),   # had x, got 6 more, now 15
    ("add", 6, 15, "SWAPPED", "x + 15 = 6"),
    ("sub", 4, 9, "WRONG_OP", "x + 4 = 9"),        # had x, gave away 4, 9 left
    ("sub", 4, 9, "SWAPPED", f"4 {M} x = 9"),
    ("mul", 4, 20, "KEYWORD", f"x = 4 {X} 20"),    # 4 bags, x each, 20 in all
    ("mul", 4, 20, "SWAPPED", "20x = 4"),
    ("div", 4, 3, "WRONG_OP", "4x = 3"),           # x shared by 4, 3 each
    ("div", 4, 3, "SWAPPED", f"4 {D} x = 3"),
])
def test_golden_write_equation(kind, a, b, label, text):
    assert text in _t4_wrongs(kind, a, b)[label]


def test_golden_inequality_picks():
    import random
    for _ in range(50):
        correct, wrongs = G._pick_values(random.Random(_), "<", 4, 0, 20)
        assert correct < 4 and ("BOUNDARY", 4) in wrongs
        assert all(v > 4 for lab, v in wrongs if lab == "WRONG_SIDE")


def test_golden_inequality_words():
    item = G.gen_t5_write(__import__("random").Random(1), 0)
    var, op, n = item["choices"][0].split()
    by_op = {c.split()[1]: lab for c, lab in zip(item["choices"], item["misconceptions"])}
    assert by_op[G.FLIP[op]] == "FLIPPED_SIGN"
    assert by_op[G.TOGGLE[op]] == "STRICT_VS_INCLUSIVE"


# ---------------------------------------------------------------------------------------------
# Every baked item: exactly one right door, checked independently
# ---------------------------------------------------------------------------------------------
STATEMENT = [
    re.compile(r"^Which makes (.+) true\?$"),
    re.compile(r"^Solve: (.+)$"),
    re.compile(r"^Which is a solution of (.+)\?$"),
]


def statement_of(prompt):
    for r in STATEMENT:
        m = r.match(prompt)
        if m:
            return m.group(1)
    return None


@pytest.mark.parametrize("item", [it for it in ITEMS if statement_of(it["prompt"])],
                         ids=[it["id"] for it in ITEMS if statement_of(it["prompt"])])
def test_numeric_items_exactly_one_true_choice(item):
    st = statement_of(item["prompt"])
    vals = [int(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals)
    true_at = [i for i, v in enumerate(vals) if truth(st, v)]
    assert true_at == [item["answer"]], (item["prompt"], item["choices"])


def _story_model(prompt):
    """Independent reading of a tier-4 story: (kind, a, b, x)."""
    a, b = [int(n) for n in re.findall(r"\d+", prompt)]
    if re.search(r"shared|equal|split", prompt):
        return "div", a, b, Fraction(a * b)
    if "in all" in prompt:
        return "mul", a, b, Fraction(b, a)
    if re.search(r"Gave away|Spent|Ate|went home", prompt):
        return "sub", a, b, Fraction(a + b)
    assert re.search(r"more|Earned", prompt), prompt
    return "add", a, b, Fraction(b - a)


EXPECTED_EQ = {"add": "x + {a} = {b}", "sub": f"x {M} {{a}} = {{b}}", "mul": "{a}x = {b}",
               "div": f"x {D} {{a}} = {{b}}"}


@pytest.mark.parametrize("item", by_tier(4), ids=[it["id"] for it in by_tier(4)])
def test_write_equation_items(item):
    kind, a, b, x = _story_model(item["prompt"])
    assert x.denominator == 1 and x >= 1
    assert item["choices"][item["answer"]] == EXPECTED_EQ[kind].format(a=a, b=b)
    true_at = [i for i, c in enumerate(item["choices"]) if truth(c, x)]
    assert true_at == [item["answer"]], item
    sols = [solve_one_step(c) for c in item["choices"]]  # no two equations equal in value
    assert len(set(sols)) == len(sols), (item["choices"], sols)


WORD_OPS = [  # order matters: "no more than" before "more than"
    (r"no more than|at most|or less", LE),
    (r"at least|or more", GE),
    (r"fewer than|less than|below|under", "<"),
    (r"more than|taller than|greater than|over", ">"),
]


def _word_op(prompt):
    low = prompt.lower()
    for pat, op in WORD_OPS:
        if re.search(pat, low):
            return op
    raise AssertionError(prompt)


T5_WORDS = [it for it in by_tier(5) if it["prompt"].endswith("Which fits?")]


@pytest.mark.parametrize("item", T5_WORDS, ids=[it["id"] for it in T5_WORDS])
def test_word_inequalities(item):
    n = int(re.findall(r"\d+", item["prompt"])[0])
    var, op, num = item["choices"][item["answer"]].split()
    assert op == _word_op(item["prompt"]) and int(num) == n
    assert re.search(rf"\b{var}\b", item["prompt"]), item["prompt"]
    parsed = [tuple(c.split()) for c in item["choices"]]
    assert all(p[0] == var and int(p[2]) == n for p in parsed)
    assert len({p[1] for p in parsed}) == 4  # four different solution sets


def test_every_item_is_checked():
    checked = sum(1 for it in ITEMS if statement_of(it["prompt"])) + len(by_tier(4)) + len(T5_WORDS)
    assert checked == len(ITEMS)


# ---------------------------------------------------------------------------------------------
# Labels name the rule that produced the value (tiers 1–3, modelled here independently)
# ---------------------------------------------------------------------------------------------
def _model_wrongs(eq):
    """{value: allowed labels} for a one-step equation, from this file's own reading."""
    out = {}

    def put(v, lab):
        if v is not None and Fraction(v).denominator == 1:
            out.setdefault(int(v), set()).add(lab)

    nums = [int(n) for n in re.findall(r"\d+", eq)]
    for n in nums:
        put(n, "VALUE_SHOWN")
    if m := re.fullmatch(r"(?:[a-z] \+ (\d+) = (\d+)|(\d+) = [a-z] \+ (\d+))", eq):
        a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(4)), int(m.group(3)))
        put(b + a, "SAME_OP")
    elif m := re.fullmatch(rf"[a-z] {M} (\d+) = (\d+)", eq):
        put(int(m.group(2)) - int(m.group(1)), "SAME_OP")
    elif m := re.fullmatch(rf"(\d+) {M} [a-z] = (\d+)", eq):
        put(int(m.group(1)) + int(m.group(2)), "SAME_OP")
    elif m := re.fullmatch(r"(?:(\d+)[a-z] = (\d+)|(\d+) = (\d+)[a-z])", eq):
        a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(4)), int(m.group(3)))
        put(a * b, "SAME_OP")
        put(b - a, "SUBTRACTED")
    elif m := re.fullmatch(rf"[a-z] {D} (\d+) = (\d+)", eq):
        a, b = int(m.group(1)), int(m.group(2))
        put(Fraction(b, a), "SAME_OP")
        put(a + b, "ADDED")
    elif m := re.fullmatch(rf"(\d+) {D} [a-z] = (\d+)", eq):
        put(int(m.group(1)) * int(m.group(2)), "SAME_OP")
    else:
        raise AssertionError(eq)
    return out


@pytest.mark.parametrize("item", [it for it in ITEMS if it["tier"] <= 3],
                         ids=[it["id"] for it in ITEMS if it["tier"] <= 3])
def test_one_step_labels_match_their_rule(item):
    model = _model_wrongs(statement_of(item["prompt"]))
    for c, lab in zip(item["choices"], item["misconceptions"]):
        if lab is None or lab == "ARITH":
            continue
        assert lab in model.get(int(c), set()), (item["prompt"], c, lab)


def test_arith_is_filler_only():
    labels = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert labels["ARITH"] <= 0.15 * sum(labels.values())


def test_every_declared_misconception_used():
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert set(BAKED["misconceptions"]) <= used


def test_four_choices_everywhere():
    assert all(len(it["choices"]) == 4 for it in ITEMS)


# ---------------------------------------------------------------------------------------------
# Content bounds (manifest "bounds"), walked from the prompt text
# ---------------------------------------------------------------------------------------------
def _fact(a, b):
    return 2 <= a <= 10 and 2 <= b <= 10


def bounds_violations(prompt, choices=()):
    bad = []
    st = statement_of(prompt)
    if st is None and prompt.endswith("Equation?"):
        kind, a, b, x = _story_model(prompt)
        if kind in ("add", "sub") and not (1 <= a <= 20 and 1 <= b <= 20):
            bad.append("literal over 20")
        if kind == "mul" and not (b % a == 0 and _fact(a, b // a)):
            bad.append("not a times-table fact")
        if kind == "div" and not _fact(a, b):
            bad.append("not a times-table fact")
        if not (x.denominator == 1 and 1 <= x <= 100):
            bad.append(f"solution {x}")
        return bad
    if st is None and prompt.endswith("Which fits?"):
        n = int(re.findall(r"\d+", prompt)[0])
        return [] if 1 <= n <= 20 else [f"boundary {n}"]
    if st is None:
        return ["unrecognised prompt"]
    nums = [int(n) for n in re.findall(r"\d+", st)]
    if re.search(r"[<>≤≥]", st):  # inequality
        if m := re.fullmatch(r"(\d+)([a-z]) \S (\d+)", st):  # ax op b
            a, b = int(m.group(1)), int(m.group(3))
            if not (b % a == 0 and _fact(a, b // a)):
                bad.append("ax boundary not a times-table fact")
            if any(not 1 <= int(c) <= 10 for c in choices):
                bad.append("a choice plugged into ax is not 1-10")
        elif m := re.fullmatch(r"[a-z] \+ (\d+) \S (\d+)", st):
            a, b = int(m.group(1)), int(m.group(2))
            if a > 20 or b > 20:
                bad.append("literal over 20")
            if any(int(c) + a > 20 for c in choices):
                bad.append("a plugged-in sum over 20")
        elif not all(1 <= n <= 20 for n in nums):
            bad.append("boundary outside 1-20")
        return bad
    # one-step equation
    sol = solve_one_step(st)
    if sol.denominator != 1 or sol < 1:
        bad.append(f"solution {sol}")
    if "+" in st or M in st:
        if any(n > 20 for n in nums):
            bad.append("literal over 20")
        if sol > 40:
            bad.append(f"solution {sol} over 40")
    elif m := re.fullmatch(r"(?:(\d+)[a-z] = (\d+)|(\d+) = (\d+)[a-z])", st):
        a = int(m.group(1) or m.group(4))
        if not _fact(a, int(sol)):
            bad.append("ax = b not a times-table fact")
    elif m := re.fullmatch(rf"[a-z] {D} (\d+) = (\d+)", st):
        if not _fact(int(m.group(1)), int(m.group(2))):
            bad.append("x ÷ a = b not a times-table fact")
    elif m := re.fullmatch(rf"(\d+) {D} [a-z] = (\d+)", st):
        if not _fact(int(m.group(2)), int(sol)):
            bad.append("D ÷ x = q not a times-table fact")
    else:
        bad.append("unrecognised equation")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_content_bounds(item):
    assert bounds_violations(item["prompt"], item["choices"]) == [], item["prompt"]


def test_manifest_states_bounds():
    assert "times-table" in BAKED["bounds"] and "20" in BAKED["bounds"]


@pytest.mark.parametrize("prompt,choices,expect_bad", [
    ("Solve: x + 7 = 15", (), False),
    ("Solve: x + 25 = 30", (), True),            # literal 25
    ("Solve: 12x = 36", (), True),               # factor 12
    ("Solve: x ÷ 5 = 6", (), False),
    ("Solve: x ÷ 5 = 12", (), True),             # quotient 12: dividend 60 is not a fact
    ("Solve: 30 = x + 40", (), True),            # negative solution, literal 40
    ("Which makes 3x < 45 true?", ("14",), True),  # boundary 15, not a fact
    ("Which makes 3x < 12 true?", ("2", "4", "5", "6"), False),
    ("Which makes x + 6 > 10 true?", ("16",), True),  # 16 + 6 = 22
    ("6 bags, x apples each. 72 apples in all. Equation?", (), True),
    ("At least 25 players, p, can come. Which fits?", (), True),
])
def test_bounds_checker_catches(prompt, choices, expect_bad):
    assert bool(bounds_violations(prompt, choices)) == expect_bad, prompt
