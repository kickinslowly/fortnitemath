"""Procedural generator for the facts-subtraction cartridge (fnm-cart/1).

Prompt ``s − a = ?`` (U+2212): the addition fact a + b = s read backwards, answer b. Stdlib only,
deterministic for a given ``rng``, imports nothing from other cartridges (PROTOCOL 4c, LIBRARY.md "Facts").

Per tier: pick the prompts by stratum (see ``pick_prompts``), compute every valid set of three wrong
values (modelled misconceptions first, ``ARITH`` only to fill), assign each item the answer's rank by
value (smallest .. largest) so each rank holds 15-35% of the tier, then assign answer positions
round-robin.
"""
from __future__ import annotations

import itertools
import random

MINUS = "−"
MAX_CHOICE = 999
NEAR = (1, 2, 10)

# (low, high) of the minuend s per tier
BANDS = {1: (2, 10), 2: (11, 20), 3: (21, 40), 4: (41, 70), 5: (71, 100)}


def regroups(s: int, a: int) -> bool:
    """The ones of s are smaller than the ones of a (a trade is needed)."""
    return s % 10 < a % 10


def smaller_from_larger(s: int, a: int) -> int:
    """Each place: larger digit minus smaller digit (14 − 6 → 12, 52 − 38 → 26)."""
    out, place = 0, 1
    while s or a:
        out += abs(s % 10 - a % 10) * place
        s //= 10
        a //= 10
        place *= 10
    return out


def wrong_candidates(s: int, a: int, tier: int):
    """Ordered list of (value, key): every wrong value a modelled misconception gives, then ARITH fill.
    When two keys give one value, the key listed first wins."""
    b = s - a
    cands = []

    def add(v, key):
        if v < 0 or v > MAX_CHOICE or v == b or any(v == c[0] for c in cands):
            return
        cands.append((v, key))

    add(b + 1, "ONE_OFF")
    add(b - 1, "ONE_OFF")
    add(s + a, "ADDED")
    if regroups(s, a):
        add(smaller_from_larger(s, a), "SMALLER_FROM_LARGER")
        add(b + 10, "FORGOT_TRADE")
    if tier >= 3:
        add(b + 10, "TENS_SLIP")
        add(b - 10, "TENS_SLIP")
    add(b + 2, "ARITH")
    add(b - 2, "ARITH")
    add(b - 3, "ARITH")
    add(b + 3, "ARITH")
    if tier < 3:
        add(b + 10, "ARITH")
    return cands


def is_near(v: int, b: int) -> bool:
    return abs(v - b) in NEAR


def valid_sets(s: int, a: int, tier: int):
    """Every valid triple of wrong candidates, as (rank_of_answer, ((v, key), ...), arith_count)."""
    b = s - a
    cands = wrong_candidates(s, a, tier)
    out = []
    for trio in itertools.combinations(cands, 3):
        vals = [v for v, _ in trio]
        if sum(1 for v in vals if is_near(v, b)) < 2:
            continue
        if sum(1 for v in vals if not is_near(v, b)) > 1:
            continue
        if tier >= 3 and not any(v % 10 == b % 10 for v in vals):
            continue
        rank = sum(1 for v in vals if v < b)
        arith = sum(1 for _, k in trio if k == "ARITH")
        out.append((rank, trio, arith))
    return out


def explanation(s: int, a: int, rng: random.Random) -> str:
    b = s - a
    if s <= 10:
        if a == b:
            return f"{s} {MINUS} {a} = {b} because double {a} is {s}."
        return f"{s} {MINUS} {a} = {b} because {a} + {b} = {s}."
    if s % 10 == 0 and a < 10:
        return f"{s} {MINUS} {a} = {b}: 10 {MINUS} {a} = {10 - a}, so {s - 10} + {10 - a} = {b}."
    if s <= 20:
        if a == b:
            return f"{s} {MINUS} {a} = {b} because double {a} is {s}."
        if a < 10 and regroups(s, a):
            down = s % 10
            return (f"{s} {MINUS} {a}: {s} {MINUS} {down} = 10, then {a - down} more is {b}. "
                    f"Check: {a} + {b} = {s}.")
        return f"{s} {MINUS} {a} = {b} because {a} + {b} = {s}."
    # two-digit minuend
    if a < 10:
        if s % 10 == 0:
            return f"{s} {MINUS} {a} = {b}: 10 {MINUS} {a} = {10 - a}, so {s - 10} + {10 - a} = {b}."
        if regroups(s, a):
            down = s % 10
            return f"{s} {MINUS} {a}: {s} {MINUS} {down} = {s - down}, then {a - down} more is {b}."
        return f"{s} {MINUS} {a} = {b}: the ones are {s % 10} {MINUS} {a} = {s % 10 - a}, the tens stay."
    if a % 10 == 0:
        return f"{s} {MINUS} {a} = {b}: {s // 10} tens {MINUS} {a // 10} tens = {b // 10} tens, plus {s % 10}."
    tens, ones = a - a % 10, a % 10
    if regroups(s, a) and rng.random() < 0.5:
        return f"{s} {MINUS} {a}: count up from {a} to {s}, {b} steps. Check: {a} + {b} = {s}."
    return f"{s} {MINUS} {a}: {s} {MINUS} {tens} = {s - tens}, then {s - tens} {MINUS} {ones} = {b}."


def _is_m10(s: int, a: int) -> bool:
    """A multiple of 10 as an operand (minuend, subtrahend) or as the answer."""
    return s % 10 == 0 or a % 10 == 0 or (s - a) % 10 == 0


def pick_prompts(tier: int, count: int, rng: random.Random):
    lo, hi = BANDS[tier]
    pool = [(s, a) for s in range(lo, hi + 1) for a in range(1, s)]  # a, b >= 1
    if tier == 1:
        return rng.sample(pool, count)
    pool = [(s, a) for (s, a) in pool if a >= 2 and s - a >= 2]
    if tier == 2:
        pool = [(s, a) for (s, a) in pool if min(a, s - a) <= 9]
        cross = [p for p in pool if p[1] < 10 and regroups(*p)]
        crossed = set(cross)
        rest = [p for p in pool if p not in crossed]
        n_cross = count * 3 // 5
        return rng.sample(cross, n_cross) + rng.sample(rest, count - n_cross)
    quota = {  # (regroups, one-digit a) -> items of 40
        (False, False): 6, (False, True): 6, (True, False): 10, (True, True): 14,
    }
    strata = {k: [] for k in quota}
    m10 = []
    for (s, a) in pool:
        if _is_m10(s, a):
            m10.append((s, a))
        else:
            strata[(regroups(s, a), a < 10)].append((s, a))
    chosen = []
    for k in sorted(quota):
        chosen += rng.sample(strata[k], round(quota[k] * count / 40))
    chosen += rng.sample(m10, count - len(chosen))
    return chosen


def _balanced(n: int, k: int, rng: random.Random):
    out = [i % k for i in range(n)]
    rng.shuffle(out)
    return out


def gen_tier(tier: int, count: int, rng: random.Random):
    prompts = pick_prompts(tier, count, rng)
    rng.shuffle(prompts)
    sets = [valid_sets(s, a, tier) for (s, a) in prompts]
    # answer rank per item: scarcest items first, least-used feasible rank (round-robin catch-up)
    order = sorted(range(count), key=lambda i: (len({r for r, _, _ in sets[i]}), i))
    used = [0, 0, 0, 0]
    ranks = [0] * count
    for i in order:
        feasible = sorted({r for r, _, _ in sets[i]})
        if not feasible:
            raise RuntimeError(f"tier {tier}: no wrong set for {prompts[i]}")
        low = min(used[r] for r in feasible)
        r = rng.choice([r for r in feasible if used[r] == low])
        used[r] += 1
        ranks[i] = r
    positions = _balanced(count, 4, rng)
    items = []
    for i, (s, a) in enumerate(prompts):
        b = s - a
        options = [x for x in sets[i] if x[0] == ranks[i]]
        best = min(x[2] for x in options)
        options = [x for x in options if x[2] == best]
        _, trio, _ = rng.choice(options)
        wrong = list(trio)
        rng.shuffle(wrong)
        choices, keys = [], []
        for slot in range(4):
            if slot == positions[i]:
                choices.append(str(b))
                keys.append(None)
            else:
                v, k = wrong.pop()
                choices.append(str(v))
                keys.append(k)
        items.append({
            "tier": tier,
            "prompt": f"{s} {MINUS} {a} = ?",
            "choices": choices,
            "answer": positions[i],
            "misconceptions": keys,
            "explanation": explanation(s, a, rng),
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
