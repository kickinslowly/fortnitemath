"""Procedural generator for the percent-problems cartridge (fnm-cart/1, grade 7, 7.RP.A.3).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every prompt kind has a few *templates* (``TEMPLATES``). A builder picks numbers inside the manifest's
  ``bounds`` and fills a template; ``analyze(prompt)`` then re-reads that text with regexes compiled
  from the same templates and returns the correct choice, every modelled misconception's wrong choice
  and the explanation. The text a student sees is the only thing ever solved.
* A choice is ``(display, value)`` with an exact ``Fraction`` value (``$48`` -> 48, ``25%`` -> 25,
  ``0.25%`` -> 1/4). No two choices of an item share a value (never two right doors).
* Wrong choices: misconception values first, in the order listed per kind. The first two are always kept;
  the third is drawn at random from the rest. ``ARITH`` only fills up to 4 choices and never equals ANY
  rule's value for that prompt.
* Bounds (PROTOCOL §4b percents) live in ``base_ok`` / ``part_ok`` and the ``*_PCTS`` tables: a percent is
  only ever taken of a whole it divides cleanly (10% = 1/10 of a ten, 25% = 1/4 of a four, ...).
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

MINUS = "−"

# ---------------------------------------------------------------------------------------------
# Bounds (PROTOCOL §4b percents, stated in the manifest "bounds")
# ---------------------------------------------------------------------------------------------
TIP_PCTS = (10, 20, 25)
TAX_PCTS = (10, 20)
OFF_PCTS = (10, 20, 25, 30, 40, 50, 75)
MARKUP_PCTS = (10, 20, 25, 30, 40, 50)
RATE_PCTS = (10, 20, 25)
CHANGE_PCTS = (10, 20, 25, 30, 40, 50, 75)
ERROR_PCTS = (10, 20, 25, 30, 40, 50)
EXTRA_OFF_PCTS = (10, 20, 25)
YEARS = (2, 3, 4, 5)
MAX_PART = 20  # each amount added or subtracted
MAX_TOTAL = 100  # every whole, new price and total
MAX_DISTRACTOR = 999
MAX_PROMPT, MAX_CHOICE, MAX_EXPL = 60, 14, 160


def base_ok(p: int, W: int) -> bool:
    """p% of W is a clean mental fact: tens of percent of 20-90 in tens, 25%/75% of 8-40 in fours,
    50% also of evens 4-20."""
    if p in (25, 75):
        return W % 4 == 0 and 8 <= W <= 40
    if p % 10:
        return False
    if W % 10 == 0 and 20 <= W <= 90:
        return True
    return p == 50 and W % 2 == 0 and 4 <= W <= 20


class NotMine(Exception):
    """The text is not one of this cartridge's prompts, or breaks its bounds."""


def part(p: int, W: int) -> int:
    v = Fraction(p * W, 100)
    if v.denominator != 1:
        raise NotMine(f"{p}% of {W} is not whole")
    return int(v)


def part_ok(p: int, W: int) -> bool:
    return base_ok(p, W) and 2 <= part(p, W) <= MAX_PART


WHOLES = {p: [W for W in range(4, 91) if part_ok(p, W)] for p in range(10, 100, 5)
          if any(part_ok(p, W) for W in range(4, 91))}

# ---------------------------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------------------------


def dec(v: Fraction) -> str:
    """0.25, 0.1 -- only for values whose denominator divides 100."""
    return f"{float(v):.2f}".rstrip("0").rstrip(".")


def cash(n):
    n = int(n)
    return (f"${n}", Fraction(n))


def pc(v):
    v = Fraction(v)
    return (f"{v.numerator}%" if v.denominator == 1 else f"{dec(v)}%", v)


def money(n) -> str:
    return f"${n}"


def plain(n) -> str:
    return str(n)


# ---------------------------------------------------------------------------------------------
# Templates (the single source of the prompt text AND of its parser)
# ---------------------------------------------------------------------------------------------
TEMPLATES = {
    # T1
    "tip_total": ["${W} meal plus a {p}% tip. Total?",
                  "The ${W} bill gets a {p}% tip. Total paid?",
                  "You tip {p}% on the ${W} dinner. Total cost?"],
    "tax_total": ["${W} jacket plus {p}% sales tax. Total cost?",
                  "Tax is {p}% on the ${W} game. Total price?",
                  "The ${W} toy has {p}% tax. What do you pay?"],
    "tip_part": ["{p}% tip on the ${W} meal. How much is the tip?",
                 "Tip {p}% on the ${W} bill. Tip in dollars?"],
    "tax_part": ["{p}% sales tax on ${W}. How much is the tax?",
                 "The ${W} game has {p}% tax. Tax in dollars?"],
    # T2
    "disc_price": ["${W} shirt, {p}% off. Sale price?",
                   "The ${W} game is {p}% off. What do you pay?",
                   "Sale! {p}% off the ${W} bag. New price?",
                   "The ${W} hoodie gets a {p}% discount. Price now?"],
    "disc_save": ["{p}% off the ${W} coat. How much do you save?",
                  "${W} shoes, {p}% off. How much is the discount?",
                  "The ${W} cap gets {p}% off. Savings in dollars?"],
    # T3
    "markup_price": ["A shop pays ${W} and marks it up {p}%. Selling price?",
                     "Cost ${W}, markup {p}%. What is the selling price?",
                     "The ${W} item gets a {p}% markup. New price?"],
    "markup_amt": ["Cost ${W}, markup {p}%. How much is the markup?",
                   "A shop marks up the ${W} item {p}%. Markup in dollars?"],
    "interest": ["${P} at {r}% simple interest a year for {t} years. Interest?",
                 "${P} earns {r}% simple interest a year. Interest in {t} years?",
                 "${P} deposit, {r}% simple interest a year, {t} years. Interest?"],
    "balance": ["${P} at {r}% simple interest a year for {t} years. Balance?",
                "${P} deposit, {r}% simple interest a year, {t} years. Balance?",
                "${P} earns {r}% simple interest a year. Balance in {t} years?"],
    # T4
    "inc": ["Price rises from ${O} to ${N}. Percent increase?",
            "A club grows from {O} to {N} kids. Percent increase?",
            "A plant grows from {O} cm to {N} cm. Percent increase?",
            "Tickets go up from ${O} to ${N}. Percent increase?",
            "Score rises from {O} to {N} points. Percent increase?"],
    "dec": ["Price drops from ${O} to ${N}. Percent decrease?",
            "A class shrinks from {O} to {N} kids. Percent decrease?",
            "Water drops from {O} cm to {N} cm. Percent decrease?",
            "Sales fall from ${O} to ${N}. Percent decrease?",
            "Score falls from {O} to {N} points. Percent decrease?"],
    # T5
    "pe": ["Guessed {g}. Actual was {A}. Percent error?",
           "Estimated {g} kids. Really {A}. Percent error?",
           "Measured {g} cm. True length: {A} cm. Percent error?",
           "Scale shows {g} lb. True weight: {A} lb. Percent error?",
           "Guessed ${g}. Actual price: ${A}. Percent error?"],
    "disc_tax": ["${W} coat, {p1}% off, then {p2}% tax. Cost?",
                 "${W} bike, {p1}% off, then {p2}% tax. Total?",
                 "The ${W} game is {p1}% off, then {p2}% tax. Total?"],
    "disc_disc": ["${W} shirt, {p1}% off, then {p2}% off that. Price?",
                  "${W} jacket, {p1}% off, then {p2}% off the sale price. Price?"],
    "mark_disc": ["Cost ${W}, marked up {p1}%, then {p2}% off that. Price?",
                  "The ${W} item is marked up {p1}%, then {p2}% off that. Price?"],
}


def _compile(template: str):
    pieces = re.split(r"\{(\w+)\}", template)
    rx = "".join(f"(?P<{s}>\\d+)" if i % 2 else re.escape(s) for i, s in enumerate(pieces))
    return re.compile("^" + rx + "$")


RE = {kind: [_compile(t) for t in ts] for kind, ts in TEMPLATES.items()}


# ---------------------------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------------------------
def pct_phrase(p: int, W: int, fmt=money) -> str:
    """How to get p% of W in the head; ends with the amount."""
    a = part(p, W)
    if p == 10:
        return f"10% of {fmt(W)} is {fmt(a)}"
    if p == 25:
        return f"25% is 1/4 of {fmt(W)}: {fmt(a)}"
    if p == 75:
        return f"1/4 of {fmt(W)} is {fmt(W // 4)}, so 75% is {fmt(a)}"
    if p == 50:
        return f"50% is half of {fmt(W)}: {fmt(a)}"
    return f"10% of {fmt(W)} is {fmt(W // 10)}, so {p}% is {fmt(a)}"


def ratio_phrase(d: int, B: int, p: int, fmt) -> str:
    """Why d out of B is p% (B is the original / actual value)."""
    if p == 10:
        return f"{fmt(d)} is 1/10 of {fmt(B)}, so 10%."
    if p == 25:
        return f"{fmt(d)} is 1/4 of {fmt(B)}, so 25%."
    if p == 50:
        return f"{fmt(d)} is half of {fmt(B)}, so 50%."
    if p == 75:
        return f"1/4 of {fmt(B)} is {fmt(B // 4)}; {fmt(d)} is 3 of those, so 75%."
    return f"10% of {fmt(B)} is {fmt(B // 10)}; {fmt(d)} is {p // 10} of those, so {p}%."


# ---------------------------------------------------------------------------------------------
# Solvers: group dict -> (correct choice, [(label, choice) in priority order], explanation)
# ---------------------------------------------------------------------------------------------
def _add_total(g):  # tip, tax, markup: price plus the percent
    W, p = g["W"], g["p"]
    a = part(p, W)
    wrong = [("PART_ONLY", cash(a)), ("PERCENT_AS_DOLLARS", cash(W + p))]
    if p != 10 and W % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", cash(W + W // 10)))
    wrong.append(("SUBTRACTED", cash(W - a)))
    return cash(W + a), wrong, f"{pct_phrase(p, W)}. ${W} + ${a} = ${W + a}."


def _add_part(g):  # how much is the tip / tax / markup
    W, p = g["W"], g["p"]
    a = part(p, W)
    wrong = [("TOTAL_FOR_PART", cash(W + a)), ("PERCENT_AS_DOLLARS", cash(p))]
    if p != 10 and W % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", cash(W // 10)))
    return cash(a), wrong, f"{pct_phrase(p, W)}."


def _disc_price(g):
    W, p = g["W"], g["p"]
    a = part(p, W)
    wrong = [("DISCOUNT_ONLY", cash(a)), ("PERCENT_AS_DOLLARS", cash(W - p)),
             ("ADDED", cash(W + a))]
    if p != 10 and W % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", cash(W - W // 10)))
    return cash(W - a), wrong, f"{pct_phrase(p, W)}. ${W} {MINUS} ${a} = ${W - a}."


def _disc_save(g):
    W, p = g["W"], g["p"]
    a = part(p, W)
    wrong = [("SALE_FOR_SAVINGS", cash(W - a)), ("PERCENT_AS_DOLLARS", cash(p))]
    if p != 10 and W % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", cash(W // 10)))
    return cash(a), wrong, f"{pct_phrase(p, W)}."


def _interest_parts(g):
    P, r, t = g["P"], g["r"], g["t"]
    a = part(r, P)
    return P, r, t, a, a * t


def _interest(g):
    P, r, t, a, I = _interest_parts(g)
    wrong = [("ONE_YEAR", cash(a)), ("TOTAL_FOR_INTEREST", cash(P + I)),
             ("PERCENT_AS_DOLLARS", cash(r * t))]
    if r != 10 and P % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", cash(P // 10 * t)))
    return cash(I), wrong, f"{pct_phrase(r, P)} a year. {t} × ${a} = ${I}."


def _balance(g):
    P, r, t, a, I = _interest_parts(g)
    wrong = [("INTEREST_ONLY", cash(I)), ("ONE_YEAR", cash(P + a)),
             ("PERCENT_AS_DOLLARS", cash(P + r * t))]
    if r != 10 and P % 10 == 0:
        wrong.append(("TENTH_FOR_ALL", cash(P + P // 10 * t)))
    return (cash(P + I), wrong,
            f"{pct_phrase(r, P)} a year. {t} × ${a} = ${I}. ${P} + ${I} = ${P + I}.")


def _decimal_wrong(d, B):
    return ("DECIMAL_NOT_PERCENT", pc(Fraction(d, B)))


def _change(g, money_flag, up):
    O, N = g["O"], g["N"]
    fmt = money if money_flag else plain
    if (N > O) != up:
        raise NotMine("direction")
    d = abs(N - O)
    pct = Fraction(100 * d, O)
    if pct.denominator != 1:
        raise NotMine("not a clean percent")
    p = int(pct)
    wrong = [("DIFFERENCE_AS_PERCENT", pc(d)), ("RATIO_AS_CHANGE", pc(Fraction(100 * N, O)))]
    if (100 * d) % N == 0:
        wrong.append(("NEW_AS_BASE", pc(Fraction(100 * d, N))))
    wrong.append(_decimal_wrong(d, O))
    hi, lo = (N, O) if up else (O, N)
    return (pc(p), wrong,
            f"Change: {fmt(hi)} {MINUS} {fmt(lo)} = {fmt(d)}. {ratio_phrase(d, O, p, fmt)}")


def _pe(g, money_flag):
    guess, A = g["g"], g["A"]
    fmt = money if money_flag else plain
    d = abs(guess - A)
    pct = Fraction(100 * d, A)
    if pct.denominator != 1 or d == 0:
        raise NotMine("not a clean percent")
    p = int(pct)
    wrong = [("DIFFERENCE_AS_PERCENT", pc(d)), ("GUESS_RATIO", pc(Fraction(100 * guess, A)))]
    if (100 * d) % guess == 0:
        wrong.append(("GUESS_AS_BASE", pc(Fraction(100 * d, guess))))
    wrong.append(_decimal_wrong(d, A))
    hi, lo = (guess, A) if guess > A else (A, guess)
    return (pc(p), wrong,
            f"Miss: {fmt(hi)} {MINUS} {fmt(lo)} = {fmt(d)}. Compare with the actual "
            f"{fmt(A)}. {ratio_phrase(d, A, p, fmt)}")


def _two_step(g, kind):
    W, p1, p2 = g["W"], g["p1"], g["p2"]
    a1 = part(p1, W)
    up1 = kind == "mark_disc"
    V1 = W + a1 if up1 else W - a1
    a2 = part(p2, V1)
    up2 = kind == "disc_tax"
    V2 = V1 + a2 if up2 else V1 - a2
    net = {"disc_tax": 100 - p1 + p2, "disc_disc": 100 - p1 - p2, "mark_disc": 100 + p1 - p2}[kind]
    wrong = [("FORGOT_SECOND", cash(V1))]
    if (W * net) % 100 == 0:
        wrong.append(("COMBINED_PERCENTS", cash(W * net // 100)))
    wrong.append(("PERCENT_AS_DOLLARS", cash(V1 + p2 if up2 else V1 - p2)))
    wrong.append(("SECOND_WRONG_WAY", cash(V1 - a2 if up2 else V1 + a2)))
    s1 = f"{pct_phrase(p1, W)}; ${W} {'+' if up1 else MINUS} ${a1} = ${V1}."
    s2 = f"{pct_phrase(p2, V1)}; ${V1} {'+' if up2 else MINUS} ${a2} = ${V2}."
    return cash(V2), wrong, f"{s1} {s2}"


def _s_inc(g):
    return _change(g, g["_money"], True)


def _s_dec(g):
    return _change(g, g["_money"], False)


def _s_pe(g):
    return _pe(g, g["_money"])


_SOLVERS = {
    "tip_total": _add_total, "tax_total": _add_total, "markup_price": _add_total,
    "tip_part": _add_part, "tax_part": _add_part, "markup_amt": _add_part,
    "disc_price": _disc_price, "disc_save": _disc_save,
    "interest": _interest, "balance": _balance,
    "inc": _s_inc, "dec": _s_dec, "pe": _s_pe,
    "disc_tax": lambda g: _two_step(g, "disc_tax"),
    "disc_disc": lambda g: _two_step(g, "disc_disc"),
    "mark_disc": lambda g: _two_step(g, "mark_disc"),
}


def analyze(prompt: str):
    """THE solver: (kind, correct choice, [(label, choice)...], explanation) from the display text.

    The wrong list is in priority order; it may hold values equal to the answer or to each other --
    ``misconception_choices`` dedups by value."""
    for kind, rxs in RE.items():
        for rx in rxs:
            m = rx.match(prompt)
            if m:
                g = {k: int(v) for k, v in m.groupdict().items()}
                g["_money"] = "$" in prompt
                return (kind,) + _SOLVERS[kind](g)
    raise NotMine(prompt)


# ---------------------------------------------------------------------------------------------
# Distractor assembly
# ---------------------------------------------------------------------------------------------
def misconception_choices(prompt: str):
    """[(label, (display, value))] distinct in value, none equal to the answer, positive, short."""
    _, correct, wrong, _ = analyze(prompt)
    seen = {correct[1]}
    out = []
    for label, ch in wrong:
        if ch[1] <= 0 or ch[1] in seen or len(ch[0]) > MAX_CHOICE or ch[1] > MAX_DISTRACTOR:
            continue
        seen.add(ch[1])
        out.append((label, ch))
    return out


def _arith_candidates(correct, rng):
    disp, v = correct
    if disp.endswith("%"):
        near = [v + 5, v - 5]
        far = [v + d for d in (10, -10, 15, -15, 20)]
        mk = pc
    else:
        near = [v + d for d in (1, -1, 2, -2)]
        far = [v + d for d in (3, -3, 5, -5, 10, -10)]
        mk = cash
    rng.shuffle(near)
    rng.shuffle(far)
    return [mk(x) for x in near + far if x > 0]


# A third door that would show up on nearly every item teaches "always skip that one": keep it rare.
OPTIONAL_P = {"DECIMAL_NOT_PERCENT": 0.3}


def make_item(prompt: str, tier: int, answer_pos: int, rng: random.Random):
    if len(prompt) > MAX_PROMPT:
        return None
    _, correct, raw, expl = analyze(prompt)
    if len(expl) > MAX_EXPL or len(correct[0]) > MAX_CHOICE:
        return None
    mis = misconception_choices(prompt)
    if not mis:
        return None
    core, rest = mis[:2], mis[2:]
    rest = [w for w in rest if rng.random() < OPTIONAL_P.get(w[0], 1.0)]
    rng.shuffle(rest)
    wrong = (core + rest)[:3]
    used = {correct[1]} | {ch[1] for _, ch in raw}  # ARITH never equals ANY rule's value
    for ch in _arith_candidates(correct, rng):
        if len(wrong) == 3:
            break
        if ch[1] not in used:
            used.add(ch[1])
            wrong.append(("ARITH", ch))
    if len(wrong) < 3:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, correct)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [ch[0] for _, ch in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


# ---------------------------------------------------------------------------------------------
# Builders (pick numbers inside the bounds, fill a template)
# ---------------------------------------------------------------------------------------------
def _template(rng, kind, **kw):
    return rng.choice(TEMPLATES[kind]).format(**kw)


def _add_build(kind, pcts):
    def build(rng):
        p = rng.choice(pcts)
        W = rng.choice([w for w in WHOLES[p] if w + part(p, w) <= MAX_TOTAL])
        return _template(rng, kind, W=W, p=p)
    return build


def _plain_build(kind, pcts):
    def build(rng):
        p = rng.choice(pcts)
        return _template(rng, kind, W=rng.choice(WHOLES[p]), p=p)
    return build


def _interest_build(kind):
    def build(rng):
        r = rng.choice(RATE_PCTS)
        opts = [(P, t) for P in WHOLES[r] for t in YEARS
                if part(r, P) <= 10 and part(r, P) * t <= MAX_PART
                and P + part(r, P) * t <= MAX_TOTAL]
        P, t = rng.choice(opts)
        return _template(rng, kind, P=P, r=r, t=t)
    return build


def _change_build(kind):
    up = kind == "inc"

    def build(rng):
        want_new_base = rng.random() < 0.5  # half the items can offer the NEW_AS_BASE door
        for _ in range(30):
            p = rng.choice(CHANGE_PCTS)
            opts = [(O, O + part(p, O) if up else O - part(p, O)) for O in WHOLES[p]]
            opts = [(O, N) for O, N in opts if 2 <= N <= MAX_TOTAL]
            O, N = rng.choice(opts)
            if not want_new_base or (100 * abs(N - O)) % N == 0:
                break
        return _template(rng, kind, O=O, N=N)
    return build


def _pe_build(rng):
    want_guess_base = rng.random() < 0.5  # half the items can offer the GUESS_AS_BASE door
    for _ in range(30):
        p = rng.choice(ERROR_PCTS)
        A = rng.choice(WHOLES[p])
        d = part(p, A)
        g = A + d if rng.random() < 0.5 else A - d
        if g <= MAX_TOTAL and (not want_guess_base or (100 * d) % g == 0):
            break
    if g > MAX_TOTAL:
        return None
    return _template(rng, "pe", g=g, A=A)


def _two_step_combos(kind, p1s, p2s):
    out = []
    for p1 in p1s:
        for W in WHOLES[p1]:
            a1 = part(p1, W)
            V1 = W + a1 if kind == "mark_disc" else W - a1
            if not 1 <= V1 <= MAX_TOTAL:
                continue
            for p2 in p2s:
                if not part_ok(p2, V1):
                    continue
                a2 = part(p2, V1)
                V2 = V1 + a2 if kind == "disc_tax" else V1 - a2
                if 1 <= V2 <= MAX_TOTAL:
                    out.append((W, p1, p2))
    return out


_TWO_STEP = {
    "disc_tax": _two_step_combos("disc_tax", OFF_PCTS, TAX_PCTS),
    "disc_disc": _two_step_combos("disc_disc", OFF_PCTS, EXTRA_OFF_PCTS),
    "mark_disc": _two_step_combos("mark_disc", MARKUP_PCTS, EXTRA_OFF_PCTS),
}


def _two_step_build(kind):
    def build(rng):
        W, p1, p2 = rng.choice(_TWO_STEP[kind])
        return _template(rng, kind, W=W, p1=p1, p2=p2)
    return build


BUILDERS = {
    "tip_total": _add_build("tip_total", TIP_PCTS),
    "tax_total": _add_build("tax_total", TAX_PCTS),
    "tip_part": _add_build("tip_part", TIP_PCTS),  # the total is a wrong door: keep it <= 100 too
    "tax_part": _add_build("tax_part", TAX_PCTS),
    "disc_price": _plain_build("disc_price", OFF_PCTS),
    "disc_save": _plain_build("disc_save", OFF_PCTS),
    "markup_price": _add_build("markup_price", MARKUP_PCTS),
    "markup_amt": _add_build("markup_amt", MARKUP_PCTS),
    "interest": _interest_build("interest"),
    "balance": _interest_build("balance"),
    "inc": _change_build("inc"),
    "dec": _change_build("dec"),
    "pe": _pe_build,
    "disc_tax": _two_step_build("disc_tax"),
    "disc_disc": _two_step_build("disc_disc"),
    "mark_disc": _two_step_build("mark_disc"),
}

# (kind, share of a 40-item tier); scaled by largest remainder for other sizes
TIER_PLAN = {
    1: [("tip_total", 14), ("tax_total", 14), ("tip_part", 6), ("tax_part", 6)],
    2: [("disc_price", 28), ("disc_save", 12)],
    3: [("markup_price", 12), ("markup_amt", 6), ("interest", 14), ("balance", 8)],
    4: [("inc", 20), ("dec", 20)],
    5: [("pe", 16), ("disc_tax", 6), ("disc_disc", 9), ("mark_disc", 9)],
}


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def _balanced(count, k, rng):
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def _alloc(plan, count):
    total = sum(w for _, w in plan)
    raw = [count * w / total for _, w in plan]
    n = [int(x) for x in raw]
    order = sorted(range(len(plan)), key=lambda i: raw[i] - n[i], reverse=True)
    for i in order[:count - sum(n)]:
        n[i] += 1
    return n


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000):
    plan = TIER_PLAN[tier]
    kinds = []
    for (kind, _), n in zip(plan, _alloc(plan, count)):
        kinds += [kind] * n
    rng.shuffle(kinds)
    positions = _balanced(count, 4, rng)
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        prompt = BUILDERS[kinds[len(items)]](rng)
        if prompt is None or prompt in prompts:
            continue
        try:
            item = make_item(prompt, tier, positions[len(items)], rng)
        except NotMine:
            continue
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
