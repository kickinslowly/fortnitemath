"""Procedural generator for the ratios-rates cartridge (fnm-cart/1, grade 6, RP.A.1-3).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Each tier has a few prompt *templates*. A builder picks numbers inside the manifest's ``bounds``
  and renders the prompt text; ``analyze(prompt)`` then re-reads that text with regexes and returns
  the correct choice, every modelled misconception's wrong choice and the explanation. The text a
  student sees is the only thing ever solved.
* A choice is ``(display, value)``. Ratios have value ``Fraction(p, q)``, so ``2:4`` and ``1:2`` count
  as the same value; numbers and prices have their Fraction value. No two choices of an item share
  a value (the player never faces two right doors).
* Wrong choices: misconception values first, in the order listed per template (the first label to
  produce a value keeps it); ``ARITH`` only fills up to 4 choices and never equals ANY
  misconception value of that prompt.
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

# ---------------------------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------------------------
MINUS = "−"


def frac(v: Fraction) -> str:
    """Whole number, a/b, or mixed w a/b (simplest form)."""
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    w, r = divmod(v.numerator, v.denominator)
    return f"{w} {r}/{v.denominator}" if w else f"{r}/{v.denominator}"


def dec(v: Fraction) -> str:
    """Decimal with at most 2 places (only for values with denominator dividing 100)."""
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    assert 100 % v.denominator == 0, v
    s = f"{float(v):.2f}".rstrip("0").rstrip(".")
    return s


def money(v: Fraction) -> str:
    return "$" + frac(v)


def ratio(p: int, q: int):
    return (f"{p}:{q}", Fraction(p, q))


def number(v, show=frac):
    v = Fraction(v)
    return (show(v), v)


def cash(v):
    v = Fraction(v)
    return (money(v), v)


# ---------------------------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------------------------
GROUPS = [  # (group X, group Y, the whole)
    ("cats", "dogs", "pets"),
    ("boys", "girls", "kids"),
    ("apples", "pears", "fruits"),
    ("wins", "losses", "games"),
    ("hawks", "owls", "birds"),
    ("cars", "vans", "vehicles"),
]
WHOLE_OF = {x: n for x, y, n in GROUPS} | {y: n for x, y, n in GROUPS}

MIXES = [  # (mix name, X, Y)
    ("Paint", "red", "blue"),
    ("Lemonade", "lemons", "cups"),
    ("Trail mix", "nuts", "raisins"),
    ("Slime", "glue", "water"),
]

ITEMS_FOR_SALE = [("pens", "pen"), ("tickets", "ticket"), ("cans", "can"), ("books", "book"),
                  ("tacos", "taco")]
SINGULAR = dict(ITEMS_FOR_SALE)

RATES = [  # (amount, time unit plural, amount cap, time singular)
    ("miles", "hours", "Miles", "hour"),
    ("pages", "days", "Pages", "day"),
    ("laps", "minutes", "Laps", "minute"),
    ("points", "games", "Points", "game"),
]

UNITS = [  # (big singular, big plural, small, factor)
    ("yd", "yd", "ft", 3),
    ("gal", "gal", "qt", 4),
    ("qt", "qt", "pt", 2),
    ("pt", "pt", "cups", 2),
    ("week", "weeks", "days", 7),
]
UNIT_FACTOR = {u[2]: u[3] for u in UNITS}

PCT_CONTEXTS = [("kids", "ride a bus"), ("games", "were wins"), ("seats", "are empty"),
                ("apples", "are red"), ("songs", "are pop")]

TENS = (20, 30, 40, 50, 60, 70, 80, 90)

# ---------------------------------------------------------------------------------------------
# Regexes (one per template) -- shared by analyze() only
# ---------------------------------------------------------------------------------------------
RE = {
    "t1_and": re.compile(r"^(\d+) (\w+) and (\d+) (\w+)\. Ratio of (\w+) to (\w+)\?$"),
    "t1_every": re.compile(r"^For every (\d+) (\w+) there are (\d+) (\w+)\. Ratio of (\w+) to (\w+)\?$"),
    "t1_all": re.compile(r"^(\d+) (\w+) and (\d+) (\w+)\. Ratio of (\w+) to all (\w+)\?$"),
    "t1_rest": re.compile(r"^(\d+) (\w+): (\d+) are (\w+), the rest (\w+)\. Ratio of (\w+) to (\w+)\?$"),
    "t2_left": re.compile(r"^(\d+):(\d+) = \?:(\d+)$"),
    "t2_right": re.compile(r"^(\d+):(\d+) = (\d+):\?$"),
    "t2_mix": re.compile(r"^[\w ]+: (\d+) (\w+) to (\d+) (\w+)\. (\w+) for (\d+) (\w+)\?$"),
    "t3_price": re.compile(r"^(\d+) (\w+) cost \$(\d+)\. Cost per (\w+)\?$"),
    "t3_speed": re.compile(r"^(\d+) (\w+) in (\d+) (\w+)\. (\w+) per (\w+)\?$"),
    "t3_convert": re.compile(r"^1 (\w+) = (\d+) (\w+)\. (\d+) (\w+) = \? (\w+)$"),
    "t4_pct": re.compile(r"^(?:What is )?(\d+)% of (\d+)(?:\?| \w+ [\w ]+\. How many\?)$"),
    "t5_share": re.compile(r"^(\w+):(\w+) is (\d+):(\d+)\. (\d+) (\w+) in all\. How many (\w+)\?$"),
    "t5_total": re.compile(r"^(\w+):(\w+) is (\d+):(\d+)\. There are (\d+) (\w+)\. How many (\w+)\?$"),
    "t5_whole": re.compile(r"^(\d+) is (\d+)% of what number\?$"),
    "t5_price": re.compile(r"^(\d+) (\w+) cost \$(\d+)\. Cost of (\d+) (\w+)\?$"),
}


class NotMine(Exception):
    pass


def analyze(prompt: str):
    """THE solver: (kind, correct choice, [(label, choice)...], explanation) from the display text.

    The misconception list is ordered by priority; it may hold values equal to the answer or to
    each other -- ``make_item`` dedups by value."""
    for kind, rx in RE.items():
        m = rx.match(prompt)
        if m:
            return (kind,) + _SOLVERS[kind](m)
    raise NotMine(prompt)


# --- T1 ----------------------------------------------------------------------------------------
def _t1_pp(m):
    a, x, b, y, P, Q = int(m[1]), m[2], int(m[3]), m[4], m[5], m[6]
    cnt = {x: a, y: b}
    p, q = cnt[P], cnt[Q]
    s = a + b
    wrong = [("REVERSED", ratio(q, p)), ("PART_TO_WHOLE", ratio(p, s)),
             ("PART_TO_WHOLE", ratio(q, s))]
    return ratio(p, q), wrong, f"{P.capitalize()} first, then {Q}: {p} to {q} is {p}:{q}."


def _t1_all(m):
    a, x, b, y, P, N = int(m[1]), m[2], int(m[3]), m[4], m[5], m[6]
    cnt = {x: a, y: b}
    p = cnt[P]
    q = b if P == x else a
    s = a + b
    wrong = [("PART_TO_PART", ratio(p, q)), ("REVERSED", ratio(s, p)),
             ("OTHER_PART", ratio(q, s))]
    return ratio(p, s), wrong, f"All {N}: {a} + {b} = {s}. {P.capitalize()} to all is {p}:{s}."


def _t1_rest(m):
    T, N, a, x, y, P, Q = int(m[1]), m[2], int(m[3]), m[4], m[5], m[6], m[7]
    cnt = {x: a, y: T - a}
    p, q = cnt[P], cnt[Q]
    as_total = {x: a, y: T}  # the rest read as the whole
    wrong = [("WHOLE_FOR_PART", ratio(as_total[P], as_total[Q])), ("REVERSED", ratio(q, p)),
             ("PART_TO_WHOLE", ratio(p, T)), ("PART_TO_WHOLE", ratio(q, T))]
    return (ratio(p, q), wrong,
            f"{y.capitalize()}: {T} {MINUS} {a} = {T - a}. {P.capitalize()} to {Q} is {p}:{q}.")


# --- T2 ----------------------------------------------------------------------------------------
def _scale(known_match: int, given: int):
    if given % known_match:
        raise NotMine("inexact scale")
    return given // known_match


def _t2_core(match, other, given):
    """match:other = given:?  (given scales match)."""
    k = _scale(match, given)
    ans = other * k
    wrong = [("ADDITIVE", number(other + (given - match))), ("WRONG_TERM", number(given * k)),
             ("FACTOR_ONLY", number(k))]
    expl = f"{match} × {k} = {given}, so {other} × {k} = {ans}."
    return number(ans), wrong, expl


def _t2_left(m):
    a, b, B = int(m[1]), int(m[2]), int(m[3])
    c, w, e = _t2_core(b, a, B)
    return c, w, e + f" {a}:{b} = {c[0]}:{B}."


def _t2_right(m):
    a, b, A = int(m[1]), int(m[2]), int(m[3])
    c, w, e = _t2_core(a, b, A)
    return c, w, e + f" {a}:{b} = {A}:{c[0]}."


def _t2_mix(m):
    a, x, b, y, asked, n, given_unit = int(m[1]), m[2], int(m[3]), m[4], m[5].lower(), int(m[6]), m[7]
    cnt = {x: a, y: b}
    return _t2_core(cnt[given_unit], cnt[asked], n)


# --- T3 ----------------------------------------------------------------------------------------
def _t3_price(m):
    n, items, t = int(m[1]), m[2], int(m[3])
    r = Fraction(t, n)
    wrong = [("MULTIPLIED_RATE", cash(t * n)), ("INVERTED", cash(Fraction(n, t)))]
    return cash(r), wrong, f"${t} ÷ {n} = ${frac(r)} per {SINGULAR[items]}."


def _t3_speed(m):
    t, amt, n, unit = int(m[1]), m[2], int(m[3]), m[4]
    r = Fraction(t, n)
    wrong = [("MULTIPLIED_RATE", number(t * n)), ("INVERTED", number(Fraction(n, t)))]
    return number(r), wrong, f"{t} {amt} ÷ {n} {unit} = {frac(r)} {amt} per {m[6]}."


def _t3_convert(m):
    big, f, small, n, given, asked = m[1], int(m[2]), m[3], int(m[4]), m[5], m[6]
    if given == small:  # to the bigger unit: divide
        ans = Fraction(n, f)
        wrong = [("MULTIPLIED_RATE", number(n * f)), ("INVERTED", number(Fraction(f, n)))]
        expl = f"Every {f} {small} make 1 {big}: {n} ÷ {f} = {frac(ans)}, so {n} {small} = {frac(ans)} {asked}."
    else:  # to the smaller unit: multiply
        ans = Fraction(n * f)
        wrong = [("DIVIDED_RATE", number(Fraction(n, f))), ("ADDITIVE", number(n + f)),
                 ("DIVIDED_RATE", number(Fraction(f, n)))]
        expl = f"Each {big} is {f} {small}: {n} × {f} = {frac(ans)}, so {n} {given} = {frac(ans)} {small}."
    return number(ans), wrong, expl


# --- T4 ----------------------------------------------------------------------------------------
def pct_steps(p: int, W: int) -> str:
    """Correct working for p% of W (also the explanation)."""
    v = Fraction(p * W, 100)
    if p == 10:
        return f"10% is 1/10: {W} ÷ 10 = {frac(v)}."
    if p == 25:
        return f"25% is 1/4: {W} ÷ 4 = {frac(v)}."
    if p == 75:
        return f"25% of {W} is {W} ÷ 4 = {W // 4}, so 75% is 3 × {W // 4} = {frac(v)}."
    if p == 50 and W % 10:
        return f"50% is half: {W} ÷ 2 = {frac(v)}."
    return f"10% of {W} is {W // 10}, so {p}% is {p // 10} × {W // 10} = {frac(v)}."


def _t4_pct(m):
    p, W = int(m[1]), int(m[2])
    ans = Fraction(p * W, 100)
    wrong = [("PERCENT_AS_PART", number(p))]
    if W > p:
        wrong.append(("SUBTRACTED", number(W - p)))
    if p != 10 and W % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", number(W // 10)))
    if p == 75:
        wrong.append(("ONE_PART", number(Fraction(W, 4))))
    return number(ans), wrong, pct_steps(p, W)


# --- T5 ----------------------------------------------------------------------------------------
def _ratio_pair(m):
    x, y, a, b = m[1].lower(), m[2], int(m[3]), int(m[4])
    return {x: a, y: b}, x, y


def _t5_share(m):
    cnt, x, y = _ratio_pair(m)
    T, N, asked = int(m[5]), m[6], m[7]
    s = cnt[x] + cnt[y]
    k = _scale(s, T)
    other = y if asked == x else x
    wrong = [("OTHER_PART", number(cnt[other] * k))]
    if (T * cnt[asked]) % cnt[other] == 0:  # the total read as the other group's count
        wrong.append(("PART_AS_TOTAL", number(T * cnt[asked] // cnt[other])))
    wrong.append(("FACTOR_ONLY", number(k)))
    expl = (f"{cnt[x]} + {cnt[y]} = {s} parts. {T} ÷ {s} = {k} per part. "
            f"{asked.capitalize()}: {cnt[asked]} × {k} = {cnt[asked] * k}.")
    return number(cnt[asked] * k), wrong, expl


def _t5_total(m):
    cnt, x, y = _ratio_pair(m)
    n, given, N = int(m[5]), m[6], m[7]
    other = y if given == x else x
    k = _scale(cnt[given], n)
    s = cnt[x] + cnt[y]
    wrong = [("OTHER_PART", number(cnt[other] * k)), ("FACTOR_ONLY", number(k)),
             ("ADDITIVE", number(n + cnt[other]))]
    expl = (f"{n} {given} ÷ {cnt[given]} = {k} per part. {cnt[x]} + {cnt[y]} = {s} parts. "
            f"{s} × {k} = {s * k} {N}.")
    return number(s * k), wrong, expl


def _t5_whole(m):
    P, p = int(m[1]), int(m[2])
    W = Fraction(P * 100, p)
    wrong = [("PERCENT_OF_PART", number(Fraction(P * p, 100), dec))]
    if p != 50:  # the rest of the whole, not the whole (for 50% the rest is the given number)
        wrong.append(("OTHER_PART", number(W - P)))
    if p == 75:
        wrong.append(("ONE_PART", number(Fraction(P, 3))))
        expl = f"75% is 3 quarters: {P} ÷ 3 = {P // 3} per quarter. 4 × {P // 3} = {frac(W)}."
    elif p == 25:
        expl = f"25% is 1/4 of the whole, so the whole is 4 × {P} = {frac(W)}."
    elif p == 50:
        expl = f"50% is half of the whole, so the whole is 2 × {P} = {frac(W)}."
    elif p == 10:
        expl = f"10% is 1/10 of the whole, so the whole is 10 × {P} = {frac(W)}."
    else:
        k = p // 10
        wrong.append(("ONE_PART", number(Fraction(P, k))))
        expl = f"{P} is {p}%, so 10% is {P} ÷ {k} = {P // k}. 100% is 10 × {P // k} = {frac(W)}."
    return number(W), wrong, expl


def _t5_price(m):
    n, items, t, mm = int(m[1]), m[2], int(m[3]), int(m[4])
    r = Fraction(t, n)
    wrong = [("ADDITIVE", cash(t + mm - n)), ("TOTAL_AS_UNIT", cash(t * mm)),
             ("FACTOR_ONLY", cash(r))]
    expl = f"${t} ÷ {n} = ${frac(r)} per {SINGULAR[items]}. {mm} × ${frac(r)} = ${frac(r * mm)}."
    return cash(r * mm), wrong, expl


_SOLVERS = {
    "t1_and": _t1_pp, "t1_every": _t1_pp, "t1_all": _t1_all, "t1_rest": _t1_rest,
    "t2_left": _t2_left, "t2_right": _t2_right, "t2_mix": _t2_mix,
    "t3_price": _t3_price, "t3_speed": _t3_speed, "t3_convert": _t3_convert,
    "t4_pct": _t4_pct,
    "t5_share": _t5_share, "t5_total": _t5_total, "t5_whole": _t5_whole, "t5_price": _t5_price,
}

# t1_all must be tried before t1_and ("to all X" also fits "to (\w+)"? no: "all pets" is two words,
# so t1_and cannot match it; order kept anyway for clarity).


# ---------------------------------------------------------------------------------------------
# Distractor assembly
# ---------------------------------------------------------------------------------------------
def misconception_choices(prompt: str):
    """[(label, (display, value))] distinct in value, none equal to the answer, positive."""
    _, correct, wrong, _ = analyze(prompt)
    seen = {correct[1]}
    out = []
    for label, ch in wrong:
        if ch[1] <= 0 or ch[1] in seen or len(ch[0]) > 14 or ch[1] > 999:
            continue
        seen.add(ch[1])
        out.append((label, ch))
    return out


def _arith_candidates(correct, rng):
    disp, v = correct
    if ":" in disp:
        p, q = (int(s) for s in disp.split(":"))
        c = [(p + 1, q), (p, q + 1), (p - 1, q), (p, q - 1), (p + 2, q), (p, q + 2)]
        rng.shuffle(c)
        return [ratio(a, b) for a, b in c if a > 0 and b > 0]
    mk = cash if disp.startswith("$") else number
    deltas = [1, -1, 2, -2]
    rng.shuffle(deltas)
    far = [5, -5, 10, -10, 3, -3]
    rng.shuffle(far)
    return [mk(v + d) for d in deltas + far if v + d > 0]


def make_item(prompt: str, tier: int, answer_pos: int, rng: random.Random):
    if len(prompt) > 60:
        return None
    _, correct, raw, expl = analyze(prompt)
    if len(expl) > 160 or len(correct[0]) > 14:
        return None
    mis = misconception_choices(prompt)
    if not mis:
        return None
    wrong = list(mis)
    if len(wrong) > 3:
        wrong = wrong[:3]
    used = {correct[1]} | {ch[1] for _, ch in raw}  # ARITH never equals ANY rule's value
    for ch in _arith_candidates(correct, rng):
        if len(wrong) == 3:
            break
        if ch[1] not in used:
            used.add(ch[1])
            wrong.append(("ARITH", ch))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, correct)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [ch[0] for _, ch in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


# ---------------------------------------------------------------------------------------------
# Builders (pick numbers inside the bounds, render a prompt)
# ---------------------------------------------------------------------------------------------
def _two_counts(rng, lo=2, hi=10):
    while True:
        a, b = rng.randint(lo, hi), rng.randint(lo, hi)
        if a != b:
            return a, b


def b_t1(rng, kind):
    x, y, n = rng.choice(GROUPS)
    a, b = _two_counts(rng)
    P, Q = (x, y) if rng.random() < 0.5 else (y, x)
    if kind == 0:
        return f"{a} {x} and {b} {y}. Ratio of {P} to {Q}?"
    if kind == 1:
        return f"For every {a} {x} there are {b} {y}. Ratio of {P} to {Q}?"
    if kind == 2:
        return f"{a} {x} and {b} {y}. Ratio of {P} to all {n}?"
    T = a + b  # total 4..20
    if T > 20:
        return None
    return f"{T} {n}: {a} are {x}, the rest {y}. Ratio of {P} to {Q}?"


def b_t2(rng, kind):
    a, b = _two_counts(rng, 2, 10)  # no 1: the scale factor would equal a given number
    k = rng.randint(2, 10)
    if kind == 0:
        return f"{a}:{b} = ?:{b * k}"
    if kind == 1:
        return f"{a}:{b} = {a * k}:?"
    mix, x, y = rng.choice(MIXES)
    if rng.random() < 0.5:
        return f"{mix}: {a} {x} to {b} {y}. {x.capitalize()} for {b * k} {y}?"
    return f"{mix}: {a} {x} to {b} {y}. {y.capitalize()} for {a * k} {x}?"


def b_t3(rng, kind):
    n, r = rng.randint(2, 10), rng.randint(2, 10)
    if kind == 0:
        items, one = rng.choice(ITEMS_FOR_SALE)
        return f"{n} {items} cost ${n * r}. Cost per {one}?"
    if kind == 1:
        amt, unit, cap, one = rng.choice(RATES)
        return f"{n * r} {amt} in {n} {unit}. {cap} per {one}?"
    big, bigs, small, f = rng.choice(UNITS)
    if kind == 2:  # small -> big
        return f"1 {big} = {f} {small}. {n * f} {small} = ? {bigs}"
    return f"1 {big} = {f} {small}. {n} {bigs if n > 1 else big} = ? {small}"


def b_t4(rng, kind):
    """kind: 0 tens percent, 1 25% or 75%, 2 10%."""
    if kind == 0:
        p, W = rng.choice(TENS), 10 * rng.randint(2, 9)
    elif kind == 1:
        p, W = rng.choice((25, 75)), 4 * rng.randint(2, 10)
    else:
        p, W = 10, 10 * rng.randint(2, 9)
    if rng.random() < 0.5:
        return f"What is {p}% of {W}?"
    noun, verb = rng.choice(PCT_CONTEXTS)
    return f"{p}% of {W} {noun} {verb}. How many?"


def b_t5(rng, kind):
    if kind in (0, 1):
        x, y, n = rng.choice(GROUPS)
        while True:
            a, b = _two_counts(rng, 2, 8)
            if a + b <= 10:
                break
        k = rng.randint(2, 10)
        head = f"{x.capitalize()}:{y} is {a}:{b}."
        if kind == 0:
            asked = x if rng.random() < 0.5 else y
            return f"{head} {(a + b) * k} {n} in all. How many {asked}?"
        given, g = (x, a) if rng.random() < 0.5 else (y, b)
        return f"{head} There are {g * k} {given}. How many {n}?"
    if kind == 2:
        r = rng.random()
        if r < 0.5:
            p, W = rng.choice([t for t in TENS if t != 50]), 10 * rng.randint(2, 9)  # 50% uses 2q
        elif r < 0.75:
            p, W = rng.choice((25, 75)), 4 * rng.randint(2, 10)
        elif r < 0.9:
            p, W = 50, 2 * rng.randint(3, 10)
        else:
            p, W = 10, 10 * rng.randint(2, 9)
        return f"{p * W // 100} is {p}% of what number?"
    items, _ = rng.choice(ITEMS_FOR_SALE)
    n, r, mm = rng.randint(2, 10), rng.randint(2, 10), rng.randint(2, 10)
    if mm == n:
        return None
    return f"{n} {items} cost ${n * r}. Cost of {mm} {items}?"


BUILDERS = {1: (b_t1, 4), 2: (b_t2, 3), 3: (b_t3, 4), 4: (b_t4, 3), 5: (b_t5, 4)}
T4_KINDS = [0] * 22 + [1] * 12 + [2] * 6  # tens percents most, then quarters, then 10%


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def _balanced(count, k, rng):
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000):
    build, n_kinds = BUILDERS[tier]
    positions = _balanced(count, 4, rng)
    if tier == 4:
        kinds = list(T4_KINDS[:count]) + [0] * max(0, count - len(T4_KINDS))
        rng.shuffle(kinds)
    else:
        kinds = _balanced(count, n_kinds, rng)
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        prompt = build(rng, kinds[len(items)])
        if prompt is None or prompt in prompts:
            continue
        try:
            item = make_item(prompt, tier, positions[len(items)], rng)
        except NotMine:
            continue
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
