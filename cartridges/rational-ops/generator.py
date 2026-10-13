"""Procedural generator for the rational-ops cartridge (fnm-cart/1, grade 7, CCSS 7.NS.A.1.C/D, A.2.B/C/D, A.3).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every number is an exact ``Fraction``. ``dec`` / ``frac`` / ``money`` write one value one way (no trailing
  zeros, simplest form, mixed numbers above 1), so two choices with different text never have equal value.
* Each misconception is a function of the prompt's operands that returns the value a student holding that
  wrong rule writes, or leaves the label out where the rule does not apply. A *family* (a kind of prompt)
  has an ``ORDERS`` list: when two rules give the same value, the first label in the list names it.
* Wrong choices come from those rules first; ``ARITH`` (a one-unit slip in the last place) only fills the
  rest and never equals any rule's value.
* ``steps_ok`` walks the correct working step by step and enforces the §4b bounds in the manifest's
  ``bounds`` string; every candidate item is rejected unless it passes.

Families (one per kind of prompt)
---------------------------------
  add_dec  T1  "-0.5 + 0.8"            add_frac  T2  "-1/2 + 3/4"
  fmul / fdiv  T3  fractions and wholes   dmul / ddiv  T3  decimals
  term / rep  T4  fraction -> decimal     formA / formB  T4  "Which equals -3/5?"
  story_add / story_add_frac  T5  temperature, elevation, money, fraction elevation
  rate_dec / rate_frac  T5  rate x time   dist  T5  distance across zero
  e1 / e2 / e3  T5  a x (b + c),  a + b x c,  (a + b) / c
"""
from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

MINUS = "−"
MAX_DISTRACTOR = 999
MAX_CHOICE = 14


def sign(v) -> int:
    return (v > 0) - (v < 0)


# ---------------------------------------------------------------------------------------------
# Number text
# ---------------------------------------------------------------------------------------------
def places(v: Fraction):
    """Fewest decimal places that write v exactly (0 for an integer), or None past 4."""
    for k in range(5):
        if (v * 10 ** k).denominator == 1:
            return k
    return None


def dec(v: Fraction):
    """-0.75, 0.5, 12: no trailing zeros. None when v does not terminate."""
    k = places(v)
    if k is None:
        return None
    s = str(int(abs(v) * 10 ** k))
    if k:
        s = s.rjust(k + 1, "0")
        s = s[:-k] + "." + s[-k:]
    return (MINUS if v < 0 else "") + s


def rep(v: Fraction):
    """-0.666... : a decimal whose single repeating digit starts at the first place. None otherwise."""
    a = abs(v)
    f = a - int(a)
    c = f * 9
    if f == 0 or c.denominator != 1:
        return None
    return (MINUS if v < 0 else "") + f"{int(a)}." + str(int(c)) * 3 + "..."


def dec_or_rep(v: Fraction):
    return dec(v) or rep(v)


def frac(v: Fraction) -> str:
    """-3/4, 7, -1 1/4 (simplest form, mixed above 1)."""
    n, d = abs(v.numerator), v.denominator
    s = MINUS if v < 0 else ""
    if d == 1:
        return f"{s}{n}"
    w, r = divmod(n, d)
    return f"{s}{r}/{d}" if w == 0 else f"{s}{w} {r}/{d}"


def money(v: Fraction):
    c = abs(v) * 100
    if c.denominator != 1:
        return None
    c = int(c)
    body = f"${c // 100}" if c % 100 == 0 else f"${c // 100}.{c % 100:02d}"
    return (MINUS if v < 0 else "") + body


def term(v, f, first):
    """Operand as a prompt shows it: a negative after an operator is parenthesised."""
    s = f(v)
    return s if first or v >= 0 else f"({s})"


def sfrac(n: int, d: int) -> str:
    """Raw (unsimplified) signed fraction text."""
    return (MINUS if n < 0 else "") + f"{abs(n)}/{d}"


# ---------------------------------------------------------------------------------------------
# Bounds (the manifest's "bounds" string), checked on every correct step
# ---------------------------------------------------------------------------------------------
def nonzero_digits(v: Fraction) -> int:
    return sum(ch != "0" for ch in str(int(abs(v) * 10 ** places(v))))


def digits(v: Fraction) -> int:
    """The digits with the point removed: 0.35 -> 35, 4 -> 4."""
    return int(abs(v) * 10 ** places(v))


def carries(x: Fraction, y: Fraction) -> int:
    """Carries (same signs) or borrows (different signs) in the column arithmetic of x + y."""
    k = max(places(x), places(y))
    X, Y = int(abs(x) * 10 ** k), int(abs(y) * 10 ** k)
    n = 0
    if (x < 0) == (y < 0):
        c = 0
        while X or Y or c:
            s = X % 10 + Y % 10 + c
            c = 1 if s >= 10 else 0
            n += c
            X //= 10
            Y //= 10
        return n
    big, small, b = max(X, Y), min(X, Y), 0
    while big:
        d = big % 10 - small % 10 - b
        b = 1 if d < 0 else 0
        n += b
        big //= 10
        small //= 10
    return n


def value_ok(form: str, v: Fraction) -> bool:
    if abs(v) > 12:
        return False
    if v.denominator == 1:
        return True
    if form == "dec":
        k = places(v)
        return k is not None and k <= 2 and nonzero_digits(v) <= 2
    return 2 <= v.denominator <= 12 and abs(v) < 11


def step_ok(form: str, op: str, x: Fraction, y: Fraction) -> bool:
    """One correct step: ``x + y`` (y signed, so a difference is x + (-y)), ``x × y`` or ``x ÷ y``."""
    if op == "+":
        z = x + y
    elif op == "×":
        z = x * y
    else:
        if y == 0:
            return False
        z = x / y
    if not all(value_ok(form, v) for v in (x, y, z)):
        return False
    if op == "+":
        if form == "dec":
            return carries(x, y) <= 1
        if x.denominator != 1 and y.denominator != 1:
            return x.denominator % y.denominator == 0 or y.denominator % x.denominator == 0
        return True
    if form == "dec":
        dx, dy = digits(x), digits(y)
        if op == "×":
            return 2 <= dx <= 10 and 2 <= dy <= 10
        return 2 <= dy <= 10 and dx % dy == 0 and 2 <= dx // dy <= 10 and dx <= 100
    return max(abs(x.numerator), x.denominator, abs(y.numerator), y.denominator) <= 10


def steps_ok(form: str, steps) -> bool:
    return all(step_ok(form, op, x, y) for op, x, y in steps)


# ---------------------------------------------------------------------------------------------
# Misconception rules. Each returns {label: wrong value}; a label is absent where it does not apply.
# ---------------------------------------------------------------------------------------------
def add_rules(a, op, b, is_frac):
    """a + b or a - b (a, b signed, as the prompt shows them)."""
    e = b if op == "+" else -b
    c = a + e
    sa, se, ma, me = sign(a), sign(e), abs(a), abs(e)
    big = a if ma > me else e
    r = {}
    if sa < 0 and se < 0:
        r["NEG_NEG_ADD"] = -c
    if op == "−" and b < 0:
        r["SUB_NEG"] = a + b
    if sa * se < 0 and ma != me:
        r["ADD_SIZES"] = sign(big) * (ma + me)
        r["KEEP_FIRST_SIGN"] = sa * (ma + me)
    if sa * se > 0 and ma != me:
        r["SAME_SIGN_SUB"] = sign(big) * (max(ma, me) - min(ma, me))
    if c != 0:
        r["WRONG_SIGN"] = -c
    if is_frac:
        r["ADD_ACROSS"] = Fraction(a.numerator + e.numerator, a.denominator + e.denominator)
        if a.denominator != e.denominator:
            r["NO_SCALE"] = Fraction(a.numerator + e.numerator, max(a.denominator, e.denominator))
    return r


def story_add_rules(a, op, b, is_frac):
    r = add_rules(a, op, b, is_frac)
    e = b if op == "+" else -b
    r["DIRECTION"] = a - e
    return r


def muldiv_rules(a, op, b, form):
    """a × b or a ÷ b; form is 'frac' (fractions and wholes) or 'dec'."""
    r = {}
    if op == "×":
        c = a * b
        r["SIGN_RULE"] = -c
        r["ADD_FOR_MUL"] = a + b
        if form == "frac":
            if a.denominator != 1 and b.denominator != 1:
                r["ADD_BOTTOMS"] = sign(c) * Fraction(abs(a.numerator * b.numerator),
                                                      a.denominator + b.denominator)
                r["FLIP_MULT"] = a / b
            elif (a.denominator == 1) != (b.denominator == 1):
                w, f = (a, b) if a.denominator == 1 else (b, a)
                r["WHOLE_ON_BOTTOM"] = sign(c) * Fraction(abs(f.numerator), f.denominator * abs(w))
                r["FLIP_MULT"] = a / b
        else:
            both_dec = a.denominator != 1 and b.denominator != 1
            r["POINT_PLACE"] = c * 10 if both_dec else c / 10
    else:
        c = a / b
        r["SIGN_RULE"] = -c
        if form == "frac":
            r["NO_FLIP"] = a * b
            r["FLIP_FIRST"] = 1 / c
        else:
            r["MUL_FOR_DIV"] = a * b
            if b.denominator != 1:
                r["POINT_PLACE"] = c / 10
            r["WRONG_ORDER"] = b / a
    return r


def conv_rules(f):
    """f = a negative or positive fraction in lowest terms; wrong decimals for 'f as a decimal'."""
    n, d, s = abs(f.numerator), f.denominator, sign(f)
    r = {}
    if f < 0:
        r["DROPPED_SIGN"] = -f
    r["FLIPPED"] = s * Fraction(d, n)
    glued = f"{n}{d}"
    r["DIGITS_AS_DECIMAL"] = s * Fraction(int(glued), 10 ** len(glued))
    if d <= 9:
        r["DENOM_ONLY"] = s * Fraction(d, 10)
    if n > 1:
        r["UNIT_ONLY"] = s * Fraction(1, d)
    if places(f) is not None:
        r["POINT_PLACE"] = f * 10
    else:
        r["TRUNCATED"] = s * Fraction(int(abs(f) * 10), 10)
    # Never a wrong door within 0.05 of the answer: 0.3 for 1/3 or 0.7 for 0.75 is "close enough" to a sharp kid.
    return {k: v for k, v in r.items() if abs(v - f) >= Fraction(1, 20)}


def form_rules(target):
    """Wrong forms for 'Which equals <target>?' where target = -n/d or n/d (lowest terms, n >= 2)."""
    r = {"FLIPPED": 1 / target}
    if target < 0:
        r["DOUBLE_NEG"] = -target
        r["DROPPED_SIGN"] = -target
    else:
        r["NEG_STAYS"] = -target
    return r


def e1_rules(a, b, op, c):
    """a × (b op c)."""
    e = c if op == "+" else -c
    inner = b + e
    r = {"ORDER": a * b + e}
    if op == "−" and c < 0:
        r["SUB_NEG"] = a * (b + c)
    if sign(b) * sign(e) < 0 and abs(b) != abs(e):
        r["ADD_SIZES"] = a * sign(b if abs(b) > abs(e) else e) * (abs(b) + abs(e))
    r["SIGN_RULE"] = -(a * inner)
    return r


def e2_rules(a, op, b, c):
    """a op (b × c)."""
    p = b * c
    e = p if op == "+" else -p
    r = {"ORDER": ((a + b) if op == "+" else (a - b)) * c}
    if sign(a) * sign(e) < 0 and abs(a) != abs(e):
        r["ADD_SIZES"] = sign(a if abs(a) > abs(e) else e) * (abs(a) + abs(e))
    r["SIGN_RULE"] = a - e
    if a + e != 0:
        r["WRONG_SIGN"] = -(a + e)
    return r


def e3_rules(a, op, b, c):
    """(a op b) ÷ c."""
    e = b if op == "+" else -b
    inner = a + e
    r = {"ORDER": a + e / c, "MUL_FOR_DIV": inner * c}
    if sign(a) * sign(e) < 0 and abs(a) != abs(e):
        r["ADD_SIZES"] = sign(a if abs(a) > abs(e) else e) * (abs(a) + abs(e)) / c
    r["SIGN_RULE"] = -(inner / c)
    return r


def rate_rules(r_, n, form):
    """rate × count."""
    c = r_ * n
    out = {"SIGN_RULE": -c, "ADD_FOR_MUL": r_ + n}
    if form == "frac":
        out["WHOLE_ON_BOTTOM"] = sign(c) * Fraction(abs(r_.numerator), r_.denominator * n)
    else:
        out["POINT_PLACE"] = c / 10
    return out


def dist_rules(a, b):
    """Distance between a < 0 < b."""
    return {"SUBTRACT_SIZES": abs(abs(b) - abs(a)), "NEG_DISTANCE": -(b - a),
            "ONE_SIDE": max(abs(a), abs(b))}


_ADD = ["NEG_NEG_ADD", "SUB_NEG", "ADD_SIZES", "KEEP_FIRST_SIGN", "SAME_SIGN_SUB", "WRONG_SIGN"]
ORDERS = {
    "add_dec": _ADD,
    "add_frac": ["NEG_NEG_ADD", "SUB_NEG", "ADD_ACROSS", "NO_SCALE", "ADD_SIZES", "KEEP_FIRST_SIGN", "SAME_SIGN_SUB",
                 "WRONG_SIGN"],
    "story_add": ["DIRECTION"] + _ADD,
    "story_add_frac": ["DIRECTION", "NEG_NEG_ADD", "ADD_ACROSS", "NO_SCALE", "ADD_SIZES", "KEEP_FIRST_SIGN",
                       "SAME_SIGN_SUB", "WRONG_SIGN"],
    "fmul": ["SIGN_RULE", "WHOLE_ON_BOTTOM", "ADD_BOTTOMS", "FLIP_MULT", "ADD_FOR_MUL"],
    "fdiv": ["SIGN_RULE", "NO_FLIP", "FLIP_FIRST"],
    "dmul": ["SIGN_RULE", "POINT_PLACE", "ADD_FOR_MUL"],
    "ddiv": ["SIGN_RULE", "POINT_PLACE", "MUL_FOR_DIV", "WRONG_ORDER"],
    "term": ["DROPPED_SIGN", "FLIPPED", "DIGITS_AS_DECIMAL", "DENOM_ONLY", "UNIT_ONLY", "POINT_PLACE"],
    "rep": ["DROPPED_SIGN", "FLIPPED", "TRUNCATED", "DIGITS_AS_DECIMAL", "DENOM_ONLY", "UNIT_ONLY"],
    "formA": ["DOUBLE_NEG", "DROPPED_SIGN", "FLIPPED"],  # DOUBLE_NEG / DROPPED_SIGN: one of the two (same value)
    "formB": ["NEG_STAYS", "FLIPPED"],
    "e1": ["ORDER", "SUB_NEG", "ADD_SIZES", "SIGN_RULE"],
    "e2": ["ORDER", "ADD_SIZES", "SIGN_RULE", "WRONG_SIGN"],
    "e3": ["ORDER", "MUL_FOR_DIV", "ADD_SIZES", "SIGN_RULE"],
    "rate_dec": ["SIGN_RULE", "ADD_FOR_MUL", "POINT_PLACE"],
    "rate_frac": ["SIGN_RULE", "WHOLE_ON_BOTTOM", "ADD_FOR_MUL"],
    "dist": ["SUBTRACT_SIZES", "NEG_DISTANCE", "ONE_SIDE"],
}


# ---------------------------------------------------------------------------------------------
# Explanations (<= 160 characters, each ends with the answer)
# ---------------------------------------------------------------------------------------------
def expl_add(a, op, b, form, f):
    e = b if op == "+" else -b
    c = a + e
    head = "" if op == "+" else f"Subtracting {f(b)} is adding {f(e)}. "
    if form == "dec":
        word = "negative" if (c < 0) else "positive"
        if sign(a) * sign(e) < 0:
            big, small = (a, e) if abs(a) > abs(e) else (e, a)
            word = "negative" if big < 0 else "positive"
            body = (f"Signs differ: {f(abs(big))} − {f(abs(small))} = {f(abs(c))}, and the bigger "
                    f"one is {word}, so {f(c)}.")
        else:
            body = f"Same signs: {f(abs(a))} + {f(abs(e))} = {f(abs(c))}, both {word}, so {f(c)}."
        return head + body
    D = max(a.denominator, e.denominator)
    na, ne = a.numerator * (D // a.denominator), e.numerator * (D // e.denominator)
    raw = sfrac(na + ne, D)
    mid = f"{sfrac(na, D)} + " + (f"({sfrac(ne, D)})" if ne < 0 else sfrac(ne, D))
    tail = "" if raw == f(c) else f" = {f(c)}"
    return head + f"Common bottom {D}: {mid} = {raw}{tail}."


def _neg_count(a, b):
    return (a < 0) + (b < 0)


def _sign_text(a, b):
    return "One negative, so negative." if _neg_count(a, b) == 1 else "Two negatives, so positive."


def expl_mul_frac(a, op, b, c):
    sg = _sign_text(a, b)
    aa, bb = abs(a), abs(b)
    if op == "×":
        N, D = aa.numerator * bb.numerator, aa.denominator * bb.denominator
        mid = f"{aa.numerator}×{bb.numerator} over {aa.denominator}×{bb.denominator} = "
    else:
        N, D = aa.numerator * bb.denominator, aa.denominator * bb.numerator
        recip = str(bb.denominator) if bb.numerator == 1 else f"{bb.denominator}/{bb.numerator}"
        mid = f"Flip the divisor: {frac(aa)} × {recip} = "
    raw = str(N) if D == 1 else f"{N}/{D}"
    tail = "" if raw == frac(abs(c)) else f" = {frac(abs(c))}"
    return f"{sg} {mid}{raw}{tail}, so {frac(c)}."


def expl_mul_dec(a, op, b, c):
    sg = _sign_text(a, b)
    dx, dy = digits(a), digits(b)
    if op == "×":
        pl = places(a) + places(b)
        unit = "decimal place" if pl == 1 else "decimal places"
        return f"{sg} Digits: {dx} × {dy} = {dx * dy}; {pl} {unit} in all, so {dec(c)}."
    return f"{sg} Digits: {dx} ÷ {dy} = {dx // dy}, then place the point: {dec(c)}."


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def arith_pool(c: Fraction, form: str, rng: random.Random):
    """Near misses of c: a one-unit slip in the last place (or numerator / denominator)."""
    if form in ("dec", "money"):
        unit = Fraction(1, 10 ** (places(c) or 0))
        near = [unit, Fraction(1, 10)] if form == "dec" else [Fraction(1, 2)]
        cands = [c + s for s in near] + [c - s for s in near]
        rng.shuffle(cands)
        far = [c + 1, c - 1]
        rng.shuffle(far)
        return [v for v in cands + far if v != 0]
    if form == "rep":
        cands = [c + Fraction(1, 9), c - Fraction(1, 9), c + 1, c - 1]
    elif form == "term":
        cands = [c + Fraction(1, 10), c - Fraction(1, 10), c + Fraction(1, 4), c - Fraction(1, 4)]
    else:
        p, q = c.numerator, c.denominator
        cands = [Fraction(p + 1, q), Fraction(p - 1, q), Fraction(p, q + 1), c + 1, c - 1]
        if q > 2:
            cands.append(Fraction(p, q - 1))
    rng.shuffle(cands)
    return [v for v in cands if v != 0]


def make_item(tier, case, pos, rng):
    """Case -> item dict, or None when the case cannot supply enough distinct, displayable choices."""
    fmt, correct, rules = case["fmt"], case["correct"], case["rules"]
    want = case.get("choices", 4) - 1
    ctext = case.get("correct_text") or fmt(correct)
    if ctext is None or len(ctext) > MAX_CHOICE:
        return None
    texts = case.get("texts", {})
    seen, wrong = {correct}, []
    for lab in case["order"]:
        v = rules.get(lab)
        if v is None or v in seen or abs(v) > MAX_DISTRACTOR:
            continue
        t = texts.get(lab) or fmt(v)
        if t is None or len(t) > MAX_CHOICE:
            continue
        seen.add(v)
        wrong.append((lab, v, t))
    if len(wrong) > want:
        keep = [w for w in wrong if w[0] in case.get("must_keep", ())]
        rest = [w for w in wrong if w not in keep]
        rng.shuffle(rest)
        keep = (keep + rest)[:want]
        wrong = [w for w in wrong if w in keep]
    used = {correct} | {v for v in rules.values() if v is not None}
    if len(wrong) < want and not case.get("no_arith"):
        for v in arith_pool(correct, case["pool"], rng):
            if len(wrong) == want:
                break
            t = fmt(v)
            if v in used or t is None or len(t) > MAX_CHOICE or abs(v) > MAX_DISTRACTOR:
                continue
            used.add(v)
            wrong.append(("ARITH", v, t))
    if len(wrong) < want or not any(lab != "ARITH" for lab, _, _ in wrong):
        return None
    if len(case["prompt"]) > 60 or len(case["expl"]) > 160:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:pos] + [(None, correct, ctext)] + wrong[pos:]
    return {
        "tier": tier,
        "prompt": case["prompt"],
        "choices": [t for _, _, t in pairs],
        "answer": pos,
        "misconceptions": [lab for lab, _, _ in pairs],
        "explanation": case["expl"],
    }


def _case(prompt, correct, rules, order, fmt, expl, pool, **kw):
    d = {"prompt": prompt, "correct": correct, "rules": rules, "order": order, "fmt": fmt,
         "expl": expl, "pool": pool}
    d.update(kw)
    return d


# --- add / subtract (T1, T2, T5 stories) ---------------------------------------------------------
PATTERNS = [(-1, "+", 1), (-1, "+", -1), (1, "+", -1), (-1, "−", 1), (-1, "−", -1), (1, "−", 1), (1, "−", -1)]


def add_case(a, op, b, form, order_key, f=None, prompt=None, lead="", story=False, pool=None):
    f = f or (dec if form == "dec" else frac)
    e = b if op == "+" else -b
    c = a + e
    if c == 0 or not steps_ok(form, [("+", a, e)]):
        return None
    if sign(a) * sign(e) > 0 and abs(a) == abs(e):
        return None  # 0.3 + 0.3: SAME_SIGN_SUB would be 0 and the item has nothing to subtract
    is_frac = form == "frac"
    rules = (story_add_rules if story else add_rules)(a, op, b, is_frac)
    prompt = prompt or f"{term(a, f, True)} {op} {term(b, f, False)}"
    return _case(prompt, c, rules, ORDERS[order_key], f, lead + expl_add(a, op, b, form, f),
                 pool or ("dec" if form == "dec" else "frac"))


def build_t1(rng, kind):
    sa, op, sb = PATTERNS[kind]
    ta, tb = rng.randint(1, 19), rng.randint(1, 19)
    if ta == 10 or tb == 10:
        return None
    a, b = Fraction(sa * ta, 10), Fraction(sb * tb, 10)
    if abs(a + (b if op == "+" else -b)) > 2:
        return None
    if (sa, op, sb) == (1, "−", 1) and b < a:
        return None  # 0.9 − 0.6 is a plain subtraction; keep only the ones that cross zero
    return add_case(a, op, b, "dec", "add_dec")


T2_DENS = (2, 3, 4, 5, 6, 8, 9, 10, 12)


def _proper(rng, d):
    n = rng.randint(1, d - 1)
    return n if gcd(n, d) == 1 else None


def build_t2(rng, kind):
    pat, like = kind
    sa, op, sb = PATTERNS[pat]
    if like:
        d1 = rng.randint(3, 12)
        d2 = d1
    else:
        d1 = rng.choice(T2_DENS)
        opts = [d for d in range(2, 13) if d != d1 and (d % d1 == 0 or d1 % d == 0)]
        if not opts:
            return None
        d2 = rng.choice(opts)
    n1, n2 = _proper(rng, d1), _proper(rng, d2)
    if n1 is None or n2 is None:
        return None
    a, b = Fraction(sa * n1, d1), Fraction(sb * n2, d2)
    if abs(a) == abs(b) and like:
        return None
    if (sa, op, sb) == (1, "−", 1) and b < a:
        return None  # a plain subtraction of a smaller positive; keep only the ones that cross zero
    return add_case(a, op, b, "frac", "add_frac")


# --- multiply / divide (T3) ----------------------------------------------------------------------
SIGNS = [(-1, 1), (1, -1), (-1, -1)]


def _fraction_ok(c):
    """T3 answer: simplest form, denominator and numerator at most 12, magnitude at most 12."""
    return abs(c) <= 12 and c.denominator <= 12 and abs(c.numerator) <= 12


def build_t3(rng, kind):
    sa, sb = rng.choice(SIGNS)
    if kind in ("fm", "fd", "fwm", "fwd"):
        d1 = rng.randint(2, 10)
        n1 = _proper(rng, d1)
        if kind in ("fm", "fd"):
            d2 = rng.randint(2, 10)
            n2 = _proper(rng, d2)
            b_abs = Fraction(n2, d2) if n2 else None
        else:
            b_abs = Fraction(rng.randint(2, 10))
        if n1 is None or b_abs is None:
            return None
        a_abs = Fraction(n1, d1)
        if kind == "fwm" and rng.random() < 0.5:
            a_abs, b_abs = b_abs, a_abs  # whole × fraction
        if kind == "fwd" and rng.random() < 0.5:
            a_abs, b_abs = b_abs, a_abs  # whole ÷ fraction
        a, b = sa * a_abs, sb * b_abs
        op = "×" if kind in ("fm", "fwm") else "÷"
        if abs(a) == abs(b):
            return None
        c = a * b if op == "×" else a / b
        if not _fraction_ok(c) or not steps_ok("frac", [(op, a, b)]):
            return None
        f = frac
        return _case(f"{term(a, f, True)} {op} {term(b, f, False)}", c, muldiv_rules(a, op, b, "frac"),
                     ORDERS["fmul" if op == "×" else "fdiv"], f, expl_mul_frac(a, op, b, c), "frac",
                     must_keep=("SIGN_RULE",))
    # decimals
    if kind in ("dmw", "dmd"):
        t = rng.randint(2, 9)
        a_abs = Fraction(t, 10)
        b_abs = Fraction(rng.randint(2, 10)) if kind == "dmw" else Fraction(rng.randint(2, 9), 10)
        a, b = sa * a_abs, sb * b_abs
        if kind == "dmw" and rng.random() < 0.5:
            a, b = b, a  # whole × decimal
        op = "×"
    else:
        q = rng.randint(2, 9)
        k = rng.randint(2, 10)
        if kind == "ddd":
            a_abs, b_abs = Fraction(q * k, 10), Fraction(q, 10)
        else:
            a_abs, b_abs = Fraction(q * k, 10), Fraction(q)
        if a_abs.denominator == 1 or a_abs > 9:
            return None
        a, b, op = sa * a_abs, sb * b_abs, "÷"
    c = a * b if op == "×" else a / b
    if not steps_ok("dec", [(op, a, b)]):
        return None
    f = dec
    return _case(f"{term(a, f, True)} {op} {term(b, f, False)}", c, muldiv_rules(a, op, b, "dec"),
                 ORDERS["dmul" if op == "×" else "ddiv"], f, expl_mul_dec(a, op, b, c), "dec",
                 must_keep=("SIGN_RULE",))


# --- fractions as decimals (T4) ------------------------------------------------------------------
TERM_DENS = (2, 4, 4, 5, 5, 10, 20, 20, 25, 25)
REP_DENS = (3, 9, 9, 9)


def expl_conv(f, rep_):
    n, d = abs(f.numerator), f.denominator
    if rep_:
        pos = dec_or_rep(abs(f))
        return f"{n} ÷ {d} repeats forever: {pos}" + (f", so {dec_or_rep(f)}" if f < 0 else "")
    if d == 10:
        mid = f"{n}/10 = {dec(abs(f))}"
    else:
        base = 10 if d in (2, 5) else 100
        mid = f"{n}/{d} = {n * (base // d)}/{base} = {dec(abs(f))}"
    return mid + (f", so {dec(f)}." if f < 0 else ".")


def build_t4(rng, kind):
    if kind in ("term", "rep"):
        d = rng.choice(TERM_DENS if kind == "term" else REP_DENS)
        n = rng.randint(1, min(d - 1, 12))
        if gcd(n, d) != 1:
            return None
        f = rng.choice((-1, 1)) * Fraction(n, d)
        style = rng.randint(0, 2)
        prompt = (f"{frac(f)} as a decimal?", f"Write {frac(f)} as a decimal.",
                  f"Convert {frac(f)} to a decimal.")[style]
        rules = conv_rules(f)
        return _case(prompt, f, rules, ORDERS[kind], dec_or_rep, expl_conv(f, kind == "rep"),
                     "term" if kind == "term" else "rep", key=("conv", f),
                     must_keep=("FLIPPED", "DIGITS_AS_DECIMAL") if kind == "term" else ("TRUNCATED", "FLIPPED"))
    d = rng.randint(3, 12)
    n = rng.randint(2, d - 1)
    if gcd(n, d) != 1:
        return None
    L, R = f"{n}/{d}", f"{d}/{n}"
    if kind == "formA":  # Which equals -n/d?  (the correct forms: n/(-d) or (-n)/d)
        target = -Fraction(n, d)
        style = rng.randint(0, 1)
        correct_text = f"{n}/({MINUS}{d})" if style == 0 else f"({MINUS}{n})/{d}"
        flipped = f"{d}/({MINUS}{n})" if style == 0 else f"({MINUS}{d})/{n}"
        first = rng.choice(("DOUBLE_NEG", "DROPPED_SIGN"))
        texts = {"DOUBLE_NEG": f"{MINUS}{n}/({MINUS}{d})", "DROPPED_SIGN": L, "FLIPPED": flipped}
        order = [first, "FLIPPED"]
        expl = (f"A minus sign on the top, the bottom or the front means the same: "
                f"{MINUS}{L} = {correct_text}.")
        prompt = f"Which equals {MINUS}{L}?"
    else:  # Which equals n/d?  (the correct forms: -n/(-d) or (-n)/(-d))
        target = Fraction(n, d)
        style = rng.randint(0, 1)
        correct_text = f"{MINUS}{n}/({MINUS}{d})" if style == 0 else f"({MINUS}{n})/({MINUS}{d})"
        neg = f"{n}/({MINUS}{d})" if rng.random() < 0.5 else f"({MINUS}{n})/{d}"
        texts = {"NEG_STAYS": neg, "FLIPPED": R}
        order = ["NEG_STAYS", "FLIPPED"]
        expl = f"Two negatives cancel: {correct_text} = {L}."
        prompt = f"Which equals {L}?"
    return _case(prompt, target, form_rules(target), order, lambda v: None, expl, "frac",
                 key=("form", kind, n, d), texts=texts, correct_text=correct_text, choices=3,
                 no_arith=True)


# --- stories and two steps (T5) ------------------------------------------------------------------
def _tenths(rng, lo, hi, s=1):
    return Fraction(s * rng.randint(lo, hi), 10)


def build_sA(rng):
    a = _tenths(rng, 1, 39, rng.choice((-1, 1)))
    b = _tenths(rng, 5, 39)
    op = rng.choice(("+", "−"))
    if a > 0 and op == "+":
        return None
    if a > 0 and a - b > 0:
        return None  # 2.5 drops 1.5 never crosses zero: not a signed-number story
    word = "rises" if op == "+" else "drops"
    prompt = f"Temp is {dec(a)} degrees, then {word} {dec(b)} degrees. Now?"
    lead = "Rises means add. " if op == "+" else "Drops means subtract. "
    return add_case(a, op, b, "dec", "story_add", prompt=prompt, lead=lead, story=True)


def build_sB(rng, is_frac):
    op = rng.choice(("+", "−"))
    if is_frac:
        d1, d2 = rng.choice(T2_DENS), rng.choice(T2_DENS)
        if not (d1 % d2 == 0 or d2 % d1 == 0):
            return None
        n1, n2 = _proper(rng, d1), _proper(rng, d2)
        if n1 is None or n2 is None:
            return None
        a, b, f, form = Fraction(-n1, d1), Fraction(n2, d2), frac, "frac"
    else:
        a, b, f, form = _tenths(rng, 5, 49, -1), _tenths(rng, 5, 39), dec, "dec"
    if op == "+":
        prompt = f"Diver at {f(a)} m swims up {f(b)} m. New elevation?"
        lead = "Up means add. "
    else:
        prompt = f"Diver at {f(a)} m dives {f(b)} m deeper. New elevation?"
        lead = "Deeper means subtract. "
    return add_case(a, op, b, form, "story_add_frac" if is_frac else "story_add", f=f, prompt=prompt,
                    lead=lead, story=True)


def build_sC(rng):
    a = Fraction(rng.choice((-1, 1)) * rng.randint(1, 19), 2)
    b = Fraction(rng.randint(2, 19), 2)
    op = rng.choice(("+", "−"))
    if a > 0 and op == "+":
        return None
    if a > 0 and a - b > 0:
        return None
    word = "deposit" if op == "+" else "spend"
    prompt = f"Balance is {money(a)}. You {word} {money(b)}. New balance?"
    lead = "Deposit means add. " if op == "+" else "Spend means subtract. "
    return add_case(a, op, b, "dec", "story_add", f=money, prompt=prompt, lead=lead, story=True, pool="money")


def build_sD(rng, kind):
    n = rng.randint(2, 10)
    if kind == "dec":
        r_, form, f = Fraction(-rng.randint(2, 9), 10), "dec", dec
        prompt = f"Temp changes {dec(r_)} degrees an hour for {n} hours. Total?"
    elif kind == "money":
        r_, form, f = Fraction(-rng.choice((Fraction(1, 2), 2, 3, 4, 5))), "dec", money
        prompt = f"Account changes {money(r_)} a day for {n} days. Total?"
    else:
        d = rng.randint(2, 6)
        k = _proper(rng, d)
        if k is None:
            return None
        r_, form, f = Fraction(-k, d), "frac", frac
        prompt = f"Water level changes {frac(r_)} inch a day for {n} days. Total?"
    c = r_ * n
    if not steps_ok(form, [("×", r_, Fraction(n))]) or c == 0:
        return None
    if form == "frac":
        raw = abs(r_.numerator) * n
        D = r_.denominator
        mid = f"{abs(r_.numerator)}×{n} over {D} = {raw}/{D}"
        tail = "" if frac(abs(c)) == f"{raw}/{D}" else f" = {frac(abs(c))}"
        expl = f"{n} days of {frac(r_)}: one negative, so negative. {mid}{tail}, so {frac(c)}."
    else:
        expl = (f"{n} groups of {f(r_)}: one negative, so negative. "
                f"Digits {digits(r_)} × {n} = {digits(r_) * n}, so {f(c)}.")
    return _case(prompt, c, rate_rules(r_, n, form), ORDERS["rate_frac" if form == "frac" else "rate_dec"],
                 f, expl, "frac" if form == "frac" else ("money" if kind == "money" else "dec"),
                 must_keep=("ADD_FOR_MUL",))


def build_sE(rng):
    a, b = _tenths(rng, 5, 39, -1), _tenths(rng, 5, 39)
    if not steps_ok("dec", [("+", b, -a)]):
        return None
    c = b - a
    if rng.random() < 0.5:
        prompt = f"Temps are {dec(a)} and {dec(b)} degrees. How far apart?"
    else:
        prompt = f"A diver at {dec(a)} m and a bird at {dec(b)} m. Distance apart?"
    expl = (f"Across zero, add the sizes: {dec(abs(a))} + {dec(b)} = {dec(c)}. "
            f"Distance is |{dec(b)} − ({dec(a)})| = {dec(c)}.")
    return _case(prompt, c, dist_rules(a, b), ORDERS["dist"], dec, expl, "dec")


def _int_term(v, first):
    s = (MINUS if v < 0 else "") + str(abs(v))
    return s if first or v >= 0 else f"({s})"


def build_e1(rng, form):
    """a × (b op c): finish the parentheses first."""
    s = rng.choice((-1, 1))
    if form == "frac":
        d = rng.choice((2, 3, 4, 5))
        n = rng.choice((1, 1, 1, 3)) if d > 3 else 1
        a, f = s * Fraction(n, d), frac
    else:
        a, f = s * Fraction(rng.randint(2, 9), 10), dec
    b = rng.randint(-10, 10)
    op = rng.choice(("+", "−"))
    c = rng.randint(2, 10) * (1 if rng.random() < (0.5 if op == "−" else 0.75) else -1)
    e = c if op == "+" else -c
    inner = b + e
    if abs(b) < 2 or abs(inner) < 2 or abs(inner) > 10:
        return None
    if a > 0 and b > 0 and e > 0:
        return None  # no negative anywhere: the sign rules would have nothing to catch
    val = a * inner
    if not steps_ok(form, [("+", Fraction(b), Fraction(e)), ("×", a, Fraction(inner))]):
        return None
    if form == "frac" and rng.random() < 0.75 and inner % a.denominator:
        return None  # mostly whole answers
    sub = f"{_int_term(b, True)} {op} {_int_term(c, False)}"
    expl = f"Inside first: {sub} = {_int_term(inner, True)}. Then {f(a)} × {_int_term(inner, False)} = {f(val)}."
    return _case(f"{f(a)} × ({sub})", val, e1_rules(a, Fraction(b), op, Fraction(c)), ORDERS["e1"], f, expl,
                 "frac" if form == "frac" else "dec", must_keep=("ORDER",))


def build_e2(rng, form):
    """a op b × c: multiply before you add."""
    op = rng.choice(("+", "−"))
    if form == "frac":
        d = rng.choice((2, 3, 4, 6, 8))
        n = _proper(rng, d)
        d2 = rng.choice((2, 3, 4))
        n2 = _proper(rng, d2)
        if n is None or n2 is None:
            return None
        a = rng.choice((-1, 1)) * Fraction(n, d)
        b = rng.choice((-1, 1)) * Fraction(n2, d2)
        c = Fraction(rng.randint(2, 6) * (1 if rng.random() < 0.75 else -1))
        f = frac
    else:
        a, b, f = _tenths(rng, 1, 29, rng.choice((-1, 1))), _tenths(rng, 2, 9, rng.choice((-1, 1))), dec
        c = Fraction(rng.randint(2, 10) * (1 if rng.random() < 0.75 else -1))
    if (a > 0 and b > 0 and c > 0 and op == "+") or abs(a) == abs(b):
        return None
    p = b * c
    e = p if op == "+" else -p
    val = a + e
    if val == 0 or abs(p) > (4 if form == "frac" else 9) or abs(p) < Fraction(1, 2):
        return None
    if not steps_ok(form, [("×", b, c), ("+", a, e)]):
        return None
    prompt = f"{f(a)} {op} {term(b, f, False)} × {term(c, f, False)}"
    expl = (f"Multiply first: {f(b)} × {term(c, f, False)} = {f(p)}. "
            f"Then {f(a)} {op} {term(p, f, False)} = {f(val)}.")
    return _case(prompt, val, e2_rules(a, op, b, c), ORDERS["e2"], f, expl,
                 "frac" if form == "frac" else "dec", must_keep=("ORDER",))


def build_e3(rng, form):
    """(a op b) ÷ c: the parentheses first, then divide."""
    op = rng.choice(("+", "−"))
    c = Fraction(rng.randint(2, 5 if form == "frac" else 9) * (1 if rng.random() < 0.7 else -1))
    if form == "frac":
        d1 = rng.choice((2, 3, 4, 6, 8, 12))
        d2 = rng.choice([d for d in range(2, 13) if d % d1 == 0 or d1 % d == 0])
        n1, n2 = _proper(rng, d1), _proper(rng, d2)
        if n1 is None or n2 is None:
            return None
        a, b, f = rng.choice((-1, 1)) * Fraction(n1, d1), rng.choice((-1, 1)) * Fraction(n2, d2), frac
    else:
        a, b, f = _tenths(rng, 1, 19, rng.choice((-1, 1))), _tenths(rng, 1, 19, rng.choice((-1, 1))), dec
    e = b if op == "+" else -b
    inner = a + e
    if (a > 0 and e > 0 and c > 0) or abs(a) == abs(b):
        return None
    if inner == 0 or abs(inner) == abs(a) or not steps_ok(form, [("+", a, e), ("÷", inner, c)]):
        return None
    val = inner / c
    sub = f"{f(a)} {op} {term(b, f, False)}"
    expl = f"Inside first: {sub} = {f(inner)}. Then {f(inner)} ÷ {term(c, f, False)} = {f(val)}."
    return _case(f"({sub}) ÷ {term(c, f, False)}", val, e3_rules(a, op, b, c), ORDERS["e3"], f, expl,
                 "frac" if form == "frac" else "dec", must_keep=("ORDER",))


def build_t5(rng, kind):
    if kind == "sA":
        return build_sA(rng)
    if kind == "sBd":
        return build_sB(rng, False)
    if kind == "sBf":
        return build_sB(rng, True)
    if kind == "sC":
        return build_sC(rng)
    if kind in ("sDd", "sDm", "sDf"):
        return build_sD(rng, {"sDd": "dec", "sDm": "money", "sDf": "frac"}[kind])
    if kind == "sE":
        return build_sE(rng)
    form = "frac" if kind.endswith("f") else "dec"
    return {"e1": build_e1, "e2": build_e2, "e3": build_e3}[kind[:2]](rng, form)


# ---------------------------------------------------------------------------------------------
# Tier plans
# ---------------------------------------------------------------------------------------------
def _shuffled(kinds, rng):
    kinds = list(kinds)
    rng.shuffle(kinds)
    return kinds


def plan(tier, count, rng):
    if tier == 1:
        return _shuffled([i % 7 for i in range(count)], rng)
    if tier == 2:
        return _shuffled([(i % 7, i % 5 < 2) for i in range(count)], rng)
    if tier == 3:
        base = ["fm"] * 8 + ["fd"] * 8 + ["fwm"] * 4 + ["fwd"] * 4 + ["dmw"] * 4 + ["dmd"] * 4 + ["ddd"] * 4 + ["ddw"] * 4
    elif tier == 4:
        base = ["term"] * 22 + ["rep"] * 10 + ["formA"] * 4 + ["formB"] * 4
    else:
        base = (["sA"] * 4 + ["sBd"] * 2 + ["sBf"] * 3 + ["sC"] * 3 + ["sDd"] * 2 + ["sDm"] + ["sDf"] * 2 +
                ["sE"] * 3 + ["e1d"] * 3 + ["e1f"] * 4 + ["e2d"] * 4 + ["e2f"] * 3 + ["e3d"] * 3 + ["e3f"] * 3)
    kinds = [base[i % len(base)] for i in range(count)]
    return _shuffled(kinds, rng)


BUILDERS = {1: build_t1, 2: build_t2, 3: build_t3, 4: build_t4, 5: build_t5}
THREE_CHOICE = ("formA", "formB")


def _positions(kinds, rng):
    """Answer positions balanced separately for the 3-choice and the 4-choice items."""
    pos = [0] * len(kinds)
    for k in (3, 4):
        idx = [i for i, kd in enumerate(kinds) if (3 if kd in THREE_CHOICE else 4) == k]
        xs = [j % k for j in range(len(idx))]
        rng.shuffle(xs)
        for i, x in zip(idx, xs):
            pos[i] = x
    return pos


def gen_tier(tier, count, rng, max_attempts=400000):
    kinds = plan(tier, count, rng)
    pos = _positions(kinds, rng)
    items, keys = [], set()
    attempts = 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items (stuck on {kinds[len(items)]!r})")
        i = len(items)
        case = BUILDERS[tier](rng, kinds[i])
        if case is None:
            continue
        key = case.get("key", case["prompt"])
        if key in keys or case["prompt"] in keys:
            continue
        item = make_item(tier, case, pos[i], rng)
        if item is None:
            continue
        keys.add(key)
        keys.add(case["prompt"])
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
