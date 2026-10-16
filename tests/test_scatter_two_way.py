"""scatter-two-way cartridge (grade 8, 8.SP.A.1-A.4): golden misconception rules, an independent
re-check of every baked item (the prompt is parsed here with regexes and solved with Fractions or
plain Python, never with the generator's solvers), the cartridge's bounds, and a disproof.
"""
import json
import re
from collections import Counter
from fractions import Fraction
from math import gcd

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "scatter-two-way"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
with open(REPO_ROOT / "cartridges" / CID / "cartridge.json", encoding="utf-8") as _f:
    MANIFEST = json.load(_f)
ITEMS = BAKED["items"]
M = "−"
ALLOWED_EXTRA = set("×÷−≤≥≠√π")


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def pn(s: str) -> int:
    return int(s.replace(M, "-"))


# ---------------------------------------------------------------------------------------------
# Golden cases: each rule on a hand-worked item
# ---------------------------------------------------------------------------------------------
def test_golden_predict():
    # y = 2x + 10 at x = 5 is 20; dropping the start gives 10, adding all three 17, swapping m and b 52
    assert G.predict_wrongs(2, 10, 5) == [("NO_START", 10), ("ADDED_ALL", 17), ("START_AS_SLOPE", 52)]
    # y = 3x + 4 at x = 6 is 22
    assert G.predict_wrongs(3, 4, 6) == [("NO_START", 18), ("ADDED_ALL", 13), ("START_AS_SLOPE", 27)]
    # a swapped product past 100 is not offered
    assert G.predict_wrongs(3, 20, 10) == [("NO_START", 30), ("ADDED_ALL", 33)]
    # negative slope: y = −2x + 18 at x = 5 is 8
    assert G.predict_wrongs(-2, 18, 5) == [("NO_START", -10), ("ADDED_ALL", 21), ("START_AS_SLOPE", 88)]


def test_golden_slope_and_start():
    assert G.slope_wrongs(3, 4) == [("START_AS_SLOPE", 4), ("ADDED_SLOPE_START", 7), ("MULT_SLOPE_START", 12)]
    assert G.start_wrongs(2, 5) == [("SLOPE_AS_START", 2), ("ADDED_SLOPE_START", 7), ("MULT_SLOPE_START", 10)]


def test_golden_inverse():
    # y = 3x + 6, y = 18: x = 4. Stop after the subtraction -> 12; forget the start -> 6; add it -> 8
    assert G.inverse_wrongs(3, 6, 18) == [("STOPPED_EARLY", 12), ("IGNORE_START", 6), ("ADD_START", 8)]
    # 7x + 4 = 25: y / m and (y + b) / m are not whole, so only the first rule fires
    assert G.inverse_wrongs(7, 4, 25) == [("STOPPED_EARLY", 21)]


def test_golden_lines():
    # points (1, 3), (2, 5), (3, 7): y = 2x + 1
    assert G.line_wrongs(2, 1, 1, 3) == [("START_AS_SLOPE", (1, 2)), ("NO_START", (2, 0)),
                                          ("SLOPE_FROM_ONE_POINT", (3, 0))]
    assert G.line_text(2, 1) == "y = 2x + 1" and G.line_text(1, 2) == "y = x + 2"
    assert G.line_text(-1, 9) == f"y = {M}x + 9" and G.line_text(9, -2) == f"y = 9x {M} 2"
    # first point (2, 5): 5 / 2 is not whole, so the one-point rule does not fire
    assert [lab for lab, _ in G.line_wrongs(3, 1, 2, 7)] == ["START_AS_SLOPE", "NO_START"]


def test_golden_tables():
    # Boys: 6 yes, 4 no. Girls: 7 yes, 3 no. (total yes 13, boys 10, all 20)
    assert G.col_wrongs(6, 4, 7, 3) == [("GRAND_TOTAL", 20), ("WRONG_ROW", 10), ("ONE_CELL", 6),
                                         ("WRONG_ROW", 10), ("WRONG_ROW", 7)]
    assert G.row_wrongs(6, 4, 7, 3) == [("GRAND_TOTAL", 20), ("WRONG_ROW", 13), ("ONE_CELL", 6), ("WRONG_ROW", 7)]
    assert G.grand_wrongs(6, 4, 7, 3, 3) == [("WRONG_ROW", 10), ("LEFT_OUT_CELL", 17), ("WRONG_ROW", 13),
                                              ("WRONG_ROW", 10)]
    # 12 play sports, 5 of them play music: sports only is 7
    assert G.only_wrongs(12, 5) == [("ADDED_FOR_ONLY", 17), ("WHOLE_FOR_ONLY", 12), ("ONLY_IS_BOTH", 5)]
    # Yes: 13 in all, 6 are boys: girls 7
    assert G.missing_wrongs(13, 6) == [("ADDED_FOR_MISSING", 19), ("GIVEN_CELL", 6), ("TOTAL_AS_MISSING", 13)]


def test_golden_frequencies():
    from fractions import Fraction as F
    # Boys: 6 yes, 4 no -> 3/5; part-to-part 3/2, the other part 2/5, whole over part 5/3
    assert G.frac_wrongs(6, 4) == [("PART_TO_PART", F(3, 2)), ("OTHER_PART", F(2, 5)), ("WHOLE_OVER_PART", F(5, 3))]
    # with 13 yes in all the column total is the wrong denominator; with 20 in all the grand total is
    assert G.frac_wrongs(6, 4, ("WRONG_TOTAL", 13))[0] == ("WRONG_TOTAL", F(6, 13))
    assert G.frac_wrongs(6, 4, ("GRAND_DENOMINATOR", 20))[0] == ("GRAND_DENOMINATOR", F(3, 10))
    # Girls: 3 yes, 7 no: 30 percent; the other part is 70, the count as a percent is 3
    assert G.percent_wrongs(3, 30) == [("OTHER_PART", 70), ("COUNT_AS_PERCENT", 3)]
    assert G.frac_text(F(6, 4)) == "3/2" and G.frac_text(F(4, 1)) == "4"


def test_golden_association_labels():
    # both fall: a student calls it negative
    assert G.t1_labels(0, -1) == {1: "BOTH_DOWN_NEGATIVE", 2: "MISSES_PATTERN"}
    assert G.t1_labels(0, 1) == {1: "REVERSED", 2: "MISSES_PATTERN"}
    assert G.t1_labels(0, 1, noncausal=True)[2] == "CAUSE_FOR_LINK"
    # first variable rises, second falls: a student who watches only the first says positive
    assert G.t1_labels(1, 1) == {0: "FIRST_VARIABLE", 2: "DOWN_IS_NONE"}
    assert G.t1_labels(1, -1)[0] == "REVERSED"
    assert G.t1_labels(2, None) == {0: "PATTERN_FROM_NOISE", 1: "PATTERN_FROM_NOISE"}
    assert G.t1_labels(1, None) == {0: "REVERSED", 2: "DOWN_IS_NONE"}


def test_golden_make_item_rejects_equal_values():
    import random
    # `2/4` and `1/2` have the same value: the second can never be offered next to the first
    it = G.make_item(5, "p", ("1/2", Fraction(1, 2)),
                     [("PART_TO_PART", "2/4", Fraction(2, 4)), ("OTHER_PART", "1/3", Fraction(1, 3)),
                      ("WHOLE_OVER_PART", "2", Fraction(2)), ("ARITH", "3/4", Fraction(3, 4))],
                     0, "e", random.Random(1), n=4)
    assert it is not None and "2/4" not in it["choices"]


# ---------------------------------------------------------------------------------------------
# Independent parsing and solving
# ---------------------------------------------------------------------------------------------
SING = {"boy": "boys", "girl": "girls", "kid": "kids", "adult": "adults", "taco": "tacos"}


def prio(pairs):
    """{value: label} where the FIRST rule that produces a value owns it (the generator's priority)."""
    out = {}
    for k, lab in pairs:
        out.setdefault(k, lab)
    return out


def norm_noun(w):
    return SING.get(w, w)


# the test's own copy of which pairs of variables really move together (+1) or opposite (-1)
REAL = {
    ("study time", "test scores"): 1, ("practice time", "shots made"): 1, ("hours worked", "pay"): 1,
    ("tree height", "trunk width"): 1, ("pizza size", "price"): 1, ("rainfall", "umbrella sales"): 1,
    ("puppy age", "puppy weight"): 1, ("ice cream sales", "sunburns"): 1,
    ("car age", "car value"): -1, ("temperature", "cocoa sales"): -1, ("miles driven", "gas left"): -1,
    ("screen time", "sleep time"): -1, ("absences", "grades"): -1, ("burn time", "candle height"): -1,
    ("altitude", "air temperature"): -1, ("car speed", "trip time"): -1,
}
NONCAUSAL = {("ice cream sales", "sunburns")}
NO_PAIRS = {("shoe size", "favorite color"), ("birth month", "quiz score"), ("hair length", "math grade"),
            ("locker number", "height"), ("eye color", "free throws made"), ("backpack color", "reading speed"),
            ("seat number", "lunch cost"), ("phone number", "shoe size")}

PT = re.compile(r"\((" + M + r"?\d+), (" + M + r"?\d+)\)")


def points_of(text):
    return [(pn(a), pn(b)) for a, b in PT.findall(text)]


def cov_sign(points):
    n = len(points)
    mx = Fraction(sum(x for x, _ in points), n)
    my = Fraction(sum(y for _, y in points), n)
    c = sum((x - mx) * (y - my) for x, y in points)
    return (c > 0) - (c < 0)


LINE_RE = re.compile(r"^y = (" + M + r"?\d*)x(?: (\+|" + M + r") (\d+))?$")


def parse_line(text):
    mt = LINE_RE.match(text)
    assert mt, text
    c = mt.group(1)
    m = 1 if c == "" else -1 if c == M else pn(c)
    b = 0 if mt.group(2) is None else (int(mt.group(3)) if mt.group(2) == "+" else -int(mt.group(3)))
    return m, b


def strip_units(text):
    return text.replace("$", "").replace(" cm", "").replace(" mi", "")


def fraction_of(text):
    text = text.strip()
    if text.endswith("%"):
        return Fraction(int(text[:-1]))
    if "/" in text:
        a, b = text.split("/")
        return Fraction(int(a), int(b))
    return Fraction(pn(text))


def solve(item):
    """-> (kind, data, correct_key, {label: key}, key_fn). Everything computed here from the prompt."""
    t, p = item["tier"], item["prompt"]
    if t == 1:
        mt = re.match(r"^(.+?) (rises?|falls?), (.+?) (rises?|falls?)\. Association\?$", p)
        if mt:
            xn, yn = mt.group(1).lower(), mt.group(3)
            xdir = 1 if mt.group(2).startswith("rise") else -1
            ydir = 1 if mt.group(4).startswith("rise") else -1
            assert REAL[(xn, yn)] == xdir * ydir, "the sentence must state a true relationship"
            ans = "Positive" if xdir == ydir else "Negative"
            nc = (xn, yn) in NONCAUSAL
            wrong = {}
            if ans == "Positive":
                wrong["Negative"] = "BOTH_DOWN_NEGATIVE" if xdir == -1 else "REVERSED"
                wrong["None"] = "CAUSE_FOR_LINK" if nc else "MISSES_PATTERN"
            else:
                wrong["Positive"] = "FIRST_VARIABLE" if xdir == 1 else "REVERSED"
                wrong["None"] = "CAUSE_FOR_LINK" if nc else "DOWN_IS_NONE"
            return "assoc", None, ans, wrong, str
        mt = re.match(r"^(.+) and (.+)\. Association\?$", p)
        if mt:
            assert (mt.group(1).lower(), mt.group(2)) in NO_PAIRS
            return "assoc", None, "None", {"Positive": "PATTERN_FROM_NOISE", "Negative": "PATTERN_FROM_NOISE"}, str
        mt = re.match(r"^Points (.*)\. Association\?$", p)
        pts = points_of(mt.group(1))
        s = cov_sign(pts)
        ys = [y for _, y in pts]
        if s > 0:
            assert all(b > a for a, b in zip(ys, ys[1:])), "positive lists rise at every step"
            ans, wrong = "Positive", {"Negative": "REVERSED", "None": "MISSES_PATTERN"}
        elif s < 0:
            assert all(b < a for a, b in zip(ys, ys[1:])), "negative lists fall at every step"
            ans, wrong = "Negative", {"Positive": "REVERSED", "None": "DOWN_IS_NONE"}
        else:
            # no association: zigzag, no net movement
            assert all((ys[i + 1] - ys[i]) * (ys[i + 2] - ys[i + 1]) < 0 for i in range(len(ys) - 2))
            assert abs(ys[-1] - ys[0]) <= 3
            ans, wrong = "None", {"Positive": "PATTERN_FROM_NOISE", "Negative": "PATTERN_FROM_NOISE"}
        return "assoc", pts, ans, wrong, str
    if t == 2:
        mt = re.match(r"^(?:Points|Plot) (.*)\. Outlier\?$", p)
        if mt:
            pts = points_of(mt.group(1))
            odd = []
            for i in range(len(pts)):
                rest = pts[:i] + pts[i + 1:]
                (x0, y0), (x1, y1) = rest[0], rest[1]
                if all((y - y0) * (x1 - x0) == (y1 - y0) * (x - x0) for x, y in rest):
                    odd.append(pts[i])
            assert len(odd) == 1, "exactly one point breaks the line"
            xmax = max(x for x, _ in pts)
            ymax = max(y for _, y in pts)
            wrong = {}
            for q in pts:
                if q == odd[0]:
                    continue
                if q[0] == xmax:
                    wrong[q] = "LARGEST_X_OUTLIER"
                elif q[1] == ymax:
                    wrong[q] = "HIGHEST_Y_OUTLIER"
                else:
                    wrong[q] = "ANY_POINT"
            return "outlier", pts, odd[0], wrong, lambda s_: points_of(s_)[0]
        mt = re.match(r"^(?:Which line fits|Line of fit for) (.*)\?$", p)
        pts = points_of(mt.group(1))
        (x0, y0), (x1, y1) = pts[0], pts[1]
        m = Fraction(y1 - y0, x1 - x0)
        assert m.denominator == 1
        m = int(m)
        b = y0 - m * x0
        assert all(y == m * x + b for x, y in pts)
        wrong = {(b, m): "START_AS_SLOPE", (m, 0): "NO_START"}
        if y0 % x0 == 0:
            wrong[(y0 // x0, 0)] = "SLOPE_FROM_ONE_POINT"
        return "line", pts, (m, b), wrong, parse_line
    if t == 3:
        mt = re.match(r"^Line of fit y = (" + M + r"?\d*)x \+ (\d+)\. Predict y at x = (\d+)\.$", p)
        if mt:
            c = mt.group(1)
            m = 1 if c == "" else -1 if c == M else pn(c)
            b, x = int(mt.group(2)), int(mt.group(3))
            return "predict", (m, b, x), m * x + b, \
                prio([(m * x, "NO_START"), (m + x + b, "ADDED_ALL"), (b * x + m, "START_AS_SLOPE")]), \
                lambda s_: pn(strip_units(s_))
        mt = re.match(r"^Line of fit y = (\d+)x \+ (\d+)\. For which x is y = (\d+)\?$", p)
        if mt:
            m, b, y = (int(g) for g in mt.groups())
            assert (y - b) % m == 0
            pairs = [(y - b, "STOPPED_EARLY")]
            if y % m == 0:
                pairs.append((y // m, "IGNORE_START"))
            if (y + b) % m == 0:
                pairs.append(((y + b) // m, "ADD_START"))
            wrong = prio(pairs)
            return "inverse", (m, b, y), (y - b) // m, wrong, lambda s_: pn(strip_units(s_))
        mt = re.match(r"^(Cost|Height|Savings|Miles) y = (\d+)x \+ (\d+) \(x (hours|weeks)\)\. (.+)$", p)
        m, b, q = int(mt.group(2)), int(mt.group(3)), mt.group(5)
        if " per " in q:
            return "slope", (m, b), m, prio([(b, "START_AS_SLOPE"), (m + b, "ADDED_SLOPE_START"),
                                             (m * b, "MULT_SLOPE_START")]), lambda s_: pn(strip_units(s_))
        if "start" in q or "at 0 hours" in q:
            return "start", (m, b), b, prio([(m, "SLOPE_AS_START"), (m + b, "ADDED_SLOPE_START"),
                                             (m * b, "MULT_SLOPE_START")]), lambda s_: pn(strip_units(s_))
        x = int(re.search(r"(\d+)", q).group(1))
        return "predict", (m, b, x), m * x + b, \
            prio([(m * x, "NO_START"), (m + x + b, "ADDED_ALL"), (b * x + m, "START_AS_SLOPE")]), \
            lambda s_: pn(strip_units(s_))
    if t == 4:
        mt = re.match(r"^(\w+): (\d+) (\w+), (\d+) (\w+)\. (\w+): (\d+) (\w+), (\d+) (\w+)\. (.+)$", p)
        if mt:
            A, a1, X, a2, Y, B, b1, X2, b2, Y2, q = mt.groups()
            a1, a2, b1, b2 = int(a1), int(a2), int(b1), int(b2)
            assert (X, Y) == (X2, Y2)
            grand = a1 + a2 + b1 + b2
            if q == f"Total {X}?":
                ans = a1 + b1
                wrong = prio([(grand, "GRAND_TOTAL"), (a1 + a2, "WRONG_ROW"), (a1, "ONE_CELL"),
                              (b1 + b2, "WRONG_ROW"), (a2 + b2, "WRONG_ROW")])
            elif q == f"Total {A.lower()}?" or q == f"Total {B.lower()}?":
                if q == f"Total {A.lower()}?":
                    c1, c2, d1, d2 = a1, a2, b1, b2
                else:
                    c1, c2, d1, d2 = b1, b2, a1, a2
                ans = c1 + c2
                wrong = prio([(grand, "GRAND_TOTAL"), (c1 + d1, "WRONG_ROW"), (c1, "ONE_CELL"),
                              (c2 + d2, "WRONG_ROW")])
            else:
                assert q == "How many in all?"
                ans = grand
                wrong = prio([(a1 + a2, "WRONG_ROW"), (a1 + b1, "WRONG_ROW"), (b1 + b2, "WRONG_ROW")]
                             + [(grand - cell, "LEFT_OUT_CELL") for cell in (a1, a2, b1, b2)])
            return "table", (a1, a2, b1, b2), ans, wrong, pn
        mt = re.match(r"^(\d+) kids (.+); (\d+) of them (.+)\. (.+) only\?$", p)
        if mt:
            n, k = int(mt.group(1)), int(mt.group(3))
            return "only", (n, k), n - k, prio([(n + k, "ADDED_FOR_ONLY"), (n, "WHOLE_FOR_ONLY"), (k, "ONLY_IS_BOTH")]), pn
        mt = re.match(r"^(.+): (\d+) in all, (\d+) are (\w+)\. How many are (\w+)\?$", p)
        t_, a = int(mt.group(2)), int(mt.group(3))
        return "missing", (t_, a), t_ - a, prio([(t_ + a, "ADDED_FOR_MISSING"), (a, "GIVEN_CELL"), (t_, "TOTAL_AS_MISSING")]), pn
    # tier 5
    mt = re.match(r"^(\w+): (\d+) of (\d+) (.+)\. (\w+): (\d+) of (\d+)\. Who is more likely\?$", p)
    if mt:
        A, a, n, _, B, c, m = mt.groups()
        a, n, c, m = int(a), int(n), int(c), int(m)
        f1, f2 = Fraction(a, n), Fraction(c, m)
        ans = "Same" if f1 == f2 else (A if f1 > f2 else B)
        big = A if a > c else B
        wrong = {w: ("COUNT_NOT_RATE" if w == big else "NOT_COMPARED") for w in (A, B, "Same") if w != ans}
        return "compare", (a, n, c, m, A, B), ans, wrong, str
    mt = re.match(r"^(.+): (\d+) (\w+), (\d+) (\w+)\. Fraction that are (\w+)\?$", p)
    if mt:
        _, a, A, b, B, asked = mt.groups()
        a, b = int(a), int(b)
        assert norm_noun(A) == asked
        tot = a + b
        wrong = prio([(Fraction(a, b), "PART_TO_PART"), (Fraction(b, tot), "OTHER_PART"),
                      (Fraction(tot, a), "WHOLE_OVER_PART")])
        return "column", (a, b), Fraction(a, tot), wrong, fraction_of
    mt = re.match(r"^(\w+): (\d+) (\w+), (\d+) (\w+)\.(?: (\d+) in all\.| All: (\d+) (\w+)\.)? "
                  r"(Fraction|Percent) of (\w+) (.+)\?$", p)
    a, b = int(mt.group(2)), int(mt.group(4))
    tot = a + b
    assert norm_noun(mt.group(10)) == norm_noun(mt.group(1).lower())
    if mt.group(9) == "Percent":
        pct = Fraction(100 * a, tot)
        wrong = {100 - pct: "OTHER_PART", Fraction(a): "COUNT_AS_PERCENT"}
        return "percent", (a, b), pct, wrong, fraction_of
    pairs = []
    if mt.group(6):
        pairs.append((Fraction(a, int(mt.group(6))), "GRAND_DENOMINATOR"))
    if mt.group(7):
        pairs.append((Fraction(a, int(mt.group(7))), "WRONG_TOTAL"))
    pairs += [(Fraction(a, b), "PART_TO_PART"), (Fraction(b, tot), "OTHER_PART"), (Fraction(tot, a), "WHOLE_OVER_PART")]
    wrong = prio(pairs)
    return "fraction", (a, b), Fraction(a, tot), wrong, fraction_of


def choice_keys(item):
    _, _, _, _, kf = solve(item)
    return [kf(c) for c in item["choices"]]


def test_item_count_and_tiers():
    assert len(ITEMS) == 200
    assert [len(by_tier(t)) for t in range(1, 6)] == [40] * 5
    assert MANIFEST["grade"] == "8" and MANIFEST["seed"] == 20261040
    assert all(s.startswith("CCSS.MATH.CONTENT.8.SP.A.") for s in MANIFEST["standards"])


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_answer_independent(item):
    kind, data, correct, wrong, kf = solve(item)
    keys = choice_keys(item)
    assert keys[item["answer"]] == correct, (item["prompt"], item["choices"], correct)
    # no second right door: no other choice equals the right value (exact value compare)
    for i, k in enumerate(keys):
        if i != item["answer"]:
            assert k != correct, (item["prompt"], item["choices"])
    assert len(set(keys)) == len(keys), ("equal values among choices", item["prompt"], item["choices"])


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_labels_are_produced_by_their_rule(item):
    kind, data, correct, wrong, kf = solve(item)
    keys = choice_keys(item)
    for k, lab in zip(keys, item["misconceptions"]):
        if lab is None:
            continue
        if lab == "ARITH":
            assert k not in wrong, ("ARITH value that a misconception produces", item["prompt"], k)
        else:
            assert k in wrong and wrong[k] == lab, (item["prompt"], k, lab, wrong)


def test_word_choices_have_exactly_one_true():
    for it in ITEMS:
        kind, data, correct, wrong, kf = solve(it)
        if kind in ("assoc", "compare"):
            assert sorted(it["choices"]) == sorted(set(it["choices"]))
            true = [c for c in it["choices"] if c == correct]
            assert len(true) == 1, it["prompt"]


def test_no_hyphen_minus_and_charset():
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"], *it["choices"]]:
            assert "-" not in s, s
            for ch in s:
                assert 32 <= ord(ch) < 127 or ch in ALLOWED_EXTRA, (ch, s)
        for s in it["choices"]:
            if "/" in s:
                a, b = (int(v) for v in s.split("/"))
                assert gcd(a, b) == 1 and b > 1, ("unsimplified distractor", s)


def test_answer_positions_balanced_per_choice_count():
    for t in range(1, 6):
        for n in (3, 4):
            its = [i for i in by_tier(t) if len(i["choices"]) == n]
            if not its:
                continue
            c = Counter(i["answer"] for i in its)
            for pos in range(n):
                assert 0.5 / n * len(its) <= c[pos] <= 1.5 / n * len(its), (t, n, c)


def test_arith_share_is_low():
    labs = [m for it in ITEMS for m in it["misconceptions"] if m]
    assert labs.count("ARITH") / len(labs) < 0.15
    for t in range(1, 6):
        ls = [m for it in by_tier(t) for m in it["misconceptions"] if m]
        assert ls.count("ARITH") / len(ls) < 0.3, t


def test_every_declared_key_is_used_and_every_used_key_declared():
    used = {m for it in ITEMS for m in it["misconceptions"] if m} - {"ARITH"}
    declared = set(MANIFEST["misconceptions"])
    assert used <= declared
    assert declared <= used, declared - used


def test_prompts_unique_per_tier_and_tiers_have_both_shapes():
    for t in range(1, 6):
        ps = [i["prompt"] for i in by_tier(t)]
        assert len(set(ps)) == 40
    kinds = Counter(solve(i)[0] for i in ITEMS)
    for k in ("assoc", "outlier", "line", "predict", "slope", "start", "inverse", "table", "only", "missing",
              "fraction", "percent", "column", "compare"):
        assert kinds[k] >= 4, (k, kinds)


def test_tier_one_answers_are_spread():
    c = Counter(solve(i)[2] if not isinstance(solve(i)[2], list) else None for i in by_tier(1))
    assert c["Positive"] >= 10 and c["Negative"] >= 10 and c["None"] >= 8, c


def test_compare_answers_spread_and_trap_present():
    its = [i for i in by_tier(5) if solve(i)[0] == "compare"]
    answers = Counter(i["choices"][i["answer"]] for i in its)
    assert answers["Same"] >= 2
    first = sum(1 for i in its if i["choices"][i["answer"]] == solve(i)[1][4])
    second = sum(1 for i in its if i["choices"][i["answer"]] == solve(i)[1][5])
    assert first >= 2 and second >= 2, (first, second)
    for i in its:
        a, n, c, m, A, B = solve(i)[1]
        if Fraction(a, n) != Fraction(c, m):
            # the group with the larger count has the lower rate: the count trap is live
            assert (a > c) != (Fraction(a, n) > Fraction(c, m))


# ---------------------------------------------------------------------------------------------
# Bounds (this cartridge's `bounds` string), checked by walking each item
# ---------------------------------------------------------------------------------------------
PERCENTS = {10, 20, 30, 40, 50, 60, 70, 80, 90, 25, 75, 100}


def bad_line(m, b):
    out = []
    if not (1 <= m <= 10 or -5 <= m <= -1):
        out.append(f"slope {m}")
    if not 0 <= b <= 20:
        out.append(f"start {b}")
    return out


def check_bounds(item):
    """Violations of the bounds string for one item (own implementation)."""
    kind, data, correct, wrong, kf = solve(item)
    bad = []
    if kind == "assoc" and data is not None:
        if not 3 <= len(data) <= 5 or any(not (0 <= x <= 20 and 0 <= y <= 20) for x, y in data):
            bad.append(f"points {data}")
    elif kind == "outlier":
        if not 4 <= len(data) <= 5 or any(not (0 <= x <= 20 and 0 <= y <= 20) for x, y in data):
            bad.append(f"points {data}")
        rest = [q for q in data if q != correct]
        (x0, y0), (x1, y1) = rest[0], rest[1]
        m = Fraction(y1 - y0, x1 - x0)
        b = y0 - m * x0
        if m.denominator != 1 or bad_line(int(m), int(b)):
            bad.append(f"line m={m} b={b}")
        elif abs(correct[1] - (int(m) * correct[0] + int(b))) < 7:
            bad.append("outlier less than 7 off the line")
    elif kind == "line":
        if len(data) != 3 or any(not (0 <= x <= 20 and 0 <= y <= 20) for x, y in data):
            bad.append(f"points {data}")
        bad += bad_line(*correct)
    elif kind in ("predict", "inverse"):
        m, b, x = data
        if kind == "inverse":
            m, b, y = data
            x = correct
            if not (2 <= m <= 10 and 2 <= x <= 10 and y <= 100):
                bad.append(f"inverse {data}")
        bad += bad_line(m, b)
        if kind == "predict":
            if not 1 <= x <= 10:
                bad.append(f"x {x}")
            if not 0 <= m * x + b <= 100:
                bad.append(f"prediction {m * x + b}")
    elif kind in ("slope", "start"):
        m, b = data
        bad += bad_line(m, b)
    elif kind == "table":
        cells = data
        if any(not 0 <= c <= 20 for c in cells) or sum(cells) > 60:
            bad.append(f"cells {cells}")
    elif kind == "only":
        n, k = data
        if not (n <= 20 and 0 < k < n and n + k <= 60):
            bad.append(f"only {data}")
    elif kind == "missing":
        t_, a = data
        if not (t_ <= 20 and 0 < a < t_):
            bad.append(f"missing {data}")
    elif kind in ("fraction", "column"):
        a, b = data
        tot = a + b
        if not (4 <= tot <= 20 and a > 0 and b > 0):
            bad.append(f"total {tot}")
        if not (2 <= correct.denominator <= 12 and 0 < correct < 1):
            bad.append(f"fraction {correct}")
        m_ = re.search(r"(\d+) in all|All: (\d+)", item["prompt"])
        if m_ and int(m_.group(1) or m_.group(2)) > 60:
            bad.append("clause total over 60")
    elif kind == "percent":
        a, b = data
        if (a + b) not in (4, 5, 8, 10, 20) or correct.denominator != 1 or int(correct) not in PERCENTS:
            bad.append(f"percent {correct} of {a + b}")
    elif kind == "compare":
        a, n, c, m, A, B = data
        if max(n, m) > 20:
            bad.append("total over 20")
        for f in (Fraction(a, n), Fraction(c, m)):
            if not 2 <= f.denominator <= 12:
                bad.append(f"rate {f}")
        if Fraction(a, n) != Fraction(c, m) and abs(Fraction(a, n) - Fraction(c, m)) < Fraction(3, 20):
            bad.append("rates too close to compare in the head")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_bounds(item):
    assert check_bounds(item) == []


def test_validation_limits():
    for it in ITEMS:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160
        assert all(len(c) <= 14 for c in it["choices"])
    for k, v in MANIFEST["misconceptions"].items():
        assert len(v["student"]) <= 80, k
    assert len(MANIFEST["title"]) <= 32 and len(MANIFEST["subtitle"]) <= 40
    assert all(len(t["name"]) <= 24 for t in MANIFEST["tiers"])
    assert "bounds" in MANIFEST and len(MANIFEST["bounds"]) > 100


# ---------------------------------------------------------------------------------------------
# Disproof: the checkers can fail
# ---------------------------------------------------------------------------------------------
def fake(tier, prompt, choices, answer=0):
    return {"tier": tier, "prompt": prompt, "choices": choices, "answer": answer,
            "misconceptions": [None] + ["ARITH"] * (len(choices) - 1), "explanation": "x"}


@pytest.mark.parametrize("item", [
    fake(3, "Line of fit y = 12x + 5. Predict y at x = 5.", ["65", "1", "2", "3"]),        # slope 12 > 10
    fake(3, "Line of fit y = 5x + 30. Predict y at x = 5.", ["55", "1", "2", "3"]),        # start 30 > 20
    fake(3, "Line of fit y = 10x + 20. Predict y at x = 10.", ["120", "1", "2", "3"]),     # prediction > 100
    fake(4, "Boys: 25 yes, 4 no. Girls: 7 yes, 3 no. Total yes?", ["32", "1", "2", "3"]),  # cell 25 > 20
    fake(4, "Boys: 20 yes, 19 no. Girls: 15 yes, 9 no. Total yes?", ["35", "1", "2", "3"]),  # total 63 > 60
    fake(5, "Boys: 6 yes, 7 no. Fraction of boys saying yes?", ["6/13", "1/2", "2/3", "3/4"]),  # denominator 13
    fake(5, "Boys: 3 yes, 4 no. Percent of boys saying yes?", ["43%", "1%", "2%", "3%"]),     # not a 4b percent
    fake(5, "Boys: 4 of 5 say yes. Girls: 5 of 6. Who is more likely?", ["Girls", "Boys", "Same"]),  # too close
    fake(2, "Points (1, 2), (2, 3), (3, 4), (4, 7). Outlier?", ["(4, 7)", "(1, 2)", "(2, 3)", "(3, 4)"]),  # only 3 off
    fake(1, "Points (1, 1), (2, 3), (3, 25). Association?", ["Positive", "Negative", "None"]),  # y 25 > 20
])
def test_bounds_checker_rejects(item):
    assert check_bounds(item) != []


def test_answer_checker_catches_a_planted_wrong_answer():
    it = next(i for i in ITEMS if solve(i)[0] == "predict")
    bad = dict(it)
    bad["answer"] = (it["answer"] + 1) % len(it["choices"])
    kind, data, correct, wrong, kf = solve(bad)
    assert choice_keys(bad)[bad["answer"]] != correct


def test_label_checker_catches_a_swapped_label():
    it = next(i for i in ITEMS if solve(i)[0] == "predict")
    kind, data, correct, wrong, kf = solve(it)
    keys = choice_keys(it)
    i = next(j for j, lab in enumerate(it["misconceptions"]) if lab == "NO_START")
    assert wrong[keys[i]] == "NO_START"
    assert wrong[keys[i]] != "ADDED_ALL"
