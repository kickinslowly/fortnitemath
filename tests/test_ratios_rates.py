"""ratios-rates cartridge: golden misconception values, an independent re-solve of every baked item,
choice-value uniqueness, and the manifest's bounds walked over every correct step of baked.json.

The independent solver below reads each prompt with its own number-extraction rules and computes with
``fractions.Fraction`` -- it never calls the generator's ``analyze``.
"""
import json
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "ratios-rates"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Golden cases: every catalog key, on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt, correct display, {label: wrong display}
    ("3 cats and 5 dogs. Ratio of dogs to cats?", "5:3",
     {"REVERSED": "3:5", "PART_TO_WHOLE": "5:8"}),
    ("3 cats and 5 dogs. Ratio of cats to all pets?", "3:8",
     {"PART_TO_PART": "3:5", "REVERSED": "8:3", "OTHER_PART": "5:8"}),
    ("8 pets: 3 are cats, the rest dogs. Ratio of dogs to cats?", "5:3",
     {"WHOLE_FOR_PART": "8:3", "REVERSED": "3:5", "PART_TO_WHOLE": "5:8"}),
    ("2:3 = ?:12", "8", {"ADDITIVE": "11", "WRONG_TERM": "48", "FACTOR_ONLY": "4"}),
    ("2:3 = 8:?", "12", {"ADDITIVE": "9", "WRONG_TERM": "32", "FACTOR_ONLY": "4"}),
    ("Paint: 2 red to 3 blue. Red for 12 blue?", "8", {"ADDITIVE": "11"}),
    ("6 pens cost $24. Cost per pen?", "$4", {"MULTIPLIED_RATE": "$144", "INVERTED": "$1/4"}),
    ("40 miles in 5 hours. Miles per hour?", "8", {"MULTIPLIED_RATE": "200", "INVERTED": "1/8"}),
    ("1 yd = 3 ft. 12 ft = ? yd", "4", {"MULTIPLIED_RATE": "36", "INVERTED": "1/4"}),
    ("1 yd = 3 ft. 4 yd = ? ft", "12", {"DIVIDED_RATE": "1 1/3", "ADDITIVE": "7"}),
    ("What is 25% of 40?", "10", {"PERCENT_AS_PART": "25", "SUBTRACTED": "15", "TENTH_FOR_ALL": "4"}),
    ("What is 75% of 40?", "30", {"ONE_PART": "10", "TENTH_FOR_ALL": "4"}),
    ("30% of 70 kids ride a bus. How many?", "21", {"TENTH_FOR_ALL": "7", "SUBTRACTED": "40"}),
    ("Boys:girls is 2:3. 20 kids in all. How many girls?", "12",
     {"OTHER_PART": "8", "PART_AS_TOTAL": "30", "FACTOR_ONLY": "4"}),
    ("Boys:girls is 2:3. There are 8 boys. How many kids?", "20",
     {"OTHER_PART": "12", "FACTOR_ONLY": "4"}),
    ("10 is 25% of what number?", "40", {"PERCENT_OF_PART": "2.5", "OTHER_PART": "30"}),
    ("21 is 30% of what number?", "70", {"ONE_PART": "7", "PERCENT_OF_PART": "6.3"}),
    ("4 cans cost $12. Cost of 7 cans?", "$21",
     {"ADDITIVE": "$15", "TOTAL_AS_UNIT": "$84", "FACTOR_ONLY": "$3"}),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_misconception_values(prompt, correct, wrong):
    _, c, _, _ = G.analyze(prompt)
    assert c[0] == correct
    got = {}
    for lab, ch in G.misconception_choices(prompt):
        got.setdefault(lab, set()).add(ch[0])
    for lab, disp in wrong.items():
        assert disp in got.get(lab, set()), (lab, got)


def test_golden_covers_every_catalog_key():
    used = {lab for _, _, w in GOLDEN for lab in w}
    assert used == set(BAKED["misconceptions"])


def test_fifty_percent_has_no_rest_door():
    # for 50% the rest of the whole equals the given number: no OTHER_PART door
    labels = [lab for lab, _ in G.misconception_choices("8 is 50% of what number?")]
    assert "OTHER_PART" not in labels


# ---------------------------------------------------------------------------------------------
# Independent solver: (kind, value, steps) from the prompt text alone
#   steps: list of (op, a, b) with op in "+ - × ÷" -- the correct working, for the bounds walk
# ---------------------------------------------------------------------------------------------
UNIT_FACTORS = {"ft": 3, "qt": 4, "pt": 2, "cups": 2, "days": 7}  # small unit -> per big unit
BIG_OF = {"ft": "yd", "qt": "gal", "pt": "qt", "cups": "pt", "days": "week"}


def ints(s):
    return [int(x) for x in re.findall(r"\d+", s)]


def solve(prompt):
    p = prompt
    n = ints(p)
    if "% of what number" in p:
        part, pct = n
        whole = Fraction(part * 100, pct)
        if pct == 75:
            steps = [("÷", part, 3), ("×", 4, part // 3)]
        elif pct in (10, 25, 50):
            steps = [("×", 100 // pct, part)]
        else:
            steps = [("÷", part, pct // 10), ("×", 10, part // (pct // 10))]
        return "num", whole, steps, {"pct": pct, "whole": whole}
    if "%" in p:
        pct, whole = n
        v = Fraction(pct * whole, 100)
        if pct == 25:
            steps = [("÷", whole, 4)]
        elif pct == 75:
            steps = [("÷", whole, 4), ("×", 3, whole // 4)]
        elif pct == 10:
            steps = [("÷", whole, 10)]
        elif whole % 10 == 0:
            steps = [("÷", whole, 10), ("×", pct // 10, whole // 10)]
        else:  # 50% of a non-multiple of 10
            steps = [("÷", whole, 2)]
        return "num", v, steps, {"pct": pct, "whole": whole}
    if "cost $" in p:
        count, total = n[0], n[1]
        unit = Fraction(total, count)
        if "Cost per" in p:
            return "cash", unit, [("÷", total, count)], {}
        more = n[2]
        return "cash", unit * more, [("÷", total, count), ("×", more, unit)], {}
    if " per " in p and " in " in p:
        amount, time = n
        return "num", Fraction(amount, time), [("÷", amount, time)], {}
    if p.startswith("1 "):
        m = re.match(r"1 \w+ = (\d+) (\w+)\. (\d+) (\w+) = \? (\w+)$", p)
        f, small, given, given_unit, asked = int(m[1]), m[2], int(m[3]), m[4], m[5]
        assert UNIT_FACTORS[small] == f  # the stated fact is true
        if given_unit == small:
            return "num", Fraction(given, f), [("÷", given, f)], {}
        return "num", Fraction(given * f), [("×", given, f)], {}
    if re.match(r"^\d+:\d+ = ", p):
        a, b, c = n
        if p.endswith("?:" + str(c)):  # a:b = ?:c
            k = Fraction(c, b)
            return "num", a * k, [("÷", c, b), ("×", a, k)], {}
        k = Fraction(c, a)  # a:b = c:?
        return "num", b * k, [("÷", c, a), ("×", b, k)], {}
    m = re.match(r"^[\w ]+: (\d+) (\w+) to (\d+) (\w+)\. (\w+) for (\d+) (\w+)\?$", p)
    if m:
        cnt = {m[2]: int(m[1]), m[4]: int(m[3])}
        given, gu, asked = int(m[6]), m[7], m[5].lower()
        k = Fraction(given, cnt[gu])
        return "num", cnt[asked] * k, [("÷", given, cnt[gu]), ("×", cnt[asked], k)], {}
    m = re.match(r"^(\w+):(\w+) is (\d+):(\d+)\. (.*)$", p)
    if m:
        cnt = {m[1].lower(): int(m[3]), m[2]: int(m[4])}
        s = int(m[3]) + int(m[4])
        rest = m[5]
        if "in all" in rest:
            total = ints(rest)[0]
            asked = re.search(r"How many (\w+)\?", rest)[1]
            k = Fraction(total, s)
            return ("num", cnt[asked] * k,
                    [("+", int(m[3]), int(m[4])), ("÷", total, s), ("×", cnt[asked], k)], {})
        g = re.match(r"There are (\d+) (\w+)\.", rest)
        k = Fraction(int(g[1]), cnt[g[2]])
        return ("num", s * k,
                [("÷", int(g[1]), cnt[g[2]]), ("+", int(m[3]), int(m[4])), ("×", s, k)], {})
    # T1 ratio language
    asked = re.search(r"Ratio of (\w+) to (all )?(\w+)\?$", p)
    first, to_all, second = asked[1], bool(asked[2]), asked[3]
    m = re.match(r"^(\d+) \w+: (\d+) are (\w+), the rest (\w+)\.", p)
    if m:
        total, a = int(m[1]), int(m[2])
        cnt = {m[3]: a, m[4]: total - a}
        steps = [("-", total, a)]
    else:
        m = re.match(r"^(?:For every )?(\d+) (\w+) (?:and|there are) (\d+) (\w+)\.", p)
        cnt = {m[2]: int(m[1]), m[4]: int(m[3])}
        steps = []
    names = list(cnt)
    if to_all:
        steps.append(("+", cnt[names[0]], cnt[names[1]]))
        return "ratio", (cnt[first], sum(cnt.values())), steps, {}
    return "ratio", (cnt[first], cnt[second]), steps, {}


def choice_value(disp):
    """Fraction value of a choice's display text (ratio, price, number, fraction, mixed, decimal)."""
    s = disp.lstrip("$")
    if ":" in s:
        a, b = s.split(":")
        return Fraction(int(a), int(b))
    m = re.fullmatch(r"(\d+) (\d+)/(\d+)", s)
    if m:
        return int(m[1]) + Fraction(int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d+)/(\d+)", s)
    if m:
        return Fraction(int(m[1]), int(m[2]))
    assert re.fullmatch(r"\d+(\.\d{1,2})?", s), disp
    return Fraction(s)


def show(kind, v):
    if kind == "ratio":
        return f"{v[0]}:{v[1]}"
    assert v.denominator == 1, v
    return ("$" if kind == "cash" else "") + str(v.numerator)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    kind, v, _, _ = solve(item["prompt"])
    assert item["choices"][item["answer"]] == show(kind, v)
    assert show(kind, v) in item["explanation"]
    assert len(item["choices"]) == 4


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(item):
    vals = [choice_value(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert all(0 < x <= 999 for x in vals)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_share_one_display_kind(item):
    """Prices are all $; ratios are all p:q -- no door is wrong just by its format."""
    ch = item["choices"]
    assert len({c.startswith("$") for c in ch}) == 1, ch
    assert len({":" in c for c in ch}) == 1, ch


# ---------------------------------------------------------------------------------------------
# Labels are honest; misconceptions do the work
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_come_from_their_rule(item):
    _, _, raw, _ = G.analyze(item["prompt"])
    produced = {}
    for lab, ch in raw:
        produced.setdefault(ch[1], lab)  # first label to produce a value owns it
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels)
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        v = choice_value(c)
        if m == "ARITH":
            assert v not in produced, f"ARITH {c} is really {produced.get(v)}"
        else:
            assert produced.get(v) == m, (c, m, produced)


def test_arith_share_at_most_a_third():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 1 / 3


def test_every_template_appears():
    kinds = Counter(G.analyze(it["prompt"])[0] for it in ITEMS)
    assert set(kinds) == set(G.RE), kinds


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"), walking every correct step of the independent solver
# ---------------------------------------------------------------------------------------------
TENS = {20, 30, 40, 50, 60, 70, 80, 90}


def bounds_violations(prompt):
    bad = []
    kind, v, steps, info = solve(prompt)
    for op, a, b in steps:
        a, b = Fraction(a), Fraction(b)
        if a.denominator != 1 or b.denominator != 1:
            bad.append(f"non-integer step {a} {op} {b}")
            continue
        if op == "×":
            if not (2 <= a <= 10 and 2 <= b <= 10):
                bad.append(f"× outside the tables: {a} × {b}")
        elif op == "÷":
            q = a / b
            if q.denominator != 1 or not 2 <= b <= 10 or not 2 <= q <= 10:
                bad.append(f"÷ not a table fact: {a} ÷ {b}")
        elif op in "+-":
            if not (1 <= a <= 20 and 1 <= b <= 20):
                bad.append(f"{op} literal over 20: {a} {op} {b}")
            if op == "+" and a + b > 20:
                bad.append(f"total over 20: {a} + {b}")
    nums = ints(prompt)
    if kind == "ratio":
        p, q = v
        if not (1 <= p <= 20 and 1 <= q <= 20):
            bad.append(f"ratio term over 20: {p}:{q}")
        if not prompt[0].isdigit() and not prompt.startswith("For every"):
            bad.append("unknown ratio template")
        counts = nums[1:] if ": " in prompt else nums
        if any(not 2 <= c <= 10 for c in counts):
            bad.append(f"count outside 2..10: {counts}")
    else:
        if v.denominator != 1 or not 1 <= v <= 100:
            bad.append(f"answer {v} not a whole number 1..100")
    if "pct" in info:
        pct, whole = info["pct"], info["whole"]
        ok = ((pct in TENS or pct == 10) and whole % 10 == 0 and 20 <= whole <= 90) or \
             (pct in (25, 75) and whole % 4 == 0 and 8 <= whole <= 40) or \
             (pct == 50 and whole % 2 == 0 and 4 <= whole <= 20)
        if not ok:
            bad.append(f"{pct}% of {whole} outside the percent bounds")
    m = re.match(r"^\w+:\w+ is (\d+):(\d+)", prompt)
    if m and not (2 <= int(m[1]) <= 8 and 2 <= int(m[2]) <= 8 and int(m[1]) + int(m[2]) <= 10):
        bad.append("sharing ratio terms outside 2..8 / sum 10")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]


@pytest.mark.parametrize("prompt,expect_bad", [
    ("2:3 = ?:12", False),
    ("2:3 = ?:36", True),                                    # scale factor 12
    ("What is 25% of 40?", False),
    ("What is 25% of 80?", True),                            # 80 ÷ 4 = 20: quotient over 10
    ("What is 30% of 100?", True),                           # whole 100 is outside 10q, q 2..9
    ("What is 75% of 44?", True),                            # 44 ÷ 4 = 11
    ("6 pens cost $24. Cost per pen?", False),
    ("4 pens cost $48. Cost per pen?", True),                # unit rate 12
    ("Boys:girls is 2:3. 20 kids in all. How many girls?", False),
    ("Boys:girls is 7:5. 24 kids in all. How many girls?", True),  # 12 parts
    ("12 cats and 5 dogs. Ratio of dogs to cats?", True),    # count 12
    ("15 is 75% of what number?", False),
    ("33 is 75% of what number?", True),                     # 33 ÷ 3 = 11
    ("1 yd = 3 ft. 36 ft = ? yd", True),                     # 36 ÷ 3 = 12
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, bounds_violations(prompt)


def test_manifest_states_bounds():
    assert "bounds" in BAKED and "times-table" in BAKED["bounds"]
