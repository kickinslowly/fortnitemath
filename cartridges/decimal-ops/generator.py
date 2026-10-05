"""Procedural generator for the decimal-operations cartridge (fnm-cart/1, grade 6, 6.NS.B.3).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every number is an exact ``Fraction``; ``fmt`` writes it as a decimal with no trailing zeros, so two
  choices with different text always have different values (no ``0.5`` beside ``0.50``).
* Each misconception is a function of the prompt's operands that returns the value a student holding
  that wrong rule writes, or None where the rule does not apply. ``WRONG_RULES[tier]`` lists them in
  label priority: when two rules give the same value, the first one names it.
* Wrong choices come from those rules first; ``ARITH`` (one-column slips: ± one unit in the answer's
  last place or the place before) only fills the rest, and never equals any rule's value.
* §4b bounds (the manifest's ``bounds``): operands 0.01-10 with ≤ 2 places and ≤ 2 non-zero digits;
  + − answers ≤ 20 with at most one carry or borrow; × ÷ digit work inside the times tables.
"""
from __future__ import annotations

import random
from fractions import Fraction

ADD, SUB, MUL, DIV = "+", "−", "×", "÷"
MAX_DISTRACTOR = 999
PLACE_NAME = {1: "tenths", 2: "hundredths", 3: "thousandths"}


# ---------------------------------------------------------------------------------------------
# Number helpers
# ---------------------------------------------------------------------------------------------
def places(v: Fraction) -> int:
    """Fewest decimal places that write ``v`` exactly (raises if it does not terminate in 6)."""
    v = Fraction(v)
    for k in range(7):
        if (v * 10 ** k).denominator == 1:
            return k
    raise ValueError(f"{v} is not a short decimal")


def fixed(v: Fraction, k: int) -> str:
    """``v`` written with exactly ``k`` decimal places (``v`` must fit)."""
    n = v * 10 ** k
    if n.denominator != 1 or n < 0:
        raise ValueError(f"{v} does not fit {k} places")
    ip, fp = divmod(int(n), 10 ** k)
    return str(ip) if k == 0 else f"{ip}.{fp:0{k}d}"


def fmt(v: Fraction) -> str:
    """Display form: no trailing zeros, leading 0 before the point (0.75, 1.2, 12, 0.006)."""
    return fixed(Fraction(v), places(v))


def money(v: Fraction) -> str:
    return "$" + fixed(Fraction(v), 2)


def digits_of(v: Fraction) -> int:
    """The digits with the point removed: 0.35 -> 35, 4.5 -> 45, 0.06 -> 6, 3 -> 3."""
    return int(v * 10 ** places(v))


def nonzero_digits(v: Fraction) -> int:
    return sum(c not in "0." for c in fmt(v))


def dec(d: int, k: int) -> Fraction:
    return Fraction(d, 10 ** k)


def trunc(v: Fraction, k: int) -> Fraction:
    return Fraction(int(v * 10 ** k), 10 ** k)  # v >= 0, so int() floors


def carries(a: Fraction, b: Fraction, op: str) -> int:
    """Carries (+) or borrows (−) in column arithmetic on a and b written to hundredths."""
    x, y = int(a * 100), int(b * 100)
    n, c = 0, 0
    while x or y:
        dx, dy = x % 10, y % 10
        if op == ADD:
            c = 1 if dx + dy + c >= 10 else 0
        else:
            c = 1 if dx - dy - c < 0 else 0
        n += c
        x //= 10
        y //= 10
    return n


def correct_value(a: Fraction, op: str, b: Fraction) -> Fraction:
    return {ADD: a + b, SUB: a - b, MUL: a * b, DIV: a / b}[op]


# ---------------------------------------------------------------------------------------------
# Misconception rules: f(a, op, b, ctx) -> wrong value or None
# ctx: {"money": bool} for story prompts (money is shown with 2 places)
# ---------------------------------------------------------------------------------------------
def align_right(a, op, b, ctx):
    """Right-justified digits: 0.4 + 0.35 -> 4 + 35 = 39 hundredths; 4.5 − 2 -> 45 − 2 = 4.3."""
    pa, pb = places(a), places(b)
    if op not in (ADD, SUB) or pa == pb:
        return None
    ia, ib, p = digits_of(a), digits_of(b), max(pa, pb)
    v = ia + ib if op == ADD else ia - ib
    return dec(v, p) if v > 0 else None


def drop_place(a, op, b, ctx):
    """Drops the digit that has no partner: 0.4 + 0.35 -> 0.4 + 0.3 = 0.7."""
    pa, pb = places(a), places(b)
    if op not in (ADD, SUB) or pa == pb or min(pa, pb) == 0:
        return None
    p = min(pa, pb)
    v = correct_value(trunc(a, p), op, trunc(b, p))
    return v if v > 0 else None


def bring_down(a, op, b, ctx):
    """Empty top place: bring the bottom digit down. 0.6 − 0.25 -> 0.4 then 5 -> 0.45."""
    pa, pb = places(a), places(b)
    if op != SUB or pa >= pb:
        return None
    t = trunc(b, pa)
    if a - t < 0:
        return None
    return (a - t) + (b - t)


def decimal_as_whole(a, op, b, ctx):
    """Decimal parts added as whole numbers, no carry: 0.8 + 0.5 -> 0.13; 1.6 + 0.7 -> 1.13."""
    pa, pb = places(a), places(b)
    if op != ADD or pa != pb or pa == 0:
        return None
    wa, fa = divmod(digits_of(a), 10 ** pa)
    wb, fb = divmod(digits_of(b), 10 ** pb)
    s = fa + fb
    if s < 10 ** pa:
        return None  # no carry: the rule gives the right answer
    return wa + wb + dec(s, len(str(s)))


def place_lost(a, op, b, ctx):
    """The digit result with no point: 0.3 × 4 -> 12; 2.4 ÷ 3 -> 8 (24 tenths ÷ 3)."""
    if op == MUL:
        return Fraction(digits_of(a) * digits_of(b))
    if op == DIV and places(b) == 0:
        c = a / b
        return c * 10 ** places(c)
    return None


def extra_place(a, op, b, ctx):
    if op == MUL or (op == DIV and places(b) == 0):
        return correct_value(a, op, b) / 10
    return None


def missed_place(a, op, b, ctx):
    if op == MUL or (op == DIV and places(b) == 0):
        return correct_value(a, op, b) * 10
    return None


def count_places(a, op, b, ctx):
    """Addition's rule used for ×: the product gets the longer factor's places. 0.6 × 0.2 -> 1.2."""
    if op != MUL:
        return None
    return dec(digits_of(a) * digits_of(b), max(places(a), places(b)))


def too_many_places(a, op, b, ctx):
    return correct_value(a, op, b) / 10 if op == MUL else None


def big_into_small(a, op, b, ctx):
    """Whole ÷ larger whole, reversed: 4 ÷ 5 -> 5 ÷ 4 = 1.25 (only when it terminates in ≤ 3)."""
    if op != DIV or places(a) or places(b) or a >= b:
        return None
    v = b / a
    try:
        return v if places(v) <= 3 else None
    except ValueError:
        return None


def _shift_k(a, b, ctx):
    return 2 if ctx.get("money") else places(b)


def shift_divisor_only(a, op, b, ctx):
    """Moves the divisor's point but not the dividend's: 1.2 ÷ 0.3 -> 1.2 ÷ 3 = 0.4."""
    if op != DIV or places(b) == 0:
        return None
    return a / (b * 10 ** _shift_k(a, b, ctx))


def shift_dividend_only(a, op, b, ctx):
    """Moves the dividend's point but not the divisor's: 1.2 ÷ 0.3 -> 12 ÷ 0.3 = 40."""
    if op != DIV or places(b) == 0:
        return None
    return a * 10 ** _shift_k(a, b, ctx) / b


def mult_for_div(a, op, b, ctx):
    """"Division makes smaller": multiplies by the decimal divisor. 2 ÷ 0.5 -> 1."""
    if op != DIV or places(b) == 0 or b >= 1 or ctx.get("story"):
        return None
    v = a * b
    return v if places(v) <= 2 else None


# Per tier, in label priority (first rule to produce a value names it).
WRONG_RULES = {
    1: [("BRING_DOWN", bring_down), ("ALIGN_RIGHT", align_right),
        ("DECIMAL_AS_WHOLE", decimal_as_whole), ("DROP_PLACE", drop_place)],
    2: [("PLACE_LOST", place_lost), ("EXTRA_PLACE", extra_place), ("MISSED_PLACE", missed_place)],
    3: [("PLACE_LOST", place_lost), ("COUNT_PLACES", count_places),
        ("TOO_MANY_PLACES", too_many_places)],
    4: [("BIG_INTO_SMALL", big_into_small), ("PLACE_LOST", place_lost),
        ("EXTRA_PLACE", extra_place), ("MISSED_PLACE", missed_place)],
    5: [("SHIFT_ONE_SIDE", shift_divisor_only), ("SHIFT_ONE_SIDE", shift_dividend_only),
        ("MULT_FOR_DIV", mult_for_div)],
}


def misconception_values(a, op, b, tier, ctx=None):
    """[(label, value)] for every rule of the tier giving a distinct usable wrong value."""
    ctx = ctx or {}
    correct = correct_value(a, op, b)
    out, seen = [], {correct}
    for label, f in WRONG_RULES[tier]:
        v = f(a, op, b, ctx)
        if v is None or v in seen or v <= 0 or v > MAX_DISTRACTOR:
            continue
        try:
            places(v)
        except ValueError:
            continue
        seen.add(v)
        out.append((label, v))
    return out


# ---------------------------------------------------------------------------------------------
# Bounds (§4b, the manifest's "bounds")
# ---------------------------------------------------------------------------------------------
def operand_ok(v: Fraction) -> bool:
    return Fraction(1, 100) <= v <= 10 and places(v) <= 2 and nonzero_digits(v) <= 2


def bounds_ok(a: Fraction, op: str, b: Fraction) -> bool:
    if not (operand_ok(a) and operand_ok(b)):
        return False
    c = correct_value(a, op, b)
    if op in (ADD, SUB):
        return 0 < c <= 20 and carries(a, b, op) <= 1
    if op == MUL:
        da, db = digits_of(a), digits_of(b)
        return 2 <= da <= 10 and 2 <= db <= 10 and places(c) <= 3
    # ÷: shift both points until the divisor is whole; then digit work q = D ÷ d is a fact
    k = places(b)
    d = digits_of(b)
    try:
        pc = places(c)
    except ValueError:
        return False
    q = int(c * 10 ** pc)
    D = a * 10 ** (k + pc)
    return (D.denominator == 1 and 2 <= d <= 10 and 2 <= q <= 10 and D == d * q
            and pc <= 3)


# ---------------------------------------------------------------------------------------------
# Explanations (≤ 160 chars)
# ---------------------------------------------------------------------------------------------
def explain(a, op, b, kind, ctx=None):
    ctx = ctx or {}
    c = correct_value(a, op, b)
    if op in (ADD, SUB):
        if kind == "carry":
            p = places(a)
            s = (digits_of(a) % 10 ** p) + (digits_of(b) % 10 ** p)
            return (f"{fmt(a)} + {fmt(b)}: {PLACE_NAME[p]} {digits_of(a) % 10 ** p} + "
                    f"{digits_of(b) % 10 ** p} = {s}, and 10 {PLACE_NAME[p]} make 1. "
                    f"So {fmt(c)}.")
        p = max(places(a), places(b))
        return f"Line up the points: {fixed(a, p)} {op} {fixed(b, p)} = {fmt(c)}."
    if op == MUL:
        da, db = digits_of(a), digits_of(b)
        pa, pb = places(a), places(b)
        p = pa + pb
        if pa and pb:
            return (f"{fmt(a)} × {fmt(b)}: {da} × {db} = {da * db}. {pa} + {pb} = {p} places, "
                    f"so {fixed(c, p)}" + (f" = {fmt(c)}." if places(c) < p else "."))
        n = da * db
        return (f"{fmt(a)} × {fmt(b)}: {da} × {db} = {n}, so {n} {PLACE_NAME[p]} = {fmt(c)}.")
    # ÷
    if ctx.get("story"):
        k = 2 if ctx.get("money") else places(b)
        sa, sb = fmt(a * 10 ** k), fmt(b * 10 ** k)
        what = "cents" if ctx.get("money") else "pieces"
        if ctx.get("money"):
            return f"{money(a)} ÷ {money(b)}: in cents, {sa} ÷ {sb} = {fmt(c)}."
        return f"{fmt(a)} ÷ {fmt(b)}: move both points {k} place{'s' * (k > 1)}: {sa} ÷ {sb} = {fmt(c)} {what}."
    if places(b) == 0:  # ÷ whole: work in the answer's unit
        p = places(c)
        n = a * 10 ** p
        unit = PLACE_NAME[p]
        lead = f"{fmt(a)} = {fmt(n)} {unit}. " if places(a) < p else ""
        return (f"{fmt(a)} ÷ {fmt(b)}: {lead}{fmt(n)} {unit} ÷ {fmt(b)} = {fmt(c * 10 ** p)} "
                f"{unit} = {fmt(c)}.")
    k = places(b)
    return (f"{fmt(a)} ÷ {fmt(b)}: move both points {k} place{'s' * (k > 1)}: "
            f"{fmt(a * 10 ** k)} ÷ {fmt(b * 10 ** k)} = {fmt(c)}.")


# ---------------------------------------------------------------------------------------------
# ARITH filler and item assembly
# ---------------------------------------------------------------------------------------------
def arith_candidates(correct: Fraction, rng: random.Random, k: int | None = None) -> list:
    """One-column slips in place ``k`` (default: the answer's last place)."""
    u = Fraction(1, 10 ** (places(correct) if k is None else k))
    near = [correct + u, correct - u]
    rng.shuffle(near)
    far = [correct + 2 * u, correct - 2 * u, correct + 10 * u, correct - 10 * u]
    rng.shuffle(far)
    return near + far + [correct + 3 * u, correct + 4 * u]


def make_item(tier, prompt, a, op, b, expl, answer_pos, rng, ctx=None):
    ctx = ctx or {}
    correct = correct_value(a, op, b)
    wrong = misconception_values(a, op, b, tier, ctx)
    if not wrong:
        return None
    if len(wrong) > 3:
        rng.shuffle(wrong)
        wrong = wrong[:3]
    used = {correct} | {v for _, v in misconception_values(a, op, b, tier, ctx)}
    # + −: slip in the problem's smallest place (0.7 + 0.3 -> 0.9 / 1.1, not 0 / 2)
    k = max(places(a), places(b), places(correct)) if op in (ADD, SUB) else None
    for v in arith_candidates(correct, rng, k):
        if len(wrong) == 3:
            break
        if 0 < v <= MAX_DISTRACTOR and v not in used:
            used.add(v)
            wrong.append(("ARITH", v))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, correct)] + wrong[answer_pos:]
    choices = [fmt(v) for _, v in pairs]
    if (len(prompt) > 60 or len(expl) > 160 or any(len(c) > 14 for c in choices)):
        return None
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": choices,
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def _bare(a, op, b):
    return f"{fmt(a)} {op} {fmt(b)}"


# ---------------------------------------------------------------------------------------------
# Tier builders: rng, kind -> (prompt, a, op, b, expl, ctx) or None
# ---------------------------------------------------------------------------------------------
def _t1(rng, kind):
    if kind == "mixed_add":  # w.x + 0.yz  (0.4 + 0.35)
        a = dec(rng.randint(0, 3) * 10 + rng.randint(1, 9), 1)
        b = dec(rng.randint(0, 9) * 10 + rng.randint(1, 9), 2)
        op = ADD
    elif kind == "whole_add":  # 3 + 0.4, 3 + 0.25
        a = Fraction(rng.randint(2, 9))
        b = dec(rng.randint(1, 9), 1) if rng.random() < 0.5 else dec(rng.randint(1, 99), 2)
        op = ADD
    elif kind == "carry_add":  # 0.8 + 0.5, 1.6 + 0.7: tenths make a whole
        x, y = rng.randint(2, 9), rng.randint(2, 9)
        if x + y < 10:
            return None
        a = dec(rng.randint(0, 3) * 10 + x, 1)
        b = dec(y, 1)
        op = ADD
    elif kind == "short_minus_long":  # 0.6 − 0.25, 3 − 0.4
        if rng.random() < 0.6:
            a = dec(rng.randint(0, 3) * 10 + rng.randint(1, 9), 1)
            b = dec(rng.randint(0, 9) * 10 + rng.randint(1, 9), 2)
        else:
            a = Fraction(rng.randint(1, 9))
            b = dec(rng.randint(1, 9), 1)
        op = SUB
    else:  # long_minus_short: 0.75 − 0.3, 4.5 − 2
        if rng.random() < 0.6:
            a = dec(rng.randint(1, 9) * 10 + rng.randint(1, 9), 2)
            b = dec(rng.randint(1, 9), 1)
        else:
            a = dec(rng.randint(1, 9) * 10 + rng.randint(1, 9), 1)
            b = Fraction(rng.randint(1, 9))
        op = SUB
    if op == ADD and rng.random() < 0.5:
        a, b = b, a
    if op == SUB and a <= b:
        return None
    ex_kind = "carry" if kind == "carry_add" else "align"
    return _bare(a, op, b), a, op, b, explain(a, op, b, ex_kind), {}


def _t2(rng, kind):
    k = 1 if kind == "tenths" else 2
    a = dec(rng.randint(2, 9), k)
    b = Fraction(rng.randint(2, 10))
    if rng.random() < 0.4:
        a, b = b, a
    return _bare(a, MUL, b), a, MUL, b, explain(a, MUL, b, None), {}


def _t3(rng, kind):
    a = dec(rng.randint(2, 9), 1)
    b = dec(rng.randint(2, 9), 1 if kind == "t_t" else 2)
    if rng.random() < 0.5:
        a, b = b, a
    return _bare(a, MUL, b), a, MUL, b, explain(a, MUL, b, None), {}


def _t4(rng, kind):
    d, q = rng.randint(2, 9), rng.randint(2, 9)
    m = 1 if kind == "tenths" else 2
    if kind == "whole":  # 4 ÷ 5: the dividend is a whole number smaller than the divisor
        if (d * q) % 10:
            return None
        m = 1
    a, b = dec(d * q, m), Fraction(d)
    if kind != "whole" and places(a) == 0:
        return None
    return _bare(a, DIV, b), a, DIV, b, explain(a, DIV, b, None), {}


THINGS = ("Pens", "Stickers", "Pencils", "Erasers", "Cards", "Apples", "Cookies", "Tickets")
LENGTHS = ("rope", "ribbon", "string", "wire", "pipe")


def _t5(rng, kind):
    d, q = rng.randint(2, 9), rng.randint(2, 9)
    if kind == "money":  # Pens cost $0.60 each. How many for $4.20?
        b = dec(d, 1)  # $0.20-$0.90: a real price
        a = b * q
        ctx = {"story": True, "money": True}
        prompt = f"{rng.choice(THINGS)} cost {money(b)} each. How many for {money(a)}?"
        return prompt, a, DIV, b, explain(a, DIV, b, None, ctx), ctx
    if kind == "length":  # Cut 2.4 m of rope into 0.3 m pieces. How many?
        b = dec(d, 1)  # 0.2-0.9 m pieces
        a = b * q
        ctx = {"story": True}
        prompt = f"Cut {fmt(a)} m of {rng.choice(LENGTHS)} into {fmt(b)} m pieces. How many?"
        return prompt, a, DIV, b, explain(a, DIV, b, None, ctx), ctx
    k = rng.choice((1, 1, 2))
    m = 1 if kind == "decimal_answer" else 0
    b = dec(d, k)
    c = dec(q, m)
    a = b * c
    return _bare(a, DIV, b), a, DIV, b, explain(a, DIV, b, None), {}


TIER_KINDS = {
    1: [("mixed_add", 10), ("whole_add", 6), ("carry_add", 8), ("short_minus_long", 8),
        ("long_minus_short", 8)],
    2: [("tenths", 26), ("hundredths", 14)],
    3: [("t_t", 26), ("t_h", 14)],
    4: [("tenths", 18), ("hundredths", 14), ("whole", 8)],
    5: [("whole_answer", 16), ("decimal_answer", 8), ("money", 9), ("length", 7)],
}
BUILDERS = {1: _t1, 2: _t2, 3: _t3, 4: _t4, 5: _t5}


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 100000) -> list:
    plan = [k for k, n in TIER_KINDS[tier] for _ in range(n)]
    plan = (plan * (count // len(plan) + 1))[:count]
    rng.shuffle(plan)
    positions = _balanced(count, 4, rng)
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        got = BUILDERS[tier](rng, plan[len(items)])
        if got is None:
            continue
        prompt, a, op, b, expl, ctx = got
        if prompt in prompts or not bounds_ok(a, op, b):
            continue
        item = make_item(tier, prompt, a, op, b, expl, positions[len(items)], rng, ctx)
        if item is None:
            continue
        prompts.add(prompt)
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
