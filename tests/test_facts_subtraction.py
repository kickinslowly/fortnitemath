"""facts-subtraction cartridge: golden misconception values, an independent re-check of every baked
item, the PROTOCOL 4c / LIBRARY.md "Facts" bounds on baked.json, and the anti-tell rules."""
import json
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "facts-subtraction"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
PROMPT = re.compile(r"^(\d+) − (\d+) = \?$")
BANDS = {1: (2, 10), 2: (11, 20), 3: (21, 40), 4: (41, 70), 5: (71, 100)}


def by_tier(t, items=None):
    return [it for it in (ITEMS if items is None else items) if it["tier"] == t]


def parse(it):
    m = PROMPT.match(it["prompt"])
    assert m, it["prompt"]
    return int(m.group(1)), int(m.group(2))


# ---------------------------------------------------------------------------------------------
# Golden cases, hand-worked: prompt -> {key: wrong value}
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # (tier, s, a, answer, {value: key})
    (2, 14, 6, 8, {9: "ONE_OFF", 7: "ONE_OFF", 20: "ADDED", 12: "SMALLER_FROM_LARGER", 18: "FORGOT_TRADE"}),
    (4, 52, 38, 14, {15: "ONE_OFF", 13: "ONE_OFF", 90: "ADDED", 26: "SMALLER_FROM_LARGER",
                     24: "FORGOT_TRADE", 4: "TENS_SLIP"}),
    (3, 34, 7, 27, {28: "ONE_OFF", 26: "ONE_OFF", 41: "ADDED", 37: "FORGOT_TRADE", 17: "TENS_SLIP"}),
    (3, 36, 2, 34, {35: "ONE_OFF", 33: "ONE_OFF", 38: "ADDED", 44: "TENS_SLIP", 24: "TENS_SLIP"}),
    (1, 10, 8, 2, {3: "ONE_OFF", 1: "ONE_OFF", 18: "ADDED", 12: "FORGOT_TRADE"}),
]


@pytest.mark.parametrize("tier,s,a,b,wrong", GOLDEN, ids=[f"{g[1]}-{g[2]}" for g in GOLDEN])
def test_golden_misconception_values(tier, s, a, b, wrong):
    got = {v: k for v, k in G.wrong_candidates(s, a, tier)}
    for v, key in wrong.items():
        assert got.get(v) == key, (v, key, got)
    assert b not in got


def test_golden_smaller_from_larger_and_regroup():
    assert G.smaller_from_larger(14, 6) == 12
    assert G.smaller_from_larger(52, 38) == 26
    assert G.regroups(14, 6) and G.regroups(52, 38) and not G.regroups(57, 23)


def test_collisions_keep_the_first_key():
    # 52 − 37: SMALLER_FROM_LARGER and FORGOT_TRADE are both 25 (LIBRARY.md): kept once, first key.
    got = {v: k for v, k in G.wrong_candidates(52, 37, 4)}
    assert got[25] == "SMALLER_FROM_LARGER"
    assert len(got) == len(G.wrong_candidates(52, 37, 4))


# ---------------------------------------------------------------------------------------------
# The checker (also self-tested below with planted bad items)
# ---------------------------------------------------------------------------------------------
def problems(it):
    """Independent problems with one item: plain Python on the parsed prompt, never the generator."""
    out = []
    m = PROMPT.match(it["prompt"])
    if not m:
        return ["prompt shape"]
    s, a = int(m.group(1)), int(m.group(2))
    b = s - a
    vals = [int(c) for c in it["choices"]]
    if len(vals) != 4 or len(set(vals)) != 4:
        out.append("four distinct choices")
    if vals[it["answer"]] != b:
        out.append("answer wrong")
    if sum(1 for v in vals if v == b) != 1:
        out.append("exactly one right choice")
    if any(v < 0 or v > 999 for v in vals):
        out.append("range")
    wrong = [v for i, v in enumerate(vals) if i != it["answer"]]
    if sum(1 for v in wrong if abs(v - b) in (1, 2, 10)) < 2:
        out.append("near distractors")
    if sum(1 for v in wrong if abs(v - b) not in (1, 2, 10)) > 1:
        out.append("far distractors")
    if it["misconceptions"][it["answer"]] is not None:
        out.append("answer key")
    return out


def test_every_item_rechecked_independently():
    assert len(ITEMS) == 200
    bad = {it["prompt"]: problems(it) for it in ITEMS if problems(it)}
    assert not bad, bad


def test_checker_rejects_planted_items():
    good = dict(ITEMS[0])
    assert problems(good) == []
    wrong_answer = dict(good, answer=(good["answer"] + 1) % 4)
    assert "answer wrong" in problems(wrong_answer)
    dup = dict(good, choices=[good["choices"][0]] * 4)
    assert "four distinct choices" in problems(dup)
    s, a = parse(good)
    far = dict(good, choices=[str(s - a), str(s - a + 40), str(s - a + 50), str(s - a + 60)], answer=0,
               misconceptions=[None, "ARITH", "ARITH", "ARITH"])
    assert "near distractors" in problems(far) and "far distractors" in problems(far)
    assert "prompt shape" in problems(dict(good, prompt="7 + 8 = ?"))
    assert "range" in problems(dict(good, choices=[good["choices"][good["answer"]], "1000", "5", "6"],
                                    answer=0))


# ---------------------------------------------------------------------------------------------
# Bounds on baked.json
# ---------------------------------------------------------------------------------------------
def test_counts_and_prompts_unique():
    for t in range(1, 6):
        its = by_tier(t)
        assert len(its) == BAKED["items_per_tier"] == 40
        assert len({it["prompt"] for it in its}) == 40


def test_tier_bands():
    for t, (lo, hi) in BANDS.items():
        for it in by_tier(t):
            s, a = parse(it)
            b = s - a
            assert lo <= s <= hi, it["prompt"]
            assert a >= 1 and b >= 1, it["prompt"]
            if t >= 2:
                assert a >= 2 and b >= 2, it["prompt"]
            if t == 2:
                assert min(a, b) <= 9, it["prompt"]


def test_tier2_crossing_ten_share():
    its = by_tier(2)
    crossing = sum(1 for it in its if parse(it)[1] <= 9 and parse(it)[0] % 10 < parse(it)[1])
    assert crossing >= len(its) / 2, crossing


@pytest.mark.parametrize("t", [3, 4, 5])
def test_upper_tier_mix(t):
    its = by_tier(t)
    n = len(its)
    regroup = sum(1 for it in its if parse(it)[0] % 10 < parse(it)[1] % 10)
    one_digit = sum(1 for it in its if parse(it)[1] < 10)
    m10 = sum(1 for it in its
              if any(x % 10 == 0 for x in (parse(it)[0], parse(it)[1], parse(it)[0] - parse(it)[1])))
    assert regroup >= n / 2, regroup
    assert one_digit >= n / 4, one_digit
    assert m10 <= n / 4, m10


def test_wrong_choices_distinct_nonnegative_ints():
    for it in ITEMS:
        vals = [int(c) for c in it["choices"]]
        assert len(set(vals)) == 4
        assert all(0 <= v <= 999 for v in vals)


# ---------------------------------------------------------------------------------------------
# Anti-tells
# ---------------------------------------------------------------------------------------------
def rank(it):
    b = int(it["choices"][it["answer"]])
    return sum(1 for c in it["choices"] if int(c) < b)


def tier_rank_shares_ok(its):
    n = len(its)
    c = Counter(rank(it) for it in its)
    return all(0.15 * n <= c[r] <= 0.35 * n for r in range(4))


@pytest.mark.parametrize("t", range(1, 6))
def test_no_middle_tell_each_rank_15_to_35_percent(t):
    assert tier_rank_shares_ok(by_tier(t)), Counter(rank(it) for it in by_tier(t))


def test_rank_checker_rejects_a_planted_tier():
    planted = [dict(it, choices=["1", "2", "3", "4"], answer=1) for it in by_tier(1)]  # always rank 1
    assert not tier_rank_shares_ok(planted)


@pytest.mark.parametrize("t", [3, 4, 5])
def test_no_ones_digit_tell(t):
    its = by_tier(t)
    only = 0
    for it in its:
        b = int(it["choices"][it["answer"]])
        if all(int(c) % 10 != b % 10 for i, c in enumerate(it["choices"]) if i != it["answer"]):
            only += 1
    assert only <= len(its) * 0.25, only


@pytest.mark.parametrize("t", range(1, 6))
def test_answer_positions_balanced(t):
    c = Counter(it["answer"] for it in by_tier(t))
    assert all(0.125 * 40 <= c[p] <= 0.375 * 40 for p in range(4)), c


def test_keys_declared_and_wrong_choices_labelled():
    declared = set(BAKED["misconceptions"]) | {"ARITH"}
    used = Counter()
    for it in ITEMS:
        for i, k in enumerate(it["misconceptions"]):
            assert (k is None) == (i == it["answer"])
            if k:
                assert k in declared
                used[k] += 1
    # modelled misconceptions dominate, ARITH only fills
    assert used["ARITH"] <= 0.35 * sum(used.values())
    for k in BAKED["misconceptions"]:
        assert used[k] > 0, k


def test_keys_match_their_rule_on_baked_items():
    for it in ITEMS:
        s, a = parse(it)
        b = s - a
        for c, k in zip(it["choices"], it["misconceptions"]):
            v = int(c)
            if k == "ADDED":
                assert v == s + a
            elif k == "ONE_OFF":
                assert abs(v - b) == 1
            elif k == "FORGOT_TRADE":
                assert v == b + 10 and s % 10 < a % 10
            elif k == "TENS_SLIP":
                assert abs(v - b) == 10
            elif k == "SMALLER_FROM_LARGER":
                assert s % 10 < a % 10
                digits = lambda n: str(n).zfill(3)
                assert v == int("".join(str(abs(int(x) - int(y)))
                                        for x, y in zip(digits(s), digits(a))))


def test_text_limits_and_charset():
    ok = set(chr(c) for c in range(32, 127)) | set("×÷−≤≥≠√π")
    for it in ITEMS:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160
        assert all(len(c) <= 14 for c in it["choices"])
        for text in (it["prompt"], it["explanation"], *it["choices"]):
            assert set(text) <= ok, text
    for v in BAKED["misconceptions"].values():
        assert len(v["student"]) <= 80


def test_explanations_state_the_right_answer():
    for it in ITEMS:
        s, a = parse(it)
        assert f"{s} − {a}" in it["explanation"]
        assert str(s - a) in it["explanation"]


def test_generator_is_deterministic():
    import random
    m = {k: v for k, v in BAKED.items() if k not in ("items", "baked_with")}
    first = G.generate(m, random.Random(m["seed"]))
    again = G.generate(m, random.Random(m["seed"]))
    assert first == again
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == first
