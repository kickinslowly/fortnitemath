"""Procedural generator for the expressions cartridge (fnm-cart/1, grade 6, 6.EE.A.2-4).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4
shape without ``id``. Stdlib only. Deterministic for a given ``rng`` seed. Imports nothing from
other cartridges.

Design
------
* Every item comes from a *builder*: a pure function of its parameters returning the prompt, the
  correct choice, an ordered list of ``(misconception, wrong choice)`` candidates and the
  explanation. Builders are deterministic so the tests can call them with hand-worked parameters
  (golden cases). The random part only picks parameters (``_pick_*``).
* Candidates are listed most-telling first. ``make_item`` keeps the first three whose VALUE differs
  from the answer and from every kept choice (``fingerprint``: the expression evaluated at several
  variable assignments, so ``3x + 6`` and ``6 + 3x`` count as equal), then fills with ``ARITH``
  (a number in the answer nudged by 1 or 2) only if fewer than three survive.
* No negatives anywhere (grade-6 expressions). Bounds are the manifest's ``bounds`` string; the
  tests walk every baked prompt to assert them.
"""
from __future__ import annotations

import math
import random
import re
from fractions import Fraction

SUB, MUL, DIV = "−", "×", "÷"  # U+2212, U+00D7, U+00F7

LETTERS = ("n", "x", "y", "a", "b", "m", "p", "t", "w", "k")
PAIRS = (("x", "y"), ("a", "b"), ("m", "n"), ("p", "t"))


# ---------------------------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------------------------
def term(c: int, v: str) -> str:
    """Coefficient c times variable v: 'x' for 1, '3x' otherwise."""
    return v if c == 1 else f"{c}{v}"


# ---------------------------------------------------------------------------------------------
# Value engine (for distinctness only; never used to pick the right answer)
# ---------------------------------------------------------------------------------------------
_TOKEN = re.compile(r"\s*(\d+|[A-Za-z]|[+\-−×÷^()])")


def _tokens(text: str) -> list:
    toks, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"bad text {text!r}")
        toks.append(m.group(1).replace("-", SUB))
        pos = m.end()
    out = []
    for t in toks:  # implicit multiplication: 3x, 2(…), rt, x(…), )(
        if out and (out[-1].isdigit() or out[-1].isalpha() or out[-1] == ")") \
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
        if t.isdigit():
            return Fraction(int(t))
        if t.isalpha():
            return Fraction(env[t])
        if t == "(":
            v = expr(1)
            if peek() != ")":
                raise ValueError("unbalanced")
            pos += 1
            return v
        raise ValueError(f"unexpected {t!r}")

    def power():
        nonlocal pos
        b = atom()
        if peek() == "^":
            pos += 1
            return b ** power()
        return b

    def expr(level):
        nonlocal pos
        if level == 3:
            return power()
        lhs = expr(level + 1)
        ops = ("+", SUB) if level == 1 else (MUL, DIV)
        while peek() in ops:
            op = toks[pos]
            pos += 1
            rhs = expr(level + 1)
            if op == "+":
                lhs = lhs + rhs
            elif op == SUB:
                lhs = lhs - rhs
            elif op == MUL:
                lhs = lhs * rhs
            else:
                lhs = lhs / rhs  # ZeroDivisionError propagates
        return lhs

    v = expr(1)
    if pos != len(toks):
        raise ValueError(f"trailing tokens in {text!r}")
    return v


_SAMPLE_VALUES = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)


def fingerprint(text: str):
    """Hashable identity of a choice's VALUE: the expression evaluated at 6 assignments of distinct
    primes to its letters (two different polynomials of degree <= 3 cannot agree on all of them).
    Non-expressions (words) fingerprint as their own text."""
    letters = sorted(set(re.findall(r"[A-Za-z]", text)))
    if letters and all(len(w) > 1 for w in re.findall(r"[A-Za-z]+", text)):
        return ("text", text.strip())
    try:
        vals = []
        for s in range(6):
            env = {L: _SAMPLE_VALUES[(i * 5 + s * 7) % len(_SAMPLE_VALUES)] + s
                   for i, L in enumerate("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")}
            try:
                vals.append(value(text, env))
            except ZeroDivisionError:
                vals.append("div0")
        return ("value", tuple(vals))
    except (ValueError, KeyError):
        return ("text", text.strip())


# ---------------------------------------------------------------------------------------------
# Tier 1: words to expressions (6.EE.A.2a)
# ---------------------------------------------------------------------------------------------
def t1_less_than(v, k):
    return dict(prompt=f"{k} less than {v}", answer=f"{v} {SUB} {k}",
                wrong=[("ORDER_SUB", f"{k} {SUB} {v}"), ("WRONG_OP", f"{v} + {k}"),
                       ("WRONG_OP", f"{k}{v}")],
                explanation=f"Start at {v} and take {k} away: {v} {SUB} {k}. "
                            f"'Less than' flips the order of the words.")


def t1_subtract_from(v, k):
    return dict(prompt=f"Subtract {v} from {k}", answer=f"{k} {SUB} {v}",
                wrong=[("ORDER_SUB", f"{v} {SUB} {k}"), ("WRONG_OP", f"{k} + {v}"),
                       ("WRONG_OP", f"{k}{v}")],
                explanation=f"Start with {k}, then take {v} away from it: {k} {SUB} {v}.")


def t1_divided_by(v, k, quotient_words=False):
    p = f"The quotient of {v} and {k}" if quotient_words else f"{v} divided by {k}"
    return dict(prompt=p, answer=f"{v} {DIV} {k}",
                wrong=[("SWAP_DIV", f"{k} {DIV} {v}"), ("WRONG_OP", f"{k}{v}"),
                       ("WRONG_OP", f"{v} {SUB} {k}")],
                explanation=f"{v} is the number being split into {k} equal parts: {v} {DIV} {k}.")


def t1_more_than_product(v, a, b):
    return dict(prompt=f"{a} more than the product of {b} and {v}", answer=f"{b}{v} + {a}",
                wrong=[("SWAPPED_NUMS", f"{a}{v} + {b}"), ("EXTRA_PARENS", f"{b}({v} + {a})"),
                       ("WRONG_OP", f"{b}{v} {SUB} {a}")],
                explanation=f"The product of {b} and {v} is {b}{v}. {a} more than that: "
                            f"{b}{v} + {a}.")


def t1_less_than_product(v, a, b):
    return dict(prompt=f"{a} less than the product of {b} and {v}", answer=f"{b}{v} {SUB} {a}",
                wrong=[("ORDER_SUB", f"{a} {SUB} {b}{v}"),
                       ("EXTRA_PARENS", f"{b}({v} {SUB} {a})"),
                       ("SWAPPED_NUMS", f"{a}{v} {SUB} {b}")],
                explanation=f"The product of {b} and {v} is {b}{v}. Take {a} away from it: "
                            f"{b}{v} {SUB} {a}.")


def t1_times_sum(v, a, b):
    return dict(prompt=f"{b} times the sum of {v} and {a}", answer=f"{b}({v} + {a})",
                wrong=[("MISSING_PARENS", f"{b}{v} + {a}"), ("SWAPPED_NUMS", f"{a}({v} + {b})"),
                       ("WRONG_OP", f"{b} + {v} + {a}")],
                explanation=f"Find the sum {v} + {a} first, so keep it together in ( ), "
                            f"then times {b}: {b}({v} + {a}).")


def t1_times_difference(v, a, b):
    return dict(prompt=f"{b} times the difference of {v} and {a}", answer=f"{b}({v} {SUB} {a})",
                wrong=[("MISSING_PARENS", f"{b}{v} {SUB} {a}"),
                       ("ORDER_SUB", f"{b}({a} {SUB} {v})"),
                       ("SWAPPED_NUMS", f"{a}({v} {SUB} {b})")],
                explanation=f"The difference of {v} and {a} is {v} {SUB} {a}. Keep it in ( ), "
                            f"then times {b}: {b}({v} {SUB} {a}).")


def t1_divide_sum(v, a, b):
    return dict(prompt=f"Divide the sum of {v} and {a} by {b}", answer=f"({v} + {a}) {DIV} {b}",
                wrong=[("MISSING_PARENS", f"{v} + {a} {DIV} {b}"),
                       ("SWAP_DIV", f"{b} {DIV} ({v} + {a})"),
                       ("SWAPPED_NUMS", f"({v} + {b}) {DIV} {a}")],
                explanation=f"The whole sum {v} + {a} is divided, so it goes in ( ): "
                            f"({v} + {a}) {DIV} {b}.")


def _pick_t1(rng, kind):
    v = rng.choice(LETTERS)
    a, b = rng.randint(2, 10), rng.randint(2, 10)
    if kind == 0:
        return t1_less_than(v, rng.randint(2, 20))
    if kind == 1:
        return t1_subtract_from(v, rng.randint(2, 20))
    if kind == 2:
        return t1_divided_by(v, rng.randint(2, 10), quotient_words=rng.random() < 0.5)
    if a == b:
        return None
    return (t1_more_than_product, t1_less_than_product, t1_times_sum, t1_times_difference,
            t1_divide_sum)[kind - 3](v, a, b)


# ---------------------------------------------------------------------------------------------
# Tier 2: parts of an expression (6.EE.A.2b)
# ---------------------------------------------------------------------------------------------
def t2_coefficient(v, c, k, const_first=False):
    e = f"{k} + {c}{v}" if const_first else f"{c}{v} + {k}"
    return dict(prompt=f"Coefficient of {v} in {e}?", answer=str(c),
                wrong=[("COEF_CONST_MIX", str(k)), ("TERM_FOR_COEF", f"{c}{v}"),
                       ("VARIABLE_FOR_NUMBER", v)],
                explanation=f"In {e}, {c} multiplies {v}, so {c} is the coefficient. "
                            f"{k} stands alone: it is the constant.")


def t2_hidden_one(v, k, other=None):
    """Coefficient of a bare variable: ``v + k`` or ``c·u + v + k`` (other = (u, c))."""
    if other:
        u, c = other
        e = f"{c}{u} + {v} + {k}"
        wrong = [("HIDDEN_ONE", "0"), ("OTHER_VARIABLE", str(c)), ("COEF_CONST_MIX", str(k))]
    else:
        e = f"{v} + {k}"
        wrong = [("HIDDEN_ONE", "0"), ("COEF_CONST_MIX", str(k)), ("VARIABLE_FOR_NUMBER", v)]
    return dict(prompt=f"Coefficient of {v} in {e}?", answer="1", wrong=wrong,
                explanation=f"{v} alone means 1 × {v}, so the coefficient of {v} is 1.")


def t2_two_var_coefficient(u, v, cu, cv, k):
    e = f"{cu}{u} + {cv}{v} + {k}"
    return dict(prompt=f"Coefficient of {v} in {e}?", answer=str(cv),
                wrong=[("OTHER_VARIABLE", str(cu)), ("COEF_CONST_MIX", str(k)),
                       ("TERM_FOR_COEF", f"{cv}{v}")],
                explanation=f"The number in front of {v} is {cv}, so {cv} is its coefficient. "
                            f"{cu} goes with {u}; {k} is the constant.")


def t2_constant(v, c, k, const_first=False):
    e = f"{k} + {c}{v}" if const_first else f"{c}{v} + {k}"
    return dict(prompt=f"Constant term in {e}?", answer=str(k),
                wrong=[("COEF_CONST_MIX", str(c)), ("VARIABLE_TERM", f"{c}{v}"),
                       ("VARIABLE_TERM", v)],
                explanation=f"The constant has no letter, so it never changes: {k}. "
                            f"{c} is the coefficient of {v}.")


def t2_count_terms(var_terms, k):
    """var_terms: [(coef, letter)] with distinct letters; one constant k at the end. (Counting the
    + signs would also be a real slip, but with one constant it always equals COUNTS_VARIABLES.)"""
    parts = [term(c, v) for c, v in var_terms] + [str(k)]
    e = " + ".join(parts)
    n = len(parts)
    pieces = sum(2 if c > 1 else 1 for c, _ in var_terms) + 1
    return dict(prompt=f"How many terms in {e}?", answer=str(n),
                wrong=[("COUNTS_VARIABLES", str(len(var_terms))),
                       ("COUNTS_PIECES", str(pieces))],
                explanation=f"Terms are the pieces joined by +: {', '.join(parts)}. "
                            f"That is {n} terms.")


NAMES = {"+": "sum", SUB: "difference", MUL: "product", DIV: "quotient"}
WORD_ORDER = ("sum", "difference", "product", "quotient")


def t2_name(form, v, a, b):
    """form: (display template, last op, inner op)."""
    shape, last, inner = form
    e = shape.format(v=v, a=a, b=b, S=SUB, D=DIV)
    right, inner_w = NAMES[last], NAMES[inner]
    others = [w for w in WORD_ORDER if w not in (right, inner_w)]
    first = {"+": "add", SUB: "subtract", MUL: "multiply", DIV: "divide"}
    return dict(prompt=f"What kind of expression is {e}?", answer=right,
                wrong=[("INNER_OP", inner_w)] + [("LAST_STEP", w) for w in others],
                explanation=f"In {e} you {first[inner]} first and {first[last]} last. "
                            f"The last step names it: a {right}.")


NAME_FORMS = (
    ("{b}({v} + {a})", MUL, "+"),
    ("{b}({v} {S} {a})", MUL, SUB),
    ("{b}{v} + {a}", "+", MUL),
    ("{b}{v} {S} {a}", SUB, MUL),
    ("({v} + {a}) {D} {b}", DIV, "+"),
    ("({v} {S} {a}) {D} {b}", DIV, SUB),
    ("{v} {D} {b} + {a}", "+", DIV),
    ("{a} + {b}{v}", "+", MUL),
)


def _pick_t2(rng, kind):
    v = rng.choice(LETTERS)
    if kind == 0:
        c, k = rng.randint(2, 10), rng.randint(1, 20)
        return None if c == k else t2_coefficient(v, c, k, rng.random() < 0.3)
    if kind == 1:
        k = rng.randint(2, 20)
        if rng.random() < 0.5:
            u, v = rng.choice(PAIRS)
            c = rng.randint(2, 10)
            return None if c == k else t2_hidden_one(v, k, (u, c))
        return t2_hidden_one(v, k)
    if kind == 2:
        u, v = rng.choice(PAIRS)
        cu, cv, k = rng.randint(2, 10), rng.randint(2, 10), rng.randint(1, 20)
        return None if len({cu, cv, k}) < 3 else t2_two_var_coefficient(u, v, cu, cv, k)
    if kind == 3:
        c, k = rng.randint(2, 10), rng.randint(1, 20)
        return None if c == k else t2_constant(v, c, k, rng.random() < 0.3)
    if kind == 4:
        letters = rng.choice((("a", "b", "c"), ("x", "y", "z"), ("m", "n", "p")))
        nv = rng.choice((2, 2, 3))
        coefs = [rng.choice((1, 2, 3, 4, 5, 6, 7, 8, 9)) for _ in range(nv)]
        if all(c == 1 for c in coefs):
            return None
        return t2_count_terms(list(zip(coefs, letters[:nv])), rng.randint(1, 20))
    a, b = rng.randint(1, 10), rng.randint(2, 10)
    return t2_name(rng.choice(NAME_FORMS), v, a, b)


# ---------------------------------------------------------------------------------------------
# Tier 3: evaluate (6.EE.A.2c). All candidate values are plain whole numbers.
# ---------------------------------------------------------------------------------------------
def _cat(*parts) -> int:
    """Digits written side by side: _cat(3, 5) = 35."""
    return int("".join(str(p) for p in parts))


def _num_item(prompt, correct, wrong, explanation):
    return dict(prompt=prompt, answer=str(correct),
                wrong=[(lab, str(w)) for lab, w in wrong if w is not None and 0 <= w <= 999],
                explanation=explanation)


def t3_linear(v, c, k, n):
    """c·v + k at v = n."""
    return _num_item(f"Find {c}{v} + {k} when {v} = {n}", c * n + k,
                     [("CONCAT", _cat(c, n) + k), ("ORDER", c * (n + k)), ("ADD_COEF", c + n + k)],
                     f"{c}{v} means {c} × {n} = {c * n}. Then {c * n} + {k} = {c * n + k}.")


def t3_linear_const_first(v, c, k, n):
    """k + c·v at v = n."""
    return _num_item(f"Find {k} + {c}{v} when {v} = {n}", k + c * n,
                     [("ORDER", (k + c) * n), ("CONCAT", k + _cat(c, n)), ("ADD_COEF", k + c + n)],
                     f"Multiply first: {c} × {n} = {c * n}. Then {k} + {c * n} = {k + c * n}.")


def t3_coef_square(v, c, n):
    """c·v^2 at v = n."""
    return _num_item(f"Find {c}{v}^2 when {v} = {n}", c * n * n,
                     [("SQUARE_PRODUCT", (c * n) ** 2), ("EXP_AS_TIMES", c * n * 2),
                      ("ADD_COEF", c + n * n)],
                     f"Square first: {n}^2 = {n * n}. Then {c} × {n * n} = {c * n * n}.")


def t3_power_plus(v, e, k, n):
    """v^e + k at v = n."""
    p = n ** e
    return _num_item(f"Find {v}^{e} + {k} when {v} = {n}", p + k,
                     [("EXP_AS_TIMES", n * e + k), ("ORDER", (n + k) ** e)],
                     f"{n}^{e} = {' × '.join([str(n)] * e)} = {p}. Then {p} + {k} = {p + k}.")


def t3_group(v, c, op, k, n):
    """c(v op k) at v = n."""
    g = n + k if op == "+" else n - k
    flat = c * n + k if op == "+" else c * n - k
    return _num_item(f"Find {c}({v} {op} {k}) when {v} = {n}", c * g,
                     [("PARENS_SKIPPED", flat),
                      ("ADD_COEF", c + g),
                      ("CONCAT", _cat(c, n) + k if op == "+" else _cat(c, n) - k)],
                     f"( ) first: {n} {op} {k} = {g}. Then {c} × {g} = {c * g}.")


def t3_two_vars(u, v, c, op, m, n):
    """c·u op v at u = m, v = n."""
    cm = c * m
    val = cm + n if op == "+" else cm - n
    cat = _cat(c, m) + n if op == "+" else _cat(c, m) - n
    add = c + m + n if op == "+" else c + m - n
    return _num_item(f"Find {c}{u} {op} {v} when {u} = {m}, {v} = {n}", val,
                     [("CONCAT", cat), ("ADD_COEF", add)],
                     f"{c}{u} means {c} × {m} = {cm}. Then {cm} {op} {n} = {val}.")


def t3_formula_square(n):
    return _num_item(f"A = s^2. Find A when s = {n}", n * n,
                     [("EXP_AS_TIMES", 2 * n)],
                     f"s^2 means s × s: {n} × {n} = {n * n}.")


def t3_formula_perimeter(l, w):
    return _num_item(f"P = 2L + 2W. Find P when L = {l}, W = {w}", 2 * l + 2 * w,
                     [("ADD_COEF", 2 + l + 2 + w), ("CONCAT", _cat(2, l) + _cat(2, w)),
                      ("ORDER", 2 * (l + 2) * w)],
                     f"2L = 2 × {l} = {2 * l}, 2W = 2 × {w} = {2 * w}. "
                     f"Then {2 * l} + {2 * w} = {2 * l + 2 * w}.")


def t3_formula_rate(r, t):
    return _num_item(f"d = rt. Find d when r = {r}, t = {t}", r * t,
                     [("ADD_COEF", r + t), ("CONCAT", _cat(r, t))],
                     f"rt means r × t: {r} × {t} = {r * t}.")


def _pick_t3(rng, kind):
    v = rng.choice(LETTERS)
    if kind == 0:
        c, n, k = rng.randint(2, 10), rng.randint(2, 9), rng.randint(1, 20)
        return t3_linear(v, c, k, n) if c * n + k <= 100 else None
    if kind == 1:
        c, n, k = rng.randint(2, 10), rng.randint(2, 9), rng.randint(1, 20)
        return t3_linear_const_first(v, c, k, n) if c * n + k <= 100 else None
    if kind == 2:
        n = rng.choice((2, 3))
        c = rng.randint(2, 10)
        return t3_coef_square(v, c, n)
    if kind == 3:
        if rng.random() < 0.25:
            e, n = 3, rng.randint(2, 4)
        else:
            e, n = 2, rng.randint(3, 10)
        k = rng.randint(1, 20)
        return t3_power_plus(v, e, k, n) if n ** e + k <= 100 else None
    if kind == 4:
        op = rng.choice(("+", SUB))
        c, n, k = rng.randint(2, 10), rng.randint(2, 10), rng.randint(1, 8)
        g = n + k if op == "+" else n - k
        return t3_group(v, c, op, k, n) if 2 <= g <= 10 else None
    if kind == 5:
        u, w = rng.choice(PAIRS)
        op = rng.choice(("+", SUB))
        c, m, n = rng.randint(2, 10), rng.randint(2, 9), rng.randint(1, 20)
        val = c * m + n if op == "+" else c * m - n
        return t3_two_vars(u, w, c, op, m, n) if 1 <= val <= 100 else None
    f = rng.randrange(3)
    if f == 0:
        return t3_formula_square(rng.randint(3, 10))
    if f == 1:
        return t3_formula_perimeter(rng.randint(2, 10), rng.randint(2, 10))
    return t3_formula_rate(rng.randint(2, 10), rng.randint(2, 10))


# ---------------------------------------------------------------------------------------------
# Tier 4: distributive property (6.EE.A.3)
# ---------------------------------------------------------------------------------------------
def t4_expand(v, a, b, c, op="+"):
    """a(b·v op c) -> ab·v op ac."""
    inner = f"{term(b, v)} {op} {c}"
    ab, ac = a * b, a * c
    wrong = [("PARTIAL_DIST", f"{term(ab, v)} {op} {c}")]
    if op == SUB:
        wrong.append(("SIGN_DROP", f"{term(ab, v)} + {ac}"))
        wrong.append(("ADD_FOR_MUL", f"{term(ab, v)} {SUB} {a + c}"))
    else:
        wrong.append(("ADD_FOR_MUL", f"{term(ab, v)} + {a + c}"))
        wrong.append(("UNLIKE_COMBINED", term(ab + ac, v)))
    ex = (f"{a} × {term(b, v)} = {term(ab, v)}" if b > 1 else f"{a} × {v} = {term(ab, v)}")
    return dict(prompt=f"Distribute: {a}({inner})", answer=f"{term(ab, v)} {op} {ac}",
                wrong=wrong,
                explanation=f"Multiply each term by {a}: {ex} and {a} × {c} = {ac}. "
                            f"So {term(ab, v)} {op} {ac}.")


def t4_expand_const_first(v, a, c):
    """a(c + v) -> ac + a·v."""
    ac = a * c
    return dict(prompt=f"Distribute: {a}({c} + {v})", answer=f"{ac} + {term(a, v)}",
                wrong=[("PARTIAL_DIST", f"{ac} + {v}"), ("ADD_FOR_MUL", f"{a + c} + {term(a, v)}"),
                       ("UNLIKE_COMBINED", term(ac + a, v))],
                explanation=f"Multiply each term by {a}: {a} × {c} = {ac} and {a} × {v} = "
                            f"{term(a, v)}. So {ac} + {term(a, v)}.")


def t4_factor(v, g, p, q, op="+"):
    """g·p·v op g·q  ->  g(p·v op q), gcd(p, q) = 1."""
    gp, gq = g * p, g * q
    wrong = [("PARTIAL_FACTOR", f"{g}({term(p, v)} {op} {gq})")]
    if p >= 2 and q >= 2:
        wrong.append(("SUB_FOR_DIV", f"{g}({term(gp - g, v)} {op} {gq - g})"))
    if op == "+" or p > q:  # never show a door like 2x(4 − 7)
        wrong.append(("X_FROM_BOTH", f"{term(g, v)}({p} {op} {q})"))
    return dict(prompt=f"Factor out the GCF: {term(gp, v)} {op} {gq}",
                answer=f"{g}({term(p, v)} {op} {q})", wrong=wrong,
                explanation=f"GCF of {gp} and {gq} is {g}. {term(gp, v)} ÷ {g} = {term(p, v)}, "
                            f"{gq} ÷ {g} = {q}. So {g}({term(p, v)} {op} {q}).")


def _pick_t4(rng, kind):
    v = rng.choice(LETTERS)
    if kind == 0:
        a, c = rng.randint(2, 10), rng.randint(2, 10)
        return t4_expand(v, a, 1, c)
    if kind == 1:
        a, c = rng.randint(2, 10), rng.randint(2, 10)
        return t4_expand(v, a, 1, c, SUB)
    if kind == 2:
        a, b, c = rng.randint(2, 5), rng.randint(2, 5), rng.randint(1, 10)
        return t4_expand(v, a, b, c, rng.choice(("+", "+", SUB)))
    if kind == 3:
        return t4_expand_const_first(v, rng.randint(2, 10), rng.randint(2, 10))
    g = rng.randint(2, 10)
    p, q = rng.randint(1, 10), rng.randint(1, 10)
    if math.gcd(p, q) != 1 or (p == 1 and q == 1) or g * p > 100 or g * q > 100:
        return None
    return t4_factor(v, g, p, q, rng.choice(("+", SUB)))


# ---------------------------------------------------------------------------------------------
# Tier 5: equivalent expressions (6.EE.A.3, A.4)
# ---------------------------------------------------------------------------------------------
def t5_dist_plus_terms(v, a, c, d):
    """a(v + c) + d·v -> (a + d)v + ac."""
    ac, s = a * c, a + d
    return dict(prompt=f"Simplify: {a}({v} + {c}) + {term(d, v)}", answer=f"{term(s, v)} + {ac}",
                wrong=[("PARTIAL_DIST", f"{term(s, v)} + {c}"),
                       ("UNLIKE_COMBINED", term(s + ac, v)),
                       ("DROPPED_TERM", f"{term(a, v)} + {ac}")],
                explanation=f"{a}({v} + {c}) = {term(a, v)} + {ac}. Then {term(a, v)} + "
                            f"{term(d, v)} = {term(s, v)}. So {term(s, v)} + {ac}.")


def t5_dist_minus_term(v, a, c):
    """a(v + c) − v -> (a − 1)v + ac."""
    ac = a * c
    return dict(prompt=f"Simplify: {a}({v} + {c}) {SUB} {v}", answer=f"{term(a - 1, v)} + {ac}",
                wrong=[("SIGN_DROP", f"{term(a + 1, v)} + {ac}"),
                       ("PARTIAL_DIST", f"{term(a - 1, v)} + {c}"),
                       ("UNLIKE_COMBINED", term(a - 1 + ac, v))],
                explanation=f"{a}({v} + {c}) = {term(a, v)} + {ac}. Then {term(a, v)} {SUB} {v} "
                            f"= {term(a - 1, v)}. So {term(a - 1, v)} + {ac}.")


def t5_repeat_add(v, n):
    """v + v + ... (n times) -> n·v."""
    return dict(prompt="Simplify: " + " + ".join([v] * n), answer=term(n, v),
                wrong=[("POWER_FOR_SUM", f"{v}^{n}"), ("POWER_FOR_SUM", f"{n}{v}^{n}")],
                explanation=f"{n} groups of {v} added together is {n} × {v} = {term(n, v)}.")


def t5_like_terms(v, a, b, op="+"):
    """a·v op b·v -> (a op b)v; b may be 1 (a bare v)."""
    s = a + b if op == "+" else a - b
    wrong = []
    if b == 1:
        wrong.append(("HIDDEN_ONE", term(a, v)))
    if op == SUB:
        wrong.append(("SIGN_DROP", term(a + b, v)))
    wrong.append(("POWER_FOR_SUM", f"{term(s, v)}^2"))
    if b > 1 and op == "+":
        wrong.append(("MULT_COEF", term(a * b, v)))
    one = f" ({v} is 1{v})" if b == 1 else ""
    return dict(prompt=f"Simplify: {term(a, v)} {op} {term(b, v)}", answer=term(s, v),
                wrong=wrong,
                explanation=f"Like terms: {op == '+' and 'add' or 'subtract'} the coefficients"
                            f"{one}. {a} {op} {b} = {s}, so {term(s, v)}.")


def t5_repeat_mul(v, n):
    """v × v (× v) -> v^n."""
    return dict(prompt="Simplify: " + f" {MUL} ".join([v] * n), answer=f"{v}^{n}",
                wrong=[("SUM_FOR_POWER", term(n, v)), ("SUM_FOR_POWER", f"{n}{v}^{n}"),
                       ("ARITH", f"{v}^{n + 1}")],  # miscounted the factors
                explanation=f"{v} multiplied by itself {n} times is {v}^{n}. "
                            f"({term(n, v)} would be {v} added {n} times.)")


def t5_collect(v, a, c, b):
    """a·v + c + b·v -> (a + b)v + c."""
    s = a + b
    return dict(prompt=f"Simplify: {term(a, v)} + {c} + {term(b, v)}", answer=f"{term(s, v)} + {c}",
                wrong=[("UNLIKE_COMBINED", term(s + c, v)),
                       ("POWER_FOR_SUM", f"{term(s, v)}^2 + {c}"),
                       ("DROPPED_TERM", f"{term(a, v)} + {c}")],
                explanation=f"Like terms {term(a, v)} and {term(b, v)} make {term(s, v)}. "
                            f"{c} has no {v}, so it stays: {term(s, v)} + {c}.")


def t5_two_groups(v, a, c, b, d):
    """a(v + c) + b(v + d) -> (a + b)v + (ac + bd)."""
    s, k = a + b, a * c + b * d
    return dict(prompt=f"Simplify: {a}({v} + {c}) + {b}({v} + {d})", answer=f"{term(s, v)} + {k}",
                wrong=[("PARTIAL_DIST", f"{term(s, v)} + {c + d}"),
                       ("UNLIKE_COMBINED", term(s + k, v)),
                       ("ADD_FOR_MUL", f"{term(s, v)} + {a + c + b + d}")],
                explanation=f"{term(a, v)} + {a * c} and {term(b, v)} + {b * d}. "
                            f"{v} terms: {term(s, v)}. Numbers: {a * c} + {b * d} = {k}. "
                            f"So {term(s, v)} + {k}.")


def _pick_t5(rng, kind):
    v = rng.choice(LETTERS)
    if kind == 0:
        a, c, d = rng.randint(2, 9), rng.randint(2, 10), rng.randint(1, 9)
        return t5_dist_plus_terms(v, a, c, d) if a + d <= 10 else None
    if kind == 1:
        return t5_dist_minus_term(v, rng.randint(2, 10), rng.randint(2, 10))
    if kind == 2:
        return t5_repeat_add(v, rng.randint(2, 5))
    if kind == 3:
        op = rng.choice(("+", "+", SUB))
        a, b = rng.randint(2, 10), rng.choice((1, 2, 3, 4, 5, 6, 7, 8, 9))
        if op == SUB and a <= b + 1:
            return None
        if a == b:
            return None
        return t5_like_terms(v, a, b, op)
    if kind == 4:
        return t5_repeat_mul(v, rng.choice((2, 2, 3)))
    if kind == 5:
        a, b, c = rng.randint(2, 9), rng.randint(2, 9), rng.randint(1, 20)
        return t5_collect(v, a, c, b) if a + b <= 20 else None
    a, b = rng.randint(2, 5), rng.randint(2, 5)
    c, d = rng.randint(1, 6), rng.randint(1, 6)
    if a * c + b * d > 40:
        return None
    return t5_two_groups(v, a, c, b, d)


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
PICKERS = {1: _pick_t1, 2: _pick_t2, 3: _pick_t3, 4: _pick_t4, 5: _pick_t5}

# How many items of each builder kind per tier (40 each).
KIND_COUNTS = {
    1: [5, 5, 5, 5, 5, 5, 5, 5],
    2: [8, 5, 6, 6, 7, 8],
    3: [7, 5, 6, 6, 6, 5, 5],
    4: [8, 7, 8, 5, 12],
    5: [7, 6, 4, 8, 4, 5, 6],
}

_NUM = re.compile(r"(?<![\^\d])\d+")


def arith_candidates(answer: str) -> list:
    """Near-miss texts: one number of the answer nudged by +-1 or +-2 (never an exponent).
    Coefficients stay >= 2 so the text never shows '1x' or '0x'."""
    out = []
    for d in (1, -1, 2, -2):
        for m in _NUM.finditer(answer):
            n = int(m.group()) + d
            is_coef = m.end() < len(answer) and answer[m.end()].isalpha()
            if n < (2 if is_coef else 0):
                continue
            out.append(answer[:m.start()] + str(n) + answer[m.end():])
    return out


def make_item(built: dict, tier: int, answer_pos: int):
    ans = built["answer"]
    seen = {fingerprint(ans)}
    wrong = []
    for lab, text in built["wrong"]:
        fp = fingerprint(text)
        if fp in seen or len(wrong) == 3:
            continue
        seen.add(fp)
        wrong.append((lab, text))
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


def gen_tier(tier: int, count: int, declared, rng: random.Random, max_attempts: int = 100000):
    counts = KIND_COUNTS[tier]
    kinds = [k for k, n in enumerate(counts) for _ in range(n)]
    kinds = (kinds * (count // len(kinds) + 1))[:count]
    rng.shuffle(kinds)
    positions = [i % 4 for i in range(count)]
    rng.shuffle(positions)
    items, prompts, attempts = [], set(), 0
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
        # wrong labels are shuffled into place, so the misconception order is not a tell
        item = make_item(built, tier, positions[len(items)])
        if item is None:
            continue
        wrong = [(m, c) for m, c in zip(item["misconceptions"], item["choices"]) if m]
        rng.shuffle(wrong)
        ap = item["answer"]
        pairs = wrong[:ap] + [(None, item["choices"][ap])] + wrong[ap:]
        item["choices"] = [c for _, c in pairs]
        item["misconceptions"] = [m for m, _ in pairs]
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
