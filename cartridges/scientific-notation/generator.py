"""Procedural generator for the scientific-notation cartridge (fnm-cart/1, grade 8, 8.EE.A.3-A.4).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every number is an exact ``Fraction``; a scientific-notation number is (coefficient, exponent).
* A prompt is built from parameters, then *re-parsed from its display text* by ``analyze``: the text a
  student sees is the only thing the solver ever reads. ``analyze`` returns the right answer and the
  value each modelled misconception produces (``cands``, in label priority: when two rules give the
  same value the first names it) plus plain one-place slips (``fill``, labelled ARITH, used only to
  reach three wrong choices and never equal to any modelled value).
* Two families cannot be re-parsed because the prompt holds no data (``Which is in scientific
  notation?``, ``Which is greater than ...?``): their choices are built from parameters directly.
* Choices are compared by exact VALUE (key), never by text, so a player never faces two right doors.
* Bounds (the manifest's ``bounds``): coefficients d or d.d; exponents of size <= 12; standard forms
  <= 14 chars; every coefficient x or / a times-table fact renormalised by one place.
"""
from __future__ import annotations

import random
import re
from fractions import Fraction as F

MINUS, TIMES, DIVSIGN = "−", "×", "÷"
MAX_CHOICE = 14
MAX_PROMPT = 60
MAX_EXPL = 160


# ---------------------------------------------------------------------------------------------
# Number helpers
# ---------------------------------------------------------------------------------------------
def e_str(e: int) -> str:
    return f"{MINUS}{-e}" if e < 0 else str(e)


def POW(e: int) -> F:
    return F(10) ** e


def dec(v: F) -> str:
    """Exact decimal text, no commas, no trailing zeros: 3.2, 0.0005, 32000."""
    v = F(v)
    if v.denominator == 1:
        return str(v.numerator)
    k = 1
    while (v * 10 ** k).denominator != 1:
        k += 1
        if k > 40:
            raise ValueError(f"{v} does not terminate")
    s = str(int(v * 10 ** k)).rjust(k + 1, "0")
    return s[:-k] + "." + s[-k:]


def std(v: F) -> str:
    """Standard form: commas on the whole part (32,000), plain decimals (0.0005)."""
    v = F(v)
    if v < 0:
        return MINUS + std(-v)
    ip, _, fp = dec(v).partition(".")
    return f"{int(ip):,}" + ("." + fp if fp else "")


def sci(c: F, e: int) -> str:
    return f"{dec(c)} {TIMES} 10^{e_str(e)}"


def norm(v: F) -> tuple:
    """(coefficient, exponent) with 1 <= coefficient < 10."""
    v = F(v)
    e = 0
    while v >= 10:
        v /= 10
        e += 1
    while v < 1:
        v *= 10
        e -= 1
    return v, e


def sci_v(v: F) -> str:
    c, e = norm(v)
    return sci(c, e)


def paren(e: int) -> str:
    return f"({e_str(e)})" if e < 0 else str(e)


_C = r"(\d+(?:\.\d+)?)"
_E = r"(−?\d+)"
_SCI = _C + r" × 10\^" + _E
_STD = r"(\d[\d,]*(?:\.\d+)?)"


def pe(s: str) -> int:
    return int(s.replace(MINUS, "-"))


def pstd(s: str) -> F:
    return F(s.replace(",", ""))


def log10_exact(v: F) -> int:
    n, x = 0, F(v)
    while x >= 10:
        x /= 10
        n += 1
    while x < 1:
        x *= 10
        n -= 1
    if x != 1:
        raise ValueError(f"{v} is not a power of 10")
    return n


class A:
    """What a prompt means: right answer, modelled wrong values, one-place slips, explanation."""

    def __init__(self, prompt, ctext, ckey, cands, fill, expl, binary=False):
        self.prompt, self.ctext, self.ckey = prompt, ctext, ckey
        self.cands, self.fill, self.expl, self.binary = cands, fill, expl, binary

    def wrong_texts(self) -> dict:
        """{label: text} for the modelled wrong values that differ from the right answer (first label
        wins a value)."""
        out, seen = {}, {self.ckey}
        for lab, t, k in self.cands:
            if k in seen:
                continue
            seen.add(k)
            out.setdefault(lab, t)
        return out


def _sci_fill(c: F, e: int) -> list:
    return [(sci(c, e + d), c * POW(e + d)) for d in (1, -1, 2, -2)]


def _std_fill(v: F) -> list:
    return [(std(v * POW(d)), v * POW(d)) for d in (1, -1, 2, -2)]


# ---------------------------------------------------------------------------------------------
# Tier 1: powers of 10
# ---------------------------------------------------------------------------------------------
def _a_pow(m):
    n = pe(m.group(1))
    v = POW(n)
    cands = []
    if n > 0:
        cands = [("ZEROS_PLUS_ONE", std(POW(n + 1)), POW(n + 1)),
                 ("TIMES_FOR_POWER", str(10 * n), F(10 * n)),
                 ("DIGITS_SIDE_BY_SIDE", "10" + str(n), F(int("10" + str(n)))),
                 ("ONE_ZERO_SHORT", std(POW(n - 1)), POW(n - 1))]
        expl = f"10^{n} is a 1 followed by {n} zero{'' if n == 1 else 's'}: {std(v)}."
    elif n == 0:
        cands = [("ZERO_IS_ZERO", "0", F(0)), ("ZERO_KEEPS_BASE", "10", F(10))]
        expl = "Any number to the power 0 is 1, so 10^0 = 1."
    else:
        k = -n
        cands = [("NEG_IS_NEGATIVE", MINUS + std(POW(k)), -POW(k)),
                 ("NEG_IGNORED", std(POW(k)), POW(k)),
                 ("DECIMAL_SLIP", std(POW(-(k + 1))), POW(-(k + 1))),
                 ("ONE_PLACE_SHORT", std(POW(-(k - 1))), POW(-(k - 1)))]
        expl = f"10^−{k} = 1/{std(POW(k))} = {std(v)}: the 1 is {k} place{'' if k == 1 else 's'} right of the point."
    return m.string, std(v), v, cands, _std_fill(v), expl


def _a_whatpower(m):
    v = pstd(m.group(1))
    n = log10_exact(v)
    if n > 0:
        cands = [("ZEROS_PLUS_ONE", e_str(n + 1), F(n + 1)), ("ONE_ZERO_SHORT", e_str(n - 1), F(n - 1))]
        expl = f"{std(v)} is a 1 followed by {n} zero{'' if n == 1 else 's'}, so it is 10^{n}."
    else:
        k = -n
        cands = [("SIGN_DROPPED", str(k), F(k)),
                 ("DECIMAL_SLIP", e_str(-(k - 1)), F(-(k - 1))),
                 ("ONE_PLACE_OVER", e_str(-(k + 1)), F(-(k + 1)))]
        expl = f"In {std(v)} the 1 is {k} place{'' if k == 1 else 's'} right of the point, so it is 10^−{k}."
    fill = [(e_str(n + d), F(n + d)) for d in (1, -1, 2, -2)]
    return m.string, e_str(n), F(n), cands, fill, expl


def _a_whichpower(m):
    v = pstd(m.group(1))
    n = log10_exact(v)
    P = lambda e: f"10^{e_str(e)}"
    if n > 0:
        cands = [("ZEROS_PLUS_ONE", P(n + 1), F(n + 1)), ("ONE_ZERO_SHORT", P(n - 1), F(n - 1))]
        expl = f"{std(v)} is a 1 followed by {n} zero{'' if n == 1 else 's'}, so it is 10^{n}."
    else:
        k = -n
        cands = [("SIGN_DROPPED", P(k), F(k)),
                 ("DECIMAL_SLIP", P(-(k - 1)), F(-(k - 1))),
                 ("ONE_PLACE_OVER", P(-(k + 1)), F(-(k + 1)))]
        expl = f"In {std(v)} the 1 is {k} place{'' if k == 1 else 's'} right of the point, so it is 10^−{k}."
    fill = [(P(n + d), F(n + d)) for d in (1, -1, 2, -2)]
    return m.string, P(n), F(n), cands, fill, expl


# ---------------------------------------------------------------------------------------------
# Tier 2: write in scientific notation
# ---------------------------------------------------------------------------------------------
def _moves(v: F):
    """(c, e, all_digits_exp, zeros_exp) for a coefficient d or d.d times a power of 10 written out."""
    c, e = norm(v)
    ip, _, fp = dec(v).partition(".")
    if v >= 1:
        all_digits = len(ip)
        zeros = len(ip) - len(ip.rstrip("0"))
    else:
        all_digits = -len(fp)
        zeros = -(len(fp) - len(fp.lstrip("0")))
    return c, e, all_digits, zeros


def _a_write(m):
    v = pstd(m.group(1))
    c, e, alld, zer = _moves(v)
    cands = [("COUNTED_ALL_DIGITS", sci(c, alld), c * POW(alld)),
             ("SIGN_FLIP", sci(c, -e), c * POW(-e)),
             ("COUNTED_ZEROS", sci(c, zer), c * POW(zer)),
             ("ONE_PLACE_SHORT", sci(c, e - 1 if e > 0 else e + 1), c * POW(e - 1 if e > 0 else e + 1)),
             ("ONE_PLACE_OVER", sci(c, e + 1 if e > 0 else e - 1), c * POW(e + 1 if e > 0 else e - 1))]
    if e > 0:
        expl = f"The point moves {e} places left to make {dec(c)}, so {std(v)} = {sci(c, e)}."
    else:
        expl = f"The point moves {-e} places right to make {dec(c)}, so {std(v)} = {sci(c, e)}."
    return m.string, sci(c, e), v, cands, _sci_fill(c, e), expl


def _a_write_exp(m):
    v = pstd(m.group(1))
    c0 = F(m.group(2))
    c, e, alld, zer = _moves(v)
    if c != c0:
        raise ValueError("coefficient does not match")
    cands = [("COUNTED_ALL_DIGITS", e_str(alld), F(alld)),
             ("SIGN_FLIP", e_str(-e), F(-e)),
             ("COUNTED_ZEROS", e_str(zer), F(zer)),
             ("ONE_PLACE_SHORT", e_str(e - 1 if e > 0 else e + 1), F(e - 1 if e > 0 else e + 1)),
             ("ONE_PLACE_OVER", e_str(e + 1 if e > 0 else e - 1), F(e + 1 if e > 0 else e - 1))]
    way = "left" if e > 0 else "right"
    expl = f"The point moves {abs(e)} places {way} to make {dec(c)}, so the power is {e_str(e)}."
    fill = [(e_str(e + d), F(e + d)) for d in (1, -1, 2, -2)]
    return m.string, e_str(e), F(e), cands, fill, expl


# ---------------------------------------------------------------------------------------------
# Tier 3: read in standard form
# ---------------------------------------------------------------------------------------------
def _std_analysis(prompt, c, e, expl):
    v = c * POW(e)
    s = 1 if e > 0 else -1
    cands = [("SIGN_FLIP", std(c * POW(-e)), c * POW(-e)),
             ("EXTRA_ZERO", std(v * POW(s)), v * POW(s)),
             ("DECIMAL_SLIP", std(v * POW(-s)), v * POW(-s))]
    if e > 0 and c.denominator != 1:
        cands.insert(0, ("APPENDED_ZEROS", dec(c) + "0" * e, c))
    return prompt, std(v), v, cands, _std_fill(v), expl


def _a_std(m):
    c, e = F(m.group(1)), pe(m.group(2))
    if e > 0:
        expl = f"10^{e} moves the point {e} places right: {sci(c, e)} = {std(c * POW(e))}."
    else:
        expl = f"10^−{-e} moves the point {-e} places left: {sci(c, e)} = {std(c * POW(e))}."
    return _std_analysis(m.string, c, e, expl)


def _a_calc(m):
    c, e = F(m.group(1)), pe(m.group(2))
    expl = f"E{e_str(e)} means × 10^{e_str(e)}: {dec(c)}E{e_str(e)} = {sci(c, e)} = {std(c * POW(e))}."
    return _std_analysis(m.string, c, e, expl)


# ---------------------------------------------------------------------------------------------
# Tier 4: compare and how many times
# ---------------------------------------------------------------------------------------------
def _a_howmany(m):
    a, e1, b, e2 = F(m.group(1)), pe(m.group(2)), F(m.group(3)), pe(m.group(4))
    r = (a / b) * POW(e1 - e2)
    if r.denominator != 1 or r <= 1:
        raise ValueError("ratio must be a whole number above 1")
    k, d = a / b, e1 - e2
    inv = "1/" + std(r)
    if d == 0:
        cands = [("SUBTRACTED", dec(a - b), a - b), ("DIVIDED_WRONG_WAY", "1/" + dec(k), 1 / k),
                 ("MULTIPLIED_COEFS", dec(a * b), a * b)]
        expl = f"Same power of 10, so divide the coefficients: {dec(a)} ÷ {dec(b)} = {dec(k)}."
        fill = [(dec(k + 1), k + 1), (dec(k * 10), k * 10), (dec(k + 2), k + 2)]
    elif k == 1:
        cands = [("EXPONENT_DIFF", str(d), F(d)), ("DIVIDED_WRONG_WAY", inv, 1 / r),
                 ("ONE_ZERO_OFF", std(r * 10), r * 10), ("ONE_ZERO_OFF", std(r / 10), r / 10)]
        expl = f"The coefficients match and the powers differ by {d}, so it is 10^{d} = {std(r)} times."
        fill = [(std(r * 100), r * 100), (std(r * 2), r * 2)]
    else:
        cands = [("EXPONENT_DIFF", str(d), F(d)), ("COEF_RATIO_ONLY", dec(k), k),
                 ("DIVIDED_WRONG_WAY", inv, 1 / r)]
        expl = (f"{dec(a)} ÷ {dec(b)} = {dec(k)}, and the powers differ by {d}: "
                f"{dec(k)} × {std(POW(d))} = {std(r)}.")
        fill = [(std(r * 10), r * 10), (std(r / 10), r / 10), (std(r * 2), r * 2)]
        fill = [(t, kk) for t, kk in fill if kk.denominator == 1]
    return m.string, std(r), r, cands, fill, expl


def _a_pair(m):
    which = m.group(1)
    a1, e1, a2, e2 = F(m.group(2)), pe(m.group(3)), F(m.group(4)), pe(m.group(5))
    x1, x2 = (a1, e1), (a2, e2)
    v1, v2 = a1 * POW(e1), a2 * POW(e2)
    if v1 == v2:
        raise ValueError("tie")
    win, lose = (x1, x2) if (v1 > v2) == (which == "Larger") else (x2, x1)
    label = "NEG_EXP_BIGGER" if e1 < 0 and e2 < 0 else "COEF_FIRST"
    word = "larger" if which == "Larger" else "smaller"
    expl = f"Compare the powers of 10 first: {sci(*win)} is the {word} number."
    return (m.string, sci(*win), win[0] * POW(win[1]),
            [(label, sci(*lose), lose[0] * POW(lose[1]))], [], expl, True)


# ---------------------------------------------------------------------------------------------
# Tier 5: multiply, divide, add
# ---------------------------------------------------------------------------------------------
def _k(c, e):
    return (sci(c, e), c * POW(e))


def _a_calc_ops(m):
    a, m1, op, b, n1 = F(m.group(1)), pe(m.group(2)), m.group(3), F(m.group(4)), pe(m.group(5))
    ia, ib = int(a), int(b)
    if a.denominator != 1 or b.denominator != 1:
        raise ValueError("tier 5 coefficients are whole digits")
    if op == TIMES:
        ab = a * b
        c0, car = norm(ab)
        e = m1 + n1 + car
        cc = c0
        cands = [("MULT_EXPONENTS", *_k(c0, m1 * n1 + car))]
        if ia + ib < 10:
            cands.append(("ADD_COEFS", *_k(F(ia + ib), m1 + n1)))
        if car:
            cands.append(("NO_CARRY", *_k(c0, m1 + n1)))
        cands.append(("EXPONENTS_SUBTRACTED", *_k(c0, m1 - n1 + car)))
        step = f"{ia} × {ib} = {ab}" + (f" = {dec(c0)} × 10^1" if car else "")
        expl = f"{step}; the powers add: {paren(m1)} + {paren(n1)} = {e_str(m1 + n1)}. So {sci(c0, e)}."
    elif op == DIVSIGN:
        q = a / b
        c0, e0 = norm(q)
        e = m1 - n1 + e0
        cc = c0
        cands = [("ADD_EXPONENTS", *_k(c0, m1 + n1 + e0))]
        if n1 != 0 and m1 % n1 == 0:
            cands.append(("DIVIDE_EXPONENTS", *_k(c0, m1 // n1 + e0)))
        if 1 <= ia - ib <= 9:
            cands.append(("SUB_COEFS", *_k(F(ia - ib), m1 - n1)))
        cands.append(("FLIPPED_EXPONENTS", *_k(c0, n1 - m1 + e0)))
        if e0:
            cands.append(("NO_CARRY", *_k(c0, m1 - n1)))
        step = f"{ia} ÷ {ib} = {dec(q)}" + (f" = {dec(c0)} × 10^{e_str(e0)}" if e0 else "")
        expl = f"{step}; the powers subtract: {paren(m1)} − {paren(n1)} = {e_str(m1 - n1)}. So {sci(c0, e)}."
    else:  # +
        if m1 == n1:
            s = ia + ib
            c0, car = norm(F(s))
            e = m1 + car
            cc = c0
            pc, pcar = norm(F(ia * ib))
            cands = [("ADD_EXPONENTS_ON_SUM", *_k(c0, 2 * m1 + car)),
                     ("MULT_FOR_ADD", *_k(pc, m1 + pcar))]
            if car:
                cands.append(("NO_CARRY", *_k(c0, m1)))
            step = f"Same power, so add the coefficients: {ia} + {ib} = {s}"
            expl = step + (f" = {dec(c0)} × 10^1. So {sci(c0, e)}." if car else f". So {sci(c0, e)}.")
        else:
            if abs(m1 - n1) != 1:
                raise ValueError("gap must be one")
            hi_a, hi_e, lo_b = (ia, m1, ib) if m1 > n1 else (ib, n1, ia)
            cs = F(hi_a) + F(lo_b, 10)
            c0, car = norm(cs)
            if car or c0 > F(19, 2):
                raise ValueError("gap sum must stay under 9.5")
            e = hi_e
            cc = cs
            s = hi_a + lo_b
            cs_n, cs_car = norm(F(s))
            cands = [("IGNORE_GAP", *_k(cs_n, hi_e + cs_car)),
                     ("KEPT_SMALLER_POWER", *_k(cs_n, hi_e - 1 + cs_car)),
                     ("ADD_EXPONENTS_ON_SUM", *_k(cs_n, 2 * hi_e - 1 + cs_car))]
            expl = (f"Match the powers: {lo_b} × 10^{e_str(hi_e - 1)} = {dec(F(lo_b, 10))} × 10^{e_str(hi_e)}. "
                    f"Add: {hi_a} + {dec(F(lo_b, 10))} = {dec(cs)}.")
    return m.string, sci(cc, e), cc * POW(e), cands, _sci_fill(cc, e), expl


# ---------------------------------------------------------------------------------------------
# Prompt families: regex -> handler
# ---------------------------------------------------------------------------------------------
_P = lambda s: re.compile(s)
_FAMILIES = [
    (_P(r"10\^" + _E + r" = \?"), _a_pow),
    (_P(r"Which equals 10\^" + _E + r"\?"), _a_pow),
    (_P(r"Standard form of 10\^" + _E + r"\?"), _a_pow),
    (_P(_STD + r" is 10 to what power\?"), _a_whatpower),
    (_P(r"Which power of 10 equals " + _STD + r"\?"), _a_whichpower),
    (_P(r"Write " + _STD + r" in scientific notation\."), _a_write),
    (_P(_STD + r" = " + _C + r" × 10\^\?"), _a_write_exp),
    (_P(_SCI + r" in standard form\?"), _a_std),
    (_P(r"Standard form of " + _SCI + r"\?"), _a_std),
    (_P(r"Which equals " + _SCI + r"\?"), _a_std),
    (_P(r"(?:A calculator shows|Calculator screen:) " + _C + r"E" + _E + r"\. Value\?"), _a_calc),
    (_P(_SCI + r" is how many times " + _SCI + r"\?"), _a_howmany),
    (_P(r"(Larger|Smaller): " + _SCI + r" or " + _SCI + r"\?"), _a_pair),
    # groups: a, m, operator, b, n (the operator sits between the two terms)
    (_P(r"\(" + _C + r" × 10\^" + _E + r"\) ([×÷+]) \(" + _C + r" × 10\^" + _E + r"\)"), _a_calc_ops),
]


def analyze(prompt: str) -> A:
    for rx, fn in _FAMILIES:
        m = rx.fullmatch(prompt)
        if m:
            res = fn(m)
            return A(*res)
    raise ValueError(f"unrecognised prompt: {prompt!r}")


# ---------------------------------------------------------------------------------------------
# Structural families (the prompt carries no data)
# ---------------------------------------------------------------------------------------------
FORM_PROMPTS = ("Which is in scientific notation?", "Which number is in scientific notation?",
                "Which one is in scientific notation?")


def form_analysis(prompt: str, c: F, e: int) -> A:
    right = sci(c, e)
    cands = [("COEF_NOT_1_TO_10", sci(c * 10, e), c * 10 * POW(e)),
             ("COEF_BELOW_1", sci(c / 10, e), c / 10 * POW(e)),
             ("ADDED_NOT_TIMES", f"{dec(c)} + 10^{e}", c + POW(e)),
             ("BASE_EXP_SWAP", f"{dec(c)} {TIMES} {e}^10", c * F(e) ** 10)]
    expl = f"One digit before the point, times a power of 10: {right}. The others break that rule."
    return A(prompt, right, c * POW(e), cands, [], expl)


def compare_analysis(greater: bool, t: F, et: int, r: F, er: int, w1: tuple, w2: tuple, same: tuple) -> A:
    word = "greater" if greater else "less"
    prompt = f"Which is {word} than {sci(t, et)}?"
    cands = [("COEF_FIRST", sci(*w1), w1[0] * POW(w1[1])), ("COEF_FIRST", sci(*w2), w2[0] * POW(w2[1]))]
    fill = [(sci(*same), same[0] * POW(same[1]))]
    expl = (f"Compare the powers of 10 first: {sci(r, er)} has a "
            f"{'bigger' if greater else 'smaller'} power, so it is {word} than {sci(t, et)}.")
    return A(prompt, sci(r, er), r * POW(er), cands, fill, expl)


# ---------------------------------------------------------------------------------------------
# Item building
# ---------------------------------------------------------------------------------------------
def _draw(decks: dict, n: int, rng: random.Random) -> int:
    d = decks.setdefault(n, [])
    if not d:
        d.extend(range(n))
        rng.shuffle(d)
    return d.pop()


def build_item(a: A, tier: int, rng: random.Random, decks: dict):
    if len(a.prompt) > MAX_PROMPT or len(a.expl) > MAX_EXPL or len(a.ctext) > MAX_CHOICE:
        return None
    seen = {a.ckey}
    wrong = []
    for lab, t, k in a.cands:
        if k in seen or len(t) > MAX_CHOICE:
            continue
        seen.add(k)
        wrong.append((lab, t))
    target = 1 if a.binary else 3
    if len(wrong) > target:
        wrong = rng.sample(wrong, target)
    used = {a.ckey} | {k for _, _, k in a.cands}
    for t, k in a.fill:
        if len(wrong) >= target:
            break
        if k in used or len(t) > MAX_CHOICE:
            continue
        used.add(k)
        wrong.append(("ARITH", t))
    if len(wrong) < target:
        return None
    rng.shuffle(wrong)
    pos = _draw(decks, len(wrong) + 1, rng)
    pairs = wrong[:pos] + [(None, a.ctext)] + wrong[pos:]
    return {
        "tier": tier,
        "prompt": a.prompt,
        "choices": [t for _, t in pairs],
        "answer": pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": a.expl,
    }


# ---------------------------------------------------------------------------------------------
# Pools per tier (prompt strings, or A objects for the structural families)
# ---------------------------------------------------------------------------------------------
SINGLES = [F(i) for i in range(2, 10)]
TWO_DIGIT = [F(i * 10 + j, 10) for i in range(1, 10) for j in range(1, 10) if i * 10 + j <= 95]


def _pool_t1(rng):
    a_pool = []
    for n in list(range(0, 10)) + list(range(-8, 0)):
        if n == 0:
            a_pool.append("10^0 = ?")
            continue
        form = rng.choice(("10^{} = ?", "Which equals 10^{}?", "Standard form of 10^{}?"))
        a_pool.append(form.format(e_str(n)))
    c_pool = [f"{std(POW(n))} is 10 to what power?" for n in list(range(2, 10)) + list(range(-8, -1))]
    d_pool = [f"Which power of 10 equals {std(POW(n))}?" for n in list(range(1, 10)) + list(range(-8, 0))]
    return [(14, a_pool), (13, c_pool), (13, d_pool)]


def _pool_t2(rng):
    big_single = [f"Write {std(c * POW(e))} in scientific notation." for c in SINGLES for e in range(3, 11)]
    big_two = [f"Write {std(c * POW(e))} in scientific notation." for c in TWO_DIGIT for e in range(3, 11)]
    small_single = [f"Write {std(c * POW(e))} in scientific notation." for c in SINGLES for e in range(-9, -1)]
    small_two = [f"Write {std(c * POW(e))} in scientific notation." for c in TWO_DIGIT for e in range(-9, -1)]
    which = [f"{std(c * POW(e))} = {dec(c)} × 10^?" for c in SINGLES + TWO_DIGIT[::4] for e in
             list(range(3, 9)) + list(range(-8, -2))]
    forms = []
    for i, p in enumerate(FORM_PROMPTS):
        c = F(rng.randint(11, 95), 10)
        if c % 1 == 0:
            c += F(1, 10)
        forms.append(form_analysis(p, c, rng.randint(2, 9)))
    return [(9, big_single), (8, big_two), (8, small_single), (6, small_two), (6, which), (3, forms)]


def _pool_t3(rng):
    forms = ("{} in standard form?", "Standard form of {}?", "Which equals {}?")
    pos, neg = [], []
    for c in SINGLES + TWO_DIGIT:
        for e in range(2, 10):
            if c.denominator != 1 and e < 2:
                continue
            pos.append(rng.choice(forms).format(sci(c, e)))
        for e in range(-9, -1):
            neg.append(rng.choice(forms).format(sci(c, e)))
    calc_pos = [f"{rng.choice(('A calculator shows', 'Calculator screen:'))} {dec(c)}E{e}. Value?"
                for c in SINGLES + TWO_DIGIT[::3] for e in range(3, 10)]
    calc_neg = [f"{rng.choice(('A calculator shows', 'Calculator screen:'))} {dec(c)}E{e_str(e)}. Value?"
                for c in SINGLES + TWO_DIGIT[::3] for e in range(-9, -2)]
    has_point = lambda p: re.search(r"\d\.\d", p) is not None
    pos_int = [p for p in pos if not has_point(p)]
    pos_dec = [p for p in pos if has_point(p)]
    neg_int = [p for p in neg if not has_point(p)]
    neg_dec = [p for p in neg if has_point(p)]
    return [(10, pos_int), (6, pos_dec), (10, neg_int), (6, neg_dec), (4, calc_pos), (4, calc_neg)]


_HOW_PAIRS = [(4, 2), (6, 2), (8, 2), (6, 3), (9, 3), (8, 4)]


def _pool_t4(rng):
    exps = [e for e in range(-8, 9) if e != 0]
    h1 = []
    for c in SINGLES:
        for e2 in range(-6, 6):
            for d in range(1, 6):
                e1 = e2 + d
                if e1 == 0 or e2 == 0 or abs(e1) > 8 or abs(e2) > 8:
                    continue
                h1.append(f"{sci(c, e1)} is how many times {sci(c, e2)}?")
    h2 = [f"{sci(F(a), e)} is how many times {sci(F(b), e)}?" for a, b in _HOW_PAIRS for e in exps]
    h3 = []
    for a, b in _HOW_PAIRS:
        for d in (1, 2, 3):
            for e2 in range(-7, 6):
                e1 = e2 + d
                if e1 == 0 or e2 == 0:
                    continue
                h3.append(f"{sci(F(a), e1)} is how many times {sci(F(b), e2)}?")
    pair = []
    for which in ("Larger", "Smaller"):
        for e_lo in range(-8, 8):
            for gap in range(1, 7):
                e_hi = e_lo + gap
                if e_lo == 0 or e_hi == 0 or e_hi > 8:
                    continue
                for _ in range(2):
                    x = rng.randint(2, 8)
                    y = rng.randint(x + 1, 9)  # the higher power has the smaller coefficient
                    hi, lo = (F(x), e_hi), (F(y), e_lo)
                    first, second = (hi, lo) if rng.random() < 0.5 else (lo, hi)
                    pair.append(f"{which}: {sci(*first)} or {sci(*second)}?")
    pair_larger = [p for p in pair if p.startswith("Larger")]
    pair_smaller = [p for p in pair if p.startswith("Smaller")]
    gt = []
    for t in range(2, 9):
        for et in list(range(-8, 0)) + list(range(1, 8)):
            gt.append(_compare_pool_item(True, F(t), et, rng))
    lt = []
    for t in range(3, 10):
        for et in list(range(-7, 0)) + list(range(1, 9)):
            lt.append(_compare_pool_item(False, F(t), et, rng))
    return [(9, h1), (6, h2), (7, h3), (7, pair_larger), (5, pair_smaller), (4, gt), (2, lt)]


def _compare_pool_item(greater: bool, t: F, et: int, rng) -> A:
    if greater:
        er = et + rng.randint(1, 2)
        r = F(rng.randint(2, 9))
        d1, d2 = rng.sample((1, 2, 3), 2)
        w1 = (F(rng.randint(int(t) + 1, 9)), et - d1) if t < 9 else (F(9), et - d1)
        w2 = (F(rng.randint(2, 9)), et - d2)
        same = (F(rng.randint(1, int(t) - 1)), et) if t > 1 else (F(1), et - 1)
    else:
        er = et - rng.randint(1, 2)
        r = F(rng.randint(2, 9))
        d1, d2 = rng.sample((1, 2, 3), 2)
        w1 = (F(rng.randint(2, int(t) - 1)), et + d1)
        w2 = (F(rng.randint(2, 9)), et + d2)
        same = (F(rng.randint(int(t) + 1, 9)), et) if t < 9 else (F(9), et + 1)
    a = compare_analysis(greater, t, et, r, er, w1, w2, same)
    return a


def _pool_t5(rng):
    nz = [e for e in range(-6, 7) if e != 0]
    mul_carry, mul_plain = [], []
    for a in range(2, 10):
        for b in range(a, 10):
            for m1 in nz:
                for n1 in nz:
                    if abs(m1 * n1) > 20 or m1 * n1 == m1 + n1:
                        continue
                    c0, car = norm(F(a * b))
                    if abs(m1 + n1 + car) > 12:
                        continue
                    x, y = (a, m1), (b, n1)
                    if rng.random() < 0.5:
                        x, y = y, x
                    p = f"({x[0]} × 10^{e_str(x[1])}) × ({y[0]} × 10^{e_str(y[1])})"
                    (mul_carry if car else mul_plain).append(p)
    div_div, div_plain, div_half = [], [], []
    for a, b in [(4, 2), (6, 2), (8, 2), (6, 3), (9, 3), (8, 4), (2, 4), (3, 6), (4, 8)]:
        half = a < b
        for m1 in nz:
            for n1 in nz:
                e = m1 - n1 + (-1 if half else 0)
                if abs(e) > 12 or m1 == n1:
                    continue
                p = f"({a} × 10^{e_str(m1)}) ÷ ({b} × 10^{e_str(n1)})"
                if half:
                    div_half.append(p)
                elif m1 % n1 == 0 and m1 // n1 not in (1, m1 - n1):
                    div_div.append(p)
                else:
                    div_plain.append(p)
    add_carry, add_plain, add_gap = [], [], []
    for a in range(2, 10):
        for b in range(2, 10):
            for e in nz:
                if a + b >= 10:
                    add_carry.append(f"({a} × 10^{e_str(e)}) + ({b} × 10^{e_str(e)})")
                else:
                    add_plain.append(f"({a} × 10^{e_str(e)}) + ({b} × 10^{e_str(e)})")
                if F(a) + F(b, 10) <= F(19, 2) and e - 1 != 0:
                    p1 = f"({a} × 10^{e_str(e)}) + ({b} × 10^{e_str(e - 1)})"
                    p2 = f"({b} × 10^{e_str(e - 1)}) + ({a} × 10^{e_str(e)})"
                    add_gap.append(p1 if rng.random() < 0.5 else p2)
    return [(9, mul_carry), (5, mul_plain), (7, div_div), (4, div_plain), (3, div_half),
            (4, add_carry), (4, add_plain), (4, add_gap)]


_POOLS = {1: _pool_t1, 2: _pool_t2, 3: _pool_t3, 4: _pool_t4, 5: _pool_t5}


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def gen_tier(tier: int, count: int, rng: random.Random) -> list:
    groups = _POOLS[tier](rng)
    if sum(q for q, _ in groups) != count:
        scale = count / sum(q for q, _ in groups)
        groups = [(max(1, round(q * scale)), p) for q, p in groups]
        groups[0] = (groups[0][0] + count - sum(q for q, _ in groups), groups[0][1])
    items, used, decks = [], set(), {}
    for quota, pool in groups:
        pool = list(pool)
        rng.shuffle(pool)
        got = 0
        for e in pool:
            if got == quota:
                break
            a = e if isinstance(e, A) else analyze(e)
            if a.prompt in used:
                continue
            item = build_item(a, tier, rng, decks)
            if item is None:
                continue
            used.add(a.prompt)
            items.append(item)
            got += 1
        if got < quota:
            raise RuntimeError(f"tier {tier}: pool of {len(pool)} gave {got} of {quota} items")
    rng.shuffle(items)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
