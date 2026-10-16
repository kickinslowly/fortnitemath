"""Generator for the roots-irrationals cartridge (fnm-cart/1, grade 8).

Contract (PROTOCOL.md section 3): ``generate(manifest, rng) -> list[dict]``, items in the section 4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every tier is a list of *forms*; a form enumerates (or randomly builds) problems, each carrying the
  right choice, ordered wrong-choice candidates that come from a modelled misconception, and a short
  ARITH fill list used only when the misconceptions yield too few distinct values.
* Every choice has an exact *value key* (a ``Fraction``, ``("sqrt", n)``, ``("pi",)`` or a tuple), so two
  choices that are equal in value (``0.333...`` and ``1/3``) can never sit together.
* Answer positions are assigned per tier and per choice count (``i % n``, shuffled), so section 5
  rule 8 holds exactly.
"""
from __future__ import annotations

import itertools
import math
import random
from fractions import Fraction
from math import isqrt

MINUS = "−"
SQRT = "√"
PI = "π"

SQUARES = [s * s for s in range(2, 11)]  # 4..100
NON_SQUARES = [n for n in range(2, 100) if isqrt(n) ** 2 != n]
CUBES = {1: 1, 2: 8, 3: 27, 4: 64}  # root -> cube


# ----------------------------------------------------------------------------------------------
# Small exact helpers
# ----------------------------------------------------------------------------------------------
def is_square(n: int) -> bool:
    return isqrt(n) ** 2 == n


def rk(n: int):
    """Exact value key of sqrt(n)."""
    return Fraction(isqrt(n)) if is_square(n) else ("sqrt", n)


def ntext(x) -> str:
    """Exact text of a terminating Fraction: 7, -3 (U+2212), 24.5, 0.375."""
    x = Fraction(x)
    neg = x < 0
    x = abs(x)
    if x.denominator == 1:
        t = str(x.numerator)
    else:
        k = 0
        while (10 ** k) % x.denominator:
            k += 1
            if k > 6:
                raise ValueError(f"non-terminating {x}")
        n = x.numerator * 10 ** k // x.denominator
        s = str(n).rjust(k + 1, "0")
        t = (s[:-k] + "." + s[-k:]).rstrip("0").rstrip(".")
    return (MINUS + t) if neg else t


def ftext(f) -> str:
    f = Fraction(f)
    if f.denominator == 1:
        return ntext(f)
    return f"{f.numerator}/{f.denominator}"


class Problem:
    def __init__(self, prompt, right, wrongs, fill, expl, n=4):
        self.prompt = prompt
        self.right = right  # (text, vkey)
        self.wrongs = wrongs  # [(text, vkey, key)]
        self.fill = fill  # [(text, vkey)]
        self.expl = expl
        self.n = n


def num_c(x, key):
    """Candidate from a Fraction value."""
    x = Fraction(x)
    return (ntext(x), x, key)


def num_f(x):
    x = Fraction(x)
    return (ntext(x), x)


# ----------------------------------------------------------------------------------------------
# Tier 1: square and cube roots
# ----------------------------------------------------------------------------------------------
def t1_problems():
    forms = {k: [] for k in ("root", "xpos", "xneg", "area", "both", "cube", "xcube", "edge")}
    for N in SQUARES:
        s = isqrt(N)
        pos_fill = [num_f(v) for v in (s + 1, s - 1, s + 2, s - 2) if v >= 1 and v != s]
        neg_fill = [num_f(-v) for v in (s + 1, s - 1, s + 2, s - 2) if v >= 1]
        e = f"{s} × {s} = {N}, so √{N} = {s}."

        forms["root"].append(Problem(
            f"√{N} = ?", num_f(s),
            [num_c(Fraction(N, 2), "HALVED"), num_c(2 * s, "DOUBLED"), num_c(N, "NOT_ROOTED")],
            pos_fill, e))
        forms["xpos"].append(Problem(
            f"x^2 = {N} and x > 0. x?", num_f(s),
            [num_c(Fraction(N, 2), "HALVED"), num_c(N, "NOT_ROOTED"), num_c(2 * s, "DOUBLED")],
            pos_fill, f"{s} × {s} = {N}, and x is positive, so x = {s}."))
        forms["xneg"].append(Problem(
            f"x^2 = {N} and x < 0. x?", num_f(-s),
            [num_c(s, "POSITIVE_ONLY"), num_c(-Fraction(N, 2), "HALVED"), num_c(-N, "NOT_ROOTED")],
            neg_fill, f"{s} × {s} = {N} and (−{s}) × (−{s}) = {N}. x is negative, so x = −{s}."))
        forms["area"].append(Problem(
            f"A square has area {N}. Side?", num_f(s),
            [num_c(Fraction(N, 2), "HALVED"), num_c(Fraction(N, 4), "AREA_OVER_4"),
             num_c(4 * s, "PERIMETER_FOR_SIDE"), num_c(N, "NOT_ROOTED")],
            pos_fill, f"Side × side = area. {s} × {s} = {N}, so the side is {s}."))
        both = f"{s} or {MINUS}{s}"
        forms["both"].append(Problem(
            f"All solutions of x^2 = {N}?", (both, ("pm", s)),
            [(str(s), ("pm1", s), "POSITIVE_ONLY"),
             (f"{ntext(Fraction(N, 2))} or {MINUS}{ntext(Fraction(N, 2))}", ("pm", Fraction(N, 2)), "HALVED"),
             (f"{N} or {MINUS}{N}", ("pm", N), "NOT_ROOTED")],
            [(f"{v} or {MINUS}{v}", ("pm", v)) for v in (s + 1, s - 1, s + 2) if v >= 1 and v != s],
            f"{s} × {s} = {N} and (−{s}) × (−{s}) = {N}. Both {s} and −{s} work."))
    for c, N in CUBES.items():
        pos_fill = [num_f(v) for v in (c + 1, c + 2, c - 1, 2 * c + 1) if v >= 1 and v != c]
        e = f"{c} × {c} × {c} = {N}, so the cube root of {N} is {c}."
        wr = []
        if N % 3 == 0:
            wr.append(num_c(Fraction(N, 3), "THIRD_FOR_CUBE"))
        if is_square(N):
            wr.append(num_c(isqrt(N), "SQUARE_ROOT_FOR_CUBE"))
        wr += [num_c(3 * c, "TRIPLED"), num_c(Fraction(N, 2), "HALVED"), num_c(N, "NOT_ROOTED")]
        forms["cube"].append(Problem(f"Cube root of {N}?", num_f(c), wr, pos_fill, e))
        forms["xcube"].append(Problem(f"x^3 = {N}. x?", num_f(c), wr, pos_fill, e))
        if c >= 2:
            forms["edge"].append(Problem(f"A cube has volume {N}. Edge?", num_f(c), wr, pos_fill,
                                         f"Edge × edge × edge = volume. {c} × {c} × {c} = {N}, so the edge is {c}."))
    return forms, {"root": 7, "xpos": 6, "xneg": 6, "area": 6, "both": 6,
                   "cube": 3, "xcube": 3, "edge": 3}


# ----------------------------------------------------------------------------------------------
# Tier 2: rational or irrational
# ----------------------------------------------------------------------------------------------
RATIONAL, IRRATIONAL = "Rational", "Irrational"


def _word_problem(prompt, is_rational, key_if_wrong, expl):
    right, wrong = (RATIONAL, IRRATIONAL) if is_rational else (IRRATIONAL, RATIONAL)
    return Problem(prompt, (right, right), [(wrong, wrong, key_if_wrong)], [], expl, n=2)


REPEATS = [("0.333...", Fraction(1, 3)), ("0.666...", Fraction(2, 3)), ("0.1818...", Fraction(2, 11)),
           ("0.2727...", Fraction(3, 11)), ("0.8333...", Fraction(5, 6)), ("0.777...", Fraction(7, 9)),
           ("0.4545...", Fraction(5, 11)), ("0.1666...", Fraction(1, 6)), ("0.555...", Fraction(5, 9))]
ENDINGS = [("0.25", Fraction(1, 4)), ("0.5", Fraction(1, 2)), ("1.5", Fraction(3, 2)), ("0.75", Fraction(3, 4)),
           ("0.125", Fraction(1, 8)), ("2.4", Fraction(12, 5)), ("0.6", Fraction(3, 5)), ("1.25", Fraction(5, 4))]
FRACS = [(2, 3), (5, 8), (3, 7), (7, 9), (4, 11), (1, 6), (9, 10), (5, 12)]


def t2_problems():
    forms = {k: [] for k in ("irr_root", "sq_root", "repeat", "ending", "frac", "special", "ctx", "which")}
    for n in NON_SQUARES:
        forms["irr_root"].append(_word_problem(
            f"√{n} is?", False, "ROOT_IS_RATIONAL",
            f"{n} is not a perfect square, so √{n} never ends or repeats: irrational."))
    for n in SQUARES:
        s = isqrt(n)
        forms["sq_root"].append(_word_problem(
            f"√{n} is?", True, "ROOT_IS_IRRATIONAL", f"√{n} = {s}, a whole number, so it is rational."))
    for t, f in REPEATS:
        forms["repeat"].append(_word_problem(
            f"{t} is?", True, "REPEAT_IS_IRRATIONAL",
            f"A repeating decimal is a fraction ({ftext(f)}), so it is rational."))
    for t, f in ENDINGS:
        forms["ending"].append(_word_problem(
            f"{t} is?", True, "NONWHOLE_IS_IRRATIONAL",
            f"{t} ends, so it is a fraction ({ftext(f)}): rational."))
    for a, b in FRACS:
        forms["frac"].append(_word_problem(
            f"{a}/{b} is?", True, "NONWHOLE_IS_IRRATIONAL",
            f"{a}/{b} is a fraction of whole numbers, so it is rational."))
    forms["special"].append(_word_problem(
        f"{PI} is?", False, "PI_IS_RATIONAL",
        f"{PI} never ends and never repeats, so it is irrational."))
    forms["special"].append(_word_problem(
        "A circle has diameter 1. Circumference?", False, "PI_IS_RATIONAL",
        f"Circumference = {PI} × diameter = {PI}, which never ends or repeats: irrational."))
    forms["special"].append(_word_problem(
        "A circle has radius 1. Its area is?", False, "PI_IS_RATIONAL",
        f"Area = {PI} × 1 × 1 = {PI}, which never ends or repeats: irrational."))
    for n in (20, 50, 18, 45, 3, 11):
        forms["ctx"].append(_word_problem(
            f"A square has area {n}. Its side is?", False, "ROOT_IS_RATIONAL",
            f"Side = √{n}. {n} is not a perfect square, so the side is irrational."))
    for n in (25, 49, 81, 16, 64, 36):
        s = isqrt(n)
        forms["ctx"].append(_word_problem(
            f"A square has area {n}. Its side is?", True, "ROOT_IS_IRRATIONAL",
            f"Side = √{n} = {s}, a whole number, so it is rational."))
    # "which" items (numbers listed in the prompt, 4 choices) are built by t2_which
    sq_pool = [(f"{SQRT}{n}", Fraction(isqrt(n)), n) for n in (9, 16, 25, 36, 49, 64, 81)]
    rep_pool = [(t, f) for t, f in REPEATS]
    flat_pool = [(t, f) for t, f in ENDINGS] + [(f"{a}/{b}", Fraction(a, b)) for a, b in FRACS]
    return forms, {"irr_root": 3, "sq_root": 2, "repeat": 1, "ending": 1, "frac": 1, "special": 3, "ctx": 1},         (sq_pool, rep_pool, flat_pool)


def _listed(want_rational, right, wr, expl, rng):
    toks = [right[0]] + [w[0] for w in wr]
    rng.shuffle(toks)
    word = "rational" if want_rational else "irrational"
    return Problem(f"Which is {word}: " + ", ".join(toks) + "?", right, wr, [], expl)


def t2_which(want_rational, pools, rng):
    wording = None
    sq_pool, rep_pool, flat_pool = pools
    irr_roots = [(f"{SQRT}{n}", ("sqrt", n)) for n in NON_SQUARES]
    pi_c = (PI, ("pi",))
    if not want_rational:
        # one irrational, three rational of different kinds
        n = rng.choice([x for x in NON_SQUARES if x <= 40])
        right = rng.choice([(f"{SQRT}{n}", ("sqrt", n)), (f"{SQRT}{n}", ("sqrt", n)), pi_c])
        a = rng.choice(sq_pool)
        b = rng.choice(rep_pool)
        c = rng.choice(flat_pool)
        while c[1] == b[1]:
            c = rng.choice(flat_pool)
        wr = [(a[0], a[1], "ROOT_IS_IRRATIONAL"), (b[0], b[1], "REPEAT_IS_IRRATIONAL"),
              (c[0], c[1], "NONWHOLE_IS_IRRATIONAL")]
        if right[1] == ("pi",):
            expl = f"{PI} never ends or repeats: irrational. The others are fractions or whole numbers."
        else:
            expl = f"{n} is not a perfect square, so {SQRT}{n} is irrational. The others are rational."
        return _listed(want_rational, right, wr, expl, rng)
    kind = rng.choice(["sq", "rep", "flat"])
    if kind == "sq":
        a = rng.choice(sq_pool)
        right = (a[0], a[1])
        expl = f"{a[0]} = {ftext(a[1])}, a whole number: rational. The others never end or repeat."
    elif kind == "rep":
        a = rng.choice(rep_pool)
        right = (a[0], a[1])
        expl = f"{a[0]} repeats, so it is the fraction {ftext(a[1])}: rational. The others are not."
    else:
        a = rng.choice(flat_pool)
        right = (a[0], a[1])
        expl = f"{a[0]} is a fraction or ends: rational. The others never end or repeat."
    ns = rng.sample([x for x in NON_SQUARES if x <= 40], 3)
    wr = [(f"{SQRT}{ns[0]}", ("sqrt", ns[0]), "ROOT_IS_RATIONAL"),
          (f"{SQRT}{ns[1]}", ("sqrt", ns[1]), "ROOT_IS_RATIONAL"),
          (PI, ("pi",), "PI_IS_RATIONAL")] if rng.random() < 0.6 else \
         [(f"{SQRT}{ns[0]}", ("sqrt", ns[0]), "ROOT_IS_RATIONAL"),
          (f"{SQRT}{ns[1]}", ("sqrt", ns[1]), "ROOT_IS_RATIONAL"),
          (f"{SQRT}{ns[2]}", ("sqrt", ns[2]), "ROOT_IS_RATIONAL")]
    return _listed(want_rational, right, wr, expl, rng)


# ----------------------------------------------------------------------------------------------
# Tier 3: repeating decimals
# ----------------------------------------------------------------------------------------------
def t3_problems():
    forms = {k: [] for k in ("one", "two", "six", "which", "ending", "x1", "x2")}
    one, two, six = [], [], []  # (decimal text, fraction, cands, fill, expl)
    for d in range(1, 9):
        f = Fraction(d, 9)
        t = f"0.{d}{d}{d}..."
        wr = [(ftext(Fraction(d, 10)), Fraction(d, 10), "OVER_TEN"),
              (ftext(Fraction(d + 1, 10)), Fraction(d + 1, 10), "ROUNDED_UP")]
        fill = [(ftext(Fraction(d + k, 9)), Fraction(d + k, 9)) for k in (1, -1, 2, -2) if 1 <= d + k <= 8]
        fill += [(ftext(Fraction(d, 8)), Fraction(d, 8)), (ftext(Fraction(d, 11)), Fraction(d, 11))]
        one.append((t, f, wr, fill, f"One digit repeats, so {t} = {d}/9" + (f" = {ftext(f)}." if f.denominator != 9 else ".")))
    for n in range(1, 11):
        ab = f"{9 * n:02d}"
        f = Fraction(n, 11)
        t = f"0.{ab}{ab}..."
        wr = [(ftext(Fraction(9 * n, 100)), Fraction(9 * n, 100), "OVER_HUNDRED")]
        if n < 9:
            wr.append((ftext(Fraction(n, 9)), Fraction(n, 9), "NINTHS_ONLY"))
        fill = [(ftext(Fraction(n + k, 11)), Fraction(n + k, 11)) for k in (1, -1, 2, -2) if 1 <= n + k <= 10]
        fill += [(ftext(Fraction(n, 10)), Fraction(n, 10))] if n < 10 else []
        fill += [(ftext(Fraction(n, 12)), Fraction(n, 12))]
        two.append((t, f, wr, fill, f"Two digits repeat: {t} = {9 * n}/99 = {n}/11."))
    for t, f, first, rep in (("0.1666...", Fraction(1, 6), 1, 6), ("0.8333...", Fraction(5, 6), 8, 3)):
        approx = int(t[2:4])
        wr = [(ftext(Fraction(approx, 100)), Fraction(approx, 100), "OVER_HUNDRED"),
              (ftext(Fraction(approx + 1, 100)), Fraction(approx + 1, 100), "ROUNDED_UP")]
        fill = [(ftext(Fraction(1, 5)), Fraction(1, 5)), (ftext(Fraction(1, 7)), Fraction(1, 7)),
                (ftext(Fraction(5, 7)), Fraction(5, 7)), (ftext(Fraction(5, 9)), Fraction(5, 9))]
        six.append((t, f, wr, fill, f"1/6 = 0.1666... and 5/6 = 0.8333...; {t} = {ftext(f)}."))
    for t, f, wr, fill, e in one + two + six:
        forms["one" if (t, f, wr, fill, e) in one else "two" if (t, f, wr, fill, e) in two else "six"].append(
            Problem(f"{t} as a fraction?", (ftext(f), f), wr, fill, e))
        forms["which"].append(Problem(f"Which fraction equals {t}?", (ftext(f), f), wr, fill, e))
    # ending decimals
    for dec, f in (("0.5", Fraction(1, 2)), ("0.2", Fraction(1, 5)), ("0.4", Fraction(2, 5)), ("0.6", Fraction(3, 5)),
                   ("0.8", Fraction(4, 5)), ("0.25", Fraction(1, 4)), ("0.75", Fraction(3, 4)),
                   ("0.1", Fraction(1, 10)), ("0.3", Fraction(3, 10)), ("0.7", Fraction(7, 10)),
                   ("0.9", Fraction(9, 10)), ("0.125", Fraction(1, 8)), ("0.375", Fraction(3, 8)),
                   ("0.625", Fraction(5, 8)), ("0.875", Fraction(7, 8))):
        digits = dec[2:]
        ndig = int(digits)
        L = len(digits)
        nine = Fraction(ndig, 10 ** L - 1)
        slip = {1: Fraction(ndig, 100), 2: Fraction(ndig, 10), 3: Fraction(ndig, 100)}[L]
        wr = [(ftext(nine), nine, "NINE_FOR_TERMINATING"),
              (ftext(Fraction(1, ndig)), Fraction(1, ndig), "DIGIT_AS_DENOM"),
              (ftext(slip), slip, "PLACE_VALUE_SLIP")]
        fill = [(ftext(f + Fraction(1, 10)), f + Fraction(1, 10)), (ftext(f * 2), f * 2)]
        forms["ending"].append(Problem(
            f"{dec} as a fraction?", (ftext(f), f), wr, fill,
            f"{dec} = {ndig}/{10 ** L}" + (f" = {ftext(f)}." if f.denominator != 10 ** L else ".")))
    # the 10x - x step
    for d in range(1, 9):
        t = f"0.{d}{d}{d}..."
        wr = [(f"{d}.{d}{d}{d}...", Fraction(10 * d, 9), "TIMES_ONLY"),
              ("9", Fraction(9), "NINES_ONLY"),
              (ntext(Fraction(9 * d, 10)), Fraction(9 * d, 10), "TRUNCATED_REPEAT"),
              (ntext(Fraction(d, 10)), Fraction(d, 10), "DECIMAL_SLIP")]
        fill = [(str(d + 1), Fraction(d + 1)), (str(10 * d), Fraction(10 * d))]
        forms["x1"].append(Problem(
            f"x = {t} Then 10x − x = ?", (str(d), Fraction(d)), wr, fill,
            f"10x = {d}.{d}{d}{d}... and x = {t}. Subtract: 9x = {d}, so 10x − x = {d}."))
    for n in range(1, 11):
        ab = f"{9 * n:02d}"
        t = f"0.{ab}{ab}..."
        big = f"{9 * n}.{ab}{ab}..."
        wr = [(big, Fraction(9 * n * 100, 99), "TIMES_ONLY"),
              ("99", Fraction(99), "NINES_ONLY"),
              (ntext(Fraction(99 * 9 * n, 100)), Fraction(99 * 9 * n, 100), "TRUNCATED_REPEAT"),
              (ntext(Fraction(9 * n, 100)), Fraction(9 * n, 100), "DECIMAL_SLIP")]
        fill = [(str(9 * n + 1), Fraction(9 * n + 1)), (str(900 * n), Fraction(900 * n))]
        forms["x2"].append(Problem(
            f"x = {t} Then 100x − x = ?", (str(9 * n), Fraction(9 * n)), wr, fill,
            f"100x = {big} and x = {t}. Subtract: 99x = {9 * n}, so 100x − x = {9 * n}."))
    quotas = {"one": 5, "two": 6, "six": 2, "which": 9, "ending": 8, "x1": 4, "x2": 6}
    return forms, quotas


# ----------------------------------------------------------------------------------------------
# Tier 4: estimate square roots
# ----------------------------------------------------------------------------------------------
def t4_problems():
    forms = {k: [] for k in ("between", "ctx", "nearest", "about")}
    for n in NON_SQUARES:
        s = isqrt(n)
        right = f"{s} and {s + 1}"
        h = n // 2
        wr = [(f"{s * s} and {(s + 1) ** 2}", ("sq", s), "SQUARES_NOT_ROOTS"),
              (f"{h} and {h + 1}", ("pair", h), "HALVED"),
              (f"{s - 1} and {s}", ("pair", s - 1), "NEXT_SQUARE_DOWN"),
              (f"{s + 1} and {s + 2}", ("pair", s + 1), "NEXT_SQUARE_UP")]
        # keys: pairs use ("pair", lo); right is ("pair", s); squares ("sq", s) never collides with a pair
        e = f"{s}^2 = {s * s} and {s + 1}^2 = {(s + 1) ** 2}. {n} is between, so √{n} is between {s} and {s + 1}."
        fill = [(f"{s + 2} and {s + 3}", ("pair", s + 2))]
        forms["between"].append(Problem(f"√{n} is between which two whole numbers?", (right, ("pair", s)), wr, fill, e))
        forms["ctx"].append(Problem(f"Square area {n}. Side is between which whole numbers?",
                                    (right, ("pair", s)), wr, fill, e))
        frac = math.sqrt(n) - s
        if frac < 0.3 or frac > 0.7:
            r = s if frac < 0.5 else s + 1
            other = s + 1 if r == s else s
            near_sq = r * r
            wr2 = [num_c(near_sq, "NEAREST_SQUARE_NOT_ROOT"), num_c(other, "ROUNDED_WRONG")]
            if abs(n / 2 - math.sqrt(n)) >= 1:  # a halved value that is also close would be a second right door
                wr2.append(num_c(Fraction(n, 2), "HALVED"))
            fill2 = [num_f(v) for v in (r + 1, r - 1, r + 2, r + 3, r - 2) if v >= 1 and v != r]
            e2 = (f"{n} is close to {near_sq} = {r} × {r}, so √{n} is about {r}.")
            forms["nearest"].append(Problem(f"Nearest whole number to √{n}?", num_f(r), wr2, fill2, e2))
    for k in range(2, 10):
        n = k * (k + 1)
        wr = [num_c(Fraction(n, 2), "HALVED"), num_c(k * k, "NEAREST_SQUARE_NOT_ROOT"),
              num_c((k + 1) ** 2, "NEAREST_SQUARE_NOT_ROOT")]
        fill = [num_f(Fraction(2 * k + 3, 2)), num_f(Fraction(2 * k - 1, 2))]
        forms["about"].append(Problem(
            f"√{n} is about?", num_f(Fraction(2 * k + 1, 2)), wr, fill,
            f"{n} is halfway between {k}^2 = {k * k} and {k + 1}^2 = {(k + 1) ** 2}, so √{n} is about {k}.5."))
    return forms, {"between": 20, "ctx": 6, "nearest": 8, "about": 6}


# ----------------------------------------------------------------------------------------------
# Tier 5: compare and order
# ----------------------------------------------------------------------------------------------
def _item_root(n):
    return {"text": f"{SQRT}{n}", "val": math.sqrt(n), "face": float(n), "key": rk(n), "n": n}


def _item_int(k):
    return {"text": str(k), "val": float(k), "face": float(k), "key": Fraction(k), "n": None}


def _item_half(x2):
    return {"text": ntext(Fraction(x2, 2)), "val": x2 / 2, "face": x2 / 2, "key": Fraction(x2, 2), "n": None}


def _item_pi():
    return {"text": PI, "val": math.pi, "face": 3.14, "key": ("pi",), "n": None}


def t5_compare_problems(rng):
    """'Greater: sqrt(N) or x?' items. The root side is always a non-square root or pi."""
    out = []
    roots = [_item_root(n) for n in NON_SQUARES]
    others = [_item_int(k) for k in range(2, 11)] + [_item_half(2 * k + 1) for k in range(2, 10)]
    for r in roots:
        for o in others:
            if abs(r["val"] - o["val"]) < 0.3 or o["val"] >= 10.5:
                continue
            out.append((r, o))
    for n in (8, 12):
        out.append((_item_root(n), _item_pi()))
    out.append((_item_pi(), _item_half(7)))
    return out


def make_compare(r, o, word):
    """'Greater: r or o?'. None when no modelled misconception explains the wrong pick."""
    big = word == "Greater"
    items = [r, o]
    right = max(items, key=lambda i: i["val"]) if big else min(items, key=lambda i: i["val"])
    wrong = o if right is r else r
    face_pick = max(items, key=lambda i: i["face"]) if big else min(items, key=lambda i: i["face"])
    # "a root is small": for Greater the habit picks the plain number, for Smaller it picks the root
    small_pick = o if big else r
    if face_pick is wrong:
        key = "RADICAND_AS_VALUE"
    elif small_pick is wrong and r["n"] is not None:
        key = "ROOT_ALWAYS_SMALL"
    else:
        return None
    if r["n"] is not None:
        s = isqrt(r["n"])
        why = f"√{r['n']} is between {s} and {s + 1}"
    else:
        why = f"{PI} is about 3.14"
    expl = f"{why}, so {right['text']} is the {'greater' if big else 'smaller'}."
    prompt = f"{word}: {r['text']} or {o['text']}?"
    return Problem(prompt, (right["text"], right["key"]), [(wrong["text"], wrong["key"], key)], [], expl, n=2)


def t5_between_problems(rng):
    out = []
    for a in range(3, 10):
        lo, hi = a + 0.3, a + 0.7
        right_ns = [n for n in NON_SQUARES if lo <= math.sqrt(n) <= hi]
        below = [n for n in NON_SQUARES if (a - 1) + 0.3 <= math.sqrt(n) <= a - 0.3]
        above = [n for n in NON_SQUARES if a + 1.3 <= math.sqrt(n) <= a + 1.7]
        if not (right_ns and below and above):
            continue
        for wording in ("Which is between {a} and {b}?", "Which number lies between {a} and {b}?"):
            out.append((a, wording, right_ns, below, above))
    return out


def make_between(spec, rng):
    a, wording, right_ns, below, above = spec
    n = rng.choice(right_ns)
    nb, na = rng.choice(below), rng.choice(above)
    s = isqrt(n)
    wr = [(f"{SQRT}{a}", rk(a), "RADICAND_AS_VALUE"),
          (f"{SQRT}{nb}", rk(nb), "NEXT_SQUARE_DOWN"),
          (f"{SQRT}{na}", rk(na), "NEXT_SQUARE_UP")]
    expl = f"{a}^2 = {a * a} and {a + 1}^2 = {(a + 1) ** 2}. {n} is between them, so √{n} is between {a} and {a + 1}."
    return Problem(wording.format(a=a, b=a + 1), (f"{SQRT}{n}", rk(n)), wr, [], expl)


def t5_order_problem(rng, taken):
    """Three values, at least one root, pairwise >= 0.3 apart; the radicand order must differ from the truth."""
    for _ in range(2000):
        nroots = rng.choice([1, 1, 2])
        ns = rng.sample([n for n in NON_SQUARES if n <= 60], nroots)
        ints = rng.sample(range(2, 11), 3 - nroots)
        vals = [_item_root(n) for n in ns] + [_item_int(k) for k in ints]
        ok = all(abs(x["val"] - y["val"]) >= 0.3 for i, x in enumerate(vals) for y in vals[i + 1:])
        if not ok:
            continue
        rng.shuffle(vals)
        asc = rng.random() < 0.7
        truth = sorted(vals, key=lambda i: i["val"], reverse=not asc)
        if [v["text"] for v in vals] == [v["text"] for v in truth]:
            continue
        face = sorted(vals, key=lambda i: i["face"], reverse=not asc)
        if [v["text"] for v in face] == [v["text"] for v in truth]:
            continue
        word = "Least to greatest" if asc else "Greatest to least"
        prompt = f"{word}: " + ", ".join(v["text"] for v in vals)
        if prompt in taken:
            continue
        def txt(order):
            return ", ".join(v["text"] for v in order)
        def vk(order):
            return tuple(v["key"] for v in order)
        wr = [(txt(face), vk(face), "RADICAND_AS_VALUE"),
              (txt(list(reversed(truth))), vk(list(reversed(truth))), "ORDER_REVERSED"),
              (txt(vals), vk(vals), "GIVEN_ORDER")]
        roots_ = [v for v in truth if v["n"] is not None]
        plain_ = [v for v in truth if v["n"] is None]
        small = roots_ + plain_ if asc else plain_ + roots_  # roots treated as the smallest numbers
        wr.append((txt(small), vk(small), "ROOT_ALWAYS_SMALL"))
        fill = []
        import itertools
        for p in itertools.permutations(vals):
            fill.append((txt(p), vk(p)))
        rng.shuffle(fill)
        rootexp = "; ".join(
            f"√{v['n']} is between {isqrt(v['n'])} and {isqrt(v['n']) + 1}" for v in vals if v["n"] is not None)
        expl = f"{rootexp}. Sorted {'least to greatest' if asc else 'greatest to least'}: {txt(truth)}."
        return Problem(prompt, (txt(truth), vk(truth)), wr, fill, expl)
    raise RuntimeError("no ordering problem")


def _band(r):
    return f"√{r['n']} is between {isqrt(r['n'])} and {isqrt(r['n']) + 1}"


def t5_list_problem(rng, taken, least, root_right):
    """'Greatest: √50, 6.5, √30?' -- three numbers, one plain and two roots, every pair >= 0.3 apart.

    Plain number x with roots below it (radicands above it) is the trap for the radicand habit; a root above x
    is the trap for 'roots are small'. About half of each form has a root as the answer."""
    plains = [_item_pi()] + [_item_int(k) for k in range(3, 9)] + [_item_half(2 * k + 1) for k in range(3, 9)]
    word = "Least" if least else "Greatest"
    for _ in range(5000):
        x = rng.choice(plains)
        below = [n for n in NON_SQUARES if math.sqrt(n) <= x["val"] - 0.3]
        above = [n for n in NON_SQUARES if x["val"] + 0.3 <= math.sqrt(n) <= 9.9]
        if not least and root_right:        # Greatest, a root wins: R above x, S below x
            if not below or not above:
                continue
            R, S = _item_root(rng.choice(above)), _item_root(rng.choice(below))
            right = R
            wr = [(x["text"], x["key"], "ROOT_ALWAYS_SMALL"), (S["text"], S["key"], "ARITH")]
            expl = f"{_band(R)}, above {x['text']}; {_band(S)}, below it. {R['text']} is the greatest."
            vals = [x, R, S]
        elif not least:                      # Greatest, the plain number wins: both roots below x
            below = [n for n in below if n > x["face"]]
            if len(below) < 2:
                continue
            n1, n2 = rng.sample(below, 2)
            r1, r2 = _item_root(n1), _item_root(n2)
            big = r1 if n1 > n2 else r2      # the larger radicand is the one the radicand habit picks
            small = r2 if big is r1 else r1
            right = x
            wr = [(big["text"], big["key"], "RADICAND_AS_VALUE"), (small["text"], small["key"], "ARITH")]
            expl = f"{_band(r1)}; {_band(r2)}. Both are below {x['text']}, so {x['text']} is the greatest."
            vals = [x, r1, r2]
        elif root_right:                     # Least, a root wins: both roots below x, radicands above x
            below = [n for n in below if n > x["face"]]
            if len(below) < 2:
                continue
            n1, n2 = rng.sample(below, 2)
            r1, r2 = _item_root(n1), _item_root(n2)
            right = min((r1, r2), key=lambda r: r["val"])
            other = r2 if right is r1 else r1
            wr = [(x["text"], x["key"], "RADICAND_AS_VALUE"), (other["text"], other["key"], "ARITH")]
            expl = f"{_band(r1)}; {_band(r2)}. Both are below {x['text']}; {right['text']} is the least."
            vals = [x, r1, r2]
        else:                                # Least, the plain number wins: both roots above x
            if len(above) < 2:
                continue
            n1, n2 = rng.sample(above, 2)
            r1, r2 = _item_root(n1), _item_root(n2)
            right = x
            lo, hi = (r1, r2) if r1["val"] < r2["val"] else (r2, r1)
            wr = [(lo["text"], lo["key"], "ROOT_ALWAYS_SMALL"), (hi["text"], hi["key"], "ARITH")]
            expl = f"{_band(r1)}; {_band(r2)}. Both are above {x['text']}, so {x['text']} is the least."
            vals = [x, r1, r2]
        if any(abs(u["val"] - v["val"]) < 0.3 for u, v in itertools.combinations(vals, 2)):
            continue
        rng.shuffle(vals)
        prompt = f"{word}: " + ", ".join(v["text"] for v in vals) + "?"
        if prompt in taken or len(expl) > 160:
            continue
        return Problem(prompt, (right["text"], right["key"]), wr, [], expl, n=3)
    raise RuntimeError("no list problem")


def t5_special():
    return [Problem(
        f"{PI}^2 is about?", num_f(10),
        [num_c(6, "TIMES_FOR_POWER")],
        [num_f(5), num_f(14), num_f(31), num_f(3), num_f(20)],
        f"{PI} is about 3.14. {PI}^2 = {PI} × {PI}, a bit under 10.")]


# ----------------------------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------------------------
def _realise(p: Problem, rng):
    """Pick the distractors: modelled misconceptions first, ARITH only to fill."""
    want = p.n - 1
    seen_v = {p.right[1]}
    seen_t = {p.right[0]}
    chosen = []
    real = list(p.wrongs)
    rng.shuffle(real)
    for text, vk, key in real:
        if vk in seen_v or text in seen_t or len(text) > 14:
            continue
        chosen.append((text, key))
        seen_v.add(vk)
        seen_t.add(text)
        if len(chosen) == want:
            break
    if len(chosen) < want:
        fill = list(p.fill)
        rng.shuffle(fill)
        for text, vk in fill:
            if vk in seen_v or text in seen_t or len(text) > 14:
                continue
            chosen.append((text, "ARITH"))
            seen_v.add(vk)
            seen_t.add(text)
            if len(chosen) == want:
                break
    if len(chosen) < want:
        raise RuntimeError(f"not enough distractors for {p.prompt!r}")
    rng.shuffle(chosen)
    return chosen


def _finish(tier, problems, rng):
    items = []
    realised = [(p, _realise(p, rng)) for p in problems]
    by_n = {}
    for idx, (p, _) in enumerate(realised):
        by_n.setdefault(p.n, []).append(idx)
    pos = {}
    for n, idxs in by_n.items():
        ps = [i % n for i in range(len(idxs))]
        rng.shuffle(ps)
        for idx, q in zip(idxs, ps):
            pos[idx] = q
    for idx, (p, wrongs) in enumerate(realised):
        q = pos[idx]
        choices = [t for t, _ in wrongs]
        keys = [k for _, k in wrongs]
        choices.insert(q, p.right[0])
        keys.insert(q, None)
        assert len(p.prompt) <= 60, p.prompt
        assert len(p.expl) <= 160, (p.prompt, p.expl)
        items.append({"tier": tier, "prompt": p.prompt, "choices": choices, "answer": q,
                      "misconceptions": keys, "explanation": p.expl})
    return items


def _take(forms, quotas, rng, taken):
    """Draw each form's quota of problems with unique prompts; top up from the leftovers."""
    chosen = []
    leftovers = []
    for name, probs in forms.items():
        probs = list(probs)
        rng.shuffle(probs)
        k = quotas.get(name, 0)
        n_taken = 0
        for p in probs:
            if p.prompt in taken:
                continue
            if n_taken < k:
                taken.add(p.prompt)
                chosen.append(p)
                n_taken += 1
            else:
                leftovers.append(p)
    return chosen, leftovers


def _top_up(chosen, leftovers, n, rng, taken):
    rng.shuffle(leftovers)
    for p in leftovers:
        if len(chosen) >= n:
            break
        if p.prompt not in taken:
            taken.add(p.prompt)
            chosen.append(p)
    return chosen


def gen_tier(tier, n, rng):
    taken = set()
    if tier == 1:
        forms, quotas = t1_problems()
        chosen, left = _take(forms, quotas, rng, taken)
    elif tier == 2:
        forms, quotas, pools = t2_problems()
        chosen, left = _take(forms, quotas, rng, taken)
        for i in range(n - len(chosen)):
            while True:
                p = t2_which(i % 2 == 1, pools, rng)
                if p.prompt not in taken:
                    break
            taken.add(p.prompt)
            chosen.append(p)
    elif tier == 3:
        forms, quotas = t3_problems()
        chosen, left = _take(forms, quotas, rng, taken)
    elif tier == 4:
        forms, quotas = t4_problems()
        chosen, left = _take(forms, quotas, rng, taken)
    elif tier == 5:
        chosen, left = [], []
        for p in t5_special():
            taken.add(p.prompt)
            chosen.append(p)
        pairs = t5_compare_problems(rng)
        rng.shuffle(pairs)
        k = 0
        for r, o in pairs:
            if k >= 7:
                break
            word = rng.choice(["Greater", "Smaller"])
            # keep the radicand rule informative: the root should lose to the number it is compared with,
            # but only (n > x) so the wrong radicand habit shows up
            p = make_compare(r, o, word)
            if p is None or p.prompt in taken:
                continue
            if r["n"] is not None and not (r["val"] < o["val"] < r["n"]) and rng.random() < 0.7:
                continue
            taken.add(p.prompt)
            chosen.append(p)
            k += 1
        for least, root_right in ((False, False), (False, True), (False, False), (False, True), (False, False),
                                  (False, True), (True, False), (True, True), (True, False), (True, True)):
            p = t5_list_problem(rng, taken, least=least, root_right=root_right)
            taken.add(p.prompt)
            chosen.append(p)
        specs = t5_between_problems(rng)
        rng.shuffle(specs)
        for spec in specs:
            if sum(1 for p in chosen if p.prompt.startswith("Which") and "between" in p.prompt) >= 10:
                break
            p = make_between(spec, rng)
            if p.prompt in taken:
                continue
            taken.add(p.prompt)
            chosen.append(p)
        while len(chosen) < n:
            p = t5_order_problem(rng, taken)
            taken.add(p.prompt)
            chosen.append(p)
    else:
        raise ValueError(tier)
    if tier != 5:
        chosen = _top_up(chosen, left, n, rng, taken)
    chosen = chosen[:n]
    if len(chosen) < n:
        raise RuntimeError(f"tier {tier}: only {len(chosen)} problems")
    rng.shuffle(chosen)
    return _finish(tier, chosen, rng)


def generate(manifest: dict, rng: random.Random) -> list:
    items = []
    n = manifest["items_per_tier"]
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
