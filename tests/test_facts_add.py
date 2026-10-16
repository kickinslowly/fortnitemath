"""facts-add-{10,20,50,100}: the four addition range cartridges (briefs/facts2, Aaron 2026-10-16).

One generator file, byte-identical in all four. Every baked item is re-solved here from its prompt with plain Python
(never the generator); the tier pools are rebuilt from the words of briefs/facts2/pools.py with a different
construction than the generator's; the anti-tell rules (near distractors, rank spread, ones digit, parity) are asserted
on baked.json; a checker self-test plants bad items the checker must reject."""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, bake_bytes, load_generator, load_manifest

RANGES = [10, 20, 50, 100]
IDS = [f"facts-add-{r}" for r in RANGES]
GENS = {cid: load_generator(cid) for cid in IDS}
MANIFESTS = {cid: load_manifest(cid) for cid in IDS}
BAKED = {}
for _cid in IDS:
    with open(REPO_ROOT / "cartridges" / _cid / "baked.json", encoding="utf-8") as _f:
        BAKED[_cid] = json.load(_f)
PROMPT_RE = re.compile(r"^(\d+|\?) ([+−×÷]) (\d+|\?) = (\d+|\?)$")
SUMS = {10: (1, 10), 20: (11, 20), 50: (21, 50), 100: (51, 100)}
N = 24


def by_tier(cid, t):
    return [it for it in BAKED[cid]["items"] if it["tier"] == t]


def rng_of(cid):
    return int(cid.rsplit("-", 1)[1])


# ---------------------------------------------------------------------------------------------
# Pools, rebuilt from the words of pools.py: tier -> [(form, set of (a, b), floor)]
# ---------------------------------------------------------------------------------------------
def grid(lo, hi, low):
    """Every (a, b), a and b >= low, lo <= a + b <= hi."""
    return {(a, b) for a in range(low, hi + 1) for b in range(low, hi + 1) if lo <= a + b <= hi}


def ones_make_ten(a, b):
    return (a % 10) + (b % 10) >= 10


def has_tens_operand(a, b):
    return any(v > 0 and v % 10 == 0 for v in (a, b))


def pools_for(r):
    if r == 10:
        p = grid(1, 10, 0)
        ten_pairs = {(a, 10 - a) for a in range(1, 10)}
        five_ten = grid(5, 10, 2)
        return {
            1: [("R", {x for x in p if min(x) <= 2}, 0)],
            2: [("R", {x for x in p if min(x) >= 2}, 0)],
            3: [("R", {x for x in p if min(x) >= 3}, 8), ("C", ten_pairs, 4), ("S", ten_pairs, 4)],
            4: [("C", {x for x in p if min(x) >= 1}, 0)],
            5: [("S", five_ten, 12), ("C", five_ten, 0)],
        }
    if r == 20:
        p = grid(11, 20, 1)
        single = {x for x in p if x[0] <= 9 and x[1] <= 9}
        ten_plus_no_new_ten = {x for x in p if (x[0] >= 10 or x[1] >= 10) and not ones_make_ten(*x)}
        t2 = {x for x in p if min(x) >= 2 and (x[0] == x[1] or abs(x[0] - x[1]) == 1 or (9 in x and x in single))}
        missing = {x for x in p if min(x) >= 2}
        missing_single = missing & single
        return {
            1: [("R", ten_plus_no_new_ten, 0)],
            2: [("R", t2, 0)],
            3: [("R", single, 0)],
            4: [("C", missing_single, 12), ("C", missing, 0)],
            5: [("S", missing_single, 6), ("S", missing, 12), ("C", missing_single, 0)],
        }
    lo, hi = SUMS[r]
    p = grid(lo, hi, 2)
    plain = {x for x in p if not has_tens_operand(*x)}
    reg = {x for x in plain if ones_make_ten(*x)}
    noreg = plain - reg
    one_digit = lambda xs: {x for x in xs if min(x) <= 9}
    both_two = lambda xs: {x for x in xs if min(x) >= 10}
    return {
        1: [("R", {x for x in grid(lo, hi, 1) if has_tens_operand(*x)}, 0)],
        2: [("R", one_digit(noreg), 8), ("R", both_two(noreg), 8)],
        3: [("R", one_digit(reg), 8), ("R", both_two(reg), 8)],
        4: [("C", reg, 12), ("C", plain, 0)],
        5: [("S", reg, 6), ("S", plain, 12), ("C", reg, 6), ("C", plain, 0)],
    }


POOLS = {r: pools_for(r) for r in RANGES}


# ---------------------------------------------------------------------------------------------
# Independent solver: regex + plain Python
# ---------------------------------------------------------------------------------------------
def parse(prompt):
    """(form, (a, b), answer) with a + b = s read the way pools.py does; raises on a malformed prompt."""
    m = PROMPT_RE.match(prompt)
    assert m, prompt
    x, op, y, z = m.groups()
    assert op == "+", prompt
    assert [x, y, z].count("?") == 1, prompt
    if z == "?":
        a, b = int(x), int(y)
        return "R", (a, b), a + b
    if y == "?":
        a, s = int(x), int(z)
        return "C", (a, s - a), s - a
    b, s = int(y), int(z)
    return "S", (s - b, b), s - b


def check_item(cid, it):
    """Return a list of problems with one baked item (empty = fine)."""
    r = rng_of(cid)
    bad = []
    try:
        form, (a, b), ans = parse(it["prompt"])
    except AssertionError:
        return ["prompt shape"]
    ch = it["choices"]
    if len(ch) != 4 or len(set(ch)) != 4:
        bad.append("four distinct choices")
    if not all(c.isdigit() for c in ch):
        return bad + ["non-integer choice"]
    vals = [int(c) for c in ch]
    if min(a, b) < 0:
        bad.append("negative operand")
    if vals[it["answer"]] != ans:
        bad.append("answer is wrong")
    if sum(v == ans for v in vals) != 1:
        bad.append("not exactly one right choice")
    if any(v < 0 or v > 999 for v in vals):
        bad.append("choice out of 0..999")
    if it["misconceptions"][it["answer"]] is not None:
        bad.append("answer carries a key")
    wrong = [v for k, v in enumerate(vals) if k != it["answer"]]
    if sum(abs(v - ans) in (1, 2, 10) for v in wrong) < 2:
        bad.append("fewer than 2 near distractors")
    if sum(abs(v - ans) not in (1, 2, 10) for v in wrong) > 1:
        bad.append("more than 1 far distractor")
    lo, hi = SUMS[r]
    if not lo <= a + b <= hi:
        bad.append("sum outside the range")
    if not any(f == form and (a, b) in ps for f, ps, _ in POOLS[r][it["tier"]]):
        bad.append("pair not in the tier's pools")
    return bad


# ---------------------------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------------------------
def test_generators_byte_identical():
    blobs = {cid: (REPO_ROOT / "cartridges" / cid / "generator.py").read_bytes() for cid in IDS}
    assert len(set(blobs.values())) == 1


@pytest.mark.parametrize("cid", IDS)
def test_baked_is_current_and_deterministic(cid):
    on_disk = (REPO_ROOT / "cartridges" / cid / "baked.json").read_bytes()
    assert bake_bytes(cid) == on_disk
    m = MANIFESTS[cid]
    a = GENS[cid].generate(m, random.Random(m["seed"]))
    b = GENS[cid].generate(m, random.Random(m["seed"]))
    assert a == b


@pytest.mark.parametrize("cid", IDS)
def test_manifest_fields(cid):
    m = MANIFESTS[cid]
    r = rng_of(cid)
    assert m["grade"] == "Facts" and m["picker_order"] == RANGES.index(r) + 1
    assert m["items_per_tier"] == N and m["version"] == "1.0.0" and m["protocol"] == "fnm-cart/1"
    assert m["seed"] == 20261051 + RANGES.index(r)
    assert len(m["tiers"]) == 5 and [t["tier"] for t in m["tiers"]] == [1, 2, 3, 4, 5]
    assert all(s.startswith("CCSS.MATH.CONTENT.") for s in m["standards"])
    assert "bounds" in m and str(SUMS[r][1]) in m["bounds"]
    assert m["tiers"][3]["name"] == "Missing numbers" and m["tiers"][4]["name"] == "Missing first numbers"


@pytest.mark.parametrize("cid", IDS)
def test_text_limits(cid):
    m = MANIFESTS[cid]
    for it in BAKED[cid]["items"]:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160, it
        assert all(len(c) <= 14 for c in it["choices"])
    for mc in m["misconceptions"].values():
        assert len(mc["student"]) <= 80
    assert len(m["title"]) <= 32 and len(m["subtitle"]) <= 40
    assert all(len(t["name"]) <= 24 for t in m["tiers"])


@pytest.mark.parametrize("cid", IDS)
def test_every_declared_key_is_used_and_every_used_key_declared(cid):
    used = {k for it in BAKED[cid]["items"] for k in it["misconceptions"] if k}
    declared = set(MANIFESTS[cid]["misconceptions"]) | {"ARITH"}
    assert used <= declared, used - declared
    assert set(MANIFESTS[cid]["misconceptions"]) <= used, set(MANIFESTS[cid]["misconceptions"]) - used


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked prompt -> the wrong value each key must give (G.candidates(range, form, a, b))
# ---------------------------------------------------------------------------------------------
# (range, form, a, b, answer, {value: key}) where the prompt reads (a, b): R a + b = ?, C a + ? = s, S ? + b = s
GOLDEN = [
    (10, "R", 3, 5, 8, {7: "ONE_OFF", 9: "ONE_OFF", 2: "SUBTRACTED", 6: "ARITH", 10: "ARITH"}),
    (10, "C", 3, 7, 7, {13: "MISSING_ADDED", 6: "MISSING_ONE_OFF", 8: "MISSING_ONE_OFF", 5: "ARITH", 9: "ARITH"}),
    (10, "S", 4, 3, 4, {10: "MISSING_ADDED", 3: "MISSING_ONE_OFF", 5: "MISSING_ONE_OFF", 2: "ARITH", 6: "ARITH"}),
    (20, "R", 8, 5, 13, {12: "ONE_OFF", 14: "ONE_OFF", 3: "SUBTRACTED", 23: "TENS_SLIP"}),  # |8-5| = s-10: SUBTRACTED wins
    (20, "R", 9, 4, 13, {5: "SUBTRACTED", 3: "NO_CARRY", 23: "TENS_SLIP", 12: "ONE_OFF"}),
    (20, "R", 12, 3, 15, {9: "SUBTRACTED", 5: "TENS_SLIP", 25: "TENS_SLIP", 14: "ONE_OFF"}),  # no regroup: s-10 is TENS_SLIP
    (20, "C", 7, 8, 8, {22: "MISSING_ADDED", 7: "MISSING_ONE_OFF", 9: "MISSING_ONE_OFF", 18: "MISSING_TENS"}),
    (20, "S", 8, 6, 8, {20: "MISSING_ADDED", 7: "MISSING_ONE_OFF", 9: "MISSING_ONE_OFF", 18: "MISSING_TENS"}),
    (50, "R", 27, 6, 33, {21: "SUBTRACTED", 23: "NO_CARRY", 43: "TENS_SLIP", 32: "ONE_OFF"}),
    (50, "C", 26, 14, 14, {66: "MISSING_ADDED", 13: "MISSING_ONE_OFF", 15: "MISSING_ONE_OFF", 4: "MISSING_TENS", 24: "MISSING_TENS"}),
    (50, "S", 35, 36, 35, {107: "MISSING_ADDED", 34: "MISSING_ONE_OFF", 36: "MISSING_ONE_OFF", 25: "MISSING_TENS", 45: "MISSING_TENS"}),
    (100, "R", 34, 52, 86, {18: "SUBTRACTED", 76: "TENS_SLIP", 96: "TENS_SLIP", 87: "ONE_OFF"}),
    (100, "R", 56, 29, 85, {27: "SUBTRACTED", 75: "NO_CARRY", 95: "TENS_SLIP", 84: "ONE_OFF"}),
    (100, "C", 38, 47, 47, {123: "MISSING_ADDED", 46: "MISSING_ONE_OFF", 48: "MISSING_ONE_OFF", 37: "MISSING_TENS", 57: "MISSING_TENS"}),
]


@pytest.mark.parametrize("r,form,a,b,ans,wrong", GOLDEN, ids=[f"{g[0]}-{g[1]}-{g[2]},{g[3]}" for g in GOLDEN])
def test_golden_candidate_keys(r, form, a, b, ans, wrong):
    G = GENS[f"facts-add-{r}"]
    assert G.answer_of(form, a, b) == ans
    # the prompt really reads the way the golden case says (independent parse)
    pform, pair, pans = parse(G.prompt_of(form, a, b))
    assert (pform, pair, pans) == (form, (a, b), ans)
    cand = G.candidates(r, form, a, b)
    assert ans not in cand
    for v, key in wrong.items():
        assert cand.get(v) == key, (v, key, cand)


def test_golden_tens_keys_only_in_two_digit_ranges():
    G = GENS["facts-add-10"]
    assert 18 not in G.candidates(10, "R", 3, 5) and 13 not in G.candidates(10, "R", 3, 5)
    assert 17 not in G.candidates(10, "C", 3, 7) and 27 not in G.candidates(10, "C", 3, 7)


def test_golden_key_yielding_the_answer_is_dropped():
    G = GENS["facts-add-20"]
    assert 5 not in G.candidates(20, "R", 0, 5)  # |0 - 5| = 5 = the answer
    assert G.candidates(10, "R", 0, 5).get(5) is None


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked item
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cid", IDS)
def test_every_baked_item_is_right(cid):
    problems = [(it["id"], it["prompt"], check_item(cid, it)) for it in BAKED[cid]["items"] if check_item(cid, it)]
    assert not problems, problems[:5]


@pytest.mark.parametrize("cid", IDS)
def test_explanation_states_the_fact(cid):
    for it in BAKED[cid]["items"]:
        form, (a, b), ans = parse(it["prompt"])
        assert it["explanation"].startswith(it["prompt"].replace(" = ?", "") if form == "R" else it["prompt"]), it
        assert f"{a} + {b} = {a + b}" in it["explanation"], it
        if form != "R":
            assert f"so ? = {ans}" in it["explanation"], it


@pytest.mark.parametrize("cid", IDS)
def test_strategy_clause_is_not_the_fact_restated(cid):
    for it in BAKED[cid]["items"]:
        form, (a, b), ans = parse(it["prompt"])
        assert "1 tens" not in it["explanation"], it
        if form == "R":
            continue
        k = a if form == "C" else b
        strategy = it["explanation"].split(f"so ? = {ans}.", 1)[1].strip()
        assert strategy, it
        assert f"{k} + {ans} = {a + b}" not in strategy and f"{ans} + {k} = {a + b}" not in strategy, it


def test_strategy_checker_can_fail():
    bad = "8 + ? = 10: 8 + 2 = 10, so ? = 2. Count up: 8 + 2 = 10."
    strategy = bad.split("so ? = 2.", 1)[1].strip()
    assert "8 + 2 = 10" in strategy


@pytest.mark.parametrize("cid", IDS)
def test_counts_unique_prompts_and_form_floors(cid):
    r = rng_of(cid)
    for t in range(1, 6):
        its = by_tier(cid, t)
        assert len(its) == N
        assert len({it["prompt"] for it in its}) == N
        forms = [parse(it["prompt"])[:2] for it in its]
        for form, pairs, floor in POOLS[r][t]:
            have = sum(1 for f, x in forms if f == form and x in pairs)
            assert have >= floor, (cid, t, form, have, floor)
        # no ambiguity: the equation has one non-negative solution (always true for +; asserted anyway)
        for it in its:
            f, (a, b), ans = parse(it["prompt"])
            assert ans >= 0 and a >= 0 and b >= 0


@pytest.mark.parametrize("cid", IDS)
def test_tier_forms(cid):
    """T1-T3 are R only except range 10's T3; T4 is C only; T5 is S and C (the spec's ladder)."""
    for t in range(1, 6):
        forms = Counter(parse(it["prompt"])[0] for it in by_tier(cid, t))
        allowed = {f for f, _, _ in POOLS[rng_of(cid)][t]}
        assert set(forms) <= allowed, (cid, t, forms)
        if t == 5:
            assert forms["S"] >= 12
        if t == 4:
            assert set(forms) == {"C"}


def test_pool_sizes_cover_24():
    for r in RANGES:
        for t in range(1, 6):
            union = {(f, x) for f, ps, _ in POOLS[r][t] for x in ps}
            assert len(union) >= N, (r, t, len(union))


# ---------------------------------------------------------------------------------------------
# Anti-tell rules on baked.json
# ---------------------------------------------------------------------------------------------
def vals_of(it):
    return [int(c) for c in it["choices"]]


def rank_of_answer(it):
    v = vals_of(it)
    return sum(x < v[it["answer"]] for x in v)


def ones_alone(it):
    v = vals_of(it)
    a = v[it["answer"]]
    return all(x % 10 != a % 10 for k, x in enumerate(v) if k != it["answer"])


def parity_alone(it):
    v = vals_of(it)
    a = v[it["answer"]]
    return all(x % 2 != a % 2 for k, x in enumerate(v) if k != it["answer"])


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_no_middle_tell_rank_spread(cid, t):
    its = by_tier(cid, t)
    rc = Counter(rank_of_answer(it) for it in its)
    for rank in range(4):
        assert 0.15 <= rc[rank] / len(its) <= 0.35, (cid, t, rank, rc)


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_answer_positions_balanced(cid, t):
    pos = Counter(it["answer"] for it in by_tier(cid, t))
    assert all(4 <= pos[p] <= 8 for p in range(4)), (cid, t, pos)


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_no_ones_digit_tell(cid, t):
    big = [it for it in by_tier(cid, t) if vals_of(it)[it["answer"]] >= 20]
    if len(big) >= 8:
        assert sum(ones_alone(it) for it in big) / len(big) <= 0.25, (cid, t)


@pytest.mark.parametrize("cid", IDS)
@pytest.mark.parametrize("t", range(1, 6))
def test_no_parity_or_neighbour_tell(cid, t):
    its = by_tier(cid, t)
    assert sum(parity_alone(it) for it in its) / len(its) <= 0.10, (cid, t)
    tri = sum({vals_of(it)[it["answer"]] - 1, vals_of(it)[it["answer"]] + 1} <= set(vals_of(it)) for it in its)
    assert tri / len(its) <= 0.5


@pytest.mark.parametrize("cid", IDS)
def test_wrong_choices_distinct_nonnegative_bounded(cid):
    for it in BAKED[cid]["items"]:
        v = vals_of(it)
        assert len(set(v)) == 4 and all(0 <= x <= 999 for x in v)


@pytest.mark.parametrize("cid", IDS)
def test_keys_match_the_value_they_label(cid):
    """A labelled wrong value really is what its key says (R and missing forms), checked from the prompt alone."""
    r = rng_of(cid)
    for it in BAKED[cid]["items"]:
        form, (a, b), ans = parse(it["prompt"])
        s = a + b
        k = a if form == "C" else b
        for c, key in zip(vals_of(it), it["misconceptions"]):
            if key is None or key == "ARITH":
                continue
            if form == "R":
                ok = {"ONE_OFF": abs(c - s) == 1, "SUBTRACTED": c == abs(a - b),
                      "NO_CARRY": c == s - 10 and ones_make_ten(a, b), "TENS_SLIP": abs(c - s) == 10}[key]
            else:
                ok = {"MISSING_ADDED": c == k + s, "MISSING_ONE_OFF": abs(c - ans) == 1,
                      "MISSING_TENS": abs(c - ans) == 10}[key]
            assert ok, (it["prompt"], c, key)
            if r == 10:
                assert key not in ("NO_CARRY", "TENS_SLIP", "MISSING_TENS")


# ---------------------------------------------------------------------------------------------
# Disproofs: the checkers must be able to fail
# ---------------------------------------------------------------------------------------------
def test_checker_rejects_planted_bad_items():
    cid = "facts-add-50"
    good = next(it for it in by_tier(cid, 3))
    assert check_item(cid, good) == []
    form, (a, b), ans = parse(good["prompt"])

    shifted = dict(good, choices=[str(int(c) + 1) for c in good["choices"]])
    assert "answer is wrong" in check_item(cid, shifted)

    other = dict(good, answer=(good["answer"] + 1) % 4)
    assert "answer is wrong" in check_item(cid, other)

    far = dict(good, choices=list(good["choices"]))
    for k in range(4):
        if k != good["answer"]:
            far["choices"][k] = str(ans + 31 + k)
    bad = check_item(cid, far)
    assert "fewer than 2 near distractors" in bad and "more than 1 far distractor" in bad

    dup = dict(good, choices=[good["choices"][good["answer"]]] * 4)
    assert "four distinct choices" in check_item(cid, dup)

    out_of_range = dict(good, prompt=f"{a} + {b + 90} = ?")
    assert "sum outside the range" in check_item(cid, out_of_range)

    # a prompt of the right range but a pair/form outside the tier's pools: a tier-5 style S prompt in tier 1
    t5 = next(it for it in by_tier(cid, 5) if parse(it["prompt"])[0] == "S")
    assert check_item(cid, t5) == []
    assert "pair not in the tier's pools" in check_item(cid, dict(t5, tier=1))
    # a pair with a multiple of ten in tier 2's no-regrouping pool
    tens = dict(good, tier=2, prompt="20 + 15 = ?")
    assert "pair not in the tier's pools" in check_item(cid, tens)

    with_negative = dict(good, prompt="? + 5 = 3")
    assert check_item(cid, with_negative)  # a negative answer cannot pass the choice or range checks


def test_floor_counter_can_fail():
    """Disproof: a tier made only of one-digit-operand prompts misses add-50 T2's 'both two-digit' floor."""
    r = 50
    (form1, pairs1, f1), (form2, pairs2, f2) = POOLS[r][2]
    only_small = [("R", x) for x in sorted(pairs1 - pairs2)][:N]
    assert len(only_small) == N
    assert sum(1 for f, x in only_small if x in pairs1) >= f1
    assert sum(1 for f, x in only_small if x in pairs2) < f2


def test_ones_digit_and_parity_checkers_can_fail():
    tell = {"choices": ["81", "82", "83", "85"], "answer": 3}
    assert ones_alone(tell)
    ok = {"choices": ["75", "84", "85", "95"], "answer": 2}
    assert not ones_alone(ok)
    assert sum(ones_alone(it) for it in [tell] * 10 + [ok] * 30) / 40 <= 0.25
    assert sum(ones_alone(it) for it in [tell] * 20 + [ok] * 20) / 40 > 0.25
    odd_one = {"choices": ["12", "14", "16", "13"], "answer": 3}
    assert parity_alone(odd_one)
    assert not parity_alone({"choices": ["12", "14", "13", "15"], "answer": 2})


def test_rank_spread_checker_can_fail():
    always_middle = [{"choices": ["10", "11", "12", "13"], "answer": 1}] * 24
    rc = Counter(rank_of_answer(it) for it in always_middle)
    assert rc[1] / 24 > 0.35
