"""facts-sub-10 / -20 / -50 / -100 cartridges: one generator in four dirs, golden misconception values for each
prompt form, an independent re-check of every baked item, the tier pools and floors rebuilt from the words of
briefs/facts2/pools.py (not imported from the generator), the distractor / anti-tell rules on baked.json, and a
checker self-test with planted bad items."""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

RANGES = [10, 20, 50, 100]
IDS = [f"facts-sub-{r}" for r in RANGES]
GEN = {i: load_generator(i) for i in IDS}
BAKED = {}
for _i in IDS:
    with open(REPO_ROOT / "cartridges" / _i / "baked.json", encoding="utf-8") as _f:
        BAKED[_i] = json.load(_f)
PROMPT = re.compile(r"^(\d+|\?) ([+−×÷]) (\d+|\?) = (\d+|\?)$")
SUM_BAND = {10: (1, 10), 20: (11, 20), 50: (21, 50), 100: (51, 100)}


def rng_of(cid):
    return int(cid.rsplit("-", 1)[1])


def by_tier(cid, t, items=None):
    return [it for it in (BAKED[cid]["items"] if items is None else items) if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# The independent solver: the prompt alone, plain Python, never the generator
# ---------------------------------------------------------------------------------------------
def solve(prompt):
    """-> (form, a, b, answer) for 's − a = ?' (R), 's − ? = b' (C), '? − a = b' (S); pair (a, b), s = a + b."""
    m = PROMPT.match(prompt)
    assert m, prompt
    x, op, y, z = m.groups()
    assert op == "−" and [x, y, z].count("?") == 1, prompt
    if z == "?":
        return "R", int(y), int(x) - int(y), int(x) - int(y)
    if y == "?":
        return "C", int(x) - int(z), int(z), int(x) - int(z)
    return "S", int(y), int(z), int(z) + int(y)


# ---------------------------------------------------------------------------------------------
# Tier pools, rebuilt from the words of pools.py: PARTS[range][tier] = [(form, predicate(a, b), floor)]
# ---------------------------------------------------------------------------------------------
def traded(a, b):
    """Reading s − a: the ones of s are smaller than the ones of a (a trade); a + b makes a new ten."""
    return (a + b) % 10 < a % 10


def tens_operand(a, b):
    return (a > 0 and a % 10 == 0) or (b > 0 and b % 10 == 0)


def make_ten(a, b):
    return a + b == 10 and a >= 1 and b >= 1


def parts_for(r):
    lo, hi = SUM_BAND[r]
    inband = lambda a, b, low=0: lo <= a + b <= hi and a >= low and b >= low
    if r == 10:
        p1 = lambda a, b: inband(a, b)
        return {
            1: [("R", lambda a, b: p1(a, b) and min(a, b) <= 2, 0)],
            2: [("R", lambda a, b: p1(a, b) and min(a, b) >= 2, 0)],
            3: [("R", lambda a, b: p1(a, b) and min(a, b) >= 3, 8), ("C", make_ten, 4), ("S", make_ten, 4)],
            4: [("C", lambda a, b: p1(a, b) and min(a, b) >= 1, 0)],
            5: [("S", lambda a, b: 5 <= a + b <= 10 and min(a, b) >= 2, 12),
                ("C", lambda a, b: 5 <= a + b <= 10 and min(a, b) >= 2, 0)],
        }
    if r == 20:
        p = lambda a, b: inband(a, b, 1)
        missing = lambda a, b: p(a, b) and min(a, b) >= 2
        small = lambda a, b: missing(a, b) and max(a, b) <= 9
        return {
            1: [("R", lambda a, b: p(a, b) and max(a, b) >= 10 and a % 10 + b % 10 < 10, 0)],
            2: [("R", lambda a, b: missing(a, b) and (a == b or abs(a - b) == 1 or (9 in (a, b) and max(a, b) <= 9)), 0)],
            3: [("R", lambda a, b: p(a, b) and max(a, b) <= 9, 0)],
            4: [("C", small, 12), ("C", missing, 0)],
            5: [("S", small, 6), ("S", missing, 12), ("C", small, 0)],
        }
    p2 = lambda a, b: inband(a, b, 2)
    plain = lambda a, b: p2(a, b) and not tens_operand(a, b)
    no_reg = lambda a, b: plain(a, b) and not traded(a, b)
    reg = lambda a, b: plain(a, b) and traded(a, b)
    return {
        1: [("R", lambda a, b: inband(a, b, 1) and tens_operand(a, b), 0)],
        2: [("R", lambda a, b: no_reg(a, b) and min(a, b) <= 9, 8), ("R", lambda a, b: no_reg(a, b) and min(a, b) >= 10, 8)],
        3: [("R", lambda a, b: reg(a, b) and min(a, b) <= 9, 8), ("R", lambda a, b: reg(a, b) and min(a, b) >= 10, 8)],
        4: [("C", reg, 12), ("C", plain, 0)],
        5: [("S", reg, 6), ("S", plain, 12), ("C", reg, 6), ("C", plain, 0)],
    }


PARTS = {r: parts_for(r) for r in RANGES}


def in_tier_pools(r, tier, form, a, b):
    return any(f == form and pred(a, b) for f, pred, _ in PARTS[r][tier])


def floor_shortfalls(r, tier, its):
    pairs = [solve(it["prompt"]) for it in its]
    out = []
    for form, pred, floor in PARTS[r][tier]:
        got = sum(1 for f, a, b, _ in pairs if f == form and pred(a, b))
        if got < floor:
            out.append((form, floor, got))
    return out


# ---------------------------------------------------------------------------------------------
# The checker (also self-tested below with planted bad items)
# ---------------------------------------------------------------------------------------------
def problems(it, r=None):
    out = []
    try:
        form, a, b, ans = solve(it["prompt"])
    except AssertionError:
        return ["prompt shape"]
    vals = [int(c) for c in it["choices"]]
    if len(vals) != 4 or len(set(vals)) != 4:
        out.append("four distinct choices")
    if vals[it["answer"]] != ans:
        out.append("answer wrong")
    if sum(1 for v in vals if v == ans) != 1:
        out.append("exactly one right choice")
    if any(v < 0 or v > 999 for v in vals):
        out.append("range")
    wrong = [v for i, v in enumerate(vals) if i != it["answer"]]
    if sum(1 for v in wrong if abs(v - ans) in (1, 2, 10)) < 2:
        out.append("near distractors")
    if sum(1 for v in wrong if abs(v - ans) not in (1, 2, 10)) > 1:
        out.append("far distractors")
    if ans >= 20 and all(v % 10 != ans % 10 for v in wrong):
        out.append("ones-digit tell")
    if it["misconceptions"][it["answer"]] is not None:
        out.append("answer key")
    if r is not None:
        lo, hi = SUM_BAND[r]
        if not lo <= a + b <= hi:
            out.append("sum outside the range")
        if not in_tier_pools(r, it["tier"], form, a, b):
            out.append("pair outside the tier pools")
    return out


# ---------------------------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------------------------
def test_generators_byte_identical():
    blobs = {i: (REPO_ROOT / "cartridges" / i / "generator.py").read_bytes() for i in IDS}
    assert len(set(blobs.values())) == 1


@pytest.mark.parametrize("cid", IDS)
def test_manifest_shape(cid):
    b = BAKED[cid]
    assert b["grade"] == "Facts" and b["items_per_tier"] == 24 and b["version"] == "1.0.0"
    assert [t["tier"] for t in b["tiers"]] == [1, 2, 3, 4, 5]
    assert all(len(t["name"]) <= 24 and t["description"] for t in b["tiers"])
    assert len(b["title"]) <= 32 and len(b["subtitle"]) <= 40
    assert b["picker_order"] == 5 + RANGES.index(rng_of(cid))
    assert b["seed"] == 20261055 + RANGES.index(rng_of(cid))


# ---------------------------------------------------------------------------------------------
# Golden cases, hand-worked: (form, a, b) -> {value: key} for each prompt form
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # R  s − a = ?  (answer b)
    ("R", 6, 8, {9: "ONE_OFF", 7: "ONE_OFF", 20: "ADDED", 12: "SMALLER_FROM_LARGER", 18: "FORGOT_TRADE"}),       # 14 − 6
    ("R", 38, 14, {15: "ONE_OFF", 13: "ONE_OFF", 90: "ADDED", 26: "SMALLER_FROM_LARGER", 24: "FORGOT_TRADE",
                   4: "TENS_SLIP"}),                                                                              # 52 − 38
    ("R", 2, 34, {35: "ONE_OFF", 33: "ONE_OFF", 38: "ADDED", 44: "TENS_SLIP", 24: "TENS_SLIP"}),                  # 36 − 2
    ("R", 8, 2, {3: "ONE_OFF", 1: "ONE_OFF", 18: "ADDED"}),                                   # 10 − 8
    # C  s − ? = b  (answer a)
    ("C", 6, 8, {22: "MISSING_ADDED", 7: "MISSING_ONE_OFF", 5: "MISSING_ONE_OFF", 16: "MISSING_TENS"}),           # 14 − ? = 8
    ("C", 38, 14, {66: "MISSING_ADDED", 39: "MISSING_ONE_OFF", 37: "MISSING_ONE_OFF", 48: "MISSING_TENS",
                   28: "MISSING_TENS"}),                                                                          # 52 − ? = 14
    ("C", 6, 4, {14: "MISSING_ADDED", 7: "MISSING_ONE_OFF", 5: "MISSING_ONE_OFF", 8: "ARITH"}),                   # 10 − ? = 4
    # S  ? − a = b  (answer s)
    ("S", 6, 8, {2: "START_SUBTRACTED", 15: "MISSING_ONE_OFF", 13: "MISSING_ONE_OFF", 4: "START_NO_CARRY",
                 24: "MISSING_TENS"}),                                                                            # ? − 6 = 8
    ("S", 21, 34, {13: "START_SUBTRACTED", 56: "MISSING_ONE_OFF", 54: "MISSING_ONE_OFF", 65: "MISSING_TENS",
                   45: "MISSING_TENS"}),                                                                          # ? − 21 = 34
    ("S", 38, 14, {24: "START_SUBTRACTED", 53: "MISSING_ONE_OFF", 51: "MISSING_ONE_OFF", 42: "START_NO_CARRY",
                   62: "MISSING_TENS"}),                                                                          # ? − 38 = 14
]
ANSWER = {"R": lambda a, b: b, "C": lambda a, b: a, "S": lambda a, b: a + b}


@pytest.mark.parametrize("form,a,b,wrong", GOLDEN, ids=[f"{g[0]}-{g[1]}-{g[2]}" for g in GOLDEN])
def test_golden_misconception_values(form, a, b, wrong):
    for cid in IDS:  # the same generator in every dir
        got = {v: k for v, k in GEN[cid].wrong_candidates(form, a, b)}
        for v, key in wrong.items():
            assert got.get(v) == key, (cid, v, key, got)
        assert ANSWER[form](a, b) not in got


def test_golden_helpers_and_collisions():
    g = GEN["facts-sub-100"]
    assert g.smaller_from_larger(14, 6) == 12 and g.smaller_from_larger(52, 38) == 26
    assert g.regroups(6, 8) and g.regroups(38, 14) and not g.regroups(21, 34)
    # 52 − 37: SMALLER_FROM_LARGER and FORGOT_TRADE are both 25; the first key stays, once
    got = [(v, k) for v, k in g.wrong_candidates("R", 37, 15)]
    assert dict(got)[25] == "SMALLER_FROM_LARGER" and len({v for v, _ in got}) == len(got)


def test_prompts_and_answers_by_form():
    g = GEN["facts-sub-20"]
    assert g.prompt_of("R", 6, 8) == "14 − 6 = ?" and g.prompt_of("C", 6, 8) == "14 − ? = 8"
    assert g.prompt_of("S", 6, 8) == "? − 6 = 8"
    assert [g.answer_of(f, 6, 8) for f in "RCS"] == [8, 6, 14]
    assert [solve(g.prompt_of(f, 6, 8))[3] for f in "RCS"] == [8, 6, 14]


# ---------------------------------------------------------------------------------------------
# Every baked item, independently
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cid", IDS)
def test_every_item_rechecked_independently(cid):
    items = BAKED[cid]["items"]
    assert len(items) == 120
    bad = {it["prompt"]: problems(it, rng_of(cid)) for it in items if problems(it, rng_of(cid))}
    assert not bad, bad


@pytest.mark.parametrize("cid", IDS)
def test_counts_and_prompts_unique(cid):
    for t in range(1, 6):
        its = by_tier(cid, t)
        assert len(its) == 24
        assert len({it["prompt"] for it in its}) == 24


@pytest.mark.parametrize("cid", IDS)
def test_tier_floors_and_forms(cid):
    r = rng_of(cid)
    for t in range(1, 6):
        its = by_tier(cid, t)
        assert not floor_shortfalls(r, t, its), (t, floor_shortfalls(r, t, its))
        forms = Counter(solve(it["prompt"])[0] for it in its)
        assert set(forms) <= {f for f, _, _ in PARTS[r][t]}, forms


@pytest.mark.parametrize("cid", IDS)
def test_no_ambiguous_missing_number(cid):
    for it in BAKED[cid]["items"]:
        form, a, b, ans = solve(it["prompt"])
        assert a >= 0 and b >= 0
        if form == "S":
            assert a >= 1  # '? − 0 = b' would read as no change
        # s − ? = b and ? − a = b each have exactly one solution; check by brute force
        s = a + b
        if form == "C":
            assert [x for x in range(0, 1000) if s - x == b] == [a]
        if form == "S":
            assert [x for x in range(0, 1000) if x - a == b] == [s]


@pytest.mark.parametrize("cid", IDS)
def test_the_levels_climb_within_the_range(cid):
    """Easy to hard: the forms grow (R only, then C, then S) and the answers are never all one size."""
    items = BAKED[cid]["items"]
    forms = {t: Counter(solve(it["prompt"])[0] for it in by_tier(cid, t)) for t in range(1, 6)}
    assert forms[1]["C"] == 0 and forms[1]["S"] == 0 and forms[2]["C"] == 0 and forms[2]["S"] == 0
    assert forms[4]["C"] > 0 and forms[5]["S"] >= 6
    assert all(len({solve(it["prompt"])[3] for it in by_tier(cid, t)}) >= 6 for t in range(1, 6)), items[0]


# ---------------------------------------------------------------------------------------------
# Distractors and anti-tells on baked.json
# ---------------------------------------------------------------------------------------------
def rank(it):
    ans = int(it["choices"][it["answer"]])
    return sum(1 for c in it["choices"] if int(c) < ans)


def rank_shares_ok(its):
    n = len(its)
    c = Counter(rank(it) for it in its)
    return all(0.15 * n <= c[k] <= 0.35 * n for k in range(4))


@pytest.mark.parametrize("cid", IDS)
def test_wrong_choices_distinct_nonnegative_ints(cid):
    for it in BAKED[cid]["items"]:
        vals = [int(c) for c in it["choices"]]
        assert len(set(vals)) == 4 and all(0 <= v <= 999 for v in vals)
        ans = solve(it["prompt"])[3]
        wrong = [v for i, v in enumerate(vals) if i != it["answer"]]
        assert sum(1 for v in wrong if abs(v - ans) in (1, 2, 10)) >= 2
        assert sum(1 for v in wrong if abs(v - ans) not in (1, 2, 10)) <= 1


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_no_middle_tell_each_rank_15_to_35_percent(cid, t):
    assert rank_shares_ok(by_tier(cid, t)), Counter(rank(it) for it in by_tier(cid, t))


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_no_ones_digit_tell(cid, t):
    big = [it for it in by_tier(cid, t) if int(it["choices"][it["answer"]]) >= 20]
    only = sum(1 for it in big
               if all(int(c) % 10 != int(it["choices"][it["answer"]]) % 10
                      for i, c in enumerate(it["choices"]) if i != it["answer"]))
    if len(big) >= 8:
        assert only <= 0.25 * len(big), (only, len(big))
    assert only == 0, (only, len(big))  # the generator demands a twin for every answer of 20 or more


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_answer_positions_balanced(cid, t):
    c = Counter(it["answer"] for it in by_tier(cid, t))
    assert all(4 <= c[p] <= 8 for p in range(4)), c


@pytest.mark.parametrize("cid", IDS)
def test_keys_declared_used_and_labelled(cid):
    b = BAKED[cid]
    declared = set(b["misconceptions"]) | {"ARITH"}
    used = Counter()
    for it in b["items"]:
        for i, k in enumerate(it["misconceptions"]):
            assert (k is None) == (i == it["answer"])
            if k:
                assert k in declared, k
                used[k] += 1
    assert used["ARITH"] <= 0.40 * sum(used.values())
    for k in b["misconceptions"]:
        assert used[k] > 0, k
        assert len(b["misconceptions"][k]["student"]) <= 80


@pytest.mark.parametrize("cid", IDS)
def test_keys_match_their_rule_on_baked_items(cid):
    for it in BAKED[cid]["items"]:
        form, a, b, ans = solve(it["prompt"])
        s = a + b
        for c, k in zip(it["choices"], it["misconceptions"]):
            v = int(c)
            if k in ("ONE_OFF", "MISSING_ONE_OFF"):
                assert abs(v - ans) == 1 and (form == "R") == (k == "ONE_OFF")
            elif k == "ADDED":
                assert form == "R" and v == s + a
            elif k == "MISSING_ADDED":
                assert form == "C" and v == s + b
            elif k == "START_SUBTRACTED":
                assert form == "S" and v == abs(b - a)
            elif k == "START_NO_CARRY":
                assert form == "S" and v == s - 10 and a % 10 + b % 10 >= 10
            elif k == "FORGOT_TRADE":
                assert form == "R" and v == b + 10 and s % 10 < a % 10
            elif k == "SMALLER_FROM_LARGER":
                assert form == "R" and s % 10 < a % 10
                dig = lambda n: str(n).zfill(3)
                assert v == int("".join(str(abs(int(x) - int(y))) for x, y in zip(dig(s), dig(a))))
            elif k in ("TENS_SLIP", "MISSING_TENS"):
                assert abs(v - ans) == 10 and s >= 11 and (form == "R") == (k == "TENS_SLIP")


@pytest.mark.parametrize("cid", IDS)
def test_text_limits_and_charset(cid):
    ok = set(chr(c) for c in range(32, 127)) | set("×÷−≤≥≠√π")
    for it in BAKED[cid]["items"]:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160
        assert all(len(c) <= 14 for c in it["choices"])
        for text in (it["prompt"], it["explanation"], *it["choices"]):
            assert set(text) <= ok, text


@pytest.mark.parametrize("cid", IDS)
def test_explanations_state_the_fact(cid):
    for it in BAKED[cid]["items"]:
        form, a, b, ans = solve(it["prompt"])
        s = a + b
        e = it["explanation"]
        if form == "R":
            assert f"{s} − {a}" in e and str(b) in e, e
        elif form == "C":
            assert e.startswith(it["prompt"]) and f"{s} − {a} = {b}" in e and f"? = {a}" in e, e
        else:
            assert e.startswith(it["prompt"]) and f"? = {s}" in e and f"{b} + {a} = {s}" in e, e


@pytest.mark.parametrize("cid", IDS)
def test_generator_is_deterministic(cid):
    m = {k: v for k, v in BAKED[cid].items() if k not in ("items", "baked_with")}
    first = GEN[cid].generate(m, random.Random(m["seed"]))
    again = GEN[cid].generate(m, random.Random(m["seed"]))
    assert first == again
    assert [{k: v for k, v in it.items() if k != "id"} for it in BAKED[cid]["items"]] == first


# ---------------------------------------------------------------------------------------------
# Checker self-test: planted bad items the checker must reject
# ---------------------------------------------------------------------------------------------
def test_checker_rejects_planted_items():
    good = dict(by_tier("facts-sub-20", 1)[0])
    assert problems(good, 20) == []
    form, a, b, ans = solve(good["prompt"])
    assert "answer wrong" in problems(dict(good, answer=(good["answer"] + 1) % 4))
    assert "four distinct choices" in problems(dict(good, choices=[good["choices"][0]] * 4))
    far = dict(good, choices=[str(ans), str(ans + 40), str(ans + 50), str(ans + 60)], answer=0,
               misconceptions=[None, "ARITH", "ARITH", "ARITH"])
    assert "near distractors" in problems(far) and "far distractors" in problems(far)
    assert "prompt shape" in problems(dict(good, prompt="7 + 8 = ?"))
    assert "prompt shape" in problems(dict(good, prompt="? − ? = 8"))
    assert "range" in problems(dict(good, choices=[str(ans), "1000", "5", "6"], answer=0))
    # a pair outside the tier's pools: 17 − 9 = ? is a tier 3 fact (both one digit), not tier 1
    out_of_tier = dict(good, tier=1, prompt="17 − 9 = ?", choices=["8", "7", "9", "6"], answer=0,
                       misconceptions=[None, "ONE_OFF", "ONE_OFF", "ARITH"])
    assert "pair outside the tier pools" in problems(out_of_tier, 20)
    out_of_range = dict(out_of_tier, tier=3, prompt="30 − 9 = ?", choices=["21", "20", "22", "31"], answer=0)
    assert "sum outside the range" in problems(out_of_range, 20)
    # the ones-digit tell: answer 27 with no wrong choice ending in 7
    tell = dict(good, tier=3, prompt="34 − 7 = ?", choices=["27", "26", "28", "41"], answer=0,
                misconceptions=[None, "ONE_OFF", "ONE_OFF", "ADDED"])
    assert "ones-digit tell" in problems(tell, 50)


def test_floor_and_rank_checkers_can_fail():
    its = by_tier("facts-sub-50", 3)
    assert not floor_shortfalls(50, 3, its)
    only_two_digit = [it for it in its if solve(it["prompt"])[2] >= 10 and solve(it["prompt"])[1] >= 10][:3]
    assert floor_shortfalls(50, 3, only_two_digit)  # too few of every part
    planted = [dict(it, choices=["1", "2", "3", "4"], answer=1) for it in by_tier("facts-sub-10", 1)]
    assert not rank_shares_ok(planted)  # always rank 1


def test_sub_10_has_no_tens_keys_or_plus_minus_10_values():
    banned = {"FORGOT_TRADE", "START_NO_CARRY", "TENS_SLIP", "MISSING_TENS", "SMALLER_FROM_LARGER"}
    b = BAKED["facts-sub-10"]
    assert not banned & set(b["misconceptions"])
    for it in b["items"]:
        ans = solve(it["prompt"])[3]
        assert not banned & set(k for k in it["misconceptions"] if k)
        assert all(abs(int(c) - ans) != 10 for c in it["choices"]), it
    # the generator never offers them for a minuend of 10 or less (10 - 8: 12 was FORGOT_TRADE)
    g = GEN["facts-sub-10"]
    assert all(abs(v - 2) != 10 and k not in banned for v, k in g.wrong_candidates("R", 8, 2))


def test_no_ascii_hyphen_subtraction_and_no_more_is_in_texts():
    for cid in IDS:
        b = BAKED[cid]
        for v in b["misconceptions"].values():
            assert " - " not in v["student"], v["student"]
        for it in b["items"]:
            assert "more is" not in it["explanation"], it["explanation"]
