"""Procedural generator for the order-of-operations cartridge (fnm-cart/1).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4
shape without ``id``. Stdlib only. Deterministic for a given ``rng`` seed.

Design
------
* Expressions are built as trees, rendered to display text, and then *re-parsed from the display
  text* for every evaluation. The text a student sees is therefore the only thing ever evaluated,
  so the display and the answer cannot drift apart.
* ONE evaluator (``evaluate``) parameterised by a ``Rule``: a precedence table plus two switches
  (strip parentheses, treat ``^`` as ``×``). The correct rules and every misconception are rows in
  ``RULES``.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from fractions import Fraction

# ---------------------------------------------------------------------------------------------
# Display characters
# ---------------------------------------------------------------------------------------------
ADD, SUB, MUL, DIV, POW = "+", "−", "×", "÷", "^"
BINARY_OPS = (ADD, SUB, MUL, DIV, POW)


# ---------------------------------------------------------------------------------------------
# Rules (the single evaluator's parameter)
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    name: str
    prec: dict  # op -> binding strength (higher binds tighter)
    right_assoc: frozenset = frozenset()
    strip_parens: bool = False
    exp_as_mult: bool = False


_CORRECT_PREC = {ADD: 1, SUB: 1, MUL: 2, DIV: 2, POW: 3}

RULES = {
    "CORRECT": Rule("CORRECT", _CORRECT_PREC, right_assoc=frozenset({POW})),
    # Strict left to right; parentheses still respected.
    "LTR": Rule("LTR", {ADD: 1, SUB: 1, MUL: 1, DIV: 1, POW: 1}),
    # + − bind tighter than × ÷; ^ unchanged.
    "ADD_FIRST": Rule("ADD_FIRST", {ADD: 2, SUB: 2, MUL: 1, DIV: 1, POW: 3}),
    # Delete all parentheses, then correct precedence.
    "IGNORE_PARENS": Rule("IGNORE_PARENS", _CORRECT_PREC, strip_parens=True),
    # a^b evaluated as a × b, in ^'s precedence slot.
    "EXP_AS_MULT": Rule("EXP_AS_MULT", _CORRECT_PREC, exp_as_mult=True),
    # ^ looser than × ÷ but tighter than + −.
    "EXP_AFTER_MULT": Rule("EXP_AFTER_MULT", {ADD: 1, SUB: 1, POW: 2, MUL: 3, DIV: 3}),
    # × tighter than ÷.
    "M_BEFORE_D": Rule("M_BEFORE_D", {ADD: 1, SUB: 1, DIV: 2, MUL: 3, POW: 4}),
    # + tighter than −.
    "A_BEFORE_S": Rule("A_BEFORE_S", {SUB: 1, ADD: 2, MUL: 3, DIV: 3, POW: 4}),
}

# When two misconceptions produce the same wrong value, the label is the first in this list.
LABEL_PRIORITY = ("EXP_AS_MULT", "EXP_AFTER_MULT", "IGNORE_PARENS", "M_BEFORE_D",
                  "A_BEFORE_S", "ADD_FIRST", "LTR")


class Invalid(Exception):
    """Raised when an expression cannot be evaluated under a rule (÷0, huge power, ...)."""


# ---------------------------------------------------------------------------------------------
# Tokenise / parse / evaluate
# ---------------------------------------------------------------------------------------------
def tokenize(text: str) -> list:
    toks, i = [], 0
    while i < len(text):
        c = text[i]
        if c == " ":
            i += 1
        elif c.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            toks.append(int(text[i:j]))
            i = j
        elif c in BINARY_OPS or c in "()":
            toks.append(c)
            i += 1
        else:
            raise ValueError(f"bad character {c!r} in {text!r}")
    return toks


def parse(tokens: list, rule: Rule, meta: dict | None = None):
    """Precedence climbing. Returns a tree: int | (op, left, right).
    If ``meta`` is given it is filled with id(node) -> (paren depth, operator token index)."""
    if rule.strip_parens:
        tokens = [t for t in tokens if t not in ("(", ")")]
    pos = 0
    depth = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def primary():
        nonlocal pos, depth
        t = peek()
        if isinstance(t, int):
            pos += 1
            return t
        if t == "(":
            pos += 1
            depth += 1
            node = expr(0)
            if peek() != ")":
                raise ValueError("unbalanced parentheses")
            pos += 1
            depth -= 1
            return node
        raise ValueError(f"unexpected token {t!r}")

    def expr(min_prec):
        nonlocal pos
        lhs = primary()
        while True:
            op = peek()
            if op not in rule.prec or rule.prec[op] < min_prec:
                return lhs
            op_pos, op_depth = pos, depth
            pos += 1
            p = rule.prec[op]
            rhs = expr(p if op in rule.right_assoc else p + 1)
            lhs = (op, lhs, rhs)
            if meta is not None:
                meta[id(lhs)] = (op_depth, op_pos)

    tree = expr(0)
    if pos != len(tokens):
        raise ValueError("trailing tokens")
    return tree


def _apply(op: str, a: Fraction, b: Fraction, rule: Rule) -> Fraction:
    if op == POW and rule.exp_as_mult:
        op = MUL
    if op == ADD:
        return a + b
    if op == SUB:
        return a - b
    if op == MUL:
        return a * b
    if op == DIV:
        if b == 0:
            raise Invalid("division by zero")
        return a / b
    if op == POW:
        if b.denominator != 1 or not 0 <= b <= 10 or abs(a) > 10 ** 4:
            raise Invalid("unsupported power")
        return a ** int(b)
    raise ValueError(op)


def _eval_tree(node, rule: Rule, steps: list | None):
    if isinstance(node, int):
        return Fraction(node)
    op, l, r = node
    a, b = _eval_tree(l, rule, steps), _eval_tree(r, rule, steps)
    v = _apply(op, a, b, rule)
    if abs(v) > 10 ** 7:
        raise Invalid("value too large")
    if steps is not None:
        steps.append((op, a, b, v))
    return v


def evaluate(text: str, rule: Rule | str = "CORRECT"):
    """THE evaluator. Value of display text under ``rule`` as a Fraction, or None if invalid."""
    if isinstance(rule, str):
        rule = RULES[rule]
    try:
        return _eval_tree(parse(tokenize(text), rule), rule, None)
    except Invalid:
        return None


def trace(text: str):
    """Correct-rule steps [(op, a, b, result), ...] in the order a student is taught to work:
    innermost parentheses first, then ^, then × ÷, then + −, left to right within a level."""
    rule = RULES["CORRECT"]
    meta: dict = {}
    tree = parse(tokenize(text), rule, meta)
    value: dict = {}
    nodes: list = []

    def collect(node):
        if isinstance(node, int):
            return
        collect(node[1])
        collect(node[2])
        nodes.append(node)

    def val(node):
        return Fraction(node) if isinstance(node, int) else value[id(node)]

    collect(tree)
    steps = []
    pending = list(nodes)
    while pending:
        ready = [n for n in pending
                 if all(isinstance(c, int) or id(c) in value for c in (n[1], n[2]))]
        n = max(ready, key=lambda n: (meta[id(n)][0], rule.prec[n[0]], -meta[id(n)][1]))
        a, b = val(n[1]), val(n[2])
        v = _apply(n[0], a, b, rule)
        value[id(n)] = v
        steps.append((n[0], a, b, v))
        pending = [m for m in pending if m is not n]  # identity: equal twins are distinct nodes
    return steps


# ---------------------------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------------------------
def fmt_op(a, op, b) -> str:
    return f"{a}^{b}" if op == POW else f"{a} {op} {b}"


def render(node, parent_prec: int = 0, side: str = "L") -> str:
    """Minimal-parenthesis display under correct precedence (all left-assoc; ^ base always a group)."""
    if isinstance(node, int):
        return str(node)
    op, l, r = node
    p = _CORRECT_PREC[op]
    s = fmt_op(render(l, p, "L"), op, render(r, p, "R"))
    if p < parent_prec or (p == parent_prec and (side == "R" or op == POW)):
        return f"({s})"
    return s


# ---------------------------------------------------------------------------------------------
# Value-aware random construction (keeps every intermediate a non-negative integer, ÷ exact)
# ---------------------------------------------------------------------------------------------
MAX_VALUE = 999
MAX_LEAF = 100  # no number in a prompt larger than this (keeps 6th-grade mental math sane)


class _Retry(Exception):
    pass


def _val(node) -> int:
    v = evaluate(render(node))
    if v is None or v.denominator != 1:
        raise _Retry
    return int(v)


def _leaf(rng: random.Random) -> int:
    return rng.randint(2, 12)


def _build(rng: random.Random, n_ops: int, ops: tuple, max_pow: int):
    """Random tree with exactly n_ops binary operators drawn from ops."""
    if n_ops == 0:
        return _leaf(rng)
    choices = [o for o in ops if o != POW or max_pow > 0]
    op = rng.choice(choices)
    if op == POW:
        base = _build(rng, n_ops - 1, ops, max_pow - 1)
        if not isinstance(base, int) and base[0] == POW:
            raise _Retry  # no chained powers
        bv = _val(base)
        if isinstance(base, int):
            base = rng.randint(2, 10)
            bv = base
        if not 2 <= bv <= 10:
            raise _Retry
        exps = [e for e in (2, 3) if bv ** e <= 1000]
        return (POW, base, rng.choice(exps))
    k = rng.randint(0, n_ops - 1)
    left = _build(rng, k, ops, max_pow)
    right = _build(rng, n_ops - 1 - k, ops, max_pow - _count(left, POW))
    lv, rv = _val(left), _val(right)
    if op == DIV:
        if isinstance(right, int):
            divs = [d for d in range(2, 13) if lv % d == 0 and lv // d >= 1]
            if not divs:
                if isinstance(left, int):
                    right = rng.randint(2, 9)
                    left = right * rng.randint(2, 9)
                else:
                    raise _Retry
            else:
                right = rng.choice(divs)
        elif isinstance(left, int):
            if rv < 2:
                raise _Retry
            left = rv * rng.randint(2, 9)
        elif rv < 2 or lv % rv:
            raise _Retry
    elif op == SUB:
        if isinstance(right, int):
            if lv < 2:
                raise _Retry
            right = rng.randint(1, min(lv - 1, 20))
        elif isinstance(left, int):
            left = rv + rng.randint(1, 12)
        elif lv <= rv:
            raise _Retry
    if any(isinstance(x, int) and x > MAX_LEAF for x in (left, right)):
        raise _Retry
    node = (op, left, right)
    v = _val(node)
    if not 0 <= v <= MAX_VALUE:
        raise _Retry
    return node


def _count(node, op) -> int:
    if isinstance(node, int):
        return 0
    return (node[0] == op) + _count(node[1], op) + _count(node[2], op)


def _all_steps_ok(text: str) -> bool:
    try:
        steps = trace(text)
    except Invalid:
        return False
    return all(v.denominator == 1 and 0 <= v <= MAX_VALUE for *_, v in steps)


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
ASMD = (ADD, SUB, MUL, DIV)
ALL = ASMD + (POW,)


def _differs(text: str, correct, *rules: str) -> bool:
    return any(evaluate(text, r) not in (None, correct) for r in rules)


@dataclass
class TierSpec:
    n_ops: tuple
    ops: tuple
    max_pow: int
    check: callable = field(repr=False)


def _t1(text, c):  # two ops, no parens/powers, a naive LTR reading differs
    return "(" not in text and POW not in text and _differs(text, c, "LTR")


def _t2(text, c):  # exactly one paren group, and it changes the result
    return text.count("(") == 1 and POW not in text and _differs(text, c, "IGNORE_PARENS")


def _t3(text, c):  # exactly one exponent, no parens, precedence matters
    return ("(" not in text and text.count(POW) == 1
            and _differs(text, c, "LTR", "EXP_AFTER_MULT", "ADD_FIRST"))


def _t4(text, c):  # exponent(s) + parentheses that matter
    return POW in text and "(" in text and _differs(text, c, "IGNORE_PARENS")


def _t5(text, c):  # 4-5 ops, ÷ and ^ present, at least one paren group
    return DIV in text and POW in text and "(" in text


TIERS = {
    1: TierSpec((2,), ASMD, 0, _t1),
    2: TierSpec((2, 3), ASMD, 0, _t2),
    3: TierSpec((2, 3), ALL, 1, _t3),
    4: TierSpec((2, 3, 4), ALL, 2, _t4),
    5: TierSpec((4, 5), ALL, 2, _t5),
}


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def explanation(text: str) -> str:
    parts = [f"{fmt_op(int(a), op, int(b))} = {int(v)}" for op, a, b, v in trace(text)]
    return ", then ".join(parts) + "."


_SUPER = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _unicode_len(s: str) -> int:
    """Length after the unicode render profile (^digits -> superscripts)."""
    import re
    return len(re.sub(r"\^(\d+)", lambda m: m.group(1).translate(_SUPER), s))


def misconception_values(text: str, declared) -> list:
    """[(label, value)] for every declared misconception rule yielding a distinct usable wrong value,
    labelled by LABEL_PRIORITY when rules collide."""
    correct = evaluate(text)
    out, seen = [], {correct}
    for label in LABEL_PRIORITY:
        if label not in declared:
            continue
        v = evaluate(text, label)
        if v is None or v.denominator != 1 or not 0 <= v <= MAX_VALUE or v in seen:
            continue
        seen.add(v)
        out.append((label, int(v)))
    return out


_ARITH_OFFSETS = (1, -1, 2, -2, 10, -10, 3, -3, 4, -4, 5, -5)


def make_item(text: str, tier: int, declared, answer_pos: int, rng: random.Random):
    correct = int(evaluate(text))
    wrong = misconception_values(text, declared)
    if not wrong:
        return None
    if len(wrong) > 3:
        keep = sorted(rng.sample(range(len(wrong)), 3))
        wrong = [wrong[i] for i in keep]
    used = {correct} | {v for _, v in wrong}
    offsets = list(_ARITH_OFFSETS)
    rng.shuffle(offsets)
    for off in offsets:
        if len(wrong) == 3:
            break
        v = correct + off
        if 0 <= v <= MAX_VALUE and v not in used:
            used.add(v)
            wrong.append(("ARITH", v))
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, correct)] + wrong[answer_pos:]
    exp = explanation(text)
    if _unicode_len(exp) > 160:
        return None
    return {
        "tier": tier,
        "prompt": text,
        "choices": [str(v) for _, v in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": exp,
    }


def gen_tier(tier: int, count: int, declared, rng: random.Random, max_attempts: int = 200000):
    spec = TIERS[tier]
    positions = [i % 4 for i in range(count)]  # exact balance: count/4 per position
    rng.shuffle(positions)
    items, prompts = [], set()
    attempts = 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        try:
            tree = _build(rng, rng.choice(spec.n_ops), spec.ops, spec.max_pow)
        except _Retry:
            continue
        text = render(tree)
        if text in prompts or len(text) > 60 or not _all_steps_ok(text):
            continue
        c = evaluate(text)
        if c is None or c.denominator != 1 or not 0 <= c <= MAX_VALUE:
            continue
        if not spec.check(text, c):
            continue
        item = make_item(text, tier, declared, positions[len(items)], rng)
        if item is None:
            continue
        prompts.add(text)
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    declared = set(manifest["misconceptions"])
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, declared, rng))
    return items
