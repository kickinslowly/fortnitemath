"""two-step-equations cartridge (grade 7): golden misconception cases, an independent re-check of every
baked item, label checks, and the cartridge's content bounds asserted on baked.json.

The independent check never calls the generator's solver or its candidate functions on a baked item.
It rewrites every prompt to a Python expression and plugs values in with ``fractions.Fraction``
(equations, inequalities by a truth table over sample points), reads the stories with this file's own
regexes (one per story template), and models every misconception label with its own formulas.
"""
import json
import random
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "two-step-equations"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M, X, D, LE, GE = "−", "×", "÷", "≤", "≥"
FLIP = {"<": ">", ">": "<", LE: GE, GE: LE}
TOGGLE = {"<": LE, LE: "<", ">": GE, GE: ">"}


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def as_int(s):
    return int(s.replace(M, "-"))


# ---------------------------------------------------------------------------------------------
# Independent evaluator: display text -> exact value / truth with a number plugged in
# ---------------------------------------------------------------------------------------------
TOKEN = re.compile(r"\s*(\d+|[a-z]|[+\-*/()]|==|<=|>=|<|>)")


def to_python(text: str) -> str:
    s = (text.replace(M, "-").replace(X, "*").replace(D, "/").replace(LE, "<=").replace(GE, ">="))
    s = re.sub(r"(?<![<>=])=(?!=)", "==", s)
    return re.sub(r"(\d)([a-z(])", r"\1*\2", s)  # 4x -> 4*x, 3(x -> 3*(x


def variable_of(text: str) -> str:
    letters = set(re.findall(r"[a-z]", text))
    assert len(letters) == 1, text
    return letters.pop()


def evaluate(expr: str, value, var: str):
    py, pos, out = to_python(expr), 0, []
    while pos < len(py):  # whitelist tokens, then wrap numbers in Fraction
        m = TOKEN.match(py, pos)
        assert m, (expr, py[pos:])
        tok = m.group(1)
        if tok.isdigit():
            out.append(f"F({tok})")
        elif tok == var:
            f = Fraction(value)
            out.append(f"F({f.numerator}, {f.denominator})")
        else:
            assert not tok.isalpha(), ("second variable", expr)
            out.append(tok)
        pos = m.end()
    return eval(" ".join(out), {"F": Fraction, "__builtins__": {}})


def truth(statement: str, value) -> bool:
    return bool(evaluate(statement, value, variable_of(statement)))


def linear_parts(eq: str):
    """(a, b, R) for 'a·v + b = R' read from the text (either side may hold the variable; the
    variable appears on one side only)."""
    v = variable_of(eq)
    lhs, rhs = eq.split(" = ")
    if v not in lhs:
        lhs, rhs = rhs, lhs
    assert v not in rhs, eq
    R = evaluate(rhs, 0, v)
    b = evaluate(lhs, 0, v)
    a = evaluate(lhs, 1, v) - b
    assert evaluate(lhs, 2, v) - evaluate(lhs, 1, v) == a, eq  # linear
    assert a.denominator == b.denominator == R.denominator == 1, eq
    return int(a), int(b), int(R)


def solve_linear(eq: str) -> Fraction:
    a, b, R = linear_parts(eq)
    return Fraction(R - b, a)


GROUP = re.compile(rf"^(?:(?P<R1>{M}?\d+) = )?(?P<p>{M}?\d+)\((?P<v>[a-z]) (?P<s>[+{M}]) (?P<q>\d+)\)"
                   rf"(?: = (?P<R2>{M}?\d+))?$")


def group_parts(text: str):
    """(p, q, R, var) for 'p(v + q) = R' or 'R = p(v + q)'."""
    m = GROUP.match(text)
    assert m, text
    q = int(m.group("q")) * (1 if m.group("s") == "+" else -1)
    return as_int(m.group("p")), q, as_int(m.group("R1") or m.group("R2")), m.group("v")


def test_independent_evaluator_disproof():
    assert truth("2x + 6 = 14", 4) and not truth("2x + 6 = 14", 10)
    assert truth("−2x + 5 = 11", -3) and not truth("−2x + 5 = 11", 3)
    assert truth("5 − 2x = 11", -3) and not truth("5 − 2x = 11", 3)
    assert truth("3(x + 2) = 21", 5) and not truth("3(x + 2) = 21", 9)
    assert truth("−3(n − 2) = 12", -2) and not truth("−3(n − 2) = 12", 6)
    assert truth("2x + 3 > 11", 5) and not truth("2x + 3 > 11", 4)
    assert truth("−3x + 2 ≤ 14", -4) and not truth("−3x + 2 ≤ 14", -5)
    assert truth("x = 4", 4) and not truth("x = 4", 5)
    assert linear_parts("14 = 2x + 6") == (2, 6, 14)
    assert linear_parts("4x − 3 = −11") == (4, -3, -11)
    assert linear_parts("5 − 2x = 11") == (-2, 5, 11)
    assert solve_linear("−2x + 5 = 11") == -3
    assert group_parts("12 = 3(y + 9)") == (3, 9, 12, "y")
    assert group_parts("−4(k − 2) = 16") == (-4, -2, 16, "k")


# ---------------------------------------------------------------------------------------------
# Golden misconception cases (hand-worked)
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("a,b,R,expected", [
    # 2x + 6 = 14 -> 4: added 6 back, divided only 14, stopped at 2x, multiplied, subtracted 2
    (2, 6, 14, {"SAME_OP": 10, "DIVIDE_FIRST": 1, "ONE_STEP": 8, "MULTIPLIED": 16, "SUBTRACTED": 6,
                "SIGN_DROP": -4, "IGNORED_FIXED": 7}),
    # −2x + 5 = 11 -> −3
    (-2, 5, 11, {"SAME_OP": -8, "DIVIDE_FIRST": Fraction(-21, 2), "ONE_STEP": 6, "SIGN_DROP": 3,
                 "MULTIPLIED": -12}),
    # 4x − 3 = −11 -> −2
    (4, -3, -11, {"SAME_OP": Fraction(-7, 2), "DIVIDE_FIRST": Fraction(1, 4), "ONE_STEP": -8,
                  "SIGN_DROP": 2, "MULTIPLIED": -32}),
    # 3m + 1 = 13 -> 4
    (3, 1, 13, {"ONE_STEP": 12, "MULTIPLIED": 36, "SUBTRACTED": 9, "SAME_OP": Fraction(14, 3)}),
])
def test_golden_linear_candidates(a, b, R, expected):
    got = G.lin_candidates(a, b, R)
    for label, v in expected.items():
        assert got[label] == Fraction(v), (a, b, R, label)


@pytest.mark.parametrize("p,q,R,expected", [
    # 3(x + 2) = 21 -> 5
    (3, 2, 21, {"WRONG_INVERSE": 9, "ONE_STEP": 7, "DROPPED_P": 19, "PARTIAL_DIST": Fraction(19, 3),
                "SIGN_DROP": -5}),
    # 4(x − 1) = 20 -> 6
    (4, -1, 20, {"WRONG_INVERSE": 4, "ONE_STEP": 5, "DROPPED_P": 21, "PARTIAL_DIST": Fraction(21, 4)}),
    # 3(x + 3) = 24 -> 5: distributing to x only gives 3x + 3 = 24, so 7
    (3, 3, 24, {"PARTIAL_DIST": 7, "WRONG_INVERSE": 11, "ONE_STEP": 8}),
    # −2(x + 3) = 8 -> −7
    (-2, 3, 8, {"WRONG_INVERSE": -1, "ONE_STEP": -4, "DROPPED_P": 5, "PARTIAL_DIST": Fraction(-5, 2),
                "SIGN_DROP": 7}),
])
def test_golden_group_candidates(p, q, R, expected):
    got = G.grp_candidates(p, q, R)
    for label, v in expected.items():
        assert got[label] == Fraction(v), (p, q, R, label)


def test_golden_write_equations():
    r = "r"
    w = dict(G.lin_write_wrongs(2, 4, 16))        # $4 to get in, $2 a ride, spent $16: 2r + 4 = 16
    assert G.eq_str(w["IGNORED_FIXED"], r) == "2r = 16"
    assert G.eq_str(w["SWAPPED"], r) == "4r + 2 = 16"
    assert G.eq_str(w["WRONG_OP"], r) == f"2r {M} 4 = 16"
    assert G.eq_str(w["COMBINED_TERMS"], r) == "6r = 16"
    n = dict(G.lin_write_wrongs(5, -6, 14))       # 5 boxes of n, gave away 6, 14 left: 5n − 6 = 14
    assert G.eq_str(n["SWAPPED"], "n") == f"6n {M} 5 = 14"
    assert G.eq_str(n["WRONG_OP"], "n") == "5n + 6 = 14"
    assert "COMBINED_TERMS" not in n              # 5 − 6 would be a negative coefficient
    g = dict(G.grp_write_wrongs(3, 2, 21))        # each of 3 kids pays c plus $2: 3(c + 2) = 21
    assert "PARTIAL_DIST" not in g                # 3c + 2 = 21 is a defensible reading of a story
    assert G.eq_str(g["WRONG_OP"], "c") == f"3(c {M} 2) = 21"
    assert G.eq_str(g["SWAPPED"], "c") == "2(c + 3) = 21"
    assert G.eq_str(g["IGNORED_FIXED"], "c") == "3c = 21"


def test_golden_distribute():
    w = dict(G.dist_wrongs(3, 2, 21))             # 3(x + 2) = 21 -> 3x + 6 = 21
    assert G.eq_str(("lin", 3, 6, 21), "x") == "3x + 6 = 21"
    assert G.eq_str(w["PARTIAL_DIST"], "x") == "3x + 2 = 21"
    assert G.eq_str(w["DIST_LAST_ONLY"], "x") == "x + 6 = 21"
    assert G.eq_str(w["DIST_SIGN"], "x") == f"3x {M} 6 = 21"
    assert G.eq_str(w["ADDED_FOR_MULT"], "x") == "3x + 5 = 21"
    neg = dict(G.dist_wrongs(-3, -2, 12))         # −3(x − 2) = 12 -> −3x + 6 = 12
    assert G.eq_str(("lin", -3, 6, 12), "x") == f"{M}3x + 6 = 12"
    assert "ADDED_FOR_MULT" not in neg


def test_golden_inequalities():
    c = G.ineq_candidates(2, 3, 4, 11, ">")       # 2x + 3 > 11 -> x > 4
    assert c["FLIP_WRONG"] == ("<", 4) and c["BOUNDARY_ONLY"] == ("=", 4)
    assert c["STRICT_VS_INCLUSIVE"] == (GE, 4) and c["SAME_OP"] == (">", 7) and c["ONE_STEP"] == (">", 8)
    n = G.ineq_candidates(-3, 2, -4, 14, LE)      # −3x + 2 ≤ 14 -> x ≥ −4
    assert n["NO_FLIP"] == (LE, -4) and n["SIGN_DROP"] == (GE, 4)
    assert n["STRICT_VS_INCLUSIVE"] == (">", -4) and n["ONE_STEP"] == (LE, 12)
    assert n["SAME_OP"][1] == Fraction(16, -3)
    s = G.story_ineq_candidates(2, 4, 8, 20, LE)  # $4 entry, $2 a ride, at most $20 -> r ≤ 8
    assert s["WRONG_DIRECTION"] == (GE, 8) and s["STRICT_VS_INCLUSIVE"] == ("<", 8)
    assert s["BOUNDARY_ONLY"] == ("=", 8) and s["ONE_STEP"] == (LE, 16) and s["SAME_OP"] == (LE, 12)


def test_golden_rendering():
    assert G.lin_text(-2, "x", 5) == f"{M}2x + 5"
    assert G.lin_text(-2, "x", 5, True) == f"5 {M} 2x"
    assert G.lin_text(4, "x", -3) == f"4x {M} 3"
    assert G.lin_text(-3, "y", -4, True) == f"{M}4 {M} 3y"
    assert G.grp_text(-3, "k", -2) == f"{M}3(k {M} 2)"
    assert G.num(-7) == f"{M}7" and G.par(-7) == f"({M}7)"


# ---------------------------------------------------------------------------------------------
# Item classification: every baked item is read by exactly one family below
# ---------------------------------------------------------------------------------------------
N_RX = [  # noun stories: (regex, variable, noun); always px + q = R
    (r"\$(?P<q>\d+) to get in, \$(?P<p>\d+) a ride\. Spent \$(?P<R>\d+)\.", "r", "rides"),
    (r"Plan: \$(?P<q>\d+) plus \$(?P<p>\d+) a month\. Paid \$(?P<R>\d+)\.", "m", "months"),
    (r"Save \$(?P<p>\d+) a week from \$(?P<q>\d+) to reach \$(?P<R>\d+)\.", "w", "weeks"),
    (r"Taxi: \$(?P<q>\d+) plus \$(?P<p>\d+) a mile\. Fare \$(?P<R>\d+)\.", "m", "miles"),
    (r"Gym: \$(?P<q>\d+) to join, \$(?P<p>\d+) a visit\. Paid \$(?P<R>\d+)\.", "v", "visits"),
]
E_RX = [  # the letter is in the story: (regex, form)
    (r"(?P<p>\d+) bags of (?P<v>n) apples plus (?P<q>\d+) loose make (?P<R>\d+)\.", "plus"),
    (r"(?P<p>\d+) pens at \$(?P<v>c) each plus a \$(?P<q>\d+) bag cost \$(?P<R>\d+)\.", "plus"),
    (r"(?P<p>\d+) rows of (?P<v>k) seats plus (?P<q>\d+) extra make (?P<R>\d+) seats\.", "plus"),
    (r"(?P<p>\d+) boxes of (?P<v>n) pens\. Gave away (?P<q>\d+)\. (?P<R>\d+) left\.", "minus"),
    (r"(?P<p>\d+) shirts cost \$(?P<v>s) each\. \$(?P<q>\d+) coupon\. Paid \$(?P<R>\d+)\.", "minus"),
    (r"(?P<p>\d+) packs of (?P<v>k) cards, lost (?P<q>\d+)\. (?P<R>\d+) cards left\.", "minus"),
    (r"Each of (?P<p>\d+) kids pays \$(?P<v>c) plus \$(?P<q>\d+) tax\. \$(?P<R>\d+) in all\.", "group"),
    (r"Each of (?P<p>\d+) pals pays \$(?P<v>b) plus a \$(?P<q>\d+) tip\. \$(?P<R>\d+) in all\.", "group"),
    (r"Each of (?P<p>\d+) kids gets (?P<v>n) cards and (?P<q>\d+) pins: (?P<R>\d+) items\.", "group"),
    (r"Each of (?P<p>\d+) teams gets (?P<v>t) balls and (?P<q>\d+) cones: (?P<R>\d+) items\.", "group"),
]
S5_RX = [  # inequality stories: (regex, relation of  p·v + q  to  R)
    (r"Entry \$(?P<q>\d+), rides \$(?P<p>\d+) each\. Spend at most \$(?P<R>\d+)\. Rides (?P<v>r)\?", LE),
    (r"Gym \$(?P<q>\d+) to join, \$(?P<p>\d+) a visit\. Spend at most \$(?P<R>\d+)\. Visits (?P<v>v)\?", LE),
    (r"Need at least (?P<R>\d+) points\. Have (?P<q>\d+), earn (?P<p>\d+) a game\. Games (?P<v>g)\?", GE),
    (r"Run at least (?P<R>\d+) laps\. Did (?P<q>\d+), do (?P<p>\d+) more a day\. Days (?P<v>d)\?", GE),
    (r"Phone plan: \$(?P<q>\d+) plus \$(?P<p>\d+) a month\. Cost over \$(?P<R>\d+)\. Months (?P<v>m)\?", ">"),
    (r"Save more than \$(?P<R>\d+)\. Have \$(?P<q>\d+), add \$(?P<p>\d+) a week\. Weeks (?P<v>w)\?", ">"),
    (r"Under (?P<R>\d+) lb allowed\. Cart (?P<q>\d+) lb, boxes (?P<p>\d+) lb\. Boxes (?P<v>b)\?", "<"),
    (r"Spend under \$(?P<R>\d+)\. Taxi \$(?P<q>\d+) plus \$(?P<p>\d+) a mile\. Miles (?P<v>m)\?", "<"),
]
DIST = re.compile(rf"^(?P<eq>.+)\. Distribute the (?P<p>{M}?\d+)\. Result\?$")


def classify(item):
    """(family, info). Families: lin, group, ineq, dist, story_solve, story_write, ineq_story."""
    pr = item["prompt"]
    if m := re.match(r"^Solve: (.+)$", pr):
        st = m.group(1)
        if re.search(r"[<>≤≥]", st):
            return "ineq", {"st": st}
        return ("group" if "(" in st else "lin"), {"st": st}
    if m := DIST.match(pr):
        return "dist", {"eq": m.group("eq"), "p": as_int(m.group("p"))}
    for rx, var, noun in N_RX:
        if m := re.match(rf"^{rx} (?P<ask>.+)$", pr):
            d = {k: int(v) for k, v in m.groupdict().items() if k != "ask"}
            if m.group("ask") == f"{noun.capitalize()}?":
                return "story_solve", dict(d, form="plus", v=var)
            assert m.group("ask") == f"Equation for {var} {noun}?", pr
            return "story_write", dict(d, form="plus", v=var)
    for rx, form in E_RX:
        if m := re.match(rf"^{rx} (?P<ask>.+)$", pr):
            gd = m.groupdict()
            d = {k: int(gd[k]) for k in "pqR"}
            if gd["ask"] == f"Find {gd['v']}.":
                return "story_solve", dict(d, form=form, v=gd["v"])
            assert gd["ask"] == "Equation?", pr
            return "story_write", dict(d, form=form, v=gd["v"])
    for rx, op in S5_RX:
        if m := re.match(rf"^{rx}$", pr):
            gd = m.groupdict()
            return "ineq_story", dict({k: int(gd[k]) for k in "pqR"}, op=op, v=gd["v"])
    raise AssertionError(f"unrecognised prompt: {pr!r}")


CLASSIFIED = [(it, *classify(it)) for it in ITEMS]


def family(*names):
    return [(it, info) for it, fam, info in CLASSIFIED if fam in names]


def param(rows):
    return pytest.mark.parametrize("item,info", rows, ids=[it["id"] for it, _ in rows])


def test_every_item_is_classified_by_tier():
    fam_by_tier = {t: {f for it, f, _ in CLASSIFIED if it["tier"] == t} for t in range(1, 6)}
    assert fam_by_tier[1] == {"lin"} and fam_by_tier[2] == {"lin"}
    assert fam_by_tier[3] == {"group", "dist"}
    assert fam_by_tier[4] == {"story_solve", "story_write"}
    assert fam_by_tier[5] == {"ineq", "ineq_story"}


def test_tier_shapes():
    """Each tier teaches what its name says (guards generator drift)."""
    t1 = [classify(it)[1]["st"] for it in by_tier(1)]
    assert all(not re.search(rf"[{M}]\d|\({M}", s.replace(f" {M} ", " ")) for s in t1)  # no negative numbers
    assert sum(" = " in s and s.split(" = ")[0].isdigit() for s in t1) >= 8        # R = px + q
    assert sum(bool(re.match(r"^\d+ [+] \d+[a-z] = ", s)) for s in t1) >= 8        # q + px = R
    assert sum(bool(re.search(rf" {M} \d+ = ", s)) for s in t1) >= 8                # px − q = R
    t2 = [classify(it)[1]["st"] for it in by_tier(2)]
    assert sum(s.startswith(M) and re.match(rf"^{M}\d*[a-z]", s) is not None for s in t2) >= 8   # −px + q
    assert sum(bool(re.match(rf"^{M}?\d+ [+{M}] \d+[a-z] = ", s)) for s in t2) >= 8             # q ± px
    assert sum(" = " in s and s.split(" = ")[0].lstrip(M).isdigit() for s in t2) >= 8           # R = ...
    t3 = family("group", "dist")
    assert sum(1 for it, _ in t3 if it["tier"] == 3 and "Distribute" in it["prompt"]) >= 8
    assert sum(1 for it, i in family("group") if it["tier"] == 3 and i["st"].startswith(M)) >= 5
    t4 = by_tier(4)
    assert sum(it["prompt"].endswith("Equation?") or "Equation for" in it["prompt"] for it in t4) >= 15
    assert sum("Equation" not in it["prompt"] for it in t4) >= 15
    assert sum(1 for it in t4 if re.search(r"\(", it["choices"][it["answer"]])) >= 4        # p(x + q)
    assert sum(1 for _, i in family("story_write", "story_solve") if i["form"] == "minus") >= 5
    t5 = [classify(it) for it in by_tier(5)]
    assert sum(f == "ineq_story" for f, _ in t5) >= 8
    assert sum(f == "ineq" and re.match(rf"^(?:{M}\d*[a-z]|\d+ {M} \d*[a-z])", i["st"]) is not None
               for f, i in t5) >= 15                                                         # negative p: the flip


# ---------------------------------------------------------------------------------------------
# Exactly one right door, checked independently
# ---------------------------------------------------------------------------------------------
def numbers(item):
    vals = [as_int(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    return vals


@param(family("lin"))
def test_lin_exactly_one_true_choice(item, info):
    st = info["st"]
    vals = numbers(item)
    assert [i for i, v in enumerate(vals) if truth(st, v)] == [item["answer"]], (st, item["choices"])
    assert vals[item["answer"]] == solve_linear(st)


@param(family("group"))
def test_group_exactly_one_true_choice(item, info):
    st = info["st"]
    vals = numbers(item)
    assert [i for i, v in enumerate(vals) if truth(st, v)] == [item["answer"]], (st, item["choices"])
    p, q, R, _ = group_parts(st)
    assert vals[item["answer"]] == Fraction(R, p) - q


@param(family("dist"))
def test_dist_exactly_one_correct_expansion(item, info):
    p, q, R, v = group_parts(info["eq"])
    assert p == info["p"]
    right = []
    for i, c in enumerate(item["choices"]):
        a, b, R2 = linear_parts(c)
        if (a, b, R2) == (p, p * q, R):                      # the expansion, term by term
            right.append(i)
        else:  # not equivalent either: a different solution set (no second right door)
            assert Fraction(R2 - b, a) != Fraction(R, p) - q, (info["eq"], c)
    assert right == [item["answer"]], (info["eq"], item["choices"])


def story_equation(i):
    """The equation the story means, as display text with the story's letter."""
    v, p, q, R = i["v"], i["p"], i["q"], i["R"]
    if i["form"] == "plus":
        return f"{p}{v} + {q} = {R}"
    if i["form"] == "minus":
        return f"{p}{v} {M} {q} = {R}"
    return f"{p}({v} + {q}) = {R}"


def story_solution(i):
    p, q, R = i["p"], i["q"], i["R"]
    return {"plus": Fraction(R - q, p), "minus": Fraction(R + q, p), "group": Fraction(R, p) - q}[i["form"]]


@param(family("story_solve"))
def test_story_solve_exactly_one_true_choice(item, info):
    eq = story_equation(info)
    vals = numbers(item)
    assert [i for i, v in enumerate(vals) if truth(eq, v)] == [item["answer"]], (item["prompt"], eq)
    assert vals[item["answer"]] == story_solution(info)


def parse_equation(c):
    """('grp', p, q, R) or ('lin', a, b, R) from a displayed equation."""
    if "(" in c:
        p, q, R, _ = group_parts(c)
        return "grp", p, q, R
    a, b, R = linear_parts(c)
    return "lin", a, b, R


def eq_solution(e):
    kind, u, w, R = e
    return Fraction(R - w, u) if kind == "lin" else Fraction(R, u) - w


@param(family("story_write"))
def test_story_write_exactly_one_right_equation(item, info):
    model = story_equation(info)
    sol = story_solution(info)
    assert item["choices"][item["answer"]] == model, item["prompt"]
    sols = [eq_solution(parse_equation(c)) for c in item["choices"]]
    assert sols[item["answer"]] == sol and sol.denominator == 1
    assert sorted(sols).count(sol) == 1 and len(set(sols)) == len(sols), (item["prompt"], item["choices"])
    # every other choice really is a different statement: the story's solution fails it
    for i, c in enumerate(item["choices"]):
        assert truth(c, sol) == (i == item["answer"]), (item["prompt"], c)


POINTS = [Fraction(k, 2) for k in range(-60, 61)]


def table(statement):
    return tuple(truth(statement, x) for x in POINTS)


def sig_of(choice):
    m = re.fullmatch(rf"([a-z]) ([<>=≤≥]) ({M}?\d+)", choice)
    assert m, choice
    return m.group(1), m.group(2), as_int(m.group(3))


@param(family("ineq"))
def test_inequality_exactly_one_right_choice(item, info):
    st = info["st"]
    want = table(st)
    right = [i for i, c in enumerate(item["choices"]) if table(c) == want]
    assert right == [item["answer"]], (st, item["choices"])
    sigs = [sig_of(c)[1:] for c in item["choices"]]
    assert len(set(sigs)) == len(sigs)


@param(family("ineq_story"))
def test_inequality_story_exactly_one_right_choice(item, info):
    v = info["v"]
    want = table(f"{info['p']}{v} + {info['q']} {info['op']} {info['R']}")
    right = [i for i, c in enumerate(item["choices"]) if table(c) == want]
    assert right == [item["answer"]], (item["prompt"], item["choices"])
    vv, op, c = sig_of(item["choices"][item["answer"]])
    assert vv == v and op == info["op"] and Fraction(c) == Fraction(info["R"] - info["q"], info["p"])


def test_choices_are_never_equal_in_value():
    for it, fam, info in CLASSIFIED:
        ch = it["choices"]
        assert len(set(ch)) == len(ch), it["id"]
        if fam in ("lin", "group", "story_solve"):
            assert len({as_int(c) for c in ch}) == len(ch), it["id"]
        elif fam in ("dist", "story_write"):
            sols = {eq_solution(parse_equation(c)) for c in ch}
            assert len(sols) == len(ch), (it["id"], ch)
        else:
            assert len({sig_of(c)[1:] for c in ch}) == len(ch), it["id"]


# ---------------------------------------------------------------------------------------------
# Labels name the rule that produced the value (modelled here independently)
# ---------------------------------------------------------------------------------------------
def lin_model(a, b, R):
    x = Fraction(R - b, a)
    return {"SAME_OP": Fraction(R + b, a), "DIVIDE_FIRST": Fraction(R, a) - b, "ONE_STEP": Fraction(R - b),
            "MULTIPLIED": Fraction((R - b) * a), "SUBTRACTED": Fraction(R - b - a), "SIGN_DROP": -x,
            "IGNORED_FIXED": Fraction(R, a), "ADDED_FIXED": Fraction(R + b, a)}


def group_model(p, q, R):
    s = Fraction(R, p)
    return {"WRONG_INVERSE": s + q, "ONE_STEP": s, "DROPPED_P": Fraction(R - q), "PARTIAL_DIST": Fraction(R - q, p),
            "SIGN_DROP": -(s - q)}


def check_numeric_labels(item, model, allowed):
    for c, lab in zip(item["choices"], item["misconceptions"]):
        if lab is None:
            continue
        assert lab in allowed, (item["id"], lab)
        assert Fraction(as_int(c)) == model[lab], (item["id"], c, lab)


@param(family("lin"))
def test_lin_labels_match_their_rule(item, info):
    a, b, R = linear_parts(info["st"])
    allowed = ({"SAME_OP", "DIVIDE_FIRST", "ONE_STEP", "MULTIPLIED", "SUBTRACTED"} if item["tier"] == 1
               else {"SIGN_DROP", "SAME_OP", "DIVIDE_FIRST", "ONE_STEP", "MULTIPLIED"})
    check_numeric_labels(item, lin_model(a, b, R), allowed)


@param(family("group"))
def test_group_labels_match_their_rule(item, info):
    p, q, R, _ = group_parts(info["st"])
    check_numeric_labels(item, group_model(p, q, R), {"WRONG_INVERSE", "ONE_STEP", "DROPPED_P", "PARTIAL_DIST",
                                                       "SIGN_DROP"})


@param(family("story_solve"))
def test_story_solve_labels_match_their_rule(item, info):
    p, q, R = info["p"], info["q"], info["R"]
    if info["form"] == "group":
        check_numeric_labels(item, group_model(p, q, R), {"WRONG_INVERSE", "ONE_STEP", "DROPPED_P"})
    else:
        b = q if info["form"] == "plus" else -q
        check_numeric_labels(item, lin_model(p, b, R),
                             {"ADDED_FIXED", "IGNORED_FIXED", "ONE_STEP", "MULTIPLIED", "SUBTRACTED"})


@param(family("dist"))
def test_dist_labels_match_their_rule(item, info):
    p, q, R, _ = group_parts(info["eq"])
    shape = {"PARTIAL_DIST": (p, q), "DIST_LAST_ONLY": (1, p * q), "DIST_SIGN": (p, -p * q),
             "ADDED_FOR_MULT": (p, p + q)}
    for c, lab in zip(item["choices"], item["misconceptions"]):
        if lab is not None:
            assert linear_parts(c) == (*shape[lab], R), (item["id"], c, lab)


@param(family("story_write"))
def test_story_write_labels_match_their_rule(item, info):
    p, q, R = info["p"], info["q"], info["R"]
    if info["form"] == "group":
        shape = {"WRONG_OP": ("grp", p, -q), "SWAPPED": ("grp", q, p), "IGNORED_FIXED": ("lin", p, 0)}
    else:
        b = q if info["form"] == "plus" else -q
        shape = {"IGNORED_FIXED": ("lin", p, 0), "SWAPPED": ("lin", q, p if b > 0 else -p),
                 "WRONG_OP": ("lin", p, -b), "COMBINED_TERMS": ("lin", p + b, 0)}
    for c, lab in zip(item["choices"], item["misconceptions"]):
        if lab is not None:
            assert parse_equation(c) == (*shape[lab], R), (item["prompt"], c, lab)


def split_ineq(st):
    lhs, op, rhs = re.split(r" ([<>≤≥]) ", st)
    a, b, R = linear_parts(f"{lhs} = {rhs}")
    return a, b, op, R


@param(family("ineq"))
def test_inequality_labels_match_their_rule(item, info):
    a, b, op0, R = split_ineq(info["st"])
    c = Fraction(R - b, a)
    assert c.denominator == 1
    op1 = op0 if a > 0 else FLIP[op0]
    model = {"NO_FLIP": (op0, c), "FLIP_WRONG": (FLIP[op0], c), "BOUNDARY_ONLY": ("=", c),
             "STRICT_VS_INCLUSIVE": (TOGGLE[op1], c), "SAME_OP": (op1, Fraction(R + b, a)),
             "ONE_STEP": (op0, Fraction(R - b)), "SIGN_DROP": (op1, -c)}
    assert sig_of(item["choices"][item["answer"]])[1:] == (op1, int(c))
    labels = [lab for lab in item["misconceptions"] if lab]
    assert ("NO_FLIP" in labels) == (a < 0) and ("FLIP_WRONG" in labels) == (a > 0)
    for ch, lab in zip(item["choices"], item["misconceptions"]):
        if lab is not None:
            op, val = sig_of(ch)[1:]
            assert (op, Fraction(val)) == model[lab], (info["st"], ch, lab)


@param(family("ineq_story"))
def test_inequality_story_labels_match_their_rule(item, info):
    p, q, R, op = info["p"], info["q"], info["R"], info["op"]
    c = Fraction(R - q, p)
    model = {"WRONG_DIRECTION": (FLIP[op], c), "STRICT_VS_INCLUSIVE": (TOGGLE[op], c), "BOUNDARY_ONLY": ("=", c),
             "ONE_STEP": (op, Fraction(R - q)), "SAME_OP": (op, Fraction(R + q, p))}
    for ch, lab in zip(item["choices"], item["misconceptions"]):
        if lab is not None:
            o, val = sig_of(ch)[1:]
            assert (o, Fraction(val)) == model[lab], (item["prompt"], ch, lab)


GROUP_STORIES = [(it, i) for it, i in family("story_solve", "story_write") if i["form"] == "group"]


@param(GROUP_STORIES)
def test_group_stories_have_one_reading(item, info):
    """A group story p(x + q) = r must not read two ways. 'Each of p ...' leads, so the extra q belongs
    to every group; the other reading, px + q = r (q added once, answer (r - q) / p), is never a choice."""
    p, q, R = info["p"], info["q"], info["R"]
    assert item["prompt"].startswith(f"Each of {p} "), item["prompt"]
    other = Fraction(R - q, p)
    if "Equation" in item["prompt"]:
        for c in item["choices"]:
            assert parse_equation(c) != ("lin", p, q, R), (item["prompt"], c)
            assert eq_solution(parse_equation(c)) != other, (item["prompt"], c)
    else:
        assert other not in {Fraction(as_int(c)) for c in item["choices"]}, (item["prompt"], item["choices"])
    assert "PARTIAL_DIST" not in item["misconceptions"]


@param([(it, i) for it, i in GROUP_STORIES if "$" in it["prompt"].split(".")[0]])
def test_dollar_group_stories_keep_the_extra_below_the_price(item, info):
    price = info["R"] // info["p"] - info["q"]
    assert info["q"] < price, item["prompt"]


def test_group_story_checks_have_something_to_check():
    assert len(GROUP_STORIES) >= 8
    assert sum("Equation" in it["prompt"] for it, _ in GROUP_STORIES) >= 4
    assert sum("$" in it["prompt"].split(".")[0] for it, _ in GROUP_STORIES) >= 4


def test_group_story_reading_check_can_fail():
    """Disproof: the second reading really is a different equation with a different answer, and the
    parser tells it apart from the right one."""
    p, q, R = 5, 2, 30                              # 5t + 2 = 30 is the second reading of 5(t + 2) = 30
    assert eq_solution(("lin", p, q, R)) == Fraction(R - q, p) != Fraction(R, p) - q
    assert parse_equation("5t + 2 = 30") == ("lin", p, q, R)
    assert parse_equation("5(t + 2) = 30") == ("grp", p, q, R)


def test_explanations_state_the_answer():
    for it in ITEMS:
        right = it["choices"][it["answer"]]
        expl = it["explanation"]
        if re.fullmatch(rf"{M}?\d+", right):
            assert f"= {right}" in expl, it["id"]
        else:
            assert right in expl, it["id"]


# ---------------------------------------------------------------------------------------------
# Whole-cartridge properties
# ---------------------------------------------------------------------------------------------
def test_arith_is_filler_only():
    labels = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert labels["ARITH"] <= 0.05 * sum(labels.values())


def test_every_declared_misconception_used():
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert set(BAKED["misconceptions"]) <= used


def test_four_choices_everywhere():
    assert all(len(it["choices"]) == 4 for it in ITEMS)


def test_baked_matches_a_fresh_deterministic_generate():
    manifest = {k: v for k, v in BAKED.items() if k not in ("items", "baked_with")}
    a = G.generate(manifest, random.Random(manifest["seed"]))
    b = G.generate(manifest, random.Random(manifest["seed"]))
    assert a == b
    strip = [{k: v for k, v in it.items() if k != "id"} for it in ITEMS]
    assert strip == a


def test_no_question_repeats_with_only_the_letter_changed():
    for t in range(1, 6):
        keys = [re.sub(r"(?<![A-Za-z])[a-z](?![A-Za-z])", "_", it["prompt"]) for it in by_tier(t)]
        assert len(set(keys)) == len(keys), t


def test_display_strings_use_the_true_minus_and_no_other_variables():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in s, (it["id"], s)               # U+2212 only
            assert "^" not in s
    for it, fam, info in CLASSIFIED:
        if fam in ("lin", "group", "ineq"):
            variable_of(info["st"])                           # exactly one letter
            assert len(re.findall(r"[a-z]", info["st"])) == 1, "variable on both sides"


# ---------------------------------------------------------------------------------------------
# Content bounds (manifest "bounds"), walked from the prompt text
# ---------------------------------------------------------------------------------------------
def bounds_violations(tier, prompt):
    bad = []
    fam, info = classify({"prompt": prompt, "tier": tier})
    if fam in ("lin", "group", "ineq") and len(re.findall(r"[a-z]", info["st"])) != 1:
        return ["variable on both sides (grade 8)"]

    def span(name, v, lo, hi):
        if not lo <= abs(v) <= hi:
            bad.append(f"{name} {v} not in {lo}-{hi}")

    def whole(name, f):
        if Fraction(f).denominator != 1:
            bad.append(f"{name} {f} is not a whole number")
            return False
        return True

    if fam == "lin":
        a, b, R = linear_parts(info["st"])
        x = Fraction(R - b, a)
        if tier == 1:
            if a < 0 or R < 1 or x < 0:
                bad.append("negative number in tier 1")
            span("coefficient", a, 2, 9)
            span("constant", b, 1, 12)
            if not 1 <= R <= 20:
                bad.append(f"r {R} not in 1-20")
            if whole("solution", x):
                span("solution", int(x), 2, 10)
                if a * x > 32:
                    bad.append(f"px {a * x} over 32")
        else:
            span("coefficient", a, 2, 10)
            span("constant", b, 1, 12)
            span("r", R, 1, 12)
            if whole("solution", x):
                span("solution", int(x), 2, 10)
                if abs(a * x) > 24:
                    bad.append(f"px {a * x} over 24 in size")
                if not (a < 0 or x < 0 or R < 0):
                    bad.append("tier 2 item with no negative")
    elif fam in ("group", "dist"):
        p, q, R, _ = group_parts(info["st"] if fam == "group" else info["eq"])
        span("p", p, 2, 10)
        span("q", q, 1 if fam == "group" else 2, 10)
        if R % p == 0:
            s = R // p
            span("group value", s, 2, 10)
            span("solution", s - q, 2, 10)
            if abs(R) > 100:
                bad.append(f"r {R} over 100")
        else:
            bad.append(f"{R} is not a multiple of {p}")
    elif fam in ("story_solve", "story_write"):
        p, q, R = info["p"], info["q"], info["R"]
        span("p", p, 2, 9 if info["form"] != "group" else 10)
        if info["form"] == "group":
            span("q", q, 1, 10)
            if R % p == 0:
                span("group value", R // p, 2, 10)
                span("solution", R // p - q, 2, 10)
                if R > 100:
                    bad.append(f"r {R} over 100")
            else:
                bad.append(f"{R} is not a multiple of {p}")
        else:
            span("q", q, 2, 12)
            if not 2 <= R <= 20:
                bad.append(f"r {R} not in 2-20")
            if q == p:
                bad.append("q equals p")
            x = story_solution(info)
            if whole("solution", x):
                span("solution", int(x), 2, 10)
                if p * x > 32:
                    bad.append(f"px {p * x} over 32")
    elif fam == "ineq":
        a, b, op0, R = split_ineq(info["st"])
        span("coefficient", a, 2, 10)
        span("constant", b, 1, 12)
        span("r", R, 0, 12)
        c = Fraction(R - b, a)
        if whole("boundary", c):
            span("boundary", int(c), 2, 10)
            if abs(a * c) > 24:
                bad.append(f"px {a * c} over 24 in size")
    else:  # ineq_story
        p, q, R = info["p"], info["q"], info["R"]
        span("p", p, 2, 9)
        span("q", q, 2, 12)
        if not 1 <= R <= 20:
            bad.append(f"r {R} not in 1-20")
        c = Fraction(R - q, p)
        if whole("boundary", c):
            span("boundary", int(c), 3, 10)
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_content_bounds(item):
    assert bounds_violations(item["tier"], item["prompt"]) == [], item["prompt"]


def test_manifest_states_bounds():
    b = BAKED["bounds"]
    assert "times-table" in b and "never on both sides" in b and "whole number" in b


@pytest.mark.parametrize("tier,prompt,expect_bad", [
    (1, "Solve: 2x + 6 = 14", False),
    (1, "Solve: 14 = 2x + 6", False),
    (1, "Solve: 4x − 3 = 9", False),
    (1, "Solve: 2x + 25 = 31", True),            # constant 25
    (1, "Solve: 12x + 6 = 30", True),            # coefficient 12
    (1, "Solve: 2x + 6 = 15", True),             # solution 4.5
    (1, "Solve: −2x + 5 = 11", True),            # a negative in tier 1
    (1, "Solve: 7x + 5 = 40", True),             # r over 20
    (1, "Solve: 3x + 4 = 5x", True),             # variable on both sides
    (2, "Solve: −2x + 5 = 11", False),
    (2, "Solve: 4x − 3 = −11", False),
    (2, "Solve: 2x + 6 = 14", True),             # no negative anywhere
    (2, "Solve: 2x + 14 = −4", True),            # constant 14
    (2, "Solve: −5x + 2 = 12", False),
    (2, "Solve: −9x + 2 = 11", True),            # solution −1
    (3, "Solve: 3(x + 2) = 21", False),
    (3, "Solve: 4(x − 1) = 20", False),
    (3, "Solve: 3(x + 2) = 22", True),           # 22 is not a multiple of 3
    (3, "Solve: 12(x + 2) = 60", True),          # p = 12
    (3, "Solve: 3(x + 15) = 60", True),          # q = 15
    (3, "Solve: 10(x + 1) = 110", True),         # group value 11
    (3, "3(x + 1) = 12. Distribute the 3. Result?", True),   # distributing by q = 1 is not a times-table fact
    (3, "3(x + 2) = 21. Distribute the 3. Result?", False),
    (4, "$4 to get in, $2 a ride. Spent $16. Rides?", False),
    (4, "$4 to get in, $4 a ride. Spent $16. Rides?", True),    # q equals p
    (4, "$4 to get in, $2 a ride. Spent $30. Rides?", True),    # r over 20
    (4, "Each of 3 kids pays $c plus $2 tax. $21 in all. Find c.", False),
    (4, "Each of 3 kids pays $c plus $2 tax. $20 in all. Find c.", True),
    (4, "3 bags of n apples plus 15 loose make 99. Equation?", True),
    (5, "Solve: 2x + 3 > 11", False),
    (5, "Solve: −3x + 2 ≤ 11", False),
    (5, "Solve: −3x + 2 ≤ 14", True),             # r 14 is over 12 (the LIBRARY.md example breaks its own bound)
    (5, "Solve: 2x + 1 > 13", True),             # r over 12
    (5, "Solve: 2x + 3 > 12", True),             # boundary 4.5
    (5, "Entry $4, rides $2 each. Spend at most $20. Rides r?", False),
    (5, "Entry $3, rides $2 each. Spend at most $50. Rides r?", True),
])
def test_bounds_checker_catches(tier, prompt, expect_bad):
    assert bool(bounds_violations(tier, prompt)) == expect_bad, prompt


def test_the_checker_can_fail_on_a_planted_bad_baked_item():
    bad = dict(ITEMS[0], prompt="Solve: 2x + 25 = 31")
    assert bounds_violations(bad["tier"], bad["prompt"]) != []
