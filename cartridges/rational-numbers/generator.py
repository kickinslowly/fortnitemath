"""Procedural generator for the rational-numbers cartridge (fnm-cart/1), grade 6 NS.C.5-8.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4
shape without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other
cartridges.

Design
------
* Every item kind is a pure builder ``make_<kind>(params) -> (prompt, answer, wrong, explanation)``
  where ``wrong`` is a list of (misconception key, choice text): one wrong value per modelled
  misconception, computed by applying that wrong rule to the same numbers. The ``pick_<kind>(rng)``
  functions only choose the numbers, so the tests can call the builders on hand-worked prompts.
* ``ARITH`` is used only for the ±1 slip on an absolute-value sum or difference, and only when a
  misconception rule gives no distinct value there.
* Answer positions are dealt per tier and per choice count so each position holds the answer
  equally often (§5 rule 8). Choice text never depends on position.

Bounds (manifest ``bounds``): numbers shown are integers or halves of size <= 20; coordinates
1..10 in size; absolute-value operands <= 12; moves <= 10; every correct answer size <= 20. The
tests re-derive every step from the prompt text and assert these bounds on baked.json.
"""
from __future__ import annotations

import random
from fractions import Fraction as F

MINUS = "−"  # U+2212
MAX_CHOICE = 14
MAX_PROMPT = 60
MAX_EXPL = 160
MAX_ANSWER = 20
HALVES = [F(k, 2) for k in range(1, 20, 2)]  # 0.5 .. 9.5


# ---------------------------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------------------------
def dec(v) -> str:
    """Integer or half as display text: −7, 0, 2.5, −0.5."""
    v = F(v)
    if v.denominator == 1:
        s = str(abs(v.numerator))
    elif v.denominator == 2:
        s = f"{abs(v.numerator) // 2}.5"
    else:
        raise ValueError(f"not an integer or half: {v}")
    return f"{MINUS}{s}" if v < 0 else s


def frac(v) -> str:
    """Fraction as a/b (or an integer): −1/7, 2/5, 2."""
    v = F(v)
    if v.denominator == 1:
        return dec(v)
    s = f"{abs(v.numerator)}/{v.denominator}"
    return f"{MINUS}{s}" if v < 0 else s


def pt(x, y) -> str:
    return f"({dec(x)}, {dec(y)})"


def money(v) -> str:
    v = int(v)
    return f"{MINUS}${-v}" if v < 0 else f"${v}"


ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}


def quadrant(x, y) -> int:
    if x > 0 and y > 0:
        return 1
    if x < 0 < y:
        return 2
    if x < 0 and y < 0:
        return 3
    if x > 0 > y:
        return 4
    raise ValueError("on an axis")


def _seq(vals):
    return ", ".join(dec(v) for v in vals)


# ---------------------------------------------------------------------------------------------
# Tier 1: opposites, signs in context, moving on a number line (NS.C.5, C.6a, C.6c)
# ---------------------------------------------------------------------------------------------
def make_opposite(n, long_form=False):
    n = F(n)
    prompt = ("What is the opposite of {}?" if long_form else "Opposite of {}?").format(dec(n))
    ans = dec(-n)
    wrong = [("SAME_NUMBER", dec(n)), ("RECIPROCAL", frac(1 / n)), ("RECIPROCAL", frac(-1 / n))]
    expl = f"The opposite is the same distance from 0 on the other side of 0: {ans}."
    return prompt, ans, wrong, expl


def pick_opposite(rng):
    if rng.random() < 0.3:
        n = rng.choice(HALVES[:6])  # 0.5 .. 5.5: reciprocals 2, 2/3, 2/5 .. 2/11
    else:
        n = F(rng.randint(2, 12))
    if rng.random() < 0.5:
        n = -n
    return make_opposite(n, rng.random() < 0.5)


# theme: (negative phrase, positive phrase, negative word, positive word)
THEMES = [
    ("owe ${}", "earn ${}", "Owe", "Earn"),
    ("lose {} yards", "gain {} yards", "Lose", "Gain"),
    ("{} degrees below 0", "{} degrees above 0", "Below", "Above"),
    ("withdraw ${}", "deposit ${}", "Withdraw", "Deposit"),
    ("go down {} floors", "go up {} floors", "Down", "Up"),
    ("lose {} points", "win {} points", "Lose", "Win"),
    ("{} m below sea level", "{} m above sea level", "Below", "Above"),
]


def make_context(theme, a, b, first_neg):
    """Two quantities in words (sizes a then b, one negative, one positive) -> the integer pair."""
    neg_p, pos_p, neg_w, pos_w = THEMES[theme]
    if first_neg:
        p1, p2, x, y, w1, w2 = neg_p.format(a), pos_p.format(b), -a, b, neg_w, pos_w
    else:
        p1, p2, x, y, w1, w2 = pos_p.format(a), neg_p.format(b), a, -b, pos_w, neg_w
    prompt = f"{p1[0].upper()}{p1[1:]}, then {p2}. As integers?"

    def pair(u, v):
        return f"{dec(u)} and {dec(v)}"

    def word(w, v):
        return f"{w} means {'negative' if v < 0 else 'positive'}: {dec(v)}"

    ans = pair(x, y)
    wrong = [("WRONG_SIGN_CONTEXT", pair(-x, -y)), ("WRONG_SIGN_CONTEXT", pair(a, b)),
             ("WRONG_SIGN_CONTEXT", pair(-a, -b))]
    expl = f"{word(w1, x)}. {word(w2, y)}. So {ans}."
    return prompt, ans, wrong, expl


def pick_context(rng):
    a, b = rng.sample(range(2, 21), 2)  # 2+: "lose 1 yards" reads wrong
    return make_context(rng.randrange(len(THEMES)), a, b, rng.random() < 0.5)


def make_move(start, step, left):
    end = start - step if left else start + step
    prompt = f"Start at {dec(start)} and move {step} {'left' if left else 'right'}. Where are you?"
    ans = dec(end)
    wrong_dir = start + step if left else start - step
    from_zero = -step if left else step
    off = end + 1 if left else end - 1  # counted the starting tick as the first of `step`
    wrong = [("WRONG_DIRECTION", dec(wrong_dir)), ("FROM_ZERO", dec(from_zero)),
             ("OFF_BY_ONE", dec(off))]
    if left:
        expl = f"Left means smaller: {dec(start)} {MINUS} {step} = {ans}."
    else:
        expl = f"Right means bigger: {dec(start)} + {step} = {ans}."
    return prompt, ans, wrong, expl


def pick_move(rng):
    start = rng.choice([v for v in range(-10, 11) if v != 0])
    step = rng.randint(2, 10)
    left = rng.random() < 0.5
    end = start - step if left else start + step
    if end == 0 or ((start < 0) == (end < 0) and rng.random() < 0.6):
        return None  # prefer moves that cross 0
    return make_move(start, step, left)


# ---------------------------------------------------------------------------------------------
# Tier 2: absolute value (NS.C.7c, C.7d)
# ---------------------------------------------------------------------------------------------
def make_abs(u, op, v, arith=(1, -1)):
    """|u| op |v| for op in '+', '−'. ``arith`` orders the ±1 fills."""
    a, b = abs(u), abs(v)
    sym = "+" if op == "+" else MINUS
    core = f"|{dec(u)}| {sym} |{dec(v)}|"
    if op == "+":
        correct, keeps, opp = a + b, u + v, -u - v
    else:
        correct, keeps, opp = a - b, u - v, -u + v
    prompt = f"{core} = ?"
    wrong, seen = [], {correct}
    for lab, w in (("KEEPS_SIGN", keeps), ("OPPOSITE_FOR_ABS", opp)):
        if w not in seen:
            seen.add(w)
            wrong.append((lab, dec(w)))
    for d in arith:
        if len(wrong) < 3 and correct + d not in seen:
            seen.add(correct + d)
            wrong.append(("ARITH", dec(correct + d)))
    expl = f"|{dec(u)}| = {a} and |{dec(v)}| = {b}, so {a} {sym} {b} = {dec(correct)}."
    return prompt, dec(correct), wrong, expl


def pick_abs(rng, op):
    a, b = rng.sample(range(2, 13), 2)
    if op != "+" and a < b:
        a, b = b, a  # bigger size first: grade 6 never subtracts into negatives (that is 7.NS)
    if op == "+" and a + b > MAX_ANSWER:
        return None
    # |−a| − |−b|: the opposite rule gives the right answer, so only + uses two negatives.
    signs = ((-1, 1), (1, -1), (-1, -1)) if op == "+" else ((-1, 1), (1, -1))
    sa, sb = rng.choice(signs)
    return make_abs(sa * a, op, sb * b, tuple(rng.sample([1, -1], 2)))


def make_debt(balances):
    """Three balances (two negative, one positive) -> the biggest debt."""
    negs = sorted(v for v in balances if v < 0)
    pos = [v for v in balances if v > 0]
    big, small = negs[0], negs[1]
    shown = [money(v) for v in balances]
    prompt = f"Biggest debt: {shown[0]}, {shown[1]} or {shown[2]}?"
    ans = money(big)
    wrong = [("NEG_SIZE", money(small)), ("POSITIVE_DEBT", money(pos[0]))]
    expl = (f"A debt is a negative balance; its size is the absolute value. "
            f"|{MINUS}{-big}| = {-big} > |{MINUS}{-small}| = {-small}, so {ans} is the biggest debt.")
    return prompt, ans, wrong, expl


def pick_debt(rng):
    a, b = sorted(rng.sample(range(2, 20), 2), reverse=True)
    c = rng.randint(a + 1, 20)  # the positive balance is the biggest-looking number
    vals = [-a, -b, c]
    rng.shuffle(vals)
    return make_debt(vals)


# ---------------------------------------------------------------------------------------------
# Tier 3: compare and order (NS.C.7a, C.7b)
# ---------------------------------------------------------------------------------------------
def _pick_num(rng, lo, hi):
    """An integer or (sometimes) a half with lo <= value <= hi (lo, hi > 0)."""
    if rng.random() < 0.3:
        opts = [h for h in HALVES if lo <= h <= hi]
        if opts:
            return rng.choice(opts)
    ints = [k for k in range(1, 13) if lo <= k <= hi]
    return F(rng.choice(ints)) if ints else None


LESS_FORMS = ("Which number is less than {}?", "Which is to the left of {}?")


def make_less(r, s, t, p, form=0):
    """Which is less than −r? correct −s (s > r); NEG_SIZE −t (t < r); ZERO_LEAST 0; ABS_ORDER p
    (0 < p < r)."""
    prompt = LESS_FORMS[form].format(dec(-r))
    ans = dec(-s)
    wrong = [("NEG_SIZE", dec(-t)), ("ZERO_LEAST", "0"), ("ABS_ORDER", dec(p))]
    expl = (f"Less means farther left on the number line. {ans} is left of {dec(-r)}; "
            f"{dec(-t)}, 0 and {dec(p)} are to its right.")
    return prompt, ans, wrong, expl


def pick_less(rng):
    r = _pick_num(rng, F(3, 2), 10)
    s = _pick_num(rng, r + F(1, 2), 12)
    t = _pick_num(rng, F(1, 2), r - F(1, 2))
    p = _pick_num(rng, F(1, 2), r - F(1, 2))
    if None in (s, t, p):
        return None
    return make_less(r, s, t, p, rng.randrange(2))


def make_order(shown):
    """Three numbers −a, −b, c with a > c > b > 0, in display order."""
    correct = sorted(shown)
    a, b, c = -correct[0], -correct[1], correct[2]
    assert a > c > b > 0
    prompt = f"Order from least to greatest: {_seq(shown)}"
    ans = _seq(correct)
    wrong = [("NEG_SIZE", _seq([-b, -a, c])), ("ABS_ORDER", _seq(sorted(shown, key=abs))),
             ("GREATEST_FIRST", _seq(sorted(shown, reverse=True)))]
    expl = f"Left to right on a number line: {ans}. Negatives come first, and {dec(-a)} < {dec(-b)}."
    return prompt, ans, wrong, expl


def pick_order(rng):
    a = _pick_num(rng, 3, 12)
    c = _pick_num(rng, 2, a - 1)
    b = c and _pick_num(rng, 1, c - 1)
    if not b or not a > c > b > 0:
        return None
    shown = [-a, -b, c]
    rng.shuffle(shown)
    if shown == sorted(shown):
        return None
    return make_order(shown)


LEAST_FORMS = [
    ("Coldest: {} degrees?", "Coldest is the least temperature, farthest left"),
    ("Lowest score: {}?", "Lowest is the least number, farthest left"),
    ("Least: {}?", "Least is farthest left on the number line"),
    ("Lowest point: {} m?", "Lowest is farthest below sea level (0)"),
]


def make_least(vals, form=2):
    """Three numbers −a, −b, c with a > b > c > 0, in display order."""
    s = sorted(vals)
    a, b, c = -s[0], -s[1], s[2]
    assert a > b > c > 0
    text, why = LEAST_FORMS[form]
    prompt = text.format(f"{dec(vals[0])}, {dec(vals[1])} or {dec(vals[2])}")
    ans = dec(-a)
    wrong = [("NEG_SIZE", dec(-b)), ("ABS_ORDER", dec(c))]
    expl = f"{why}: {dec(-a)} < {dec(-b)} < {dec(c)}."
    return prompt, ans, wrong, expl


def pick_least(rng):
    a = _pick_num(rng, 3, 12)
    b = _pick_num(rng, 2, a - 1)
    c = b and _pick_num(rng, 1, b - 1)
    if not c or not a > b > c > 0:
        return None
    vals = [-a, -b, c]
    rng.shuffle(vals)
    form = rng.randrange(len(LEAST_FORMS))
    if form == 0 and c == 1:
        return None  # "or 1 degrees"
    return make_least(vals, form)


# ---------------------------------------------------------------------------------------------
# Tier 4: quadrants and reflections (NS.C.6b, C.6c)
# ---------------------------------------------------------------------------------------------
def _signed_coords(rng):
    x, y = rng.sample(range(1, 11), 2)  # different sizes: (x, y) and (y, x) never coincide
    return rng.choice((-1, 1)) * x, rng.choice((-1, 1)) * y


def make_quadrant(x, y):
    q = quadrant(x, y)
    prompt = f"{pt(x, y)} is in which quadrant?"
    wrong = [("CLOCKWISE" if {k, q} == {2, 4} else "SIGN_MISREAD", ROMAN[k])
             for k in (1, 2, 3, 4) if k != q]
    xs = "negative (left)" if x < 0 else "positive (right)"
    ys = "negative (down)" if y < 0 else "positive (up)"
    expl = f"x = {dec(x)} is {xs}, y = {dec(y)} is {ys}: quadrant {ROMAN[q]}."
    return prompt, ROMAN[q], wrong, expl


def pick_quadrant(rng):
    x, y = rng.sample(range(1, 11), 2)
    sx, sy = rng.choice(((-1, 1), (-1, 1), (1, -1), (1, -1), (-1, -1)))  # II, IV most often
    return make_quadrant(sx * x, sy * y)


def _images(x, y, axis):
    """(image, image over the other axis)."""
    return ((x, -y), (-x, y)) if axis == "x" else ((-x, y), (x, -y))


def make_reflect(x, y, axis):
    img, other = _images(x, y, axis)
    rule = "x stays and y changes sign" if axis == "x" else "y stays and x changes sign"
    prompt = f"Reflect {pt(x, y)} over the {axis}-axis. New point?"
    ans = pt(*img)
    wrong = [("WRONG_AXIS", pt(*other)), ("BOTH_FLIPPED", pt(-x, -y)),
             ("SWAPPED_XY", pt(img[1], img[0]))]
    expl = f"Over the {axis}-axis, {rule}: {pt(x, y)} becomes {ans}."
    return prompt, ans, wrong, expl


def pick_reflect(rng):
    x, y = _signed_coords(rng)
    return make_reflect(x, y, rng.choice("xy"))


def make_reflect_quadrant(x, y, axis):
    img, other = _images(x, y, axis)
    q = quadrant(*img)
    prompt = f"Reflect {pt(x, y)} over the {axis}-axis. Which quadrant?"
    wrong = [("WRONG_AXIS", ROMAN[quadrant(*other)]), ("BOTH_FLIPPED", ROMAN[quadrant(-x, -y)]),
             ("NO_MOVE", ROMAN[quadrant(x, y)])]
    ch = "y" if axis == "x" else "x"
    expl = (f"Over the {axis}-axis, {ch} changes sign: {pt(x, y)} becomes {pt(*img)}, "
            f"in quadrant {ROMAN[q]}.")
    return prompt, ROMAN[q], wrong, expl


def pick_reflect_quadrant(rng):
    x, y = _signed_coords(rng)
    return make_reflect_quadrant(x, y, rng.choice("xy"))


# ---------------------------------------------------------------------------------------------
# Tier 5: distance (NS.C.8)
# ---------------------------------------------------------------------------------------------
def _dist_wrong(u, v):
    """Labelled wrong distances for two values u, v on one line."""
    d = abs(u - v)
    if (u < 0) != (v < 0):
        sizes = ("SUBTRACTED_SIZES", abs(abs(u) - abs(v)))
    else:
        sizes = ("ADDED_SIZES", abs(u) + abs(v))
    return [(lab, dec(w)) for lab, w in (sizes, ("NEG_DISTANCE", -d), ("OFF_BY_ONE", d + 1))]


def make_distance(p, q):
    if p[0] == q[0]:
        along, same, u, v = "y", "x", p[1], q[1]
    else:
        along, same, u, v = "x", "y", p[0], q[0]
    assert p[0] == q[0] or p[1] == q[1]
    d = abs(u - v)
    prompt = f"Distance from {pt(*p)} to {pt(*q)}?"
    if (u < 0) != (v < 0):
        how = f"opposite sides of 0, so add: {abs(u)} + {abs(v)} = {d}"
    else:
        how = f"same side of 0, so subtract: {max(abs(u), abs(v))} {MINUS} {min(abs(u), abs(v))} = {d}"
    expl = f"Same {same}, so use the {along}-values {dec(u)} and {dec(v)}: {how}."
    return prompt, dec(d), _dist_wrong(u, v), expl


def pick_distance(rng, cross):
    nz = [k for k in range(-10, 11) if k != 0]
    u, v = rng.sample(nz, 2)
    if ((u < 0) != (v < 0)) != cross or abs(u) == abs(v) or (u > 0 and v > 0):
        return None
    k = rng.choice(nz)
    if rng.random() < 0.5:
        return make_distance((u, k), (v, k))
    return make_distance((k, u), (k, v))


STORIES = [
    "A bird is at {} m and a fish at {} m. How far apart?",
    "A kite is at {} m and a diver at {} m. How far apart?",
    "Floors {} and {} (below ground is −). Floors apart?",
    "It was {} degrees, then {} degrees. Degrees apart?",
]


def make_story(form, u, v):
    """Two values on opposite sides of 0 in a story -> how far apart."""
    assert (u < 0) != (v < 0)
    prompt = STORIES[form].format(dec(u), dec(v))
    d = abs(u - v)
    expl = f"0 is between them: {abs(u)} on one side, {abs(v)} on the other. {abs(u)} + {abs(v)} = {d}."
    return prompt, dec(d), _dist_wrong(u, v), expl


def pick_story(rng):
    a, b = rng.sample(range(1, 11), 2)
    form = rng.randrange(len(STORIES))
    if form < 2:
        u, v = a, -b  # something above sea level, something below
    else:
        u, v = (a, -b) if rng.random() < 0.5 else (-a, b)
    return make_story(form, u, v)


def make_reflect_distance(x, y, axis):
    moving, staying = (y, x) if axis == "x" else (x, y)
    m = abs(moving)
    d = 2 * m
    prompt = f"How far is {pt(x, y)} from its {axis}-axis reflection?"
    wrong = [("TO_AXIS", dec(m)), ("WRONG_COORD", dec(2 * abs(staying))), ("NEG_DISTANCE", dec(-d))]
    expl = (f"{pt(x, y)} is {m} from the {axis}-axis and its image is {m} on the other side: "
            f"{m} + {m} = {d}.")
    return prompt, dec(d), wrong, expl


def pick_reflect_distance(rng):
    x, y = _signed_coords(rng)
    axis = rng.choice("xy")
    moving, staying = (y, x) if axis == "x" else (x, y)
    if 2 * abs(staying) == abs(moving):
        return None  # WRONG_COORD would equal TO_AXIS
    return make_reflect_distance(x, y, axis)


# ---------------------------------------------------------------------------------------------
# Tier plans and assembly
# ---------------------------------------------------------------------------------------------
PLANS = {
    1: [(pick_opposite, 14), (pick_context, 13), (pick_move, 13)],
    2: [(lambda r: pick_abs(r, "+"), 14), (lambda r: pick_abs(r, "−"), 12), (pick_debt, 14)],
    3: [(pick_less, 14), (pick_order, 13), (pick_least, 13)],
    4: [(pick_quadrant, 14), (pick_reflect, 14), (pick_reflect_quadrant, 12)],
    5: [(lambda r: pick_distance(r, True), 16), (lambda r: pick_distance(r, False), 8),
        (pick_story, 8), (pick_reflect_distance, 8)],
}


def _ok(prompt, ans, wrong, expl):
    texts = [ans] + [w for _, w in wrong]
    return (len(prompt) <= MAX_PROMPT and len(expl) <= MAX_EXPL
            and all(len(t) <= MAX_CHOICE for t in texts) and len(set(texts)) == len(texts))


def gen_tier(tier: int, count: int, rng: random.Random) -> list:
    plan = PLANS[tier]
    assert sum(n for _, n in plan) == count, (tier, count)
    raw, prompts = [], set()
    for pick, n in plan:
        got, attempts = 0, 0
        while got < n:
            attempts += 1
            if attempts > 100000:
                raise RuntimeError(f"tier {tier}: {pick} could not make {n} items")
            r = pick(rng)
            if r is None:
                continue
            prompt, ans, wrong, expl = r
            if prompt in prompts or not _ok(prompt, ans, wrong, expl):
                continue
            prompts.add(prompt)
            raw.append((prompt, ans, list(wrong), expl))
            got += 1
    rng.shuffle(raw)
    # Deal answer positions per choice count: each position equally often.
    by_n: dict = {}
    for i, (_, _, wrong, _) in enumerate(raw):
        by_n.setdefault(len(wrong) + 1, []).append(i)
    pos = {}
    for n, idxs in sorted(by_n.items()):
        slots = [k % n for k in range(len(idxs))]
        rng.shuffle(slots)
        pos.update(zip(idxs, slots))
    items = []
    for i, (prompt, ans, wrong, expl) in enumerate(raw):
        rng.shuffle(wrong)
        p = pos[i]
        pairs = wrong[:p] + [(None, ans)] + wrong[p:]
        items.append({
            "tier": tier,
            "prompt": prompt,
            "choices": [t for _, t in pairs],
            "answer": p,
            "misconceptions": [lab for lab, _ in pairs],
            "explanation": expl,
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
