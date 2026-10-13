"""Procedural generator for the proportional-relationships cartridge (fnm-cart/1, grade 7).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Each tier has a few prompt *templates*. A builder picks numbers inside the manifest's ``bounds`` and
  renders the prompt text; ``analyze(prompt)`` then re-reads that text with regexes and returns the
  correct choice, every modelled misconception's wrong choice and the explanation. The text a student
  sees is the only thing ever solved. (Choices that cannot be read from the prompt, such as the
  "other point" of T2, are a pure function of the numbers in the prompt.)
* A choice is ``(display, key)``. The key is the choice's VALUE: a Fraction for numbers, prices and
  areas, ``("pt", x, y)`` for a point, ``("eq", m, b)`` for the line ``dependent = m * independent + b``
  (so ``x = 4y`` and ``y = x/4`` are the same key), ``("by", a, b)`` for an unordered ``a by b`` size.
  No two choices of an item share a key: the player never faces two right doors.
* Wrong choices: misconception values first (the first label to produce a value keeps it; when more than
  three are distinct, three are drawn at random); ``ARITH`` only fills up to 4 choices and never
  equals ANY misconception value of that prompt.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from fractions import Fraction

# ---------------------------------------------------------------------------------------------
# Display / choice constructors
# ---------------------------------------------------------------------------------------------
def frac(v) -> str:
    """Whole number, a/b, or mixed w a/b (simplest form)."""
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    w, r = divmod(v.numerator, v.denominator)
    return f"{w} {r}/{v.denominator}" if w else f"{r}/{v.denominator}"


def num(v):
    v = Fraction(v)
    return (frac(v), v)


def cash(v):
    v = Fraction(v)
    return ("$" + frac(v), v)


def area(v, unit):
    v = Fraction(v)
    return (f"{frac(v)} sq {unit}", v)


def pt(x, y):
    return (f"({x}, {y})", ("pt", x, y))


def by(a, b):
    return (f"{a} by {b}", ("by",) + tuple(sorted((a, b))))


def txt(s):
    return (s, ("txt", s))


def E(lhs, rvar, m, b, dep, ind):
    """The equation ``lhs = m rvar + b`` as a choice. The key is the line dep = m' ind + b'."""
    m, b = Fraction(m), Fraction(b)
    assert m.denominator == 1 and b.denominator == 1 and m > 0 and b >= 0, (m, b)
    mi, bi = int(m), int(b)
    text = f"{lhs} = {rvar if mi == 1 else str(mi) + rvar}" + (f" + {bi}" if bi else "")
    if lhs == dep:
        key = ("eq", m, b)
    else:  # ind = m dep + b  ->  dep = (ind - b) / m
        key = ("eq", 1 / m, -b / m)
    return (text, key)


def INV(lhs, k, rvar):
    """``lhs = k/rvar``: the rate written over the variable."""
    return (f"{lhs} = {k}/{rvar}", ("inv", int(k)))


# ---------------------------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------------------------
DENOMS = (2, 3, 4, 5, 6, 8, 10)
FRACS = [(a, b) for b in DENOMS for a in range(1, b) if math.gcd(a, b) == 1]

IN_CONTEXTS = [  # (agent phrase, amount unit, time unit, question noun)
    ("A snail crawls", "ft", "minute", "Feet"),
    ("A hiker walks", "mile", "hour", "Miles"),
    ("A tap fills", "gal", "minute", "Gallons"),
    ("A plant grows", "inch", "day", "Inches"),
    ("A painter covers", "wall", "hour", "Walls"),
    ("A cyclist rides", "mile", "hour", "Miles"),
    ("A hose adds", "gal", "minute", "Gallons"),
]
MAKES_CONTEXTS = [  # (material, unit, verb, thing made, question noun)
    ("flour", "cup", "makes", "batch", "Cups"),
    ("sugar", "cup", "makes", "batch", "Cups"),
    ("paint", "gal", "covers", "wall", "Gallons"),
    ("dough", "lb", "makes", "pizza", "Pounds"),
    ("yarn", "yd", "makes", "scarf", "Yards"),
    ("wood", "ft", "builds", "shelf", "Feet"),
]
FOODS = ["nuts", "cheese", "grapes", "beans", "fudge", "ham"]
TIMES_NOUNS = [("Rope", "rope"), ("Pipe", "pipe"), ("Wire", "wire"), ("Bar", "bar"), ("Tube", "tube")]
TIMES_UNITS = ("ft", "yd")

PAIRS2 = [("y", "x"), ("d", "t"), ("c", "n"), ("p", "h"), ("w", "d")]  # (dependent, independent)
EQ_PHRASES = ("Which shows {Y} proportional to {X}, k = {k}?",
              "Which equation has {Y} proportional to {X} with k = {k}?")
XS_PROP = [(2, 4, 6), (3, 6, 9), (2, 3, 4), (3, 4, 5), (4, 5, 6), (2, 5, 8)]
XS_ADD = [(1, 2, 3), (1, 2, 4), (1, 3, 5), (1, 2, 5), (1, 3, 4), (2, 3, 4), (2, 4, 6)]
XS_K = [(2, 4, 6), (3, 6, 9), (2, 3, 4), (3, 4, 5), (4, 5, 6), (2, 5, 8)]

ITEMS_T3 = ["pens", "tickets", "cans", "books", "tacos"]
WORD_IN = [  # (things, units, dependent, independent)
    ("miles", "hours", "d", "h"),
    ("pages", "days", "p", "d"),
    ("cards", "packs", "c", "p"),
    ("goals", "games", "g", "n"),
    ("words", "minutes", "w", "m"),
]

ITEMS_T4 = [("pens", "p"), ("tickets", "n"), ("cans", "n"), ("books", "b"), ("tacos", "t")]
TOTAL_IN = [  # (things, units, Things, dependent, independent)
    ("miles", "hours", "Miles", "d", "h"),
    ("pages", "days", "Pages", "p", "d"),
    ("laps", "minutes", "Laps", "n", "m"),
    ("goals", "games", "Goals", "g", "n"),
    ("pizzas", "hours", "Pizzas", "p", "h"),
    ("words", "minutes", "Words", "w", "m"),
]
RATE_CONTEXTS = [  # (agent phrase, unit, per, Things, dependent, independent, pers)
    ("A tap fills", "gal", "minute", "Gallons", "g", "m", "minutes"),
    ("A jogger runs", "miles", "hour", "Miles", "d", "h", "hours"),
    ("A printer prints", "pages", "minute", "Pages", "p", "m", "minutes"),
    ("A worker packs", "boxes", "hour", "Boxes", "b", "h", "hours"),
    ("A plant grows", "inches", "week", "Inches", "g", "w", "weeks"),
    ("A snail crawls", "feet", "hour", "Feet", "f", "h", "hours"),
    ("A baker makes", "rolls", "hour", "Rolls", "r", "h", "hours"),
]
EACH_CONTEXTS = [  # (Things, things, independent)
    ("Tickets", "tickets", "n"), ("Pens", "pens", "p"), ("Books", "books", "b"),
    ("Cans", "cans", "n"), ("Tacos", "tacos", "t"),
]
CONVS = [  # (big word, big plural, small unit, Smalls, factor, dependent, independent)
    ("yard", "yards", "ft", "Feet", 3, "f", "y"),
    ("gallon", "gallons", "qt", "Quarts", 4, "q", "g"),
    ("quart", "quarts", "pt", "Pints", 2, "p", "q"),
    ("pint", "pints", "cups", "Cups", 2, "c", "p"),
    ("week", "weeks", "days", "Days", 7, "d", "w"),
    ("dollar", "dollars", "dimes", "Dimes", 10, "d", "n"),
]

UNITS5 = [  # (lead, drawn unit, real unit, real thing, view)
    ("Map scale", "cm", "km", "road", "map"),
    ("Map scale", "in", "mi", "trail", "map"),
    ("Plan scale", "cm", "m", "wall", "plan"),
    ("Plan scale", "in", "ft", "wall", "plan"),
]
ROOM_UNITS = [("cm", "m"), ("in", "ft")]

# ---------------------------------------------------------------------------------------------
# Regexes (one per template) -- shared by analyze() only
# ---------------------------------------------------------------------------------------------
FR = r"(\d+/\d+)"
RE = {
    "t1_in": re.compile(rf"^(A [\w ]+?) {FR} (\w+) in {FR} (\w+)\. (\w+) per (\w+)\?$"),
    "t1_makes": re.compile(rf"^{FR} (\w+) of (\w+) (\w+) {FR} (\w+)\. (\w+) for 1 (\w+)\?$"),
    "t1_price": re.compile(rf"^{FR} lb of (\w+) costs \$(\d+)\. Cost per lb\?$"),
    "t1_times": re.compile(rf"^(\w+) A is {FR} (\w+), (\w+) B is {FR} (\w+)\. A is how many times B\?$"),
    "t2_point": re.compile(r"^\((\d+), (\d+)\) is on y = kx\. Which point is also on it\?$"),
    "t2_eq": re.compile(r"^Which (?:shows|equation has) (\w) proportional to (\w)(?:,| with) k = (\d+)\?$"),
    "t2_table": re.compile(r"^x: ([\d, ]+)\. y: ([\d, ]+)\. Which equation fits\?$"),
    "t3_eq": re.compile(r"^(\w) = (\d+)(\w)\. Constant of proportionality of \1 to \3\?$"),
    "t3_point": re.compile(r"^\((\d+), (\d+)\) is on y = kx\. What is k\?$"),
    "t3_cost": re.compile(r"^(\d+) (\w+) cost \$(\d+)\. In (\w) = k(\w), what is k\?$"),
    "t3_in": re.compile(r"^(\d+) (\w+) in (\d+) (\w+)\. In (\w) = k(\w), what is k\?$"),
    "t3_earns": re.compile(r"^Earns \$(\d+) in (\d+) hours\. In (\w) = k(\w), what is k\?$"),
    "t3_table": re.compile(r"^x: ([\d, ]+)\. y: ([\d, ]+)\. In y = kx, what is k\?$"),
    "t4_cost": re.compile(r"^(\d+) (\w+) cost \$(\d+)\. Cost (\w) for (\w) (\w+)\?$"),
    "t4_in": re.compile(r"^(\d+) (\w+) in (\d+) (\w+)\. (\w+) (\w) in (\w) (\w+)\?$"),
    "t4_rate": re.compile(r"^(A [\w ]+?) (\d+) (\w+) per (\w+)\. (\w+) (\w) in (\w) (\w+)\?$"),
    "t4_each": re.compile(r"^(\w+) cost \$(\d+) each\. Cost (\w) for (\w) (\w+)\?$"),
    "t4_conv_a": re.compile(r"^1 (\w+) = (\d+) (\w+)\. \w+ (\w) in (\w) \w+\?$"),
    "t4_conv_b": re.compile(r"^Each (\w+) is (\d+) (\w+)\. \w+ (\w) in (\w) \w+\?$"),
    "t4_conv_c": re.compile(r"^(\d+) (\w+) make 1 (\w+)\. \w+ (\w) in (\w) \w+\?$"),
    "t5_real": re.compile(r"^(Map scale|Plan scale) 1 (\w+) : (\d+) (\w+)\. (\d+) \2 is how many \4\?$"),
    "t5_draw": re.compile(r"^(Map scale|Plan scale) 1 (\w+) : (\d+) (\w+)\. A (\d+) \4 (\w+) is how many \2\?$"),
    "t5_area_real": re.compile(r"^Scale 1 (\w+) = (\d+) (\w+)\. A room is drawn (\d+) \1 by (\d+) \1\. Real area\?$"),
    "t5_area_draw": re.compile(r"^Scale 1 (\w+) = (\d+) (\w+)\. A room is (\d+) \3 by (\d+) \3\. Drawing area\?$"),
    "t5_find": re.compile(r"^(\d+) (\w+) on the (?:map|plan) is (\d+) (\w+)\. 1 \2 = \? \4$"),
    "t5_rect": re.compile(r"^(?:Scale a|Enlarge a) (\d+) by (\d+) rectangle (?:by|with scale factor) (\d+)\. "
                          r"New size\?$"),
    "t5_shrink": re.compile(r"^Divide each side of a (\d+) by (\d+) rectangle by (\d+)\. New size\?$"),
    "t5_factor": re.compile(r"^(?:Scale factor (\d+)\. Area is multiplied by what\?|"
                            r"Each side is (\d+) times as long\. Area is \? times as big\.)$"),
}


class NotMine(Exception):
    pass


@dataclass
class Analysis:
    kind: str
    correct: tuple
    wrong: list  # [(label, choice)] in priority order; may repeat values / equal the answer
    expl: str
    arith: object  # callable(rng) -> [choice]


def analyze(prompt: str) -> Analysis:
    """THE solver: reads the display text and returns the correct choice, every modelled wrong choice
    and the explanation."""
    for kind, rx in RE.items():
        m = rx.match(prompt)
        if m:
            return _SOLVERS[kind](kind, m)
    raise NotMine(prompt)


def numeric_arith(fmt, v):
    v = Fraction(v)

    def f(rng):
        deltas = [Fraction(1), Fraction(-1), Fraction(2), Fraction(-2)]
        rng.shuffle(deltas)
        far = [Fraction(3), Fraction(-3), Fraction(5), Fraction(-5)]
        rng.shuffle(far)
        return [fmt(v + d) for d in deltas + far if v + d > 0]
    return f


# --- T1 ----------------------------------------------------------------------------------------
def _flip(c, d):
    return str(d) if c == 1 else f"{d}/{c}"


def _div_expl(A: Fraction, B: Fraction, v: Fraction, tail: str) -> str:
    a, b, c, d = A.numerator, A.denominator, B.numerator, B.denominator
    pstr = f"{a * d}/{b * c}"
    s = f"{a}/{b} ÷ {c}/{d} = {a}/{b} × {_flip(c, d)} = {pstr}"
    if pstr != frac(v):
        s += f" = {frac(v)}"
    return s + tail


def _rate_wrong(A: Fraction, B: Fraction, fmt=num):
    a, b, c, d = A.numerator, A.denominator, B.numerator, B.denominator
    out = [("INVERTED", fmt(B / A)), ("MULTIPLIED", fmt(A * B))]
    flipped = Fraction(b * d, a * c)
    if flipped.denominator <= 6 and flipped <= 20:  # 5 5/9 or 33 1/3 is a giveaway, not a door
        out.append(("FLIPPED_BOTH", fmt(flipped)))
    return out + [("DROP_DENOMS", fmt(Fraction(a, c)))]


def _t1_in(kind, m):
    A, B, Q, u2 = Fraction(m[2]), Fraction(m[4]), m[6], m[5]
    v = A / B
    return Analysis(kind, num(v), _rate_wrong(A, B), _div_expl(A, B, v, f" {Q.lower()} per {u2}."),
                    numeric_arith(num, v))


def _t1_makes(kind, m):
    A, B, Q, thing = Fraction(m[1]), Fraction(m[5]), m[7], m[6]
    v = A / B
    return Analysis(kind, num(v), _rate_wrong(A, B), _div_expl(A, B, v, f" {Q.lower()} per {thing}."),
                    numeric_arith(num, v))


def _t1_price(kind, m):
    A, t = Fraction(m[1]), int(m[3])
    v = t / A
    flip = _flip(A.numerator, A.denominator)
    wrong = [("INVERTED", cash(A / t)), ("MULTIPLIED", cash(t * A)),
             ("DROP_DENOMS", cash(Fraction(t, A.numerator)))]
    return Analysis(kind, cash(v), wrong, f"${t} ÷ {A} = ${t} × {flip} = ${frac(v)} per lb.",
                    numeric_arith(cash, v))


def _t1_times(kind, m):
    A, B = Fraction(m[2]), Fraction(m[5])
    v = A / B
    wrong = [("INVERTED", num(B / A)), ("MULTIPLIED", num(A * B)),
             ("DIFFERENCE", num(abs(A - B))), ("DROP_DENOMS", num(Fraction(A.numerator, B.numerator)))]
    return Analysis(kind, num(v), wrong, _div_expl(A, B, v, " times as long."), numeric_arith(num, v))


# --- T2 ----------------------------------------------------------------------------------------
def _point_n(x0: int, k: int) -> int:
    """The x of the other point: a pure function of the prompt's numbers, 2..10, never x0."""
    n = 2 + (3 * x0 + 5 * k) % 9
    if n == x0:
        n = 2 + (n - 1) % 9
    return n


def _t2_point(kind, m):
    x0, y0 = int(m[1]), int(m[2])
    if y0 % x0:
        raise NotMine("k is not a whole number")
    k = y0 // x0
    n = _point_n(x0, k)
    wrong = [("ADDITIVE", pt(n, n + y0 - x0)), ("SWAPPED_XY", pt(k * n, n))]
    if (x0 * y0) % n == 0:  # x went down, y went UP by the same factor (or the reverse)
        wrong.append(("INVERSE", pt(n, x0 * y0 // n)))

    def arith(rng):
        ds = [1, -1, 2, -2, 3, -3]
        rng.shuffle(ds)
        return [pt(n, k * n + d) for d in ds if k * n + d > 0]
    expl = f"{y0} ÷ {x0} = {k}, so y = {k}x. At x = {n}: {k} × {n} = {k * n}. Point ({n}, {k * n})."
    return Analysis(kind, pt(n, k * n), wrong, expl, arith)


def _eq_arith(dep, ind, k):
    def f(rng):
        ms = [k + 1, k - 1, k + 2, k - 2]
        rng.shuffle(ms)
        return [E(dep, ind, mm, 0, dep, ind) for mm in ms if mm >= 2]
    return f


def _t2_eq(kind, m):
    Y, X, k = m[1], m[2], int(m[3])
    c = 1 + (k + ord(Y) + ord(X)) % 5
    wrong = [("ADDS_CONSTANT", E(Y, X, 1, k, Y, X)), ("HAS_START", E(Y, X, k, c, Y, X)),
             ("SWAPPED_XY", E(X, Y, k, 0, Y, X))]
    expl = f"Proportional means {Y} = k{X} with nothing added. With k = {k}: {Y} = {k}{X}."
    return Analysis(kind, E(Y, X, k, 0, Y, X), wrong, expl, _eq_arith(Y, X, k))


def _ints(s):
    return [int(v) for v in s.split(", ")]


def _t2_table(kind, m):
    xs, ys = _ints(m[1]), _ints(m[2])
    if len(xs) != len(ys) or len(xs) < 3:
        raise NotMine("table")
    x1, y1, x2, y2 = xs[0], ys[0], xs[1], ys[1]
    if len({Fraction(y, x) for x, y in zip(xs, ys)}) == 1:
        k = y1 // x1
        if y1 % x1:
            raise NotMine("k is not a whole number")
        wrong = [("ADDS_CONSTANT", E("y", "x", 1, y1 - x1, "y", "x")), ("Y_AS_K", E("y", "x", y1, 0, "y", "x")),
                 ("SWAPPED_XY", E("x", "y", k, 0, "y", "x"))]
        expl = f"y ÷ x is {k} every time ({y1} ÷ {x1} = {k}), so y = {k}x."
        return Analysis(kind, E("y", "x", k, 0, "y", "x"), wrong, expl, _eq_arith("y", "x", k))
    if len({y - x for x, y in zip(xs, ys)}) == 1:
        c = y1 - x1
        wrong = []
        if y1 % x1 == 0:
            wrong.append(("PROP_ASSUMED", E("y", "x", y1 // x1, 0, "y", "x")))
        wrong += [("PLUS_AS_TIMES", E("y", "x", c, 0, "y", "x")), ("SWAPPED_XY", E("x", "y", 1, c, "y", "x"))]
        expl = (f"{y1} ÷ {x1} and {y2} ÷ {x2} differ, so not proportional. "
                f"Each y is x + {c}: y = x + {c}.")
        return Analysis(kind, E("y", "x", 1, c, "y", "x"), wrong, expl, _eq_arith("y", "x", c + 1))
    raise NotMine("table is neither proportional nor additive")


# --- T3 ----------------------------------------------------------------------------------------
def _t3_eq(kind, m):
    Y, k, X = m[1], int(m[2]), m[3]
    wrong = [("INVERTED", num(Fraction(1, k))), ("KEEPS_VAR", txt(f"{k}{X}"))]
    return Analysis(kind, num(k), wrong, f"{Y} = k{X}, so k is the number with {X}: k = {k}.",
                    numeric_arith(num, k))


def _k_wrong(count, total, fmt):
    count, total = Fraction(count), Fraction(total)
    return [("INVERTED", fmt(count / total)), ("DIFFERENCE", fmt(total - count)),
            ("PRODUCT", fmt(count * total))]


def _t3_point(kind, m):
    x0, y0 = int(m[1]), int(m[2])
    if y0 % x0:
        raise NotMine("k is not a whole number")
    k = y0 // x0
    return Analysis(kind, num(k), _k_wrong(x0, y0, num), f"k = y ÷ x = {y0} ÷ {x0} = {k}.",
                    numeric_arith(num, k))


def _t3_cost(kind, m):
    n, t = int(m[1]), int(m[3])
    k = Fraction(t, n)
    return Analysis(kind, cash(k), _k_wrong(n, t, cash), f"k = {m[4]} ÷ {m[5]} = ${t} ÷ {n} = ${frac(k)}.",
                    numeric_arith(cash, k))


def _t3_in(kind, m):
    t, n = int(m[1]), int(m[3])
    k = Fraction(t, n)
    return Analysis(kind, num(k), _k_wrong(n, t, num), f"k = {m[5]} ÷ {m[6]} = {t} ÷ {n} = {frac(k)}.",
                    numeric_arith(num, k))


def _t3_earns(kind, m):
    t, n = int(m[1]), int(m[2])
    k = Fraction(t, n)
    return Analysis(kind, cash(k), _k_wrong(n, t, cash), f"k = {m[3]} ÷ {m[4]} = ${t} ÷ {n} = ${frac(k)}.",
                    numeric_arith(cash, k))


def _t3_table(kind, m):
    xs, ys = _ints(m[1]), _ints(m[2])
    if len({Fraction(y, x) for x, y in zip(xs, ys)}) != 1 or ys[0] % xs[0]:
        raise NotMine("table is not proportional with whole k")
    x1, y1, x2, y2 = xs[0], ys[0], xs[1], ys[1]
    k = y1 // x1
    wrong = [("INVERTED", num(Fraction(x1, y1))), ("Y_AS_K", num(y1)), ("DIFFERENCE", num(y1 - x1)),
             ("Y_STEP", num(y2 - y1))]
    return Analysis(kind, num(k), wrong, f"k = y ÷ x. {y1} ÷ {x1} = {k}; {y2} ÷ {x2} = {k}.",
                    numeric_arith(num, k))


# --- T4 ----------------------------------------------------------------------------------------
def _total_analysis(kind, n, t, dep, ind):
    if t % n:
        raise NotMine("rate is not whole")
    k = t // n
    wrong = [("SWAPPED_VARS", E(ind, dep, k, 0, dep, ind)), ("TOTAL_AS_RATE", E(dep, ind, t, 0, dep, ind)),
             ("COUNT_AS_RATE", E(dep, ind, n, 0, dep, ind)), ("ADDS_CONSTANT", E(dep, ind, 1, t - n, dep, ind))]
    return Analysis(kind, E(dep, ind, k, 0, dep, ind), wrong, f"{t} ÷ {n} = {k} for 1, so {dep} = {k}{ind}.",
                    _eq_arith(dep, ind, k))


def _t4_cost(kind, m):
    return _total_analysis(kind, int(m[1]), int(m[3]), m[4], m[5])


def _t4_in(kind, m):
    return _total_analysis(kind, int(m[3]), int(m[1]), m[6], m[7])


def _rate_analysis(kind, k, dep, ind, expl):
    wrong = [("SWAPPED_VARS", E(ind, dep, k, 0, dep, ind)), ("ADDS_CONSTANT", E(dep, ind, 1, k, dep, ind)),
             ("DIVIDES", INV(dep, k, ind))]
    return Analysis(kind, E(dep, ind, k, 0, dep, ind), wrong, expl, _eq_arith(dep, ind, k))


def _t4_rate(kind, m):
    k, per, dep, ind = int(m[2]), m[4], m[6], m[7]
    return _rate_analysis(kind, k, dep, ind, f"{k} {m[3]} each {per}, so {dep} = {k}{ind}.")


def _t4_each(kind, m):
    k, dep, ind = int(m[2]), m[3], m[4]
    return _rate_analysis(kind, k, dep, ind, f"Each one costs ${k}, so {dep} = {k}{ind}.")


def _t4_conv(kind, m):
    if kind == "t4_conv_c":
        k, small, big = int(m[1]), m[2], m[3]
    else:
        big, k, small = m[1], int(m[2]), m[3]
    dep, ind = m[4], m[5]
    return _rate_analysis(kind, k, dep, ind, f"1 {big} = {k} {small}, so {dep} = {k}{ind}.")


# --- T5 ----------------------------------------------------------------------------------------
def _t5_real(kind, m):
    du, k, au, n = m[2], int(m[3]), m[4], int(m[5])
    wrong = [("SCALED_DOWN", num(Fraction(n, k))), ("FACTOR_ONLY", num(k)), ("ADDITIVE", num(n + k))]
    return Analysis(kind, num(n * k), wrong, f"Each {du} is {k} {au}: {n} × {k} = {n * k} {au}.",
                    numeric_arith(num, n * k))


def _t5_draw(kind, m):
    du, k, au, real = m[2], int(m[3]), m[4], int(m[5])
    if real % k:
        raise NotMine("not a multiple")
    n = real // k
    wrong = [("WRONG_WAY", num(real * k)), ("FACTOR_ONLY", num(k)), ("ADDITIVE", num(real - k))]
    return Analysis(kind, num(n), wrong, f"Each {du} is {k} {au}: {real} ÷ {k} = {n} {du}.",
                    numeric_arith(num, n))


def _t5_area_real(kind, m):
    du, k, au, a, b = m[1], int(m[2]), m[3], int(m[4]), int(m[5])
    A, B = a * k, b * k
    wrong = [("DRAWING_AREA", area(a * b, au)), ("LINEAR_AREA", area(a * b * k, au)),
             ("ADDITIVE", area((a + k) * (b + k), au))]
    expl = f"Sides: {a} × {k} = {A} {au}, {b} × {k} = {B} {au}. Area {A} × {B} = {A * B} sq {au}."
    return Analysis(kind, area(A * B, au), wrong, expl, numeric_arith(lambda v: area(v, au), A * B))


def _t5_area_draw(kind, m):
    du, k, au, A, B = m[1], int(m[2]), m[3], int(m[4]), int(m[5])
    if A % k or B % k:
        raise NotMine("not multiples")
    a, b = A // k, B // k
    wrong = [("ACTUAL_AREA", area(A * B, du)), ("LINEAR_AREA", area(A * B // k, du))]
    expl = f"Sides: {A} ÷ {k} = {a} {du}, {B} ÷ {k} = {b} {du}. Area {a} × {b} = {a * b} sq {du}."
    return Analysis(kind, area(a * b, du), wrong, expl, numeric_arith(lambda v: area(v, du), a * b))


def _t5_find(kind, m):
    n, du, t, au = int(m[1]), m[2], int(m[3]), m[4]
    if t % n:
        raise NotMine("scale not whole")
    k = t // n
    wrong = [("INVERTED", num(Fraction(n, t))), ("ADDITIVE", num(t - n)), ("ACTUAL_AS_SCALE", num(t))]
    return Analysis(kind, num(k), wrong, f"{t} ÷ {n} = {k}, so 1 {du} = {k} {au}.", numeric_arith(num, k))


def _t5_rect(kind, m):
    a, b, k = int(m[1]), int(m[2]), int(m[3])
    wrong = [("ADDITIVE", by(a + k, b + k)), ("ONE_SIDE", by(a * k, b)), ("ONE_SIDE", by(a, b * k))]

    def arith(rng):
        ds = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        rng.shuffle(ds)
        return [by(a * k + da, b * k + db) for da, db in ds if a * k + da > 0 and b * k + db > 0]
    expl = f"Multiply both sides by {k}: {a} × {k} = {a * k}, {b} × {k} = {b * k}."
    return Analysis(kind, by(a * k, b * k), wrong, expl, arith)


def _t5_shrink(kind, m):
    A, B, k = int(m[1]), int(m[2]), int(m[3])
    if A % k or B % k:
        raise NotMine("not multiples")
    a, b = A // k, B // k
    wrong = [("ADDITIVE", by(A - k, B - k)), ("ONE_SIDE", by(a, B)), ("ONE_SIDE", by(A, b))]

    def arith(rng):
        ds = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        rng.shuffle(ds)
        return [by(a + da, b + db) for da, db in ds if a + da > 0 and b + db > 0]
    expl = f"Divide both sides by {k}: {A} ÷ {k} = {a}, {B} ÷ {k} = {b}."
    return Analysis(kind, by(a, b), wrong, expl, arith)


def _t5_factor(kind, m):
    k = int(m[1] or m[2])
    wrong = [("LINEAR_AREA", num(k)), ("ADDED_SIDES", num(2 * k)), ("CUBED", num(k ** 3))]
    return Analysis(kind, num(k * k), wrong, f"Area multiplies both sides: {k} × {k} = {k * k}.",
                    numeric_arith(num, k * k))


_SOLVERS = {
    "t1_in": _t1_in, "t1_makes": _t1_makes, "t1_price": _t1_price, "t1_times": _t1_times,
    "t2_point": _t2_point, "t2_eq": _t2_eq, "t2_table": _t2_table,
    "t3_eq": _t3_eq, "t3_point": _t3_point, "t3_cost": _t3_cost, "t3_in": _t3_in, "t3_earns": _t3_earns,
    "t3_table": _t3_table,
    "t4_cost": _t4_cost, "t4_in": _t4_in, "t4_rate": _t4_rate, "t4_each": _t4_each,
    "t4_conv_a": _t4_conv, "t4_conv_b": _t4_conv, "t4_conv_c": _t4_conv,
    "t5_real": _t5_real, "t5_draw": _t5_draw, "t5_area_real": _t5_area_real, "t5_area_draw": _t5_area_draw,
    "t5_find": _t5_find, "t5_rect": _t5_rect, "t5_shrink": _t5_shrink, "t5_factor": _t5_factor,
}


# ---------------------------------------------------------------------------------------------
# Distractor assembly
# ---------------------------------------------------------------------------------------------
def _usable(choice) -> bool:
    disp, key = choice
    if len(disp) > 14:
        return False
    if isinstance(key, Fraction):
        return 0 < key <= 999
    return True


def misconception_choices(prompt: str):
    """[(label, choice)] distinct in value, none equal to the answer, all displayable."""
    a = analyze(prompt)
    seen = {a.correct[1]}
    out = []
    for label, ch in a.wrong:
        if ch[1] in seen or not _usable(ch):
            continue
        seen.add(ch[1])
        out.append((label, ch))
    return out


def make_item(prompt: str, tier: int, answer_pos: int, rng: random.Random):
    if len(prompt) > 60:
        return None
    a = analyze(prompt)
    if len(a.expl) > 160 or len(a.correct[0]) > 14:
        return None
    wrong = misconception_choices(prompt)
    if not wrong:
        return None
    if len(wrong) > 3:
        keep = sorted(rng.sample(range(len(wrong)), 3))
        wrong = [wrong[i] for i in keep]
    used = {a.correct[1]} | {ch[1] for _, ch in a.wrong}  # ARITH never equals ANY rule's value
    for ch in a.arith(rng):
        if len(wrong) == 3:
            break
        if ch[1] not in used and _usable(ch):
            used.add(ch[1])
            wrong.append(("ARITH", ch))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, a.correct)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [ch[0] for _, ch in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": a.expl,
    }


# ---------------------------------------------------------------------------------------------
# Builders (pick numbers inside the bounds, render a prompt)
# ---------------------------------------------------------------------------------------------
def _classify(v: Fraction):
    if v.denominator == 1:
        return "whole" if 2 <= v <= 10 else None
    if v < 1:
        return "frac" if v.denominator in (2, 3, 4, 5) else None
    return "mixed" if v.numerator // v.denominator <= 4 and v.denominator in (2, 3, 4) else None


def _build_pool():
    pool = {"whole": [], "frac": [], "mixed": []}
    for a, b in FRACS:
        for c, d in FRACS:
            if (a, b) == (c, d) or (b % d and d % b):
                continue  # denominators equal or one a multiple of the other (head math)
            cls = _classify(Fraction(a * d, b * c))
            if cls:
                pool[cls].append((a, b, c, d))
    return pool


POOL = _build_pool()
PRICE_POOL = [(a, b, t) for a, b in FRACS for t in range(2, 10)
              if (t * b) % a == 0 and 2 <= t * b // a <= 10]


def _pair(rng):
    cls = rng.choices(("whole", "frac", "mixed"), weights=(5, 2, 3))[0]
    a, b, c, d = rng.choice(POOL[cls])
    return f"{a}/{b}", f"{c}/{d}"


def b_t1(rng, kind):
    if kind == 0:
        A, B = _pair(rng)
        agent, u1, u2, Q = rng.choice(IN_CONTEXTS)
        return f"{agent} {A} {u1} in {B} {u2}. {Q} per {u2}?"
    if kind == 1:
        A, B = _pair(rng)
        what, unit, verb, thing, Q = rng.choice(MAKES_CONTEXTS)
        return f"{A} {unit} of {what} {verb} {B} {thing}. {Q} for 1 {thing}?"
    if kind == 2:
        a, b, t = rng.choice(PRICE_POOL)
        return f"{a}/{b} lb of {rng.choice(FOODS)} costs ${t}. Cost per lb?"
    A, B = _pair(rng)
    N, n = rng.choice(TIMES_NOUNS)
    u = rng.choice(TIMES_UNITS)
    return f"{N} A is {A} {u}, {n} B is {B} {u}. A is how many times B?"


def b_t2(rng, kind):
    if kind == 0:
        x0, k = rng.randint(2, 6), rng.randint(2, 10)
        return f"({x0}, {x0 * k}) is on y = kx. Which point is also on it?"
    if kind == 1:
        Y, X = rng.choice(PAIRS2)
        return rng.choice(EQ_PHRASES).format(Y=Y, X=X, k=rng.randint(2, 10))
    if kind == 2:
        xs, k = rng.choice(XS_PROP), rng.randint(2, 10)
        ys = [k * x for x in xs]
    else:
        xs = rng.choice(XS_ADD)
        c = rng.randint(2, 9)
        if xs[0] == 2 and c % 2:  # keep the first ratio a whole number (the PROP_ASSUMED door)
            c -= 1
        ys = [x + c for x in xs]
    return f"x: {', '.join(map(str, xs))}. y: {', '.join(map(str, ys))}. Which equation fits?"


def b_t3(rng, kind):
    """0 equation, 1 point, 2 cost story, 3 earns story, 4 'in' story, 5 table."""
    if kind == 0:
        Y, X = rng.choice(PAIRS2)
        return f"{Y} = {rng.randint(2, 10)}{X}. Constant of proportionality of {Y} to {X}?"
    if kind == 1:
        x0, k = rng.randint(2, 10), rng.randint(2, 10)
        return f"({x0}, {x0 * k}) is on y = kx. What is k?"
    if kind in (2, 3, 4):
        n, k = rng.randint(2, 10), rng.randint(2, 10)
        if kind == 2:
            return f"{n} {rng.choice(ITEMS_T3)} cost ${n * k}. In c = kn, what is k?"
        if kind == 3:
            return f"Earns ${n * k} in {n} hours. In p = kh, what is k?"
        things, units, dep, ind = rng.choice(WORD_IN)
        return f"{n * k} {things} in {n} {units}. In {dep} = k{ind}, what is k?"
    xs, k = rng.choice(XS_K), rng.randint(2, 10)
    return f"x: {', '.join(str(x) for x in xs)}. y: {', '.join(str(k * x) for x in xs)}. In y = kx, what is k?"


def b_t4(rng, kind):
    """0 cost total, 1 'in' total, 2 rate, 3 'each' price, 4-6 conversions in three phrasings."""
    if kind == 0:
        n, k = rng.randint(2, 10), rng.randint(2, 10)
        items, ind = rng.choice(ITEMS_T4)
        return f"{n} {items} cost ${n * k}. Cost c for {ind} {items}?"
    if kind == 1:
        n, k = rng.randint(2, 10), rng.randint(2, 10)
        things, units, Q, dep, ind = rng.choice(TOTAL_IN)
        return f"{n * k} {things} in {n} {units}. {Q} {dep} in {ind} {units}?"
    if kind == 2:
        k = rng.randint(2, 10)
        agent, unit, per, Q, dep, ind, pers = rng.choice(RATE_CONTEXTS)
        return f"{agent} {k} {unit} per {per}. {Q} {dep} in {ind} {pers}?"
    if kind == 3:
        k = rng.randint(2, 10)
        Q, things, ind = rng.choice(EACH_CONTEXTS)
        return f"{Q} cost ${k} each. Cost c for {ind} {things}?"
    big, bigs, small, Q, k, dep, ind = rng.choice(CONVS)
    if kind == 4:
        return f"1 {big} = {k} {small}. {Q} {dep} in {ind} {bigs}?"
    if kind == 5:
        return f"Each {big} is {k} {small}. {Q} {dep} in {ind} {bigs}?"
    return f"{k} {small} make 1 {big}. {Q} {dep} in {ind} {bigs}?"


def b_t5(rng, kind):
    """0 to real, 1 to drawing, 2 real area, 3 drawing area, 4 find the scale, 5 enlarge, 6 shrink, 7 area factor."""
    if kind in (0, 1):
        lead, du, au, thing, view = rng.choice(UNITS5)
        n, k = rng.randint(2, 10), rng.randint(2, 10)
        if kind == 0:
            return f"{lead} 1 {du} : {k} {au}. {n} {du} is how many {au}?"
        return f"{lead} 1 {du} : {k} {au}. A {n * k} {au} {thing} is how many {du}?"
    if kind in (2, 3):
        du, au = rng.choice(ROOM_UNITS)
        k = rng.randint(2, 5)
        top = 10 // k
        a, b = rng.randint(2, top), rng.randint(2, top)
        if kind == 2:
            return f"Scale 1 {du} = {k} {au}. A room is drawn {a} {du} by {b} {du}. Real area?"
        return f"Scale 1 {du} = {k} {au}. A room is {a * k} {au} by {b * k} {au}. Drawing area?"
    if kind == 4:
        lead, du, au, thing, view = rng.choice(UNITS5)
        n, k = rng.randint(2, 10), rng.randint(2, 10)
        return f"{n} {du} on the {view} is {n * k} {au}. 1 {du} = ? {au}"
    if kind == 5:
        k = rng.choice((2, 2, 2, 3, 3, 4))
        a = rng.randint(1, 10 // k - 1)
        b = rng.randint(a + 1, 10 // k)
        if rng.random() < 0.5:
            return f"Scale a {a} by {b} rectangle by {k}. New size?"
        return f"Enlarge a {a} by {b} rectangle with scale factor {k}. New size?"
    if kind == 6:  # shrink: sides are multiples of k, quotients 2..5, a < b
        k = rng.choice((2, 2, 2, 3))
        a = rng.randint(2, 10 // k - 1)
        b = rng.randint(a + 1, 10 // k)
        return f"Divide each side of a {a * k} by {b * k} rectangle by {k}. New size?"
    k = rng.randint(2, 10)
    if rng.random() < 0.5:
        return f"Scale factor {k}. Area is multiplied by what?"
    return f"Each side is {k} times as long. Area is ? times as big."


# kinds per tier: how many of the 40 items each template gets (every template is guaranteed to appear)
KIND_COUNTS = {
    1: (12, 10, 9, 9),
    2: (10, 10, 10, 10),
    3: (10, 10, 4, 2, 4, 10),
    4: (7, 7, 10, 4, 4, 4, 4),
    5: (8, 7, 4, 4, 6, 3, 2, 6),
}
BUILDERS = {1: b_t1, 2: b_t2, 3: b_t3, 4: b_t4, 5: b_t5}


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def _balanced(count, k, rng):
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def _kinds(tier, count, rng):
    counts = KIND_COUNTS[tier]
    kinds = [i for i, c in enumerate(counts) for _ in range(c)]
    if len(kinds) != count:  # a manifest with another items_per_tier: stretch the last template
        kinds = (kinds + [len(counts) - 1] * count)[:count]
    rng.shuffle(kinds)
    return kinds


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000):
    build = BUILDERS[tier]
    positions = _balanced(count, 4, rng)
    kinds = _kinds(tier, count, rng)
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        prompt = build(rng, kinds[len(items)])
        if prompt is None or prompt in prompts:
            continue
        try:
            item = make_item(prompt, tier, positions[len(items)], rng)
        except NotMine:
            continue
        if item is None:
            continue
        prompts.add(prompt)
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
