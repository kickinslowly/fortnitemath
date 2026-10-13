"""Procedural generator for the circles cartridge (fnm-cart/1), grade 7, CCSS 7.G.B.4.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* A *kind* is a family of prompts: a list of wording frames (``"A wheel has radius {r}. Its circumference?"``),
  a list of parameter dicts (``{"r": 3}``) and a solver. Frames and parameters make the prompt text; the
  solver is only ever called on a prompt that is read back from its own text (regex per frame), so what a
  student sees is the only thing ever solved. Hand-written concept questions (vocabulary, formulas, "about how
  many diameters") live in ``BANKS`` and are looked up by their text.
* A value is ``(text, key)``: the choice text and a canonical key, so ``2/4`` and ``1/2`` would collide.
  ``P(n)`` is ``n`` times π, ``N(v)`` a plain number (decimal ``.5`` allowed), ``Q(v)`` a plain fraction,
  ``PP(a, b)`` is ``aπ + b``, ``T(text)`` a word or formula. A constructor returns ``None`` for a value the
  display cannot show (a non-whole π coefficient), and that distractor is simply not offered.
* ``solve`` returns the correct value, its working as steps ``(op, a, b, result)``, the explanation and every
  modelled misconception's value in label priority order (including ones that land on the answer).
* ``steps_ok`` is the manifest ``bounds`` gate on those steps (PROTOCOL §4a/§4b).
* A prompt is rejected when any modelled misconception gives the right answer: a student holding that wrong
  rule would walk through the right door (a radius of 2 makes 2πr and πr² both ``4π``).
* Each tier draws its quota from every kind's pool; a kind uses each parameter once before reusing one under
  another wording.
"""
from __future__ import annotations

import random
import re
from fractions import Fraction as F

MUL, DIV, ADD = "×", "÷", "+"
MAX_VALUE = 100
MAX_DISTRACTOR = 999
MAX_CHOICE = 14
MAX_PROMPT = 60


# ---------------------------------------------------------------------------------------------
# Numbers and values
# ---------------------------------------------------------------------------------------------
def fnum(v) -> str:
    """7, 3.5 (halves only), else a/b."""
    v = F(v)
    if v.denominator == 1:
        return str(v.numerator)
    if v.denominator == 2:
        return f"{v.numerator // 2}.5"
    return f"{v.numerator}/{v.denominator}"


def P(c):
    """c times π, c a whole number >= 1."""
    c = F(c)
    if c.denominator != 1 or c <= 0:
        return None
    n = c.numerator
    return ("π" if n == 1 else f"{n}π", ("pi", n))


def N(v):
    """A plain number: a whole number or a half (3.5)."""
    v = F(v)
    if v <= 0 or v.denominator not in (1, 2):
        return None
    return (fnum(v), ("num", v))


def Q(v):
    """A plain whole number or fraction (1/4): scale factors."""
    v = F(v)
    if v <= 0:
        return None
    text = str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    return (text, ("num", v))


def PP(a, b):
    """aπ + b."""
    a, b = F(a), F(b)
    if a.denominator != 1 or b.denominator != 1 or a <= 0 or b <= 0:
        return None
    a, b = a.numerator, b.numerator
    return (f"{'' if a == 1 else a}π + {b}", ("piplus", a, b))


def T(text):
    """A word or a formula, compared as text."""
    return (text, ("txt", text))


def magnitude(key) -> int:
    kind = key[0]
    if kind in ("pi", "num"):
        return key[1]
    if kind == "piplus":
        return max(key[1], key[2])
    return 0


# ---------------------------------------------------------------------------------------------
# Working, as steps (op, a, b, result)
# ---------------------------------------------------------------------------------------------
def _mul(a, b):
    return (MUL, a, b, F(a) * F(b))


def _div(a, b):
    return (DIV, a, b, F(a) / F(b))


def _add(a, b):
    return (ADD, a, b, F(a) + F(b))


def half_product(a, b):
    """Steps for a × b ÷ 2 that stay in the times tables: halve an even factor of 4+ first, else
    multiply and halve a product of 20 or less. None when neither works or the result is odd."""
    for x, y in ((a, b), (b, a)):
        if x % 2 == 0 and x // 2 >= 2:
            return [_div(x, 2), _mul(x // 2, y)]
    p = a * b
    if p % 2 == 0 and 2 <= p // 2 <= 10:
        return [_mul(a, b), _div(p, 2)]
    return None


def steps_ok(steps) -> bool:
    """THE bounds gate (manifest ``bounds``): × factors 1-10; ÷ exact with divisor and quotient 2-10 (a
    halved odd number may end in .5); + joins values of 20 or less; every result 1-100."""
    if steps is None:
        return False
    for op, a, b, r in steps:
        a, b, r = F(a), F(b), F(r)
        if op == MUL:
            ok = 1 <= a <= 10 and 1 <= b <= 10 and r.denominator == 1
        elif op == DIV:
            ok = (a.denominator == 1 and a <= MAX_VALUE and 2 <= b <= 10 and 2 <= r <= 10
                  and (r.denominator == 1 or (r.denominator == 2 and b == 2)))
        elif op == ADD:
            ok = 1 <= a <= 20 and 1 <= b <= 20 and r.denominator == 1
        else:
            ok = False
        if not ok or not 1 <= r <= MAX_VALUE:
            return False
    return True


def say(steps) -> str:
    return ", ".join(f"{fnum(a)} {op} {fnum(b)} = {fnum(r)}" for op, a, b, r in steps)


# ---------------------------------------------------------------------------------------------
# Kinds: frames x params, solver
# ---------------------------------------------------------------------------------------------
FIELD_RX = {
    "r": r"(?P<r>\d+)", "d": r"(?P<d>\d+)", "c": r"(?P<c>\d+)", "a": r"(?P<a>\d+)", "b": r"(?P<b>\d+)",
    "w": r"(?P<w>doubles|triples|quadruples|is halved)",
}
SCALE = {"doubles": F(2), "triples": F(3), "quadruples": F(4), "is halved": F(1, 2)}
KINDS = {}


def _fields(frame: str) -> tuple:
    return tuple(re.findall(r"\{(\w+)\}", frame))


def _frame_regex(frame: str):
    parts = re.split(r"\{(\w+)\}", frame)
    rx = "".join(re.escape(p) if i % 2 == 0 else FIELD_RX[p] for i, p in enumerate(parts))
    return re.compile("^" + rx + "$")


class Kind:
    def __init__(self, name, frames, params, solver, entries=None):
        self.name, self.frames, self.params, self.solver, self.entries = name, frames, params, solver, entries
        self.regexes = [(f, _frame_regex(f)) for f in frames]

    def candidates(self):
        """[(group, prompt)] in a fixed order; a group is one parameter choice (several wordings)."""
        if self.entries is not None:
            return [(p, p) for p in self.entries]
        out = []
        for params in self.params:
            group = tuple(sorted(params.items()))
            for frame in self.frames:
                if set(_fields(frame)) == set(params):
                    out.append((group, frame.format(**params)))
        return out


def kind(name, frames, params):
    def deco(fn):
        KINDS[name] = Kind(name, frames, params, fn)
        return fn
    return deco


def rng_of(lo, hi, key="r", skip=()):
    return [{key: v} for v in range(lo, hi + 1) if v not in skip]


# ---- Tier 1: radius, diameter, π -------------------------------------------------------------
@kind("r2d", [
    "Circle: radius {r}. Diameter?",
    "A wheel has radius {r}. Its diameter?",
    "A pizza has radius {r}. Its diameter?",
    "A pond has radius {r}. What is its diameter?",
    "Radius {r}. What is the diameter of the circle?",
], rng_of(2, 10))
def _r2d(r):
    s = [_mul(2, r)]
    return dict(correct=N(2 * r), steps=s, expl=f"Diameter = 2 × radius: {say(s)}.",
                wrong=[("HALVED_FOR_DOUBLED", N(F(r, 2))), ("SAME_NUMBER", N(r)), ("C_FOR_D", P(2 * r))])


@kind("d2r", [
    "Circle: diameter {d}. Radius?",
    "A wheel has diameter {d}. Its radius?",
    "A pizza has diameter {d}. Its radius?",
    "A pond has diameter {d}. What is its radius?",
    "Diameter {d}. What is the radius of the circle?",
], rng_of(4, 10, "d"))
def _d2r(d):
    s = [_div(d, 2)]
    return dict(correct=N(F(d, 2)), steps=s, expl=f"Radius = diameter ÷ 2: {say(s)}.",
                wrong=[("DOUBLED_FOR_HALVED", N(2 * d)), ("SAME_NUMBER", N(d)), ("HALVED_TWICE", N(F(d, 4)))])


@kind("ratio_d", [
    "Circle: radius {r}. Circumference ÷ diameter?",
    "A wheel has radius {r}. Circumference ÷ diameter?",
    "Circle: diameter {d}. Circumference ÷ diameter?",
    "A wheel has diameter {d}. Circumference ÷ diameter?",
], rng_of(2, 10) + rng_of(2, 10, "d"))
def _ratio_d(r=None, d=None):
    size = r if r is not None else d
    return dict(correct=P(1), steps=[], expl="Circumference ÷ diameter is π for every circle, big or small.",
                wrong=[("SIZE_MATTERS", N(size)), ("TWO_PI", P(2)), ("INVERTED", T("1/π"))])


@kind("ratio_r", [
    "Circle: radius {r}. Circumference ÷ radius?",
    "A wheel has radius {r}. Circumference ÷ radius?",
], rng_of(2, 10))
def _ratio_r(r):
    return dict(correct=P(2), steps=[], expl="C = 2πr, so circumference ÷ radius = 2π.",
                wrong=[("DIAMETER_RATIO", P(1)), ("SIZE_MATTERS", N(r)), ("INVERTED", T("1/(2π)"))])


# ---- Tier 2: circumference -------------------------------------------------------------------
@kind("c_rad", [
    "Circle: radius {r}. Circumference?",
    "A wheel has radius {r}. Its circumference?",
    "A pond has radius {r}. Distance around it?",
    "A wheel with radius {r} rolls once. How far does it go?",
    "Ribbon around a round cake, radius {r}. Ribbon length?",
], rng_of(3, 10))
def _c_rad(r):
    s = [_mul(2, r)]
    return dict(correct=P(2 * r), steps=s, expl=f"Circumference = 2 × π × radius: {say(s)}, so {2 * r}π.",
                wrong=[("R_FOR_D", P(r)), ("AREA_FOR_C", P(r * r)), ("DOUBLED_D", P(4 * r)), ("NO_PI", N(2 * r))])


@kind("c_dia", [
    "Circle: diameter {d}. Circumference?",
    "A wheel has diameter {d}. Its circumference?",
    "A pond has diameter {d}. Distance around it?",
    "A wheel with diameter {d} rolls once. How far does it go?",
    "Ribbon around a round cake, diameter {d}. Ribbon length?",
], rng_of(3, 10, "d", skip=(4,)))
def _c_dia(d):
    return dict(correct=P(d), steps=[], expl=f"Circumference = π × diameter = {d}π.",
                # AREA_FOR_C: the circle's area (an odd diameter has no whole half, so then the diameter itself is squared)
                wrong=[("DOUBLED_D", P(2 * d)), ("R_FOR_D", P(F(d, 2))),
                       ("AREA_FOR_C", P(F(d, 2) ** 2) or P(d * d)), ("NO_PI", N(d))])


SCALE_FRAMES_C = ["Radius {w}. Circumference is how many times as long?"]
SCALE_FRAMES_A = ["Radius {w}. Area is how many times as big?"]
SCALE_PARAMS = [{"w": w} for w in ("doubles", "triples", "quadruples", "is halved")]
SCALE_POOL = [Q(x) for x in (F(1, 8), F(1, 4), F(1, 2), 1, 2, 3, 4, 6, 8, 9, 12, 16)]


@kind("scale_c", SCALE_FRAMES_C, SCALE_PARAMS)
def _scale_c(w):
    k = SCALE[w]
    return dict(correct=Q(k), steps=[], expl=f"Circumference is proportional to the radius, so it changes by the same factor: {Q(k)[0]}.",
                wrong=[("SQUARED_SCALE", Q(k * k)), ("CUBED_SCALE", Q(k ** 3))], pool=SCALE_POOL)


# ---- Tier 3: area ----------------------------------------------------------------------------
@kind("a_rad", [
    "Circle: radius {r}. Area?",
    "A rug has radius {r}. Its area?",
    "A pizza has radius {r}. Its area?",
    "A drum top has radius {r}. Its area?",
    "A sprinkler waters a circle, radius {r}. Area?",
], rng_of(3, 10))
def _a_rad(r):
    s = [_mul(r, r)]
    return dict(correct=P(r * r), steps=s, expl=f"Area = π × radius × radius: {say(s)}, so {r * r}π.",
                wrong=[("C_FOR_AREA", P(2 * r)), ("DOUBLED_RADIUS", P(4 * r * r)), ("NO_SQUARE", P(r)),
                       ("NO_PI", N(r * r))])


@kind("a_dia", [
    "Circle: diameter {d}. Area?",
    "A rug has diameter {d}. Its area?",
    "A pizza has diameter {d}. Its area?",
    "A drum top has diameter {d}. Its area?",
    "A sprinkler waters a circle, diameter {d}. Area?",
], [{"d": d} for d in (6, 8, 10)])
def _a_dia(d):
    r = d // 2
    s = [_div(d, 2), _mul(r, r)]
    return dict(correct=P(r * r), steps=s, expl=f"Radius = {d} ÷ 2 = {r}. Area = π × {r} × {r} = {r * r}π.",
                wrong=[("D_FOR_R", P(d * d)), ("C_FOR_AREA", P(d)), ("NO_SQUARE", P(r)), ("NO_PI", N(r * r))])


@kind("scale_a", SCALE_FRAMES_A, SCALE_PARAMS)
def _scale_a(w):
    k = SCALE[w]
    return dict(correct=Q(k * k), steps=[], expl=f"Area uses r × r, so the factor is squared: {Q(k)[0]} × {Q(k)[0]} = {Q(k * k)[0]}.",
                wrong=[("SAME_SCALE", Q(k)), ("CUBED_SCALE", Q(k ** 3))], pool=SCALE_POOL)


@kind("two_circ", [
    "Two circles: radius {a} and radius {b}. Total area?",
    "A rug (radius {a}) and a mat (radius {b}). Total area?",
    "Two coins, radius {a} and radius {b}. Total area of both?",
], [{"a": a, "b": b} for a, b in ((2, 3), (2, 4), (3, 4))])
def _two_circ(a, b):
    s = [_mul(a, a), _mul(b, b), _add(a * a, b * b)]
    return dict(correct=P(a * a + b * b), steps=s,
                expl=f"Each area is π × r × r: {a * a}π and {b * b}π. Add: {a * a} + {b * b} = {a * a + b * b}, so {a * a + b * b}π.",
                wrong=[("SUM_RADII", P((a + b) ** 2)), ("C_FOR_AREA", P(2 * a + 2 * b)), ("ONE_CIRCLE", P(b * b))])


# ---- Tier 4: work backward, estimate ---------------------------------------------------------
@kind("back_r", [
    "Circle: circumference {c}π. Radius?",
    "A wheel's circumference is {c}π. Its radius?",
    "A pond's distance around is {c}π. Its radius?",
    "Circumference {c}π. What is the radius?",
], [{"c": c} for c in range(4, 21, 2)])
def _back_r(c):
    s = [_div(c, 2)]
    return dict(correct=N(c // 2), steps=s, expl=f"C = 2πr, so the radius is {c} ÷ 2 = {c // 2}.",
                wrong=[("GAVE_DIAMETER", N(c)), ("WRONG_WAY", N(2 * c)), ("HALVED_TWICE", N(F(c, 4)))])


@kind("back_d", [
    "Circle: circumference {c}π. Diameter?",
    "A wheel's circumference is {c}π. Its diameter?",
    "Circumference {c}π. What is the diameter?",
], rng_of(3, 10, "c"))
def _back_d(c):
    return dict(correct=N(c), steps=[], expl=f"C = π × diameter, so {c}π means the diameter is {c}.",
                wrong=[("GAVE_RADIUS", N(F(c, 2))), ("WRONG_WAY", N(2 * c))])


@kind("back_area", [
    "Circle: circumference {c}π. Area?",
    "A rug's distance around is {c}π. Its area?",
    "A pond's distance around is {c}π. Area of the pond?",
], [{"c": c} for c in range(4, 21, 2)])
def _back_area(c):
    r = c // 2
    s = [_div(c, 2), _mul(r, r)]
    return dict(correct=P(r * r), steps=s, expl=f"C = 2πr gives r = {c} ÷ 2 = {r}. Area = π × {r} × {r} = {r * r}π.",
                wrong=[("D_FOR_R", P(c * c)), ("C_FOR_AREA", P(c)), ("NO_SQUARE", P(r)), ("NO_PI", N(r * r))])


@kind("est_c", [
    "Radius {r}. Circumference? Use 3 for π.",
    "A wheel has radius {r}. Circumference? Use 3 for π.",
    "A pond has radius {r}. Distance around it? Use 3 for π.",
    "Diameter {d}. Circumference? Use 3 for π.",
    "A wheel has diameter {d}. Circumference? Use 3 for π.",
    "A pond has diameter {d}. Distance around it? Use 3 for π.",
], rng_of(3, 10) + rng_of(3, 10, "d", skip=(4,)))
def _est_c(r=None, d=None):
    if r is not None:
        s = [_mul(2, 3), _mul(6, r)]
        return dict(correct=N(6 * r), steps=s, expl=f"C = 2 × 3 × radius: {say(s)}.",
                    wrong=[("AREA_FOR_C", N(3 * r * r)), ("R_FOR_D", N(3 * r)), ("DOUBLED_D", N(12 * r)),
                           ("NO_PI", N(2 * r))])
    s = [_mul(3, d)]
    return dict(correct=N(3 * d), steps=s, expl=f"C = 3 × diameter: {say(s)}.",
                wrong=[("DOUBLED_D", N(6 * d)), ("R_FOR_D", N(F(3 * d, 2))), ("AREA_FOR_C", N(F(3 * d * d, 4))),
                       ("NO_PI", N(d))])


@kind("est_area", [
    "Radius {r}. Area? Use 3 for π.",
    "A rug has radius {r}. Its area? Use 3 for π.",
    "A drum top has radius {r}. Area? Use 3 for π.",
    "Diameter {d}. Area? Use 3 for π.",
    "A rug has diameter {d}. Its area? Use 3 for π.",
    "A drum top has diameter {d}. Area? Use 3 for π.",
], [{"r": 3}, {"d": 6}])
def _est_area(r=None, d=None):
    squared = "DOUBLED_RADIUS"  # a radius was given: doubling it first is the slip
    if r is None:
        r = d // 2
        s = [_div(d, 2)]
        squared = "D_FOR_R"  # a diameter was given: squaring it as if it were the radius
    else:
        s = []
    s += [_mul(r, r), _mul(3, r * r)]
    return dict(correct=N(3 * r * r), steps=s, expl=f"Area = 3 × radius × radius: radius {r}, {r} × {r} = {r * r}, 3 × {r * r} = {3 * r * r}.",
                wrong=[("C_FOR_AREA", N(6 * r)), ("NO_SQUARE", N(3 * r)), (squared, N(12 * r * r)),
                       ("NO_PI", N(r * r))])


@kind("est_back_r", [
    "Circle: circumference {c}. Radius? Use 3 for π.",
    "A wheel's circumference is {c}. Its radius? Use 3 for π.",
    "A pond's distance around is {c}. Radius? Use 3 for π.",
], [{"c": 6 * r} for r in range(2, 11)])
def _est_back_r(c):
    r = c // 6
    return dict(correct=N(r), steps=[_div(c, 6)], expl=f"C = 2 × 3 × radius = 6 × radius, so radius = {c} ÷ 6 = {r}.",
                wrong=[("GAVE_DIAMETER", N(c // 3)), ("FORGOT_PI", N(c // 2)), ("HALVED_TWICE", N(F(c, 12)))])


@kind("est_back_d", [
    "Circle: circumference {c}. Diameter? Use 3 for π.",
    "A wheel's circumference is {c}. Its diameter? Use 3 for π.",
    "A pond's distance around is {c}. Diameter? Use 3 for π.",
], [{"c": 3 * d} for d in range(3, 11)])
def _est_back_d(c):
    d = c // 3
    return dict(correct=N(d), steps=[_div(c, 3)], expl=f"C = 3 × diameter, so diameter = {c} ÷ 3 = {d}.",
                wrong=[("GAVE_RADIUS", N(F(c, 6))), ("FORGOT_PI", N(c)), ("WRONG_WAY", N(3 * c))])


# ---- Tier 5: half and quarter circles --------------------------------------------------------
@kind("semi_a", [
    "Semicircle: radius {r}. Area?",
    "Half of a circle has radius {r}. Area of the half?",
    "A half-circle rug has radius {r}. Its area?",
    "A half-circle window has radius {r}. Its area?",
    "Semicircle: diameter {d}. Area?",
    "A half-circle rug has diameter {d}. Its area?",
], [{"r": r} for r in (4, 6, 8, 10)] + [{"d": 8}])
def _semi_a(r=None, d=None):
    lead = []
    if r is None:
        r = d // 2
        lead = [_div(d, 2)]
    hp = half_product(r, r)
    steps = (lead + hp) if hp else None
    area = r * r // 2
    return dict(correct=P(area), steps=steps,
                expl=f"Half of π × r × r with r = {r}: {say(hp or [])}, so {area}π.",
                wrong=[("WHOLE_CIRCLE", P(r * r)), ("HALVED_RADIUS", P(F(r, 2) ** 2)), ("ARC_FOR_AREA", P(r))])


@kind("quart_a", [
    "Quarter circle: radius {r}. Area?",
    "A quarter of a circle has radius {r}. Its area?",
    "A quarter-circle rug has radius {r}. Its area?",
    "A quarter-circle garden has radius {r}. Its area?",
    "A pizza slice is a quarter circle, radius {r}. Area?",
], [{"r": r} for r in (4, 6, 8, 10)])
def _quart_a(r):
    q = r // 2
    s = [_div(r, 2), _mul(q, q)]
    return dict(correct=P(q * q), steps=s, expl=f"A quarter circle is (r ÷ 2) × (r ÷ 2) × π: {say(s)}, so {q * q}π.",
                wrong=[("WHOLE_CIRCLE", P(r * r)), ("HALF_FOR_QUARTER", P(r * r // 2)), ("NO_SQUARE", P(q)),
                       ("QUARTERED_RADIUS", P(F(r, 4) ** 2))])


@kind("semi_arc", [
    "Semicircle: radius {r}. Length of the curved edge?",
    "A half-circle rug has radius {r}. Curved edge length?",
    "A half-circle window has radius {r}. Curved edge length?",
    "Semicircle: diameter {d}. Length of the curved edge?",
    "A half-circle rug has diameter {d}. Curved edge length?",
], rng_of(3, 10) + rng_of(6, 10, "d", skip=(7, 9)))
def _semi_arc(r=None, d=None):
    if r is not None:
        return dict(correct=P(r), steps=[], expl=f"Half of the circumference 2πr is πr = {r}π.",
                    wrong=[("WHOLE_CIRCLE", P(2 * r)), ("PERIMETER_NOT_ARC", PP(r, 2 * r)),
                           ("AREA_FOR_ARC", P(F(r * r, 2)))])
    h = d // 2
    return dict(correct=P(h), steps=[_div(d, 2)], expl=f"Half of the circumference πd is {d}π ÷ 2 = {h}π.",
                wrong=[("WHOLE_CIRCLE", P(d)), ("PERIMETER_NOT_ARC", PP(h, d)), ("AREA_FOR_ARC", P(F(d * d, 8)))])


@kind("quart_arc", [
    "Quarter circle: radius {r}. Length of the curved edge?",
    "A quarter-circle rug has radius {r}. Curved edge length?",
], [{"r": r} for r in (4, 6, 8, 10)])
def _quart_arc(r):
    q = r // 2
    return dict(correct=P(q), steps=[_div(r, 2)], expl=f"A quarter of the circumference 2πr is πr ÷ 2 = {r}π ÷ 2 = {q}π.",
                wrong=[("HALF_FOR_QUARTER", P(r)), ("WHOLE_CIRCLE", P(2 * r)), ("AREA_FOR_ARC", P(q * q))])


@kind("semi_p", [
    "Semicircle: radius {r}. Perimeter, flat side included?",
    "Rug: half circle, radius {r}. Distance all the way around?",
    "Semicircle: diameter {d}. Perimeter, flat side included?",
    "Rug: half circle, diameter {d}. Distance all the way around?",
], rng_of(3, 10) + rng_of(4, 10, "d", skip=(5, 7, 9)))
def _semi_p(r=None, d=None):
    if r is not None:
        s = [_mul(2, r)]
        return dict(correct=PP(r, 2 * r), steps=s,
                    expl=f"Curved edge πr = {r}π, flat side = diameter = {say(s)}. Total {r}π + {2 * r}.",
                    wrong=[("ARC_ONLY", P(r)), ("WHOLE_C_PLUS", PP(2 * r, 2 * r)), ("HALF_C_PLUS_R", PP(r, r))])
    h = d // 2
    return dict(correct=PP(h, d), steps=[_div(d, 2)],
                expl=f"Curved edge = half of {d}π = {h}π. Flat side = the diameter, {d}. Total {h}π + {d}.",
                wrong=[("ARC_ONLY", P(h)), ("WHOLE_C_PLUS", PP(d, d)), ("HALF_C_PLUS_R", PP(h, h))])


# ---------------------------------------------------------------------------------------------
# Hand-written concept questions (BANKS): prompt -> correct, modelled wrong, ARITH pool, explanation
# ---------------------------------------------------------------------------------------------
def _bank(entries):
    out = {}
    for prompt, (correct, wrong, arith, expl) in entries.items():
        out[prompt] = dict(correct=correct, steps=[], expl=expl, wrong=wrong, pool=arith)
    return out


BANK1 = _bank({
    "Circumference ÷ diameter = ?": (
        P(1), [("TWO_PI", P(2)), ("INVERTED", T("1/π"))], [T("π/2")],
        "Circumference ÷ diameter is π for every circle. That is what π means."),
    "Pi (π) is circumference divided by what?": (
        T("diameter"), [("R_FOR_D", T("radius")), ("AREA_FOR_C", T("radius^2")), ("VOCAB_MIX", T("area"))], [],
        "π = circumference ÷ diameter, so circumference = π × diameter."),
    "A string around a circle is about how many diameters?": (
        N(3), [("RADII_COUNT", N(6)), ("SQUARE_AROUND", N(4))], [N(2)],
        "Circumference = π × diameter, and π is a little more than 3: about 3 diameters."),
    "A string around a circle is about how many radii?": (
        N(6), [("DIAMETER_COUNT", N(3)), ("SQUARE_AROUND", N(8))], [N(12)],
        "About 3 diameters, and each diameter is 2 radii: 3 × 2 = 6 radii."),
    "Circumference ÷ radius = ?": (
        P(2), [("DIAMETER_RATIO", P(1)), ("INVERTED", T("1/(2π)"))], [P(4)],
        "C = 2πr, so circumference ÷ radius = 2π."),
    "Distance around a circle is its?": (
        T("circumference"), [("VOCAB_MIX", T("diameter")), ("VOCAB_MIX", T("radius")), ("VOCAB_MIX", T("area"))], [],
        "The circumference is the distance around a circle."),
    "A line across a circle through its center is called?": (
        T("diameter"), [("VOCAB_MIX", T("radius")), ("VOCAB_MIX", T("circumference")), ("VOCAB_MIX", T("area"))], [],
        "A diameter goes straight across, through the center."),
    "A line from the center to the edge is called?": (
        T("radius"), [("VOCAB_MIX", T("diameter")), ("VOCAB_MIX", T("circumference")), ("VOCAB_MIX", T("area"))], [],
        "A radius goes from the center out to the edge. A diameter is 2 radii."),
})

BANK2 = _bank({
    "Circumference formula, using radius r?": (
        T("2πr"), [("AREA_FOR_C", T("πr^2")), ("R_FOR_D", T("πr")), ("DOUBLED_D", T("4πr"))], [],
        "Circumference = 2 × π × r. With the diameter d = 2r, that is πd."),
    "Circumference formula, using diameter d?": (
        T("πd"), [("DOUBLED_D", T("2πd")), ("AREA_FOR_C", T("πd^2")), ("R_FOR_D", T("πd/2"))], [],
        "Circumference = π × diameter. With the radius it is 2πr."),
})

BANK3 = _bank({
    "Area formula, using radius r?": (
        T("πr^2"), [("C_FOR_AREA", T("2πr")), ("NO_SQUARE", T("πr")), ("D_FOR_R", T("πd^2"))], [],
        "Area = π × r × r = πr^2."),
    "Area of a circle is π times what?": (
        T("radius^2"), [("NO_SQUARE", T("radius")), ("C_FOR_AREA", T("diameter")), ("D_FOR_R", T("diameter^2"))], [],
        "Area = π × radius × radius: π times the radius squared."),
    "Radius × radius × π gives a circle's what?": (
        T("area"), [("VOCAB_MIX", T("circumference")), ("VOCAB_MIX", T("diameter")), ("VOCAB_MIX", T("radius"))], [],
        "π × r × r is the area, the space inside the circle."),
})

for _name, _bank_entries in (("bank1", BANK1), ("bank2", BANK2), ("bank3", BANK3)):
    KINDS[_name] = Kind(_name, list(_bank_entries), [], None, entries=_bank_entries)


# ---------------------------------------------------------------------------------------------
# Solving a prompt from its own text
# ---------------------------------------------------------------------------------------------
def solve(prompt: str) -> dict:
    """Read a prompt's own text and solve it. ``wrong`` keeps every modelled (label, value), in label
    priority order, including values equal to the answer or that cannot be shown (None)."""
    for k in KINDS.values():
        if k.entries is not None:
            if prompt in k.entries:
                return dict(k.entries[prompt])
            continue
        for _, rx in k.regexes:
            m = rx.match(prompt)
            if m:
                params = {key: (v if key == "w" else int(v)) for key, v in m.groupdict().items()}
                return k.solver(**params)
    raise ValueError(f"no template matches {prompt!r}")


def misconception_values(sol: dict) -> list:
    """[(label, value)] usable distinct wrong values: different from the answer and from every earlier
    label, shown within the door's width, at most 999."""
    seen = {sol["correct"][1]}
    out = []
    for lab, v in sol["wrong"]:
        if v is None or v[1] in seen or magnitude(v[1]) > MAX_DISTRACTOR or len(v[0]) > MAX_CHOICE:
            continue
        seen.add(v[1])
        out.append((lab, v))
    return out


def in_range(value) -> bool:
    key = value[1]
    if key[0] == "txt":
        return True
    return 0 < magnitude(key) <= MAX_VALUE


def check(prompt: str):
    """The solved prompt when it is usable in an item, else None."""
    if len(prompt) > MAX_PROMPT:
        return None
    sol = solve(prompt)
    c = sol["correct"]
    if c is None or not in_range(c) or not steps_ok(sol["steps"]) or len(sol["expl"]) > 160:
        return None
    if any(v is not None and v[1] == c[1] for _, v in sol["wrong"]):
        return None  # a wrong rule lands on the right door: not a usable prompt
    if not misconception_values(sol):
        return None
    return sol


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def near(value) -> list:
    """ARITH candidates around the correct value, same shape."""
    key = value[1]
    deltas = (1, -1, 2, -2, 3, -3, 4, -4, 5, -5)
    if key[0] == "pi":
        return [P(key[1] + d) for d in deltas]
    if key[0] == "num":
        return [N(key[1] + d) for d in deltas]
    if key[0] == "piplus":
        return [PP(key[1] + d, key[2]) for d in deltas] + [PP(key[1], key[2] + d) for d in deltas]
    return []


def make_item(prompt: str, tier: int, answer_pos: int, rng: random.Random):
    sol = check(prompt)
    if sol is None:
        raise ValueError(f"unusable prompt {prompt!r}")
    c = sol["correct"]
    wrong = misconception_values(sol)
    head, tail = wrong[:1], wrong[1:]
    rng.shuffle(tail)
    chosen = (head + tail)[:3]
    used = {c[1]} | {v[1] for _, v in sol["wrong"] if v is not None}
    pool = list(sol.get("pool") or near(c))
    if sol.get("pool") is None:
        near_part, far_part = pool[:4], pool[4:]
        rng.shuffle(near_part)
        pool = near_part + far_part
    elif len(sol["pool"]) > 3:
        rng.shuffle(pool)
    for v in pool:
        if len(chosen) == 3:
            break
        if v is None or v[1] in used or len(v[0]) > MAX_CHOICE:
            continue
        used.add(v[1])
        chosen.append(("ARITH", v))
    if len(chosen) < 3:
        raise ValueError(f"cannot fill 4 choices for {prompt!r}")
    rng.shuffle(chosen)
    pairs = chosen[:answer_pos] + [(None, c)] + chosen[answer_pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [v[0] for _, v in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": sol["expl"],
    }


# tier -> [(kind, quota)]
PLAN = {
    1: [("r2d", 12), ("d2r", 11), ("ratio_d", 6), ("ratio_r", 3), ("bank1", 8)],
    2: [("c_rad", 17), ("c_dia", 17), ("scale_c", 4), ("bank2", 2)],
    3: [("a_rad", 18), ("a_dia", 10), ("two_circ", 5), ("scale_a", 4), ("bank3", 3)],
    4: [("back_r", 7), ("back_d", 3), ("back_area", 8), ("est_c", 9), ("est_area", 4), ("est_back_r", 6),
        ("est_back_d", 3)],
    5: [("semi_a", 9), ("quart_a", 9), ("semi_arc", 8), ("quart_arc", 3), ("semi_p", 11)],
}


def usable_pool(name: str) -> dict:
    """{group: [prompt, ...]} of the kind's usable prompts, in a fixed order."""
    groups: dict = {}
    for group, prompt in KINDS[name].candidates():
        if check(prompt) is not None:
            groups.setdefault(group, []).append(prompt)
    return groups


def pick(name: str, quota: int, rng: random.Random) -> list:
    """quota prompts: every parameter once before any repeats, each under a random wording."""
    groups = usable_pool(name)
    order = list(groups)
    rng.shuffle(order)
    out = []
    while len(out) < quota:
        progressed = False
        for g in order:
            if len(out) == quota:
                break
            if groups[g]:
                out.append(groups[g].pop(rng.randrange(len(groups[g]))))
                progressed = True
        if not progressed:
            raise RuntimeError(f"{name}: only {len(out)} usable prompts, need {quota}")
    return out


def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def gen_tier(tier: int, count: int, rng: random.Random) -> list:
    prompts = []
    for name, quota in PLAN[tier]:
        prompts += pick(name, quota, rng) if quota else []
    assert len(prompts) == count, (tier, len(prompts), count)
    rng.shuffle(prompts)
    positions = _balanced(count, 4, rng)
    return [make_item(p, tier, pos, rng) for p, pos in zip(prompts, positions)]


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
