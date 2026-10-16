"""Procedural generator for the facts-combo cartridge (fnm-cart/1, grade "Facts", PROTOCOL 4c).

``generate(manifest, rng) -> list[dict]``: stdlib only, deterministic for the rng passed in, imports nothing from other
cartridges. Each tier is a quarter each of ``a + b = ?``, ``s − a = ?``, ``a × b = ?`` and ``p ÷ a = ?`` (10 of each at
40 items a tier), every operation drawn from its own cartridge's band at the same tier. The prompt pools, the wrong
values, the near / far / ones-digit rules and the explanations are copied from the four single-operation generators
(cartridges import nothing from each other), with keys prefixed by the operation: ADD_, SUB_, MUL_, DIV_.

Per tier: pick the prompts, compute for every prompt each valid set of three wrong values (>= 2 near, <= 1 far, a
value with the answer's ones digit where the operation's tier needs one), then give every item a target rank (smallest
.. largest by value among its four choices) greedily: the most constrained item first, the least-used feasible rank.
Answer positions are round-robin, then shuffled.
"""
from __future__ import annotations

import itertools
import random

PLUS, MINUS, MUL, DIV = "+", "−", "×", "÷"
MAX_WRONG = 999

ADD_BANDS = {1: (2, 10), 2: (11, 20), 3: (21, 40), 4: (41, 70), 5: (71, 100)}
MUL_BANDS = {1: (1, 5, 1), 2: (6, 8, 2), 3: (9, 10, 2), 4: (11, 12, 2), 5: (13, 15, 2)}  # lo, hi of max factor, min factor


def _key(prefix: str, key: str) -> str:
    return key if key == "ARITH" else f"{prefix}_{key}"


# =============================================================================================
# Addition (copied from facts-addition)
# =============================================================================================
def regroups_add(a: int, b: int) -> bool:
    return a % 10 + b % 10 >= 10


def add_band_pairs(tier: int) -> list:
    lo, hi = ADD_BANDS[tier]
    minop = 1 if tier == 1 else 2
    out = []
    for s in range(lo, hi + 1):
        for a in range(minop, s - minop + 1):
            b = s - a
            if tier == 2 and min(a, b) > 9:
                continue
            out.append((a, b))
    return out


def _pick(pool: list, k: int, used: set, rng: random.Random) -> list:
    avail = [p for p in pool if p not in used]
    rng.shuffle(avail)
    got = avail[:k]
    used.update(got)
    return got


def _is_tens(p) -> bool:
    return p[0] % 10 == 0 or p[1] % 10 == 0


def _is_small(p) -> bool:
    return min(p) <= 9 and max(p) >= 10 and not _is_tens(p)


def _is_both2(p) -> bool:
    return min(p) >= 10 and not _is_tens(p)


def add_prompts(tier: int, n: int, rng: random.Random) -> list:
    pairs = add_band_pairs(tier)
    used: set = set()
    if tier == 1:
        out = _pick(pairs, n, used, rng)
    elif tier == 2:
        cross = [p for p in pairs if max(p) <= 9 and sum(p) >= 11]
        cross_set = set(cross)
        rest = [p for p in pairs if p not in cross_set]
        k = (n * 3 + 4) // 5  # 60% one digit + one digit crossing ten
        out = _pick(cross, k, used, rng) + _pick(rest, n - k, used, rng)
    else:
        n_tens = n // 10
        n_small = (n * 7 + 19) // 20  # 35%: two digits + one digit
        n_rest = n - n_tens - n_small
        n_reg_small = n_small * 2 // 3
        n_reg_rest = (n_rest * 2 + 2) // 3
        out = []
        out += _pick([p for p in pairs if _is_tens(p)], n_tens, used, rng)
        out += _pick([p for p in pairs if _is_small(p) and regroups_add(*p)], n_reg_small, used, rng)
        out += _pick([p for p in pairs if _is_small(p) and not regroups_add(*p)], n_small - n_reg_small, used, rng)
        out += _pick([p for p in pairs if _is_both2(p) and regroups_add(*p)], n_reg_rest, used, rng)
        out += _pick([p for p in pairs if _is_both2(p) and not regroups_add(*p)], n_rest - n_reg_rest, used, rng)
    if len(out) != n:
        raise ValueError(f"add tier {tier}: only {len(out)} of {n} prompts")
    return out


ADD_ORDER = ("ONE_OFF", "SUBTRACTED", "NO_CARRY", "TENS_SLIP", "ARITH")
ADD_WEIGHT = {"ONE_OFF": 3.0, "SUBTRACTED": 2.5, "NO_CARRY": 4.0, "TENS_SLIP": 3.0, "ARITH": 1.0}


def add_candidates(tier: int, a: int, b: int) -> dict:
    """value -> key (unprefixed) for every wrong value we may offer (collisions resolved by ADD_ORDER)."""
    s = a + b
    raw = [("ONE_OFF", s - 1), ("ONE_OFF", s + 1), ("SUBTRACTED", abs(a - b))]
    if tier >= 2:
        raw.append(("NO_CARRY" if regroups_add(a, b) else "TENS_SLIP", s - 10))
        raw.append(("TENS_SLIP", s + 10))
    raw += [("ARITH", s + d) for d in (-2, 2, -3, 3, -4, 4)]
    out: dict = {}
    for key in ADD_ORDER:
        for k, v in raw:
            if k == key and 0 <= v <= MAX_WRONG and v != s and v not in out:
                out[v] = key
    return out


def add_sets(tier: int, a: int, b: int, rng: random.Random) -> list:
    """[(rank, score, [(value, key), x3])] for every valid trio."""
    s = a + b
    cand = add_candidates(tier, a, b)
    noise = {v: rng.random() * 0.6 for v in sorted(cand)}
    out = []
    for combo in itertools.combinations(sorted(cand), 3):
        if sum(abs(v - s) in (1, 2, 10) for v in combo) < 2:
            continue
        if tier >= 3 and not any((v - s) % 10 == 0 for v in combo):
            continue
        score = sum(ADD_WEIGHT[cand[v]] + noise[v] for v in combo)
        if len({cand[v] for v in combo}) == 3:
            score += 1.0
        out.append((sum(v < s for v in combo), score, [(v, _key("ADD", cand[v])) for v in combo]))
    return out


def add_explain(tier: int, a: int, b: int) -> str:
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
    if _is_tens((a, b)):
        t, o = (a, b) if a % 10 == 0 else (b, a)
        if o % 10 == 0:
            return f"{a} + {b} = {s}: {a // 10} tens + {b // 10} tens = {s // 10} tens."
        if o >= 10:
            return f"{a} + {b} = {s}: {t} + {o - o % 10} = {t + o - o % 10}, then {o % 10} more is {s}."
        return f"{a} + {b} = {s}: the tens stay, {t} + {o} = {s}."
    if lo <= 9:
        if regroups_add(a, b):
            need = 10 - hi % 10
            return f"{a} + {b} = {s}: {hi} + {need} = {hi + need}, then {lo - need} more is {s}."
        return f"{a} + {b} = {s}: the tens stay, the ones go from {hi % 10} to {s % 10}."
    ta, tb = a - a % 10, b - b % 10
    ones = a % 10 + b % 10
    return f"{a} + {b} = {s}: {ta} + {tb} = {ta + tb}, {a % 10} + {b % 10} = {ones}, {ta + tb} + {ones} = {s}."


# =============================================================================================
# Subtraction (copied from facts-subtraction)
# =============================================================================================
def regroups_sub(s: int, a: int) -> bool:
    return s % 10 < a % 10


def smaller_from_larger(s: int, a: int) -> int:
    out, place = 0, 1
    while s or a:
        out += abs(s % 10 - a % 10) * place
        s //= 10
        a //= 10
        place *= 10
    return out


def sub_candidates(s: int, a: int, tier: int) -> list:
    b = s - a
    cands: list = []

    def add(v, key):
        if v < 0 or v > MAX_WRONG or v == b or any(v == c[0] for c in cands):
            return
        cands.append((v, key))

    add(b + 1, "ONE_OFF")
    add(b - 1, "ONE_OFF")
    add(s + a, "ADDED")
    if regroups_sub(s, a):
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


def sub_sets(s: int, a: int, tier: int) -> list:
    b = s - a
    cands = sub_candidates(s, a, tier)
    out = []
    for trio in itertools.combinations(cands, 3):
        vals = [v for v, _ in trio]
        if sum(abs(v - b) in (1, 2, 10) for v in vals) < 2:
            continue
        if tier >= 3 and not any(v % 10 == b % 10 for v in vals):
            continue
        arith = sum(1 for _, k in trio if k == "ARITH")
        score = 3.0 - arith + (1.0 if len({k for _, k in trio}) == 3 else 0.0)
        out.append((sum(v < b for v in vals), score, [(v, _key("SUB", k)) for v, k in trio]))
    return out


def sub_explain(s: int, a: int, rng: random.Random) -> str:
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
        if a < 10 and regroups_sub(s, a):
            down = s % 10
            return (f"{s} {MINUS} {a}: {s} {MINUS} {down} = 10, then {a - down} more is {b}. "
                    f"Check: {a} + {b} = {s}.")
        return f"{s} {MINUS} {a} = {b} because {a} + {b} = {s}."
    if a < 10:
        if s % 10 == 0:
            return f"{s} {MINUS} {a} = {b}: 10 {MINUS} {a} = {10 - a}, so {s - 10} + {10 - a} = {b}."
        if regroups_sub(s, a):
            down = s % 10
            return f"{s} {MINUS} {a}: {s} {MINUS} {down} = {s - down}, then {a - down} more is {b}."
        return f"{s} {MINUS} {a} = {b}: the ones are {s % 10} {MINUS} {a} = {s % 10 - a}, the tens stay."
    if a % 10 == 0:
        return f"{s} {MINUS} {a} = {b}: {s // 10} tens {MINUS} {a // 10} tens = {b // 10} tens, plus {s % 10}."
    tens, ones = a - a % 10, a % 10
    if regroups_sub(s, a) and rng.random() < 0.5:
        return f"{s} {MINUS} {a}: count up from {a} to {s}, {b} steps. Check: {a} + {b} = {s}."
    return f"{s} {MINUS} {a}: {s} {MINUS} {tens} = {s - tens}, then {s - tens} {MINUS} {ones} = {b}."


def _is_m10(s: int, a: int) -> bool:
    return s % 10 == 0 or a % 10 == 0 or (s - a) % 10 == 0


def sub_prompts(tier: int, count: int, rng: random.Random) -> list:
    lo, hi = ADD_BANDS[tier]
    pool = [(s, a) for s in range(lo, hi + 1) for a in range(1, s)]
    if tier == 1:
        return rng.sample(pool, count)
    pool = [(s, a) for (s, a) in pool if a >= 2 and s - a >= 2]
    if tier == 2:
        pool = [(s, a) for (s, a) in pool if min(a, s - a) <= 9]
        cross = [p for p in pool if p[1] < 10 and regroups_sub(*p)]
        crossed = set(cross)
        rest = [p for p in pool if p not in crossed]
        n_cross = count * 3 // 5
        return rng.sample(cross, n_cross) + rng.sample(rest, count - n_cross)
    quota = {(False, False): 6, (False, True): 6, (True, False): 10, (True, True): 14}  # of 40
    strata = {k: [] for k in quota}
    m10 = []
    for (s, a) in pool:
        if _is_m10(s, a):
            m10.append((s, a))
        else:
            strata[(regroups_sub(s, a), a < 10)].append((s, a))
    chosen = []
    for k in sorted(quota):
        chosen += rng.sample(strata[k], round(quota[k] * count / 40))
    chosen += rng.sample(m10, count - len(chosen))
    return chosen


# =============================================================================================
# Multiplication (copied from facts-multiplication)
# =============================================================================================
def mul_pairs(tier: int) -> list:
    lo, hi, low = MUL_BANDS[tier]
    return [(a, b) for a in range(low, hi + 1) for b in range(low, hi + 1) if lo <= max(a, b) <= hi]


def mul_candidates(a: int, b: int, tier: int) -> list:
    p = a * b
    raw = [("GROUP_OFF", v) for v in (a * (b + 1), (a + 1) * b, a * (b - 1), (a - 1) * b)]
    raw.append(("ADDED", a + b))
    if tier >= 4:
        big, small = max(a, b), min(a, b)
        if small >= 10:
            raw.append(("PARTIAL_PRODUCTS", (a // 10) * (b // 10) * 100 + (a % 10) * (b % 10)))
        elif big >= 10 and (big % 10) * small >= 10:
            raw.append(("DROPPED_CARRY", p - 10))
        raw.append(("TENS_SLIP", p - 10))
        raw.append(("TENS_SLIP", p + 10))
    out, seen = [], {p}
    for key, v in raw:
        if 0 <= v <= MAX_WRONG and v not in seen:
            seen.add(v)
            out.append((key, v))
    return out


def mul_sets(a: int, b: int, tier: int, use_added: bool) -> list:
    p = a * b
    pool = mul_candidates(a, b, tier)
    taken = {v for _, v in pool}
    for d in (1, 2, 3):
        for v in (p - d, p + d):
            if 0 <= v <= MAX_WRONG and v != p and v not in taken:
                pool.append(("ARITH", v))
    weight = {"GROUP_OFF": 3, "ADDED": 4 if use_added else 2, "DROPPED_CARRY": 4, "TENS_SLIP": 3,
              "PARTIAL_PRODUCTS": 4, "ARITH": 0}
    out = []
    for combo in itertools.combinations(pool, 3):
        vals = [v for _, v in combo]
        if sum(1 for v in vals if abs(v - p) <= max(a, b)) < 2:
            continue
        if tier >= 4 and not any(v % 10 == p % 10 for v in vals):
            continue
        out.append((sum(v < p for v in vals), float(sum(weight[k] for k, _ in combo)),
                    [(v, _key("MUL", k)) for k, v in combo]))
    return out


def mul_explain(a: int, b: int) -> str:
    return f"{a} {MUL} {b} = {a * b}: " + _mul_strategy(a, b).split(": ", 1)[1]


def _mul_strategy(a: int, b: int) -> str:
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


# =============================================================================================
# Division (copied from facts-division)
# =============================================================================================
def div_candidates(p: int, a: int, tier: int) -> dict:
    """value -> (key, kind); first added wins a collision."""
    b = p // a
    out: dict = {}

    def add(v, key, kind):
        if v is None or v < 0 or v > MAX_WRONG or v == b or v in out:
            return
        out[v] = (key, kind)

    for sign, size in ((1, 1), (-1, 1), (1, 2), (-1, 2)):
        add(b + sign * size, "GROUP_OFF", "near")
    if tier in (4, 5):
        add(b + 10, "TENS_SLIP", "other")
        add(b - 10, "TENS_SLIP", "other")
    add(p - a, "SUBTRACTED", "far")
    add(p * a if p * a <= MAX_WRONG else None, "MULTIPLIED", "far")
    add(b + 3, "ARITH", "fill")
    add(b - 3, "ARITH", "fill")
    return out


def div_sets(p: int, a: int, tier: int, need_tens: bool) -> list:
    b = p // a
    cand = div_candidates(p, a, tier)
    w = {"GROUP_OFF": 2.0, "SUBTRACTED": 2.0, "MULTIPLIED": 2.0, "TENS_SLIP": 2.0, "ARITH": 1.0}
    out = []
    for trio in itertools.combinations(sorted(cand), 3):
        kinds = [cand[v][1] for v in trio]
        if sum(k == "near" for k in kinds) < 2 or sum(k == "far" for k in kinds) > 1:
            continue
        if need_tens and not any(cand[v][0] == "TENS_SLIP" for v in trio):
            continue
        out.append((sum(v < b for v in trio), float(sum(w[cand[v][0]] for v in trio)),
                    [(v, _key("DIV", cand[v][0])) for v in trio]))
    return out


def div_explain(p: int, a: int) -> str:
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


# =============================================================================================
# Combo tier
# =============================================================================================
def gen_tier(tier: int, n: int, rng: random.Random) -> list:
    per = n // 4
    pending = []  # dicts: prompt, answer, explanation, sets
    for a, b in add_prompts(tier, per, rng):
        pending.append({"prompt": f"{a} {PLUS} {b} = ?", "answer": a + b, "expl": add_explain(tier, a, b),
                        "sets": add_sets(tier, a, b, rng)})
    for s, a in sub_prompts(tier, per, rng):
        pending.append({"prompt": f"{s} {MINUS} {a} = ?", "answer": s - a, "expl": sub_explain(s, a, rng),
                        "sets": sub_sets(s, a, tier)})
    for a, b in rng.sample(mul_pairs(tier), per):
        pending.append({"prompt": f"{a} {MUL} {b} = ?", "answer": a * b, "expl": mul_explain(a, b),
                        "sets": mul_sets(a, b, tier, rng.random() < 0.4)})
    for a, b in rng.sample(mul_pairs(tier), per):
        p = a * b
        need = tier in (4, 5)  # always, at 10 items a tier: the single cartridge's 85% would leave 1 in 3 as a tell
        sets = div_sets(p, a, tier, need) or div_sets(p, a, tier, False)
        pending.append({"prompt": f"{p} {DIV} {a} = ?", "answer": b, "expl": div_explain(p, a), "sets": sets})
    rng.shuffle(pending)
    for it in pending:
        if not it["sets"]:
            raise RuntimeError(f"tier {tier}: no wrong set for {it['prompt']}")
    # target ranks: most constrained first, least-used feasible rank
    order = sorted(range(len(pending)), key=lambda i: (len({r for r, _, _ in pending[i]["sets"]}), i))
    used = [0, 0, 0, 0]
    ranks = {}
    for i in order:
        feasible = sorted({r for r, _, _ in pending[i]["sets"]})
        low = min(used[r] for r in feasible)
        r = rng.choice([r for r in feasible if used[r] == low])
        used[r] += 1
        ranks[i] = r
    positions = [i % 4 for i in range(len(pending))]
    rng.shuffle(positions)
    items = []
    for i, it in enumerate(pending):
        options = [(sc + rng.random() * 1.5, trio) for r, sc, trio in it["sets"] if r == ranks[i]]
        _, trio = max(options, key=lambda x: x[0])
        wrong = list(trio)
        rng.shuffle(wrong)
        choices, keys = [], []
        for slot in range(4):
            if slot == positions[i]:
                choices.append(str(it["answer"]))
                keys.append(None)
            else:
                v, k = wrong.pop()
                choices.append(str(v))
                keys.append(k)
        items.append({"tier": tier, "prompt": it["prompt"], "choices": choices, "answer": positions[i],
                      "misconceptions": keys, "explanation": it["expl"]})
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
