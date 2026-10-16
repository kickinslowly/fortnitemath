"""Procedural generator for the exponent-rules cartridge (grade 8, 8.EE.A.1; fnm-cart/1).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every item comes from a *spec*: prompt, the correct choice, a list of misconception candidates
  ``(key, display, value)`` and a list of ARITH fillers. A candidate is the exact choice a student
  holding that one wrong rule would pick; the candidate functions (``t2_cands`` ...) are pure and
  the tests call them directly.
* Values are ``Fraction``s. Two choices with the same value are never offered together (the
  later one is dropped), so ``2^8`` / ``4^4`` style double-right doors cannot happen.
* Bounds (PROTOCOL §4b Exponents): bases 2-10, every exponent shown or reached has size <= 12.
  Candidates that would break a bound are dropped, not rewritten. A plain number is shown only if
  it is a power of 10, 1, the base, or size <= 100 (and 1 over such a number).
* Answer positions are balanced per tier within each choice-count group.
"""
from __future__ import annotations

import random
from fractions import Fraction

MINUS = "−"  # U+2212
MAX_EXP = 12


# --------------------------------------------------------------------------------------------
# Display and value helpers
# --------------------------------------------------------------------------------------------
def sg(e: int) -> str:
    """Signed integer text: 5, −3."""
    return str(e) if e >= 0 else MINUS + str(-e)


def P(b: int, e: int):
    """A power as a choice: (display, value). Callers check the bound."""
    return (f"{b}^{sg(e)}", Fraction(b) ** e)


def fnum(v: Fraction) -> str:
    s = MINUS if v < 0 else ""
    v = abs(v)
    return s + (str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}")


def V(v) -> tuple:
    v = Fraction(v)
    return (fnum(v), v)


def is_pow10(n: int) -> bool:
    s = str(n)
    return n >= 10 and s[0] == "1" and set(s[1:]) <= {"0"}


def show_ok(v: Fraction) -> bool:
    """A plain value may be shown: 0, 1, size <= 100, a power of 10 (<= 10^6), or 1 over those (<= 10^4)."""
    a = abs(v)
    if a.denominator == 1:
        n = a.numerator
        return n <= 100 or (is_pow10(n) and n <= 10 ** 6)
    if a.numerator == 1:
        d = a.denominator
        return d <= 100 or (is_pow10(d) and d <= 10 ** 4)
    return False


def exp_ok(e: int) -> bool:
    return abs(e) <= MAX_EXP


def add_str(m: int, n: int) -> str:
    return f"{sg(m)} + ({sg(n)})" if n < 0 else f"{sg(m)} + {n}"


def sub_str(m: int, n: int) -> str:
    return f"{sg(m)} − ({sg(n)})" if n < 0 else f"{sg(m)} − {n}"


def sum_str(xs) -> str:
    return " + ".join(sg(x) if (x >= 0 or i == 0) else f"({sg(x)})" for i, x in enumerate(xs))


def mul_str(m: int, n: int) -> str:
    return f"{sg(m)} × ({sg(n)})" if n < 0 else f"{sg(m)} × {n}"


def around(b: int, r: int):
    """ARITH fillers: the same base, an exponent one or two off."""
    return [P(b, r + d) for d in (1, -1, 2, -2) if exp_ok(r + d)]


def around_int(r: int):
    return [V(r + d) for d in (1, -1, 2, -2) if exp_ok(r + d)]


# --------------------------------------------------------------------------------------------
# Tier 1: zero and negative exponents
# --------------------------------------------------------------------------------------------
def t1_zero_cands(b: int):
    return [("ZERO_IS_ZERO",) + V(0), ("ZERO_KEEPS_BASE",) + V(b)]


def t1_neg_cands(b: int, n: int):
    """Choices for b^−n asked as a value."""
    p = Fraction(b) ** n
    return [
        ("NEG_VALUE",) + V(-p),
        ("NEG_TIMES",) + V(-b * n),
        ("NEG_FRACTION",) + V(-1 / p),
        ("IGNORE_SIGN",) + V(p),
        ("TIMES_FOR_POWER",) + V(b * n),
        ("RECIP_TIMES",) + V(Fraction(1, b * n)),
    ]


def t1_which_cands(b: int, n: int):
    """Choices for 'Which equals 1/b^n?'; the right one is b^−n."""
    p = Fraction(b) ** n
    out = [
        ("IGNORE_SIGN",) + P(b, n),
        ("NEG_VALUE", f"{MINUS}({b}^{n})", -p),
        ("NEG_FRACTION", f"{MINUS}({b}^{sg(-n)})", -1 / p),
    ]
    if n >= 2:
        out.append(("SWAP_BASE_EXP",) + P(n, -b))
    return out


NEG_PAIRS = [(b, n) for b in range(2, 11) for n in range(1, 7) if show_ok(Fraction(1, b ** n))]


def t1_zero(rng):
    b = rng.randint(2, 10)
    prompt = rng.choice(["{b}^0", "What is {b}^0?", "{b}^0 = ?", "Evaluate {b}^0"]).format(b=b)
    return dict(prompt=prompt, correct=V(1), cands=t1_zero_cands(b), fill=[], nw=2,
                expl=f"{b}^2 ÷ {b}^2 = 1, and by the quotient rule it is {b}^0. So {b}^0 = 1.")


def t1_neg(rng):
    b, n = rng.choice(NEG_PAIRS)
    prompt = rng.choice(["{b}^−{n}", "Value of {b}^−{n}", "{b}^−{n} = ?", "Simplify {b}^−{n}"]).format(b=b, n=n)
    fill = [V(Fraction(1, b ** (n + k))) for k in (1, 2)] + ([V(Fraction(1, b ** (n - 1)))] if n > 1 else [V(1)])
    return dict(prompt=prompt, correct=V(Fraction(1, b ** n)), cands=t1_neg_cands(b, n), fill=fill, nw=3,
                expl=f"{b}^−{n} = 1/{b}^{n} = {fnum(Fraction(1, b ** n))}. A minus in the exponent flips the power.")


def t1_which(rng):
    b, n = rng.choice(NEG_PAIRS)
    t = Fraction(1, b ** n)
    prompt = f"Which equals {fnum(t)}?"
    fill = [P(b, -(n + 1)), P(b, -(n + 2))] + ([P(b, -(n - 1))] if n > 1 else [])
    return dict(prompt=prompt, correct=P(b, -n), cands=t1_which_cands(b, n), fill=fill, nw=3,
                expl=f"{b}^−{n} = 1/{b}^{n} = {fnum(t)}. The minus flips the power, it does not make it negative.")


# --------------------------------------------------------------------------------------------
# Tier 2: product rule
# --------------------------------------------------------------------------------------------
def t2_cands(b: int, m: int, n: int):
    s = m + n
    out = []
    if exp_ok(m * n):
        out.append(("MULT_EXPONENTS",) + P(b, m * n))
    out.append(("MULT_BASES",) + P(b * b, s))  # a wrong choice's base may pass 10 (up to 100)
    if exp_ok(m * n):
        out.append(("MULT_BOTH",) + P(b * b, m * n))
    if 2 * b <= 10 and 2 * b != b * b:
        out.append(("ADD_BASES",) + P(2 * b, s))
    if exp_ok(m - n):
        out.append(("SUB_EXPONENTS",) + P(b, m - n))
    if (m < 0 or n < 0) and exp_ok(abs(m) + abs(n)):
        out.append(("SIGN_SLIP",) + P(b, abs(m) + abs(n)))
    return out


def t2_three_cands(b: int, m: int, n: int, k: int):
    out = []
    if exp_ok(m * n * k):
        out.append(("MULT_EXPONENTS",) + P(b, m * n * k))
    out.append(("SKIPS_FACTOR",) + P(b, m + n))
    if exp_ok(m - n - k):
        out.append(("SUB_EXPONENTS",) + P(b, m - n - k))
    if min(m, n, k) < 0 and exp_ok(abs(m) + abs(n) + abs(k)):
        out.append(("SIGN_SLIP",) + P(b, abs(m) + abs(n) + abs(k)))
    return out


def t2_fill_cands(m: int, t: int):
    """b^m × b^? = b^t."""
    out = []
    for key, v in (("ADD_GIVEN", m + t), ("COPY_TOTAL", t), ("MULT_GIVEN", m * t)):
        if exp_ok(v):
            out.append((key,) + V(v))
    return out


def t2_two(rng, kind):
    b = rng.choice([2, 3]) if rng.random() < 0.35 else rng.randint(2, 10)
    if kind == "pos":
        m = rng.randint(2, 8)
        n = rng.randint(2, min(8, 12 - m))
    elif kind == "one_neg":
        m, n = rng.randint(2, 9), -rng.randint(2, 9)
        if rng.random() < 0.5:
            m, n = n, m
    else:  # both negative
        m, n = -rng.randint(2, 6), -rng.randint(2, 6)
    if rng.random() < 0.7 and abs(m * n) > 12:
        return None  # most items keep the 'multiply instead' slip showable
    s = m + n
    if s == 0 or not exp_ok(s):
        return None
    prompt = f"{b}^{sg(m)} × {b}^{sg(n)}"
    return dict(prompt=prompt, correct=P(b, s), cands=t2_cands(b, m, n), fill=around(b, s), nw=3, first="MULT_BASES",
                expl=f"Same base, add the exponents: {add_str(m, n)} = {sg(s)}. So {b}^{sg(s)}.")


def t2_three(rng, kind):
    b = rng.randint(2, 10)
    if kind == "pos":
        m, n, k = rng.randint(2, 4), rng.randint(2, 4), rng.randint(2, 4)
    else:
        parts = [rng.randint(2, 6), rng.randint(2, 6), -rng.randint(2, 6)]
        rng.shuffle(parts)
        m, n, k = parts
    s = m + n + k
    if s == 0 or not exp_ok(s):
        return None
    prompt = f"{b}^{sg(m)} × {b}^{sg(n)} × {b}^{sg(k)}"
    return dict(prompt=prompt, correct=P(b, s), cands=t2_three_cands(b, m, n, k), fill=around(b, s), nw=3,
                expl=f"Same base, add all the exponents: {sum_str([m, n, k])} = {sg(s)}. So {b}^{sg(s)}.")


def t2_fill(rng):
    b = rng.randint(2, 10)
    m = rng.randint(2, 6)
    n = rng.randint(2, 7) if rng.random() < 0.75 else -rng.randint(2, 4)
    t = m + n
    if t == 0 or not exp_ok(t):
        return None
    prompt = f"{b}^{m} × {b}^? = {b}^{sg(t)}"
    return dict(prompt=prompt, correct=V(n), cands=t2_fill_cands(m, t), fill=around_int(n), nw=3,
                expl=f"Exponents add: {m} + ? = {sg(t)}, so ? = {sub_str(t, m)} = {sg(n)}.")


# --------------------------------------------------------------------------------------------
# Tier 3: quotient rule
# --------------------------------------------------------------------------------------------
def t3_cands(b: int, m: int, n: int):
    d = m - n
    out = []
    if n != 0 and m % n == 0 and exp_ok(m // n):
        out.append(("DIVIDE_EXPONENTS",) + P(b, m // n))
    if exp_ok(m + n):
        out.append(("SUB_NEG" if n < 0 else "ADD_EXPONENTS",) + P(b, m + n))
    out.append(("DIVIDE_BASES",) + P(1, d))
    if exp_ok(n - m):
        out.append(("FLIPPED_SUB",) + P(b, n - m))
    if (m < 0 or n < 0) and exp_ok(abs(m) - abs(n)):
        out.append(("SIGN_SLIP",) + P(b, abs(m) - abs(n)))
    return out


def t3_fill_cands(m: int, t: int):
    """b^m ÷ b^? = b^t."""
    out = []
    for key, v in (("ADD_GIVEN", m + t), ("COPY_TOTAL", t), ("FLIPPED_SUB", t - m)):
        if exp_ok(v):
            out.append((key,) + V(v))
    return out


def t3_div(rng, kind):
    b = rng.randint(2, 10)
    if kind == "pos":
        m = rng.randint(3, 12)
        n = rng.randint(2, m - 1)
    elif kind == "negres":
        m = rng.randint(2, 8)
        n = rng.randint(m + 1, 12)
    else:
        m, n = rng.randint(-8, 9), rng.randint(-8, 9)
        if (m >= 0 and n >= 0) or abs(m) < 2 or abs(n) < 2:
            return None
    d = m - n
    if d == 0 or not exp_ok(d):
        return None
    prompt = f"{b}^{sg(m)} ÷ {b}^{sg(n)}"
    cands = [c for c in t3_cands(b, m, n) if c[0] != "DIVIDE_BASES" or rng.random() < 0.35]
    return dict(prompt=prompt, correct=P(b, d), cands=cands, fill=around(b, d), nw=3,
                expl=f"Same base, subtract the exponents: {sub_str(m, n)} = {sg(d)}. So {b}^{sg(d)}.")


def t3_fill(rng):
    b = rng.randint(2, 10)
    m = rng.randint(5, 12)
    n = rng.randint(2, 6)
    t = m - n
    if t == 0:
        return None
    prompt = f"{b}^{m} ÷ {b}^? = {b}^{sg(t)}"
    return dict(prompt=prompt, correct=V(n), cands=t3_fill_cands(m, t), fill=around_int(n), nw=3,
                expl=f"Exponents subtract: {m} − ? = {sg(t)}, so ? = {sub_str(m, t)} = {n}.")


# --------------------------------------------------------------------------------------------
# Tier 4: power of a power, power of a product
# --------------------------------------------------------------------------------------------
def t4_pp_cands(b: int, m: int, n: int):
    out = []
    if exp_ok(m + n):
        out.append(("ADD_FOR_POWER",) + P(b, m + n))
    if m < 0 or n < 0:
        out.append(("SIGN_SLIP",) + P(b, -m * n))
    out.append(("DROP_OUTER",) + P(b, m))
    out.append(("DROP_INNER",) + P(b, n))
    return out


def t4_prod_cands(a: int, c: int, n: int):
    return [
        ("FIRST_FACTOR_ONLY", f"{a}^{n} × {c}", Fraction(a) ** n * c),
        ("FIRST_FACTOR_ONLY", f"{a} × {c}^{n}", a * Fraction(c) ** n),
        ("SUM_FOR_PRODUCT", f"{a}^{n} + {c}^{n}", Fraction(a) ** n + Fraction(c) ** n),
        ("TIMES_FOR_POWER", f"{a} × {c} × {n}", Fraction(a * c * n)),
        ("SUM_BASES", f"({a} + {c})^{n}", Fraction(a + c) ** n),
    ]


def t4_fill_cands(m: int, t: int):
    """(b^m)^? = b^t."""
    out = []
    for key, v in (("ADD_FOR_POWER", t - m), ("COPY_TOTAL", t), ("ADD_GIVEN", t + m)):
        if exp_ok(v):
            out.append((key,) + V(v))
    return out


def t4_pp(rng, kind):
    b = rng.randint(2, 10)
    if kind == "pp":
        m, n = rng.randint(2, 6), rng.randint(2, 6)
    elif kind == "negin":
        m, n = -rng.randint(2, 6), rng.randint(2, 6)
    elif kind == "negout":
        m, n = rng.randint(2, 6), -rng.randint(2, 6)
    else:
        m, n = -rng.randint(2, 4), -rng.randint(2, 3)
    if not exp_ok(m * n):
        return None
    prompt = f"({b}^{sg(m)})^{sg(n)}"
    return dict(prompt=prompt, correct=P(b, m * n), cands=t4_pp_cands(b, m, n), fill=around(b, m * n), nw=3,
                expl=f"Power of a power: multiply the exponents, {mul_str(m, n)} = {sg(m * n)}. So {b}^{sg(m * n)}.")


def t4_prod(rng):
    a, c = sorted(rng.sample(range(2, 11), 2))
    n = rng.randint(2, 5)
    correct = (f"{a}^{n} × {c}^{n}", Fraction(a) ** n * Fraction(c) ** n)
    return dict(prompt=f"({a} × {c})^{n}", correct=correct, cands=t4_prod_cands(a, c, n), fill=[], nw=3,
                expl=f"The exponent goes on each factor: ({a} × {c})^{n} = {a}^{n} × {c}^{n}.")


def t4_fill(rng):
    b = rng.randint(2, 10)
    m = rng.choice([2, 3, 4])
    n = rng.randint(2, 12 // m)
    t = m * n
    prompt = f"({b}^{m})^? = {b}^{t}"
    return dict(prompt=prompt, correct=V(n), cands=t4_fill_cands(m, t), fill=around_int(n), nw=3,
                expl=f"Power of a power multiplies: {m} × ? = {t}, so ? = {t} ÷ {m} = {n}.")


# --------------------------------------------------------------------------------------------
# Tier 5: two rules in a row, then a value
# --------------------------------------------------------------------------------------------
def t5_exponent(name: str, es, flags=()):
    """Final exponent of a structure under the correct rules (flags=()) or one wrong rule.
    Flags: 'mult' (product multiplies), 'addq' (quotient adds), 'addp' (power of power adds),
    'subm' (product subtracts)."""
    if "abs" in flags:
        es = [abs(x) for x in es]

    def prod(x, y):
        if "mult" in flags:
            return x * y
        if "subm" in flags:
            return x - y
        return x + y

    def quot(x, y):
        if "flip" in flags:
            return y - x
        return x + y if "addq" in flags else x - y

    def powp(x, y):
        return x + y if "addp" in flags else x * y

    if name == "mul":
        return prod(es[0], es[1])
    if name == "div":
        return quot(es[0], es[1])
    if name == "pow_div":  # (b^m)^n ÷ b^k
        return quot(powp(es[0], es[1]), es[2])
    if name == "pow_mul":  # (b^m)^n × b^k
        return prod(powp(es[0], es[1]), es[2])
    if name == "mul_div":  # b^m × b^n ÷ b^k
        return quot(prod(es[0], es[1]), es[2])
    if name == "div_div":  # b^m ÷ b^n ÷ b^k
        return quot(quot(es[0], es[1]), es[2])
    raise ValueError(name)


def t5_text(name: str, b: int, es) -> str:
    e = [sg(x) for x in es]
    if name == "mul":
        return f"{b}^{e[0]} × {b}^{e[1]}"
    if name == "div":
        return f"{b}^{e[0]} ÷ {b}^{e[1]}"
    if name == "pow_div":
        return f"({b}^{e[0]})^{e[1]} ÷ {b}^{e[2]}"
    if name == "pow_mul":
        return f"({b}^{e[0]})^{e[1]} × {b}^{e[2]}"
    if name == "mul_div":
        return f"{b}^{e[0]} × {b}^{e[1]} ÷ {b}^{e[2]}"
    return f"{b}^{e[0]} ÷ {b}^{e[1]} ÷ {b}^{e[2]}"


def t5_steps(name: str, es):
    """The correct partial exponents (each must have size <= 12); the last is the answer."""
    if name in ("mul", "div"):
        return [t5_exponent(name, es)]
    if name == "pow_div":
        return [es[0] * es[1], es[0] * es[1] - es[2]]
    if name == "pow_mul":
        return [es[0] * es[1], es[0] * es[1] + es[2]]
    if name == "mul_div":
        return [es[0] + es[1], es[0] + es[1] - es[2]]
    return [es[0] - es[1], es[0] - es[1] - es[2]]


def t5_value_ok(b: int, r: int) -> bool:
    return exp_ok(r) and show_ok(Fraction(b) ** r)


def t5_cands(name: str, b: int, es):
    r = t5_exponent(name, es)
    vals = []
    for key, flag in (("MULT_EXPONENTS", "mult"), ("SUB_EXPONENTS", "subm"),
                      ("ADD_EXPONENTS", "addq"), ("ADD_FOR_POWER", "addp"),
                      ("SIGN_SLIP", "abs"), ("FLIPPED_SUB", "flip")):
        w = t5_exponent(name, es, (flag,))
        if w != r and exp_ok(w):
            vals.append((key, Fraction(b) ** w))
    p = Fraction(b) ** r
    if r < 0:
        vals += [("NEG_VALUE", -(Fraction(b) ** -r)), ("NEG_FRACTION", -p), ("IGNORE_SIGN", Fraction(b) ** -r),
                 ("NEG_TIMES", Fraction(-b * -r))]
    if r == 0:
        vals += [("ZERO_IS_ZERO", Fraction(0)), ("ZERO_KEEPS_BASE", Fraction(b))]
    if r > 0:
        vals += [("TIMES_FOR_POWER", Fraction(b * r))]
    return [(k,) + V(v) for k, v in vals]


def t5_item(rng, name):
    b = rng.choice([2, 2, 3, 3, 4, 5, 5, 6, 7, 8, 9, 10, 10, 10])
    k = 2 if name in ("mul", "div") else 3
    es = [rng.choice([x for x in range(-8, 9) if x not in (0, 1, -1)]) for _ in range(k)]
    if name in ("pow_div", "pow_mul"):
        es[0] = rng.choice([-4, -3, -2, 2, 3, 4])
        es[1] = rng.choice([-3, -2, 2, 3])
    st = t5_steps(name, es)
    if any(not exp_ok(x) for x in st):
        return None
    r = st[-1]
    if not t5_value_ok(b, r):
        return None
    text = t5_text(name, b, es)
    val = Fraction(b) ** r
    fill = [V(Fraction(b) ** (r + d)) for d in (1, -1, 2, -2) if t5_value_ok(b, r + d)]
    if len(st) == 1:
        e1 = add_str(es[0], es[1]) if name == "mul" else sub_str(es[0], es[1])
        word = "Add" if name == "mul" else "Subtract"
        expl = f"{word} the exponents: {e1} = {sg(r)}. So {b}^{sg(r)} = {fnum(val)}."
    else:
        first = {"pow_div": mul_str(es[0], es[1]), "pow_mul": mul_str(es[0], es[1]),
                 "mul_div": add_str(es[0], es[1]), "div_div": sub_str(es[0], es[1])}[name]
        second = (add_str if name == "pow_mul" else sub_str)(st[0], es[2])
        expl = f"{first} = {sg(st[0])}; then {second} = {sg(r)}. So {b}^{sg(r)} = {fnum(val)}."
    return dict(prompt=text, correct=V(val), cands=t5_cands(name, b, es), fill=fill, nw=3, expl=expl)


# --------------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------------
def assemble(spec, rng):
    """Pick the wrong choices for a spec; None if it cannot reach spec['nw'] distinct ones."""
    cv = spec["correct"][1]
    allvals = {cv}  # every value any rule produces: ARITH never coincides with one
    seen = {cv}
    picks = []
    order = list(spec["cands"])
    rng.shuffle(order)
    order.sort(key=lambda c: c[0] != spec.get("first"))  # a required slip goes ahead of the others
    for key, d, v in order:
        allvals.add(v)
        if v in seen or len(d) > 14:
            continue
        if "^" not in d and " " not in d and not show_ok(v):
            continue  # a plain number must be showable (PROTOCOL §4b Exponents)
        seen.add(v)
        picks.append((key, d, v))
    picks = picks[:spec["nw"]]
    arith = 0
    for d, v in spec["fill"]:
        if len(picks) >= spec["nw"] or arith >= spec.get("max_arith", 1):
            break
        if v in allvals or len(d) > 14:
            continue
        allvals.add(v)
        arith += 1
        picks.append(("ARITH", d, v))
    if len(picks) < spec["nw"] or len(spec["prompt"]) > 60 or len(spec["expl"]) > 160:
        return None
    if len(spec["correct"][0]) > 14:
        return None
    rng.shuffle(picks)
    return picks


def balanced(count: int, k: int, rng) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def make_kind(tier, kind, rng):
    if tier == 1:
        return {"zero": t1_zero, "neg": t1_neg, "which": t1_which}[kind](rng)
    if tier == 2:
        if kind in ("pos", "one_neg", "both_neg"):
            return t2_two(rng, kind)
        if kind in ("three_pos", "three_neg"):
            return t2_three(rng, kind.split("_")[1])
        return t2_fill(rng)
    if tier == 3:
        if kind in ("pos", "negres", "negexp"):
            return t3_div(rng, kind)
        return t3_fill(rng)
    if tier == 4:
        if kind in ("pp", "negin", "negout", "negboth"):
            return t4_pp(rng, kind)
        if kind == "prod":
            return t4_prod(rng)
        return t4_fill(rng)
    return t5_item(rng, kind)


PLANS = {
    1: [("zero", 8), ("neg", 20), ("which", 12)],
    2: [("pos", 10), ("one_neg", 8), ("both_neg", 4), ("three_pos", 4), ("three_neg", 6), ("fill", 8)],
    3: [("pos", 10), ("negres", 8), ("negexp", 14), ("fill", 8)],
    4: [("pp", 10), ("negin", 5), ("negout", 5), ("negboth", 2), ("prod", 10), ("fill", 8)],
    5: [("mul", 5), ("div", 7), ("pow_div", 9), ("pow_mul", 5), ("mul_div", 8), ("div_div", 6)],
}


def plan(tier: int, count: int) -> list:
    """Kinds for `count` items: PLANS scaled to count (the first kind absorbs rounding)."""
    q = PLANS[tier]
    kinds = []
    for kind, c in q:
        kinds += [kind] * max(1, round(c * count / 40))
    while len(kinds) < count:
        kinds.append(q[1][0])
    return kinds[:count]


def gen_tier(tier, count, rng, max_attempts=200000):
    kinds = plan(tier, count)
    rng.shuffle(kinds)
    raw, prompts, attempts = [], set(), 0
    while len(raw) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        spec = make_kind(tier, kinds[len(raw)], rng)
        if spec is None or spec["prompt"] in prompts:
            continue
        picks = assemble(spec, rng)
        if picks is None:
            continue
        prompts.add(spec["prompt"])
        raw.append((spec, picks))
    # answer positions balanced within each choice-count group
    groups = {}
    for i, (_, picks) in enumerate(raw):
        groups.setdefault(len(picks) + 1, []).append(i)
    pos = {}
    for k, idxs in sorted(groups.items()):
        for i, p in zip(idxs, balanced(len(idxs), k, rng)):
            pos[i] = p
    items = []
    for i, (spec, picks) in enumerate(raw):
        a = pos[i]
        wrong = [(key, d) for key, d, _ in picks]
        seq = wrong[:a] + [(None, spec["correct"][0])] + wrong[a:]
        items.append({
            "tier": tier,
            "prompt": spec["prompt"],
            "choices": [d for _, d in seq],
            "answer": a,
            "misconceptions": [key for key, _ in seq],
            "explanation": spec["expl"],
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
