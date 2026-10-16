"""facts-addition cartridge: golden misconception values, an independent re-check of every baked item,
the LIBRARY.md "Facts" bounds, and the anti-tell rules (near distractors, rank spread, ones digit)."""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator, load_manifest

CID = "facts-addition"
G = load_generator(CID)
MANIFEST = load_manifest(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
PROMPT_RE = re.compile(r"^(\d+) \+ (\d+) = \?$")
BANDS = {1: (2, 10), 2: (11, 20), 3: (21, 40), 4: (41, 70), 5: (71, 100)}


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def operands(it):
    m = PROMPT_RE.match(it["prompt"])
    assert m, it["prompt"]
    return int(m.group(1)), int(m.group(2))


def regroup(a, b):
    return a % 10 + b % 10 >= 10


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked prompt -> wrong value each key must give
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # tier, a, b, answer, {value: key}
    (1, 3, 5, 8, {7: "ONE_OFF", 9: "ONE_OFF", 2: "SUBTRACTED"}),
    (2, 8, 5, 13, {12: "ONE_OFF", 14: "ONE_OFF", 3: "SUBTRACTED", 23: "TENS_SLIP"}),   # |8-5| = 3 = s-10: first key listed wins
    (2, 9, 4, 13, {5: "SUBTRACTED", 3: "NO_CARRY", 23: "TENS_SLIP"}),
    (3, 27, 6, 33, {21: "SUBTRACTED", 23: "NO_CARRY", 43: "TENS_SLIP", 32: "ONE_OFF"}),
    (4, 38, 47, 85, {9: "SUBTRACTED", 75: "NO_CARRY", 95: "TENS_SLIP", 84: "ONE_OFF"}),
    (4, 34, 52, 86, {18: "SUBTRACTED", 76: "TENS_SLIP", 96: "TENS_SLIP", 87: "ONE_OFF"}),
    (5, 56, 29, 85, {27: "SUBTRACTED", 75: "NO_CARRY", 95: "TENS_SLIP"}),
]


@pytest.mark.parametrize("tier,a,b,s,wrong", GOLDEN, ids=[f"{g[1]}+{g[2]}" for g in GOLDEN])
def test_golden_candidate_keys(tier, a, b, s, wrong):
    assert a + b == s
    cand = G.candidates(tier, a, b)
    assert s not in cand
    for v, key in wrong.items():
        assert cand.get(v) == key, (v, key, cand)


def test_every_declared_key_is_used_and_every_used_key_declared():
    used = {k for it in ITEMS for k in it["misconceptions"] if k}
    declared = set(MANIFEST["misconceptions"]) | {"ARITH"}
    assert used <= declared
    assert set(MANIFEST["misconceptions"]) <= used


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked item (regex + plain Python, never the generator)
# ---------------------------------------------------------------------------------------------
def check_item(it):
    """Return a list of problems with one baked item (empty = fine)."""
    bad = []
    m = PROMPT_RE.match(it["prompt"])
    if not m:
        return ["prompt shape"]
    a, b = int(m.group(1)), int(m.group(2))
    s = a + b
    ch = it["choices"]
    if len(ch) != 4 or len(set(ch)) != 4:
        bad.append("four distinct choices")
    if not all(c.isdigit() for c in ch):
        return bad + ["non-integer choice"]
    vals = [int(c) for c in ch]
    if vals[it["answer"]] != s:
        bad.append("answer is not a + b")
    if sum(v == s for v in vals) != 1:
        bad.append("not exactly one right choice")
    if any(v < 0 or v > 999 for v in vals):
        bad.append("choice out of 0..999")
    if it["misconceptions"][it["answer"]] is not None:
        bad.append("answer carries a key")
    near = sum(abs(v - s) in (1, 2, 10) for k, v in enumerate(vals) if k != it["answer"])
    if near < 2:
        bad.append("fewer than 2 near distractors")
    lo, hi = BANDS[it["tier"]]
    if not lo <= s <= hi:
        bad.append("sum outside tier band")
    return bad


def test_every_baked_item_is_right():
    problems = [(it["id"], check_item(it)) for it in ITEMS if check_item(it)]
    assert not problems, problems[:5]


def test_checker_rejects_planted_bad_items():
    """Disproof: the checker must be able to fail."""
    good = next(it for it in ITEMS if it["tier"] == 3)
    assert check_item(good) == []
    a, b = operands(good)
    s = a + b

    wrong_answer = dict(good, choices=list(good["choices"]))
    other = (good["answer"] + 1) % 4
    wrong_answer["answer"] = other
    assert check_item(wrong_answer)

    shifted = dict(good, choices=[str(int(c) + 1) for c in good["choices"]])  # answer now a + b + 1
    assert "answer is not a + b" in check_item(shifted)

    far = dict(good, choices=list(good["choices"]))
    for k in range(4):
        if k != good["answer"]:
            far["choices"][k] = str(s + 31 + k)
    assert "fewer than 2 near distractors" in check_item(far)

    dup = dict(good, choices=[good["choices"][good["answer"]]] * 4)
    assert "four distinct choices" in check_item(dup)

    out_of_band = dict(good, prompt=f"{a} + {b + 90} = ?")
    assert check_item(out_of_band)


# ---------------------------------------------------------------------------------------------
# Counts, uniqueness, determinism
# ---------------------------------------------------------------------------------------------
def test_counts_and_unique_prompts():
    assert MANIFEST["grade"] == "Facts" and MANIFEST["picker_order"] == 1
    for t in range(1, 6):
        its = by_tier(t)
        assert len(its) == MANIFEST["items_per_tier"] == 40
        assert len({it["prompt"] for it in its}) == len(its)


def test_generator_is_deterministic():
    a = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    b = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    assert a == b


def test_answer_positions_balanced():
    for t in range(1, 6):
        pos = Counter(it["answer"] for it in by_tier(t))
        assert all(8 <= pos[p] <= 12 for p in range(4)), (t, pos)


# ---------------------------------------------------------------------------------------------
# Bounds (LIBRARY.md "Facts" table), asserted on baked.json
# ---------------------------------------------------------------------------------------------
def test_operand_bounds():
    for it in ITEMS:
        a, b = operands(it)
        t = it["tier"]
        minop = 1 if t == 1 else 2
        assert a >= minop and b >= minop, it["prompt"]
        lo, hi = BANDS[t]
        assert lo <= a + b <= hi, it["prompt"]
        if t == 2:
            assert min(a, b) <= 9, it["prompt"]


def test_tier2_crossing_ten_share():
    its = by_tier(2)
    cross = [it for it in its if max(operands(it)) <= 9 and sum(operands(it)) >= 11]
    assert len(cross) * 2 >= len(its)


@pytest.mark.parametrize("t", [3, 4, 5])
def test_upper_tier_mix(t):
    its = by_tier(t)
    n = len(its)
    ops = [operands(it) for it in its]
    assert sum(regroup(a, b) for a, b in ops) * 2 >= n
    assert sum(min(a, b) <= 9 and max(a, b) >= 10 for a, b in ops) * 4 >= n
    assert sum(a % 10 == 0 or b % 10 == 0 for a, b in ops) * 4 <= n


def test_wrong_choices_distinct_nonnegative_bounded():
    for it in ITEMS:
        vals = [int(c) for c in it["choices"]]
        assert len(set(vals)) == 4
        assert all(0 <= v <= 999 for v in vals)


# ---------------------------------------------------------------------------------------------
# Anti-tell rules
# ---------------------------------------------------------------------------------------------
def rank_of_answer(it):
    vals = [int(c) for c in it["choices"]]
    return sum(v < vals[it["answer"]] for v in vals)


@pytest.mark.parametrize("t", range(1, 6))
def test_no_middle_tell_rank_spread(t):
    its = by_tier(t)
    rc = Counter(rank_of_answer(it) for it in its)
    for r in range(4):
        share = rc[r] / len(its)
        assert 0.15 <= share <= 0.35, (t, r, share)


@pytest.mark.parametrize("t", range(1, 6))
def test_not_always_consecutive_neighbours(t):
    its = by_tier(t)
    tri = 0
    for it in its:
        vals = sorted(int(c) for c in it["choices"])
        s = int(it["choices"][it["answer"]])
        tri += {s - 1, s + 1} <= set(vals)
    assert tri / len(its) <= 0.5


def ones_alone(it):
    vals = [int(c) for c in it["choices"]]
    s = vals[it["answer"]]
    return all(v % 10 != s % 10 for k, v in enumerate(vals) if k != it["answer"])


@pytest.mark.parametrize("t", [3, 4, 5])
def test_no_ones_digit_tell(t):
    its = by_tier(t)
    alone = sum(ones_alone(it) for it in its)
    assert alone / len(its) <= 0.25, (t, alone)


def test_ones_digit_checker_can_fail():
    """Disproof: the ones-digit rule flags a planted tell and a tier built only from tells."""
    tell = {"choices": ["81", "82", "83", "85"], "answer": 3}
    assert ones_alone(tell)
    ok = {"choices": ["75", "84", "85", "95"], "answer": 2}
    assert not ones_alone(ok)
    planted_tier = [tell] * 10 + [ok] * 30
    assert sum(ones_alone(it) for it in planted_tier) / len(planted_tier) <= 0.25
    planted_tier = [tell] * 20 + [ok] * 20
    assert sum(ones_alone(it) for it in planted_tier) / len(planted_tier) > 0.25


def test_text_limits():
    for it in ITEMS:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160
        assert all(len(c) <= 14 for c in it["choices"])
    for m in MANIFEST["misconceptions"].values():
        assert len(m["student"]) <= 80
    assert len(MANIFEST["title"]) <= 32 and len(MANIFEST["subtitle"]) <= 40
    assert all(len(t["name"]) <= 24 for t in MANIFEST["tiers"])
