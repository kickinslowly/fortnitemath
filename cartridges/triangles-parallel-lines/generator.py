"""Procedural generator for the triangles-parallel-lines cartridge (fnm-cart/1), grade 8, CCSS 8.G.A.5.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design (same shape as the grade-7 angle-relationships generator, written fresh)
------
* Every prompt is rendered from a format string (``{a}`` a number, ``{A}`` a coefficient written ``x``,
  ``2x``, ..., ``{K}`` a coefficient of 2 or more), then ``solve`` re-reads the DISPLAYED text with a regex
  compiled from the same format, so the text a student sees is the only thing ever solved.
* ``solve`` returns the correct choice, the correct working as steps ``(op, a, b, result)`` counted in TENS of
  degrees (180 - 70 is 18 - 7), the explanation, and every modelled misconception value in priority order.
* ``steps_ok`` is the manifest ``bounds`` gate on those steps (PROTOCOL §4a).
* A prompt is rejected when any modelled misconception gives the right answer (a kid holding the wrong rule must
  not walk through the right door), or when the explanation or prompt is too long.
* Candidates are enumerated per group, shuffled, and taken greedily: distinct facts first, a repeat of the same
  fact (in other words) only when the pool of distinct facts is used up.
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

EQUAL, ADD180, ADD90, YES, NO = "Equal", "Add to 180", "Add to 90", "Yes", "No"


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
    """Exact positive integer n / d, or None."""
    if d and n % d == 0 and n // d > 0:
        return n // d
    return None


def pos(n):
    """n when it is a positive whole number, else None."""
    return n if n > 0 else None


def cx(k: int) -> str:
    return "x" if k == 1 else f"{k}x"


def sol(correct, steps, expl, wrong, givens=()):
    return dict(correct=correct, steps=steps, expl=expl, wrong=wrong, givens=list(givens))


# ---------------------------------------------------------------------------------------------
# Tier 1: triangle angle sum
# ---------------------------------------------------------------------------------------------
def h_tri3(a, b):
    c = 180 - a - b
    return sol(c, [S("+", a // 10, b // 10), S(M, 18, (a + b) // 10)],
               f"A triangle's angles add to 180: 180 {M} {a} {M} {b} = {c}.",
               [("USED_360", 360 - a - b), ("FORGOT_ONE", 180 - a), ("FORGOT_ONE", 180 - b),
                ("ADDED_ANGLES", a + b), ("USED_90", pos(90 - a - b))], [a, b])


def h_right(a):
    c = 90 - a
    return sol(c, [S(M, 9, a // 10)],
               f"A right triangle has a 90 angle, so the other two add to 90: 90 {M} {a} = {c}.",
               [("FORGOT_RIGHT", 180 - a), ("USED_360", 270 - a), ("ADDED_ANGLES", 90 + a)], [a])


def h_isotop(t):
    base = (180 - t) // 2
    return sol(base, [S(M, 18, t // 10), S("÷", 18 - t // 10, 2)],
               f"Base angles are equal and all three add to 180: (180 {M} {t}) ÷ 2 = {base}.",
               [("NO_HALF", 180 - t), ("HALF_TOP", t // 2), ("SAME_AS_TOP", t)], [t])


def h_isobase(b):
    top = 180 - 2 * b
    return sol(top, [S("×", 2, b // 10), S(M, 18, 2 * b // 10)],
               f"The two base angles make {b} + {b} = {2 * b}. Top angle: 180 {M} {2 * b} = {top}.",
               [("NO_DOUBLE", 180 - b), ("SAME_AS_BASE", b), ("ADDED_ANGLES", 2 * b)], [b])


def h_equil():
    return sol(60, [S("÷", 18, 3)], "All three angles are equal and add to 180: 180 ÷ 3 = 60.",
               [("USED_360", 120), ("SPLIT_IN_TWO", 90)])


# ---------------------------------------------------------------------------------------------
# Tier 2: exterior angles
# ---------------------------------------------------------------------------------------------
def h_extsum(a, b):
    e = a + b
    return sol(e, [S("+", a // 10, b // 10)],
               f"An exterior angle equals the two remote angles added: {a} + {b} = {e}.",
               [("INTERIOR_FOR_EXTERIOR", 180 - e), ("ONE_REMOTE", a), ("ONE_REMOTE", b),
                ("USED_360", 360 - e)], [a, b])


def h_extother(e, a):
    o = e - a
    return sol(o, [S(M, e // 10, a // 10)],
               f"The exterior angle is the sum of the remote angles: {e} {M} {a} = {o}.",
               [("ADDED_NOT_SUB", e + a), ("EQUAL_REMOTES", a), ("INTERIOR_FOR_EXTERIOR", 180 - e)], [e, a])


def h_extadj(e):
    i = 180 - e
    return sol(i, [S(M, 18, e // 10)],
               f"The exterior angle and the inside angle next to it make a line: 180 {M} {e} = {i}.",
               [("SAME_AS_EXT", e), ("USED_90", abs(90 - e)), ("USED_360", 360 - e)], [e])


# ---------------------------------------------------------------------------------------------
# Tiers 3-4: parallel lines
# ---------------------------------------------------------------------------------------------
def h_peq(name):
    def h(a):
        return sol(a, [], f"Parallel lines make {name} angles equal, so it is also {a} degrees.",
                   [("SUPP_FOR_EQUAL", 180 - a), ("COMP_FOR_EQUAL", abs(90 - a)), ("USED_360", 360 - a)], [a])
    return h


def h_psupp(name):
    def h(a):
        c = 180 - a
        return sol(c, [S(M, 18, a // 10)],
                   f"Parallel lines: {name} angles add to 180: 180 {M} {a} = {c}.",
                   [("EQUAL_FOR_SUPP", a), ("USED_90", abs(90 - a)), ("USED_360", 360 - a)], [a])
    return h


def h_vert(a):
    return sol(a, [], f"Vertical angles are always equal, so it is also {a} degrees.",
               [("SUPP_FOR_EQUAL", 180 - a), ("COMP_FOR_EQUAL", abs(90 - a)), ("USED_360", 360 - a)], [a])


def h_linear(a):
    c = 180 - a
    return sol(c, [S(M, 18, a // 10)], f"Angles next to each other on a line add to 180: 180 {M} {a} = {c}.",
               [("EQUAL_FOR_SUPP", a), ("USED_90", abs(90 - a)), ("USED_360", 360 - a)], [a])


def h_pword(name, equal):
    if equal:
        return lambda: sol(EQUAL, [], f"Parallel lines make {name} angles equal.",
                           [("SUPP_FOR_EQUAL", ADD180), ("COMP_FOR_EQUAL", ADD90)])
    return lambda: sol(ADD180, [], f"Parallel lines: {name} angles add to 180.",
                       [("EQUAL_FOR_SUPP", EQUAL), ("USED_90", ADD90)])


def h_yn(a, b):
    s = a + b
    if s == 180:
        return sol(YES, [S("+", a // 10, b // 10)],
                   f"{a} + {b} = 180, so the same-side angles are supplementary: parallel.",
                   [("EQUAL_FOR_SUPP", NO)], [a, b])
    wrong = []
    if a == b:
        wrong.append(("EQUAL_FOR_SUPP", YES))
    if s == 90:
        wrong.append(("USED_90", YES))
    return sol(NO, [S("+", a // 10, b // 10)],
               f"{a} + {b} = {s}, not 180, so the lines are not parallel.", wrong, [a, b])


# ---------------------------------------------------------------------------------------------
# Tier 5: x in triangles and parallel lines, similar triangles
# ---------------------------------------------------------------------------------------------
def h_trix(A, B, C):
    s = A + B + C
    x = ex(180, s)
    m = max(A, B, C)
    return sol(None if x is None else x,
               [S("+", A, B), S("+", A + B, C), S("÷", 18, s)],
               f"Angles add to 180: {cx(A)} + {cx(B)} + {cx(C)} = {s}x = 180, so x = {x}.",
               [("GAVE_ANGLE", None if x is None else m * x), ("NO_DIVIDE", 180), ("SPLIT_EVENLY", 60),
                ("USED_360", ex(360, s))])


def h_trilarge(A, B, C):
    s = A + B + C
    x = ex(180, s)
    m = max(A, B, C)
    second = sorted((A, B, C))[1]
    ans = None if x is None else m * x
    return sol(ans, [S("+", A, B), S("+", A + B, C), S("÷", 18, s), S("×", m, 18 // s)],
               f"{cx(A)} + {cx(B)} + {cx(C)} = {s}x = 180, x = {x}. Largest: {m} × {x} = {ans}.",
               [("GAVE_X", x), ("OTHER_ANGLE", None if x is None else second * x), ("SPLIT_EVENLY", 60),
                ("USED_360", None if ex(360, s) is None else m * ex(360, s))])


def h_rtx(A, B):
    s = A + B
    x = ex(90, s)
    m = max(A, B)
    return sol(x, [S("+", A, B), S("÷", 9, s)],
               f"The other two angles add to 90: {cx(A)} + {cx(B)} = {s}x = 90, so x = {x}.",
               [("USED_180", ex(180, s)), ("GAVE_ANGLE", None if x is None else m * x), ("NO_DIVIDE", 90),
                ("SPLIT_EVENLY", 45)])


def h_extx(e, A, B):
    s = A + B
    x = ex(e, s)
    m = max(A, B)
    return sol(x, [S("+", A, B), S("÷", e // 10, s)],
               f"Exterior = remote angles added: {cx(A)} + {cx(B)} = {s}x = {e}, so x = {x}.",
               [("NO_DIVIDE", e), ("GAVE_ANGLE", None if x is None else m * x), ("USED_180", ex(180, s)),
                ("INTERIOR_FOR_EXTERIOR", ex(180 - e, s))], [e])


def h_eqx1(name):  # K x = b
    def h(K, b):
        x = ex(b, K)
        return sol(x, [S("÷", b // 10, K)],
                   f"{name.capitalize()} angles are equal: {K}x = {b}, so x = {b} ÷ {K} = {x}.",
                   [("SUPP_FOR_EQUAL", ex(180 - b, K)), ("NO_DIVIDE", b), ("MULTIPLIED_NOT_DIVIDED", K * b)], [b])
    return h


def h_eqx2(name):  # x + c = b
    def h(c, b):
        x = b - c
        return sol(x, [S(M, b // 10, c // 10)],
                   f"{name.capitalize()} angles are equal: x + {c} = {b}, so x = {b} {M} {c} = {x}.",
                   [("SIGN_SLIP", b + c), ("SUPP_FOR_EQUAL", pos(180 - b - c)), ("GAVE_ANGLE", b)], [c, b])
    return h


def h_eqx3(name):  # K x + c = b
    def h(K, c, b):
        x = ex(b - c, K)
        return sol(x, [S(M, b // 10, c // 10), S("÷", (b - c) // 10, K)],
                   f"{name.capitalize()} angles are equal: {K}x + {c} = {b}, {K}x = {b - c}, x = {x}.",
                   [("NO_DIVIDE", b - c), ("SIGN_SLIP", ex(b + c, K)), ("FORGOT_ONE", ex(b, K)),
                    ("SUPP_FOR_EQUAL", ex(180 - b - c, K))], [c, b])
    return h


def h_sx1(name):  # K x + b = 180
    def h(K, b):
        x = ex(180 - b, K)
        return sol(x, [S(M, 18, b // 10), S("÷", (180 - b) // 10, K)],
                   f"Same-side angles add to 180: {K}x = 180 {M} {b} = {180 - b}, x = {x}.",
                   [("EQUAL_FOR_SUPP", ex(b, K)), ("NO_DIVIDE", 180 - b), ("USED_90", ex(90 - b, K))], [b])
    return h


def h_sx2(name):  # x + c + b = 180
    def h(c, b):
        x = 180 - b - c
        return sol(x, [S("+", c // 10, b // 10), S(M, 18, (b + c) // 10)],
                   f"Same-side angles add to 180: x + {c} + {b} = 180, x = 180 {M} {b + c} = {x}.",
                   [("EQUAL_FOR_SUPP", pos(b - c)), ("FORGOT_ONE", 180 - b), ("SIGN_SLIP", 180 - b + c),
                    ("USED_90", pos(90 - b - c))], [c, b])
    return h


def h_sx3(name):  # K x + c + b = 180
    def h(K, c, b):
        x = ex(180 - b - c, K)
        return sol(x, [S("+", c // 10, b // 10), S(M, 18, (b + c) // 10), S("÷", (180 - b - c) // 10, K)],
                   f"Same-side angles add to 180: {K}x + {c} + {b} = 180, {K}x = {180 - b - c}, x = {x}.",
                   [("NO_DIVIDE", 180 - b - c), ("FORGOT_ONE", ex(180 - b, K)), ("SIGN_SLIP", ex(180 - b + c, K)),
                    ("EQUAL_FOR_SUPP", ex(b - c, K))], [c, b])
    return h


def h_sim(a, b, c, d):
    ta, tb = 180 - a - b, 180 - c - d
    A3, B3 = sorted((a, b, ta)), sorted((c, d, tb))
    listing = f"A: {A3[0]}, {A3[1]}, {A3[2]}. B: {B3[0]}, {B3[1]}, {B3[2]}."
    if A3 == B3:
        return sol(YES, [S("+", a // 10, b // 10), S(M, 18, (a + b) // 10), S("+", c // 10, d // 10),
                         S(M, 18, (c + d) // 10)],
                   f"{listing} The same three angles, so similar.",
                   [("NEEDS_SAME_LISTED", NO)] if sorted((a, b)) != sorted((c, d)) else [], [a, b, c, d])
    shared = bool({a, b} & {c, d})
    return sol(NO, [S("+", a // 10, b // 10), S(M, 18, (a + b) // 10), S("+", c // 10, d // 10),
                    S(M, 18, (c + d) // 10)],
               f"{listing} Different angles, so not similar.",
               [("ONE_ANGLE_ENOUGH" if shared else "ALL_TRIANGLES_ALIKE", YES)], [a, b, c, d])


# ---------------------------------------------------------------------------------------------
# Parameter grids
# ---------------------------------------------------------------------------------------------
def tens(lo, hi):
    return range(lo, hi + 1, 10)


def p_pair170():
    return [{"a": a, "b": b} for a in tens(10, 160) for b in tens(a, 160) if a + b <= 170]


def p_a(lo, hi):
    return lambda: [{"a": a} for a in tens(lo, hi)]


def p_t():
    return [{"t": t} for t in range(20, 161, 20)]


def p_e():
    return [{"e": e} for e in tens(10, 170)]


def p_extother():
    return [{"e": e, "a": a} for e in tens(30, 170) for a in tens(10, e - 10)]


def p_yn_yes():
    return [{"a": a, "b": 180 - a} for a in tens(10, 170) if a != 90]


def p_yn_no():
    return ([{"a": a, "b": a} for a in tens(10, 170) if a != 90]
            + [{"a": a, "b": 90 - a} for a in tens(10, 80)])


def p_none():
    return [{}]


def perms_distinct(combos):
    out = []
    for combo in combos:
        for p in sorted(set(itertools.permutations(combo))):
            out.append({"A": p[0], "B": p[1], "C": p[2]})
    return out


TRI_SETS = [(1, 2, 3), (1, 1, 4), (1, 2, 6), (1, 3, 5), (2, 3, 4), (1, 4, 4), (2, 2, 5), (1, 1, 7)]


def p_trix():
    return perms_distinct(TRI_SETS)


def p_trilarge():
    # the largest angle must be unique in size, or "largest" is still one value but OTHER_ANGLE would collide
    return perms_distinct([t for t in TRI_SETS if t.count(max(t)) == 1])


def p_rtx():
    return [{"A": A, "B": B} for A, B in ((1, 2), (2, 1), (4, 5), (5, 4))]


def p_extx():
    return [{"e": 10 * (A + B) * xt, "A": A, "B": B} for A in range(1, 9) for B in range(1, 9)
            if A != B and 3 <= A + B <= 9 for xt in range(2, 10) if (A + B) * xt <= 17]


def p_eqx1():
    return [{"K": K, "b": 10 * K * xt} for K in range(2, 7) for xt in range(2, 10) if K * xt <= 17]


def p_eqx2():
    return [{"c": c, "b": c + 10 * xt} for c in tens(10, 90) for xt in range(1, 10) if c + 10 * xt <= 170]


def p_eqx3():
    return [{"K": K, "c": c, "b": 10 * K * xt + c} for K in range(2, 6) for c in tens(10, 90)
            for xt in range(2, 10) if 10 * K * xt + c <= 170]


def p_sx1():
    return [{"K": K, "b": 180 - 10 * K * xt} for K in range(2, 7) for xt in range(2, 10) if 10 * K * xt <= 170]


def p_sx2():
    return [{"c": c, "b": 180 - c - 10 * xt} for c in tens(10, 90) for xt in range(1, 10) if c + 10 * xt <= 170]


def p_sx3():
    return [{"K": K, "c": c, "b": 180 - c - 10 * K * xt} for K in range(2, 6) for c in tens(10, 90)
            for xt in range(2, 10) if c + 10 * K * xt <= 170]


def triples():
    return [(x, y, 18 - x - y) for x in range(1, 17) for y in range(x, 17) if 18 - x - y >= y]


def p_sim_yes():
    out = []
    for t in triples():
        T = [10 * v for v in t]
        pairs = sorted({tuple(sorted(p)) for p in itertools.combinations(T, 2)})
        for pa in pairs:
            for pb in pairs:
                if pa != pb:
                    out.append({"a": pa[0], "b": pa[1], "c": pb[0], "d": pb[1]})
    return out


def p_sim_no(shared):
    """Not-similar pairs whose listed angles share one angle (shared) or none."""
    out = []
    ts = triples()
    for t1 in ts:
        for t2 in ts:
            if t1 == t2:
                continue
            for pa in {tuple(sorted(p)) for p in itertools.combinations([10 * v for v in t1], 2)}:
                for pb in {tuple(sorted(p)) for p in itertools.combinations([10 * v for v in t2], 2)}:
                    if bool(set(pa) & set(pb)) == shared:
                        out.append({"a": pa[0], "b": pa[1], "c": pb[0], "d": pb[1]})
    return sorted(out, key=lambda d: tuple(d.values()))


# ---------------------------------------------------------------------------------------------
# Families: group -> list of (family name, formats, handler, params())
# ---------------------------------------------------------------------------------------------
GROUPS: dict = {}


def fam(group, name, fmts, handler, params):
    GROUPS.setdefault(group, []).append((name, fmts, handler, params))


# tier 1
fam("tri3", "tri3", ["A triangle has angles {a} and {b} degrees. Third angle?",
                     "Two angles of a triangle are {a} and {b}. The third?",
                     "Triangle angles: {a} and {b} degrees. Third angle?"], h_tri3, p_pair170)
fam("right", "right", ["Right triangle with an angle of {a} degrees. Third angle?",
                       "A right triangle has an angle of {a}. Its third angle?"], h_right, p_a(10, 80))
fam("isotop", "isotop", ["Isosceles triangle, top angle {t} degrees. Each base angle?",
                         "An isosceles triangle has top angle {t}. Each base angle?"], h_isotop, p_t)
fam("isobase", "isobase", ["Isosceles triangle, base angles {b} degrees each. Top angle?",
                           "An isosceles triangle has two {b} degree angles. The third?"], h_isobase,
    lambda: [{"b": b} for b in tens(10, 80)])
fam("equil", "equil", ["Each angle of an equilateral triangle, in degrees?",
                       "An equilateral triangle has three equal angles. Each?"], h_equil, p_none)
# tier 2
fam("extsum", "extsum", ["Triangle angles {a} and {b}. Exterior angle at the third?",
                         "Remote angles are {a} and {b} degrees. Exterior angle?"], h_extsum, p_pair170)
fam("extother", "extother", ["Exterior angle {e}, one remote angle {a}. The other?",
                            "Exterior angle is {e}. Remote angles: {a} and x. x?"], h_extother, p_extother)
fam("extadj", "extadj", ["A triangle's exterior angle is {e}. Inside angle next to it?",
                         "Exterior angle is {e}. Its adjacent inside angle?"], h_extadj, p_e)
# tier 3
EQ_NAMES = ["corresponding", "alternate interior", "alternate exterior"]
for _n in EQ_NAMES:
    fam("peq", f"peq_{_n}", [f"Parallel lines. Angle {{a}}. Its {_n} angle?",
                              f"Parallel lines. {_n.capitalize()} pair: one is {{a}}. Other?",
                              f"Parallel lines. An angle is {{a}}. Its {_n} angle?"], h_peq(_n), p_a(10, 170))
fam("vert", "vert", ["Lines cross. One angle is {a} degrees. Its vertical angle?",
                     "Vertical angles: one is {a} degrees. The other?"], h_vert, p_a(10, 170))
fam("linear", "linear", ["Two lines cross. One angle is {a}. The angle next to it?",
                         "An angle is {a} degrees. The angle next to it on a line?"], h_linear, p_a(10, 170))
for _n in ("corresponding", "alternate exterior"):
    fam("pword3", f"pw3_{_n}", [f"Parallel lines: {_n} angles are?",
                                 f"Parallel lines: {_n} angles are always?",
                                 f"Parallel lines cut by a line: {_n} angles are?"], h_pword(_n, True), p_none)
# tier 4
SS_NAMES = ["same-side interior", "same-side exterior"]
for _n in SS_NAMES:
    fam("psupp", f"ps_{_n}", [f"Parallel lines. Angle {{a}}. Its {_n} angle?",
                               f"Parallel lines. {_n.capitalize()} pair: one is {{a}}. Other?",
                               f"{{a}} and x are {_n} angles of parallel lines. x?"], h_psupp(_n), p_a(10, 170))
fam("pword4", "pw4_alt", [f"Parallel lines: alternate interior angles are?",
                          f"Parallel lines: alternate interior angles are always?",
                          f"In parallel lines, alternate interior angles are?"], h_pword("alternate interior", True), p_none)
for _n in SS_NAMES:
    fam("pword4", f"pw4_{_n}", [f"Parallel lines: {_n} angles are?",
                                 f"Parallel lines: {_n} angles are always?",
                                 f"In parallel lines, {_n} angles are?"], h_pword(_n, False), p_none)
fam("yes", "yes", ["Same-side interior angles are {a} and {b}. Lines parallel?",
                   "Same-side interior: {a} and {b}. Are the lines parallel?"], h_yn, p_yn_yes)
fam("no", "no", ["Same-side interior angles are {a} and {b}. Lines parallel?",
                 "Same-side interior: {a} and {b}. Are the lines parallel?"], h_yn, p_yn_no)
# tier 5
fam("trix", "trix", ["A triangle has angles {A}, {B} and {C}. x?",
                     "Triangle angles {A}, {B} and {C} degrees. x?"], h_trix, p_trix)
fam("trilarge", "trilarge", ["Triangle angles {A}, {B} and {C}. Largest angle?",
                             "A triangle has angles {A}, {B} and {C}. Largest angle?"], h_trilarge, p_trilarge)
fam("rtx", "rtx", ["Right triangle: 90, {A} and {B}. x?",
                   "A right triangle has angles 90, {A} and {B}. x?"], h_rtx, p_rtx)
fam("extx", "extx", ["Exterior angle is {e}. Remote angles are {A} and {B}. x?",
                     "Triangle: exterior angle {e}, remote angles {A} and {B}. x?"], h_extx, p_extx)
for _n in ("corresponding", "alternate interior", "alternate exterior"):
    fam("eqx1", f"eqx1_{_n}", [f"Parallel lines: {_n} angles {{K}} and {{b}}. x?"], h_eqx1(_n), p_eqx1)
    fam("eqx2", f"eqx2_{_n}", [f"Parallel lines: {_n} angles x + {{c}} and {{b}}. x?"], h_eqx2(_n), p_eqx2)
    fam("eqx3", f"eqx3_{_n}", [f"Parallel lines: {_n} angles {{K}} + {{c}} and {{b}}. x?"], h_eqx3(_n), p_eqx3)
for _n in SS_NAMES:
    fam("sx1", f"sx1_{_n}", [f"Parallel lines: {_n} angles {{K}} and {{b}}. x?"], h_sx1(_n), p_sx1)
    fam("sx2", f"sx2_{_n}", [f"Parallel lines: {_n} angles x + {{c}} and {{b}}. x?"], h_sx2(_n), p_sx2)
    fam("sx3", f"sx3_{_n}", [f"Parallel lines: {_n} angles {{K}} + {{c}} and {{b}}. x?"], h_sx3(_n), p_sx3)
fam("simyes", "simyes", ["Triangle A: {a} and {b}. Triangle B: {c} and {d}. Similar?",
                         "Triangle A has {a} and {b}. B has {c} and {d}. Similar?"], h_sim, p_sim_yes)
for _g, _sh in (("simno1", True), ("simno2", False)):
    fam(_g, _g, ["Triangle A: {a} and {b}. Triangle B: {c} and {d}. Similar?",
                 "Triangle A has {a} and {b}. B has {c} and {d}. Similar?"], h_sim, (lambda sh=_sh: p_sim_no(sh)))


# ---------------------------------------------------------------------------------------------
# Format <-> regex
# ---------------------------------------------------------------------------------------------
_PH = re.compile(r"\{([a-zA-Z])\}")


def compile_fmt(fmt):
    """-> (compiled regex, kinds). Lowercase {a} = a number, {A} = a coefficient like 2x or x,
    {K} = a coefficient of 2 or more (2x, 3x, ...)."""
    parts, kinds, pos_ = [], [], 0
    for m in _PH.finditer(fmt):
        parts.append(re.escape(fmt[pos_:m.start()]))
        if m.group(1) == "K":
            parts.append(r"(\d+)x")
            kinds.append("coef")
        elif m.group(1).isupper():
            parts.append(r"(\d*)x")
            kinds.append("coef")
        else:
            parts.append(r"(\d+)")
            kinds.append("int")
        pos_ = m.end()
    parts.append(re.escape(fmt[pos_:]))
    return re.compile("".join(parts)), kinds


def render(fmt, vals):
    return fmt.format(**{k: (cx(v) if k.isupper() else v) for k, v in vals.items()})


COMPILED = [(*compile_fmt(f), handler) for group in GROUPS.values() for _, fmts, handler, _ in group for f in fmts]


def solve(prompt: str) -> dict:
    """Read a prompt's own text and solve it. ``wrong`` keeps every modelled (label, value) in priority
    order, including values that are None, negative or equal to the answer."""
    hits = []
    seen = set()
    for rx, kinds, handler in COMPILED:
        m = rx.fullmatch(prompt)
        if m:
            vals = [(int(g) if g else 1) if k == "coef" else int(g) for g, k in zip(m.groups(), kinds)]
            sig = (id(handler), tuple(vals))
            if sig in seen:
                continue  # the yes/no groups share one family's text and handler
            seen.add(sig)
            hits.append((handler, vals))
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} templates match {prompt!r}")
    handler, vals = hits[0]
    return handler(*vals)


def candidates(group: str, only=None) -> list:
    """[(fact key, prompt)] for a group, every parameter set in every wording."""
    out = []
    for name, fmts, _, params in GROUPS[group]:
        if only and not any(o in name for o in only):
            continue
        for vals in params():
            key = (name, tuple(sorted(vals.items())))
            for fmt in fmts:
                out.append((key, render(fmt, vals)))
    return out


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
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
        if len(str(v)) > MAX_CHOICE:
            continue
        seen.add(v)
        out.append((lab, v))
    return out


def choose_wrongs(c: int, mis: list, used: set, rng: random.Random):
    """Three (label, value) wrongs for a numeric answer, or None. Modelled misconceptions first; near misses
    (ARITH) fill. The wrong values are also spread around the answer so its size never gives it away: a random
    target (how many wrongs sit below it) is matched when it can be with at most two near misses; otherwise the
    combination with the fewest near misses wins. At most one value above 180."""
    cand = list(mis) + [("ARITH", v) for v in arith_pool(c, used, rng)]
    target = rng.randrange(4)
    max_arith = 3 - len(mis) if len(mis) < 3 else 2
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
    if any(not (g % 10 == 0 and 10 <= g <= 170) for g in s["givens"]):
        return None
    if isinstance(c, int) and not (c % 10 == 0 and 10 <= c <= 170):
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
    return dict(prompt=prompt, correct=str(c), wrongs=[(lab, str(v)) for lab, v in pool], expl=s["expl"])


def pick(group: str, count: int, taken: set, rng: random.Random, only=None, levels=(1, 2, 3, 4)) -> list:
    """`count` built items from a group: distinct facts first, then repeats of a fact in other words."""
    cands = candidates(group, only)
    rng.shuffle(cands)
    chosen, per_key = [], {}
    for level in levels:
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
    1: [("tri3", 16), ("right", 8), ("isotop", 7), ("isobase", 7), ("equil", 2)],
    2: [("extsum", 14), ("extother", 16), ("extadj", 10)],
    3: [("peq", 20), ("vert", 3), ("psupp", 9, ("interior",)), ("linear", 4), ("pword3", 4, None, (1, 2))],
    4: [("psupp", 13), ("peq", 13), ("pword4", 6, None, (1, 2)), ("yes", 4), ("no", 4)],
    5: [("trix", 4), ("trilarge", 4), ("rtx", 4), ("extx", 4), ("eqx1", 3), ("eqx2", 3), ("eqx3", 2),
        ("sx1", 3), ("sx2", 2), ("sx3", 1), ("simyes", 5), ("simno1", 3), ("simno2", 2)],
}


def gen_tier(tier: int, count: int, rng: random.Random) -> list:
    taken: set = set()
    built = []
    for group, n, *extra in PLAN[tier]:
        built.extend(pick(group, n, taken, rng, *extra))
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
        for b, p in zip(group, positions):
            wrongs = list(b["wrongs"])
            rng.shuffle(wrongs)
            pairs = wrongs[:p] + [(None, b["correct"])] + wrongs[p:]
            b["choices"] = [t for _, t in pairs]
            b["misconceptions"] = [lab for lab, _ in pairs]
            b["answer"] = p
    return [{"tier": tier, "prompt": b["prompt"], "choices": b["choices"], "answer": b["answer"],
             "misconceptions": b["misconceptions"], "explanation": b["expl"]} for b in built]


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
