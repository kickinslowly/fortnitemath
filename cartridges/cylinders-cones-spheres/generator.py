"""Procedural generator for cylinders-cones-spheres (fnm-cart/1), grade 8, CCSS 8.G.C.9.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* A *Kind* is a family of prompts: wording frames, a list of parameter dicts and a ``solve`` function that returns
  the correct value, every modelled misconception's value (in a list, ``None`` when it cannot be shown), the
  explanation and the *hidden steps* of the working.
* A value is ``(text, key)``: the choice text and a canonical key (an exact Fraction), so two choices that are
  equal in value can never both be offered.
* ``steps`` are the mental-math steps of the correct working. ``steps_ok`` is the manifest ``bounds`` gate on them
  (PROTOCOL §4a/§4b "π volumes"). A parameter set with no admissible route is simply not generated.
* A modelled misconception whose value equals the correct one is dropped for that item. An item needs at least
  two real misconceptions; ``ARITH`` fills the rest.
* Each tier draws its quota from every kind's pool; a kind uses each parameter set once before reusing one under
  another wording.
"""
from __future__ import annotations

import random
from fractions import Fraction as F
from functools import lru_cache

MAX_PROMPT, MAX_CHOICE, MAX_EXPL = 60, 14, 160
MAX_DISTRACTOR = 999


# ---------------------------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------------------------
def Pi(c):
    """c times π. c a positive Fraction: 36π, π, (4/3)π, (32/3)π."""
    c = F(c)
    if c <= 0 or c > MAX_DISTRACTOR:
        return None
    if c.denominator == 1:
        text = "π" if c == 1 else f"{c.numerator}π"
    else:
        text = f"({c.numerator}/{c.denominator})π"
    return (text, ("pi", c)) if len(text) <= MAX_CHOICE else None


def Num(v):
    """A plain whole number or fraction: 20, 1/4."""
    v = F(v)
    if v <= 0 or v > MAX_DISTRACTOR:
        return None
    text = str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    return (text, ("num", v)) if len(text) <= MAX_CHOICE else None


def Txt(s):
    return (s, ("txt", s))


# ---------------------------------------------------------------------------------------------
# Hidden steps and the bounds gate
# ---------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _dfs(vals, div):
    """Steps that fold the sorted values ``vals`` into one (and divide once by ``div`` if given), or None."""
    if len(vals) <= 1 and div is None:
        return ()
    if div is not None and 2 <= div <= 10:
        for v in sorted(set(vals)):
            if v <= 100 and v % div == 0 and 2 <= v // div <= 10:
                rest = list(vals)
                rest.remove(v)
                rest.append(v // div)
                r = _dfs(tuple(sorted(rest)), None)
                if r is not None:
                    return (("÷", v, div, v // div),) + r
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i], vals[j]
            if a <= 10 and b <= 10 and a * b <= 100:
                rest = [x for k, x in enumerate(vals) if k not in (i, j)] + [a * b]
                r = _dfs(tuple(sorted(rest)), div)
                if r is not None:
                    return (("×", a, b, a * b),) + r
    return None


def find_steps(factors, divisor=None):
    """Times-table route to prod(factors) / divisor, as a list of (op, a, b, result), or None."""
    vals = tuple(sorted(int(f) for f in factors if f != 1))
    r = _dfs(vals, divisor)
    return None if r is None else list(r)


def steps_ok(steps):
    """The manifest bounds on hidden steps: PROTOCOL §4a (× ÷), plus halving a diameter and perfect roots."""
    for op, a, b, res in steps:
        if op == "×":
            ok = 1 <= a <= 10 and 1 <= b <= 10 and a * b == res <= 100
        elif op == "÷":
            ok = 2 <= b <= 10 and a <= 100 and a % b == 0 and a // b == res and 2 <= res <= 10
        elif op == "half":
            ok = b == 2 and a == 2 * res and 1 <= res <= 5
        elif op == "root2":
            ok = a == res * res and 1 <= res <= 10
        elif op == "root3":
            ok = a == res ** 3 and res in (1, 2, 3, 4)
        else:
            ok = False
        if not ok:
            return False
    return True


# ---------------------------------------------------------------------------------------------
# Kinds
# ---------------------------------------------------------------------------------------------
class Case:
    def __init__(self, prompt, correct, miscs, expl, steps):
        self.prompt, self.correct, self.expl, self.steps = prompt, correct, expl, steps
        self.miscs = miscs  # [(KEY, Value | None)]
        self.wrong = {k: (v[0] if v else None) for k, v in miscs}  # key -> text, for tests

    @property
    def text(self):
        return self.correct[0]


class Kind:
    def __init__(self, name, frames, params, solve):
        self.name, self.frames, self.params, self.solve = name, frames, params, solve

    def case(self, frame, **p):
        out = self.solve(**p)
        if out is None:
            return None
        correct, miscs, expl, steps = out
        if correct is None or steps is None or not steps_ok(steps):
            return None
        return Case(self.frames[frame].format(**p), correct, miscs, expl, steps)


def _radius(dim, x):
    """(radius, halving steps) from a radius or diameter."""
    if dim == "radius":
        return x, []
    return x // 2, [("half", x, 2, x // 2)]


def _plain(n):
    return str(F(n).numerator) if F(n).denominator == 1 else f"{F(n).numerator}/{F(n).denominator}"


def _frac_or_none(v, whole=False):
    v = F(v)
    if whole and v.denominator != 1:
        return None
    return v


def _pi_or_none(v, whole=False):
    v = _frac_or_none(v, whole)
    return None if v is None else Pi(v)


# ---- Tier 1: cylinders -----------------------------------------------------------------------
def solve_cyl(dim, x, h):
    r, pre = _radius(dim, x)
    d = 2 * r
    c = r * r * h
    steps = find_steps([r, r, h])
    if steps is None:
        return None
    miscs = [
        ("NO_SQUARE", Pi(r * h)),
        ("LATERAL_AREA", Pi(2 * r * h)),
        ("FORGOT_HEIGHT", Pi(r * r)),
        ("ADDED_HEIGHT", Pi(r * r + h)),
    ]
    if dim == "diameter":
        miscs = [("DIAMETER_AS_RADIUS", Pi(d * d * h)), ("HALVED_AFTER_SQUARE", Pi(F(d * d * h, 2)))] + miscs
        expl = f"Radius = {x} ÷ 2 = {r}. Volume = π × {r} × {r} × {h} = {c}π."
    else:
        expl = f"Volume = π × r × r × h = π × {r} × {r} × {h} = {c}π."
    return Pi(c), miscs, expl, pre + steps


def solve_cyl_area(k, h):
    steps = find_steps([k, h])
    if steps is None:
        return None
    miscs = [("ADDED_HEIGHT", Pi(k + h)), ("FORGOT_HEIGHT", Pi(k)), ("AREA_AS_RADIUS", Pi(k * k * h))]
    return Pi(k * h), miscs, f"Volume = base area × height = {k}π × {h} = {k * h}π.", steps


BANK1 = [
    dict(prompt="Cylinder volume = base area × ?", correct="Height",
         wrongs=[("Radius", "FORMULA_MIX"), ("Diameter", "FORMULA_MIX"), ("Circumference", "FORMULA_MIX")],
         expl="Stack the circular base up the whole cylinder: volume = base area × height."),
    dict(prompt="A cylinder's base is a circle. Its area is?", correct="π × r × r",
         wrongs=[("2 × π × r", "CIRCUMFERENCE_FOR_AREA"), ("π × d × d", "DIAMETER_AS_RADIUS"),
                 ("π × r", "RADIUS_NOT_SQUARED")],
         expl="A circle's area is π × r × r. 2 × π × r measures around the edge."),
    dict(prompt="Same base area; B is taller. Which cylinder holds more?", correct="B (taller)",
         wrongs=[("A (shorter)", "SHORTER_HOLDS_MORE"), ("Same", "SAME_BASE_SAME_VOLUME"),
                 ("Can't tell", "CANT_TELL")],
         expl="Volume = base area × height. Same base, so the taller cylinder holds more."),
]


def solve_bank(prompt, correct, wrongs, expl):
    return Txt(correct), [(k, Txt(t)) for t, k in wrongs], expl, []


# ---- Tier 2: cones ---------------------------------------------------------------------------
def solve_cone(dim, x, h):
    r, pre = _radius(dim, x)
    d = 2 * r
    cyl = r * r * h
    if cyl % 3:
        return None
    c = F(cyl, 3)
    steps = find_steps([r, r, h], 3)
    if steps is None:
        return None
    miscs = [
        ("NO_THIRD", Pi(cyl)),
        ("HALF_FOR_THIRD", _pi_or_none(F(cyl, 2), True)),
        ("NO_SQUARE", _pi_or_none(F(r * h, 3), True)),
        ("TIMES_THREE", Pi(3 * cyl)),
    ]
    if dim == "diameter":
        miscs.insert(0, ("DIAMETER_AS_RADIUS", Pi(F(d * d * h, 3))))
        lead = f"Radius = {x} ÷ 2 = {r}. "
    else:
        lead = ""
    expl = f"{lead}Cylinder: {cyl}π. A cone is one third: {cyl}π ÷ 3 = {c}π."
    return Pi(c), miscs, expl, pre + steps


def solve_cone_from_cyl(c):
    if c % 3 or not 2 <= c // 3 <= 10:
        return None
    miscs = [("SAME_AS_CYLINDER", Pi(c)), ("HALF_FOR_THIRD", _pi_or_none(F(c, 2), True)), ("TIMES_THREE", Pi(3 * c))]
    return Pi(c // 3), miscs, f"A cone is one third of its cylinder: {c}π ÷ 3 = {c // 3}π.", [("÷", c, 3, c // 3)]


def solve_cyl_from_cone(v):
    miscs = [("SAME_AS_CONE", Pi(v)), ("DIVIDED_BY_THREE", Pi(F(v, 3))), ("ADDED_THREE", Pi(v + 3)),
             ("HALF_FOR_THIRD", Pi(2 * v))]
    return Pi(3 * v), miscs, f"Three cones fill the cylinder: {v}π × 3 = {3 * v}π.", [("×", v, 3, 3 * v)]


BANK2 = [
    dict(prompt="Same base and height: how many cones fill one cylinder?", correct="3",
         wrongs=[("2", "HALF_FOR_THIRD"), ("1", "SAME_AS_CYLINDER"), ("4", "ARITH")],
         expl="A cone is one third of the cylinder with the same base and height: 3 cones fill it."),
    dict(prompt="Cone and cylinder, same base and height. Cone is what part?", correct="1/3",
         wrongs=[("1/2", "HALF_FOR_THIRD"), ("3", "TIMES_THREE"), ("2/3", "SPHERE_FOR_CONE")],
         expl="Same base and height: the cone is one third of the cylinder."),
]


# ---- Tier 3: spheres --------------------------------------------------------------------------
def _sphere_core(r, factor, num):
    """Coefficient (num/3) r^3 as a Value with steps; only r = 1 (a fraction) and r = 3 (whole) are shown."""
    coef = F(num * r ** 3, 3)
    if r == 1:
        return coef, []
    if r != 3:
        return None, None
    return coef, find_steps([num, r, r, r], 3)


def solve_sphere(dim, x):
    r, pre = _radius(dim, x)
    d = 2 * r
    coef, steps = _sphere_core(r, 4, 4)
    if coef is None or steps is None:
        return None
    miscs = [
        ("NO_FOUR_THIRDS", Pi(r ** 3)),
        ("SQUARED_NOT_CUBED", Pi(F(4 * r * r, 3))),
        ("FOUR_NOT_THIRD", Pi(4 * r ** 3)),
        ("HEMI_FORMULA", Pi(F(2 * r ** 3, 3))),
    ]
    if dim == "diameter":
        miscs.insert(0, ("DIAMETER_AS_RADIUS", Pi(F(4 * d ** 3, 3))))
    lead = f"Radius = {x} ÷ 2 = {r}. " if dim == "diameter" else ""
    if r == 1:
        expl = lead + "Volume = (4/3) × π × 1 × 1 × 1 = (4/3)π."
    else:
        expl = lead + f"Volume = (4/3) × π × {r} × {r} × {r} = (4/3) × {r ** 3}π = {coef}π."
    return Pi(coef), miscs, expl, pre + steps


def solve_hemi(dim, x):
    r, pre = _radius(dim, x)
    d = 2 * r
    coef, steps = _sphere_core(r, 2, 2)
    if coef is None or steps is None:
        return None
    miscs = [
        ("WHOLE_FOR_HALF", Pi(F(4 * r ** 3, 3))),
        ("NO_TWO_THIRDS", Pi(r ** 3)),
        ("SQUARED_NOT_CUBED", Pi(F(2 * r * r, 3))),
    ]
    if dim == "diameter":
        miscs.insert(0, ("DIAMETER_AS_RADIUS", Pi(F(2 * d ** 3, 3))))
    lead = f"Radius = {x} ÷ 2 = {r}. " if dim == "diameter" else ""
    if r == 1:
        expl = lead + "A hemisphere is half a sphere: (2/3) × π × 1 × 1 × 1 = (2/3)π."
    else:
        expl = lead + f"Half a sphere: (2/3) × π × {r} × {r} × {r} = (2/3) × {r ** 3}π = {coef}π."
    return Pi(coef), miscs, expl, pre + steps


def solve_sphere3(shape, dim, x):
    """Sphere or hemisphere volume with 3 for π (the 3 cancels the thirds)."""
    r, pre = _radius(dim, x)
    d = 2 * r
    n = 4 if shape == "sphere" else 2
    steps = find_steps([n, r, r, r])
    if steps is None:
        return None
    v = n * r ** 3
    if shape == "sphere":
        miscs = [("NO_FOUR_THIRDS", Num(3 * r ** 3)), ("SQUARED_NOT_CUBED", Num(4 * r * r)),
                 ("FOUR_NOT_THIRD", Num(12 * r ** 3))]
    else:
        miscs = [("NO_TWO_THIRDS", Num(3 * r ** 3)), ("WHOLE_FOR_HALF", Num(4 * r ** 3)),
                 ("SQUARED_NOT_CUBED", Num(2 * r * r))]
    if dim == "diameter":
        miscs.insert(0, ("DIAMETER_AS_RADIUS", Num(n * d ** 3)))
    lead = f"Radius = {x} ÷ 2 = {r}. " if dim == "diameter" else ""
    frac = "(4/3)" if shape == "sphere" else "(2/3)"
    expl = lead + f"{frac} × 3 = {n}, then {n} × {r} × {r} × {r} = {v}."
    return Num(v), miscs, expl, pre + steps


# ---- Tier 4: work backward and estimate -------------------------------------------------------
def solve_cyl_height(C, r):
    h = F(C, r * r)
    if h.denominator != 1 or not 2 <= h <= 10:
        return None
    h = int(h)
    miscs = [("FORGOT_SQUARE", Num(F(C, r))), ("RADIUS_AS_DIAMETER", Num(4 * h)), ("RADIUS_FOR_HEIGHT", Num(r))]
    expl = f"C = π × r × r × h, so h = {C} ÷ ({r} × {r}) = {C} ÷ {r * r} = {h}."
    return Num(h), miscs, expl, [("÷", C, r * r, h)]


def solve_cyl_radius(C, h):
    q = F(C, h)
    if q.denominator != 1:
        return None
    q = int(q)
    r = {4: 2, 9: 3}.get(q)
    if r is None:
        return None
    miscs = [("STOPPED_AT_SQUARE", Num(q)), ("DIAMETER_FOR_RADIUS", Num(2 * r)), ("HEIGHT_FOR_RADIUS", Num(h))]
    expl = f"{C} ÷ {h} = {q} = r × r, so r = {r}."
    return Num(r), miscs, expl, [("÷", C, h, q), ("root2", q, 0, r)]


def solve_cone_height(V, r):
    if r == 3:
        if V % 3 or not 2 <= V // 3 <= 10:
            return None
        h = V // 3
        miscs = [("FORGOT_THIRD", Num(F(V, 9))), ("NO_SQUARE", Num(F(3 * V, 3))), ("DIVIDED_NOT_MULTIPLIED", Num(F(V, 27)))]
        expl = f"(1/3) × 3 × 3 = 3, so V = 3 × h. {V} ÷ 3 = {h}."
        return Num(h), miscs, expl, [("÷", V, 3, h)]
    if r == 2:
        if V % 4 or not 2 <= V // 4 <= 10:
            return None
        h = V // 4 * 3
        if not 2 <= h <= 10:
            return None
        miscs = [("FORGOT_THIRD", Num(F(V, 4))), ("NO_SQUARE", Num(F(3 * V, 2))), ("DIVIDED_NOT_MULTIPLIED", Num(F(V, 12)))]
        expl = f"(1/3) × 2 × 2 × h = V. So h = {V} ÷ 4 × 3 = {V // 4} × 3 = {h}."
        return Num(h), miscs, expl, [("÷", V, 4, V // 4), ("×", V // 4, 3, h)]
    return None


SOLID_VOL = {  # volume text -> (kind, radius, coefficient)
    "36π": ("sphere", 3, F(36)), "(4/3)π": ("sphere", 1, F(4, 3)),
    "18π": ("hemi", 3, F(18)), "(2/3)π": ("hemi", 1, F(2, 3)),
}


def solve_solid_back(shape, V, ask):
    kind, r, coef = SOLID_VOL[V]
    if kind != shape:
        return None
    if r == 3:
        n = 4 if shape == "sphere" else 2
        steps = [("÷", int(coef), n, int(coef) // n), ("×", int(coef) // n, 3, int(coef) // n * 3), ("root3", 27, 0, 3)]
    else:
        steps = [("root3", 1, 0, 1)]
    if ask == "radius":
        correct = Num(r)
        miscs = [("STOPPED_AT_CUBE", Num(r ** 3)), ("DIAMETER_FOR_RADIUS", Num(2 * r)),
                 ("DIVIDED_NOT_ROOTED", Num(F(r ** 3, 3))), ("COEFFICIENT_AS_RADIUS", Num(coef))]
        expl = f"Undo the formula: r × r × r = {r ** 3}, and {r} × {r} × {r} = {r ** 3}, so r = {r}."
    else:
        correct = Num(2 * r)
        miscs = [("RADIUS_FOR_DIAMETER", Num(r)), ("STOPPED_AT_CUBE", Num(r ** 3)),
                 ("COEFFICIENT_AS_RADIUS", Num(coef))]
        expl = f"Undo the formula: r × r × r = {r ** 3}, so r = {r}. Diameter = 2 × {r} = {2 * r}."
    return correct, miscs, expl, steps


def solve_cyl3(r, h):
    steps = find_steps([3, r, r, h])
    if steps is None:
        return None
    v = 3 * r * r * h
    miscs = [("NO_SQUARE", Num(3 * r * h)), ("LEFT_OUT_PI", Num(r * r * h)), ("LATERAL_AREA", Num(6 * r * h)),
             ("ADDED_HEIGHT", Num(3 * (r * r + h)))]
    return Num(v), miscs, f"3 × r × r × h = 3 × {r} × {r} × {h} = {v}.", steps


def solve_cone3(r, h):
    steps = find_steps([r, r, h])
    if steps is None:
        return None
    v = r * r * h
    miscs = [("NO_THIRD", Num(3 * v)), ("LEFT_OUT_PI", Num(F(v, 3)) if v % 3 == 0 else None), ("NO_SQUARE", Num(r * h))]
    return Num(v), miscs, f"(1/3) × 3 = 1, so volume = {r} × {r} × {h} = {v}.", steps


# ---- Tier 5: compare and scale ----------------------------------------------------------------
SCALE_WORD = {2: ("Double", "doubled"), 3: ("Triple", "tripled"), F(1, 2): ("Halve", "halved")}
EXPONENT = {("cylinder", "radius"): 2, ("cylinder", "height"): 1, ("cylinder", "both"): 3,
            ("cone", "radius"): 2, ("cone", "height"): 1, ("cone", "both"): 3, ("sphere", "radius"): 3}


def _scale_miscs(e, s, mk):
    """Wrong multipliers a student could apply, each made a Value by ``mk``."""
    out = []
    if e != 1:
        out.append(("LINEAR_SCALE", mk(s)))
    if e == 3:
        out.append(("SQUARE_FOR_CUBE", mk(s * s)))
    if e == 2:
        out.append(("CUBE_FOR_SQUARE", mk(s ** 3)))
    if e == 1:
        out.append(("SQUARE_FOR_LINEAR", mk(s * s)))
        out.append(("CUBE_FOR_LINEAR", mk(s ** 3)))
    if s >= 2 and e >= 2:
        out.append(("MULT_BY_EXPONENT", mk(s * e)))
    return out


def solve_scale(solid, dim, s, **_):
    s = F(s)
    e = EXPONENT[(solid, dim)]
    ans = s ** e
    if s >= 2:
        exp_txt = " × ".join(str(s.numerator) for _ in range(e))
        steps = find_steps([int(s)] * e)
    else:
        exp_txt = " × ".join("1/2" for _ in range(e))
        steps = []
    if steps is None:
        return None
    where = {1: "Height appears once in the formula", 2: "Radius appears twice (r × r)",
             3: "Radius appears three times (r × r × r)"}[e]
    if dim == "both":
        where = "Radius appears twice and height once: three scaled lengths"
    expl = f"{where}, so multiply by {exp_txt} = {_plain(ans)}."
    return Num(ans), _scale_miscs(e, s, Num), expl, steps


def solve_scale_v(solid, dim, s, v, **_):
    s = F(s)
    e = EXPONENT[(solid, dim)]
    mult = s ** e
    if s >= 2:
        steps = find_steps([v] + [int(s)] * e)
        if steps is None:
            return None
        ans = v * mult
        how = f"{v} × " + " × ".join(str(int(s)) for _ in range(e)) + f" = {ans}"
    else:
        D = int(1 / mult)
        if v % D or not 2 <= v // D <= 10:
            return None
        ans = F(v, D)
        steps = [("÷", v, D, v // D)]
        how = f"{v} ÷ {D} = {v // D}"
    wrong = _scale_miscs(e, s, lambda m: Pi(v * m))
    return Pi(ans), wrong, f"Volume changes by {_plain(mult)} times: {how}, so {_plain(ans)}π.", steps


BANK5 = [
    dict(prompt="Same base and height: a cone is what part of the cylinder?", correct="1/3",
         wrongs=[("1/2", "HALF_RULE"), ("2/3", "SPHERE_FOR_CONE"), ("3", "TIMES_THREE")],
         expl="Three cones fill a cylinder with the same base and height: each is 1/3."),
    dict(prompt="A ball fits a can exactly. The ball is what part of the can?", correct="2/3",
         wrongs=[("1/3", "CONE_FOR_SPHERE"), ("1/2", "HALF_RULE"), ("3/4", "ARITH")],
         expl="A ball that just fits a can fills 2/3 of it (a cone would fill 1/3)."),
    dict(prompt="A cone fits a can exactly. The cone is what part of the can?", correct="1/3",
         wrongs=[("2/3", "SPHERE_FOR_CONE"), ("1/2", "HALF_RULE"), ("3", "TIMES_THREE")],
         expl="A cone with the can's base and height is 1/3 of the can (a ball would be 2/3)."),
]


def solve_can(n, shape):
    third = n // 3
    if n % 3 or not 2 <= third <= 10:
        return None
    if shape == "ball":
        ans = 2 * third
        miscs = [("CONE_FOR_SPHERE", Num(third)), ("HALF_RULE", Num(F(n, 2)) if n % 2 == 0 else None), ("TIMES_THREE", Num(3 * n))]
        expl = f"A ball that fits a can fills 2/3 of it: {n} ÷ 3 × 2 = {third} × 2 = {ans}."
        steps = [("÷", n, 3, third), ("×", third, 2, ans)]
    else:
        ans = third
        miscs = [("SPHERE_FOR_CONE", Num(2 * third)), ("HALF_RULE", Num(F(n, 2)) if n % 2 == 0 else None), ("TIMES_THREE", Num(3 * n))]
        expl = f"A cone with the can's base and height holds 1/3 of it: {n} ÷ 3 = {ans}."
        steps = [("÷", n, 3, third)]
    return Num(ans), miscs, expl, steps


# ---------------------------------------------------------------------------------------------
# Kind tables
# ---------------------------------------------------------------------------------------------
def _dims(radii, diams):
    return [("radius", x) for x in radii] + [("diameter", x) for x in diams]


CYL_FRAMES = [
    "Cylinder: {dim} {x}, height {h}. Volume?",
    "A can has {dim} {x} and height {h}. Its volume?",
    "Tank: {dim} {x}, height {h}. How much does it hold?",
    "A drum has {dim} {x} and height {h}. Volume?",
    "Silo: {dim} {x}, height {h}. What is its volume?",
    "A jar is a cylinder, {dim} {x}, height {h}. Volume?",
]
CONE_FRAMES = [
    "Cone: {dim} {x}, height {h}. Volume?",
    "A cone has {dim} {x} and height {h}. Its volume?",
    "Traffic cone: {dim} {x}, height {h}. Volume?",
    "Party hat (a cone): {dim} {x}, height {h}. Volume?",
    "A cone-shaped cup: {dim} {x}, height {h}. Volume?",
    "Ice cream cone: {dim} {x}, height {h}. Volume?",
]
SPHERE_FRAMES = [
    "Sphere: {dim} {x}. Volume?",
    "A ball has {dim} {x}. Its volume?",
    "Marble with {dim} {x}. What is its volume?",
    "A globe has {dim} {x}. Volume?",
    "Bubble: {dim} {x}. Volume?",
    "Planet (a sphere) with {dim} {x}. Volume?",
]
HEMI_FRAMES = [
    "Hemisphere: {dim} {x}. Volume?",
    "A bowl is a half sphere with {dim} {x}. Volume?",
    "Dome (half a sphere): {dim} {x}. Volume?",
    "Half a ball, {dim} {x}. Its volume?",
]
SPHERE3_FRAMES = [
    "Sphere: {dim} {x}. Volume, using 3 for π?",
    "A ball has {dim} {x}. Volume, using 3 for π?",
    "Marble with {dim} {x}. Volume, using 3 for π?",
]
HEMI3_FRAMES = [
    "Hemisphere: {dim} {x}. Volume, using 3 for π?",
    "Half a ball, {dim} {x}. Volume, using 3 for π?",
    "Dome (half a sphere): {dim} {x}. Volume, using 3 for π?",
]


def _kinds():
    K = {}
    K["cyl"] = Kind("cyl", CYL_FRAMES,
                    [dict(dim=d, x=x, h=h) for d, x in _dims(range(1, 6), (2, 4, 6, 8, 10)) for h in range(1, 11)],
                    solve_cyl)
    K["cyl_area"] = Kind("cyl_area", [
        "A cylinder's base area is {k}π, height {h}. Volume?",
        "Can: base area {k}π, height {h}. Its volume?",
        "Tank: base area {k}π, height {h}. How much does it hold?",
    ], [dict(k=k, h=h) for k in range(2, 11) for h in range(2, 11)], solve_cyl_area)
    K["bank1"] = Kind("bank1", ["{prompt}"], BANK1, solve_bank)

    K["cone"] = Kind("cone", CONE_FRAMES,
                     [dict(dim=d, x=x, h=h) for d, x in _dims(range(1, 6), (2, 4, 6, 8, 10)) for h in range(2, 11)],
                     solve_cone)
    K["cone_from_cyl"] = Kind("cone_from_cyl", [
        "Same base and height: cylinder {c}π. The cone?",
        "A cylinder holds {c}π. A cone with its base and height holds?",
        "Cylinder {c}π; cone with the same base and height. Cone?",
    ], [dict(c=c) for c in range(6, 31, 3)], solve_cone_from_cyl)
    K["cyl_from_cone"] = Kind("cyl_from_cone", [
        "Same base and height: cone {v}π. The cylinder?",
        "A cone holds {v}π. The cylinder with its base and height holds?",
        "Cone {v}π; cylinder with the same base and height. Cylinder?",
    ], [dict(v=v) for v in range(2, 11)], solve_cyl_from_cone)
    K["bank2"] = Kind("bank2", ["{prompt}"], BANK2, solve_bank)

    K["sphere"] = Kind("sphere", SPHERE_FRAMES, [dict(dim=d, x=x) for d, x in _dims((1, 3), (2, 6))], solve_sphere)
    K["hemi"] = Kind("hemi", HEMI_FRAMES, [dict(dim=d, x=x) for d, x in _dims((1, 3), (2, 6))], solve_hemi)
    K["sphere3"] = Kind("sphere3", SPHERE3_FRAMES,
                        [dict(shape="sphere", dim=d, x=x) for d, x in _dims((1, 2), (2, 4))], solve_sphere3)
    K["hemi3"] = Kind("hemi3", HEMI3_FRAMES,
                      [dict(shape="hemi", dim=d, x=x) for d, x in _dims((1, 2, 3), (2, 4, 6))], solve_sphere3)

    K["cyl_height"] = Kind("cyl_height", [
        "Cylinder volume {C}π, radius {r}. Height?",
        "A can holds {C}π and has radius {r}. Its height?",
        "Tank holds {C}π, radius {r}. How tall is it?",
        "Drum: volume {C}π, radius {r}. Find the height.",
    ], [dict(C=r * r * h, r=r) for r in (2, 3) for h in range(2, 11)], solve_cyl_height)
    K["cyl_radius"] = Kind("cyl_radius", [
        "Cylinder volume {C}π, height {h}. Radius?",
        "A can holds {C}π and is {h} tall. Its radius?",
        "Tank holds {C}π, height {h}. What is the radius?",
        "Drum: volume {C}π, height {h}. Find the radius.",
    ], [dict(C=r * r * h, h=h) for r in (2, 3) for h in range(2, 11)], solve_cyl_radius)
    K["cone_height"] = Kind("cone_height", [
        "Cone volume {V}π, radius {r}. Height?",
        "A cone holds {V}π and has radius {r}. Its height?",
        "Cone-shaped cup: volume {V}π, radius {r}. How tall?",
    ], [dict(V=v, r=3) for v in (9, 18, 27)] + [dict(V=v, r=2) for v in (8, 12)], solve_cone_height)
    K["sphere_radius"] = Kind("sphere_radius", [
        "Sphere volume {V}. Radius?",
        "A ball has volume {V}. Its radius?",
        "Marble with volume {V}. What is its radius?",
    ], [dict(shape="sphere", V=v, ask="radius") for v in ("36π", "(4/3)π")], solve_solid_back)
    K["sphere_diam"] = Kind("sphere_diam", [
        "Sphere volume {V}. Diameter?",
        "A ball has volume {V}. Its diameter?",
        "Marble with volume {V}. What is its diameter?",
    ], [dict(shape="sphere", V=v, ask="diameter") for v in ("36π", "(4/3)π")], solve_solid_back)
    K["hemi_radius"] = Kind("hemi_radius", [
        "Hemisphere volume {V}. Radius?",
        "A bowl (half sphere) holds {V}. Its radius?",
        "Dome (half a sphere) with volume {V}. Radius?",
    ], [dict(shape="hemi", V=v, ask="radius") for v in ("18π", "(2/3)π")], solve_solid_back)
    K["hemi_diam"] = Kind("hemi_diam", [
        "Hemisphere volume {V}. Diameter?",
        "A bowl (half sphere) holds {V}. Its diameter?",
        "Dome (half a sphere) with volume {V}. Diameter?",
    ], [dict(shape="hemi", V=v, ask="diameter") for v in ("18π", "(2/3)π")], solve_solid_back)
    K["cyl3"] = Kind("cyl3", [
        "Cylinder: radius {r}, height {h}. Volume, using 3 for π?",
        "A can has radius {r} and height {h}. Volume, using 3 for π?",
    ], [dict(r=r, h=h) for r in (1, 2, 3) for h in range(2, 11)], solve_cyl3)
    K["cone3"] = Kind("cone3", [
        "Cone: radius {r}, height {h}. Volume, using 3 for π?",
        "A cone has radius {r} and height {h}. Volume, using 3 for π?",
    ], [dict(r=r, h=h) for r in (1, 2, 3, 4, 5) for h in range(2, 11)], solve_cone3)

    # tier 5
    solids = {"cylinder": "cylinder", "cone": "cone", "sphere": "sphere"}
    owner = {"cylinder": "can", "cone": "cone", "sphere": "ball"}
    sp = []
    for (solid, dim), e in EXPONENT.items():
        for s in (2, 3, F(1, 2)):
            sp.append(dict(solid=solid, dim=dim, s=s, Verb=SCALE_WORD[s][0], verb=SCALE_WORD[s][1],
                           thing=owner[solid], dims=("radius and height" if dim == "both" else dim),
                           are="are" if dim == "both" else "is"))
    K["scale"] = Kind("scale", [
        "{Verb} a {solid}'s {dims}. Volume times?",
        "A {thing}'s {dims} {are} {verb}. Its volume is multiplied by?",
        "{Verb} the {dims} of a {solid}. New volume is ? times as big.",
    ], sp, solve_scale)
    sv = []
    for (solid, dim), e in EXPONENT.items():
        if dim == "both":
            continue
        for s in (2, 3, F(1, 2)):
            for v in (range(2, 11) if s >= 2 else range(8, 41, 4)):
                sv.append(dict(solid=solid, Solid=solid.capitalize(), dim=dim, s=s, v=v, Verb=SCALE_WORD[s][0],
                               verb=SCALE_WORD[s][1], thing=owner[solid]))
    K["scale_v"] = Kind("scale_v", [
        "{Solid} volume {v}π. {Verb} the {dim}. New volume?",
        "A {thing} holds {v}π. Its {dim} is {verb}. New volume?",
    ], sv, solve_scale_v)
    K["bank5"] = Kind("bank5", ["{prompt}"], BANK5, solve_bank)
    K["can_ball"] = Kind("can_ball", [
        "A can holds {n} cups. A ball just fits inside it. Ball holds?",
        "Can: {n} cups. A ball fits it exactly. How much does the ball hold?",
    ], [dict(n=n, shape="ball") for n in range(6, 31, 3)], solve_can)
    K["can_cone"] = Kind("can_cone", [
        "A can holds {n} cups. A cone with its base and height holds?",
        "Can: {n} cups. A cone has the same base and height. Cone holds?",
    ], [dict(n=n, shape="cone") for n in range(6, 31, 3)], solve_can)
    return K


KINDS = _kinds()

TIERS = {
    1: [("cyl", 27), ("cyl_area", 10), ("bank1", 3)],
    2: [("cone", 24), ("cone_from_cyl", 6), ("cyl_from_cone", 8), ("bank2", 2)],
    3: [("sphere", 9), ("hemi", 9), ("sphere3", 10), ("hemi3", 12)],
    4: [("cyl_height", 6), ("cyl_radius", 6), ("cone_height", 6), ("sphere_radius", 3), ("sphere_diam", 3),
        ("hemi_radius", 3), ("hemi_diam", 2), ("cyl3", 6), ("cone3", 5)],
    5: [("scale", 20), ("scale_v", 10), ("bank5", 3), ("can_ball", 4), ("can_cone", 3)],
}


# ---------------------------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------------------------
def _fill_candidates(correct):
    """ARITH distractors near the right value, as Values."""
    typ, c = correct[1]
    if typ == "txt":
        return []
    mk = Pi if typ == "pi" else Num
    if c < 1:
        cands = [F(1, 2), F(1, 4), F(1, 8), F(1, 3), F(2, 3), F(1, 16), F(1, 6), F(3, 4), 1, 2]
    elif c.denominator != 1:
        cands = [c + 1, c + 2, c * 2, c - 1, c / 2, c + 3, c * 3]
    else:
        cands = [c + 1, c - 1, c + 2, c - 2, c + 3, c - 3, c * 2, c + 5, c - 5, c + 10]
    return [v for v in (mk(x) for x in cands) if v is not None]


def build_item(case, rng):
    """(prompt, correct_text, [(wrong_text, key)], explanation) or None."""
    correct = case.correct
    seen, avail = {correct[1]}, []
    for key, val in case.miscs:
        if val is None or val[1] in seen:
            continue
        seen.add(val[1])
        avail.append((key, val))
    if len(avail) < 2 and case.correct[1][0] != "txt":
        return None
    rng.shuffle(avail)
    wrongs = [(v[0], k) for k, v in avail[:3]]
    for v in _fill_candidates(correct):
        if len(wrongs) >= 3:
            break
        if v[1] in seen:
            continue
        seen.add(v[1])
        wrongs.append((v[0], "ARITH"))
    if len(wrongs) < 2:
        return None
    if len(case.prompt) > MAX_PROMPT or len(case.expl) > MAX_EXPL:
        return None
    if any(len(t) > MAX_CHOICE for t, _ in wrongs) or len(correct[0]) > MAX_CHOICE:
        return None
    return case.prompt, correct[0], wrongs, case.expl


def _ordered_pool(kind, rng):
    combos = [(f, p) for p in kind.params for f in range(len(kind.frames))]
    rng.shuffle(combos)
    seen, ranked = {}, []
    for f, p in combos:
        key = repr(sorted(p.items(), key=lambda kv: kv[0]))
        ranked.append((seen.get(key, 0), len(ranked), f, p))
        seen[key] = seen.get(key, 0) + 1
    ranked.sort(key=lambda t: (t[0], t[1]))
    return [(f, p) for _, _, f, p in ranked]


def _tier_items(plan, n, rng):
    pools = {}
    for name, _ in plan:
        if name not in pools:
            pools[name] = _ordered_pool(KINDS[name], rng)
    quotas = {}
    order = []
    for name, q in plan:
        order.append(name)
        quotas[name] = quotas.get(name, 0) + q
    chosen, prompts = [], set()

    def take(name):
        pool = pools[name]
        while pool:
            f, p = pool.pop(0)
            case = KINDS[name].case(f, **p)
            if case is None or case.prompt in prompts:
                continue
            item = build_item(case, rng)
            if item is None:
                continue
            prompts.add(case.prompt)
            return item
        return None

    uniq = list(dict.fromkeys(order))
    got = {name: 0 for name in uniq}
    for name in uniq:
        while got[name] < quotas[name] and len(chosen) < n:
            it = take(name)
            if it is None:
                break
            chosen.append(it)
            got[name] += 1
    # a kind that ran dry hands its quota to the others, largest pools first
    while len(chosen) < n:
        progressed = False
        for name in sorted(uniq, key=lambda k: -len(pools[k])):
            if len(chosen) >= n:
                break
            it = take(name)
            if it is not None:
                chosen.append(it)
                progressed = True
        if not progressed:
            raise RuntimeError(f"tier plan {plan} cannot reach {n} items (got {len(chosen)})")
    return chosen


def _place(items, rng):
    """Balanced answer positions per choice count, then the final item dicts."""
    by_n = {}
    for i, (prompt, correct, wrongs, expl) in enumerate(items):
        by_n.setdefault(len(wrongs) + 1, []).append(i)
    pos = {}
    for n, idxs in by_n.items():
        slots = [k % n for k in range(len(idxs))]
        rng.shuffle(slots)
        for i, s in zip(idxs, slots):
            pos[i] = s
    out = []
    for i, (prompt, correct, wrongs, expl) in enumerate(items):
        rng.shuffle(wrongs)
        choices = [t for t, _ in wrongs]
        keys = [k for _, k in wrongs]
        a = pos[i]
        choices.insert(a, correct)
        keys.insert(a, None)
        out.append({"tier": 0, "prompt": prompt, "choices": choices, "answer": a, "misconceptions": keys,
                    "explanation": expl})
    rng.shuffle(out)
    return out


def generate(manifest, rng):
    n = manifest["items_per_tier"]
    items = []
    for tier in range(1, 6):
        built = _tier_items(TIERS[tier], n, rng)
        for it in _place(built, rng):
            it["tier"] = tier
            items.append(it)
    return items
