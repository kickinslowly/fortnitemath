"""facts-div-5/10/12/15: golden misconception values, an independent re-check of every baked item, pools and floors
rebuilt here from the words of briefs/facts2/pools.py, distractor rules, and a checker self-test (a disproof)."""
import json
import random
import re

import pytest

from fnm.cart import REPO_ROOT, load_generator

RANGES = (5, 10, 12, 15)
IDS = [f"facts-div-{r}" for r in RANGES]
BAKED = {}
for _id in IDS:
    with open(REPO_ROOT / "cartridges" / _id / "baked.json", encoding="utf-8") as _f:
        BAKED[_id] = json.load(_f)
G = load_generator("facts-div-5")
PROMPT = re.compile(r"^(\d+|\?) ([+−×÷]) (\d+|\?) = (\d+|\?)$")
TIER_CASES = [(i, t) for i in IDS for t in range(1, 6)]


def items(cid, tier):
    return [it for it in BAKED[cid]["items"] if it["tier"] == tier]


# ------------------------------------------------------------------------------------------------ independent solve
def parse(prompt):
    """-> (form, a, b, p, answer) solved with plain Python; form R, C or S."""
    m = PROMPT.match(prompt)
    assert m, prompt
    x, op, y, z = m.groups()
    assert op == "÷" and [x, y, z].count("?") == 1, prompt
    if z == "?":
        p, a = int(x), int(y)
        assert a != 0 and p % a == 0, prompt
        return "R", a, p // a, p, p // a
    if y == "?":
        p, b = int(x), int(z)
        assert b != 0 and p % b == 0, prompt
        return "C", p // b, b, p, p // b
    a, b = int(y), int(z)
    assert a != 0 and b != 0, prompt
    return "S", a, b, a * b, a * b


# ------------------------------------------------------------------------------------------------ independent pools
def grid(n, low=0):
    return {(a, b) for a in range(low, n + 1) for b in range(low, n + 1)}


EASY = {0, 1, 2, 5, 10}
MID = {3, 4, 9}
HARD = {6, 7, 8}
CORE = MID | HARD


def easy_fact(x):
    return bool(EASY & set(x)) or (11 in x and min(x) <= 9)


def mk_pools(r):
    """tier -> [(form, set of pairs, floor)] before the division filter."""
    if r == 5:
        g, g1, g2 = grid(5), grid(5, 1), grid(5, 2)
        return {1: [("R", {x for x in g if {0, 1, 2, 5} & set(x)}, 0)],
                2: [("R", g1, 0)],
                3: [("R", g2, 12), ("C", {x for x in g1 if x[0] in (2, 5)}, 8)],
                4: [("C", g1, 0)],
                5: [("S", g2, 12), ("C", g2, 0)]}
    if r == 10:
        g = grid(10)
        core = {x for x in g if set(x) <= CORE}
        return {1: [("R", {x for x in g if EASY & set(x)}, 0)],
                2: [("R", {x for x in core if set(x) <= MID}, 8), ("R", {x for x in core if MID & set(x)}, 0)],
                3: [("R", {x for x in core if set(x) <= HARD}, 8), ("R", {x for x in core if HARD & set(x)}, 0)],
                4: [("C", core, 12), ("C", grid(10, 2), 0)],
                5: [("S", core, 12), ("C", core, 0)]}
    if r == 12:
        g = grid(12)
        core = {x for x in g if set(x) <= CORE}
        t1 = {x for x in g if easy_fact(x)}
        t2n = {x for x in g if 12 in x and min(x) in MID}
        t3n = {x for x in g if not easy_fact(x) and max(x) >= 11 and (HARD & set(x) or min(x) >= 11)}
        c12 = {x for x in grid(12, 3) if not easy_fact(x)}
        bg = lambda s: {x for x in s if max(x) >= 11}
        return {1: [("R", bg(t1), 8), ("R", t1, 0)],
                2: [("R", t2n, 6), ("R", {x for x in core if set(x) <= MID}, 6), ("R", {x for x in core if MID & set(x)}, 0)],
                3: [("R", t3n, 8), ("R", {x for x in core if set(x) <= HARD}, 6), ("R", {x for x in core if HARD & set(x)}, 0)],
                4: [("C", bg(c12), 6), ("C", core, 8), ("C", grid(12, 2), 0)],
                5: [("S", bg(c12), 6), ("S", c12, 6), ("C", bg(c12), 4), ("C", c12, 0)]}
    g = grid(15)
    t1 = {x for x in g if easy_fact(x)}
    teen = lambda s: {x for x in s if max(x) >= 11}
    core = {x for x in g if set(x) <= CORE}
    h = {x for x in grid(15, 3) if not easy_fact(x)}
    t2 = {x for x in teen(g) if not easy_fact(x) and min(x) in (3, 4)}
    t3 = {x for x in teen(g) if not easy_fact(x) and (min(x) in (6, 7, 8, 9) or min(x) >= 11)}
    return {1: [("R", teen(t1), 12), ("R", t1, 0)],
            2: [("R", t2, 12), ("R", {x for x in core if MID & set(x)}, 0)],
            3: [("R", t3, 12), ("R", {x for x in core if HARD & set(x)}, 0)],
            4: [("C", teen(h), 12), ("C", h, 0)],
            5: [("S", teen(h), 8), ("S", h, 4), ("C", teen(h), 4), ("C", h, 0)]}


def usable(form, x):
    return x[0] != 0 and (form == "R" or x[1] >= 1)


def tier_union(r, t):
    return {(f, x) for f, ps, _ in mk_pools(r)[t] for x in ps if usable(f, x)}


NAMES = {
    5: ["Easy: 0, 1, 2, 5", "All to 25 ÷ 5", "Facts with 2 to 5", "Missing divisors", "Missing dividends"],
    10: ["Easy: 0, 1, 2, 5, 10", "Facts with 3, 4, 9", "Facts with 6, 7, 8", "Missing divisors", "Missing dividends"],
    12: ["Easy rows and 11s", "Facts with 3, 4, 9, 12", "Facts with 6, 7, 8, 12", "Missing divisors", "Missing dividends"],
    15: ["Easy rows to 15", "Teens and 3s, 4s", "Teens and 6 to 15", "Missing divisors", "Missing dividends"],
}


# ------------------------------------------------------------------------------------------------ the checker
def check_item(it, r):
    """Every rule on one baked item; returns a list of problems (empty = fine)."""
    bad = []
    try:
        form, a, b, p, ans = parse(it["prompt"])
    except AssertionError:
        return [f"unparseable or inexact {it['prompt']}"]
    if (form, (a, b)) not in tier_union(r, it["tier"]):
        bad.append("outside the tier's pools")
    vals = [int(c) for c in it["choices"]]
    if len(vals) != 4:
        bad.append("not 4 choices")
    if vals[it["answer"]] != ans:
        bad.append("wrong answer")
    if sum(v == ans for v in vals) != 1:
        bad.append("answer not unique")
    if len(set(vals)) != len(vals):
        bad.append("choices not distinct")
    if not all(0 <= v <= 999 for v in vals):
        bad.append("range")
    tol = max(a, b) if form == "S" else 2
    wrong = [v for v in vals if v != ans]
    near = sum(1 for v in wrong if abs(v - ans) <= tol)
    if near < 2:
        bad.append("fewer than 2 near")
    if len(wrong) - near > 1:
        bad.append("more than 1 far")
    return bad


@pytest.mark.parametrize("cid,tier", TIER_CASES)
def test_every_baked_item_rechecked(cid, tier):
    r = int(cid.rsplit("-", 1)[1])
    its = items(cid, tier)
    assert len(its) == BAKED[cid]["items_per_tier"] == 24
    for it in its:
        assert check_item(it, r) == [], it["prompt"]


def test_checker_rejects_planted_items():
    good = dict(tier=3, prompt="56 ÷ 7 = ?", choices=["8", "9", "7", "49"], answer=0)
    assert check_item(good, 10) == []
    assert "wrong answer" in check_item({**good, "answer": 1}, 10)
    # 56 ÷ 7 is a facts-with-6,7,8 prompt: planted in tier 1 or 2 of range 10 it is outside the pools
    assert "outside the tier's pools" in check_item({**good, "tier": 2}, 10)
    assert "outside the tier's pools" in check_item({**good, "tier": 1}, 10)
    assert "fewer than 2 near" in check_item({**good, "choices": ["8", "9", "20", "49"]}, 10)
    assert "choices not distinct" in check_item({**good, "choices": ["8", "9", "9", "49"]}, 10)
    assert "more than 1 far" in check_item({**good, "choices": ["8", "9", "100", "49"]}, 10)
    assert check_item({**good, "prompt": "57 ÷ 7 = ?"}, 10) == ["unparseable or inexact 57 ÷ 7 = ?"]
    assert check_item({**good, "prompt": "8 ÷ 0 = ?"}, 10)
    assert check_item({**good, "prompt": "? ÷ ? = 8"}, 10)
    # a missing dividend with answer 0 would be ambiguous: 0 ÷ ? = 0
    assert check_item({**good, "prompt": "0 ÷ ? = 0", "choices": ["1", "2", "3", "4"]}, 10)
    # an item from range 15's pools is outside range 5's
    assert "outside the tier's pools" in check_item(dict(tier=1, prompt="165 ÷ 11 = ?", choices=["15", "14", "16", "13"], answer=0), 5)


# ------------------------------------------------------------------------------------------------ golden values
GOLDEN = [
    # form, key, a, b, sign, size, wrong value   (fact p = a x b)
    ("R", "GROUP_OFF", 7, 8, 1, 1, 9), ("R", "GROUP_OFF", 7, 8, -1, 1, 7), ("R", "GROUP_OFF", 7, 8, 1, 2, 10),
    ("R", "SUBTRACTED", 7, 8, 1, 1, 49), ("R", "MULTIPLIED", 7, 8, 1, 1, 392),
    ("R", "TENS_SLIP", 12, 13, 1, 1, 23), ("R", "TENS_SLIP", 12, 13, -1, 1, 3), ("R", "TENS_SLIP", 7, 8, 1, 1, None),
    ("R", "MULTIPLIED", 15, 15, 1, 1, None),
    ("C", "MISSING_ONE_OFF", 6, 7, 1, 1, 7), ("C", "MISSING_ONE_OFF", 6, 7, -1, 1, 5),
    ("C", "MISSING_SUBTRACTED", 6, 7, 1, 1, 35), ("C", "MISSING_MULTIPLIED", 6, 7, 1, 1, 294),
    ("C", "MISSING_MULTIPLIED", 15, 15, 1, 1, None),
    ("S", "START_GROUP_OFF", 6, 7, 1, 1, 48), ("S", "START_GROUP_OFF", 6, 7, -1, 1, 36),
    ("S", "START_ADDED", 6, 7, 1, 1, 13), ("S", "START_TENS", 12, 7, 1, 1, 94), ("S", "START_TENS", 12, 7, -1, 1, 74),
    ("S", "START_TENS", 6, 7, 1, 1, None),
]


@pytest.mark.parametrize("form,key,a,b,sign,size,wrong", GOLDEN)
def test_golden_values(form, key, a, b, sign, size, wrong):
    assert G.wrong_value(form, key, a, b, sign, size) == wrong


def test_candidates_first_key_wins_and_never_the_answer():
    cand = G.candidates("R", 2, 1)  # 2 ÷ 2 = 1: p - a = 0 is also GROUP_OFF b - 1 = 0
    assert cand[0][0] == "GROUP_OFF" and 1 not in cand
    cand = G.candidates("S", 1, 5)  # ? ÷ 1 = 5: START_ADDED a + b = 6 is also START_GROUP_OFF p + a = 6
    assert cand[6][0] == "START_GROUP_OFF" and 5 not in cand


def test_hand_worked_prompts_of_each_form():
    assert G.prompt_of("R", 7, 6) == "42 ÷ 7 = ?" and G.answer_of("R", 7, 6) == 6
    assert G.prompt_of("C", 6, 7) == "42 ÷ ? = 7" and G.answer_of("C", 6, 7) == 6
    assert G.prompt_of("S", 6, 7) == "? ÷ 6 = 7" and G.answer_of("S", 6, 7) == 42
    assert G.explanation("C", 6, 7) .startswith("42 ÷ ? = 7: 7 × 6 = 42, so ? = 6.")
    assert G.explanation("S", 6, 7).startswith("? ÷ 6 = 7: 6 × 7 = 42, so ? = 42.")
    assert G.explanation("R", 6, 7).startswith("42 ÷ 6 = 7 because 6 × 7 = 42.")


def test_explanations_fit():
    for r in RANGES:
        for t in range(1, 6):
            for f, (a, b) in tier_union(r, t):
                e = G.explanation(f, a, b)
                assert len(e) <= 160 and e.isprintable(), (f, a, b, e)


# ------------------------------------------------------------------------------------------------ pools and floors
def test_generators_byte_identical():
    ref = (REPO_ROOT / "cartridges" / IDS[0] / "generator.py").read_bytes()
    for cid in IDS[1:]:
        assert (REPO_ROOT / "cartridges" / cid / "generator.py").read_bytes() == ref


@pytest.mark.parametrize("cid,tier", TIER_CASES)
def test_pools_floors_and_uniqueness(cid, tier):
    r = int(cid.rsplit("-", 1)[1])
    its = items(cid, tier)
    prompts = [it["prompt"] for it in its]
    assert len(set(prompts)) == len(prompts)
    seen = []
    for it in its:
        form, a, b, p, ans = parse(it["prompt"])
        assert (form, (a, b)) in tier_union(r, tier), it["prompt"]
        assert a >= 1 and (form == "R" or b >= 1)
        seen.append((form, (a, b)))
    for form, pairs, floor in mk_pools(r)[tier]:
        ps = {x for x in pairs if usable(form, x)}
        assert sum(1 for f, x in seen if f == form and x in ps) >= floor, (form, floor)


def test_tier_names_and_catalog():
    for cid, r in zip(IDS, RANGES):
        B = BAKED[cid]
        assert [t["name"] for t in B["tiers"]] == NAMES[r]
        assert B["grade"] == "Facts" and B["picker_order"] == 13 + RANGES.index(r)
        assert B["seed"] == 20261063 + RANGES.index(r)
        keys = {k for it in B["items"] for k in it["misconceptions"] if k not in (None, "ARITH")}
        assert keys <= set(B["misconceptions"])


# ------------------------------------------------------------------------------------------------ labels, ranks, ones
def test_misconception_labels_match_values():
    for cid in IDS:
        for it in BAKED[cid]["items"]:
            form, a, b, p, ans = parse(it["prompt"])
            for c, k in zip(it["choices"], it["misconceptions"]):
                v = int(c)
                if k is None:
                    assert v == ans
                elif k == "GROUP_OFF":
                    assert form == "R" and abs(v - b) in (1, 2), it
                elif k == "SUBTRACTED":
                    assert form == "R" and v == p - a, it
                elif k == "MULTIPLIED":
                    assert form == "R" and v == p * a, it
                elif k == "TENS_SLIP":
                    assert form == "R" and abs(v - b) == 10, it
                elif k == "MISSING_ONE_OFF":
                    assert form == "C" and abs(v - a) == 1, it
                elif k == "MISSING_SUBTRACTED":
                    assert form == "C" and v == p - b, it
                elif k == "MISSING_MULTIPLIED":
                    assert form == "C" and v == p * b, it
                elif k == "START_GROUP_OFF":
                    assert form == "S" and abs(v - p) == a, it
                elif k == "START_ADDED":
                    assert form == "S" and v == a + b, it
                elif k == "START_TENS":
                    assert form == "S" and abs(v - p) == 10 and max(a, b) >= 11, it
                else:
                    assert k == "ARITH", it


def rank_shares(its):
    counts = [0, 0, 0, 0]
    for it in its:
        vals = [int(c) for c in it["choices"]]
        counts[sum(v < vals[it["answer"]] for v in vals)] += 1
    return [c / len(its) for c in counts]


@pytest.mark.parametrize("cid,tier", TIER_CASES)
def test_no_middle_tell(cid, tier):
    for share in rank_shares(items(cid, tier)):
        assert 0.15 <= share <= 0.35, rank_shares(items(cid, tier))


def test_rank_checker_fails_on_a_middle_tell():
    planted = [dict(choices=["7", "8", "9", "30"], answer=1) for _ in range(10)]
    assert not all(0.15 <= s <= 0.35 for s in rank_shares(planted))


def twin_items(its):
    out = []
    for it in its:
        form, a, b, p, ans = parse(it["prompt"])
        if form == "S" and max(a, b) >= 11 and ans >= 20:
            out.append(it)
    return out


def only_share(its):
    only = 0
    for it in its:
        vals = [int(c) for c in it["choices"]]
        ans = vals[it["answer"]]
        only += sum(v % 10 == ans % 10 for v in vals) == 1
    return only / len(its) if its else 0.0


@pytest.mark.parametrize("cid,tier", TIER_CASES)
def test_no_ones_digit_tell(cid, tier):
    sel = twin_items(items(cid, tier))
    if len(sel) >= 8:
        assert only_share(sel) <= 0.25, (len(sel), only_share(sel))


def test_ones_digit_checker_fails_on_a_tell():
    planted = [dict(prompt="? ÷ 12 = 7", choices=["84", "74", "83", "85"], answer=0),
               dict(prompt="? ÷ 12 = 7", choices=["84", "88", "83", "85"], answer=0)]
    assert only_share(planted) == 0.5


@pytest.mark.parametrize("cid,tier", TIER_CASES)
def test_answer_positions_balanced(cid, tier):
    its = items(cid, tier)
    for pos in range(4):
        share = sum(it["answer"] == pos for it in its) / len(its)
        assert 0.5 / 4 <= share <= 1.5 / 4


def test_determinism():
    for cid in IDS:
        B = BAKED[cid]
        again = load_generator(cid).generate(B, random.Random(B["seed"]))
        assert [(i["prompt"], i["choices"]) for i in again] == [(i["prompt"], i["choices"]) for i in B["items"]]


# ------------------------------------------------------------------------------------------------ explanation / text truth
def test_divided_by_itself_only_when_dividend_equals_divisor():
    hits = 0
    for cid in IDS:
        for it in BAKED[cid]["items"]:
            form, a, b, p, ans = parse(it["prompt"])
            if "divided by itself" in it["explanation"]:
                hits += 1
                assert p == a, (it["prompt"], it["explanation"])
    assert hits > 0
    sq = G.explanation("C", 5, 5)
    assert "divided by itself" not in sq and "5 × 5 = 25" in sq


def test_student_texts_are_generic():
    """A student text shows after the wrong door on every item of its key: it must quote no example numbers."""
    for cid in IDS:
        for key, m in BAKED[cid]["misconceptions"].items():
            assert not re.search(r"\d", m["student"]), (key, m["student"])
            assert len(m["student"]) <= 80
