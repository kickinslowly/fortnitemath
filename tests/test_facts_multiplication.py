"""facts-multiplication cartridge: golden misconception values, an independent re-check of every baked item,
the §4c bands and distractor rules walked on baked.json, and a checker self-test (a planted bad item must fail).

The independent checks parse the prompt text with a regex and compute with plain Python; they never call the
generator's arithmetic.
"""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "facts-multiplication"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
PROMPT_RE = re.compile(r"^(\d+) ([+−×÷]) (\d+) = \?$")
BAND = {1: (1, 5, 1), 2: (6, 8, 2), 3: (9, 10, 2), 4: (11, 12, 2), 5: (13, 15, 2)}  # larger lo, hi, smaller lo
PROMPT_COUNT = {1: 25, 2: 33, 3: 32, 4: 40, 5: 75}


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def parse(it):
    m = PROMPT_RE.match(it["prompt"])
    assert m, it["prompt"]
    assert m.group(2) == "×"
    return int(m.group(1)), int(m.group(3))


def problems(it):
    """Everything wrong with one baked item (empty list = fine). Independent of the generator."""
    out = []
    try:
        a, b = parse(it)
    except AssertionError:
        return ["prompt shape"]
    p = a * b
    ch = [int(c) for c in it["choices"]]
    if len(ch) != 4 or len(set(ch)) != 4:
        out.append("choices not 4 distinct")
    if ch[it["answer"]] != p:
        out.append("answer wrong")
    if sum(1 for c in ch if c == p) != 1:
        out.append("answer not unique")
    wrong = [c for i, c in enumerate(ch) if i != it["answer"]]
    if any(c < 0 or c > 999 for c in wrong):
        out.append("wrong choice out of range")
    lo, hi, low = BAND[it["tier"]]
    if not (lo <= max(a, b) <= hi) or min(a, b) < low:
        out.append("band")
    if p > 225:
        out.append("product over 225")
    if sum(1 for c in wrong if abs(c - p) <= max(a, b)) < 2:
        out.append("fewer than 2 near values")
    if sum(1 for c in wrong if abs(c - p) > max(a, b)) > 1:
        out.append("more than 1 far value")
    if it["tier"] >= 4 and not any(c % 10 == p % 10 for c in wrong):
        out.append("ones-digit tell")
    if [m is None for m in it["misconceptions"]] != [i == it["answer"] for i in range(4)]:
        out.append("misconception null placement")
    return out


# ---------------------------------------------------------------------------------------------
# Golden cases: each misconception key gives its expected wrong value on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
def _group(pairs):
    d = {}
    for k, v in pairs:
        d.setdefault(k, []).append(v)
    return d


def test_golden_group_off():
    # 7 x 8 = 56: 7 x 9 = 63, 8 x 8 = 64, 7 x 7 = 49, 6 x 8 = 48
    assert sorted(_group(G.candidates(7, 8, 2))["GROUP_OFF"]) == [48, 49, 63, 64]
    # 4 x 3 = 12: 4 x 4, 5 x 3, 4 x 2, 3 x 3
    assert sorted(_group(G.candidates(4, 3, 1))["GROUP_OFF"]) == [8, 9, 15, 16]


def test_golden_added():
    assert _group(G.candidates(7, 8, 2))["ADDED"] == [15]
    assert _group(G.candidates(4, 3, 1))["ADDED"] == [7]


def test_golden_dropped_carry():
    # 13 x 6 = 78 = 60 + 18; losing the ten of 18 gives 68
    g = _group(G.candidates(13, 6, 5))
    assert g["DROPPED_CARRY"] == [68]
    assert sorted(g["TENS_SLIP"]) == [88]  # 68 is DROPPED_CARRY (first key wins), 88 is the other slip
    assert _group(G.candidates(6, 13, 5))["DROPPED_CARRY"] == [68]
    # 12 x 3 = 36: ones product 6 does not carry, so only TENS_SLIP
    g = _group(G.candidates(12, 3, 4))
    assert "DROPPED_CARRY" not in g and sorted(g["TENS_SLIP"]) == [26, 46]


def test_golden_partial_products():
    # 13 x 14 = 182: 10 x 10 + 3 x 4 = 112
    assert _group(G.candidates(13, 14, 5))["PARTIAL_PRODUCTS"] == [112]
    # 11 x 12 = 132: 100 + 2
    assert _group(G.candidates(11, 12, 4))["PARTIAL_PRODUCTS"] == [102]


def test_golden_tens_slip_ones_digit():
    for a, b, t in ((10, 7, 3), (14, 9, 5), (12, 11, 4), (15, 15, 5)):
        for v in _group(G.candidates(a, b, t)).get("TENS_SLIP", []):
            assert v % 10 == (a * b) % 10


def test_golden_arith_only_fills():
    # 1 x 1 = 1: GROUP_OFF gives 2 and 0, ADDED 2 (dup, dropped); ARITH fills with 3 and 4
    keys = dict((v, k) for k, v in G.candidates(1, 1, 1))
    assert keys == {2: "GROUP_OFF", 0: "GROUP_OFF"}
    assert [v for _, v in G.fill_values(1, 1, {0, 2})] == [3, 4]  # +-1 taken, -2 < 0, +2 = 3, +3 = 4
    # the answer itself is never a candidate (2 x 2: ADDED is 4)
    assert 4 not in dict((v, k) for k, v in G.candidates(2, 2, 1))


def test_golden_explanations():
    assert G.explain(7, 8) == "7 × 8 = 56: 7 × 7 = 49, plus one more 7 = 56."
    assert G.explain(13, 6) == "13 × 6 = 78: split 13 into 10 and 3. 60 + 18 = 78."
    assert G.explain(9, 7) == "9 × 7 = 63: 10 × 7 = 70, minus one 7 = 63."
    assert G.explain(5, 6) == "5 × 6 = 30: half of 6 × 10 = 60, and half of 60 is 30."
    assert G.explain(6, 8) == "6 × 8 = 48: split 6 into 5 and 1. 5 × 8 = 40, 1 × 8 = 8, total 48."


# ---------------------------------------------------------------------------------------------
# Independent re-check of EVERY baked item
# ---------------------------------------------------------------------------------------------
def test_item_counts():
    assert len(ITEMS) == 5 * BAKED["items_per_tier"]
    for t in BAND:
        assert len(by_tier(t)) == BAKED["items_per_tier"]


@pytest.mark.parametrize("it", ITEMS, ids=[f"t{i['tier']}-{i['prompt']}" for i in ITEMS])
def test_every_item_rechecked(it):
    assert problems(it) == []
    a, b = parse(it)
    assert int(it["choices"][it["answer"]]) == a * b
    assert it["explanation"].startswith(f"{a} × {b} = {a * b}: ")
    assert len(it["explanation"]) <= 160


def test_prompts_unique_per_tier():
    for t in BAND:
        ps = [it["prompt"] for it in by_tier(t)]
        assert len(ps) == len(set(ps))


def test_prompt_pool_sizes_match_the_library_table():
    for t, n in PROMPT_COUNT.items():
        assert len(G.prompts_for_tier(t)) == n


# ---------------------------------------------------------------------------------------------
# Bands, distractors, tells
# ---------------------------------------------------------------------------------------------
def test_bands_and_ranges_on_baked():
    for it in ITEMS:
        a, b = parse(it)
        lo, hi, low = BAND[it["tier"]]
        assert lo <= max(a, b) <= hi and min(a, b) >= low and max(a, b) <= 15
        wrong = [int(c) for i, c in enumerate(it["choices"]) if i != it["answer"]]
        assert len(set(wrong)) == 3 and all(0 <= w <= 999 and w != a * b for w in wrong)


def test_near_distractor_rule():
    for it in ITEMS:
        a, b = parse(it)
        p = a * b
        wrong = [int(c) for i, c in enumerate(it["choices"]) if i != it["answer"]]
        assert sum(1 for w in wrong if abs(w - p) <= max(a, b)) >= 2, it
        assert sum(1 for w in wrong if abs(w - p) > max(a, b)) <= 1, it


def ranks(t):
    c = Counter()
    for it in by_tier(t):
        vals = sorted(int(x) for x in it["choices"])
        c[vals.index(int(it["choices"][it["answer"]]))] += 1
    return c


@pytest.mark.parametrize("t", sorted(BAND))
def test_no_middle_tell_each_rank_15_to_35_percent(t):
    c = ranks(t)
    n = len(by_tier(t))
    for r in range(4):
        assert 0.15 * n <= c[r] <= 0.35 * n, (t, dict(c))


@pytest.mark.parametrize("t", sorted(BAND))
def test_answer_position_balance(t):
    c = Counter(it["answer"] for it in by_tier(t))
    n = len(by_tier(t))
    for pos in range(4):
        assert 0.5 / 4 * n <= c[pos] <= 1.5 / 4 * n, (t, dict(c))


@pytest.mark.parametrize("t", [4, 5])
def test_no_ones_digit_tell(t):
    its = by_tier(t)
    only = 0
    for it in its:
        p = int(it["choices"][it["answer"]])
        if sum(1 for c in it["choices"] if int(c) % 10 == p % 10) == 1:
            only += 1
    assert only <= 0.25 * len(its), (t, only)


def test_misconception_keys_declared_and_used():
    declared = set(BAKED["misconceptions"]) | {"ARITH"}
    used = {k for it in ITEMS for k in it["misconceptions"] if k}
    assert used <= declared
    assert {"GROUP_OFF", "ADDED", "TENS_SLIP", "PARTIAL_PRODUCTS", "DROPPED_CARRY"} <= used
    for k, v in BAKED["misconceptions"].items():
        assert len(v["student"]) <= 80 and v["teacher"]


def test_arith_is_a_filler_not_the_norm():
    n = sum(1 for it in ITEMS for k in it["misconceptions"] if k == "ARITH")
    assert n <= 0.25 * len(ITEMS) * 3


def test_generation_is_deterministic():
    m = {k: v for k, v in BAKED.items() if k not in ("items", "baked_with")}
    assert G.generate(m, random.Random(m["seed"])) == G.generate(m, random.Random(m["seed"]))


# ---------------------------------------------------------------------------------------------
# Checker self-test: the checker can fail
# ---------------------------------------------------------------------------------------------
GOOD = {"tier": 2, "prompt": "7 × 8 = ?", "choices": ["56", "63", "49", "15"], "answer": 0,
        "misconceptions": [None, "GROUP_OFF", "GROUP_OFF", "ADDED"], "explanation": "x"}


def test_checker_accepts_a_good_item():
    assert problems(GOOD) == []


@pytest.mark.parametrize("mutation,expected", [
    ({"choices": ["54", "63", "49", "15"]}, "answer wrong"),                       # key is not 7 x 8
    ({"choices": ["56", "15", "1", "99"]}, "fewer than 2 near values"),            # far-only distractors
    ({"choices": ["56", "56", "49", "63"]}, "choices not 4 distinct"),             # two right doors
    ({"choices": ["56", "63", "49", "-3"]}, "wrong choice out of range"),
    ({"prompt": "9 × 8 = ?"}, "band"),                                             # tier 2 needs a larger factor of 6-8
    ({"choices": ["56", "63", "49", "1000"]}, "wrong choice out of range"),
    ({"misconceptions": ["ARITH", "GROUP_OFF", "GROUP_OFF", "ADDED"]}, "misconception null placement"),
])
def test_checker_rejects_planted_bad_items(mutation, expected):
    bad = {**GOOD, **mutation}
    assert expected in problems(bad)


def test_checker_rejects_ones_digit_tell_on_tier_4():
    bad = {"tier": 4, "prompt": "12 × 7 = ?", "choices": ["84", "91", "77", "96"], "answer": 0,
           "misconceptions": [None, "GROUP_OFF", "GROUP_OFF", "GROUP_OFF"], "explanation": "x"}
    assert "ones-digit tell" in problems(bad)
