"""Procedural generator for the transformations cartridge (fnm-cart/1, grade 8, 8.G.A.1-4).

Contract (PROTOCOL.md section 3): ``generate(manifest, rng) -> list[dict]`` returning items in the section 4
shape without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* A family function builds one item: a prompt, the right choice, a list of *modelled* wrong choices
  (each one is what a student holding one named misconception would pick) and an explanation. ``ARITH``
  only fills a missing slot.
* Choices carry a VALUE key (a point tuple, a Fraction, a normalised text) next to the display text, and a
  wrong choice whose key equals the right one (or another wrong one) is dropped, so a player never faces
  two right doors.
* Points are plain int tuples; a dilation keeps ``Fraction`` factors and refuses a non-integer image.
* Bounds (also in the manifest ``bounds`` string): integer coordinates of size <= 10 before every move and
  after every rigid move; slides <= 10 per axis; turns of 90 and 180 degrees about (0, 0); flips over the
  axes; dilations about (0, 0) by 2-5 or 1/2, 1/3, 1/4, images <= 20 in size.
* Answer positions are balanced per choice count with a shuffled round-robin.
"""
from __future__ import annotations

import random
from fractions import Fraction

MINUS = "−"  # U+2212
MAX_PROMPT, MAX_CHOICE, MAX_EXPL = 60, 14, 160


class Reject(Exception):
    """This draw cannot make a clean item; draw again."""


# ---------------------------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------------------------
def n(v) -> str:
    v = int(v)
    return f"{MINUS}{-v}" if v < 0 else str(v)


def pt(p) -> str:
    return f"({n(p[0])}, {n(p[1])})"


def ftxt(k: Fraction) -> str:
    return str(k.numerator) if k.denominator == 1 else f"{k.numerator}/{k.denominator}"


def sgn(v) -> int:
    return (v > 0) - (v < 0)


# ---------------------------------------------------------------------------------------------
# The moves (all about the origin / the axes)
# ---------------------------------------------------------------------------------------------
def slide(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


def rx(p):  # reflection over the x-axis
    return (p[0], -p[1])


def ry(p):  # reflection over the y-axis
    return (-p[0], p[1])


def ccw(p):  # 90 degrees counterclockwise about (0, 0)
    return (-p[1], p[0])


def cw(p):  # 90 degrees clockwise about (0, 0)
    return (p[1], -p[0])


def half(p):  # 180 degrees
    return (-p[0], -p[1])


def dil(p, k: Fraction):
    x, y = p[0] * k, p[1] * k
    if x.denominator != 1 or y.denominator != 1:
        return None
    return (int(x), int(y))


def inb(p, lim=10) -> bool:
    return abs(p[0]) <= lim and abs(p[1]) <= lim


def rng_nz(rng, lim):
    return rng.choice([i for i in range(-lim, lim + 1) if i])


def rpt(rng, lim=10):
    return (rng_nz(rng, lim), rng_nz(rng, lim))


def dir_word(dx, dy):
    return ("right" if dx > 0 else "left") if dx else ("up" if dy > 0 else "down")


def slide_phrase(rng, dx, dy):
    parts = []
    if dx:
        parts.append(f"{abs(dx)} {'right' if dx > 0 else 'left'}")
    if dy:
        parts.append(f"{abs(dy)} {'up' if dy > 0 else 'down'}")
    if len(parts) == 2 and rng.random() < 0.5:
        parts.reverse()
    return " and ".join(parts)


def slide_choice(dx, dy) -> str:
    """Choice text: '3 right 2 down' (horizontal first) or '4 left'."""
    parts = []
    if dx:
        parts.append(f"{abs(dx)} {'right' if dx > 0 else 'left'}")
    if dy:
        parts.append(f"{abs(dy)} {'up' if dy > 0 else 'down'}")
    return " ".join(parts)


def rule_text(dx, dy) -> str:
    xs = f"x {'+' if dx > 0 else MINUS} {abs(dx)}" if dx else "x"
    ys = f"y {'+' if dy > 0 else MINUS} {abs(dy)}" if dy else "y"
    return f"({xs}, {ys})"


def slide_wrongs(dx, dy):
    """(vector, key) wrong slides a student might use for the slide (dx, dy)."""
    out = []
    if dx and dy:
        out += [((-dx, -dy), "REVERSED_DIRECTION"), ((-dx, dy), "HALF_REVERSED"), ((dx, -dy), "HALF_REVERSED"),
                ((sgn(dx) * abs(dy), sgn(dy) * abs(dx)), "SWAPPED_AMOUNTS"), ((dx, 0), "ONE_AXIS"),
                ((0, dy), "ONE_AXIS")]
    else:
        a = dx or dy
        out.append(((-dx, -dy), "REVERSED_DIRECTION"))
        if dx:
            out += [((0, a), "WRONG_AXIS"), ((0, -a), "WRONG_AXIS")]
        else:
            out += [((a, 0), "WRONG_AXIS"), ((-a, 0), "WRONG_AXIS")]
    return out


# ---------------------------------------------------------------------------------------------
# Item assembly
# ---------------------------------------------------------------------------------------------
def pick(rng, ckey, cands, nwrong, fill=(), must=()):
    """Choose ``nwrong`` wrong choices: modelled first (``must`` keys earliest), ARITH only to fill."""
    c = list(cands)
    rng.shuffle(c)
    c.sort(key=lambda t: 0 if t[2] in must else 1)
    seen, out = {ckey}, []
    for text, key, mis in c:
        if key in seen or len(out) >= nwrong:
            continue
        seen.add(key)
        out.append((text, mis))
    for text, key in fill:
        if len(out) >= nwrong:
            break
        if key in seen:
            continue
        seen.add(key)
        out.append((text, "ARITH"))
    if len(out) < nwrong:
        raise Reject
    return out


def mk(rng, tier, prompt, correct, cands, expl, nwrong=3, fill=(), must=()):
    """``correct`` is (text, key); ``cands`` is [(text, key, misconception)]."""
    if len(prompt) > MAX_PROMPT or len(expl) > MAX_EXPL:
        raise Reject
    wrongs = pick(rng, correct[1], cands, nwrong, fill, must)
    if any(len(t) > MAX_CHOICE for t, _ in wrongs) or len(correct[0]) > MAX_CHOICE:
        raise Reject
    return {"tier": tier, "prompt": prompt, "correct": correct[0], "wrongs": wrongs, "explanation": expl}


def pc(p):  # point choice: (text, key)
    return (pt(p), p)


def pcands(points):
    return [(pt(p), p, m) for p, m in points if p is not None]


def fill_pt(c):
    x, y = c
    return [(pt(q), q) for q in [(x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1), (x + 2, y), (x, y - 2)]]


def fill_num(v, lo=1):
    cand = [v + 1, v - 1, v + 2, v - 2, 2 * v, v + 3]
    return [(str(q), Fraction(q)) for q in cand if q >= lo and q != v]


# ---------------------------------------------------------------------------------------------
# Tier 1: slides
# ---------------------------------------------------------------------------------------------
def f_slide_apply(rng, tier):
    if rng.random() < 0.65:
        dx, dy = rng.choice([-1, 1]) * rng.randint(1, 9), rng.choice([-1, 1]) * rng.randint(1, 9)
    elif rng.random() < 0.5:
        dx, dy = rng.choice([-1, 1]) * rng.randint(1, 10), 0
    else:
        dx, dy = 0, rng.choice([-1, 1]) * rng.randint(1, 10)
    p = rpt(rng)
    q = slide(p, dx, dy)
    if not inb(q):
        raise Reject
    prompt = f"{pt(p)} {rng.choice(['slides', 'moves', 'shifts'])} {slide_phrase(rng, dx, dy)}. {rng.choice(['Image?', 'New point?'])}"
    cands = pcands([(slide(p, *v), m) for v, m in slide_wrongs(dx, dy)])
    expl = f"Right and up add, left and down subtract: {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


def f_slide_find(rng, tier):
    if rng.random() < 0.6:
        dx, dy = rng.choice([-1, 1]) * rng.randint(1, 9), rng.choice([-1, 1]) * rng.randint(1, 9)
    elif rng.random() < 0.5:
        dx, dy = rng.choice([-1, 1]) * rng.randint(1, 10), 0
    else:
        dx, dy = 0, rng.choice([-1, 1]) * rng.randint(1, 10)
    p = rpt(rng)
    q = slide(p, dx, dy)
    if not inb(q):
        raise Reject
    prompt = f"{pt(p)} moves to {pt(q)}. The slide?"
    cands = [(slide_choice(*v), slide_choice(*v), m) for v, m in slide_wrongs(dx, dy)]
    right = slide_choice(dx, dy)
    expl = f"End minus start: x changes by {n(dx)}, y by {n(dy)}. That is {right}."
    return mk(rng, tier, prompt, (right, right), cands, expl)


def f_rule_apply(rng, tier):
    dx, dy = rng.choice([-1, 1]) * rng.randint(1, 9), rng.choice([-1, 1]) * rng.randint(1, 9)
    p = rpt(rng)
    q = slide(p, dx, dy)
    if not inb(q):
        raise Reject
    r = rule_text(dx, dy)
    prompt = rng.choice([f"Slide rule {r}. Where does {pt(p)} go?", f"Rule {r} is applied to {pt(p)}. Image?"])
    cands = pcands([(slide(p, *v), m) for v, m in slide_wrongs(dx, dy)])
    expl = f"{r} adds {n(dx)} to x and {n(dy)} to y: {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


def f_rule_find(rng, tier):
    if rng.random() < 0.7:
        dx, dy = rng.choice([-1, 1]) * rng.randint(1, 9), rng.choice([-1, 1]) * rng.randint(1, 9)
    elif rng.random() < 0.5:
        dx, dy = rng.choice([-1, 1]) * rng.randint(1, 10), 0
    else:
        dx, dy = 0, rng.choice([-1, 1]) * rng.randint(1, 10)
    p = rpt(rng)
    q = slide(p, dx, dy)
    if not inb(q):
        raise Reject
    prompt = f"Which rule slides {pt(p)} to {pt(q)}?"
    cands = [(rule_text(*v), rule_text(*v), m) for v, m in slide_wrongs(dx, dy)]
    right = rule_text(dx, dy)
    expl = f"x goes {n(p[0])} to {n(q[0])} and y goes {n(p[1])} to {n(q[1])}, so the rule is {right}."
    return mk(rng, tier, prompt, (right, right), cands, expl)


def f_slide_example(rng, tier):
    dx, dy = rng.choice([-1, 1]) * rng.randint(1, 8), rng.choice([-1, 1]) * rng.randint(1, 8)
    a, c = rpt(rng), rpt(rng)
    b, d = slide(a, dx, dy), slide(c, dx, dy)
    if not (inb(b) and inb(d)) or c == a:
        raise Reject
    prompt = f"A slide takes {pt(a)} to {pt(b)}. Where does {pt(c)} go?"
    cands = pcands([(b, "IMAGE_AS_ANSWER"), (slide(c, -dx, -dy), "REVERSED_DIRECTION"),
                    (slide(c, sgn(dx) * abs(dy), sgn(dy) * abs(dx)), "SWAPPED_AMOUNTS"),
                    ((c[0] + b[0], c[1] + b[1]), "ADDED_COORDS")])
    expl = f"The slide is {n(dx)} in x and {n(dy)} in y. Apply it to {pt(c)}: {pt(d)}."
    return mk(rng, tier, prompt, pc(d), cands, expl, fill=fill_pt(d))


def f_rigid_size(rng, tier):
    """8.G.A.1: a rigid motion keeps lengths and angles."""
    if tier == 1:
        d = rng.randint(2, 9)
        motion = rng.choice([f"slides {d} {rng.choice(['left', 'right', 'up', 'down'])}"])
        extra, kind = d, "slide"
    elif tier == 2:
        motion = rng.choice(["is flipped over the x-axis", "is flipped over the y-axis", "is reflected", "is flipped"])
        extra, kind = None, "flip"
    else:
        motion = rng.choice(["turns 90 degrees", "turns 180 degrees", "is rotated", "is turned"])
        extra, kind = None, "turn"
    if rng.random() < 0.5:
        L = rng.randint(2, 9)
        prompt = f"A segment of length {L} {motion}. New length?"
        cands = [(str(2 * L), Fraction(2 * L), "SIZE_CHANGES")]
        if L % 2 == 0:
            cands.append((str(L // 2), Fraction(L, 2), "SIZE_CHANGES"))
        if extra:
            cands.append((str(L + extra), Fraction(L + extra), "LENGTH_CHANGES"))
            if L > extra:
                cands.append((str(L - extra), Fraction(L - extra), "LENGTH_CHANGES"))
        expl = f"Slides, flips and turns keep every length. The segment is still {L}."
        return mk(rng, tier, prompt, (str(L), Fraction(L)), cands, expl, fill=fill_num(L, 1))
    a = rng.choice([10, 20, 30, 40, 50, 60, 70, 80, 100, 110, 120, 130, 140, 150, 160, 170])
    prompt = f"A {a} degree angle {motion}. New angle?"
    cands = []
    if a != 90:
        cands.append((str(180 - a), Fraction(180 - a), "FLIP_SUPPLEMENT" if kind == "flip" else "ANGLE_CHANGES"))
    if a < 90:
        cands.append((str(90 - a), Fraction(90 - a), "ANGLE_CHANGES"))
    if 2 * a <= 180:
        cands.append((str(2 * a), Fraction(2 * a), "ANGLE_CHANGES"))
    if kind == "flip":
        cands.append((n(-a), Fraction(-a), "REFLECTION_NEGATES"))
    expl = f"Rigid moves keep every angle. A {a} degree angle is still {a} degrees."
    return mk(rng, tier, prompt, (str(a), Fraction(a)), cands, expl, fill=[(str(q * 10), Fraction(q * 10)) for q in (a // 10 + 1, a // 10 - 1, a // 10 + 2) if q > 0 and q * 10 != a])


# ---------------------------------------------------------------------------------------------
# Tier 2: reflections
# ---------------------------------------------------------------------------------------------
def refl(p, axis):
    return rx(p) if axis == "x" else ry(p)


def refl_wrongs(p, axis):
    other = "y" if axis == "x" else "x"
    return [(refl(p, other), "WRONG_MIRROR"), (half(p), "BOTH_SIGNS"), ((p[1], p[0]), "SWAPPED_XY")]


def f_reflect(rng, tier):
    p = rpt(rng)
    if abs(p[0]) == abs(p[1]):
        raise Reject
    axis = rng.choice("xy")
    q = refl(p, axis)
    prompt = f"{pt(p)} {rng.choice(['reflected', 'flipped'])} over the {axis}-axis?"
    cands = pcands(refl_wrongs(p, axis))
    changed = "y" if axis == "x" else "x"
    expl = f"Over the {axis}-axis only {changed} changes sign: {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


def f_unreflect(rng, tier):
    img = rpt(rng)
    if abs(img[0]) == abs(img[1]):
        raise Reject
    axis = rng.choice("xy")
    start = refl(img, axis)
    prompt = f"A flip over the {axis}-axis gives {pt(img)}. Start point?"
    cands = pcands([(img, "IMAGE_AS_START")] + refl_wrongs(start, axis)[0:3])
    expl = f"A flip undoes itself: flip {pt(img)} over the {axis}-axis to get {pt(start)}."
    return mk(rng, tier, prompt, pc(start), cands, expl, fill=fill_pt(start))


def f_which_flip(rng, tier):
    p = rpt(rng)
    if abs(p[0]) == abs(p[1]):
        raise Reject
    axis = rng.choice("xy")
    q = refl(p, axis)
    right = f"Over {axis}-axis"
    other = "y" if axis == "x" else "x"
    # slide by the changed coordinate's size, toward zero (a student's slide-for-flip)
    if axis == "y":
        sl = (-p[0], 0)
        sl_text = f"Slide {abs(p[0])} {'left' if p[0] > 0 else 'right'}"
    else:
        sl = (0, -p[1])
        sl_text = f"Slide {abs(p[1])} {'down' if p[1] > 0 else 'up'}"
    cands = [(f"Over {other}-axis", f"Over {other}-axis", "WRONG_MIRROR"), ("Turn 180", "Turn 180", "TURN_FOR_FLIP"),
             (sl_text, sl_text, "SLIDE_FOR_FLIP")]
    # no wrong choice may also work
    works = {f"Over {other}-axis": refl(p, other), "Turn 180": half(p), sl_text: slide(p, *sl)}
    if any(v == q for v in works.values()):
        raise Reject
    prompt = rng.choice([f"{pt(p)} maps to {pt(q)}. Which move?", f"Which move takes {pt(p)} to {pt(q)}?"])
    changed = "y" if axis == "x" else "x"
    expl = f"Only {changed} changes sign, so it is a flip over the {axis}-axis."
    return mk(rng, tier, prompt, (right, right), cands, expl)


def f_fixed_image(rng, tier):
    a = rng.choice([i for i in range(-9, 10) if i])
    axis = rng.choice("xy")
    p = (a, 0) if axis == "x" else (0, a)
    prompt = f"{pt(p)} is {rng.choice(['flipped', 'reflected'])} over the {axis}-axis. Image?"
    cands = pcands([(half(p), "BOTH_SIGNS"), ((p[1], p[0]), "SWAPPED_XY"), ((-p[1], -p[0]), "SWAPPED_XY")])
    expl = f"{pt(p)} is on the {axis}-axis, so a flip over it leaves the point where it is."
    return mk(rng, tier, prompt, pc(p), cands, expl, fill=fill_pt(p))


def f_stays_put(rng, tier):
    a = rng.choice([i for i in range(-9, 10) if i])
    axis = rng.choice("xy")
    p = (a, 0) if axis == "x" else (0, a)
    other = (0, a) if axis == "x" else (a, 0)
    prompt = f"Which point stays put when {rng.choice(['flipped', 'reflected'])} over the {axis}-axis?"
    cands = pcands([(other, "WRONG_MIRROR"), ((a, a), "NOT_ON_AXIS"), ((-a, a), "NOT_ON_AXIS"), ((a, -a), "NOT_ON_AXIS")])
    zero = "y = 0" if axis == "x" else "x = 0"
    expl = f"A point on the {axis}-axis ({zero}) is its own mirror image. {pt(p)} stays put."
    return mk(rng, tier, prompt, pc(p), cands, expl)


def f_which_sign(rng, tier):
    axis = rng.choice("xy")
    prompt = f"{rng.choice(['Flip', 'Reflect'])} over the {axis}-axis. Which coordinate changes sign?"
    right = "y" if axis == "x" else "x"
    wrong = "x" if axis == "x" else "y"
    cands = [(wrong, wrong, "WRONG_MIRROR"), ("Both", "Both", "BOTH_SIGNS"), ("Neither", "Neither", "NOTHING_CHANGES")]
    expl = f"The axis is a mirror: distance along it stays, the other coordinate ({right}) changes sign."
    return mk(rng, tier, prompt, (right, right), cands, expl)


def f_flip_rule(rng, tier):
    axis = rng.choice("xy")
    prompt = f"{rng.choice(['Flip', 'Reflect'])} over the {axis}-axis: (x, y) becomes?"
    right = f"(x, {MINUS}y)" if axis == "x" else f"({MINUS}x, y)"
    wrong = f"({MINUS}x, y)" if axis == "x" else f"(x, {MINUS}y)"
    cands = [(wrong, wrong, "WRONG_MIRROR"), (f"({MINUS}x, {MINUS}y)", "both", "BOTH_SIGNS"), ("(y, x)", "(y, x)", "SWAPPED_XY")]
    expl = f"Over the {axis}-axis only the {'y' if axis == 'x' else 'x'} sign changes: {right}."
    return mk(rng, tier, prompt, (right, right), cands, expl)


# ---------------------------------------------------------------------------------------------
# Tier 3: turns
# ---------------------------------------------------------------------------------------------
def f_turn90(rng, tier):
    p = rpt(rng, 10)
    if rng.random() < 0.12:
        p = rng.choice([(rng_nz(rng, 9), 0), (0, rng_nz(rng, 9))])
    direction = rng.choice(["clockwise", "counterclockwise"])
    q = ccw(p) if direction == "counterclockwise" else cw(p)
    opp = cw(p) if direction == "counterclockwise" else ccw(p)
    prompt = f"{pt(p)} turns 90 degrees {direction} about (0, 0)?"
    cands = pcands([(opp, "WRONG_TURN"), ((p[1], p[0]), "SWAP_ONLY"), (ry(p) if direction == "counterclockwise" else rx(p), "REFLECTED_INSTEAD"),
                    (half(p), "HALF_FOR_QUARTER")])
    if direction == "counterclockwise":
        expl = f"Counterclockwise: (x, y) becomes ({MINUS}y, x). {pt(p)} goes to {pt(q)}."
    else:
        expl = f"Clockwise: (x, y) becomes (y, {MINUS}x). {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


def f_turn180(rng, tier):
    p = rpt(rng)
    q = half(p)
    prompt = f"{pt(p)} turns 180 degrees about {rng.choice(['(0, 0)', 'the origin'])}?"
    cands = pcands([(ry(p), "REFLECTED_INSTEAD"), (rx(p), "REFLECTED_INSTEAD"), (ccw(p), "QUARTER_FOR_HALF"),
                    (cw(p), "QUARTER_FOR_HALF"), ((p[1], p[0]), "SWAP_ONLY")])
    expl = f"A half turn changes both signs: {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


TURN_MOVES = {"90 CCW": ccw, "90 CW": cw, "180 turn": half, "Over x-axis": rx, "Over y-axis": ry}


def f_which_turn(rng, tier):
    p = rpt(rng)
    if abs(p[0]) == abs(p[1]):
        raise Reject
    right = rng.choice(["90 CCW", "90 CW", "180 turn"])
    q = TURN_MOVES[right](p)
    if not inb(q):
        raise Reject
    cands = []
    for name, fn in TURN_MOVES.items():
        if name == right:
            continue
        if fn(p) == q:
            raise Reject  # a second move that also works
        if right in ("90 CCW", "90 CW"):
            mis = "WRONG_TURN" if name in ("90 CCW", "90 CW") else ("HALF_FOR_QUARTER" if name == "180 turn" else "REFLECTED_INSTEAD")
        else:
            mis = "QUARTER_FOR_HALF" if name in ("90 CCW", "90 CW") else "REFLECTED_INSTEAD"
        cands.append((name, name, mis))
    prompt = f"About (0, 0), {pt(p)} maps to {pt(q)}. Which move?"
    expl = f"{pt(p)} to {pt(q)}: {right} (CW is clockwise, CCW is counterclockwise)."
    return mk(rng, tier, prompt, (right, right), cands, expl)


def f_turn_rule(rng, tier):
    kind = rng.choice(["ccw", "cw", "half"])
    word = {"ccw": "90 degree counterclockwise", "cw": "90 degree clockwise", "half": "180 degree"}[kind]
    body = {"ccw": f"({MINUS}y, x)", "cw": f"(y, {MINUS}x)", "half": f"({MINUS}x, {MINUS}y)"}[kind]
    if rng.random() < 0.5:
        prompt = f"Rule for a {word} turn about (0, 0)?"
    else:
        phrase = {"ccw": "90 degrees counterclockwise", "cw": "90 degrees clockwise", "half": "180 degrees"}[kind]
        prompt = f"Turning (x, y) {phrase} gives?"
    pool = {f"({MINUS}y, x)": "ccw", f"(y, {MINUS}x)": "cw", f"({MINUS}x, {MINUS}y)": "half"}
    cands = []
    for text in [f"({MINUS}y, x)", f"(y, {MINUS}x)", f"({MINUS}x, {MINUS}y)", "(y, x)", f"({MINUS}x, y)", f"(x, {MINUS}y)"]:
        if text == body:
            continue
        if text in pool:
            mis = {("ccw", "cw"): "WRONG_TURN", ("cw", "ccw"): "WRONG_TURN"}.get((kind, pool[text]))
            mis = mis or ("HALF_FOR_QUARTER" if pool[text] == "half" else "QUARTER_FOR_HALF")
        elif text == "(y, x)":
            mis = "SWAP_ONLY"
        else:
            mis = "REFLECTED_INSTEAD"
        cands.append((text, text, mis))
    expl = {"ccw": f"Counterclockwise: swap, then negate the new x. (3, 1) goes to ({MINUS}1, 3).",
            "cw": f"Clockwise: swap, then negate the new y. (3, 1) goes to (1, {MINUS}3).",
            "half": f"A half turn negates both. (3, 1) goes to ({MINUS}3, {MINUS}1)."}[kind]
    return mk(rng, tier, prompt, (body, body), cands, expl)


# ---------------------------------------------------------------------------------------------
# Tier 4: dilations
# ---------------------------------------------------------------------------------------------
INT_K = [Fraction(k) for k in (2, 3, 4, 5)]
FRAC_K = [Fraction(1, d) for d in (2, 3, 4)]


def f_dilate_up(rng, tier):
    k = rng.choice(INT_K)
    lim = min(10, 20 // int(k))
    p = rpt(rng, lim)
    q = dil(p, k)
    ki = int(k)
    prompt = f"{pt(p)} dilated by scale factor {ki} from (0, 0)?"
    cands = pcands([((p[0] + ki, p[1] + ki), "ADDED_FACTOR"), ((q[0], p[1]), "ONE_COORD"), ((p[0], q[1]), "ONE_COORD")])
    expl = f"Multiply both coordinates by {ki}: {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


def f_dilate_down(rng, tier):
    k = rng.choice(FRAC_K)
    d = k.denominator
    p = (d * rng_nz(rng, 10 // d), d * rng_nz(rng, 10 // d))
    q = dil(p, k)
    prompt = f"{pt(p)} dilated by scale factor {ftxt(k)} from (0, 0)?"
    cands = pcands([((p[0] * d, p[1] * d), "INVERTED_FACTOR"), ((q[0], p[1]), "ONE_COORD"), ((p[0], q[1]), "ONE_COORD"),
                    ((p[0] - d, p[1] - d), "SUBTRACTED_DENOM")])
    expl = f"Multiply by {ftxt(k)}, which means divide by {d}: {pt(p)} goes to {pt(q)}."
    return mk(rng, tier, prompt, pc(q), cands, expl, fill=fill_pt(q))


def f_scale_factor(rng, tier):
    k = rng.choice(INT_K + FRAC_K)
    if k > 1:
        a = rng.randint(2, 20 // int(k)) if 20 // int(k) >= 2 else 2
        a = min(a, 10)
        b = a * int(k)
    else:
        b = rng.randint(2, 10)
        a = b * k.denominator
        if a > 20:
            raise Reject
    noun = rng.choice(["side", "segment", "leg"])
    prompt = f"A {noun} of {a} becomes {b}. Scale factor?"
    inv = 1 / k
    cands = []
    cands.append((ftxt(inv), inv, "INVERTED_FACTOR"))
    dif = abs(b - a)
    if dif > 1:
        cands.append((str(dif), Fraction(dif), "DIFFERENCE"))
    cands.append((str(b), Fraction(b), "IMAGE_AS_FACTOR"))
    fill = []
    for q in (k + 1, k * 2, k - 1, Fraction(1, 2), Fraction(3), Fraction(1, 3)):
        if q > 0 and q != k and (q.denominator == 1 or q.numerator == 1):
            fill.append((ftxt(q), q))
    expl = f"Scale factor = new length / old length = {b}/{a} = {ftxt(k)}."
    return mk(rng, tier, prompt, (ftxt(k), k), cands, expl, fill=fill)


def f_scaled_length(rng, tier):
    noun = rng.choice(["side", "segment", "leg"])
    if rng.random() < 0.55:
        k = rng.choice(INT_K)
        a = rng.randint(2, min(10, 20 // int(k)))
        r = a * int(k)
        ki = int(k)
        prompt = f"Scale factor {ki}. A {noun} of {a} becomes?"
        cands = [(str(a + ki), Fraction(a + ki), "ADDED_FACTOR"), (str(a * ki * ki), Fraction(a * ki * ki), "AREA_FACTOR"),
                 (str(a), Fraction(a), "SAME_SIZE")]
        expl = f"Lengths grow by the scale factor: {a} x {ki} = {r}."
    else:
        k = rng.choice(FRAC_K)
        d = k.denominator
        m = rng.randint(2, 10)
        a = m * d
        if a > 20:
            raise Reject
        r = m
        prompt = f"Scale factor {ftxt(k)}. A {noun} of {a} becomes?"
        cands = [(str(a * d), Fraction(a * d), "INVERTED_FACTOR"), (str(a - d), Fraction(a - d), "SUBTRACTED_DENOM"),
                 (str(a), Fraction(a), "SAME_SIZE")]
        if a % (d * d) == 0:
            cands.append((str(a // (d * d)), Fraction(a, d * d), "AREA_FACTOR"))
        expl = f"Multiply by {ftxt(k)}, which means divide by {d}: {a} becomes {r}."
    return mk(rng, tier, prompt, (str(r), Fraction(r)), cands, expl, fill=fill_num(r, 1))


def f_scaled_angle(rng, tier):
    if rng.random() < 0.5:
        k = rng.choice(INT_K)
        a = rng.choice([10, 20, 30, 40, 50, 60])
        ki = int(k)
        kt = str(ki)
        cands = [(str(a * ki), Fraction(a * ki), "ANGLES_SCALE"), (str(a + ki), Fraction(a + ki), "ADDED_FACTOR"),
                 (str(180 - a), Fraction(180 - a), "ANGLE_CHANGES")]
    else:
        k = rng.choice(FRAC_K)
        d = k.denominator
        a = rng.choice([x for x in (20, 40, 60, 80, 120, 160) if x % d == 0])
        kt = ftxt(k)
        cands = [(str(a // d), Fraction(a, d), "ANGLES_SCALE"), (str(a * d), Fraction(a * d), "INVERTED_FACTOR"),
                 (str(a - d), Fraction(a - d), "SUBTRACTED_DENOM"), (str(180 - a), Fraction(180 - a), "ANGLE_CHANGES")]
    prompt = f"Scale factor {kt}. A {a} degree angle becomes?"
    expl = f"A dilation changes lengths but never angles. The angle stays {a} degrees."
    return mk(rng, tier, prompt, (str(a), Fraction(a)), cands, expl,
              fill=[(str(q), Fraction(q)) for q in (a + 10, a - 10, a + 20) if q > 0])


def f_grow_shrink(rng, tier):
    k = rng.choice(INT_K + FRAC_K)
    kt = ftxt(k)
    prompt = rng.choice([f"Scale factor {kt} makes the figure?", f"A dilation has scale factor {kt}. The image is?",
                         f"With scale factor {kt}, the image is?"])
    right = "Larger" if k > 1 else "Smaller"
    wrong = "Smaller" if k > 1 else "Larger"
    cands = [(wrong, wrong, "GROW_SHRINK_SWAP"), ("Same size", "Same size", "SAME_SIZE")]
    expl = f"A factor {'above' if k > 1 else 'below'} 1 makes the image {right.lower()}."
    return mk(rng, tier, prompt, (right, right), cands, expl, nwrong=2)


def f_find_factor_points(rng, tier):
    k = rng.choice(INT_K + FRAC_K)
    if k > 1:
        lim = 20 // int(k)
        p = rpt(rng, min(10, lim))
    else:
        d = k.denominator
        p = (d * rng_nz(rng, 10 // d), d * rng_nz(rng, 10 // d))
    q = dil(p, k)
    if q is None or p == q:
        raise Reject
    prompt = f"{pt(p)} dilates to {pt(q)} about (0, 0). Factor?"
    inv = 1 / k
    cands = [(ftxt(inv), inv, "INVERTED_FACTOR")]
    dx = abs(q[0] - p[0])
    if dx > 1:
        cands.append((str(dx), Fraction(dx), "DIFFERENCE"))
    cands.append((str(abs(q[0])), Fraction(abs(q[0])), "IMAGE_AS_FACTOR"))
    fill = [(ftxt(x), x) for x in (k + 1, k * 2, Fraction(1, 2), Fraction(3), Fraction(1, 3), Fraction(2)) if x != k]
    expl = f"Scale factor = image / start: {n(q[0])}/{n(p[0])} = {ftxt(k)}."
    return mk(rng, tier, prompt, (ftxt(k), k), cands, expl, fill=fill)


def f_center(rng, tier):
    k = rng.choice(INT_K + FRAC_K)
    kt = ftxt(k)
    m = int(k) if k > 1 else k.denominator
    prompt = f"(0, 0) dilated by scale factor {kt} from (0, 0)?"
    cands = pcands([((m, m), "CENTER_MOVES"), ((0, m), "CENTER_MOVES"), ((m, 0), "CENTER_MOVES"), ((-m, -m), "CENTER_MOVES")])
    expl = "The center of a dilation stays put. 0 x any factor is 0, so (0, 0) stays (0, 0)."
    return mk(rng, tier, prompt, pc((0, 0)), cands, expl)


# ---------------------------------------------------------------------------------------------
# Tier 5: sequences, size, similarity
# ---------------------------------------------------------------------------------------------
def mv_text(m):
    t = m[0]
    if t == "slide":
        return f"slide {abs(m[1] or m[2])} {dir_word(m[1], m[2])}"
    if t == "rx":
        return "flip over the x-axis"
    if t == "ry":
        return "flip over the y-axis"
    if t == "half":
        return "turn 180 degrees"
    if t == "ccw":
        return "turn 90 CCW"
    return f"dilate by {ftxt(m[1])}"


def mv_apply(m, p):
    if p is None:
        return None
    t = m[0]
    if t == "slide":
        return slide(p, m[1], m[2])
    if t == "dil":
        return dil(p, m[1])
    return {"rx": rx, "ry": ry, "half": half, "ccw": ccw}[t](p)


def mv_fault(m):
    t = m[0]
    if t == "slide":
        return ("slide", -m[1], -m[2]), "REVERSED_DIRECTION"
    if t == "rx":
        return ("ry",), "WRONG_MIRROR"
    if t == "ry":
        return ("rx",), "WRONG_MIRROR"
    if t == "half":
        return ("ccw",), "QUARTER_FOR_HALF"
    if t == "ccw":
        return ("half",), "HALF_FOR_QUARTER"
    return ("dil", 1 / m[1]), "INVERTED_FACTOR"


def rand_rigid(rng, types=("slide", "rx", "ry", "half", "ccw")):
    t = rng.choice(types)
    if t == "slide":
        a = rng.randint(1, 9) * rng.choice([-1, 1])
        return ("slide", a, 0) if rng.random() < 0.5 else ("slide", 0, a)
    return (t,)


def seq_item(rng, tier, p, m1, m2):
    mid = mv_apply(m1, p)
    ans = mv_apply(m2, mid)
    if mid is None or ans is None:
        raise Reject
    # bounds: before a rigid move size <= 10, after a rigid move size <= 10, a dilation image <= 20
    for m, before, after in ((m1, p, mid), (m2, mid, ans)):
        if m[0] == "dil":
            if not inb(before) or not inb(after, 20):
                raise Reject
        elif not (inb(before) and inb(after)):
            raise Reject
    swap = mv_apply(m1, mv_apply(m2, p))
    f1, k1 = mv_fault(m1)
    f2, k2 = mv_fault(m2)
    cands = [(swap, "ORDER_SWAP"), (mid, "ONLY_FIRST"), (mv_apply(m2, p), "ONLY_SECOND"),
             (mv_apply(m2, mv_apply(f1, p)), k1), (mv_apply(f2, mid), k2)]
    if m1[0] == "dil" and m1[1] > 1:
        cands.append((mv_apply(m2, (p[0] + int(m1[1]), p[1] + int(m1[1]))), "ADDED_FACTOR"))
    if m2[0] == "dil" and m2[1] > 1:
        cands.append(((mid[0] + int(m2[1]), mid[1] + int(m2[1])), "ADDED_FACTOR"))
    prompt = f"{pt(p)}: {mv_text(m1)}, then {mv_text(m2)}?"
    expl = f"{mv_text(m1)}: {pt(mid)}; then {mv_text(m2)}: {pt(ans)}."
    return mk(rng, tier, prompt, pc(ans), pcands(cands), expl, fill=fill_pt(ans), must=("ORDER_SWAP",))


def f_seq_rigid(rng, tier):
    m1, m2 = rand_rigid(rng), rand_rigid(rng)
    if m1[0] == m2[0] or (m1[0] == "slide" and m2[0] == "slide"):
        raise Reject
    p = rpt(rng)
    return seq_item(rng, tier, p, m1, m2)


def f_seq_dilate(rng, tier):
    k = rng.choice([Fraction(2), Fraction(3), Fraction(4), Fraction(1, 2)])
    d = ("dil", k)
    r = rand_rigid(rng, ("slide", "slide", "slide", "slide", "rx", "ry", "half", "ccw"))
    if k < 1:
        p = (2 * rng_nz(rng, 5), 2 * rng_nz(rng, 5))
    else:
        p = rpt(rng, 5)
    if r[0] == "slide":
        r = ("slide", rng.randint(1, 3) * sgn(r[1] or r[2]), 0) if r[1] else ("slide", 0, rng.randint(1, 3) * sgn(r[2]))
    return seq_item(rng, tier, p, *( (r, d) if rng.random() < 0.5 else (d, r) ))


def f_which_move_size(rng, tier):
    prompt = rng.choice(["Which move can change a shape's size?", "Which move can make a shape bigger?",
                         "Which move can shrink a shape?", "Which move is NOT rigid?"])
    cands = [(w, w, "RIGID_CHANGES_SIZE") for w in ("Slide", "Flip", "Turn")]
    expl = "Slides, flips and turns are rigid: size stays. Only a dilation changes size."
    return mk(rng, tier, prompt, ("Dilation", "Dilation"), cands, expl)


def f_which_factor(rng, tier):
    kind = rng.choice(["small", "big", "same"])
    ints = [Fraction(x) for x in (2, 3, 4, 5)]
    fr = [Fraction(1, d) for d in (2, 3, 4)]
    if kind == "small":
        prompt = rng.choice(["Which scale factor shrinks a figure?", "Which factor makes a shape smaller?"])
        right = rng.choice(fr)
        rest = rng.sample(ints, 3)
        expl = f"A factor below 1 shrinks a figure. {ftxt(right)} is below 1."
        cands = [(ftxt(x), x, "GROW_SHRINK_SWAP") for x in rest]
    elif kind == "big":
        prompt = rng.choice(["Which scale factor enlarges a figure?", "Which factor makes a shape larger?"])
        right = rng.choice(ints)
        rest = fr[:]
        expl = f"A factor above 1 enlarges a figure. {ftxt(right)} is above 1."
        cands = [(ftxt(x), x, "GROW_SHRINK_SWAP") for x in rest]
    else:
        prompt = rng.choice(["Which scale factor keeps the size the same?", "Which factor leaves a shape's size alone?"])
        right = Fraction(1)
        rest = [rng.choice(ints), rng.choice(ints), rng.choice(fr)]
        if len({*rest}) < 3:
            raise Reject
        expl = "Scale factor 1 multiplies every length by 1, so the size stays the same."
        cands = [(ftxt(x), x, "SAME_SIZE") for x in rest]
    return mk(rng, tier, prompt, (ftxt(right), right), cands, expl)


RIGID_WORDS = ["Slide", "Flip", "Turn"]


def f_similar(rng, tier):
    w = rng.choice(RIGID_WORDS)
    k = rng.choice(INT_K + FRAC_K)
    if rng.random() < 0.5:
        prompt = f"{w} it, then dilate by {ftxt(k)}. The image is?"
    else:
        prompt = f"Dilate by {ftxt(k)}, then {w.lower()} it. The image is?"
    cands = [("Congruent", "Congruent", "DILATION_CONGRUENT"), ("Neither", "Neither", "NEEDS_SAME_SIZE")]
    expl = "Same shape, new size: the image is similar to the start. Congruent needs the same size."
    return mk(rng, tier, prompt, ("Similar", "Similar"), cands, expl, nwrong=2)


SIZE_WORDS = ("Stays same", "Gets bigger", "Gets smaller")


def f_size_change(rng, tier):
    kind = rng.choice(["rigid", "dil", "two"])
    if kind == "rigid":
        a, b = rng.sample(RIGID_WORDS, 2)
        prompt = f"{a} it, then {b.lower()} it. Its size?"
        right = "Stays same"
        cands = [("Gets bigger", "Gets bigger", "RIGID_CHANGES_SIZE"), ("Gets smaller", "Gets smaller", "RIGID_CHANGES_SIZE")]
        expl = "Slides, flips and turns keep size, so two of them keep size."
    elif kind == "dil":
        w = rng.choice(RIGID_WORDS)
        k = rng.choice(INT_K + FRAC_K)
        if rng.random() < 0.5:
            prompt = f"{w} it, then dilate by {ftxt(k)}. Its size?"
        else:
            prompt = f"Dilate by {ftxt(k)}, then {w.lower()} it. Its size?"
        right = "Gets bigger" if k > 1 else "Gets smaller"
        wrong = "Gets smaller" if k > 1 else "Gets bigger"
        cands = [("Stays same", "Stays same", "SAME_SIZE"), (wrong, wrong, "GROW_SHRINK_SWAP")]
        expl = f"Only the dilation changes size, and a factor {'above' if k > 1 else 'below'} 1 makes it {right[5:]}."
    else:
        k1 = rng.choice(INT_K[:3])
        k2 = rng.choice(FRAC_K)
        prod = k1 * k2
        if rng.random() < 0.5:
            k1, k2 = k2, k1
        prompt = f"Dilate by {ftxt(k1)}, then by {ftxt(k2)}. Its size?"
        right = "Stays same" if prod == 1 else ("Gets bigger" if prod > 1 else "Gets smaller")
        cands = [(w, w, "COMPOSE_WRONG") for w in SIZE_WORDS if w != right]
        expl = f"Multiply the factors: {ftxt(k1)} x {ftxt(k2)} = {ftxt(prod)}, so the size {right.lower().replace('stays same', 'stays the same')}."
    return mk(rng, tier, prompt, (right, right), cands, expl, nwrong=2)


PAST = {"slide": "slid", "flip": "flipped", "turn": "turned"}


def f_seq_measure(rng, tier):
    kind = rng.choice(["angle_rigid", "angle_dil", "len_dil"])
    a, b = rng.sample(["slide", "flip", "turn"], 2)
    if kind == "angle_rigid":
        ang = rng.choice([10, 20, 30, 40, 50, 60, 70, 80, 100, 110, 120, 130, 140, 150, 160, 170])
        prompt = f"A {ang} degree angle is {PAST[a]}, then {PAST[b]}. New angle?"
        cands = []
        if ang != 90:
            cands.append((str(180 - ang), Fraction(180 - ang), "FLIP_SUPPLEMENT"))
        if ang < 90:
            cands.append((str(90 - ang), Fraction(90 - ang), "ANGLE_CHANGES"))
        if 2 * ang <= 180:
            cands.append((str(2 * ang), Fraction(2 * ang), "ANGLE_CHANGES"))
        expl = f"Rigid moves keep angles, however many you do. Still {ang} degrees."
        return mk(rng, tier, prompt, (str(ang), Fraction(ang)), cands, expl,
                  fill=[(str(q), Fraction(q)) for q in (ang + 10, ang - 10, ang + 20) if q > 0])
    k = rng.choice(INT_K + FRAC_K)
    kt = ftxt(k)
    if kind == "angle_dil":
        if k > 1:
            ang = rng.choice([10, 20, 30, 40, 50, 60])
            cands = [(str(ang * int(k)), Fraction(ang * int(k)), "ANGLES_SCALE"), (str(ang + int(k)), Fraction(ang + int(k)), "ADDED_FACTOR"),
                     (str(180 - ang), Fraction(180 - ang), "ANGLE_CHANGES")]
        else:
            d = k.denominator
            ang = rng.choice([x for x in (20, 40, 60, 80, 120, 160) if x % d == 0])
            cands = [(str(ang // d), Fraction(ang, d), "ANGLES_SCALE"), (str(ang * d), Fraction(ang * d), "INVERTED_FACTOR"),
                     (str(180 - ang), Fraction(180 - ang), "ANGLE_CHANGES")]
        prompt = f"A {ang} degree angle is {PAST[a]}, then dilated by {kt}. New angle?"
        expl = f"Flips, slides, turns and dilations all keep angles. Still {ang} degrees."
        return mk(rng, tier, prompt, (str(ang), Fraction(ang)), cands, expl,
                  fill=[(str(q), Fraction(q)) for q in (ang + 10, ang - 10, ang + 20) if q > 0])
    if k > 1:
        ki = int(k)
        L = rng.randint(2, min(10, 20 // ki))
        r = L * ki
        cands = [(str(L), Fraction(L), "SAME_SIZE"), (str(L + ki), Fraction(L + ki), "ADDED_FACTOR"),
                 (str(L * ki * ki), Fraction(L * ki * ki), "AREA_FACTOR")]
    else:
        d = k.denominator
        r = rng.randint(2, 10)
        L = r * d
        if L > 20:
            raise Reject
        cands = [(str(L), Fraction(L), "SAME_SIZE"), (str(L * d), Fraction(L * d), "INVERTED_FACTOR"),
                 (str(L - d), Fraction(L - d), "SUBTRACTED_DENOM")]
    prompt = f"A side of {L} is {PAST[a]}, then dilated by {kt}. New length?"
    expl = f"The {a} keeps length {L}; the dilation multiplies by {kt}. New length {r}."
    return mk(rng, tier, prompt, (str(r), Fraction(r)), cands, expl, fill=fill_num(r, 1))


# ---------------------------------------------------------------------------------------------
# Tier plans and assembly
# ---------------------------------------------------------------------------------------------
FAMILIES = {
    1: [(f_slide_apply, 11), (f_slide_find, 9), (f_rule_apply, 6), (f_rule_find, 4), (f_slide_example, 5), (f_rigid_size, 5)],
    2: [(f_reflect, 12), (f_unreflect, 7), (f_which_flip, 8), (f_rigid_size, 4), (f_fixed_image, 3), (f_stays_put, 2),
        (f_which_sign, 2), (f_flip_rule, 2)],
    3: [(f_turn90, 14), (f_turn180, 8), (f_which_turn, 8), (f_turn_rule, 4), (f_rigid_size, 6)],
    4: [(f_dilate_up, 10), (f_dilate_down, 8), (f_scale_factor, 6), (f_scaled_length, 4), (f_scaled_angle, 3),
        (f_grow_shrink, 6), (f_find_factor_points, 2), (f_center, 1)],
    5: [(f_seq_rigid, 14), (f_seq_dilate, 6), (f_which_move_size, 3), (f_which_factor, 3), (f_similar, 4),
        (f_size_change, 4), (f_seq_measure, 6)],
}


def _balanced(count: int, n_pos: int, rng: random.Random) -> list:
    pos = [i % n_pos for i in range(count)]
    rng.shuffle(pos)
    return pos


def gen_tier(tier: int, count: int, declared, rng: random.Random) -> list:
    raw, seen = [], set()
    for fn, quota in FAMILIES[tier]:
        got, attempts = 0, 0
        while got < quota:
            attempts += 1
            if attempts > 20000:
                raise RuntimeError(f"tier {tier}: {fn.__name__} could not make {quota} items")
            try:
                it = fn(rng, tier)
            except Reject:
                continue
            if it["prompt"] in seen:
                continue
            seen.add(it["prompt"])
            raw.append(it)
            got += 1
    if len(raw) != count:
        raise RuntimeError(f"tier {tier}: plan makes {len(raw)} items, manifest wants {count}")
    rng.shuffle(raw)
    # answer positions: balanced per choice count
    by_n: dict = {}
    for it in raw:
        by_n.setdefault(1 + len(it["wrongs"]), []).append(it)
    out = []
    for npos, group in sorted(by_n.items()):
        slots = _balanced(len(group), npos, rng)
        for it, slot in zip(group, slots):
            wrongs = list(it["wrongs"])
            rng.shuffle(wrongs)
            choices = [t for t, _ in wrongs]
            mis = [m for _, m in wrongs]
            choices.insert(slot, it["correct"])
            mis.insert(slot, None)
            for m in mis:
                if m is not None and m != "ARITH" and m not in declared:
                    raise RuntimeError(f"undeclared misconception {m}")
            out.append({"tier": tier, "prompt": it["prompt"], "choices": choices, "answer": slot,
                        "misconceptions": mis, "explanation": it["explanation"]})
    rng.shuffle(out)
    return out


def generate(manifest: dict, rng: random.Random) -> list:
    declared = set(manifest["misconceptions"])
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], manifest["items_per_tier"], declared, rng))
    return items
