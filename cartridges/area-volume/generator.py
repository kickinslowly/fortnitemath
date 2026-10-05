"""Procedural generator for the area-volume cartridge (fnm-cart/1), grade 6, CCSS 6.G.A.1, A.2, A.4.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every prompt is built from a fixed template, then re-read from its own display text by ``solve``
  (regex per template), so the text a student sees is the only thing ever solved.
* ``solve`` returns the correct value, the correct working as a list of arithmetic steps
  ``(op, a, b, result)``, the explanation, and every modelled misconception's value in label
  priority order (the order of ``SOLVERS``' wrong lists). When two misconceptions give the same
  value, the first one listed keeps it.
* ``steps_ok`` is the manifest ``bounds`` gate on those steps (PROTOCOL §4a/§4b): × factors 1-10,
  ÷ exact with divisor and quotient 2-10, every value a whole number 1-100.
* A prompt is rejected when any modelled misconception gives the right answer (a kid holding the
  wrong rule must not walk through the right door).
* T4 volume choices carry units ("24 cu units"): the unit is half the concept and SQUARE_UNITS is
  the right number in the wrong unit. Every other choice is a bare number; the prompt names the
  measure.
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

MUL, DIV, ADD = "×", "÷", "+"
HALF = Fraction(1, 2)
MAX_LEN = 10
MAX_VALUE = 100
MAX_DISTRACTOR = 999
MAX_CHOICE = 14


# ---------------------------------------------------------------------------------------------
# Numbers and choice text
# ---------------------------------------------------------------------------------------------
def fmt(v) -> str:
    """7, 1/2, 7 1/2."""
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    w, r = divmod(v.numerator, v.denominator)
    frac = f"{r}/{v.denominator}"
    return f"{w} {frac}" if w else frac


def choice_text(v, unit) -> str:
    return f"{fmt(v)} {unit} units" if unit else fmt(v)


def _len(s: str) -> Fraction:
    return HALF if s == "1/2" else Fraction(int(s))


# ---------------------------------------------------------------------------------------------
# Correct working, as steps (op, a, b, result)
# ---------------------------------------------------------------------------------------------
def _mul(a, b):
    return (MUL, a, b, a * b)


def _div(a, b):
    return (DIV, a, b, Fraction(a) / b)


def _add(a, b):
    return (ADD, a, b, a + b)


def half_product(a, b):
    """Steps for a × b ÷ 2 that stay in the times tables: halve an even length of 4+ first, else
    multiply and halve a product of 20 or less. None when neither works or the result is odd."""
    for x, y in ((a, b), (b, a)):
        if x % 2 == 0 and x // 2 >= 2:
            return [_div(x, 2), _mul(x // 2, y)]
    p = a * b
    if p % 2 == 0 and 2 <= p // 2 <= 10:
        return [_mul(a, b), _div(p, 2)]
    return None


def product3(a, b, c):
    """Steps for a × b × c with every × factor <= 10: pick the pair whose product is <= 10."""
    for x, y, z in ((a, b, c), (a, c, b), (b, c, a)):
        if x * y <= MAX_LEN:
            return [_mul(x, y), _mul(x * y, z)]
    return None


def steps_ok(steps) -> bool:
    """THE bounds gate (manifest ``bounds``)."""
    if not steps:
        return False
    for op, a, b, r in steps:
        for v in (a, b, r):
            if Fraction(v).denominator != 1:
                return False
        if op == MUL and not (1 <= a <= MAX_LEN and 1 <= b <= MAX_LEN):
            return False
        if op == DIV and not (2 <= b <= 10 and 2 <= r <= 10 and a <= MAX_VALUE):
            return False
        if op == ADD and not (a >= 1 and b >= 1):
            return False
        if not 1 <= r <= MAX_VALUE:
            return False
    return True


def say(steps) -> str:
    return ", ".join(f"{fmt(a)} {op} {fmt(b)} = {fmt(r)}" for op, a, b, r in steps)


# ---------------------------------------------------------------------------------------------
# Templates: regex -> solver. Each solver returns dict(correct, unit, steps, expl, wrong=[(label, value, unit)])
# ---------------------------------------------------------------------------------------------
N = r"(\d+|1/2)"


def _rect(m):
    l, w = int(m[1]), int(m[2])
    s = [_mul(l, w)]
    return dict(correct=l * w, steps=s, expl=f"Area = length × width: {say(s)}.",
                wrong=[("PERIMETER", 2 * (l + w)), ("ADD_SIDES", l + w)])


def _square(m):
    a = int(m[1])
    s = [_mul(a, a)]
    return dict(correct=a * a, steps=s, expl=f"Area = side × side: {say(s)}.",
                wrong=[("PERIMETER", 4 * a), ("ADD_SIDES", 2 * a)])


def _para(m):
    vals = {m[2]: int(m[3]), m[4]: int(m[5])}
    b, sl, h = int(m["b"]), vals.get("side"), vals.get("height")
    s = [_mul(b, h)]
    return dict(correct=b * h, steps=s,
                expl=f"Area = base × height: {say(s)}. The side {sl} is slanted, so it is not the height.",
                wrong=[("SLANT_SIDE", b * sl), ("PERIMETER", 2 * (b + sl)), ("ADD_SIDES", b + h)])


def _tri(m):
    b, h = int(m[1]), int(m[2])
    s = half_product(b, h)
    return dict(correct=Fraction(b * h, 2), steps=s,
                expl=f"Triangle = half of base × height: {say(s or [])}.",
                wrong=[("NO_HALF", b * h), ("ADD_SIDES", b + h)])


def _tri_side(m):
    vals = {m[2]: int(m[3]), m[4]: int(m[5])}
    b, sl, h = int(m[1]), vals.get("side"), vals.get("height")
    s = half_product(b, h)
    return dict(correct=Fraction(b * h, 2), steps=s,
                expl=f"Half of base × height: {say(s or [])}. The side {sl} is slanted, so it is not the height.",
                wrong=[("SLANT_SIDE", Fraction(b * sl, 2)), ("NO_HALF", b * h), ("ADD_SIDES", b + h)])


def _right_tri(m):
    a, b = int(m[1]), int(m[2])
    s = half_product(a, b)
    return dict(correct=Fraction(a * b, 2), steps=s,
                expl=f"The legs are a base and a height at a right angle. Half of base × height: {say(s or [])}.",
                wrong=[("NO_HALF", a * b), ("ADD_SIDES", a + b)])


def _cut_rect(m):
    l, w = int(m[1]), int(m[2])
    s = half_product(l, w)
    return dict(correct=Fraction(l * w, 2), steps=s,
                expl=f"Each half is a triangle, half the rectangle's area: {say(s or [])}.",
                wrong=[("NO_HALF", l * w), ("ADD_SIDES", l + w)])


def _trap(m):
    a, b, h = int(m[1]), int(m[2]), int(m[3])
    s = [_add(a, b), _div(a + b, 2), _mul(Fraction(a + b, 2), h)]
    return dict(correct=Fraction(a + b, 2) * h, steps=s,
                expl=f"Average the bases, then × height: {say(s)}.",
                wrong=[("NO_AVERAGE", (a + b) * h), ("ONE_BASE", max(a, b) * h)])


def _missing(m):
    area, known = int(m[2]), int(m[3])
    s = [_div(area, known)]
    want = "length" if m[1] == "Rectangle" else "height"
    return dict(correct=Fraction(area, known), steps=s,
                expl=f"Area = {'length × width' if want == 'length' else 'base × height'}, so divide: {say(s)}.",
                wrong=[("SUBTRACTED", area - known), ("MULTIPLIED", area * known)])


def _tri_missing(m):
    area, b = int(m[1]), int(m[2])
    s = [_div(b, 2), _div(area, Fraction(b, 2))]
    return dict(correct=Fraction(2 * area, b), steps=s,
                expl=f"Area = half the base × height. {say(s)}. Check: {fmt(Fraction(b, 2))} × {fmt(Fraction(2 * area, b))} = {area}.",
                wrong=[("NO_HALF", Fraction(area, b)), ("SUBTRACTED", area - b), ("MULTIPLIED", area * b)])


def _box_volume(m):
    edges = [_len(m[1]), _len(m[2]), _len(m[3])]
    vol = edges[0] * edges[1] * edges[2]
    whole = [e for e in edges if e != HALF]
    if len(whole) == 2:  # one 1/2 edge
        x, y = int(whole[0]), int(whole[1])
        s = half_product(x, y)
        expl = f"Volume = length × width × height, and × 1/2 is half: {say(s or [])} cubic units."
        missed = x * y
    else:
        a, b, c = (int(e) for e in edges)
        s = product3(a, b, c)
        expl = f"Volume = length × width × height: {say(s or [])} cubic units."
        missed = a * b
    return dict(correct=vol, unit="cu", steps=s, expl=expl,
                wrong=[("MISSED_EDGE", missed, "cu"), ("SQUARE_UNITS", vol, "sq"),
                       ("ADDED_EDGES", sum(edges), "cu")])


def _packing(m):
    a, b, c = int(m[1]), int(m[2]), int(m[3])
    s = product3(a, b, c)
    vol = a * b * c
    s = (s or []) + [_mul(vol, 8)]
    return dict(correct=8 * vol, steps=s,
                expl=f"{vol} unit cube{'s' if vol > 1 else ''}; each holds 2 × 2 × 2 = 8 cubes of edge 1/2: {say(s[-1:])}.",
                wrong=[("COUNTED_UNITS", vol), ("DOUBLED_ONCE", 2 * vol), ("HALVED_COUNT", Fraction(vol, 2))])


def _cube_sa(m):
    e = int(m[1])
    s = [_mul(e, e), _mul(6, e * e)]
    return dict(correct=6 * e * e, steps=s,
                expl=f"6 equal square faces: {say(s)}.",
                wrong=[("VOLUME_FOR_SA", e ** 3), ("ONE_FACE", e * e), ("FOUR_FACES", 4 * e * e)])


def _box_sa(m):
    a, b, c = int(m[1]), int(m[2]), int(m[3])
    f1, f2, f3 = a * b, a * c, b * c
    t = f1 + f2 + f3
    s = [_mul(a, b), _mul(a, c), _mul(b, c), _add(f1, f2), _add(f1 + f2, f3), _add(t, t)]
    return dict(correct=2 * t, steps=s,
                expl=f"Faces {f1}, {f2}, {f3}, each twice: {f1} + {f2} + {f3} = {t}, {t} + {t} = {2 * t}.",
                wrong=[("VOLUME_FOR_SA", a * b * c), ("THREE_FACES", t), ("ONE_FACE", f1)])


def _pyramid_sa(m):
    sd, h = int(m[1]), int(m[2])
    hp = half_product(sd, h)
    face = Fraction(sd * h, 2)
    s = [_mul(sd, sd)] + (hp or []) + [_mul(4, face), _add(sd * sd, 4 * face)]
    return dict(correct=sd * sd + 4 * face, steps=s if hp else None,
                expl=f"Base {sd} × {sd} = {sd * sd}. Each triangle: {say(hp or [])}. "
                     f"4 × {fmt(face)} = {fmt(4 * face)}, {sd * sd} + {fmt(4 * face)} = {fmt(sd * sd + 4 * face)}.",
                wrong=[("NO_BASE", 4 * face), ("NO_HALF", sd * sd + 4 * sd * h)])


SOLVERS = [
    (re.compile(r"^Rectangle: length (\d+), width (\d+)\. Area\?$"), _rect),
    (re.compile(r"^Square: side (\d+)\. Area\?$"), _square),
    (re.compile(r"^Parallelogram: base (?P<b>\d+), (side|height) (\d+), (side|height) (\d+)\. Area\?$"), _para),
    (re.compile(r"^Triangle: base (\d+), height (\d+)\. Area\?$"), _tri),
    (re.compile(r"^Triangle: base (\d+), (side|height) (\d+), (side|height) (\d+)\. Area\?$"), _tri_side),
    (re.compile(r"^Right triangle: legs (\d+) and (\d+)\. Area\?$"), _right_tri),
    (re.compile(r"^Cut an? (\d+) by (\d+) rectangle corner to corner\. Area of each half\?$"), _cut_rect),
    (re.compile(r"^Trapezoid: bases (\d+) and (\d+), height (\d+)\. Area\?$"), _trap),
    (re.compile(r"^(Rectangle): area (\d+), width (\d+)\. Length\?$"), _missing),
    (re.compile(r"^(Parallelogram): area (\d+), base (\d+)\. Height\?$"), _missing),
    (re.compile(r"^Triangle: area (\d+), base (\d+)\. Height\?$"), _tri_missing),
    (re.compile(rf"^Box {N} by {N} by {N}\. Volume\?$"), _box_volume),
    (re.compile(r"^How many cubes of edge 1/2 fill a (\d+) by (\d+) by (\d+) box\?$"), _packing),
    (re.compile(r"^Cube, edge (\d+)\. Surface area\?$"), _cube_sa),
    (re.compile(r"^Box (\d+) by (\d+) by (\d+)\. Surface area\?$"), _box_sa),
    (re.compile(r"^Square pyramid: base edge (\d+), slant height (\d+)\. Surface area\?$"), _pyramid_sa),
]


def solve(prompt: str) -> dict:
    """Read a prompt's own text and solve it. ``wrong`` keeps every modelled value, in label
    priority order, as (label, value, unit) -- including ones equal to the answer."""
    for rx, fn in SOLVERS:
        m = rx.match(prompt)
        if m:
            out = fn(m)
            unit = out.get("unit")
            out["unit"] = unit
            out["correct"] = Fraction(out["correct"])
            out["wrong"] = [(w[0], Fraction(w[1]), w[2] if len(w) > 2 else unit) for w in out["wrong"]]
            return out
    raise ValueError(f"no template matches {prompt!r}")


def misconception_values(prompt: str) -> list:
    """[(label, value, unit)] usable distinct wrong values: whole numbers (or a T4 1/2) that differ
    from the answer and from every earlier label, at most 999, and short enough for a door."""
    sol = solve(prompt)
    seen = {(sol["correct"], sol["unit"])}
    out = []
    for lab, v, u in sol["wrong"]:
        if (v, u) in seen or v <= 0 or v > MAX_DISTRACTOR:
            continue
        if v.denominator != 1 and not (u and v.denominator == 2):
            continue
        if len(choice_text(v, u)) > MAX_CHOICE:
            continue
        seen.add((v, u))
        out.append((lab, v, u))
    return out


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def _arith(correct: Fraction, used: set, unit, rng: random.Random) -> list:
    near = [correct + d for d in (1, -1, 2, -2)]
    rng.shuffle(near)
    far = [correct + d for d in (4, -4, 10, -10, 3, -3)]
    return [v for v in near + far if v >= 1 and (v, unit) not in used]


def make_item(prompt: str, tier: int, answer_pos: int, rng: random.Random):
    if len(prompt) > 60:
        return None
    sol = solve(prompt)
    c, unit = sol["correct"], sol["unit"]
    if c.denominator != 1 or not steps_ok(sol["steps"]) or not 1 <= c <= MAX_VALUE:
        return None
    if any(v == c and u == unit for _, v, u in sol["wrong"]):
        return None  # a wrong rule lands on the right door: not a usable prompt
    wrong = misconception_values(prompt)
    if not wrong or len(sol["expl"]) > 160:
        return None
    wrong = wrong[:3]
    used = {(c, unit)} | {(v, u) for _, v, u in sol["wrong"]}  # ARITH never equals a rule's value
    for v in _arith(c, used, unit, rng):
        if len(wrong) == 3:
            break
        used.add((v, unit))
        wrong.append(("ARITH", v, unit))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, c, unit)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [choice_text(v, u) for _, v, u in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _, _ in pairs],
        "explanation": sol["expl"],
    }


# ---------------------------------------------------------------------------------------------
# Prompt makers per kind. Each returns (prompt, canonical key) or None.
# ---------------------------------------------------------------------------------------------
def _r(rng, lo=2, hi=MAX_LEN):
    return rng.randint(lo, hi)


def _side_height(rng, b, label):
    h = _r(rng, 2, 9)
    sl = _r(rng, h + 1, MAX_LEN) if h < MAX_LEN else None
    if sl is None:
        return None
    parts = [f"side {sl}", f"height {h}"]
    rng.shuffle(parts)
    return f"{label}: base {b}, {parts[0]}, {parts[1]}. Area?", (label, b, sl, h)


def k_rect(rng):
    l, w = _r(rng), _r(rng)
    if l == w:
        return None
    return f"Rectangle: length {l}, width {w}. Area?", ("R", max(l, w), min(l, w))


def k_square(rng):
    a = _r(rng, 3)
    return f"Square: side {a}. Area?", ("S", a)


def k_para(rng):
    return _side_height(rng, _r(rng), "Parallelogram")


def k_tri(rng):
    b, h = _r(rng), _r(rng)
    return f"Triangle: base {b}, height {h}. Area?", ("T", b, h)


def k_tri_side(rng):
    return _side_height(rng, _r(rng), "Triangle")


def k_right_tri(rng):
    a, b = _r(rng), _r(rng)
    return f"Right triangle: legs {a} and {b}. Area?", ("RT", max(a, b), min(a, b))


def k_cut(rng):
    l, w = _r(rng), _r(rng)
    if l == w:
        return None
    art = "an" if l == 8 else "a"
    return f"Cut {art} {l} by {w} rectangle corner to corner. Area of each half?", ("C", max(l, w), min(l, w))


def k_trap(rng):
    a, b = sorted(rng.sample(range(1, MAX_LEN + 1), 2))
    if (a + b) % 2:
        return None
    h = _r(rng)
    if rng.random() < 0.5:
        a, b = b, a
    return f"Trapezoid: bases {a} and {b}, height {h}. Area?", ("TZ", min(a, b), max(a, b), h)


def k_missing(rng):
    known, other = _r(rng), _r(rng)
    if known == other:
        return None
    if rng.random() < 0.5:
        return f"Rectangle: area {known * other}, width {known}. Length?", ("MR", known, other)
    return f"Parallelogram: area {known * other}, base {known}. Height?", ("MP", known, other)


def k_tri_missing(rng):
    b = rng.choice((4, 6, 8, 10))
    h = _r(rng)
    return f"Triangle: area {b // 2 * h}, base {b}. Height?", ("MT", b, h)


def k_box(rng):
    e = [_r(rng), _r(rng), _r(rng)]
    if len(set(e)) == 1:
        return None
    return f"Box {e[0]} by {e[1]} by {e[2]}. Volume?", ("V",) + tuple(sorted(e))


def k_box_half(rng):
    e = [str(_r(rng)), str(_r(rng)), "1/2"]
    rng.shuffle(e)
    return f"Box {e[0]} by {e[1]} by {e[2]}. Volume?", ("VH",) + tuple(sorted(e))


def k_packing(rng):
    e = [_r(rng, 1, 5), _r(rng, 1, 3), _r(rng, 1, 2)]
    rng.shuffle(e)
    if e[0] * e[1] * e[2] > 10:
        return None
    return f"How many cubes of edge 1/2 fill a {e[0]} by {e[1]} by {e[2]} box?", ("PK",) + tuple(sorted(e))


def k_cube_sa(rng):
    e = _r(rng, 1, 3)
    return f"Cube, edge {e}. Surface area?", ("CS", e)


def k_box_sa(rng):
    e = [_r(rng, 1), _r(rng, 1), _r(rng, 1)]
    if len(set(e)) == 1:
        return None
    return f"Box {e[0]} by {e[1]} by {e[2]}. Surface area?", ("BS",) + tuple(sorted(e))


def k_pyramid(rng):
    s = rng.choice((2, 3, 4, 5))  # base edge first, so 2 does not crowd out the rest
    h = _r(rng, 3)
    if 2 * h <= s:  # slant height must be longer than half the base edge
        return None
    return f"Square pyramid: base edge {s}, slant height {h}. Surface area?", ("PY", s, h)


# tier -> [(kind, count)]
PLAN = {
    1: [(k_rect, 12), (k_square, 6), (k_para, 22)],
    2: [(k_tri, 14), (k_tri_side, 12), (k_right_tri, 8), (k_cut, 6)],
    3: [(k_trap, 16), (k_missing, 12), (k_tri_missing, 12)],
    4: [(k_box, 22), (k_box_half, 10), (k_packing, 8)],
    5: [(k_cube_sa, 3), (k_box_sa, 29), (k_pyramid, 8)],
}


def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000) -> list:
    kinds = [k for k, n in PLAN[tier] for _ in range(n)]
    assert len(kinds) == count, (tier, len(kinds), count)
    rng.shuffle(kinds)
    positions = _balanced(count, 4, rng)
    items, keys = [], set()
    attempts = 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        got = kinds[len(items)](rng)
        if got is None:
            continue
        prompt, key = got
        if key in keys:
            continue
        item = make_item(prompt, tier, positions[len(items)], rng)
        if item is None:
            continue
        keys.add(key)
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
