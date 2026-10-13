"""probability cartridge: golden misconception rules, an independent re-check of every baked item, and the
manifest's ``bounds`` walked over every baked item.

The independent solver below reads each prompt with this file's own regexes, builds each event from
scratch (sets of faces, ``itertools.product`` over coins and marbles) and computes with
``fractions.Fraction``. It never calls the generator's ``members`` / ``uniform_wrongs`` / ``pick``. It also
re-derives, per item family, the ordered list of wrong values each misconception produces, so a label on a
baked choice is checked against the rule it names (and against the rules that outrank it).
"""
import itertools
import json
import re
from collections import Counter
from fractions import Fraction as Fr
from math import gcd

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "probability"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M = "−"  # U+2212


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def lt1(v):
    return v if v is not None and 0 < v < 1 else None


def read_value(text):
    """A choice's value: Fraction for a number (fraction, decimal, percent, count), else the text."""
    t = text.replace(M, "-")
    if re.fullmatch(r"-?\d+(?:\.\d+)?%", t):
        return Fr(t[:-1]) / 100
    if re.fullmatch(r"-?\d+/\d+", t) or re.fullmatch(r"-?\d+(?:\.\d+)?", t):
        return Fr(t)
    return text


def form_of(text):
    if text.endswith("%"):
        return "pct"
    if "/" in text:
        return "frac"
    if "." in text:
        return "dec"
    return "int"


# ---------------------------------------------------------------------------------------------
# Golden cases: every rule function, on hand-worked numbers
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # P(red) with 3 red, 5 blue: part-to-part 3/5, the other color 5/8, "50-50", one outcome 1/8
    ("bag 3 red 5 blue", lambda: G.uniform_wrongs(3, 8),
     [("PART_TO_PART", Fr(3, 5)), ("OTHER_EVENT", Fr(5, 8)), ("EQUAL_CHANCE", Fr(1, 2)),
      ("ONE_OVER_TOTAL", Fr(1, 8))]),
    # die, more than 4: {5, 6}; counting the 4 too gives 3/6
    ("die more than 4", lambda: G.uniform_wrongs(2, 6, boundary=3),
     [("BOUNDARY", Fr(1, 2)), ("PART_TO_PART", Fr(1, 2)), ("OTHER_EVENT", Fr(2, 3)),
      ("EQUAL_CHANCE", Fr(1, 2)), ("ONE_OVER_TOTAL", Fr(1, 6))]),
    # die, prime {2, 3, 5}: counting 1 gives 4/6; part-to-part 3/3 = 1 is not a probability
    ("die prime", lambda: G.uniform_wrongs(3, 6, prime_one=4),
     [("PRIME_ONE", Fr(2, 3)), ("PART_TO_PART", None), ("OTHER_EVENT", Fr(1, 2)),
      ("EQUAL_CHANCE", Fr(1, 2)), ("ONE_OVER_TOTAL", Fr(1, 6))]),
    # BANANA, P(A): 3 of 6; 1 distinct A out of 3 distinct letters is 1/3
    ("BANANA P(A)", lambda: G.uniform_wrongs(3, 6, distinct=(1, 3)),
     [("DISTINCT_OUTCOMES", Fr(1, 3)), ("PART_TO_PART", None), ("OTHER_EVENT", Fr(1, 2)),
      ("EQUAL_CHANCE", Fr(1, 2)), ("ONE_OVER_TOTAL", Fr(1, 6))]),
    # P(not red), 6 red and 2 yellow: P(red) = 3/4; yellow : red = 2/6
    ("not red 6 2", lambda: G.comp_bag_wrongs(6, [2]),
     [("SAME_AS_EVENT", Fr(3, 4)), ("PART_TO_PART", Fr(1, 3))]),
    # three colors, 2 red 5 blue 4 green: only blue is 5/11; 9 : 2 is over 1
    ("not red 2 5 4", lambda: G.comp_bag_wrongs(2, [5, 4]),
     [("SAME_AS_EVENT", Fr(2, 11)), ("ONE_OTHER", Fr(5, 11)), ("PART_TO_PART", None)]),
    # P(hit) = 3/10: same 3/10, part-to-part 3/7, 1 + 3/10 = 13/10
    ("P(hit) 3/10", lambda: G.comp_given_wrongs(Fr(3, 10), True),
     [("SAME_AS_EVENT", Fr(3, 10)), ("PART_TO_PART", Fr(3, 7)), ("ADD_TO_ONE", Fr(13, 10))]),
    ("P(win) 0.6", lambda: G.comp_given_wrongs(Fr(3, 5), False),
     [("SAME_AS_EVENT", Fr(3, 5)), ("ADD_TO_ONE", Fr(8, 5))]),
    # 1/4 of 40 is 10; dividing by 1/4 gives 160; the losses are 30
    ("1/4 of 40", lambda: G.expect_wrongs(1, 4, 40),
     [("IGNORED_NUMERATOR", None), ("INVERTED_P", 160), ("OTHER_EVENT", 30)]),
    # 3/10 of 20 is 6; the 20 ÷ 10 = 2 stops early; 200/3 is not whole; the other 14
    ("3/10 of 20", lambda: G.expect_wrongs(3, 10, 20),
     [("IGNORED_NUMERATOR", 2), ("INVERTED_P", None), ("OTHER_EVENT", 14)]),
    # 6 of 20 sampled, of 100: 30; the sample 6; adding 80 gives 86; the scale 5; the other 70
    ("6 of 20 to 100", lambda: G.sample_wrongs(6, 20, 100),
     [("SAMPLE_COUNT", 6), ("ADDITIVE", 86), ("SCALE_ONLY", 5), ("OTHER_EVENT", 70)]),
    # 6 of 20: 3/10; part-to-part 6/14; the other 14/20; flipped 20/6
    ("6 of 20 estimate", lambda: G.estimate_wrongs(6, 20),
     [("PART_TO_PART", Fr(3, 7)), ("OTHER_EVENT", Fr(7, 10)), ("FLIPPED", Fr(10, 3))]),
    ("3 shirts 4 pants", lambda: G.prod2_wrongs(3, 4), [("ADDED_COUNTS", 7), ("ONE_STAGE", 4)]),
    ("3 4 2", lambda: G.prod3_wrongs(3, 4, 2), [("ADDED_COUNTS", 9), ("FORGOT_ONE", 12), ("MIXED_OPS", 14)]),
    ("3 flips", lambda: G.flip_wrongs(3),
     [("ORDER_BLIND", 4), ("POWER_FLIP", 9), ("MULT_BY_COUNT", 6), ("ONE_STAGE", 2)]),
    ("3-part spinner twice", lambda: G.twice_wrongs(3),
     [("ORDER_BLIND", 6), ("ADDED_COUNTS", 6), ("ONE_STAGE", 3)]),
    # two coins, at least one head: HH HT TH is 3 outcomes; the head totals 2 and 1 are 2 groups
    ("two coins, a head", lambda: G.coin_count_wrongs(2, 3, 2),
     [("ORDER_BLIND", 2), ("COUNTED_ALL", 4), ("ONE_OUTCOME", 1)]),
    ("heads and a number over 3 is 3", lambda: G.coin_die_count_wrongs(3),
     [("ADDED_COUNTS", 4), ("IGNORED_PART", 6), ("IGNORED_PART", 6), ("TOTAL_NOT_EVENT", 12)]),
    # coin and die, heads and a 6: 1/12; 1/2 + 1/6; 1/(2 + 6); the die alone; the coin alone
    ("heads and a 6", lambda: G.coin_die_prob_wrongs(1),
     [("ADDED_PROBS", Fr(2, 3)), ("ADD_DENOMS", Fr(1, 8)), ("FORGOT_STAGE", Fr(1, 6)),
      ("FORGOT_STAGE", Fr(1, 2))]),
    ("heads and an odd number", lambda: G.coin_die_prob_wrongs(3),
     [("ADDED_PROBS", None), ("ADD_DENOMS", Fr(3, 8)), ("FORGOT_STAGE", Fr(1, 2)),
      ("FORGOT_STAGE", Fr(1, 2))]),
    # two coins, one head one tail: HT and TH merged leave 1 of 3 groups
    ("two coins one each", lambda: G.coins_prob_wrongs(2, ["HT", "TH"]),
     [("ORDER_BLIND", Fr(1, 3)), ("OTHER_EVENT", Fr(1, 2)), ("FORGOT_STAGE", Fr(1, 2)),
      ("ONE_OUTCOME", Fr(1, 4))]),
    ("three coins all heads", lambda: G.coins_prob_wrongs(3, ["HHH"]),
     [("ORDER_BLIND", Fr(1, 4)), ("ADD_DENOMS", Fr(1, 6)), ("OTHER_EVENT", Fr(7, 8)),
      ("FORGOT_STAGE", Fr(1, 2)), ("ONE_OUTCOME", Fr(1, 8))]),
    ("red and heads", lambda: G.spin_coin_wrongs(3, 1),
     [("ADDED_PROBS", Fr(5, 6)), ("ADD_DENOMS", Fr(1, 5)), ("FORGOT_STAGE", Fr(1, 3)),
      ("FORGOT_STAGE", Fr(1, 2))]),
    # 1 red 2 blue, replace: red then blue is 1/3 × 2/3 = 2/9; either order would be 4/9
    ("red then blue", lambda: G.bag_draw_wrongs(1, 2, 3, True),
     [("ORDER_OVER", Fr(4, 9)), ("ADDED_PROBS", None), ("ADD_DENOMS", Fr(1, 3)), ("FORGOT_STAGE", Fr(1, 3))]),
    ("one red one blue", lambda: G.bag_draw_wrongs(1, 2, 3, False),
     [("ONE_ORDER", Fr(2, 9)), ("ADDED_PROBS", None), ("ADD_DENOMS", Fr(1, 3)), ("FORGOT_STAGE", Fr(1, 3))]),
]


@pytest.mark.parametrize("name,call,expect", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_rule_values(name, call, expect):
    got = call()
    assert [(lab, None if v is None else Fr(v)) for lab, v in got] == \
           [(lab, None if v is None else Fr(v)) for lab, v in expect]


def test_golden_words():
    assert G.WORD_WRONGS["Likely"] == [("SCALE_FLIP", "Unlikely"), ("HALF_WORD", "Equally likely"),
                                       ("ROUNDED", "Certain")]
    assert G.WORD_WRONGS["Unlikely"] == [("SCALE_FLIP", "Likely"), ("HALF_WORD", "Equally likely"),
                                         ("ROUNDED", "Impossible")]
    assert G.WORD_WRONGS["Equally likely"] == [("HALF_LEANS", "Likely"), ("HALF_LEANS", "Unlikely"),
                                               ("WORD_MIXUP", "Impossible")]
    assert G.WORD_WRONGS["Impossible"][0] == ("SCALE_FLIP", "Certain")
    assert G.WORD_WRONGS["Certain"][0] == ("SCALE_FLIP", "Impossible")
    # no wrong word overlaps the right one: never "Unlikely" beside "Impossible" or "Likely" beside "Certain"
    for right, wrongs in G.WORD_WRONGS.items():
        ws = [w for _, w in wrongs]
        if right == "Impossible":
            assert "Unlikely" not in ws
        if right == "Certain":
            assert "Likely" not in ws
        assert right not in ws and len(set(ws)) == len(ws)
    for x, w in (("0", "Impossible"), ("1", "Certain"), ("1/2", "Equally likely"), ("0.9", "Likely"),
                 ("1/10", "Unlikely"), ("3/4", "Likely"), ("1/4", "Unlikely")):
        assert G.word_for(Fr(x)) == w


def baked_item(prompt):
    hits = [it for it in ITEMS if it["prompt"] == prompt]
    assert len(hits) == 1, prompt
    return hits[0]


EXTREMES = {
    "As a decimal, the greatest a probability can be?": ("1", {"100": "PERCENT_MIX", "No limit": "OVER_ONE",
                                                              "10": "ARITH"}),
    "As a decimal, the least a probability can be?": ("0", {"1": "SCALE_FLIP", M + "1": "NEGATIVE",
                                                           "No limit": "NEGATIVE"}),
    "As a decimal, a probability is between which numbers?": ("0 and 1", {
        "0 and 100": "PERCENT_MIX", M + "1 and 1": "NEGATIVE", "0 and 10": "ARITH"}),
}


@pytest.mark.parametrize("prompt", list(EXTREMES))
def test_golden_extremes(prompt):
    it = baked_item(prompt)
    right, labels = EXTREMES[prompt]
    assert it["choices"][it["answer"]] == right
    got = {c: m for c, m in zip(it["choices"], it["misconceptions"]) if m}
    assert got == labels


LISTS = {
    "Flip two coins. Which lists every outcome?": ("HH, HT, TH, TT", {
        "HH, HT, TT": "ORDER_BLIND", "HH, TT": "MATCHING_ONLY", "H, T": "ONE_STAGE"}),
    "Flip a coin and spin 1 or 2. Which lists every outcome?": ("H1, H2, T1, T2", {
        "H, T, 1, 2": "NOT_PAIRED", "H1, H2, T1": "MISSED_ONE", "H1, T2": "MISSED_ONE"}),
}


@pytest.mark.parametrize("prompt", list(LISTS))
def test_golden_lists(prompt):
    it = baked_item(prompt)
    right, labels = LISTS[prompt]
    assert it["choices"][it["answer"]] == right
    assert {c: m for c, m in zip(it["choices"], it["misconceptions"]) if m} == labels
    # the right list really is all 4 pairings, each wrong list really is missing or reshaping something
    pairs = set(itertools.product("HT", "HT" if "two coins" in prompt else "12"))
    names = {a + b for a, b in pairs}
    assert set(right.split(", ")) == names
    for c in labels:
        assert set(c.split(", ")) != names


# ---------------------------------------------------------------------------------------------
# The independent solver
# ---------------------------------------------------------------------------------------------
PRIMES = {2, 3, 5, 7, 11}
TEST_WORD_WRONGS = {  # the labels and words a student holding each slip would pick (own copy)
    "Impossible": [("SCALE_FLIP", "Certain"), ("HALF_WORD", "Equally likely"), ("WORD_MIXUP", "Likely")],
    "Certain": [("SCALE_FLIP", "Impossible"), ("HALF_WORD", "Equally likely"), ("WORD_MIXUP", "Unlikely")],
    "Unlikely": [("SCALE_FLIP", "Likely"), ("HALF_WORD", "Equally likely"), ("ROUNDED", "Impossible")],
    "Likely": [("SCALE_FLIP", "Unlikely"), ("HALF_WORD", "Equally likely"), ("ROUNDED", "Certain")],
    "Equally likely": [("HALF_LEANS", "Likely"), ("HALF_LEANS", "Unlikely"), ("WORD_MIXUP", "Impossible")],
}


def word_of(v):
    if v == 0:
        return "Impossible"
    if v == 1:
        return "Certain"
    if v == Fr(1, 2):
        return "Equally likely"
    return "Unlikely" if v < Fr(1, 2) else "Likely"


class S:
    """What the independent solver says about one item."""

    def __init__(self, answer, wrongs=(), bad=(), label_fn=None):
        self.answer = answer  # value in read_value's domain
        self.wrongs = list(wrongs)  # [(label, value|None)] in priority order
        self.bad = list(bad)  # bound violations
        self.label_fn = label_fn  # (text, value) -> label, for items whose wrongs follow from the choices
        self.prio = {}
        for lab, v in self.wrongs:
            if v is not None and v != answer and v not in self.prio:
                self.prio[v] = lab


def chance_text_bad(text, over=False):
    """PROTOCOL §4b for a probability written in a prompt: fractions with denominators 2-12 in simplest
    form; decimals with at most 2 places and 2 non-zero digits; percents 10, 20, 25, 50, 75 or tens."""
    t = text.replace(M, "-")
    out = []
    if t.endswith("%"):
        a = abs(int(t[:-1]))
        if not (a in (0, 25, 75, 100) or (a % 10 == 0 and a <= (300 if over else 100))):
            out.append(f"percent {text}")
    elif "/" in t:
        a, b = (int(x) for x in t.split("/"))
        if gcd(abs(a), b) != 1 or not 2 <= b <= 12 or abs(a) > 12:
            out.append(f"fraction {text}")
    elif "." in t:
        whole, dec = t.lstrip("-").split(".")
        if len(dec) > 2 or sum(ch in "123456789" for ch in whole + dec) > 2:
            out.append(f"decimal {text}")
    return out


# --- events on faces / cards -----------------------------------------------------------------
def faces_of(phrase, N=6):
    """Outcomes 1..N matching an event phrase from any T1/T4/T5 template."""
    nums = list(range(1, N + 1))
    m = re.fullmatch(r"an? (even|odd) number|(even|odd)", phrase)
    if m:
        want = m[1] or m[2]
        return [x for x in nums if x % 2 == (0 if want == "even" else 1)]
    if re.fullmatch(r"a prime( number)?|prime", phrase):
        return [x for x in nums if x in PRIMES]
    m = re.fullmatch(r"a multiple of (\d+)", phrase)
    if m:
        return [x for x in nums if x % int(m[1]) == 0]
    m = re.fullmatch(r"a factor of (\d+)", phrase)
    if m:
        return [x for x in nums if int(m[1]) % x == 0]
    if phrase == "a square number":
        return [x for x in nums if x in (1, 4, 9)]
    m = re.fullmatch(r"a number (over|under) (\d+)", phrase)
    if m:
        t = int(m[2])
        return [x for x in nums if (x > t if m[1] == "over" else x < t)]
    if re.fullmatch(r"a number from 1 to 6", phrase):
        return [x for x in nums if 1 <= x <= 6]
    m = re.fullmatch(r"a (\d+)", phrase)
    if m:
        return [x for x in nums if x == int(m[1])]
    raise AssertionError(f"unreadable event {phrase!r}")


def set_event(phrase, N):
    """(members, kind): kind gt/lt/ge/le (threshold), prime, other."""
    nums = list(range(1, N + 1))
    m = re.fullmatch(r"(more than|less than|at least|at most) (\d+)", phrase)
    if m:
        t = int(m[2])
        tests = {"more than": (lambda x: x > t, "gt"), "less than": (lambda x: x < t, "lt"),
                 "at least": (lambda x: x >= t, "ge"), "at most": (lambda x: x <= t, "le")}
        f, kind = tests[m[1]]
        return [x for x in nums if f(x)], kind
    if phrase == "prime":
        return [x for x in nums if x in PRIMES], "prime"
    if phrase in ("even", "odd"):
        return [x for x in nums if x % 2 == (0 if phrase == "even" else 1)], "other"
    return faces_of(phrase, N), "other"


def uniform_oracle(k, n, kind="other", distinct=None, equal=Fr(1, 2)):
    out = []
    b = {"gt": k + 1, "lt": k + 1, "ge": k - 1, "le": k - 1}.get(kind)
    if b is not None and b >= 1:
        out.append(("BOUNDARY", lt1(Fr(b, n))))
    if kind == "prime":
        out.append(("PRIME_ONE", lt1(Fr(k + 1, n))))
    if distinct:
        out.append(("DISTINCT_OUTCOMES", lt1(Fr(distinct[0], distinct[1]))))
    out.append(("PART_TO_PART", lt1(Fr(k, n - k))))
    out.append(("OTHER_EVENT", lt1(Fr(n - k, n))))
    out.append(("EQUAL_CHANCE", equal))
    out.append(("ONE_OVER_TOTAL", lt1(Fr(1, n))))
    return out


# --- coins -------------------------------------------------------------------------------------
def coin_pred(desc):
    num = {"one": 1, "two": 2, "three": 3}
    m = re.fullmatch(r"exactly (one|two) (head|heads|tail|tails)", desc)
    if m:
        ch = "H" if m[2].startswith("head") else "T"
        return lambda s: s.count(ch) == num[m[1]]
    m = re.fullmatch(r"at least (one|two) (head|heads|tail|tails)", desc)
    if m:
        ch = "H" if m[2].startswith("head") else "T"
        return lambda s: s.count(ch) >= num[m[1]]
    m = re.fullmatch(r"at most (one|two) (head|heads|tail|tails)", desc)
    if m:
        ch = "H" if m[2].startswith("head") else "T"
        return lambda s: s.count(ch) <= num[m[1]]
    m = re.fullmatch(r"two or more (heads|tails)", desc)
    if m:
        ch = "H" if m[1] == "heads" else "T"
        return lambda s: s.count(ch) >= 2
    fixed = {
        "the same side up": lambda s: len(set(s)) == 1, "the coins match": lambda s: len(set(s)) == 1,
        "all three match": lambda s: len(set(s)) == 1, "different sides up": lambda s: len(set(s)) == 2,
        "different sides": lambda s: len(set(s)) == 2, "two heads": lambda s: s == "HH",
        "two tails": lambda s: s == "TT", "one head, one tail": lambda s: sorted(s) == ["H", "T"],
        "no heads": lambda s: "H" not in s, "all heads": lambda s: s == "HHH",
        "heads on the first flip": lambda s: s[0] == "H", "not all heads": lambda s: s != "HHH",
        "H, H, T in that order": lambda s: s == "HHT",
    }
    if desc in fixed:
        return fixed[desc]
    raise AssertionError(f"unreadable coin event {desc!r}")


def coin_outs(n, desc):
    pred = coin_pred(desc)
    return ["".join(t) for t in itertools.product("HT", repeat=n) if pred("".join(t))]


# --- tier 1 ------------------------------------------------------------------------------------
def solve_t1(item):
    p = item["prompt"]
    for rx in (r"A probability of (\S+) means the event is\?", r"A (\S+) chance means the event is\?",
               r"P\(event\) = (\S+)\. How likely is the event\?"):
        m = re.fullmatch(rx, p)
        if m:
            w = word_of(read_value(m[1]))
            return S(w, TEST_WORD_WRONGS[w], chance_text_bad(m[1]))
    m = re.fullmatch(r"(.*) How likely\?", p)
    if m:
        text = m[1]
        bad = []
        if (mm := re.fullmatch(r"Roll a die\. Get (.+)\.", text)):
            prob = Fr(len(faces_of(mm[1], 6)), 6)
        elif text == "Flip a fair coin. Get heads.":
            prob = Fr(1, 2)
        elif (mm := re.fullmatch(r"Bag: (\d+) red, (\d+) blue\. Pick red\.", text)):
            prob = Fr(int(mm[1]), int(mm[1]) + int(mm[2]))
            if int(mm[1]) + int(mm[2]) > 12:
                bad.append("bag over 12")
        elif (mm := re.fullmatch(r"Bag has only (red|blue) marbles\. Pick red\.", text)):
            prob = Fr(1 if mm[1] == "red" else 0)
        elif (mm := re.fullmatch(r"Cards 1 to (\d+)\. Pick (.+)\.", text)):
            prob = Fr(len(faces_of(mm[2], int(mm[1]))), int(mm[1]))
        elif (mm := re.fullmatch(r"Spinner is (half|3/4|1/4) red\. Land on red\.", text)):
            prob = Fr(1, 2) if mm[1] == "half" else Fr(mm[1])
        else:
            raise AssertionError(f"unreadable event {text!r}")
        if not (prob in (0, 1, Fr(1, 2)) or prob <= Fr(1, 4) or prob >= Fr(3, 4)):
            bad.append(f"{prob} sits in the gap between unlikely and likely")
        if prob.denominator > 12:
            bad.append("denominator over 12")
        w = word_of(prob)
        return S(w, TEST_WORD_WRONGS[w], bad)
    m = re.fullmatch(r"Which (could|can't) be (.+)\?", p)
    if m:
        vals = [read_value(c) for c in item["choices"]]
        bad = [b for c in item["choices"] for b in chance_text_bad(c, over=True)]
        valid = [i for i, v in enumerate(vals) if 0 <= v <= 1]
        if m[1] == "could":
            assert len(valid) == 1, item["choices"]
            right = vals[valid[0]]

            def label(text, v):
                return "OVER_ONE" if v > 1 else "NEGATIVE"
        else:
            assert len(valid) == 3, item["choices"]
            right = [v for v in vals if not 0 <= v <= 1][0]

            def label(text, v):
                return "EDGE_EXCLUDED" if v in (0, 1) else "RANGE_CHECK"
        return S(right, [], bad, label)
    if p in EXTREMES:
        right, labels = EXTREMES[p]

        def label(text, v):
            return labels[text]

        return S(read_value(right), [], [], label)
    raise AssertionError(f"unreadable T1 prompt {p!r}")


# --- tier 2 ------------------------------------------------------------------------------------
def solve_t2(item):
    p = item["prompt"]
    bad = []
    if (m := re.fullmatch(r"Bag: (\d+) (\w+), (\d+) (\w+)\. P\((\w+)\)\?", p)):
        counts, colors, ask = (int(m[1]), int(m[3])), (m[2], m[4]), m[5]
        n, k = sum(counts), counts[colors.index(ask)]
        if n > 12 or min(counts) < 1:
            bad.append(f"bag of {n}")
        return S(Fr(k, n), uniform_oracle(k, n), bad)
    if (m := re.fullmatch(r"Bag: (\d+) (\w+), (\d+) (\w+), (\d+) (\w+)\. P\((\w+)\)\?", p)):
        counts, colors, ask = (int(m[1]), int(m[3]), int(m[5])), (m[2], m[4], m[6]), m[7]
        n, k = sum(counts), counts[colors.index(ask)]
        if n > 12 or min(counts) < 1:
            bad.append(f"bag of {n}")
        return S(Fr(k, n), uniform_oracle(k, n, equal=Fr(1, 3)), bad)
    if (m := re.fullmatch(r"Spinner: (\d+) equal parts, (\d+) (\w+)\. P\((\w+)\)\?", p)):
        n, k = int(m[1]), int(m[2])
        assert m[3] == m[4]
        if not 2 <= n <= 12 or not 1 <= k < n:
            bad.append(f"spinner {k}/{n}")
        return S(Fr(k, n), uniform_oracle(k, n), bad)
    if (m := re.fullmatch(r"Roll a die\. P\((.+)\)\?", p)):
        mem, kind = set_event(m[1], 6)
        return S(Fr(len(mem), 6), uniform_oracle(len(mem), 6, kind), bad)
    if (m := re.fullmatch(r"Cards 1 to (\d+), pick one\. P\((.+)\)\?", p)):
        N = int(m[1])
        if N not in (8, 10, 12):
            bad.append(f"cards 1 to {N}")
        mem, kind = set_event(m[2], N)
        return S(Fr(len(mem), N), uniform_oracle(len(mem), N, kind), bad)
    if (m := re.fullmatch(r"A letter is picked from ([A-Z]+)\. P\((.+)\)\?", p)):
        word, ev = m[1], m[2]
        if ev == "a vowel":
            test = lambda ch: ch in "AEIOU"
        elif ev == "a consonant":
            test = lambda ch: ch not in "AEIOU"
        else:
            test = lambda ch: ch == ev
        k = sum(test(ch) for ch in word)
        letters = []
        for ch in word:
            if ch not in letters:
                letters.append(ch)
        dk = sum(test(ch) for ch in letters)
        if len(word) > 12:
            bad.append("word longer than 12")
        return S(Fr(k, len(word)), uniform_oracle(k, len(word), distinct=(dk, len(letters))), bad)
    raise AssertionError(f"unreadable T2 prompt {p!r}")


# --- tier 3 ------------------------------------------------------------------------------------
def expect_oracle(a, d, n):
    k = n // d
    inv = Fr(n * d, a)
    return [("IGNORED_NUMERATOR", Fr(k) if a > 1 else None),
            ("INVERTED_P", inv if inv.denominator == 1 and inv <= 999 else None),
            ("OTHER_EVENT", Fr(n - a * k))]


T3_PLURALS = {"6s": 1, "3s": 1, "even numbers": 3, "odd numbers": 3, "numbers over 4": 2,
              "numbers under 3": 2, "multiples of 3": 2, "primes": 3, "numbers over 2": 4,
              "numbers under 5": 4}


def solve_t3(item):
    p = item["prompt"]
    bad = []
    if (m := re.fullmatch(r"Bag: (\d+) (\w+), (\d+) (\w+)\. P\(not (\w+)\)\?", p)):
        a, b = int(m[1]), int(m[3])
        assert m[5] == m[2]
        n = a + b
        if n > 12:
            bad.append(f"bag of {n}")
        return S(Fr(b, n), [("SAME_AS_EVENT", Fr(a, n)), ("PART_TO_PART", lt1(Fr(b, a)))], bad)
    if (m := re.fullmatch(r"Bag: (\d+) (\w+), (\d+) (\w+), (\d+) (\w+)\. P\(not (\w+)\)\?", p)):
        a, b, c = int(m[1]), int(m[3]), int(m[5])
        assert m[7] == m[2]
        n = a + b + c
        if n > 12:
            bad.append(f"bag of {n}")
        return S(Fr(b + c, n), [("SAME_AS_EVENT", Fr(a, n)), ("ONE_OTHER", Fr(b, n)),
                                ("PART_TO_PART", lt1(Fr(b + c, a)))], bad)
    if (m := re.fullmatch(r"P\(([a-z ]+)\) = (\S+)\. P\(([a-z ]+)\)\?", p)):
        txt = m[2]
        pv = read_value(txt)
        bad += chance_text_bad(txt)
        out = [("SAME_AS_EVENT", pv)]
        if "/" in txt:
            out.append(("PART_TO_PART", lt1(Fr(pv.numerator, pv.denominator - pv.numerator))))
        out.append(("ADD_TO_ONE", 1 + pv))
        return S(1 - pv, out, bad)
    if (m := re.fullmatch(r"P\(\w+\) = (\S+)\. (\w+) (\d+) times\. About how many (\w+)\?", p)):
        txt = m[1]
        pv, n = read_value(txt), int(m[3])
        a, d = pv.numerator, pv.denominator
        bad += chance_text_bad(txt)
        if n % d:
            bad.append(f"{n} is not a multiple of {d}")
            return S(pv * n, [], bad)
        k = n // d
        if not (2 <= d <= 10 and 2 <= k <= 10 and a * k <= 100 and n <= 100):
            bad.append(f"expected count {a}/{d} of {n}")
        return S(pv * n, expect_oracle(a, d, n), bad)
    if (m := re.fullmatch(r"Roll a die (\d+) times\. About how many (.+)\?", p)):
        n, fav = int(m[1]), T3_PLURALS[m[2]]
        k = n // 6
        if n % 6 or not 2 <= k <= 10 or fav * k > 100:
            bad.append(f"die count {n}")
        return S(Fr(fav * n, 6), expect_oracle(fav, 6, n), bad)
    if (m := re.fullmatch(r"Sample of (\d+) kids: (\d+) ([a-z ]+)\. About how many of (\d+)\?", p)):
        s, c, N = int(m[1]), int(m[2]), int(m[4])
        if N % s:
            bad.append("sample does not scale evenly")
            return S(Fr(c * N, s), [], bad)
        k = N // s
        if not (2 <= k <= 10 and N <= 100 and 2 <= c < s and c <= 10 and c * k <= 100):
            bad.append(f"sample {c} of {s} to {N}")
        return S(Fr(c * k), [("SAMPLE_COUNT", Fr(c)), ("ADDITIVE", Fr(c + N - s)), ("SCALE_ONLY", Fr(k)),
                             ("OTHER_EVENT", Fr(N - c * k))], bad)
    if (m := re.search(r"(\d+) of (\d+) [^.]*\. Estimate P\(\w+\)\?$", p)):
        c, n = int(m[1]), int(m[2])
        pv = Fr(c, n)
        g = gcd(c, n)
        if not (2 <= g <= 10 and pv.denominator <= 12 and pv.numerator <= 12 and pv != Fr(1, 2) and n <= 50):
            bad.append(f"estimate {c} of {n}")
        return S(pv, [("PART_TO_PART", lt1(Fr(c, n - c))), ("OTHER_EVENT", Fr(n - c, n)),
                      ("FLIPPED", Fr(n, c))], bad)
    raise AssertionError(f"unreadable T3 prompt {p!r}")


# --- tier 4 ------------------------------------------------------------------------------------
STAGES = {"flip a coin": 2, "roll a die": 6, "spin a 3-part spinner": 3, "spin a 4-part spinner": 4,
          "spin a 5-part spinner": 5}
FIXED3 = {"Roll a die and flip two coins. How many outcomes?": (6, 2, 2),
          "Flip two coins and spin a 3-part spinner. Outcomes?": (2, 2, 3),
          "Flip a coin, roll a die, spin a 4-part spinner. Outcomes?": (2, 6, 4),
          "Flip a coin, spin a 3-part spinner twice. Outcomes?": (2, 3, 3)}


def three_stage_ok(stages):
    lo, mid, hi = sorted(stages)
    return lo >= 2 and hi <= 10 and lo * mid <= 10


def solve_t4(item):
    p = item["prompt"]
    bad = []
    if p in LISTS:
        right, labels = LISTS[p]

        def label(text, v):
            return labels[text]

        return S(right, [], [], label)
    if (m := re.fullmatch(r"(.+) and (.+)\. How many outcomes\?", p)) and m[1].lower() in STAGES \
            and m[2] in STAGES:
        a, b = STAGES[m[1].lower()], STAGES[m[2]]
        return S(Fr(a * b), [("ADDED_COUNTS", Fr(a + b)), ("ONE_STAGE", Fr(max(a, b)))], bad)
    if (m := re.fullmatch(r"(\d+) (\w+) and (\d+) (\w+)\. How many (\w+)\?", p)):
        a, b = int(m[1]), int(m[3])
        if not (2 <= a <= 10 and 2 <= b <= 10):
            bad.append(f"factor outside 2-10: {a}, {b}")
        return S(Fr(a * b), [("ADDED_COUNTS", Fr(a + b)), ("ONE_STAGE", Fr(max(a, b)))], bad)
    if (m := re.fullmatch(r"(\d+) (\w+), (\d+) (\w+), (\d+) (\w+)\. How many (\w+)\?", p)) or p in FIXED3:
        a, b, c = (int(m[1]), int(m[3]), int(m[5])) if m else FIXED3[p]
        if not three_stage_ok((a, b, c)):
            bad.append(f"three stages {a}, {b}, {c}: no times-table order")
        return S(Fr(a * b * c), [("ADDED_COUNTS", Fr(a + b + c)), ("FORGOT_ONE", Fr(a * b)),
                                 ("MIXED_OPS", Fr((a + b) * c))], bad)
    m = (re.fullmatch(r"(?:Flip a coin|Toss a coin) (\d) times\. How many outcomes\?", p)
         or re.fullmatch(r"Flip (\d) coins\. How many outcomes\?", p))
    if m:
        n = int(m[1])
        if not 2 <= n <= 4:
            bad.append(f"{n} flips")
        return S(Fr(2 ** n), [("ORDER_BLIND", Fr(n + 1)), ("POWER_FLIP", Fr(n * n)),
                              ("MULT_BY_COUNT", Fr(2 * n)), ("ONE_STAGE", Fr(2))], bad)
    m = re.fullmatch(r"Spin a (\d)-part spinner twice\. How many outcomes\?", p)
    if m or p in ("Roll a die twice. How many outcomes?", "Roll two dice. How many outcomes?"):
        sides = int(m[1]) if m else 6
        if not 2 <= sides <= 6:
            bad.append(f"{sides} sides")
        return S(Fr(sides * sides), [("ORDER_BLIND", Fr(sides * (sides + 1) // 2)),
                                     ("ADDED_COUNTS", Fr(2 * sides)), ("ONE_STAGE", Fr(sides))], bad)
    if (m := re.fullmatch(r"Flip (two|three) coins\. How many outcomes have (.+)\?", p)):
        n = 2 if m[1] == "two" else 3
        outs = coin_outs(n, m[2])
        heads = len({s.count("H") for s in outs})
        if len(outs) < 2:
            bad.append("an event with one outcome")
        return S(Fr(len(outs)), [("ORDER_BLIND", Fr(heads)), ("COUNTED_ALL", Fr(2 ** n)),
                                 ("ONE_OUTCOME", Fr(1))], bad)
    if (m := re.fullmatch(r"Coin and die\. How many outcomes: (heads|tails) and (.+)\?", p)):
        s = len(faces_of(m[2], 6))
        return S(Fr(s), [("ADDED_COUNTS", Fr(1 + s)), ("IGNORED_PART", Fr(2 * s)), ("IGNORED_PART", Fr(6)),
                         ("TOTAL_NOT_EVENT", Fr(12))], bad)
    raise AssertionError(f"unreadable T4 prompt {p!r}")


# --- tier 5 ------------------------------------------------------------------------------------
def solve_t5(item):
    p = item["prompt"]
    bad = []
    if (m := re.fullmatch(r"Flip a coin, roll a die\. P\((heads|tails) and (.+)\)\?", p)):
        f = len(faces_of(m[2], 6))
        ans = Fr(sum(1 for side, x in itertools.product("HT", range(1, 7))
                     if side == m[1][0].upper() and x in faces_of(m[2], 6)), 12)
        assert ans == Fr(f, 12)
        return S(ans, [("ADDED_PROBS", lt1(Fr(1, 2) + Fr(f, 6))), ("ADD_DENOMS", lt1(Fr(f, 8))),
                       ("FORGOT_STAGE", lt1(Fr(f, 6))), ("FORGOT_STAGE", Fr(1, 2))], bad)
    if (m := re.fullmatch(r"Flip (two|three) coins\. P\((.+)\)\?", p)):
        n = 2 if m[1] == "two" else 3
        outs = coin_outs(n, m[2])
        heads = len({s.count("H") for s in outs})
        out = [("ORDER_BLIND", lt1(Fr(heads, n + 1)))]
        if n == 3:
            out.append(("ADD_DENOMS", lt1(Fr(len(outs), 6))))
        out += [("OTHER_EVENT", lt1(Fr(2 ** n - len(outs), 2 ** n))), ("FORGOT_STAGE", Fr(1, 2)),
                ("ONE_OUTCOME", lt1(Fr(1, 2 ** n)))]
        return S(Fr(len(outs), 2 ** n), out, bad)
    if (m := re.fullmatch(r"3-part spinner \(red, blue, green\), coin\. P\((.+) and (heads|tails)\)\?", p)):
        colors = {"red": ["red"], "blue": ["blue"], "green": ["green"], "red or blue": ["red", "blue"],
                  "blue or green": ["blue", "green"]}[m[1]]
        parts = ["red", "blue", "green"]
        count = sum(1 for part, side in itertools.product(parts, "HT") if part in colors and side == m[2][0].upper())
        s = len(colors)
        return S(Fr(count, 6), [("ADDED_PROBS", lt1(Fr(s, 3) + Fr(1, 2))), ("ADD_DENOMS", lt1(Fr(s, 5))),
                                ("FORGOT_STAGE", lt1(Fr(s, 3))), ("FORGOT_STAGE", Fr(1, 2))], bad)
    if (m := re.fullmatch(r"4-part spinner \(1 to 4\), coin\. P\((.+) and (heads|tails)\)\?", p)):
        ev = {"a 1": {1}, "a 4": {4}, "even": {2, 4}, "odd": {1, 3}, "over 2": {3, 4}, "under 4": {1, 2, 3}}[m[1]]
        count = sum(1 for x, side in itertools.product(range(1, 5), "HT") if x in ev and side == m[2][0].upper())
        s = len(ev)
        return S(Fr(count, 8), [("ADDED_PROBS", lt1(Fr(s, 4) + Fr(1, 2))), ("ADD_DENOMS", lt1(Fr(s, 6))),
                                ("FORGOT_STAGE", lt1(Fr(s, 4))), ("FORGOT_STAGE", Fr(1, 2))], bad)
    if (m := re.fullmatch(r"Bag: (\d+) (\w+), (\d+) (\w+)\. Draw, replace, draw\. P\((.+)\)\?", p)):
        c1, c2 = m[2], m[4]
        marbles = [c1] * int(m[1]) + [c2] * int(m[3])
        n = len(marbles)
        if n > 3:
            bad.append(f"bag of {n}: squares past 9")
        ev = m[5]
        if (mm := re.fullmatch(r"(\w+) twice", ev)):
            first, second, ordered = mm[1], mm[1], True
        elif (mm := re.fullmatch(r"(\w+) then (\w+)", ev)):
            first, second, ordered = mm[1], mm[2], True
        elif ev == "one of each":
            first, second, ordered = c1, c2, False
        else:
            raise AssertionError(ev)
        pairs = list(itertools.product(marbles, marbles))
        if ordered:
            hit = sum(1 for a, b in pairs if a == first and b == second)
        else:
            hit = sum(1 for a, b in pairs if {a, b} == {first, second} and a != b)
        x1, x2 = marbles.count(first), marbles.count(second)
        out = []
        if not ordered:
            out.append(("ONE_ORDER", lt1(Fr(x1 * x2, n * n))))
        elif x1 != x2:
            out.append(("ORDER_OVER", lt1(Fr(2 * x1 * x2, n * n))))
        out += [("ADDED_PROBS", lt1(Fr(x1 + x2, n))), ("ADD_DENOMS", lt1(Fr(x1 * x2, 2 * n))),
                ("FORGOT_STAGE", lt1(Fr(x1, n)))]
        return S(Fr(hit, n * n), out, bad)
    raise AssertionError(f"unreadable T5 prompt {p!r}")


SOLVERS = {1: solve_t1, 2: solve_t2, 3: solve_t3, 4: solve_t4, 5: solve_t5}


def solve(item):
    return SOLVERS[item["tier"]](item)


# ---------------------------------------------------------------------------------------------
# One checker per concern; item_problems() runs them all (and is what the disproofs sabotage)
# ---------------------------------------------------------------------------------------------
def check_answer(item, s):
    out = []
    ch = item["choices"]
    if len(ch) != 4:
        out.append(f"{len(ch)} choices")
    got = read_value(ch[item["answer"]])
    if got != s.answer:
        out.append(f"answer {ch[item['answer']]!r} reads as {got}, expected {s.answer}")
    if item["misconceptions"][item["answer"]] is not None:
        out.append("answer carries a label")
    return out


def check_distinct(item, s):
    vals = [read_value(c) for c in item["choices"]]
    return [f"two choices equal in value: {item['choices']}"] if len(set(vals)) != len(vals) else []


def check_labels(item, s):
    out = []
    ch, mis = item["choices"], item["misconceptions"]
    real = [m for m in mis if m and m != "ARITH"]
    if not real:
        out.append("no modelled misconception")
    for c, lab in zip(ch, mis):
        if lab is None:
            continue
        v = read_value(c)
        if s.label_fn:
            if lab != s.label_fn(c, v):
                out.append(f"{c!r} labelled {lab}, expected {s.label_fn(c, v)}")
        elif lab == "ARITH":
            if v in s.prio or v == s.answer:
                out.append(f"ARITH {c!r} is really {s.prio.get(v, 'the answer')}")
        elif s.prio.get(v) != lab:
            out.append(f"{c!r} labelled {lab}, rules say {s.prio.get(v)}")
    return out


def check_form(item, s):
    out = []
    forms = {form_of(c) for c in item["choices"]} - {"int"}
    if len(forms) > 1:
        out.append(f"mixed forms {sorted(forms)}: {item['choices']}")
    for c in item["choices"]:
        if "/" in c:
            a, b = (int(x) for x in c.replace(M, "").split("/"))
            if gcd(a, b) != 1:
                out.append(f"{c} is not in simplest form")
    if any("-" in c for c in item["choices"]):
        out.append("hyphen used for a minus sign")
    return out


def check_expl(item, s):
    ans = item["choices"][item["answer"]]
    e = item["explanation"]
    if e.endswith(ans + "."):
        return []
    if ans.replace(" ", "").isalpha() and re.search(r"\b" + re.escape(ans.lower()) + r"\.$", e.lower()):
        return []
    return [f"explanation does not end with the answer {ans!r}: {e!r}"]


def check_bounds(item, s):
    out = list(s.bad)
    a = s.answer
    if isinstance(a, Fr):
        if a.denominator > 12:
            out.append(f"answer {a} has a denominator over 12")
        if a.denominator == 1 and a > 100:
            out.append(f"count {a} over 100")
        if item["tier"] in (2, 5) and not 0 < a < 1:
            out.append(f"probability answer {a} is not strictly between 0 and 1")
    return out


CHECKS = {"answer": check_answer, "distinct": check_distinct, "labels": check_labels, "form": check_form,
          "expl": check_expl, "bounds": check_bounds}


def item_problems(item, which=None):
    s = solve(item)
    out = []
    for name, fn in CHECKS.items():
        if which is None or name in which:
            out += [f"{name}: {p}" for p in fn(item, s)]
    return out


@pytest.mark.parametrize("which", list(CHECKS))
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_item(item, which):
    assert item_problems(item, [which]) == [], item["prompt"]


# ---------------------------------------------------------------------------------------------
# Content shape
# ---------------------------------------------------------------------------------------------
def test_counts_and_shape():
    assert BAKED["items_per_tier"] == 40 and len(BAKED["tiers"]) == 5
    for t in range(1, 6):
        assert len(by_tier(t)) == 40
    assert all(len(it["choices"]) == 4 for it in ITEMS)
    assert BAKED["grade"] == "7" and BAKED["seed"] == 20261028
    assert all(s.startswith("CCSS.MATH.CONTENT.7.SP.") for s in BAKED["standards"])
    assert "CCSS.MATH.CONTENT.7.SP.C.8.B" in BAKED["standards"]


def test_arith_share_is_small():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 0.2
    for t in range(1, 6):
        ct = Counter(m for it in by_tier(t) for m in it["misconceptions"] if m)
        assert ct["ARITH"] / sum(ct.values()) <= 0.3, t


def test_every_catalog_key_is_used_and_every_used_key_declared():
    used = {m for it in ITEMS for m in it["misconceptions"] if m} - {"ARITH"}
    assert used == set(BAKED["misconceptions"]), (used ^ set(BAKED["misconceptions"]))
    for key, m in BAKED["misconceptions"].items():
        assert m["student"] and m["teacher"] and len(m["student"]) <= 80, key


def test_tier_shapes():
    t1 = by_tier(1)
    assert sum(it["prompt"].endswith("How likely?") for it in t1) == 12
    assert sum(it["prompt"].startswith("Which could") for it in t1) == 6
    assert sum(it["prompt"].startswith("Which can't") for it in t1) == 6
    assert all(it["prompt"].endswith("?") for it in ITEMS)
    assert all(re.search(r"P\(.+\)\?$", it["prompt"]) for it in by_tier(2) + by_tier(5))
    assert sum("Which lists every outcome" in it["prompt"] for it in by_tier(4)) == 2
    # T3 has every one of its four skills
    t3 = by_tier(3)
    assert sum(it["prompt"].startswith("Sample of") for it in t3) >= 8
    assert sum("Estimate" in it["prompt"] for it in t3) >= 6
    assert sum("About how many" in it["prompt"] and "Sample" not in it["prompt"] for it in t3) >= 10
    assert sum("P(not" in it["prompt"] or "P(no " in it["prompt"] for it in t3) >= 10


def test_bake_is_the_generators_output():
    import random
    manifest = {k: v for k, v in BAKED.items() if k not in ("items", "baked_with")}
    fresh = G.generate(manifest, random.Random(manifest["seed"]))
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == fresh


def test_wrong_choices_are_not_probability_giveaways_in_t2():
    # T2 wrong choices are real probabilities (strictly between 0 and 1): no 5/3 to eliminate on sight
    for it in by_tier(2):
        for c in it["choices"]:
            assert 0 < read_value(c) < 1, (it["prompt"], c)


# ---------------------------------------------------------------------------------------------
# Disproofs: the checkers must be able to fail
# ---------------------------------------------------------------------------------------------
def find(tier, pred):
    """A deep copy of the first baked item of a tier that satisfies pred."""
    for it in by_tier(tier):
        if pred(it):
            return json.loads(json.dumps(it))
    raise AssertionError("no such baked item")


def test_checker_catches_a_wrong_answer_index():
    it = find(2, lambda it: it["prompt"].startswith("Roll a die. P("))
    assert item_problems(it) == []
    it["answer"] = (it["answer"] + 1) % 4
    assert any(p.startswith("answer") for p in item_problems(it))


def test_checker_catches_two_right_doors():
    it = find(2, lambda it: it["choices"][it["answer"]] == "1/2")
    assert item_problems(it) == []
    i = next(k for k, m in enumerate(it["misconceptions"]) if m and k != it["answer"])
    it["choices"][i] = "3/6"  # 3/6 is 1/2 in value
    probs = item_problems(it)
    assert any(p.startswith("distinct") for p in probs)
    assert any(p.startswith("form") for p in probs)  # and it is not in simplest form


def test_checker_catches_a_wrong_label():
    it = find(2, lambda it: "BOUNDARY" in it["misconceptions"])
    assert item_problems(it) == []
    i = it["misconceptions"].index("BOUNDARY")
    it["misconceptions"][i] = "OTHER_EVENT"
    assert any(p.startswith("labels") for p in item_problems(it))
    it["misconceptions"][i] = "ARITH"
    assert any(p.startswith("labels") for p in item_problems(it))


def test_checker_catches_a_word_item_with_the_wrong_word():
    it = find(1, lambda it: it["choices"][it["answer"]] == "Likely" and "Certain" in it["choices"])
    assert item_problems(it) == []
    it["answer"] = it["choices"].index("Certain")
    assert any(p.startswith("answer") for p in item_problems(it))


def test_checker_catches_an_explanation_that_does_not_end_with_the_answer():
    it = find(2, lambda it: it["prompt"].startswith("Roll a die. P("))
    it["explanation"] = "Six is one face of six."
    assert any(p.startswith("expl") for p in item_problems(it))


@pytest.mark.parametrize("prompt,tier", [
    ("Bag: 5 red, 8 blue. P(red)?", 2),                                     # 13 marbles
    ("Spinner: 15 equal parts, 4 red. P(red)?", 2),                         # 15 parts
    ("Cards 1 to 20, pick one. P(even)?", 2),                               # 20 cards
    ("A letter is picked from PNEUMATICALLY. P(a vowel)?", 2),              # 13 letters
    ("P(win) = 1/4. Play 60 times. About how many wins?", 3),               # 60 ÷ 4 = 15 is past the table
    ("P(win) = 1/7. Play 70 times. About how many wins?", 3),               # denominator 7 is fine, k = 10
    ("P(win) = 1/4. Play 42 times. About how many wins?", 3),               # not a multiple of 4
    ("P(win) = 0.33. Play 100 times. About how many wins?", 3),             # 33/100: denominator 100
    ("Sample of 20 kids: 6 like jazz. About how many of 300?", 3),          # 300 is past 100
    ("Sample of 5 kids: 2 like jazz. About how many of 80?", 3),            # scale factor 16
    ("Spinner: red 14 of 98 spins. Estimate P(red)?", 3),                   # n = 98, gcd 14
    ("9 hats and 12 scarves. How many outfits?", 4),                        # a factor of 12
    ("Flip a coin 5 times. How many outcomes?", 4),                         # 32 outcomes
    ("3 shirts, 4 pants, 5 hats. How many outfits?", 4),                    # no order of small products
    ("Bag: 1 red, 3 blue. Draw, replace, draw. P(red twice)?", 5),          # 1/16
])
def test_bounds_checker_catches(prompt, tier):
    item = {"prompt": prompt, "tier": tier, "choices": [], "misconceptions": []}
    try:
        bad = solve(item).bad
    except AssertionError:
        bad = ["unreadable"]
    # the 1/7 line is bound-clean on purpose (d = 7, k = 10): the checker must also be able to pass
    expect_clean = prompt.startswith("P(win) = 1/7")
    assert bool(bad) == (not expect_clean), (prompt, bad)


@pytest.mark.parametrize("text,over,expect_bad", [
    ("3/8", False, False), ("2/4", False, True), ("1/13", False, True), ("13/12", False, True),
    ("0.25", False, False), ("0.333", False, True), ("0.35", False, False), ("1.25", True, True),
    ("1.5", True, False),
    ("30%", False, False), ("33%", False, True), ("110%", False, True), ("110%", True, False),
    ("350%", True, True), (M + "1/4", True, False),
])
def test_chance_text_checker(text, over, expect_bad):
    assert bool(chance_text_bad(text, over)) == expect_bad
