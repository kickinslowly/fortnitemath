"""percent-problems cartridge: golden misconception values, an independent re-solve of every baked
item, choice-value uniqueness, an arithmetic check of every explanation, and the manifest's bounds
walked over every correct step of baked.json.

The independent solver below reads each prompt with its own keyword rules and computes with
``fractions.Fraction`` -- it never calls the generator's ``analyze``.
"""
import json
import random
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator, load_manifest

CID = "percent-problems"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M = "−"  # U+2212


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Golden cases: every catalog key, on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt, correct display, {label: wrong display}
    ("$40 meal plus a 20% tip. Total?", "$48",
     {"PART_ONLY": "$8", "PERCENT_AS_DOLLARS": "$60", "TENTH_FOR_ALL": "$44", "SUBTRACTED": "$32"}),
    ("20% tip on the $40 meal. How much is the tip?", "$8",
     {"TOTAL_FOR_PART": "$48", "PERCENT_AS_DOLLARS": "$20", "TENTH_FOR_ALL": "$4"}),
    ("$40 shirt, 25% off. Sale price?", "$30",
     {"DISCOUNT_ONLY": "$10", "PERCENT_AS_DOLLARS": "$15", "ADDED": "$50", "TENTH_FOR_ALL": "$36"}),
    ("25% off the $40 coat. How much do you save?", "$10",
     {"SALE_FOR_SAVINGS": "$30", "PERCENT_AS_DOLLARS": "$25", "TENTH_FOR_ALL": "$4"}),
    ("A shop pays $30 and marks it up 50%. Selling price?", "$45",
     {"PART_ONLY": "$15", "PERCENT_AS_DOLLARS": "$80", "TENTH_FOR_ALL": "$33"}),
    ("The $30 item gets a 30% markup. New price?", "$39",
     {"PART_ONLY": "$9", "PERCENT_AS_DOLLARS": "$60", "TENTH_FOR_ALL": "$33", "SUBTRACTED": "$21"}),
    ("Cost $30, markup 50%. How much is the markup?", "$15",
     {"TOTAL_FOR_PART": "$45", "PERCENT_AS_DOLLARS": "$50", "TENTH_FOR_ALL": "$3"}),
    ("$50 at 10% simple interest a year for 2 years. Interest?", "$10",
     {"ONE_YEAR": "$5", "TOTAL_FOR_INTEREST": "$60", "PERCENT_AS_DOLLARS": "$20"}),
    ("$30 at 20% simple interest a year for 3 years. Interest?", "$18",
     {"ONE_YEAR": "$6", "TOTAL_FOR_INTEREST": "$48", "PERCENT_AS_DOLLARS": "$60",
      "TENTH_FOR_ALL": "$9"}),
    ("$50 at 10% simple interest a year for 2 years. Balance?", "$60",
     {"INTEREST_ONLY": "$10", "ONE_YEAR": "$55", "PERCENT_AS_DOLLARS": "$70"}),
    ("Price rises from $20 to $25. Percent increase?", "25%",
     {"DIFFERENCE_AS_PERCENT": "5%", "NEW_AS_BASE": "20%", "RATIO_AS_CHANGE": "125%",
      "DECIMAL_NOT_PERCENT": "0.25%"}),
    ("Water drops from 50 cm to 40 cm. Percent decrease?", "20%",
     {"DIFFERENCE_AS_PERCENT": "10%", "NEW_AS_BASE": "25%", "RATIO_AS_CHANGE": "80%",
      "DECIMAL_NOT_PERCENT": "0.2%"}),
    ("Guessed 40. Actual was 50. Percent error?", "20%",
     {"DIFFERENCE_AS_PERCENT": "10%", "GUESS_AS_BASE": "25%", "GUESS_RATIO": "80%",
      "DECIMAL_NOT_PERCENT": "0.2%"}),
    ("$40 coat, 50% off, then 10% tax. Cost?", "$22",
     {"FORGOT_SECOND": "$20", "COMBINED_PERCENTS": "$24", "PERCENT_AS_DOLLARS": "$30",
      "SECOND_WRONG_WAY": "$18"}),
    ("$40 shirt, 25% off, then 10% off that. Price?", "$27",
     {"FORGOT_SECOND": "$30", "COMBINED_PERCENTS": "$26", "PERCENT_AS_DOLLARS": "$20",
      "SECOND_WRONG_WAY": "$33"}),
    ("Cost $20, marked up 50%, then 10% off that. Price?", "$27",
     {"FORGOT_SECOND": "$30", "COMBINED_PERCENTS": "$28", "PERCENT_AS_DOLLARS": "$20",
      "SECOND_WRONG_WAY": "$33"}),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_misconception_values(prompt, correct, wrong):
    kind, c, _, _ = G.analyze(prompt)
    assert c[0] == correct
    got = {lab: ch[0] for lab, ch in G.misconception_choices(prompt)}
    assert got == wrong, got


def test_golden_covers_every_catalog_key():
    used = {lab for _, _, w in GOLDEN for lab in w}
    assert used == set(BAKED["misconceptions"])


@pytest.mark.parametrize("prompt,label,why", [
    ("$50 shirt, 10% off. Sale price?", "TENTH_FOR_ALL", "10% already is a tenth"),
    ("$40 shirt, 50% off. Sale price?", "DISCOUNT_ONLY", "half off: the discount equals the price"),
    ("You tip 25% on the $12 dinner. Total cost?", "TENTH_FOR_ALL", "a tenth of 12 is not whole"),
    ("Price drops from $18 to $9. Percent decrease?", "RATIO_AS_CHANGE", "9/18 is the answer itself"),
    ("Guessed 45. Actual was 50. Percent error?", "GUESS_AS_BASE", "5/45 is not a whole percent"),
    ("The $16 item is marked up 25%, then 20% off that. Price?", "COMBINED_PERCENTS",
     "16 x 105% is not whole"),
    ("A shop pays $30 and marks it up 50%. Selling price?", "SUBTRACTED",
     "30 - 15 equals the markup itself, which is already PART_ONLY"),
    ("Score rises from 70 to 77 points. Percent increase?", "NEW_AS_BASE", "7/77 is not whole"),
])
def test_rule_does_not_fire_where_it_does_not_apply(prompt, label, why):
    assert label not in [lab for lab, _ in G.misconception_choices(prompt)], why


def test_values_equal_to_the_answer_or_below_zero_are_dropped():
    # 50% off $40: PERCENT_AS_DOLLARS 40 - 50 is negative (dropped); DISCOUNT_ONLY 20 equals the answer
    labels = [lab for lab, _ in G.misconception_choices("$40 shirt, 50% off. Sale price?")]
    assert labels == ["ADDED", "TENTH_FOR_ALL"]


def test_prompt_outside_the_templates_is_refused():
    with pytest.raises(G.NotMine):
        G.analyze("What is 25% of 40?")
    with pytest.raises(G.NotMine):
        G.analyze("Price rises from $20 to $25. Percent decrease?")  # wrong direction word


# ---------------------------------------------------------------------------------------------
# Independent solver: from the prompt text alone
#   returns kind, answer (Fraction), unit ("$" or "%"), plus the numbers the bounds walk needs
# ---------------------------------------------------------------------------------------------
def ints(s):
    return [int(x) for x in re.findall(r"\d+", s)]


def dollars(s):
    return [int(x) for x in re.findall(r"\$(\d+)", s)]


def percents(s):
    return [int(x) for x in re.findall(r"(\d+)%", s)]


def solve(prompt):
    p = prompt
    low = p.lower()
    if p.endswith("Percent increase?") or p.endswith("Percent decrease?"):
        O, N = ints(p)
        assert (N > O) == p.endswith("increase?"), p
        d = abs(N - O)
        return {"kind": "change", "ans": Fraction(100 * d, O), "unit": "%", "O": O, "N": N, "d": d}
    if p.endswith("Percent error?"):
        g, A = ints(p)
        d = abs(g - A)
        return {"kind": "error", "ans": Fraction(100 * d, A), "unit": "%", "g": g, "A": A, "d": d}
    if "simple interest" in low:
        P, r, t = ints(p)
        a = Fraction(P * r, 100)
        I = a * t
        balance = "balance" in low
        return {"kind": "balance" if balance else "interest", "ans": P + I if balance else I,
                "unit": "$", "P": P, "r": r, "t": t, "a": a, "I": I}
    if p.count("%") == 2:
        assert " then " in p, p
        W = dollars(p)[0]
        p1, p2 = percents(p)
        if "marked up" in low:  # marked up, then off
            sub, V1 = "mark_disc", W * Fraction(100 + p1, 100)
            V2 = V1 * Fraction(100 - p2, 100)
        elif "tax" in low:  # off, then taxed
            sub, V1 = "disc_tax", W * Fraction(100 - p1, 100)
            V2 = V1 * Fraction(100 + p2, 100)
        else:  # off, then off again
            sub, V1 = "disc_disc", W * Fraction(100 - p1, 100)
            V2 = V1 * Fraction(100 - p2, 100)
        return {"kind": "two_step", "sub": sub, "ans": V2, "unit": "$", "W": W, "p1": p1, "p2": p2,
                "V1": V1}
    # one percent of one price
    assert p.count("%") == 1 and len(dollars(p)) == 1, p
    W, pct = dollars(p)[0], percents(p)[0]
    a = Fraction(W * pct, 100)
    part_ask = bool(re.search(r"how much|in dollars", low))
    if re.search(r"\boff\b|discount", low):
        kind, ans = "disc", (a if part_ask else W - a)
    elif "mark" in low:
        kind, ans = "markup", (a if part_ask else W + a)
    else:
        assert "tip" in low or "tax" in low, p
        kind, ans = ("tip" if "tip" in low else "tax"), (a if part_ask else W + a)
    return {"kind": kind, "ans": ans, "unit": "$", "W": W, "pct": pct, "a": a}


def show(info):
    v = info["ans"]
    assert v.denominator == 1, (info, v)
    return f"${v.numerator}" if info["unit"] == "$" else f"{v.numerator}%"


def choice_value(disp):
    s = disp.lstrip("$").rstrip("%")
    assert re.fullmatch(r"\d+(\.\d{1,2})?", s), disp
    return Fraction(s)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    info = solve(item["prompt"])
    assert item["choices"][item["answer"]] == show(info)
    assert item["explanation"].endswith(show(info) + "."), item["explanation"]
    assert len(item["choices"]) == 4


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(item):
    vals = [choice_value(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert all(0 < x <= 999 for x in vals)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_share_one_display_kind(item):
    """All dollars or all percents -- no door is wrong just by its format."""
    ch = item["choices"]
    assert len({c.startswith("$") for c in ch}) == 1, ch
    assert len({c.endswith("%") for c in ch}) == 1, ch
    assert all(c.startswith("$") != c.endswith("%") for c in ch), ch


def test_solver_refuses_an_unknown_prompt():
    with pytest.raises(AssertionError):
        solve("What is 25% of 40?")


# ---------------------------------------------------------------------------------------------
# Explanations: every "a op b = c" written in them is true
# ---------------------------------------------------------------------------------------------
EQ = re.compile(r"\$?(\d+) ([+−×]) \$?(\d+) = \$?(\d+)")


def false_equations(text):
    """Every 'a op b = c' in the text whose arithmetic is wrong."""
    out = []
    for a, op, b, c in EQ.findall(text):
        a, b, c = int(a), int(b), int(c)
        if {"+": a + b, M: a - b, "×": a * b}[op] != c:
            out.append((a, op, b, c))
    return out


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_explanation_arithmetic_is_true(item):
    assert false_equations(item["explanation"]) == [], item["explanation"]
    info = solve(item["prompt"])
    asks_part = bool(re.search(r"how much|in dollars", item["prompt"].lower()))
    if info["kind"] not in ("interest", "change", "error") and not asks_part:
        assert EQ.search(item["explanation"]), item["explanation"]  # totals show their last sum


def test_explanation_checker_can_fail():
    assert false_equations("10% of $40 is $4. $40 + $4 = $45.") == [(40, "+", 4, 45)]
    assert false_equations("Change: 25 − 20 = 5. 3 × 4 = 12.") == []


# ---------------------------------------------------------------------------------------------
# Labels are honest; misconceptions do the work
# ---------------------------------------------------------------------------------------------
def label_problems(item):
    """Why an item's misconception labels are dishonest (empty list: they are honest)."""
    _, _, raw, _ = G.analyze(item["prompt"])
    produced = {}
    for lab, ch in raw:
        produced.setdefault(ch[1], lab)  # first label to produce a value owns it
    out = []
    labels = [m for m in item["misconceptions"] if m]
    if not any(m != "ARITH" for m in labels):
        out.append("needs at least one misconception distractor")
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        v = choice_value(c)
        if m == "ARITH":
            if v in produced:
                out.append(f"ARITH {c} is really {produced[v]}")
        elif produced.get(v) != m:
            out.append(f"{c} is labelled {m} but the rules give {produced.get(v)}")
    return out


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_come_from_their_rule(item):
    assert label_problems(item) == []


def test_label_checker_can_fail():
    good = {"prompt": "$40 meal plus a 20% tip. Total?", "choices": ["$48", "$8", "$60", "$44"],
            "misconceptions": [None, "PART_ONLY", "PERCENT_AS_DOLLARS", "TENTH_FOR_ALL"]}
    assert label_problems(good) == []
    hides_a_rule = dict(good, misconceptions=[None, "ARITH", "PERCENT_AS_DOLLARS", "TENTH_FOR_ALL"])
    assert any("ARITH $8 is really PART_ONLY" in p for p in label_problems(hides_a_rule))
    wrong_label = dict(good, misconceptions=[None, "TENTH_FOR_ALL", "PERCENT_AS_DOLLARS", "PART_ONLY"])
    assert len(label_problems(wrong_label)) == 2


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("tier", range(1, 6))
def test_other_seeds_hold_the_same_properties(seed, tier):
    """The baked sample is one draw: a fresh draw must also be right, honest and in bounds."""
    for it in G.gen_tier(tier, 40, random.Random(seed * 1000 + tier)):
        info = solve(it["prompt"])
        assert it["choices"][it["answer"]] == show(info), it["prompt"]
        vals = [choice_value(c) for c in it["choices"]]
        assert len(set(vals)) == 4 and all(0 < v <= 999 for v in vals), it
        assert label_problems(it) == [], it
        assert bounds_violations(it["prompt"]) == [], it["prompt"]
        assert false_equations(it["explanation"]) == [], it["explanation"]


def test_arith_share_at_most_a_third_overall_and_a_quarter_per_tier():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 1 / 3
    for t in range(1, 6):
        ct = Counter(m for it in by_tier(t) for m in it["misconceptions"] if m)
        assert ct["ARITH"] / sum(ct.values()) <= 0.25, t


def test_every_catalog_key_is_used():
    used = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    for key in BAKED["misconceptions"]:
        assert used[key] >= 3, (key, used[key])
    for key, v in BAKED["misconceptions"].items():
        assert v["student"] and v["teacher"] and len(v["student"]) <= 80, key


def test_decimal_door_stays_rare():
    """A third door on nearly every item would teach 'always skip the 0.x% one'."""
    t45 = by_tier(4) + by_tier(5)
    share = sum("DECIMAL_NOT_PERCENT" in it["misconceptions"] for it in t45) / len(t45)
    assert 0.05 <= share <= 0.4, share


# ---------------------------------------------------------------------------------------------
# Display rules and tier shapes
# ---------------------------------------------------------------------------------------------
def test_no_hyphen_minus_and_no_article_before_a_price():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in s, s
        assert not re.search(r"\b[Aa]n? \$", it["prompt"]), it["prompt"]  # "a $8" / "a $80"


TIER_KINDS = {1: {"tip", "tax"}, 2: {"disc"}, 3: {"markup", "interest", "balance"},
              4: {"change"}, 5: {"error", "two_step"}}


@pytest.mark.parametrize("tier", range(1, 6))
def test_tier_shapes(tier):
    kinds = Counter(solve(it["prompt"])["kind"] for it in by_tier(tier))
    assert set(kinds) == TIER_KINDS[tier], kinds
    assert len(by_tier(tier)) == 40


def test_both_asks_appear_in_the_add_on_and_discount_tiers():
    for tier in (1, 2, 3):
        asks = Counter(bool(re.search(r"how much|in dollars", it["prompt"].lower()))
                       for it in by_tier(tier))
        assert asks[True] >= 4 and asks[False] >= 20, (tier, asks)
    two = Counter(solve(it["prompt"])["sub"] for it in by_tier(5)
                  if solve(it["prompt"])["kind"] == "two_step")
    assert set(two) == {"disc_tax", "disc_disc", "mark_disc"} and min(two.values()) >= 5, two
    assert any(it["prompt"].endswith("Percent error?") for it in by_tier(5))
    inc = sum(it["prompt"].endswith("increase?") for it in by_tier(4))
    assert 12 <= inc <= 28


def test_reproducible_from_the_seed():
    m = load_manifest(CID)
    again = G.generate(m, random.Random(m["seed"]))
    stripped = [{k: v for k, v in it.items() if k != "id"} for it in ITEMS]
    assert again == stripped


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"), walking every correct step of the independent solver
# ---------------------------------------------------------------------------------------------
TIP, TAX = {10, 20, 25}, {10, 20}
OFF, MARKUP = {10, 20, 25, 30, 40, 50, 75}, {10, 20, 25, 30, 40, 50}
RATE, CHANGE, ERROR = {10, 20, 25}, {10, 20, 25, 30, 40, 50, 75}, {10, 20, 25, 30, 40, 50}
EXTRA_OFF = {10, 20, 25}
TENS_WHOLES = set(range(20, 91, 10))
QUARTER_WHOLES = set(range(8, 41, 4))
HALF_WHOLES = set(range(4, 21, 2))


def clean_base(p, W):
    """p% of W is a mental fact: tens of percent of 20-90 in tens, 25%/75% of 8-40 in fours,
    50% also of evens 4-20."""
    if p in (25, 75):
        return W in QUARTER_WHOLES
    if p % 10 == 0:
        return W in TENS_WHOLES or (p == 50 and W in HALF_WHOLES)
    return False


def bounds_violations(prompt):
    bad = []
    info = solve(prompt)
    kind = info["kind"]

    def pct_step(p, W, allowed, what):
        """Check p% of W; return the amount (or 0 when it is not a clean one)."""
        if p not in allowed:
            bad.append(f"{what}: {p}% not in {sorted(allowed)}")
        if not clean_base(p, W):
            bad.append(f"{what}: {p}% of {W} is not a clean fact")
            return 0
        a = Fraction(p * W, 100)
        if a.denominator != 1 or not 2 <= a <= 20:
            bad.append(f"{what}: amount {a} outside 2..20")
        return a

    def in_range(v, what):
        if not 1 <= v <= 100:
            bad.append(f"{what} {v} outside 1..100")

    if kind in ("tip", "tax", "markup", "disc"):
        allowed = {"tip": TIP, "tax": TAX, "markup": MARKUP, "disc": OFF}[kind]
        W = info["W"]
        in_range(W, "whole")
        a = pct_step(info["pct"], W, allowed, kind)
        in_range(W - a if kind == "disc" else W + a, "new price")
    elif kind in ("interest", "balance"):
        P, r, t = info["P"], info["r"], info["t"]
        a = pct_step(r, P, RATE, "interest")
        if a and not 2 <= a <= 10:
            bad.append(f"yearly interest {a} outside 2..10")
        if not 2 <= t <= 5:
            bad.append(f"years {t} outside 2..5")
        if a * t > 20:
            bad.append(f"interest {a * t} over 20")
        in_range(P + a * t, "balance")
    elif kind in ("change", "error"):
        base = info["O"] if kind == "change" else info["A"]
        other = info["N"] if kind == "change" else info["g"]
        d = info["d"]
        in_range(base, "base")
        in_range(other, "other value")
        if not 2 <= d <= 20:
            bad.append(f"change {d} outside 2..20")
        p = info["ans"]
        if p.denominator != 1:
            bad.append(f"percent {p} is not whole")
        else:
            if p not in (CHANGE if kind == "change" else ERROR):
                bad.append(f"percent {p} not allowed")
            if not clean_base(int(p), base):
                bad.append(f"{p}% of {base} is not a clean fact")
    else:  # two_step
        sub, W, p1, p2 = info["sub"], info["W"], info["p1"], info["p2"]
        a1_set, a2_set = {"disc_tax": (OFF, TAX), "disc_disc": (OFF, EXTRA_OFF),
                          "mark_disc": (MARKUP, EXTRA_OFF)}[sub]
        in_range(W, "whole")
        a1 = pct_step(p1, W, a1_set, "first step")
        V1 = W + a1 if sub == "mark_disc" else W - a1
        in_range(V1, "first result")
        a2 = pct_step(p2, V1, a2_set, "second step")
        V2 = V1 + a2 if sub == "disc_tax" else V1 - a2
        in_range(V2, "second result")
        if V2 != info["ans"]:
            bad.append("solver disagrees with the walk")
    ans = info["ans"]
    if ans.denominator != 1 or (info["unit"] == "$" and not 1 <= ans <= 100):
        bad.append(f"answer {ans} not a whole number 1..100")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]
    for c in item["choices"]:  # wrong choices keep the 999 ceiling
        assert choice_value(c) <= 999


@pytest.mark.parametrize("prompt,expect_bad", [
    # accepted
    ("$40 meal plus a 20% tip. Total?", False),
    ("$40 bike, 25% off, then 10% tax. Total?", False),
    ("Price rises from $20 to $26. Percent increase?", False),
    ("Guessed 45. Actual was 50. Percent error?", False),
    ("$30 at 20% simple interest a year for 3 years. Interest?", False),
    ("The $20 item is marked up 50%, then 10% off that. Price?", False),
    ("$50 shirt, 10% off. Sale price?", False),
    # rejected: each breaks one clause of the bounds
    ("$40 meal plus a 15% tip. Total?", True),                       # 15% is not a tip percent
    ("$90 meal plus a 20% tip. Total?", True),                       # total 108
    ("$44 meal plus a 25% tip. Total?", True),                       # 44 is not a four-multiple <= 40
    ("$70 jacket plus 30% sales tax. Total cost?", True),            # 30% tax; amount 21
    ("75% off the $40 bag. New price?", True),                       # discount of 30
    ("$100 shirt, 10% off. Sale price?", True),                      # whole 100
    ("$40 at 20% simple interest a year for 5 years. Interest?", True),  # interest 40
    ("$40 at 10% simple interest a year for 1 years. Interest?", True),  # one year
    ("Price rises from $20 to $27. Percent increase?", True),        # 35%
    ("Price rises from $20 to $40. Percent increase?", True),        # 100%, change 20 but not allowed
    ("Guessed 35. Actual was 30. Percent error?", True),             # 16.7%
    ("$40 coat, 50% off, then 15% tax. Cost?", True),                # 15% tax
    ("$50 jacket, 50% off, then 10% tax. Total?", True),             # discount of 25
    ("$40 shirt, 50% off, then 25% tax. Total?", True),              # 25% tax; also 5 is not clean
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, bounds_violations(prompt)


def test_manifest_states_bounds():
    assert "bounds" in BAKED and "times-table" in BAKED["bounds"]
    assert BAKED["standards"] == ["CCSS.MATH.CONTENT.7.RP.A.3"] and BAKED["grade"] == "7"
