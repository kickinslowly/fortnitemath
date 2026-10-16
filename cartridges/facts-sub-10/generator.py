"""Procedural generator for the facts-sub-<range> cartridges (fnm-cart/1): one file, byte-identical in
facts-sub-10, -20, -50 and -100; the range comes from the id (``int(manifest["id"].rsplit("-", 1)[1])``).

Subtraction reads the addition pools backwards: the pair (a, b) is the fact ``s - a = b`` with s = a + b.
Three prompt forms read one pair:
  R  ``s - a = ?``  -> b      C  ``s - ? = b``  -> a      S  ``? - a = b``  -> s
A tier is a list of PARTS (form, pairs, at_least); the tier draws ITEMS prompts from the union of its parts such
that at least ``at_least`` items lie in each part (floors filled in list order, the rest drawn from the union).
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges (PROTOCOL 4c).

Per item: every wrong value a modelled misconception gives (``ARITH`` only to fill), the valid triples (at least
two near, at most one far, a ones-digit twin where the answer is 20 or more), the answer's rank by value spread
round-robin per tier, then answer positions round-robin and shuffled.
"""
from __future__ import annotations

import itertools
import random

MINUS = "−"
MAX_CHOICE = 999
NEAR = (1, 2, 10)


# ------------------------------------------------------------------------------------------------ pools
def ten_count(n: int) -> str:
    """'1 ten', '3 tens', '0 tens'."""
    return f"{n} ten" if n == 1 else f"{n} tens"


def regroups(a: int, b: int) -> bool:
    """The ones of a and b make a ten (read backwards: the ones of s are smaller than the ones of a: a trade)."""
    return a % 10 + b % 10 >= 10


def is_tens(a: int, b: int) -> bool:
    """An operand is a non-zero multiple of 10."""
    return (a > 0 and a % 10 == 0) or (b > 0 and b % 10 == 0)


def pairs_for(lo: int, hi: int, low: int = 0) -> list:
    """Every (a, b) with lo <= a + b <= hi and a, b >= low."""
    return [(a, b) for s in range(lo, hi + 1) for a in range(low, s - low + 1) for b in [s - a]]


def parts_10() -> dict:
    p = pairs_for(1, 10)
    make_ten = [(a, 10 - a) for a in range(1, 10)]
    return {
        1: [("R", [x for x in p if min(x) <= 2], 0)],
        2: [("R", [x for x in p if min(x) >= 2], 0)],
        3: [("R", [x for x in p if min(x) >= 3], 8), ("C", make_ten, 4), ("S", make_ten, 4)],
        4: [("C", [x for x in p if min(x) >= 1], 0)],
        5: [("S", pairs_for(5, 10, 2), 12), ("C", pairs_for(5, 10, 2), 0)],
    }


def parts_20() -> dict:
    p = pairs_for(11, 20, 1)
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


def parts_big(lo: int, hi: int) -> dict:
    """Sums 21-50 and 51-100."""
    p = pairs_for(lo, hi, 2)
    plain = [x for x in p if not is_tens(*x)]
    two_one = lambda xs: [x for x in xs if min(x) <= 9]
    no_reg = [x for x in plain if not regroups(*x)]
    reg = [x for x in plain if regroups(*x)]
    return {
        1: [("R", [x for x in pairs_for(lo, hi, 1) if is_tens(*x)], 0)],
        2: [("R", two_one(no_reg), 8), ("R", [x for x in no_reg if min(x) >= 10], 8)],
        3: [("R", two_one(reg), 8), ("R", [x for x in reg if min(x) >= 10], 8)],
        4: [("C", reg, 12), ("C", plain, 0)],
        5: [("S", reg, 6), ("S", plain, 12), ("C", reg, 6), ("C", plain, 0)],
    }


PARTS = {10: parts_10, 20: parts_20, 50: lambda: parts_big(21, 50), 100: lambda: parts_big(51, 100)}


def pick_prompts(parts: list, count: int, rng: random.Random) -> list:
    """Fill each part's floor in list order, then draw the rest from the union. Returns [(form, (a, b))]."""
    chosen, seen = [], set()
    for form, pairs, need in parts:
        members = set(pairs)
        have = sum(1 for f, x in chosen if f == form and x in members)
        usable = [(form, x) for x in pairs if (form, x) not in seen]
        take = max(0, need - have)
        if len(usable) < take:
            raise RuntimeError(f"part {form} cannot reach its floor {need}")
        for item in rng.sample(usable, take):
            chosen.append(item)
            seen.add(item)
    union, listed = [], set(seen)
    for form, pairs, _ in parts:
        for x in pairs:
            if (form, x) not in listed:
                listed.add((form, x))
                union.append((form, x))
    chosen += rng.sample(union, count - len(chosen))
    return chosen


# ------------------------------------------------------------------------------------------------ wrong values
def smaller_from_larger(s: int, a: int) -> int:
    """Each place: larger digit minus smaller digit (14 - 6 -> 12, 52 - 38 -> 26)."""
    out, place = 0, 1
    while s or a:
        out += abs(s % 10 - a % 10) * place
        s //= 10
        a //= 10
        place *= 10
    return out


def answer_of(form: str, a: int, b: int) -> int:
    return {"R": b, "C": a, "S": a + b}[form]


def wrong_candidates(form: str, a: int, b: int):
    """Ordered list of (value, key): every wrong value a modelled misconception gives, then ARITH fill.
    When two keys give one value, the key listed first wins; a key that yields the answer is dropped."""
    s = a + b
    ans = answer_of(form, a, b)
    cands = []

    def add(v, key):
        if v < 0 or v > MAX_CHOICE or v == ans or any(v == c[0] for c in cands):
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


def is_near(v: int, ans: int) -> bool:
    return abs(v - ans) in NEAR


def valid_sets(form: str, a: int, b: int):
    """Every valid triple of wrong candidates, as (rank_of_answer, ((v, key), ...), arith_count)."""
    ans = answer_of(form, a, b)
    out = []
    for trio in itertools.combinations(wrong_candidates(form, a, b), 3):
        vals = [v for v, _ in trio]
        if sum(1 for v in vals if is_near(v, ans)) < 2:
            continue
        if sum(1 for v in vals if not is_near(v, ans)) > 1:
            continue
        if ans >= 20 and not any(v % 10 == ans % 10 for v in vals):
            continue
        out.append((sum(1 for v in vals if v < ans), trio, sum(1 for _, k in trio if k == "ARITH")))
    return out


# ------------------------------------------------------------------------------------------------ text
def explanation_r(s: int, a: int, rng: random.Random) -> str:
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
        return f"{head}: {ten_count(s // 10)} {MINUS} {ten_count(a // 10)} = {ten_count(b // 10)}, plus {s % 10}."
    tens, ones = a - a % 10, a % 10
    if regroups(a, b) and b <= 20 and rng.random() < 0.5:
        return f"{s} {MINUS} {a}: count up from {a} to {s}, {b} steps. Check: {a} + {b} = {s}."
    return f"{s} {MINUS} {a}: {s} {MINUS} {tens} = {s - tens}, then {s - tens} {MINUS} {ones} = {b}."


def explanation_c(s: int, a: int, rng: random.Random) -> str:
    b = s - a
    if a > 20 or rng.random() < 0.5:
        return f"{s} {MINUS} ? = {b}: {s} {MINUS} {a} = {b}, so ? = {a}. Think addition: {b} + {a} = {s}."
    return f"{s} {MINUS} ? = {b}: count up from {b} to {s}, that is {a}. So {s} {MINUS} {a} = {b}, ? = {a}."


def explanation_s(s: int, a: int, rng: random.Random) -> str:
    b = s - a
    if rng.random() < 0.5:
        return f"? {MINUS} {a} = {b}: add back, {b} + {a} = {s}, so ? = {s}."
    return f"? {MINUS} {a} = {b}: undo the take away, {b} + {a} = {s}, so ? = {s}. Check: {s} {MINUS} {a} = {b}."


def prompt_of(form: str, a: int, b: int) -> str:
    s = a + b
    return {"R": f"{s} {MINUS} {a} = ?", "C": f"{s} {MINUS} ? = {b}", "S": f"? {MINUS} {a} = {b}"}[form]


# ------------------------------------------------------------------------------------------------ tiers
def _balanced(n: int, k: int, rng: random.Random):
    out = [i % k for i in range(n)]
    rng.shuffle(out)
    return out


def gen_tier(rng_range: int, tier: int, count: int, rng: random.Random):
    prompts = pick_prompts(PARTS[rng_range]()[tier], count, rng)
    rng.shuffle(prompts)
    sets = [valid_sets(f, x[0], x[1]) for f, x in prompts]
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
    for i, (form, (a, b)) in enumerate(prompts):
        ans = answer_of(form, a, b)
        options = [x for x in sets[i] if x[0] == ranks[i]]
        best = min(x[2] for x in options)
        _, trio, _ = rng.choice([x for x in options if x[2] == best])
        wrong = list(trio)
        rng.shuffle(wrong)
        choices, keys = [], []
        for slot in range(4):
            if slot == positions[i]:
                choices.append(str(ans))
                keys.append(None)
            else:
                v, k = wrong.pop()
                choices.append(str(v))
                keys.append(k)
        expl = {"R": explanation_r, "C": explanation_c, "S": explanation_s}[form](a + b, a, rng)
        items.append({
            "tier": tier,
            "prompt": prompt_of(form, a, b),
            "choices": choices,
            "answer": positions[i],
            "misconceptions": keys,
            "explanation": expl,
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    rng_range = int(manifest["id"].rsplit("-", 1)[1])
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(rng_range, t["tier"], n, rng))
    return items
