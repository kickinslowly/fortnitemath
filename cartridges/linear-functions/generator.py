"""Procedural generator for the linear-functions cartridge (fnm-cart/1, grade 8).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every template is a ``s_*`` function: hand-picked numbers in, a ``Spec`` out (prompt, the correct
  choice, every modelled wrong choice with its misconception key, the explanation, and a filler for
  ``ARITH``). The ``b_*`` functions only pick numbers (inside the manifest's ``bounds``) and call them,
  so the golden tests can drive ``s_*`` with hand-worked numbers.
* A choice is ``(display, key)``. The key is the choice's VALUE: ``("n", Fraction)`` for numbers,
  ``("eq", m, b)`` for the line ``y = m x + b`` (so ``y = 7 - 2x`` and ``y = -2x + 7`` are one value),
  ``("set", frozenset(pairs))`` for a set of ordered pairs, ``("nl", kind, b)`` for a non-linear rule and
  ``("txt", s)`` for a word. No two choices of an item share a key: the player never faces two right doors.
* Wrong choices: misconception values first (when more than needed, labels are covered first, then
  random), ``ARITH`` only fills up to the item's choice count and never equals a misconception value.
* Answer positions are balanced per tier and per choice count by always filling the least-used slot.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from fractions import Fraction

MINUS = "−"
ALLOWED_EXTRA = set("×÷−≤≥≠√π")


# ---------------------------------------------------------------------------------------------
# Display / choice constructors
# ---------------------------------------------------------------------------------------------
def fnum(v) -> str:
    v = Fraction(v)
    a = abs(v)
    body = str(a.numerator) if a.denominator == 1 else f"{a.numerator}/{a.denominator}"
    return (MINUS if v < 0 else "") + body


def pp(v) -> str:
    """A number inside an expression: negatives in parentheses."""
    return f"({fnum(v)})" if Fraction(v) < 0 else fnum(v)


def N(v):
    v = Fraction(v)
    return (fnum(v), ("n", v))


def txt(s):
    return (s, ("txt", s))


YES, NO = txt("Yes"), txt("No")


def pt(x, y) -> str:
    return f"({fnum(x)}, {fnum(y)})"


def lst(vs) -> str:
    return ", ".join(fnum(v) for v in vs)


def eq_text(m, b, dep="y", ind="x") -> str:
    """``dep = m ind + b`` in the standard form."""
    m, b = int(m), int(b)
    if m == 0:
        return f"{dep} = {fnum(b)}"
    lead = ind if m == 1 else (MINUS + ind if m == -1 else f"{fnum(m)}{ind}")
    if b == 0:
        return f"{dep} = {lead}"
    return f"{dep} = {lead} {'+' if b > 0 else MINUS} {abs(b)}"


def eq_bfirst(m, b, dep="y", ind="x") -> str:
    """``dep = b + m ind`` (constant first): y = 7 - 2x."""
    m, b = int(m), int(b)
    lead = ind if abs(m) == 1 else f"{abs(m)}{ind}"
    return f"{dep} = {fnum(b)} {'+' if m > 0 else MINUS} {lead}"


def EQ(m, b, dep="y", ind="x"):
    return (eq_text(m, b, dep, ind), ("eq", Fraction(m), Fraction(b)))


def lin_choice(m, b, bfirst=False):
    t = eq_bfirst(m, b) if bfirst and b != 0 else eq_text(m, b)
    return (t, ("eq", Fraction(m), Fraction(b)))


NL_BASE = {"sq": "x^2", "cu": "x^3", "ex": "2^x"}


def nl_text(kind, b) -> str:
    base = NL_BASE[kind]
    if b == 0:
        return f"y = {base}"
    return f"y = {base} {'+' if b > 0 else MINUS} {abs(b)}"


def NL(kind, b):
    return (nl_text(kind, b), ("nl", kind, b))


def pairs_text(ps) -> str:
    return ", ".join(f"({a}, {b})" for a, b in sorted(ps))


def SET(ps):
    ps = frozenset(ps)
    return (pairs_text(ps), ("set", ps))


@dataclass
class Spec:
    prompt: str
    correct: tuple
    wrong: list  # [(label, choice)] in priority order; may repeat values / equal the answer
    expl: str
    arith: object = None  # callable(rng) -> [choice] (candidates for ARITH)
    n: int = 4  # choices per item


def near(v, deltas=(1, -1, 2, -2, 3, -3), lo=None):
    """Candidates for ARITH: v moved by a few; with ``lo`` nothing below it (a rate of 0 is no door)."""
    def f(rng):
        ds = list(deltas)
        rng.shuffle(ds)
        return [N(Fraction(v) + d) for d in ds if lo is None or Fraction(v) + d >= lo]
    return f


def near_eq(m, b):
    def f(rng):
        opts = [(m, b + 1), (m, b - 1), (m + 1, b), (m - 1, b), (m, b + 2), (m, b - 2)]
        rng.shuffle(opts)
        return [EQ(mm, bb) for mm, bb in opts if mm != 0]
    return f


# =============================================================================================
# TIER 1: Is It a Function?
# =============================================================================================
def _dup_input(ps):
    """(input, sorted outputs) of the first input that has two outputs, else None."""
    by = {}
    for a, b in sorted(ps):
        by.setdefault(a, []).append(b)
    for a in sorted(by):
        if len(by[a]) > 1:
            return a, by[a]
    return None


def s_pairs_fn(pairs):
    ps = sorted(set(pairs))
    prompt = f"Pairs {pairs_text(ps)}. Is it a function?"
    dup = _dup_input(ps)
    ys = [b for _, b in ps]
    if dup is None:
        rep = len(set(ys)) < len(ys)
        wrong = [("REPEAT_OUTPUT" if rep else "ARITH", NO)]
        expl = "Each input appears once, so each has one output. A repeated output is fine."
        return Spec(prompt, YES, wrong, expl, None, 2)
    a, outs = dup
    label = "INPUT_OUTPUT_SWAP" if len(set(ys)) == len(ys) else "REPEAT_INPUT_OK"
    expl = f"Input {a} has two outputs, {outs[0]} and {outs[1]}, so it is not a function."
    return Spec(prompt, NO, [(label, YES)], expl, None, 2)


def b1_pairs(rng):
    k = rng.choice((3, 4))
    if rng.random() < 0.5:  # a function with a repeated output
        xs = sorted(rng.sample(range(0, 10), k))
        ys = [rng.randint(1, 9) for _ in xs]
        if len(set(ys)) == k:
            return None
        return s_pairs_fn(list(zip(xs, ys)))
    xs = sorted(rng.sample(range(0, 10), k - 1))
    ys = [rng.randint(1, 9) for _ in xs]
    j = rng.randrange(len(xs))
    y2 = rng.randint(1, 9)
    if y2 == ys[j]:
        return None
    return s_pairs_fn(list(zip(xs, ys)) + [(xs[j], y2)])


NOT_PHRASES = ["Which set is NOT a function?", "Which pairs are NOT a function?",
               "Which of these is NOT a function?", "Pick the set that is NOT a function."]
IS_PHRASES = ["Which set IS a function?", "Which set of pairs is a function?",
              "Which of these is a function?", "Pick the set that is a function."]


def s_which_fn(mode, phrase, correct_ps, wrong_sets):
    """mode 'not': correct is NOT a function, wrong_sets are [(label, pairs)] functions.
    mode 'is': correct IS a function, wrong_sets are [(label, pairs)] non-functions."""
    correct = SET(correct_ps)
    wrong = [(lab, SET(ps)) for lab, ps in wrong_sets]
    if mode == "not":
        a, outs = _dup_input(sorted(correct_ps))
        expl = f"Input {a} has two outputs, {outs[0]} and {outs[1]}. A function gives one output per input."
    else:
        expl = f"Each input in {correct[0]} has one output. A repeated output is fine."

    def arith(rng):
        out = []
        for _ in range(12):
            a1, a2 = rng.sample(range(0, 10), 2)
            b1, b2 = rng.sample(range(1, 10), 2)
            out.append(SET([(a1, b1), (a2, b2)]))
        return out
    return Spec(phrase, correct, wrong, expl, arith if mode == "not" else None, 4)


def _rep_set(rng):
    a1, a2 = rng.sample(range(0, 10), 2)
    b = rng.randint(1, 9)
    return [(a1, b), (a2, b)]


def _plain_set(rng):
    a1, a2 = rng.sample(range(0, 10), 2)
    b1, b2 = rng.sample(range(1, 10), 2)
    return [(a1, b1), (a2, b2)]


def _nonfn_set(rng):
    a = rng.randint(0, 9)
    b1, b2 = rng.sample(range(1, 10), 2)
    return [(a, b1), (a, b2)]


def b1_which_not(rng):
    return s_which_fn("not", rng.choice(NOT_PHRASES), _nonfn_set(rng),
                      [("REPEAT_OUTPUT", _rep_set(rng)), ("REPEAT_OUTPUT", _rep_set(rng))])


def b1_which_is(rng):
    correct = _rep_set(rng) if rng.random() < 0.5 else _plain_set(rng)
    wrong = [("REPEAT_INPUT_OK", _nonfn_set(rng)), ("REPEAT_INPUT_OK", _nonfn_set(rng)),
             ("INPUT_OUTPUT_SWAP", _nonfn_set(rng))]
    return s_which_fn("is", rng.choice(IS_PHRASES), correct, wrong)


def s_eval(m, b, x, phrase_variant=0):
    out = m * x + b
    eq = eq_text(m, b)
    prompt = f"{eq}. Input {x}. Output?" if phrase_variant == 0 else f"{eq}. If x = {x}, what is y?"
    wrong = [("PLUGGED_WRONG", N(m * (x + b))), ("ADDED_PARTS", N(m + x + b))]
    if (x - b) % m == 0:
        wrong.append(("INPUT_OUTPUT_SWAP", N(Fraction(x - b, m))))
    sign = "+" if b > 0 else MINUS
    expl = f"{m} × {x} {sign} {abs(b)} = {out}."
    return Spec(prompt, N(out), wrong, expl, near(out, (1, -1, 2, -2, 3), 1))


def b1_eval(rng):
    m, x = rng.randint(2, 5), rng.randint(1, 6)
    b = rng.choice([v for v in range(-6, 10) if v != 0])
    if not 1 <= m * x + b <= 20:
        return None
    return s_eval(m, b, x, rng.randint(0, 1))


def s_rule(m, b, x, mult_first):
    """Rule words: multiply by m, then add b (b may be negative: subtract)."""
    word = "add" if b > 0 else "subtract"
    ab = abs(b)
    if mult_first:
        prompt = f"Rule: multiply by {m}, then {word} {ab}. Input {x}. Output?"
        out = m * x + b
        other = m * (x + b)
        partial = m * x
        expl = f"{x} × {m} = {m * x}, then {m * x} {'+' if b > 0 else MINUS} {ab} = {out}."
    else:
        prompt = f"Rule: {word} {ab}, then multiply by {m}. Input {x}. Output?"
        out = (x + b) * m
        other = m * x + b
        partial = x + b
        expl = f"{x} {'+' if b > 0 else MINUS} {ab} = {x + b}, then {x + b} × {m} = {out}."
    wrong = [("PLUGGED_WRONG", N(other)), ("ADDED_PARTS", N(m + x + b)), ("STOPPED_EARLY", N(partial))]
    return Spec(prompt, N(out), wrong, expl, near(out, (1, -1, 2, -2), 1))


def b1_rule(rng):
    m, x = rng.randint(2, 5), rng.randint(1, 5)
    b = rng.choice([v for v in range(-4, 10) if v != 0])
    mult_first = rng.random() < 0.65
    if not mult_first and x + b < 1:
        return None
    out = m * x + b if mult_first else (x + b) * m
    if not 1 <= out <= 20:
        return None
    return s_rule(m, b, x, mult_first)


# (input phrase, output phrase, reason) -- outputs repeat naturally
FN_YES = [
    ("a person", "their birth month", "Each person has one birth month."),
    ("a student", "their grade level", "Each student is in one grade."),
    ("a book", "its page count", "Each book has one page count."),
    ("a city", "its state", "Each city is in one state."),
    ("a snack", "its price", "Each snack has one price."),
    ("a student", "their math teacher", "Each student has one math teacher."),
]
FN_NO = [
    ("a state", "a city in it", "A state has many cities."),
    ("a person", "a parent of theirs", "A person has two parents."),
    ("a student", "a class they take", "A student takes many classes."),
    ("a team", "a player on it", "A team has many players."),
    ("a store", "an item it sells", "A store sells many items."),
    ("a movie", "an actor in it", "A movie has many actors."),
    ("a number", "a number bigger than it", "Many numbers are bigger."),
]


def s_words_fn(inp, out, reason, is_fn):
    prompt = f"Input: {inp}. Output: {out}. Function?"
    if is_fn:
        return Spec(prompt, YES, [("REPEAT_OUTPUT", NO)], reason + " Outputs may repeat.", None, 2)
    return Spec(prompt, NO, [("REPEAT_INPUT_OK", YES)], reason + " One input, many outputs.", None, 2)


def b1_words(rng):
    if rng.random() < 0.5:
        inp, out, why = rng.choice(FN_YES)
        return s_words_fn(inp, out, why, True)
    inp, out, why = rng.choice(FN_NO)
    return s_words_fn(inp, out, why, False)


NONE = txt("None")


def s_dup_input(pairs):
    """Which input has two outputs? The inputs are the doors, plus `None` for a function."""
    ps = sorted(set(pairs))
    prompt = f"Which input has two outputs: {pairs_text(ps)}?"
    dup = _dup_input(ps)
    ins = sorted({a for a, _ in ps})
    outs = {}
    for a, b in ps:
        outs.setdefault(b, set()).add(a)
    shares = {a for s in outs.values() if len(s) > 1 for a in s}  # inputs that share an output with another
    if dup is None:
        correct = NONE
        wrong = [("REPEAT_OUTPUT" if a in shares else "ARITH", N(a)) for a in ins]
        n = min(4, len(ins) + 1)
        expl = "Every input appears once, so each has one output. None has two."
    else:
        a0, o = dup
        correct = N(a0)
        wrong = [("REPEAT_OUTPUT" if a in shares else "ARITH", N(a)) for a in ins if a != a0]
        wrong.append(("REPEAT_INPUT_OK", NONE))
        n = min(4, len(ins) + 1)
        expl = f"Input {a0} goes to {o[0]} and {o[1]}: two outputs."
    return Spec(prompt, correct, wrong, expl, None, n)


def b1_dup_input(rng):
    """A repeated input is the answer; at least one other input shares an output (a real trap)."""
    xs = sorted(rng.sample(range(0, 10), 3))
    ys = [rng.randint(1, 9) for _ in xs]
    j = rng.randrange(3)
    y2 = rng.randint(1, 9)
    if y2 == ys[j]:
        return None
    pairs = list(zip(xs, ys)) + [(xs[j], y2)]
    shared = {a for a, b in pairs for c, d in pairs if a != c and b == d}
    if not any(a in shared for a in xs if a != xs[j]):
        return None
    return s_dup_input(pairs)


def b1_dup_none(rng):
    """A function: `None` is right, and every input shares an output with another (two repeated outputs)."""
    xs = rng.sample(range(0, 10), 4)
    u, v = rng.sample(range(1, 10), 2)
    return s_dup_input(sorted(zip(xs, [u, u, v, v])))


# =============================================================================================
# TIER 2: Slope & Rate of Change
# =============================================================================================
def s_points(x1, y1, x2, y2):
    rise, run = y2 - y1, x2 - x1
    slope = Fraction(rise, run)
    prompt = f"Slope through {pt(x1, y1)} and {pt(x2, y2)}?"
    wrong = [("RUN_OVER_RISE", N(Fraction(run, rise))), ("SIGN_SLIP", N(-slope)), ("RISE_ONLY", N(rise))]
    expl = f"Rise {pp(y2)} − {pp(y1)} = {fnum(rise)}, run {pp(x2)} − {pp(x1)} = {fnum(run)}. {fnum(rise)} ÷ {fnum(run)} = {fnum(slope)}."
    if slope.denominator == 1:
        arith = near(slope, (1, -1, 2, -2))
    else:
        def arith(rng):
            a, b = slope.numerator, slope.denominator
            opts = [Fraction(a + 1, b), Fraction(a - 1, b), Fraction(a, b + 1), Fraction(a, b + 2)]
            rng.shuffle(opts)
            return [N(o) for o in opts if o != 0]
    return Spec(prompt, N(slope), wrong, expl, arith)


def b2_points(rng):
    if rng.random() < 0.5:
        slope = Fraction(rng.choice((2, 3, 4, 5)) * rng.choice((1, -1)))
    else:
        a, b = rng.randint(1, 5), rng.randint(2, 5)
        if math.gcd(a, b) != 1:
            return None
        slope = Fraction(a * rng.choice((1, -1)), b)
    den = slope.denominator
    g = rng.randint(1, 5)
    run_abs = den * g
    if run_abs < 2 or run_abs > 10 or abs(slope.numerator) * g > 10:
        return None
    run = run_abs * (1 if rng.random() < 0.7 else -1)
    rise = int(slope * run)
    if rng.random() < 0.15:
        x1, y1 = 0, 0
    else:
        x1, y1 = rng.randint(-5, 5), rng.randint(-5, 5)
    x2, y2 = x1 + run, y1 + rise
    if max(abs(x2), abs(y2)) > 10:
        return None
    return s_points(x1, y1, x2, y2)


def s_table_rate(xs, ys):
    s = xs[1] - xs[0]
    d = ys[1] - ys[0]
    r = Fraction(d, s)
    prompt = f"x: {lst(xs)}. y: {lst(ys)}. Rate of change?"
    wrong = [("START_AS_RATE", N(ys[0])), ("TOTAL_CHANGE", N(ys[2] - ys[0])), ("SIGN_SLIP", N(-r))]
    if s != 1:
        wrong.append(("RISE_ONLY", N(d)))
    expl = f"From x = {xs[0]} to {xs[1]}, y goes {ys[0]} to {ys[1]}: {fnum(d)} ÷ {s} = {fnum(r)} per 1."
    return Spec(prompt, N(r), wrong, expl, near(r, (1, -1, 2, -2)))


def b2_table(rng):
    r = rng.choice([-5, -4, -3, -2, 2, 3, 4, 5])
    s = rng.choice((1, 1, 1, 2))
    x0 = rng.choice((0, 0, 1, 2, 3))
    xs = [x0, x0 + s, x0 + 2 * s]
    y0 = rng.randint(1, 20)
    ys = [y0 + r * s * i for i in range(3)]
    if min(ys) < 0 or max(ys) > 20:
        return None
    return s_table_rate(xs, ys)


UP_CTX = [("A plant", "is", "in", "week"), ("A tank", "has", "gal", "min"),
          ("A pup", "is", "lb", "month"), ("A tree", "is", "ft", "year")]
DOWN_CTX = [("A candle", "is", "in", "hour"), ("A pool", "has", "gal", "min"),
            ("A snowman", "is", "in", "hour"), ("A puddle", "is", "cm", "hour")]


def s_words_rate(subject, verb, unit, tu, t0, t1, v0, v1):
    run, d = t1 - t0, v1 - v0
    r = Fraction(d, run)
    prompt = f"{subject}: {v0} {unit} at {tu} {t0}, {v1} at {tu} {t1}. Change per {tu}?"
    wrong = [("RISE_ONLY", N(d)), ("RUN_OVER_RISE", N(Fraction(run, d))), ("SIGN_SLIP", N(-r)),
             ("START_AS_RATE", N(v0))]
    expl = f"y goes {v0} to {v1} in {run} {tu}s: {fnum(d)} ÷ {run} = {fnum(r)} per {tu}."
    return Spec(prompt, N(r), wrong, expl, near(r, (1, -1, 2, -2)))


def b2_words(rng):
    r = rng.choice([-5, -4, -3, -2, 2, 3, 4, 5])
    subject, verb, unit, tu = rng.choice(UP_CTX if r > 0 else DOWN_CTX)
    run = rng.randint(2, 4)
    t0 = rng.randint(0, 3)
    v0 = rng.randint(1, 20)
    v1 = v0 + r * run
    if not (1 <= v1 <= 20):
        return None
    return s_words_rate(subject, verb, unit, tu, t0, t0 + run, v0, v1)


RAMP_THINGS = [("A ramp", "ft"), ("A roof", "ft"), ("A slide", "ft"), ("A hill", "m"), ("A trail", "m"),
               ("Stairs", "in")]


def s_ramp(thing, unit, rise, run):
    slope = Fraction(rise, run)
    verb = "rise" if thing == "Stairs" else "rises"
    prompt = f"{thing} {verb} {rise} {unit} over a run of {run} {unit}. Slope?"
    wrong = [("RUN_OVER_RISE", N(Fraction(run, rise))), ("ADDED_RISE_RUN", N(rise + run)),
             ("RISE_ONLY", N(rise))]
    expl = f"Slope = rise ÷ run = {rise} ÷ {run} = {fnum(slope)}."
    return Spec(prompt, N(slope), wrong, expl, near(slope, (1, -1, 2)))


def b2_ramp(rng):
    thing, unit = rng.choice(RAMP_THINGS)
    run = rng.randint(2, 10)
    rise = rng.randint(1, 10)
    sl = Fraction(rise, run)
    if sl == 1:
        return None
    if sl.denominator == 1:
        if not 2 <= sl <= 10:
            return None
    elif sl.numerator > 5 or sl.denominator > 5:
        return None
    return s_ramp(thing, unit, rise, run)


# =============================================================================================
# TIER 3: Start Value & y = mx + b
# =============================================================================================
def _eq_form(m, b, bfirst):
    return eq_bfirst(m, b) if bfirst else eq_text(m, b)


INIT_Q = ["Initial value?", "Starting value?", "Value of y when x = 0?"]


def s_initial(m, b, bfirst, q):
    eq = _eq_form(m, b, bfirst)
    prompt = f"{eq}. {q}"
    wrong = [("SLOPE_AS_START", N(m)), ("SLOPE_AS_START", N(abs(m))), ("VALUE_AT_1", N(m + b))]
    if b < 0:
        wrong.append(("SIGN_DROPPED", N(abs(b))))
    expl = f"At x = 0, y = {fnum(b)}. The start is the lone number, {fnum(b)}."
    return Spec(prompt, N(b), wrong, expl, near(b, (1, -1, 2, -2)))


def b3_initial(rng):
    m = rng.choice([v for v in range(-9, 10) if v != 0])
    b = rng.choice([v for v in range(-9, 10) if v != 0])
    return s_initial(m, b, rng.random() < 0.4, rng.choice(INIT_Q))


SLOPE_Q = ["Slope of", "Rate of change of"]


def s_slope(m, b, bfirst, q):
    eq = _eq_form(m, b, bfirst)
    prompt = f"{q} {eq}?"
    wrong = [("START_AS_SLOPE", N(b)), ("START_AS_SLOPE", N(abs(b)))]
    if m < 0:
        wrong.append(("SIGN_DROPPED", N(abs(m))))
    expl = f"The number multiplying x is the slope: {fnum(m)}."
    return Spec(prompt, N(m), wrong, expl, near(m, (1, -1, 2, -2)))


def b3_slope(rng):
    m = rng.choice([v for v in range(-9, 10) if v != 0])
    b = rng.choice([v for v in range(-9, 10) if v != 0])
    return s_slope(m, b, rng.random() < 0.4, rng.choice(SLOPE_Q))


# (template, sign of the slope)
WORD_EQ_CTX = [
    ("A jar has ${b}. Add ${m} a week. Total y after x weeks?", 1),
    ("A gym costs ${b} to join, ${m} a month. Cost y for x months?", 1),
    ("A taxi charges ${b} plus ${m} a mile. Cost y for x miles?", 1),
    ("Tank: {b} gal, gains {m} gal a min. Gallons y after x min?", 1),
    ("A plant is {b} in, grows {m} in a week. Height y after x weeks?", 1),
    ("Tank: {b} gal, loses {m} gal a min. Gallons y after x min?", -1),
    ("A {b} in candle burns {m} in an hour. Height y after x hours?", -1),
    ("You have ${b}. Spend ${m} a day. Money y after x days?", -1),
]


def s_word_eq(template, sign, b, m):
    prompt = template.format(b=b, m=m)
    sm = sign * m
    correct = EQ(sm, b)
    wrong = [("SWAPPED_MB", EQ(sign * b, m)), ("NO_START", EQ(sm, 0))]
    if sign < 0:
        wrong.append(("SIGN_DROPPED", EQ(m, b)))
    expl = f"Start {b} is the added number; {m} per x is the slope{' (going down, so negative)' if sign < 0 else ''}."
    return Spec(prompt, correct, wrong, expl, near_eq(sm, b))


def b3_word_eq(rng):
    template, sign = rng.choice(WORD_EQ_CTX)
    b, m = rng.randint(2, 10), rng.randint(2, 9)
    if b == m:
        return None
    return s_word_eq(template, sign, b, m)


def s_slope_init(m, b):
    prompt = f"Slope {fnum(m)}, initial value {fnum(b)}. Equation?"
    wrong = [("SWAPPED_MB", EQ(b, m)), ("NO_START", EQ(m, 0))]
    if b < 0:
        wrong.append(("SIGN_DROPPED", EQ(m, abs(b))))
    if m < 0:
        wrong.append(("SIGN_DROPPED", EQ(abs(m), b)))
    expl = f"y = mx + b with m = {fnum(m)} and b = {fnum(b)}: {eq_text(m, b)}."
    return Spec(prompt, EQ(m, b), wrong, expl, near_eq(m, b))


def b3_slope_init(rng):
    m = rng.choice([v for v in range(-9, 10) if v != 0])
    b = rng.choice([v for v in range(-9, 10) if v != 0])
    return s_slope_init(m, b)


def s_table_eq(x0, m, b):
    xs = [x0, x0 + 1, x0 + 2]
    ys = [m * x + b for x in xs]
    prompt = f"x: {lst(xs)}. y: {lst(ys)}. Equation?"
    wrong = [("SWAPPED_MB", EQ(b, m)), ("VALUE_AT_1", EQ(m, m + b)), ("LAST_VALUE", EQ(m, ys[2]))]
    if m < 0:
        wrong.append(("SIGN_DROPPED", EQ(abs(m), b)))
    if b < 0:
        wrong.append(("SIGN_DROPPED", EQ(m, abs(b))))
    if x0 == 0:
        expl = f"y at x = 0 is {fnum(b)}, the start. Each step adds {fnum(m)}: {eq_text(m, b)}."
    else:
        expl = f"Each step adds {fnum(m)}. Back up to x = 0: y = {fnum(b)}. {eq_text(m, b)}."
    return Spec(prompt, EQ(m, b), wrong, expl, near_eq(m, b))


def b3_table_eq(rng):
    x0 = rng.choice((0, 0, 1))
    m = rng.choice([-5, -4, -3, -2, 2, 3, 4, 5])
    b = rng.choice([v for v in range(-6, 10) if v != 0])
    ys = [m * (x0 + i) + b for i in range(3)]
    if max(abs(y) for y in ys) > 20:
        return None
    return s_table_eq(x0, m, b)


# =============================================================================================
# TIER 4: Proportional & Compare
# =============================================================================================
SAME = txt("Same")


def s_cmp(prompt, correct, wrong_label, expl):
    """Two lines and a `Same` door; exactly one is right. wrong_label belongs to the other letter."""
    other = "B" if correct == "A" else "A"
    return Spec(prompt, txt(correct), [(wrong_label, txt(other)), ("SAME_NOT_CHECKED", SAME)], expl, None, 3)


def s_cmp_same(prompt, label_a, label_b, expl):
    """The rates are equal: `Same` is right, each letter is a wrong door."""
    return Spec(prompt, SAME, [(label_a, txt("A")), (label_b, txt("B"))], expl, None, 3)


CMP_CTX = [  # (dependent, independent, things, units, unit singular)
    ("d", "t", "miles", "hours", "hour"), ("p", "m", "pages", "minutes", "minute"),
    ("w", "m", "words", "minutes", "minute"), ("c", "h", "cans", "hours", "hour"),
    ("g", "m", "gallons", "minutes", "minute"),
]


def s_cmp_words(ctx, k, tot, h, eq_is_a):
    dep, ind, things, units, unit = ctx
    r = Fraction(tot, h)
    eq_part = f"{dep} = {k}{ind}"
    wd_part = f"{tot} {things} in {h} {units}"
    a_text, b_text = (eq_part, wd_part) if eq_is_a else (wd_part, eq_part)
    prompt = f"A: {a_text}. B: {b_text}. Which is faster?"
    eq_letter, wd_letter = ("A", "B") if eq_is_a else ("B", "A")
    if k == r:
        expl = f"Both go {k} per {unit} ({tot} ÷ {h} = {k}). Same."
        return s_cmp_same(prompt, "RATE_NOT_COMPARED", "RATE_NOT_COMPARED", expl)
    if k > r:
        correct, label = eq_letter, "BIGGER_TOTAL"
    else:
        correct, label = wd_letter, "INVERTED_RATE"
    expl = f"{eq_letter} goes {k} per {unit}. {wd_letter}: {tot} ÷ {h} = {fnum(r)} per {unit}. {correct} is faster."
    return s_cmp(prompt, correct, label, expl)


def b4_cmp_words(rng):
    ctx = rng.choice(CMP_CTX)
    h = rng.randint(2, 5)
    k = rng.randint(2, 9)
    same = rng.random() < 0.2
    r = k if same else rng.randint(2, 9)
    if not same and k == r:
        return None
    tot = r * h
    if k > r and tot <= k:
        return None
    return s_cmp_words(ctx, k, tot, h, rng.random() < 0.5)


def s_cmp_point(k, x, y, eq_is_a):
    r = Fraction(y, x)
    eq_part = f"y = {k}x"
    pt_part = f"line through (0, 0) and ({x}, {y})"
    a_text, b_text = (eq_part, pt_part) if eq_is_a else (pt_part, eq_part)
    prompt = f"A: {a_text}. B: {b_text}. Steeper?"
    eq_letter, pt_letter = ("A", "B") if eq_is_a else ("B", "A")
    if k == r:
        expl = f"Both have slope {k} ({y} ÷ {x} = {k}). Same."
        return s_cmp_same(prompt, "RATE_NOT_COMPARED", "RATE_NOT_COMPARED", expl)
    if k > r:
        correct, label = eq_letter, "BIGGER_TOTAL"
    else:
        correct, label = pt_letter, "INVERTED_RATE"
    expl = f"{eq_letter} has slope {k}. {pt_letter}: {y} ÷ {x} = {fnum(r)}. {correct} is steeper."
    return s_cmp(prompt, correct, label, expl)


def b4_cmp_point(rng):
    x = rng.randint(2, 5)
    r = rng.randint(2, 5)
    y = r * x
    if y > 10:
        return None
    same = rng.random() < 0.2
    k = r if same else rng.randint(2, 9)
    if not same and (k == r or (k > r and y <= k)):
        return None
    return s_cmp_point(k, x, y, rng.random() < 0.5)


def s_cmp_eq(fast, slow, fast_is_a):
    (pf, qf), (ps, qs) = fast, slow
    ft, st = eq_text(pf, qf), eq_text(ps, qs)
    a_text, b_text = (ft, st) if fast_is_a else (st, ft)
    prompt = f"A: {a_text}. B: {b_text}. Which grows faster?"
    correct = "A" if fast_is_a else "B"
    expl = f"Growth speed is the slope: {pf} beats {ps}. The bigger start ({qs}) does not matter."
    return s_cmp(prompt, correct, "START_NOT_RATE", expl)


def s_cmp_eq_same(a, b):
    """Equal slopes, different starts."""
    (m, qa), (_, qb) = a, b
    prompt = f"A: {eq_text(m, qa)}. B: {eq_text(m, qb)}. Which grows faster?"
    big = "A" if qa > qb else "B"
    la, lb = ("START_NOT_RATE", "RATE_NOT_COMPARED") if big == "A" else ("RATE_NOT_COMPARED", "START_NOT_RATE")
    expl = f"Both have slope {m}, so they grow equally fast. Only the starts differ. Same."
    return s_cmp_same(prompt, la, lb, expl)


def b4_cmp_eq(rng):
    if rng.random() < 0.2:
        m = rng.randint(2, 9)
        qa, qb = rng.sample(range(0, 10), 2)
        return s_cmp_eq_same((m, qa), (m, qb))
    pf = rng.randint(3, 9)
    ps = rng.randint(2, pf - 1)
    qf = rng.randint(0, 4)
    qs = rng.randint(qf + 2, 9)
    return s_cmp_eq((pf, qf), (ps, qs), rng.random() < 0.5)


UNIT_PHRASES = ["A line through (0, 0) and ({x}, {y}). Unit rate?",
                "y = kx, and ({x}, {y}) is on it. Unit rate?"]


def s_unit_rate(x, y, variant):
    k = Fraction(y, x)
    prompt = UNIT_PHRASES[variant].format(x=x, y=y)
    wrong = [("INVERTED_RATE", N(Fraction(x, y))), ("DIFFERENCE", N(y - x)), ("TOTAL_AS_RATE", N(y))]
    expl = f"Unit rate = y ÷ x = {y} ÷ {x} = {fnum(k)}."
    return Spec(prompt, N(k), wrong, expl, near(k, (1, -1, 2, -2), 1))


def b4_unit_rate(rng):
    x, k = rng.randint(2, 5), rng.randint(2, 5)
    if x * k > 10:
        return None
    return s_unit_rate(x, x * k, rng.randint(0, 1))


def s_which_prop(k, hs_k, hs_c, add_c, order):
    """Three equations in the prompt: y = kx (right), y = hs_k x + hs_c (has a start), y = x + add_c."""
    ch = {"c": EQ(k, 0), "h": EQ(hs_k, hs_c), "a": EQ(1, add_c)}
    texts = ", ".join(ch[o][0] for o in order)
    prompt = f"Which is proportional: {texts}?"
    wrong = [("HAS_START", ch["h"]), ("ADDS_NOT_MULTIPLIES", ch["a"])]
    expl = f"Proportional means y = kx with no added number: y = {k}x."
    return Spec(prompt, ch["c"], wrong, expl, None, 3)


def b4_which_prop(rng):
    hs_c = rng.choice([v for v in range(-9, 10) if v != 0])
    return s_which_prop(rng.randint(2, 9), rng.randint(2, 9), hs_c, rng.randint(2, 9), rng.sample("cha", 3))


def s_table_prop(xs, ys):
    prompt = f"x: {lst(xs)}. y: {lst(ys)}. Proportional?"
    if 0 in xs:  # a row with x = 0 must have y = 0 in a proportional table (this builder never makes one)
        assert ys[xs.index(0)] != 0
        expl = f"At x = 0, y is {ys[xs.index(0)]}, not 0. A proportional line passes through (0, 0)."
        return Spec(prompt, NO, [("STEADY_MEANS_PROP", YES)], expl, None, 2)
    ratios = {Fraction(y, x) for x, y in zip(xs, ys)}
    if len(ratios) == 1:
        k = next(iter(ratios))
        expl = f"y ÷ x is {fnum(k)} in every row, so it is proportional."
        return Spec(prompt, YES, [("NEEDS_ZERO_ROW", NO)], expl, None, 2)
    rs = ", ".join(fnum(Fraction(y, x)) for x, y in zip(xs, ys))
    expl = f"y ÷ x is {rs}: not the same, so it is not proportional."
    return Spec(prompt, NO, [("STEADY_MEANS_PROP", YES)], expl, None, 2)


XS_TABLES = [(1, 2, 3), (2, 3, 4), (2, 4, 6), (1, 3, 5), (3, 4, 5), (1, 2, 4), (2, 3, 5)]


def b4_table_prop(rng):
    xs = list(rng.choice(XS_TABLES))
    if rng.random() < 0.5:
        k = rng.randint(2, 6)
        ys = [k * x for x in xs]
    else:
        k = rng.randint(1, 5)
        c = rng.choice([-3, -2, -1, 1, 2, 3, 4, 5])
        ys = [k * x + c for x in xs]
        if rng.random() < 0.3:  # a table that starts at x = 0
            xs = [0, 1, 2]
            ys = [k * x + c for x in xs]
    if min(ys) < 1 or max(ys) > 20:
        return None
    return s_table_prop(xs, ys)


# =============================================================================================
# TIER 5: Linear or Not?
# =============================================================================================
def s_which_lin(mode, lin_items, nl_items, order):
    """Three rules listed in the prompt. mode 'not': correct is nl_items[0], the wrongs are lin_items[:2]
    (m, b, bfirst). mode 'is': correct is lin_items[0], the wrongs are nl_items[:2] (kind, b).
    order: a permutation of (0, 1, 2) = (correct, wrong 1, wrong 2) for the listing in the prompt."""
    if mode == "not":
        kind, b = nl_items[0]
        correct = NL(kind, b)
        wrong = []
        for m, bb, bf in lin_items[:2]:
            ch = lin_choice(m, bb, bf)
            wrong.append(("MINUS_NOT_LINEAR" if MINUS in ch[0] else "CONSTANT_NOT_LINEAR", ch))
        expl = f"{correct[0]} has a power of x, so its graph curves. The others are lines."
        stem = "Which is NOT linear: "
    else:
        m, bb, bf = lin_items[0]
        correct = lin_choice(m, bb, bf)
        wrong = [("EXPONENT_IGNORED", NL(k, b)) for k, b in nl_items[:2]]
        expl = f"{correct[0]} is y = mx + b: a line. The others have x squared, cubed or as an exponent."
        stem = "Which is linear: "
    pool = [correct, wrong[0][1], wrong[1][1]]
    prompt = stem + ", ".join(pool[i][0] for i in order) + "?"
    return Spec(prompt, correct, wrong, expl, None, 3)


def _rand_lin(rng):
    m = rng.choice([-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6])
    b = rng.choice([v for v in range(-8, 9) if v != 0])
    return (m, b, rng.random() < 0.35)


def _rand_nl(rng):
    return (rng.choice(("sq", "sq", "cu", "ex")), rng.choice([0, 0, 1, 2, 3, 4, 5, -1, -2, -3]))


def b5_which_not(rng):
    return s_which_lin("not", [_rand_lin(rng) for _ in range(2)], [_rand_nl(rng)], rng.sample(range(3), 3))


def b5_which_is(rng):
    return s_which_lin("is", [_rand_lin(rng)], [_rand_nl(rng) for _ in range(2)], rng.sample(range(3), 3))


def s_eq_linear(rule, is_lin, has_minus):
    """rule: the equation text; has_minus/is_lin pick the misconception label."""
    prompt = f"Is {rule} linear?"
    if is_lin:
        label = "MINUS_NOT_LINEAR" if has_minus else "CONSTANT_NOT_LINEAR"
        expl = f"{rule} fits y = mx + b: x only to the first power, so it is a line."
        return Spec(prompt, YES, [(label, NO)], expl, None, 2)
    expl = f"{rule} has x raised to a power (or as an exponent), so its graph curves."
    return Spec(prompt, NO, [("EXPONENT_IGNORED", YES)], expl, None, 2)


def b5_eq_linear(rng):
    if rng.random() < 0.5:
        m, b, bf = _rand_lin(rng)
        text = _eq_form(m, b, bf)
        return s_eq_linear(text, True, MINUS in text)
    kind, b = _rand_nl(rng)
    return s_eq_linear(nl_text(kind, b), False, False)


INC, DEC, STAY = txt("Increases"), txt("Decreases"), txt("Stays same")


def s_direction(m, b, bfirst):
    eq = "y = " + fnum(b) if m == 0 else _eq_form(m, b, bfirst)
    prompt = f"{eq}. As x grows, y?"
    if m > 0:
        correct = INC
        other = ("CONSTANT_SIGN_DECIDES" if b < 0 else "SLOPE_SIGN_IGNORED", DEC)
        expl = f"The slope {m} is positive, so y goes up as x goes up."
    elif m < 0:
        correct = DEC
        other = ("CONSTANT_SIGN_DECIDES" if b > 0 else "SLOPE_SIGN_IGNORED", INC)
        expl = f"The slope {fnum(m)} is negative, so y goes down as x goes up."
    else:
        correct = STAY
        wrong = [("SLOPE_SIGN_IGNORED", INC), ("SLOPE_SIGN_IGNORED", DEC)]
        return Spec(prompt, correct, wrong, f"No x in the rule: the slope is 0, so y stays {fnum(b)}.", None, 3)
    wrong = [other, ("CONSTANT_RATE_MEANS_SAME", STAY)]
    return Spec(prompt, correct, wrong, expl, None, 3)


def b5_direction(rng):
    if rng.random() < 0.12:
        return s_direction(0, rng.randint(1, 9), False)
    m = rng.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5])
    b = rng.choice([v for v in range(-9, 10) if v != 0])
    return s_direction(m, b, rng.random() < 0.35)


def _collinear(xs, ys):
    return Fraction(ys[1] - ys[0], xs[1] - xs[0]) == Fraction(ys[2] - ys[1], xs[2] - xs[1])


def s_table_linear(xs, ys):
    prompt = f"x: {lst(xs)}. y: {lst(ys)}. Linear?"
    lin = _collinear(xs, ys)
    if lin:
        rate = Fraction(ys[1] - ys[0], xs[1] - xs[0])
        even = (xs[1] - xs[0]) == (xs[2] - xs[1])
        label = "DECREASING_NOT_LINEAR" if (even and rate < 0) else "EQUAL_STEPS_MISSED"
        expl = f"y changes {fnum(rate)} per 1 of x every time: a steady rate, so it is linear."
        return Spec(prompt, YES, [(label, NO)], expl, None, 2)
    r1 = Fraction(ys[1] - ys[0], xs[1] - xs[0])
    r2 = Fraction(ys[2] - ys[1], xs[2] - xs[1])
    expl = f"The rate changes ({fnum(r1)}, then {fnum(r2)}) instead of staying steady, so it is not linear."
    return Spec(prompt, NO, [("LOOKS_GROWING", YES)], expl, None, 2)


XS_EVEN = [(1, 2, 3), (0, 1, 2), (2, 4, 6), (1, 3, 5), (2, 3, 4)]
XS_UNEVEN = [(1, 2, 4), (0, 1, 3), (1, 3, 4), (2, 3, 5), (0, 2, 3), (1, 2, 5)]


def _b5_table(rng, kind):
    if kind in (0, 1):  # linear: kind 0 uneven x steps, kind 1 steady decrease
        xs = list(rng.choice(XS_UNEVEN if kind == 0 else XS_EVEN))
        m = rng.randint(1, 4) * (1 if kind == 0 else -1)
        b = rng.randint(-2, 18)
        ys = [m * x + b for x in xs]
    elif kind == 2:  # not linear, even x steps, going up with growing steps
        xs = list(rng.choice(XS_EVEN))
        d1, d2 = rng.randint(1, 4), rng.randint(2, 7)
        if d1 == d2:
            return None
        y0 = rng.randint(0, 6)
        ys = [y0, y0 + d1, y0 + d1 + d2]
    else:  # not linear, uneven x steps, going up
        xs = list(rng.choice(XS_UNEVEN))
        y0 = rng.randint(0, 6)
        ys = [y0, y0 + rng.randint(1, 6), 0]
        ys[2] = ys[1] + rng.randint(1, 8)
    if min(ys) < 0 or max(ys) > 20 or len(set(ys)) < 3:
        return None
    if kind in (2, 3) and _collinear(xs, ys):
        return None
    return s_table_linear(xs, ys)


def b5_table_uneven(rng):  # linear, uneven x gaps
    return _b5_table(rng, 0)


def b5_table_down(rng):  # linear, steadily decreasing
    return _b5_table(rng, 1)


def b5_table_curve(rng):  # not linear, even x gaps
    return _b5_table(rng, 2)


def b5_table_curve_uneven(rng):  # not linear, uneven x gaps
    return _b5_table(rng, 3)


def s_cmp_fn(eq, table, eq_is_a, correct_letter, label):
    (pm, pb), (xs, ys) = eq, table
    eq_t = eq_text(pm, pb)
    tb_t = f"x: {lst(xs)}; y: {lst(ys)}"
    a_t, b_t = (eq_t, tb_t) if eq_is_a else (tb_t, eq_t)
    prompt = f"A: {a_t}. B: {b_t}. Greater rate?"
    rt = Fraction(ys[1] - ys[0], xs[1] - xs[0])
    eq_letter, tb_letter = ("A", "B") if eq_is_a else ("B", "A")
    if correct_letter == "Same":
        big = eq_letter if pb > ys[0] else tb_letter
        la, lb = ("START_NOT_RATE", "RATE_NOT_COMPARED") if big == "A" else ("RATE_NOT_COMPARED", "START_NOT_RATE")
        return s_cmp_same(prompt, la, lb, f"Both rise {pm} per step. Only the starts differ. Same.")
    expl = f"{eq_letter} has rate {pm}. {tb_letter} rises {fnum(rt)} per step. {correct_letter} is greater."
    return s_cmp(prompt, correct_letter, label, expl)


def b5_cmp_fn(rng):
    xs = [0, 1, 2]
    eq_is_a = rng.random() < 0.5
    eq_letter, tb_letter = ("A", "B") if eq_is_a else ("B", "A")
    if rng.random() < 0.22:  # equal rates, different starts
        r = rng.randint(2, 6)
        qe, qt = rng.sample(range(1, 10), 2)
        return s_cmp_fn((r, qe), (xs, [qt + r * x for x in xs]), eq_is_a, "Same", "START_NOT_RATE")
    fast, slow = rng.randint(3, 6), rng.randint(2, 5)
    if fast <= slow:
        return None
    qf, qs = rng.randint(1, 3), rng.randint(5, 9)  # the faster one has the smaller start
    fast_is_eq = rng.random() < 0.5
    if fast_is_eq:
        eq, table = (fast, qf), (xs, [qs + slow * x for x in xs])
    else:
        eq, table = (slow, qs), (xs, [qf + fast * x for x in xs])
    correct = eq_letter if fast_is_eq else tb_letter
    return s_cmp_fn(eq, table, eq_is_a, correct, "START_NOT_RATE")


# =============================================================================================
# Assembly
# =============================================================================================
# (builder, how many of the 40 items) per tier; each builder is guaranteed its count
TIERS = {
    1: [(b1_pairs, 5), (b1_which_not, 4), (b1_which_is, 4), (b1_eval, 9), (b1_rule, 4), (b1_words, 7),
        (b1_dup_input, 5), (b1_dup_none, 2)],
    2: [(b2_points, 17), (b2_table, 9), (b2_words, 8), (b2_ramp, 6)],
    3: [(b3_initial, 8), (b3_slope, 8), (b3_word_eq, 10), (b3_slope_init, 5), (b3_table_eq, 9)],
    4: [(b4_cmp_words, 8), (b4_cmp_point, 5), (b4_cmp_eq, 4), (b4_unit_rate, 7), (b4_which_prop, 8),
        (b4_table_prop, 8)],
    5: [(b5_which_not, 7), (b5_which_is, 6), (b5_eq_linear, 5), (b5_direction, 11), (b5_table_uneven, 2),
        (b5_table_down, 1), (b5_table_curve, 2), (b5_table_curve_uneven, 1), (b5_cmp_fn, 5)],
}


def pick_wrongs(spec: Spec, rng: random.Random):
    ck = spec.correct[1]
    seen = {ck}
    cand = []
    for lab, ch in spec.wrong:
        if ch[1] in seen:
            continue
        seen.add(ch[1])
        cand.append((lab, ch))
    need = spec.n - 1
    if len(cand) > need:  # cover distinct labels first, then random
        rng.shuffle(cand)
        first, rest, labs = [], [], set()
        for lab, ch in cand:
            (rest if lab in labs else first).append((lab, ch))
            labs.add(lab)
        cand = (first + rest)[:need]
    if len(cand) < need and spec.arith:
        taken = {ch[1] for _, ch in cand} | {ch[1] for _, ch in spec.wrong} | {ck}
        for ch in spec.arith(rng):
            if len(cand) == need:
                break
            if ch[1] in taken:
                continue
            taken.add(ch[1])
            cand.append(("ARITH", ch))
    if len(cand) < need:
        return None
    return cand


def _text_ok(it) -> bool:
    if len(it["prompt"]) > 60 or len(it["explanation"]) > 160:
        return False
    if any(len(c) > 14 for c in it["choices"]):
        return False
    for s in [it["prompt"], it["explanation"]] + it["choices"]:
        if any(not (" " <= ch <= "~" or ch in ALLOWED_EXTRA) for ch in s):
            return False
    return True


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 200000):
    plan = TIERS[tier]
    total = sum(c for _, c in plan)
    kinds = [i for i, (_, c) in enumerate(plan) for _ in range(c)]
    if total != count:  # a manifest with another items_per_tier: stretch the last template
        kinds = (kinds + [len(plan) - 1] * count)[:count]
    rng.shuffle(kinds)
    items, prompts, attempts = [], set(), 0
    pos_counts: dict = {}
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        spec = plan[kinds[len(items)]][0](rng)
        if spec is None or spec.prompt in prompts:
            continue
        wrongs = pick_wrongs(spec, rng)
        if wrongs is None:
            continue
        rng.shuffle(wrongs)
        n = len(wrongs) + 1
        counts = pos_counts.setdefault(n, [0] * n)
        low = min(counts)
        pos = rng.choice([i for i, c in enumerate(counts) if c == low])
        choices = [ch[0] for _, ch in wrongs]
        labels = [lab for lab, _ in wrongs]
        choices.insert(pos, spec.correct[0])
        labels.insert(pos, None)
        item = {"tier": tier, "prompt": spec.prompt, "choices": choices, "answer": pos,
                "misconceptions": labels, "explanation": spec.expl}
        if not _text_ok(item):
            continue
        counts[pos] += 1
        prompts.add(spec.prompt)
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
