"""facts-mul-5 / -10 / -12 / -15 (the times-tables range cartridges): the four generators are one file, golden
misconception values per prompt form, an independent re-check of EVERY baked item (parsed from the prompt text, solved
with plain Python), every item's form and pair inside its tier's pools (rebuilt here from the words of
briefs/facts2/pools.py, not imported from the generator), the parts' floors, the distractor rules and rank spread on
baked.json, and a checker self-test (planted bad items must fail).
"""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

RANGES = (5, 10, 12, 15)
CIDS = {n: f"facts-mul-{n}" for n in RANGES}
GEN = {n: load_generator(c) for n, c in CIDS.items()}
BAKED = {}
for _n, _c in CIDS.items():
    with open(REPO_ROOT / "cartridges" / _c / "baked.json", encoding="utf-8") as _f:
        BAKED[_n] = json.load(_f)
ALL = [(n, it) for n in RANGES for it in BAKED[n]["items"]]
PROMPT_RE = re.compile(r"^(\d+|\?) ([+−×÷]) (\d+|\?) = (\d+|\?)$")


def by_tier(n, t):
    return [it for it in BAKED[n]["items"] if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# The pools, rebuilt independently from the words of pools.py: tier -> [(form, set of pairs, floor)]
# ---------------------------------------------------------------------------------------------
def grid(n, low=0):
    return {(a, b) for a in range(low, n + 1) for b in range(low, n + 1)}


E, M, H = {0, 1, 2, 5, 10}, {3, 4, 9}, {6, 7, 8}
C6 = M | H


def touches(xs, s):
    return {x for x in xs if s & set(x)}


def within(xs, s):
    return {x for x in xs if set(x) <= s}


def easy_fact(x):
    return bool(E & set(x)) or (11 in x and min(x) <= 9)


def pools(n):
    g = grid(n)
    if n == 5:
        return {
            1: [("R", touches(g, {0, 1, 2, 5}), 0)],
            2: [("R", grid(5, 1), 0)],
            3: [("R", grid(5, 2), 12), ("C", {x for x in grid(5, 1) if x[0] in (2, 5)}, 8)],
            4: [("C", grid(5, 1), 0)],
            5: [("S", grid(5, 2), 12), ("C", grid(5, 2), 0)],
        }
    if n == 10:
        core = within(g, C6)
        return {
            1: [("R", touches(g, E), 0)],
            2: [("R", within(core, M), 8), ("R", touches(core, M), 0)],
            3: [("R", within(core, H), 8), ("R", touches(core, H), 0)],
            4: [("C", core, 12), ("C", grid(10, 2), 0)],
            5: [("S", core, 12), ("C", core, 0)],
        }
    if n == 12:
        core = within(g, C6)
        t1 = {x for x in g if easy_fact(x)}
        core12 = {x for x in grid(12, 3) if not easy_fact(x)}
        t2_new = {x for x in g if 12 in x and min(x) in M}
        t3_new = {x for x in g if not easy_fact(x) and max(x) >= 11 and (H & set(x) or min(x) >= 11)}
        top = lambda xs: {x for x in xs if max(x) >= 11}
        return {
            1: [("R", top(t1), 8), ("R", t1, 0)],
            2: [("R", t2_new, 6), ("R", within(core, M), 6), ("R", touches(core, M), 0)],
            3: [("R", t3_new, 8), ("R", within(core, H), 6), ("R", touches(core, H), 0)],
            4: [("C", top(core12), 6), ("C", core, 8), ("C", grid(12, 2), 0)],
            5: [("S", top(core12), 6), ("S", core12, 6), ("C", top(core12), 4), ("C", core12, 0)],
        }
    g = grid(15)
    t1 = {x for x in g if easy_fact(x)}
    teen = lambda xs: {x for x in xs if max(x) >= 11}
    hard = {x for x in grid(15, 3) if not easy_fact(x)}
    core = within(g, C6)
    return {
        1: [("R", teen(t1), 12), ("R", t1, 0)],
        2: [("R", {x for x in teen(g) if not easy_fact(x) and min(x) in (3, 4)}, 12), ("R", touches(core, M), 0)],
        3: [("R", {x for x in teen(g) if not easy_fact(x) and (min(x) in (6, 7, 8, 9) or min(x) >= 11)}, 12),
            ("R", touches(core, H), 0)],
        4: [("C", teen(hard), 12), ("C", hard, 0)],
        5: [("S", teen(hard), 8), ("S", hard, 4), ("C", teen(hard), 4), ("C", hard, 0)],
    }


POOLS = {n: pools(n) for n in RANGES}
TIERS = range(1, 6)


# ---------------------------------------------------------------------------------------------
# The independent checker: everything wrong with one baked item (empty = fine). Never calls the generator.
# ---------------------------------------------------------------------------------------------
def read(prompt):
    """(form, a, b, p, answer) from the prompt text alone, solved with plain Python."""
    m = PROMPT_RE.match(prompt)
    assert m, prompt
    x, op, y, z = m.groups()
    assert op == "×" and [x, y, z].count("?") == 1, prompt
    if z == "?":
        return "R", int(x), int(y), int(x) * int(y), int(x) * int(y)
    if y == "?":
        assert int(x) > 0 and int(z) % int(x) == 0, prompt
        return "C", int(x), int(z) // int(x), int(z), int(z) // int(x)
    assert int(y) > 0 and int(z) % int(y) == 0, prompt
    return "S", int(z) // int(y), int(y), int(z), int(z) // int(y)


def near(form, a, b):
    return max(a, b, 2) if form == "R" else 2


def problems(it, n):
    out = []
    try:
        form, a, b, p, ans = read(it["prompt"])
    except AssertionError:
        return ["prompt shape"]
    ch = [int(c) for c in it["choices"]]
    if len(ch) != 4 or len(set(ch)) != 4:
        out.append("choices not 4 distinct")
    if ch[it["answer"]] != ans:
        out.append("answer wrong")
    if sum(1 for c in ch if c == ans) != 1:
        out.append("answer not unique")
    wrong = [c for i, c in enumerate(ch) if i != it["answer"]]
    if any(c < 0 or c > 999 for c in wrong):
        out.append("wrong choice out of range")
    if form != "R" and min(a, b) < 1:
        out.append("zero factor missing")
    if max(a, b) > n:
        out.append("factor over range")
    if (form, (a, b)) not in {(f, x) for f, xs, _ in POOLS[n][it["tier"]] for x in xs}:
        out.append("pair outside the tier's pools")
    lim = near(form, a, b)
    if sum(1 for c in wrong if abs(c - ans) <= lim) < 2:
        out.append("fewer than 2 near values")
    if sum(1 for c in wrong if abs(c - ans) > lim) > 1:
        out.append("more than 1 far value")
    if form == "R" and max(a, b) >= 11 and p >= 20 and not any(c % 10 == p % 10 for c in wrong):
        out.append("ones-digit tell")
    if [m is None for m in it["misconceptions"]] != [i == it["answer"] for i in range(4)]:
        out.append("misconception null placement")
    return out


# ---------------------------------------------------------------------------------------------
# One generator file
# ---------------------------------------------------------------------------------------------
def test_generators_are_byte_identical():
    blobs = {(REPO_ROOT / "cartridges" / c / "generator.py").read_bytes() for c in CIDS.values()}
    assert len(blobs) == 1


# ---------------------------------------------------------------------------------------------
# Golden cases: each misconception key gives its expected wrong value on a hand-worked prompt of each form
# ---------------------------------------------------------------------------------------------
def _group(pairs):
    d = {}
    for k, v in pairs:
        d.setdefault(k, []).append(v)
    return d


G = GEN[15]


def test_golden_r_group_off():
    # 7 x 8 = 56: 7 x 9 = 63, 8 x 8 = 64, 7 x 7 = 49, 6 x 8 = 48
    assert sorted(_group(G.candidates("R", 7, 8))["GROUP_OFF"]) == [48, 49, 63, 64]
    # 0 x 5 = 0: 0 x 6 and 0 x 4 are the answer (dropped), (0 - 1) x 5 < 0 (dropped); only 1 x 5 = 5 stays
    assert _group(G.candidates("R", 0, 5))["GROUP_OFF"] == [5]


def test_golden_r_added():
    assert _group(G.candidates("R", 7, 8))["ADDED"] == [15]
    assert _group(G.candidates("R", 4, 3))["ADDED"] == [7]


def test_golden_r_dropped_carry_tens_slip_partial_products():
    g = _group(G.candidates("R", 13, 6))  # 78 = 60 + 18; losing the ten of 18 gives 68
    assert g["DROPPED_CARRY"] == [68] and g["TENS_SLIP"] == [88]
    assert _group(G.candidates("R", 6, 13))["DROPPED_CARRY"] == [68]
    g = _group(G.candidates("R", 12, 3))  # 36: ones product 6 does not carry
    assert "DROPPED_CARRY" not in g and sorted(g["TENS_SLIP"]) == [26, 46]
    assert _group(G.candidates("R", 13, 14))["PARTIAL_PRODUCTS"] == [112]  # 10 x 10 + 3 x 4
    assert _group(G.candidates("R", 11, 12))["PARTIAL_PRODUCTS"] == [102]
    # the last three exist only where a factor is 11 or more: 10 x 7 and 9 x 9 have GROUP_OFF and ADDED only
    for a, b in ((10, 7), (9, 9), (10, 10)):
        assert set(_group(G.candidates("R", a, b))) <= {"GROUP_OFF", "ADDED"}
    for a, b in ((12, 11), (14, 9), (15, 15)):
        for v in _group(G.candidates("R", a, b)).get("TENS_SLIP", []):
            assert v % 10 == (a * b) % 10


def test_golden_c_forms():
    # 6 x ? = 42 (answer 7, shown 6)
    g = _group(G.candidates("C", 6, 7))
    assert sorted(g["MISSING_ONE_OFF"]) == [6, 8] and g["MISSING_SUBTRACTED"] == [36] and g["MISSING_PRODUCT"] == [42]
    # 12 x ? = 84: answer 7
    g = _group(G.candidates("C", 12, 7))
    assert sorted(g["MISSING_ONE_OFF"]) == [6, 8] and g["MISSING_SUBTRACTED"] == [72] and g["MISSING_PRODUCT"] == [84]


def test_golden_s_forms():
    # ? x 7 = 42 (answer 6, shown 7)
    g = _group(G.candidates("S", 6, 7))
    assert sorted(g["MISSING_ONE_OFF"]) == [5, 7] and g["MISSING_SUBTRACTED"] == [35] and g["MISSING_PRODUCT"] == [42]
    # ? x 12 = 84: answer 7, shown 12
    g = _group(G.candidates("S", 7, 12))
    assert sorted(g["MISSING_ONE_OFF"]) == [6, 8] and g["MISSING_SUBTRACTED"] == [72] and g["MISSING_PRODUCT"] == [84]


def test_golden_a_key_that_yields_the_answer_is_dropped():
    assert 4 not in dict((v, k) for k, v in G.candidates("R", 2, 2))  # ADDED 2 + 2 = 4 is the answer
    assert dict((v, k) for k, v in G.candidates("C", 2, 2)) == {3: "MISSING_ONE_OFF", 1: "MISSING_ONE_OFF",
                                                              4: "MISSING_PRODUCT"}  # p - k = 2 is the answer
    # 1 x 1 = 1: GROUP_OFF gives 2 and 0; ADDED 2 collides (first key wins)
    assert dict((v, k) for k, v in G.candidates("R", 1, 1)) == {2: "GROUP_OFF", 0: "GROUP_OFF"}


def test_golden_arith_only_fills():
    assert [v for _, v in G.fill_values("R", 1, 1, {0, 2})] == [3, 4]
    assert [v for _, v in G.fill_values("C", 6, 7, set())] == [6, 8, 5, 9, 4, 10]  # answer 7, +-1, +-2, +-3


def test_golden_explanations():
    assert G.explain("R", 7, 8) == "7 × 8 = 56: 7 × 7 = 49, plus one more 7 = 56."
    assert G.explain("R", 13, 6) == "13 × 6 = 78: split 13 into 10 and 3. 60 + 18 = 78."
    assert G.explain("R", 9, 7) == "9 × 7 = 63: 10 × 7 = 70, minus one 7 = 63."
    assert G.explain("R", 5, 6) == "5 × 6 = 30: half of 6 × 10 = 60, and half of 60 is 30."
    assert G.explain("R", 6, 8) == "6 × 8 = 48: split 6 into 5 and 1. 5 × 8 = 40, 1 × 8 = 8, total 48."
    assert G.explain("R", 0, 9) == "0 × 9 = 0: no groups, or groups of nothing, make 0. Anything times 0 is 0."
    assert G.explain("C", 6, 7) == "6 × ? = 42: 6 × 7 = 42, so ? = 7. Count by 6s up to 42, or divide: 42 ÷ 6 = 7."
    assert G.explain("S", 6, 7) == "? × 7 = 42: 6 × 7 = 42, so ? = 6. Count by 7s up to 42, or divide: 42 ÷ 7 = 6."
    assert G.explain("C", 2, 9) == "2 × ? = 18: 2 × 9 = 18, so ? = 9. Half of 18 is 9."
    assert G.explain("S", 4, 10) == "? × 10 = 40: 4 × 10 = 40, so ? = 4. Drop the zero from 40: 4."


# ---------------------------------------------------------------------------------------------
# Independent re-check of EVERY baked item
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", RANGES)
def test_item_counts_and_manifest(n):
    b = BAKED[n]
    assert b["id"] == CIDS[n] and b["grade"] == "Facts" and b["items_per_tier"] == 24
    assert len(b["items"]) == 5 * 24
    for t in TIERS:
        assert len(by_tier(n, t)) == 24
    assert len(b["tiers"]) == 5 and all(len(t["name"]) <= 24 for t in b["tiers"])


@pytest.mark.parametrize("n,it", ALL, ids=[f"{n}-t{i['tier']}-{i['prompt']}" for n, i in ALL])
def test_every_item_rechecked(n, it):
    assert problems(it, n) == []
    form, a, b, p, ans = read(it["prompt"])
    assert int(it["choices"][it["answer"]]) == ans
    assert it["explanation"].startswith(f"{it['prompt']}: " if form != "R" else f"{a} × {b} = {p}: ")
    if form != "R":
        assert f"{a} × {b} = {p}, so ? = {ans}." in it["explanation"]
    assert len(it["explanation"]) <= 160
    assert "÷" not in it["prompt"] and "0 ÷" not in it["prompt"]


@pytest.mark.parametrize("n", RANGES)
def test_prompts_unique_per_tier(n):
    for t in TIERS:
        ps = [it["prompt"] for it in by_tier(n, t)]
        assert len(ps) == len(set(ps))


# ---------------------------------------------------------------------------------------------
# Pools: form + pair in the tier's pools, floors, no 0 factor in a missing-number prompt
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", RANGES)
def test_pools_membership_and_floors(n):
    for t in TIERS:
        its = [read(it["prompt"]) for it in by_tier(n, t)]
        keyed = {(f, (a, b)) for f, a, b, _, _ in its}
        union = {(f, x) for f, xs, _ in POOLS[n][t] for x in xs if f == "R" or min(x) >= 1}
        assert keyed <= union, (n, t, sorted(keyed - union))
        for form, xs, floor in POOLS[n][t]:
            have = sum(1 for k in keyed if k[0] == form and k[1] in xs)
            assert have >= floor, (n, t, form, have, floor)
        for f, a, b, _, _ in its:
            assert f == "R" or min(a, b) >= 1


@pytest.mark.parametrize("n", RANGES)
def test_every_pool_floor_is_reachable_and_tiers_have_enough_prompts(n):
    for t in TIERS:
        union = {(f, x) for f, xs, _ in POOLS[n][t] for x in xs if f == "R" or min(x) >= 1}
        assert len(union) >= 24
        assert sum(fl for _, _, fl in POOLS[n][t]) <= 24


@pytest.mark.parametrize("n", RANGES)
def test_zero_factor_prompts_are_capped(n):
    for t in TIERS:
        zeros = sum(1 for it in by_tier(n, t) if re.search(r"(^| )0 ×|× 0 =", it["prompt"]))
        assert zeros <= 6


@pytest.mark.parametrize("n", RANGES)
def test_forms_by_tier(n):
    """R tiers are R only; the missing-number tiers 4-5 never show R."""
    for t in TIERS:
        forms = {read(it["prompt"])[0] for it in by_tier(n, t)}
        allowed = {f for f, _, _ in POOLS[n][t]}
        assert forms <= allowed
    for t in (4, 5):
        assert "R" not in {read(it["prompt"])[0] for it in by_tier(n, t)}


# ---------------------------------------------------------------------------------------------
# Distractors, tells
# ---------------------------------------------------------------------------------------------
def ranks(n, t):
    c = Counter()
    for it in by_tier(n, t):
        vals = sorted(int(x) for x in it["choices"])
        c[vals.index(int(it["choices"][it["answer"]]))] += 1
    return c


@pytest.mark.parametrize("n", RANGES)
@pytest.mark.parametrize("t", TIERS)
def test_no_middle_tell_each_rank_15_to_35_percent(n, t):
    c = ranks(n, t)
    cnt = len(by_tier(n, t))
    for r in range(4):
        assert 0.15 * cnt <= c[r] <= 0.35 * cnt, (n, t, dict(c))


@pytest.mark.parametrize("n", RANGES)
@pytest.mark.parametrize("t", TIERS)
def test_answer_position_balance(n, t):
    c = Counter(it["answer"] for it in by_tier(n, t))
    cnt = len(by_tier(n, t))
    for pos in range(4):
        assert 0.5 / 4 * cnt <= c[pos] <= 1.5 / 4 * cnt, (n, t, dict(c))


@pytest.mark.parametrize("n", RANGES)
@pytest.mark.parametrize("t", TIERS)
def test_no_ones_digit_tell(n, t):
    """R items with a factor of 11 or more and an answer of 20 or more: the answer is the only choice with its ones
    digit in at most 25% of them (when a tier has 8 or more)."""
    rows = [it for it in by_tier(n, t) if read(it["prompt"])[0] == "R"
            and max(read(it["prompt"])[1:3]) >= 11 and read(it["prompt"])[3] >= 20]
    if len(rows) < 8:
        return
    only = sum(1 for it in rows
               if sum(1 for c in it["choices"] if int(c) % 10 == int(it["choices"][it["answer"]]) % 10) == 1)
    assert only <= 0.25 * len(rows), (n, t, only, len(rows))


@pytest.mark.parametrize("n", RANGES)
def test_misconception_keys_declared_and_used(n):
    b = BAKED[n]
    declared = set(b["misconceptions"]) | {"ARITH"}
    used = {k for it in b["items"] for k in it["misconceptions"] if k}
    assert used <= declared
    r_only = {"GROUP_OFF", "ADDED"}
    missing = {"MISSING_ONE_OFF", "MISSING_SUBTRACTED", "MISSING_PRODUCT"}
    big = {"DROPPED_CARRY", "TENS_SLIP", "PARTIAL_PRODUCTS"}
    assert (r_only | missing) <= used
    assert (big <= used) if n >= 12 else not (big & used)
    for k, v in b["misconceptions"].items():
        assert len(v["student"]) <= 80 and v["teacher"]
    # the keys sit on the forms they belong to
    for it in b["items"]:
        form = read(it["prompt"])[0]
        for k in it["misconceptions"]:
            if k and k != "ARITH":
                assert k.startswith("MISSING_") == (form != "R"), (it["prompt"], k)


@pytest.mark.parametrize("n", RANGES)
def test_arith_is_a_filler_not_the_norm(n):
    wrong = [k for it in BAKED[n]["items"] for k in it["misconceptions"] if k]
    assert sum(1 for k in wrong if k == "ARITH") <= 0.30 * len(wrong)


@pytest.mark.parametrize("n", RANGES)
def test_generation_is_deterministic(n):
    b = BAKED[n]
    m = {k: v for k, v in b.items() if k not in ("items", "baked_with")}
    assert GEN[n].generate(m, random.Random(m["seed"])) == GEN[n].generate(m, random.Random(m["seed"]))
    assert GEN[n].generate(m, random.Random(m["seed"])) == [{k: v for k, v in it.items() if k != "id"} for it in b["items"]]


# ---------------------------------------------------------------------------------------------
# Checker self-test: the checker can fail
# ---------------------------------------------------------------------------------------------
GOOD = {"tier": 3, "prompt": "7 × 8 = ?", "choices": ["56", "63", "49", "15"], "answer": 0,
        "misconceptions": [None, "GROUP_OFF", "GROUP_OFF", "ADDED"], "explanation": "x"}
GOOD_C = {"tier": 4, "prompt": "6 × ? = 42", "choices": ["7", "8", "6", "42"], "answer": 0,
          "misconceptions": [None, "MISSING_ONE_OFF", "MISSING_ONE_OFF", "MISSING_PRODUCT"], "explanation": "x"}
GOOD_BIG = {"tier": 3, "prompt": "13 × 7 = ?", "choices": ["91", "101", "84", "98"], "answer": 0,
            "misconceptions": [None, "TENS_SLIP", "GROUP_OFF", "GROUP_OFF"], "explanation": "x"}


def test_checker_accepts_good_items():
    assert problems(GOOD, 10) == []
    assert problems(GOOD_C, 10) == []
    assert problems(GOOD_BIG, 15) == []


@pytest.mark.parametrize("base,n,mutation,expected", [
    (GOOD, 10, {"choices": ["54", "63", "49", "15"]}, "answer wrong"),                    # key is not 7 x 8
    (GOOD, 10, {"choices": ["56", "15", "1", "99"]}, "fewer than 2 near values"),         # far-only distractors
    (GOOD, 10, {"choices": ["56", "56", "49", "63"]}, "choices not 4 distinct"),          # two right doors
    (GOOD, 10, {"choices": ["56", "63", "49", "-3"]}, "wrong choice out of range"),
    (GOOD, 10, {"choices": ["56", "63", "49", "1000"]}, "wrong choice out of range"),
    (GOOD, 10, {"prompt": "10 × 7 = ?"}, "pair outside the tier's pools"),                # 10 is not in T2's 3-4-6-9 core
    (GOOD, 5, {"prompt": "7 × 8 = ?"}, "factor over range"),
    (GOOD, 10, {"misconceptions": ["ARITH", "GROUP_OFF", "GROUP_OFF", "ADDED"]}, "misconception null placement"),
    (GOOD_C, 10, {"choices": ["6", "8", "7", "42"], "answer": 0}, "answer wrong"),        # 6 x 6 is not 42
    (GOOD_C, 10, {"choices": ["7", "42", "40", "41"]}, "fewer than 2 near values"),       # near for C is within 2
    (GOOD_C, 10, {"choices": ["7", "8", "6", "100"], "misconceptions": [None, "A", "B", "C"]}, None),
    (GOOD_C, 10, {"prompt": "0 × ? = 0", "choices": ["1", "2", "3", "4"], "answer": 0}, "prompt shape"),                  # 0 x ? = 0 has no single answer
    (GOOD_BIG, 15, {"choices": ["91", "102", "84", "98"]}, "ones-digit tell"),            # 91 is the only ending in 1
])
def test_checker_rejects_planted_bad_items(base, n, mutation, expected):
    bad = {**base, **mutation}
    got = problems(bad, n)
    if expected is None:
        assert got == []  # a far value alone (one far) is allowed
    else:
        assert expected in got


def test_checker_rejects_a_pair_outside_the_tier_in_every_range():
    # 9 x 12 is a tier-2 fact of the 12 range only; the 5 and 10 ranges cannot hold it
    bad = {**GOOD, "prompt": "9 × 12 = ?", "choices": ["108", "118", "120", "98"], "tier": 2}
    assert problems(bad, 12) == []
    assert "factor over range" in problems(bad, 10)
