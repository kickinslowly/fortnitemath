"""Procedural generator for the Times Tables Facts cartridges (fnm-cart/1, grade "Facts"): facts-mul-5, -10, -12, -15.

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape without
``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges. ONE file, byte-identical
in the four directories; the range (the factors 0 to N) comes from the id: ``facts-mul-<N>``.

Design (briefs/facts2/pools.py is the spec; the pools below are copied from it)
------
* A fact is an ordered pair (a, b), a x b = p. Three FORMS read it: R ``a × b = ?`` (answer p), C ``a × ? = p``
  (answer b), S ``? × b = p`` (answer a). A missing factor is never 0 (``mul_ok``), so it is never ambiguous.
* Each tier is a list of PARTS (form, pairs, at_least). ``select`` fills each part's floor in list order, then draws
  the rest from the union at random: 24 unique prompts per tier. Prompts with a 0 factor are capped per tier
  (ZERO_CAP) so that "answer 0 is always the smallest" cannot make the smallest rank a tell.
* Wrong values come from modelled misconceptions first (``candidates``), ``ARITH`` (answer +- 1..3) only to fill.
  Near = within the larger factor of the answer (at least 2) for R, within 2 for C / S. At least two wrong values
  near, at most one far. R items with a factor of 11 or more and an answer of 20 or more always hold a wrong value
  with the answer's ones digit (so the ones digit alone never gives the answer away).
* Per item and target rank there is a best set of three wrong values (``best_combo``). Ranks (smallest .. largest by
  value) are assigned across a tier greedily, most constrained item first, to the rank held least so far; a tier whose
  ranks do not land in 15-35% is redrawn. Answer positions are round-robin, then shuffled.
"""
from __future__ import annotations

import random
from itertools import combinations

MUL = "×"
MAX_CHOICE = 999
ZERO_CAP = 6  # prompts with a 0 factor per tier (R form only: answer 0)
ATTEMPTS = 400


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
    """Times 0, 1, 2, 5, 10, and 11 x a single digit."""
    a, b = x
    return bool(EASY & {a, b}) or (11 in x and min(x) <= 9)


def mul_ok(form: str, x) -> bool:
    """A missing factor is never ambiguous: no 0 x ? = 0."""
    return form == "R" or min(x) >= 1


def mul_5() -> dict:
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


def mul_10() -> dict:
    p = mul_pairs(10)
    core = [x for x in p if set(x) <= CORE]
    return {
        1: [("R", [x for x in p if EASY & set(x)], 0)],
        2: [("R", [x for x in core if set(x) <= MID], 8), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", [x for x in core if set(x) <= HARD], 8), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", core, 12), ("C", mul_pairs(10, 2), 0)],
        5: [("S", core, 12), ("C", core, 0)],
    }


def mul_12() -> dict:
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


def mul_15() -> dict:
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


POOLS = {5: mul_5, 10: mul_10, 12: mul_12, 15: mul_15}


# ------------------------------------------------------------------------------------------------ facts
def answer_of(form: str, a: int, b: int) -> int:
    return {"R": a * b, "C": b, "S": a}[form]


def prompt_of(form: str, a: int, b: int) -> str:
    if form == "R":
        return f"{a} {MUL} {b} = ?"
    if form == "C":
        return f"{a} {MUL} ? = {a * b}"
    return f"? {MUL} {b} = {a * b}"


def near_limit(form: str, a: int, b: int) -> int:
    """How far from the answer a wrong value may be and still count as near."""
    return max(a, b, 2) if form == "R" else 2


def needs_twin(form: str, a: int, b: int) -> bool:
    """Ones-digit rule: R with a factor of 11 or more and an answer of 20 or more."""
    return form == "R" and max(a, b) >= 11 and a * b >= 20


# ------------------------------------------------------------------------------------------------ distractors
def candidates(form: str, a: int, b: int) -> list:
    """Modelled wrong values as (key, value); the first key wins a duplicate value; never the answer."""
    p = a * b
    raw = []
    if form == "R":
        for v in (a * (b + 1), (a + 1) * b, a * (b - 1), (a - 1) * b):
            raw.append(("GROUP_OFF", v))
        raw.append(("ADDED", a + b))
        if max(a, b) >= 11:
            hi, lo = max(a, b), min(a, b)
            if lo >= 10:  # two two-digit factors: tens x tens + ones x ones
                raw.append(("PARTIAL_PRODUCTS", (a // 10) * (b // 10) * 100 + (a % 10) * (b % 10)))
            elif (hi % 10) * lo >= 10:  # the ones product carries a ten
                raw.append(("DROPPED_CARRY", p - 10))
            raw.append(("TENS_SLIP", p - 10))
            raw.append(("TENS_SLIP", p + 10))
        ans = p
    else:
        m = answer_of(form, a, b)
        k = b if form == "S" else a  # the factor shown
        raw.append(("MISSING_ONE_OFF", m + 1))
        raw.append(("MISSING_ONE_OFF", m - 1))
        raw.append(("MISSING_SUBTRACTED", p - k))
        raw.append(("MISSING_PRODUCT", p))
        ans = m
    out, seen = [], {ans}
    for key, v in raw:
        if 0 <= v <= MAX_CHOICE and v not in seen:
            seen.add(v)
            out.append((key, v))
    return out


def fill_values(form: str, a: int, b: int, taken: set) -> list:
    """ARITH fill: the answer +- 1, 2, 3 (nearest first)."""
    ans = answer_of(form, a, b)
    out = []
    for d in (1, 2, 3):
        for v in (ans - d, ans + d):
            if 0 <= v <= MAX_CHOICE and v != ans and v not in taken:
                out.append(("ARITH", v))
    return out


def best_combo(form: str, a: int, b: int, rank: int, rng: random.Random, flag: bool):
    """Three (key, value) wrong choices with exactly ``rank`` of them below the answer, or None."""
    ans = answer_of(form, a, b)
    pool = candidates(form, a, b)
    pool = pool + fill_values(form, a, b, {v for _, v in pool})
    limit = near_limit(form, a, b)
    twin = needs_twin(form, a, b)
    weight = {"GROUP_OFF": 3, "ADDED": 4 if flag else 2, "DROPPED_CARRY": 4, "TENS_SLIP": 3, "PARTIAL_PRODUCTS": 4,
              "MISSING_ONE_OFF": 3, "MISSING_SUBTRACTED": 4 if flag else 2, "MISSING_PRODUCT": 2 if flag else 4,
              "ARITH": 0}
    best, best_score = [], None
    for combo in combinations(pool, 3):
        vals = [v for _, v in combo]
        if sum(1 for v in vals if v < ans) != rank:
            continue
        if sum(1 for v in vals if abs(v - ans) <= limit) < 2:
            continue
        if twin and not any(v % 10 == ans % 10 for v in vals):
            continue
        score = sum(weight[k] for k, _ in combo)
        if best_score is None or score > best_score:
            best, best_score = [combo], score
        elif score == best_score:
            best.append(combo)
    if not best:
        return None
    return list(best[rng.randrange(len(best))])


# ------------------------------------------------------------------------------------------------ explanations
def _tail(a: int, b: int) -> str:
    p = a * b
    lo, hi = min(a, b), max(a, b)
    if lo == 0:
        return "no groups, or groups of nothing, make 0. Anything times 0 is 0."
    if lo == 1:
        return f"one group of {hi}. Any number times 1 is itself."
    if hi == 10:
        return f"ten groups of {lo}, so put a zero after {lo}."
    if lo == 2:
        return f"doubling. Double {hi} is {hi} + {hi} = {p}."
    if lo == 5 and hi <= 10:
        return f"half of {hi} × 10 = {hi * 10}, and half of {hi * 10} is {p}."
    if hi >= 11:
        rest = hi - 10
        if hi == 15:
            return f"10 × {lo} = {10 * lo}, 5 × {lo} = {5 * lo}, then {10 * lo} + {5 * lo} = {p}."
        if hi == 11:
            return f"10 × {lo} = {10 * lo}, plus one more {lo} = {p}."
        return f"split {hi} into 10 and {rest}. {10 * lo} + {rest * lo} = {p}."
    if hi == 9:
        return f"10 × {lo} = {10 * lo}, minus one {lo} = {p}."
    if lo == 4:
        return f"double {hi} is {2 * hi}, double again is {p}."
    if lo == 3:
        return f"2 × {hi} = {2 * hi}, plus one more {hi} = {p}."
    if hi - lo == 1:
        return f"{lo} × {lo} = {lo * lo}, plus one more {lo} = {p}."
    return f"split {lo} into 5 and {lo - 5}. 5 × {hi} = {5 * hi}, {lo - 5} × {hi} = {(lo - 5) * hi}, total {p}."


def explain(form: str, a: int, b: int) -> str:
    """The fact and one reusable strategy (<= 160 chars)."""
    p = a * b
    if form == "R":
        return f"{a} {MUL} {b} = {p}: " + _tail(a, b)
    m = answer_of(form, a, b)
    k = b if form == "S" else a
    head = f"{prompt_of(form, a, b)}: {a} {MUL} {b} = {p}, so ? = {m}. "
    if k == 1:
        tip = "Any number times 1 is itself."
    elif k == 2:
        tip = f"Half of {p} is {m}."
    elif k == 5:
        tip = f"Count by 5s to {p}: {m} jumps."
    elif k == 10:
        tip = f"Drop the zero from {p}: {m}."
    else:
        tip = f"Count by {k}s up to {p}, or divide: {p} ÷ {k} = {m}."
    return head + tip


# ------------------------------------------------------------------------------------------------ selection
def select(parts: list, n: int, rng: random.Random) -> list:
    """n unique (form, a, b): each part's floor in list order, then the rest from the union."""
    usable = [[(f, x[0], x[1]) for x in pairs if mul_ok(f, x)] for f, pairs, _ in parts]
    chosen, chosen_set = [], set()
    zeros = [0]

    def ok(it):
        return it not in chosen_set and not (it[0] == "R" and 0 in (it[1], it[2]) and zeros[0] >= ZERO_CAP)

    def add(it):
        chosen.append(it)
        chosen_set.add(it)
        if it[0] == "R" and 0 in (it[1], it[2]):
            zeros[0] += 1

    for (f, pairs, need), use in zip(parts, usable):
        members = set(use)
        have = sum(1 for it in chosen if it in members)
        for _ in range(max(0, need - have)):
            cand = [it for it in use if ok(it)]
            if not cand:
                raise ValueError("a floor cannot be met")
            add(cand[rng.randrange(len(cand))])
    union = []
    seen = set()
    for use in usable:
        for it in use:
            if it not in seen:
                seen.add(it)
                union.append(it)
    while len(chosen) < n:
        cand = [it for it in union if ok(it)]
        if not cand:
            raise ValueError("not enough prompts")
        add(cand[rng.randrange(len(cand))])
    return chosen


def assemble(tier: int, picked: list, n: int, rng: random.Random):
    info = []
    for form, a, b in picked:
        flag = rng.random() < 0.4
        combos = {}
        for r in range(4):
            c = best_combo(form, a, b, r, rng, flag)
            if c is not None:
                combos[r] = c
        if not combos:
            return None
        info.append(((form, a, b), combos))
    counts = [0, 0, 0, 0]
    assigned = {}
    order = sorted(range(n), key=lambda i: (len(info[i][1]), rng.random()))
    for i in order:
        feas = sorted(info[i][1])
        low = min(counts[r] for r in feas)
        r = rng.choice([r for r in feas if counts[r] == low])
        counts[r] += 1
        assigned[i] = r
    if any(not (0.15 * n <= c <= 0.35 * n) for c in counts):
        return None
    positions = [i % 4 for i in range(n)]
    rng.shuffle(positions)
    items = []
    for i in range(n):
        (form, a, b), combos = info[i]
        wrong = list(combos[assigned[i]])
        rng.shuffle(wrong)
        slots = [None] * 4
        slots[positions[i]] = (None, answer_of(form, a, b))
        it = iter(wrong)
        for s in range(4):
            if slots[s] is None:
                slots[s] = next(it)
        items.append({
            "tier": tier,
            "prompt": prompt_of(form, a, b),
            "choices": [str(v) for _, v in slots],
            "answer": positions[i],
            "misconceptions": [k for k, _ in slots],
            "explanation": explain(form, a, b),
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    tiers = POOLS[int(manifest["id"].rsplit("-", 1)[1])]()
    items = []
    for tier in sorted(tiers):
        for _ in range(ATTEMPTS):
            built = assemble(tier, select(tiers[tier], n, rng), n, rng)
            if built is not None:
                items += built
                break
        else:
            raise ValueError(f"tier {tier}: no draw met the rank balance")
    return items
