"""Procedural generator for the integer-operations cartridge (fnm-cart/1).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4
shape without ``id``. Stdlib only. Deterministic for a given ``rng`` seed. Independent of every
other cartridge (patterns borrowed from order-of-ops-exponents, nothing imported).

Design
------
* Expressions are built as trees, rendered to display text, and then *re-parsed from the display
  text* for every evaluation, so the text a student sees is the only thing ever evaluated.
* ONE evaluator (``evaluate``) parameterised by a ``Rule``. The correct rule and every
  misconception are rows in ``RULES``. A misconception rule is the correct rule with exactly one
  fault switched on:
    - a *step fault* replaces the result of one kind of binary step wherever it applies
      (NEG_NEG_ADD, ADD_SIZES, SUB_NEG, SIGN_RULE_PRODUCT, MUL_FOR_DIV, ADD_FOR_MUL) -- a student
      holding the faulty rule applies it every time it fits;
    - ORDER parses + − × ÷ strictly left to right (parentheses and ^ still respected);
    - NEG_POWER swaps the meaning of −a^n and (−a)^n;
    - WRONG_SIGN negates the final answer when the last step is a sum or difference.
* T4/T5 never contain a sub-expression (any non-leaf node, the whole prompt included) whose
  correct value is 0, e.g. ``(−10 + 10) × (−6)``: a zero intermediate makes the rest trivial.
* Display: negatives use U+2212. A negative that follows an operator is parenthesised
  (``5 + (−9)``), a leading negative is bare (``−7 + 3``), a negative power base is always
  parenthesised (``(−3)^2``) and ``−a^n`` (= −(a^n)) only ever appears in leading position.

Collision priority
------------------
When several faulty rules produce the same wrong value, the label is the first rule in
``LABEL_PRIORITY`` that produced it: most specific (names one concrete wrong rule about one
construct) first, generic last. NEG_POWER > SUB_NEG > NEG_NEG_ADD > ADD_SIZES >
SIGN_RULE_PRODUCT > MUL_FOR_DIV > ADD_FOR_MUL > ORDER > WRONG_SIGN. Example: −3 + (−5) = −8; NEG_NEG_ADD and WRONG_SIGN both
give 8, labelled NEG_NEG_ADD.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from fractions import Fraction

# ---------------------------------------------------------------------------------------------
# Display characters
# ---------------------------------------------------------------------------------------------
ADD, SUB, MUL, DIV, POW = "+", "−", "×", "÷", "^"
MINUS = "−"  # U+2212, both binary minus and the negative sign
UNARY = "u−"  # token for a unary minus (never displayed)
ARITH_OPS = (ADD, SUB, MUL, DIV)

# PROTOCOL §4a (concept over arithmetic; signs are this topic's concept, so literals are tighter).
MAX_VALUE = 100  # every intermediate value and the answer: size <= 100
MAX_DISTRACTOR = 999  # wrong choices: whatever a misreading produces, size <= this
MAX_ADDEND = 12  # T1/T2 literal sizes 1..12
MAX_FACTOR = 10  # factors, divisors, quotients, power bases, T4/T5 leaves; every × operand
MAX_CUBE_BASE = 4  # cubes of 2..4 only (power results <= 100)


def num(n) -> str:
    """Choice / value string: −12, 0, 7."""
    n = int(n)
    return f"{MINUS}{-n}" if n < 0 else str(n)


# ---------------------------------------------------------------------------------------------
# Trees: int (a non-negative literal) | Neg(x) | Bin(op, l, r) | Pow(base, exp)
# ---------------------------------------------------------------------------------------------
class Node:
    depth = 0  # paren depth of the operator (set by the parser)
    pos = 0  # token index of the operator (set by the parser)


class Neg(Node):
    def __init__(self, x):
        self.x = x


class Bin(Node):
    def __init__(self, op, l, r):
        self.op, self.l, self.r = op, l, r


class Pow(Node):
    def __init__(self, base, exp):
        self.base, self.exp = base, exp


# ---------------------------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------------------------
def _neg_neg_add(op, a, b):
    """−a + (−b) → a + b (positive)."""
    if op == ADD and a < 0 and b < 0:
        return -a - b
    return None


def _add_sizes(op, a, b):
    """Mixed-sign addition adds the sizes and keeps the sign of the larger size."""
    if op == ADD and (a < 0) != (b < 0) and a != 0 and b != 0 and abs(a) != abs(b):
        big = a if abs(a) > abs(b) else b
        s = abs(a) + abs(b)
        return -s if big < 0 else s
    return None


def _sub_neg(op, a, b):
    """a − (−b) → a − b."""
    if op == SUB and b < 0:
        return a + b
    return None


def _sign_rule(op, a, b):
    """Wrong sign on a product or quotient that involves a negative."""
    if op in (MUL, DIV) and (a < 0 or b < 0) and a != 0:
        if op == DIV and b == 0:
            return None
        return -(a * b) if op == MUL else -(a / b)
    return None


def _mul_for_div(op, a, b):
    """Multiplies instead of dividing on a quotient with a negative: −12 ÷ 3 → −36."""
    if op == DIV and (a < 0 or b < 0) and b != 0:
        return a * b
    return None


def _add_for_mul(op, a, b):
    """Adds instead of multiplying on a product with a negative: −6 × 4 → −2."""
    if op == MUL and (a < 0 or b < 0) and a + b != 0:
        return a + b
    return None


@dataclass(frozen=True)
class Rule:
    name: str
    step: object = None  # callable(op, a, b) -> faulty value or None (= correct)
    ltr: bool = False  # + − × ÷ all one precedence level, left to right
    neg_power_swap: bool = False
    root_negate: bool = False


RULES = {
    "CORRECT": Rule("CORRECT"),
    "NEG_NEG_ADD": Rule("NEG_NEG_ADD", step=_neg_neg_add),
    "ADD_SIZES": Rule("ADD_SIZES", step=_add_sizes),
    "SUB_NEG": Rule("SUB_NEG", step=_sub_neg),
    "SIGN_RULE_PRODUCT": Rule("SIGN_RULE_PRODUCT", step=_sign_rule),
    "MUL_FOR_DIV": Rule("MUL_FOR_DIV", step=_mul_for_div),
    "ADD_FOR_MUL": Rule("ADD_FOR_MUL", step=_add_for_mul),
    "ORDER": Rule("ORDER", ltr=True),
    "NEG_POWER": Rule("NEG_POWER", neg_power_swap=True),
    "WRONG_SIGN": Rule("WRONG_SIGN", root_negate=True),
}

LABEL_PRIORITY = ("NEG_POWER", "SUB_NEG", "NEG_NEG_ADD", "ADD_SIZES",
                  "SIGN_RULE_PRODUCT", "MUL_FOR_DIV", "ADD_FOR_MUL", "ORDER", "WRONG_SIGN")

_PREC = {ADD: 1, SUB: 1, MUL: 2, DIV: 2}
_LTR_PREC = {ADD: 1, SUB: 1, MUL: 1, DIV: 1}


class Invalid(Exception):
    """Expression cannot be evaluated under a rule (÷0, inexact ÷, huge value)."""


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
        elif c == MINUS:
            prev = toks[-1] if toks else None
            toks.append(UNARY if prev is None or prev == "(" or prev in ARITH_OPS + (POW,)
                        else SUB)
            i += 1
        elif c in ARITH_OPS or c in "()^":
            toks.append(c)
            i += 1
        else:
            raise ValueError(f"bad character {c!r} in {text!r}")
    return toks


def parse(text: str, rule: Rule):
    tokens = tokenize(text)
    prec = _LTR_PREC if rule.ltr else _PREC
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
        raise ValueError(f"unexpected token {t!r} in {text!r}")

    def power():
        nonlocal pos
        base = primary()
        if peek() == POW:
            op_pos = pos
            pos += 1
            e = primary()
            if not isinstance(e, int):
                raise ValueError("exponent must be a digit")
            n = Pow(base, e)
            n.depth, n.pos = depth, op_pos
            return n
        return base

    def unary():
        nonlocal pos
        if peek() == UNARY:
            op_pos = pos
            pos += 1
            n = Neg(unary() if peek() == UNARY else power())
            n.depth, n.pos = depth, op_pos
            return n
        return power()

    def expr(min_prec):
        nonlocal pos
        lhs = unary()
        while True:
            op = peek()
            if op not in prec or prec[op] < min_prec:
                return lhs
            op_pos = pos
            pos += 1
            rhs = expr(prec[op] + 1)
            n = Bin(op, lhs, rhs)
            n.depth, n.pos = depth, op_pos
            lhs = n

    tree = expr(0)
    if pos != len(tokens):
        raise ValueError(f"trailing tokens in {text!r}")
    return tree


def _correct_step(op, a, b):
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
    raise ValueError(op)


def _eval(node, rule: Rule) -> Fraction:
    if isinstance(node, int):
        return Fraction(node)
    if isinstance(node, Neg):
        if rule.neg_power_swap and isinstance(node.x, Pow):
            return (-_eval(node.x.base, rule)) ** node.x.exp  # −a^n read as (−a)^n
        return -_eval(node.x, rule)
    if isinstance(node, Pow):
        if rule.neg_power_swap and isinstance(node.base, Neg):
            return -(_eval(node.base.x, rule) ** node.exp)  # (−a)^n read as −(a^n)
        return _eval(node.base, rule) ** node.exp
    a, b = _eval(node.l, rule), _eval(node.r, rule)
    v = rule.step(node.op, a, b) if rule.step else None
    if v is None:
        v = _correct_step(node.op, a, b)
    if v.denominator != 1:
        raise Invalid("inexact division")
    if abs(v) > MAX_DISTRACTOR:
        raise Invalid("value too large")
    return v


def evaluate(text: str, rule: Rule | str = "CORRECT"):
    """THE evaluator. Integer value of display text under ``rule``, or None if not applicable/valid.

    For a misconception rule, returns None when the rule does not apply to this expression (it
    would give the correct value) or the result is unusable."""
    if isinstance(rule, str):
        rule = RULES[rule]
    tree = parse(text, rule)
    try:
        if rule.root_negate:
            if not (isinstance(tree, Bin) and tree.op in (ADD, SUB)):
                return None
            v = -_eval(tree, RULES["CORRECT"])
        else:
            v = _eval(tree, rule)
    except (Invalid, ZeroDivisionError):
        return None
    if v.denominator != 1 or abs(v) > MAX_DISTRACTOR:
        return None
    return int(v)


# ---------------------------------------------------------------------------------------------
# Rendering (tree -> display text)
# ---------------------------------------------------------------------------------------------
def render(node, follows_op: bool = False, parent_prec: int = 0, side: str = "L") -> str:
    """Minimal parentheses under correct precedence; negatives per the display rules."""
    if isinstance(node, int):
        if node < 0:
            return f"({MINUS}{-node})" if follows_op else f"{MINUS}{-node}"
        return str(node)
    if isinstance(node, Neg) and isinstance(node.x, int):  # parsed negative literal
        node = -node.x
        return render(node, follows_op, parent_prec, side)
    if isinstance(node, Pow):
        b = node.base
        if isinstance(b, Neg):
            b = -b.x
        bs = f"({MINUS}{-b})" if b < 0 else str(b)
        return f"{bs}^{node.exp}"
    if isinstance(node, Neg):  # only Neg(Pow) is generated; must be in leading position
        if follows_op:
            raise ValueError("−a^n may only lead")
        return f"{MINUS}{render(node.x)}"
    p = _PREC[node.op]
    needs = p < parent_prec or (p == parent_prec and side == "R")
    inner_follows = False if needs else follows_op
    s = (f"{render(node.l, inner_follows, p, 'L')} {node.op} "
         f"{render(node.r, True, p, 'R')}")
    return f"({s})" if needs else s


# ---------------------------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------------------------
def _lead(v) -> str:
    return num(v)


def _follow(v) -> str:
    v = int(v)
    return f"({MINUS}{-v})" if v < 0 else str(v)


def trace(text: str):
    """Correct steps [str, ...] in the order a student is taught to work: innermost parentheses
    first, then powers (and −a^n), then × ÷, then + −, left to right within a level."""
    rule = RULES["CORRECT"]
    tree = parse(text, rule)
    nodes = []

    def collect(n):
        if isinstance(n, Bin):
            collect(n.l)
            collect(n.r)
            nodes.append(n)
        elif isinstance(n, Neg):
            collect(n.x)
            if isinstance(n.x, Pow):
                nodes.append(n)
        elif isinstance(n, Pow):
            nodes.append(n)  # (−a)^n is one step

    collect(tree)

    def level(n):
        if isinstance(n, (Pow, Neg)):
            return 3
        return _PREC[n.op]

    def kids(n):
        if isinstance(n, Bin):
            return [n.l, n.r]
        if isinstance(n, Neg):
            return [n.x]
        return [n.base]

    done = set()

    def ready(n):
        return all(not isinstance(k, (Bin, Pow)) and not (isinstance(k, Neg) and isinstance(k.x, Pow))
                   or id(k) in done for k in kids(n))

    steps = []
    pending = list(nodes)
    while pending:
        cand = [n for n in pending if ready(n)]
        n = max(cand, key=lambda n: (n.depth, level(n), -n.pos))
        v = _eval(n, rule)
        if isinstance(n, Pow):
            steps.append(f"{render(n)} = {num(v)}")
        elif isinstance(n, Neg):
            steps.append(f"{MINUS}{render(n.x)} = {num(v)}")
        else:
            a, b = _eval(n.l, rule), _eval(n.r, rule)
            steps.append(f"{_lead(a)} {n.op} {_follow(b)} = {num(v)}")
        done.add(id(n))
        pending = [m for m in pending if m is not n]
    return steps


def _add_expl(a: int, b: int, head: str) -> str:
    """Explain a + b for a, b not both positive. ``head`` is what the student sees first."""
    v = a + b
    if a < 0 and b < 0:
        return f"{head}: both negative, {-a} + {-b} = {-v}, so {num(v)}."
    if a > 0 and b > 0:
        return f"{head} = {num(v)}."
    big, small = (a, b) if abs(a) > abs(b) else (b, a)
    sign = "negative" if big < 0 else "positive"
    return (f"{head}: signs differ, {abs(big)} {MINUS} {abs(small)} = {abs(v)}. "
            f"{num(big)} is farther from 0, so {sign}: {num(v)}.")


def explain_t1(a: int, b: int) -> str:
    return _add_expl(a, b, f"{_lead(a)} + {_follow(b)}")


def explain_t2(a: int, b: int) -> str:
    head = f"{_lead(a)} {SUB} {_follow(b)}"
    if b < 0:
        return _add_expl(a, -b, f"{head} = {_lead(a)} + {-b}")
    return _add_expl(a, -b, f"{head} = {_lead(a)} + {_follow(-b)}")


def explain_t3(a: int, op: str, b: int) -> str:
    v = a * b if op == MUL else a // b
    mag = f"{abs(a)} {op} {abs(b)} = {abs(v)}"
    if a < 0 and b < 0:
        return f"{_lead(a)} {op} {_follow(b)}: two negatives make a positive. {mag}."
    return f"{_lead(a)} {op} {_follow(b)}: one negative makes it negative. {mag}, so {num(v)}."


def explain_steps(text: str) -> str:
    return ", then ".join(trace(text)) + "."


# ---------------------------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------------------------
def misconception_values(text: str, declared) -> list:
    """[(label, value)] for every declared misconception rule yielding a distinct usable wrong value,
    labelled by LABEL_PRIORITY when rules collide."""
    correct = evaluate(text)
    out, seen = [], {correct}
    for label in LABEL_PRIORITY:
        if label not in declared:
            continue
        v = evaluate(text, label)
        if v is None or v in seen:
            continue
        seen.add(v)
        out.append((label, v))
    return out


def _arith_candidates(correct: int, rng: random.Random) -> list:
    near = [correct + d for d in (1, -1, 2, -2)]
    rng.shuffle(near)
    far = [correct + d for d in (3, -3)] + [-(correct + 1), -(correct - 1)]
    rng.shuffle(far)
    return near + far


MUST_KEEP = ("NEG_POWER", "ORDER")  # tier-defining misconceptions are never dropped


def make_item(text: str, tier: int, declared, answer_pos: int, rng: random.Random, expl: str):
    correct = evaluate(text)
    allv = misconception_values(text, declared)
    if not allv:
        return None
    wrong = list(allv)
    if len(wrong) > 3:
        keep = [w for w in wrong if w[0] in MUST_KEEP]
        rest = [w for w in wrong if w[0] not in MUST_KEEP]
        rng.shuffle(rest)
        keep = (keep + rest)[:3]
        wrong = [w for w in wrong if w in keep]
    used = {correct} | {v for _, v in allv}  # ARITH never coincides with ANY rule's value
    for v in _arith_candidates(correct, rng):
        if len(wrong) == 3:
            break
        if abs(v) <= MAX_DISTRACTOR and v not in used:
            used.add(v)
            wrong.append(("ARITH", v))
    if len(wrong) < 3 or len(expl) > 160 or len(text) > 60:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:answer_pos] + [(None, correct)] + wrong[answer_pos:]
    return {
        "tier": tier,
        "prompt": text,
        "choices": [num(v) for _, v in pairs],
        "answer": answer_pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


def _nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v


def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


# --- T1: a + b ----------------------------------------------------------------------------------
def _t1(rng, kind):
    if kind == 0:  # both negative
        a, b = -rng.randint(1, MAX_ADDEND), -rng.randint(1, MAX_ADDEND)
    else:  # mixed sign, either order
        a, b = rng.randint(1, MAX_ADDEND), -rng.randint(1, MAX_ADDEND)
        if rng.random() < 0.5:
            a, b = b, a
        if abs(a) == abs(b):
            return None
    return f"{_lead(a)} + {_follow(b)}", explain_t1(a, b)


# --- T2: a − b ----------------------------------------------------------------------------------
def _t2(rng, kind):
    if kind in (0, 1, 2):  # subtract a negative (a either sign)
        a, b = _nz(rng, -MAX_ADDEND, MAX_ADDEND), -rng.randint(1, MAX_ADDEND)
    elif kind == 3:  # negative minus positive
        a, b = -rng.randint(1, MAX_ADDEND), rng.randint(1, MAX_ADDEND)
    else:  # positive minus bigger positive: crosses zero
        a, b = rng.randint(1, MAX_ADDEND - 1), rng.randint(2, MAX_ADDEND)
        if a >= b:
            return None
    if a == b:
        return None
    return f"{_lead(a)} {SUB} {_follow(b)}", explain_t2(a, b)


# --- T3: a × b, a ÷ b -----------------------------------------------------------------------------
def _signs(rng, x, y):
    s = rng.choice(((-1, 1), (1, -1), (-1, -1)))
    return s[0] * x, s[1] * y


def _t3(rng, kind):
    if kind == 0:
        a, b = _signs(rng, rng.randint(2, MAX_FACTOR), rng.randint(2, MAX_FACTOR))
        op = MUL
    else:  # every operand (dividend included) within −20..20, exact; divisor, quotient 2..10
        d = rng.randint(2, MAX_FACTOR)
        q = rng.randint(2, 20 // d)
        a, b = _signs(rng, d * q, d)
        op = DIV
    return f"{_lead(a)} {op} {_follow(b)}", explain_t3(a, op, b)


# --- T4 / T5: random trees ------------------------------------------------------------------------
class _Retry(Exception):
    pass


def _shape(rng, n_ops):
    if n_ops == 0:
        return None
    k = rng.randint(0, n_ops - 1)
    return [rng.choice(ARITH_OPS), _shape(rng, k), _shape(rng, n_ops - 1 - k)]


def _leaves(shape) -> int:
    return 1 if shape is None else _leaves(shape[1]) + _leaves(shape[2])


def _value(node) -> int:
    v = evaluate(render(node))
    if v is None:
        raise _Retry
    return v


def _fill(rng, shape, counter, power_leaf, power_kind):
    """Shape -> tree. Leaf number ``power_leaf`` (in-order) becomes a power of a negative."""
    if shape is None:
        idx = counter[0]
        counter[0] += 1
        if idx == power_leaf:
            e = rng.choice((2, 2, 3))
            base = rng.randint(2, MAX_FACTOR if e == 2 else MAX_CUBE_BASE)
            return Neg(Pow(base, e)) if power_kind == "neg" else Pow(-base, e)
        v = rng.randint(2, MAX_FACTOR)
        return -v if rng.random() < 0.5 else v
    op, ls, rs = shape
    left = _fill(rng, ls, counter, power_leaf, power_kind)
    right = _fill(rng, rs, counter, power_leaf, power_kind)
    if op == DIV:  # exact; divisor and quotient sizes 2..10
        lv = _value(left)
        if isinstance(right, int):
            divs = [d for d in range(2, MAX_FACTOR + 1)
                    if lv % d == 0 and 2 <= abs(lv) // d <= MAX_FACTOR]
            if divs:
                d = rng.choice(divs)
                right = -d if rng.random() < 0.5 else d
            elif isinstance(left, int):
                d = rng.randint(2, MAX_FACTOR)
                right = -d if rng.random() < 0.5 else d
                left = right * rng.choice((-1, 1)) * rng.randint(2, MAX_FACTOR)
            else:
                raise _Retry
        else:
            rv = _value(right)
            if isinstance(left, int) and 2 <= abs(rv) <= MAX_FACTOR:
                left = rv * rng.choice((-1, 1)) * rng.randint(2, MAX_FACTOR)
            elif (not 2 <= abs(rv) <= MAX_FACTOR or lv % rv
                  or not 2 <= abs(lv) // abs(rv) <= MAX_FACTOR):
                raise _Retry
    elif op == MUL:  # both operand values <= 10 in size (a group's value counts)
        if abs(_value(left)) > MAX_FACTOR or abs(_value(right)) > MAX_FACTOR:
            raise _Retry
    node = Bin(op, left, right)
    if abs(_value(node)) > MAX_VALUE:
        raise _Retry
    return node


def _steps_ok(text: str, tier: int) -> bool:
    """THE §4a gate, on the displayed text's correct tree: every intermediate and the answer size
    <= 100; every × operand <= 10; every ÷ exact with divisor and quotient 2..10; squares of 2..10,
    cubes of 2..4; literal sizes per tier (T1/T2 1..12, T3+ 2..10; a bare dividend <= 100, T3's
    <= 20)."""
    lo, hi = (1, MAX_ADDEND) if tier <= 2 else (2, MAX_FACTOR)
    dividend_hi = 20 if tier == 3 else 100
    rule = RULES["CORRECT"]

    def lit(n):
        if isinstance(n, int):
            return n
        if isinstance(n, Neg) and isinstance(n.x, int):
            return -n.x
        return None

    def ok(n) -> bool:
        if lit(n) is not None:
            return True
        if isinstance(n, Neg):
            if not ok(n.x):
                return False
        elif isinstance(n, Pow):
            if lit(n.base) is None:
                return False
            b = abs(lit(n.base))
            if not (n.exp in (2, 3) and 2 <= b <= (MAX_FACTOR if n.exp == 2 else MAX_CUBE_BASE)):
                return False
        else:
            if not (ok(n.l) and ok(n.r)):
                return False
            a, b = _eval(n.l, rule), _eval(n.r, rule)
            la, lb = lit(n.l), lit(n.r)
            if n.op == DIV:
                if b == 0 or (a / b).denominator != 1:
                    return False
                if not (2 <= abs(b) <= MAX_FACTOR and 2 <= abs(a / b) <= MAX_FACTOR):
                    return False
                if la is not None and abs(la) > dividend_hi:
                    return False
            else:
                if n.op == MUL and (abs(a) > MAX_FACTOR or abs(b) > MAX_FACTOR or 0 in (a, b)):
                    return False
                if la is not None and not lo <= abs(la) <= hi:
                    return False
            if lb is not None and not lo <= abs(lb) <= hi:
                return False
        return abs(_eval(n, rule)) <= MAX_VALUE

    try:
        return ok(parse(text, rule))
    except (Invalid, ZeroDivisionError):
        return False


def _has_neg_literal(node) -> bool:
    if isinstance(node, int):
        return node < 0
    if isinstance(node, (Neg, Pow)):
        return True
    return _has_neg_literal(node.l) or _has_neg_literal(node.r)


def has_zero_intermediate(text: str) -> bool:
    """True when any non-leaf node of the displayed expression (root included) is 0 under the
    correct rule."""
    rule = RULES["CORRECT"]

    def walk(n) -> bool:
        if isinstance(n, int) or (isinstance(n, Neg) and isinstance(n.x, int)):
            return False  # a literal (parsed negatives are Neg(int))
        if _eval(n, rule) == 0:
            return True
        if isinstance(n, Bin):
            return walk(n.l) or walk(n.r)
        if isinstance(n, Neg):
            return walk(n.x)
        return walk(n.base)

    try:
        return walk(parse(text, rule))
    except (Invalid, ZeroDivisionError):
        return True


def _t45(rng, n_ops_choices, power_kind):
    """power_kind: None, 'neg' (−a^n, leading) or 'paren' ((−a)^n anywhere)."""
    n_ops = rng.choice(n_ops_choices)
    bin_ops = n_ops - (1 if power_kind else 0)
    shape = _shape(rng, bin_ops)
    n_leaves = _leaves(shape)
    if power_kind == "neg":
        power_leaf = 0  # the leftmost leaf is never preceded by an operator
    elif power_kind == "paren":
        power_leaf = rng.randrange(n_leaves)
    else:
        power_leaf = -1
    try:
        tree = _fill(rng, shape, [0], power_leaf, power_kind)
        text = render(tree)
    except (_Retry, ValueError):
        return None
    if not _has_neg_literal(tree):
        return None
    c = evaluate(text)
    if c is None or has_zero_intermediate(text):
        return None
    try:
        steps = trace(text)
    except (Invalid, ZeroDivisionError):
        return None
    if not power_kind and evaluate(text, "ORDER") in (None, c):
        return None  # precedence must matter
    return text, ", then ".join(steps) + "."


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def gen_tier(tier: int, count: int, declared, rng: random.Random, max_attempts: int = 200000):
    positions = _balanced(count, 4, rng)
    if tier == 1:
        kinds = _balanced(count, 3, rng)  # 1/3 both negative, 2/3 mixed sign
    elif tier == 2:
        kinds = _balanced(count, 5, rng)  # 3/5 subtract a negative, 1/5 neg − pos, 1/5 crosses 0
    elif tier == 3:
        kinds = _balanced(count, 2, rng)  # half ×, half ÷
    elif tier == 4:
        kinds = [None] * count
    else:  # 12 of each power form, the rest without powers
        kinds = ["neg"] * 12 + ["paren"] * 12 + [None] * (count - 24)
        rng.shuffle(kinds)
    items, prompts = [], set()
    attempts = 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        kind = kinds[len(items)]
        if tier == 1:
            got = _t1(rng, kind)
        elif tier == 2:
            got = _t2(rng, kind)
        elif tier == 3:
            got = _t3(rng, kind)
        elif tier == 4:
            got = _t45(rng, (2, 3), None)
        else:
            got = _t45(rng, (3, 4), kind)
        if got is None:
            continue
        text, expl = got
        if text in prompts or not _steps_ok(text, tier):
            continue
        item = make_item(text, tier, declared, positions[len(items)], rng, expl)
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
