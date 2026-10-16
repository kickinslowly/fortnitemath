"""Procedural generator for the Multiplication Facts cartridge (fnm-cart/1, grade "Facts").

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape without
``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Tier bands (PROTOCOL §4c / LIBRARY.md "Facts"): the larger factor sits in the tier's band, both factors in
  the tier's range. ``items_per_tier`` prompts are sampled per tier, unique (3 x 7 and 7 x 3 are two prompts).
* Wrong values come from modelled misconceptions first (``candidates``), ``ARITH`` (answer +- 1..3) only to fill.
* Per item and target rank there is a best set of three wrong values (``best_combo``): at least two near
  (within the larger factor of the answer), at most one far, on tiers 4-5 one with the answer's ones digit.
  Ranks (smallest .. largest by value) are assigned across a tier greedily, most constrained item first, to the
  rank held least so far, so each rank lands near 25%. Answer positions are round-robin, then shuffled.
"""
from __future__ import annotations

import random
from itertools import combinations

MUL = "×"
BANDS = {  # tier: (lowest larger factor, highest larger factor, lowest factor)
    1: (1, 5, 1),
    2: (6, 8, 2),
    3: (9, 10, 2),
    4: (11, 12, 2),
    5: (13, 15, 2),
}
MAX_CHOICE = 999


def prompts_for_tier(tier: int) -> list:
    """Every (a, b) in the tier's band, in a fixed order."""
    lo, hi, low = BANDS[tier]
    return [(a, b) for a in range(low, hi + 1) for b in range(low, hi + 1) if lo <= max(a, b) <= hi]


def candidates(a: int, b: int, tier: int) -> list:
    """Modelled wrong values for a x b as (key, value); the first key wins a duplicate value; never the answer."""
    p = a * b
    raw = []
    for v in (a * (b + 1), (a + 1) * b, a * (b - 1), (a - 1) * b):
        raw.append(("GROUP_OFF", v))
    raw.append(("ADDED", a + b))
    if tier >= 4:
        big, small = max(a, b), min(a, b)
        if small >= 10:  # two two-digit factors: tens x tens + ones x ones
            raw.append(("PARTIAL_PRODUCTS", (a // 10) * (b // 10) * 100 + (a % 10) * (b % 10)))
        elif big >= 10 and (big % 10) * small >= 10:  # the ones product carries a ten
            raw.append(("DROPPED_CARRY", p - 10))
        raw.append(("TENS_SLIP", p - 10))
        raw.append(("TENS_SLIP", p + 10))
    out, seen = [], {p}
    for key, v in raw:
        if 0 <= v <= MAX_CHOICE and v not in seen:
            seen.add(v)
            out.append((key, v))
    return out


def fill_values(a: int, b: int, taken: set) -> list:
    """ARITH fill: the answer +- 1, 2, 3 (nearest first)."""
    p = a * b
    out = []
    for d in (1, 2, 3):
        for v in (p - d, p + d):
            if 0 <= v <= MAX_CHOICE and v != p and v not in taken:
                out.append(("ARITH", v))
    return out


def is_near(a: int, b: int, v: int) -> bool:
    return abs(v - a * b) <= max(a, b)


def best_combo(a: int, b: int, tier: int, rank: int, rng: random.Random, use_added: bool):
    """Three (key, value) wrong choices with exactly ``rank`` of them below the answer, or None."""
    p = a * b
    pool = candidates(a, b, tier)
    pool = pool + fill_values(a, b, {v for _, v in pool})
    weight = {"GROUP_OFF": 3, "ADDED": 4 if use_added else 2, "DROPPED_CARRY": 4, "TENS_SLIP": 3,
              "PARTIAL_PRODUCTS": 4, "ARITH": 0}
    best, best_score = [], None
    for combo in combinations(pool, 3):
        vals = [v for _, v in combo]
        if sum(1 for v in vals if v < p) != rank:
            continue
        if sum(1 for v in vals if is_near(a, b, v)) < 2:
            continue
        if tier >= 4 and not any(v % 10 == p % 10 for v in vals):
            continue
        score = sum(weight[k] for k, _ in combo)
        if best_score is None or score > best_score:
            best, best_score = [combo], score
        elif score == best_score:
            best.append(combo)
    if not best:
        return None
    return list(best[rng.randrange(len(best))])


def explain(a: int, b: int) -> str:
    """The fact in the prompt's order plus one reusable strategy (<= 160 chars)."""
    return f"{a} {MUL} {b} = {a * b}: " + _strategy(a, b).split(": ", 1)[1]


def _strategy(a: int, b: int) -> str:
    p = a * b
    lo, hi = min(a, b), max(a, b)
    if lo == 1:
        return f"1 × {hi} = {hi}: one group of {hi}. Any number times 1 is itself."
    if hi == 10:
        return f"{lo} × 10 = {p}: ten groups of {lo}, so put a zero after {lo}."
    if lo == 2:
        return f"{hi} × 2 = {p}: doubling. Double {hi} is {hi} + {hi} = {p}."
    if lo == 5 and hi <= 10:
        return f"{hi} × 5 = {p}: half of {hi} × 10 = {hi * 10}, and half of {hi * 10} is {p}."
    if hi >= 11:
        rest = hi - 10
        if hi == 15:
            return f"15 × {lo} = {p}: 10 × {lo} = {10 * lo}, 5 × {lo} = {5 * lo}, then {10 * lo} + {5 * lo} = {p}."
        if hi == 11:
            return f"11 × {lo} = {p}: 10 × {lo} = {10 * lo}, plus one more {lo} = {p}."
        return f"{hi} × {lo} = {p}: split {hi} into 10 and {rest}. {10 * lo} + {rest * lo} = {p}."
    if hi == 9:
        return f"{lo} × 9 = {p}: 10 × {lo} = {10 * lo}, minus one {lo} = {p}."
    if lo == 4:
        return f"{hi} × 4 = {p}: double {hi} is {2 * hi}, double again is {p}."
    if lo == 3:
        return f"{hi} × 3 = {p}: 2 × {hi} = {2 * hi}, plus one more {hi} = {p}."
    if hi - lo == 1:
        return f"{hi} × {lo} = {p}: {lo} × {lo} = {lo * lo}, plus one more {lo} = {p}."
    return (f"{hi} × {lo} = {p}: split {lo} into 5 and {lo - 5}. 5 × {hi} = {5 * hi}, "
            f"{lo - 5} × {hi} = {(lo - 5) * hi}, total {p}.")


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for tier in sorted(BANDS):
        picked = rng.sample(prompts_for_tier(tier), n)
        info = []
        for a, b in picked:
            use_added = rng.random() < 0.4
            combos = {}
            for r in range(4):
                c = best_combo(a, b, tier, r, rng, use_added)
                if c is not None:
                    combos[r] = c
            if not combos:
                raise ValueError(f"no distractor set for {a} {MUL} {b}")
            info.append(((a, b), combos))
        counts = [0, 0, 0, 0]
        assigned = {}
        order = sorted(range(n), key=lambda i: (len(info[i][1]), rng.random()))
        for i in order:
            feas = sorted(info[i][1])
            low = min(counts[r] for r in feas)
            r = rng.choice([r for r in feas if counts[r] == low])
            counts[r] += 1
            assigned[i] = r
        positions = [i % 4 for i in range(n)]
        rng.shuffle(positions)
        for i in range(n):
            (a, b), combos = info[i]
            wrong = list(combos[assigned[i]])
            rng.shuffle(wrong)
            slots = [None] * 4
            slots[positions[i]] = (None, a * b)
            it = iter(wrong)
            for s in range(4):
                if slots[s] is None:
                    slots[s] = next(it)
            items.append({
                "tier": tier,
                "prompt": f"{a} {MUL} {b} = ?",
                "choices": [str(v) for _, v in slots],
                "answer": positions[i],
                "misconceptions": [k for k, _ in slots],
                "explanation": explain(a, b),
            })
    return items
