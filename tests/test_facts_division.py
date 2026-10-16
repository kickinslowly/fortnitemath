"""facts-division cartridge: golden misconception values, an independent re-check of every baked item,
PROTOCOL 4c bounds, near / no-middle-tell / no-ones-digit-tell rules, and a checker self-test (a disproof)."""
import json
import re

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "facts-division"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
PROMPT = re.compile(r"^(\d+) ÷ (\d+) = \?$")
BANDS = {1: (1, 5, 1), 2: (6, 8, 2), 3: (9, 10, 2), 4: (11, 12, 2), 5: (13, 15, 2)}  # (lo, hi, min factor)
TIER_PAIRS = {1: 25, 2: 33, 3: 32, 4: 40, 5: 75}


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def parse(prompt):
    m = PROMPT.match(prompt)
    assert m, prompt
    return int(m.group(1)), int(m.group(2))


# ---------------------------------------------------------------------------------------------
# Golden misconception values (hand-worked)
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt p ÷ a, answer, key, sign, size, wrong value
    (56, 7, 8, "GROUP_OFF", 1, 1, 9),
    (56, 7, 8, "GROUP_OFF", -1, 1, 7),
    (56, 7, 8, "GROUP_OFF", 1, 2, 10),
    (56, 7, 8, "SUBTRACTED", 1, 1, 49),
    (56, 7, 8, "MULTIPLIED", 1, 1, 392),
    (156, 12, 13, "TENS_SLIP", 1, 1, 23),
    (156, 12, 13, "TENS_SLIP", -1, 1, 3),
    (156, 12, 13, "SUBTRACTED", 1, 1, 144),
    (20, 4, 5, "SUBTRACTED", 1, 1, 16),
]


@pytest.mark.parametrize("p,a,b,key,sign,size,wrong", GOLDEN)
def test_golden_values(p, a, b, key, sign, size, wrong):
    assert p == a * b
    assert G.misconception_value(key, p, a, sign, size) == wrong


def test_multiplied_dropped_when_over_999():
    assert G.misconception_value("MULTIPLIED", 225, 15) is None  # 3375
    assert G.misconception_value("MULTIPLIED", 100, 10) is None  # 1000 > 999


def test_candidates_keep_first_key_on_collision():
    # 2 ÷ 1: SUBTRACTED p - a = 1 is also GROUP_OFF b - 1 = 1; GROUP_OFF listed first
    cand = G.candidates(2, 1, 1)
    assert cand[1][0] == "GROUP_OFF"
    assert 2 not in cand  # the answer itself is never a candidate


def test_explanations_fit_and_teach():
    assert G.explanation(56, 7).startswith("56 ÷ 7 = 8 because 7 × 8 = 56.")
    assert "Split 14 as 10 and 4: 120 + 48 = 168" in G.explanation(168, 12)
    assert G.explanation(18, 2) == "18 ÷ 2 = 9: half of 18 is 9, because 9 + 9 = 18."
    assert all(len(G.explanation(a * b, a)) <= 160 for t in range(1, 6) for a, b in G.pairs(t))


# ---------------------------------------------------------------------------------------------
# The checker: every rule applied to one item; returns a list of problems (empty = fine)
# ---------------------------------------------------------------------------------------------
def check_item(it):
    bad = []
    p, a = parse(it["prompt"])
    if a == 0 or p % a:
        return [f"inexact {it['prompt']}"]
    b = p // a  # plain Python, never the generator
    lo, hi, mf = BANDS[it["tier"]]
    if not (lo <= max(a, b) <= hi and min(a, b) >= mf):
        bad.append("band")
    vals = [int(c) for c in it["choices"]]
    if vals[it["answer"]] != b:
        bad.append("wrong answer")
    if sum(v == b for v in vals) != 1:
        bad.append("answer not unique")
    if len(set(vals)) != 4:
        bad.append("choices not distinct")
    if not all(0 <= v <= 999 for v in vals):
        bad.append("range")
    wrong = [v for v in vals if v != b]
    if sum(1 for v in wrong if abs(v - b) <= 2) < 2:
        bad.append("fewer than 2 near")
    if sum(1 for v in wrong if v in (p - a, p * a) and abs(v - b) > 3) > 1:
        bad.append("more than 1 far")
    return bad


@pytest.mark.parametrize("tier", range(1, 6))
def test_every_baked_item_rechecked(tier):
    its = by_tier(tier)
    assert len(its) == BAKED["items_per_tier"] == 24
    for it in its:
        assert check_item(it) == [], it["prompt"]
        assert len(it["choices"]) == 4


def test_checker_rejects_planted_items():
    good = dict(tier=2, prompt="56 ÷ 7 = ?", choices=["8", "9", "7", "49"], answer=0)
    assert check_item(good) == []
    assert "wrong answer" in check_item({**good, "answer": 1})
    assert "band" in check_item({**good, "tier": 1})
    assert "fewer than 2 near" in check_item({**good, "choices": ["8", "9", "20", "49"]})
    assert "choices not distinct" in check_item({**good, "choices": ["8", "9", "9", "49"]})
    assert "more than 1 far" in check_item({**good, "choices": ["8", "9", "392", "49"]})
    assert check_item({**good, "prompt": "57 ÷ 7 = ?"}) == ["inexact 57 ÷ 7 = ?"]


def test_misconception_labels_match_values():
    for it in ITEMS:
        p, a = parse(it["prompt"])
        b = p // a
        for c, k in zip(it["choices"], it["misconceptions"]):
            v = int(c)
            if k is None:
                assert v == b
            elif k == "GROUP_OFF":
                assert abs(v - b) in (1, 2), it
            elif k == "TENS_SLIP":
                assert abs(v - b) == 10, it
            elif k == "SUBTRACTED":
                assert v == p - a, it
            elif k == "MULTIPLIED":
                assert v == p * a, it
            else:
                assert k == "ARITH" and abs(v - b) == 3, it


# ---------------------------------------------------------------------------------------------
# Bounds on baked.json
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("tier", range(1, 6))
def test_tier_prompts_unique_and_in_band(tier):
    prompts = [it["prompt"] for it in by_tier(tier)]
    assert len(set(prompts)) == len(prompts)
    allowed = {f"{a * b} ÷ {a} = ?" for a in range(1, 16) for b in range(1, 16)
               if BANDS[tier][0] <= max(a, b) <= BANDS[tier][1] and min(a, b) >= BANDS[tier][2]}
    assert len(allowed) == TIER_PAIRS[tier]
    assert set(prompts) <= allowed


def test_sums_of_tier_names_and_bounds_text():
    assert [t["name"] for t in BAKED["tiers"]] == ["Up to 25 ÷ 5", "Up to 64 ÷ 8", "Up to 100 ÷ 10",
                                                   "Up to 144 ÷ 12", "Up to 225 ÷ 15"]
    assert BAKED["grade"] == "Facts" and BAKED["picker_order"] == 4
    assert "T5 max 13-15" in BAKED["bounds"]


# ---------------------------------------------------------------------------------------------
# Rank spread (no middle tell), ones-digit tell, answer positions
# ---------------------------------------------------------------------------------------------
def rank_shares(its):
    counts = [0, 0, 0, 0]
    for it in its:
        vals = [int(c) for c in it["choices"]]
        b = vals[it["answer"]]
        counts[sum(v < b for v in vals)] += 1
    return [c / len(its) for c in counts]


@pytest.mark.parametrize("tier", range(1, 6))
def test_no_middle_tell(tier):
    for share in rank_shares(by_tier(tier)):
        assert 0.15 <= share <= 0.35, rank_shares(by_tier(tier))


def test_rank_checker_fails_on_a_middle_tell():
    planted = [dict(choices=["7", "8", "9", "30"], answer=1) for _ in range(10)]
    assert not all(0.15 <= s <= 0.35 for s in rank_shares(planted))


@pytest.mark.parametrize("tier", (4, 5))
def test_no_ones_digit_tell(tier):
    its = by_tier(tier)
    only = 0
    for it in its:
        vals = [int(c) for c in it["choices"]]
        b = vals[it["answer"]]
        if sum(v % 10 == b % 10 for v in vals) == 1:
            only += 1
    assert only / len(its) <= 0.25
    assert sum(1 for it in its if "TENS_SLIP" in it["misconceptions"]) / len(its) >= 0.75


@pytest.mark.parametrize("tier", range(1, 6))
def test_answer_positions_balanced(tier):
    its = by_tier(tier)
    for pos in range(4):
        share = sum(it["answer"] == pos for it in its) / len(its)
        assert 0.5 / 4 <= share <= 1.5 / 4


def test_determinism_and_item_count():
    import random
    again = G.generate(BAKED, random.Random(BAKED["seed"]))
    assert [(i["prompt"], i["choices"]) for i in again] == [(i["prompt"], i["choices"]) for i in ITEMS]
