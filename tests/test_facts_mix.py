"""facts-mix-{10,20,50,100}: + - x / together (briefs/facts2, Aaron 2026-10-16).

Each mix tier is 6 items from each of the four operations' own cartridges at the paired range and the same tier
(floors scaled to ceil(n / 4)). One generator file, byte-identical in all four. Every baked item is re-solved here from
its prompt with plain Python (never the generator); the pools are rebuilt here from the words of briefs/facts2/pools.py;
the 6/6/6/6 split, the floors, the anti-tell rules and the agreement with the operations' own baked.json are asserted;
a checker self-test plants bad items the checker must reject."""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, bake_bytes, load_generator, load_manifest

RANGES = [10, 20, 50, 100]
IDS = [f"facts-mix-{r}" for r in RANGES]
PAIR = {10: (10, 5), 20: (20, 10), 50: (50, 12), 100: (100, 15)}  # mix range -> (add/sub range, mul/div range)
OP_OF = {"+": "add", "−": "sub", "×": "mul", "÷": "div"}
OPS = ["add", "sub", "mul", "div"]
GENS = {cid: load_generator(cid) for cid in IDS}
MANIFESTS = {cid: load_manifest(cid) for cid in IDS}
PROMPT_RE = re.compile(r"^(\d+|\?) ([+−×÷]) (\d+|\?) = (\d+|\?)$")
SUMS = {10: (1, 10), 20: (11, 20), 50: (21, 50), 100: (51, 100)}
N = 24
PER_OP = 6


def load_baked(cid):
    with open(REPO_ROOT / "cartridges" / cid / "baked.json", encoding="utf-8") as f:
        return json.load(f)


BAKED = {cid: load_baked(cid) for cid in IDS}


def own_id(op, mix_range):
    h, n = PAIR[mix_range]
    return f"facts-{op}-{h if op in ('add', 'sub') else n}"


def by_tier(cid, t):
    return [it for it in BAKED[cid]["items"] if it["tier"] == t]


def rng_of(cid):
    return int(cid.rsplit("-", 1)[1])


def ceil4(n):
    return -(-n // 4)


# ---------------------------------------------------------------------------------------------
# Pools, rebuilt from the words of pools.py: (op, hi, nd) -> tier -> [(form, set of (a, b), floor of 6)]
# ---------------------------------------------------------------------------------------------
def regroups(a, b):
    return a % 10 + b % 10 >= 10


def has_tens_operand(a, b):
    return any(v > 0 and v % 10 == 0 for v in (a, b))


def grid_add(lo, hi, low):
    return {(a, b) for a in range(low, hi + 1) for b in range(low, hi + 1) if lo <= a + b <= hi}


def grid_mul(n, low=0):
    return {(a, b) for a in range(low, n + 1) for b in range(low, n + 1)}


def add_pools(r):
    if r == 10:
        p = grid_add(1, 10, 0)
        ten_pairs = {(a, 10 - a) for a in range(1, 10)}
        five_ten = grid_add(5, 10, 2)
        return {1: [("R", {x for x in p if min(x) <= 2}, 0)],
                2: [("R", {x for x in p if min(x) >= 2}, 0)],
                3: [("R", {x for x in p if min(x) >= 3}, 8), ("C", ten_pairs, 4), ("S", ten_pairs, 4)],
                4: [("C", {x for x in p if min(x) >= 1}, 0)],
                5: [("S", five_ten, 12), ("C", five_ten, 0)]}
    if r == 20:
        p = grid_add(11, 20, 1)
        single = {x for x in p if x[0] <= 9 and x[1] <= 9}
        t1 = {x for x in p if (x[0] >= 10 or x[1] >= 10) and not regroups(*x)}
        t2 = {x for x in p if min(x) >= 2 and (x[0] == x[1] or abs(x[0] - x[1]) == 1 or (9 in x and x in single))}
        missing = {x for x in p if min(x) >= 2}
        return {1: [("R", t1, 0)], 2: [("R", t2, 0)], 3: [("R", single, 0)],
                4: [("C", missing & single, 12), ("C", missing, 0)],
                5: [("S", missing & single, 6), ("S", missing, 12), ("C", missing & single, 0)]}
    lo, hi = SUMS[r]
    p = grid_add(lo, hi, 2)
    plain = {x for x in p if not has_tens_operand(*x)}
    reg = {x for x in plain if regroups(*x)}
    noreg = plain - reg
    one_digit = lambda xs: {x for x in xs if min(x) <= 9}
    both_two = lambda xs: {x for x in xs if min(x) >= 10}
    return {1: [("R", {x for x in grid_add(lo, hi, 1) if has_tens_operand(*x)}, 0)],
            2: [("R", one_digit(noreg), 8), ("R", both_two(noreg), 8)],
            3: [("R", one_digit(reg), 8), ("R", both_two(reg), 8)],
            4: [("C", reg, 12), ("C", plain, 0)],
            5: [("S", reg, 6), ("S", plain, 12), ("C", reg, 6), ("C", plain, 0)]}


EASY = {0, 1, 2, 5, 10}
MID = {3, 4, 9}
HARD = {6, 7, 8}
CORE = MID | HARD


def easy_fact(x):
    return bool(EASY & set(x)) or (11 in x and min(x) <= 9)


def mul_pools(n):
    p = grid_mul(n)
    core = {x for x in p if set(x) <= CORE}
    if n == 5:
        one_five, two_five = grid_mul(5, 1), grid_mul(5, 2)
        return {1: [("R", {x for x in p if {0, 1, 2, 5} & set(x)}, 0)],
                2: [("R", one_five, 0)],
                3: [("R", two_five, 12), ("C", {x for x in one_five if x[0] in (2, 5)}, 8)],
                4: [("C", one_five, 0)],
                5: [("S", two_five, 12), ("C", two_five, 0)]}
    if n == 10:
        return {1: [("R", {x for x in p if EASY & set(x)}, 0)],
                2: [("R", {x for x in core if set(x) <= MID}, 8), ("R", {x for x in core if MID & set(x)}, 0)],
                3: [("R", {x for x in core if set(x) <= HARD}, 8), ("R", {x for x in core if HARD & set(x)}, 0)],
                4: [("C", core, 12), ("C", grid_mul(10, 2), 0)],
                5: [("S", core, 12), ("C", core, 0)]}
    big = lambda x: max(x) >= 11
    if n == 12:
        t1 = {x for x in p if easy_fact(x)}
        t2_new = {x for x in p if 12 in x and min(x) in MID}
        t3_new = {x for x in p if not easy_fact(x) and big(x) and (HARD & set(x) or min(x) >= 11)}
        core12 = {x for x in grid_mul(12, 3) if not easy_fact(x)}
        return {1: [("R", {x for x in t1 if big(x)}, 8), ("R", t1, 0)],
                2: [("R", t2_new, 6), ("R", {x for x in core if set(x) <= MID}, 6),
                    ("R", {x for x in core if MID & set(x)}, 0)],
                3: [("R", t3_new, 8), ("R", {x for x in core if set(x) <= HARD}, 6),
                    ("R", {x for x in core if HARD & set(x)}, 0)],
                4: [("C", {x for x in core12 if big(x)}, 6), ("C", core, 8), ("C", grid_mul(12, 2), 0)],
                5: [("S", {x for x in core12 if big(x)}, 6), ("S", core12, 6),
                    ("C", {x for x in core12 if big(x)}, 4), ("C", core12, 0)]}
    t1 = {x for x in p if easy_fact(x)}
    t2 = {x for x in p if big(x) and not easy_fact(x) and min(x) in (3, 4)}
    t3 = {x for x in p if big(x) and not easy_fact(x) and (min(x) in (6, 7, 8, 9) or min(x) >= 11)}
    hard15 = {x for x in grid_mul(15, 3) if not easy_fact(x)}
    return {1: [("R", {x for x in t1 if big(x)}, 12), ("R", t1, 0)],
            2: [("R", t2, 12), ("R", {x for x in core if MID & set(x)}, 0)],
            3: [("R", t3, 12), ("R", {x for x in core if HARD & set(x)}, 0)],
            4: [("C", {x for x in hard15 if big(x)}, 12), ("C", hard15, 0)],
            5: [("S", {x for x in hard15 if big(x)}, 8), ("S", hard15, 4), ("C", {x for x in hard15 if big(x)}, 4),
                ("C", hard15, 0)]}


def usable(op, form, x):
    if op == "mul":
        return form == "R" or min(x) >= 1
    if op == "div":
        return x[0] != 0 and (form == "R" or x[1] >= 1)
    return True


def pools_for(op, r):
    """tier -> [(form, usable pairs, floor of 6 items)] for the op inside mix range r."""
    h, n = PAIR[r]
    raw = add_pools(h) if op in ("add", "sub") else mul_pools(n)
    return {t: [(f, {x for x in ps if usable(op, f, x)}, ceil4(fl)) for f, ps, fl in parts] for t, parts in raw.items()}


POOLS = {(op, r): pools_for(op, r) for op in OPS for r in RANGES}


# ---------------------------------------------------------------------------------------------
# Independent solver: regex + plain Python. -> (op, form, (a, b), answer); the pair is read as in pools.py:
# add a + b = s | sub s - a = b | mul a x b = p | div p / a = b
# ---------------------------------------------------------------------------------------------
def parse(prompt):
    m = PROMPT_RE.match(prompt)
    assert m, prompt
    x, sym, y, z = m.groups()
    op = OP_OF[sym]
    assert [x, y, z].count("?") == 1, prompt
    if op == "add":
        if z == "?":
            return op, "R", (int(x), int(y)), int(x) + int(y)
        if y == "?":
            return op, "C", (int(x), int(z) - int(x)), int(z) - int(x)
        return op, "S", (int(z) - int(y), int(y)), int(z) - int(y)
    if op == "sub":
        if z == "?":  # s - a = ?
            s, a = int(x), int(y)
            return op, "R", (a, s - a), s - a
        if y == "?":  # s - ? = b
            s, b = int(x), int(z)
            return op, "C", (s - b, b), s - b
        a, b = int(y), int(z)  # ? - a = b
        return op, "S", (a, b), a + b
    if op == "mul":
        if z == "?":
            return op, "R", (int(x), int(y)), int(x) * int(y)
        if y == "?":  # a x ? = p
            a, p = int(x), int(z)
            assert a != 0 and p % a == 0, prompt
            return op, "C", (a, p // a), p // a
        b, p = int(y), int(z)  # ? x b = p
        assert b != 0 and p % b == 0, prompt
        return op, "S", (p // b, b), p // b
    if z == "?":  # p / a = ?
        p, a = int(x), int(y)
        assert a != 0 and p % a == 0, prompt
        return op, "R", (a, p // a), p // a
    if y == "?":  # p / ? = b
        p, b = int(x), int(z)
        assert b != 0 and p % b == 0, prompt
        return op, "C", (p // b, b), p // b
    a, b = int(y), int(z)  # ? / a = b
    assert a != 0, prompt
    return op, "S", (a, b), a * b


def near_limit(op, form, a, b):
    if op in ("add", "sub"):
        return None  # +-1, 2, 10
    if op == "mul":
        return max(a, b, 2) if form == "R" else 2
    return max(a, b) if form == "S" else 2


def is_near(op, form, a, b, ans, v):
    if op in ("add", "sub"):
        return abs(v - ans) in (1, 2, 10)
    return abs(v - ans) <= near_limit(op, form, a, b)


def check_item(cid, it):
    """Return a list of problems with one baked item (empty = fine)."""
    r = rng_of(cid)
    bad = []
    try:
        op, form, (a, b), ans = parse(it["prompt"])
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
    if sum(is_near(op, form, a, b, ans, v) for v in wrong) < 2:
        bad.append("fewer than 2 near distractors")
    if sum(not is_near(op, form, a, b, ans, v) for v in wrong) > 1:
        bad.append("more than 1 far distractor")
    h, n = PAIR[r]
    if op in ("add", "sub") and not SUMS[h][0] <= a + b <= SUMS[h][1]:
        bad.append("sum outside the range")
    if op in ("mul", "div") and max(a, b) > n:
        bad.append("factor over range")
    if not any(f == form and (a, b) in ps for f, ps, _ in POOLS[(op, r)].get(it["tier"], [])):
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
    assert bake_bytes(cid) == (REPO_ROOT / "cartridges" / cid / "baked.json").read_bytes()
    m = MANIFESTS[cid]
    a = GENS[cid].generate(m, random.Random(m["seed"]))
    b = GENS[cid].generate(m, random.Random(m["seed"]))
    assert a == b


@pytest.mark.parametrize("cid", IDS)
def test_manifest_fields(cid):
    m = MANIFESTS[cid]
    i = RANGES.index(rng_of(cid))
    assert m["grade"] == "Facts" and m["picker_order"] == 17 + i and m["seed"] == 20261067 + i
    assert m["items_per_tier"] == N and m["version"] == "1.0.0" and m["protocol"] == "fnm-cart/1"
    assert [t["tier"] for t in m["tiers"]] == [1, 2, 3, 4, 5]
    assert m["tiers"][3]["name"] == "Missing numbers" and m["tiers"][4]["name"] == "Missing first numbers"
    assert all(s.startswith("CCSS.MATH.CONTENT.") for s in m["standards"])
    h, n = PAIR[rng_of(cid)]
    assert f"facts-add-{h}" in m["bounds"] and f"facts-mul-{n}" in m["bounds"]
    assert len(m["title"]) <= 32 and len(m["subtitle"]) <= 40 and all(len(t["name"]) <= 24 for t in m["tiers"])
    assert {m["title"], m["subtitle"]} and m["standards"] == sorted(set(m["standards"]), key=m["standards"].index)


@pytest.mark.parametrize("cid", IDS)
def test_standards_are_the_union_of_the_four_operations(cid):
    r = rng_of(cid)
    union = set()
    for op in OPS:
        union |= set(load_manifest(own_id(op, r))["standards"])
    assert set(MANIFESTS[cid]["standards"]) == union


@pytest.mark.parametrize("cid", IDS)
def test_text_limits(cid):
    for it in BAKED[cid]["items"]:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160, it
        assert all(len(c) <= 14 for c in it["choices"])
    for mc in MANIFESTS[cid]["misconceptions"].values():
        assert len(mc["student"]) <= 80


@pytest.mark.parametrize("cid", IDS)
def test_keys_are_prefixed_declared_and_used(cid):
    declared = set(MANIFESTS[cid]["misconceptions"])
    used = set()
    for it in BAKED[cid]["items"]:
        op = parse(it["prompt"])[0]
        for k in it["misconceptions"]:
            if k is None or k == "ARITH":
                continue
            assert k.startswith(op.upper() + "_"), (it["prompt"], k)
            used.add(k)
    assert used == declared, (used ^ declared)


@pytest.mark.parametrize("cid", IDS)
def test_student_text_is_the_operations_own(cid):
    """Each catalog entry is copied from the paired operation cartridge's own catalog."""
    r = rng_of(cid)
    for key, mc in MANIFESTS[cid]["misconceptions"].items():
        op, _, bare = key.partition("_")
        own = load_manifest(own_id(op.lower(), r))["misconceptions"]
        assert own[bare]["student"] == mc["student"] and own[bare]["teacher"] == mc["teacher"], key


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked prompt -> the wrong value each key must give (generator's candidate functions)
# ---------------------------------------------------------------------------------------------
def add_cand(r, form, a, b):
    return GENS[f"facts-mix-{r}"].add_candidates(PAIR[r][0], form, a, b)


ADD_GOLDEN = [  # (mix range, form, a, b, answer, {value: key})   prompt reads (a, b): R a + b = ?, C a + ? = s, S ? + b = s
    (10, "R", 3, 5, 8, {7: "ONE_OFF", 9: "ONE_OFF", 2: "SUBTRACTED", 6: "ARITH", 10: "ARITH"}),
    (10, "C", 3, 7, 7, {13: "MISSING_ADDED", 6: "MISSING_ONE_OFF", 8: "MISSING_ONE_OFF", 5: "ARITH"}),
    (20, "R", 9, 4, 13, {5: "SUBTRACTED", 3: "NO_CARRY", 23: "TENS_SLIP", 12: "ONE_OFF"}),
    (20, "C", 7, 8, 8, {22: "MISSING_ADDED", 7: "MISSING_ONE_OFF", 9: "MISSING_ONE_OFF", 18: "MISSING_TENS"}),
    (50, "R", 27, 6, 33, {21: "SUBTRACTED", 23: "NO_CARRY", 43: "TENS_SLIP", 32: "ONE_OFF"}),
    (50, "S", 35, 36, 35, {107: "MISSING_ADDED", 34: "MISSING_ONE_OFF", 36: "MISSING_ONE_OFF", 25: "MISSING_TENS"}),
    (100, "R", 56, 29, 85, {27: "SUBTRACTED", 75: "NO_CARRY", 95: "TENS_SLIP", 84: "ONE_OFF"}),
]


@pytest.mark.parametrize("r,form,a,b,ans,wrong", ADD_GOLDEN, ids=[f"{g[0]}-{g[1]}-{g[2]},{g[3]}" for g in ADD_GOLDEN])
def test_golden_add_keys(r, form, a, b, ans, wrong):
    G = GENS[f"facts-mix-{r}"]
    assert G.answer_of("add", form, a, b) == ans
    assert parse(G.prompt_of("add", form, a, b)) == ("add", form, (a, b), ans)
    cand = add_cand(r, form, a, b)
    assert ans not in cand
    for v, key in wrong.items():
        assert cand.get(v) == key, (v, key, cand)


SUB_GOLDEN = [  # (mix range, form, a, b, answer, {value: key}); the fact is s - a = b with s = a + b
    (20, "R", 6, 8, 8, {9: "ONE_OFF", 7: "ONE_OFF", 20: "ADDED", 12: "SMALLER_FROM_LARGER", 18: "FORGOT_TRADE"}),
    (20, "C", 8, 6, 8, {20: "MISSING_ADDED", 9: "MISSING_ONE_OFF", 7: "MISSING_ONE_OFF", 18: "MISSING_TENS"}),
    (20, "S", 6, 8, 14, {2: "START_SUBTRACTED", 15: "MISSING_ONE_OFF", 13: "MISSING_ONE_OFF", 4: "START_NO_CARRY",
                         24: "MISSING_TENS"}),
    (50, "R", 8, 25, 25, {26: "ONE_OFF", 24: "ONE_OFF", 41: "ADDED", 35: "SMALLER_FROM_LARGER"}),  # FORGOT_TRADE b+10 collides: first wins
    (50, "R", 4, 45, 45, {46: "ONE_OFF", 44: "ONE_OFF", 53: "ADDED", 55: "TENS_SLIP", 35: "TENS_SLIP"}),
    (10, "R", 3, 4, 4, {5: "ONE_OFF", 3: "ONE_OFF", 10: "ADDED"}),
]


@pytest.mark.parametrize("r,form,a,b,ans,wrong", SUB_GOLDEN, ids=[f"{g[0]}-{g[1]}-{g[2]},{g[3]}" for g in SUB_GOLDEN])
def test_golden_sub_keys(r, form, a, b, ans, wrong):
    G = GENS[f"facts-mix-{r}"]
    assert G.answer_of("sub", form, a, b) == ans
    assert parse(G.prompt_of("sub", form, a, b)) == ("sub", form, (a, b), ans)
    cand = {v: k for v, k in G.sub_candidates(form, a, b)}
    assert ans not in cand
    for v, key in wrong.items():
        assert cand.get(v) == key, (v, key, cand)


def test_golden_sub_10_has_no_tens_keys_or_pm_10_values():
    G = GENS["facts-mix-10"]
    for form, a, b in (("R", 3, 4), ("C", 4, 6), ("S", 3, 6)):
        ans = G.answer_of("sub", form, a, b)
        cand = dict(G.sub_candidates(form, a, b))
        assert not any(abs(v - ans) == 10 for v in cand), (form, cand)
        assert "TENS_SLIP" not in cand.values() and "MISSING_TENS" not in cand.values()


MUL_GOLDEN = [  # (form, a, b, answer, {value: key})   R a x b = ?, C a x ? = p, S ? x b = p
    ("R", 3, 4, 12, {15: "GROUP_OFF", 16: "GROUP_OFF", 9: "GROUP_OFF", 8: "GROUP_OFF", 7: "ADDED"}),
    ("R", 13, 6, 78, {91: "GROUP_OFF", 72: "GROUP_OFF", 19: "ADDED", 68: "DROPPED_CARRY", 88: "TENS_SLIP"}),
    ("R", 12, 13, 156, {106: "PARTIAL_PRODUCTS", 146: "TENS_SLIP", 166: "TENS_SLIP", 25: "ADDED"}),
    ("C", 6, 7, 7, {8: "MISSING_ONE_OFF", 6: "MISSING_ONE_OFF", 36: "MISSING_SUBTRACTED", 42: "MISSING_PRODUCT"}),
    ("S", 6, 7, 6, {7: "MISSING_ONE_OFF", 5: "MISSING_ONE_OFF", 35: "MISSING_SUBTRACTED", 42: "MISSING_PRODUCT"}),
]


@pytest.mark.parametrize("form,a,b,ans,wrong", MUL_GOLDEN, ids=[f"{g[0]}-{g[1]}x{g[2]}" for g in MUL_GOLDEN])
def test_golden_mul_keys(form, a, b, ans, wrong):
    G = GENS["facts-mix-50"]
    assert G.answer_of("mul", form, a, b) == ans
    assert parse(G.prompt_of("mul", form, a, b)) == ("mul", form, (a, b), ans)
    cand = {v: k for k, v in G.mul_candidates(form, a, b)}
    assert ans not in cand
    for v, key in wrong.items():
        assert cand.get(v) == key, (v, key, cand)
    if max(a, b) < 11:
        assert not {"DROPPED_CARRY", "TENS_SLIP", "PARTIAL_PRODUCTS"} & set(cand.values())


DIV_GOLDEN = [  # (form, a, b, answer, {value: key})   the fact is p / a = b, p = a x b
    ("R", 6, 7, 7, {8: "GROUP_OFF", 6: "GROUP_OFF", 9: "GROUP_OFF", 5: "GROUP_OFF", 36: "SUBTRACTED", 252: "MULTIPLIED"}),
    ("R", 3, 14, 14, {15: "GROUP_OFF", 13: "GROUP_OFF", 24: "TENS_SLIP", 4: "TENS_SLIP", 39: "SUBTRACTED"}),
    ("C", 6, 7, 6, {7: "MISSING_ONE_OFF", 5: "MISSING_ONE_OFF", 35: "MISSING_SUBTRACTED", 294: "MISSING_MULTIPLIED"}),
    ("S", 6, 7, 42, {48: "START_GROUP_OFF", 36: "START_GROUP_OFF", 13: "START_ADDED"}),
    ("S", 12, 7, 84, {96: "START_GROUP_OFF", 72: "START_GROUP_OFF", 19: "START_ADDED", 94: "START_TENS", 74: "START_TENS"}),
]


@pytest.mark.parametrize("form,a,b,ans,wrong", DIV_GOLDEN, ids=[f"{g[0]}-{g[1]},{g[2]}" for g in DIV_GOLDEN])
def test_golden_div_keys(form, a, b, ans, wrong):
    G = GENS["facts-mix-50"]
    assert G.answer_of("div", form, a, b) == ans
    assert parse(G.prompt_of("div", form, a, b)) == ("div", form, (a, b), ans)
    cand = {v: k for v, (k, _) in G.div_candidates(form, a, b).items()}
    assert ans not in cand
    for v, key in wrong.items():
        assert cand.get(v) == key, (v, key, cand)


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked item; the 6/6/6/6 split; floors; zero cap
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cid", IDS)
def test_every_baked_item_is_right(cid):
    problems = [(it["id"], it["prompt"], check_item(cid, it)) for it in BAKED[cid]["items"] if check_item(cid, it)]
    assert not problems, problems[:5]


@pytest.mark.parametrize("cid", IDS)
def test_split_is_six_of_each_operation_per_tier_and_prompts_unique(cid):
    for t in range(1, 6):
        its = by_tier(cid, t)
        assert len(its) == N
        assert len({it["prompt"] for it in its}) == N
        assert Counter(parse(it["prompt"])[0] for it in its) == {op: PER_OP for op in OPS}, (cid, t)


@pytest.mark.parametrize("cid", IDS)
def test_floors_forms_and_no_ambiguity(cid):
    r = rng_of(cid)
    for t in range(1, 6):
        for op in OPS:
            sixes = [parse(it["prompt"]) for it in by_tier(cid, t) if parse(it["prompt"])[0] == op]
            forms = [(f, x) for _, f, x, _ in sixes]
            for form, pairs, floor in POOLS[(op, r)][t]:
                have = sum(1 for f, x in forms if f == form and x in pairs)
                assert have >= floor, (cid, t, op, form, have, floor)
            allowed = {f for f, _, _ in POOLS[(op, r)][t]}
            assert {f for f, _ in forms} <= allowed, (cid, t, op)
            for f, (a, b) in forms:
                if op == "div":
                    assert a >= 1, "division by 0"
                if f != "R" and op == "mul":
                    assert a >= 1 and b >= 1, "0 x ? = 0 is ambiguous"
                if f != "R" and op == "div":
                    assert b >= 1, "0 / ? = 0 is ambiguous"
    for t in (4,):
        assert {parse(it["prompt"])[1] for it in by_tier(cid, t)} == {"C"}


@pytest.mark.parametrize("cid", IDS)
def test_zero_factor_multiplication_is_capped(cid):
    for t in range(1, 6):
        zeros = [it for it in by_tier(cid, t)
                 if parse(it["prompt"])[0] == "mul" and parse(it["prompt"])[1] == "R" and 0 in parse(it["prompt"])[2]]
        assert len(zeros) <= 2, (cid, t, len(zeros))


def test_pool_sizes_cover_six():
    for (op, r), pools in POOLS.items():
        for t in range(1, 6):
            union = {(f, x) for f, ps, _ in pools[t] for x in ps}
            assert len(union) >= PER_OP, (op, r, t, len(union))
            assert sum(fl for _, _, fl in pools[t]) <= PER_OP + 1  # overlapping parts may share an item


@pytest.mark.parametrize("cid", IDS)
def test_same_prompt_same_answer_as_the_operations_own_cartridge(cid):
    r = rng_of(cid)
    shared = 0
    for op in OPS:
        own = {(it["tier"], it["prompt"]): it for it in load_baked(own_id(op, r))["items"]}
        for it in BAKED[cid]["items"]:
            if parse(it["prompt"])[0] != op:
                continue
            twin = own.get((it["tier"], it["prompt"]))
            if twin is not None:
                shared += 1
                assert twin["choices"][twin["answer"]] == it["choices"][it["answer"]], (cid, it["prompt"])
    assert shared >= 1, "no prompt in common with any own cartridge: the cross-check checked nothing"


def test_cross_check_can_fail():
    """Disproof: an item whose answer differs from the own cartridge's is caught by the same comparison."""
    own = load_baked("facts-add-20")["items"][0]
    wrong = dict(own, choices=[str(int(c) + 1) for c in own["choices"]])
    assert own["choices"][own["answer"]] != wrong["choices"][wrong["answer"]]


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


def needs_twin(it):
    """The ones-digit rule applies: add and sub answers >= 20; mul R and div S with a factor >= 11 and answer >= 20."""
    op, form, (a, b), ans = parse(it["prompt"])
    if ans < 20:
        return False
    if op in ("add", "sub"):
        return True
    if op == "mul":
        return form == "R" and max(a, b) >= 11
    return form == "S" and max(a, b) >= 11


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
    rule = [it for it in by_tier(cid, t) if needs_twin(it)]
    if len(rule) >= 8:
        assert sum(ones_alone(it) for it in rule) / len(rule) <= 0.25, (cid, t)


@pytest.mark.parametrize("cid", IDS)
def test_ones_digit_twin_on_every_ruled_item(cid):
    tells = [it["prompt"] for it in BAKED[cid]["items"] if needs_twin(it) and ones_alone(it)]
    assert len(tells) <= 0.1 * N * 5, tells  # the generator relaxes the twin only where no value can carry it
    assert len(tells) <= 2, tells


@pytest.mark.parametrize("cid", IDS)
def test_addition_has_no_parity_tell(cid):
    adds = [it for it in BAKED[cid]["items"] if parse(it["prompt"])[0] == "add"]
    odd_one = sum(all(x % 2 != vals_of(it)[it["answer"]] % 2
                      for k, x in enumerate(vals_of(it)) if k != it["answer"]) for it in adds)
    assert odd_one / len(adds) <= 0.10, (cid, odd_one)


@pytest.mark.parametrize("cid", IDS)
def test_wrong_choices_distinct_nonnegative_bounded(cid):
    for it in BAKED[cid]["items"]:
        v = vals_of(it)
        assert len(set(v)) == 4 and all(0 <= x <= 999 for x in v)


def test_range_10_additive_items_carry_no_pm_10_values():
    cid = "facts-mix-10"
    for it in BAKED[cid]["items"]:
        op, form, (a, b), ans = parse(it["prompt"])
        if op == "sub":  # (add 5 + 5 may offer 0 = |a - b| as SUBTRACTED, a misconception that happens to sit 10 away)
            assert all(abs(v - ans) != 10 for v in vals_of(it)), it["prompt"]
        if op in ("add", "sub"):
            assert not any(k and k.endswith(("TENS_SLIP", "TENS", "NO_CARRY", "FORGOT_TRADE")) for k in it["misconceptions"])


# ---------------------------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cid", IDS)
def test_explanation_states_the_answer_and_the_fact(cid):
    for it in BAKED[cid]["items"]:
        op, form, (a, b), ans = parse(it["prompt"])
        e = it["explanation"]
        assert "1 tens" not in e, it
        if form == "R":
            assert re.search(rf"\b{ans}\b", e), it
            assert e.startswith(it["prompt"].replace(" = ?", "").replace("?", "")[:2]), it
        else:
            assert e.startswith(it["prompt"]), it
            assert re.search(rf"\? = {ans}\b", e), it
        if op == "add":
            assert f"{a} + {b} = {a + b}" in e, it
        if op == "mul":
            assert f"{a} × {b} = {a * b}" in e or form == "R" and f"{a} × {b} = {a * b}" in e, it
        if op == "div" and form != "R":
            assert f"{a * b}" in e, it


@pytest.mark.parametrize("cid", IDS)
def test_add_strategy_clause_is_not_the_fact_restated(cid):
    for it in BAKED[cid]["items"]:
        op, form, (a, b), ans = parse(it["prompt"])
        if op != "add" or form == "R":
            continue
        k = a if form == "C" else b
        strategy = it["explanation"].split(f"so ? = {ans}.", 1)[1].strip()
        assert strategy, it
        assert f"{k} + {ans} = {a + b}" not in strategy and f"{ans} + {k} = {a + b}" not in strategy, it


# ---------------------------------------------------------------------------------------------
# Key labels: a labelled wrong value really is what its key says (checked from the prompt alone)
# ---------------------------------------------------------------------------------------------
def slfl(s, a):
    out, place = 0, 1
    while s or a:
        out += abs(s % 10 - a % 10) * place
        s //= 10
        a //= 10
        place *= 10
    return out


def key_ok(op, bare, form, a, b, ans, c):
    s, p = a + b, a * b
    if op == "add":
        k = a if form == "C" else b
        return {"ONE_OFF": abs(c - s) == 1, "SUBTRACTED": c == abs(a - b),
                "NO_CARRY": c == s - 10 and regroups(a, b), "TENS_SLIP": abs(c - s) == 10,
                "MISSING_ADDED": c == k + s, "MISSING_ONE_OFF": abs(c - ans) == 1,
                "MISSING_TENS": abs(c - ans) == 10}[bare]
    if op == "sub":
        return {"ONE_OFF": abs(c - b) == 1, "ADDED": c == s + a, "SMALLER_FROM_LARGER": c == slfl(s, a),
                "FORGOT_TRADE": c == b + 10, "TENS_SLIP": abs(c - ans) == 10, "MISSING_ADDED": c == s + b,
                "MISSING_ONE_OFF": abs(c - ans) == 1, "MISSING_TENS": abs(c - ans) == 10,
                "START_SUBTRACTED": c == abs(b - a), "START_NO_CARRY": c == s - 10 and regroups(a, b)}[bare]
    if op == "mul":
        k = b if form == "S" else a
        return {"GROUP_OFF": c in (a * (b + 1), (a + 1) * b, a * (b - 1), (a - 1) * b), "ADDED": c == a + b,
                "DROPPED_CARRY": c == p - 10, "TENS_SLIP": abs(c - p) == 10,
                "PARTIAL_PRODUCTS": c == (a // 10) * (b // 10) * 100 + (a % 10) * (b % 10),
                "MISSING_ONE_OFF": abs(c - ans) == 1, "MISSING_SUBTRACTED": c == p - k, "MISSING_PRODUCT": c == p}[bare]
    return {"GROUP_OFF": abs(c - b) in (1, 2), "SUBTRACTED": c == p - a, "MULTIPLIED": c == p * a,
            "TENS_SLIP": abs(c - b) == 10, "MISSING_ONE_OFF": abs(c - a) == 1, "MISSING_SUBTRACTED": c == p - b,
            "MISSING_MULTIPLIED": c == p * b, "START_GROUP_OFF": c in (a * (b + 1), a * (b - 1)),
            "START_ADDED": c == a + b, "START_TENS": abs(c - p) == 10}[bare]


@pytest.mark.parametrize("cid", IDS)
def test_keys_match_the_value_they_label(cid):
    for it in BAKED[cid]["items"]:
        op, form, (a, b), ans = parse(it["prompt"])
        for c, key in zip(vals_of(it), it["misconceptions"]):
            if key is None or key == "ARITH":
                continue
            bare = key.split("_", 1)[1]
            assert key_ok(op, bare, form, a, b, ans, c), (it["prompt"], c, key)


# ---------------------------------------------------------------------------------------------
# Disproofs: the checkers must be able to fail
# ---------------------------------------------------------------------------------------------
def planted(cid, tier, prompt, choices, answer=0):
    return {"tier": tier, "prompt": prompt, "choices": choices, "answer": answer,
            "misconceptions": [None] + ["ARITH"] * 3, "explanation": "x"}


def test_checker_accepts_a_good_item_of_each_operation():
    assert check_item("facts-mix-50", planted(0, 3, "27 + 6 = ?", ["33", "32", "34", "23"])) == []
    assert check_item("facts-mix-50", planted(0, 3, "33 − 6 = ?", ["27", "26", "28", "37"])) == []
    assert check_item("facts-mix-50", planted(0, 3, "7 × 8 = ?", ["56", "63", "49", "15"])) == []
    assert check_item("facts-mix-50", planted(0, 3, "56 ÷ 8 = ?", ["7", "6", "8", "9"])) == []


def test_checker_rejects_planted_bad_items():
    cid = "facts-mix-50"
    good = planted(0, 3, "7 × 8 = ?", ["56", "63", "49", "15"])
    assert check_item(cid, good) == []
    assert "answer is wrong" in check_item(cid, dict(good, choices=["54", "63", "49", "15"]))
    assert "four distinct choices" in check_item(cid, dict(good, choices=["56", "56", "49", "63"]))
    bad = check_item(cid, dict(good, choices=["56", "15", "1", "99"]))
    assert "fewer than 2 near distractors" in bad and "more than 1 far distractor" in bad
    assert "choice out of 0..999" in check_item(cid, dict(good, choices=["56", "63", "49", "1000"]))
    assert "factor over range" in check_item("facts-mix-10", dict(good, prompt="7 × 8 = ?"))
    # a pair outside the tier's pools: 10 x 7 is not a tier-2 pair of mul-12 (3, 4, 9, 12)
    assert "pair not in the tier's pools" in check_item(cid, dict(good, tier=2, prompt="10 × 7 = ?"))
    # a sum outside the range, and an add pair with a multiple of ten in the no-regrouping tier
    assert "sum outside the range" in check_item(cid, dict(planted(0, 2, "20 + 90 = ?", ["110", "109", "111", "100"])))
    assert "pair not in the tier's pools" in check_item(cid, planted(0, 2, "20 + 15 = ?", ["35", "34", "36", "25"]))
    # a wrong division answer and a division in the wrong form for the tier
    assert "answer is wrong" in check_item(cid, planted(0, 3, "56 ÷ 8 = ?", ["8", "7", "6", "9"]))
    assert "pair not in the tier's pools" in check_item(cid, planted(0, 4, "56 ÷ 8 = ?", ["7", "6", "8", "9"]))
    # a near set for a multiplication C item is within 2, not within the larger factor
    assert "fewer than 2 near distractors" in check_item(
        cid, planted(0, 4, "6 × ? = 42", ["7", "42", "40", "35"]))
    # 0 x ? = 0 has no single answer: the parser refuses it
    assert check_item(cid, planted(0, 4, "0 × ? = 0", ["1", "2", "3", "4"])) == ["prompt shape"]


def test_split_and_floor_counters_can_fail():
    cid = "facts-mix-50"
    lopsided = [it for it in by_tier(cid, 2) if parse(it["prompt"])[0] != "div"][:18] + [
        it for it in by_tier(cid, 2) if parse(it["prompt"])[0] == "add"][:6]
    assert Counter(parse(it["prompt"])[0] for it in lopsided) != {op: PER_OP for op in OPS}
    # floor counter: add-50 T2 asks (R one-digit no-regroup >= 2, R both two-digit >= 2); six one-digit-only prompts miss the second
    (f1, pairs1, fl1), (f2, pairs2, fl2) = POOLS[("add", 50)][2]
    only_small = [x for x in sorted(pairs1 - pairs2)][:PER_OP]
    assert len(only_small) == PER_OP
    assert sum(x in pairs1 for x in only_small) >= fl1 and sum(x in pairs2 for x in only_small) < fl2


def test_ones_digit_and_rank_checkers_can_fail():
    tell = {"choices": ["81", "82", "83", "85"], "answer": 3}
    assert ones_alone(tell)
    assert not ones_alone({"choices": ["75", "84", "85", "95"], "answer": 2})
    always_middle = [{"choices": ["10", "11", "12", "13"], "answer": 1}] * 24
    assert Counter(rank_of_answer(it) for it in always_middle)[1] / 24 > 0.35
    assert needs_twin({"prompt": "13 × 7 = ?"}) and not needs_twin({"prompt": "6 × 7 = ?"})
