"""Procedural generator for the Division range cartridges (facts-div-5 / -10 / -12 / -15; fnm-cart/1, grade "Facts").

``generate(manifest, rng) -> list[dict]``: stdlib only, deterministic for the rng passed in, imports nothing from other
cartridges. One file for all four ranges, byte-identical in the four directories; the range comes from the id
(``facts-div-12`` -> 12). Division reads the multiplication table backwards: a fact is the pair (a, b), p = a x b, and

  R  ``p ÷ a = ?``  answer b (the quotient)       C  ``p ÷ ? = b``  answer a (the divisor)
  S  ``? ÷ a = b``  answer p (the dividend)

Each tier is a list of PARTS (form, pairs, at_least) (briefs/facts2/pools.py). A tier draws 24 unique prompts from the
union of its parts: each part's floor is filled in list order, the rest is drawn from the union. Division never
divides by 0 and a missing number is never ambiguous (``div_ok``: no 0 ÷ ? = 0).

Wrong choices (modelled misconceptions first, ARITH only to fill; the first key listed wins a value collision):
  R  GROUP_OFF b +- 1, +- 2 | SUBTRACTED p - a | MULTIPLIED p x a (<= 999) | TENS_SLIP b +- 10 (quotient >= 11)
  C  MISSING_ONE_OFF a +- 1 | MISSING_SUBTRACTED p - b | MISSING_MULTIPLIED p x b (<= 999)
  S  START_GROUP_OFF a x (b +- 1) = p +- a | START_ADDED a + b | START_TENS p +- 10 (a factor >= 11)
Near: R and C within 2 of the answer (the answer is a factor); S within the larger factor of the answer (one group off).
Every item has >= 2 near wrong values and at most 1 far one. Per tier each rank of the answer among its four values
(smallest .. largest) is balanced (the most constrained items choose first, each takes the least-used feasible rank),
and S items with a factor >= 11 and p >= 20 always carry a START_TENS value (the answer's ones digit is not unique).
"""
from __future__ import annotations

import itertools
import random

DIV = "÷"
MAX_WRONG = 999


# ------------------------------------------------------------------------------------------------ pools
def mul_pairs(n: int, low: int = 0) -> list:
    return [(a, b) for a in range(low, n + 1) for b in range(low, n + 1)]


EASY = {0, 1, 2, 5, 10}
MID = {3, 4, 9}
HARD = {6, 7, 8}
CORE = MID | HARD


def big(x, n_from: int = 11) -> bool:
    return max(x) >= n_from


def easy_fact(x) -> bool:
    a, b = x
    return bool(EASY & {a, b}) or (11 in x and min(x) <= 9)


def parts_5() -> dict:
    p = mul_pairs(5)
    one_five = mul_pairs(5, 1)
    two_five = mul_pairs(5, 2)
    return {
        1: [("R", [x for x in p if {0, 1, 2, 5} & set(x)], 0)],
        2: [("R", one_five, 0)],
        3: [("R", two_five, 12), ("C", [x for x in one_five if x[0] in (2, 5)], 8)],
        4: [("C", one_five, 0)],
        5: [("S", two_five, 12), ("C", two_five, 0)],
    }


def parts_10() -> dict:
    p = mul_pairs(10)
    core = [x for x in p if set(x) <= CORE]
    return {
        1: [("R", [x for x in p if EASY & set(x)], 0)],
        2: [("R", [x for x in core if set(x) <= MID], 8), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", [x for x in core if set(x) <= HARD], 8), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", core, 12), ("C", mul_pairs(10, 2), 0)],
        5: [("S", core, 12), ("C", core, 0)],
    }


def parts_12() -> dict:
    p = mul_pairs(12)
    core = [x for x in p if set(x) <= CORE]
    t1 = [x for x in p if easy_fact(x)]
    t2_new = [x for x in p if 12 in x and min(x) in MID]
    t3_new = [x for x in p if not easy_fact(x) and big(x) and (HARD & set(x) or min(x) >= 11)]
    core12 = [x for x in mul_pairs(12, 3) if not easy_fact(x)]
    return {
        1: [("R", [x for x in t1 if big(x)], 8), ("R", t1, 0)],
        2: [("R", t2_new, 6), ("R", [x for x in core if set(x) <= MID], 6), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", t3_new, 8), ("R", [x for x in core if set(x) <= HARD], 6), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", [x for x in core12 if big(x)], 6), ("C", core, 8), ("C", mul_pairs(12, 2), 0)],
        5: [("S", [x for x in core12 if big(x)], 6), ("S", core12, 6), ("C", [x for x in core12 if big(x)], 4), ("C", core12, 0)],
    }


def parts_15() -> dict:
    p = mul_pairs(15)
    t1 = [x for x in p if easy_fact(x)]
    teen = lambda x: max(x) >= 11
    t2 = [x for x in p if teen(x) and not easy_fact(x) and min(x) in (3, 4)]
    t3 = [x for x in p if teen(x) and not easy_fact(x) and (min(x) in (6, 7, 8, 9) or min(x) >= 11)]
    core = [x for x in p if set(x) <= CORE]
    hard15 = [x for x in mul_pairs(15, 3) if not easy_fact(x)]
    return {
        1: [("R", [x for x in t1 if teen(x)], 12), ("R", t1, 0)],
        2: [("R", t2, 12), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", t3, 12), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", [x for x in hard15 if teen(x)], 12), ("C", hard15, 0)],
        5: [("S", [x for x in hard15 if teen(x)], 8), ("S", hard15, 4), ("C", [x for x in hard15 if teen(x)], 4), ("C", hard15, 0)],
    }


PARTS = {5: parts_5, 10: parts_10, 12: parts_12, 15: parts_15}


def div_ok(form: str, x) -> bool:
    """(a, b) is p ÷ a = b: never divide by 0; a missing number is never ambiguous (no 0 ÷ ? = 0)."""
    a, b = x
    if a == 0:
        return False
    return form == "R" or b >= 1


def range_of(manifest: dict) -> int:
    return int(manifest["id"].rsplit("-", 1)[1])


def tier_parts(rng_n: int, tier: int) -> list:
    """The tier's parts as (form, [usable pairs], at_least)."""
    return [(f, [x for x in ps if div_ok(f, x)], n) for f, ps, n in PARTS[rng_n]()[tier]]


def draw_prompts(rng_n: int, tier: int, n: int, rng: random.Random) -> list:
    """n unique (form, (a, b)): floors filled in part order, then the rest from the union."""
    parts = tier_parts(rng_n, tier)
    chosen: list = []
    taken: set = set()

    def have(form, pairs):
        ps = set(pairs)
        return sum(1 for f, x in chosen if f == form and x in ps)

    for form, pairs, need in parts:
        while have(form, pairs) < need:
            free = [x for x in pairs if (form, x) not in taken]
            x = rng.choice(free)
            taken.add((form, x))
            chosen.append((form, x))
    union = []
    seen: set = set()
    for form, pairs, _ in parts:
        for x in pairs:
            if (form, x) not in seen:
                seen.add((form, x))
                union.append((form, x))
    rest = [fx for fx in union if fx not in taken]
    chosen.extend(rng.sample(rest, n - len(chosen)))
    return chosen


# ------------------------------------------------------------------------------------------------ wrong values
def wrong_value(form: str, key: str, a: int, b: int, sign: int = 1, size: int = 1):
    """The wrong value a student holding ``key`` gets for the fact p ÷ a = b in prompt form ``form`` (None when it
    does not apply). ``sign`` / ``size`` pick the direction and size of the slips."""
    p = a * b
    if form == "R":
        if key == "GROUP_OFF":
            return b + sign * size
        if key == "SUBTRACTED":
            return p - a
        if key == "MULTIPLIED":
            return p * a if p * a <= MAX_WRONG else None
        if key == "TENS_SLIP":
            return b + 10 * sign if b >= 11 else None
    elif form == "C":
        if key == "MISSING_ONE_OFF":
            return a + sign * size
        if key == "MISSING_SUBTRACTED":
            return p - b
        if key == "MISSING_MULTIPLIED":
            return p * b if p * b <= MAX_WRONG else None
    elif form == "S":
        if key == "START_GROUP_OFF":
            return a * (b + sign * size)
        if key == "START_ADDED":
            return a + b
        if key == "START_TENS":
            return p + 10 * sign if max(a, b) >= 11 else None
    raise KeyError((form, key))


def answer_of(form: str, a: int, b: int) -> int:
    return {"R": b, "C": a, "S": a * b}[form]


def near_tol(form: str, a: int, b: int) -> int:
    """How close counts as near: R and C answers are factors (within 2); S answer is a product (one group off)."""
    return max(a, b) if form == "S" else 2


def prompt_of(form: str, a: int, b: int) -> str:
    p = a * b
    return {"R": f"{p} {DIV} {a} = ?", "C": f"{p} {DIV} ? = {b}", "S": f"? {DIV} {a} = {b}"}[form]


def candidates(form: str, a: int, b: int) -> dict:
    """value -> (key, kind) for every usable wrong value, in the brief's key order; kind 'near' or 'far' by distance."""
    ans = answer_of(form, a, b)
    tol = near_tol(form, a, b)
    out: dict = {}

    def add(v, key):
        if v is None or v < 0 or v > MAX_WRONG or v == ans or v in out:
            return
        out[v] = (key, "near" if abs(v - ans) <= tol else "far")

    if form == "R":
        for size in (1, 2):
            for sign in (1, -1):
                add(wrong_value("R", "GROUP_OFF", a, b, sign, size), "GROUP_OFF")
        add(wrong_value("R", "SUBTRACTED", a, b), "SUBTRACTED")
        add(wrong_value("R", "MULTIPLIED", a, b), "MULTIPLIED")
        for sign in (1, -1):
            add(wrong_value("R", "TENS_SLIP", a, b, sign), "TENS_SLIP")
        for d in (3, -3):
            add(ans + d, "ARITH")
    elif form == "C":
        for sign in (1, -1):
            add(wrong_value("C", "MISSING_ONE_OFF", a, b, sign), "MISSING_ONE_OFF")
        add(wrong_value("C", "MISSING_SUBTRACTED", a, b), "MISSING_SUBTRACTED")
        add(wrong_value("C", "MISSING_MULTIPLIED", a, b), "MISSING_MULTIPLIED")
        for d in (2, -2, 3, -3):
            add(ans + d, "ARITH")
    else:
        for sign in (1, -1):
            add(wrong_value("S", "START_GROUP_OFF", a, b, sign), "START_GROUP_OFF")
        add(wrong_value("S", "START_ADDED", a, b), "START_ADDED")
        for sign in (1, -1):
            add(wrong_value("S", "START_TENS", a, b, sign), "START_TENS")
        for d in (b, -b, 1, -1, 2, -2):
            add(ans + d, "ARITH")
    return out


WEIGHT = {"GROUP_OFF": 2.0, "SUBTRACTED": 2.0, "MULTIPLIED": 2.0, "TENS_SLIP": 2.0, "MISSING_ONE_OFF": 2.0,
          "MISSING_SUBTRACTED": 2.0, "MISSING_MULTIPLIED": 2.0, "START_GROUP_OFF": 2.0, "START_ADDED": 2.0,
          "START_TENS": 2.0, "ARITH": 1.0}


def needs_twin(form: str, a: int, b: int) -> bool:
    """S items with a factor >= 11 and a product >= 20: the answer's ones digit must not be unique."""
    return form == "S" and max(a, b) >= 11 and a * b >= 20


def feasible_combos(form: str, a: int, b: int, need_tens: bool) -> dict:
    """rank (number of wrong values below the answer) -> list of (score, [(value, key), x3])."""
    ans = answer_of(form, a, b)
    cand = candidates(form, a, b)
    res: dict = {}
    for trio in itertools.combinations(sorted(cand), 3):
        kinds = [cand[v][1] for v in trio]
        if sum(1 for k in kinds if k == "near") < 2 or sum(1 for k in kinds if k == "far") > 1:
            continue
        if need_tens and not any(cand[v][0] == "START_TENS" for v in trio):
            continue
        rank = sum(1 for v in trio if v < ans)
        score = sum(WEIGHT[cand[v][0]] for v in trio)
        res.setdefault(rank, []).append((score, [(v, cand[v][0]) for v in trio]))
    return res


# ------------------------------------------------------------------------------------------------ explanations
def explanation(form: str, a: int, b: int) -> str:
    p = a * b
    if form == "R":
        base = f"{p} {DIV} {a} = {b} because {a} × {b} = {p}."
        if b == 0:
            return f"{p} {DIV} {a} = 0: zero shared into groups of {a} leaves none, and {a} × 0 = 0."
        if a == 1:
            return f"{p} {DIV} 1 = {p}: dividing by 1 changes nothing."
        if b == 1:
            return f"{p} {DIV} {a} = 1: any number divided by itself is 1."
        if a == 2:
            return f"{p} {DIV} 2 = {b}: half of {p} is {b}, because {b} + {b} = {p}."
        if a == 5:
            return f"{p} {DIV} 5 = {b} because 5 × {b} = {p}. Fives: half of {10 * b} is {p}."
        if a == 10:
            return f"{p} {DIV} 10 = {b}: take the zero off {p}. Check: 10 × {b} = {p}."
        if b >= 11:
            return f"{base} Split {b} as 10 and {b - 10}: {a * 10} + {a * (b - 10)} = {p}."
        if a >= 11:
            return f"{base} Split {a} as 10 and {a - 10}: {10 * b} + {(a - 10) * b} = {p}."
        if a == 9:
            return f"{base} Nines: 10 × {b} = {10 * b}, minus one {b} is {p}."
        if a >= 3 and b >= 3:
            return f"{base} Neighbour fact: {a} × {b - 1} = {a * (b - 1)}, plus one more {a}."
        return f"{base} Think: what times {a} makes {p}?"
    if form == "C":
        base = f"{p} {DIV} ? = {b}: {b} × {a} = {p}, so ? = {a}."
        if a == 1:
            return f"{base} Dividing by 1 changes nothing."
        if b == 1:
            return f"{base} A number divided by itself is 1."
        if a == b:
            return f"{base} A square fact: {a} times itself makes {p}."
        if b >= 11 or a >= 11:
            hi, lo = (b, a) if b >= a else (a, b)
            return f"{base} Split {hi} as 10 and {hi - 10}: {lo * 10} + {lo * (hi - 10)} = {p}."
        return f"{base} Ask: what times {b} makes {p}?"
    base = f"? {DIV} {a} = {b}: {a} × {b} = {p}, so ? = {p}."
    if a == 1:
        return f"{base} Dividing by 1 changes nothing."
    if b == 1:
        return f"{base} Dividing by {a} leaves 1, so it was {a}."
    if a == 2:
        return f"{base} Undo halving by doubling: {b} + {b} = {p}."
    if a == 5:
        return f"{base} Fives: half of {10 * b} is {p}."
    if a == 10:
        return f"{base} Undo it: put a zero on {b}."
    if b >= 11:
        return f"{base} Split {b} as 10 and {b - 10}: {a * 10} + {a * (b - 10)} = {p}."
    if a >= 11:
        return f"{base} Split {a} as 10 and {a - 10}: {10 * b} + {(a - 10) * b} = {p}."
    if a == 9:
        return f"{base} Nines: 10 × {b} = {10 * b}, minus one {b} is {p}."
    return f"{base} Undo dividing by multiplying: {a} × {b}."


# ------------------------------------------------------------------------------------------------ tier
def gen_tier(rng_n: int, tier: int, n: int, rng: random.Random) -> list:
    chosen = draw_prompts(rng_n, tier, n, rng)
    info = []
    for form, (a, b) in chosen:
        combos = feasible_combos(form, a, b, needs_twin(form, a, b))
        if not combos:  # cannot honour the twin requirement: relax it
            combos = feasible_combos(form, a, b, False)
        info.append(((form, a, b), combos))
    order = list(range(n))
    rng.shuffle(order)
    order.sort(key=lambda i: len(info[i][1]))
    counts = [0, 0, 0, 0]
    picked = {}
    for i in order:
        combos = info[i][1]
        low = min(counts[r] for r in combos)
        r = rng.choice([r for r in sorted(combos) if counts[r] == low])
        counts[r] += 1
        pool = sorted(((s + rng.random() * 2.0, t) for s, t in combos[r]), key=lambda x: -x[0])
        picked[i] = pool[0][1]
    positions = [i % 4 for i in range(n)]
    rng.shuffle(positions)
    items = []
    for i in range(n):
        (form, a, b), _ = info[i]
        wrong = list(picked[i])
        rng.shuffle(wrong)
        choices, miscs = [], []
        w = iter(wrong)
        for pos in range(4):
            if pos == positions[i]:
                choices.append(str(answer_of(form, a, b)))
                miscs.append(None)
            else:
                v, key = next(w)
                choices.append(str(v))
                miscs.append(key)
        items.append({
            "tier": tier,
            "prompt": prompt_of(form, a, b),
            "choices": choices,
            "answer": positions[i],
            "misconceptions": miscs,
            "explanation": explanation(form, a, b),
        })
    rng.shuffle(items)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    r = range_of(manifest)
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(r, t["tier"], n, rng))
    return items
