"""Procedural generator for the equations-inequalities cartridge (fnm-cart/1, grade 6, 6.EE.B.5–8).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` in the §4 shape without ``id``.
Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Tiers
-----
1. Is it a solution?  "Which makes x + 6 = 14 true?"  (+, −, ×, ÷; substitution)
2. Add & subtract     "Solve: x + 7 = 15", "15 = x + 7", "x − 4 = 9", "15 − x = 9"
3. Multiply & divide  "Solve: 4x = 28", "28 = 4x", "x ÷ 5 = 6", "24 ÷ x = 6"
4. Write the equation  a one-line story → the equation whose solution matches it
5. Inequalities        words → p ≥ 12; "Which is a solution of x < 4?"; "Which makes x + 2 < 7 true?"

Every distractor comes from a modelled misconception (``ARITH`` only to fill to 4). Two choices
never share a value: numbers by value, equations by their solution, inequalities by (direction,
strictness, boundary) -- so a player never faces two right doors.
"""
from __future__ import annotations

import random
from fractions import Fraction

MINUS, TIMES, DIV = "−", "×", "÷"
LT, GT, LE, GE = "<", ">", "≤", "≥"
VARS = ("x", "n", "y", "m", "k")
N_CHOICES = 4

MAX_PROMPT, MAX_CHOICE, MAX_EXPL = 60, 14, 160


# ---------------------------------------------------------------------------------------------
# Equation forms: (form, a, b) -> text / solution. ``v`` is the variable letter.
# ---------------------------------------------------------------------------------------------
def eq_text(form: str, v: str, a: int, b: int) -> str:
    return {
        "add": f"{v} + {a} = {b}",
        "add_r": f"{b} = {v} + {a}",
        "sub": f"{v} {MINUS} {a} = {b}",
        "rsub": f"{a} {MINUS} {v} = {b}",
        "mul": f"{a}{v} = {b}",
        "mul_r": f"{b} = {a}{v}",
        "div": f"{v} {DIV} {a} = {b}",
        "rdiv": f"{a} {DIV} {v} = {b}",
        "is_sum": f"{v} = {a} + {b}",
        "is_diff": f"{v} = {a} {MINUS} {b}",
        "is_prod": f"{v} = {a} {TIMES} {b}",
        "is_quot": f"{v} = {a} {DIV} {b}",
    }[form]


def eq_solution(form: str, a: int, b: int):
    """Exact solution of the one-step equation, or None when there is none."""
    a, b = Fraction(a), Fraction(b)
    if form in ("add", "add_r"):
        return b - a
    if form == "sub":
        return b + a
    if form == "rsub":
        return a - b
    if form in ("mul", "mul_r"):
        return b / a
    if form == "div":
        return a * b
    if form == "rdiv":
        return a / b if b else None
    return {"is_sum": a + b, "is_diff": a - b, "is_prod": a * b,
            "is_quot": a / b if b else None}[form]


# ---------------------------------------------------------------------------------------------
# Item assembly
# ---------------------------------------------------------------------------------------------
def _arith_fill(correct: int, taken: set, rng: random.Random) -> list:
    near = [correct + d for d in (1, -1, 2, -2, 3, 10, -10)]
    near = [v for v in near if v >= 1 and v not in taken]
    rng.shuffle(near)
    return near


def assemble(prompt, correct_text, correct_key, wrongs, pos, expl, rng, arith=None):
    """wrongs: [(label, text, key)] in priority order. Keys compare values; duplicates and any wrong
    choice equal in value to the correct one are dropped. ``arith`` (an int) fills with ARITH."""
    chosen, keys = [], {correct_key}
    for label, text, key in wrongs:
        if key in keys or key is None:
            continue
        chosen.append((label, text))
        keys.add(key)
        if len(chosen) == N_CHOICES - 1:
            break
    if arith is not None and len(chosen) < N_CHOICES - 1:
        for v in _arith_fill(arith, keys, rng):
            chosen.append(("ARITH", str(v)))
            keys.add(v)
            if len(chosen) == N_CHOICES - 1:
                break
    if len(chosen) < N_CHOICES - 1:
        return None
    rng.shuffle(chosen)
    choices = [t for _, t in chosen]
    labels = [lab for lab, _ in chosen]
    choices.insert(pos, correct_text)
    labels.insert(pos, None)
    if (len(prompt) > MAX_PROMPT or len(expl) > MAX_EXPL
            or any(len(c) > MAX_CHOICE for c in choices)):
        raise ValueError(f"length limit: {prompt!r} {choices} {expl!r}")
    return {"prompt": prompt, "choices": choices, "answer": pos,
            "misconceptions": labels, "explanation": expl}


def _numeric(prompt, sol, wrongs, pos, expl, rng):
    """Numeric choices; wrong values must be positive integers ≤ 999."""
    w = [(lab, str(v), v) for lab, v in wrongs
         if isinstance(v, int) and 1 <= v <= 999]
    return assemble(prompt, str(sol), sol, w, pos, expl, rng, arith=sol)


def _int(q):
    q = Fraction(q)
    return int(q) if q.denominator == 1 else None


# ---------------------------------------------------------------------------------------------
# Tiers 1–3: one-step equations
# ---------------------------------------------------------------------------------------------
def _one_step(rng, kind, small):
    """Returns (form, a, b, sol). ``small`` = tier 1 numbers."""
    top = 12 if small else 20
    fmax = 5 if small else 10
    if kind in ("add", "add_r"):
        a = rng.randint(2, top - 2)
        sol = rng.randint(1, top - a)
        return kind, a, a + sol, sol
    if kind == "sub":
        a = rng.randint(2, top - 3)
        b = rng.randint(1, top - a) if small else rng.randint(1, 20)
        return kind, a, b, a + b
    if kind == "rsub":  # a − x = b
        a = rng.randint(6, 20)
        b = rng.randint(1, a - 2)
        return kind, a, b, a - b
    if kind in ("mul", "mul_r"):
        a = rng.randint(2, fmax if small else 10)
        sol = rng.randint(2, 10 if not small else 6)
        return kind, a, a * sol, sol
    if kind == "div":
        a = rng.randint(2, fmax if small else 10)
        b = rng.randint(2, 10 if not small else 6)
        return kind, a, b, a * b
    if kind == "rdiv":  # D ÷ x = q
        q = rng.randint(2, 10)
        sol = rng.randint(2, 10)
        return kind, q * sol, q, sol
    raise ValueError(kind)


def _one_step_wrongs(form, a, b):
    """Misconception values for a one-step equation, priority order."""
    if form in ("add", "add_r"):
        return [("SAME_OP", b + a), ("VALUE_SHOWN", b), ("VALUE_SHOWN", a)]
    if form == "sub":
        return [("SAME_OP", b - a), ("VALUE_SHOWN", b), ("VALUE_SHOWN", a)]
    if form == "rsub":
        return [("SAME_OP", a + b), ("VALUE_SHOWN", b), ("VALUE_SHOWN", a)]
    if form in ("mul", "mul_r"):
        return [("SAME_OP", a * b), ("SUBTRACTED", b - a), ("VALUE_SHOWN", b)]
    if form == "div":
        return [("SAME_OP", _int(Fraction(b, a))), ("ADDED", a + b), ("VALUE_SHOWN", b)]
    if form == "rdiv":
        return [("SAME_OP", a * b), ("VALUE_SHOWN", b), ("VALUE_SHOWN", a)]
    raise ValueError(form)


def _check_text(form, v, a, b, sol):
    """'8 + 6 = 14' -- the equation with the solution plugged in."""
    return eq_text(form, v, a, b).replace(f"{a}{v}", f"{a} {TIMES} {sol}").replace(v, str(sol))


def _solve_expl(form, v, a, b, sol):
    if form in ("add", "add_r"):
        return f"Subtract {a} from both sides: {v} = {b} {MINUS} {a} = {sol}. Check: {sol} + {a} = {b}."
    if form == "sub":
        return f"Add {a} to both sides: {v} = {b} + {a} = {sol}. Check: {sol} {MINUS} {a} = {b}."
    if form == "rsub":
        return (f"{a} {MINUS} {v} = {b}: take {v} from {a} to leave {b}, so {v} = {a} {MINUS} {b} = {sol}. "
                f"Check: {a} {MINUS} {sol} = {b}.")
    if form in ("mul", "mul_r"):
        return f"Divide both sides by {a}: {v} = {b} {DIV} {a} = {sol}. Check: {a} {TIMES} {sol} = {b}."
    if form == "div":
        return f"Multiply both sides by {a}: {v} = {b} {TIMES} {a} = {sol}. Check: {sol} {DIV} {a} = {b}."
    if form == "rdiv":
        return (f"{a} {DIV} {v} = {b} asks what {a} splits by to give {b}: {v} = {a} {DIV} {b} = {sol}. "
                f"Check: {a} {DIV} {sol} = {b}.")
    raise ValueError(form)


def gen_t1(rng, kind, pos):
    v = rng.choice(VARS)
    form, a, b, sol = _one_step(rng, kind, small=True)
    prompt = f"Which makes {eq_text(form, v, a, b)} true?"
    expl = f"Try {sol}: {_check_text(form, v, a, b, sol)}. True, so {v} = {sol} is the solution."
    return _numeric(prompt, sol, _one_step_wrongs(form, a, b), pos, expl, rng)


def gen_t23(rng, kind, pos):
    v = rng.choice(VARS)
    form, a, b, sol = _one_step(rng, kind, small=False)
    prompt = f"Solve: {eq_text(form, v, a, b)}"
    return _numeric(prompt, sol, _one_step_wrongs(form, a, b), pos, _solve_expl(form, v, a, b, sol), rng)


# ---------------------------------------------------------------------------------------------
# Tier 4: write the equation
# ---------------------------------------------------------------------------------------------
STORIES = {
    "add": ("Had x cards. Got {a} more. Now has {b}.",
            "x kids on a bus. {a} more get on. Now {b}.",
            "Had ${{x}}. Earned ${a}. Now has ${b}.",
            "x birds in a tree. {a} more land. Now {b}."),
    "sub": ("Had x stickers. Gave away {a}. {b} left.",
            "Had ${{x}}. Spent ${a}. ${b} left.",
            "x cookies. Ate {a}. {b} are left.",
            "x kids at the park. {a} went home. {b} stayed."),
    "mul": ("{a} bags, x apples each. {b} apples in all.",
            "{a} rows of x chairs. {b} chairs in all.",
            "x pages a day for {a} days. {b} pages in all.",
            "{a} packs of x cards. {b} cards in all."),
    "div": ("x cookies shared by {a} kids. {b} each.",
            "x pencils in {a} equal boxes. {b} per box.",
            "${{x}} split by {a} friends. ${b} each.",
            "x players make {a} equal teams of {b}."),
}

# Correct form and candidate wrong forms (label, form, swap_ab) in priority order.
T4_FORMS = {
    "add": ("add", [("WRONG_OP", "sub", False), ("SWAPPED", "add", True),
                    ("KEYWORD", "is_sum", False), ("WRONG_OP", "mul", False)]),
    "sub": ("sub", [("WRONG_OP", "add", False), ("SWAPPED", "rsub", False),
                    ("KEYWORD", "is_diff", True), ("WRONG_OP", "div", False),
                    ("WRONG_OP", "mul", False)]),
    "mul": ("mul", [("WRONG_OP", "add", False), ("SWAPPED", "mul", True),
                    ("KEYWORD", "is_prod", False), ("WRONG_OP", "div", False)]),
    "div": ("div", [("WRONG_OP", "mul", False), ("SWAPPED", "rdiv", False),
                    ("KEYWORD", "is_quot", True), ("WRONG_OP", "sub", False)]),
}

T4_EXPL = {
    "add": "Start with x, add the {a} more, get {b}: x + {a} = {b}. (x = {s})",
    "sub": "Start with x, take away {a}, leave {b}: x − {a} = {b}. (x = {s})",
    "mul": "{a} groups of x make {b}: {a}x = {b}. (x = {s})",
    "div": "x split into {a} equal parts gives {b} each: x ÷ {a} = {b}. (x = {s})",
}


def gen_t4(rng, kind, pos):
    if kind == "add":
        a = rng.randint(2, 15)
        s = rng.randint(1, 20 - a)
        b = s + a
    elif kind == "sub":
        a = rng.randint(2, 15)
        b = rng.randint(2, 20)
        if a == b:
            return None
        s = a + b
    elif kind == "mul":
        a, s = rng.randint(2, 10), rng.randint(2, 10)
        b = a * s
    else:
        a, b = rng.randint(2, 10), rng.randint(2, 10)
        s = a * b
    story = rng.choice(STORIES[kind]).format(a=a, b=b).replace("${x}", "$x")
    prompt = f"{story} Equation?"
    form, cands = T4_FORMS[kind]
    wrongs = []
    for label, wform, swap in cands:
        wa, wb = (b, a) if swap else (a, b)
        wrongs.append((label, eq_text(wform, "x", wa, wb), eq_solution(wform, wa, wb)))
    expl = T4_EXPL[kind].format(a=a, b=b, s=s)
    return assemble(prompt, eq_text(form, "x", a, b), eq_solution(form, a, b), wrongs, pos, expl, rng)


# ---------------------------------------------------------------------------------------------
# Tier 5: inequalities
# ---------------------------------------------------------------------------------------------
PHRASES = {
    GE: (("p", "A team needs at least {n} players, p."),
         ("s", "To win, score s must be at least {n}."),
         ("a", "Rider age a must be at least {n} years."),
         ("t", "A ride takes {n} or more tickets, t.")),
    LE: (("k", "At most {n} kids, k, fit in the van."),
         ("c", "Take no more than {n} cards, c."),
         ("w", "The bag holds {n} lb or less, w."),
         ("g", "At most {n} guests, g, can come.")),
    GT: (("p", "More than {n} people, p, came."),
         ("h", "Plants taller than {n} cm, h, win a prize."),
         ("s", "The speed s is greater than {n}."),
         ("d", "The trip took over {n} days, d.")),
    LT: (("s", "Fewer than {n} seats, s, are left."),
         ("t", "The temperature t is below {n} degrees."),
         ("w", "Bags under {n} lb, w, fly free."),
         ("m", "Less than {n} minutes, m, remain.")),
}
FLIP = {LT: GT, GT: LT, LE: GE, GE: LE}
TOGGLE = {LT: LE, LE: LT, GT: GE, GE: GT}
WORDS = {GE: "{n} or more", LE: "{n} or less", GT: "more than {n}", LT: "less than {n}"}


def holds(op, x, c) -> bool:
    return {LT: x < c, GT: x > c, LE: x <= c, GE: x >= c}[op]


def gen_t5_write(rng, pos):
    op = rng.choice((GE, LE, GT, LT))
    v, phrase = rng.choice(PHRASES[op])
    n = rng.randint(3, 20)
    prompt = f"{phrase.format(n=n)} Which fits?"
    wrongs = [("FLIPPED_SIGN", f"{v} {FLIP[op]} {n}", (FLIP[op], n)),
              ("STRICT_VS_INCLUSIVE", f"{v} {TOGGLE[op]} {n}", (TOGGLE[op], n)),
              ("FLIPPED_SIGN", f"{v} {FLIP[TOGGLE[op]]} {n}", (FLIP[TOGGLE[op]], n))]
    expl = f"{WORDS[op].format(n=n).capitalize()}: {v} {op} {n}."
    if op in (GE, LE):
        expl += f" {n} itself counts, so the line goes under the sign."
    else:
        expl += f" {n} itself does not count, so no line under the sign."
    return assemble(prompt, f"{v} {op} {n}", (op, n), wrongs, pos, expl, rng)


def _pick_values(rng, op, c, lo, hi):
    """(correct, [(label, value)]) for 'which value makes it true', all in lo..hi."""
    members = [x for x in range(lo, hi + 1) if holds(op, x, c) and abs(x - c) <= 3]
    if op in (LE, GE) and rng.random() < 0.4:
        correct = c
    else:
        members = [x for x in members if x != c]
        correct = rng.choice(members)
    wrongs = []
    if op in (LT, GT):
        wrongs.append(("BOUNDARY", c))
    side = [x for x in range(lo, hi + 1) if not holds(op, x, c) and x != c and abs(x - c) <= 4]
    rng.shuffle(side)
    for x in side:
        wrongs.append(("WRONG_SIDE", x))
    return correct, wrongs


def gen_t5_pick(rng, pos, reversed_form):
    v = rng.choice(VARS)
    op = rng.choice((LT, GT, LE, GE))
    c = rng.randint(4, 16)
    correct, wrongs = _pick_values(rng, op, c, 0, 20)
    if reversed_form:  # "9 > n" is "n < 9"
        shown = f"{c} {FLIP[op]} {v}"
        wrongs = [("FLIPPED_SIGN" if lab == "WRONG_SIDE" else lab, x) for lab, x in wrongs]
        prompt = f"Which makes {shown} true?"
        expl = f"{shown} means {v} {op} {c}. Try {correct}: {c} {FLIP[op]} {correct} is true."
    else:
        prompt = f"Which is a solution of {v} {op} {c}?"
        expl = f"Try {correct}: {correct} {op} {c} is true."
    if op in (LT, GT):
        expl += f" {c} {op} {c} is false: {c} is not a solution."
    return _numeric(prompt, correct, wrongs, pos, expl, rng)


def gen_t5_plug(rng, pos):
    """'Which makes x + 2 < 7 true?' / 'Which makes 3x ≥ 12 true?'"""
    v = rng.choice(VARS)
    op = rng.choice((LT, GT, LE, GE))
    if rng.random() < 0.5:
        a = rng.randint(2, 6)
        c = rng.randint(4, 10)
        b = a + c
        correct, wrongs = _pick_values(rng, op, c, 1, 20 - a)
        prompt = f"Which makes {v} + {a} {op} {b} true?"
        expl = f"Try {correct}: {correct} + {a} = {correct + a}, and {correct + a} {op} {b} is true."
        if op in (LT, GT):
            expl += f" {c} + {a} = {b}, and {b} {op} {b} is false."
    else:
        a = rng.randint(2, 9)
        c = rng.randint(4, 6)
        b = a * c
        correct, wrongs = _pick_values(rng, op, c, 1, 10)
        prompt = f"Which makes {a}{v} {op} {b} true?"
        expl = (f"Try {correct}: {a} {TIMES} {correct} = {a * correct}, and {a * correct} {op} {b} "
                f"is true.")
        if op in (LT, GT):
            expl += f" {a} {TIMES} {c} = {b}, and {b} {op} {b} is false."
    return _numeric(prompt, correct, wrongs, pos, expl, rng)


# ---------------------------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------------------------
def _balanced(count: int, kinds, rng: random.Random) -> list:
    xs = [kinds[i % len(kinds)] for i in range(count)]
    rng.shuffle(xs)
    return xs


TIER_KINDS = {
    1: ("add", "sub", "mul", "div"),
    2: ("add", "add_r", "sub", "rsub"),
    3: ("mul", "mul_r", "div", "rdiv"),
    4: ("add", "sub", "mul", "div"),
    5: ("write", "write", "write", "pick", "pick_rev", "plug", "plug"),
}


def _one(tier, kind, rng, pos):
    if tier == 1:
        return gen_t1(rng, kind, pos)
    if tier in (2, 3):
        return gen_t23(rng, kind, pos)
    if tier == 4:
        return gen_t4(rng, kind, pos)
    if kind == "write":
        return gen_t5_write(rng, pos)
    if kind in ("pick", "pick_rev"):
        return gen_t5_pick(rng, pos, kind == "pick_rev")
    return gen_t5_plug(rng, pos)


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 100000) -> list:
    positions = _balanced(count, tuple(range(N_CHOICES)), rng)
    kinds = _balanced(count, TIER_KINDS[tier], rng)
    items, seen = [], set()
    for i in range(count):
        for _ in range(max_attempts):
            it = _one(tier, kinds[i], rng, positions[i])
            if it is None or it["prompt"] in seen:
                continue
            seen.add(it["prompt"])
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
