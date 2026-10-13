"""Procedural generator for the linear-expressions cartridge (fnm-cart/1, grade 7, 7.EE.A.1-2).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4
shape without ``id``. Stdlib only. Deterministic for a given ``rng`` seed. Imports nothing from
other cartridges.

Design
------
* Every item comes from a *builder*: a pure function of its parameters returning the prompt, the
  correct choice, an ordered list of ``(misconception, wrong choice)`` candidates and the
  explanation. Builders are deterministic so the tests can call them with hand-worked parameters
  (golden cases). The random part only picks parameters (``_pick_*``).
* ``pick_wrong`` keeps three candidates whose VALUE differs from the answer and from each other
  (``fingerprint``: the choice parsed and evaluated at six assignments of its letters, so
  ``3x + 6`` and ``6 + 3x`` are the same value), one per misconception label first, labels in a
  random order so every misconception turns up across a tier. ``ARITH`` (a number of the answer
  nudged by 1 or 2) fills only when fewer than three real ones survive.
* Terms are written by ``poly``: coefficient 1 hides (``x``, ``−x``), a zero term vanishes, a
  minus is U+2212. Variable terms come before the constant in every answer.
* Bounds are the manifest's ``bounds`` string; the tests walk every baked prompt to assert them.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter
from fractions import Fraction

SUB, MUL, DIV = "−", "×", "÷"  # U+2212, U+00D7, U+00F7

LETTERS = ("x", "y", "n", "a", "b", "m", "p", "t", "k", "w")
WORD_LETTERS = ("p", "s", "g", "c", "b", "m", "h", "t", "w", "n")  # never 'a': "a" is also a word
PAIRS = (("x", "y"), ("a", "b"), ("m", "n"), ("p", "t"), ("c", "d"))


# ---------------------------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------------------------
def sn(n: int) -> str:
    """Signed integer text: '5', '−5'."""
    return str(n) if n >= 0 else f"{SUB}{-n}"


def par(n: int) -> str:
    """A number as an operand: '(−4)' for negatives."""
    return f"({sn(n)})" if n < 0 else str(n)


def pw(text: str) -> str:
    """Wrap a negative term in ( ) when it follows an operator."""
    return f"({text})" if text.startswith(SUB) else text


def poly(parts) -> str:
    """parts: [(coef, letter | None)] -> '−3x + 12'. Zero terms vanish; coefficient 1 hides."""
    out = ""
    for c, v in parts:
        if c == 0:
            continue
        mag = abs(c)
        body = str(mag) if v is None else (v if mag == 1 else f"{mag}{v}")
        if not out:
            out = (SUB if c < 0 else "") + body
        else:
            out += (f" {SUB} " if c < 0 else " + ") + body
    return out or "0"


def tt(c: int, v) -> str:
    """One signed term: '−4', '2x', '−x'."""
    return poly([(c, v)])


def group(m: int, inner: str) -> str:
    """Outside number times a bracket: '−3(x − 4)', '−(2x + 5)', '4(2x + 1)'."""
    return f"{SUB}({inner})" if m == -1 else f"{sn(m)}({inner})"


def sgn(n) -> int:
    return 1 if n > 0 else -1


def dec(f: Fraction) -> str:
    """Decimal text of a Fraction with at most 2 decimal places: 0.8, 1.05, 12."""
    n = f * 100
    assert n.denominator == 1, f
    whole, fr = divmod(int(n), 100)
    if fr == 0:
        return str(whole)
    if fr % 10 == 0:
        return f"{whole}.{fr // 10}"
    return f"{whole}.{fr:02d}"


def ok_dec(f: Fraction) -> bool:
    """PROTOCOL §4b decimals: positive, at most 2 places and at most 2 non-zero digits."""
    if f <= 0 or (f * 100).denominator != 1:
        return False
    return sum(ch not in "0." for ch in dec(f)) <= 2


def ctext(f: Fraction, v: str) -> str:
    """Decimal coefficient and letter: '0.8p', '1.05a', 'p' for 1."""
    return v if f == 1 else f"{dec(f)}{v}"


def ftext(f: Fraction, v: str) -> str:
    """Fraction coefficient and letter: '(3/4)x'."""
    return f"({f.numerator}/{f.denominator}){v}"


# ---------------------------------------------------------------------------------------------
# Value engine (for distinctness only; never used to pick the right answer)
# ---------------------------------------------------------------------------------------------
_TOKEN = re.compile(r"\s*(\d+\.\d+|\d+|[A-Za-z]|[+−×÷/()])")


def _tokens(text: str) -> list:
    toks, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"bad text {text!r}")
        toks.append(m.group(1))
        pos = m.end()
    out = []
    for t in toks:  # implicit multiplication: 3x, 2(…), x(…), )(, )x
        if out and (out[-1][0].isdigit() or out[-1].isalpha() or out[-1] == ")") \
                and (t.isalpha() or t == "("):
            out.append(MUL)
        out.append(t)
    return out


def value(text: str, env: dict) -> Fraction:
    """Value of display text with letters from ``env``. Raises ValueError on non-expressions."""
    toks = _tokens(text)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def atom():
        nonlocal pos
        t = peek()
        if t is None:
            raise ValueError("unexpected end")
        pos += 1
        if t[0].isdigit():
            return Fraction(t)
        if t.isalpha():
            return Fraction(env[t])
        if t == "(":
            v = expr()
            if peek() != ")":
                raise ValueError("unbalanced")
            pos += 1
            return v
        raise ValueError(f"unexpected {t!r}")

    def unary():
        nonlocal pos
        if peek() == SUB:
            pos += 1
            return -unary()
        return atom()

    def term():
        nonlocal pos
        v = unary()
        while peek() in (MUL, DIV, "/"):
            op = toks[pos]
            pos += 1
            rhs = unary()
            v = v * rhs if op == MUL else v / rhs
        return v

    def expr():
        nonlocal pos
        v = term()
        while peek() in ("+", SUB):
            op = toks[pos]
            pos += 1
            rhs = term()
            v = v + rhs if op == "+" else v - rhs
        return v

    v = expr()
    if pos != len(toks):
        raise ValueError(f"trailing tokens in {text!r}")
    return v


# six assignments for up to three letters; no three of the first two coordinates are collinear
_SAMPLES = ((3, 5, 7), (11, 2, 13), (4, 17, 6), (19, 8, 23), (5, 29, 9), (31, 10, 37))


def fingerprint(text: str):
    """Hashable identity of a choice's VALUE (words and expressions alike). Percent texts compare
    as their number; everything else is evaluated at six assignments of its letters."""
    text = text.strip()
    if text.endswith("%"):
        return ("pct", Fraction(text[:-1]))
    letters = sorted(set(re.findall(r"[A-Za-z]", text)))
    vals = []
    for s in _SAMPLES:
        env = {L: Fraction(s[i]) for i, L in enumerate(letters)}
        vals.append(value(text, env))
    return ("value", tuple(vals))


# ---------------------------------------------------------------------------------------------
# Tier 1: combine like terms with signs (7.EE.A.1)
# ---------------------------------------------------------------------------------------------
def _add_sizes(c1: int, c2: int) -> int:
    """Different signs, sizes added, sign of the bigger one."""
    big = c1 if abs(c1) > abs(c2) else c2
    return sgn(big) * (abs(c1) + abs(c2))


def t1_like_two(v, a, b):
    """a·v + b·v with signs: '5x − 8x', '−7x + 3x', 'x − 6x'."""
    s = a + b
    ans = tt(s, v)
    wrong = []
    if b < 0 and a + abs(b) != 0:
        wrong.append(("IGNORED_MINUS", tt(a + abs(b), v)))
    if (a > 0) != (b > 0):
        wrong.append(("ADD_SIZES", tt(_add_sizes(a, b), v)))
    wrong.append(("WRONG_SIGN", tt(-s, v)))
    wrong.append(("DROPPED_VARIABLE", sn(s)))
    note = f" ({v} alone is 1{v})" if 1 in (abs(a), abs(b)) else ""
    return dict(prompt=f"Simplify: {poly([(a, v), (b, v)])}", answer=ans, wrong=wrong,
                explanation=f"Add the coefficients{note}: {poly([(a, None), (b, None)])} = "
                            f"{sn(s)}. So {poly([(a, v), (b, v)])} = {ans}.")


def t1_like_const(v, a, b, k, order=("a", "b", "k")):
    """Two v-terms and a number in any order: '4a + 3 − a', '3 + 2a − 6a'."""
    parts = {"a": (a, v), "b": (b, v), "k": (k, None)}
    seq = [parts[o] for o in order]
    var_seq = [p for p in seq if p[1] is not None]
    (c1, _), (c2, _) = var_seq
    s = c1 + c2
    ans = poly([(s, v), (k, None)])
    wrong = []
    if c2 < 0 and c1 + abs(c2) != 0:
        wrong.append(("IGNORED_MINUS", poly([(c1 + abs(c2), v), (k, None)])))
    if k < 0:
        wrong.append(("IGNORED_MINUS", poly([(s, v), (abs(k), None)])))
    if abs(c2) == 1:
        wrong.append(("NO_COEF_ONE", poly([(c1, v), (k, None)])))
    elif abs(c1) == 1:
        wrong.append(("NO_COEF_ONE", poly([(c2, v), (k, None)])))
    if (c1 > 0) != (c2 > 0):
        wrong.append(("ADD_SIZES", poly([(_add_sizes(c1, c2), v), (k, None)])))
    wrong.append(("WRONG_SIGN", poly([(-s, v), (k, None)])))
    wrong.append(("WRONG_SIGN", poly([(s, v), (-k, None)])))
    if c1 + c2 + k != 0:
        wrong.append(("UNLIKE_COMBINED", tt(c1 + c2 + k, v)))
    wrong.append(("DROPPED_VARIABLE", sn(s + k)))
    return dict(prompt=f"Simplify: {poly(seq)}", answer=ans, wrong=wrong,
                explanation=f"Like terms: {poly(var_seq)} = {tt(s, v)}. {sn(k)} has no {v}, "
                            f"so it stays: {ans}.")


def t1_two_vars(u, v, a, b, c, order=("a", "b", "c")):
    """Two u-terms (a, b) and one v-term (c): '3x + 2y − x'. Letters stay in order of appearance."""
    parts = {"a": (a, u), "b": (b, u), "c": (c, v)}
    seq = [parts[o] for o in order]
    first = seq[0][1]
    s = a + b
    u_seq = [p for p in seq if p[1] == u]
    (c1, _), (c2, _) = u_seq

    def two(cu, cv):
        return poly([(cu, u), (cv, v)] if first == u else [(cv, v), (cu, u)])

    ans = two(s, c)
    wrong = []
    if c2 < 0 and c1 + abs(c2) != 0:
        wrong.append(("IGNORED_MINUS", two(c1 + abs(c2), c)))
    if c < 0:
        wrong.append(("IGNORED_MINUS", two(s, abs(c))))
    if abs(c2) == 1:
        wrong.append(("NO_COEF_ONE", two(c1, c)))
    elif abs(c1) == 1:
        wrong.append(("NO_COEF_ONE", two(c2, c)))
    if (c1 > 0) != (c2 > 0):
        wrong.append(("ADD_SIZES", two(_add_sizes(c1, c2), c)))
    if a + b + c != 0:
        wrong.append(("UNLIKE_COMBINED", tt(a + b + c, first)))
    wrong.append(("DROPPED_TERM", tt(s, u)))
    wrong.append(("WRONG_SIGN", two(-s, c)))
    return dict(prompt=f"Simplify: {poly(seq)}", answer=ans, wrong=wrong,
                explanation=f"Combine only the {u} terms: {poly(u_seq)} = {tt(s, u)}. "
                            f"The {v} term stays: {ans}.")


def t1_four(v, a, b, k1, k2, layout=0):
    """Two v-terms and two numbers: '4x − 3 − 6x + 5' (layout 0), '3 + 4x + 2 − 6x' (1), ..."""
    seqs = {0: [(a, v), (k1, None), (b, v), (k2, None)],
            1: [(k1, None), (a, v), (k2, None), (b, v)],
            2: [(a, v), (k1, None), (k2, None), (b, v)]}
    seq = seqs[layout]
    s, big_k = a + b, k1 + k2
    ans = poly([(s, v), (big_k, None)])
    wrong = []
    if b < 0 and a + abs(b) != 0:
        wrong.append(("IGNORED_MINUS", poly([(a + abs(b), v), (big_k, None)])))
    if k2 < 0 and k1 + abs(k2) != 0:
        wrong.append(("IGNORED_MINUS", poly([(s, v), (k1 + abs(k2), None)])))
    if (k1 > 0) != (k2 > 0):
        wrong.append(("ADD_SIZES", poly([(s, v), (_add_sizes(k1, k2), None)])))
    if (a > 0) != (b > 0):
        wrong.append(("ADD_SIZES", poly([(_add_sizes(a, b), v), (big_k, None)])))
    wrong.append(("WRONG_SIGN", poly([(-s, v), (big_k, None)])))
    wrong.append(("WRONG_SIGN", poly([(s, v), (-big_k, None)])))
    if s + big_k != 0:
        wrong.append(("UNLIKE_COMBINED", tt(s + big_k, v)))
    wrong.append(("DROPPED_VARIABLE", sn(s + big_k)))
    var_seq = [p for p in seq if p[1] is not None]
    num_seq = [p for p in seq if p[1] is None]
    return dict(prompt=f"Simplify: {poly(seq)}", answer=ans, wrong=wrong,
                explanation=f"{v} terms: {poly(var_seq)} = {tt(s, v)}. Numbers: "
                            f"{poly(num_seq)} = {sn(big_k)}. So {ans}.")


def _signed(rng, lo, hi):
    m = rng.randint(lo, hi)
    return m if rng.random() < 0.5 else -m


def _pick_t1(rng, kind):
    v = rng.choice(LETTERS)
    if kind in (0, 1):  # two terms; kind 1 has a bare letter
        a, b = (_signed(rng, 2, 11), _signed(rng, 2, 11))
        if kind == 1:
            if rng.random() < 0.5:
                a = rng.choice((1, -1))
            else:
                b = rng.choice((1, -1))
        if a > 0 and b > 0:
            b = -b
        s = a + b
        if s == 0 or abs(s) > 12 or (kind == 1 and abs(a) == abs(b)):
            return None
        return t1_like_two(v, a, b)
    if kind in (2, 3):  # two terms and a number
        a, b, k = _signed(rng, 2, 9), _signed(rng, 2, 9), _signed(rng, 1, 12)
        if kind == 3:
            if rng.random() < 0.5:
                a = rng.choice((1, -1))
            else:
                b = rng.choice((1, -1))
        if a > 0 and b > 0:
            b = -b
        s = a + b
        if s == 0 or abs(s) > 12:
            return None
        order = list("abk")
        rng.shuffle(order)
        return t1_like_const(v, a, b, k, tuple(order))
    if kind == 4:
        u, w = rng.choice(PAIRS)
        a, b, c = _signed(rng, 1, 9), _signed(rng, 1, 9), _signed(rng, 1, 9)
        if min(a, b, c) > 0:
            b = -b
        if a + b == 0 or abs(a + b) > 12 or a + b + c == 0:
            return None
        order = list("abc")
        rng.shuffle(order)
        return t1_two_vars(u, w, a, b, c, tuple(order))
    a, b = _signed(rng, 2, 9), _signed(rng, 2, 9)
    k1, k2 = _signed(rng, 1, 9), _signed(rng, 1, 9)
    if sum(1 for n in (a, b, k1, k2) if n < 0) < 2:
        return None
    if a + b == 0 or k1 + k2 == 0 or abs(a + b) > 12 or abs(k1 + k2) > 12:
        return None
    return t1_four(v, a, b, k1, k2, rng.randrange(3))


# ---------------------------------------------------------------------------------------------
# Tier 2: distribute with negatives (7.EE.A.1)
# ---------------------------------------------------------------------------------------------
def t2_distribute(v, m, a, k, const_first=False):
    """m(a·v + k) -> m·a·v + m·k, m may be negative (−1 prints as a bare minus)."""
    orig = [(a, v), (k, None)]
    if const_first:
        orig = orig[::-1]
    corr = [(m * c, l) for c, l in orig]
    ans = poly(corr)
    wrong = []
    first = "NEG_FIRST_ONLY" if m == -1 else "PARTIAL_DIST"
    wrong.append((first, poly([corr[0], orig[1]])))
    if m < 0:
        if m != -1:  # for a bare minus this is NEG_FIRST_ONLY's value
            wrong.append(("SIGN_INSIDE", poly([corr[0], (-corr[1][0], corr[1][1])])))
        wrong.append(("IGNORED_OUTER_MINUS", poly([(-c, l) for c, l in corr])))
        if orig[0][0] < 0:
            wrong.append(("SIGN_INSIDE", poly([(-corr[0][0], corr[0][1]), corr[1]])))
    else:
        if orig[1][0] < 0:
            wrong.append(("DROPPED_NEG", poly([corr[0], (-corr[1][0], corr[1][1])])))
        if orig[0][0] < 0:
            wrong.append(("DROPPED_NEG", poly([(-corr[0][0], corr[0][1]), corr[1]])))
    total = sum(c for c, _ in corr)
    if total != 0:
        wrong.append(("UNLIKE_COMBINED", tt(total, v)))
    e = [f"{sn(m)} × {pw(tt(o, l))} = {tt(c, l)}" for (o, l), (c, _) in zip(orig, corr)]
    return dict(prompt=f"Distribute: {group(m, poly(orig))}", answer=ans, wrong=wrong,
                explanation=f"Multiply each term by {sn(m)}: {e[0]} and {e[1]}. So {ans}.")


def _fits(m, *cs, cap=12):
    return all(abs(m * c) <= cap for c in cs) and m * sum(cs) != 0


def _pick_t2(rng, kind):
    v = rng.choice(LETTERS)
    if kind == 0:  # −m(a·v − k)
        m, a, k = -rng.randint(2, 6), rng.randint(1, 6), -rng.randint(1, 6)
        return t2_distribute(v, m, a, k) if _fits(m, a, k) else None
    if kind == 1:  # −m(a·v + k)
        m, a, k = -rng.randint(2, 6), rng.randint(1, 6), rng.randint(1, 6)
        return t2_distribute(v, m, a, k) if _fits(m, a, k) else None
    if kind == 2:  # −(a·v ± k)
        a, k = rng.randint(1, 12), _signed(rng, 1, 12)
        return t2_distribute(v, -1, a, k) if a + k != 0 else None
    if kind == 3:  # m(−a·v ± k)
        m, a, k = rng.randint(2, 6), -rng.randint(1, 6), _signed(rng, 1, 6)
        return t2_distribute(v, m, a, k) if _fits(m, a, k) else None
    if kind == 4:  # −m(−a·v ± k)
        m, a, k = -rng.randint(1, 6), -rng.randint(1, 6), _signed(rng, 1, 6)
        return t2_distribute(v, m, a, k) if _fits(m, a, k) else None
    m, a, k = -rng.randint(1, 6), _signed(rng, 1, 6), _signed(rng, 1, 6)  # −m(k ± a·v)
    return t2_distribute(v, m, a, k, const_first=True) if _fits(m, a, k) else None


# ---------------------------------------------------------------------------------------------
# Tier 3: add and subtract expressions (7.EE.A.1)
# ---------------------------------------------------------------------------------------------
def t3_groups(slots, c1, op, c2, neg_first=False, single_first=False):
    """Two bracketed expressions over the same slots (letters, then None for the number).

    c1, c2: coefficient tuples per slot. ``op`` joins them; ``neg_first`` puts a minus in front of
    the first bracket ('−(3x + 2) + (5x − 4)'); ``single_first`` writes the first group as a bare
    term ('6x − (2x + 3)').
    """
    n = len(slots)
    g1 = poly(list(zip(c1, slots)))
    if single_first:
        left = g1
    else:
        left = f"{SUB}({g1})" if neg_first else f"({g1})"
    prompt = f"Simplify: {left} {op} ({poly(list(zip(c2, slots)))})"
    negated = 1 if neg_first else (2 if op == SUB else 0)
    e1 = tuple(-c for c in c1) if negated == 1 else tuple(c1)
    e2 = tuple(-c for c in c2) if negated == 2 else tuple(c2)
    corr = tuple(x + y for x, y in zip(e1, e2))
    ans = poly(list(zip(corr, slots)))

    def show(vals):
        return poly(list(zip(vals, slots)))

    wrong = []
    if negated:
        g = c1 if negated == 1 else c2
        other = e2 if negated == 1 else e1
        first_only = tuple((-g[i] if i == 0 else g[i]) + other[i] for i in range(n))
        wrong.append(("FIRST_TERM_ONLY", show(first_only)))
        wrong.append(("IGNORED_MINUS", show(tuple(x + y for x, y in zip(c1, c2)))))
    else:
        for j in range(n):  # a negative inside is dropped
            if c2[j] < 0:
                alt = list(corr)
                alt[j] = e1[j] + abs(c2[j])
                wrong.append(("DROPPED_NEG", show(tuple(alt))))
                break
        else:
            for j in range(n):
                if c1[j] < 0:
                    alt = list(corr)
                    alt[j] = abs(c1[j]) + c2[j]
                    wrong.append(("DROPPED_NEG", show(tuple(alt))))
                    break
        for j in range(n):  # unlike signs: sizes added
            if (e1[j] > 0) != (e2[j] > 0) and e1[j] != 0:
                alt = list(corr)
                alt[j] = _add_sizes(e1[j], e2[j])
                wrong.append(("ADD_SIZES", show(tuple(alt))))
    wrong.append(("WRONG_SIGN", show((-corr[0],) + corr[1:])))
    wrong.append(("WRONG_SIGN", show(corr[:-1] + (-corr[-1],))))
    if sum(corr) != 0:
        wrong.append(("UNLIKE_COMBINED", poly([(sum(corr), slots[0])])))
    flat = poly(list(zip(e1, slots)) + list(zip(e2, slots)))
    if negated:
        ex = f"Change every sign in the subtracted ( ): {flat}. Combine: {ans}."
    else:
        ex = f"Drop the ( ): {flat}. Combine like terms: {ans}."
    return dict(prompt=prompt, answer=ans, wrong=wrong, explanation=ex)


def t3_mult_group(v, a, c, m, b, d):
    """a·v + c − m(b·v + d), m >= 2: '5x + 4 − 2(x + 1)'."""
    ans = poly([(a - m * b, v), (c - m * d, None)])
    wrong = [("PARTIAL_DIST", poly([(a - m * b, v), (c - d, None)])),
             ("FIRST_TERM_ONLY", poly([(a - m * b, v), (c + m * d, None)])),
             ("IGNORED_MINUS", poly([(a + m * b, v), (c + m * d, None)]))]
    total = a - m * b + c - m * d
    if total != 0:
        wrong.append(("UNLIKE_COMBINED", tt(total, v)))
    flat = poly([(a, v), (c, None), (-m * b, v), (-m * d, None)])
    return dict(prompt=f"Simplify: {poly([(a, v), (c, None)])} {SUB} {m}({poly([(b, v), (d, None)])})",
                answer=ans, wrong=wrong,
                explanation=f"Distribute {SUB}{m}: {flat}. Combine: {ans}.")


def _ok_result(*vals):
    return all(v != 0 and abs(v) <= 12 for v in vals)


def _pick_t3(rng, kind):
    v = rng.choice(LETTERS)
    if kind in (0, 1, 3):
        a1, a2 = _signed(rng, 1, 9), _signed(rng, 1, 9)
        k1, k2 = _signed(rng, 1, 9), _signed(rng, 1, 9)
        if min(a1, a2, k1, k2) > 0:  # at least one negative in every item
            if rng.random() < 0.5:
                a2 = -a2
            else:
                k2 = -k2
        neg_first = kind == 3
        op = SUB if kind == 1 else "+"
        if neg_first:
            r = (-a1 + a2, -k1 + k2)
        elif op == "+":
            r = (a1 + a2, k1 + k2)
        else:
            r = (a1 - a2, k1 - k2)
        if not _ok_result(*r):
            return None
        return t3_groups((v, None), (a1, k1), op, (a2, k2), neg_first=neg_first)
    if kind == 2:  # bare term minus a group
        a1, a2, k2 = _signed(rng, 2, 9), _signed(rng, 1, 9), _signed(rng, 1, 9)
        if not _ok_result(a1 - a2, -k2):
            return None
        return t3_groups((v, None), (a1, 0), SUB, (a2, k2), single_first=True)
    if kind == 4:  # two letters
        u, w = rng.choice(PAIRS)
        c1 = (_signed(rng, 1, 9), _signed(rng, 1, 9))
        c2 = (_signed(rng, 1, 9), _signed(rng, 1, 9))
        op = rng.choice(("+", SUB))
        r = tuple(x + (y if op == "+" else -y) for x, y in zip(c1, c2))
        if not _ok_result(*r):
            return None
        return t3_groups((u, w), c1, op, c2)
    m = rng.randint(2, 6)
    a, c, b, d = _signed(rng, 2, 9), _signed(rng, 1, 9), _signed(rng, 1, 4), _signed(rng, 1, 4)
    if not _fits(m, b, d) or not _ok_result(a - m * b, c - m * d):
        return None
    return t3_mult_group(v, a, c, m, b, d)


# ---------------------------------------------------------------------------------------------
# Tier 4: factor (7.EE.A.1)
# ---------------------------------------------------------------------------------------------
def t4_factor_pos(v, g, p, q, sq=1):
    """g·p·v + sq·g·q -> g(p·v + sq·q), GCF g, gcd(p, q) = 1."""
    gp, gq = g * p, g * q
    ans = f"{g}({poly([(p, v), (sq * q, None)])})"
    wrong = [("PARTIAL_FACTOR", f"{g}({poly([(p, v), (sq * gq, None)])})")]
    if p >= 2 and q >= 2:
        wrong.append(("SUB_FOR_DIV", f"{g}({poly([(gp - g, v), (sq * (gq - g), None)])})"))
    elif p == 1 and q >= 2:
        wrong.append(("SUB_FOR_DIV", f"{g}({poly([(1, v), (sq * (gq - g), None)])})"))
    wrong.append(("ONE_TERM_FACTOR", f"{gp}({poly([(1, v), (sq * gq, None)])})"))
    wrong.append(("ONE_TERM_FACTOR", f"{gq}({poly([(gp, v), (sq, None)])})"))
    if sq < 0:
        wrong.append(("DROPPED_NEG", f"{g}({poly([(p, v), (q, None)])})"))
    return dict(prompt=f"Factor out the GCF: {poly([(gp, v), (sq * gq, None)])}", answer=ans,
                wrong=wrong,
                explanation=f"GCF of {gp} and {gq} is {g}. Divide each term by {g}: "
                            f"{poly([(p, v), (sq * q, None)])}. So {ans}.")


def t4_factor_neg(v, g, p, q, cs=1):
    """−g·p·v + cs·g·q -> −g(p·v − cs·q): factor out the negative."""
    gp, gq = g * p, g * q
    expr = poly([(-gp, v), (cs * gq, None)])
    ans = f"{SUB}{g}({poly([(p, v), (-cs * q, None)])})"
    wrong = [("SIGN_FACTOR", f"{SUB}{g}({poly([(p, v), (cs * q, None)])})"),
             ("PARTIAL_FACTOR", f"{SUB}{g}({poly([(p, v), (cs * gq, None)])})"),
             ("DROPPED_NEG", f"{g}({poly([(p, v), (cs * q, None)])})")]
    return dict(prompt=f"Factor out {SUB}{g}: {expr}", answer=ans, wrong=wrong,
                explanation=f"Divide each term by {SUB}{g}: {tt(-gp, v)} ÷ {par(-g)} = {tt(p, v)}, "
                            f"{sn(cs * gq)} ÷ {par(-g)} = {sn(-cs * q)}. So {ans}.")


def t4_fill_in(v, f, p, t):
    """f·p·v + f·t = f(p·v + ?) -> t. f is the signed factor, t the signed answer."""
    c = f * t
    expr = poly([(f * p, v), (c, None)])
    wrong = [("PARTIAL_FACTOR", sn(c)), ("SIGN_FACTOR", sn(-t))]
    if c != f:  # a zero choice would be a strange door
        wrong.append(("SUB_FOR_DIV", sn(c - f)))
    return dict(prompt=f"{expr} = {sn(f)}({tt(p, v)} + ?)", answer=sn(t),
                wrong=wrong,
                explanation=f"Divide each term by {sn(f)}: {sn(c)} ÷ {par(f)} = {sn(t)}. "
                            f"So {sn(f)}({poly([(p, v), (t, None)])}).")


def _pick_t4(rng, kind):
    v = rng.choice(LETTERS)
    g, p, q = rng.randint(2, 6), rng.randint(1, 6), rng.randint(1, 6)
    if math.gcd(p, q) != 1 or g * p > 12 or g * q > 12:
        return None
    if kind in (0, 1):
        if p == q == 1:
            return None
        return t4_factor_pos(v, g, p, q, 1 if kind == 0 else -1)
    if kind == 2:
        return t4_factor_neg(v, g, p, q, rng.choice((1, -1)))
    f = g if rng.random() < 0.5 else -g
    return t4_fill_in(v, f, p, q if rng.random() < 0.5 else -q)


# ---------------------------------------------------------------------------------------------
# Tier 5: rewrite to show meaning (7.EE.A.2)
# ---------------------------------------------------------------------------------------------
DOWN_PCT = (10, 20, 25, 30, 40, 50, 60, 75)
UP_PCT = (5, 10, 20, 30, 40, 50)

OFF_FORMS = (
    ("p", "Price p, then {r}% off. New price?"),
    ("s", "A shirt costs s. It goes {r}% off. Sale price?"),
    ("g", "A game costs g. Now {r}% off. New price?"),
    ("c", "Cost c, with {r}% taken off. New cost?"),
    ("b", "A bike costs b. Sale: {r}% off. Sale price?"),
)
UP_FORMS = (
    ("p", "Price p, then {r}% tax. Total price?"),
    ("m", "A meal costs m. Add a {r}% tip. Total?"),
    ("s", "Salary s gets a {r}% raise. New salary?"),
    ("h", "A plant is h tall and grows {r}%. New height?"),
    ("c", "Cost c rises {r}%. New cost?"),
)


def t5_pct_change(letter, tmpl, r, up):
    """A price changes by r %: the one-term form v·(1 ± r/100)."""
    q = Fraction(r, 100)
    m = 1 + q if up else 1 - q
    ans = ctext(m, letter)
    opp = 1 - q if up else 1 + q
    place = (1 + Fraction(r, 1000)) if up else (1 - Fraction(r, 1000))
    sign = "+" if up else SUB
    wrong = [("PART_ONLY", ctext(q, letter)),
             ("PERCENT_AS_NUMBER", f"{letter} {sign} {r}"),
             ("PERCENT_AS_NUMBER", f"{letter} {sign} {dec(q)}")]
    if ok_dec(opp):
        wrong.append(("WRONG_DIRECTION", ctext(opp, letter)))
    if ok_dec(place):
        wrong.append(("PLACE_VALUE", ctext(place, letter)))
    word = "Adding" if up else "Taking off"
    return dict(prompt=tmpl.format(r=r), answer=ans, wrong=wrong,
                explanation=f"{word} {r}% of {letter}: {letter} {sign} {dec(q)}{letter} = "
                            f"{ans}.")


def t5_dec_combine(v, a, r, op):
    """a·v ± r·v with a decimal r: 'n + 0.05n' -> '1.05n'."""
    res = a + r if op == "+" else a - r
    ans = ctext(res, v)
    opp = a - r if op == "+" else a + r
    place = r / 10 if r >= Fraction(1, 10) else r * 10
    wrong = [("PART_ONLY", ctext(r, v))]
    if ok_dec(opp):
        wrong.append(("WRONG_DIRECTION", ctext(opp, v)))
    pl = a + place if op == "+" else a - place
    if (place * 100).denominator == 1 and ok_dec(pl):
        wrong.append(("PLACE_VALUE", ctext(pl, v)))
    wrong.append(("DROPPED_VARIABLE", dec(res)))
    return dict(prompt=f"Simplify: {ctext(Fraction(a), v)} {op} {dec(r)}{v}", answer=ans,
                wrong=wrong,
                explanation=f"Like terms: {dec(Fraction(a))} {op} {dec(r)} = {dec(res)}, so "
                            f"{ctext(Fraction(a), v)} {op} {dec(r)}{v} = {ans}.")


def _frac_or_whole(f: Fraction, v: str):
    """(3/4)x for a proper fraction; None if it is not one (so the candidate is dropped)."""
    if 0 < f < 1 and f.denominator <= 12:
        return ftext(f, v)
    return None


def t5_fracs(v, f1, f2, op):
    """(n/d)v ± (n/d)v with unlike denominators: '(1/2)x + (1/4)x' -> '(3/4)x'."""
    res = f1 + f2 if op == "+" else f1 - f2
    ans = ftext(res, v)
    n1, d1, n2, d2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator
    lcm = d1 * d2 // math.gcd(d1, d2)
    wrong = []
    across_n = n1 + n2 if op == "+" else n1 - n2
    across_d = d1 + d2 if op == "+" else d1 - d2
    if across_n > 0 and across_d > 0:
        t = _frac_or_whole(Fraction(across_n, across_d), v)
        if t:
            wrong.append(("ADD_ACROSS", t))
    top = n1 + n2 if op == "+" else n1 - n2
    if top > 0:
        t = _frac_or_whole(Fraction(top, lcm), v)
        if t:
            wrong.append(("NO_CONVERT", t))
    t = _frac_or_whole(Fraction(n1 * n2, d1 * d2), v)
    if t:
        wrong.append(("MULTIPLIED", t))
    wrong.append(("DROPPED_TERM", ftext(f1, v)))
    wrong.append(("DROPPED_VARIABLE", f"{res.numerator}/{res.denominator}"))
    a, b = n1 * (lcm // d1), n2 * (lcm // d2)
    c = a + b if op == "+" else a - b
    red = f" = {res.numerator}/{res.denominator}" if math.gcd(c, lcm) > 1 else ""
    return dict(prompt=f"Simplify: {ftext(f1, v)} {op} {ftext(f2, v)}", answer=ans, wrong=wrong,
                explanation=f"Use denominator {lcm}: {a}/{lcm} {op} {b}/{lcm} = {c}/{lcm}{red}. "
                            f"So {ans}.")


MULT_FORMS = {
    True: ("Increase by {r}%: multiply by what?", "A price rises {r}%. New price = old price × ?"),
    False: ("Decrease by {r}%: multiply by what?", "Sale: {r}% off. Sale price = old price × ?"),
}


def t5_multiplier(tmpl, r, up):
    """'Increase by 10%: multiply by what?' -> 1.1."""
    q = Fraction(r, 100)
    ans = dec(1 + q if up else 1 - q)
    opp = 1 - q if up else 1 + q
    place = (1 + Fraction(r, 1000)) if up else (1 - Fraction(r, 1000))
    wrong = [("PART_ONLY", dec(q)), ("PERCENT_AS_NUMBER", str(r))]
    if ok_dec(opp):
        wrong.append(("WRONG_DIRECTION", dec(opp)))
    if ok_dec(place):
        wrong.append(("PLACE_VALUE", dec(place)))
    word = "adds" if up else "takes away"
    return dict(prompt=tmpl.format(r=r), answer=ans, wrong=wrong,
                explanation=f"{r}% is {dec(q)}. The whole is 1, and the change {word} {dec(q)}: "
                            f"1 {'+' if up else SUB} {dec(q)} = {ans}.")


def _pct(f: Fraction) -> str:
    return f"{f.numerator}%" if f.denominator == 1 else f"{dec(f)}%"


def t5_meaning(v, r, up):
    """'1.2p means p went up by what percent?' -> 20%."""
    q = Fraction(r, 100)
    m = 1 + q if up else 1 - q
    ans = _pct(Fraction(r))
    wrong = [("RATIO_AS_CHANGE", _pct(m * 100)), ("PLACE_VALUE", f"{dec(m)}%"),
             ("PLACE_VALUE", _pct(m * 10)), ("PLACE_VALUE", _pct(Fraction(r, 10)))]
    verb = "went up" if up else "dropped"
    sign = "+" if up else SUB
    return dict(prompt=f"{ctext(m, v)} means {v} {verb} by what percent?", answer=ans,
                wrong=wrong,
                explanation=f"{ctext(m, v)} = {v} {sign} {dec(q)}{v}, and {dec(q)} is {r}%, so "
                            f"{v} {verb} by {ans}.")


def t5_perimeter(v, k, c):
    """Rectangle: width v, length k·v + c. Perimeter = (2 + 2k)v + 2c."""
    length = poly([(k, v), (c, None)])
    ans = poly([(2 + 2 * k, v), (2 * c, None)])
    wrong = [("PARTIAL_DIST", poly([(2 + 2 * k, v), (c, None)])),
             ("HALF_PERIMETER", poly([(1 + k, v), (c, None)])),
             ("MISSING_SIDE", poly([(1 + 2 * k, v), (2 * c, None)])),
             ("UNLIKE_COMBINED", tt(2 + 2 * k + 2 * c, v))]
    return dict(prompt=f"Rectangle: width {v}, length {length}. Perimeter?", answer=ans,
                wrong=wrong,
                explanation=f"All 4 sides: {v} + ({length}) + {v} + ({length}). "
                            f"Combine like terms: {ans}.")


def _build_frac_pairs():
    fracs = [Fraction(n, d) for d in range(2, 13) for n in range(1, d) if math.gcd(n, d) == 1]
    pairs = []
    for f1 in fracs:
        for f2 in fracs:
            d1, d2 = f1.denominator, f2.denominator
            if d1 == d2 or d1 * d2 // math.gcd(d1, d2) > 12:
                continue
            if f1 + f2 < 1:
                pairs.append((f1, f2, "+"))
            if f1 > f2:
                pairs.append((f1, f2, SUB))
    return pairs


FRAC_PAIRS = _build_frac_pairs()
DEC_PARTS = tuple(Fraction(n, 100) for n in (5, 10, 20, 30, 40, 50, 60, 25, 75))


def _pick_t5(rng, kind):
    if kind == 0:
        letter, tmpl = rng.choice(OFF_FORMS)
        return t5_pct_change(letter, tmpl, rng.choice(DOWN_PCT), False)
    if kind == 1:
        letter, tmpl = rng.choice(UP_FORMS)
        return t5_pct_change(letter, tmpl, rng.choice(UP_PCT), True)
    if kind == 2:
        v = rng.choice(LETTERS)
        a, r, op = rng.randint(1, 5), rng.choice(DEC_PARTS), rng.choice(("+", SUB))
        res = a + r if op == "+" else a - r
        return t5_dec_combine(v, a, r, op) if ok_dec(res) else None
    if kind == 3:
        f1, f2, op = rng.choice(FRAC_PAIRS)
        return t5_fracs(rng.choice(LETTERS), f1, f2, op)
    if kind == 4:
        up = rng.random() < 0.5
        r = rng.choice(UP_PCT if up else DOWN_PCT)
        return t5_multiplier(rng.choice(MULT_FORMS[up]), r, up)
    if kind == 5:
        up = rng.random() < 0.5
        return t5_meaning(rng.choice(WORD_LETTERS), rng.choice(UP_PCT if up else DOWN_PCT), up)
    return t5_perimeter(rng.choice(WORD_LETTERS), rng.randint(1, 3), rng.randint(1, 6))


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
PICKERS = {1: _pick_t1, 2: _pick_t2, 3: _pick_t3, 4: _pick_t4, 5: _pick_t5}

# How many items of each builder kind per tier (40 each).
KIND_COUNTS = {
    1: [9, 5, 9, 4, 7, 6],
    2: [8, 6, 8, 8, 5, 5],
    3: [7, 10, 5, 4, 5, 9],
    4: [8, 7, 14, 11],
    5: [7, 6, 7, 7, 5, 4, 4],
}

_NUM = re.compile(r"(?<![\d./])\d+(?![\d./])")


def arith_candidates(answer: str) -> list:
    """Near-miss texts: one whole number of the answer nudged by +-1 or +-2 (decimals and
    fractions are left alone). A coefficient stays >= 2 so the text never shows '1x' or '0x'."""
    out = []
    for d in (1, -1, 2, -2):
        for m in _NUM.finditer(answer):
            n = int(m.group()) + d
            nxt = answer[m.end()] if m.end() < len(answer) else ""
            floor = 2 if (nxt.isalpha() or nxt == "(") else 1
            if n < floor:
                continue
            out.append(answer[:m.start()] + str(n) + answer[m.end():])
    return out


def pick_wrong(cands, answer_fp, rng, usage):
    """Up to three (label, text) with distinct values: one per label first, the labels this tier
    has used least first (ties in random order), so every misconception gets its turns."""
    by_label: dict = {}
    for lab, text in cands:
        by_label.setdefault(lab, []).append(text)
    order = list(by_label)
    rng.shuffle(order)
    order.sort(key=lambda lab: usage[lab])
    seen, chosen = {answer_fp}, []
    for rnd in range(max(len(v) for v in by_label.values())):
        for lab in order:
            lst = by_label[lab]
            if rnd < len(lst) and len(chosen) < 3:
                fp = fingerprint(lst[rnd])
                if fp in seen:
                    continue
                seen.add(fp)
                chosen.append((lab, lst[rnd]))
                usage[lab] += 1
    return chosen, seen


def make_item(built: dict, tier: int, answer_pos: int, rng: random.Random, usage):
    ans = built["answer"]
    wrong, seen = pick_wrong(built["wrong"], fingerprint(ans), rng, usage)
    if not wrong:
        return None
    for text in arith_candidates(ans):
        if len(wrong) == 3:
            break
        fp = fingerprint(text)
        if fp not in seen:
            seen.add(fp)
            wrong.append(("ARITH", text))
    if len(wrong) < 3:
        return None
    texts = [ans] + [t for _, t in wrong]
    if (len(built["prompt"]) > 60 or len(built["explanation"]) > 160
            or any(len(t) > 14 for t in texts) or len(set(texts)) != 4):
        return None
    pairs = wrong[:answer_pos] + [(None, ans)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": built["prompt"],
        "choices": [t for _, t in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": built["explanation"],
    }


def gen_tier(tier: int, count: int, declared, rng: random.Random, max_attempts: int = 200000):
    counts = KIND_COUNTS[tier]
    kinds = [k for k, n in enumerate(counts) for _ in range(n)]
    kinds = (kinds * (count // len(kinds) + 1))[:count]
    rng.shuffle(kinds)
    positions = [i % 4 for i in range(count)]
    rng.shuffle(positions)
    items, prompts, attempts, usage = [], set(), 0, Counter()
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        built = PICKERS[tier](rng, kinds[len(items)])
        if built is None or built["prompt"] in prompts:
            continue
        for lab, _ in built["wrong"]:
            if lab not in declared and lab != "ARITH":
                raise KeyError(f"undeclared misconception {lab}")
        snapshot = Counter(usage)
        item = make_item(built, tier, positions[len(items)], rng, usage)
        if item is None:
            usage.clear()
            usage.update(snapshot)  # a rejected item does not count against its labels
            continue
        prompts.add(built["prompt"])
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    declared = set(manifest["misconceptions"])
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, declared, rng))
    return items
