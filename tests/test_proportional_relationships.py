"""proportional-relationships cartridge: golden misconception values, an independent re-solve of every
baked item, choice-value uniqueness, honest labels, and the manifest's bounds walked over every correct
step of baked.json (with a checker self-test that must reject planted bad prompts).

The independent solver below reads each prompt with its own regexes and computes with
``fractions.Fraction`` (cross-multiplication, not the generator's division path). It never calls the
generator's ``analyze``. For questions whose answer is a choice that satisfies a relation (a point on
y = kx, an equation that fits a table) it evaluates every choice against the relation, so the check is
"exactly one door is right" rather than "the door I computed is right".
"""
import json
import math
import random
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "proportional-relationships"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


# ---------------------------------------------------------------------------------------------
# Golden cases: every catalog key, on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt, correct display, {label: wrong display (or list of displays)}
    # T1: (1/2) / (1/4): 2. Inverted 1/4 / 1/2 = 1/2. Multiplied 1/8. Flipped both 2 x 4 = 8. Tops 1 / 1.
    ("A hiker walks 1/2 mile in 1/4 hour. Miles per hour?", "2",
     {"INVERTED": "1/2", "MULTIPLIED": "1/8", "FLIPPED_BOTH": "8", "DROP_DENOMS": "1"}),
    # 3/4 / 1/2 = 3/2. Inverted 2/3. Multiplied 3/8. Tops 3 / 1.
    ("3/4 cup of flour makes 1/2 batch. Cups for 1 batch?", "1 1/2",
     {"INVERTED": "2/3", "MULTIPLIED": "3/8", "DROP_DENOMS": "3"}),
    # $6 / (3/4 lb) = $8. Inverted (3/4) / 6 = 1/8. Multiplied 6 x 3/4 = 4 1/2. 6 / 3 = 2.
    ("3/4 lb of nuts costs $6. Cost per lb?", "$8",
     {"INVERTED": "$1/8", "MULTIPLIED": "$4 1/2", "DROP_DENOMS": "$2"}),
    # (3/4) / (1/2) = 3/2. Inverted 2/3. Multiplied 3/8. Difference 3/4 - 1/2 = 1/4. Tops 3.
    ("Rope A is 3/4 ft, rope B is 1/2 ft. A is how many times B?", "1 1/2",
     {"INVERTED": "2/3", "MULTIPLIED": "3/8", "DIFFERENCE": "1/4", "DROP_DENOMS": "3"}),
    # T2 (the point kind is in test_point_distractors): equations. k = 4.
    ("Which shows y proportional to x, k = 4?", "y = 4x",
     {"ADDS_CONSTANT": "y = x + 4", "SWAPPED_XY": "x = 4y"}),
    # table 2,4,6 -> 6,12,18: k = 3. Adds y1 - x1 = 4. First y = 6.
    ("x: 2, 4, 6. y: 6, 12, 18. Which equation fits?", "y = 3x",
     {"ADDS_CONSTANT": "y = x + 4", "Y_AS_K": "y = 6x", "SWAPPED_XY": "x = 3y"}),
    # table 1,2,3 -> 5,6,7: y = x + 4. First ratio 5. Plus read as times 4. Swapped.
    ("x: 1, 2, 3. y: 5, 6, 7. Which equation fits?", "y = x + 4",
     {"PROP_ASSUMED": "y = 5x", "PLUS_AS_TIMES": "y = 4x", "SWAPPED_XY": "x = y + 4"}),
    # T3
    ("y = 6x. Constant of proportionality of y to x?", "6", {"INVERTED": "1/6", "KEEPS_VAR": "6x"}),
    ("(4, 20) is on y = kx. What is k?", "5", {"INVERTED": "1/5", "DIFFERENCE": "16", "PRODUCT": "80"}),
    ("4 tickets cost $28. In c = kn, what is k?", "$7",
     {"INVERTED": "$1/7", "DIFFERENCE": "$24", "PRODUCT": "$112"}),
    ("x: 2, 4, 6. y: 6, 12, 18. In y = kx, what is k?", "3",
     {"INVERTED": "1/3", "Y_AS_K": "6", "DIFFERENCE": "4"}),
    # x: 2, 5, 8 -> 6, 15, 24: k = 3; y goes up by 9; first y 6
    ("x: 2, 5, 8. y: 6, 15, 24. In y = kx, what is k?", "3", {"Y_AS_K": "6", "Y_STEP": "9"}),
    # T4: 15 / 5 = 3 per pen
    ("5 pens cost $15. Cost c for p pens?", "c = 3p",
     {"SWAPPED_VARS": "p = 3c", "TOTAL_AS_RATE": "c = 15p", "COUNT_AS_RATE": "c = 5p",
      "ADDS_CONSTANT": "c = p + 10"}),
    ("A tap fills 4 gal per minute. Gallons g in m minutes?", "g = 4m",
     {"SWAPPED_VARS": "m = 4g", "ADDS_CONSTANT": "g = m + 4", "DIVIDES": "g = 4/m"}),
    ("1 yard = 3 ft. Feet f in y yards?", "f = 3y",
     {"SWAPPED_VARS": "y = 3f", "ADDS_CONSTANT": "f = y + 3", "DIVIDES": "f = 3/y"}),
    # T5
    ("Map scale 1 cm : 5 km. 4 cm is how many km?", "20",
     {"SCALED_DOWN": "4/5", "FACTOR_ONLY": "5", "ADDITIVE": "9"}),
    ("Map scale 1 cm : 5 km. A 30 km road is how many cm?", "6",
     {"WRONG_WAY": "150", "FACTOR_ONLY": "5", "ADDITIVE": "25"}),
    # drawn 3 x 4 cm, 1 cm = 2 m: real 6 x 8 = 48; drawn area 12; 12 x 2 = 24; (3+2)(4+2) = 30
    ("Scale 1 cm = 2 m. A room is drawn 3 cm by 4 cm. Real area?", "48 sq m",
     {"DRAWING_AREA": "12 sq m", "LINEAR_AREA": "24 sq m", "ADDITIVE": "30 sq m"}),
    # real 6 x 8 m: drawn 3 x 4 = 12 sq cm; real area 48; 48 / 2 = 24
    ("Scale 1 cm = 2 m. A room is 6 m by 8 m. Drawing area?", "12 sq cm",
     {"ACTUAL_AREA": "48 sq cm", "LINEAR_AREA": "24 sq cm"}),
    ("3 cm on the plan is 12 m. 1 cm = ? m", "4",
     {"INVERTED": "1/4", "ADDITIVE": "9", "ACTUAL_AS_SCALE": "12"}),
    ("Scale a 2 by 3 rectangle by 3. New size?", "6 by 9",
     {"ADDITIVE": "5 by 6", "ONE_SIDE": ["6 by 3", "2 by 9"]}),
    ("Divide each side of a 6 by 9 rectangle by 3. New size?", "2 by 3",
     {"ADDITIVE": "3 by 6", "ONE_SIDE": ["2 by 9", "6 by 3"]}),
    ("Scale factor 3. Area is multiplied by what?", "9",
     {"LINEAR_AREA": "3", "ADDED_SIDES": "6", "CUBED": "27"}),
]
# keys exercised by the dedicated tests below rather than by GOLDEN rows
SPECIAL_KEYS = {"HAS_START", "ADDITIVE", "SWAPPED_XY", "INVERSE"}


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_misconception_values(prompt, correct, wrong):
    a = G.analyze(prompt)
    assert a.correct[0] == correct
    got = {}
    for lab, ch in a.wrong:
        got.setdefault(lab, set()).add(ch[0])
    for lab, disp in wrong.items():
        for d in ([disp] if isinstance(disp, str) else disp):
            assert d in got.get(lab, set()), (lab, d, got)


def test_golden_covers_every_catalog_key():
    used = {lab for _, _, w in GOLDEN for lab in w} | SPECIAL_KEYS
    assert used == set(BAKED["misconceptions"])


@pytest.mark.parametrize("x0", range(2, 7))
@pytest.mark.parametrize("k", range(2, 11))
def test_point_distractors(x0, k):
    """T2 point: y = kx; hand formulas for the other point's three wrong doors."""
    y0 = k * x0
    a = G.analyze(f"({x0}, {y0}) is on y = kx. Which point is also on it?")
    _, n, y = a.correct[1]
    assert 2 <= n <= 10 and n != x0 and y == k * n
    got = {}
    for lab, ch in a.wrong:
        got.setdefault(lab, set()).add(ch[1])
    assert ("pt", n, n + (y0 - x0)) in got["ADDITIVE"]  # added the same gap to both
    assert ("pt", k * n, n) in got["SWAPPED_XY"]  # x and y swapped
    if (x0 * y0) % n == 0:
        assert ("pt", n, x0 * y0 // n) in got["INVERSE"]  # kept x * y fixed
    else:
        assert "INVERSE" not in got


def test_has_start_goes_above_zero():
    for Y, X in G.PAIRS2:
        for k in range(2, 11):
            a = G.analyze(f"Which shows {Y} proportional to {X}, k = {k}?")
            texts = [ch[0] for lab, ch in a.wrong if lab == "HAS_START"]
            assert len(texts) == 1
            m = re.fullmatch(rf"{Y} = {k}{X} \+ (\d)", texts[0])
            assert m and 1 <= int(m[1]) <= 5, texts


def test_inverse_is_golden_by_hand():
    # (4, 12): other point at x = 2 (generator's pick). x * y = 48, so the inverse door is (2, 24).
    a = G.analyze("(4, 12) is on y = kx. Which point is also on it?")
    n = a.correct[1][1]
    assert n == 2
    assert dict((lab, ch[0]) for lab, ch in a.wrong)["INVERSE"] == "(2, 24)"
    assert dict((lab, ch[0]) for lab, ch in a.wrong)["ADDITIVE"] == "(2, 10)"
    assert dict((lab, ch[0]) for lab, ch in a.wrong)["SWAPPED_XY"] == "(6, 2)"


# ---------------------------------------------------------------------------------------------
# Independent parsing of choices (never the generator's keys)
# ---------------------------------------------------------------------------------------------
EQ_LIN = re.compile(r"^(\w) = (\d*)(\w)(?: \+ (\d+))?$")
EQ_INV = re.compile(r"^(\w) = (\d+)/(\w)$")
PT = re.compile(r"^\((\d+), (\d+)\)$")
BY = re.compile(r"^(\d+) by (\d+)$")


def canon_eq(s):
    """Orientation-free value of an equation: lhs - coef * rvar = const, over the sorted variable pair."""
    m = EQ_INV.match(s)
    if m:
        return ("inv", tuple(sorted((m[1], m[3]))), int(m[2]))
    m = EQ_LIN.match(s)
    if not m:
        return None
    lhs, coef, rvar, const = m[1], int(m[2] or 1), m[3], int(m[4] or 0)
    u, v = sorted((lhs, rvar))
    cu, cv = (1, -coef) if lhs == u else (-coef, 1)
    return ("lin", u, v, Fraction(cv, cu), Fraction(const, cu))


def holds(s, env):
    """Does the equation text hold for the variable values in env?"""
    m = EQ_INV.match(s)
    if m:
        return env[m[1]] * env[m[3]] == int(m[2])
    m = EQ_LIN.match(s)
    return env[m[1]] == int(m[2] or 1) * env[m[3]] + int(m[4] or 0)


def num_value(s):
    """Fraction value of a number-like choice (3, 1 1/2, 2/3, $8, $1/8, 48 sq m), else None."""
    s = re.sub(r" sq \w+$", "", s.strip().lstrip("$"))
    m = re.fullmatch(r"(\d+) (\d+)/(\d+)", s)
    if m:
        return int(m[1]) + Fraction(int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d+)/(\d+)", s)
    if m:
        return Fraction(int(m[1]), int(m[2]))
    return Fraction(int(s)) if re.fullmatch(r"\d+", s) else None


def choice_value(c):
    """Value key of any choice, computed independently of the generator."""
    m = PT.match(c)
    if m:
        return ("pt", int(m[1]), int(m[2]))
    m = BY.match(c)
    if m:
        return ("by",) + tuple(sorted((int(m[1]), int(m[2]))))
    v = num_value(c)
    if v is not None:
        return v
    e = canon_eq(c)
    if e is not None:
        return e
    if re.fullmatch(r"\d+[a-z]", c):
        return ("txt", c)
    raise AssertionError(f"cannot read choice {c!r}")


def canon_str(v, pre="", post=""):
    """The simplest-form text of a rational: 3, 2/3, 1 1/2."""
    v = Fraction(v)
    w, r = divmod(v.numerator, v.denominator)
    body = str(w) if r == 0 else (f"{r}/{v.denominator}" if w == 0 else f"{w} {r}/{v.denominator}")
    return pre + body + post


# ---------------------------------------------------------------------------------------------
# Independent solver: right(choice) + the correct working's steps + bounds violations
#   steps: [(op, a, b)] with op in "× ÷ +" -
# ---------------------------------------------------------------------------------------------
DENOMS = {2, 3, 4, 5, 6, 8, 10}


def ints(s):
    return [int(x) for x in re.findall(r"\d+", s)]


def step_bad(steps):
    """The §4a checks on the correct working, step by step."""
    bad = []
    for op, a, b in steps:
        a, b = Fraction(a), Fraction(b)
        if a.denominator != 1 or b.denominator != 1:
            bad.append(f"non-integer step {a} {op} {b}")
        elif op == "×":
            if not (1 <= a <= 10 and 1 <= b <= 10 and a * b <= 100):
                bad.append(f"× outside the tables: {a} × {b}")
        elif op == "÷":
            q = a / b
            if q.denominator != 1 or not 2 <= b <= 10 or not 2 <= q <= 10:
                bad.append(f"÷ not a table fact: {a} ÷ {b}")
        elif op in "+-":
            if not (0 <= a <= 20 and 0 <= b <= 20):
                bad.append(f"{op} literal over 20: {a} {op} {b}")
    return bad


def t1_bad(A, B):
    """T1 bounds for the rate A ÷ B of two proper fractions (Fractions in lowest terms)."""
    a, b, c, d = A.numerator, A.denominator, B.numerator, B.denominator
    bad = []
    for f in (A, B):
        if not (f.numerator < f.denominator and f.denominator in DENOMS):
            bad.append(f"fraction {f} outside T1")
    if b % d and d % b:
        bad.append(f"denominators {b} and {d} are not equal or multiples")
    if max(a, b, c, d) > 10:
        bad.append(f"cross products {a * d}, {b * c} not table facts")
    v = Fraction(a * d, b * c)
    whole = v.denominator == 1 and 2 <= v <= 10
    proper = 0 < v < 1 and v.denominator <= 5
    mixed = v > 1 and v.denominator != 1 and v.numerator // v.denominator <= 4 and v.denominator <= 4
    if not (whole or proper or mixed):
        bad.append(f"unit rate {v} outside T1")
    return bad


class Solved:
    def __init__(self, right, steps=(), bad=()):
        self.right, self.steps, self.bad = right, list(steps), list(bad)


def solve(prompt):  # noqa: C901 -- one branch per template
    p = prompt
    # ---- T1
    m = re.match(r"^A [\w ]+? (\d+/\d+) \w+ in (\d+/\d+) \w+\. \w+ per \w+\?$", p)
    if not m:
        m = re.match(r"^(\d+/\d+) \w+ of \w+ \w+ (\d+/\d+) \w+\. \w+ for 1 \w+\?$", p)
    if not m:
        m = re.match(r"^\w+ A is (\d+/\d+) \w+, \w+ B is (\d+/\d+) \w+\. A is how many times B\?$", p)
    if m:
        A, B = Fraction(m[1]), Fraction(m[2])
        v = Fraction(A.numerator * B.denominator, A.denominator * B.numerator)  # cross-multiplied
        bad = t1_bad(A, B)
        for raw in (m[1], m[2]):  # Fraction() reduces 4/6, so check the printed text itself
            if math.gcd(*map(int, raw.split("/"))) != 1:
                bad.append(f"{raw} is not in simplest form")
        return Solved(lambda c, e=canon_str(v): c == e, bad=bad)
    m = re.match(r"^(\d+/\d+) lb of \w+ costs \$(\d+)\. Cost per lb\?$", p)
    if m:
        A, t = Fraction(m[1]), int(m[2])
        v = Fraction(t * A.denominator, A.numerator)
        bad = []
        if not (A.numerator < A.denominator and A.denominator in DENOMS):
            bad.append("price fraction outside T1")
        if not (2 <= t <= 9 and v.denominator == 1 and 2 <= v <= 10):
            bad.append(f"price {t} / {A} = {v} outside T1")
        return Solved(lambda c, e=canon_str(v, "$"): c == e, bad=bad)
    # ---- T2
    m = re.match(r"^\((\d+), (\d+)\) is on y = kx\. Which point is also on it\?$", p)
    if m:
        x0, y0 = int(m[1]), int(m[2])
        k = Fraction(y0, x0)

        def right_pt(c, k=k):
            q = PT.match(c)
            return bool(q) and int(q[2]) == k * int(q[1])
        bad = []
        if not (2 <= x0 <= 6 and k.denominator == 1 and 2 <= k <= 10 and y0 <= 100):
            bad.append(f"point ({x0}, {y0}) outside T2")
        return Solved(right_pt, [("÷", y0, x0)], bad)
    m = re.match(r"^Which (?:shows|equation has) (\w) proportional to (\w)(?:,| with) k = (\d+)\?$", p)
    if m:
        want = canon_eq(f"{m[1]} = {m[3]}{m[2]}")
        k = int(m[3])
        return Solved(lambda c, w=want: canon_eq(c) == w, bad=[] if 2 <= k <= 10 else [f"k = {k}"])
    m = re.match(r"^x: ([\d, ]+)\. y: ([\d, ]+)\. (Which equation fits|In y = kx, what is k)\?$", p)
    if m:
        xs, ys = ints(m[1]), ints(m[2])
        rows = list(zip(xs, ys))
        bad, steps = [], []
        if len(rows) != 3 or max(xs) > 9 or max(ys) > 100 or xs != sorted(set(xs)):
            bad.append(f"table {rows} outside bounds")
        ratios = {Fraction(y, x) for x, y in rows}
        if len(ratios) == 1:
            k = ratios.pop()
            steps = [("÷", y, x) for x, y in rows]
            if not (k.denominator == 1 and 2 <= k <= 10):
                bad.append(f"k = {k}")
            if m[3] == "In y = kx, what is k":
                if min(xs) < 2:
                    bad.append("T3 table starts at x < 2")
                return Solved(lambda c, e=canon_str(k): c == e, steps, bad + step_bad(steps))
            return Solved(lambda c, r=rows: (canon_eq(c) is not None
                                             and all(holds(c, {"x": x, "y": y}) for x, y in r)),
                          steps, bad + step_bad(steps))
        gaps = {y - x for x, y in rows}
        assert m[3] == "Which equation fits" and len(gaps) == 1, f"neither proportional nor additive: {p}"
        gap = gaps.pop()
        if not 2 <= gap <= 9:
            bad.append(f"gap {gap}")
        steps = [("-", y, x) for x, y in rows]
        return Solved(lambda c, r=rows: (canon_eq(c) is not None
                                         and all(holds(c, {"x": x, "y": y}) for x, y in r)),
                      steps, bad + step_bad(steps))
    # ---- T3
    m = re.match(r"^(\w) = (\d+)(\w)\. Constant of proportionality of (\w) to (\w)\?$", p)
    assert not m or (m[4], m[5]) == (m[1], m[3]), p  # the question names the same two letters
    if m:
        k = int(m[2])
        return Solved(lambda c, e=str(k): c == e, bad=[] if 2 <= k <= 10 else [f"k = {k}"])
    m = re.match(r"^\((\d+), (\d+)\) is on y = kx\. What is k\?$", p)
    if m:
        x0, y0 = int(m[1]), int(m[2])
        k = Fraction(y0, x0)
        bad = []
        if not (2 <= x0 <= 10 and k.denominator == 1 and 2 <= k <= 10 and y0 <= 100):
            bad.append(f"point ({x0}, {y0}) outside T3")
        return Solved(lambda c, e=canon_str(k): c == e, [("÷", y0, x0)], bad + step_bad([("÷", y0, x0)]))
    m = re.match(r"^(\d+) \w+ cost \$(\d+)\. In (\w) = k(\w), what is k\?$", p)
    if m:
        n, t = int(m[1]), int(m[2])
        pre, count, total = "$", n, t
    else:
        m = re.match(r"^(\d+) \w+ in (\d+) \w+\. In (\w) = k(\w), what is k\?$", p)
        if m:
            pre, count, total = "", int(m[2]), int(m[1])
        else:
            m = re.match(r"^Earns \$(\d+) in (\d+) hours\. In (\w) = k(\w), what is k\?$", p)
            pre, count, total = ("$", int(m[2]), int(m[1])) if m else ("", 0, 0)
    if m and count:
        k = Fraction(total, count)
        bad = []
        if not (2 <= count <= 10 and k.denominator == 1 and 2 <= k <= 10 and total <= 100):
            bad.append(f"{total} / {count} outside T3")
        return Solved(lambda c, e=canon_str(k, pre): c == e, [("÷", total, count)],
                      bad + step_bad([("÷", total, count)]))
    # ---- T4: the answer is the equation dep = k * ind
    m = re.match(r"^(\d+) \w+ cost \$(\d+)\. Cost (\w) for (\w) \w+\?$", p)
    if m:
        n, t, dep, ind = int(m[1]), int(m[2]), m[3], m[4]
    else:
        m = re.match(r"^(\d+) \w+ in (\d+) \w+\. \w+ (\w) in (\w) \w+\?$", p)
        n, t, dep, ind = (int(m[2]), int(m[1]), m[3], m[4]) if m else (0, 0, "", "")
    if m:
        k = Fraction(t, n)
        want = canon_eq(f"{dep} = {k.numerator}{ind}")
        bad = []
        if not (2 <= n <= 10 and k.denominator == 1 and 2 <= k <= 10 and t <= 100):
            bad.append(f"{t} / {n} outside T4")
        return Solved(lambda c, w=want: canon_eq(c) == w, [("÷", t, n)], bad + step_bad([("÷", t, n)]))
    for rx, kgroup, dgroup in (
            (r"^A [\w ]+? (\d+) \w+ per \w+\. \w+ (\w) in (\w) \w+\?$", 1, 2),
            (r"^\w+ cost \$(\d+) each\. Cost (\w) for (\w) \w+\?$", 1, 2),
            (r"^1 \w+ = (\d+) \w+\. \w+ (\w) in (\w) \w+\?$", 1, 2),
            (r"^Each \w+ is (\d+) \w+\. \w+ (\w) in (\w) \w+\?$", 1, 2),
            (r"^(\d+) \w+ make 1 \w+\. \w+ (\w) in (\w) \w+\?$", 1, 2)):
        m = re.match(rx, p)
        if m:
            k, dep, ind = int(m[kgroup]), m[dgroup], m[dgroup + 1]
            want = canon_eq(f"{dep} = {k}{ind}")
            return Solved(lambda c, w=want: canon_eq(c) == w, bad=[] if 2 <= k <= 10 else [f"k = {k}"])
    # ---- T5
    m = re.match(r"^(?:Map|Plan) scale 1 (\w+) : (\d+) (\w+)\. (\d+) \1 is how many \3\?$", p)
    if m:
        k, n = int(m[2]), int(m[4])
        steps = [("×", n, k)]
        bad = [] if 2 <= k <= 10 and 2 <= n <= 10 and n * k <= 100 else [f"{n} x {k} outside T5"]
        return Solved(lambda c, e=str(n * k): c == e, steps, bad + step_bad(steps))
    m = re.match(r"^(?:Map|Plan) scale 1 (\w+) : (\d+) (\w+)\. A (\d+) \3 \w+ is how many \1\?$", p)
    if m:
        k, real = int(m[2]), int(m[4])
        steps = [("÷", real, k)]
        bad = [] if 2 <= k <= 10 and real <= 100 else [f"{real} / {k} outside T5"]
        return Solved(lambda c, e=str(real // k): c == e and real % k == 0, steps, bad + step_bad(steps))
    m = re.match(r"^Scale 1 (\w+) = (\d+) (\w+)\. A room is drawn (\d+) \1 by (\d+) \1\. Real area\?$", p)
    if m:
        k, a, b, au = int(m[2]), int(m[4]), int(m[5]), m[3]
        A, B = a * k, b * k  # real sides
        steps = [("×", a, k), ("×", b, k), ("×", A, B)]
        bad = [] if (2 <= k <= 10 and a >= 2 and b >= 2 and A <= 10 and B <= 10) else [f"room {A} x {B}"]
        return Solved(lambda c, e=f"{A * B} sq {au}": c == e, steps, bad + step_bad(steps))
    m = re.match(r"^Scale 1 (\w+) = (\d+) (\w+)\. A room is (\d+) \3 by (\d+) \3\. Drawing area\?$", p)
    if m:
        du, k, A, B = m[1], int(m[2]), int(m[4]), int(m[5])
        a, b = A // k, B // k
        steps = [("÷", A, k), ("÷", B, k), ("×", a, b)]
        bad = [] if (2 <= k <= 10 and A % k == 0 and B % k == 0 and A <= 10 and B <= 10) else [f"room {A} x {B}"]
        return Solved(lambda c, e=f"{a * b} sq {du}": c == e, steps, bad + step_bad(steps))
    m = re.match(r"^(\d+) (\w+) on the (?:map|plan) is (\d+) (\w+)\. 1 \2 = \? \4$", p)
    if m:
        n, t = int(m[1]), int(m[3])
        steps = [("÷", t, n)]
        bad = [] if (2 <= n <= 10 and t % n == 0 and 2 <= t // n <= 10 and t <= 100) else [f"{t} / {n}"]
        return Solved(lambda c, e=str(t // n): c == e and t % n == 0, steps, bad + step_bad(steps))
    m = re.match(r"^(?:Scale a|Enlarge a) (\d+) by (\d+) rectangle (?:by|with scale factor) (\d+)\. New size\?$", p)
    if m:
        a, b, k = int(m[1]), int(m[2]), int(m[3])
        steps = [("×", a, k), ("×", b, k)]
        bad = [] if (a < b and 2 <= k <= 10 and b * k <= 10) else [f"{a} by {b} scaled by {k}"]
        return Solved(lambda c, e=f"{a * k} by {b * k}": c == e, steps, bad + step_bad(steps))
    m = re.match(r"^Divide each side of a (\d+) by (\d+) rectangle by (\d+)\. New size\?$", p)
    if m:
        A, B, k = int(m[1]), int(m[2]), int(m[3])
        steps = [("÷", A, k), ("÷", B, k)]
        bad = [] if (A < B <= 10 and 2 <= k <= 10) else [f"{A} by {B} divided by {k}"]
        return Solved(lambda c, e=f"{A // k} by {B // k}": c == e and A % k == 0 and B % k == 0, steps,
                      bad + step_bad(steps))
    m = re.match(r"^(?:Scale factor (\d+)\. Area is multiplied by what|"
                 r"Each side is (\d+) times as long\. Area is \? times as big)[?.]$", p)
    if m:
        k = int(m[1] or m[2])
        steps = [("×", k, k)]
        return Solved(lambda c, e=str(k * k): c == e, steps, step_bad(steps) + ([] if 2 <= k <= 10 else [f"k={k}"]))
    raise AssertionError(f"independent solver cannot read: {p!r}")


def right_indices(item):
    s = solve(item["prompt"])
    return [i for i, c in enumerate(item["choices"]) if s.right(c)]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    """Exactly one door is right by the independent solver, and it is the baked answer."""
    assert right_indices(item) == [item["answer"]], (item["prompt"], item["choices"])
    assert len(item["choices"]) == 4


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_explanation_shows_the_answer(item):
    expl, ans = item["explanation"], item["choices"][item["answer"]]
    nums = re.findall(r"\d+", ans)
    assert ans in expl or all(re.search(rf"\b{n}\b", expl) for n in nums), (ans, expl)


def test_answer_checker_can_fail():
    """Disproof: plant a wrong answer and a second right door; the independent check must notice."""
    it = dict(next(i for i in ITEMS if i["tier"] == 2 and i["prompt"].startswith("(")))
    wrong = (it["answer"] + 1) % 4
    assert right_indices({**it, "answer": wrong}) != [wrong]
    twin = list(it["choices"])
    twin[wrong] = twin[it["answer"]]  # a duplicate right door
    assert len(right_indices({**it, "choices": twin})) == 2
    it = next(i for i in ITEMS if i["tier"] == 5 and i["prompt"].startswith("Scale factor"))
    assert right_indices({**it, "answer": (it["answer"] + 1) % 4}) != [(it["answer"] + 1) % 4]


# ---------------------------------------------------------------------------------------------
# Choices: unique in value, simplest form, one display kind
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(item):
    vals = [choice_value(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    for v in vals:
        if isinstance(v, Fraction):
            assert 0 < v <= 999


@pytest.mark.parametrize("a,b", [("1/2", "2/4"), ("2", "4/2"), ("1 1/2", "3/2"), ("$8", "8"),
                                 ("48 sq m", "48"), ("y = 4x", "y = 4x + 0"), ("c = 3p", "c = 3p + 0"),
                                 ("(5, 15)", "(5, 15)"), ("6 by 9", "9 by 6")])
def test_value_checker_sees_equal_forms(a, b):
    """Disproof of the uniqueness check: forms equal in value must collide, so a planted pair that is
    equal in value but not in text (1/2 and 2/4) would be caught by test_no_two_choices_equal_in_value."""
    assert choice_value(a) == choice_value(b)


def test_planted_equal_pair_fails_the_uniqueness_check():
    item = {"choices": ["1/2", "2/4", "3", "4"]}
    vals = [choice_value(c) for c in item["choices"]]
    assert len(set(vals)) != len(vals)


def test_value_checker_separates_different_things():
    assert choice_value("p = 3c") != choice_value("c = 3p")
    assert choice_value("c = p + 10") != choice_value("c = 10p")
    assert choice_value("5 by 6") != choice_value("6 by 9")
    assert choice_value("6 by 9") == choice_value("9 by 6")  # the same rectangle: never offered together
    assert choice_value("(5, 15)") != choice_value("(15, 5)")


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_numbers_are_in_simplest_form(item):
    for c in item["choices"]:
        v = num_value(c)
        if v is None:
            continue
        assert re.sub(r" sq \w+$", "", c.lstrip("$")) == canon_str(v), c


def shape(c):
    if c.startswith("$"):
        return "money"
    if " sq " in c:
        return "area"
    if PT.match(c):
        return "point"
    if BY.match(c):
        return "by"
    if "=" in c:
        return "equation"
    return "number"


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_share_one_display_kind(item):
    shapes = Counter(shape(c) for c in item["choices"])
    if "Constant of proportionality of" in item["prompt"]:
        # the "6x" door (the whole term, not k) is the one deliberate odd shape
        assert shapes == Counter({"number": 4}) and sum(1 for c in item["choices"] if re.fullmatch(r"\d+[a-z]", c)) == 1
        return
    assert len(shapes) == 1, item["choices"]


# ---------------------------------------------------------------------------------------------
# Labels are honest; misconceptions do the work
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_come_from_their_rule(item):
    a = G.analyze(item["prompt"])
    by_label = {}
    all_vals = set()
    for lab, ch in a.wrong:
        by_label.setdefault(lab, set()).add(ch[0])
        all_vals.add(choice_value(ch[0]))
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels)
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        if m == "ARITH":
            assert choice_value(c) not in all_vals, f"ARITH {c} is really a modelled wrong rule"
        else:
            assert c in by_label.get(m, set()), (c, m, by_label)


def test_arith_share_is_small():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 1 / 3


def test_every_template_appears():
    kinds = Counter(G.analyze(it["prompt"]).kind for it in ITEMS)
    assert set(kinds) == set(G.RE), set(G.RE) - set(kinds)


def test_every_catalog_key_is_used_by_some_item():
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert set(BAKED["misconceptions"]) <= used


def test_tier_shape():
    assert [t["tier"] for t in BAKED["tiers"]] == [1, 2, 3, 4, 5]
    assert Counter(it["tier"] for it in ITEMS) == Counter({t: 40 for t in range(1, 6)})
    assert BAKED["grade"] == "7"
    assert all(s.startswith("CCSS.MATH.CONTENT.7.") for s in BAKED["standards"])


def test_regenerating_matches_baked():
    fresh = G.generate(BAKED, random.Random(BAKED["seed"]))
    assert len(fresh) == len(ITEMS)
    for f, b in zip(fresh, ITEMS):
        assert {k: f[k] for k in f} == {k: b[k] for k in f}


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"), walking every correct step of the independent solver
# ---------------------------------------------------------------------------------------------
def bounds_violations(prompt):
    return solve(prompt).bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]


@pytest.mark.parametrize("item", [i for i in ITEMS if i["tier"] == 2 and i["prompt"].startswith("(")],
                         ids=lambda i: i["id"])
def test_other_point_stays_small(item):
    x, y = (int(v) for v in re.findall(r"\d+", item["choices"][item["answer"]]))
    assert 2 <= x <= 10 and y <= 100


@pytest.mark.parametrize("prompt,expect_bad", [
    # T1
    ("A hiker walks 1/2 mile in 1/4 hour. Miles per hour?", False),
    ("A hiker walks 1/3 mile in 1/4 hour. Miles per hour?", True),       # denominators 3 and 4
    ("A hiker walks 1/2 mile in 1/12 hour. Miles per hour?", True),      # denominator 12
    ("A hiker walks 3/4 mile in 1/8 hour. Miles per hour?", False),      # 6
    ("A hiker walks 7/8 mile in 1/8 hour. Miles per hour?", False),      # 7, cross products 56 and 8
    ("A hiker walks 5/6 mile in 1/12 hour. Miles per hour?", True),
    ("A hiker walks 4/6 mile in 1/6 hour. Miles per hour?", True),       # 4/6 is not simplest form
    ("A hiker walks 1/2 mile in 3/4 hour. Miles per hour?", False),      # 2/3, a proper fraction
    ("A hiker walks 7/10 mile in 3/5 hour. Miles per hour?", True),      # 7/6: a 1 1/6 answer is too fiddly
    ("A hiker walks 3/4 mile in 1/2 hour. Miles per hour?", False),      # 1 1/2
    ("3/4 lb of nuts costs $6. Cost per lb?", False),
    ("3/4 lb of nuts costs $10. Cost per lb?", True),                    # 40/3 is not whole
    ("1/10 lb of nuts costs $9. Cost per lb?", True),                    # $90 rate
    # T2
    ("(2, 6) is on y = kx. Which point is also on it?", False),
    ("(8, 24) is on y = kx. Which point is also on it?", True),          # x0 = 8
    ("(2, 26) is on y = kx. Which point is also on it?", True),          # k = 13
    ("Which shows y proportional to x, k = 4?", False),
    ("Which shows y proportional to x, k = 14?", True),
    ("x: 2, 4, 6. y: 6, 12, 18. Which equation fits?", False),
    ("x: 3, 6, 9. y: 36, 72, 108. Which equation fits?", True),          # y over 100 and k = 12
    ("x: 1, 2, 3. y: 5, 6, 7. Which equation fits?", False),
    ("x: 1, 2, 3. y: 15, 16, 17. Which equation fits?", True),           # gap 14
    # T3
    ("(4, 20) is on y = kx. What is k?", False),
    ("(4, 44) is on y = kx. What is k?", True),                          # k = 11
    ("y = 6x. Constant of proportionality of y to x?", False),
    ("y = 12x. Constant of proportionality of y to x?", True),
    ("4 tickets cost $28. In c = kn, what is k?", False),
    ("4 tickets cost $30. In c = kn, what is k?", True),                 # 7 1/2
    ("12 pens cost $24. In c = kn, what is k?", True),                   # 12 pens
    # T4
    ("5 pens cost $15. Cost c for p pens?", False),
    ("5 pens cost $60. Cost c for p pens?", True),                       # rate 12
    ("A tap fills 4 gal per minute. Gallons g in m minutes?", False),
    ("A tap fills 14 gal per minute. Gallons g in m minutes?", True),
    # T5
    ("Map scale 1 cm : 5 km. 4 cm is how many km?", False),
    ("Map scale 1 cm : 12 km. 4 cm is how many km?", True),
    ("Map scale 1 cm : 9 km. 12 cm is how many km?", True),              # drawn length 12
    ("Map scale 1 cm : 5 km. A 30 km road is how many cm?", False),
    ("Map scale 1 cm : 5 km. A 33 km road is how many cm?", True),       # 33 / 5
    ("Scale 1 cm = 2 m. A room is drawn 3 cm by 4 cm. Real area?", False),
    ("Scale 1 cm = 2 m. A room is drawn 6 cm by 4 cm. Real area?", True),  # 12 m side
    ("Scale 1 cm = 2 m. A room is 6 m by 8 m. Drawing area?", False),
    ("Scale 1 cm = 2 m. A room is 6 m by 9 m. Drawing area?", True),     # 9 / 2
    ("3 cm on the plan is 12 m. 1 cm = ? m", False),
    ("3 cm on the plan is 14 m. 1 cm = ? m", True),
    ("Scale a 2 by 3 rectangle by 3. New size?", False),
    ("Scale a 2 by 6 rectangle by 3. New size?", True),                  # 18
    ("Divide each side of a 6 by 9 rectangle by 3. New size?", False),
    ("Divide each side of a 6 by 9 rectangle by 4. New size?", True),
    ("Scale factor 3. Area is multiplied by what?", False),
    ("Scale factor 11. Area is multiplied by what?", True),
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, bounds_violations(prompt)


def test_manifest_states_bounds():
    assert "bounds" in BAKED and "times-table" in BAKED["bounds"]
    assert "denominators equal or one a multiple" in BAKED["bounds"] or "equal or one a multiple" in BAKED["bounds"]


def test_pool_denominators_are_compatible():
    """The T1 pool never pairs unlike denominators that are not multiples (e.g. 1/3 with 1/4)."""
    for cls, rows in G.POOL.items():
        for a, b, c, d in rows:
            assert b % d == 0 or d % b == 0, (cls, a, b, c, d)
            assert math.gcd(a, b) == 1 and math.gcd(c, d) == 1
