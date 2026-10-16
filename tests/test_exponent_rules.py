"""exponent-rules cartridge (grade 8, 8.EE.A.1): golden misconception cases, an independent re-check of
every baked item, the cartridge's bounds asserted on baked.json, and disproofs.

The independent check parses the prompt and every choice with a small recursive-descent evaluator
written HERE (Fractions, real exponentiation) and never calls the generator's candidate or value
functions. Equal-value double doors (2^8 vs 4^4, 1/8 vs 2^-3) are caught by exact value.
"""
import json
import random
import re
from collections import Counter
from fractions import Fraction

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "exponent-rules"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
with open(REPO_ROOT / "cartridges" / CID / "cartridge.json", encoding="utf-8") as _f:
    MANIFEST = json.load(_f)
ITEMS = BAKED["items"]
M = "−"  # U+2212


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def cd(cands):
    """candidate list -> {key: (display, value)} (first of a key wins)."""
    out = {}
    for key, d, v in cands:
        out.setdefault(key, (d, v))
    return out


# ---------------------------------------------------------------------------------------------
# Independent evaluator
# ---------------------------------------------------------------------------------------------
TOK = re.compile(r"\s*(\d+|[()^×÷/+−])")


def tokenize(s):
    pos, out = 0, []
    s = s.strip()
    while pos < len(s):
        m = TOK.match(s, pos)
        assert m, f"cannot tokenize {s!r} at {pos}"
        out.append(m.group(1))
        pos = m.end()
    return out


class Parser:
    """expr := add; add := mul (('+'|'−') mul)*; mul := unary (('×'|'÷'|'/') unary)*;
    unary := '−' unary | pow; pow := atom ('^' '−'? atom)?; atom := NUMBER | '(' expr ')'.
    A unary minus binds looser than ^, so −5^2 = −(5^2), as in the cartridge."""

    def __init__(self, text):
        self.t = tokenize(text)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        v = self.add()
        assert self.peek() is None, f"trailing tokens in {self.t}"
        return v

    def add(self):
        v = self.mul()
        while self.peek() in ("+", M):
            op = self.take()
            r = self.mul()
            v = v + r if op == "+" else v - r
        return v

    def mul(self):
        v = self.unary()
        while self.peek() in ("×", "÷", "/"):
            op = self.take()
            r = self.unary()
            v = v * r if op == "×" else v / r
        return v

    def unary(self):
        if self.peek() == M:
            self.take()
            return -self.unary()
        return self.pow()

    def pow(self):
        base = self.atom()
        if self.peek() == "^":
            self.take()
            neg = self.peek() == M
            if neg:
                self.take()
            e = self.atom()
            assert e.denominator == 1
            e = int(e)
            return base ** (-e if neg else e)
        return base

    def atom(self):
        tok = self.take()
        if tok == "(":
            v = self.add()
            assert self.take() == ")"
            return v
        assert tok.isdigit(), f"unexpected {tok}"
        return Fraction(int(tok))


def ev(text):
    return Parser(text).parse()


def sg(n):
    return str(n) if n >= 0 else M + str(-n)


PREFIXES = ("What is ", "Value of ", "Simplify ", "Evaluate ")


def is_fill(prompt):
    return " = " in prompt and "?" in prompt and not prompt.endswith(" = ?")


def target_value(prompt):
    """The value the correct choice must have, from the prompt alone."""
    m = re.fullmatch(r"Which equals (.+)\?", prompt)
    if m:
        return ev(m.group(1))
    if is_fill(prompt):
        lhs, rhs = prompt.split(" = ")
        want = ev(rhs)
        sols = [n for n in range(-20, 21) if ev(lhs.replace("?", sg(n))) == want]
        assert len(sols) == 1, f"{prompt}: solutions {sols}"
        return Fraction(sols[0])
    p = prompt
    for pre in PREFIXES:
        if p.startswith(pre):
            p = p[len(pre):]
    if p.endswith(" = ?"):
        p = p[:-4]
    return ev(p.rstrip("?"))


# ---------------------------------------------------------------------------------------------
# Golden cases: each misconception key yields its expected wrong value on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
def test_golden_tier1_zero():
    c = cd(G.t1_zero_cands(7))
    assert c["ZERO_IS_ZERO"][1] == 0 and c["ZERO_KEEPS_BASE"][1] == 7


def test_golden_tier1_negative_value():
    # 2^−3 = 1/8
    c = cd(G.t1_neg_cands(2, 3))
    assert c["NEG_VALUE"][1] == -8
    assert c["NEG_TIMES"][1] == -6
    assert c["NEG_FRACTION"][1] == Fraction(-1, 8)
    assert c["IGNORE_SIGN"][1] == 8
    assert c["TIMES_FOR_POWER"][1] == 6
    assert c["RECIP_TIMES"][1] == Fraction(1, 6)


def test_golden_tier1_which_equals():
    # Which equals 1/25? right: 5^−2
    c = cd(G.t1_which_cands(5, 2))
    assert c["IGNORE_SIGN"][0] == "5^2"
    assert c["NEG_VALUE"][0] == f"{M}(5^2)" and c["NEG_VALUE"][1] == -25
    assert c["NEG_FRACTION"][0] == f"{M}(5^{M}2)"
    assert c["SWAP_BASE_EXP"][0] == f"2^{M}5"
    assert "SWAP_BASE_EXP" not in cd(G.t1_which_cands(5, 1))  # base 1 is no base


def test_golden_tier2_product():
    # 2^3 × 2^4 = 2^7
    c = cd(G.t2_cands(2, 3, 4))
    assert c["MULT_EXPONENTS"][0] == "2^12"
    assert c["MULT_BASES"][0] == "4^7"
    assert c["MULT_BOTH"][0] == "4^12"
    assert c["SUB_EXPONENTS"][0] == f"2^{M}1"
    assert "SIGN_SLIP" not in c and "ADD_BASES" not in c
    # 5^−2 × 5^6 = 5^4
    c = cd(G.t2_cands(5, -2, 6))
    assert c["SIGN_SLIP"][0] == "5^8"
    assert c["SUB_EXPONENTS"][0] == f"5^{M}8"
    assert c["MULT_EXPONENTS"][0] == f"5^{M}12"
    assert c["ADD_BASES"][0] == "10^4"
    assert c["MULT_BASES"][0] == f"25^4"  # a wrong choice's base may pass 10


def test_golden_tier2_three_factors_and_missing():
    c = cd(G.t2_three_cands(3, 2, 3, 4))  # 3^2 × 3^3 × 3^4 = 3^9
    assert c["SKIPS_FACTOR"][0] == "3^5"
    assert c["SUB_EXPONENTS"][0] == f"3^{M}5"
    assert "MULT_EXPONENTS" not in c  # 24 > 12
    c = cd(G.t2_fill_cands(3, 9))  # 3^3 × 3^? = 3^9, ? = 6
    assert c["ADD_GIVEN"][1] == 12 and c["COPY_TOTAL"][1] == 9
    assert "MULT_GIVEN" not in c  # 27 > 12
    assert cd(G.t2_fill_cands(2, 5))["MULT_GIVEN"][1] == 10


def test_golden_tier3_quotient():
    # 7^8 ÷ 7^3 = 7^5
    c = cd(G.t3_cands(7, 8, 3))
    assert c["ADD_EXPONENTS"][0] == "7^11"
    assert c["DIVIDE_BASES"][0] == "1^5"
    assert c["FLIPPED_SUB"][0] == f"7^{M}5"
    assert "DIVIDE_EXPONENTS" not in c  # 8 ÷ 3 is not whole
    # 6^10 ÷ 6^2 = 6^8
    assert cd(G.t3_cands(6, 10, 2))["DIVIDE_EXPONENTS"][0] == "6^5"
    # 3^2 ÷ 3^6 = 3^−4
    assert cd(G.t3_cands(3, 2, 6))["FLIPPED_SUB"][0] == "3^4"
    # 5^3 ÷ 5^−2 = 5^5; the negative divisor exponent makes the add slip SUB_NEG
    c = cd(G.t3_cands(5, 3, -2))
    assert c["SUB_NEG"][0] == "5^1" and "ADD_EXPONENTS" not in c
    assert c["SIGN_SLIP"][0] == "5^1" or c["SIGN_SLIP"][0] == "5^1"
    # 4^−4 ÷ 4^3 = 4^−7
    assert cd(G.t3_cands(4, -4, 3))["SIGN_SLIP"][0] == "4^1"
    c = cd(G.t3_fill_cands(9, 3))  # 4^9 ÷ 4^? = 4^3, ? = 6
    assert c["ADD_GIVEN"][1] == 12 and c["COPY_TOTAL"][1] == 3 and c["FLIPPED_SUB"][1] == -6


def test_golden_tier4_power_of_power_and_product():
    c = cd(G.t4_pp_cands(2, 3, 4))  # (2^3)^4 = 2^12
    assert c["ADD_FOR_POWER"][0] == "2^7"
    assert c["DROP_OUTER"][0] == "2^3" and c["DROP_INNER"][0] == "2^4"
    assert "SIGN_SLIP" not in c
    c = cd(G.t4_pp_cands(5, -2, 3))  # (5^−2)^3 = 5^−6
    assert c["ADD_FOR_POWER"][0] == "5^1" and c["SIGN_SLIP"][0] == "5^6"
    # (2 × 3)^4 = 2^4 × 3^4 = 1296
    got = [(k, d, v) for k, d, v in G.t4_prod_cands(2, 3, 4)]
    assert ("FIRST_FACTOR_ONLY", "2^4 × 3", 48) in got
    assert ("FIRST_FACTOR_ONLY", "2 × 3^4", 162) in got
    assert ("SUM_FOR_PRODUCT", "2^4 + 3^4", 97) in got
    assert ("TIMES_FOR_POWER", "2 × 3 × 4", 24) in got
    assert ("SUM_BASES", "(2 + 3)^4", 625) in got
    c = cd(G.t4_fill_cands(3, 12))  # (2^3)^? = 2^12, ? = 4
    assert c["ADD_FOR_POWER"][1] == 9 and c["COPY_TOTAL"][1] == 12 and "ADD_GIVEN" not in c


def test_golden_tier5_rules_in_a_row():
    # (3^2)^3 ÷ 3^4 = 3^2 = 9
    assert G.t5_exponent("pow_div", [2, 3, 4]) == 2
    assert G.t5_exponent("pow_div", [2, 3, 4], ("addp",)) == 1      # 2 + 3 - 4
    assert G.t5_exponent("pow_div", [2, 3, 4], ("addq",)) == 10     # 6 + 4
    # 2^3 × 2^−5 = 2^−2 = 1/4
    assert G.t5_exponent("mul", [3, -5]) == -2
    assert G.t5_exponent("mul", [3, -5], ("mult",)) == -15
    assert G.t5_exponent("mul", [3, -5], ("subm",)) == 8
    assert G.t5_exponent("mul", [3, -5], ("abs",)) == 8
    # 10^5 ÷ 10^7 = 10^−2 = 1/100; flipped subtraction gives 10^2 = 100
    assert G.t5_exponent("div", [5, 7]) == -2 and G.t5_exponent("div", [5, 7], ("flip",)) == 2
    c = cd(G.t5_cands("div", 10, [5, 7]))
    assert c["NEG_VALUE"][1] == -100 and c["NEG_FRACTION"][1] == Fraction(-1, 100)
    assert c["IGNORE_SIGN"][1] == 100 and c["NEG_TIMES"][1] == -20
    assert c["FLIPPED_SUB"][1] == 100 or "FLIPPED_SUB" in c
    # a zero exponent: 2^3 × 2^−3 = 1
    c = cd(G.t5_cands("mul", 2, [3, -3]))
    assert c["ZERO_IS_ZERO"][1] == 0 and c["ZERO_KEEPS_BASE"][1] == 2
    # a positive result: 3^6 ÷ 3^4 = 9, and 'times for power' is 3 × 2 = 6
    assert cd(G.t5_cands("div", 3, [6, 4]))["TIMES_FOR_POWER"][1] == 6


def test_no_bare_leading_minus_on_a_power():
    """-2^-2 reads as (-2)^-2 = 1/4 to many 13-year-olds: never offer a bare leading minus on a power."""
    for it in ITEMS:
        for c in it["choices"]:
            assert not re.match(r"−\d+\^", c), (it["prompt"], c)


def test_leading_minus_power_would_be_two_right_doors():
    """Disproof: read both ways, the old choice -2^-2 collides with 2^-2; the parenthesised form does not."""
    assert ev("−2^−2") == Fraction(-1, 4) and ev("(−2)^−2") == Fraction(1, 4) == ev("2^−2")
    assert ev("−(2^−2)") == Fraction(-1, 4)
    bare = re.compile(r"−\d+\^")
    assert bare.match("−2^−2") and not bare.match("−(2^−2)")


def test_value_helpers():
    assert G.sg(-3) == f"{M}3" and G.sg(0) == "0"
    assert G.P(2, -3) == (f"2^{M}3", Fraction(1, 8))
    assert G.fnum(Fraction(-1, 8)) == f"{M}1/8" and G.fnum(Fraction(12)) == "12"
    assert G.show_ok(Fraction(1, 8)) and G.show_ok(Fraction(100)) and G.show_ok(Fraction(10 ** 6))
    assert not G.show_ok(Fraction(128)) and not G.show_ok(Fraction(3, 8)) and not G.show_ok(Fraction(1, 128))
    assert G.show_ok(Fraction(1, 10 ** 4)) and not G.show_ok(Fraction(1, 10 ** 5))


def test_candidates_drop_when_they_break_a_bound():
    # 8^4 × 8^5: MULT_EXPONENTS would be 8^20, so it is not offered
    assert "MULT_EXPONENTS" not in cd(G.t2_cands(8, 4, 5))
    # exact equal values are removed in assemble: (b^m)^n where m == n has DROP_OUTER == DROP_INNER
    rng = random.Random(1)
    spec = dict(prompt="(2^3)^3", correct=G.P(2, 9), cands=G.t4_pp_cands(2, 3, 3), fill=G.around(2, 9), nw=3, expl="x")
    picks = G.assemble(spec, rng)
    vals = [v for _, _, v in picks] + [spec["correct"][1]]
    assert len(set(vals)) == 4
    # a candidate equal to the right answer is dropped (2^2 × 2^2: multiplying gives 2^4 too)
    spec = dict(prompt="2^2 × 2^2", correct=G.P(2, 4), cands=G.t2_cands(2, 2, 2), fill=G.around(2, 4), nw=3, expl="x")
    assert all(v != Fraction(16) for _, _, v in G.assemble(spec, rng))


# ---------------------------------------------------------------------------------------------
# Independent answer check on every baked item
# ---------------------------------------------------------------------------------------------
def test_shape_and_counts():
    assert BAKED["id"] == CID and len(ITEMS) == 200
    for t in range(1, 6):
        assert len(by_tier(t)) == 40
    # tier 1 has 8 zero-power items with 3 choices; everything else has 4
    assert Counter(len(i["choices"]) for i in by_tier(1)) == {4: 32, 3: 8}
    for t in range(2, 6):
        assert {len(i["choices"]) for i in by_tier(t)} == {4}


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_answer_is_the_only_right_door(item):
    want = target_value(item["prompt"])
    vals = [ev(c) for c in item["choices"]]
    assert vals[item["answer"]] == want, (item["prompt"], item["choices"])
    # exactly one choice has the right value, and no two choices share a value
    assert sum(1 for v in vals if v == want) == 1
    assert len(set(vals)) == len(vals), (item["prompt"], item["choices"])
    # the explanation names the right answer
    assert item["choices"][item["answer"]] in item["explanation"], item["explanation"]


def test_prompts_unique_per_tier():
    for t in range(1, 6):
        ps = [i["prompt"] for i in by_tier(t)]
        assert len(set(ps)) == len(ps)


def test_every_declared_misconception_is_used_and_every_used_one_declared():
    declared = set(MANIFEST["misconceptions"])
    used = Counter(k for i in ITEMS for k in i["misconceptions"] if k not in (None, "ARITH"))
    assert set(used) <= declared
    assert declared - set(used) == set(), f"declared but never used: {declared - set(used)}"
    # ARITH is a filler: at most one per item
    assert all(i["misconceptions"].count("ARITH") <= 1 for i in ITEMS)


def test_answer_positions_balanced_per_tier():
    for t in range(1, 6):
        for k in (3, 4):
            grp = [i for i in by_tier(t) if len(i["choices"]) == k]
            if not grp:
                continue
            c = Counter(i["answer"] for i in grp)
            assert all(0.5 / k * len(grp) <= c[p] <= 1.5 / k * len(grp) for p in range(k)), (t, k, c)


# Independent label checks: a labelled wrong choice holds the value its rule promises.
def _bn(prompt):
    m = re.search(r"(\d+)\^", prompt)
    return int(m.group(1))


def test_tier1_labels_hold_their_values():
    for it in by_tier(1):
        p = it["prompt"]
        for c, k in zip(it["choices"], it["misconceptions"]):
            if k is None:
                continue
            if k == "ZERO_IS_ZERO":
                assert ev(c) == 0 and re.search(r"\d+\^0", p)
            elif k == "ZERO_KEEPS_BASE":
                assert ev(c) == _bn(p) and re.search(r"\d+\^0", p)
            elif k in ("NEG_VALUE", "NEG_FRACTION", "IGNORE_SIGN") and p.startswith("Which"):
                t = target_value(p)
                if k == "NEG_VALUE":
                    assert ev(c) == -(1 / t) and c.startswith(M)
                elif k == "NEG_FRACTION":
                    assert ev(c) == -t
                else:
                    assert ev(c) == 1 / t
            elif k == "NEG_VALUE":
                assert ev(c) == -1 / target_value(p)
            elif k == "NEG_FRACTION":
                assert ev(c) == -target_value(p)
            elif k == "IGNORE_SIGN":
                assert ev(c) == 1 / target_value(p)
            elif k == "NEG_TIMES":
                m = re.search(r"(\d+)\^−(\d+)", p)
                assert ev(c) == -int(m.group(1)) * int(m.group(2))
            elif k == "TIMES_FOR_POWER":
                m = re.search(r"(\d+)\^−(\d+)", p)
                assert ev(c) == int(m.group(1)) * int(m.group(2))
            elif k == "RECIP_TIMES":
                m = re.search(r"(\d+)\^−(\d+)", p)
                assert ev(c) == Fraction(1, int(m.group(1)) * int(m.group(2)))
            elif k == "SWAP_BASE_EXP":
                tm = re.search(r"Which equals", p)
                assert tm and re.fullmatch(r"(\d+)\^−(\d+)", c)


def test_tier2_to_4_labels_hold_their_values():
    for it in ITEMS:
        if it["tier"] not in (2, 3, 4):
            continue
        p = it["prompt"]
        exps = [int(x.replace(M, "-")) for x in re.findall(r"\^(−?\d+)", p)]
        for c, k in zip(it["choices"], it["misconceptions"]):
            if k is None or k == "ARITH":
                continue
            if is_fill(p):
                n = int(target_value(p))
                if it["tier"] == 2:
                    m, t = exps
                    want = {"ADD_GIVEN": m + t, "COPY_TOTAL": t, "MULT_GIVEN": m * t}[k]
                elif it["tier"] == 3:
                    m, t = exps
                    want = {"ADD_GIVEN": m + t, "COPY_TOTAL": t, "FLIPPED_SUB": t - m}[k]
                else:
                    m, t = exps
                    want = {"ADD_FOR_POWER": t - m, "COPY_TOTAL": t, "ADD_GIVEN": t + m}[k]
                assert ev(c) == want, (p, c, k)
                continue
            if it["tier"] == 2 and "(" not in p:
                b = _bn(p)
                if len(exps) == 2:
                    m, n = exps
                    cases = {"MULT_EXPONENTS": (b, m * n), "SUB_EXPONENTS": (b, m - n),
                             "MULT_BASES": (b * b, m + n), "MULT_BOTH": (b * b, m * n),
                             "ADD_BASES": (2 * b, m + n), "SIGN_SLIP": (b, abs(m) + abs(n))}
                else:
                    m, n, q = exps
                    cases = {"MULT_EXPONENTS": (b, m * n * q), "SUB_EXPONENTS": (b, m - n - q),
                             "SKIPS_FACTOR": (b, m + n), "SIGN_SLIP": (b, abs(m) + abs(n) + abs(q))}
                base, e = cases[k]
                assert ev(c) == Fraction(base) ** e, (p, c, k)
            elif it["tier"] == 3:
                b = _bn(p)
                m, n = exps
                cases = {"DIVIDE_EXPONENTS": (b, m // n if n else 0), "ADD_EXPONENTS": (b, m + n),
                         "SUB_NEG": (b, m + n), "DIVIDE_BASES": (1, m - n), "FLIPPED_SUB": (b, n - m),
                         "SIGN_SLIP": (b, abs(m) - abs(n))}
                base, e = cases[k]
                assert ev(c) == Fraction(base) ** e, (p, c, k)
                if k == "SUB_NEG":
                    assert n < 0
                if k == "DIVIDE_EXPONENTS":
                    assert n != 0 and m % n == 0
            elif it["tier"] == 4:
                mm = re.fullmatch(r"\((\d+)\^(−?\d+)\)\^(−?\d+)", p)
                if mm:
                    b, m, n = int(mm.group(1)), exps[0], exps[1]
                    cases = {"ADD_FOR_POWER": m + n, "SIGN_SLIP": -m * n, "DROP_OUTER": m, "DROP_INNER": n}
                    assert ev(c) == Fraction(b) ** cases[k], (p, c, k)
                else:
                    a, cc = map(int, re.findall(r"\d+", p)[:2])
                    n = exps[0] if exps else int(re.findall(r"\d+", p)[2])
                    n = int(re.fullmatch(r"\(\d+ × \d+\)\^(\d+)", p).group(1))
                    cases = {"SUM_FOR_PRODUCT": [Fraction(a) ** n + Fraction(cc) ** n],
                             "TIMES_FOR_POWER": [Fraction(a * cc * n)],
                             "SUM_BASES": [Fraction(a + cc) ** n],
                             "FIRST_FACTOR_ONLY": [Fraction(a) ** n * cc, a * Fraction(cc) ** n]}
                    assert ev(c) in cases[k], (p, c, k)


# ---------------------------------------------------------------------------------------------
# Bounds (the manifest's `bounds` string), asserted on baked.json
# ---------------------------------------------------------------------------------------------
POW = re.compile(r"(\d+)\^(−?\d+)")
FLAT = re.compile(r"(\d+)\^(−?\d+)((?: [×÷] \d+\^−?\d+)+)")
PP = re.compile(r"\((\d+)\^(−?\d+)\)\^(−?\d+)((?: [×÷] \d+\^−?\d+)*)")
PROD = re.compile(r"\((\d+) × (\d+)\)\^(\d+)")
FILL = re.compile(r"(.+) = (\d+\^−?\d+)")


def to_int(s):
    return int(s.replace(M, "-"))


def pow10(n):
    return n >= 10 and set(str(n)) <= {"0", "1"} and str(n).count("1") == 1 and str(n)[0] == "1"


def plain_ok(v):
    """A plain number shown as a choice: size <= 100, or a power of 10 up to 10^6; or 1 over one."""
    a = abs(v)
    if a.denominator == 1:
        return a.numerator <= 100 or (pow10(a.numerator) and a.numerator <= 10 ** 6)
    return a.numerator == 1 and (a.denominator <= 100 or (pow10(a.denominator) and a.denominator <= 10 ** 4))


def small(n):
    return abs(n) <= 12


def bounds_problems(prompt, choices):
    """Problems with one item under the cartridge's bounds string; [] if it meets them."""
    bad = []
    for b, e in POW.findall(prompt):
        if not 2 <= int(b) <= 10:
            bad.append(f"base {b}")
        if not small(to_int(e)):
            bad.append(f"exponent {e}")
    for c in choices:
        for _, e in POW.findall(c):
            if not small(to_int(e)):
                bad.append(f"choice exponent {e}")
        if "^" not in c and " " not in c and not plain_ok(ev(c)):
            bad.append(f"plain value {c}")
    # walk the correct steps
    m = FLAT.fullmatch(prompt)
    if m:
        pairs = [(m.group(1), m.group(2))] + re.findall(r"[×÷] (\d+)\^(−?\d+)", m.group(3))
        ops = re.findall(r"([×÷]) \d+\^", m.group(3))
        if len({b for b, _ in pairs}) != 1:
            bad.append("mixed bases in a product or quotient")
        run = to_int(pairs[0][1])
        for op, (_, e) in zip(ops, pairs[1:]):
            run = run + to_int(e) if op == "×" else run - to_int(e)
            if not small(run):
                bad.append(f"step {run}")
    m = PP.fullmatch(prompt)
    if m:
        mi, no = to_int(m.group(2)), to_int(m.group(3))
        if abs(mi) < 2 or abs(no) < 2 or not small(mi * no):
            bad.append(f"power step {mi} × {no}")
        run = mi * no
        rest = re.findall(r"([×÷]) \d+\^(−?\d+)", m.group(4))
        for op, e in rest:
            if m.group(1) and not re.search(rf"[×÷] {m.group(1)}\^", m.group(4)):
                bad.append("mixed bases")
            run = run + to_int(e) if op == "×" else run - to_int(e)
            if not small(run):
                bad.append(f"step {run}")
    m = PROD.fullmatch(prompt)
    if m and not (2 <= int(m.group(3)) <= 5 and 2 <= int(m.group(1)) < int(m.group(2)) <= 10):
        bad.append("product shape")
    if "?" in prompt and not prompt.endswith(" = ?"):
        n = int(target_value(prompt))
        if not small(n):
            bad.append("missing exponent too big")
    return bad


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_bounds_on_baked(item):
    assert bounds_problems(item["prompt"], item["choices"]) == []
    assert len(item["prompt"]) <= 60 and all(len(c) <= 14 for c in item["choices"])


def test_manifest_states_bounds():
    b = MANIFEST["bounds"]
    assert "2-10" in b and "12" in b and M in b


def test_bounds_checker_can_fail():
    """Disproof: the checker rejects items that break each clause."""
    ok = ["2^3 × 2^4", "5^−2 × 5^6", "(2^3)^4", "(2 × 3)^4", "7^8 ÷ 7^3", "3^6 × 3^6", "10^5 ÷ 10^7 ÷ 10^3"]
    assert all(bounds_problems(p, ["1"]) == [] for p in ok)
    assert bounds_problems("2^13 × 2^2", ["2^15"])               # exponent over 12
    assert bounds_problems("11^2 × 11^3", ["11^5"])              # base over 10
    assert bounds_problems("1^2 × 1^3", ["1^5"])                 # base 1
    assert bounds_problems("2^7 × 2^8", ["2^15"])                # step 15
    assert bounds_problems("3^6 × 3^6 × 3^6", ["3^18"])          # running sum 18
    assert bounds_problems("(2^5)^3", ["2^15"])                  # power step 15
    assert bounds_problems("(2^1)^3", ["2^3"])                   # trivial inner exponent
    assert bounds_problems("2^3 × 2^4", ["2^30"])                # a choice exponent over 12
    assert bounds_problems("2^3 × 2^4", ["128"])                 # an unshowable plain value
    assert bounds_problems("2^3 × 3^4", ["2^3"])                 # mixed bases
    assert bounds_problems("2^3 × 2^? = 2^20", ["17"])           # missing exponent too big
    assert not plain_ok(Fraction(128)) and not plain_ok(Fraction(3, 8)) and plain_ok(Fraction(1, 1000))


def test_checker_sees_a_planted_bad_item():
    bad = dict(ITEMS[0])
    assert bounds_problems(bad["prompt"], bad["choices"]) == []
    assert bounds_problems("9^8 ÷ 9^−7", ["9^15"])               # answer exponent 15


def test_evaluator_conventions():
    assert ev("−5^2") == -25 and ev("2^−3") == Fraction(1, 8) and ev("(2 + 3)^2") == 25
    assert ev("2^4 × 3") == 48 and ev("1/8") == Fraction(1, 8) and ev("−1/8") == Fraction(-1, 8)
    assert ev("2^8") == ev("4^4") == ev("16^2")                  # the equal-value trap the check must catch
    assert ev("2^4 × 3^4") == ev("6^4")


def test_equal_value_double_door_is_caught():
    spec_vals = [ev("2^8"), ev("4^4")]
    assert len(set(spec_vals)) == 1                              # a bad item would fail test_answer_is_the_only_right_door


# ---------------------------------------------------------------------------------------------
# Determinism and the generator contract
# ---------------------------------------------------------------------------------------------
def test_generate_is_deterministic_and_matches_baked():
    a = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    b = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    assert a == b
    assert [{k: v for k, v in i.items() if k != "id"} for i in ITEMS] == a


def test_generator_imports_nothing_from_other_cartridges():
    src = (REPO_ROOT / "cartridges" / CID / "generator.py").read_text(encoding="utf-8")
    imports = re.findall(r"^(?:from|import) (\S+)", src, re.M)
    assert set(imports) <= {"__future__", "random", "fractions"}
