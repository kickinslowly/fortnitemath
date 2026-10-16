"""linear-equations cartridge (grade 8): golden misconception cases, an independent re-check of every baked
item, label checks, value-uniqueness of choices, and the cartridge's content bounds asserted on baked.json.

The independent check never calls the generator's solver or candidate functions on a baked item. It rewrites
every prompt to a Python expression and evaluates it with ``fractions.Fraction`` (a line is read off by
evaluating it at 0, 1, 2), counts solutions of a system with 2x2 determinants, and models every label with
this file's own formulas.
"""
import json
import re
from collections import Counter
from fractions import Fraction as F

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "linear-equations"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M, DIV = "−", "÷"
WORDS = ("One", "None", "Infinite", "Two")


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def as_num(s):
    return F(s.replace(M, "-"))


# ---------------------------------------------------------------------------------------------
# Independent evaluator
# ---------------------------------------------------------------------------------------------
def to_py(text):
    s = text.replace(M, "-").replace(DIV, "/")
    s = re.sub(r"(?<=[\d\)a-z])(?=[a-z\(])", "*", s)  # 2x -> 2*x, 3(x -> 3*(x, )x -> )*x
    s = re.sub(r"\d+(?:\.\d+)?", lambda m: f"F('{m.group()}')", s)
    cleaned = re.sub(r"F\('[\d.]+'\)", "N", s)
    assert re.fullmatch(r"[N a-z+\-*/()]*", cleaned), text
    return s


def ev(text, env):
    return eval(to_py(text), {"__builtins__": {}, "F": F}, dict(env))


def variable_of(text):
    letters = set(re.findall(r"(?<![A-Za-z])[a-z](?![A-Za-z])", text))
    assert len(letters) == 1, text
    return letters.pop()


def sides(eq):
    lhs, rhs = eq.split(" = ")
    return lhs, rhs


def lin(expr, var):
    """(slope, intercept) of a linear expression, verified linear at 0, 1, 2."""
    f0, f1, f2 = (ev(expr, {var: F(v)}) for v in (0, 1, 2))
    assert f2 - f1 == f1 - f0, expr
    return f1 - f0, f0


def solve1(eq):
    """(var, slope, intercept) of lhs - rhs = slope*v + intercept."""
    v = variable_of(eq)
    lhs, rhs = sides(eq)
    (a, b), (c, d) = lin(lhs, v), lin(rhs, v)
    return v, a - c, b - d


def count_of(eq):
    _, s, i = solve1(eq)
    if s != 0:
        return "One"
    return "Infinite" if i == 0 else "None"


def coefs2(eq):
    """(a, b, c) with a*x + b*y = c for a two-variable equation."""
    lhs, rhs = sides(eq)
    g = lambda x, y: ev(lhs, {"x": F(x), "y": F(y)}) - ev(rhs, {"x": F(x), "y": F(y)})
    g00 = g(0, 0)
    a, b = g(1, 0) - g00, g(0, 1) - g00
    assert g(1, 1) - g00 == a + b, eq
    return a, b, -g00


def solve2(e1, e2):
    a1, b1, c1 = coefs2(e1)
    a2, b2, c2 = coefs2(e2)
    det = a1 * b2 - a2 * b1
    if det != 0:
        return "One", ((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det)
    consistent = (a1 * c2 == a2 * c1) and (b1 * c2 == b2 * c1)
    return ("Infinite" if consistent else "None"), None


def parse_point(s):
    m = re.fullmatch(r"\(([−\d]+), ([−\d]+)\)", s)
    assert m, s
    return as_num(m.group(1)), as_num(m.group(2))


COUNT_RE = re.compile(r"^(.*)\. How many solutions\?$")
Q_RE = re.compile(r"^(.*)\. (Infinite solutions|Infinite|No solution) when k is\?$")
SYS_COUNT_RE = re.compile(r"^(y .*) and (y .*)\. How many solutions\?$")
SD_RE = re.compile(r"^(.*) and (.*)\. Find (x|y|\(x, y\))\.$")
MEET_RE = re.compile(r"^(y = .*) and (y = .*)\. Where do they meet\?$")


def kind_of(it):
    p, t = it["prompt"], it["tier"]
    if p.startswith("Solve: "):
        return "solve"
    if t == 3 and Q_RE.match(p):
        return "q"
    if t == 3 and COUNT_RE.match(p):
        return "count"
    if t == 5 and SYS_COUNT_RE.match(p):
        return "syscount"
    if t == 5 and MEET_RE.match(p):
        return "meet"
    if t == 5 and SD_RE.match(p):
        return "sd"
    raise AssertionError(p)


def text_of(it, i):
    return it["choices"][i]


def correct(it):
    return it["choices"][it["answer"]]


# ---------------------------------------------------------------------------------------------
# Bounds (the manifest's "bounds"): returns a list of violations, empty when the item is fine
# ---------------------------------------------------------------------------------------------
ALLOWED_FR = {F(1, 2), F(1, 3), F(1, 4), F(1, 5)}
ALLOWED_DEC = {F(1, 2), F(1, 4), F(1, 5), F(1, 10)}
BOTH_PAIRS = {(F(1), F(1, 2)), (F(1, 2), F(1)), (F(1, 2), F(1, 4)), (F(1, 4), F(1, 2))}
FR_PAT = [r"\(1/[2-5]\)[a-z]", r"(?<=[a-z])/[2-5]\b", r"0\.(?:5|25|2|1)(?=[a-z])"]


def plain_numbers(eq):
    """(coefficients, constants) of the integer literals; fraction/decimal coefficients are stripped first."""
    s = eq
    for pat in FR_PAT:
        s = re.sub(pat, "", s)
    coefs, consts = [], []
    for m in re.finditer(r"\d+(?:\.\d+)?", s):
        n = F(m.group())
        nxt = s[m.end():m.end() + 1]
        (coefs if nxt.isalpha() or nxt == "(" else consts).append(n)
    return coefs, consts


def has_negative_literal(eq):
    """A minus anywhere in a one-variable equation is a negative literal: "5x − 15" holds the constant −15."""
    return M in eq


def bounds_problems(it):
    p, t = it["prompt"], it["tier"]
    bad = []
    kind = kind_of(it)
    if kind == "solve":
        eq = p[len("Solve: "):]
        v, s, i = solve1(eq)
        coefs, consts = plain_numbers(eq)
        lim = 12 if has_negative_literal(eq) else 20
        if any(c > 10 for c in coefs):
            bad.append("coefficient over 10")
        if any(c > lim for c in consts):
            bad.append(f"constant over {lim}")
        for gm in re.finditer(r"(\d+)\((\w) ([+−]) (\d+)\)", eq):
            pp, tt = int(gm.group(1)), int(gm.group(4))
            if not 2 <= pp <= 6:
                bad.append("group multiplier outside 2-6")
            if pp * tt > lim or tt > lim:
                bad.append(f"distributed product over {lim}")
        x = -i / s
        k = -i  # the number side after collecting: s*x = k
        if x.denominator != 1 or x == 0:
            bad.append("solution not a nonzero integer")
        if t in (1, 2):
            if not (2 <= abs(s) <= 10 and abs(x) <= 10):
                bad.append("collected coefficient or solution out of range")
        if t == 4:
            if abs(x) > 40 or k.denominator != 1 or abs(k) > 10:
                bad.append("T4 solution or collected number out of range")
            lhs, rhs = sides(eq)
            (a, _), (c, _) = lin(lhs, v), lin(rhs, v)
            if c == 0:
                if not (a in ALLOWED_FR or a in ALLOWED_DEC):
                    bad.append("one-sided coefficient not allowed")
            elif (a, c) not in BOTH_PAIRS:
                bad.append("both-sided pair not allowed")
        if abs(k) > 100:
            bad.append("number side over 100")
    elif kind == "count":
        eq = COUNT_RE.match(p).group(1)
        v, s, i = solve1(eq)
        coefs, consts = plain_numbers(eq)
        lim = 12 if has_negative_literal(eq) else 20
        if any(c > 10 for c in coefs) or any(c > lim for c in consts):
            bad.append("literal out of range")
        for gm in re.finditer(r"(\d+)\((\w) ([+−]) (\d+)\)", eq):
            if int(gm.group(1)) * int(gm.group(4)) > lim:
                bad.append("distributed product too big")
        if s != 0:
            x = -i / s
            if x.denominator != 1 or x == 0 or abs(x) > 10 or abs(s) > 10:
                bad.append("one-solution item without a nonzero integer solution")
    elif kind == "q":
        eq = Q_RE.match(p).group(1)
        coefs, consts = plain_numbers(eq.replace("k", ""))
        if any(c > 10 for c in coefs) or any(c > 20 for c in consts):
            bad.append("literal out of range")
    elif kind == "syscount":
        for line in SYS_COUNT_RE.match(p).groups():
            a, b, c = coefs2(line)
            if b != 1 or not 1 <= abs(a) <= 6 or abs(c) > 12:
                bad.append("line out of range")
    elif kind == "meet":
        for line in MEET_RE.match(p).groups():
            a, b, c = coefs2(line)
            if b != 1 or not 1 <= abs(a) <= 5 or abs(c) > 12:
                bad.append("line out of range")
        _, (x, y) = solve2(*MEET_RE.match(p).groups())
        if x.denominator != 1 or y.denominator != 1 or abs(x) > 10 or abs(y) > 10:
            bad.append("meeting point not an integer point within 10")
    else:  # sd
        e1, e2, _ = SD_RE.match(p).groups()
        status, (x, y) = solve2(e1, e2)
        if status != "One" or x.denominator != 1 or y.denominator != 1 or not (1 <= x <= 8 and 1 <= y <= 8) or x == y:
            bad.append("system solution out of range")
        lim = 12 if any(coefs2(e)[2] < 0 for e in (e1, e2)) else 20  # "x − y" is an operator, "= −3" a literal
        for e in (e1, e2):
            a, b, c = coefs2(e)
            if abs(c) > lim or not (1 <= abs(a) <= 2 and 1 <= abs(b) <= 2):
                bad.append("system coefficient or constant out of range")
        (a1, b1, _), (a2, b2, _) = coefs2(e1), coefs2(e2)
        if not ((b1 + b2 == 0 and a1 > 0 and a2 > 0) or (a1 + a2 == 0 and b1 > 0 and b2 > 0)):
            bad.append("equations do not add to eliminate a variable")
    return bad


# ---------------------------------------------------------------------------------------------
# Golden misconception cases (hand-worked)
# ---------------------------------------------------------------------------------------------
def test_golden_t1():
    c = G.t1_cands(5, 2, 3, 10)           # 5x + 2 = 3x + 10, x = 4
    assert (c["SAME_SIGN_MOVE"], c["CONST_SIGN"], c["ONE_STEP"], c["SIGN_SLIP"]) == (1, 6, 8, -4)
    c = G.t1_cands(7, -3, 4, 9)           # 7x - 3 = 4x + 9, x = 4
    assert (c["CONST_SIGN"], c["ONE_STEP"], c["SIGN_SLIP"]) == (2, 12, -4)
    assert c["SAME_SIGN_MOVE"] == F(12, 11)
    c = G.t1_cands(2, 9, 5, 0)            # 2x + 9 = 5x, x = 3
    assert (c["CONST_SIGN"], c["ONE_STEP"], c["SIGN_SLIP"]) == (-3, -9, -3)


def test_golden_t2():
    c = G.t2_cands(3, 0, 1, 2, 14)        # 3(x + 2) = x + 14, x = 4
    assert c["PARTIAL_DIST"] == 6 and c["CONST_SIGN"] == 10 and c["SAME_SIGN_MOVE"] == 2
    c = G.t2_cands(2, 1, 0, -1, 13)       # 2(x - 1) + x = 13, x = 5
    assert c["DROP_LIKE_TERM"] == F(15, 2) and c["SIGN_INSIDE"] == F(11, 3) and c["PARTIAL_DIST"] == F(14, 3)
    c = G.t2_cands(4, 0, 2, -3, 4)        # 4(x - 3) = 2x + 4, x = 8
    assert c["SIGN_INSIDE"] == -4 and c["PARTIAL_DIST"] == F(7, 2) and c["SAME_SIGN_MOVE"] == F(16, 6)


def test_golden_t4():
    c = G.t4_cands(F(1, 2), 3, F(0), 7, False)       # (1/2)x + 3 = 7, x = 8
    assert (c["DIVIDE_FOR_MULT"], c["FORGOT_LAST_STEP"], c["ONE_TERM_CLEARED"], c["CONST_SIGN"]) == (2, 4, 1, 20)
    c = G.t4_cands(F(1, 3), -1, F(0), 3, False)      # x/3 - 1 = 3, x = 12
    assert (c["DIVIDE_FOR_MULT"], c["FORGOT_LAST_STEP"], c["ONE_TERM_CLEARED"], c["CONST_SIGN"]) == (F(4, 3), 4, 6, 6)
    c = G.t4_cands(F(1, 2), 2, F(1), -1, True)       # 0.5x + 2 = x - 1, x = 6
    assert (c["DEC_WRONG_WAY"], c["SAME_SIGN_MOVE"], c["CONST_SIGN"], c["SIGN_SLIP"], c["FORGOT_LAST_STEP"]) == \
        (F(3, 2), -2, -2, -6, -3)
    c = G.t4_cands(F(1, 5), 3, F(0), 6, True)        # 0.2x + 3 = 6, x = 15
    assert (c["DEC_AS_FRAC"], c["DEC_WRONG_WAY"], c["FORGOT_LAST_STEP"]) == (6, F(3, 5), 3)


def test_golden_choice_text():
    assert G.line_plain(2, 1) == "y = 2x + 1" and G.line_plain(-1, -4) == "y = −x − 4"
    assert G.line_alt(2, 3) == "y − 2x = 3" and G.line_alt(-3, 5) == "y + 3x = 5"
    assert G.both_text(5, 2, 3, 10, "x") == "5x + 2 = 3x + 10"
    assert G.group_eq_text(3, 0, 1, 2, 14, "x", False) == "3(x + 2) = x + 14"
    assert G.group_eq_text(2, 1, 0, -1, 13, "x", False) == "2(x − 1) + x = 13"
    assert G.coef_text(F(1, 2), "paren", "x") == "(1/2)x" and G.coef_text(F(1, 3), "div", "x") == "x/3"


# ---------------------------------------------------------------------------------------------
# Structure of the baked file
# ---------------------------------------------------------------------------------------------
def test_shape():
    assert len(ITEMS) == 200 and BAKED["grade"] == "8"
    for t in range(1, 6):
        assert len(by_tier(t)) == 40
        assert len({it["prompt"] for it in by_tier(t)}) == 40
    assert all(len(it["choices"]) == 4 for it in ITEMS)


# ---------------------------------------------------------------------------------------------
# Independent re-check of EVERY baked item
# ---------------------------------------------------------------------------------------------
def choice_key(it, i):
    text = it["choices"][i]
    if text in WORDS or re.fullmatch(r"[a-z] = 0", text):
        return text
    if text.startswith("("):
        return parse_point(text)
    return as_num(text)


@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_answer_independent(it):
    kind = kind_of(it)
    p = it["prompt"]
    ans = correct(it)
    keys = [choice_key(it, i) for i in range(len(it["choices"]))]
    assert len(set(keys)) == len(keys), ("equal-value choices", it["choices"])
    wrong_idx = [i for i in range(len(it["choices"])) if i != it["answer"]]
    if kind == "solve":
        eq = p[len("Solve: "):]
        v, s, i = solve1(eq)
        x = -i / s
        assert as_num(ans) == x, (p, ans)
        for w in wrong_idx:
            assert ev(eq.split(" = ")[0], {v: as_num(it["choices"][w])}) != ev(eq.split(" = ")[1], {v: as_num(it["choices"][w])})
    elif kind == "count":
        eq = COUNT_RE.match(p).group(1)
        v, s, i = solve1(eq)
        want = count_of(eq)
        assert ans == want, (p, ans)
        for w in wrong_idx:
            assert it["choices"][w] != want
            if it["choices"][w] == f"{v} = 0":
                # x = 0 is only ever a distractor on a "how many" item: never the count
                assert it["choices"][w] not in WORDS
        assert sorted(c for c in it["choices"] if c in WORDS) == sorted(set(WORDS[:3]) & set(it["choices"]))
        assert f"{v} = 0" in it["choices"] and len([c for c in it["choices"] if c in WORDS]) == 3
        if want == "One":
            assert -i / s != 0
    elif kind == "q":
        eq, phrase = Q_RE.match(p).groups()
        target = "None" if phrase == "No solution" else "Infinite"
        hits = []
        for idx, c in enumerate(it["choices"]):
            sub = eq.replace("k", f"({c.replace(M, '-')})".replace("(-", "(−"))
            if count_of(sub) == target:
                hits.append(idx)
        assert hits == [it["answer"]], (p, it["choices"], hits)
    elif kind == "syscount":
        l1, l2 = SYS_COUNT_RE.match(p).groups()
        status, _ = solve2(l1, l2)
        assert ans == status, (p, ans)
        assert ans != "Two" and "Two" in it["choices"]
    elif kind in ("meet", "sd"):
        if kind == "meet":
            e1, e2 = MEET_RE.match(p).groups()
            ask = "(x, y)"
        else:
            e1, e2, ask = SD_RE.match(p).groups()
        status, (x, y) = solve2(e1, e2)
        assert status == "One"
        want = {"x": x, "y": y, "(x, y)": (x, y)}[ask]
        got = parse_point(ans) if ask == "(x, y)" else as_num(ans)
        assert got == want, (p, ans)
        for w in wrong_idx:
            gw = parse_point(it["choices"][w]) if ask == "(x, y)" else as_num(it["choices"][w])
            assert gw != want
            if ask == "(x, y)":
                # a wrong point must fail at least one of the two equations
                px, py = gw
                assert not all(ev(e.split(" = ")[0], {"x": px, "y": py}) == ev(e.split(" = ")[1], {"x": px, "y": py})
                               for e in (e1, e2))


@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_explanation_matches_answer(it):
    """The explanation states the correct answer (as text) somewhere, and never a wrong choice as the result."""
    kind = kind_of(it)
    ans = correct(it)
    if kind == "q":
        assert re.search(rf"k = {re.escape(ans)}\b", it["explanation"])
    elif kind in ("count", "syscount"):
        words = {"Infinite": "infinitely many", "None": "no ", "One": "one|exactly once"}
        assert re.search(words[ans], it["explanation"], re.I), it["explanation"]
    elif kind == "solve" or kind in ("meet", "sd"):
        flat = re.sub(r"\s+", " ", it["explanation"])
        if kind == "sd" and ans.startswith("("):
            x, y = parse_point(ans)
            assert f"x = {G.num(x)}" in flat or f"y = {G.num(y)}" in flat
            assert f"y = {G.num(y)}" in flat and f"x = {G.num(x)}" in flat
        elif kind == "meet":
            x, y = parse_point(ans)
            assert f"x = {G.num(x)}" in flat and f"y = {G.num(y)}" in flat
        else:
            assert re.search(rf"= {re.escape(ans)}\.$", flat), flat


# ---------------------------------------------------------------------------------------------
# Labels: every non-null label's value is what the modelled rule gives
# ---------------------------------------------------------------------------------------------
def linear_label_values(eq):
    """Independent model of the T1/T4 wrong rules from the two sides' (slope, intercept)."""
    v = variable_of(eq)
    lhs, rhs = sides(eq)
    (a, b), (c, d) = lin(lhs, v), lin(rhs, v)
    m, k = a - c, d - b
    x = k / m
    out = {"SAME_SIGN_MOVE": [k / (a + c)], "CONST_SIGN": [(d + b) / m], "ONE_STEP": [k],
           "FORGOT_LAST_STEP": [k], "SIGN_SLIP": [-x], "DIVIDE_FOR_MULT": [k * m], "DEC_WRONG_WAY": [k * m]}
    if c == 0:
        out["ONE_TERM_CLEARED"] = [d - b / a]
        out["DEC_AS_FRAC"] = [k * {F(1, 2): 5, F(1, 4): 25, F(1, 5): 2, F(1, 10): 1}.get(a, 0)]
    return out


def group_label_values(eq):
    v = variable_of(eq)
    lhs, rhs = sides(eq)
    gside, oside = (lhs, rhs) if "(" in lhs else (rhs, lhs)
    gm = re.search(r"(\d+)\((\w) ([+−]) (\d+)\)", gside)
    pp, tt = int(gm.group(1)), int(gm.group(4)) * (1 if gm.group(3) == "+" else -1)
    gs, gi = lin(gside, v)
    c, d = lin(oside, v)
    e = gs - pp                      # the loose x term next to the group: p(x + t) + e x = c x + d
    assert gi == pp * tt             # no other number on the group side
    m, k = pp + e - c, d - pp * tt
    return {"PARTIAL_DIST": [(d - tt) / m], "SIGN_INSIDE": [(d + pp * tt) / m], "CONST_SIGN": [(d + pp * tt) / m],
            "SAME_SIGN_MOVE": [k / (pp + e + c)], "DROP_LIKE_TERM": [k / (pp - c)] if pp != c else []}


@pytest.mark.parametrize("it", [i for i in ITEMS if i["tier"] in (1, 4)], ids=lambda i: i["id"])
def test_labels_linear(it):
    eq = it["prompt"][len("Solve: "):]
    model = linear_label_values(eq)
    for i, lab in enumerate(it["misconceptions"]):
        if lab in (None, "ARITH"):
            continue
        assert lab in model, (it["prompt"], lab)
        assert as_num(it["choices"][i]) in model[lab], (it["prompt"], lab, it["choices"][i], model[lab])


@pytest.mark.parametrize("it", [i for i in ITEMS if i["tier"] == 2], ids=lambda i: i["id"])
def test_labels_distribute(it):
    eq = it["prompt"][len("Solve: "):]
    model = group_label_values(eq)
    for i, lab in enumerate(it["misconceptions"]):
        if lab in (None, "ARITH"):
            continue
        assert lab in model, (it["prompt"], lab)
        assert as_num(it["choices"][i]) in model[lab], (it["prompt"], lab, it["choices"][i], model[lab])


def test_labels_counts_and_systems():
    for it in by_tier(3) + by_tier(5):
        kind = kind_of(it)
        ans = correct(it)
        for i, lab in enumerate(it["misconceptions"]):
            if lab in (None, "ARITH"):
                continue
            c = it["choices"][i]
            if kind == "count":
                v = variable_of(COUNT_RE.match(it["prompt"]).group(1))
                want = {"ALWAYS_ONE": ("One", ("None", "Infinite")), "NONE_FOR_IDENTITY": ("None", ("Infinite",)),
                        "INFINITE_FOR_FALSE": ("Infinite", ("None",)), "ONE_IS_MANY": ("Infinite", ("One",)),
                        "ONE_IS_NONE": ("None", ("One",)), "CANCEL_IS_ZERO": (f"{v} = 0", ("None", "Infinite")),
                        "ZERO_GUESS": (f"{v} = 0", ("One",))}[lab]
                assert c == want[0] and ans in want[1], (it["prompt"], lab, c)
            elif kind == "q":
                assert lab in ("CONST_FOR_COEFF", "SIGN_PICK")
            elif kind == "syscount":
                want = {"PARALLEL_ONE": ("One", ("None", "Infinite")), "SAME_SLOPE_SAME_LINE": ("Infinite", ("None",)),
                        "NONE_FOR_IDENTITY": ("None", ("Infinite",)), "ONE_IS_NONE": ("None", ("One",)),
                        "ONE_IS_MANY": ("Infinite", ("One",)), "TWO_LINES_TWO": ("Two", WORDS)}[lab]
                assert c == want[0] and ans in want[1], (it["prompt"], lab, c)
            elif kind == "meet":
                x, y = parse_point(ans)
                px, py = parse_point(c)
                e1, e2 = MEET_RE.match(it["prompt"]).groups()
                intercepts = {coefs2(e1)[2], coefs2(e2)[2]}
                if lab == "SWAPPED_XY":
                    assert (px, py) == (y, x)
                elif lab == "INTERCEPT_AS_MEET":
                    assert px == 0 and py in intercepts
                elif lab == "DROPPED_SLOPE":
                    assert px == x and py in {x + b for b in intercepts}
                else:
                    raise AssertionError(lab)
            else:  # sd
                e1, e2, ask = SD_RE.match(it["prompt"]).groups()
                _, (x, y) = solve2(e1, e2)
                csum = coefs2(e1)[2] + coefs2(e2)[2]
                c2 = coefs2(e2)[2]
                if ask == "(x, y)":
                    px, py = parse_point(c)
                    if lab == "SWAPPED_XY":
                        assert (px, py) == (y, x)
                    elif lab == "READ_CONSTANT":
                        assert (px, py) in {(x, c2), (csum, y), (x, csum)}
                    else:
                        raise AssertionError(lab)
                else:
                    val = as_num(c)
                    if lab == "STOPPED_AT_SUM":
                        assert val == csum
                    elif lab == "GAVE_OTHER":
                        assert val == (y if ask == "x" else x)
                    elif lab == "READ_CONSTANT":
                        assert val == c2
                    else:
                        raise AssertionError(lab)


def test_every_label_declared_and_used():
    declared = set(BAKED["misconceptions"])
    used = {lab for it in ITEMS for lab in it["misconceptions"] if lab not in (None, "ARITH")}
    assert used <= declared
    assert declared - used == set(), declared - used


def test_no_division_by_a_negative_in_explanations():
    for it in ITEMS:
        assert "÷ (" + M not in it["explanation"] and f"÷ {M}" not in it["explanation"], it["explanation"]


def test_arith_is_rare():
    arith = sum(lab == "ARITH" for it in ITEMS for lab in it["misconceptions"])
    assert arith / (3 * len(ITEMS)) < 0.15, arith


def test_answer_balance_and_no_x_zero_answer():
    for t in range(1, 6):
        pos = Counter(it["answer"] for it in by_tier(t))
        assert all(pos[i] == 10 for i in range(4)), (t, pos)
    for it in ITEMS:
        assert not re.fullmatch(r"[a-z] = 0", correct(it))


# ---------------------------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_bounds(it):
    assert bounds_problems(it) == [], it["prompt"]


def fake(prompt, tier, choices=("1", "2", "3", "4")):
    return {"prompt": prompt, "tier": tier, "choices": list(choices), "answer": 0}


@pytest.mark.parametrize("prompt,tier", [
    ("Solve: 5x + 25 = 3x + 10", 1),            # constant 25 over 20
    ("Solve: 5x − 15 = 3x + 1", 1),             # negative present, 15 over 12
    ("Solve: 12x + 2 = 3x + 11", 1),            # coefficient 12 over 10
    ("Solve: 4x + 2 = 4x + 6", 1),              # no x left: not a solve item
    ("Solve: 4x + 1 = 3x + 10", 1),             # collected coefficient 1
    ("Solve: 5x + 2 = 3x + 11", 1),             # non-integer solution
    ("Solve: 3(x + 9) = x + 40", 2),            # product 27 over 20
    ("Solve: 8(x + 1) = 2x + 20", 2),           # multiplier 8 over 6
    ("Solve: 0.3x + 1 = 4", 4),                 # decimal outside the set
    ("Solve: (1/6)x + 1 = 4", 4),               # denominator outside the set
])
def test_bounds_checker_rejects(prompt, tier):
    try:
        problems = bounds_problems(fake(prompt, tier))
    except (AssertionError, ZeroDivisionError):
        return  # the checker could not even read it: also a rejection
    assert problems, prompt


@pytest.mark.parametrize("prompt,tier", [
    ("Solve: 5x + 2 = 3x + 10", 1),
    ("Solve: 3(x + 2) = x + 14", 2),
    ("Solve: (1/2)x + 3 = 7", 4),
    ("Solve: 0.5x + 2 = x − 1", 4),
    ("3x + 4 = 3x + 7. How many solutions?", 3),
    ("y = 2x + 1 and y = 2x + 5. How many solutions?", 5),
    ("x + y = 10 and x − y = 4. Find x.", 5),
    ("y = x + 4 and y = 3x. Where do they meet?", 5),
])
def test_bounds_checker_accepts(prompt, tier):
    assert bounds_problems(fake(prompt, tier)) == []


def test_bounds_checker_rejects_systems():
    assert bounds_problems(fake("x + y = 16 and x − y = 4. Find x.", 5))      # x = 10 over 8
    assert bounds_problems(fake("x + y = 8 and x − y = 0. Find x.", 5))       # x = y
    assert bounds_problems(fake("x + y = 7 and 2x + y = 9. Find x.", 5))      # nothing eliminates by adding
    assert bounds_problems(fake("y = 8x + 1 and y = 2x + 5. How many solutions?", 5))  # slope 8
    assert bounds_problems(fake("y = 2x + 1 and y = 3x + 9. Where do they meet?", 5))  # meets at x = -8, y = -15


def test_independent_check_can_fail():
    """Disproof: a planted wrong answer and a planted equal-value pair are caught by the same machinery."""
    it = next(i for i in by_tier(1))
    eq = it["prompt"][len("Solve: "):]
    v, s, i = solve1(eq)
    wrong = G.num(-i / s + 1)
    assert as_num(wrong) != -i / s
    assert ev(eq.split(" = ")[0], {v: as_num(wrong)}) != ev(eq.split(" = ")[1], {v: as_num(wrong)})
    # two choices equal in value: 2(x + 3) = 2x + 6 and 2x + 6 = 2(x + 3) are both identities
    assert count_of("2(x + 3) = 2x + 6") == count_of("2x + 6 = 2(x + 3)") == "Infinite"
    # and an item with two right doors is detected by the exactly-one-hit test
    eq2 = "3x + 4 = kx + 2"
    hits = [c for c in ("3", "4", "3") if count_of(eq2.replace("k", f"({c})")) == "None"]
    assert len(hits) != 1
