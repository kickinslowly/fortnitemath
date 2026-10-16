"""Procedural generator for the Division Facts cartridge (fnm-cart/1, PROTOCOL 4c).

``generate(manifest, rng) -> list[dict]``: stdlib only, deterministic for the rng passed in, imports nothing from
other cartridges. A prompt is ``p ÷ a = ?`` where ``p = a × b`` (the multiplication fact read backwards); the
answer is the quotient ``b``.

Wrong choices (cartridges/LIBRARY.md "Rules for every Facts cartridge"):
  GROUP_OFF   quotient +- 1 or +- 2             (near: a group or two off)
  ARITH       quotient +- 3 (fill only, when a rank needs a third value on one side)
  TENS_SLIP   quotient +- 10, tiers 4-5         (keeps the answer's ones digit)
  SUBTRACTED  p - a                             (far, wrong operation)
  MULTIPLIED  p * a, only when <= 999           (far, wrong operation)
Rules per item: >= 2 near values, at most 1 far value; per tier the answer's value rank among its four choices is
balanced (greedy: the most constrained items choose first, each takes the least-used feasible rank), and in tiers
4-5 about 85% of items carry a TENS_SLIP value (the ones-digit tell).
"""
from __future__ import annotations

import itertools
import random

DIV = "÷"
MAX_WRONG = 999

# tier -> max(a, b) must lie in [band_lo, band_hi]; both factors >= min_f
BANDS = {
    1: dict(min_f=1, band_lo=1, band_hi=5),
    2: dict(min_f=2, band_lo=6, band_hi=8),
    3: dict(min_f=2, band_lo=9, band_hi=10),
    4: dict(min_f=2, band_lo=11, band_hi=12),
    5: dict(min_f=2, band_lo=13, band_hi=15),
}
TENS_TIERS = (4, 5)
TENS_SHARE = 0.85  # share of tier 4-5 items that carry a TENS_SLIP value

WEIGHT = {"GROUP_OFF": 2.0, "SUBTRACTED": 2.0, "MULTIPLIED": 2.0, "TENS_SLIP": 2.0, "ARITH": 1.0}


def pairs(tier: int) -> list:
    """All (a, b) divisor/quotient pairs of the tier's band, in a fixed order."""
    c = BANDS[tier]
    out = []
    for a in range(c["min_f"], c["band_hi"] + 1):
        for b in range(c["min_f"], c["band_hi"] + 1):
            if c["band_lo"] <= max(a, b) <= c["band_hi"]:
                out.append((a, b))
    return out


def misconception_value(key: str, p: int, a: int, sign: int = 1, size: int = 1):
    """The wrong value a student holding misconception ``key`` gets for ``p ÷ a`` (None if it does not apply).
    ``sign`` picks the direction of the slips (GROUP_OFF: b+1 / b-1, or b+-2 via ``size=2``; TENS_SLIP: b+-10)."""
    b = p // a
    if key == "SUBTRACTED":
        return p - a
    if key == "MULTIPLIED":
        return p * a if p * a <= MAX_WRONG else None
    if key == "GROUP_OFF":
        return b + sign * size
    if key == "TENS_SLIP":
        return b + 10 * sign
    raise KeyError(key)


def candidates(p: int, a: int, tier: int) -> dict:
    """value -> (key, kind) for every usable wrong value; kind is 'near', 'far', 'other' or 'fill'.
    When two keys give one value the first added wins (GROUP_OFF, ARITH near, TENS_SLIP, SUBTRACTED, MULTIPLIED)."""
    b = p // a
    out: dict = {}

    def add(v, key, kind):
        if v is None or v < 0 or v > MAX_WRONG or v == b or v in out:
            return
        out[v] = (key, kind)

    add(misconception_value("GROUP_OFF", p, a, 1), "GROUP_OFF", "near")
    add(misconception_value("GROUP_OFF", p, a, -1), "GROUP_OFF", "near")
    add(misconception_value("GROUP_OFF", p, a, 1, 2), "GROUP_OFF", "near")
    add(misconception_value("GROUP_OFF", p, a, -1, 2), "GROUP_OFF", "near")
    if tier in TENS_TIERS:
        add(misconception_value("TENS_SLIP", p, a, 1), "TENS_SLIP", "other")
        add(misconception_value("TENS_SLIP", p, a, -1), "TENS_SLIP", "other")
    add(misconception_value("SUBTRACTED", p, a), "SUBTRACTED", "far")
    add(misconception_value("MULTIPLIED", p, a), "MULTIPLIED", "far")
    add(b + 3, "ARITH", "fill")
    add(b - 3, "ARITH", "fill")
    return out


def feasible_combos(p: int, a: int, tier: int, need_tens: bool) -> dict:
    """rank (number of wrong values below the answer) -> list of (score, [(value, key), x3])."""
    b = p // a
    cand = candidates(p, a, tier)
    res: dict = {}
    for trio in itertools.combinations(sorted(cand), 3):
        kinds = [cand[v][1] for v in trio]
        if sum(1 for k in kinds if k == "near") < 2:
            continue
        if sum(1 for k in kinds if k == "far") > 1:
            continue
        if need_tens and not any(cand[v][0] == "TENS_SLIP" for v in trio):
            continue
        rank = sum(1 for v in trio if v < b)
        score = sum(WEIGHT[cand[v][0]] for v in trio)
        res.setdefault(rank, []).append((score, [(v, cand[v][0]) for v in trio]))
    return res


def explanation(p: int, a: int) -> str:
    b = p // a
    base = f"{p} {DIV} {a} = {b} because {a} × {b} = {p}."
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
    if b >= 3 and a >= 3:
        return f"{base} Neighbour fact: {a} × {b - 1} = {a * (b - 1)}, plus one more {a}."
    return f"{base} Think: what times {a} makes {p}?"


def gen_tier(tier: int, n: int, rng: random.Random) -> list:
    chosen = rng.sample(pairs(tier), n)
    info = []
    for (a, b) in chosen:
        p = a * b
        need = tier in TENS_TIERS and rng.random() < TENS_SHARE
        combos = feasible_combos(p, a, tier, need)
        if not combos:  # cannot honour the tens requirement: relax it
            combos = feasible_combos(p, a, tier, False)
        info.append(((a, b), combos))
    # most constrained items choose first; ties by rng
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
        # best score with noise, so the mix of distractor kinds varies
        pool = sorted(((s + rng.random() * 2.0, t) for s, t in combos[r]), key=lambda x: -x[0])
        picked[i] = pool[0][1]
    positions = [i % 4 for i in range(n)]
    rng.shuffle(positions)
    items = []
    for i in range(n):
        (a, b), _ = info[i]
        p = a * b
        wrong = list(picked[i])
        rng.shuffle(wrong)
        choices, miscs = [], []
        w = iter(wrong)
        for pos in range(4):
            if pos == positions[i]:
                choices.append(str(b))
                miscs.append(None)
            else:
                v, key = next(w)
                choices.append(str(v))
                miscs.append(key)
        items.append({
            "tier": tier,
            "prompt": f"{p} {DIV} {a} = ?",
            "choices": choices,
            "answer": positions[i],
            "misconceptions": miscs,
            "explanation": explanation(p, a),
        })
    rng.shuffle(items)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
