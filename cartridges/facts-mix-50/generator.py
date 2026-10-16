"""Procedural generator for the facts-mix-<range> cartridges (fnm-cart/1; one file, byte-identical in all four).

Contract (PROTOCOL.md 3): ``generate(manifest, rng) -> list[dict]``, items in the 4 shape without ``id``. Stdlib only,
deterministic for a given ``rng``, imports nothing from other cartridges (the four operations' rules are copied below).

A mix tier is 6 items from each of the four operations' own cartridges at the paired range and the SAME tier:
  facts-mix-10 = add-10, sub-10, mul-5, div-5        facts-mix-20 = add-20, sub-20, mul-10, div-10
  facts-mix-50 = add-50, sub-50, mul-12, div-12      facts-mix-100 = add-100, sub-100, mul-15, div-15
Each operation draws its 6 prompts from its own pools (briefs/facts2/pools.py) with every part's floor n scaled to
ceil(n / 4) (zero-factor multiplication prompts capped at ceil(6 / 4) = 2). Forms, distractors, explanations and
misconception keys are the operations' own; every key is prefixed with its operation (ADD_, SUB_, MUL_, DIV_), ARITH
(the filler) stays plain. Then the 24 items are balanced together: the answer's rank among its four values (smallest ..
largest) is spread round-robin over the tier (the most constrained items choose first, each takes the least-used feasible
rank; a tier outside 15-35% per rank is redrawn), answer positions are round-robin and shuffled, and the tier order is
shuffled so the operations interleave.

Forms (a fact is the ordered pair (a, b)):
  add  R a + b = ?  -> s      C a + ? = s  -> b      S ? + b = s  -> a
  sub  R s - a = ?  -> b      C s - ? = b  -> a      S ? - a = b  -> s        (s = a + b)
  mul  R a x b = ?  -> p      C a x ? = p  -> b      S ? x b = p  -> a
  div  R p / a = ?  -> b      C p / ? = b  -> a      S ? / a = b  -> p        (p = a x b)
Near (at least 2 per item) and far (at most 1): add and sub within +-1, 2 or 10 of the answer; mul R and div S within the
larger factor (one group off; mul R at least 2); mul C/S and div R/C within 2. Answers >= 20 in addition and subtraction,
mul R with a factor >= 11 and div S with a factor >= 11 always carry a wrong value with the answer's ones digit.
"""
from __future__ import annotations

import itertools
import random

MINUS = "−"
MUL = "×"
DIV = "÷"
MAX_WRONG = 999
ATTEMPTS = 600
PER_OP = 6
OPS = ("add", "sub", "mul", "div")
# mix range -> (add/sub range, mul/div range)
PAIRING = {10: (10, 5), 20: (20, 10), 50: (50, 12), 100: (100, 15)}
ZERO_CAP = 2  # mul R prompts with a 0 factor per mix tier (the old 6 of 24, scaled)


def scaled(n: int) -> int:
    """A part's floor n of 24 becomes ceil(n / 4) of 6."""
    return -(-n // 4)


# =================================================================================================
# Pools (briefs/facts2/pools.py), the four operations
# =================================================================================================
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


ADD_POOLS = {10: add_10, 20: add_20, 50: lambda: add_big(21, 50), 100: lambda: add_big(51, 100)}


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
        5: [("S", [x for x in core12 if big(x)], 6), ("S", core12, 6), ("C", [x for x in core12 if big(x)], 4),
            ("C", core12, 0)],
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
        5: [("S", [x for x in hard15 if teen(x)], 8), ("S", hard15, 4), ("C", [x for x in hard15 if teen(x)], 4),
            ("C", hard15, 0)],
    }


MULDIV_POOLS = {5: mul_5, 10: mul_10, 12: mul_12, 15: mul_15}  # division reads the same pairs backwards


def mul_ok(form: str, x) -> bool:
    """A missing factor is never ambiguous: no 0 x ? = 0."""
    return form == "R" or min(x) >= 1


def div_ok(form: str, x) -> bool:
    """(a, b) is p / a = b: never divide by 0; a missing number is never ambiguous (no 0 / ? = 0)."""
    a, b = x
    if a == 0:
        return False
    return form == "R" or b >= 1


def ok_fn(op: str):
    return {"add": lambda f, x: True, "sub": lambda f, x: True, "mul": mul_ok, "div": div_ok}[op]


def pools_of(op: str, hi: int, n: int, tier: int) -> list:
    """The tier's parts as (form, usable pairs, floor scaled to 6 items)."""
    if op in ("add", "sub"):
        parts = ADD_POOLS[hi]()[tier]
    else:
        parts = MULDIV_POOLS[n]()[tier]
    ok = ok_fn(op)
    return [(f, [x for x in ps if ok(f, x)], scaled(fl)) for f, ps, fl in parts]


def draw(op: str, parts: list, count: int, rng: random.Random) -> list:
    """count unique (op, form, a, b): each part's floor in list order, then the rest from the union."""
    chosen, chosen_set = [], set()
    zeros = [0]

    def zero(it):
        return op == "mul" and it[1] == "R" and 0 in (it[2], it[3])

    def free(it):
        return it not in chosen_set and not (zero(it) and zeros[0] >= ZERO_CAP)

    def add(it):
        chosen.append(it)
        chosen_set.add(it)
        if zero(it):
            zeros[0] += 1

    usable = [[(op, f, x[0], x[1]) for x in pairs] for f, pairs, _ in parts]
    for (f, pairs, need), use in zip(parts, usable):
        members = set(use)
        have = sum(1 for it in chosen if it in members)
        for _ in range(max(0, need - have)):
            cand = [it for it in use if free(it)]
            if not cand:
                raise ValueError("a floor cannot be met")
            add(cand[rng.randrange(len(cand))])
    union, seen = [], set()
    for use in usable:
        for it in use:
            if it not in seen:
                seen.add(it)
                union.append(it)
    while len(chosen) < count:
        cand = [it for it in union if free(it)]
        if not cand:
            raise ValueError("not enough prompts")
        add(cand[rng.randrange(len(cand))])
    return chosen


# =================================================================================================
# Prompts and answers
# =================================================================================================
def answer_of(op: str, form: str, a: int, b: int) -> int:
    if op == "add":
        return a + b if form == "R" else (b if form == "C" else a)
    if op == "sub":
        return {"R": b, "C": a, "S": a + b}[form]
    if op == "mul":
        return {"R": a * b, "C": b, "S": a}[form]
    return {"R": b, "C": a, "S": a * b}[form]


def prompt_of(op: str, form: str, a: int, b: int) -> str:
    s = a + b
    p = a * b
    if op == "add":
        return {"R": f"{a} + {b} = ?", "C": f"{a} + ? = {s}", "S": f"? + {b} = {s}"}[form]
    if op == "sub":
        return {"R": f"{s} {MINUS} {a} = ?", "C": f"{s} {MINUS} ? = {b}", "S": f"? {MINUS} {a} = {b}"}[form]
    if op == "mul":
        return {"R": f"{a} {MUL} {b} = ?", "C": f"{a} {MUL} ? = {p}", "S": f"? {MUL} {b} = {p}"}[form]
    return {"R": f"{p} {DIV} {a} = ?", "C": f"{p} {DIV} ? = {b}", "S": f"? {DIV} {a} = {b}"}[form]


# =================================================================================================
# Distractor plans: for one item, rank (wrong values below the answer) -> [(value, UNPREFIXED key) x3]
# =================================================================================================
# ---- addition ---------------------------------------------------------------------------------
ADD_KEY_ORDER_R = ("ONE_OFF", "SUBTRACTED", "NO_CARRY", "TENS_SLIP", "ARITH")
ADD_KEY_ORDER_M = ("MISSING_ADDED", "MISSING_ONE_OFF", "MISSING_TENS", "ARITH")
ADD_WEIGHT = {"ONE_OFF": 3.0, "SUBTRACTED": 2.5, "NO_CARRY": 4.0, "TENS_SLIP": 3.0, "ARITH": 1.0,
              "MISSING_ADDED": 2.5, "MISSING_ONE_OFF": 3.0, "MISSING_TENS": 3.5}


def add_is_near(d: int) -> bool:
    return abs(d) in (1, 2, 10)


def add_candidates(hi: int, form: str, a: int, b: int) -> dict:
    s = a + b
    ans = answer_of("add", form, a, b)
    raw = []
    if form == "R":
        order = ADD_KEY_ORDER_R
        raw += [("ONE_OFF", s - 1), ("ONE_OFF", s + 1)]
        raw.append(("SUBTRACTED", abs(a - b)))
        if hi >= 20:
            raw.append(("NO_CARRY" if regroups(a, b) else "TENS_SLIP", s - 10))
            raw.append(("TENS_SLIP", s + 10))
    else:
        order = ADD_KEY_ORDER_M
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


def add_best_combos(hi: int, form: str, a: int, b: int, rng: random.Random, strict: bool) -> dict:
    ans = answer_of("add", form, a, b)
    cand = add_candidates(hi, form, a, b)
    noise = {v: rng.random() * 0.6 for v in sorted(cand)}
    best: dict = {}
    for combo in itertools.combinations(sorted(cand), 3):
        near = sum(add_is_near(v - ans) for v in combo)
        if near < 2:
            continue
        if sum(not add_is_near(v - ans) for v in combo) > 1:
            continue
        if ans >= 20 and not any((v - ans) % 10 == 0 for v in combo):
            continue
        if strict and not any((v - ans) % 2 == 0 for v in combo):
            continue
        rank = sum(v < ans for v in combo)
        score = sum(ADD_WEIGHT[cand[v]] + noise[v] for v in combo)
        if len({cand[v] for v in combo}) == 3:
            score += 1.0
        if ans - 1 in combo and ans + 1 in combo:
            score -= 1.0
        if rank not in best or score > best[rank][0]:
            best[rank] = (score, [(v, cand[v]) for v in combo])
    return best


def add_plan(hi: int, form: str, a: int, b: int, rng: random.Random) -> dict:
    best = add_best_combos(hi, form, a, b, rng, True)
    if not best:
        best = add_best_combos(hi, form, a, b, rng, False)
    return {r: combo for r, (_, combo) in best.items()}


# ---- subtraction ------------------------------------------------------------------------------
def smaller_from_larger(s: int, a: int) -> int:
    out, place = 0, 1
    while s or a:
        out += abs(s % 10 - a % 10) * place
        s //= 10
        a //= 10
        place *= 10
    return out


def sub_candidates(form: str, a: int, b: int) -> list:
    s = a + b
    ans = answer_of("sub", form, a, b)
    cands: list = []

    def add(v, key):
        if v < 0 or v > MAX_WRONG or v == ans or any(v == c[0] for c in cands):
            return
        if s <= 10 and abs(v - ans) == 10:
            return  # within 10 there is no ten to trade: no tens slips, no +-10 values
        cands.append((v, key))

    two_digit = s >= 11
    tens = "TENS_SLIP" if form == "R" else "MISSING_TENS"
    if form == "R":
        add(b + 1, "ONE_OFF")
        add(b - 1, "ONE_OFF")
        add(s + a, "ADDED")
        if s >= 11 and s % 10 < a % 10:
            add(smaller_from_larger(s, a), "SMALLER_FROM_LARGER")
            add(b + 10, "FORGOT_TRADE")
    elif form == "C":
        add(s + b, "MISSING_ADDED")
        add(a + 1, "MISSING_ONE_OFF")
        add(a - 1, "MISSING_ONE_OFF")
    else:
        add(abs(b - a), "START_SUBTRACTED")
        add(s + 1, "MISSING_ONE_OFF")
        add(s - 1, "MISSING_ONE_OFF")
        if s >= 11 and regroups(a, b):
            add(s - 10, "START_NO_CARRY")
    if two_digit:
        add(ans + 10, tens)
        add(ans - 10, tens)
    for d in (2, -2, 3, -3):
        add(ans + d, "ARITH")
    add(ans + 10, "ARITH")
    add(ans - 10, "ARITH")
    return cands


def sub_plan(form: str, a: int, b: int, rng: random.Random) -> dict:
    ans = answer_of("sub", form, a, b)
    sets = []
    for trio in itertools.combinations(sub_candidates(form, a, b), 3):
        vals = [v for v, _ in trio]
        if sum(1 for v in vals if abs(v - ans) in (1, 2, 10)) < 2:
            continue
        if sum(1 for v in vals if abs(v - ans) not in (1, 2, 10)) > 1:
            continue
        if ans >= 20 and not any(v % 10 == ans % 10 for v in vals):
            continue
        sets.append((sum(1 for v in vals if v < ans), trio, sum(1 for _, k in trio if k == "ARITH")))
    out = {}
    for r in sorted({x[0] for x in sets}):
        options = [x for x in sets if x[0] == r]
        best = min(x[2] for x in options)
        out[r] = list(rng.choice([x for x in options if x[2] == best])[1])
    return out


# ---- multiplication ---------------------------------------------------------------------------
def mul_near_limit(form: str, a: int, b: int) -> int:
    return max(a, b, 2) if form == "R" else 2


def mul_needs_twin(form: str, a: int, b: int) -> bool:
    return form == "R" and max(a, b) >= 11 and a * b >= 20


def mul_candidates(form: str, a: int, b: int) -> list:
    """(key, value) pairs; the first key wins a duplicate value; never the answer."""
    p = a * b
    raw = []
    if form == "R":
        for v in (a * (b + 1), (a + 1) * b, a * (b - 1), (a - 1) * b):
            raw.append(("GROUP_OFF", v))
        raw.append(("ADDED", a + b))
        if max(a, b) >= 11:
            hi, lo = max(a, b), min(a, b)
            if lo >= 10:
                raw.append(("PARTIAL_PRODUCTS", (a // 10) * (b // 10) * 100 + (a % 10) * (b % 10)))
            elif (hi % 10) * lo >= 10:
                raw.append(("DROPPED_CARRY", p - 10))
            raw.append(("TENS_SLIP", p - 10))
            raw.append(("TENS_SLIP", p + 10))
        ans = p
    else:
        m = answer_of("mul", form, a, b)
        k = b if form == "S" else a
        raw.append(("MISSING_ONE_OFF", m + 1))
        raw.append(("MISSING_ONE_OFF", m - 1))
        raw.append(("MISSING_SUBTRACTED", p - k))
        raw.append(("MISSING_PRODUCT", p))
        ans = m
    out, seen = [], {ans}
    for key, v in raw:
        if 0 <= v <= MAX_WRONG and v not in seen:
            seen.add(v)
            out.append((key, v))
    return out


def mul_fill(form: str, a: int, b: int, taken: set) -> list:
    ans = answer_of("mul", form, a, b)
    out = []
    for d in (1, 2, 3):
        for v in (ans - d, ans + d):
            if 0 <= v <= MAX_WRONG and v != ans and v not in taken:
                out.append(("ARITH", v))
    return out


MUL_WEIGHT = {"GROUP_OFF": 3, "ADDED": 4, "DROPPED_CARRY": 4, "TENS_SLIP": 3, "PARTIAL_PRODUCTS": 4,
              "MISSING_ONE_OFF": 3, "MISSING_SUBTRACTED": 4, "MISSING_PRODUCT": 2, "ARITH": 0}
MUL_WEIGHT_FLAG = dict(MUL_WEIGHT, ADDED=2, MISSING_SUBTRACTED=2, MISSING_PRODUCT=4)


def mul_plan(form: str, a: int, b: int, rng: random.Random) -> dict:
    ans = answer_of("mul", form, a, b)
    pool = mul_candidates(form, a, b)
    pool = pool + mul_fill(form, a, b, {v for _, v in pool})
    limit = mul_near_limit(form, a, b)
    twin = mul_needs_twin(form, a, b)
    weight = MUL_WEIGHT_FLAG if rng.random() < 0.4 else MUL_WEIGHT
    best: dict = {}
    for combo in itertools.combinations(pool, 3):
        vals = [v for _, v in combo]
        if sum(1 for v in vals if abs(v - ans) <= limit) < 2:
            continue
        if twin and not any(v % 10 == ans % 10 for v in vals):
            continue
        rank = sum(1 for v in vals if v < ans)
        score = sum(weight[k] for k, _ in combo)
        cur = best.get(rank)
        if cur is None or score > cur[0]:
            best[rank] = (score, [combo])
        elif score == cur[0]:
            cur[1].append(combo)
    return {r: [(v, k) for k, v in opts[rng.randrange(len(opts))]] for r, (_, opts) in best.items()}


# ---- division ---------------------------------------------------------------------------------
def div_wrong_value(form: str, key: str, a: int, b: int, sign: int = 1, size: int = 1):
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


def div_near_tol(form: str, a: int, b: int) -> int:
    return max(a, b) if form == "S" else 2


def div_candidates(form: str, a: int, b: int) -> dict:
    """value -> (key, 'near' | 'far')."""
    ans = answer_of("div", form, a, b)
    tol = div_near_tol(form, a, b)
    out: dict = {}

    def add(v, key):
        if v is None or v < 0 or v > MAX_WRONG or v == ans or v in out:
            return
        out[v] = (key, "near" if abs(v - ans) <= tol else "far")

    if form == "R":
        for size in (1, 2):
            for sign in (1, -1):
                add(div_wrong_value("R", "GROUP_OFF", a, b, sign, size), "GROUP_OFF")
        add(div_wrong_value("R", "SUBTRACTED", a, b), "SUBTRACTED")
        add(div_wrong_value("R", "MULTIPLIED", a, b), "MULTIPLIED")
        for sign in (1, -1):
            add(div_wrong_value("R", "TENS_SLIP", a, b, sign), "TENS_SLIP")
        for d in (3, -3):
            add(ans + d, "ARITH")
    elif form == "C":
        for sign in (1, -1):
            add(div_wrong_value("C", "MISSING_ONE_OFF", a, b, sign), "MISSING_ONE_OFF")
        add(div_wrong_value("C", "MISSING_SUBTRACTED", a, b), "MISSING_SUBTRACTED")
        add(div_wrong_value("C", "MISSING_MULTIPLIED", a, b), "MISSING_MULTIPLIED")
        for d in (2, -2, 3, -3):
            add(ans + d, "ARITH")
    else:
        for sign in (1, -1):
            add(div_wrong_value("S", "START_GROUP_OFF", a, b, sign), "START_GROUP_OFF")
        add(div_wrong_value("S", "START_ADDED", a, b), "START_ADDED")
        for sign in (1, -1):
            add(div_wrong_value("S", "START_TENS", a, b, sign), "START_TENS")
        for d in (b, -b, 1, -1, 2, -2):
            add(ans + d, "ARITH")
    return out


DIV_WEIGHT = {"ARITH": 1.0}


def div_needs_twin(form: str, a: int, b: int) -> bool:
    return form == "S" and max(a, b) >= 11 and a * b >= 20


def div_combos(form: str, a: int, b: int, need_tens: bool) -> dict:
    ans = answer_of("div", form, a, b)
    cand = div_candidates(form, a, b)
    res: dict = {}
    for trio in itertools.combinations(sorted(cand), 3):
        kinds = [cand[v][1] for v in trio]
        if sum(1 for k in kinds if k == "near") < 2 or sum(1 for k in kinds if k == "far") > 1:
            continue
        if need_tens and not any(cand[v][0] == "START_TENS" for v in trio):
            continue
        rank = sum(1 for v in trio if v < ans)
        score = sum(DIV_WEIGHT.get(cand[v][0], 2.0) for v in trio)
        res.setdefault(rank, []).append((score, [(v, cand[v][0]) for v in trio]))
    return res


def div_plan(form: str, a: int, b: int, rng: random.Random) -> dict:
    combos = div_combos(form, a, b, div_needs_twin(form, a, b))
    if not combos:  # cannot honour the twin requirement: relax it
        combos = div_combos(form, a, b, False)
    out = {}
    for r in sorted(combos):
        pool = sorted(((s + rng.random() * 2.0, t) for s, t in combos[r]), key=lambda x: -x[0])
        out[r] = pool[0][1]
    return out


def plan_of(op: str, hi: int, n: int, form: str, a: int, b: int, rng: random.Random) -> dict:
    if op == "add":
        return add_plan(hi, form, a, b, rng)
    if op == "sub":
        return sub_plan(form, a, b, rng)
    if op == "mul":
        return mul_plan(form, a, b, rng)
    return div_plan(form, a, b, rng)


# =================================================================================================
# Explanations: the fact and one reusable strategy (<= 160)
# =================================================================================================
def tens(n: int) -> str:
    return f"{n} ten" if n == 1 else f"{n} tens"


def add_explain_r(a: int, b: int) -> str:
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


def add_explain_missing(form: str, a: int, b: int) -> str:
    s = a + b
    m, k = (b, a) if form == "C" else (a, b)
    head = f"{prompt_of('add', form, a, b)}: {a} + {b} = {s}, so ? = {m}."
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


def sub_explanation_r(s: int, a: int, rng: random.Random) -> str:
    b = s - a
    head = f"{s} {MINUS} {a} = {b}"
    if a == 0:
        return f"{head}: taking away nothing leaves {s}."
    if b == 0:
        return f"{head}: take away all {s} and nothing is left."
    if a <= 2 and s <= 20:
        return f"{head}: count back {a} from {s}. Check: {b} + {a} = {s}."
    if a == b and s <= 20:
        return f"{head} because double {a} is {s}."
    if s <= 10:
        return f"{head} because {a} + {b} = {s}."
    if s % 10 == 0 and a < 10:
        return f"{head}: 10 {MINUS} {a} = {10 - a}, so {s - 10} + {10 - a} = {b}."
    if s <= 20:
        if a < 10 and regroups(a, b):
            down = s % 10
            return f"{s} {MINUS} {a}: take {down} to get 10, then take {a - down} more: {b}. Check: {a} + {b} = {s}."
        return f"{head} because {a} + {b} = {s}."
    if a < 10:
        if regroups(a, b):
            down = s % 10
            return f"{s} {MINUS} {a}: take {down} to get {s - down}, then take {a - down} more: {b}."
        return f"{head}: the ones are {s % 10} {MINUS} {a} = {s % 10 - a}, the tens stay."
    if a % 10 == 0:
        return f"{head}: {tens(s // 10)} {MINUS} {tens(a // 10)} = {tens(b // 10)}, plus {s % 10}."
    tens_a, ones_a = a - a % 10, a % 10
    if regroups(a, b) and b <= 20 and rng.random() < 0.5:
        return f"{s} {MINUS} {a}: count up from {a} to {s}, {b} steps. Check: {a} + {b} = {s}."
    return f"{s} {MINUS} {a}: {s} {MINUS} {tens_a} = {s - tens_a}, then {s - tens_a} {MINUS} {ones_a} = {b}."


def sub_explanation_c(s: int, a: int, rng: random.Random) -> str:
    b = s - a
    if a > 20 or rng.random() < 0.5:
        return f"{s} {MINUS} ? = {b}: {s} {MINUS} {a} = {b}, so ? = {a}. Think addition: {b} + {a} = {s}."
    return f"{s} {MINUS} ? = {b}: count up from {b} to {s}, that is {a}. So {s} {MINUS} {a} = {b}, ? = {a}."


def sub_explanation_s(s: int, a: int, rng: random.Random) -> str:
    b = s - a
    if rng.random() < 0.5:
        return f"? {MINUS} {a} = {b}: add back, {b} + {a} = {s}, so ? = {s}."
    return f"? {MINUS} {a} = {b}: undo the take away, {b} + {a} = {s}, so ? = {s}. Check: {s} {MINUS} {a} = {b}."


def mul_tail(a: int, b: int) -> str:
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


def mul_explain(form: str, a: int, b: int) -> str:
    p = a * b
    if form == "R":
        return f"{a} {MUL} {b} = {p}: " + mul_tail(a, b)
    m = answer_of("mul", form, a, b)
    k = b if form == "S" else a
    head = f"{prompt_of('mul', form, a, b)}: {a} {MUL} {b} = {p}, so ? = {m}. "
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


def div_explanation(form: str, a: int, b: int) -> str:
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


def explain(op: str, form: str, a: int, b: int, rng: random.Random) -> str:
    if op == "add":
        return add_explain_r(a, b) if form == "R" else add_explain_missing(form, a, b)
    if op == "sub":
        fn = {"R": sub_explanation_r, "C": sub_explanation_c, "S": sub_explanation_s}[form]
        return fn(a + b, a, rng)
    if op == "mul":
        return mul_explain(form, a, b)
    return div_explanation(form, a, b)


# =================================================================================================
# Tier assembly
# =================================================================================================
def prefixed(op: str, key):
    if key is None or key == "ARITH":
        return key
    return f"{op.upper()}_{key}"


def range_of(manifest: dict) -> int:
    return int(manifest["id"].rsplit("-", 1)[1])


def build_tier(r: int, tier: int, n: int, rng: random.Random):
    """One attempt at a tier of 4 x (n // 4) items, or None when the answer ranks do not balance."""
    hi, nd = PAIRING[r]
    per_op = n // 4
    picks = []
    for op in OPS:
        picks += draw(op, pools_of(op, hi, nd, tier), per_op, rng)
    rng.shuffle(picks)
    plans = []
    for op, form, a, b in picks:
        plan = plan_of(op, hi, nd, form, a, b, rng)
        if not plan:
            return None
        plans.append(plan)
    total = len(picks)
    order = sorted(range(total), key=lambda i: (len(plans[i]), rng.random()))
    counts = [0, 0, 0, 0]
    rank_of = {}
    for i in order:
        feas = sorted(plans[i])
        low = min(counts[x] for x in feas)
        x = rng.choice([y for y in feas if counts[y] == low])
        counts[x] += 1
        rank_of[i] = x
    if any(not (0.15 * total <= c <= 0.35 * total) for c in counts):
        return None
    positions = [i % 4 for i in range(total)]
    rng.shuffle(positions)
    items = []
    for i, (op, form, a, b) in enumerate(picks):
        wrong = list(plans[i][rank_of[i]])
        rng.shuffle(wrong)
        choices, keys = [], []
        w = iter(wrong)
        for slot in range(4):
            if slot == positions[i]:
                choices.append(str(answer_of(op, form, a, b)))
                keys.append(None)
            else:
                v, k = next(w)
                choices.append(str(v))
                keys.append(prefixed(op, k))
        items.append({
            "tier": tier,
            "prompt": prompt_of(op, form, a, b),
            "choices": choices,
            "answer": positions[i],
            "misconceptions": keys,
            "explanation": explain(op, form, a, b, rng),
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    r = range_of(manifest)
    n = manifest["items_per_tier"]
    if n % 4:
        raise ValueError("items_per_tier must be a multiple of 4")
    items = []
    for t in manifest["tiers"]:
        for _ in range(ATTEMPTS):
            built = build_tier(r, t["tier"], n, rng)
            if built is not None:
                items += built
                break
        else:
            raise ValueError(f"tier {t['tier']}: no draw met the rank balance in {ATTEMPTS} attempts")
    return items
