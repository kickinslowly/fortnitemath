"""Procedural generator for the facts-add-<range> cartridges (fnm-cart/1; one file, byte-identical in all four).

Contract (PROTOCOL.md 3): ``generate(manifest, rng) -> list[dict]``, items in the 4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

The range (10, 20, 50 or 100) comes from the cartridge id (``facts-add-<range>``). A fact is an ordered pair (a, b),
a + b = s, and three prompt FORMS read it (briefs/facts2/pools.py is the spec, copied below):
  R  ``a + b = ?`` -> s        C  ``a + ? = s`` -> b        S  ``? + b = s`` -> a
Each tier is a list of PARTS (form, pairs, floor). The tier draws ``items_per_tier`` unique prompts from the union of
its parts so that every part's floor holds (floors are filled in list order, an item counts toward every part that
contains it, the rest is drawn from the union).

Distractors (misconception keys, first listed wins a value collision, ARITH only to fill):
  R:   ONE_OFF s +- 1 | SUBTRACTED |a - b| | NO_CARRY s - 10 when the ones make a ten | TENS_SLIP s +- 10 otherwise
  C/S: MISSING_ADDED k + s (added the two numbers you can see; k the shown one) | MISSING_ONE_OFF m +- 1 |
       MISSING_TENS m +- 10 (m the answer).   The tens keys only in the two-digit ranges (20, 50, 100).
Each item needs >= 2 near wrong values (+-1, +-2, +-10) and at most 1 far one. A target rank (smallest .. largest among
the four values) is balanced per tier by always taking the least-used feasible rank. Answers >= 20 always carry a wrong
value with the answer's ones digit (+-10), so the ones digit alone never gives the fact away; the answer is never the
only value of its parity.
"""
from __future__ import annotations

import itertools
import random

MAX_WRONG = 999
ATTEMPTS = 400

KEY_ORDER_R = ("ONE_OFF", "SUBTRACTED", "NO_CARRY", "TENS_SLIP", "ARITH")
KEY_ORDER_M = ("MISSING_ADDED", "MISSING_ONE_OFF", "MISSING_TENS", "ARITH")
WEIGHT = {"ONE_OFF": 3.0, "SUBTRACTED": 2.5, "NO_CARRY": 4.0, "TENS_SLIP": 3.0, "ARITH": 1.0,
          "MISSING_ADDED": 2.5, "MISSING_ONE_OFF": 3.0, "MISSING_TENS": 3.5}


# ---------------------------------------------------------------------------------------------
# Pools (briefs/facts2/pools.py, addition)
# ---------------------------------------------------------------------------------------------
def regroups(a: int, b: int) -> bool:
    return a % 10 + b % 10 >= 10


def is_tens(a: int, b: int) -> bool:
    return (a > 0 and a % 10 == 0) or (b > 0 and b % 10 == 0)


def add_pairs(lo: int, hi: int, low: int = 0) -> list:
    return [(a, b) for s in range(lo, hi + 1) for a in range(low, s - low + 1) for b in [s - a]]


def add_10() -> dict:
    p = add_pairs(1, 10)
    make_ten = [(a, 10 - a) for a in range(1, 10)]
    return {
        1: [("R", [x for x in p if min(x) <= 2], 0)],
        2: [("R", [x for x in p if min(x) >= 2], 0)],
        3: [("R", [x for x in p if min(x) >= 3], 8), ("C", make_ten, 4), ("S", make_ten, 4)],
        4: [("C", [x for x in p if min(x) >= 1], 0)],
        5: [("S", add_pairs(5, 10, 2), 12), ("C", add_pairs(5, 10, 2), 0)],
    }


def add_20() -> dict:
    p = add_pairs(11, 20, 1)
    one_digit = [x for x in p if max(x) <= 9]
    t1 = [x for x in p if max(x) >= 10 and not regroups(*x)]
    t2 = [x for x in p if min(x) >= 2 and (x[0] == x[1] or abs(x[0] - x[1]) == 1 or (9 in x and max(x) <= 9))]
    missing = [x for x in p if min(x) >= 2]
    return {
        1: [("R", t1, 0)],
        2: [("R", t2, 0)],
        3: [("R", one_digit, 0)],
        4: [("C", [x for x in missing if max(x) <= 9], 12), ("C", missing, 0)],
        5: [("S", [x for x in missing if max(x) <= 9], 6), ("S", missing, 12),
            ("C", [x for x in missing if max(x) <= 9], 0)],
    }


def add_big(lo: int, hi: int) -> dict:
    p = add_pairs(lo, hi, 2)
    plain = [x for x in p if not is_tens(*x)]
    two_one = lambda xs: [x for x in xs if min(x) <= 9]
    no_reg = [x for x in plain if not regroups(*x)]
    reg = [x for x in plain if regroups(*x)]
    return {
        1: [("R", [x for x in add_pairs(lo, hi, 1) if is_tens(*x)], 0)],
        2: [("R", two_one(no_reg), 8), ("R", [x for x in no_reg if min(x) >= 10], 8)],
        3: [("R", two_one(reg), 8), ("R", [x for x in reg if min(x) >= 10], 8)],
        4: [("C", reg, 12), ("C", plain, 0)],
        5: [("S", reg, 6), ("S", plain, 12), ("C", reg, 6), ("C", plain, 0)],
    }


POOLS = {10: add_10, 20: add_20, 50: lambda: add_big(21, 50), 100: lambda: add_big(51, 100)}


def range_of(manifest: dict) -> int:
    return int(manifest["id"].rsplit("-", 1)[1])


def choose_items(parts: list, n: int, rng: random.Random) -> list:
    """n unique (form, (a, b)) prompts: each part's floor in list order, then the rest from the union."""
    chosen: list = []
    chosen_set: set = set()
    union: list = []
    union_set: set = set()
    for form, pairs, _ in parts:
        for x in pairs:
            u = (form, x)
            if u not in union_set:
                union_set.add(u)
                union.append(u)
    for form, pairs, floor in parts:
        usable = [(form, x) for x in pairs]
        usable_set = set(usable)
        have = sum(1 for u in chosen if u in usable_set)
        avail = [u for u in usable if u not in chosen_set]
        rng.shuffle(avail)
        for u in avail[:max(0, floor - have)]:
            chosen.append(u)
            chosen_set.add(u)
    rest = [u for u in union if u not in chosen_set]
    rng.shuffle(rest)
    for u in rest[:max(0, n - len(chosen))]:
        chosen.append(u)
        chosen_set.add(u)
    if len(chosen) != n:
        raise ValueError(f"only {len(chosen)} of {n} prompts")
    rng.shuffle(chosen)
    return chosen


# ---------------------------------------------------------------------------------------------
# Prompt, answer
# ---------------------------------------------------------------------------------------------
def prompt_of(form: str, a: int, b: int) -> str:
    s = a + b
    if form == "R":
        return f"{a} + {b} = ?"
    if form == "C":
        return f"{a} + ? = {s}"
    return f"? + {b} = {s}"


def answer_of(form: str, a: int, b: int) -> int:
    return a + b if form == "R" else (b if form == "C" else a)


# ---------------------------------------------------------------------------------------------
# Distractors
# ---------------------------------------------------------------------------------------------
def is_near(d: int) -> bool:
    return abs(d) in (1, 2, 10)


def candidates(hi: int, form: str, a: int, b: int) -> dict:
    """value -> key for every wrong value we may offer (collisions resolved by key order)."""
    s = a + b
    ans = answer_of(form, a, b)
    raw = []
    if form == "R":
        order = KEY_ORDER_R
        raw += [("ONE_OFF", s - 1), ("ONE_OFF", s + 1)]
        raw.append(("SUBTRACTED", abs(a - b)))
        if hi >= 20:
            raw.append(("NO_CARRY" if regroups(a, b) else "TENS_SLIP", s - 10))
            raw.append(("TENS_SLIP", s + 10))
    else:
        order = KEY_ORDER_M
        k = a if form == "C" else b
        raw.append(("MISSING_ADDED", k + s))
        raw += [("MISSING_ONE_OFF", ans - 1), ("MISSING_ONE_OFF", ans + 1)]
        if hi >= 20:
            raw += [("MISSING_TENS", ans - 10), ("MISSING_TENS", ans + 10)]
    raw += [("ARITH", ans + d) for d in (-2, 2, -3, 3, -4, 4)]
    out: dict = {}
    for key in order:
        for k2, v in raw:
            if k2 == key and 0 <= v <= MAX_WRONG and v != ans and v not in out:
                out[v] = key
    return out


def best_combos(hi: int, form: str, a: int, b: int, rng: random.Random, strict: bool) -> dict:
    """rank (number of wrong values below the answer) -> best (score, [(value, key)...])."""
    ans = answer_of(form, a, b)
    cand = candidates(hi, form, a, b)
    noise = {v: rng.random() * 0.6 for v in sorted(cand)}
    best: dict = {}
    for combo in itertools.combinations(sorted(cand), 3):
        near = sum(is_near(v - ans) for v in combo)
        if near < 2:
            continue
        if sum(not is_near(v - ans) for v in combo) > 1:
            continue
        if ans >= 20 and not any((v - ans) % 10 == 0 for v in combo):
            continue
        if strict and not any((v - ans) % 2 == 0 for v in combo):
            continue
        rank = sum(v < ans for v in combo)
        score = sum(WEIGHT[cand[v]] + noise[v] for v in combo)
        if len({cand[v] for v in combo}) == 3:
            score += 1.0  # variety of mistakes
        if ans - 1 in combo and ans + 1 in combo:
            score -= 1.0  # not always the two neighbours
        if rank not in best or score > best[rank][0]:
            best[rank] = (score, [(v, cand[v]) for v in combo])
    return best


# ---------------------------------------------------------------------------------------------
# Explanations: the fact and one reusable strategy
# ---------------------------------------------------------------------------------------------
def tens(n: int) -> str:
    return f"{n} ten" if n == 1 else f"{n} tens"


def explain_r(a: int, b: int) -> str:
    s = a + b
    lo, hi = min(a, b), max(a, b)
    head = f"{a} + {b} = {s}"
    if lo == 0:
        return f"{head}: adding 0 changes nothing, so the answer is {hi}."
    if a == b:
        return f"{head}: a double. Doubles are worth knowing by heart."
    if s == 10:
        return f"{head}: a pair that makes ten. Learn the ten pairs."
    if lo == 1:
        return f"{head}: adding 1 is just the next number after {hi}."
    if s <= 10:
        if hi - lo == 1:
            return f"{head}: double {lo} is {2 * lo}, one more is {s}."
        return f"{head}: start at {hi} and count up {lo}."
    if s <= 20:
        if hi <= 9:
            if hi - lo == 1:
                return f"{head}: double {lo} is {2 * lo}, one more is {s}."
            if hi == 9:
                return f"{head}: {lo} + 10 = {lo + 10}, and 9 is one less than 10, so {s}."
            need = 10 - hi
            return f"{head}: {hi} + {need} = 10, then {lo - need} more is {s}."
        h = hi - 10
        if h == 0:
            return f"{head}: a ten and {lo} more is {s}."
        return f"{head}: ones first, {h} + {lo} = {h + lo}, and the ten makes {s}."
    if is_tens(a, b):
        t, o = (a, b) if a % 10 == 0 else (b, a)
        if o % 10 == 0:
            return f"{head}: {tens(a // 10)} + {tens(b // 10)} = {tens(s // 10)}."
        if o >= 10:
            return f"{head}: {t} + {o - o % 10} = {t + o - o % 10}, then {o % 10} more is {s}."
        return f"{head}: the tens stay, {t} + {o} = {s}."
    if lo <= 9:
        if regroups(a, b):
            need = 10 - hi % 10
            return f"{head}: {hi} + {need} = {hi + need}, then {lo - need} more is {s}."
        return f"{head}: the tens stay, the ones go from {hi % 10} to {s % 10}."
    ta, tb = a - a % 10, b - b % 10
    ones = a % 10 + b % 10
    return f"{head}: {ta} + {tb} = {ta + tb}, {a % 10} + {b % 10} = {ones}, {ta + tb} + {ones} = {s}."


def explain_missing(form: str, a: int, b: int) -> str:
    s = a + b
    m, k = (b, a) if form == "C" else (a, b)
    head = f"{prompt_of(form, a, b)}: {a} + {b} = {s}, so ? = {m}."
    need = (-k) % 10
    if k % 10 != 0 and m >= need and m - need < 10:
        if m == need:
            if s == 10:
                return f"{head} Ten pairs: {k} and {m} make 10."
            return f"{head} {k} is {need} away from {s}."
        return f"{head} Count up: {k} + {need} = {k + need}, then {m - need} more."
    if m >= 10:
        mt, mo = m - m % 10, m % 10
        if mo == 0:
            return f"{head} Count up by tens: add {tens(m // 10)} to {k}."
        return f"{head} Count up from {k}: {k} + {mt} = {k + mt}, then {mo} more."
    return f"{head} Subtract: {s} - {k} = {m}."


# ---------------------------------------------------------------------------------------------
def build_tier(hi: int, tier: int, parts: list, n: int, rng: random.Random):
    """One attempt: n items with balanced answer ranks, or None."""
    picks = choose_items(parts, n, rng)
    positions = [i % 4 for i in range(n)]
    rng.shuffle(positions)
    rank_pref = [i % 4 for i in range(n)]
    rng.shuffle(rank_pref)
    plans = []
    for form, (a, b) in picks:
        best = best_combos(hi, form, a, b, rng, True)
        if not best:
            best = best_combos(hi, form, a, b, rng, False)
        if not best:
            return None
        plans.append(best)
    # most constrained items first (stable: the picks are already shuffled)
    order = sorted(range(n), key=lambda i: len(plans[i]))
    counts = [0, 0, 0, 0]
    rank_of = {}
    for i in order:
        feasible = sorted(plans[i])
        r = sorted(feasible, key=lambda x: (counts[x], 0 if x == rank_pref[i] else 1, x))[0]
        counts[r] += 1
        rank_of[i] = r
    lo_n, hi_n = -(-15 * n // 100), (35 * n) // 100
    if any(c < lo_n or c > hi_n for c in counts):
        return None
    items = []
    for i, (form, (a, b)) in enumerate(picks):
        ans = answer_of(form, a, b)
        wrong = list(plans[i][rank_of[i]][1])
        rng.shuffle(wrong)
        pos = positions[i]
        choices = [None] * 4
        keys = [None] * 4
        choices[pos] = str(ans)
        it = iter(wrong)
        for p in range(4):
            if p != pos:
                v, k = next(it)
                choices[p] = str(v)
                keys[p] = k
        items.append({
            "tier": tier,
            "prompt": prompt_of(form, a, b),
            "choices": choices,
            "answer": pos,
            "misconceptions": keys,
            "explanation": explain_r(a, b) if form == "R" else explain_missing(form, a, b),
        })
    return items


def gen_tier(hi: int, tier: int, parts: list, n: int, rng: random.Random) -> list:
    for _ in range(ATTEMPTS):
        items = build_tier(hi, tier, parts, n, rng)
        if items is not None:
            return items
    raise ValueError(f"tier {tier}: no balanced draw in {ATTEMPTS} attempts")


def generate(manifest: dict, rng: random.Random) -> list:
    hi = range_of(manifest)
    pools = POOLS[hi]()
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(hi, t["tier"], pools[t["tier"]], n, rng))
    return items
