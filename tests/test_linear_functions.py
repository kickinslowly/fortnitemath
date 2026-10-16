"""linear-functions cartridge: golden misconception values for every catalog key, an independent re-solve of
every baked item, choice-value uniqueness (exactly one right door), and the manifest's bounds walked over
every baked prompt (with a checker self-test that must reject planted bad prompts).

The independent solver below reads each prompt with its own regexes and computes with ``Fraction`` and a
tiny evaluator for the equation text. It never calls the generator's ``s_*`` / ``b_*`` functions. For
"which one?" questions it evaluates EVERY choice against the property (function, linear, proportional) so
the check is "exactly one door is right", not "the door I computed is right".
"""
import json
import math
import random
import re
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "linear-functions"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


# ---------------------------------------------------------------------------------------------
# Golden cases: every catalog key, on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
def disp(ch):
    return ch[0]


# (spec factory, correct display, {label: display or [displays]})
GOLDEN = [
    # T1: (1,4),(2,4),(3,5) is a function with a repeated output
    (lambda: G.s_pairs_fn([(1, 4), (2, 4), (3, 5)]), "Yes", {"REPEAT_OUTPUT": "No"}),
    # outputs 5, 7, 1 are all different: a kid who reads the second number as the input sees no repeat
    (lambda: G.s_pairs_fn([(2, 5), (2, 7), (3, 1)]), "No", {"INPUT_OUTPUT_SWAP": "Yes"}),
    # outputs 5, 7, 5 repeat: the repeated INPUT 2 is the only break
    (lambda: G.s_pairs_fn([(2, 5), (2, 7), (3, 5)]), "No", {"REPEAT_INPUT_OK": "Yes"}),
    # y = 2x + 1, input 3: 7. m(x + b) = 2 * 4 = 8. m + x + b = 6. (3 - 1) / 2 = 1.
    (lambda: G.s_eval(2, 1, 3), "7",
     {"PLUGGED_WRONG": "8", "ADDED_PARTS": "6", "INPUT_OUTPUT_SWAP": "1"}),
    # multiply by 3 then add 2, input 4: 14. Add first: 3 * 6 = 18. 3 + 4 + 2 = 9. Stopped after 3 * 4 = 12.
    (lambda: G.s_rule(3, 2, 4, True), "14",
     {"PLUGGED_WRONG": "18", "ADDED_PARTS": "9", "STOPPED_EARLY": "12"}),
    # subtract 1 then multiply by 2, input 4: (4 - 1) * 2 = 6. Multiplied first: 8 - 1 = 7. 2 + 4 - 1 = 5. Stopped: 3.
    (lambda: G.s_rule(2, -1, 4, False), "6",
     {"PLUGGED_WRONG": "7", "ADDED_PARTS": "5", "STOPPED_EARLY": "3"}),
    # T2: rise 4, run 2
    (lambda: G.s_points(1, 3, 3, 7), "2", {"RUN_OVER_RISE": "1/2", "SIGN_SLIP": "−2", "RISE_ONLY": "4"}),
    # rise -4, run 2
    (lambda: G.s_points(2, 9, 4, 5), "−2", {"RUN_OVER_RISE": "−1/2", "SIGN_SLIP": "2", "RISE_ONLY": "−4"}),
    (lambda: G.s_points(0, 0, 3, 2), "2/3", {"RUN_OVER_RISE": "3/2", "SIGN_SLIP": "−2/3", "RISE_ONLY": "2"}),
    # table 0,1,2 / 5,8,11: rate 3; first y 5; whole-table change 6; sign 3 -> -3
    (lambda: G.s_table_rate([0, 1, 2], [5, 8, 11]), "3",
     {"START_AS_RATE": "5", "TOTAL_CHANGE": "6", "SIGN_SLIP": "−3"}),
    # x steps by 2: y moves 6 per step = 3 per 1 of x. Rise only 6; first y 1; whole table 12.
    (lambda: G.s_table_rate([0, 2, 4], [1, 7, 13]), "3",
     {"RISE_ONLY": "6", "START_AS_RATE": "1", "TOTAL_CHANGE": "12"}),
    # 4 in at week 1, 10 in at week 3: rise 6, run 2 -> 3. Run over rise 2/6 = 1/3.
    (lambda: G.s_words_rate("A plant", "is", "in", "week", 1, 3, 4, 10), "3",
     {"RISE_ONLY": "6", "RUN_OVER_RISE": "1/3", "SIGN_SLIP": "−3", "START_AS_RATE": "4"}),
    (lambda: G.s_ramp("A ramp", "ft", 4, 8), "1/2",
     {"RUN_OVER_RISE": "2", "ADDED_RISE_RUN": "12", "RISE_ONLY": "4"}),
    # T3
    (lambda: G.s_initial(3, 5, False, "Initial value?"), "5", {"SLOPE_AS_START": "3", "VALUE_AT_1": "8"}),
    (lambda: G.s_initial(2, -4, False, "Initial value?"), "−4",
     {"SIGN_DROPPED": "4", "SLOPE_AS_START": "2", "VALUE_AT_1": "−2"}),
    (lambda: G.s_initial(-2, 7, True, "Starting value?"), "7", {"SLOPE_AS_START": ["−2", "2"], "VALUE_AT_1": "5"}),
    (lambda: G.s_slope(-2, 7, False, "Slope of"), "−2", {"START_AS_SLOPE": "7", "SIGN_DROPPED": "2"}),
    (lambda: G.s_slope(4, -3, False, "Slope of"), "4", {"START_AS_SLOPE": ["−3", "3"]}),
    # $10 to start, $5 a week
    (lambda: G.s_word_eq(G.WORD_EQ_CTX[0][0], 1, 10, 5), "y = 5x + 10",
     {"SWAPPED_MB": "y = 10x + 5", "NO_START": "y = 5x"}),
    # tank 9 gal, loses 4 a min
    (lambda: G.s_word_eq(G.WORD_EQ_CTX[5][0], -1, 9, 4), "y = −4x + 9",
     {"SWAPPED_MB": "y = −9x + 4", "SIGN_DROPPED": "y = 4x + 9", "NO_START": "y = −4x"}),
    (lambda: G.s_slope_init(3, -2), "y = 3x − 2",
     {"SWAPPED_MB": "y = −2x + 3", "SIGN_DROPPED": "y = 3x + 2", "NO_START": "y = 3x"}),
    # x 0,1,2 / 3,5,7: y = 2x + 3. Swapped y = 3x + 2. y at 1 is 5. Last y is 7.
    (lambda: G.s_table_eq(0, 2, 3), "y = 2x + 3",
     {"SWAPPED_MB": "y = 3x + 2", "VALUE_AT_1": "y = 2x + 5", "LAST_VALUE": "y = 2x + 7"}),
    # T4: A: d = 4t (4 per hour). B: 9 miles in 3 hours = 3 per hour. A is faster; 9 > 4 lures B.
    (lambda: G.s_cmp_words(G.CMP_CTX[0], 4, 9, 3, True), "A", {"BIGGER_TOTAL": "B", "SAME_NOT_CHECKED": "Same"}),
    # B: 10 miles in 2 hours = 5 per hour beats 4: inverted rates (2/10 < 4) pick A.
    (lambda: G.s_cmp_words(G.CMP_CTX[0], 4, 10, 2, True), "B", {"INVERTED_RATE": "A"}),
    # 8 miles in 2 hours = 4 per hour = d = 4t: a tie
    (lambda: G.s_cmp_words(G.CMP_CTX[0], 4, 8, 2, True), "Same", {"RATE_NOT_COMPARED": ["A", "B"]}),
    (lambda: G.s_cmp_point(4, 2, 6, True), "A", {"BIGGER_TOTAL": "B"}),
    (lambda: G.s_cmp_point(3, 2, 10, False), "A", {"INVERTED_RATE": "B"}),
    (lambda: G.s_cmp_point(3, 2, 6, True), "Same", {"RATE_NOT_COMPARED": ["A", "B"]}),
    (lambda: G.s_cmp_eq((5, 1), (3, 8), True), "A", {"START_NOT_RATE": "B"}),
    (lambda: G.s_cmp_eq_same((4, 1), (4, 7)), "Same", {"START_NOT_RATE": "B", "RATE_NOT_COMPARED": "A"}),
    # T1: 4 goes to 5 and 9; 2 shares its output 5 with 4
    (lambda: G.s_dup_input([(2, 5), (3, 7), (4, 5), (4, 9)]), "4",
     {"REPEAT_OUTPUT": "2", "REPEAT_INPUT_OK": "None"}),
    (lambda: G.s_dup_input([(1, 5), (2, 5), (3, 8), (4, 2)]), "None", {"REPEAT_OUTPUT": ["1", "2"]}),
    (lambda: G.s_unit_rate(4, 12, 0), "3", {"INVERTED_RATE": "1/3", "DIFFERENCE": "8", "TOTAL_AS_RATE": "12"}),
    (lambda: G.s_which_prop(5, 3, -2, 4, "cha"), "y = 5x",
     {"HAS_START": "y = 3x − 2", "ADDS_NOT_MULTIPLIES": "y = x + 4"}),
    (lambda: G.s_table_prop([1, 2, 3], [4, 8, 12]), "Yes", {"NEEDS_ZERO_ROW": "No"}),
    (lambda: G.s_table_prop([1, 2, 3], [3, 5, 7]), "No", {"STEADY_MEANS_PROP": "Yes"}),
    # T5
    (lambda: G.s_which_lin("not", [(2, 1, False), (-1, 7, True)], [("sq", 0)], (0, 1, 2)),
     "y = x^2", {"CONSTANT_NOT_LINEAR": "y = 2x + 1", "MINUS_NOT_LINEAR": "y = 7 − x"}),
    (lambda: G.s_which_lin("is", [(-4, -6, False)], [("sq", 0), ("ex", 0)], (1, 0, 2)),
     "y = −4x − 6", {"EXPONENT_IGNORED": ["y = x^2", "y = 2^x"]}),
    (lambda: G.s_eq_linear("y = 4 − 3x", True, True), "Yes", {"MINUS_NOT_LINEAR": "No"}),
    (lambda: G.s_eq_linear("y = 3x + 4", True, False), "Yes", {"CONSTANT_NOT_LINEAR": "No"}),
    (lambda: G.s_eq_linear("y = x^2 + 3", False, False), "No", {"EXPONENT_IGNORED": "Yes"}),
    (lambda: G.s_direction(-3, 2, False), "Decreases",
     {"CONSTANT_SIGN_DECIDES": "Increases", "CONSTANT_RATE_MEANS_SAME": "Stays same"}),
    (lambda: G.s_direction(3, -2, False), "Increases", {"CONSTANT_SIGN_DECIDES": "Decreases"}),
    (lambda: G.s_direction(2, 5, False), "Increases", {"SLOPE_SIGN_IGNORED": "Decreases"}),
    (lambda: G.s_direction(0, 4, False), "Stays same", {"SLOPE_SIGN_IGNORED": ["Increases", "Decreases"]}),
    (lambda: G.s_table_linear([1, 2, 3], [2, 4, 8]), "No", {"LOOKS_GROWING": "Yes"}),
    (lambda: G.s_table_linear([1, 2, 4], [3, 5, 9]), "Yes", {"EQUAL_STEPS_MISSED": "No"}),
    (lambda: G.s_table_linear([1, 2, 3], [9, 7, 5]), "Yes", {"DECREASING_NOT_LINEAR": "No"}),
    (lambda: G.s_cmp_fn((2, 1), ([0, 1, 2], [3, 6, 9]), True, "B", "START_NOT_RATE"), "B",
     {"START_NOT_RATE": "A", "SAME_NOT_CHECKED": "Same"}),
    # both rise 2 per step; the table starts higher (4 > 1), so B lures the bigger-start kid
    (lambda: G.s_cmp_fn((2, 1), ([0, 1, 2], [4, 6, 8]), True, "Same", "START_NOT_RATE"), "Same",
     {"START_NOT_RATE": "B", "RATE_NOT_COMPARED": "A"}),
]


def test_prompts_list_the_choices():
    sp = G.s_which_lin("not", [(2, 1, False), (-1, 7, True)], [("sq", 0)], (1, 0, 2))
    assert sp.prompt == "Which is NOT linear: y = 2x + 1, y = x^2, y = 7 − x?"
    sp = G.s_which_prop(5, 3, -2, 4, "cha")
    assert sp.prompt == "Which is proportional: y = 5x, y = 3x − 2, y = x + 4?"
    assert G.s_dup_input([(2, 5), (3, 7), (4, 5), (4, 9)]).prompt == \
        "Which input has two outputs: (2, 5), (3, 7), (4, 5), (4, 9)?"


@pytest.mark.parametrize("make,correct,wrong", GOLDEN, ids=[str(i) for i in range(len(GOLDEN))])
def test_golden_misconception_values(make, correct, wrong):
    sp = make()
    assert disp(sp.correct) == correct, (sp.prompt, sp.correct)
    got = {}
    for lab, ch in sp.wrong:
        got.setdefault(lab, set()).add(disp(ch))
    for lab, d in wrong.items():
        for one in ([d] if isinstance(d, str) else d):
            assert one in got.get(lab, set()), (sp.prompt, lab, one, got)


def test_golden_covers_every_catalog_key():
    used = set()
    for make, _, wrong in GOLDEN:
        used |= set(wrong)
    assert used == set(BAKED["misconceptions"]), used ^ set(BAKED["misconceptions"])


def test_golden_hand_prompts():
    """The prompts themselves, worked by hand."""
    assert G.s_points(2, 9, 4, 5).prompt == "Slope through (2, 9) and (4, 5)?"
    assert G.s_points(-1, 4, -3, 10).prompt == "Slope through (−1, 4) and (−3, 10)?"
    assert G.s_table_eq(0, 2, 3).prompt == "x: 0, 1, 2. y: 3, 5, 7. Equation?"
    assert G.s_rule(2, -1, 4, False).prompt == "Rule: subtract 1, then multiply by 2. Input 4. Output?"
    assert G.eq_text(-1, 4) == "y = −x + 4" and G.eq_bfirst(-3, 7) == "y = 7 − 3x"
    assert G.eq_text(3, -4) == "y = 3x − 4"


# ---------------------------------------------------------------------------------------------
# Independent evaluator for equation text (never the generator's keys)
# ---------------------------------------------------------------------------------------------
def eqfn(text):
    """f(X) for 'y = ...' text over one variable (any letter), ints in, Fraction out."""
    rhs = text.split(" = ", 1)[1].replace("−", "-")
    rhs = re.sub(r"[a-z]", "X", rhs)
    rhs = re.sub(r"X\^(\d)", r"(X**\1)", rhs)
    rhs = re.sub(r"(\d)\^X", r"(\1**X)", rhs)
    rhs = re.sub(r"(\d)X", r"\1*X", rhs)
    assert re.fullmatch(r"[0-9X+\-*() ]+", rhs), rhs
    return lambda X: Fraction(eval(rhs, {"__builtins__": {}}, {"X": X}))


def coef(text):
    f = eqfn(text)
    return f(0), f(1) - f(0)  # (b, m)


def is_linear(text):
    f = eqfn(text)
    return len({f(i + 1) - f(i) for i in range(4)}) == 1


def num(s):
    return Fraction(s.replace("−", "-"))


def nums(s):
    return [num(t) for t in re.findall(r"−?\d+", s)]


def pairs_of(s):
    return [(int(a), int(b)) for a, b in re.findall(r"\((\d+), (\d+)\)", s)]


def is_function(ps):
    xs = [a for a, _ in set(ps)]
    return len(xs) == len(set(xs))


def val(c):
    """Value key of any choice, computed independently of the generator."""
    s = c.replace("−", "-")
    if re.fullmatch(r"-?\d+(?:/\d+)?", s):
        return ("n", Fraction(s))
    if re.fullmatch(r"[a-z] = .+", s):
        f = eqfn(c)
        return ("eq", tuple(f(i) for i in range(5)))
    if s.startswith("("):
        return ("set", frozenset(pairs_of(c)))
    return ("txt", c)


def fits(c, pts):
    f = eqfn(c)
    return all(f(int(x)) == y for x, y in pts)


# ---------------------------------------------------------------------------------------------
# Bounds (the manifest's `bounds`, walked on the prompt text)
# ---------------------------------------------------------------------------------------------
def slope_bad(rise, run):
    bad = []
    if abs(rise) > 10 or abs(run) > 10 or abs(run) < 2:
        bad.append(f"rise {rise} / run {run} outside size 10 (run >= 2)")
        return bad
    s = Fraction(rise, run)
    if s.denominator == 1:
        if not 2 <= abs(s) <= 10:
            bad.append(f"integer slope {s}")
    elif abs(s.numerator) > 5 or s.denominator > 5 or abs(s) == 1:
        bad.append(f"fraction slope {s}")
    return bad


def mb_bad(m, b, lo=1):
    bad = []
    if not (lo <= abs(m) <= 10 and 1 <= abs(b) <= 10):
        bad.append(f"m = {m}, b = {b} outside bounds")
    return bad


def tbl_bad(vals, lim=20):
    return [f"table value {v}" for v in vals if abs(v) > lim]


EQ_RE = r"(y = [^.]+?)"


def solve(prompt, choices):  # noqa: C901 -- one branch per template
    """-> (right(choice) -> bool, bound violations, {label: {values}} for cross-checks)."""
    p = prompt.replace("−", "-")
    # ================= T1
    m = re.match(r"^Pairs (.+)\. Is it a function\?$", p)
    if m:
        ps = pairs_of(m[1])
        bad = [] if 3 <= len(set(ps)) <= 4 and all(0 <= a <= 9 and 0 <= b <= 9 for a, b in ps) else ["pairs"]
        return (lambda c, f=is_function(ps): c == ("Yes" if f else "No")), bad, {}
    if re.search(r"(NOT a function|is a function|IS a function|set of pairs is a function|Pick the set that is a function)", p):
        want_fn = "NOT" not in p
        ok = [(c, is_function(pairs_of(c))) for c in choices]
        bad = [] if all(len(pairs_of(c)) == 2 and all(0 <= v <= 9 for ab in pairs_of(c) for v in ab) for c in choices) else ["set"]
        return (lambda c, w=want_fn: any(c == cc and f == w for cc, f in ok)), bad, {}
    m = re.match(r"^(y = .+)\. (?:Input (\d+)\. Output|If x = (\d+), what is y)\?$", p)
    if m:
        x = int(m[2] or m[3])
        b, mm = coef(m[1])
        out = mm * x + b
        bad = mb_bad(mm, b)
        if not (2 <= mm <= 5 and 1 <= x <= 6 and 1 <= out <= 20):
            bad.append(f"eval {mm} {x} {b} -> {out}")
        wrong = {"PLUGGED_WRONG": {mm * (x + b)}, "ADDED_PARTS": {mm + x + b}}
        if (x - b) % mm == 0:
            wrong["INPUT_OUTPUT_SWAP"] = {Fraction(x - b) / mm}
        return (lambda c, o=out: num(c) == o), bad, wrong
    m = re.match(r"^Rule: (?:multiply by (\d+), then (add|subtract) (\d+)|(add|subtract) (\d+), then multiply by (\d+))"
                 r"\. Input (\d+)\. Output\?$", p)
    if m:
        x = int(m[7])
        if m[1]:
            mm, b = int(m[1]), int(m[3]) * (1 if m[2] == "add" else -1)
            out = mm * x + b
        else:
            mm, b = int(m[6]), int(m[5]) * (1 if m[4] == "add" else -1)
            out = (x + b) * mm
        bad = [] if (2 <= mm <= 5 and 1 <= x <= 5 and 1 <= out <= 20 and 1 <= abs(b) <= 9) else [f"rule {out}"]
        return (lambda c, o=out: num(c) == o), bad, {}
    m = re.match(r"^Input: (.+)\. Output: (.+)\. Function\?$", p)
    if m:
        yes = {"their birth month", "their grade level", "its page count", "its state", "its price",
               "their math teacher"}
        no = {"a city in it", "a parent of theirs", "a class they take", "a player on it", "an item it sells",
              "an actor in it", "a number bigger than it"}
        assert m[2] in yes | no, m[2]
        return (lambda c, y=m[2] in yes: c == ("Yes" if y else "No")), [], {}
    m = re.match(r"^Which input has two outputs: (.+)\?$", p)
    if m:
        ps = pairs_of(m[1])
        outs = {}
        for a, b in set(ps):
            outs.setdefault(a, set()).add(b)
        dups = [a for a, s in outs.items() if len(s) > 1]
        assert len(dups) <= 1
        want = str(dups[0]) if dups else "None"
        bad = [] if (len(set(ps)) == 4 and all(0 <= v <= 9 for ab in ps for v in ab)) else ["pairs"]
        return (lambda c, w=want: c == w), bad, {}
    # ================= T2
    m = re.match(r"^Slope through \((-?\d+), (-?\d+)\) and \((-?\d+), (-?\d+)\)\?$", p)
    if m:
        x1, y1, x2, y2 = map(int, m.groups())
        bad = slope_bad(y2 - y1, x2 - x1) + ([] if max(map(abs, (x1, y1, x2, y2))) <= 10 else ["coordinate"])
        s = Fraction(y2 - y1, x2 - x1)
        wrong = {"RUN_OVER_RISE": {Fraction(x2 - x1, y2 - y1)}, "SIGN_SLIP": {-s}, "RISE_ONLY": {Fraction(y2 - y1)}}
        return (lambda c, s=s: num(c) == s), bad, wrong
    m = re.match(r"^x: ([-\d, ]+)\. y: ([-\d, ]+)\. Rate of change\?$", p)
    if m:
        xs, ys = [int(t) for t in m[1].split(", ")], [int(t) for t in m[2].split(", ")]
        s = Fraction(ys[1] - ys[0], xs[1] - xs[0])
        steady = Fraction(ys[2] - ys[1], xs[2] - xs[1]) == s
        bad = tbl_bad(xs + ys) + ([] if len(xs) == 3 and steady and s.denominator == 1 and 2 <= abs(s) <= 10 else ["rate"])
        wrong = {"START_AS_RATE": {Fraction(ys[0])}, "TOTAL_CHANGE": {Fraction(ys[2] - ys[0])}, "SIGN_SLIP": {-s}}
        return (lambda c, s=s: num(c) == s), bad, wrong
    m = re.match(r"^[A-Za-z ]+: (\d+) (\w+) at (\w+) (\d+), (\d+) at \3 (\d+)\. Change per \3\?$", p)
    if m:
        v0, v1, t0, t1 = int(m[1]), int(m[5]), int(m[4]), int(m[6])
        s = Fraction(v1 - v0, t1 - t0)
        bad = tbl_bad([v0, v1, t0, t1]) + ([] if (t1 - t0 >= 2 and s.denominator == 1 and 2 <= abs(s) <= 10) else ["rate"])
        wrong = {"RISE_ONLY": {Fraction(v1 - v0)}, "RUN_OVER_RISE": {Fraction(t1 - t0, v1 - v0)}, "SIGN_SLIP": {-s},
                 "START_AS_RATE": {Fraction(v0)}}
        return (lambda c, s=s: num(c) == s), bad, wrong
    m = re.match(r"^(?:A \w+|Stairs) rises? (\d+) (\w+) over a run of (\d+) \2\. Slope\?$", p)
    if m:
        rise, run = int(m[1]), int(m[3])
        s = Fraction(rise, run)
        bad = slope_bad(rise, run)
        wrong = {"RUN_OVER_RISE": {Fraction(run, rise)}, "ADDED_RISE_RUN": {Fraction(rise + run)},
                 "RISE_ONLY": {Fraction(rise)}}
        return (lambda c, s=s: num(c) == s), bad, wrong
    # ================= T3
    m = re.match(r"^(y = .+)\. (?:Initial value|Starting value|Value of y when x = 0)\?$", p)
    if m:
        b, mm = coef(m[1])
        wrong = {"SLOPE_AS_START": {mm, abs(mm)}, "VALUE_AT_1": {mm + b}, "SIGN_DROPPED": {abs(b)}}
        return (lambda c, b=b: num(c) == b), mb_bad(mm, b), wrong
    m = re.match(r"^(?:Slope of|Rate of change of) (y = .+)\?$", p)
    if m:
        b, mm = coef(m[1])
        wrong = {"START_AS_SLOPE": {b, abs(b)}, "SIGN_DROPPED": {abs(mm)}}
        return (lambda c, mm=mm: num(c) == mm), mb_bad(mm, b), wrong
    m = re.match(r"^Slope (-?\d+), initial value (-?\d+)\. Equation\?$", p)
    if m:
        mm, b = int(m[1]), int(m[2])
        return (lambda c, mm=mm, b=b: coef(c) == (b, mm)), mb_bad(mm, b), {}
    m = re.match(r"^x: ([-\d, ]+)\. y: ([-\d, ]+)\. Equation\?$", p)
    if m:
        xs, ys = [int(t) for t in m[1].split(", ")], [int(t) for t in m[2].split(", ")]
        mm = Fraction(ys[1] - ys[0], xs[1] - xs[0])
        b = ys[0] - mm * xs[0]
        bad = tbl_bad(xs + ys) + mb_bad(mm, b)
        return (lambda c, pts=list(zip(xs, ys)): fits(c, pts)), bad, {}
    if re.search(r"(Total|Cost|Gallons|Height|Money) y (after|for) x", p):
        ints = [int(t) for t in re.findall(r"\d+", p)]
        b, mm = ints[0], ints[1]
        sign = -1 if re.search(r"loses|burns|Spend", p) else 1
        bad = [] if (2 <= b <= 10 and 2 <= mm <= 9) else [f"word eq {b} {mm}"]
        return (lambda c, b=b, mm=mm, s=sign: coef(c) == (b, s * mm)), bad, {}
    # ================= T4
    m = re.match(r"^A: (.+?)\. B: (.+)\. (Which is faster|Steeper|Which grows faster|Greater rate)\?$", p)
    if m:
        kind = m[3]
        rates, bad = [], []
        for side in (m[1], m[2]):
            mm = re.match(r"^\w = (\d+)\w$", side)
            if mm:
                rates.append(Fraction(int(mm[1])))
                bad += [] if 2 <= int(mm[1]) <= 9 else ["k"]
                continue
            mm = re.match(r"^(\d+) \w+ in (\d+) \w+$", side)
            if mm:
                tot, h = int(mm[1]), int(mm[2])
                rates.append(Fraction(tot, h))
                bad += [] if (2 <= h <= 5 and tot % h == 0 and 2 <= tot // h <= 9 and tot <= 45) else ["words"]
                continue
            mm = re.match(r"^line through \(0, 0\) and \((\d+), (\d+)\)$", side)
            if mm:
                x, y = int(mm[1]), int(mm[2])
                rates.append(Fraction(y, x))
                bad += [] if (2 <= x <= 5 and y % x == 0 and 2 <= y // x <= 5 and y <= 10) else ["point"]
                continue
            mm = re.match(r"^x: ([\d, ]+); y: ([\d, ]+)$", side)
            if mm:
                xs, ys = [int(t) for t in mm[1].split(", ")], [int(t) for t in mm[2].split(", ")]
                assert xs == [0, 1, 2]
                rates.append(Fraction(ys[1] - ys[0], 1))
                bad += tbl_bad(xs + ys) + ([] if ys[1] - ys[0] == ys[2] - ys[1] else ["not steady"])
                continue
            mm = re.match(r"^y = .+$", side)
            assert mm, side
            b, s = coef(side)
            rates.append(s)
            bad += mb_bad(s, b, lo=2) if b != 0 else ([] if 2 <= s <= 9 else ["k"])
        right = "Same" if rates[0] == rates[1] else ("A" if rates[0] > rates[1] else "B")
        return (lambda c, r=right: c == r), bad, {}
    m = re.match(r"^(?:A line through \(0, 0\) and \((\d+), (\d+)\)|y = kx, and \((\d+), (\d+)\) is on it)\. Unit rate\?$", p)
    if m:
        x, y = int(m[1] or m[3]), int(m[2] or m[4])
        k = Fraction(y, x)
        bad = [] if (2 <= x <= 5 and k.denominator == 1 and 2 <= k <= 5 and x * k <= 10) else ["unit rate"]
        wrong = {"INVERTED_RATE": {Fraction(x, y)}, "DIFFERENCE": {Fraction(y - x)}, "TOTAL_AS_RATE": {Fraction(y)}}
        return (lambda c, k=k: num(c) == k), bad, wrong
    m = re.match(r"^Which is proportional: (.+)\?$", p)
    if m:
        assert sorted(re.split(r", (?=y = )", m[1])) == sorted(c.replace("−", "-") for c in choices) or not choices  # the prompt lists the choices

        def prop(c):
            f = eqfn(c)
            return f(0) == 0 and is_linear(c) and f(1) > 0
        bad = []
        for c in choices:
            b, s = coef(c)
            bad += [] if (abs(b) <= 9 and 1 <= s <= 9) else ["eq"]
        return prop, bad, {}
    m = re.match(r"^x: ([\d, ]+)\. y: ([\d, ]+)\. Proportional\?$", p)
    if m:
        xs, ys = [int(t) for t in m[1].split(", ")], [int(t) for t in m[2].split(", ")]
        ks = {Fraction(y, x) for x, y in zip(xs, ys) if x != 0}
        prop = len(ks) == 1 and all(y == 0 for x, y in zip(xs, ys) if x == 0) and len(ks) > 0
        bad = tbl_bad(xs + ys) + ([] if len(xs) == 3 else ["rows"])
        return (lambda c, pr=prop: c == ("Yes" if pr else "No")), bad, {}
    # ================= T5
    m = re.match(r"^Which is (NOT )?linear: (.+)\?$", p)
    if m:
        want_lin = not m[1]
        assert sorted(re.split(r", (?=y = )", m[2])) == sorted(c.replace("−", "-") for c in choices) or not choices  # the prompt lists the choices
        bad = []
        for c in choices:
            if "^" not in c:
                b, s = coef(c)
                bad += [] if (abs(s) <= 6 and 1 <= abs(b) <= 8) else ["lin"]
        return (lambda c, w=want_lin: is_linear(c) == w), bad, {}
    m = re.match(r"^Is (.+) linear\?$", p)
    if m:
        lin = is_linear(m[1])
        return (lambda c, lin=lin: c == ("Yes" if lin else "No")), [], {}
    m = re.match(r"^(y = .+)\. As x grows, y\?$", p)
    if m:
        f = eqfn(m[1])
        d = f(1) - f(0)
        want = "Increases" if d > 0 else ("Decreases" if d < 0 else "Stays same")
        b, s = coef(m[1])
        bad = [] if (abs(s) <= 5 and 1 <= abs(b) <= 9) else ["dir"]
        return (lambda c, w=want: c == w), bad, {}
    m = re.match(r"^x: ([\d, ]+)\. y: ([\d, ]+)\. Linear\?$", p)
    if m:
        xs, ys = [int(t) for t in m[1].split(", ")], [int(t) for t in m[2].split(", ")]
        lin = Fraction(ys[1] - ys[0], xs[1] - xs[0]) == Fraction(ys[2] - ys[1], xs[2] - xs[1])
        return (lambda c, lin=lin: c == ("Yes" if lin else "No")), tbl_bad(xs + ys), {}
    raise AssertionError(f"no independent solver for {prompt!r}")


# ---------------------------------------------------------------------------------------------
# The tests over baked.json
# ---------------------------------------------------------------------------------------------
def test_baked_has_200_items_and_valid_shape():
    assert len(ITEMS) == 200 and BAKED["items_per_tier"] == 40 and BAKED["grade"] == "8"
    assert [t["tier"] for t in BAKED["tiers"]] == [1, 2, 3, 4, 5]
    assert all(s.startswith("CCSS.MATH.CONTENT.8.") for s in BAKED["standards"])
    assert "bounds" in BAKED and len(BAKED["bounds"]) > 100


@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_every_baked_answer_is_right_and_alone(it):
    right, bad, wrong = solve(it["prompt"], it["choices"])
    flags = [bool(right(c)) for c in it["choices"]]
    assert flags.count(True) == 1, (it["prompt"], it["choices"], flags)
    assert flags.index(True) == it["answer"], (it["prompt"], it["choices"], it["answer"])
    assert it["misconceptions"][it["answer"]] is None


@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value(it):
    vals = [val(c) for c in it["choices"]]
    assert len(set(vals)) == len(vals), (it["prompt"], it["choices"])
    assert 2 <= len(it["choices"]) <= 4


@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_every_baked_item_meets_the_bounds(it):
    _, bad, _ = solve(it["prompt"], it["choices"])
    assert bad == [], (it["prompt"], bad)


def test_labelled_wrong_choices_match_the_hand_formulas():
    """Where the solver names a label's value(s), every baked wrong choice carrying that label holds one."""
    checked = 0
    for it in ITEMS:
        _, _, wrong = solve(it["prompt"], it["choices"])
        for c, lab in zip(it["choices"], it["misconceptions"]):
            if lab in wrong and isinstance(wrong[lab], set):
                assert num(c) in wrong[lab], (it["prompt"], lab, c, wrong[lab])
                checked += 1
    assert checked > 150


def test_two_choice_items_are_capped():
    """A guessing kid wins half of the Yes/No items: at most 12 of 40 per tier (lead audit, 2026-10-14)."""
    for t in range(1, 6):
        n2 = [it for it in ITEMS if it["tier"] == t and len(it["choices"]) == 2]
        assert len(n2) <= 12, (t, len(n2))
    for it in ITEMS:
        if len(it["choices"]) == 2:
            assert sorted(it["choices"]) == ["No", "Yes"], it["choices"]


def test_compare_items_have_a_same_door_that_is_sometimes_right():
    cmp_items = [it for it in ITEMS if "Same" in it["choices"]]
    assert len(cmp_items) == 22
    right = [it for it in cmp_items if it["choices"][it["answer"]] == "Same"]
    assert 4 <= len(right) <= len(cmp_items) // 2, len(right)
    for it in cmp_items:
        assert sorted(it["choices"]) == ["A", "B", "Same"]


def test_catalog_labels_are_declared_and_used():
    cat = set(BAKED["misconceptions"]) | {"ARITH"}
    used = {lab for it in ITEMS for lab in it["misconceptions"] if lab}
    assert used <= cat
    assert set(BAKED["misconceptions"]) - used == set(), set(BAKED["misconceptions"]) - used


def test_arith_is_a_minority():
    arith = sum(1 for it in ITEMS for lab in it["misconceptions"] if lab == "ARITH")
    wrongs = sum(len(it["choices"]) - 1 for it in ITEMS)
    assert arith / wrongs < 0.12, (arith, wrongs)


def test_generation_is_deterministic():
    again = G.generate(BAKED, random.Random(BAKED["seed"]))
    assert len(again) == 200
    assert [i["prompt"] for i in again] == [i["prompt"] for i in ITEMS]
    assert [i["choices"] for i in again] == [i["choices"] for i in ITEMS]


def test_prompts_unique_per_tier_and_short():
    for t in range(1, 6):
        ps = [it["prompt"] for it in ITEMS if it["tier"] == t]
        assert len(ps) == len(set(ps)) == 40
    assert max(len(it["prompt"]) for it in ITEMS) <= 60
    assert max(len(c) for it in ITEMS for c in it["choices"]) <= 14


# ---------------------------------------------------------------------------------------------
# Disproof: the checkers can fail
# ---------------------------------------------------------------------------------------------
def test_bounds_checker_rejects_planted_bad_prompts():
    planted = [
        ("Slope through (1, 3) and (13, 9)?", []),            # coordinate 13
        ("Slope through (0, 0) and (7, 6)?", []),             # 6/7 has a part over 5
        ("Slope through (0, 0) and (1, 4)?", []),             # run 1
        ("Slope through (0, 0) and (6, 6)?", []),             # slope 1
        ("x: 0, 1, 2. y: 5, 25, 45. Rate of change?", []),    # table value 25 and rate 20
        ("y = 12x + 3. Initial value?", []),                  # m = 12
        ("y = 3x + 11. Starting value?", []),                 # b = 11
        ("Slope 3, initial value 12. Equation?", []),         # b = 12
        ("A line through (0, 0) and (3, 18). Unit rate?", []),  # k = 6, y = 18
    ]
    for prompt, choices in planted:
        _, bad, _ = solve(prompt, choices)
        assert bad, f"checker accepted {prompt!r}"


def test_solver_rejects_a_planted_wrong_answer():
    right, _, _ = solve("Slope through (1, 3) and (3, 7)?", [])
    assert right("2") and not right("4") and not right("−2") and not right("1/2")
    right, _, _ = solve("Pairs (1, 4), (2, 4), (3, 5). Is it a function?", [])
    assert right("Yes") and not right("No")
    right, _, _ = solve("Is y = x^2 + 3 linear?", [])
    assert right("No") and not right("Yes")


def test_value_comparison_sees_equal_values():
    assert val("y = 2x + 4") == val("y = 4 + 2x")
    assert val("y = 7 − 2x") == val("y = −2x + 7")
    assert val("y = 5x") != val("y = 5x + 1")
    assert val("(1, 4), (2, 5)") == val("(2, 5), (1, 4)")
    assert val("2/4") == val("1/2")  # equal in value, so a non-simplest choice would be caught as a duplicate
    assert not any(re.fullmatch(r"\d+/\d+", c) and math.gcd(*map(int, c.split("/"))) != 1
                   for it in ITEMS for c in it["choices"])


def test_which_input_items_are_not_a_none_tell():
    """Lead audit: `None` right on at most 3 of the 'Which input has two outputs' items, and at most one ARITH door each."""
    its = [it for it in ITEMS if it["prompt"].startswith("Which input has two outputs")]
    assert len(its) == 7
    assert sum(1 for it in its if it["choices"][it["answer"]] == "None") <= 3
    for it in its:
        assert sum(1 for lab in it["misconceptions"] if lab == "ARITH") <= 1, it["choices"]
