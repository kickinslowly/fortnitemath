"""Procedural generator for the scatter-two-way cartridge (fnm-cart/1, grade 8, 8.SP.A.1-A.4).

Contract (PROTOCOL.md section 3): ``generate(manifest, rng) -> list[dict]`` returning items in the
section 4 shape without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from
other cartridges.

Design
------
* Every wrong choice is the value a student holding one named misconception gets. A candidate is
  ``(label, text, key)``: ``key`` is the exact VALUE (int, Fraction, point tuple, (m, b) line, word),
  so two choices are never equal in value even when their text differs. ``ARITH`` only fills.
* Bounds (PROTOCOL 4b, grade 8: Coordinates and lines, Two-way tables) are enforced by the
  ``bad_*`` gates below before an item is built.

Tiers
-----
1. Association (positive / negative / none, from a sentence or a short point list)
2. Outliers (the point off the pattern) and the line y = mx + b through three points
3. Use a line of fit: predict, read slope and start, solve for x
4. Two-way table counts: row / column / grand totals, "only", a missing cell
5. Relative frequency: a part over its own row or column total, percents, who is more likely
"""
from __future__ import annotations

import random
from fractions import Fraction

M = "−"  # minus sign
ALLOWED_EXTRA = set("×÷−≤≥≠√π")


def num(n: int) -> str:
    return str(n).replace("-", M)


def pt(p) -> str:
    return f"({num(p[0])}, {num(p[1])})"


def pts(ps) -> str:
    return ", ".join(pt(p) for p in ps)


def line_text(m: int, b: int) -> str:
    mt = "" if m == 1 else M if m == -1 else num(m)
    s = f"y = {mt}x"
    if b > 0:
        s += f" + {b}"
    elif b < 0:
        s += f" {M} {-b}"
    return s


SINGULAR = {"boys": "boy", "girls": "girl", "kids": "kid", "adults": "adult", "tacos": "taco"}


def cnt(n: int, noun: str) -> str:
    """'1 girl', '4 girls', '3 bus' (mass nouns stay as they are)."""
    return f"{n} {SINGULAR.get(noun.lower(), noun) if n == 1 else noun}"


def frac_text(f: Fraction) -> str:
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


PERCENTS = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 25, 75}


# ---------------------------------------------------------------------------------------------
# Bounds gates (PROTOCOL 4b). Each returns a list of violations (empty = fine).
# ---------------------------------------------------------------------------------------------
def bad_points(ps) -> list:
    bad = []
    if not 3 <= len(ps) <= 5:
        bad.append(f"{len(ps)} points (want 3-5)")
    if any(not (0 <= x <= 20 and 0 <= y <= 20) for x, y in ps):
        bad.append(f"coordinate outside 0-20: {ps}")
    return bad


def bad_line(m: int, b: int) -> list:
    bad = []
    if not (1 <= m <= 10 or -5 <= m <= -1):
        bad.append(f"slope {m}")
    if not 0 <= b <= 20:
        bad.append(f"start {b}")
    return bad


def bad_predict(m: int, b: int, x: int) -> list:
    bad = bad_line(m, b)
    if not 1 <= x <= 10:
        bad.append(f"x {x}")
    if not 0 <= m * x + b <= 100:
        bad.append(f"prediction {m * x + b}")
    return bad


def bad_table(cells) -> list:
    bad = []
    if any(not 0 <= c <= 20 for c in cells):
        bad.append(f"cell outside 0-20: {cells}")
    if sum(cells) > 60:
        bad.append(f"grand total {sum(cells)} > 60")
    return bad


def bad_freq(f: Fraction, total: int) -> list:
    bad = []
    if not 2 <= total <= 20:
        bad.append(f"total {total}")
    if not 2 <= f.denominator <= 12 or not 0 < f < 1:
        bad.append(f"relative frequency {f} not a proper fraction with denominator 2-12")
    return bad


# ---------------------------------------------------------------------------------------------
# Item assembly
# ---------------------------------------------------------------------------------------------
def make_item(tier, prompt, ans, cands, pos, expl, rng, n=4, fill=(), min_real=2):
    """``ans`` = (text, key); ``cands`` = [(label, text, key)] most specific first; ``fill`` =
    [(text, key)] for ARITH. None when the item cannot be built."""
    atext, akey = ans
    wrong, seen = [], {akey}
    for lab, text, key in cands:
        if key in seen:
            continue
        seen.add(key)
        wrong.append((lab, text))
        if len(wrong) == n - 1:
            break
    real = len(wrong)
    seen |= {k for _, _, k in cands}
    for text, key in fill:
        if len(wrong) == n - 1:
            break
        if key not in seen:
            seen.add(key)
            wrong.append(("ARITH", text))
    if len(wrong) != n - 1 or real < min(min_real, n - 1):
        return None
    if len(prompt) > 60 or len(expl) > 160 or any(len(t) > 14 for _, t in wrong) or len(atext) > 14:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:pos] + [(None, atext)] + wrong[pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [t for _, t in pairs],
        "answer": pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


def int_fill(correct: int, lo=0):
    out = []
    for d in (1, -1, 2, -2, 3, -3, 4, -4, 5):
        v = correct + d
        if v >= lo:
            out.append((num(v), v))
    return out


def pick(rng, xs):
    return xs[rng.randrange(len(xs))]


# =============================================================================================
# Misconception rules: pure functions of the item's numbers (builders and tests both use them).
# Each returns [(label, value)] most specific first; None-valued rules are dropped by callers.
# =============================================================================================
def line_wrongs(m: int, b: int, x1: int, y1: int):
    """Wrong lines (m, b) for 'which line fits' through points whose first point is (x1, y1)."""
    out = []
    if b != m and b <= 10:
        out.append(("START_AS_SLOPE", (b, m)))
    out.append(("NO_START", (m, 0)))
    if y1 % x1 == 0 and y1 // x1 not in (m, b):
        out.append(("SLOPE_FROM_ONE_POINT", (y1 // x1, 0)))
    return out


def predict_wrongs(m: int, b: int, x: int):
    out = [("NO_START", m * x), ("ADDED_ALL", m + x + b)]
    if abs(b * x + m) <= 100:
        out.append(("START_AS_SLOPE", b * x + m))
    return out


def slope_wrongs(m: int, b: int):
    return [("START_AS_SLOPE", b), ("ADDED_SLOPE_START", m + b), ("MULT_SLOPE_START", m * b)]


def start_wrongs(m: int, b: int):
    return [("SLOPE_AS_START", m), ("ADDED_SLOPE_START", m + b), ("MULT_SLOPE_START", m * b)]


def inverse_wrongs(m: int, b: int, y: int):
    out = [("STOPPED_EARLY", y - b)]
    if y % m == 0:
        out.append(("IGNORE_START", y // m))
    if (y + b) % m == 0:
        out.append(("ADD_START", (y + b) // m))
    return out


def col_wrongs(a1: int, a2: int, b1: int, b2: int):
    """Total of the first column (a1 + b1)."""
    return [("GRAND_TOTAL", a1 + a2 + b1 + b2), ("WRONG_ROW", a1 + a2), ("ONE_CELL", a1), ("WRONG_ROW", b1 + b2),
            ("WRONG_ROW", a2 + b2)]


def row_wrongs(a1: int, a2: int, b1: int, b2: int):
    """Total of the first row (a1 + a2)."""
    return [("GRAND_TOTAL", a1 + a2 + b1 + b2), ("WRONG_ROW", a1 + b1), ("ONE_CELL", a1), ("WRONG_ROW", a2 + b2)]


def grand_wrongs(a1: int, a2: int, b1: int, b2: int, left_out: int):
    """Grand total; ``left_out`` is the cell the student forgets."""
    return [("WRONG_ROW", a1 + a2), ("LEFT_OUT_CELL", a1 + a2 + b1 + b2 - left_out), ("WRONG_ROW", a1 + b1),
            ("WRONG_ROW", b1 + b2)]


def only_wrongs(n: int, k: int):
    return [("ADDED_FOR_ONLY", n + k), ("WHOLE_FOR_ONLY", n), ("ONLY_IS_BOTH", k)]


def missing_wrongs(t: int, a: int):
    return [("ADDED_FOR_MISSING", t + a), ("GIVEN_CELL", a), ("TOTAL_AS_MISSING", t)]


def frac_wrongs(a: int, b: int, extra=None):
    """Fraction a / (a + b) of one row or column. ``extra`` = ("GRAND_DENOMINATOR" | "WRONG_TOTAL", N)."""
    tot = a + b
    out = []
    if extra:
        out.append((extra[0], Fraction(a, extra[1])))
    out += [("PART_TO_PART", Fraction(a, b)), ("OTHER_PART", Fraction(b, tot)), ("WHOLE_OVER_PART", Fraction(tot, a))]
    return out


def percent_wrongs(a: int, p: int):
    return [("OTHER_PART", 100 - p), ("COUNT_AS_PERCENT", a)]


# =============================================================================================
# Tier 1: association
# =============================================================================================
# (x name, x plural, y name, y plural, sign, noncausal): sign +1 means y moves the same way as x.
# The prompt names each variable once ("Car age rises, car value falls") so no phrase changes the
# variable (an "older car" / "newer car" pair would flip it).
CONTEXTS = [
    ("study time", False, "test scores", True, 1, False),
    ("practice time", False, "shots made", True, 1, False),
    ("hours worked", True, "pay", False, 1, False),
    ("tree height", False, "trunk width", False, 1, False),
    ("pizza size", False, "price", False, 1, False),
    ("rainfall", False, "umbrella sales", True, 1, False),
    ("puppy age", False, "puppy weight", False, 1, False),
    ("ice cream sales", True, "sunburns", True, 1, True),
    ("car age", False, "car value", False, -1, False),
    ("temperature", False, "cocoa sales", True, -1, False),
    ("miles driven", True, "gas left", False, -1, False),
    ("screen time", False, "sleep time", False, -1, False),
    ("absences", True, "grades", True, -1, False),
    ("burn time", False, "candle height", False, -1, False),
    ("altitude", False, "air temperature", False, -1, False),
    ("car speed", False, "trip time", False, -1, False),
]
NO_FALL = {"car age", "puppy age", "burn time"}  # these only grow; never written as "falls"
NONE_CONTEXTS = [
    ("Shoe size", "favorite color"), ("Birth month", "quiz score"), ("Hair length", "math grade"),
    ("Locker number", "height"), ("Eye color", "free throws made"), ("Backpack color", "reading speed"),
    ("Seat number", "lunch cost"), ("Phone number", "shoe size"),
]
WORDS = ("Positive", "Negative", "None")


def t1_labels(answer: int, xdir, noncausal: bool = False) -> dict:
    """{wrong word index: label}. answer 0 Positive, 1 Negative, 2 None; ``xdir`` is the first
    variable's direction in the sentence (+1 rises, -1 falls) or None for a list of points."""
    if answer == 0:
        return {1: "BOTH_DOWN_NEGATIVE" if xdir == -1 else "REVERSED",
                2: "CAUSE_FOR_LINK" if noncausal else "MISSES_PATTERN"}
    if answer == 1:
        return {0: "FIRST_VARIABLE" if xdir == 1 else "REVERSED",
                2: "CAUSE_FOR_LINK" if noncausal else "DOWN_IS_NONE"}
    return {0: "PATTERN_FROM_NOISE", 1: "PATTERN_FROM_NOISE"}


def _t1_choices(answer, wrong_labels):
    return (WORDS[answer], answer), [(wrong_labels[w], WORDS[w], w) for w in range(3) if w != answer]


def t1_context(rng, pos, sign):
    ctx = pick(rng, [c for c in CONTEXTS if c[4] == sign])
    xn, xpl, yn, ypl, _, noncausal = ctx
    xdir = 1 if xn in NO_FALL else pick(rng, (1, -1))
    ydir = xdir * sign

    def verb(d, plural):
        return ("rise" if plural else "rises") if d == 1 else ("fall" if plural else "falls")

    xs_ = f"{xn[0].upper()}{xn[1:]} {verb(xdir, xpl)}"
    prompt = f"{xs_}, {yn} {verb(ydir, ypl)}. Association?"
    ans_i = 0 if sign == 1 else 1
    labs = t1_labels(ans_i, xdir, noncausal)
    if sign == 1:
        expl = "Both go up together (or both go down): a positive association."
    else:
        expl = "One goes up while the other goes down: a negative association."
    ans, cands = _t1_choices(ans_i, labs)
    return make_item(1, prompt, ans, cands, pos, expl, rng, n=3)


def t1_none_context(rng, pos):
    a, b = pick(rng, NONE_CONTEXTS)
    prompt = f"{a} and {b}. Association?"
    ans, cands = _t1_choices(2, t1_labels(2, None))
    expl = "Knowing one tells you nothing about the other: no association."
    return make_item(1, prompt, ans, cands, pos, expl, rng, n=3)


def t1_list(rng, pos, kind):
    """kind 0 positive, 1 negative, 2 none."""
    n = rng.randint(3, 4) if kind != 2 else rng.randint(4, 5)
    if kind == 2:
        ys = [rng.randint(1, 20) for _ in range(n)]
        c = sum((i + 1 - Fraction(n + 1, 2)) * y for i, y in enumerate(ys))
        zig = all((ys[i + 1] - ys[i]) * (ys[i + 2] - ys[i + 1]) < 0 for i in range(n - 2))
        if c != 0 or not zig or max(ys) - min(ys) < 6 or abs(ys[-1] - ys[0]) > 3:
            return None
        expl = "The y values jump up and down with no trend: no association."
    else:
        steps = [rng.randint(1, 5) for _ in range(n - 1)]
        start = rng.randint(1, 9)
        ys = [start]
        for s in steps:
            ys.append(ys[-1] + s)
        if kind == 1:
            ys = [ys[-1] - y + start for y in ys]  # same gaps, falling
        if max(ys) > 20 or min(ys) < 0:
            return None
        if kind == 0:
            expl = "As x goes up, y goes up: a positive association."
        else:
            expl = "As x goes up, y goes down: a negative association."
    points = [(i + 1, y) for i, y in enumerate(ys)]
    if bad_points(points):
        return None
    prompt = f"Points {pts(points)}. Association?"
    ans, cands = _t1_choices(kind, t1_labels(kind, None))
    return make_item(1, prompt, ans, cands, pos, expl, rng, n=3)


# =============================================================================================
# Tier 2: outliers and lines of fit
# =============================================================================================
def t2_outlier(rng, pos):
    n = pick(rng, (4, 5))
    m = pick(rng, (1, 2, 3, -1, -2, -3))
    x0 = rng.randint(1, 5)
    xs = list(range(x0, x0 + n))
    b = rng.randint(0, 20)
    line = [(x, m * x + b) for x in xs]
    k = rng.randrange(n)
    dev = pick(rng, (-1, 1)) * rng.randint(7, 12)
    out = (xs[k], line[k][1] + dev)
    points = list(line)
    points[k] = out
    if bad_points(points) or bad_line(m, b):
        return None
    xmax = max(p[0] for p in points)
    ymax = max(p[1] for p in points)
    others = [p for p in points if p != out]
    cands = []
    for p in points:
        if p[0] == xmax and p != out:
            cands.append(("LARGEST_X_OUTLIER", pt(p), p))
    for p in points:
        if p[1] == ymax and p != out:
            cands.append(("HIGHEST_Y_OUTLIER", pt(p), p))
    rest = list(others)
    rng.shuffle(rest)
    for p in rest:
        cands.append(("ANY_POINT", pt(p), p))
    head = "Points" if n == 5 or rng.random() < 0.5 else "Plot"
    prompt = f"{head} {pts(points)}. Outlier?"
    expl = f"The others follow one line. {pt(out)} is far off that pattern."
    return make_item(2, prompt, (pt(out), out), cands, pos, expl, rng, n=4)


def t2_line(rng, pos):
    m = pick(rng, (1, 2, 3, 4, 5, -1, -2, -3))
    b = rng.randint(1, 15)
    x0 = pick(rng, (1, 2))
    points = [(x0 + i, m * (x0 + i) + b) for i in range(3)]
    if bad_points(points) or bad_line(m, b):
        return None
    cands = [(lab, line_text(*v), v) for lab, v in line_wrongs(m, b, points[0][0], points[0][1])]
    fill = [(line_text(m, b + d), (m, b + d)) for d in (1, -1, 2) if b + d > 0]
    fill += [(line_text(m + 1 if m > 0 else m - 1, b), (m + 1 if m > 0 else m - 1, b))]
    head = pick(rng, ("Which line fits", "Line of fit for"))
    prompt = f"{head} {pts(points)}?"
    verb = "rises" if m > 0 else "falls"
    expl = f"y {verb} {abs(m)} for each step in x, and at x = 0 it is {b}: {line_text(m, b)}."
    return make_item(2, prompt, (line_text(m, b), (m, b)), cands, pos, expl, rng, n=4, fill=fill)


# =============================================================================================
# Tier 3: use a line of fit
# =============================================================================================
# (name, rule template for y, question slope, question start, question predict, prefix, suffix)
CONTEXTS3 = [
    ("Cost y = {m}x + {b} (x hours)", "Cost per hour?", "Cost at 0 hours?", "Cost for {x} hours?", "$", ""),
    ("Height y = {m}x + {b} (x weeks)", "Growth per week?", "Height at the start?", "Height at week {x}?", "", " cm"),
    ("Savings y = {m}x + {b} (x weeks)", "Saved per week?", "Savings at the start?", "Savings after {x} weeks?", "$", ""),
    ("Miles y = {m}x + {b} (x hours)", "Miles per hour?", "Miles at the start?", "Miles after {x} hours?", "", " mi"),
]


def _fmt3(v, pre, suf):
    return f"{pre}{num(v)}{suf}" if v >= 0 else f"{M}{pre}{-v}{suf}"


def t3_predict(rng, pos, negative):
    if negative:
        m = rng.randint(-5, -1)
        x = rng.randint(2, 8)
        b = rng.randint(10, 20)
    else:
        m = rng.randint(1, 10)
        x = rng.randint(2, 10)
        b = rng.randint(1, 20)
    if bad_predict(m, b, x):
        return None
    p = m * x + b
    mt = num(m) if abs(m) != 1 else ("" if m == 1 else M)
    prompt = f"Line of fit y = {mt}x + {b}. Predict y at x = {x}."
    cands = [(lab, num(v), v) for lab, v in predict_wrongs(m, b, x)]
    expl = f"y = {num(m)} × {x} + {b} = {num(m * x)} + {b} = {num(p)}."
    return make_item(3, prompt, (num(p), p), cands, pos, expl, rng, n=4, fill=int_fill(p, 0 if p >= 0 else -99))


def t3_context(rng, pos, what):
    head, qs, qb, qp, pre, suf = pick(rng, CONTEXTS3)
    m = rng.randint(2, 10)
    b = rng.randint(1, 20)
    x = rng.randint(2, 10)
    if what == "predict":
        if bad_predict(m, b, x):
            return None
    elif m == b or bad_line(m, b):
        return None
    rule = head.format(m=m, b=b)
    if what == "slope":
        prompt, ans = f"{rule}. {qs}", m
        cands = slope_wrongs(m, b)
        expl = f"In y = mx + b the slope is the number with x: {m}."
        fill = [(v, w) for v, w in ((m + 1, 1), (m - 1, 1), (m + 2, 1), (m - 2, 1)) if v > 0]
    elif what == "start":
        prompt, ans = f"{rule}. {qb}", b
        cands = start_wrongs(m, b)
        expl = f"The start is y when x = 0: {m} × 0 + {b} = {b}."
        fill = [(v, w) for v, w in ((b + 1, 1), (b - 1, 1), (b + 2, 1), (b - 2, 1)) if v > 0]
    else:
        p = m * x + b
        prompt, ans = f"{rule}. {qp.format(x=x)}", p
        cands = predict_wrongs(m, b, x)
        expl = f"{m} × {x} + {b} = {m * x} + {b} = {p}."
        fill = [(p + d, 1) for d in (1, -1, 2, -2, 3)]
    fill = [(_fmt3(v, pre, suf), v) for v, _ in fill]
    cands = [(lab, _fmt3(v, pre, suf), v) for lab, v in cands]
    return make_item(3, prompt, (_fmt3(ans, pre, suf), ans), cands, pos, expl, rng, n=4, fill=fill)


def t3_inverse(rng, pos):
    m = rng.randint(2, 10)
    b = rng.randint(1, 20)
    x = rng.randint(2, 10)
    y = m * x + b
    if bad_predict(m, b, x):
        return None
    prompt = f"Line of fit y = {m}x + {b}. For which x is y = {y}?"
    cands = [(lab, num(v), v) for lab, v in inverse_wrongs(m, b, y)]
    expl = f"{y} {M} {b} = {y - b}, then {y - b} ÷ {m} = {x}."
    return make_item(3, prompt, (num(x), x), cands, pos, expl, rng, n=4, fill=int_fill(x, 1))


# =============================================================================================
# Tier 4: two-way table counts
# =============================================================================================
TABLES = [
    ("Boys", "Girls", "yes", "no"), ("Boys", "Girls", "bus", "walk"), ("Kids", "Adults", "pizza", "tacos"),
    ("Cats", "Dogs", "big", "small"), ("Boys", "Girls", "pass", "fail"), ("Kids", "Adults", "tea", "juice"),
]


def _table(rng):
    cells = [rng.randint(2, 14) for _ in range(4)]
    return (cells, rng.choice(TABLES)) if not bad_table(cells) else None


def t4_total(rng, pos, by):
    got = _table(rng)
    if got is None:
        return None
    (a1, a2, b1, b2), (A, B, X, Y) = got
    head = f"{A}: {cnt(a1, X)}, {cnt(a2, Y)}. {B}: {cnt(b1, X)}, {cnt(b2, Y)}."
    grand = a1 + a2 + b1 + b2
    if by == "col":  # total of the first column
        prompt, ans = f"{head} Total {X}?", a1 + b1
        cands = col_wrongs(a1, a2, b1, b2)
        expl = f"{X}: {a1} + {b1} = {ans}."
    elif by == "row":
        group = A if rng.random() < 0.5 else B
        a, c, o1, o2 = (a1, a2, b1, b2) if group == A else (b1, b2, a1, a2)
        ans = a + c
        prompt = f"{head} Total {group.lower()}?"
        cands = row_wrongs(a, c, o1, o2)
        expl = f"{group}: {a} + {c} = {ans}."
    else:
        prompt, ans = f"{head} How many in all?", grand
        cands = grand_wrongs(a1, a2, b1, b2, rng.choice((a1, a2, b1, b2)))
        expl = f"{a1} + {a2} + {b1} + {b2} = {grand}."
    cands = [(lab, num(v), v) for lab, v in cands]
    return make_item(4, prompt, (num(ans), ans), cands, pos, expl, rng, n=4, fill=int_fill(ans, 1))


ONLY = [("play sports", "play music", "Sports only"), ("have a dog", "have a cat", "Dog only"),
        ("like pizza", "like tacos", "Pizza only"), ("take art", "take band", "Art only"),
        ("ride a bus", "ride a bike", "Bus only")]


def t4_only(rng, pos):
    p1, p2, lab = pick(rng, ONLY)
    n = rng.randint(8, 20)
    k = rng.randint(2, n - 3)
    prompt = f"{n} kids {p1}; {k} of them {p2}. {lab}?"
    ans = n - k
    cands = [(l, num(v), v) for l, v in only_wrongs(n, k)]
    expl = f"The {k} who do both are inside the {n}. Only: {n} {M} {k} = {ans}."
    return make_item(4, prompt, (num(ans), ans), cands, pos, expl, rng, n=4, fill=int_fill(ans, 1))


COLNOUN = {"yes": "Yes votes", "bus": "Bus riders", "pizza": "Pizza fans", "big": "Big pets", "pass": "Passers",
           "tea": "Tea drinkers"}


def t4_missing(rng, pos):
    A, B, X, _ = pick(rng, TABLES)
    t = rng.randint(8, 20)
    a = rng.randint(2, t - 3)
    ans = t - a
    prompt = f"{COLNOUN[X]}: {t} in all, {a} are {A.lower()}. How many are {B.lower()}?"
    cands = [(l, num(v), v) for l, v in missing_wrongs(t, a)]
    expl = f"The two groups make {t}. {t} {M} {a} = {ans}."
    return make_item(4, prompt, (num(ans), ans), cands, pos, expl, rng, n=4, fill=int_fill(ans, 1))


# =============================================================================================
# Tier 5: relative frequency
# =============================================================================================
def _fr(n, d):
    return Fraction(n, d)


def _frac_fill(correct: Fraction, a: int, tot: int):
    out = []
    for n, d in ((a + 1, tot), (a - 1, tot), (a, tot + 1), (a, tot - 1), (a + 2, tot)):
        if d > 0 and 0 < n < d:
            f = Fraction(n, d)
            out.append((frac_text(f), f))
    return out


def t5_fraction(rng, pos, clause):
    A, _, X, Y = pick(rng, TABLES)
    verb = {"yes": "saying yes", "bus": "taking the bus", "pizza": "picking pizza",
            "big": "that are big", "pass": "who passed", "tea": "picking tea"}[X]
    tot = pick(rng, (4, 5, 6, 8, 9, 10, 12, 15, 16, 20))
    a = rng.randint(1, tot - 1)
    b = tot - a
    f = _fr(a, tot)
    if a == b or bad_freq(f, tot):
        return None
    extra, tag = "", None
    if clause == "grand":
        N = tot + rng.randint(4, 20)
        extra, tag = f" {N} in all.", ("GRAND_DENOMINATOR", N)
    elif clause == "col":
        N = a + rng.randint(2, 14)
        extra, tag = f" All: {cnt(N, X)}.", ("WRONG_TOTAL", N)
    cands = frac_wrongs(a, b, tag)
    prompt = f"{A}: {cnt(a, X)}, {cnt(b, Y)}.{extra} Fraction of {A.lower()} {verb}?"
    cands = [(l, frac_text(v), v) for l, v in cands]
    expl = f"{a} of {tot} {A.lower()}: {a}/{tot}" + (f" = {frac_text(f)}." if f.denominator != tot else ".")
    return make_item(5, prompt, (frac_text(f), f), cands, pos, expl, rng, n=4, fill=_frac_fill(f, a, tot))


def t5_percent(rng, pos):
    A, _, X, Y = pick(rng, TABLES)
    verb = {"yes": "saying yes", "bus": "taking the bus", "pizza": "picking pizza",
            "big": "that are big", "pass": "who passed", "tea": "picking tea"}[X]
    tot = pick(rng, (4, 5, 8, 10, 20))
    a = rng.randint(1, tot - 1)
    p = 100 * a // tot
    if 100 * a % tot or p not in PERCENTS or a * 2 == tot:
        return None
    b = tot - a
    prompt = f"{A}: {cnt(a, X)}, {cnt(b, Y)}. Percent of {A.lower()} {verb}?"
    cands = [(l, f"{v}%", v) for l, v in percent_wrongs(a, p)]
    expl = f"{a} out of {tot} = {a}/{tot} = {p}/100 = {p}%."
    fill = [(f"{v}%", v) for v in (p + 10, p - 10, p + 20, p - 20, p + 5, p - 5) if 0 < v < 100]
    return make_item(5, prompt, (f"{p}%", p), cands, pos, expl, rng, n=4, fill=fill)


COLS = [("Yes votes", "boys", "girls"), ("Bus riders", "boys", "girls"), ("Pizza fans", "kids", "adults"),
        ("Cat owners", "boys", "girls"), ("Tea drinkers", "kids", "adults"), ("Winners", "boys", "girls")]


def t5_column(rng, pos):
    head, A, B = pick(rng, COLS)
    tot = pick(rng, (4, 5, 6, 8, 9, 10, 12, 15, 16, 20))
    a = rng.randint(1, tot - 1)
    b = tot - a
    f = _fr(a, tot)
    if a == b or bad_freq(f, tot):
        return None
    prompt = f"{head}: {cnt(a, A)}, {cnt(b, B)}. Fraction that are {A}?"
    cands = [(l, frac_text(v), v) for l, v in frac_wrongs(a, b)]
    expl = f"{a} {A} out of {tot} in all: {a}/{tot}" + (f" = {frac_text(f)}." if f.denominator != tot else ".")
    return make_item(5, prompt, (frac_text(f), f), cands, pos, expl, rng, n=4, fill=_frac_fill(f, a, tot))


RATES = [(1, 4), (1, 3), (1, 2), (2, 3), (3, 4), (1, 5), (2, 5), (3, 5), (4, 5), (5, 6), (1, 6)]
VERBS = ["say yes", "pass", "win", "walk", "vote yes", "like it"]
PAIRS = [("Boys", "Girls"), ("Teens", "Parents"), ("Kids", "Adults"), ("Men", "Women")]


def t5_compare(rng, pos, tie):
    r1 = pick(rng, RATES)
    r2 = r1 if tie else pick(rng, RATES)
    if not tie and Fraction(*r1) == Fraction(*r2):
        return None
    k1, k2 = rng.randint(1, 4), rng.randint(1, 4)
    a, n = r1[0] * k1, r1[1] * k1
    c, m = r2[0] * k2, r2[1] * k2
    if max(n, m) > 20 or a == c:
        return None
    f1, f2 = _fr(a, n), _fr(c, m)
    # the larger COUNT must not belong to the higher rate (that is the trap), except on ties
    if not tie and ((a > c) == (f1 > f2) or abs(f1 - f2) < Fraction(3, 20)):
        return None
    A, B = pick(rng, PAIRS)
    verb = pick(rng, VERBS)
    prompt = f"{A}: {a} of {n} {verb}. {B}: {c} of {m}. Who is more likely?"
    ans = "Same" if tie else (A if f1 > f2 else B)
    big = A if a > c else B
    words = (A, B, "Same")
    cands = []
    for w in words:
        if w == ans:
            continue
        cands.append(("COUNT_NOT_RATE" if w == big else "NOT_COMPARED", w, w))
    cands.sort(key=lambda t: t[0] != "COUNT_NOT_RATE")
    def _s(x, y, f):
        return f"{x}/{y}" + (f" = {frac_text(f)}" if f.denominator != y else "")

    expl = f"{A} {_s(a, n, f1)}, {B} {_s(c, m, f2)}. " + ("Equal rates." if tie else f"{ans} has the greater share.")
    return make_item(5, prompt, (ans, ans), cands, pos, expl, rng, n=3)


# =============================================================================================
# Plans
# =============================================================================================
def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def _plan(tier: int, count: int, rng):
    """[(builder, n_choices)] for one tier, shuffled."""
    k = []
    if tier == 1:
        k += [(lambda r, p: t1_context(r, p, 1), 3)] * 10
        k += [(lambda r, p: t1_context(r, p, -1), 3)] * 10
        k += [(t1_none_context, 3)] * 6
        k += [(lambda r, p: t1_list(r, p, 0), 3)] * 5
        k += [(lambda r, p: t1_list(r, p, 1), 3)] * 5
        k += [(lambda r, p: t1_list(r, p, 2), 3)] * 4
    elif tier == 2:
        k += [(t2_outlier, 4)] * 20 + [(t2_line, 4)] * 20
    elif tier == 3:
        k += [(lambda r, p: t3_predict(r, p, False), 4)] * 8
        k += [(lambda r, p: t3_predict(r, p, True), 4)] * 4
        k += [(lambda r, p: t3_context(r, p, "predict"), 4)] * 8
        k += [(lambda r, p: t3_context(r, p, "slope"), 4)] * 7
        k += [(lambda r, p: t3_context(r, p, "start"), 4)] * 7
        k += [(t3_inverse, 4)] * 6
    elif tier == 4:
        k += [(lambda r, p: t4_total(r, p, "col"), 4)] * 9
        k += [(lambda r, p: t4_total(r, p, "row"), 4)] * 9
        k += [(lambda r, p: t4_total(r, p, "all"), 4)] * 6
        k += [(t4_only, 4)] * 8
        k += [(t4_missing, 4)] * 8
    else:
        k += [(lambda r, p: t5_fraction(r, p, ""), 4)] * 7
        k += [(lambda r, p: t5_fraction(r, p, "grand"), 4)] * 5
        k += [(lambda r, p: t5_fraction(r, p, "col"), 4)] * 5
        k += [(t5_percent, 4)] * 6
        k += [(t5_column, 4)] * 5
        k += [(lambda r, p: t5_compare(r, p, False), 3)] * 9
        k += [(lambda r, p: t5_compare(r, p, True), 3)] * 3
    assert len(k) == count, (tier, len(k), count)
    rng.shuffle(k)
    return k


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000):
    kinds = _plan(tier, count, rng)
    pos_by_n = {}
    for n in sorted({k for _, k in kinds}):
        pos_by_n[n] = _balanced(sum(1 for _, k in kinds if k == n), n, rng)
    used = {n: 0 for n in pos_by_n}
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        build, n = kinds[len(items)]
        item = build(rng, pos_by_n[n][used[n]])
        if item is None or item["prompt"] in prompts:
            continue
        for s in [item["prompt"], item["explanation"], *item["choices"]]:
            assert all(32 <= ord(ch) < 127 or ch in ALLOWED_EXTRA for ch in s), s
        prompts.add(item["prompt"])
        used[n] += 1
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    assert manifest["items_per_tier"] == 40
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], manifest["items_per_tier"], rng))
    return items
