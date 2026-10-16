"""Procedural generator for the facts-addition cartridge (fnm-cart/1).

Contract (PROTOCOL.md 3): ``generate(manifest, rng) -> list[dict]``, items in the 4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Prompt ``a + b = ?``; the answer is s = a + b. Tier bands (PROTOCOL 4c / LIBRARY.md "Facts"):
T1 s 2-10 (a, b >= 1); T2 s 11-20; T3 s 21-40; T4 s 41-70; T5 s 71-100 (a, b >= 2 from T2 on).

Distractors (misconception keys, first listed wins a value collision):
  ONE_OFF s +- 1 | SUBTRACTED |a - b| | NO_CARRY s - 10 when the ones make a ten | TENS_SLIP s +- 10 | ARITH to fill.
Each item needs >= 2 near wrong values (+-1, +-2, +-10) and at most 1 far one. A target rank (smallest .. largest
among the four values) is balanced per tier by always taking the least-used feasible rank. Tiers 3-5 always carry
a wrong value with the answer's ones digit (s +- 10), so the ones digit alone never gives the fact away.
"""
from __future__ import annotations

import itertools
import random

PLUS = "+"
BANDS = {1: (2, 10), 2: (11, 20), 3: (21, 40), 4: (41, 70), 5: (71, 100)}
MAX_WRONG = 999

# value-collision order and selection weight per key
KEY_ORDER = ("ONE_OFF", "SUBTRACTED", "NO_CARRY", "TENS_SLIP", "ARITH")
WEIGHT = {"ONE_OFF": 3.0, "SUBTRACTED": 2.5, "NO_CARRY": 4.0, "TENS_SLIP": 3.0, "ARITH": 1.0}


def regroups(a: int, b: int) -> bool:
    return a % 10 + b % 10 >= 10


def is_near(d: int) -> bool:
    return abs(d) in (1, 2, 10)


# ---------------------------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------------------------
def band_pairs(tier: int) -> list:
    lo, hi = BANDS[tier]
    minop = 1 if tier == 1 else 2
    out = []
    for s in range(lo, hi + 1):
        for a in range(minop, s - minop + 1):
            b = s - a
            if tier == 2 and min(a, b) > 9:
                continue
            out.append((a, b))
    return out


def pick(pool: list, k: int, used: set, rng: random.Random) -> list:
    avail = [p for p in pool if p not in used]
    rng.shuffle(avail)
    got = avail[:k]
    used.update(got)
    return got


def is_tens(p) -> bool:
    return p[0] % 10 == 0 or p[1] % 10 == 0


def is_small(p) -> bool:
    return min(p) <= 9 and max(p) >= 10 and not is_tens(p)


def is_both2(p) -> bool:
    return min(p) >= 10 and not is_tens(p)


def choose_pairs(tier: int, n: int, rng: random.Random) -> list:
    pairs = band_pairs(tier)
    used: set = set()
    if tier == 1:
        out = pick(pairs, n, used, rng)
    elif tier == 2:
        cross = [p for p in pairs if max(p) <= 9 and sum(p) >= 11]
        cross_set = set(cross)
        rest = [p for p in pairs if p not in cross_set]
        k = (n * 3 + 4) // 5  # 60% one digit + one digit crossing ten (>= half)
        out = pick(cross, k, used, rng) + pick(rest, n - k, used, rng)
    else:
        n_tens = n // 10
        n_small = (n * 7 + 19) // 20  # 35%: two digits + one digit
        n_rest = n - n_tens - n_small
        n_reg_small = n_small * 2 // 3
        n_reg_rest = (n_rest * 2 + 2) // 3
        out = []
        out += pick([p for p in pairs if is_tens(p)], n_tens, used, rng)
        out += pick([p for p in pairs if is_small(p) and regroups(*p)], n_reg_small, used, rng)
        out += pick([p for p in pairs if is_small(p) and not regroups(*p)], n_small - n_reg_small, used, rng)
        out += pick([p for p in pairs if is_both2(p) and regroups(*p)], n_reg_rest, used, rng)
        out += pick([p for p in pairs if is_both2(p) and not regroups(*p)], n_rest - n_reg_rest, used, rng)
    if len(out) != n:
        raise ValueError(f"tier {tier}: only {len(out)} of {n} prompts")
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------------------------------------
# Distractors
# ---------------------------------------------------------------------------------------------
def candidates(tier: int, a: int, b: int) -> dict:
    """value -> key for every wrong value we may offer (collisions resolved by KEY_ORDER)."""
    s = a + b
    raw = []  # (key, value)
    raw += [("ONE_OFF", s - 1), ("ONE_OFF", s + 1)]
    raw.append(("SUBTRACTED", abs(a - b)))
    if tier >= 2:
        raw.append(("NO_CARRY" if regroups(a, b) else "TENS_SLIP", s - 10))
        raw.append(("TENS_SLIP", s + 10))
    raw += [("ARITH", s + d) for d in (-2, 2, -3, 3, -4, 4)]
    out: dict = {}
    for key in KEY_ORDER:
        for k, v in raw:
            if k == key and 0 <= v <= MAX_WRONG and v != s and v not in out:
                out[v] = key
    return out


def best_combos(tier: int, a: int, b: int, rng: random.Random) -> dict:
    """rank (number of wrong values below the answer) -> best (score, [(value, key)...])."""
    s = a + b
    cand = candidates(tier, a, b)
    noise = {v: rng.random() * 0.6 for v in sorted(cand)}
    best: dict = {}
    for combo in itertools.combinations(sorted(cand), 3):
        near = sum(is_near(v - s) for v in combo)
        if near < 2:
            continue
        if sum(not is_near(v - s) for v in combo) > 1:
            continue
        if tier >= 3 and not any((v - s) % 10 == 0 for v in combo):
            continue
        rank = sum(v < s for v in combo)
        score = sum(WEIGHT[cand[v]] + noise[v] for v in combo)
        if len({cand[v] for v in combo}) == 3:
            score += 1.0  # variety of mistakes
        if rank not in best or score > best[rank][0]:
            best[rank] = (score, [(v, cand[v]) for v in combo])
    return best


def explain(tier: int, a: int, b: int) -> str:
    s = a + b
    lo, hi = min(a, b), max(a, b)
    if tier == 1:
        if a == b:
            return f"{a} + {b} = {s}: a double. Doubles are worth knowing by heart."
        if s == 10:
            return f"{a} + {b} = 10: a pair that makes ten. Learn the ten pairs."
        if lo == 1:
            return f"{a} + {b} = {s}: adding 1 is just the next number after {hi}."
        return f"{a} + {b} = {s}: start at {hi} and count up {lo}."
    if tier == 2:
        if a == b:
            return f"{a} + {b} = {s}: a double. Doubles are worth knowing by heart."
        if hi <= 9:
            if hi - lo == 1:
                return f"{a} + {b} = {s}: double {lo} is {2 * lo}, one more is {s}."
            need = 10 - hi
            return f"{a} + {b} = {s}: {hi} + {need} = 10, then {lo - need} more is {s}."
        h = hi - 10
        return f"{a} + {b} = {s}: ones first, {h} + {lo} = {h + lo}, and the ten makes {s}."
    # tiers 3-5
    if is_tens(( a, b)):
        t, o = (a, b) if a % 10 == 0 else (b, a)
        if o % 10 == 0:
            return f"{a} + {b} = {s}: {a // 10} tens + {b // 10} tens = {s // 10} tens."
        if o >= 10:
            return f"{a} + {b} = {s}: {t} + {o - o % 10} = {t + o - o % 10}, then {o % 10} more is {s}."
        return f"{a} + {b} = {s}: the tens stay, {t} + {o} = {s}."
    if lo <= 9:
        if regroups(a, b):
            need = 10 - hi % 10
            return f"{a} + {b} = {s}: {hi} + {need} = {hi + need}, then {lo - need} more is {s}."
        return f"{a} + {b} = {s}: the tens stay, the ones go from {hi % 10} to {s % 10}."
    ta, tb = a - a % 10, b - b % 10
    ones = a % 10 + b % 10
    return f"{a} + {b} = {s}: {ta} + {tb} = {ta + tb}, {a % 10} + {b % 10} = {ones}, {ta + tb} + {ones} = {s}."


# ---------------------------------------------------------------------------------------------
def gen_tier(tier: int, n: int, rng: random.Random) -> list:
    pairs = choose_pairs(tier, n, rng)
    positions = [i % 4 for i in range(n)]
    rng.shuffle(positions)
    rank_pref = [i % 4 for i in range(n)]
    rng.shuffle(rank_pref)
    rank_count = [0, 0, 0, 0]
    items = []
    for i, (a, b) in enumerate(pairs):
        s = a + b
        best = best_combos(tier, a, b, rng)
        # least-used feasible rank; the round-robin target breaks ties
        order = sorted(best, key=lambda r: (rank_count[r], 0 if r == rank_pref[i] else 1, r))
        rank = order[0]
        rank_count[rank] += 1
        wrong = list(best[rank][1])
        rng.shuffle(wrong)
        pos = positions[i]
        choices = [None] * 4
        keys = [None] * 4
        choices[pos] = str(s)
        it = iter(wrong)
        for p in range(4):
            if p != pos:
                v, k = next(it)
                choices[p] = str(v)
                keys[p] = k
        items.append({
            "tier": tier,
            "prompt": f"{a} {PLUS} {b} = ?",
            "choices": choices,
            "answer": pos,
            "misconceptions": keys,
            "explanation": explain(tier, a, b),
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
