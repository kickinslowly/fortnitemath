"""decimal-ops cartridge: golden misconception values, an independent re-check of every baked answer,
the manifest's §4b bounds walked on baked.json, and value-distinct choices.

The independent checks parse the prompt text here with regexes and compute with ``fractions.Fraction``
built from the decimal strings -- never with the generator's evaluator or its number helpers.
"""
import json
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, bake_bytes, load_generator

CID = "decimal-ops"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]

NUM = r"\d+(?:\.\d+)?"
BARE_RE = re.compile(rf"^({NUM}) ([+−×÷]) ({NUM})$")
MONEY_RE = re.compile(rf"^[A-Z][a-z]+ cost \$(\d+\.\d\d) each\. How many for \$(\d+\.\d\d)\?$")
LENGTH_RE = re.compile(rf"^Cut ({NUM}) m of [a-z]+ into ({NUM}) m pieces\. How many\?$")


def parse_prompt(prompt):
    """(a_text, op, b_text, kind) read straight from the display text."""
    m = BARE_RE.match(prompt)
    if m:
        return m.group(1), m.group(2), m.group(3), "bare"
    m = MONEY_RE.match(prompt)
    if m:
        return m.group(2), "÷", m.group(1), "money"  # total ÷ price
    m = LENGTH_RE.match(prompt)
    if m:
        return m.group(1), "÷", m.group(2), "length"
    raise AssertionError(f"unparsed prompt {prompt!r}")


def compute(a, op, b):
    a, b = Fraction(a), Fraction(b)
    if op == "+":
        return a + b
    if op == "−":
        return a - b
    if op == "×":
        return a * b
    return a / b


def dec_places(text):
    return len(text.split(".")[1]) if "." in text else 0


def choice_value(c):
    assert re.fullmatch(NUM, c), f"choice {c!r} is not a plain decimal"
    assert not (("." in c) and c.endswith("0")), f"trailing zero in {c!r}"
    assert not (len(c) > 1 and c.startswith("0") and not c.startswith("0.")), c
    return Fraction(c)


# ---------------------------------------------------------------------------------------------
# Golden cases: every misconception key on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
F = Fraction
GOLDEN = [
    # tier, a, op, b, correct, {label: wrong value}
    (1, "0.4", "+", "0.35", "0.75", {"ALIGN_RIGHT": "0.39", "DROP_PLACE": "0.7"}),
    (1, "3", "+", "0.4", "3.4", {"ALIGN_RIGHT": "0.7"}),
    (1, "4.5", "−", "2", "2.5", {"ALIGN_RIGHT": "4.3"}),
    (1, "0.75", "−", "0.3", "0.45", {"ALIGN_RIGHT": "0.72", "DROP_PLACE": "0.4"}),
    (1, "0.6", "−", "0.25", "0.35", {"BRING_DOWN": "0.45", "DROP_PLACE": "0.4"}),
    (1, "3", "−", "0.4", "2.6", {"BRING_DOWN": "3.4"}),
    (1, "0.8", "+", "0.5", "1.3", {"DECIMAL_AS_WHOLE": "0.13"}),
    (1, "1.6", "+", "0.7", "2.3", {"DECIMAL_AS_WHOLE": "1.13"}),
    (2, "0.3", "×", "4", "1.2", {"PLACE_LOST": "12", "EXTRA_PLACE": "0.12"}),
    (2, "0.04", "×", "6", "0.24", {"PLACE_LOST": "24", "EXTRA_PLACE": "0.024",
                                   "MISSED_PLACE": "2.4"}),
    (2, "5", "×", "0.4", "2", {"PLACE_LOST": "20", "EXTRA_PLACE": "0.2"}),
    (3, "0.6", "×", "0.2", "0.12", {"COUNT_PLACES": "1.2", "TOO_MANY_PLACES": "0.012",
                                    "PLACE_LOST": "12"}),
    (3, "0.3", "×", "0.02", "0.006", {"COUNT_PLACES": "0.06", "TOO_MANY_PLACES": "0.0006",
                                      "PLACE_LOST": "6"}),
    (4, "2.4", "÷", "3", "0.8", {"PLACE_LOST": "8", "EXTRA_PLACE": "0.08"}),
    (4, "0.24", "÷", "3", "0.08", {"PLACE_LOST": "8", "EXTRA_PLACE": "0.008",
                                   "MISSED_PLACE": "0.8"}),
    (4, "4", "÷", "5", "0.8", {"BIG_INTO_SMALL": "1.25", "PLACE_LOST": "8"}),
    (5, "1.2", "÷", "0.3", "4", {"SHIFT_ONE_SIDE": {"0.4", "40"}, "MULT_FOR_DIV": "0.36"}),
    (5, "2", "÷", "0.5", "4", {"SHIFT_ONE_SIDE": {"0.4", "40"}, "MULT_FOR_DIV": "1"}),
    (5, "0.12", "÷", "0.03", "4", {"SHIFT_ONE_SIDE": {"0.04", "400"}}),
]


def values_by_label(pairs):
    out = {}
    for lab, v in pairs:
        out.setdefault(lab, set()).add(v)
    return out


@pytest.mark.parametrize("tier,a,op,b,correct,wrong", GOLDEN,
                         ids=[f"t{g[0]} {g[1]} {g[2]} {g[3]}" for g in GOLDEN])
def test_golden_misconception_values(tier, a, op, b, correct, wrong):
    gop = {"+": G.ADD, "−": G.SUB, "×": G.MUL, "÷": G.DIV}[op]
    fa, fb = F(a), F(b)
    assert G.correct_value(fa, gop, fb) == F(correct)
    got = values_by_label(G.misconception_values(fa, gop, fb, tier))
    for label, v in wrong.items():
        want = {F(x) for x in v} if isinstance(v, set) else {F(v)}
        assert got.get(label) == want, (label, got)


def test_golden_covers_every_declared_key():
    used = {lab for g in GOLDEN for lab in g[5]}
    assert used == set(BAKED["misconceptions"])


def test_money_shift_uses_the_shown_two_places():
    # $4.20 ÷ $0.60: a student moving only one point sees 4.20 ÷ 60 or 420 ÷ 0.60
    got = values_by_label(G.misconception_values(F("4.2"), G.DIV, F("0.6"), 5,
                                                 {"story": True, "money": True}))
    assert got == {"SHIFT_ONE_SIDE": {F("0.07"), F(700)}}


@pytest.mark.parametrize("tier,a,op,b,label", [
    (1, "0.4", "+", "0.3", "ALIGN_RIGHT"),       # same places: right-aligning is correct
    (1, "0.4", "+", "0.3", "DECIMAL_AS_WHOLE"),  # no carry
    (1, "0.75", "−", "0.3", "BRING_DOWN"),       # top number is the longer one
    (1, "3", "+", "0.4", "DROP_PLACE"),          # a whole number has no place to drop
    (4, "6", "÷", "2", "BIG_INTO_SMALL"),        # dividend is the bigger number
    (5, "1.2", "÷", "0.3", "BIG_INTO_SMALL"),    # not in tier 5's rules
])
def test_rule_does_not_fire_where_it_does_not_apply(tier, a, op, b, label):
    gop = {"+": G.ADD, "−": G.SUB, "×": G.MUL, "÷": G.DIV}[op]
    assert label not in dict(G.misconception_values(F(a), gop, F(b), tier))


# ---------------------------------------------------------------------------------------------
# Independent answer check of every baked item
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    a, op, b, kind = parse_prompt(item["prompt"])
    value = compute(a, op, b)
    assert value > 0
    assert choice_value(item["choices"][item["answer"]]) == value
    ans = re.escape(item["choices"][item["answer"]])
    assert re.search(rf"(=|[Ss]o) {ans}( pieces)?\.$", item["explanation"]), item["explanation"]
    if kind != "bare":
        assert item["tier"] == 5 and value.denominator == 1  # stories count whole things


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(item):
    vals = [choice_value(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert all(0 < v <= 999 for v in vals)
    assert len(item["choices"]) == 4


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    a, op, b, kind = parse_prompt(item["prompt"])
    gop = {"+": G.ADD, "−": G.SUB, "×": G.MUL, "÷": G.DIV}[op]
    ctx = {"story": kind != "bare", "money": kind == "money"}
    produced = G.misconception_values(Fraction(a), gop, Fraction(b), item["tier"], ctx)
    assert produced, "needs at least one misconception distractor"
    pv = {v: lab for lab, v in produced}
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        v = Fraction(c)
        if m == "ARITH":
            assert v not in pv, f"ARITH {c} is really {pv.get(v)}"
        else:
            assert pv.get(v) == m, (c, m, pv)


def test_arith_share():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.25
    for t in (2, 3, 4, 5):
        ct = Counter(m for it in ITEMS if it["tier"] == t for m in it["misconceptions"] if m)
        assert ct["ARITH"] / sum(ct.values()) <= 0.25, t


def test_tier_shapes():
    for it in ITEMS:
        a, op, b, kind = parse_prompt(it["prompt"])
        t = it["tier"]
        assert op in {1: "+−", 2: "×", 3: "×", 4: "÷", 5: "÷"}[t], it["prompt"]
        if t == 1:
            assert dec_places(a) != dec_places(b) or "DECIMAL_AS_WHOLE" in it["misconceptions"]
        if t == 2:
            assert (dec_places(a) == 0) != (dec_places(b) == 0)
        if t == 3:
            assert dec_places(a) and dec_places(b)
        if t == 4:
            assert dec_places(b) == 0
        if t == 5:
            assert dec_places(b) > 0
    stories = [it for it in ITEMS if not BARE_RE.match(it["prompt"])]
    assert len(stories) >= 12


# ---------------------------------------------------------------------------------------------
# §4b bounds (the manifest's "bounds" string), walked independently on baked.json
# ---------------------------------------------------------------------------------------------
def column_carries(a, b, op):
    x, y = int(Fraction(a) * 100), int(Fraction(b) * 100)
    n = c = 0
    while x or y:
        dx, dy = x % 10, y % 10
        c = int(dx + dy + c >= 10) if op == "+" else int(dx - dy - c < 0)
        n += c
        x, y = x // 10, y // 10
    return n


def min_places(text):
    """Places of the VALUE (trailing zeros dropped): "0.60" -> 1."""
    return len(text.split(".")[1].rstrip("0")) if "." in text else 0


def digit_int(text):
    """Digits of the value with the point removed: "0.60" -> 6, "4.5" -> 45."""
    return int(Fraction(text) * 10 ** min_places(text))


def bounds_violations(prompt):
    a, op, b, kind = parse_prompt(prompt)
    bad = []
    for t in (a, b):
        v = Fraction(t)
        if not Fraction(1, 100) <= v <= 10:
            bad.append(f"operand {t} outside 0.01..10")
        p = len(t.split(".")[1].rstrip("0")) if "." in t else 0
        if p > 2:
            bad.append(f"operand {t} has {p} places")
        if sum(ch not in "0." for ch in t) > 2:
            bad.append(f"operand {t} has more than 2 non-zero digits")
    c = compute(a, op, b)
    if op in "+−":
        if not 0 < c <= 20:
            bad.append(f"answer {c} outside 0..20")
        if column_carries(a, b, op) > 1:
            bad.append("more than one carry/borrow")
        return bad
    if op == "×":
        da, db = digit_int(a), digit_int(b)
        if not (2 <= da <= 10 and 2 <= db <= 10):
            bad.append(f"digit work {da} × {db} is not a times-table fact")
        if (c * 1000).denominator != 1:
            bad.append(f"answer {c} has more than 3 places")
        return bad
    # ÷: the answer's digits times the divisor's digits rebuild the dividend's digits
    k = 0
    while (c * 10 ** k).denominator != 1:
        k += 1
        if k > 3:
            bad.append(f"answer {c} not exact in 3 places")
            return bad
    q = int(c * 10 ** k)
    d = digit_int(b)
    if not (2 <= d <= 10 and 2 <= q <= 10):
        bad.append(f"digit work ÷ {d} = {q} outside 2..10")
    if Fraction(a) * 10 ** (k + min_places(b)) != d * q:
        bad.append("dividend is not divisor × quotient in digits")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]
    for s in item["choices"]:
        assert len(s) <= 14


@pytest.mark.parametrize("prompt,expect_bad", [
    ("0.4 + 0.35", False),
    ("1.23 + 2", True),          # three non-zero digits
    ("0.8 + 0.35", False),       # one carry
    ("3 − 0.25", True),          # two borrows
    ("12 + 0.5", True),          # operand over 10
    ("0.25 × 4", True),          # 25 × 4 is not a times-table fact
    ("0.6 × 0.2", False),
    ("1.2 × 3", True),           # 12 × 3
    ("0.7 ÷ 7", True),           # digit quotient 1
    ("4.8 ÷ 6", False),
    ("4.8 ÷ 4", True),           # 48 ÷ 4 = 12
    ("1 ÷ 3", True),             # not exact
    ("1.2 ÷ 0.3", False),
    ("Pens cost $0.60 each. How many for $4.20?", False),
    ("Pens cost $1.50 each. How many for $6.00?", True),  # 60 ÷ 15: divisor digits 15
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, prompt


def test_generator_gate_agrees_with_checker():
    for prompt, bad in [("0.25 × 4", True), ("0.6 × 0.2", False), ("4.8 ÷ 4", True),
                        ("3 − 0.25", True), ("0.8 + 0.35", False)]:
        a, op, b, _ = parse_prompt(prompt)
        gop = {"+": G.ADD, "−": G.SUB, "×": G.MUL, "÷": G.DIV}[op]
        assert G.bounds_ok(Fraction(a), gop, Fraction(b)) != bad, prompt


def test_manifest_states_bounds():
    assert "§4b" in BAKED["bounds"]


def test_bake_is_deterministic():
    data = bake_bytes(CID)
    assert data == bake_bytes(CID)
    assert data == (REPO_ROOT / "cartridges" / CID / "baked.json").read_bytes()
