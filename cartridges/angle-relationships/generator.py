"""Procedural generator for the angle-relationships cartridge (fnm-cart/1), grade 7, CCSS 7.G.B.5.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every prompt is rendered from a format string (``{a}`` a number, ``{A}`` a coefficient written
  ``x``, ``2x``, ...), then ``solve`` re-reads the DISPLAYED text with a regex compiled from the same
  format, so the text a student sees is the only thing ever solved.
* ``solve`` returns the correct choice, the correct working as steps ``(op, a, b, result)`` counted in
  TENS of degrees (180 - 70 is 18 - 7), the explanation, and every modelled misconception value in
  priority order.
* ``steps_ok`` is the manifest ``bounds`` gate on those steps (PROTOCOL §4a): + and - on 1-18 tens,
  a x factor 1-9 with a product of 18 or less, a / divisor 2-9 into 18 or less with a quotient 1-9.
* A prompt is rejected when any modelled misconception gives the right answer (a kid holding the wrong
  rule must not walk through the right door), when two choices would be equal in value, or when the
  explanation or prompt is too long.
* Candidates are enumerated per kind, shuffled, and taken greedily: distinct facts first, a repeat of
  the same fact (in other words) only when the pool of distinct facts is used up.
"""
from __future__ import annotations

import itertools
import random
import re
from fractions import Fraction

M = "−"  # U+2212, allowed by PROTOCOL §5 rule 7
MAX_PROMPT = 60
MAX_CHOICE = 14
MAX_EXPL = 160
MAX_DISTRACTOR = 999


# ---------------------------------------------------------------------------------------------
# Steps (in tens) and the bounds gate
# ---------------------------------------------------------------------------------------------
def S(op, a, b):
    """One correct-working step. Exact: a division that does not divide keeps a Fraction."""
    if op == "+":
        r = a + b
    elif op == M:
        r = a - b
    elif op == "×":
        r = a * b
    else:
        r = Fraction(a, b)
        r = int(r) if r.denominator == 1 else r
    return (op, a, b, r)


def steps_ok(steps) -> bool:
    """THE bounds gate (manifest ``bounds``). An empty list is a no-arithmetic item."""
    for op, a, b, r in steps:
        if any(Fraction(v).denominator != 1 for v in (a, b, r)):
            return False
        a, b, r = int(a), int(b), int(r)
        if op in ("+", M):
            ok = all(1 <= v <= 18 for v in (a, b, r))
        elif op == "×":
            ok = 1 <= a <= 9 and 1 <= b <= 9 and 1 <= r <= 18
        elif op == "÷":
            ok = 2 <= b <= 9 and 1 <= r <= 9 and 1 <= a <= 18
        else:
            ok = False
        if not ok:
            return False
    return True


def ex(n, d):
    """Exact integer n / d, or None."""
    return n // d if d and n % d == 0 else None


def cx(k: int) -> str:
    return "x" if k == 1 else f"{k}x"


# ---------------------------------------------------------------------------------------------
# Solutions. Each handler returns dict(correct, steps, expl, wrong=[(label, value)], givens=[degrees])
# ---------------------------------------------------------------------------------------------
def sol(correct, steps, expl, wrong, givens=()):
    return dict(correct=correct, steps=steps, expl=expl, wrong=wrong, givens=list(givens))


def total_word(T):
    return "a right angle" if T == 90 else "a straight line"


# ---- tier 1 --------------------------------------------------------------------------------
def h_comp(a):
    c = 90 - a
    return sol(c, [S(M, 9, a // 10)], f"Complementary angles add to 90: 90 {M} {a} = {c}.",
               [("COMP_SUPP_SWAP", 180 - a), ("ADDED_NOT_SUB", a + 90), ("USED_360", 360 - a)], [a])


def h_supp(a):
    c = 180 - a
    return sol(c, [S(M, 18, a // 10)], f"Supplementary angles add to 180: 180 {M} {a} = {c}.",
               [("COMP_SUPP_SWAP", abs(90 - a)), ("ADDED_NOT_SUB", a + 180), ("USED_360", 360 - a)], [a])


# ---- tier 2 --------------------------------------------------------------------------------
def h_vert(a):
    return sol(a, [], f"Vertical angles are equal, so it is also {a} degrees.",
               [("SUPP_FOR_VERT", 180 - a), ("COMP_FOR_VERT", abs(90 - a))], [a])


def h_adj(a):
    c = 180 - a
    return sol(c, [S(M, 18, a // 10)], f"Angles next to each other on a line add to 180: 180 {M} {a} = {c}.",
               [("VERT_FOR_ADJ", a), ("COMP_FOR_SUPP", abs(90 - a))], [a])


# ---- tier 3: names ---------------------------------------------------------------------------
COMP, SUPP, VERT, ADJ = "Complementary", "Supplementary", "Vertical", "Adjacent"


def h_sumword(word, total, expl):
    other = SUPP if word == COMP else COMP
    return lambda: sol(word, [], expl,
                       [("COMP_SUPP_SWAP", other), ("POSITION_WORD_FOR_SUM", VERT)])


def h_pair(a, b):
    s = a + b
    if s not in (90, 180):
        raise ValueError(f"angles {a} and {b} do not add to 90 or 180")
    word = COMP if s == 90 else SUPP
    other = SUPP if word == COMP else COMP
    return sol(word, [S("+", a // 10, b // 10)],
               f"{a} + {b} = {s}, so the angles are {word.lower()}.",
               [("COMP_SUPP_SWAP", other), ("POSITION_WORD_FOR_SUM", VERT)], [a, b])


def h_posword(word, expl, wrong):
    return lambda: sol(word, [], expl, wrong)


def h_fact(correct, expl):
    swap = 180 if correct == 90 else 90
    return lambda: sol(correct, [], expl, [("COMP_SUPP_SWAP", swap), ("USED_360", 360)])


# ---- tier 3: split angles ----------------------------------------------------------------------
def h_split(T):
    def h(a, b):
        c = T - a - b
        other_T = 180 if T == 90 else 90
        return sol(c, [S(M, T // 10, a // 10), S(M, T // 10 - a // 10, b // 10)],
                   f"The parts add to {T}: {T} {M} {a} {M} {b} = {c}.",
                   [("FORGOT_ONE", T - a), ("WRONG_TOTAL", other_T - a - b), ("ADDED_PARTS", a + b)], [a, b])
    return h


# ---- tier 4 --------------------------------------------------------------------------------
def h_pairx(T):
    other_T = 180 if T == 90 else 90

    def h(a, b):
        s = a + b
        x = ex(T, s)
        return sol(x, [S("+", a, b), S("÷", T // 10, s)],
                   f"{cx(a)} + {cx(b)} = {T}, so {s}x = {T}. {T} ÷ {s} = {x}.",
                   [("ANGLE_NOT_X", None if x is None else max(a, b) * x), ("NO_DIVIDE", T),
                    ("WRONG_TOTAL", ex(other_T, s)), ("SPLIT_EVENLY", ex(T, 2))])
    return h


def h_xplus(T):
    other_T = 180 if T == 90 else 90

    def h(q, p):
        x = T - p - q
        return sol(x, [S("+", q // 10, p // 10), S(M, T // 10, (q + p) // 10)],
                   f"x + {q} + {p} = {T}, so x = {T} {M} {q + p} = {x}.",
                   [("FORGOT_ONE", T - p), ("SIGN_SLIP", T - p + q), ("WRONG_TOTAL", other_T - p - q),
                    ("ADDED_PARTS", p + q)], [q, p])
    return h


def h_kx(T):
    other_T = 180 if T == 90 else 90

    def h(k, p):
        x = ex(T - p, k)
        tk = ex(T, k)
        return sol(x, [S(M, T // 10, p // 10), S("÷", (T - p) // 10, k)],
                   f"{k}x + {p} = {T}, so {k}x = {T - p}. {T - p} ÷ {k} = {x}.",
                   [("NO_DIVIDE", T - p), ("WRONG_TOTAL", ex(other_T - p, k)),
                    ("DIVIDED_ONE_TERM", None if tk is None else tk - p)], [p])
    return h


# ---- tier 5 --------------------------------------------------------------------------------
def h_vertx(p, q, r):
    x = ex(r - q, p)
    return sol(x, [S(M, r // 10, q // 10), S("÷", (r - q) // 10, p)],
               f"Vertical angles are equal: {p}x + {q} = {r}, {p}x = {r - q}, x = {x}.",
               [("SUPP_FOR_VERT", ex(180 - q - r, p)), ("ANGLE_NOT_X", r), ("SIGN_SLIP", ex(r + q, p)),
                ("NO_DIVIDE", r - q)], [q, r])


def h_line(T, big):
    other_T = 180 if T == 90 else 90

    def h(a, b):
        s = a + b
        x = ex(T, s)
        c, o = (max(a, b), min(a, b)) if big else (min(a, b), max(a, b))
        ans = None if x is None else c * x
        ask = "Larger" if big else "Smaller"
        wt = ex(other_T, s)
        return sol(ans, [S("+", a, b), S("÷", T // 10, s), S("×", c, T // 10 // s)],
                   f"{cx(a)} + {cx(b)} = {T}, x = {T} ÷ {s} = {x}. {ask}: {c} × {x} = {ans}.",
                   [("GAVE_X", x), ("OTHER_ANGLE", None if x is None else o * x),
                    ("WRONG_TOTAL", None if wt is None else c * wt)])
    return h


def h_adjx(p, r):
    x = ex(180 - r, p)
    return sol(x, [S(M, 18, r // 10), S("÷", 18 - r // 10, p)],
               f"Adjacent angles add to 180: {p}x = 180 {M} {r} = {180 - r}, x = {x}.",
               [("VERT_FOR_ADJ", ex(r, p)), ("COMP_FOR_SUPP", ex(90 - r, p)), ("NO_DIVIDE", 180 - r)], [r])


def h_twostep(T):
    other_T = 180 if T == 90 else 90

    def h(p, q, r):
        x = ex(T - q - r, p)
        return sol(x, [S("+", q // 10, r // 10), S(M, T // 10, (q + r) // 10), S("÷", (T - q - r) // 10, p)],
                   f"{p}x + {q} + {r} = {T}, so {p}x = {T - q - r}, x = {x}.",
                   [("FORGOT_ONE", ex(T - r, p)), ("SIGN_SLIP", ex(T - r + q, p)), ("NO_DIVIDE", T - q - r),
                    ("WRONG_TOTAL", ex(other_T - q - r, p))], [q, r])
    return h


def h_three(a, b, c):
    s = a + b + c
    x = ex(180, s)
    m = max(a, b, c)
    second = sorted((a, b, c))[1]
    ans = None if x is None else m * x
    wt = ex(90, s)
    return sol(ans, [S("+", a, b), S("+", a + b, c), S("÷", 18, s), S("×", m, 18 // s)],
               f"{cx(a)} + {cx(b)} + {cx(c)} = 180, x = 180 ÷ {s} = {x}. Largest: {m} × {x} = {ans}.",
               [("GAVE_X", x), ("OTHER_ANGLE", None if x is None else second * x),
                ("WRONG_TOTAL", None if wt is None else m * wt)])


# ---------------------------------------------------------------------------------------------
# Prompt formats and their parameter grids
# ---------------------------------------------------------------------------------------------
def rng_angles(lo=10, hi=170, skip=(90,)):
    return [a for a in range(lo, hi + 1, 10) if a not in skip]


def pairs_x(T, sums=None):
    """(a, b) coefficient pairs, a != b, whose sum s divides T/10 with s <= 9."""
    out = []
    for a in range(1, 9):
        for b in range(1, 9):
            if a != b and a + b <= 9 and (T // 10) % (a + b) == 0:
                out.append({"A": a, "B": b})
    return out


def p_comp():
    return [{"a": a} for a in rng_angles(10, 80)]


def p_supp():
    return [{"a": a} for a in rng_angles()]


def p_pair():
    return [{"a": a, "b": 90 - a} for a in rng_angles(10, 80)] + [{"a": a, "b": 180 - a} for a in rng_angles()]


def p_split(T):
    hi = 80 if T == 90 else 170
    return [{"a": a, "b": b} for a in range(10, hi, 10) for b in range(10, hi, 10) if a + b <= hi]


def p_xplus(T):
    cap = 80 if T == 90 else 100
    return [{"q": q, "p": p} for q in range(10, cap + 1, 10) for p in range(10, cap + 1, 10) if q + p <= T - 10]


def p_kx(T):
    out = []
    for k in range(2, 7):
        for p in range(10, 151, 10):
            x = ex(T - p, k)
            if p < T and x is not None and x % 10 == 0 and 10 <= x <= 90:
                out.append({"K": k, "p": p})
    return out


def p_vertx():
    out = []
    for p in range(2, 6):
        for tx in range(1, 10):
            for tq in range(1, 7):
                if p * tx + tq <= 18:
                    out.append({"P": p, "q": 10 * tq, "r": 10 * (p * tx + tq)})
    return out


def p_adjx():
    return [{"P": p, "r": 180 - 10 * p * tx} for p in range(2, 6) for tx in range(1, 10) if p * tx <= 17]


def p_twostep(T):
    out = []
    for p in range(2, 5):
        for tq in range(1, 7):
            for tr in range(1, 10):
                rem = T // 10 - tq - tr
                if rem >= p and rem % p == 0 and rem // p <= 9:
                    out.append({"P": p, "q": 10 * tq, "r": 10 * tr})
    return out


def p_three():
    out = []
    for combo in ((1, 2, 3), (1, 2, 6), (1, 3, 5), (2, 3, 4)):
        seen = set()
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if len({i, j, k}) == 3 and (i, j, k) not in seen:
                        seen.add((i, j, k))
                        out.append({"A": combo[i], "B": combo[j], "C": combo[k]})
    return out


def none():
    return [{}]


# group -> list of (family name, formats, handler, params())
GROUPS: dict = {}


def fam(group, name, fmts, handler, params):
    GROUPS.setdefault(group, []).append((name, fmts, handler, params))


# tier 1
fam("comp", "comp", ["Complement of an angle of {a} degrees?",
                     "Angles {a} and x are complementary. x in degrees?",
                     "Two angles are complementary. One is {a} degrees. The other?"], h_comp, p_comp)
fam("supp", "supp", ["Supplement of an angle of {a} degrees?",
                     "Angles {a} and x are supplementary. x in degrees?",
                     "Two angles are supplementary. One is {a} degrees. The other?"], h_supp, p_supp)
# tier 2
fam("vert", "vert", ["Lines cross. One angle is {a} degrees. Its vertical angle?",
                     "Vertical angles: one is {a} degrees. The other?",
                     "Angle A is {a} degrees. Its vertical angle B is?"], h_vert, p_supp)
fam("adj", "adj", ["Lines cross. One angle is {a} degrees. The angle next to it?",
                   "Adjacent angles on a line: one is {a} degrees. The other?",
                   "Lines cross. One angle is {a} degrees. An adjacent angle?"], h_adj, p_supp)
# tier 3
fam("sumword", "sw90a", ["Two angles that add to 90 are?"], h_sumword(COMP, 90, "Angles that add to 90 are complementary."), none)
fam("sumword", "sw90b", ["Two angles make a right angle together. They are?"],
    h_sumword(COMP, 90, "A right angle is 90, so the pair adds to 90: complementary."), none)
fam("sumword", "sw180a", ["Two angles that add to 180 are?"], h_sumword(SUPP, 180, "Angles that add to 180 are supplementary."), none)
fam("sumword", "sw180b", ["Two angles make a straight line together. They are?"],
    h_sumword(SUPP, 180, "A straight line is 180, so the pair adds to 180: supplementary."), none)
fam("pair", "pair", ["Angles of {a} and {b} degrees are?"], h_pair, p_pair)
fam("posword", "pv", ["Angles across from each other where lines cross are?"],
    h_posword(VERT, "Vertical angles sit across from each other where two lines cross.",
              [("VERT_ADJ_SWAP", ADJ), ("SUM_WORD_FOR_POSITION", SUPP), ("SUM_WORD_FOR_POSITION", COMP)]), none)
fam("posword", "pa", ["Angles that share a side and a vertex are?"],
    h_posword(ADJ, "Adjacent angles are next to each other: they share a side and a vertex.",
              [("VERT_ADJ_SWAP", VERT), ("SUM_WORD_FOR_POSITION", SUPP), ("SUM_WORD_FOR_POSITION", COMP)]), none)
fam("posword", "pe", ["Vertical angles are always?"],
    h_posword("Equal", "Vertical angles are always equal.",
              [("SUPP_FOR_VERT", SUPP), ("COMP_FOR_VERT", COMP), ("VERT_ADJ_SWAP", ADJ)]), none)
fam("fact", "f90a", ["Complementary angles add to how many degrees?"], h_fact(90, "Complementary angles add to 90 degrees."), none)
fam("fact", "f180a", ["Supplementary angles add to how many degrees?"], h_fact(180, "Supplementary angles add to 180 degrees."), none)
fam("fact", "f180b", ["A straight angle measures how many degrees?"], h_fact(180, "A straight angle is a straight line: 180 degrees."), none)
fam("fact", "f90b", ["A right angle measures how many degrees?"], h_fact(90, "A right angle is a square corner: 90 degrees."), none)
fam("split_right", "split90", ["A right angle is split into {a}, {b} and x degrees. x?",
                               "Angles {a}, {b} and x make a right angle. x in degrees?"], h_split(90), lambda: p_split(90))
fam("split_straight", "split180", ["A straight angle is split into {a}, {b} and x degrees. x?",
                                   "Angles {a}, {b} and x make a straight line. x in degrees?"], h_split(180), lambda: p_split(180))
# tier 4
fam("pairx", "pairx_s", ["{A} and {B} are supplementary. x?", "Supplementary angles are {A} and {B}. x?",
                         "Angles {A} and {B} make a straight line. x?"], h_pairx(180), lambda: pairs_x(180))
fam("pairx", "pairx_c", ["{A} and {B} are complementary. x?", "Complementary angles are {A} and {B}. x?",
                         "Angles {A} and {B} make a right angle. x?"], h_pairx(90), lambda: pairs_x(90))
fam("xplus", "xplus_s", ["x + {q} and {p} are supplementary. x?", "Supplementary angles are x + {q} and {p}. x?",
                         "x + {q} and {p} make a straight line. x?"], h_xplus(180), lambda: p_xplus(180))
fam("xplus", "xplus_c", ["x + {q} and {p} are complementary. x?", "Complementary angles are x + {q} and {p}. x?",
                         "x + {q} and {p} make a right angle. x?"], h_xplus(90), lambda: p_xplus(90))
fam("kx", "kx_s", ["{K} and {p} are supplementary. x?", "Supplementary angles are {K} and {p}. x?",
                   "Angles {K} and {p} make a straight line. x?"], h_kx(180), lambda: p_kx(180))
fam("kx", "kx_c", ["{K} and {p} are complementary. x?", "Complementary angles are {K} and {p}. x?",
                   "Angles {K} and {p} make a right angle. x?"], h_kx(90), lambda: p_kx(90))
# tier 5
fam("vertx", "vertx", ["Vertical angles: {P} + {q} and {r}. x?", "Lines cross. Vertical angles: {P} + {q} and {r}. x?",
                       "Vertical angles are {P} + {q} and {r} degrees. x?"], h_vertx, p_vertx)
for _T, _w1, _w2 in ((180, "form a straight line", "Supplementary angles:"), (90, "form a right angle", "Complementary angles:")):
    for _big, _ask in ((True, "Larger"), (False, "Smaller")):
        fam("line", f"line{_T}{_ask}", [f"{{A}} and {{B}} {_w1}. {_ask} angle?", f"{_w2} {{A}} and {{B}}. {_ask} angle?"],
            h_line(_T, _big), (lambda T=_T: pairs_x(T)))
fam("adjx", "adjx", ["Lines cross. Adjacent angles: {P} and {r}. x?", "Adjacent angles on a line: {P} and {r}. x?"], h_adjx, p_adjx)
fam("twostep", "twostep_s", ["{P} + {q} and {r} are supplementary. x?", "Supplementary angles: {P} + {q} and {r}. x?"],
    h_twostep(180), lambda: p_twostep(180))
fam("twostep", "twostep_c", ["{P} + {q} and {r} make a right angle. x?", "Complementary angles: {P} + {q} and {r}. x?"],
    h_twostep(90), lambda: p_twostep(90))
fam("three", "three", ["{A}, {B} and {C} make a straight line. Largest angle?",
                       "Straight line: {A}, {B} and {C}. Largest angle?"], h_three, p_three)


# ---------------------------------------------------------------------------------------------
# Format <-> regex
# ---------------------------------------------------------------------------------------------
_PH = re.compile(r"\{([a-zA-Z])\}")


def compile_fmt(fmt):
    """-> (compiled regex, kinds). Lowercase {a} = a number, uppercase {A} = a coefficient like 2x or x,
    {K} and {P} = a coefficient of 2 or more (2x, 3x, ...)."""
    parts, kinds, pos = [], [], 0
    for m in _PH.finditer(fmt):
        parts.append(re.escape(fmt[pos:m.start()]))
        if m.group(1) in "KP":  # a coefficient of 2 or more: the digits are required
            parts.append(r"(\d+)x")
            kinds.append("coef")
        elif m.group(1).isupper():  # {A}: a coefficient, 1 is written as a bare x
            parts.append(r"(\d*)x")
            kinds.append("coef")
        else:
            parts.append(r"(\d+)")
            kinds.append("int")
        pos = m.end()
    parts.append(re.escape(fmt[pos:]))
    return re.compile("".join(parts)), kinds


def render(fmt, vals):
    return fmt.format(**{k: (cx(v) if k.isupper() else v) for k, v in vals.items()})


COMPILED = [(*compile_fmt(f), handler) for group in GROUPS.values() for _, fmts, handler, _ in group for f in fmts]


def solve(prompt: str) -> dict:
    """Read a prompt's own text and solve it. ``wrong`` keeps every modelled (label, value) in priority
    order, including values that are None, negative or equal to the answer."""
    hits = []
    for rx, kinds, handler in COMPILED:
        m = rx.fullmatch(prompt)
        if m:
            vals = [(int(g) if g else 1) if k == "coef" else int(g) for g, k in zip(m.groups(), kinds)]
            hits.append(handler(*vals))
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} templates match {prompt!r}")
    return hits[0]


def candidates(group: str) -> list:
    """[(fact key, prompt)] for a group, every parameter set in every wording."""
    out = []
    for name, fmts, _, params in GROUPS[group]:
        for vals in params():
            key = (name, tuple(sorted(vals.items())))
            for fmt in fmts:
                out.append((key, render(fmt, vals)))
    return out


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def choice_text(v) -> str:
    return str(v)


def arith_pool(c: int, used: set, rng: random.Random) -> list:
    ds = [10, -10, 20, -20, 30, -30]
    rng.shuffle(ds)
    return [c + d for d in ds if 10 <= c + d <= 180 and (c + d) not in used]


def valid_wrongs(sol_: dict) -> list:
    """Modelled (label, value) pairs usable as door text: whole positive numbers up to 999 (or words), distinct
    from the answer and from each earlier value (the first label listed keeps a shared value)."""
    c = sol_["correct"]
    seen, out = {c}, []
    for lab, v in sol_["wrong"]:
        if v is None or v in seen:
            continue
        if isinstance(v, int) and not 0 < v <= MAX_DISTRACTOR:
            continue
        if len(choice_text(v)) > MAX_CHOICE:
            continue
        seen.add(v)
        out.append((lab, v))
    return out


def choose_wrongs(c: int, mis: list, used: set, rng: random.Random):
    """Three (label, value) wrongs for a numeric answer, or None. Modelled misconceptions first; near misses
    (ARITH) fill. The wrong values are also spread around the answer: if they all sat above it, or it were never
    the smallest or the largest, the position of the right number would give it away. A random target (how many
    wrongs sit below the answer) is matched when it can be with at most two near misses (none beyond the forced ones for a thin pool); otherwise the combination
    with the fewest near misses wins. At most one value above 180 (an impossible angle is a free elimination)."""
    cand = list(mis) + [("ARITH", v) for v in arith_pool(c, used, rng)]
    target = rng.randrange(4)
    max_arith = 3 - len(mis) if len(mis) < 3 else 2  # a thin pool gets only the near misses it needs
    best = None
    for combo in itertools.combinations(cand, 3):
        vals = [v for _, v in combo]
        n_arith = sum(lab == "ARITH" for lab, _ in combo)
        if len(set(vals)) < 3 or n_arith > max_arith or sum(v > 180 for v in vals) > 1:
            continue
        key = (sum(v < c for v in vals) != target, n_arith, rng.random())
        if best is None or key < best[0]:
            best = (key, combo)
    return None if best is None else list(best[1])


def build(prompt: str, rng: random.Random):
    """-> dict(prompt, correct, wrongs=[(label, text)], expl) or None when the prompt is not usable."""
    if len(prompt) > MAX_PROMPT:
        return None
    s = solve(prompt)
    c = s["correct"]
    if c is None or len(s["expl"]) > MAX_EXPL or not steps_ok(s["steps"]):
        return None
    if any(not (g % 10 == 0 and 10 <= g <= 180) for g in s["givens"]):
        return None
    if isinstance(c, int) and not (c % 10 == 0 and 10 <= c <= 180):
        return None
    if any(v == c for _, v in s["wrong"]):
        return None  # a wrong rule lands on the right door: not a usable prompt
    pool = valid_wrongs(s)
    if isinstance(c, int):
        used = {c} | {v for _, v in s["wrong"] if v is not None}
        pool = choose_wrongs(c, pool, used, rng)
        if pool is None:
            return None
    elif not 1 <= len(pool) <= 3:
        return None
    return dict(prompt=prompt, correct=choice_text(c), wrongs=[(lab, choice_text(v)) for lab, v in pool], expl=s["expl"])


def pick(group: str, count: int, taken: set, rng: random.Random) -> list:
    """`count` built items from a group: distinct facts first, then repeats of a fact in other words."""
    cands = candidates(group)
    rng.shuffle(cands)
    chosen, per_key = [], {}
    for level in (1, 2):
        for key, prompt in cands:
            if len(chosen) == count:
                break
            if prompt in taken or per_key.get(key, 0) >= level:
                continue
            built = build(prompt, rng)
            if built is None:
                continue
            taken.add(prompt)
            per_key[key] = per_key.get(key, 0) + 1
            chosen.append(built)
    if len(chosen) < count:
        raise RuntimeError(f"group {group}: only {len(chosen)} of {count} usable prompts")
    return chosen


PLAN = {
    1: [("comp", 14), ("supp", 26)],
    2: [("vert", 20), ("adj", 20)],
    3: [("sumword", 4), ("pair", 5), ("posword", 3), ("fact", 4), ("split_right", 10), ("split_straight", 14)],
    4: [("pairx", 16), ("xplus", 12), ("kx", 12)],
    5: [("vertx", 10), ("line", 10), ("adjx", 8), ("twostep", 6), ("three", 6)],
}


def gen_tier(tier: int, count: int, rng: random.Random) -> list:
    taken: set = set()
    built = []
    for group, n in PLAN[tier]:
        built.extend(pick(group, n, taken, rng))
    if len(built) != count:
        raise RuntimeError(f"tier {tier}: plan makes {len(built)} items, manifest wants {count}")
    rng.shuffle(built)
    # answer positions balanced within each choice-count group (PROTOCOL §5 rule 8)
    by_n: dict = {}
    for b in built:
        by_n.setdefault(1 + len(b["wrongs"]), []).append(b)
    for n in sorted(by_n):
        group = by_n[n]
        positions = [i % n for i in range(len(group))]
        rng.shuffle(positions)
        for b, pos in zip(group, positions):
            wrongs = list(b["wrongs"])
            rng.shuffle(wrongs)
            pairs = wrongs[:pos] + [(None, b["correct"])] + wrongs[pos:]
            b["choices"] = [t for _, t in pairs]
            b["misconceptions"] = [lab for lab, _ in pairs]
            b["answer"] = pos
    return [{"tier": tier, "prompt": b["prompt"], "choices": b["choices"], "answer": b["answer"],
             "misconceptions": b["misconceptions"], "explanation": b["expl"]} for b in built]


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
