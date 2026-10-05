"""factors-multiples cartridge: golden misconception rules, an independent re-check of every baked
answer (brute force here, never the generator's gcd/lcm), value-distinct doors, and the cartridge's
bounds asserted on baked.json with a checker that is shown to reject out-of-bounds prompts.
"""
import json
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "factors-multiples"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Independent math (brute force; no math.gcd, nothing from the generator)
# ---------------------------------------------------------------------------------------------
def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def bf_gcf(a, b):
    return max(d for d in range(1, min(a, b) + 1) if a % d == 0 and b % d == 0)


def bf_lcm(*nums):
    m = max(nums)
    k = m
    while any(k % x for x in nums):
        k += m
    return k


def bf_prime(n):
    return len(divisors(n)) == 2


def nums_in(s):
    return [int(x) for x in re.findall(r"\d+", s)]


# ---------------------------------------------------------------------------------------------
# Prompt classification (by the test's own regexes)
# ---------------------------------------------------------------------------------------------
LCM_WORDS = ("Fewest", "Next together", "Next both", "again in")
GCF_WORDS = ("Most", "Longest")


def kind_of(prompt):
    if m := re.fullmatch(r"Which is a factor of (\d+)\?", prompt):
        return "factor", [int(m[1])]
    if m := re.fullmatch(r"Which is a multiple of (\d+)\?", prompt):
        return "multiple", [int(m[1])]
    if m := re.fullmatch(r"How many factors does (\d+) have\?", prompt):
        return "count", [int(m[1])]
    if prompt in G.PRIME_PROMPTS:
        return "prime", []
    if m := re.fullmatch(r"GCF of (\d+) and (\d+)\?", prompt):
        return "gcf", [int(m[1]), int(m[2])]
    if m := re.fullmatch(r"LCM of (\d+)(?:, (\d+))? and (\d+)\?", prompt):
        return "lcm", [int(x) for x in m.groups() if x]
    if m := re.fullmatch(r"Factor out the GCF: (\d+) \+ (\d+)", prompt):
        return "full", [int(m[1]), int(m[2])]
    if m := re.fullmatch(r"(\d+) \+ (\d+) = (\d+)\(\? \+ \?\)", prompt):
        return "inside", [int(m[1]), int(m[2]), int(m[3])]
    ns = nums_in(prompt)
    if any(w in prompt for w in LCM_WORDS):
        return "story_lcm", ns
    if any(w in prompt for w in GCF_WORDS):
        return "story_gcf", ns
    raise AssertionError(f"unclassified prompt {prompt!r}")


def choice_value(kind, c):
    """The value a door stands for: g(x + y) -> g·(x + y); x + y -> x + y; '12 min' -> 12."""
    if kind == "full":
        g, x, y = map(int, re.fullmatch(r"(\d+)\((\d+) \+ (\d+)\)", c).groups())
        return g * (x + y)
    if kind == "inside":
        x, y = map(int, re.fullmatch(r"(\d+) \+ (\d+)", c).groups())
        return x + y
    m = re.fullmatch(r"(\d+)(?: (s|min|m))?", c)
    assert m, c
    return int(m[1])


def is_right(kind, args, c):
    """Does choice text c answer the prompt? Independent of the generator."""
    if kind == "factor":
        return args[0] % int(c) == 0
    if kind == "multiple":
        return int(c) % args[0] == 0
    if kind == "prime":
        return bf_prime(int(c))
    if kind == "count":
        return int(c) == len(divisors(args[0]))
    if kind in ("gcf", "story_gcf"):
        return choice_value(kind, c) == bf_gcf(*args)
    if kind in ("lcm", "story_lcm"):
        return choice_value(kind, c) == bf_lcm(*args)
    if kind == "full":
        a, b = args
        g, x, y = map(int, re.fullmatch(r"(\d+)\((\d+) \+ (\d+)\)", c).groups())
        return g == bf_gcf(a, b) and g * x == a and g * y == b
    if kind == "inside":
        a, b, g = args
        x, y = map(int, re.fullmatch(r"(\d+) \+ (\d+)", c).groups())
        return g * x == a and g * y == b
    raise AssertionError(kind)


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked prompts, each misconception's wrong value
# ---------------------------------------------------------------------------------------------
def test_golden_factor_and_multiple():
    r = G.factor_rules(36)  # Which is a factor of 36?
    assert r["MULTIPLE_FOR_FACTOR"] == [72]
    assert {8, 10} <= set(r["SHARES_FACTOR"]) and not {4, 5, 6, 7, 9} & set(r["SHARES_FACTOR"])
    r = G.multiple_rules(6, 42)  # Which is a multiple of 6?
    assert r["FACTOR_FOR_MULTIPLE"] == [2, 3]
    assert {16, 26, 46} <= set(r["SAME_LAST_DIGIT"]) and 36 not in r["SAME_LAST_DIGIT"]
    assert 40 in r["SHARES_FACTOR"] and not {35, 36, 42, 48} & set(r["SHARES_FACTOR"])
    assert G.multiple_rules(7, 42)["FACTOR_FOR_MULTIPLE"] == []  # prime: no factor door
    assert 17 in G.multiple_rules(7, 42)["SAME_LAST_DIGIT"]


def test_golden_primes_and_counts():
    r = G.prime_rules()
    assert r["ONE_IS_PRIME"] == [1] and {21, 27, 49} <= set(r["ODD_IS_PRIME"])
    assert not any(bf_prime(v) for v in r["ODD_IS_PRIME"])
    r = G.count_rules(12)  # 1, 2, 3, 4, 6, 12 -> 6
    assert r == {"FORGOT_ONE_AND_SELF": [4], "PAIRS_ONLY": [3], "SQUARE_TWICE": []}
    r = G.count_rules(36)  # 9 factors; 6 × 6 counted twice -> 10
    assert r == {"FORGOT_ONE_AND_SELF": [7], "PAIRS_ONLY": [5], "SQUARE_TWICE": [10]}


def test_golden_gcf():  # LIBRARY.md: GCF of 12 and 18 -> 6
    assert G.gcf_rules(12, 18) == {"LCM_FOR_GCF": [36], "NOT_GREATEST": [2, 3],
                                   "SMALLER_NUMBER": [12]}
    assert G.gcf_rules(6, 18)["SMALLER_NUMBER"] == []  # 6 IS the GCF: not a wrong door
    assert G.gcf_rules(14, 21)["NOT_GREATEST"] == []  # GCF 7 is prime


def test_golden_lcm():  # LIBRARY.md: LCM of 4 and 6 -> 12
    assert G.lcm_rules((4, 6)) == {"PRODUCT": [24], "GCF_FOR_LCM": [2], "LARGER_NUMBER": [6],
                                   "NOT_LEAST": [36]}  # 24 is taken by PRODUCT
    assert G.lcm_rules((3, 5)) == {"PRODUCT": [], "GCF_FOR_LCM": [], "LARGER_NUMBER": [5],
                                   "NOT_LEAST": [30]}
    assert G.lcm_rules((2, 3, 4))["PRODUCT"] == [24] and G.lcm_rules((2, 3, 4))["NOT_LEAST"] == [36]


def test_golden_factor_out():  # LIBRARY.md: 24 + 36 -> 12(2 + 3)
    r = G.factor_out_rules(24, 36)
    assert (4, 6) in r["NOT_GREATEST"]  # divided by 6: 6(4 + 6) is true but not the GCF
    assert r["SUBTRACTED_GCF"] == [(12, 24)]
    assert r["ONE_TERM"] == [(2, 36), (24, 3)]


def test_golden_stories():  # LIBRARY.md: buns 8s, dogs 6s -> 24; 18 red, 24 blue -> 6
    r = G.story_rules(8, 6, True)
    assert r["WRONG_TOOL"] == [2] and r["PRODUCT"] == [48]
    r = G.story_rules(18, 24, False)
    assert r["WRONG_TOOL"] == [72] and r["NOT_GREATEST"] == [2, 3] and r["SMALLER_NUMBER"] == [18]


def rules_for(kind, args, answer_text):
    if kind == "factor":
        return G.factor_rules(args[0])
    if kind == "multiple":
        return G.multiple_rules(args[0], int(answer_text))
    if kind == "prime":
        return G.prime_rules()
    if kind == "count":
        return G.count_rules(args[0])
    if kind == "gcf":
        return G.gcf_rules(*args)
    if kind == "lcm":
        return G.lcm_rules(args)
    if kind in ("full", "inside"):
        return G.factor_out_rules(args[0], args[1])
    return G.story_rules(args[0], args[1], kind == "story_lcm")


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    kind, args = kind_of(item["prompt"])
    rules = rules_for(kind, args, item["choices"][item["answer"]])
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one misconception door"
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        if kind == "full":
            g, x, y = map(int, re.fullmatch(r"(\d+)\((\d+) \+ (\d+)\)", c).groups())
            v = (x, y)
        elif kind == "inside":
            v = tuple(map(int, re.fullmatch(r"(\d+) \+ (\d+)", c).groups()))
        else:
            v = choice_value(kind, c)
        if m == "ARITH":
            assert all(v not in vals for vals in rules.values()), f"ARITH {c} is a rule value"
        else:
            assert v in rules[m], (m, c)


def test_arith_share():
    for t in range(1, 6):
        c = Counter(m for it in by_tier(t) for m in it["misconceptions"] if m)
        assert c["ARITH"] / sum(c.values()) <= 0.3, (t, c)


def test_tier_defining_misconceptions_present():
    t5 = by_tier(5)
    assert all("WRONG_TOOL" in it["misconceptions"] for it in t5)
    assert sum("NOT_GREATEST" in it["misconceptions"] for it in by_tier(4)) >= 8
    kinds = Counter(kind_of(it["prompt"])[0] for it in t5)
    assert kinds["story_lcm"] == 20 and kinds["story_gcf"] == 20


# ---------------------------------------------------------------------------------------------
# Independent answer check + one right door + value-distinct doors
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    kind, args = kind_of(item["prompt"])
    rights = [i for i, c in enumerate(item["choices"]) if is_right(kind, args, c)]
    assert rights == [item["answer"]], (item["prompt"], item["choices"])
    assert len(item["choices"]) == 4


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_doors_equal_in_value(item):
    kind, _ = kind_of(item["prompt"])
    vals = [choice_value(kind, c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), (item["prompt"], item["choices"])


def test_value_rule_would_catch_equal_forms():
    # 6(4 + 6) and 12(2 + 3) are both 60: the distinctness test must see them as equal.
    assert choice_value("full", "6(4 + 6)") == choice_value("full", "12(2 + 3)")


def test_units_are_consistent_within_an_item():
    for it in ITEMS:
        if it["tier"] == 4:
            continue
        units = {re.sub(r"^\d+ ?", "", c) for c in it["choices"]}
        assert len(units) == 1, it["choices"]


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds"): every correct step is a times-table fact, answers ≤ 100
# ---------------------------------------------------------------------------------------------
def in_table(n):
    """n = x × y with x, y in 2..10."""
    return any(n % x == 0 and 2 <= n // x <= 10 for x in range(2, 11))


def gcf_pair_ok(a, b, bad):
    g = bf_gcf(a, b)
    if not (2 <= g <= 10 and a // g <= 10 and b // g <= 10 and a <= 100 and b <= 100):
        bad.append(f"GCF pair {a}, {b} (GCF {g}) outside g, a/g, b/g ≤ 10")


def lcm_ok(nums, bad):
    if not all(2 <= x <= 10 for x in nums):
        bad.append(f"LCM operand outside 2..10: {nums}")
    L = bf_lcm(*nums)
    if L > 60:
        bad.append(f"LCM {L} over 60")
    if L // max(nums) > 10:
        bad.append(f"skip-count of {max(nums)} to {L} is past the times table")


def bounds_violations(tier, prompt, answer_text, choices):
    kind, args = kind_of(prompt)
    bad = []
    if kind == "factor":
        n, f = args[0], int(answer_text)
        if not (n <= 100 and 2 <= f <= 10 and 2 <= n // f <= 10):
            bad.append(f"factor {f} of {n} not a times-table fact")
    elif kind == "multiple":
        m, ans = args[0], int(answer_text)
        if not (2 <= m <= 10 and 2 <= ans // m <= 10 and ans <= 100):
            bad.append(f"multiple {ans} of {m} not a times-table fact")
    elif kind == "prime":
        if int(answer_text) > 47:
            bad.append("prime over 47")
    elif kind == "count":
        if not (args[0] <= 36 and in_table(args[0])):
            bad.append(f"factor count of {args[0]}: over 36 or not a times-table product")
    elif kind in ("gcf", "story_gcf", "full"):
        gcf_pair_ok(args[0], args[1], bad)
    elif kind == "inside":
        gcf_pair_ok(args[0], args[1], bad)
        if args[2] != bf_gcf(args[0], args[1]):
            bad.append("the factor shown is not the GCF")
    elif kind in ("lcm", "story_lcm"):
        lcm_ok(args, bad)
    if kind not in ("full", "inside") and choice_value(kind, answer_text) > 100:
        bad.append("answer over 100")
    for c in choices:
        if any(n > 999 for n in nums_in(c)):
            bad.append(f"choice {c} over 999")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    ans = item["choices"][item["answer"]]
    assert bounds_violations(item["tier"], item["prompt"], ans, item["choices"]) == []


@pytest.mark.parametrize("tier,prompt,answer,expect_bad", [
    (2, "GCF of 12 and 18?", "6", False),
    (2, "GCF of 24 and 36?", "12", True),   # GCF 12: 24 = 12 × 2 is past the tables
    (2, "GCF of 11 and 22?", "11", True),
    (3, "LCM of 4 and 6?", "12", False),
    (3, "LCM of 11 and 12?", "132", True),  # operands over 10, LCM over 60
    (3, "LCM of 9 and 10?", "90", True),    # LCM over 60
    (1, "Which is a factor of 26?", "2", True),  # 26 = 2 × 13
    (1, "How many factors does 48 have?", "10", True),
    (4, "Factor out the GCF: 24 + 36", "12(2 + 3)", True),
    (4, "18 + 24 = 3(? + ?)", "6 + 8", True),  # 3 is not the GCF
    (4, "18 + 24 = 6(? + ?)", "3 + 4", False),
])
def test_bounds_checker_catches(tier, prompt, answer, expect_bad):
    assert bool(bounds_violations(tier, prompt, answer, [answer])) == expect_bad


def test_manifest_states_bounds():
    assert "§4a" in BAKED["bounds"] and "60" in BAKED["bounds"]


def test_simplest_inside_after_factoring():
    for it in by_tier(4):
        c = it["choices"][it["answer"]]
        x, y = nums_in(c)[-2:]
        assert bf_gcf(x, y) == 1, c
