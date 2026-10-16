"""Procedural generator for the pythagorean-theorem cartridge (fnm-cart/1, grade 8).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]``, items in the §4 shape without
``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every length is carried as its SQUARE (an int).  A whole length w is the square w*w; a root is the
  square n.  ``fmt(sq)`` renders a perfect square as the whole number and anything else as ``√n``
  (never simplified).  Choices are compared by square, so ``√16`` and ``4`` can never both appear and
  a wrong choice can never equal the right one in value.
* Bounds (PROTOCOL §4b, Pythagorean): sides 1-10, every square <= 100, every correct sum or difference
  (box: three squares) <= 100.  Whole answers come only from 3-4-5, 6-8-10 and the box diagonals
  1-2-2, 2-4-4, 2-3-6, 1-4-8, 4-4-7.  Every other length is an unsimplified ``√n``, n in 2..99.
  (The box 3-6-6 -> 9 is also a perfect square and is excluded: it is not in the §4b list.)
* Wrong choices come from modelled misconceptions first (``cands_*``); ``ARITH`` only fills.
"""
from __future__ import annotations

import random
from math import isqrt, sqrt

MINUS = "−"  # U+2212

WHOLE_HYP = [(3, 4), (4, 3), (6, 8), (8, 6)]  # (leg, leg) with a whole hypotenuse
WHOLE_LEG = [(5, 3), (5, 4), (10, 6), (10, 8)]  # (hypotenuse, leg) with a whole other leg
BOX_WHOLE = [(1, 2, 2), (2, 4, 4), (2, 3, 6), (1, 4, 8), (4, 4, 7)]


def is_sq(n: int) -> bool:
    return isqrt(n) ** 2 == n


def fmt(sq: int) -> str:
    """Choice text of the length whose square is ``sq``."""
    r = isqrt(sq)
    return str(r) if r * r == sq else f"√{sq}"


def whole(w: int) -> int:
    """Square of the whole length w."""
    return w * w


def coord(n: int) -> str:
    return f"{MINUS}{-n}" if n < 0 else str(n)


def pt(x: int, y: int) -> str:
    return f"({coord(x)}, {coord(y)})"


HYP_ROOT = [(a, b) for a in range(1, 10) for b in range(1, 10)
            if a * a + b * b <= 99 and not is_sq(a * a + b * b)]
LEG_ROOT = [(c, a) for c in range(2, 11) for a in range(1, c) if not is_sq(c * c - a * a)]
BOX_ROOT = [(a, b, c) for a in range(1, 10) for b in range(1, 10) for c in range(1, 10)
            if a * a + b * b + c * c <= 99 and not is_sq(a * a + b * b + c * c)]


# ---------------------------------------------------------------------------------------------
# Misconception candidates: lists of (label, square). Order = priority.
# ---------------------------------------------------------------------------------------------
def cands_hyp(a: int, b: int, rng=None):
    """Legs a, b -> wrong hypotenuses."""
    n = a * a + b * b
    opt = [("ROOT_OF_LEG_SUM", a + b), ("DOUBLED_FOR_SQUARE", 2 * a + 2 * b)]
    if rng is not None:
        rng.shuffle(opt)
    return [("ADDED_LEGS", whole(a + b)), ("NO_ROOT", whole(n))] + opt


def cands_leg(c: int, a: int, rng=None):
    """Hypotenuse c, leg a -> wrong other legs."""
    n = c * c - a * a
    opt = [("SUBTRACTED_SIDES", whole(c - a)), ("ROOT_OF_DIFF", c - a)]
    if rng is not None:
        rng.shuffle(opt)
    return [("ADDED_SQUARES", c * c + a * a), ("NO_ROOT", whole(n))] + opt


def cands_dist(dx: int, dy: int, wrong_gaps=None, rng=None):
    """Gaps dx (across), dy (up) -> wrong distances.  ``wrong_gaps`` = (gx, gy) when the points
    straddle zero and a student ignores the signs."""
    n = dx * dx + dy * dy
    base = [("TAXICAB", whole(dx + dy)), ("NO_ROOT", whole(n)), ("ONE_LEG", whole(dx)),
            ("ROOT_OF_LEG_SUM", dx + dy)]
    if wrong_gaps is not None:
        gx, gy = wrong_gaps
        sq = gx * gx + gy * gy
        if sq > 0:
            return [("NEG_DIFF", sq)] + base
    return base


def cands_box(a: int, b: int, c: int):
    """Box a by b by c -> wrong space diagonals."""
    return [("ADDED_ALL", whole(a + b + c)), ("FACE_ONLY", a * a + b * b),
            ("NO_ROOT", whole(a * a + b * b + c * c))]


# ---------------------------------------------------------------------------------------------
# Item construction
# ---------------------------------------------------------------------------------------------
def _balanced(count: int, k: int, rng: random.Random) -> list:
    """count positions 0..k-1, each used count//k (+1 for the remainder) times, shuffled."""
    out = [i % k for i in range(count)]
    rng.shuffle(out)
    return out


def _check_lengths(prompt: str, choices: list, explanation: str):
    if len(prompt) > 60 or any(len(c) > 14 for c in choices) or len(explanation) > 160:
        raise ValueError(f"over length: {prompt!r} {choices} {explanation!r}")


def _item(tier, prompt, choices, answer, labels, explanation):
    _check_lengths(prompt, choices, explanation)
    return {"tier": tier, "prompt": prompt, "choices": choices, "answer": answer,
            "misconceptions": labels, "explanation": explanation}


def length_item(rng, tier, prompt, correct_sq, cands, pos, explanation, declared, n_wrong=3):
    """4-choice item whose choices are lengths.  ``cands`` = ordered [(label, square)]."""
    seen = {correct_sq}
    wrongs = []
    for label, sq in cands:
        if sq in seen or sq < 1 or sq > 999 * 999:
            continue
        if label not in declared:
            raise KeyError(label)
        seen.add(sq)
        wrongs.append((label, sq))
    wrongs = wrongs[:n_wrong]
    if len(wrongs) < n_wrong:  # ARITH fill: a nearby length
        w = isqrt(correct_sq)
        fill = [whole(w + 1), whole(w + 2), whole(max(w - 1, 1)), correct_sq + 1, correct_sq + 2,
                max(correct_sq - 1, 1), whole(w + 3)]
        rng.shuffle(fill)
        for sq in fill:
            if len(wrongs) == n_wrong:
                break
            if sq not in seen and sq >= 1:
                seen.add(sq)
                wrongs.append(("ARITH", sq))
    if len(wrongs) < n_wrong:
        raise RuntimeError("cannot fill choices")
    rng.shuffle(wrongs)
    choices = [fmt(sq) for _, sq in wrongs]
    labels = [lab for lab, _ in wrongs]
    choices.insert(pos, fmt(correct_sq))
    labels.insert(pos, None)
    return _item(tier, prompt, choices, pos, labels, explanation)


def _gen(count, rng, make, max_attempts=100000):
    """Run make(i) until ``count`` items with unique prompts exist."""
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError("could not generate enough unique items")
        it = make(len(items))
        if it is None or it["prompt"] in prompts:
            continue
        prompts.add(it["prompt"])
        items.append(it)
    return items


# ---------------------------------------------------------------------------------------------
# Tier 1: find the hypotenuse
# ---------------------------------------------------------------------------------------------
T1_TEMPLATES = [
    "Legs {a} and {b}. Hypotenuse?",
    "A right triangle has legs {a} and {b}. Hypotenuse?",
    "Right triangle, legs {a} and {b}. Longest side?",
    "Legs {a} and {b} meet at a right angle. Hypotenuse?",
]


def gen_t1(rng, declared, n):
    positions = _balanced(n, 4, rng)
    kinds = [True] * 8 + [False] * (n - 8)  # 8 whole answers (3-4-5, 6-8-10)
    rng.shuffle(kinds)

    def make(i):
        if kinds[i]:
            a, b = rng.choice(WHOLE_HYP)
        else:
            a, b = rng.choice(HYP_ROOT)
        s = a * a + b * b
        prompt = rng.choice(T1_TEMPLATES).format(a=a, b=b)
        expl = f"{a}^2 + {b}^2 = {a * a} + {b * b} = {s}, so c = {fmt(s)}."
        return length_item(rng, 1, prompt, s, cands_hyp(a, b, rng), positions[i], expl, declared)

    return _gen(n, rng, make)


# ---------------------------------------------------------------------------------------------
# Tier 2: find a leg
# ---------------------------------------------------------------------------------------------
T2_TEMPLATES = [
    "Hypotenuse {c}, one leg {a}. Other leg?",
    "A right triangle: hypotenuse {c}, a leg {a}. Other leg?",
    "Hypotenuse {c} and a leg of {a}. How long is the other leg?",
    "Right triangle, longest side {c}, leg {a}. Other leg?",
]


def gen_t2(rng, declared, n):
    positions = _balanced(n, 4, rng)
    kinds = [True] * 8 + [False] * (n - 8)
    rng.shuffle(kinds)

    def make(i):
        if kinds[i]:
            c, a = rng.choice(WHOLE_LEG)
        else:
            c, a = rng.choice(LEG_ROOT)
        s = c * c - a * a
        prompt = rng.choice(T2_TEMPLATES).format(c=c, a=a)
        expl = f"{c}^2 − {a}^2 = {c * c} − {a * a} = {s}, so the leg is {fmt(s)}."
        return length_item(rng, 2, prompt, s, cands_leg(c, a, rng), positions[i], expl, declared)

    return _gen(n, rng, make)


# ---------------------------------------------------------------------------------------------
# Tier 3: is it a right triangle?
# ---------------------------------------------------------------------------------------------
def _is_right(a, b, c):
    a, b, c = sorted((a, b, c))
    return a * a + b * b == c * c


def _no_triples():
    """Sorted (a <= b <= c) non-right triples that form a triangle, a^2 + b^2 <= 100."""
    out = []
    for a in range(1, 11):
        for b in range(a, 11):
            for c in range(b, 11):
                if c >= 4 and c < a + b and a * a + b * b <= 100 and not _is_right(a, b, c):
                    out.append((a, b, c))
    return out


NO_ALL = _no_triples()
NO_CONSEC = [t for t in NO_ALL if t[1] == t[0] + 1 and t[2] == t[0] + 2]
NO_CLOSE = [t for t in NO_ALL if abs(t[0] ** 2 + t[1] ** 2 - t[2] ** 2) <= 2 and t not in NO_CONSEC]
NO_OTHER = [t for t in NO_ALL if t not in NO_CONSEC and t not in NO_CLOSE]
YES_TRIPLES = [(3, 4, 5), (6, 8, 10)]


def _no_label(t):
    a, b, c = t
    if t in NO_CONSEC:
        return "CONSECUTIVE"
    if abs(a * a + b * b - c * c) <= 2:
        return "CLOSE_ENOUGH"
    return "ANY_TRIANGLE"


def _perms(t):
    import itertools
    return sorted(set(itertools.permutations(t)))


T3_YN = ["Sides {a}, {b}, {c}. Right triangle?",
         "A triangle has sides {a}, {b} and {c}. Is it a right triangle?"]
T3_WHICH = [
    "Which sides make a right triangle?",
    "Which sides make a right corner?",
    "Which side lengths form a right triangle?",
    "A carpenter needs a square corner. Which sides?",
    "Which set of sides has a right angle?",
    "Which three sides make a right triangle?",
    "Which lengths fit a right triangle?",
    "Which set is a right triangle's sides?",
]


def _yn_item(rng, pos, a, b, c, truth, wrong_label, explanation):
    prompt = rng.choice(T3_YN).format(a=a, b=b, c=c)
    choices = ["Yes", "No"] if pos == 0 else ["No", "Yes"]
    ans = choices.index("Yes" if truth else "No")
    labels = [None if i == ans else wrong_label for i in range(2)]
    return _item(3, prompt, choices, ans, labels, explanation)


def gen_t3(rng, declared, n):
    # 20 Yes/No, 8 "which sides" (4 choices), 12 "which is the hypotenuse" (3 choices)
    n_yn, n_which = 20, 8
    n_hyp = n - n_yn - n_which
    items, prompts = [], set()

    # -- Yes/No: 10 yes, 10 no (3 close, 2 consecutive, 5 other)
    pos2 = _balanced(n_yn, 2, rng)
    plan = [("Y", None)] * 10 + [("N", NO_CLOSE)] * 3 + [("N", NO_CONSEC)] * 2 + [("N", NO_OTHER)] * 5
    rng.shuffle(plan)
    asc_budget = 3  # three yes-items listed in ascending order
    yes_asc = [True] * asc_budget + [False] * (10 - asc_budget)
    rng.shuffle(yes_asc)
    yi = 0
    attempts = 0
    k = 0
    while k < n_yn:
        attempts += 1
        if attempts > 100000:
            raise RuntimeError("t3 yes/no")
        kind, pool = plan[k]
        if kind == "Y":
            base = rng.choice(YES_TRIPLES)
            a, b, c = sorted(base) if yes_asc[yi] else rng.choice(_perms(base))
            if not yes_asc[yi] and (a, b, c) == tuple(sorted(base)):
                continue
            label = "ADD_SIDES" if c == max(a, b, c) else "ORDER_AS_GIVEN"
            lo, mid, hi = sorted(base)
            expl = f"{lo}^2 + {mid}^2 = {lo * lo} + {mid * mid} = {hi * hi} = {hi}^2. Yes."
            it = _yn_item(rng, pos2[k], a, b, c, True, label, expl)
        else:
            a, b, c = rng.choice(pool)
            lo, mid, hi = a, b, c
            expl = f"{lo}^2 + {mid}^2 = {lo * lo + mid * mid}, but {hi}^2 = {hi * hi}. Not equal, so no."
            it = _yn_item(rng, pos2[k], a, b, c, False, _no_label((a, b, c)), expl)
        if it["prompt"] in prompts:
            continue
        prompts.add(it["prompt"])
        items.append(it)
        if kind == "Y":
            yi += 1
        k += 1

    # -- Which sides make a right triangle? (8 distinct prompts, one per framing)
    pos4 = _balanced(n_which, 4, rng)
    framings = list(T3_WHICH)
    rng.shuffle(framings)
    for j in range(n_which):
        right = rng.choice(YES_TRIPLES)
        while True:
            d = [rng.choice(NO_CONSEC), rng.choice(NO_CLOSE), rng.choice(NO_OTHER)]
            if len(set(d)) == 3 and len({_no_label(t) for t in d}) == 3:
                break
        texts = [f"{t[0]}, {t[1]}, {t[2]}" for t in d]
        labels = [_no_label(t) for t in d]
        order = list(range(3))
        rng.shuffle(order)
        texts = [texts[o] for o in order]
        labels = [labels[o] for o in order]
        texts.insert(pos4[j], f"{right[0]}, {right[1]}, {right[2]}")
        labels.insert(pos4[j], None)
        expl = (f"{right[0]}^2 + {right[1]}^2 = {right[0] ** 2 + right[1] ** 2} = {right[2]}^2. "
                f"The other sets fail the test.")
        items.append(_item(3, framings[j], texts, pos4[j], labels, expl))

    # -- Right triangle with sides a, b, √n: which is the hypotenuse?
    pos3 = _balanced(n_hyp, 3, rng)
    pool = [(a, b) for a in range(1, 10) for b in range(a + 1, 10)
            if a * a + b * b <= 99 and not is_sq(a * a + b * b)
            and sqrt(a * a + b * b) - b >= 0.3]
    k, attempts = 0, 0
    while k < n_hyp:
        attempts += 1
        if attempts > 100000:
            raise RuntimeError("t3 hyp")
        a, b = rng.choice(pool)
        s = a * a + b * b
        listed = [str(a), str(b), f"√{s}"]
        rng.shuffle(listed)
        prompt = f"Right triangle, sides {', '.join(listed)}. Hypotenuse?"
        if prompt in prompts:
            continue
        prompts.add(prompt)
        choices = [None] * 3
        labels = [None] * 3
        # choices in a fixed set {a, b, √s}; answer placed at pos3[k]
        others = [str(a), str(b)]
        rng.shuffle(others)
        choices[pos3[k]] = f"√{s}"
        it = iter(others)
        for i in range(3):
            if choices[i] is None:
                choices[i] = next(it)
                labels[i] = "LEG_AS_LONGEST"
        expl = f"{b}^2 = {b * b}, but {a}^2 + {b}^2 = {s}. So √{s} is longer: the hypotenuse."
        items.append(_item(3, prompt, choices, pos3[k], labels, expl))
        k += 1

    rng.shuffle(items)
    return items


# ---------------------------------------------------------------------------------------------
# Tier 4: distance on the plane
# ---------------------------------------------------------------------------------------------
T4_TEMPLATES = [
    "Distance from {p} to {q}?",
    "How far is {p} from {q}?",
    "Points A{p} and B{q}. Length of AB?",
]
T4_ORIGIN = [
    "Distance from (0, 0) to {q}?",
    "How far is {q} from the origin?",
]


def _span(rng, d, sign, cross):
    """(start, end) integers in -10..10, end - start = sign * d; ``cross`` True means the two ends
    sit on opposite sides of zero, False means they do not."""
    for _ in range(1000):
        lo, hi = (-10, 10 - d) if sign > 0 else (-10 + d, 10)
        s = rng.randint(lo, hi)
        e = s + sign * d
        if (s * e < 0) == cross:
            return s, e
    return None


def gen_t4(rng, declared, n):
    positions = _balanced(n, 4, rng)
    kinds = ["cross"] * 14 + ["flat"] * 20 + ["origin"] * (n - 34)
    rng.shuffle(kinds)

    def make(i):
        kind = kinds[i]
        if rng.random() < 0.3:
            dx, dy = rng.choice(WHOLE_HYP)
        else:
            dx, dy = rng.choice(HYP_ROOT)
        n_sq = dx * dx + dy * dy
        sx, sy = rng.choice((1, -1)), rng.choice((1, -1))
        wrong_gaps = None
        if kind == "origin":
            x2, y2 = sx * dx, sy * dy
            prompt = rng.choice(T4_ORIGIN).format(q=pt(x2, y2))
        else:
            if kind == "cross":
                ax_cross = rng.choice(("x", "y", "both"))
                cx, cy = ax_cross in ("x", "both"), ax_cross in ("y", "both")
            else:
                cx = cy = False
            xs = _span(rng, dx, sx, cx)
            ys = _span(rng, dy, sy, cy)
            if xs is None or ys is None:
                return None
            (x1, x2), (y1, y2) = xs, ys
            if (x1, y1) == (0, 0):
                return None
            gx = abs(abs(x2) - abs(x1)) if cx else dx
            gy = abs(abs(y2) - abs(y1)) if cy else dy
            if kind == "cross":
                wrong_gaps = (gx, gy)
            prompt = rng.choice(T4_TEMPLATES).format(p=pt(x1, y1), q=pt(x2, y2))
        expl = f"Across {dx}, up {dy}: {dx}^2 + {dy}^2 = {n_sq}, so the distance is {fmt(n_sq)}."
        return length_item(rng, 4, prompt, n_sq, cands_dist(dx, dy, wrong_gaps), positions[i],
                           expl, declared)

    return _gen(n, rng, make)


# ---------------------------------------------------------------------------------------------
# Tier 5: stories and 3D
# ---------------------------------------------------------------------------------------------
# find the hypotenuse from two legs: (template, units)
HYP_STORIES = [
    ("Walk {a} {u} north, then {b} {u} east. How far from the start?", ("km", "mi", "m")),
    ("A {obj} is {a} {u} wide and {b} {u} tall. Diagonal length?", ("ft", "m")),
    ("A ramp rises {a} {u} over {b} {u} of ground. Ramp length?", ("ft", "m")),
    ("A TV screen is {a} in by {b} in. How long is its diagonal?", ("in",)),
    ("A field is {a} {u} by {b} {u}. Corner to corner distance?", ("m", "yd", "ft")),
    ("A boat sails {a} km east, then {b} km south. Distance from dock?", ("km",)),
]
SQUARE_STORY = "A square has side {s} {u}. How long is its diagonal?"
# find a leg from the hypotenuse and the other leg
LEG_STORIES = [
    ("{A} {c} {u} ladder, base {a} {u} from the wall. How high?", ("ft", "m")),
    ("{A} {c} {u} ladder reaches {a} {u} up. How far out is its base?", ("ft", "m")),
    ("{A} {c} {u} wire runs from a pole's top to {a} {u} out. Pole height?", ("ft", "m")),
    ("{A} {c} {u} slide is {a} {u} tall. How far out does it reach?", ("ft", "m")),
]
BOX_STORIES = [
    "Box {a} by {b} by {c}. Longest diagonal?",
    "A box is {a} by {b} by {c}. Longest diagonal inside?",
    "{A} {a} by {b} by {c} {u} crate. Longest diagonal?",
]
T5_BOX_UNITS = ("ft", "m", "cm")


def gen_t5(rng, declared, n):
    positions = _balanced(n, 4, rng)
    kinds = ["leg"] * 10 + ["hyp"] * 14 + ["square"] * 4 + ["box"] * (n - 28)
    rng.shuffle(kinds)
    whole_quota = {"leg": 4, "hyp": 6, "box": 5}
    totals = {k: kinds.count(k) for k in whole_quota}
    # Decide per kind occurrence whether it is a whole-answer item (exact quotas)
    flags = {k: [True] * whole_quota[k] + [False] * (totals[k] - whole_quota[k]) for k in whole_quota}
    for k in flags:
        rng.shuffle(flags[k])

    def make(i):
        kind = kinds[i]
        if kind == "square":
            s_side = rng.randint(2, 7)
            u = rng.choice(("cm", "ft", "m"))
            sq = 2 * s_side * s_side
            if is_sq(sq):
                return None
            prompt = SQUARE_STORY.format(s=s_side, u=u)
            expl = f"{s_side}^2 + {s_side}^2 = {s_side * s_side} + {s_side * s_side} = {sq}, so it is {fmt(sq)}."
            return length_item(rng, 5, prompt, sq, cands_hyp(s_side, s_side, rng), positions[i], expl,
                               declared)
        w = flags[kind][kinds[:i].count(kind)]
        if kind == "leg":
            c, a = rng.choice(WHOLE_LEG) if w else rng.choice(LEG_ROOT)
            tpl, units = rng.choice(LEG_STORIES)
            prompt = tpl.format(c=c, a=a, u=rng.choice(units), A=_a(c))
            s = c * c - a * a
            expl = f"{c}^2 − {a}^2 = {c * c} − {a * a} = {s}, so it is {fmt(s)}."
            it = length_item(rng, 5, prompt, s, cands_leg(c, a, rng), positions[i], expl, declared)
        elif kind == "hyp":
            a, b = rng.choice(WHOLE_HYP) if w else rng.choice(HYP_ROOT)
            tpl, units = rng.choice(HYP_STORIES)
            u = rng.choice(units)
            obj = "rectangle"
            if "{obj}" in tpl:
                door_ok = b > a and ((u == "ft" and b >= 6) or (u == "m" and b >= 2))
                obj = "door" if door_ok else rng.choice(("rectangle", "window", "sign", "panel"))
            prompt = tpl.format(a=a, b=b, u=u, obj=obj)
            s = a * a + b * b
            expl = f"{a}^2 + {b}^2 = {a * a} + {b * b} = {s}, so it is {fmt(s)}."
            it = length_item(rng, 5, prompt, s, cands_hyp(a, b, rng), positions[i], expl, declared)
        else:  # box
            if w:
                dims = list(rng.choice(BOX_WHOLE))
            else:
                dims = list(rng.choice(BOX_ROOT))
            rng.shuffle(dims)
            a, b, c = dims
            tpl = rng.choice(BOX_STORIES)
            prompt = tpl.format(a=a, b=b, c=c, u=rng.choice(T5_BOX_UNITS), A=_a(a))
            s = a * a + b * b + c * c
            expl = (f"{a}^2 + {b}^2 + {c}^2 = {a * a} + {b * b} + {c * c} = {s}, "
                    f"so the diagonal is {fmt(s)}.")
            it = length_item(rng, 5, prompt, s, cands_box(a, b, c), positions[i], expl, declared)
        return it

    return _gen(n, rng, make)


def _a(n: int) -> str:
    """Article before a number: 'An 8', 'A 6'."""
    return "An" if str(n).startswith("8") or n in (11, 18) else "A"


GENERATORS = {1: gen_t1, 2: gen_t2, 3: gen_t3, 4: gen_t4, 5: gen_t5}


def generate(manifest: dict, rng: random.Random) -> list:
    declared = set(manifest["misconceptions"])
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(GENERATORS[t["tier"]](rng, declared, n))
    return items
