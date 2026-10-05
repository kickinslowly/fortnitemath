"""Procedural generator for the fraction-division cartridge (fnm-cart/1, CCSS 6.NS.A.1).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every item is one division ``x ÷ y``. ``x`` and ``y`` are *operands* ``(num, den)`` exactly as the
  prompt shows them (a whole number has ``den == 1``; a fraction may be unsimplified, e.g. ``6/8``).
* ONE function, ``rule_value(label, x, y)``, gives the value under the correct rule or under a named
  misconception, or ``None`` where that wrong rule does not apply. Each tier offers a fixed list of
  labels in priority order: when two rules give the same value the first label wins.
* The reciprocal of the answer is one wrong value with three names, chosen by tier so the kid reads the
  right hint: FLIPPED_ANSWER (T1, T2), FLIP_FIRST (T3, T4), WRONG_ORDER (T5 stories).
* Multiplying by the divisor as given is DIVIDED_WHOLE when a whole is divided by a unit fraction (T1),
  MULT_WHOLE when the divisor is a whole number, NO_FLIP otherwise.
* Every choice is written in the canonical answer form (``fmt``): whole, ``a/b`` or ``w a/b``, simplest
  form, so the form of a door never gives the answer away. Values are Fractions, so no two doors are
  ever equal in value.
* ``ARITH`` only fills to 4 choices and never coincides with any rule's value.

Bounds (manifest ``bounds``): prompt wholes 2-10, prompt fractions proper with numerator 1-9 and
denominator 2-10; answers in simplest form with denominator <= 12 and whole part <= 10 (whole answers
<= 100). ``bounds_ok`` enforces it on every generated item.
"""
import random
from fractions import Fraction
from math import gcd

MAX_DISTRACTOR = 999

# Per tier: misconception labels in collision priority (first wins).
TIER_LABELS = {
    1: ["DIVIDED_WHOLE", "FLIPPED_ANSWER"],
    2: ["MULT_WHOLE", "FLIPPED_ANSWER", "ADDED_TO_DENOM"],
    3: ["KEEP_DENOM", "FLIP_FIRST", "NO_FLIP"],
    4: ["IGNORED_NUMERATOR", "FLIP_FIRST", "NO_FLIP", "FLIP_BOTH"],
    5: ["WRONG_ORDER", "DIVIDED_WHOLE", "IGNORED_NUMERATOR", "NO_FLIP", "MULT_WHOLE", "FLIP_BOTH"],
}
ALL_LABELS = ["DIVIDED_WHOLE", "FLIPPED_ANSWER", "MULT_WHOLE", "ADDED_TO_DENOM", "FLIP_FIRST",
              "NO_FLIP", "KEEP_DENOM", "FLIP_BOTH", "IGNORED_NUMERATOR", "WRONG_ORDER"]


# ---------------------------------------------------------------------------------------------
# Values and rules
# ---------------------------------------------------------------------------------------------
def val(op) -> Fraction:
    return Fraction(op[0], op[1])


def is_whole(op) -> bool:
    return op[1] == 1


def rule_value(label: str, x, y):
    """Value of x ÷ y under ``label`` ("CORRECT" or a misconception), or None where it does not apply."""
    X, Y = val(x), val(y)
    if label == "CORRECT":
        return X / Y
    if label in ("FLIPPED_ANSWER", "FLIP_FIRST", "WRONG_ORDER"):
        return Y / X  # divisor ÷ dividend = dividend flipped, then times the divisor
    if label == "DIVIDED_WHOLE":  # 4 ÷ 1/3 -> 4 ÷ 3
        return X * Y if is_whole(x) and not is_whole(y) and y[0] == 1 else None
    if label == "MULT_WHOLE":  # 1/2 ÷ 4 -> 1/2 × 4
        return X * Y if is_whole(y) and not is_whole(x) else None
    if label == "NO_FLIP":  # multiply straight across
        if is_whole(y):
            return None
        if is_whole(x) and y[0] == 1:
            return None  # that is DIVIDED_WHOLE's story
        return X * Y
    if label == "ADDED_TO_DENOM":  # a/b ÷ w -> a/(b + w)
        return Fraction(x[0], x[1] + y[0]) if is_whole(y) and not is_whole(x) else None
    if label == "KEEP_DENOM":  # a/b ÷ c/b -> (a ÷ c)/b
        if is_whole(x) or is_whole(y) or x[1] != y[1] or x[0] % y[0]:
            return None
        return Fraction(x[0] // y[0], x[1])
    if label == "FLIP_BOTH":
        return 1 / (X * Y) if not is_whole(x) and not is_whole(y) else None
    if label == "IGNORED_NUMERATOR":  # ÷ c/d -> × d
        return X * y[1] if not is_whole(y) and y[0] != 1 else None
    raise KeyError(label)


def fmt(v: Fraction) -> str:
    """Canonical answer text: 12, 3/4 or 2 1/3 (simplest form)."""
    if v.denominator == 1:
        return str(v.numerator)
    w, r = divmod(v.numerator, v.denominator)
    return f"{r}/{v.denominator}" if w == 0 else f"{w} {r}/{v.denominator}"


def show(op) -> str:
    """Operand as the prompt shows it (unsimplified fractions stay as given)."""
    return str(op[0]) if is_whole(op) else f"{op[0]}/{op[1]}"


def with_unit(v: Fraction, unit: str) -> str:
    return fmt(v) + (f" {unit}" if unit else "")


# ---------------------------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------------------------
def operand_ok(op) -> bool:
    n, d = op
    if d == 1:
        return 2 <= n <= 10
    return 2 <= d <= 10 and 1 <= n <= 9 and n < d


def answer_ok(v: Fraction) -> bool:
    if v <= 0:
        return False
    if v.denominator == 1:
        return v <= 100
    return v.denominator <= 12 and v < 11  # whole part <= 10


def bounds_ok(x, y) -> bool:
    return operand_ok(x) and operand_ok(y) and answer_ok(val(x) / val(y))


def trace(x, y) -> list:
    """The correct steps, as (what, value) pairs, for reviewers and tests."""
    X, Y = val(x), val(y)
    recip = (y[1], y[0])
    raw = (x[0] * recip[0], x[1] * recip[1])
    return [("reciprocal", recip), ("numerator product", raw[0]), ("denominator product", raw[1]),
            ("answer", X / Y)]


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def _arith_candidates(correct: Fraction, rng: random.Random) -> list:
    c = correct
    if c.denominator == 1:
        cands = [c + 1, c - 1, c + 2, c - 2, c * 2]
    else:
        p, q = c.numerator, c.denominator
        cands = [Fraction(p + 1, q), Fraction(p - 1, q), Fraction(p, q + 1), c + 1]
        if q > 2:
            cands.append(Fraction(p, q - 1))
    rng.shuffle(cands)
    return cands


def make_item(tier, x, y, labels, answer_pos, rng, prompt, expl, unit="", must_keep=(), arith=()):
    correct = rule_value("CORRECT", x, y)
    seen, wrong = {correct}, []
    for lab in labels:
        v = rule_value(lab, x, y)
        if v is None or v <= 0 or v in seen or v > MAX_DISTRACTOR:
            continue
        if len(with_unit(v, unit)) > 14:
            continue
        seen.add(v)
        wrong.append((lab, v))
    if len(wrong) > 3:
        keep = [w for w in wrong if w[0] in must_keep]
        rest = [w for w in wrong if w[0] not in must_keep]
        rng.shuffle(rest)
        keep = (keep + rest)[:3]
        wrong = [w for w in wrong if w in keep]
    used = {correct} | {rule_value(lab, x, y) for lab in ALL_LABELS}
    first = list(arith)
    rng.shuffle(first)
    for v in first + _arith_candidates(correct, rng):
        if len(wrong) == 3:
            break
        if v > 0 and v not in used and v.denominator <= 20 and len(with_unit(v, unit)) <= 14:
            used.add(v)
            wrong.append(("ARITH", v))
    if len(wrong) < 3 or not any(lab != "ARITH" for lab, _ in wrong):
        return None
    if len(prompt) > 60 or len(expl) > 160 or len(with_unit(correct, unit)) > 14:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, correct)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [with_unit(v, unit) for _, v in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


def _times_recip(x, y, unit="") -> str:
    """'x × d/c = p/q = ans' working (raw product shown only when it differs from the answer)."""
    if is_whole(y):
        recip = f"1/{y[0]}"
    else:
        recip = str(y[1]) if y[0] == 1 else f"{y[1]}/{y[0]}"
    num = x[0] * (1 if is_whole(y) else y[1])
    den = x[1] * y[0]
    ans = val(x) / val(y)
    raw = str(num) if den == 1 else f"{num}/{den}"
    s = f"{show(x)} ÷ {show(y)} = {show(x)} × {recip} = {raw}"
    if raw != fmt(ans):
        s += f" = {with_unit(ans, unit)}"
    elif unit:
        s += f" {unit}"
    return s + "."


STORY_DENS = (2, 3, 4, 6, 8)  # kitchen and ruler denominators for stories


def _frac(rng, simplest=True, dmax=10, dens=None):
    while True:
        d = rng.choice(dens) if dens else rng.randint(2, dmax)
        n = rng.randint(1, d - 1)
        if not simplest or gcd(n, d) == 1:
            return (n, d)


# --- T1: whole ÷ unit fraction -----------------------------------------------------------------
def _t1(rng, kind, pos):
    n, d = rng.randint(2, 10), rng.randint(2, 10)
    x, y = (n, 1), (1, d)
    arith = [Fraction(n * (d + 1)), Fraction(n * (d - 1)), Fraction((n + 1) * d)]
    prompt = f"{n} ÷ 1/{d}" if kind == 0 else f"How many 1/{d}s are in {n}?"
    expl = f"Each whole holds {d} pieces of size 1/{d}, so {n} ÷ 1/{d} = {n} × {d} = {n * d}."
    return x, y, prompt, expl, "", arith


# --- T2: fraction ÷ whole ----------------------------------------------------------------------
def _t2(rng, kind, pos):
    w = rng.randint(2, 10)
    if kind in (0, 1):
        b = rng.randint(2, 10)
        x = (1, b)
    else:
        x = _frac(rng)
        if x[0] == 1:
            return None
    y = (w, 1)
    if kind == 1:
        prompt = f"Split 1/{x[1]} into {w} equal parts. How big is each?"
    else:
        prompt = f"{show(x)} ÷ {w}"
    return x, y, prompt, _times_recip(x, y), ""


# --- T3: same denominators ---------------------------------------------------------------------
def _t3(rng, kind, pos):
    b = rng.randint(3, 10)
    a, c = rng.randint(1, b - 1), rng.randint(1, b - 1)
    if a == c:
        return None
    whole = a % c == 0
    if (kind < 2) != whole:  # 2/3 whole answers, 1/3 fraction answers
        return None
    x, y = (a, b), (c, b)
    ans = Fraction(a, c)
    tail = fmt(ans) if whole or f"{a}/{c}" == fmt(ans) else f"{a}/{c} = {fmt(ans)}"
    expl = f"Same denominators, so count the 1/{b} pieces: {a} ÷ {c} = {tail}."
    return x, y, f"{a}/{b} ÷ {c}/{b}", expl, ""


# --- T4: any two fractions ---------------------------------------------------------------------
def _t4(rng, kind, pos):
    if kind == 0:  # whole ÷ non-unit fraction
        x = (rng.randint(2, 10), 1)
        y = _frac(rng)
        if y[0] == 1:
            return None
    else:
        x, y = _frac(rng), _frac(rng)
        if x[1] == y[1]:
            return None
    if val(x) / val(y) == 1:
        return None
    return x, y, f"{show(x)} ÷ {show(y)}", "Multiply by the reciprocal: " + _times_recip(x, y), ""


# --- T5: stories --------------------------------------------------------------------------------
# (template, unit of the answer). {x} is the dividend, {y} the divisor.
STORIES = {
    "QW": [  # how many groups: whole ÷ fraction, whole-number answer
        ("{x} cups of rice, {y} cup per bowl. How many bowls?", ""),
        ("{a} {x} m rope is cut into {y} m pieces. How many pieces?", ""),
        ("{x} lb of trail mix split into {y} lb bags. How many bags?", ""),
        ("{x} hours of practice, {y} hour per drill. How many drills?", ""),
    ],
    "QF": [  # how many groups: fraction ÷ fraction
        ("{x} cup of flour, {y} cup per batch. How many batches?", ""),
        ("How many {y} mi laps make a {x} mi run?", ""),
    ],
    "PW": [  # equal shares: fraction ÷ whole
        ("{x} lb of fudge shared equally by {y} kids. Lb each?", "lb"),
        ("{y} friends split {x} of a pizza equally. How much each?", ""),
        ("{x} gal of paint covers {y} walls equally. Gal per wall?", "gal"),
    ],
    "PF": [  # how much in one whole / missing side: ÷ a fraction
        ("{y} of a bag of dog food weighs {x} lb. Whole bag?", "lb"),
        ("Rectangle: area {x} sq ft, width {y} ft. Length?", "ft"),
    ],
}
STORY_KINDS = ["QW", "QF", "PW", "PF"]
LEAD = {"QW": "Groups of {y} in {x}: ", "QF": "Groups of {y} in {x}: ",
        "PW": "Share {x} into {y} parts: ", "PF": ""}


def _t5(rng, kind, pos):
    sk = STORY_KINDS[kind]
    tmpl, unit = rng.choice(STORIES[sk])
    sf = lambda: _frac(rng, dens=STORY_DENS)  # noqa: E731
    if sk == "QW":
        x, y = (rng.randint(2, 10), 1), sf()
        if (val(x) / val(y)).denominator != 1:
            return None
    elif sk == "QF":  # whole or half batches/laps only
        x, y = sf(), sf()
        if val(x) <= val(y) or (val(x) / val(y)).denominator > 2:
            return None
    elif sk == "PW":
        x, y = sf(), (rng.randint(2, 6), 1)
    else:
        bag = "bag" in tmpl
        x = (rng.randint(2, 10), 1) if bag or rng.random() < 0.5 else sf()
        y = sf()
        if bag and y[0] == 1:
            return None  # "1/4 of a bag weighs 2 lb" is just 2 × 4: keep the flip in play
        if val(x) / val(y) == 1:
            return None
    prompt = tmpl.format(x=show(x), y=show(y), a="An" if show(x).startswith("8") else "A")
    lead = LEAD[sk].format(x=show(x), y=show(y))
    if sk == "PF":
        lead = ("Length = area ÷ width: " if "Rectangle" in tmpl
                else f"{show(y)} of the bag is {show(x)} lb, so whole = ")
    return x, y, prompt, lead + _times_recip(x, y, unit), unit


BUILDERS = {1: (_t1, 2), 2: (_t2, None), 3: (_t3, 3), 4: (_t4, 3), 5: (_t5, 4)}


def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000):
    positions = _balanced(count, 4, rng)
    build, k = BUILDERS[tier]
    if tier == 2:  # 10 unit-fraction expressions, 10 unit-fraction "split" stories, 20 non-unit
        kinds = [0] * (count // 4) + [1] * (count // 4) + [2] * (count - 2 * (count // 4))
        rng.shuffle(kinds)
    else:
        kinds = _balanced(count, k, rng)
    must_keep = ("IGNORED_NUMERATOR",) if tier == 4 else ("WRONG_ORDER",) if tier == 5 else ()
    items, prompts = [], set()
    attempts = 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        got = build(rng, kinds[len(items)], positions[len(items)])
        if got is None:
            continue
        x, y, prompt, expl, unit = got[:5]
        arith = got[5] if len(got) > 5 else ()
        if prompt in prompts or not bounds_ok(x, y):
            continue
        item = make_item(tier, x, y, TIER_LABELS[tier], positions[len(items)], rng, prompt, expl,
                         unit, must_keep, arith)
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
