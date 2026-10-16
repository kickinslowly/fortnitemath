"""scientific-notation cartridge: golden misconception cases, an independent re-check of every baked
answer (own regexes + Fraction / Decimal, never the generator's solver), the §4b bounds on baked.json,
exact-value uniqueness of every item's choices, and a bounds-checker disproof.
"""
import json
import re
from collections import Counter
from decimal import Decimal
from fractions import Fraction as F

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "scientific-notation"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
M = "−"  # U+2212


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Golden cases: prompt -> right answer and the text each misconception writes (hand-worked)
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # tier 1
    ("10^4 = ?", "10,000", {"ZEROS_PLUS_ONE": "100,000", "TIMES_FOR_POWER": "40", "DIGITS_SIDE_BY_SIDE": "104"}),
    ("10^0 = ?", "1", {"ZERO_IS_ZERO": "0", "ZERO_KEEPS_BASE": "10"}),
    ("10^−3 = ?", "0.001", {"NEG_IS_NEGATIVE": "−1,000", "NEG_IGNORED": "1,000", "DECIMAL_SLIP": "0.0001"}),
    ("1,000,000 is 10 to what power?", "6", {"ZEROS_PLUS_ONE": "7"}),
    ("0.001 is 10 to what power?", "−3", {"SIGN_DROPPED": "3", "DECIMAL_SLIP": "−2"}),
    ("Which power of 10 equals 0.01?", "10^−2", {"SIGN_DROPPED": "10^2", "DECIMAL_SLIP": "10^−1"}),
    ("Which power of 10 equals 100,000?", "10^5", {"ZEROS_PLUS_ONE": "10^6"}),
    # tier 2
    ("Write 4,000,000 in scientific notation.", "4 × 10^6",
     {"COUNTED_ALL_DIGITS": "4 × 10^7", "SIGN_FLIP": "4 × 10^−6"}),
    ("Write 0.0005 in scientific notation.", "5 × 10^−4", {"SIGN_FLIP": "5 × 10^4", "COUNTED_ZEROS": "5 × 10^−3"}),
    ("Write 32,000 in scientific notation.", "3.2 × 10^4",
     {"COUNTED_ALL_DIGITS": "3.2 × 10^5", "SIGN_FLIP": "3.2 × 10^−4", "COUNTED_ZEROS": "3.2 × 10^3"}),
    ("Write 0.0032 in scientific notation.", "3.2 × 10^−3",
     {"COUNTED_ALL_DIGITS": "3.2 × 10^−4", "SIGN_FLIP": "3.2 × 10^3", "COUNTED_ZEROS": "3.2 × 10^−2"}),
    ("45,000 = 4.5 × 10^?", "4", {"COUNTED_ALL_DIGITS": "5", "SIGN_FLIP": "−4", "COUNTED_ZEROS": "3"}),
    # tier 3
    ("6 × 10^5 in standard form?", "600,000",
     {"EXTRA_ZERO": "6,000,000", "DECIMAL_SLIP": "60,000", "SIGN_FLIP": "0.00006"}),
    ("3 × 10^−4 in standard form?", "0.0003",
     {"EXTRA_ZERO": "0.00003", "DECIMAL_SLIP": "0.003", "SIGN_FLIP": "30,000"}),
    ("Standard form of 2.5 × 10^3?", "2,500",
     {"APPENDED_ZEROS": "2.5000", "EXTRA_ZERO": "25,000", "DECIMAL_SLIP": "250", "SIGN_FLIP": "0.0025"}),
    ("A calculator shows 4.2E6. Value?", "4,200,000",
     {"APPENDED_ZEROS": "4.2000000", "EXTRA_ZERO": "42,000,000", "DECIMAL_SLIP": "420,000",
      "SIGN_FLIP": "0.0000042"}),
    # tier 4
    ("3 × 10^8 is how many times 3 × 10^6?", "100",
     {"EXPONENT_DIFF": "2", "DIVIDED_WRONG_WAY": "1/100", "ONE_ZERO_OFF": "1,000"}),
    ("8 × 10^7 is how many times 2 × 10^7?", "4",
     {"SUBTRACTED": "6", "DIVIDED_WRONG_WAY": "1/4", "MULTIPLIED_COEFS": "16"}),
    ("6 × 10^8 is how many times 2 × 10^6?", "300",
     {"EXPONENT_DIFF": "2", "COEF_RATIO_ONLY": "3", "DIVIDED_WRONG_WAY": "1/300"}),
    ("Larger: 2 × 10^5 or 9 × 10^4?", "2 × 10^5", {"COEF_FIRST": "9 × 10^4"}),
    ("Smaller: 7 × 10^1 or 2 × 10^2?", "7 × 10^1", {"COEF_FIRST": "2 × 10^2"}),
    ("Larger: 3 × 10^−2 or 8 × 10^−4?", "3 × 10^−2", {"NEG_EXP_BIGGER": "8 × 10^−4"}),
    # tier 5
    ("(2 × 10^3) × (4 × 10^5)", "8 × 10^8",
     {"MULT_EXPONENTS": "8 × 10^15", "ADD_COEFS": "6 × 10^8", "EXPONENTS_SUBTRACTED": "8 × 10^−2"}),
    ("(5 × 10^4) × (4 × 10^2)", "2 × 10^7",
     {"MULT_EXPONENTS": "2 × 10^9", "ADD_COEFS": "9 × 10^6", "NO_CARRY": "2 × 10^6",
      "EXPONENTS_SUBTRACTED": "2 × 10^3"}),
    ("(6 × 10^9) ÷ (2 × 10^3)", "3 × 10^6",
     {"ADD_EXPONENTS": "3 × 10^12", "DIVIDE_EXPONENTS": "3 × 10^3", "SUB_COEFS": "4 × 10^6",
      "FLIPPED_EXPONENTS": "3 × 10^−6"}),
    ("(2 × 10^5) ÷ (4 × 10^2)", "5 × 10^2",
     {"ADD_EXPONENTS": "5 × 10^6", "FLIPPED_EXPONENTS": "5 × 10^−4", "NO_CARRY": "5 × 10^3"}),
    ("(3 × 10^4) + (2 × 10^4)", "5 × 10^4",
     {"ADD_EXPONENTS_ON_SUM": "5 × 10^8", "MULT_FOR_ADD": "6 × 10^4"}),
    ("(7 × 10^4) + (5 × 10^4)", "1.2 × 10^5",
     {"ADD_EXPONENTS_ON_SUM": "1.2 × 10^9", "MULT_FOR_ADD": "3.5 × 10^5", "NO_CARRY": "1.2 × 10^4"}),
    ("(3 × 10^4) + (2 × 10^3)", "3.2 × 10^4",
     {"IGNORE_GAP": "5 × 10^4", "KEPT_SMALLER_POWER": "5 × 10^3", "ADD_EXPONENTS_ON_SUM": "5 × 10^7"}),
    ("(2 × 10^3) + (3 × 10^4)", "3.2 × 10^4",
     {"IGNORE_GAP": "5 × 10^4", "KEPT_SMALLER_POWER": "5 × 10^3", "ADD_EXPONENTS_ON_SUM": "5 × 10^7"}),
]


@pytest.mark.parametrize("prompt,right,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_misconception_values(prompt, right, wrong):
    a = G.analyze(prompt)
    assert a.ctext == right
    got = a.wrong_texts()
    for label, text in wrong.items():
        assert got.get(label) == text, (label, got)


def test_form_family_golden():
    a = G.form_analysis("Which is in scientific notation?", F("3.5"), 4)
    assert a.ctext == "3.5 × 10^4"
    w = {lab: t for lab, t, _ in a.cands}
    assert w == {"COEF_NOT_1_TO_10": "35 × 10^4", "COEF_BELOW_1": "0.35 × 10^4",
                 "ADDED_NOT_TIMES": "3.5 + 10^4", "BASE_EXP_SWAP": "3.5 × 4^10"}


def test_compare_family_golden():
    a = G.compare_analysis(True, F(6), 4, F(2), 5, (F(9), 3), (F(7), 2), (F(4), 4))
    assert a.prompt == "Which is greater than 6 × 10^4?" and a.ctext == "2 × 10^5"
    assert [t for _, t, _ in a.cands] == ["9 × 10^3", "7 × 10^2"] and a.fill[0][0] == "4 × 10^4"


@pytest.mark.parametrize("prompt", [g[0] for g in GOLDEN])
def test_every_golden_label_is_declared(prompt):
    for lab in G.analyze(prompt).wrong_texts():
        assert lab in BAKED["misconceptions"], lab


# ---------------------------------------------------------------------------------------------
# Independent answer check: own regexes, Decimal and Fraction
# ---------------------------------------------------------------------------------------------
SCI_RX = re.compile(r"^(\d+(?:\.\d+)?) × 10\^(−?\d+)$")


def ex(s):
    return int(s.replace(M, "-"))


def std_text(d: Decimal) -> str:
    s = format(d, "f")
    return f"{int(s):,}" if "." not in s else s


def sci_text_of(x: str) -> str:
    """Scientific notation of a written-out number, via Decimal digits (not the generator)."""
    sign, digits, exp = Decimal(x.replace(",", "")).normalize().as_tuple()
    e = exp + len(digits) - 1
    ds = "".join(map(str, digits))
    coef = ds[0] + ("." + ds[1:] if len(ds) > 1 else "")
    return f"{coef} × 10^{str(e).replace('-', M)}"


def power_of(x: str) -> int:
    d = Decimal(x.replace(",", "")).normalize()
    sign, digits, exp = d.as_tuple()
    assert digits == (1,), x
    return exp


def fval(s: str) -> F:
    """Exact value of a choice text (own parser)."""
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?) × (\d+)\^(−?\d+)", s)
    if m:
        return F(m.group(1)) * F(int(m.group(2))) ** ex(m.group(3))
    m = re.fullmatch(r"(\d+(?:\.\d+)?) \+ 10\^(−?\d+)", s)
    if m:
        return F(m.group(1)) + F(10) ** ex(m.group(2))
    m = re.fullmatch(r"10\^(−?\d+)", s)
    if m:
        return F(10) ** ex(m.group(1))
    m = re.fullmatch(r"(\d+)/([\d,]+)", s)
    if m:
        return F(int(m.group(1)), int(m.group(2).replace(",", "")))
    return F(s.replace(M, "-").replace(",", ""))


def expected_correct(prompt):
    """The right choice text, from the prompt alone (None for families checked on their choices)."""
    m = re.fullmatch(r"(?:10\^(−?\d+) = \?|Which equals 10\^(−?\d+)\?|Standard form of 10\^(−?\d+)\?)", prompt)
    if m:
        n = ex(next(g for g in m.groups() if g))
        return std_text(Decimal(1).scaleb(n))
    m = re.fullmatch(r"(.+) is 10 to what power\?", prompt)
    if m:
        return str(power_of(m.group(1))).replace("-", M)
    m = re.fullmatch(r"Which power of 10 equals (.+)\?", prompt)
    if m:
        return "10^" + str(power_of(m.group(1))).replace("-", M)
    m = re.fullmatch(r"Write (.+) in scientific notation\.", prompt)
    if m:
        return sci_text_of(m.group(1))
    m = re.fullmatch(r"(.+) = (\d+(?:\.\d+)?) × 10\^\?", prompt)
    if m:
        t = sci_text_of(m.group(1))
        assert t.startswith(m.group(2) + " × 10^"), (prompt, t)
        return t.split("^")[1]
    for rx in (r"(\d+(?:\.\d+)?) × 10\^(−?\d+) in standard form\?",
               r"Standard form of (\d+(?:\.\d+)?) × 10\^(−?\d+)\?",
               r"Which equals (\d+(?:\.\d+)?) × 10\^(−?\d+)\?",
               r"(?:A calculator shows|Calculator screen:) (\d+(?:\.\d+)?)E(−?\d+)\. Value\?"):
        m = re.fullmatch(rx, prompt)
        if m:
            return std_text(Decimal(m.group(1)).scaleb(ex(m.group(2))))
    m = re.fullmatch(r"(\d+(?:\.\d+)?) × 10\^(−?\d+) is how many times (\d+(?:\.\d+)?) × 10\^(−?\d+)\?", prompt)
    if m:
        r = F(m.group(1)) * F(10) ** ex(m.group(2)) / (F(m.group(3)) * F(10) ** ex(m.group(4)))
        assert r.denominator == 1
        return f"{int(r):,}"
    m = re.fullmatch(r"(Larger|Smaller): (\d+(?:\.\d+)?) × 10\^(−?\d+) or (\d+(?:\.\d+)?) × 10\^(−?\d+)\?", prompt)
    if m:
        x = (F(m.group(2)) * F(10) ** ex(m.group(3)), f"{m.group(2)} × 10^{m.group(3)}")
        y = (F(m.group(4)) * F(10) ** ex(m.group(5)), f"{m.group(4)} × 10^{m.group(5)}")
        return (max if m.group(1) == "Larger" else min)(x, y)[1]
    return None


OPS_RX = re.compile(r"\((\d) × 10\^(−?\d+)\) ([×÷+]) \((\d) × 10\^(−?\d+)\)")


def ops_value(prompt):
    m = OPS_RX.fullmatch(prompt)
    if not m:
        return None
    a, e1, op, b, e2 = F(m.group(1)), ex(m.group(2)), m.group(3), F(m.group(4)), ex(m.group(5))
    x, y = a * F(10) ** e1, b * F(10) ** e2
    return {"×": x * y, "÷": x / y, "+": x + y}[op]


def is_standard(text):
    m = SCI_RX.match(text)
    if not m:
        return False
    c = F(m.group(1))
    return 1 <= c < 10 and not (("." in m.group(1)) and m.group(1).endswith("0"))


STRUCTURAL = re.compile(r"Which (?:is|number is|one is) in scientific notation\?|Which is (?:greater|less) than .+\?")


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_answer_independent(item):
    p, choices, ans = item["prompt"], item["choices"], item["answer"]
    exp = expected_correct(p)
    if exp is not None:
        assert choices[ans] == exp, (p, choices[ans], exp)
        return
    v = ops_value(p)
    if v is not None:  # tier 5: the right choice is the normalised form of the exact value
        assert is_standard(choices[ans]), choices[ans]
        assert fval(choices[ans]) == v, (p, choices[ans])
        return
    m = re.fullmatch(r"Which is (greater|less) than (\d+(?:\.\d+)?) × 10\^(−?\d+)\?", p)
    if m:
        t = F(m.group(2)) * F(10) ** ex(m.group(3))
        ok = [i for i, c in enumerate(choices) if (fval(c) > t if m.group(1) == "greater" else fval(c) < t)]
        assert ok == [ans], (p, choices)
        return
    assert STRUCTURAL.fullmatch(p), p  # "Which is in scientific notation?": exactly one choice is in the form
    ok = [i for i, c in enumerate(choices) if is_standard(c)]
    assert ok == [ans], (p, choices)


def test_every_family_is_covered():
    kinds = Counter()
    for it in ITEMS:
        p = it["prompt"]
        if expected_correct(p) is not None:
            kinds["text"] += 1
        elif ops_value(p) is not None:
            kinds["ops"] += 1
        else:
            kinds["structural"] += 1
    assert kinds["text"] > 120 and kinds["ops"] == 40 and kinds["structural"] >= 9


# ---------------------------------------------------------------------------------------------
# Choices: no two equal in VALUE; word and form choices have exactly one true
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_choice_values_all_different(item):
    vals = [fval(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), (item["prompt"], item["choices"])
    assert 2 <= len(item["choices"]) <= 4


def test_value_checker_sees_equal_values():
    # the disproof for the check above: these pairs differ in text but are the same number
    assert fval("20 × 10^6") == fval("2 × 10^7")
    assert fval("0.5 × 10^3") == fval("5 × 10^2")
    assert fval("1/1,000") == fval("1/1000")
    assert fval("10^−3") == fval("0.001")


# ---------------------------------------------------------------------------------------------
# Labels are honest
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_labels_are_produced_by_their_rule(item):
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs a modelled misconception"
    try:
        a = G.analyze(item["prompt"])
    except ValueError:
        return  # structural families: checked below
    modelled = {(lab, fval(t)) for lab, t, _ in a.cands}
    modelled_vals = {v for _, v in modelled}
    for c, lab in zip(item["choices"], item["misconceptions"]):
        if lab is None:
            continue
        if lab == "ARITH":
            assert fval(c) not in modelled_vals, f"ARITH {c} is really a modelled wrong value"
        else:
            assert (lab, fval(c)) in modelled, (item["prompt"], lab, c)


def test_structural_labels():
    for it in ITEMS:
        if not STRUCTURAL.fullmatch(it["prompt"]):
            continue
        labs = {m for m in it["misconceptions"] if m}
        if "scientific" in it["prompt"]:
            assert labs <= {"COEF_NOT_1_TO_10", "COEF_BELOW_1", "ADDED_NOT_TIMES", "BASE_EXP_SWAP"}
        else:
            assert labs <= {"COEF_FIRST", "ARITH"}


def test_pair_items_label_matches_the_comparison():
    for it in ITEMS:
        m = re.fullmatch(r"(Larger|Smaller): (\d) × 10\^(−?\d+) or (\d) × 10\^(−?\d+)\?", it["prompt"])
        if not m:
            continue
        assert len(it["choices"]) == 2
        # the wrong door always has the more extreme coefficient: that is what makes the slip tempting
        wrong = it["choices"][1 - it["answer"]]
        right = it["choices"][it["answer"]]
        cw, cr = int(wrong[0]), int(right[0])
        assert (cw > cr) if m.group(1) == "Larger" else (cw < cr), it["prompt"]
        both_neg = ex(m.group(3)) < 0 and ex(m.group(5)) < 0
        lab = it["misconceptions"][1 - it["answer"]]
        assert lab == ("NEG_EXP_BIGGER" if both_neg else "COEF_FIRST")


def test_arith_share_at_most_half():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.5


def test_declared_misconceptions_are_all_used_and_short():
    used = {m for it in ITEMS for m in it["misconceptions"] if m} - {"ARITH"}
    declared = set(BAKED["misconceptions"])
    assert used <= declared
    assert declared - used == set(), f"declared but never used: {declared - used}"
    for k, v in BAKED["misconceptions"].items():
        assert v["student"] and v["teacher"] and len(v["student"]) <= 80, k


def test_display_strings_use_only_the_allowed_characters():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert re.fullmatch(r"[ -~×÷−]*", s), s


def test_exponents_use_the_unicode_minus_after_the_caret():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert not re.search(r"\^-|\^\(", s), s


def test_tier_shapes():
    t1 = by_tier(1)
    assert sum("what power" in it["prompt"] for it in t1) >= 10
    assert sum("Which power of 10" in it["prompt"] for it in t1) >= 10
    assert any(it["prompt"].startswith("10^") or "Standard form of 10^" in it["prompt"] for it in t1)
    t2 = by_tier(2)
    assert sum(it["prompt"].startswith("Write") for it in t2) >= 28
    assert sum("× 10^?" in it["prompt"] for it in t2) >= 5
    t3 = by_tier(3)
    assert sum(bool(re.search(r"\dE", it["prompt"])) for it in t3) >= 6
    assert sum(M in it["prompt"] for it in t3) >= 12 and sum(M not in it["prompt"] for it in t3) >= 12
    t4 = by_tier(4)
    assert sum("how many times" in it["prompt"] for it in t4) >= 18
    assert sum(it["prompt"].startswith(("Larger", "Smaller")) for it in t4) >= 10
    assert sum(it["prompt"].startswith("Which is") for it in t4) >= 5
    t5 = by_tier(5)
    ops = Counter(OPS_RX.fullmatch(it["prompt"]).group(3) for it in t5)
    assert ops["×"] >= 12 and ops["÷"] >= 12 and ops["+"] >= 10
    gap = [it for it in t5 if OPS_RX.fullmatch(it["prompt"]).group(3) == "+" and
           OPS_RX.fullmatch(it["prompt"]).group(2) != OPS_RX.fullmatch(it["prompt"]).group(5)]
    assert len(gap) >= 3
    carry = [it for it in t5 if OPS_RX.fullmatch(it["prompt"]).group(3) == "×" and
             int(OPS_RX.fullmatch(it["prompt"]).group(1)) * int(OPS_RX.fullmatch(it["prompt"]).group(4)) >= 10]
    assert len(carry) >= 6


# ---------------------------------------------------------------------------------------------
# PROTOCOL §4b bounds, walked on baked.json
# ---------------------------------------------------------------------------------------------
COEF = re.compile(r"^(?:[2-9]|[1-9]\.[1-9])$")
TERM = re.compile(r"(\d+(?:\.\d+)?) × 10\^(−?\d+)")


def coef_ok(c: str) -> bool:
    return bool(COEF.match(c)) and F(c) <= F(19, 2)


def times_fact(a: int, b: int) -> bool:
    return 2 <= a <= 9 and 2 <= b <= 9


def div_fact(a: int, b: int) -> bool:
    return (2 <= b <= 9 and a % b == 0 and 2 <= a // b <= 9) or (b == 2 * a and 2 <= a <= 4)


def bounds_violations(prompt: str, right: str) -> list:
    bad = []
    for c, e in TERM.findall(prompt):
        if not coef_ok(c):
            bad.append(f"coefficient {c} is not d or d.d up to 9.5")
        if abs(ex(e)) > 12:
            bad.append(f"exponent {e} over size 12")
    for c, e in re.findall(r"(\d+(?:\.\d+)?)E(−?\d+)", prompt):
        if not coef_ok(c) or abs(ex(e)) > 12:
            bad.append(f"calculator number {c}E{e}")
    for n in re.findall(r"10\^(−?\d+)(?: = \?|\?)", prompt):
        if abs(ex(n)) > 12:
            bad.append(f"power {n} over size 12")
    # written-out numbers in the prompt: <= 14 chars, a coefficient d or d.d, exponent <= 12
    wm = (re.fullmatch(r"Write (.+) in scientific notation\.", prompt) or
          re.fullmatch(r"(.+) = \d(?:\.\d)? × 10\^\?", prompt))
    if wm:
        x = wm.group(1)
        if len(x) > 14:
            bad.append(f"standard form {x} over 14 chars")
        t = TERM.fullmatch(sci_text_of(x))
        if not coef_ok(t.group(1)) or abs(ex(t.group(2))) > 12:
            bad.append(f"{x} is not a short coefficient times a power of 10")
    for rx in (r"(.+) is 10 to what power\?", r"Which power of 10 equals (.+)\?"):
        m = re.fullmatch(rx, prompt)
        if m and (len(m.group(1)) > 14 or abs(power_of(m.group(1))) > 12):
            bad.append(f"{m.group(1)} is too long")
    # the right answer
    m = SCI_RX.match(right)
    if m and (not 1 <= F(m.group(1)) <= F(19, 2) or abs(ex(m.group(2))) > 12):
        bad.append(f"answer {right} outside coefficient 1-9.5 / exponent 12")
    if not m and len(right) > 14:
        bad.append(f"answer {right} over 14 chars")
    # operations
    o = OPS_RX.fullmatch(prompt)
    if o:
        a, e1, op, b, e2 = int(o.group(1)), ex(o.group(2)), o.group(3), int(o.group(4)), ex(o.group(5))
        if op == "×" and not times_fact(a, b):
            bad.append(f"{a} × {b} is not a times-table fact")
        if op == "÷" and not div_fact(a, b):
            bad.append(f"{a} ÷ {b} is not a times-table division (or 2 ÷ 4)")
        if op == "+":
            if abs(e1 - e2) > 1:
                bad.append("+ joins exponents more than one apart")
            elif e1 != e2:
                hi, lo = (a, b) if e1 > e2 else (b, a)
                if F(hi) + F(lo, 10) > F(19, 2):
                    bad.append("gap sum passes 9.5")
    h = re.fullmatch(r"(\d+(?:\.\d+)?) × 10\^(−?\d+) is how many times (\d+(?:\.\d+)?) × 10\^(−?\d+)\?", prompt)
    if h:
        a, e1, b, e2 = F(h.group(1)), ex(h.group(2)), F(h.group(3)), ex(h.group(4))
        k, d = a / b, e1 - e2
        if k.denominator != 1 or d < 0:
            bad.append("how-many ratio is not a whole number")
        elif k == 1 and not 1 <= d <= 5:
            bad.append("power of 10 ratio over 10^5")
        elif k != 1 and not (2 <= k <= 4 and 0 <= d <= 3):
            bad.append("times-table multiple outside 2-4 x 10^0..3")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_concept_over_arithmetic_bounds(item):
    assert bounds_violations(item["prompt"], item["choices"][item["answer"]]) == [], item["prompt"]


@pytest.mark.parametrize("prompt,right,expect_bad", [
    ("(2 × 10^3) × (4 × 10^5)", "8 × 10^8", False),
    ("(2 × 10^3) × (12 × 10^5)", "2.4 × 10^9", True),        # coefficient 12 is not one digit
    ("(7 × 10^3) ÷ (2 × 10^2)", "3.5 × 10^1", True),         # 7 ÷ 2 is not a times-table fact
    ("(2 × 10^5) ÷ (4 × 10^2)", "5 × 10^2", False),          # 2 ÷ 4 = 0.5 is the allowed exception
    ("(2 × 10^3) + (4 × 10^6)", "4.002 × 10^6", True),       # exponents three apart
    ("(9 × 10^4) + (9 × 10^3)", "9.9 × 10^4", True),         # gap sum 9.9 passes 9.5
    ("(9 × 10^4) + (5 × 10^3)", "9.5 × 10^4", False),
    ("(3 × 10^20) × (2 × 10^2)", "6 × 10^22", True),         # exponent over 12
    ("Write 9.7 × 10^3 ...", "9.7 × 10^3", True),            # coefficient 9.7 over 9.5
    ("Write 0.0000000000008 in scientific notation.", "8 × 10^−13", True),
    ("Write 4,000,000 in scientific notation.", "4 × 10^6", False),
    ("5 × 10^13 in standard form?", "50,000,000,000,000", True),
    ("3 × 10^8 is how many times 3 × 10^1?", "10,000,000", True),   # ratio 10^7
    ("8 × 10^7 is how many times 2 × 10^7?", "4", False),
    ("9 × 10^7 is how many times 1.5 × 10^7?", "6", True),   # not a short ratio (and 1.5 is no times fact)
])
def test_bounds_checker_catches(prompt, right, expect_bad):
    assert bool(bounds_violations(prompt, right)) == expect_bad, prompt
