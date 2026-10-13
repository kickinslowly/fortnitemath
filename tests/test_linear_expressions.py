"""linear-expressions cartridge (grade 7, 7.EE.A.1-2): golden misconceptions, an independent re-check
of every baked item, the manifest `bounds` walked on baked.json, and value-distinct choices.

The independent check never calls the generator's value engine or its builders to find an answer:
prompts are read with regexes, and every expression (prompt and choice) is rewritten to Python,
parsed with ``ast`` and reduced to a linear form over ``fractions.Fraction`` here.
"""
import ast
import json
import math
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "linear-expressions"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M = "−"  # U+2212


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


F = Fraction
UP_FORM = G.UP_FORMS[0][1]
OFF_FORM = G.OFF_FORMS[0][1]

GOLDEN = [
    # (builder call, expected prompt, expected answer, {label: expected wrong text})
    # ---- tier 1: combine like terms
    (lambda: G.t1_like_two("x", 5, -8), "Simplify: 5x − 8x", "−3x",
     {"IGNORED_MINUS": "13x", "ADD_SIZES": "−13x", "WRONG_SIGN": "3x", "DROPPED_VARIABLE": "−3"}),
    (lambda: G.t1_like_two("x", -7, 3), "Simplify: −7x + 3x", "−4x",
     {"ADD_SIZES": "−10x", "WRONG_SIGN": "4x", "DROPPED_VARIABLE": "−4"}),
    (lambda: G.t1_like_two("x", -4, -3), "Simplify: −4x − 3x", "−7x",
     {"IGNORED_MINUS": "−x", "WRONG_SIGN": "7x", "DROPPED_VARIABLE": "−7"}),
    (lambda: G.t1_like_const("a", 4, -1, 3, ("a", "k", "b")), "Simplify: 4a + 3 − a", "3a + 3",
     {"NO_COEF_ONE": "4a + 3", "IGNORED_MINUS": "5a + 3", "UNLIKE_COMBINED": "6a",
      "WRONG_SIGN": "−3a + 3", "DROPPED_VARIABLE": "6"}),
    (lambda: G.t1_like_const("x", 6, -2, -5, ("a", "k", "b")), "Simplify: 6x − 5 − 2x", "4x − 5",
     {"IGNORED_MINUS": "4x + 5", "WRONG_SIGN": "4x + 5", "UNLIKE_COMBINED": "−x"}),
    (lambda: G.t1_two_vars("x", "y", 3, -1, 2, ("a", "c", "b")), "Simplify: 3x + 2y − x",
     "2x + 2y",
     {"UNLIKE_COMBINED": "4x", "DROPPED_TERM": "2x", "NO_COEF_ONE": "3x + 2y",
      "IGNORED_MINUS": "4x + 2y", "WRONG_SIGN": "−2x + 2y"}),
    (lambda: G.t1_two_vars("x", "y", 2, 3, -4, ("c", "a", "b")), "Simplify: −4y + 2x + 3x",
     "−4y + 5x", {"IGNORED_MINUS": "4y + 5x", "UNLIKE_COMBINED": "y", "DROPPED_TERM": "5x"}),
    (lambda: G.t1_four("x", 4, -6, -3, 5, 0), "Simplify: 4x − 3 − 6x + 5", "−2x + 2",
     {"WRONG_SIGN": "2x + 2", "ADD_SIZES": "−2x + 8", "IGNORED_MINUS": "10x + 2",
      "DROPPED_VARIABLE": "0"}),
    # ---- tier 2: distribute with negatives
    (lambda: G.t2_distribute("x", -3, 1, -4), "Distribute: −3(x − 4)", "−3x + 12",
     {"PARTIAL_DIST": "−3x − 4", "SIGN_INSIDE": "−3x − 12", "IGNORED_OUTER_MINUS": "3x − 12",
      "UNLIKE_COMBINED": "9x"}),
    (lambda: G.t2_distribute("x", -1, 2, 5), "Distribute: −(2x + 5)", "−2x − 5",
     {"NEG_FIRST_ONLY": "−2x + 5", "IGNORED_OUTER_MINUS": "2x + 5", "UNLIKE_COMBINED": "−7x"}),
    (lambda: G.t2_distribute("x", 3, -1, 4), "Distribute: 3(−x + 4)", "−3x + 12",
     {"DROPPED_NEG": "3x + 12", "PARTIAL_DIST": "−3x + 4", "UNLIKE_COMBINED": "9x"}),
    (lambda: G.t2_distribute("x", 2, -3, -1), "Distribute: 2(−3x − 1)", "−6x − 2",
     {"DROPPED_NEG": "6x − 2", "PARTIAL_DIST": "−6x − 1", "UNLIKE_COMBINED": "−8x"}),
    (lambda: G.t2_distribute("x", -2, -3, 4), "Distribute: −2(−3x + 4)", "6x − 8",
     {"SIGN_INSIDE": "−6x − 8", "IGNORED_OUTER_MINUS": "−6x + 8", "PARTIAL_DIST": "6x + 4"}),
    (lambda: G.t2_distribute("x", -2, -1, 5, True), "Distribute: −2(5 − x)", "−10 + 2x",
     {"PARTIAL_DIST": "−10 − x", "IGNORED_OUTER_MINUS": "10 − 2x", "SIGN_INSIDE": "−10 − 2x"}),
    # ---- tier 3: add and subtract groups
    (lambda: G.t3_groups(("x", None), (5, 2), M, (2, -3)), "Simplify: (5x + 2) − (2x − 3)",
     "3x + 5",
     {"FIRST_TERM_ONLY": "3x − 1", "IGNORED_MINUS": "7x − 1", "WRONG_SIGN": "−3x + 5",
      "UNLIKE_COMBINED": "8x"}),
    (lambda: G.t3_groups(("a", None), (4, -1), "+", (-2, 6)), "Simplify: (4a − 1) + (−2a + 6)",
     "2a + 5",
     {"DROPPED_NEG": "6a + 5", "ADD_SIZES": "2a + 7", "UNLIKE_COMBINED": "7a",
      "WRONG_SIGN": "−2a + 5"}),
    (lambda: G.t3_groups(("x", None), (6, 0), M, (2, 3), single_first=True),
     "Simplify: 6x − (2x + 3)", "4x − 3", {"FIRST_TERM_ONLY": "4x + 3", "IGNORED_MINUS": "8x + 3"}),
    (lambda: G.t3_groups(("x", None), (3, 2), "+", (5, -4), neg_first=True),
     "Simplify: −(3x + 2) + (5x − 4)", "2x − 6", {"FIRST_TERM_ONLY": "2x − 2",
                                                  "IGNORED_MINUS": "8x − 2"}),
    (lambda: G.t3_groups(("x", "y"), (2, 3), M, (1, 5)), "Simplify: (2x + 3y) − (x + 5y)",
     "x − 2y", {"FIRST_TERM_ONLY": "x + 8y", "IGNORED_MINUS": "3x + 8y"}),
    (lambda: G.t3_mult_group("x", 3, -2, 2, 1, 4), "Simplify: 3x − 2 − 2(x + 4)", "x − 10",
     {"PARTIAL_DIST": "x − 6", "FIRST_TERM_ONLY": "x + 6", "IGNORED_MINUS": "5x + 6",
      "UNLIKE_COMBINED": "−9x"}),
    # ---- tier 4: factor
    (lambda: G.t4_factor_pos("x", 3, 2, 3), "Factor out the GCF: 6x + 9", "3(2x + 3)",
     {"PARTIAL_FACTOR": "3(2x + 9)", "SUB_FOR_DIV": "3(3x + 6)",
      "ONE_TERM_FACTOR": "6(x + 9)"}),
    (lambda: G.t4_factor_pos("x", 3, 2, 3), "Factor out the GCF: 6x + 9", "3(2x + 3)",
     {"ONE_TERM_FACTOR": "9(6x + 1)"}),
    (lambda: G.t4_factor_pos("n", 2, 1, 2), "Factor out the GCF: 2n + 4", "2(n + 2)",
     {"PARTIAL_FACTOR": "2(n + 4)", "ONE_TERM_FACTOR": "4(2n + 1)"}),
    (lambda: G.t4_factor_pos("x", 3, 2, 3, -1), "Factor out the GCF: 6x − 9", "3(2x − 3)",
     {"DROPPED_NEG": "3(2x + 3)", "PARTIAL_FACTOR": "3(2x − 9)"}),
    (lambda: G.t4_factor_pos("x", 4, 1, 2), "Factor out the GCF: 4x + 8", "4(x + 2)",
     {"SUB_FOR_DIV": "4(x + 4)", "PARTIAL_FACTOR": "4(x + 8)"}),
    (lambda: G.t4_factor_neg("x", 4, 1, 2, 1), "Factor out −4: −4x + 8", "−4(x − 2)",
     {"SIGN_FACTOR": "−4(x + 2)", "PARTIAL_FACTOR": "−4(x + 8)", "DROPPED_NEG": "4(x + 2)"}),
    (lambda: G.t4_fill_in("x", 4, 1, 3), "4x + 12 = 4(x + ?)", "3",
     {"PARTIAL_FACTOR": "12", "SIGN_FACTOR": "−3", "SUB_FOR_DIV": "8"}),
    (lambda: G.t4_fill_in("k", -3, 1, -2), "−3k + 6 = −3(k + ?)", "−2",
     {"PARTIAL_FACTOR": "6", "SIGN_FACTOR": "2", "SUB_FOR_DIV": "9"}),
    # ---- tier 5: rewrite to show meaning
    (lambda: G.t5_pct_change("p", OFF_FORM, 20, False), "Price p, then 20% off. New price?",
     "0.8p", {"PART_ONLY": "0.2p", "PERCENT_AS_NUMBER": "p − 20", "WRONG_DIRECTION": "1.2p",
              "PLACE_VALUE": "0.98p"}),
    (lambda: G.t5_pct_change("p", UP_FORM, 10, True), "Price p, then 10% tax. Total price?",
     "1.1p", {"PART_ONLY": "0.1p", "PERCENT_AS_NUMBER": "p + 0.1", "WRONG_DIRECTION": "0.9p",
              "PLACE_VALUE": "1.01p"}),
    (lambda: G.t5_dec_combine("a", 1, F(1, 20), "+"), "Simplify: a + 0.05a", "1.05a",
     {"PART_ONLY": "0.05a", "WRONG_DIRECTION": "0.95a", "PLACE_VALUE": "1.5a",
      "DROPPED_VARIABLE": "1.05"}),
    (lambda: G.t5_dec_combine("n", 1, F(1, 10), M), "Simplify: n − 0.1n", "0.9n",
     {"PART_ONLY": "0.1n", "WRONG_DIRECTION": "1.1n", "PLACE_VALUE": "0.99n",
      "DROPPED_VARIABLE": "0.9"}),
    (lambda: G.t5_fracs("x", F(1, 2), F(1, 4), "+"), "Simplify: (1/2)x + (1/4)x", "(3/4)x",
     {"ADD_ACROSS": "(1/3)x", "MULTIPLIED": "(1/8)x", "NO_CONVERT": "(1/2)x",
      "DROPPED_TERM": "(1/2)x", "DROPPED_VARIABLE": "3/4"}),
    (lambda: G.t5_fracs("x", F(2, 3), F(1, 6), M), "Simplify: (2/3)x − (1/6)x", "(1/2)x",
     {"NO_CONVERT": "(1/6)x", "MULTIPLIED": "(1/9)x", "DROPPED_TERM": "(2/3)x"}),
    (lambda: G.t5_multiplier(G.MULT_FORMS[True][0], 10, True), "Increase by 10%: multiply by what?",
     "1.1", {"PART_ONLY": "0.1", "PERCENT_AS_NUMBER": "10", "WRONG_DIRECTION": "0.9",
             "PLACE_VALUE": "1.01"}),
    (lambda: G.t5_multiplier(G.MULT_FORMS[False][1], 25, False),
     "Sale: 25% off. Sale price = old price × ?", "0.75",
     {"PART_ONLY": "0.25", "PERCENT_AS_NUMBER": "25"}),
    (lambda: G.t5_meaning("p", 20, True), "1.2p means p went up by what percent?", "20%",
     {"RATIO_AS_CHANGE": "120%", "PLACE_VALUE": "1.2%"}),
    (lambda: G.t5_meaning("b", 25, False), "0.75b means b dropped by what percent?", "25%",
     {"RATIO_AS_CHANGE": "75%", "PLACE_VALUE": "7.5%"}),
    (lambda: G.t5_perimeter("w", 2, 3), "Rectangle: width w, length 2w + 3. Perimeter?", "6w + 6",
     {"PARTIAL_DIST": "6w + 3", "HALF_PERIMETER": "3w + 3", "MISSING_SIDE": "5w + 6",
      "UNLIKE_COMBINED": "12w"}),
]


@pytest.mark.parametrize("case", GOLDEN, ids=[str(i) for i in range(len(GOLDEN))])
def test_golden(case):
    call, prompt, answer, expected = case
    built = call()
    assert built["prompt"] == prompt
    assert built["answer"] == answer
    got = wrongs(built)
    for lab, text in expected.items():
        assert text in got.get(lab, []), (lab, text, got)


def test_every_declared_key_has_a_golden_case_and_is_used():
    golden_keys = {lab for _, _, _, exp in GOLDEN for lab in exp}
    declared = set(BAKED["misconceptions"])
    assert declared == golden_keys, declared ^ golden_keys
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert declared <= used, declared - used


def test_generator_helpers():
    assert G.poly([(-3, "x"), (12, None)]) == "−3x + 12"
    assert G.poly([(1, "x"), (-1, "y"), (0, "z")]) == "x − y"
    assert G.poly([(0, "x")]) == "0"
    assert G.group(-1, "2x + 5") == "−(2x + 5)" and G.group(-3, "x − 4") == "−3(x − 4)"
    assert G.dec(F(21, 20)) == "1.05" and G.dec(F(4, 5)) == "0.8" and G.dec(F(12)) == "12"
    assert G.ok_dec(F(3, 4)) and G.ok_dec(F(21, 20)) and not G.ok_dec(F(5, 4))  # 1.25: 3 digits
    assert not G.ok_dec(F(39, 40))  # 0.975: 3 places
    # the generator's own value engine agrees that equal forms are one value
    assert G.fingerprint("3x + 6") == G.fingerprint("6 + 3x") == G.fingerprint("3(x + 2)")
    assert G.fingerprint("(1/2)x") == G.fingerprint("0.5x")
    assert G.fingerprint("n − 5") != G.fingerprint("5 − n")
    assert G.fingerprint("20%") != G.fingerprint("2%")


# ---------------------------------------------------------------------------------------------
# Independent evaluator: Python ast -> linear form over Fraction
# ---------------------------------------------------------------------------------------------
def to_python(text: str) -> str:
    s = text.replace(M, "-").replace("×", "*").replace("÷", "/")
    # implicit multiplication: 3x, 0.8p, 2(, x(, )(, )x
    return re.sub(r"(?<=[\dA-Za-z)])(?=[A-Za-z(])", "*", s)


def _clean(d):
    return {k: v for k, v in d.items() if v != 0}


def _is_const(d):
    return set(d) <= {""}


def _lin(n):
    if isinstance(n, ast.Constant):
        return _clean({"": Fraction(str(n.value))})
    if isinstance(n, ast.Name):
        return {n.id: Fraction(1)}
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        return {k: -v for k, v in _lin(n.operand).items()}
    if isinstance(n, ast.BinOp):
        a, b = _lin(n.left), _lin(n.right)
        op = type(n.op)
        if op in (ast.Add, ast.Sub):
            out = dict(a)
            for k, v in b.items():
                out[k] = out.get(k, 0) + (v if op is ast.Add else -v)
            return _clean(out)
        if op is ast.Mult:
            if _is_const(a):
                c, other = a.get("", Fraction(0)), b
            elif _is_const(b):
                c, other = b.get("", Fraction(0)), a
            else:
                raise AssertionError("not linear")
            return _clean({k: c * v for k, v in other.items()})
        if op is ast.Div:
            assert _is_const(b) and b, "division by a non-constant"
            return _clean({k: v / b[""] for k, v in a.items()})
    raise AssertionError(f"unexpected node {ast.dump(n)}")


def lin_of(text: str) -> dict:
    return _lin(ast.parse(to_python(text), mode="eval").body)


def value_of(text: str):
    """Identity of a choice's value: a percent by its number, anything else by its linear form."""
    text = text.strip()
    if text.endswith("%"):
        return ("pct", Fraction(text[:-1]))
    return ("lin", tuple(sorted(lin_of(text).items())))


def test_evaluator_sanity():
    assert to_python("2(3x − 4)") == "2*(3*x - 4)"
    assert to_python("0.8p") == "0.8*p" and to_python("(3/4)x") == "(3/4)*x"
    assert lin_of("−3(x − 4)") == {"x": F(-3), "": F(12)}
    assert lin_of("−(2x + 5)") == {"x": F(-2), "": F(-5)}
    assert lin_of("(1/2)x + (1/4)x") == {"x": F(3, 4)}
    assert lin_of("1.05a") == {"a": F(21, 20)}
    assert lin_of("5/8") == {"": F(5, 8)}
    assert lin_of("3x + 6") == lin_of("6 + 3x") == lin_of("3(x + 2)")
    assert lin_of("n − 5") != lin_of("5 − n")
    assert lin_of("x − x") == {}
    assert value_of("20%") == ("pct", F(20)) and value_of("0.5%") == ("pct", F(1, 2))
    with pytest.raises(AssertionError):
        lin_of("x(x + 1)")  # a product of letters is not linear


# ---------------------------------------------------------------------------------------------
# Every choice value-distinct; exactly one right door
# ---------------------------------------------------------------------------------------------
def distinct(choices) -> bool:
    vals = [value_of(c) for c in choices]
    return len(set(vals)) == len(vals)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_distinct_in_value(item):
    assert distinct(item["choices"]), item["choices"]
    assert len(item["choices"]) == 4


@pytest.mark.parametrize("choices", [
    [f"{M}3x", f"2x {M} 5x", "3x", "13x"],               # a second right door, written differently
    ["3x + 6", "6 + 3x", "3x", "6x"],                    # order of terms
    ["3(x + 2)", "3x + 6", "x", "2x"],                   # factored vs expanded
    ["(1/2)x", "0.5x", "(3/4)x", "x"],                   # a fraction and its decimal
    ["0.8p", "p − 0.2p", "0.2p", "1.2p"],                # an unsimplified form
    ["25%", "25.0%", "75%", "2.5%"],                     # the same percent twice
])
def test_distinct_checker_catches(choices):
    assert not distinct(choices)


def test_distinct_checker_passes_distinct_choices():
    assert distinct([f"{M}3x", "3x", f"{M}13x", "13x"])
    assert distinct(["25%", "75%", "0.75%", "7.5%"])


# ---------------------------------------------------------------------------------------------
# Independent answer check
# ---------------------------------------------------------------------------------------------
def is_simplified(text: str) -> list:
    """No brackets, at most one term per letter and one number."""
    bad = []
    if "(" in text or ")" in text:
        bad.append("has brackets")
    terms = re.split(r" [+−] ", text)
    keys = [re.sub(r"^[−]?[\d.]*", "", t) or "#" for t in terms]
    if len(keys) != len(set(keys)):
        bad.append("a like term appears twice")
    lin = lin_of(text)
    if len(lin) != len(terms):
        bad.append("a term cancels or is not in lowest terms")
    return bad


def signed(n) -> str:
    n = int(n)
    return str(n) if n >= 0 else f"{M}{-n}"


def pct_text(f: Fraction) -> str:
    return f"{f.numerator}%" if f.denominator == 1 else f"{float(f):g}%"


def exactly_one_right(item, expected, key=value_of):
    """The expected value is held by exactly one choice, and it is the answer."""
    ch, ans = item["choices"], item["choices"][item["answer"]]
    matches = [c for c in ch if key(c) == expected]
    return [] if matches == [ans] else [f"right doors {matches}, answer {ans!r}"]


def gcd_all(values):
    g = 0
    for v in values:
        g = math.gcd(g, int(abs(v)))
    return g


def answer_problems(item) -> list:
    """[] when the baked answer of ``item`` is right and the only right door, else the reasons."""
    p, tier = item["prompt"], item["tier"]
    ans = item["choices"][item["answer"]]
    bad = []
    if len(item["choices"]) != 4:
        bad.append("not 4 choices")
    # tiers 1-3: Simplify / Distribute an expression
    m = re.match(r"^(Simplify|Distribute): (.+)$", p)
    if m:
        kind, expr = m.groups()
        if re.fullmatch(r"(\d*)([a-z]) [+−] 0\.\d+\2", expr):  # tier 5 decimals: its own branch
            return bad + t5_decimal_problems(item)
        if re.fullmatch(r"\(\d+/\d+\)([a-z]) [+−] \(\d+/\d+\)\1", expr):
            return bad + t5_fraction_problems(item)
        bad += exactly_one_right(item, value_of(expr))
        bad += is_simplified(ans)
        if tier == 1 and "(" in p:
            bad.append("tier 1 prompt has brackets")
        if tier == 3 and "(" not in p:
            bad.append("tier 3 prompt has no brackets")
        if kind == "Distribute" and tier != 2:
            bad.append("Distribute outside tier 2")
        return bad
    # tier 4: factor
    m = re.match(r"^Factor out the GCF: (.+)$", p)
    if m:
        expected = lin_of(m.group(1))
        bad += exactly_one_right(item, value_of(m.group(1)))
        mm = re.fullmatch(r"(\d+)\((.+)\)", ans)
        if not mm:
            return bad + [f"answer {ans!r} is not g(...)"]
        g, inner = int(mm.group(1)), lin_of(mm.group(2))
        if {k: g * v for k, v in inner.items()} != expected:
            bad.append("g × inner is not the prompt")
        if g != gcd_all(expected.values()) or g < 2:
            bad.append(f"{g} is not the GCF of {m.group(1)}")
        if gcd_all(inner.values()) != 1:
            bad.append("the bracket still has a common factor")
        return bad
    m = re.match(rf"^Factor out {M}(\d+): (.+)$", p)
    if m:
        g, expr = int(m.group(1)), m.group(2)
        expected = lin_of(expr)
        bad += exactly_one_right(item, value_of(expr))
        mm = re.fullmatch(rf"{M}(\d+)\((.+)\)", ans)
        if not mm or int(mm.group(1)) != g:
            return bad + [f"answer {ans!r} does not start with {M}{g}("]
        inner = lin_of(mm.group(2))
        if {k: -g * v for k, v in inner.items()} != expected:
            bad.append("−g × inner is not the prompt")
        if gcd_all(expected.values()) != g or gcd_all(inner.values()) != 1:
            bad.append("not the greatest common factor")
        return bad
    m = re.fullmatch(r"(.+) = (−?\d+)\(([^+]+) \+ \?\)", p)
    if m:
        expr, f, pv = m.group(1), int(m.group(2).replace(M, "-")), m.group(3)
        lin, head = lin_of(expr), lin_of(pv)
        letter = next(iter(head))
        if lin.get(letter) != f * head[letter]:
            bad.append("the letter term does not match the bracket")
        want = lin.get("", F(0)) / f
        if want.denominator != 1 or ans != signed(want):
            bad.append(f"answer {ans!r}, want {want}")
        if len({value_of(c) for c in item["choices"]}) != 4:
            bad.append("equal choices")
        return bad
    return bad + t5_problems(item)


def t5_problems(item) -> list:
    p = item["prompt"]
    ch, ans = item["choices"], item["choices"][item["answer"]]
    bad = []
    pct = re.search(r"(\d+)%", p)
    # a price changes by r %: one-term form
    if pct and re.search(r"(off|taken off|tax|tip|raise|grows|rises)", p) and "multiply" not in p \
            and "× ?" not in p:
        r = Fraction(int(pct.group(1)), 100)
        down = bool(re.search(r"(off|taken off)", p))
        letter = re.search(r"([a-z])$", ans) or re.search(r"([a-z])", ans)
        v = letter.group(1)
        if not re.search(rf"\b{v}\b", p):
            bad.append(f"letter {v} is not in the prompt")
        expected = {v: 1 - r if down else 1 + r}
        return bad + exactly_one_right(item, ("lin", tuple(sorted(expected.items()))))
    m = re.match(r"^(Increase|Decrease) by (\d+)%: multiply by what\?$", p) or \
        re.match(r"^A price (rises) (\d+)%\. New price = old price × \?$", p) or \
        re.match(r"^Sale: (\d+)% off\. Sale price = old price × \?$", p)
    if m:
        groups = m.groups()
        r = Fraction(int(groups[-1]) if len(groups) == 2 else int(groups[0]), 100)
        up = len(groups) == 2 and groups[0] in ("Increase", "rises")
        expected = ("lin", tuple(sorted(_clean({"": 1 + r if up else 1 - r}).items())))
        return bad + exactly_one_right(item, expected)
    m = re.match(r"^([\d.]+)([a-z]) means \2 (went up|dropped) by what percent\?$", p)
    if m:
        coef, up = Fraction(m.group(1)), m.group(3) == "went up"
        change = (coef - 1 if up else 1 - coef) * 100
        if ans != pct_text(change):
            bad.append(f"answer {ans!r}, want {pct_text(change)}")
        return bad + exactly_one_right(item, ("pct", change))
    m = re.match(r"^Rectangle: width ([a-z]), length (\d*)\1 \+ (\d+)\. Perimeter\?$", p)
    if m:
        v, k, c = m.group(1), int(m.group(2) or 1), int(m.group(3))
        expected = _clean({v: Fraction(2 + 2 * k), "": Fraction(2 * c)})
        return bad + exactly_one_right(item, ("lin", tuple(sorted(expected.items()))))
    return bad + [f"unrecognised prompt {p!r}"]


def t5_decimal_problems(item) -> list:
    m = re.fullmatch(r"Simplify: (\d*)([a-z]) ([+−]) (0\.\d+)\2", item["prompt"])
    a, v, op, r = int(m.group(1) or 1), m.group(2), m.group(3), Fraction(m.group(4))
    expected = a + r if op == "+" else a - r
    return exactly_one_right(item, ("lin", ((v, expected),)))


def t5_fraction_problems(item) -> list:
    m = re.fullmatch(r"Simplify: \((\d+)/(\d+)\)([a-z]) ([+−]) \((\d+)/(\d+)\)\3", item["prompt"])
    f1, f2 = Fraction(int(m.group(1)), int(m.group(2))), Fraction(int(m.group(5)), int(m.group(6)))
    res = f1 + f2 if m.group(4) == "+" else f1 - f2
    return exactly_one_right(item, ("lin", ((m.group(3), res),)))


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    assert answer_problems(item) == [], (item["prompt"], item["choices"])
    ans = item["choices"][item["answer"]]
    assert ans in item["explanation"], (item["prompt"], ans, item["explanation"])


def explanation_problems(text: str) -> list:
    """Every 'A = B' the explanation writes (numbers or linear expressions, chained or not) must
    hold; pieces that are not arithmetic (words, percents) are skipped."""
    bad = []
    for piece in re.split(r"\.(?=\s|$)|[:;,]| and ", text):
        piece = re.sub(r"^\s*(So|Then)\s+", "", piece).strip()
        if " = " not in piece:
            continue
        try:
            sides = [lin_of(s) for s in piece.split(" = ")]
        except (SyntaxError, AssertionError, ValueError, KeyError, ZeroDivisionError):
            continue
        if any(s != sides[0] for s in sides):
            bad.append(piece)
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_explanation_arithmetic_holds(item):
    assert explanation_problems(item["explanation"]) == [], item["explanation"]


def test_explanation_checker_is_not_vacuous():
    """Most explanations carry at least one equation, and the tier-3 ones restate the prompt."""
    with_eq = sum(1 for it in ITEMS if " = " in it["explanation"])
    assert with_eq >= 120, with_eq
    for it in by_tier(3):
        expr = it["prompt"].split(": ", 1)[1]
        flat = re.search(r": ([^.]*?)\. (?:Combine|Combine like terms)", it["explanation"])
        assert flat, it["explanation"]
        assert lin_of(flat.group(1)) == lin_of(expr), (it["prompt"], it["explanation"])


@pytest.mark.parametrize("text", [
    "Add the coefficients: 5 − 8 = −2. So 5x − 8x = −2x.",      # wrong sum
    "Multiply each term by −3: −3 × 4n = 12n and −3 × 2 = −6.",  # wrong product
    "Like terms: 4a − a = 2a. 3 has no a, so it stays: 2a + 3.",  # wrong combine
    "Use denominator 4: 2/4 + 1/4 = 1/4. So (3/4)x.",             # wrong fraction sum
])
def test_explanation_checker_catches(text):
    assert explanation_problems(text) != []


def test_explanation_checker_does_not_flag_good_text():
    assert explanation_problems("Add the coefficients: 5 − 8 = −3. So 5x − 8x = −3x.") == []
    assert explanation_problems("0.75b = b − 0.25b, and 0.25 is 25%, so b dropped by 25%.") == []
    assert explanation_problems("Use denominator 12: 1/12 + 8/12 = 9/12 = 3/4. So (3/4)a.") == []


def _fake(prompt, tier, choices, answer, **kw):
    return {"prompt": prompt, "tier": tier, "choices": choices, "answer": answer,
            "explanation": "", **kw}


@pytest.mark.parametrize("item", [
    # right answer marked as a wrong choice
    _fake("Simplify: 5x − 8x", 1, ["3x", f"{M}3x", f"{M}13x", "13x"], 0),
    # two right doors: 2x − 5x equals −3x
    _fake("Simplify: 5x − 8x", 1, [f"{M}3x", f"2x {M} 5x", "3x", "13x"], 0),
    # not simplified
    _fake("Simplify: 5x − 8x + 2", 1, [f"{M}3x + 2", "3x + 2", f"{M}13x + 2", f"5x {M} 8x + 2"], 3),
    # wrong expansion marked right
    _fake("Distribute: −3(x − 4)", 2, [f"{M}3x {M} 12", f"{M}3x + 12", "3x − 12", f"{M}3x {M} 4"], 0),
    # a factored form that is not the GCF
    _fake("Factor out the GCF: 12x + 6", 4, ["2(6x + 3)", "2(6x + 6)", "6(x + 6)", "2(5x + 2)"], 0),
    # factoring: g × bracket is not the prompt
    _fake("Factor out the GCF: 6x + 9", 4, ["3(2x + 9)", "3(2x + 3)", "6(x + 9)", "3(3x + 6)"], 0),
    # fill-in with the wrong number
    _fake("4x + 12 = 4(x + ?)", 4, ["12", "3", f"{M}3", "8"], 0),
    # percent change, wrong coefficient marked right
    _fake("Price p, then 20% off. New price?", 5, ["1.2p", "0.8p", "0.2p", "p − 20"], 0),
    # meaning
    _fake("1.2p means p went up by what percent?", 5, ["120%", "20%", "12%", "2%"], 0),
    # perimeter
    _fake("Rectangle: width w, length w + 3. Perimeter?", 5, ["2w + 3", "4w + 6", "4w + 3", "3w + 6"], 0),
    # fractions added across
    _fake("Simplify: (1/2)x + (1/4)x", 5, ["(1/3)x", "(3/4)x", "(1/8)x", "(1/2)x"], 0),
])
def test_answer_checker_catches(item):
    """Disproof: the independent check is not vacuous."""
    assert answer_problems(item) != []


def test_answer_checker_accepts_a_correct_item():
    good = _fake("Simplify: 4a + 3 − a", 1, ["3a + 3", "4a + 3", "5a + 3", "6a"], 0)
    assert answer_problems(good) == []
    good = _fake("Factor out −4: −4x + 8", 4, [f"{M}4(x {M} 2)", f"{M}4(x + 2)", "4(x + 2)",
                                                f"{M}4(x + 8)"], 0)
    assert answer_problems(good) == []


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"; PROTOCOL §4a/§4b), walked on every baked prompt and correct answer
# ---------------------------------------------------------------------------------------------
def walk_violations(text: str) -> list:
    """Tiers 1-4 expression: every literal 1-12; a term coefficient 1-12; an outside multiplier
    1-10; every intermediate coefficient and constant a whole number of size <= 12; no x^2, no
    division."""
    bad = []

    def literal(n):
        v = Fraction(str(n.value))
        if v.denominator != 1 or not 1 <= v <= 12:
            bad.append(f"literal {v} outside 1..12")

    def check(d, what):
        for k, v in d.items():
            if v.denominator != 1 or abs(v) > 12:
                bad.append(f"{what}: coefficient {v} of {k or 'number'} outside size 12")

    def walk(n):
        if isinstance(n, ast.Constant):
            literal(n)
            return _lin(n)
        if isinstance(n, ast.Name):
            return _lin(n)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            if isinstance(n.operand, ast.Constant):
                literal(n.operand)
            return {k: -v for k, v in walk(n.operand).items()}
        if isinstance(n, ast.BinOp):
            op = type(n.op)
            a, b = walk(n.left), walk(n.right)
            if op in (ast.Add, ast.Sub):
                out = _lin(n)
                check(out, "sum")
                return out
            if op is ast.Mult:
                term = isinstance(n.left, ast.Name) or isinstance(n.right, ast.Name)
                const, other = (a, b) if _is_const(a) else (b, a)
                c = abs(const.get("", Fraction(0)))
                if not term and not 1 <= c <= 10:
                    bad.append(f"multiplier {c} outside 1..10")
                if not term and any(abs(v) > 10 for v in other.values()):
                    bad.append("a bracketed coefficient over 10 times a multiplier")
                out = _lin(n)
                check(out, "product")
                return out
            bad.append(f"operator {op.__name__} not allowed")
            return {}
        bad.append(f"node {type(n).__name__} not allowed")
        return {}

    walk(ast.parse(to_python(text), mode="eval").body)
    return bad


DEC_TOKEN = re.compile(r"(?<![\d.])\d+\.\d+")
FRAC_TOKEN = re.compile(r"(\d+)/(\d+)")
DOWN_OK, UP_OK = {10, 20, 25, 30, 40, 50, 60, 75}, {5, 10, 20, 30, 40, 50}


def decimal_violations(text: str) -> list:
    bad = []
    for tok in DEC_TOKEN.findall(text):
        places = len(tok.split(".")[1])
        nonzero = sum(ch not in "0." for ch in tok)
        if places > 2 or nonzero > 2:
            bad.append(f"decimal {tok}: {places} places, {nonzero} non-zero digits")
    return bad


def fraction_violations(text: str, proper=True) -> list:
    bad = []
    for n, d in FRAC_TOKEN.findall(text):
        n, d = int(n), int(d)
        if not 2 <= d <= 12 or not 1 <= n <= 12 or math.gcd(n, d) != 1 or (proper and n >= d):
            bad.append(f"fraction {n}/{d}")
    return bad


def bounds_violations(item) -> list:
    p, tier = item["prompt"], item["tier"]
    ans = item["choices"][item["answer"]]
    bad = []
    if tier <= 4:
        m = re.match(rf"^(?:Simplify|Distribute|Factor out the GCF|Factor out {M}\d+): (.+)$", p)
        fill = re.fullmatch(rf"(.+) = ({M}?\d+)\(([^+]+) \+ \?\)", p)
        if m:
            bad += walk_violations(m.group(1))
            bad += [f"answer: {b}" for b in walk_violations(ans)]
            if tier != 4 and not lin_of(ans):
                bad.append("the answer cancels to nothing")
            if tier == 4:
                mm = re.fullmatch(rf"{M}?(\d+)\((.+)\)", ans)
                if not mm or not 2 <= int(mm.group(1)) <= 6:
                    bad.append(f"GCF of {ans!r} outside 2..6")
                elif any(abs(v) > 6 for v in lin_of(mm.group(2)).values()):
                    bad.append("a bracket part over 6")
        elif fill:
            bad += walk_violations(fill.group(1))
            if not 2 <= abs(int(fill.group(2).replace(M, "-"))) <= 6:
                bad.append("factor outside 2..6")
            if not 1 <= abs(int(ans.replace(M, "-"))) <= 6:
                bad.append("fill-in answer outside 1..6")
        else:
            bad.append(f"unrecognised prompt {p!r}")
        return bad
    # tier 5
    texts = [p] + item["choices"]
    for t in texts:
        bad += decimal_violations(t)
    pct = re.search(r"(\d+)%", p)
    if pct and not re.search(r"(means|percent)", p):
        r = int(pct.group(1))
        down = bool(re.search(r"(off|Decrease)", p))
        if r not in (DOWN_OK if down else UP_OK):
            bad.append(f"percent {r} not allowed for this direction")
    m = re.match(r"^([\d.]+)([a-z]) means", p)
    if m:
        coef = Fraction(m.group(1))
        r = abs(coef - 1) * 100
        down = "dropped" in p
        if r.denominator != 1 or int(r) not in (DOWN_OK if down else UP_OK):
            bad.append(f"meaning percent {r} not allowed")
    if FRAC_TOKEN.search(p):
        fr = [(int(a), int(b)) for a, b in FRAC_TOKEN.findall(p)]
        bad += fraction_violations(p)
        for c in item["choices"]:
            bad += fraction_violations(c)
            if "." in c:
                bad.append("a decimal among fraction choices")
        (n1, d1), (n2, d2) = fr
        if d1 == d2 or d1 * d2 // math.gcd(d1, d2) > 12:
            bad.append("denominators not unlike or lcm over 12")
        if "." in p:
            bad.append("fractions and decimals mixed")
    elif DEC_TOKEN.search(p) or "%" in p or "Simplify" in p:
        for c in item["choices"]:
            if FRAC_TOKEN.search(c):
                bad.append("a fraction among decimal choices")
    m = re.match(r"^Simplify: (\d*)([a-z]) ([+−]) (0\.\d+)\2$", p)
    if m:
        a, r = int(m.group(1) or 1), Fraction(m.group(4))
        if not 1 <= a <= 5 or r not in {F(n, 100) for n in (5, 10, 20, 25, 30, 40, 50, 60, 75)}:
            bad.append("decimal operand out of range")
    m = re.match(r"^Rectangle: width ([a-z]), length (\d*)\1 \+ (\d+)\.", p)
    if m:
        k, c = int(m.group(2) or 1), int(m.group(3))
        if not (1 <= k <= 3 and 1 <= c <= 6):
            bad.append("perimeter parameters out of range")
        if any(abs(v) > 12 for v in lin_of(ans).values()):
            bad.append("perimeter answer over size 12")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item) == [], (item["prompt"], item["choices"])


@pytest.mark.parametrize("prompt,tier,choices,answer,expect_bad", [
    ("Simplify: 5x − 8x", 1, [f"{M}3x"], 0, False),
    ("Simplify: 13x − 2x", 1, ["11x"], 0, True),                     # literal 13
    ("Simplify: 9x + 9x", 1, ["18x"], 0, True),                      # answer coefficient 18
    ("Simplify: x^2 + x", 1, ["x"], 0, True),                        # power
    ("Distribute: −3(x − 4)", 2, [f"{M}3x + 12"], 0, False),
    ("Distribute: −4(3x − 5)", 2, [f"{M}12x + 20"], 0, True),        # 4 × 5 = 20
    ("Distribute: 12(x + 1)", 2, ["12x + 12"], 0, True),             # multiplier 12
    ("Distribute: −(12x + 11)", 2, [f"{M}12x {M} 11"], 0, False),    # bare minus, size 12 is the cap
    ("Simplify: (9x + 8) + (9x + 1)", 3, ["18x + 9"], 0, True),      # combined coefficient 18
    ("Simplify: (5x + 2) − (2x − 3)", 3, ["3x + 5"], 0, False),
    ("Factor out the GCF: 6x + 9", 4, ["3(2x + 3)"], 0, False),
    ("Factor out the GCF: 24x + 36", 4, ["12(2x + 3)"], 0, True),    # literal 24, GCF 12
    ("Factor out the GCF: 8x + 12", 4, ["4(2x + 3)"], 0, False),
    ("4x + 12 = 4(x + ?)", 4, ["3"], 0, False),
    ("Price p, then 20% off. New price?", 5, ["0.8p"], 0, False),
    ("Price p, then 15% off. New price?", 5, ["0.85p"], 0, True),    # 15 % is not in the set
    ("Cost c rises 25%. New cost?", 5, ["1.25c"], 0, True),          # 25 % up; 1.25 has 3 digits
    ("Simplify: a + 0.25a", 5, ["1.25a"], 0, True),                  # decimal rule
    ("Simplify: (1/2)x + (1/4)x", 5, ["(3/4)x"], 0, False),
    ("Simplify: (1/2)x + (1/5)x", 5, ["(7/10)x"], 0, False),
    ("Simplify: (1/5)x + (1/7)x", 5, ["(12/35)x"], 0, True),         # lcm 35, denominator 35
    ("Simplify: (1/2)x + (1/4)x", 5, ["(3/4)x", "0.75x"], 0, True),  # decimal among fractions
    ("Rectangle: width w, length 3w + 6. Perimeter?", 5, ["8w + 12"], 0, False),
    ("Rectangle: width w, length 3w + 7. Perimeter?", 5, ["8w + 14"], 0, True),
])
def test_bounds_checker_catches(prompt, tier, choices, answer, expect_bad):
    got = bounds_violations({"prompt": prompt, "tier": tier, "choices": choices, "answer": answer})
    assert bool(got) == expect_bad, (prompt, got)


# ---------------------------------------------------------------------------------------------
# Shape and balance
# ---------------------------------------------------------------------------------------------
def test_arith_share_is_small():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.10
    for t in range(1, 6):
        ct = Counter(m for it in by_tier(t) for m in it["misconceptions"] if m)
        assert ct["ARITH"] / sum(ct.values()) <= 0.15, t


def test_every_item_has_a_real_misconception():
    for it in ITEMS:
        assert sum(1 for m in it["misconceptions"] if m and m != "ARITH") >= 2, it["id"]


def test_text_is_clean():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in s, s                      # U+2212 only, never a hyphen
            assert not re.search(r"[+−] [+−]|\(\+|\+\)", s), s    # doubled signs
            assert "^" not in s, s                      # no powers anywhere
        for s in [it["prompt"], *it["choices"]]:
            assert not re.search(r"(?<![\d.])[01](?=[a-z])", s), s   # never 1x or 0x


def test_answer_positions_balanced():
    for t in range(1, 6):
        c = Counter(it["answer"] for it in by_tier(t))
        assert all(8 <= c[p] <= 12 for p in range(4)), (t, c)


def test_tier_kinds_present():
    """Each tier shows its concept in the prompts (a cheap guard against a tier collapsing)."""
    t1, t2, t3, t4, t5 = (by_tier(t) for t in range(1, 6))
    assert all("(" not in it["prompt"] and M in it["prompt"] for it in t1)
    assert all(it["prompt"].startswith("Distribute: ") and "(" in it["prompt"] for it in t2)
    assert all(it["prompt"].startswith("Simplify: ") and it["prompt"].count("(") >= 1 for it in t3)
    assert any(it["prompt"].startswith(f"Factor out {M}") for it in t4)
    assert any(" = " in it["prompt"] for it in t4)
    assert sum(1 for it in t5 if "%" in it["prompt"]) >= 15
    assert sum(1 for it in t5 if FRAC_TOKEN.search(it["prompt"])) >= 5


def test_bake_matches_generator():
    """baked.json is what the generator makes from the manifest seed (no hand edits, no drift)."""
    import random
    manifest = {k: v for k, v in BAKED.items() if k not in ("baked_with", "items")}
    fresh = G.generate(manifest, random.Random(manifest["seed"]))
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == fresh
