"""Procedural generator for the linear-equations cartridge (fnm-cart/1, grade 8, 8.EE.C.7.A/B, C.8.A/B/C).

Contract (PROTOCOL.md section 3): ``generate(manifest, rng) -> list[dict]`` in the section 4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Tiers
-----
1. Variables on both sides   "Solve: 5x + 2 = 3x + 10"
2. Distribute, then solve    "Solve: 3(x + 2) = x + 14", "Solve: 2(x − 1) + x = 13"
3. One, none or infinite     "2(x + 3) = 2x + 6. How many solutions?" and "which k" items
4. Fractions and decimals    "Solve: (1/2)x + 3 = 7", "Solve: 0.5x + 2 = x − 1"
5. Systems by inspection     parallel / same line / crossing; add two equations; where two lines meet

Every wrong choice is the value a modelled misconception produces; ``ARITH`` (answer +- small) only fills
when fewer than three distinct misconception values exist. No two choices share a value (compared exactly).
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

MINUS = "−"
DIVIDE = "÷"
N_CHOICES = 4
MAX_PROMPT, MAX_CHOICE, MAX_EXPL = 60, 14, 160
VARS = ("x", "n", "y", "m", "k", "t", "w")


# ---------------------------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------------------------
def num(n) -> str:
    n = int(n)
    return str(n) if n >= 0 else f"{MINUS}{-n}"


def xt(c: int, v: str) -> str:
    """Integer coefficient times the variable: x, −x, 3x, −3x."""
    c = int(c)
    if c == 1:
        return v
    if c == -1:
        return MINUS + v
    return f"{MINUS if c < 0 else ''}{abs(c)}{v}"


def side(xs, d) -> str:
    """One side of an equation: an x term (text or None) and a constant (0 or None drops it)."""
    if xs is None:
        return num(d)
    if not d:
        return xs
    return f"{xs} {'+' if d > 0 else MINUS} {abs(d)}"


def group(p: int, v: str, t: int) -> str:
    return f"{p}({v} {'+' if t > 0 else MINUS} {abs(t)})"


def lim_for(*lits) -> int:
    """Constant bound of PROTOCOL 4a: 12 once any literal is negative, 20 when all are positive."""
    return 12 if any(int(x) < 0 for x in lits) else 20


def pick_x(rng, pos_share=0.8, hi=10) -> int:
    x = rng.randint(1, hi)
    return x if rng.random() < pos_share else -x


# ---------------------------------------------------------------------------------------------
# Choice assembly
# ---------------------------------------------------------------------------------------------
def assemble(rng, prompt, correct, wrongs, pos, expl, fill=(), min_real=2):
    """correct = (text, key); wrongs = [(label, text, key)] (shuffled here, then ``fill`` ARITH values).
    A wrong choice whose key repeats an earlier key (the correct one included) is dropped. Returns None when
    fewer than three distinct wrongs exist, fewer than ``min_real`` of them come from a modelled
    misconception, or a display limit is broken (the caller resamples)."""
    wr = list(wrongs)
    rng.shuffle(wr)
    cands = wr + [("ARITH", t, k) for t, k in fill]
    chosen, keys = [], {correct[1]}
    for label, text, key in cands:
        if key is None or key in keys:
            continue
        chosen.append((label, text))
        keys.add(key)
        if len(chosen) == N_CHOICES - 1:
            break
    if len(chosen) < N_CHOICES - 1 or sum(lab != "ARITH" for lab, _ in chosen) < min_real:
        return None
    rng.shuffle(chosen)
    choices = [t for _, t in chosen]
    labels = [lab for lab, _ in chosen]
    choices.insert(pos, correct[0])
    labels.insert(pos, None)
    if len(prompt) > MAX_PROMPT or any(len(c) > MAX_CHOICE for c in choices) or len(expl) > MAX_EXPL:
        return None
    return {"prompt": prompt, "choices": choices, "answer": pos,
            "misconceptions": labels, "explanation": expl}


def numeric_item(rng, prompt, sol, wrongs, pos, expl, cap=99):
    """Numeric choices. wrongs: [(label, value)]; only whole values of size <= cap are offered."""
    w = []
    for lab, val in wrongs:
        val = Fraction(val)
        if val.denominator != 1 or abs(val) > cap:
            continue
        n = int(val)
        w.append((lab, num(n), n))
    s = int(sol)
    fill = [(num(s + d), s + d) for d in (1, -1, 2, -2, 3, -3) if s + d != 0 and abs(s + d) <= cap]
    rng.shuffle(fill)
    return assemble(rng, prompt, (num(s), s), w, pos, expl, fill)


# ---------------------------------------------------------------------------------------------
# Tier 1: variables on both sides   ax + b = cx + d
# ---------------------------------------------------------------------------------------------
def t1_cands(a, b, c, d) -> dict:
    """The value each wrong rule gives for ax + b = cx + d (Fractions)."""
    m, k = a - c, d - b
    return {
        "SAME_SIGN_MOVE": Fraction(k, a + c),   # added cx instead of subtracting it: (a + c)x = d − b
        "CONST_SIGN": Fraction(d + b, m),       # moved b without changing its sign: mx = d + b
        "ONE_STEP": Fraction(k),                # stopped at mx = d − b
        "SIGN_SLIP": Fraction(-k, m),           # right size, wrong sign
    }


def both_text(a, b, c, d, v) -> str:
    return f"{side(xt(a, v), b)} = {side(xt(c, v), d)}"


def sample_both(rng, kind):
    """(a, b, c, d, x) with a, c in 1..10, |a − c| >= 2, a nonzero integer solution, constants within bounds."""
    for _ in range(500):
        a, c = rng.randint(1, 10), rng.randint(1, 10)
        m = a - c
        if abs(m) < 2:
            continue
        x = pick_x(rng)
        if kind == "left0":      # 5x = 3x + 10
            b = 0
            d = m * x
        elif kind == "right0":   # 2x + 9 = 5x
            d = 0
            b = -m * x
        else:
            b = rng.randint(-9, 15)
            if b == 0:
                continue
            d = b + m * x
            if d == 0:
                continue
        lim = lim_for(b, d)
        if abs(b) > lim or abs(d) > lim:
            continue
        return a, b, c, d, x
    raise RuntimeError("t1 sample failed")


def collect_expl(a, b, c, d, x, v) -> str:
    m, k = a - c, d - b
    if abs(m) == 1:
        return f"Collect {v}: {xt(m, v)} = {num(k)}, so {v} = {num(x)}."
    if m < 0:   # keep x on the side where its coefficient stays positive
        return f"Collect {v}: {num(-k)} = {xt(-m, v)}. Divide by {-m}: {v} = {num(x)}."
    return f"Collect {v}: {xt(m, v)} = {num(k)}. Divide by {num(m)}: {v} = {num(x)}."


def gen_t1(rng, kind, pos):
    a, b, c, d, x = sample_both(rng, kind)
    v = rng.choice(VARS)
    cands = t1_cands(a, b, c, d)
    return numeric_item(rng, f"Solve: {both_text(a, b, c, d, v)}", x, list(cands.items()), pos,
                        collect_expl(a, b, c, d, x, v))


# ---------------------------------------------------------------------------------------------
# Tier 2: distribute, then solve   p(x + t) [+ ex] = cx + d
# ---------------------------------------------------------------------------------------------
def t2_cands(p, e, c, t, d) -> dict:
    m, k = p + e - c, d - p * t
    out = {
        "PARTIAL_DIST": Fraction(d - t, m),
        ("SIGN_INSIDE" if t < 0 else "CONST_SIGN"): Fraction(d + p * t, m),
    }
    if c > 0:
        out["SAME_SIGN_MOVE"] = Fraction(k, p + e + c)
    if e > 0 and p - c != 0:
        out["DROP_LIKE_TERM"] = Fraction(k, p - c)
    return out


def sample_group(rng, kind):
    """(p, e, c, t, d, x). kind: plain | collect | rev (rev swaps the sides)."""
    for _ in range(800):
        p = rng.randint(2, 6)
        e = rng.randint(1, 3) if kind == "collect" else 0
        c = rng.randint(0, 10) if kind == "collect" else rng.randint(1, 10)
        if kind == "collect" and rng.random() < 0.5:
            c = 0
        m = p + e - c
        if not 2 <= abs(m) <= 10:
            continue
        x = pick_x(rng)
        t = rng.choice([1, 2, 3, 4, 5, 6]) * rng.choice([1, 1, -1])
        d = m * x + p * t
        if c == 0 and d == 0:
            continue
        lim = lim_for(t, d)
        if abs(t) > lim or p * abs(t) > lim or abs(d) > lim:
            continue
        return p, e, c, t, d, x
    raise RuntimeError("t2 sample failed")


def group_eq_text(p, e, c, t, d, v, rev) -> str:
    left = group(p, v, t) + (f" + {xt(e, v)}" if e else "")
    right = side(xt(c, v) if c else None, d)
    return f"{right} = {left}" if rev else f"{left} = {right}"


def gen_t2(rng, kind, pos):
    p, e, c, t, d, x = sample_group(rng, kind)
    v = rng.choice(VARS)
    m, k = p + e - c, d - p * t
    collected = f"{num(-k)} = {xt(-m, v)}" if m < 0 else f"{xt(m, v)} = {num(k)}"
    expl = (f"Distribute: {side(xt(p + e, v), p * t)} = {side(xt(c, v) if c else None, d)}. "
            f"Collect: {collected}. {v} = {num(x)}.")
    return numeric_item(rng, f"Solve: {group_eq_text(p, e, c, t, d, v, kind == 'rev')}", x,
                        list(t2_cands(p, e, c, t, d).items()), pos, expl)


# ---------------------------------------------------------------------------------------------
# Tier 3: one, none or infinite
# ---------------------------------------------------------------------------------------------
COUNT_CHOICES = ("One", "None", "Infinite")


def inf_eq(rng, v):
    """(text, simplified) of an identity."""
    for _ in range(300):
        if rng.random() < 0.5:   # p(x + t) = px + pt
            p, t = rng.randint(2, 6), rng.choice([1, 2, 3, 4, 5, 6]) * rng.choice([1, -1])
            lim = lim_for(t, p * t)
            if p * abs(t) > lim:
                continue
            left, right = group(p, v, t), side(xt(p, v), p * t)
            if rng.random() < 0.5:
                left, right = right, left
            return f"{left} = {right}", side(xt(p, v), p * t)
        a, e = rng.randint(1, 6), rng.randint(1, 4)   # ax + b + ex = (a + e)x + b
        b = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9]) * rng.choice([1, -1])
        if abs(b) > lim_for(b):
            continue
        left = f"{side(xt(a, v), b)} + {xt(e, v)}"
        right = side(xt(a + e, v), b)
        if rng.random() < 0.5:
            left, right = right, left
        return f"{left} = {right}", side(xt(a + e, v), b)
    raise RuntimeError("inf_eq failed")


def none_eq(rng, v):
    """(text, left simplified, right simplified) of a contradiction."""
    for _ in range(300):
        style = rng.random()
        if style < 0.4:      # p(x + t) = px + (pt + delta)
            p, t = rng.randint(2, 6), rng.choice([1, 2, 3, 4, 5, 6]) * rng.choice([1, -1])
            dl = rng.choice([1, 2, 3, 4, 5, 6]) * rng.choice([1, -1])
            k = p * t + dl
            lim = lim_for(t, p * t, k)
            if p * abs(t) > lim or abs(k) > lim:
                continue
            left, right = group(p, v, t), side(xt(p, v), k)
            ls, rs = side(xt(p, v), p * t), right
        elif style < 0.8:    # ax + b = ax + b'
            a = rng.randint(1, 9)
            b, b2 = rng.randint(-9, 15), rng.randint(-9, 15)
            if b == b2 or b == 0 or b2 == 0:
                continue
            if max(abs(b), abs(b2)) > lim_for(b, b2):
                continue
            left, right = side(xt(a, v), b), side(xt(a, v), b2)
            ls, rs = left, right
        else:                # ax + b + ex = (a + e)x + b'
            a, e = rng.randint(1, 6), rng.randint(1, 4)
            b, b2 = rng.randint(-9, 12), rng.randint(-9, 12)
            if b == b2 or b == 0 or b2 == 0:
                continue
            if max(abs(b), abs(b2)) > lim_for(b, b2):
                continue
            left = f"{side(xt(a, v), b)} + {xt(e, v)}"
            right = side(xt(a + e, v), b2)
            ls, rs = side(xt(a + e, v), b), right
        if rng.random() < 0.5:
            left, right = right, left
            ls, rs = rs, ls
        return f"{left} = {right}", ls, rs
    raise RuntimeError("none_eq failed")


def one_eq(rng, v):
    """(text, simplified collected equation) of an equation with one nonzero integer solution."""
    if rng.random() < 0.5:
        for _ in range(300):
            a, c = rng.randint(1, 9), rng.randint(1, 9)
            if a == c:
                continue
            x = pick_x(rng)
            b = rng.randint(-9, 15)
            if b == 0:
                continue
            d = b + (a - c) * x
            if d == 0 or max(abs(b), abs(d)) > lim_for(b, d):
                continue
            return both_text(a, b, c, d, v), (a - c, d - b, x)
    for _ in range(300):
        p, e, c, t, d, x = sample_group(rng, "plain")
        if p == c:
            continue
        return group_eq_text(p, 0, c, t, d, v, False), (p - c, d - p * t, x)
    raise RuntimeError("one_eq failed")


def count_item(rng, cat, pos):
    v = rng.choice(VARS)
    if cat == "inf":
        text, simp = inf_eq(rng, v)
        expl = f"Both sides simplify to {simp}. Always true, so infinitely many solutions."
        answer = "Infinite"
        wrongs = [("ALWAYS_ONE", "One"), ("NONE_FOR_IDENTITY", "None"), ("CANCEL_IS_ZERO", f"{v} = 0")]
    elif cat == "none":
        text, ls, rs = none_eq(rng, v)
        expl = f"Left is {ls}, right is {rs}. The {v} terms match, the numbers don't: no solution."
        answer = "None"
        wrongs = [("ALWAYS_ONE", "One"), ("INFINITE_FOR_FALSE", "Infinite"), ("CANCEL_IS_ZERO", f"{v} = 0")]
    else:
        text, (m, k, x) = one_eq(rng, v)
        expl = f"Collect {v}: {xt(m, v)} = {num(k)}, so {v} = {num(x)}. Exactly one solution."
        answer = "One"
        wrongs = [("ONE_IS_NONE", "None"), ("ONE_IS_MANY", "Infinite"), ("ZERO_GUESS", f"{v} = 0")]
    prompt = f"{text}. How many solutions?"
    w = [(lab, t, t) for lab, t in wrongs]
    return assemble(rng, prompt, (answer, answer), w, pos, expl)


def q_item(rng, kind, pos):
    """Which k? items on x. kind: q_const (infinite when k is the constant) | q_coef (none / infinite coefficient)."""
    if kind == "q_const":
        a = rng.randint(2, 9)
        b = rng.randint(1, 9)
        prompt = f"{side(xt(a, 'x'), b)} = {xt(a, 'x')} + k. Infinite solutions when k is?"
        wrongs = [("CONST_FOR_COEFF", a), ("SIGN_PICK", -b), ("ARITH", b + rng.choice([1, 2, -1, -2]))]
        expl = f"Same x term, so the numbers must match too: k = {b}. Then both sides are {side(xt(a, 'x'), b)}."
        correct = b
    else:
        a = rng.randint(2, 9)
        if rng.random() < 0.5:   # no solution: same coefficient, different constants
            b, d = rng.randint(1, 9), rng.randint(1, 9)
            if b == d:
                return None
            prompt = f"{side(xt(a, 'x'), b)} = kx + {d}. No solution when k is?"
            wrongs = [("CONST_FOR_COEFF", d), ("CONST_FOR_COEFF", b), ("SIGN_PICK", -a)]
            expl = f"No solution needs the same x term on both sides but different numbers: k = {a}."
        else:                    # infinite: same coefficient, same constant
            b = rng.randint(1, 9)
            prompt = f"{side(xt(a, 'x'), b)} = kx + {b}. Infinite solutions when k is?"
            wrongs = [("CONST_FOR_COEFF", b), ("SIGN_PICK", -a), ("ARITH", a + rng.choice([1, 2, -1, -2]))]
            expl = f"Infinite needs identical sides, so the x terms match: k = {a}."
        correct = a
    return numeric_item(rng, prompt, correct, wrongs, pos, expl, cap=40)


def gen_t3(rng, kind, pos):
    if kind in ("inf", "none", "one"):
        return count_item(rng, kind, pos)
    return q_item(rng, kind, pos)


# ---------------------------------------------------------------------------------------------
# Tier 4: fractions and decimals
# ---------------------------------------------------------------------------------------------
DEC = {Fraction(1, 2): "0.5", Fraction(1, 4): "0.25", Fraction(1, 5): "0.2", Fraction(1, 10): "0.1"}
DEC_DIGIT = {Fraction(1, 2): 5, Fraction(1, 4): 25, Fraction(1, 5): 2, Fraction(1, 10): 1}


def coef_text(al: Fraction, style: str, v: str) -> str:
    if al == 1:
        return v
    if style == "dec":
        return DEC[al] + v
    if style == "div":
        return f"{v}/{al.denominator}"
    return f"({al.numerator}/{al.denominator}){v}"


def t4_cands(al: Fraction, b: int, ga: Fraction, d: int, dec: bool) -> dict:
    """Wrong values for al*x + b = ga*x + d (ga = 0: one-sided)."""
    m, k = al - ga, d - b
    out = {"FORGOT_LAST_STEP": Fraction(k)}
    if ga == 0:
        out["DEC_WRONG_WAY" if dec else "DIVIDE_FOR_MULT"] = k * al
        out["CONST_SIGN"] = Fraction(d + b) / al
        if dec:
            out["DEC_AS_FRAC"] = Fraction(k * DEC_DIGIT[al])
        else:
            out["ONE_TERM_CLEARED"] = Fraction(d) - b / al
    else:
        out["DEC_WRONG_WAY" if dec else "DIVIDE_FOR_MULT"] = k * m
        out["SAME_SIGN_MOVE"] = Fraction(k) / (al + ga)
        out["CONST_SIGN"] = Fraction(d + b) / m
        out["SIGN_SLIP"] = -Fraction(k) / m
    return out


def sample_t4(rng, kind):
    """(al, b, ga, d, x, style). kinds: fr1 (one-sided fraction) | fr2 (both sides, fractions)
    | dec1 (one-sided decimal) | dec2 (both sides, decimals)."""
    for _ in range(800):
        if kind == "fr1":
            al, ga = Fraction(1, rng.choice([2, 3, 4, 5])), Fraction(0)
            style = rng.choice(["paren", "div"])
        elif kind == "dec1":
            al, ga = rng.choice(list(DEC)), Fraction(0)
            style = "dec"
        elif kind == "fr2":
            al, ga = rng.choice([(Fraction(1), Fraction(1, 2)), (Fraction(1, 2), Fraction(1, 4))])
            style = rng.choice(["paren", "div"])
            if rng.random() < 0.5:
                al, ga = ga, al
        else:
            al, ga = rng.choice([(Fraction(1, 2), Fraction(1)), (Fraction(1, 2), Fraction(1, 4))])
            style = "dec"
            if rng.random() < 0.5:
                al, ga = ga, al
        m = al - ga
        sx = 1 if rng.random() < 0.8 else -1                        # sign of the solution
        j = rng.randint(1, 10) * sx * (1 if m > 0 else -1)          # j = m*x, the collected number side
        x = Fraction(j) / m
        if abs(x) > 40 or x == 0:
            continue
        b = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) * rng.choice([1, -1])
        d = b + j
        if ga != 0 and d == 0:
            continue
        lim = lim_for(b, d)
        if abs(b) > lim or abs(d) > lim:
            continue
        return al, b, ga, d, int(x), style
    raise RuntimeError("t4 sample failed")


def gen_t4(rng, kind, pos):
    al, b, ga, d, x, style = sample_t4(rng, kind)
    v = "x" if rng.random() < 0.7 else rng.choice(VARS)
    dec = style == "dec"
    left = side(coef_text(al, style, v), b)
    right = side(coef_text(ga, style, v), d) if ga else num(d)
    cands = t4_cands(al, b, ga, d, dec)
    k = d - b
    m = al - ga
    mstr = (MINUS if m < 0 else "") + (DEC[abs(m)] if dec else f"{abs(m).numerator}/{abs(m).denominator}")
    lhs = (MINUS if m < 0 else "") + coef_text(abs(m), style, v)
    if m < 0:   # flip so the coefficient of x stays positive
        expl = f"Collect: {num(-k)} = {coef_text(abs(m), style, v)}, so {v} = {num(-k)} {DIVIDE} {mstr[1:]} = {num(x)}."
    else:
        expl = f"Collect: {lhs} = {num(k)}, so {v} = {num(k)} {DIVIDE} {mstr} = {num(x)}."
    return numeric_item(rng, f"Solve: {left} = {right}", x, list(cands.items()), pos, expl)


# ---------------------------------------------------------------------------------------------
# Tier 5: systems
# ---------------------------------------------------------------------------------------------
def line_plain(m, b) -> str:
    return "y = " + side(xt(m, "x"), b)


def line_alt(m, b) -> str:
    """The same line as y − mx = b (or y + |m|x = b)."""
    return f"y {MINUS if m > 0 else '+'} {xt(abs(m), 'x')} = {num(b)}"


def count_choices_item(rng, prompt, answer, wrongs, pos, expl):
    w = [(lab, t, t) for lab, t in wrongs]
    return assemble(rng, prompt, (answer, answer), w, pos, expl)


def gen_t5_count(rng, cat, pos):
    for _ in range(400):
        m = rng.randint(1, 6) * rng.choice([1, -1])
        b = rng.randint(-12, 12)
        if cat == "none":
            b2 = rng.randint(-12, 12)
            if b2 == b:
                continue
            alt = rng.random() < 0.4
            l1, l2 = line_plain(m, b), (line_alt(m, b2) if alt else line_plain(m, b2))
            expl = f"Both lines have slope {num(m)} but start at {num(b)} and {num(b2)}: parallel, no shared point."
            answer = "None"
            wrongs = [("PARALLEL_ONE", "One"), ("SAME_SLOPE_SAME_LINE", "Infinite"), ("TWO_LINES_TWO", "Two")]
        elif cat == "inf":
            l1, l2 = line_plain(m, b), line_alt(m, b)
            if rng.random() < 0.5:
                l1, l2 = l2, l1
            expl = f"Rearranged, both are y = {side(xt(m, 'x'), b)}: the same line, infinitely many points."
            answer = "Infinite"
            wrongs = [("PARALLEL_ONE", "One"), ("NONE_FOR_IDENTITY", "None"), ("TWO_LINES_TWO", "Two")]
        else:
            m2 = rng.randint(1, 6) * rng.choice([1, -1])
            b2 = rng.randint(-12, 12)
            if m2 == m:
                continue
            l1, l2 = line_plain(m, b), line_plain(m2, b2)
            expl = f"The slopes {num(m)} and {num(m2)} differ, so the lines cross exactly once."
            answer = "One"
            wrongs = [("ONE_IS_NONE", "None"), ("ONE_IS_MANY", "Infinite"), ("TWO_LINES_TWO", "Two")]
        prompt = f"{l1} and {l2}. How many solutions?"
        it = count_choices_item(rng, prompt, answer, wrongs, pos, expl)
        if it is not None:
            return it
    raise RuntimeError("t5 count failed")


def sample_sd(rng):
    for _ in range(800):
        x, y = rng.randint(1, 8), rng.randint(1, 8)
        if x == y:
            continue
        elim = rng.choice(["y", "x"])
        A1, A2, B = rng.choice([1, 1, 2]), rng.choice([1, 2]), rng.choice([1, 1, 2])
        if elim == "y":     # A1 x + B y = C1 and A2 x − B y = C2: add -> (A1 + A2) x
            C1, C2 = A1 * x + B * y, A2 * x - B * y
            t1 = f"{xt(A1, 'x')} + {xt(B, 'y')} = {num(C1)}"
            t2 = f"{xt(A2, 'x')} {MINUS} {xt(B, 'y')} = {num(C2)}"
            coef, var = A1 + A2, "x"
        else:               # A x + B1 y = C1 and B2 y − A x = C2: add -> (B1 + B2) y
            B1, B2 = A1, A2
            A = B
            C1, C2 = A * x + B1 * y, B2 * y - A * x
            t1 = f"{xt(A, 'x')} + {xt(B1, 'y')} = {num(C1)}"
            t2 = f"{xt(B2, 'y')} {MINUS} {xt(A, 'x')} = {num(C2)}"
            coef, var = B1 + B2, "y"
        lim = lim_for(C1, C2)
        if abs(C1) > lim or abs(C2) > lim:
            continue
        return x, y, t1, t2, coef, var, C1 + C2, C2
    raise RuntimeError("sd sample failed")


def gen_t5_sd(rng, ask, pos):
    x, y, t1, t2, coef, var, S, C2 = sample_sd(rng)
    sol = {"x": x, "y": y}
    other = "y" if var == "x" else "x"
    first = f"Add the equations: {xt(coef, var)} = {num(S)}, so {var} = {num(sol[var])}."
    back = f" Put it back: {other} = {num(sol[other])}."
    if ask in ("x", "y"):
        prompt = f"{t1} and {t2}. Find {ask}."
        gave = "y" if ask == "x" else "x"
        wrongs = [("STOPPED_AT_SUM", S), ("GAVE_OTHER", sol[gave]), ("READ_CONSTANT", C2)]
        expl = first + (back if ask == other else "")
        return numeric_item(rng, prompt, sol[ask], wrongs, pos, expl, cap=40)
    prompt = f"{t1} and {t2}. Find (x, y)."
    pt = lambda a, b: f"({num(a)}, {num(b)})"
    wrongs = [("SWAPPED_XY", pt(y, x), (y, x)), ("READ_CONSTANT", pt(x, C2), (x, C2)),
              ("READ_CONSTANT", pt(S, y) if var == "x" else pt(x, S), (S, y) if var == "x" else (x, S))]
    fill = [(pt(x + dx, y + dy), (x + dx, y + dy)) for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1))]
    rng.shuffle(fill)
    return assemble(rng, prompt, (pt(x, y), (x, y)), wrongs, pos, first + back, fill)


def gen_t5_meet(rng, pos):
    for _ in range(800):
        m1, m2 = rng.randint(1, 5) * rng.choice([1, -1]), rng.randint(1, 5) * rng.choice([1, -1])
        if m1 == m2:
            continue
        x = rng.randint(1, 6) * rng.choice([1, 1, -1])
        b1 = rng.randint(-8, 8)
        y = m1 * x + b1
        b2 = y - m2 * x
        if b1 == b2 or abs(y) > 10 or abs(b2) > 12 or (b2 == 0 and rng.random() < 0.3):
            continue
        pt = lambda a, b: f"({num(a)}, {num(b)})"
        prompt = f"{line_plain(m1, b1)} and {line_plain(m2, b2)}. Where do they meet?"
        wrongs = [("SWAPPED_XY", pt(y, x), (y, x)), ("INTERCEPT_AS_MEET", pt(0, b1), (0, b1)),
                  ("DROPPED_SLOPE", pt(x, x + b1), (x, x + b1)), ("INTERCEPT_AS_MEET", pt(0, b2), (0, b2))]
        fill = [(pt(x + dx, y + dy), (x + dx, y + dy)) for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1))]
        rng.shuffle(fill)
        expl = (f"Set equal: {side(xt(m1, 'x'), b1)} = {side(xt(m2, 'x'), b2)}, so x = {num(x)}. "
                f"Then y = {num(y)}.")
        it = assemble(rng, prompt, (pt(x, y), (x, y)), wrongs, pos, expl, fill)
        if it is not None:
            return it
    raise RuntimeError("t5 meet failed")


def gen_t5(rng, kind, pos):
    if kind.startswith("c_"):
        return gen_t5_count(rng, kind[2:], pos)
    if kind == "meet":
        return gen_t5_meet(rng, pos)
    return gen_t5_sd(rng, kind[3:], pos)


# ---------------------------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------------------------
def _balanced(count: int, kinds, rng: random.Random) -> list:
    xs = [kinds[i % len(kinds)] for i in range(count)]
    rng.shuffle(xs)
    return xs


TIER_KINDS = {
    1: ("both", "both", "both", "left0", "right0"),
    2: ("plain", "plain", "collect", "collect", "rev"),
    3: ("inf", "none", "one", "inf", "none", "one", "q_const", "q_coef"),
    4: ("fr1", "fr2", "dec1", "dec2"),
    5: ("c_none", "c_inf", "c_one", "sd_x", "sd_y", "sd_pt", "meet", "meet"),
}


def _one(tier, kind, rng, pos):
    if tier == 1:
        return gen_t1(rng, kind, pos)
    if tier == 2:
        return gen_t2(rng, kind, pos)
    if tier == 3:
        return gen_t3(rng, kind, pos)
    if tier == 4:
        return gen_t4(rng, kind, pos)
    return gen_t5(rng, kind, pos)


def same_math(prompt: str) -> str:
    """Prompt with every one-letter variable token blanked: 2x + 6 = 14 and 2n + 6 = 14 are the same question."""
    return re.sub(r"(?<![A-Za-z0-9])[a-z](?![A-Za-z])", "_", re.sub(r"(\d)[a-z]\b", r"\1_", prompt))


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 20000) -> list:
    positions = _balanced(count, tuple(range(N_CHOICES)), rng)
    kinds = _balanced(count, TIER_KINDS[tier], rng)
    items, seen = [], set()
    for i in range(count):
        for _ in range(max_attempts):
            it = _one(tier, kinds[i], rng, positions[i])
            if it is None or same_math(it["prompt"]) in seen:
                continue
            seen.add(same_math(it["prompt"]))
            it["tier"] = tier
            items.append(it)
            break
        else:
            raise RuntimeError(f"tier {tier}: could not build item {i} ({kinds[i]})")
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    count = manifest["items_per_tier"]
    out = []
    for t in manifest["tiers"]:
        for it in gen_tier(t["tier"], count, rng):
            out.append({"tier": it["tier"], "prompt": it["prompt"], "choices": it["choices"],
                        "answer": it["answer"], "misconceptions": it["misconceptions"],
                        "explanation": it["explanation"]})
    return out
