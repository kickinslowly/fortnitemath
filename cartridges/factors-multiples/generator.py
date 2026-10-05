"""Procedural generator for the factors-multiples cartridge (fnm-cart/1, CCSS 6.NS.B.4).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4
shape without ``id``. Stdlib only, deterministic for a given ``rng``, imports no other cartridge.

Tiers
-----
1. Factors & Primes: "Which is a factor of 36?", "Which is a multiple of 6?", "Which is prime?"
   (eight phrasings), "How many factors does 12 have?".
2. GCF of two numbers a = g·p, b = g·q (g, p, q <= 10, p and q share no factor).
3. LCM of two or three numbers 2..10, LCM <= 60.
4. Factor out the GCF: "Factor out the GCF: 18 + 24" -> ``6(3 + 4)``, and "18 + 24 = 6(? + ?)"
   -> ``3 + 4``. Every choice has a different VALUE (g·(x + y), or x + y), so a choice like
   ``3(6 + 8)`` (equal in value, right form, wrong factor) is never offered: the player must never
   face two right doors. NOT_GREATEST appears in the second form as ``6 + 8`` (divided by 3).
5. GCF-or-LCM story problems; WRONG_TOOL (the other tool's value) is always a door.

Every wrong value comes from a modelled misconception (``rules_*``) first; ``ARITH`` only fills.
Each kind has an ``is_right`` predicate and every wrong choice is asserted not to satisfy it, so
exactly one door is right.
"""
from __future__ import annotations

import random
from math import gcd

MAX_FACTOR = 10  # §4a: factors and divisors 2..10
MAX_LCM = 60  # LCM answers stay skip-countable
MAX_DISTRACTOR = 999
ODD_COMPOSITES = (9, 15, 21, 25, 27, 35, 45, 49)  # every one a times-table fact
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)
COUNT_NUMBERS = (6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 24, 25, 27, 28, 30, 32, 35, 36)
PRIME_PROMPTS = (
    "Which is prime?",
    "Which number is prime?",
    "Which of these is prime?",
    "Pick the prime number.",
    "Find the prime.",
    "Only one of these is prime. Which?",
    "Which has exactly two factors?",
    "Which number is a prime number?",
)


def lcm(a: int, b: int) -> int:
    return a * b // gcd(a, b)


def factors(n: int) -> list:
    return [d for d in range(1, n + 1) if n % d == 0]


def is_prime(n: int) -> bool:
    return n >= 2 and all(n % d for d in range(2, n))


def proper_common_factors(g: int) -> list:
    """Common factors of a and b strictly between 1 and their GCF g = the divisors of g."""
    return [d for d in range(2, g) if g % d == 0]


# ---------------------------------------------------------------------------------------------
# Item assembly
# ---------------------------------------------------------------------------------------------
def build(tier, prompt, correct, rule_values, arith, is_right, pos, rng, expl,
          fmt=str, key=lambda v: v, must_keep=()):
    """rule_values: [(label, value)] in preference order; arith: candidate fillers.

    Distinctness is by ``key`` (the value a choice stands for), so no two doors are equal in
    value. Returns None when the item cannot be completed."""
    assert is_right(correct)
    seen = {key(correct)}
    wrong = []
    for lab, v in rule_values:
        if v is None or key(v) in seen or is_right(v):
            continue
        seen.add(key(v))
        wrong.append((lab, v))
    if not wrong:
        return None
    if len(wrong) > 3:
        keep = [w for w in wrong if w[0] in must_keep]
        rest = [w for w in wrong if w[0] not in must_keep]
        rng.shuffle(rest)
        chosen = (keep + rest)[:3]
        wrong = [w for w in wrong if w in chosen]
    for v in arith:
        if len(wrong) == 3:
            break
        if key(v) in seen or is_right(v):
            continue
        seen.add(key(v))
        wrong.append(("ARITH", v))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:pos] + [(None, correct)] + wrong[pos:]
    choices = [fmt(v) for _, v in pairs]
    if (len(prompt) > 60 or len(expl) > 160 or any(len(c) > 14 for c in choices)
            or len(set(choices)) != len(choices)):
        return None
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": choices,
        "answer": pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


def _near(v: int, rng, spread=(1, 2, 3)) -> list:
    out = [v + s * d for d in spread for s in (1, -1)]
    rng.shuffle(out)
    return [x for x in out if 1 <= x <= MAX_DISTRACTOR]


def _join(xs) -> str:
    xs = [str(x) for x in xs]
    return ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else xs[0]


# ---------------------------------------------------------------------------------------------
# Misconception rules: pure functions, label -> every value that wrong rule can produce (in
# preference order). The tests pin these with hand-worked golden cases.
# ---------------------------------------------------------------------------------------------
def factor_rules(n: int) -> dict:
    """'Which is a factor of n?'"""
    return {
        "MULTIPLE_FOR_FACTOR": [2 * n],
        "SHARES_FACTOR": [c for c in range(2, 13) if n % c and gcd(c, n) > 1],
    }


def multiple_rules(m: int, ans: int) -> dict:
    """'Which is a multiple of m?' (ans = the right multiple, which centres the near misses)."""
    return {
        "FACTOR_FOR_MULTIPLE": proper_common_factors(m),
        "SAME_LAST_DIGIT": ([d for d in range(10 + m, 100, 10) if d % m] if m < 10 else []),
        "SHARES_FACTOR": [c for c in range(max(10, ans - 15), min(100, ans + 15))
                          if c % m and gcd(c, m) > 1],
    }


def prime_rules() -> dict:
    return {"ONE_IS_PRIME": [1], "ODD_IS_PRIME": list(ODD_COMPOSITES)}


def count_rules(n: int) -> dict:
    c = len(factors(n))
    root = int(round(n ** 0.5))
    return {
        "FORGOT_ONE_AND_SELF": [c - 2],
        "PAIRS_ONLY": [(c + 1) // 2],
        "SQUARE_TWICE": [c + 1] if root * root == n else [],
    }


def gcf_rules(a: int, b: int) -> dict:
    g = gcd(a, b)
    return {
        "LCM_FOR_GCF": [lcm(a, b)],
        "NOT_GREATEST": proper_common_factors(g),
        "SMALLER_NUMBER": [min(a, b)] if min(a, b) != g else [],
    }


def lcm_rules(nums) -> dict:
    prod, g, L = 1, 0, 1
    for x in nums:
        prod, g, L = prod * x, gcd(g, x), lcm(L, x)
    k = 2
    while L * k == prod:
        k += 1
    return {
        "PRODUCT": [prod] if prod != L else [],
        "GCF_FOR_LCM": [g] if g > 1 else [],
        "LARGER_NUMBER": [max(nums)] if max(nums) != L else [],
        "NOT_LEAST": [L * k],
    }


def factor_out_rules(a: int, b: int) -> dict:
    """'a + b = g(? + ?)': values are (x, y) insides; the full form prefixes g."""
    g = gcd(a, b)
    return {
        "NOT_GREATEST": [(a // d, b // d) for d in proper_common_factors(g)],
        "SUBTRACTED_GCF": [(a - g, b - g)],
        "ONE_TERM": [(a // g, b), (a, b // g)],
    }


def story_rules(a: int, b: int, use_lcm: bool) -> dict:
    if use_lcm:
        return {"WRONG_TOOL": [gcd(a, b)], **lcm_rules((a, b))}
    r = gcf_rules(a, b)
    return {"WRONG_TOOL": r.pop("LCM_FOR_GCF"), **r}


def free(arith, rules: dict, key=lambda v: v) -> list:
    """ARITH candidates that no modelled rule produces (else the label would lie)."""
    taken = {v for vals in rules.values() for v in vals}
    return [v for v in arith if key(v) not in taken]


def pick(rules: dict, rng, many=None) -> list:
    """[(label, value)]: one value per label (``many[label]`` values for list labels)."""
    many = many or {}
    out = []
    for lab, vals in rules.items():
        vals = list(vals)
        rng.shuffle(vals)
        out += [(lab, v) for v in vals[:many.get(lab, 1)]]
    return out


# ---------------------------------------------------------------------------------------------
# Tier 1: factors, multiples, primes, factor counts
# ---------------------------------------------------------------------------------------------
def t1_factor(rng, pos):
    f, k = rng.randint(2, MAX_FACTOR), rng.randint(2, MAX_FACTOR)
    n = f * k
    rules = factor_rules(n)
    if len(rules["SHARES_FACTOR"]) < 2:
        return None
    arith = free([c for c in range(2, 13) if n % c and gcd(c, n) == 1], rules)
    rng.shuffle(arith)
    expl = f"{n} ÷ {f} = {k}, so {f} is a factor of {n}."
    return build(1, f"Which is a factor of {n}?", f, pick(rules, rng, {"SHARES_FACTOR": 2}),
                 arith, lambda v: n % v == 0, pos, rng, expl)


def t1_multiple(rng, pos, m):
    k = rng.randint(2, MAX_FACTOR)
    ans = m * k
    if ans < 10:
        return None
    right = lambda v: v % m == 0
    all_rules = multiple_rules(m, ans)
    rules = pick(all_rules, rng, {"SAME_LAST_DIGIT": 2, "SHARES_FACTOR": 2})
    arith = free([v for v in _near(ans, rng) if not right(v)], all_rules)
    expl = f"{m} × {k} = {ans}, so {ans} is a multiple of {m}."
    return build(1, f"Which is a multiple of {m}?", ans, rules, arith, right, pos, rng, expl)


def t1_prime(rng, pos, prompt):
    p = rng.choice(PRIMES)
    rules = pick(prime_rules(), rng, {"ODD_IS_PRIME": 3})
    if rng.random() < 0.5:
        rules = rules[1:]  # three odd composites, no 1
    expl = f"{p} has only two factors, 1 and {p}, so {p} is prime."
    return build(1, prompt, p, rules, [], is_prime, pos, rng, expl)


def t1_count(rng, pos, n):
    fs = factors(n)
    c = len(fs)
    arith = free([v for v in _near(c, rng, (1, 2)) if v >= 2], count_rules(n))
    expl = f"Factors of {n}: {', '.join(map(str, fs))}. That's {c}."
    return build(1, f"How many factors does {n} have?", c, pick(count_rules(n), rng), arith,
                 lambda v: v == c, pos, rng, expl)


# ---------------------------------------------------------------------------------------------
# GCF pairs (tiers 2, 4, 5)
# ---------------------------------------------------------------------------------------------
def gcf_pair(rng, allow_one=False, composite_bias=0.7):
    """(g, p, q) with a = g·p, b = g·q, p and q share no factor and differ."""
    if rng.random() < composite_bias:
        g = rng.choice((4, 6, 8, 9, 10))
    else:
        g = rng.choice((2, 3, 5, 7))
    lo = 1 if allow_one else 2
    p, q = rng.randint(lo, MAX_FACTOR), rng.randint(2, MAX_FACTOR)
    if p == q or gcd(p, q) != 1:
        return None
    if rng.random() < 0.5:
        p, q = q, p
    return g, p, q


def gcf_expl(a, b, g, p, q) -> str:
    return f"{a} = {g} × {p}, {b} = {g} × {q}. {p} and {q} share no factor, so GCF = {g}."


def t2_gcf(rng, pos):
    got = gcf_pair(rng, allow_one=rng.random() < 0.15)
    if not got:
        return None
    g, p, q = got
    a, b = g * p, g * q
    # ARITH must not be a common factor (that is NOT_GREATEST)
    arith = free([v for v in _near(g, rng) if a % v or b % v], gcf_rules(a, b))
    return build(2, f"GCF of {a} and {b}?", g, pick(gcf_rules(a, b), rng), arith,
                 lambda v: v == g, pos, rng, gcf_expl(a, b, g, p, q))


# ---------------------------------------------------------------------------------------------
# Tier 3: LCM
# ---------------------------------------------------------------------------------------------
def lcm_expl(nums, L) -> str:
    big = max(nums)
    others = [x for x in nums if x != big]
    mult = ", ".join(str(big * i) for i in range(1, L // big + 1))
    return f"Multiples of {big}: {mult}. {L} is a multiple of {_join(others)} too, so LCM = {L}."


def t3_lcm(rng, pos, three):
    if three:
        nums = sorted(rng.sample(range(2, MAX_FACTOR + 1), 3))
        L = lcm(lcm(nums[0], nums[1]), nums[2])
        if L == nums[2]:
            return None
    else:
        nums = sorted(rng.sample(range(2, MAX_FACTOR + 1), 2))
        L = lcm(*nums)
    if L > MAX_LCM:
        return None
    arith = free([v for v in _near(L, rng, (1, 2)) if any(v % x for x in nums)],
                 lcm_rules(nums))
    return build(3, f"LCM of {_join(nums)}?", L, pick(lcm_rules(nums), rng), arith,
                 lambda v: v == L, pos, rng, lcm_expl(nums, L))


# ---------------------------------------------------------------------------------------------
# Tier 4: factor out the GCF
# ---------------------------------------------------------------------------------------------
def fmt_form(v) -> str:
    g, x, y = v
    return f"{g}({x} + {y})"


def fmt_sum(v) -> str:
    x, y = v
    return f"{x} + {y}"


def t4(rng, pos, form):
    got = gcf_pair(rng)
    if not got:
        return None
    g, p, q = got
    a, b = g * p, g * q
    all_rules = factor_out_rules(a, b)
    rules = pick(all_rules, rng)
    expl = (f"{a} = {g} × {p}, {b} = {g} × {q}. GCF {g}; {p} and {q} share no factor. "
            f"{a} + {b} = {g}({p} + {q}).")
    arith = [(p + d, q) for d in (1, -1)] + [(p, q + d) for d in (1, -1)]
    rng.shuffle(arith)
    arith = free([v for v in arith if v[0] >= 1 and v[1] >= 1], all_rules)
    if form == "full":
        # NOT_GREATEST's full form d(a/d + b/d) EQUALS a + b in value: never a door here.
        rules = [(lab, (g,) + v) for lab, v in rules if lab != "NOT_GREATEST"]
        return build(4, f"Factor out the GCF: {a} + {b}", (g, p, q), rules,
                     [(g,) + v for v in arith],
                     lambda v: v[0] == gcd(a, b) and v[0] * v[1] == a and v[0] * v[2] == b,
                     pos, rng, expl, fmt=fmt_form, key=lambda v: v[0] * (v[1] + v[2]))
    return build(4, f"{a} + {b} = {g}(? + ?)", (p, q), rules, arith,
                 lambda v: g * v[0] == a and g * v[1] == b,
                 pos, rng, expl, fmt=fmt_sum, key=lambda v: v[0] + v[1],
                 must_keep=("NOT_GREATEST",))


# ---------------------------------------------------------------------------------------------
# Tier 5: GCF or LCM? (stories)
# ---------------------------------------------------------------------------------------------
LCM_STORIES = (  # (template, unit)
    ("Hot dogs come in {a}s, buns in {b}s. Fewest of each to match?", ""),
    ("Cups stack in {a}s, lids in {b}s. Fewest of each to match?", ""),
    ("Two lights flash now, then every {a} s and {b} s. Next together?", "s"),
    ("Bus A comes every {a} min, bus B every {b}. Both now. Next both?", "min"),
    ("Ana laps in {a} min, Ben in {b} min. Both at start again in?", "min"),
)
GCF_STORIES = (
    ("{a} red, {b} blue beads. Most identical bags, none left?", ""),
    ("{a} boys, {b} girls in identical teams. Most teams?", ""),
    ("{a} pens, {b} pads into identical kits, none left. Most kits?", ""),
    ("Cut {a} m and {b} m ropes into equal pieces, no waste. Longest?", "m"),
)


def t5(rng, pos, use_lcm, story):
    tmpl, unit = story
    fmt = (lambda v: f"{v} {unit}") if unit else str
    if use_lcm:
        a, b = rng.sample(range(2, MAX_FACTOR + 1), 2)
        L, g = lcm(a, b), gcd(a, b)
        if L > MAX_LCM or g == 1 or L in (a, b):
            return None
        ans = L
        arith = [v for v in _near(L, rng, (1, 2)) if v % a or v % b]
        expl = f"Matching needs a common multiple of {a} and {b}. The least one is {fmt(L)}."
    else:
        got = gcf_pair(rng)
        if not got:
            return None
        g, p, q = got
        a, b = g * p, g * q
        ans = g
        arith = [v for v in _near(g, rng) if a % v or b % v]
        expl = (f"Equal sharing needs a common factor of {a} and {b}. "
                f"{a} = {g} × {p}, {b} = {g} × {q}: GCF {fmt(g)}.")
    all_rules = story_rules(a, b, use_lcm)
    return build(5, tmpl.format(a=a, b=b), ans, pick(all_rules, rng), free(arith, all_rules),
                 lambda v: v == ans, pos, rng, expl, fmt=fmt, must_keep=("WRONG_TOOL",))


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def _balanced(count: int, k: int, rng) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def tier_plan(tier: int, count: int, rng) -> list:
    """One zero-arg factory key per item slot."""
    if tier == 1:
        plan = ([("prime", s) for s in PRIME_PROMPTS]
                + [("multiple", m) for m in (3, 4, 6, 7, 8, 9, 10)]
                + [("count", n) for n in rng.sample(COUNT_NUMBERS, 10)])
        plan += [("factor", None)] * (count - len(plan))
    elif tier == 2:
        plan = [("gcf", None)] * count
    elif tier == 3:
        plan = [("lcm", False)] * (count - 12) + [("lcm", True)] * 12
    elif tier == 4:
        plan = [("t4", "full")] * (count // 2) + [("t4", "inside")] * (count - count // 2)
    else:
        plan = ([("t5", (True, LCM_STORIES[i % len(LCM_STORIES)])) for i in range(count // 2)]
                + [("t5", (False, GCF_STORIES[i % len(GCF_STORIES)]))
                   for i in range(count - count // 2)])
    rng.shuffle(plan)
    return plan


def make(kind, arg, rng, pos):
    if kind == "factor":
        return t1_factor(rng, pos)
    if kind == "multiple":
        return t1_multiple(rng, pos, arg)
    if kind == "prime":
        return t1_prime(rng, pos, arg)
    if kind == "count":
        return t1_count(rng, pos, arg)
    if kind == "gcf":
        return t2_gcf(rng, pos)
    if kind == "lcm":
        return t3_lcm(rng, pos, arg)
    if kind == "t4":
        return t4(rng, pos, arg)
    return t5(rng, pos, *arg)


def gen_tier(tier: int, count: int, declared, rng, max_attempts: int = 200000) -> list:
    positions = _balanced(count, 4, rng)
    plan = tier_plan(tier, count, rng)
    items, prompts, pairs_seen = [], set(), set()
    attempts = 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        kind, arg = plan[len(items)]
        item = make(kind, arg, rng, positions[len(items)])
        if item is None or item["prompt"] in prompts:
            continue
        if any(m not in declared and m not in (None, "ARITH") for m in item["misconceptions"]):
            raise ValueError(f"undeclared misconception in {item}")
        nums = tuple(sorted(int(x) for x in _numbers(item["prompt"])))
        sig = (kind, nums)
        if tier in (2, 3, 4) and sig in pairs_seen:  # same numbers, other order: same question
            continue
        pairs_seen.add(sig)
        prompts.add(item["prompt"])
        items.append(item)
    return items


def _numbers(text: str) -> list:
    out, cur = [], ""
    for ch in text:
        if ch.isdigit():
            cur += ch
        elif cur:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def generate(manifest: dict, rng: random.Random) -> list:
    declared = set(manifest["misconceptions"])
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, declared, rng))
    return items
