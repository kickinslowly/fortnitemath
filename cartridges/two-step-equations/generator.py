"""Procedural generator for the two-step-equations cartridge (fnm-cart/1, grade 7, 7.EE.B.3, B.4.A, B.4.B).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Tiers
-----
1. Solve px + q = r      "Solve: 2x + 6 = 14" (also 2x − 3 = 11, 14 = 2x + 6, 6 + 2x = 14); no negatives
2. Negatives             "Solve: −2x + 5 = 11", "5 − 2x = 11", "4x − 3 = −11"
3. Parentheses           "Solve: 3(x + 2) = 21", "Solve: −2(x + 3) = 8", and "Distribute the 3. Result?"
4. Stories               a one-line story: the answer, or the equation (px + q = r, p(x + q) = r)
5. Two-step inequalities "Solve: −3x + 2 ≤ 14" -> x ≥ −4 (the flip), and one-line budget stories

Every wrong choice is the value a modelled misconception produces. Only whole-number values are offered
as numeric distractors (a fraction would give the wrong door away); items that cannot supply three of them
are resampled, so ARITH is never needed. Two choices never share a value: numbers by value, equations by
their solution, inequalities by (sign, boundary).
"""
from __future__ import annotations

import random
import re
from fractions import Fraction

MINUS, TIMES = "−", "×"
LT, GT, LE, GE, EQ = "<", ">", "≤", "≥", "="
FLIP = {LT: GT, GT: LT, LE: GE, GE: LE}
TOGGLE = {LT: LE, LE: LT, GT: GE, GE: GT}
VARS = ("x", "n", "y", "m", "k", "t", "w")
N_CHOICES = 4

MAX_PROMPT, MAX_CHOICE, MAX_EXPL = 60, 14, 160


# ---------------------------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------------------------
def num(n) -> str:
    n = int(n)
    return str(n) if n >= 0 else f"{MINUS}{-n}"


def par(n) -> str:
    """A number as a factor: negatives get parentheses."""
    return f"({num(n)})" if int(n) < 0 else str(int(n))


def xterm(a: int, v: str) -> str:
    if a == 1:
        return v
    if a == -1:
        return MINUS + v
    return f"{MINUS if a < 0 else ''}{abs(a)}{v}"


def lin_text(a: int, v: str, b: int, const_first: bool = False) -> str:
    """a·v + b, as 2x + 6, −2x + 5, 4x − 3, or constant first (5 − 2x, 6 + 2x). b = 0 drops the constant."""
    if b == 0:
        return xterm(a, v)
    if not const_first:
        return f"{xterm(a, v)} {'+' if b > 0 else MINUS} {abs(b)}"
    return f"{num(b)} {'+' if a > 0 else MINUS} {xterm(abs(a), v)}"


def grp_text(p: int, v: str, q: int) -> str:
    """p(v + q), as 3(x + 2), 4(x − 1), −2(x + 3)."""
    return f"{MINUS if p < 0 else ''}{abs(p)}({v} {'+' if q > 0 else MINUS} {abs(q)})"


# An equation is (kind, u, w, R): "lin" is u·v + w = R, "grp" is u(v + w) = R.
def eq_str(eq, v: str, rev: bool = False, cf: bool = False) -> str:
    kind, u, w, R = eq
    lhs = lin_text(u, v, w, cf) if kind == "lin" else grp_text(u, v, w)
    return f"{num(R)} = {lhs}" if rev else f"{lhs} = {num(R)}"


def eq_solution(eq) -> Fraction:
    kind, u, w, R = eq
    return Fraction(R - w, u) if kind == "lin" else Fraction(R, u) - w


# ---------------------------------------------------------------------------------------------
# Item assembly
# ---------------------------------------------------------------------------------------------
def assemble(prompt, correct_text, correct_key, wrongs, pos, expl, rng):
    """wrongs: [(label, text, key)] in priority order. Keys compare values; a wrong choice whose key is
    already taken (the correct one included) is dropped. Returns None when fewer than three distinct
    wrongs exist or a display limit is broken (the caller resamples)."""
    chosen, keys = [], {correct_key}
    for label, text, key in wrongs:
        if key is None or key in keys:
            continue
        chosen.append((label, text))
        keys.add(key)
        if len(chosen) == N_CHOICES - 1:
            break
    if len(chosen) < N_CHOICES - 1:
        return None
    rng.shuffle(chosen)
    choices = [t for _, t in chosen]
    labels = [lab for lab, _ in chosen]
    choices.insert(pos, correct_text)
    labels.insert(pos, None)
    if len(prompt) > MAX_PROMPT or any(len(c) > MAX_CHOICE for c in choices):
        return None
    if len(expl) > MAX_EXPL:
        raise ValueError(f"explanation too long ({len(expl)}): {expl!r}")
    return {"prompt": prompt, "choices": choices, "answer": pos,
            "misconceptions": labels, "explanation": expl}


def numeric_item(rng, prompt, sol, wrongs, pos, expl, lo=None, cap=60):
    """Numeric choices. wrongs: [(label, value)]; only whole values within the limits are offered
    (size <= cap: a distractor of 147 beside an answer of 3 gives itself away)."""
    w = []
    for lab, val in wrongs:
        val = Fraction(val)
        if val.denominator != 1:
            continue
        n = int(val)
        if abs(n) > cap or (lo is not None and n < lo):
            continue
        w.append((lab, num(n), n))
    return assemble(prompt, num(sol), int(sol), w, pos, expl, rng)


def equation_item(rng, prompt, v, correct, wrongs, pos, expl):
    """Equation choices. wrongs: [(label, eq)]; keyed by solution so no two are equal in value."""
    w = [(lab, eq_str(eq, v), eq_solution(eq)) for lab, eq in wrongs]
    return assemble(prompt, eq_str(correct, v), eq_solution(correct), w, pos, expl, rng)


def inequality_item(rng, prompt, v, correct, wrongs, pos, expl):
    """Choices like 'x ≥ −4'. correct / wrongs carry (op, boundary); keyed by (op, boundary)."""
    def text(sig):
        return f"{v} {sig[0]} {num(sig[1])}"
    w = [(lab, text(sig), (sig[0], Fraction(sig[1]))) for lab, sig in wrongs
         if Fraction(sig[1]).denominator == 1]
    return assemble(prompt, text(correct), (correct[0], Fraction(correct[1])), w, pos, expl, rng)


def ordered(rng, first, middle, last=()):
    """first stay first, middle is shuffled, last stays last."""
    mid = list(middle)
    rng.shuffle(mid)
    return list(first) + mid + list(last)


# ---------------------------------------------------------------------------------------------
# Misconception values (the numbers each wrong rule produces)
# ---------------------------------------------------------------------------------------------
def lin_candidates(a: int, b: int, R: int) -> dict:
    """Wrong values for a·x + b = R, by misconception label (Fractions; the caller keeps whole ones)."""
    x = Fraction(R - b, a)
    return {
        "SAME_OP": Fraction(R + b, a),           # added b back instead of removing it
        "DIVIDE_FIRST": Fraction(R, a) - b,      # divided only the right side by a
        "ONE_STEP": Fraction(R - b),             # stopped at a·x
        "SIGN_DROP": -x,                         # lost a negative sign in the division
        "MULTIPLIED": Fraction((R - b) * a),     # multiplied by a instead of dividing
        "SUBTRACTED": Fraction(R - b - a),       # subtracted a instead of dividing
        "IGNORED_FIXED": Fraction(R, a),         # story: divided the total, forgot the fixed amount
    }


def grp_candidates(p: int, q: int, R: int) -> dict:
    """Wrong values for p(x + q) = R."""
    s = Fraction(R, p)
    return {
        "WRONG_INVERSE": s + q,                  # undid + q with the wrong operation
        "ONE_STEP": s,                           # stopped at x + q
        "DROPPED_P": Fraction(R - q),            # ignored the factor outside
        "PARTIAL_DIST": Fraction(R - q, p),      # p·x + q = R
        "SIGN_DROP": -(s - q),
    }


def _pick(cands: dict, labels, rename=None):
    rename = rename or {}
    return [(rename.get(lab, lab), cands[lab]) for lab in labels]


# ---------------------------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------------------------
def undo_short(b: int) -> str:
    return f"Subtract {b}" if b > 0 else f"Add {-b}"


def undo_phrase(b: int) -> str:
    return f"Subtract {b} from both sides" if b > 0 else f"Add {-b} to both sides"


def lin_check(a, b, x, R, cf) -> str:
    if cf:
        return f"{num(b)} {'+' if a > 0 else MINUS} {abs(a)} {TIMES} {par(x)} = {num(R)}"
    return f"{num(a)} {TIMES} {par(x)} {'+' if b > 0 else MINUS} {abs(b)} = {num(R)}"


def lin_expl(v, a, b, R, x, cf=False) -> str:
    return (f"{undo_phrase(b)}: {xterm(a, v)} = {num(R - b)}. Divide by {num(a)}: {v} = {num(x)}. "
            f"Check: {lin_check(a, b, x, R, cf)}.")


def grp_expl(v, p, q, R, x) -> str:
    s = R // p
    sg = "+" if q > 0 else MINUS
    return (f"Divide both sides by {num(p)}: {v} {sg} {abs(q)} = {num(s)}. {undo_short(q)}: {v} = {num(x)}. "
            f"Check: {num(p)}({num(x)} {sg} {abs(q)}) = {num(R)}.")


# ---------------------------------------------------------------------------------------------
# Tier 1: px + q = r, no negatives
# ---------------------------------------------------------------------------------------------
A1 = (2, 2, 3, 3, 3, 4, 4, 5, 5, 6, 7, 8, 9)
X1 = (2, 3, 3, 4, 4, 5, 5, 6, 7, 8, 9, 10)


def pick_q(rng, a, lo=1, hi=12):
    """A constant in lo..hi; 45% of the time a multiple of a, so the wrong rules that divide the right side
    (SAME_OP, DIVIDE_FIRST) land on whole numbers more often."""
    if rng.random() < 0.45:
        mult = [m for m in range(a, hi + 1, a) if m >= lo]
        if mult:
            return rng.choice(mult)
    return rng.randint(lo, hi)


def poor(rng, cands) -> bool:
    """True for an item where neither SAME_OP nor DIVIDE_FIRST is a whole number (the two most
    diagnostic wrong rules): mostly resampled, so the distractors are real mistakes, not filler."""
    return (all(cands[k].denominator != 1 for k in ("SAME_OP", "DIVIDE_FIRST"))
            and rng.random() < 0.4)


def sample_t1(rng, kind):
    """Returns (a, b, x, R): a·x + b = R, a 2-9, x 2-10, |b| 1-12, R 1-20."""
    for _ in range(1000):
        a, x = rng.choice(A1), rng.choice(X1)
        q = pick_q(rng, a)
        b = -q if kind == "sub" or (kind == "rev" and rng.random() < 0.5) else q
        R = a * x + b
        if 1 <= R <= 20:
            return a, b, x, R
    return None


def gen_t1(rng, kind, pos):
    v = rng.choice(VARS)
    s = sample_t1(rng, kind)
    if s is None:
        return None
    a, b, x, R = s
    cf = kind == "cf"
    body = eq_str(("lin", a, b, R), v, rev=(kind == "rev"), cf=cf)
    cands = lin_candidates(a, b, R)
    if poor(rng, cands):
        return None
    wrongs = _pick(cands, ordered(rng, [], ["SAME_OP", "DIVIDE_FIRST", "ONE_STEP"], ["MULTIPLIED", "SUBTRACTED"]))
    return numeric_item(rng, f"Solve: {body}", x, wrongs, pos, lin_expl(v, a, b, R, x, cf), lo=1)


# ---------------------------------------------------------------------------------------------
# Tier 2: negatives
# ---------------------------------------------------------------------------------------------
A_WEIGHTS = (2, 2, 2, 3, 3, 3, 4, 4, 5, 5, 6, 7, 8, 9, 10)


def sample_t2(rng, kind):
    """a·x + b = R with signs: |a| 2-10, |x| 2-10, |b| 1-12, |R| 1-12 (so |a·x| <= 24)."""
    for _ in range(3000):
        a = rng.choice(A_WEIGHTS) * rng.choice((-1, 1))
        x = rng.randint(2, 10) * rng.choice((-1, 1))
        b = pick_q(rng, abs(a)) * rng.choice((-1, 1))
        R = a * x + b
        if R == 0 or abs(R) > 12 or abs(a * x) > 24:
            continue
        if kind in ("neg", "neg_cf") and a > 0:
            continue
        if kind == "pos" and not (a > 0 and (x < 0 or R < 0)):
            continue
        if kind == "rev" and not (a < 0 or x < 0 or R < 0):
            continue
        return a, b, x, R
    return None


def gen_t2(rng, kind, pos):
    v = rng.choice(VARS)
    s = sample_t2(rng, kind)
    if s is None:
        return None
    a, b, x, R = s
    cf = kind == "neg_cf"
    body = eq_str(("lin", a, b, R), v, rev=(kind == "rev"), cf=cf)
    cands = lin_candidates(a, b, R)
    if poor(rng, cands):
        return None
    if rng.random() < 0.5:   # half the items carry the sign slip; the rest keep the +/- and divide slips
        order = ordered(rng, ["SIGN_DROP"], ["SAME_OP", "DIVIDE_FIRST", "ONE_STEP"], ["MULTIPLIED"])
    else:
        order = ordered(rng, [], ["SAME_OP", "DIVIDE_FIRST", "ONE_STEP"], ["MULTIPLIED", "SIGN_DROP"])
    return numeric_item(rng, f"Solve: {body}", x, _pick(cands, order), pos, lin_expl(v, a, b, R, x, cf))


# ---------------------------------------------------------------------------------------------
# Tier 3: p(x + q) = r
# ---------------------------------------------------------------------------------------------
def sample_group(rng, kind, pmax=10, qmin=1, qmax=10):
    """Returns (p, q, s, x, R): p(x + q) = R with R = p·s, s = x + q. |p| 2-pmax, |s| 2-10, |q| qmin-qmax,
    |x| 2-10. Kind 'a': all positive. 'b': q negative. 'c': a sign twist (p < 0 or s < 0)."""
    for _ in range(5000):
        if kind == "a":
            sp, ss, sq = 1, 1, 1
        elif kind == "b":
            sp, ss, sq = 1, 1, -1
        else:
            sp, ss = rng.choice(((-1, 1), (-1, -1), (1, -1)))
            sq = rng.choice((-1, 1))
        p, s, q = sp * rng.randint(2, pmax), ss * rng.randint(2, 10), sq * rng.randint(qmin, qmax)
        x = s - q
        if kind in ("a", "b") and x < 0:
            continue
        if 2 <= abs(x) <= 10:
            return p, q, s, x, p * s
    return None


def gen_t3_solve(rng, kind, pos):
    v = rng.choice(VARS)
    s = sample_group(rng, kind)
    if s is None:
        return None
    p, q, sv, x, R = s
    twist = p < 0 or sv < 0
    cands = grp_candidates(p, q, R)
    if twist:
        order = ordered(rng, ["SIGN_DROP"], ["WRONG_INVERSE", "ONE_STEP", "DROPPED_P", "PARTIAL_DIST"])
    else:
        order = ordered(rng, ["WRONG_INVERSE"], ["ONE_STEP", "DROPPED_P", "PARTIAL_DIST"])
    rev = rng.random() < 0.25
    body = eq_str(("grp", p, q, R), v, rev=rev)
    return numeric_item(rng, f"Solve: {body}", x, _pick(cands, order), pos, grp_expl(v, p, q, R, x), cap=120)


def dist_wrongs(p, q, R):
    """Wrong equations for 'distribute the p' in p(x + q) = R (the right one is px + pq = R)."""
    w = [("PARTIAL_DIST", ("lin", p, q, R)),
         ("DIST_LAST_ONLY", ("lin", 1, p * q, R)),
         ("DIST_SIGN", ("lin", p, -p * q, R))]
    if p > 0:
        w.append(("ADDED_FOR_MULT", ("lin", p, p + q, R)))
    return w


def gen_t3_dist(rng, pos):
    v = rng.choice(VARS)
    s = sample_group(rng, rng.choice(("a", "a", "b", "c")), pmax=9, qmin=2, qmax=9)
    if s is None:
        return None
    p, q, sv, x, R = s
    correct = ("lin", p, p * q, R)
    wrongs = dist_wrongs(p, q, R)
    rng.shuffle(wrongs)
    prompt = f"{eq_str(('grp', p, q, R), v)}. Distribute the {num(p)}. Result?"
    expl = (f"Multiply every term inside by {num(p)}: {num(p)}{v} and {num(p)} {TIMES} {par(q)} = {num(p * q)}. "
            f"So {eq_str(correct, v)}.")
    return equation_item(rng, prompt, v, correct, wrongs, pos, expl)


# ---------------------------------------------------------------------------------------------
# Tier 4: stories
# ---------------------------------------------------------------------------------------------
# Noun stories: p a unit, q fixed, R total, v counts the nouns. (story, var, noun, why)
N_STORIES = (
    ("${q} to get in, ${p} a ride. Spent ${R}.", "r", "rides", "${p} a ride plus ${q} to get in"),
    ("Plan: ${q} plus ${p} a month. Paid ${R}.", "m", "months", "${p} a month plus ${q}"),
    ("Save ${p} a week from ${q} to reach ${R}.", "w", "weeks", "${p} a week added to ${q}"),
    ("Taxi: ${q} plus ${p} a mile. Fare ${R}.", "m", "miles", "${p} a mile plus ${q}"),
    ("Gym: ${q} to join, ${p} a visit. Paid ${R}.", "v", "visits", "${p} a visit plus ${q} to join"),
)
# Embedded stories: the letter is in the story. (story, var, sign of q)
E_STORIES = (
    ("{p} bags of n apples plus {q} loose make {R}.", "n", 1),
    ("{p} pens at $c each plus a ${q} bag cost ${R}.", "c", 1),
    ("{p} rows of k seats plus {q} extra make {R} seats.", "k", 1),
    ("{p} boxes of n pens. Gave away {q}. {R} left.", "n", -1),
    ("{p} shirts cost $s each. ${q} coupon. Paid ${R}.", "s", -1),
    ("{p} packs of k cards, lost {q}. {R} cards left.", "k", -1),
)
# Group stories p(v + q) = R. "Each of {p} ..." leads, so the extra q plainly belongs to every group
# (a trailing "plus 2 spares" can be read as 2 in total, which makes px + q = R a second right reading).
# The total names both things it counts ("in all", "items"). (story, var, dollars): in a dollar story the
# extra stays below the price, so a tax never outweighs what it is added to.
G_STORIES = (
    ("Each of {p} kids pays $c plus ${q} tax. ${R} in all.", "c", True),
    ("Each of {p} pals pays $b plus a ${q} tip. ${R} in all.", "b", True),
    ("Each of {p} kids gets n cards and {q} pins: {R} items.", "n", False),
    ("Each of {p} teams gets t balls and {q} cones: {R} items.", "t", False),
)


def sample_t4_lin(rng, sign):
    """a·x + sign·q = R with a 2-9, x 2-10, q 2-12 (q != a), R 1-20."""
    for _ in range(1000):
        a, x = rng.choice(A1), rng.choice(X1)
        q = pick_q(rng, a, 2)
        R = a * x + sign * q
        if q != a and 2 <= R <= 20:
            return a, sign * q, x, R
    return None


def lin_write_wrongs(a, b, R):
    """Wrong equations for a story that means a·v + b = R."""
    w = [("IGNORED_FIXED", ("lin", a, 0, R)),
         ("SWAPPED", ("lin", abs(b), a if b > 0 else -a, R)),
         ("WRONG_OP", ("lin", a, -b, R))]
    if a + b >= 2:
        w.append(("COMBINED_TERMS", ("lin", a + b, 0, R)))
    return w


def gen_t4_lin(rng, pos, mode, style):
    if style == "n":
        story, v, noun, why = rng.choice(N_STORIES)
        sign = 1
    else:
        story, v, sign = rng.choice(E_STORIES)
        why = f"{{p}} groups of {v}" + (" plus {q} more" if sign > 0 else ", minus {q}")
    s = sample_t4_lin(rng, sign)
    if s is None:
        return None
    a, b, x, R = s
    text = story.format(p=a, q=abs(b), R=R)
    if mode == "solve":
        ask = f"{noun.capitalize()}?" if style == "n" else f"Find {v}."
        cands = lin_candidates(a, b, R)
        order = ordered(rng, [], ["SAME_OP", "IGNORED_FIXED", "ONE_STEP"], ["SUBTRACTED", "MULTIPLIED"])
        wrongs = _pick(cands, order, {"SAME_OP": "ADDED_FIXED"})
        eqt = eq_str(("lin", a, b, R), v)
        expl = f"{eqt}. {undo_short(b)}: {xterm(a, v)} = {R - b}. Divide by {a}: {v} = {x}."
        return numeric_item(rng, f"{text} {ask}", x, wrongs, pos, expl, lo=1)
    ask = f"Equation for {v} {noun}?" if style == "n" else "Equation?"
    correct = ("lin", a, b, R)
    wrongs = lin_write_wrongs(a, b, R)
    rng.shuffle(wrongs)
    why = why.format(p=a, q=abs(b))
    expl = f"{why}: {eq_str(correct, v)}. (Then {v} = {x}.)"
    return equation_item(rng, f"{text} {ask}", v, correct, wrongs, pos, expl)


def grp_write_wrongs(p, q, R):
    """Wrong equations for a story that means p(v + q) = R. Not px + q = R (PARTIAL_DIST): a story can be
    misread that way, and a choice a reader can defend is a second right door. T3 tests that slip."""
    return [("WRONG_OP", ("grp", p, -q, R)), ("SWAPPED", ("grp", q, p, R)),
            ("IGNORED_FIXED", ("lin", p, 0, R))]


def gen_t4_grp(rng, pos, mode):
    story, v, dollars = rng.choice(G_STORIES)
    for _ in range(1000):
        p, s, q = rng.randint(2, 9), rng.randint(4, 10), rng.randint(2, 8)
        x = s - q
        if p != q and 2 <= x <= 10 and (not dollars or q < x):
            break
    else:
        return None
    R = p * s
    text = story.format(p=p, q=q, R=R)
    if mode == "solve":
        cands = grp_candidates(p, q, R)
        order = ordered(rng, ["WRONG_INVERSE"], ["ONE_STEP", "DROPPED_P"])   # never (r - q) / p: see G_STORIES
        return numeric_item(rng, f"{text} Find {v}.", x, _pick(cands, order), pos,
                            grp_expl(v, p, q, R, x), lo=1, cap=120)
    correct = ("grp", p, q, R)
    wrongs = grp_write_wrongs(p, q, R)
    rng.shuffle(wrongs)
    expl = f"{p} people, each with ({v} + {q}): {eq_str(correct, v)}. (Then {v} = {x}.)"
    return equation_item(rng, f"{text} Equation?", v, correct, wrongs, pos, expl)


def gen_t4(rng, kind, pos):
    style, mode = kind.split("_")
    if style == "g":
        return gen_t4_grp(rng, pos, mode)
    return gen_t4_lin(rng, pos, mode, style)


# ---------------------------------------------------------------------------------------------
# Tier 5: inequalities
# ---------------------------------------------------------------------------------------------
# (story, var, op): p·v + q op R with p a unit, q fixed, R the limit.
S5_STORIES = (
    ("Entry ${q}, rides ${p} each. Spend at most ${R}. Rides r?", "r", LE),
    ("Gym ${q} to join, ${p} a visit. Spend at most ${R}. Visits v?", "v", LE),
    ("Need at least {R} points. Have {q}, earn {p} a game. Games g?", "g", GE),
    ("Run at least {R} laps. Did {q}, do {p} more a day. Days d?", "d", GE),
    ("Phone plan: ${q} plus ${p} a month. Cost over ${R}. Months m?", "m", GT),
    ("Save more than ${R}. Have ${q}, add ${p} a week. Weeks w?", "w", GT),
    ("Under {R} lb allowed. Cart {q} lb, boxes {p} lb. Boxes b?", "b", LT),
    ("Spend under ${R}. Taxi ${q} plus ${p} a mile. Miles m?", "m", LT),
)


def sample_t5_sym(rng, kind):
    """p·c + q = R with |p| 2-10, |c| 2-10, |q| 1-12, |R| 1-12; p < 0 for 'neg' kinds."""
    for _ in range(3000):
        p = rng.choice(A_WEIGHTS) * (1 if kind == "pos" else -1)
        c = rng.randint(2, 10) * (rng.choice((1, 1, 1, -1)) if kind == "pos" else rng.choice((-1, 1)))
        q = rng.randint(1, 12) * rng.choice((-1, 1))
        R = p * c + q
        if R == 0 or abs(R) > 12 or abs(p * c) > 24:
            continue
        return p, q, c, R
    return None


def ineq_candidates(p, q, c, R, op0) -> dict:
    """Wrong (sign, boundary) pairs for p·x + q op0 R, whose solution is op1 c (op1 = op0, flipped if p < 0)."""
    op1 = op0 if p > 0 else FLIP[op0]
    return {
        "NO_FLIP": (op0, c),                              # divided by a negative, kept the sign
        "FLIP_WRONG": (FLIP[op0], c),                     # flipped after dividing by a positive
        "BOUNDARY_ONLY": (EQ, c),                         # solved it as an equation
        "STRICT_VS_INCLUSIVE": (TOGGLE[op1], c),         # < for ≤ or the reverse
        "SAME_OP": (op1, Fraction(R + q, p)),             # added q back instead of removing it
        "ONE_STEP": (op0, R - q),                         # stopped at p·x
        "SIGN_DROP": (op1, -c),                           # lost a negative sign in the division
    }


def story_ineq_candidates(p, q, c, R, op) -> dict:
    """Wrong (sign, boundary) pairs for a story meaning p·v + q op R (so v op c)."""
    return {
        "WRONG_DIRECTION": (FLIP[op], c),
        "STRICT_VS_INCLUSIVE": (TOGGLE[op], c),
        "BOUNDARY_ONLY": (EQ, c),
        "ONE_STEP": (op, R - q),
        "SAME_OP": (op, Fraction(R + q, p)),
    }


def gen_t5_sym(rng, kind, pos):
    v = rng.choice(VARS)
    s = sample_t5_sym(rng, kind)
    if s is None:
        return None
    p, q, c, R = s
    op0 = rng.choice((LT, GT, LE, GE))
    op1 = op0 if p > 0 else FLIP[op0]
    cf = kind == "neg_cf"
    stmt = f"{lin_text(p, v, q, cf)} {op0} {num(R)}"
    cands = ineq_candidates(p, q, c, R, op0)
    first = [("NO_FLIP" if p < 0 else "FLIP_WRONG", cands["NO_FLIP" if p < 0 else "FLIP_WRONG"])]
    pool = [(k, cands[k]) for k in ("BOUNDARY_ONLY", "STRICT_VS_INCLUSIVE", "SAME_OP", "ONE_STEP")]
    if p < 0 or c < 0:
        pool.append(("SIGN_DROP", cands["SIGN_DROP"]))
    rng.shuffle(pool)
    mid = f"{undo_short(q)}: {xterm(p, v)} {op0} {num(R - q)}."
    if p < 0:
        tail = f"Divide by {num(p)} and flip the sign: {v} {op1} {num(c)}."
    else:
        tail = f"Divide by {p}: {v} {op1} {num(c)}. The sign stays."
    return inequality_item(rng, f"Solve: {stmt}", v, (op1, c), first + pool, pos, f"{mid} {tail}")


def gen_t5_story(rng, pos):
    story, v, op = rng.choice(S5_STORIES)
    for _ in range(1000):
        p, c = rng.choice(A1), rng.randint(3, 10)
        q = pick_q(rng, p, 2)
        R = p * c + q
        if R <= 20 and p != q:
            break
    else:
        return None
    prompt = story.format(p=p, q=q, R=R)
    cands = story_ineq_candidates(p, q, c, R, op)
    pool = [(k, cands[k]) for k in ("BOUNDARY_ONLY", "ONE_STEP", "SAME_OP")]
    rng.shuffle(pool)
    wrongs = [(k, cands[k]) for k in ("WRONG_DIRECTION", "STRICT_VS_INCLUSIVE")] + pool
    note = f"{c} counts." if op in (LE, GE) else f"{c} does not count."
    expl = (f"{lin_text(p, v, q)} {op} {R}. Subtract {q}: {xterm(p, v)} {op} {R - q}. "
            f"Divide by {p}: {v} {op} {c}. {note}")
    return inequality_item(rng, prompt, v, (op, c), wrongs, pos, expl)


# ---------------------------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------------------------
def _balanced(count: int, kinds, rng: random.Random) -> list:
    xs = [kinds[i % len(kinds)] for i in range(count)]
    rng.shuffle(xs)
    return xs


TIER_KINDS = {
    1: ("add", "sub", "rev", "cf"),
    2: ("neg", "neg_cf", "pos", "rev"),
    3: ("a", "b", "c", "dist"),
    4: ("n_solve", "n_write", "e_solve", "e_write", "e_solve", "e_write", "g_solve", "g_write"),
    5: ("neg", "neg_cf", "pos", "story"),
}


def _one(tier, kind, rng, pos):
    if tier == 1:
        return gen_t1(rng, kind, pos)
    if tier == 2:
        return gen_t2(rng, kind, pos)
    if tier == 3:
        return gen_t3_dist(rng, pos) if kind == "dist" else gen_t3_solve(rng, kind, pos)
    if tier == 4:
        return gen_t4(rng, kind, pos)
    return gen_t5_story(rng, pos) if kind == "story" else gen_t5_sym(rng, kind, pos)


def same_math(prompt: str) -> str:
    """The prompt with every one-letter token blanked: 2x + 6 = 14 and 2n + 6 = 14 are the same question."""
    return re.sub(r"(?<![A-Za-z])[a-z](?![A-Za-z])", "_", prompt)


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
