"""data-statistics cartridge: golden misconception cases, an independent re-check of every baked item
(prompt parsed here by regex, statistics computed here with ``fractions``/``statistics`` -- never the
generator's functions), the PROTOCOL §4b data bounds on baked.json, and a bounds-checker disproof.
"""
import json
import re
import statistics
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "data-statistics"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Independent prompt parser + solver
# ---------------------------------------------------------------------------------------------
NUMS = r"(\d+(?:, (?:\d+|\?))*|\?(?:, (?:\d+|\?))*)"
PATTERNS = [
    ("range", re.compile(r"^Find the range: ([\d, ]+)$")),
    ("mode", re.compile(r"^Find the mode: ([\d, ]+)$")),
    ("median", re.compile(r"^Find the median: ([\d, ]+)$")),
    ("mean", re.compile(r"^Find the mean: ([\d, ]+)$")),
    ("missing", re.compile(r"^The mean of ([\d, ?]+) is (\d+)\. What is \?$")),
    ("outlier", re.compile(r"^New value (\d+) joins ([\d, ]+)\. Which changes (more|less)\?$")),
    ("mad", re.compile(r"^Mean absolute deviation \(MAD\): ([\d, ]+)$")),
]
TIER_KINDS = {1: {"range", "mode"}, 2: {"median"}, 3: {"mean"}, 4: {"missing", "outlier"}, 5: {"mad"}}


def nums(s):
    return [int(x) for x in s.split(", ")]


def parse(prompt):
    for kind, pat in PATTERNS:
        m = pat.match(prompt)
        if m:
            return kind, m.groups()
    raise AssertionError(f"unrecognised prompt {prompt!r}")


def f_mean(xs):
    return Fraction(sum(xs), len(xs))


def f_median(xs):
    return Fraction(statistics.median(sorted(xs))).limit_denominator(2)


def solve(prompt):
    """(kind, correct answer as a string, data dict) computed independently."""
    kind, g = parse(prompt)
    if kind == "range":
        xs = nums(g[0])
        return kind, str(max(xs) - min(xs)), {"xs": xs}
    if kind == "mode":
        xs = nums(g[0])
        (v, c), (_, c2) = Counter(xs).most_common(2)
        assert c > c2, f"tied mode in {prompt}"
        return kind, str(v), {"xs": xs}
    if kind == "median":
        xs = nums(g[0])
        m = f_median(xs)
        assert m.denominator == 1
        return kind, str(m), {"xs": xs}
    if kind == "mean":
        xs = nums(g[0])
        m = f_mean(xs)
        assert m.denominator == 1
        return kind, str(m), {"xs": xs}
    if kind == "missing":
        parts = g[0].split(", ")
        assert parts.count("?") == 1
        known = [int(p) for p in parts if p != "?"]
        m = int(g[1])
        v = m * len(parts) - sum(known)
        assert 0 <= v <= 20
        assert f_mean(known + [v]) == m
        return kind, str(v), {"known": known, "n": len(parts), "m": m, "v": v}
    if kind == "outlier":
        new, xs, word = int(g[0]), nums(g[1]), g[2]
        full = xs + [new]
        dmean = abs(f_mean(full) - f_mean(xs))
        dmed = abs(f_median(full) - f_median(xs))
        assert dmean != dmed
        more = "Mean" if dmean > dmed else "Median"
        less = "Median" if more == "Mean" else "Mean"
        return kind, more if word == "more" else less, {"xs": xs, "new": new}
    xs = nums(g[0])  # mad
    m = f_mean(xs)
    d = Fraction(sum(abs(x - m) for x in xs), len(xs))
    assert d.denominator == 1
    return kind, str(d), {"xs": xs}


def wrong_values(kind, data):
    """{label: set of value strings that misconception produces}, computed here."""
    out = {}

    def put(lab, v):
        v = Fraction(v)
        if v.denominator == 1:
            out.setdefault(lab, set()).add(str(v))

    if kind in ("range", "mode", "median", "mean", "mad"):
        xs = data["xs"]
    if kind == "range":
        put("LARGEST", max(xs))
        put("FIRST_LAST", abs(xs[0] - xs[-1]))
    elif kind == "mode":
        c = Counter(xs).most_common()
        put("MOST_FOR_MODE", max(xs))
        put("COUNT_FOR_MODE", c[0][1])
        for v, k in c[1:]:
            if k > 1:
                put("MISCOUNT", v)
    elif kind == "median":
        s, n = sorted(xs), len(xs)
        k = n // 2
        put("MEAN_FOR_MEDIAN", f_mean(xs))
        if n % 2:
            put("UNSORTED", xs[k])
            put("NEXT_TO_MIDDLE", s[k - 1])
            put("NEXT_TO_MIDDLE", s[k + 1])
        else:
            put("UNSORTED", Fraction(xs[k - 1] + xs[k], 2))
            put("ONE_MIDDLE", s[k - 1])
            put("ONE_MIDDLE", s[k])
    elif kind == "mean":
        put("SUM_ONLY", sum(xs))
        put("MEDIAN_FOR_MEAN", f_median(xs))
        put("WRONG_COUNT", Fraction(sum(xs), len(xs) - 1))
        put("WRONG_COUNT", Fraction(sum(xs), len(xs) + 1))
    elif kind == "missing":
        put("MEAN_AS_MISSING", data["m"])
        put("TOTAL_ONLY", data["m"] * data["n"])
        put("MISSING_NOT_COUNTED", data["m"] * (data["n"] - 1) - sum(data["known"]))
    elif kind == "outlier":
        out["MEDIAN_MOVES"] = {"Mean", "Median"}  # the other word; checked != answer below
    else:
        m = f_mean(xs)
        put("RANGE_FOR_MAD", max(xs) - min(xs))
        put("MEAN_FOR_MAD", m)
        put("SUM_DEVIATIONS", sum(abs(x - m) for x in xs))
    return out


# ---------------------------------------------------------------------------------------------
# Golden cases (hand-worked)
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt, correct, {label: wrong value}
    ("Find the range: 4, 9, 2, 7, 5", "7", {"LARGEST": "9", "FIRST_LAST": "1"}),
    ("Find the mode: 6, 2, 6, 9, 2, 6, 4", "6",
     {"MOST_FOR_MODE": "9", "COUNT_FOR_MODE": "3", "MISCOUNT": "2"}),
    ("Find the median: 6, 2, 9, 4, 7", "6",
     {"UNSORTED": "9", "MEAN_FOR_MEDIAN": "28/5", "NEXT_TO_MIDDLE": "4"}),
    ("Find the median: 9, 2, 7, 3", "5", {"ONE_MIDDLE": "3", "UNSORTED": "9/2"}),
    ("Find the mean: 3, 5, 8, 4", "5",
     {"SUM_ONLY": "20", "MEDIAN_FOR_MEAN": "9/2", "WRONG_COUNT": "4"}),
    ("The mean of 5, 7, 4, ? is 6. What is ?", "8",
     {"MEAN_AS_MISSING": "6", "TOTAL_ONLY": "24", "MISSING_NOT_COUNTED": "2"}),
    ("Mean absolute deviation (MAD): 2, 4, 6, 8", "2",
     {"RANGE_FOR_MAD": "6", "MEAN_FOR_MAD": "5", "SUM_DEVIATIONS": "8"}),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_independent(prompt, correct, wrong):
    kind, ans, data = solve(prompt)
    assert ans == correct
    vals = wrong_values(kind, data)
    for lab, v in wrong.items():
        if "/" in v:  # a non-integer reading is never offered as a choice
            assert lab not in vals or v not in vals[lab]
        else:
            assert v in vals[lab], lab


def test_golden_generator_statistics():
    # The generator's own statistics agree on the hand-worked cases.
    assert G.mean([3, 5, 8, 4]) == 5 and G.median([6, 2, 9, 4, 7]) == 6
    assert G.median([9, 2, 7, 3]) == 5 and G.mad([2, 4, 6, 8]) == 2
    assert G.mean([3, 5, 8, 4]) * 4 == 20


def test_golden_outlier():
    kind, ans, _ = solve("New value 20 joins 2, 4, 6, 8. Which changes more?")
    assert (kind, ans) == ("outlier", "Mean")  # mean 5 -> 8, median 5 -> 6
    assert solve("New value 20 joins 2, 4, 6, 8. Which changes less?")[1] == "Median"


def test_golden_generator_items():
    """Generator item builders put the modelled values behind their labels."""
    import random
    rng = random.Random(1)
    item = G.make_item(5, "Mean absolute deviation (MAD): 2, 4, 6, 8", 2,
                       [("RANGE_FOR_MAD", 6), ("MEAN_FOR_MAD", 5), ("SUM_DEVIATIONS", 8)],
                       0, "x", rng)
    got = dict(zip(item["misconceptions"], item["choices"]))
    assert got == {None: "2", "RANGE_FOR_MAD": "6", "MEAN_FOR_MAD": "5", "SUM_DEVIATIONS": "8"}
    assert item["answer"] == 0


# ---------------------------------------------------------------------------------------------
# Every baked item, re-checked independently
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    kind, ans, _ = solve(item["prompt"])
    assert kind in TIER_KINDS[item["tier"]]
    assert item["choices"][item["answer"]] == ans


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_explanation_ends_with_answer(item):
    kind, ans, _ = solve(item["prompt"])
    if kind == "outlier":
        assert "mean a lot" in item["explanation"]
    else:
        assert re.search(rf"\b{ans}\.$", item["explanation"]), item["explanation"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_honest(item):
    kind, ans, data = solve(item["prompt"])
    vals = wrong_values(kind, data)
    produced = set().union(*vals.values()) if vals else set()
    for c, lab in zip(item["choices"], item["misconceptions"]):
        if lab is None:
            continue
        assert c != ans
        if lab == "ARITH":
            assert c not in produced, f"ARITH {c} is really a misconception value"
            assert 0 <= int(c) <= 999
        else:
            assert c in vals[lab], (lab, c, item["prompt"])


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(item):
    def value(c):
        return c if c in ("Mean", "Median") else Fraction(c)
    vs = [value(c) for c in item["choices"]]
    assert len(set(vs)) == len(vs), item["choices"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_misconception_reading_is_accidentally_right(item):
    """A student holding a modelled misconception must not land on the right door by luck."""
    kind, ans, data = solve(item["prompt"])
    if kind == "outlier":
        return
    for lab, vs in wrong_values(kind, data).items():
        if lab in ("NEXT_TO_MIDDLE", "ONE_MIDDLE", "WRONG_COUNT", "MISCOUNT"):
            continue  # these have several readings; one of them may equal nothing in particular
        assert ans not in vs, (lab, item["prompt"])


def test_shapes_and_counts():
    for t in range(1, 6):
        its = by_tier(t)
        assert len(its) == 40
        kinds = Counter(parse(it["prompt"])[0] for it in its)
        assert set(kinds) == TIER_KINDS[t], kinds
    assert all(len(it["choices"]) == 4 for it in ITEMS
               if parse(it["prompt"])[0] != "outlier")
    outl = [it for it in by_tier(4) if parse(it["prompt"])[0] == "outlier"]
    assert all(it["choices"] in (["Mean", "Median"], ["Median", "Mean"]) for it in outl)
    assert {it["choices"][it["answer"]] for it in outl} == {"Mean", "Median"}
    medians = [it for it in by_tier(2)]
    assert any(len(nums(parse(it["prompt"])[1][0])) % 2 == 0 for it in medians)
    assert any(len(nums(parse(it["prompt"])[1][0])) % 2 == 1 for it in medians)


def test_arith_share():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.3
    for t in range(1, 6):
        for it in by_tier(t):
            assert any(m not in (None, "ARITH") for m in it["misconceptions"])


def test_odd_median_lists_are_not_presorted_at_the_middle():
    for it in by_tier(2):
        xs = nums(parse(it["prompt"])[1][0])
        if len(xs) % 2:
            assert xs[len(xs) // 2] != f_median(xs), it["prompt"]


# ---------------------------------------------------------------------------------------------
# PROTOCOL §4b data bounds, walked independently on baked.json
# ---------------------------------------------------------------------------------------------
def q_ok(v):
    v = Fraction(v)
    return v.denominator == 1 and 2 <= v <= 10


def bounds_violations(prompt):
    """Walk the correct working of one prompt and list every §4b / §4a breach."""
    kind, g = parse(prompt)
    bad = []
    if kind == "missing":
        parts = g[0].split(", ")
        m, n = int(g[1]), len(parts)
        known = [int(p) for p in parts if p != "?"]
        if not (2 <= m <= 10 and 2 <= n <= 10):
            bad.append(f"total {m} × {n} not a times-table fact")
        data = known + [m * n - sum(known)]
    elif kind == "outlier":
        base = nums(g[1])
        data = base + [int(g[0])]
    else:
        data = nums(g[0])
    if not 3 <= len(data) <= 7:
        bad.append(f"{len(data)} values")
    if any(not 0 <= x <= 20 for x in data):
        bad.append(f"value outside 0-20: {data}")
    if sum(data) > 100:
        bad.append(f"sum {sum(data)} > 100")
    # every running sum <= 100 (follows from the line above; kept explicit)
    run = 0
    for x in data:
        run += x
        if run > 100:
            bad.append("running sum > 100")
    if kind == "median" and len(data) % 2 == 0 and not q_ok(f_median(data)):
        bad.append(f"halved median {f_median(data)} not an integer 2-10")
    if kind in ("mean", "missing", "mad") and not q_ok(f_mean(data)):
        bad.append(f"mean {f_mean(data)} not an integer 2-10")
    if kind == "mad":
        m = f_mean(data)
        devs = [abs(x - m) for x in data]
        if any(d > 20 for d in devs):
            bad.append("deviation > 20")
        if not q_ok(Fraction(sum(devs), len(data))):
            bad.append(f"MAD {Fraction(sum(devs), len(data))} not an integer 2-10")
    if kind == "outlier":
        for d in (base, data):
            if not q_ok(f_mean(d)):
                bad.append(f"mean {f_mean(d)} not an integer 2-10")
            med = f_median(d)
            if med.denominator != 1 or (len(d) % 2 == 0 and not q_ok(med)):
                bad.append(f"median {med} not allowed")
        new = int(g[0])
        if any(abs(new - x) < 10 for x in base):
            bad.append("new value within 10 of the data")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(item["prompt"]) == [], item["prompt"]
    for c in item["choices"]:
        if c not in ("Mean", "Median"):
            assert re.fullmatch(r"\d+", c) and int(c) <= 999, c


@pytest.mark.parametrize("prompt,expect_bad", [
    ("Find the mean: 3, 5, 8, 4", False),
    ("Find the mean: 25, 3, 2", True),            # value over 20
    ("Find the mean: 1, 2, 4", True),             # mean 7/3, not an integer
    ("Find the mean: 0, 1, 2", True),             # mean 1: quotient below 2
    ("Find the mean: 20, 20, 20", True),          # mean 20: quotient over 10
    ("Find the median: 9, 2, 7, 3", False),
    ("Find the median: 18, 12, 14, 20", True),    # (14 + 18) ÷ 2 = 16: quotient over 10
    ("Find the median: 9, 2, 8, 3", True),        # 11/2
    ("Find the range: 4, 9", True),               # 2 values
    ("Find the range: 1, 2, 3, 4, 5, 6, 7, 8", True),  # 8 values
    ("Mean absolute deviation (MAD): 2, 4, 6, 8", False),
    ("Mean absolute deviation (MAD): 1, 3, 5", True),  # MAD 4/3
    ("The mean of 5, 7, 4, ? is 6. What is ?", False),
    ("The mean of 1, 2, ? is 10. What is ?", True),    # missing value 27
    ("New value 20 joins 2, 4, 6, 8. Which changes more?", False),
    ("New value 12 joins 2, 4, 6, 8. Which changes more?", True),  # not 10 from 8
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(bounds_violations(prompt)) == expect_bad, prompt


def test_generator_bounds_gate_agrees_on_disproofs():
    assert G.check_bounds("mean", [25, 3, 2])
    assert G.check_bounds("mad", [1, 3, 5])
    assert G.check_bounds("outlier", [2, 4, 6, 8], 12)
    assert not G.check_bounds("outlier", [2, 4, 6, 8], 20)
    assert not G.check_bounds("mad", [2, 4, 6, 8])


def test_manifest_declares_bounds_and_keys():
    assert "bounds" in BAKED and "0-20" in BAKED["bounds"]
    used = {m for it in ITEMS for m in it["misconceptions"] if m and m != "ARITH"}
    assert used <= set(BAKED["misconceptions"])
    assert set(BAKED["misconceptions"]) == used, set(BAKED["misconceptions"]) - used
