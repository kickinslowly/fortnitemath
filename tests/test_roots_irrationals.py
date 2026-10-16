"""roots-irrationals cartridge: golden misconception cases, an independent re-check of every baked item
(prompt parsed here with regexes and answered with ``fractions.Fraction`` / ``math.isqrt`` / floats, never by the
generator's solver), a bounds test over ``baked.json``, value-uniqueness of choices, and a checker self-test."""
import itertools
import json
import math
import re
from collections import Counter
from fractions import Fraction
from math import isqrt

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "roots-irrationals"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
with open(REPO_ROOT / "cartridges" / CID / "cartridge.json", encoding="utf-8") as _f:
    MANIFEST = json.load(_f)
ITEMS = BAKED["items"]
M = "−"
R = "√"
PI = "π"


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def ids(items):
    return [it["id"] for it in items]


# ----------------------------------------------------------------------------------------------
# Independent number parsing (written here, not the generator's)
# ----------------------------------------------------------------------------------------------
def rep_value(intpart: int, digits: str) -> Fraction:
    """Value of intpart.digits... where the digits hold a recognised repeating pattern."""
    if len(set(digits)) == 1 and len(digits) >= 3:  # 0.777...
        a, b, whole = 0, 1, digits[:1]
    elif len(digits) == 4 and digits[:2] == digits[2:] and digits[0] != digits[1]:  # 0.1818...
        a, b, whole = 0, 2, digits[:2]
    elif len(digits) == 4 and digits[1] == digits[2] == digits[3] and digits[0] != digits[1]:  # 0.1666...
        a, b, whole = 1, 1, digits[:2]
    else:
        raise ValueError(f"not a recognised repeating pattern: {digits}")
    pre = digits[:a]
    block = digits[a:a + b]
    pre_v = int(pre) if pre else 0
    tail = Fraction(int(pre + block) - pre_v, 10 ** a * (10 ** b - 1))
    return intpart + tail


def parse_num(text: str):
    """Fraction | frozenset of Fractions ('5 or −5') | ('sqrt', n) | ('pi',) | None."""
    t = text.replace(M, "-")
    if " or " in t:
        return frozenset(Fraction(p) for p in t.split(" or "))
    m = re.fullmatch(r"(\d+)\.(\d+)\.\.\.", t)
    if m:
        return rep_value(int(m.group(1)), m.group(2))
    if re.fullmatch(r"-?\d+(\.\d+)?", t) or re.fullmatch(r"-?\d+/\d+", t):
        return Fraction(t)
    m = re.fullmatch(R + r"(\d+)", t)
    if m:
        n = int(m.group(1))
        return Fraction(isqrt(n)) if isqrt(n) ** 2 == n else ("sqrt", n)
    if t == PI:
        return ("pi",)
    return None


def fval(token: str) -> float:
    """Float value of a token used in tier-5 prompts and choices."""
    t = token.strip()
    if t == PI:
        return math.pi
    m = re.fullmatch(R + r"(\d+)", t)
    if m:
        return math.sqrt(int(m.group(1)))
    return float(t.replace(M, "-"))


def face(token: str) -> float:
    t = token.strip()
    if t == PI:
        return 3.14
    m = re.fullmatch(R + r"(\d+)", t)
    return float(m.group(1)) if m else float(t)


# ----------------------------------------------------------------------------------------------
# Golden cases: a hand-worked prompt per misconception key -> the wrong value that key yields
# ----------------------------------------------------------------------------------------------
def _find(forms, prompt):
    for probs in forms.values():
        for p in probs:
            if p.prompt == prompt:
                return p
    raise KeyError(prompt)


def wrong_by_key(p):
    d = {}
    for text, _vk, key in p.wrongs:
        d.setdefault(key, text)
    return d


T1_FORMS, _ = G.t1_problems()
T3_FORMS, _ = G.t3_problems()
T4_FORMS, _ = G.t4_problems()

GOLDEN = [
    (T1_FORMS, f"{R}49 = ?", {"HALVED": "24.5", "DOUBLED": "14", "NOT_ROOTED": "49"}),
    (T1_FORMS, "Cube root of 27?", {"THIRD_FOR_CUBE": "9", "TRIPLED": "9", "HALVED": "13.5", "NOT_ROOTED": "27"}),
    (T1_FORMS, "Cube root of 64?", {"SQUARE_ROOT_FOR_CUBE": "8", "TRIPLED": "12", "HALVED": "32"}),
    (T1_FORMS, "A square has area 36. Side?", {"AREA_OVER_4": "9", "PERIMETER_FOR_SIDE": "24", "HALVED": "18"}),
    (T1_FORMS, "x^2 = 25 and x < 0. x?", {"POSITIVE_ONLY": "5", "HALVED": f"{M}12.5", "NOT_ROOTED": f"{M}25"}),
    (T1_FORMS, "All solutions of x^2 = 25?", {"POSITIVE_ONLY": "5", "HALVED": f"12.5 or {M}12.5",
                                              "NOT_ROOTED": f"25 or {M}25"}),
    (T3_FORMS, "0.666... as a fraction?", {"OVER_TEN": "3/5", "ROUNDED_UP": "7/10"}),
    (T3_FORMS, "0.1818... as a fraction?", {"OVER_HUNDRED": "9/50", "NINTHS_ONLY": "2/9"}),
    (T3_FORMS, "0.1666... as a fraction?", {"OVER_HUNDRED": "4/25", "ROUNDED_UP": "17/100"}),
    (T3_FORMS, "0.4 as a fraction?", {"NINE_FOR_TERMINATING": "4/9", "DIGIT_AS_DENOM": "1/4",
                                      "PLACE_VALUE_SLIP": "1/25"}),
    (T3_FORMS, "0.25 as a fraction?", {"NINE_FOR_TERMINATING": "25/99", "DIGIT_AS_DENOM": "1/25",
                                       "PLACE_VALUE_SLIP": "5/2"}),
    (T3_FORMS, f"x = 0.444... Then 10x {M} x = ?", {"TIMES_ONLY": "4.444...", "NINES_ONLY": "9",
                                                    "TRUNCATED_REPEAT": "3.6", "DECIMAL_SLIP": "0.4"}),
    (T3_FORMS, f"x = 0.1818... Then 100x {M} x = ?", {"TIMES_ONLY": "18.1818...", "NINES_ONLY": "99",
                                                      "TRUNCATED_REPEAT": "17.82", "DECIMAL_SLIP": "0.18"}),
    (T4_FORMS, f"{R}20 is between which two whole numbers?",
     {"SQUARES_NOT_ROOTS": "16 and 25", "HALVED": "10 and 11", "NEXT_SQUARE_DOWN": "3 and 4",
      "NEXT_SQUARE_UP": "5 and 6"}),
    (T4_FORMS, f"Nearest whole number to {R}50?", {"HALVED": "25", "NEAREST_SQUARE_NOT_ROOT": "49",
                                                   "ROUNDED_WRONG": "8"}),
    (T4_FORMS, f"{R}30 is about?", {"HALVED": "15", "NEAREST_SQUARE_NOT_ROOT": "25"}),
]


@pytest.mark.parametrize("forms,prompt,expected", GOLDEN, ids=[g[1] for g in GOLDEN])
def test_golden_wrong_values(forms, prompt, expected):
    got = wrong_by_key(_find(forms, prompt))
    for key, text in expected.items():
        assert got[key] == text, (key, got)


def test_golden_tier2_word_keys():
    # the word choices carry their key, and the wrong word is the false one
    cases = [(f"{R}36 is?", "Irrational", "ROOT_IS_IRRATIONAL"), (f"{R}7 is?", "Rational", "ROOT_IS_RATIONAL"),
             (f"{PI} is?", "Rational", "PI_IS_RATIONAL"), ("0.333... is?", "Irrational", "REPEAT_IS_IRRATIONAL"),
             ("2/3 is?", "Irrational", "NONWHOLE_IS_IRRATIONAL")]
    forms, _, _ = G.t2_problems()
    for prompt, wrong, key in cases:
        p = _find(forms, prompt)
        assert [(w[0], w[2]) for w in p.wrongs] == [(wrong, key)], prompt


def test_golden_tier5_compare_keys():
    r, o = G._item_root(50), G._item_half(15)
    p = G.make_compare(r, o, "Greater")
    assert p.prompt == f"Greater: {R}50 or 7.5?" and p.right[0] == "7.5"
    assert p.wrongs[0][0] == f"{R}50" and p.wrongs[0][2] == "RADICAND_AS_VALUE"
    p = G.make_compare(G._item_root(75), G._item_int(6), "Greater")  # root is larger; the small-root habit errs
    assert p.right[0] == f"{R}75" and p.wrongs[0][2] == "ROOT_ALWAYS_SMALL"
    # √3 vs 4: radicand 3 < 4, so the habit does not explain a wrong pick: no problem is made
    assert G.make_compare(G._item_root(3), G._item_int(4), "Greater") is None


# ----------------------------------------------------------------------------------------------
# Independent answers
# ----------------------------------------------------------------------------------------------
def t1_truth(prompt):
    """-> (form, N, correct choice text)"""
    m = re.fullmatch(R + r"(\d+) = \?", prompt)
    if m:
        N = int(m.group(1)); s = isqrt(N); assert s * s == N
        return "root", N, str(s)
    m = re.fullmatch(r"x\^2 = (\d+) and x ([<>]) 0\. x\?", prompt)
    if m:
        N = int(m.group(1)); s = isqrt(N); assert s * s == N
        return ("xpos", N, str(s)) if m.group(2) == ">" else ("xneg", N, M + str(s))
    m = re.fullmatch(r"A square has area (\d+)\. Side\?", prompt)
    if m:
        N = int(m.group(1)); s = isqrt(N); assert s * s == N
        return "area", N, str(s)
    m = re.fullmatch(r"All solutions of x\^2 = (\d+)\?", prompt)
    if m:
        N = int(m.group(1)); s = isqrt(N); assert s * s == N
        return "both", N, f"{s} or {M}{s}"
    for pat, form in ((r"Cube root of (\d+)\?", "cube"), (r"x\^3 = (\d+)\. x\?", "xcube"),
                      (r"A cube has volume (\d+)\. Edge\?", "edge")):
        m = re.fullmatch(pat, prompt)
        if m:
            N = int(m.group(1))
            c = next(c for c in range(1, 12) if c ** 3 >= N)
            assert c ** 3 == N, prompt
            return form, N, str(c)
    raise AssertionError(f"unparsed T1 prompt {prompt!r}")


@pytest.mark.parametrize("item", by_tier(1), ids=ids(by_tier(1)))
def test_t1_answer_independent(item):
    form, N, truth = t1_truth(item["prompt"])
    assert item["choices"][item["answer"]] == truth
    vals = [parse_num(c) for c in item["choices"]]
    assert None not in vals
    # exactly one choice has the true value (a sign slip or a lone positive root is not equal)
    tv = parse_num(truth)
    assert sum(1 for v in vals if v == tv) == 1


T1_RULES = {
    "HALVED": lambda form, N, s: (frozenset({Fraction(N, 2), -Fraction(N, 2)}) if form == "both"
                                  else -Fraction(N, 2) if form == "xneg" else Fraction(N, 2)),
    "DOUBLED": lambda form, N, s: Fraction(2 * s),
    "NOT_ROOTED": lambda form, N, s: (frozenset({Fraction(N), -Fraction(N)}) if form == "both"
                                      else -Fraction(N) if form == "xneg" else Fraction(N)),
    "POSITIVE_ONLY": lambda form, N, s: Fraction(s),
    "AREA_OVER_4": lambda form, N, s: Fraction(N, 4),
    "PERIMETER_FOR_SIDE": lambda form, N, s: Fraction(4 * s),
    "THIRD_FOR_CUBE": lambda form, N, c: Fraction(N, 3),
    "TRIPLED": lambda form, N, c: Fraction(3 * c),
    "SQUARE_ROOT_FOR_CUBE": lambda form, N, c: Fraction(isqrt(N)),
}


@pytest.mark.parametrize("item", by_tier(1), ids=ids(by_tier(1)))
def test_t1_labels_are_produced_by_their_rule(item):
    form, N, truth = t1_truth(item["prompt"])
    s = int(truth.replace(M, "").split(" ")[0])
    for c, key in zip(item["choices"], item["misconceptions"]):
        if key in (None, "ARITH"):
            continue
        assert parse_num(c) == T1_RULES[key](form, N, s), (c, key)


def is_rational_text(t):
    v = parse_num(t)
    assert v is not None, t
    return not isinstance(v, tuple)


def t2_check(item):
    prompt = item["prompt"]
    ch = item["choices"]
    m = re.fullmatch(r"Which is (rational|irrational): (.+)\?", prompt)
    if m:
        want = m.group(1) == "rational"
        assert sorted(ch) == sorted(m.group(2).split(", "))  # the choices are exactly the listed numbers
        flags = [is_rational_text(c) for c in ch]
        assert sum(1 for f in flags if f == want) == 1  # exactly one choice has the asked property
        assert flags.index(want) == item["answer"]
        return
    assert sorted(ch) == ["Irrational", "Rational"]
    m = re.fullmatch(r"A square has area (\d+)\. Its side is\?", prompt)
    if m:
        n = int(m.group(1))
        truth = isqrt(n) ** 2 == n
    elif prompt == "A circle has diameter 1. Circumference?":
        truth = False  # pi * 1
    elif prompt == "A circle has radius 1. Its area is?":
        truth = False  # pi * 1^2
    elif (m := re.fullmatch(r"(\S+) is\?", prompt)):
        truth = is_rational_text(m.group(1))
    else:
        raise AssertionError(prompt)
    assert ch[item["answer"]] == ("Rational" if truth else "Irrational")


@pytest.mark.parametrize("item", by_tier(2), ids=ids(by_tier(2)))
def test_t2_answer_independent(item):
    t2_check(item)


def test_t2_labels_match_the_wrong_kind():
    for item in by_tier(2):
        for c, key in zip(item["choices"], item["misconceptions"]):
            if key in (None, "ARITH"):
                continue
            if c in ("Rational", "Irrational"):
                # a wrong WORD: Rational is wrong only for an irrational truth, so the key is *_IS_RATIONAL
                assert key in ("ROOT_IS_RATIONAL", "PI_IS_RATIONAL") if c == "Rational" else \
                    key in ("ROOT_IS_IRRATIONAL", "REPEAT_IS_IRRATIONAL", "NONWHOLE_IS_IRRATIONAL")
                continue
            v = parse_num(c)
            if key == "ROOT_IS_IRRATIONAL":
                assert re.fullmatch(R + r"\d+", c) and not isinstance(v, tuple)
            elif key == "REPEAT_IS_IRRATIONAL":
                assert c.endswith("...") and not isinstance(v, tuple)
            elif key == "NONWHOLE_IS_IRRATIONAL":
                assert not c.endswith("...") and not c.startswith(R) and not isinstance(v, tuple)
            elif key == "ROOT_IS_RATIONAL":
                assert isinstance(v, tuple) and v[0] == "sqrt"
            elif key == "PI_IS_RATIONAL":
                assert c == PI
            else:
                raise AssertionError(key)


def t3_truth(prompt):
    """-> (form, value Fraction, extra)"""
    m = re.fullmatch(r"0\.(\d+)\.\.\. as a fraction\?", prompt) or \
        re.fullmatch(r"Which fraction equals 0\.(\d+)\.\.\.\?", prompt)
    if m:
        return "rep", rep_value(0, m.group(1)), m.group(1)
    m = re.fullmatch(r"(0\.\d+) as a fraction\?", prompt)
    if m:
        return "end", Fraction(m.group(1)), m.group(1)[2:]
    m = re.fullmatch(r"x = 0\.(\d+)\.\.\. Then (10|100)x " + M + r" x = \?", prompt)
    if m:
        x = rep_value(0, m.group(1))
        return "x" + m.group(2), int(m.group(2)) * x - x, m.group(1)
    raise AssertionError(f"unparsed T3 prompt {prompt!r}")


@pytest.mark.parametrize("item", by_tier(3), ids=ids(by_tier(3)))
def test_t3_answer_independent(item):
    form, value, _ = t3_truth(item["prompt"])
    ans = item["choices"][item["answer"]]
    pv = parse_num(ans)
    assert pv == value
    if form in ("rep", "end"):
        m = re.fullmatch(r"(\d+)/(\d+)", ans)
        assert m and math.gcd(int(m.group(1)), int(m.group(2))) == 1  # simplest form
    else:
        assert re.fullmatch(r"\d+", ans)  # a whole number
    assert sum(1 for c in item["choices"] if parse_num(c) == value) == 1


@pytest.mark.parametrize("item", by_tier(3), ids=ids(by_tier(3)))
def test_t3_labels_are_produced_by_their_rule(item):
    form, value, digits = t3_truth(item["prompt"])
    for c, key in zip(item["choices"], item["misconceptions"]):
        if key in (None, "ARITH"):
            continue
        got = parse_num(c)
        if form == "rep":
            if len(digits) in (3,) or len(set(digits)) == 1:  # 0.777...
                d = int(digits[0])
                want = {"OVER_TEN": Fraction(d, 10), "ROUNDED_UP": Fraction(d + 1, 10)}
            elif digits[:2] == digits[2:]:  # 0.1818...
                ab = int(digits[:2])
                want = {"OVER_HUNDRED": Fraction(ab, 100), "NINTHS_ONLY": Fraction(ab, 81)}
            else:  # 0.1666...
                ab = int(digits[:2])
                want = {"OVER_HUNDRED": Fraction(ab, 100), "ROUNDED_UP": Fraction(ab + 1, 100)}
            assert got == want[key], (c, key)
        elif form == "end":
            n, L = int(digits), len(digits)
            want = {"NINE_FOR_TERMINATING": Fraction(n, 10 ** L - 1), "DIGIT_AS_DENOM": Fraction(1, n),
                    "PLACE_VALUE_SLIP": {1: Fraction(n, 100), 2: Fraction(n, 10), 3: Fraction(n, 100)}[L]}
            assert got == want[key], (c, key)
        else:
            k = int(form[1:])
            x = rep_value(0, digits)
            trunc_x = Fraction("0." + (digits[:2] if k == 100 else digits[:1]))
            want = {"TIMES_ONLY": k * x, "NINES_ONLY": Fraction(k - 1), "TRUNCATED_REPEAT": (k - 1) * trunc_x,
                    "DECIMAL_SLIP": trunc_x}
            assert got == want[key], (c, key)


def t4_truth(prompt):
    m = re.fullmatch(R + r"(\d+) is between which two whole numbers\?", prompt) or \
        re.fullmatch(r"Square area (\d+)\. Side is between which whole numbers\?", prompt)
    if m:
        n = int(m.group(1)); s = isqrt(n); assert s * s != n
        return "between", n, f"{s} and {s + 1}"
    m = re.fullmatch(r"Nearest whole number to " + R + r"(\d+)\?", prompt)
    if m:
        n = int(m.group(1)); s = isqrt(n)
        r = s if 4 * n < (2 * s + 1) ** 2 else s + 1  # exact: sqrt(n) < s + 1/2  iff  4n < (2s+1)^2
        return "nearest", n, str(r)
    m = re.fullmatch(R + r"(\d+) is about\?", prompt)
    if m:
        n = int(m.group(1))
        k = next(k for k in range(1, 12) if k * (k + 1) >= n)
        assert k * (k + 1) == n, prompt
        return "about", n, f"{k}.5"
    raise AssertionError(f"unparsed T4 prompt {prompt!r}")


@pytest.mark.parametrize("item", by_tier(4), ids=ids(by_tier(4)))
def test_t4_answer_independent(item):
    form, n, truth = t4_truth(item["prompt"])
    assert item["choices"][item["answer"]] == truth
    root = math.sqrt(n)
    if form == "between":
        flags = []
        for c in item["choices"]:
            a, b = (int(x) for x in re.fullmatch(r"(\d+) and (\d+)", c).groups())
            flags.append(b == a + 1 and a * a < n < b * b)
        assert flags.count(True) == 1 and flags[item["answer"]]
    elif form == "nearest":
        vals = [parse_num(c) for c in item["choices"]]
        right = Fraction(truth)
        assert vals.count(right) == 1
        for c, v in zip(item["choices"], vals):
            if v != right:
                assert abs(float(v) - root) >= 0.5  # clearly farther than the right one
        assert abs(float(right) - root) < 0.3
    else:
        right = float(truth)
        assert abs(right - root) < 0.05
        for c in item["choices"]:
            if c != truth:
                assert abs(float(parse_num(c)) - root) >= 0.5


def test_t4_labels_are_produced_by_their_rule():
    for item in by_tier(4):
        form, n, truth = t4_truth(item["prompt"])
        s = isqrt(n)
        for c, key in zip(item["choices"], item["misconceptions"]):
            if key in (None, "ARITH"):
                continue
            if form == "between":
                want = {"SQUARES_NOT_ROOTS": f"{s * s} and {(s + 1) ** 2}", "HALVED": f"{n // 2} and {n // 2 + 1}",
                        "NEXT_SQUARE_DOWN": f"{s - 1} and {s}", "NEXT_SQUARE_UP": f"{s + 1} and {s + 2}"}[key]
                assert c == want
            elif form == "nearest":
                r = int(truth)
                nearest_sq = min(range(1, 11), key=lambda q: abs(q * q - n)) ** 2
                want = {"HALVED": Fraction(n, 2), "NEAREST_SQUARE_NOT_ROOT": Fraction(nearest_sq),
                        "ROUNDED_WRONG": Fraction(s + 1 if r == s else s)}[key]
                assert parse_num(c) == want, (item["prompt"], c, key)
            else:
                k = int(truth.split(".")[0])
                assert key in ("HALVED", "NEAREST_SQUARE_NOT_ROOT")
                assert parse_num(c) in ({Fraction(n, 2)} if key == "HALVED" else {Fraction(k * k), Fraction((k + 1) ** 2)})


def t5_check(item):
    prompt, ch = item["prompt"], item["choices"]
    m = re.fullmatch(r"(Greater|Smaller): (\S+) or (\S+)\?", prompt)
    if m:
        a, b = m.group(2), m.group(3)
        assert sorted(ch) == sorted([a, b])
        pick = max if m.group(1) == "Greater" else min
        best = pick([a, b], key=fval)
        assert abs(fval(a) - fval(b)) >= 0.3
        assert ch[item["answer"]] == best
        return "compare", (m.group(1), a, b)
    m = re.fullmatch(r"Which (?:number lies|is) between (\d+) and (\d+)\?", prompt)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        assert hi == lo + 1
        flags = [lo < fval(c) < hi for c in ch]
        assert flags.count(True) == 1 and flags[item["answer"]]
        for c, f in zip(ch, flags):
            d = min(abs(fval(c) - lo), abs(fval(c) - hi))
            assert d >= 0.3, (c, d)  # the right one sits clear of the ends and so do the wrong ones
        return "between", (lo, hi)
    m = re.fullmatch(r"(Greatest|Least): (.+)\?", prompt)
    if m:
        toks = m.group(2).split(", ")
        assert sorted(ch) == sorted(toks) and len(toks) == 3
        vals = [fval(t) for t in toks]
        assert all(abs(x - y) >= 0.3 for x, y in itertools.combinations(vals, 2))
        best = (max if m.group(1) == "Greatest" else min)(toks, key=fval)
        assert ch[item["answer"]] == best
        return "list", (m.group(1), toks)
    m = re.fullmatch(r"(Least to greatest|Greatest to least): (.+)", prompt)
    if m:
        toks = m.group(2).split(", ")
        assert len(toks) == 3
        vals = [fval(t) for t in toks]
        assert all(abs(x - y) >= 0.3 for x, y in itertools.combinations(vals, 2))
        asc = m.group(1) == "Least to greatest"
        flags = []
        for c in ch:
            parts = c.split(", ")
            assert sorted(parts) == sorted(toks)
            v = [fval(t) for t in parts]
            flags.append(v == sorted(v, reverse=not asc))
        assert flags.count(True) == 1 and flags[item["answer"]]
        return "order", (asc, toks)
    if prompt == PI + "^2 is about?":
        assert ch[item["answer"]] == "10" and abs(math.pi ** 2 - 10) < 0.2
        for c in ch:
            if c != "10":
                assert abs(float(c) - math.pi ** 2) >= 1
        return "pi2", None
    raise AssertionError(f"unparsed T5 prompt {prompt!r}")


@pytest.mark.parametrize("item", by_tier(5), ids=ids(by_tier(5)))
def test_t5_answer_independent(item):
    t5_check(item)


def test_t5_labels_are_produced_by_their_rule():
    for item in by_tier(5):
        kind, info = t5_check(item)
        right = item["choices"][item["answer"]]
        for c, key in zip(item["choices"], item["misconceptions"]):
            if key in (None, "ARITH"):
                continue
            if kind == "compare":
                word, a, b = info
                items = [a, b]
                greater = word == "Greater"
                face_pick = (max if greater else min)(items, key=face)
                root_small_pick = [t for t in items if not t.startswith(R)][0] if greater else \
                    [t for t in items if t.startswith(R)][0] if any(t.startswith(R) for t in items) else None
                if key == "RADICAND_AS_VALUE":
                    assert c == face_pick
                elif key == "ROOT_ALWAYS_SMALL":
                    assert c == root_small_pick
                else:
                    raise AssertionError(key)
            elif kind == "list":
                word, toks = info
                if key == "RADICAND_AS_VALUE":
                    if word == "Greatest":  # the larger radicand among the roots, which beats the plain number
                        roots = [t for t in toks if t.startswith(R)]
                        assert c == max(roots, key=face) and face(c) > face(right)
                    else:
                        assert c == min(toks, key=face)
                elif key == "ROOT_ALWAYS_SMALL":
                    # 'roots are small': Greatest picks the plain number; Least picks a root
                    assert (not c.startswith(R)) if word == "Greatest" else c.startswith(R)
                else:
                    raise AssertionError(key)
            elif kind == "between":
                lo, hi = info
                v = fval(c)
                if key == "RADICAND_AS_VALUE":
                    assert c == f"{R}{lo}"
                elif key == "NEXT_SQUARE_DOWN":
                    assert lo - 1 < v < lo
                elif key == "NEXT_SQUARE_UP":
                    assert hi < v < hi + 1
                else:
                    raise AssertionError(key)
            elif kind == "order":
                asc, toks = info
                parts = c.split(", ")
                truth = sorted(toks, key=fval, reverse=not asc)
                if key == "RADICAND_AS_VALUE":
                    assert parts == sorted(toks, key=face, reverse=not asc)
                elif key == "ORDER_REVERSED":
                    assert parts == truth[::-1]
                elif key == "GIVEN_ORDER":
                    assert parts == toks
                elif key == "ROOT_ALWAYS_SMALL":
                    roots = [t for t in truth if t.startswith(R)]
                    plain = [t for t in truth if not t.startswith(R)]
                    assert parts == (roots + plain if asc else plain + roots)
                else:
                    raise AssertionError(key)
            else:
                assert key == "TIMES_FOR_POWER" and c == "6"


# ----------------------------------------------------------------------------------------------
# Choices: never two equal in value, ids and structure
# ----------------------------------------------------------------------------------------------
def choice_key(c):
    v = parse_num(c)
    if v is not None:
        return v
    parts = c.split(", ")
    if len(parts) == 3:  # an ordering: the sequence of values
        return tuple(parse_num(p) for p in parts)
    return ("text", c)


@pytest.mark.parametrize("item", ITEMS, ids=ids(ITEMS))
def test_no_two_choices_equal_in_value(item):
    keys = [choice_key(c) for c in item["choices"]]
    assert len(set(keys)) == len(keys), item["choices"]


def test_value_equality_detector_catches():
    # the detector must really see 0.333... = 1/3, sqrt(16) = 4, 2/4 = 1/2 and a reordering of the same list
    assert choice_key("0.333...") == choice_key("1/3")
    assert choice_key(f"{R}16") == choice_key("4")
    assert choice_key("2/4") == choice_key("1/2")
    assert choice_key(f"{R}2") != choice_key("1.4")
    assert choice_key("0.5") == choice_key("1/2")


def test_counts_and_ids():
    assert len(ITEMS) == 200
    assert Counter(i["tier"] for i in ITEMS) == {1: 40, 2: 40, 3: 40, 4: 40, 5: 40}
    assert len({i["id"] for i in ITEMS}) == 200


def test_every_declared_misconception_is_used_and_every_used_one_declared():
    declared = set(MANIFEST["misconceptions"])
    used = {k for it in ITEMS for k in it["misconceptions"] if k not in (None, "ARITH")}
    assert used <= declared
    assert declared <= used, declared - used


def test_arith_share_is_small():
    wrong = [k for it in ITEMS for k in it["misconceptions"] if k is not None]
    share = wrong.count("ARITH") / len(wrong)
    assert share <= 0.12, share
    for t in range(1, 6):
        w = [k for it in by_tier(t) for k in it["misconceptions"] if k is not None]
        assert w.count("ARITH") / len(w) <= 0.25, t


def test_charset_and_minus():
    allowed = set(chr(c) for c in range(32, 127)) | set("×÷−≤≥≠√π")
    for it in ITEMS:
        for s in [it["prompt"], it["explanation"]] + it["choices"]:
            assert set(s) <= allowed, (s, set(s) - allowed)
        for c in it["choices"]:
            assert not re.search(r"(^|[^\w])-\d", c), c  # negatives use U+2212


def test_word_choices_only_rational_irrational():
    for it in by_tier(2):
        if "Rational" in it["choices"] or "Irrational" in it["choices"]:
            assert sorted(it["choices"]) == ["Irrational", "Rational"]


# ----------------------------------------------------------------------------------------------
# Bounds (the manifest's `bounds` string), asserted on baked.json
# ----------------------------------------------------------------------------------------------
def simplest(f: Fraction, max_den, max_num):
    return 2 <= f.denominator <= max_den and f.numerator <= max_num


def bounds_violations(prompt, tier):
    bad = []
    if tier == 1:
        form, N, _ = t1_truth(prompt)
        if form in ("cube", "xcube", "edge"):
            if N not in (1, 8, 27, 64):
                bad.append(f"cube of {N}")
        else:
            if not (4 <= N <= 100 and isqrt(N) ** 2 == N):
                bad.append(f"not a perfect square 4-100: {N}")
    elif tier == 2:
        for n in re.findall(R + r"(\d+)", prompt):
            if not 2 <= int(n) <= 100:
                bad.append(f"radicand {n}")
        for a, b in re.findall(r"(\d+)/(\d+)", prompt):
            if not (1 <= int(a) <= 12 and 2 <= int(b) <= 12):
                bad.append(f"fraction {a}/{b}")
        m = re.search(r"0\.(\d+)\.\.\.", prompt)
        if m:
            try:
                v = rep_value(0, m.group(1))
                if v.denominator > 12:
                    bad.append(f"repeat denominator {v.denominator}")
            except ValueError as e:
                bad.append(str(e))
    elif tier == 3:
        form, v, digits = t3_truth(prompt)
        if form in ("rep", "end"):
            if not (v.denominator <= 12 and v.numerator <= 12):
                bad.append(f"fraction {v}")
        else:
            if not (1 <= v <= 90 and v.denominator == 1):
                bad.append(f"answer {v}")
    elif tier == 4:
        form, n, _ = t4_truth(prompt)
        if not 2 <= n <= 99 or isqrt(n) ** 2 == n:
            bad.append(f"radicand {n}")
        if form == "nearest":
            frac = math.sqrt(n) - isqrt(n)
            if 0.3 <= frac <= 0.7:
                bad.append(f"decimal part {frac:.2f} too near a half")
    else:
        m = re.fullmatch(r"(Greater|Smaller): (\S+) or (\S+)\?", prompt)
        if m and abs(fval(m.group(2)) - fval(m.group(3))) < 0.3:
            bad.append("values closer than 0.3")
        m = re.fullmatch(r"(Least to greatest|Greatest to least|Greatest|Least): (.+?)\??", prompt)
        if m:
            toks = m.group(2).split(", ")
            if len(toks) != 3:
                bad.append("not 3 values")
            if any(abs(fval(x) - fval(y)) < 0.3 for x, y in itertools.combinations(toks, 2)):
                bad.append("values closer than 0.3")
        for n in re.findall(R + r"(\d+)", prompt):
            if not 2 <= int(n) <= 99:
                bad.append(f"radicand {n}")
    return bad


TWO_CHOICE_CAP = {1: 0, 2: 12, 3: 0, 4: 0, 5: 10}


@pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
def test_two_choice_items_are_capped(tier):
    """A guesser gets half of 2-choice items right: keep them rare (lead audit, 2026-10-14)."""
    assert sum(1 for it in by_tier(tier) if len(it["choices"]) == 2) <= TWO_CHOICE_CAP[tier]


@pytest.mark.parametrize("item", ITEMS, ids=ids(ITEMS))
def test_concept_over_arithmetic_bounds(item):
    assert bounds_violations(item["prompt"], item["tier"]) == []
    for c in item["choices"]:
        v = parse_num(c)
        if isinstance(v, Fraction):
            assert abs(v) <= 999 or "/" in c  # wrong choices: whatever a misreading gives, up to 999
    # every choice text, even wrong, stays displayable
    assert all(len(c) <= 14 for c in item["choices"])


def test_bounds_manifest_string_present():
    assert "Roots" in MANIFEST["bounds"] and "0.3" in MANIFEST["bounds"]


BAD_PROMPTS = [
    (f"{R}50 = ?", 1),                                     # 50 is not a perfect square
    ("Cube root of 125?", 1),                              # only 1, 8, 27, 64
    ("x^2 = 144 and x > 0. x?", 1),                        # past 100
    (f"{R}101 is?", 2),                                    # radicand past 100
    ("0.142857... is?", 2),                                # not a 1-2 digit repeat
    ("0.1212... as a fraction?", 3),                       # 4/33: denominator over 12
    ("0.1313... as a fraction?", 3),                       # 13/99: not a bounded fraction
    ("0.35 as a fraction?", 3),                            # 7/20
    (f"{R}25 is between which two whole numbers?", 4),     # a perfect square
    (f"{R}101 is about?" , 4),                             # not k(k+1)-shaped (parser rejects)
    (f"Nearest whole number to {R}56?", 4),                # 7.48: a coin flip
    (f"Greater: {R}50 or 7.1?", 5),                        # 0.03 apart
    (f"Least to greatest: {R}5, 2.2, 3", 5),               # 2.236 vs 2.2
    (f"Greatest: {R}50, 7.1, 6?", 5),                      # 7.07 vs 7.1
]


@pytest.mark.parametrize("prompt,tier", BAD_PROMPTS)
def test_bounds_checker_rejects(prompt, tier):
    try:
        bad = bounds_violations(prompt, tier)
    except (AssertionError, ValueError, StopIteration):
        return  # the parser itself refused it
    assert bad, f"checker accepted {prompt!r}"


def test_list_forms_have_a_root_answer_about_half_the_time():
    """Lead audit: 'greatest is the plain number' must not be a tell. Per form, a root is the answer on 1/3 to 2/3."""
    for word in ("Greatest", "Least"):
        its = [it for it in by_tier(5) if re.match(word + r": ", it["prompt"])]
        assert len(its) >= 3
        roots = sum(1 for it in its if it["choices"][it["answer"]].startswith(R))
        assert len(its) / 3 <= roots <= 2 * len(its) / 3, (word, roots, len(its))
