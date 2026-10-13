"""rational-ops cartridge: golden misconception rules, an independent re-check of every baked item, and the
manifest's "bounds" (PROTOCOL §4b) walked step by step on baked.json.

The independent check reads each prompt with this file's own parser, computes with ``fractions.Fraction`` (and,
as a cross-check on the parser, with Python's own ``eval``), reads each choice with its own reader, and counts
decimal places / carries with ``decimal`` and digit sums -- never the generator's solver or its bound helpers.
"""
import json
import random
import re
from decimal import Decimal
from fractions import Fraction
from math import gcd

import pytest

from fnm.cart import REPO_ROOT, load_generator
from fnm.validate import validate_baked

CID = "rational-ops"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]
M = "−"  # U+2212


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


def F(*a):
    """Fraction from a short literal: F('-3/4'), F('0.5'), F(3), F(1, 20)."""
    return Fraction(*a)


# ---------------------------------------------------------------------------------------------
# Own number readers
# ---------------------------------------------------------------------------------------------
NUM = r"(?:\d+/\d+|\d+\.\d+|\d+)"


def num(tok):
    return Fraction(tok)  # '3/4', '0.5' and '12' all parse exactly


def sval(tok):
    """'(−0.4)', '−1/2', '$3.50', '−$7' -> signed Fraction."""
    tok = tok.strip("()")
    neg = tok.startswith(M)
    tok = tok.lstrip(M).replace("$", "")
    v = num(tok)
    return -v if neg else v


def read_choice(text):
    """Value of one choice: decimal, repeating decimal, fraction, mixed number, money or a sign-placement form."""
    m = re.fullmatch(rf"(−?)\$(\d+)(?:\.(\d\d))?", text)
    if m:
        v = Fraction(f"{m[2]}.{m[3] or '0'}")
        return -v if m[1] else v
    m = re.fullmatch(r"(−?)(\d+)\.(\d)\3\3\.\.\.", text)
    if m:
        v = int(m[2]) + Fraction(int(m[3]), 9)
        return -v if m[1] else v
    m = re.fullmatch(r"(−?)(\d+)(?:\.(\d+))?", text)
    if m:
        v = Fraction(f"{m[2]}.{m[3] or '0'}")
        return -v if m[1] else v
    m = re.fullmatch(r"(−?)(?:(\d+) )?(\d+)/(\d+)", text)
    if m:
        v = int(m[2] or 0) + Fraction(int(m[3]), int(m[4]))
        return -v if m[1] else v
    m = re.fullmatch(r"(\(−\d+\)|−?\d+)/(\(−\d+\)|\d+)", text)
    if m:
        top = int(m[1].strip("()").replace(M, "-"))
        bottom = int(m[2].strip("()").replace(M, "-"))
        return Fraction(top, bottom)
    raise AssertionError(f"unreadable choice {text!r}")


def canonical(text, kind):
    """The one way a value of this kind is written: no trailing zeros, simplest form, mixed above 1."""
    if kind == "money":
        return bool(re.fullmatch(r"−?\$(0|[1-9]\d*)(\.\d\d)?", text)) and not text.endswith("00") or \
            bool(re.fullmatch(r"−?\$(0|[1-9]\d*)", text))
    if kind in ("dec", "decrep"):
        if re.fullmatch(r"−?(0|[1-9]\d*)(\.\d*[1-9])?", text):
            return text != "−0"
        return kind == "decrep" and bool(re.fullmatch(r"−?(0|[1-9]\d*)\.(\d)\2\2\.\.\.", text))
    if kind == "frac":
        if re.fullmatch(r"−?(0|[1-9]\d*)", text):
            return text != "−0"
        m = re.fullmatch(r"−?(?:([1-9]\d*) )?(\d+)/(\d+)", text)
        return bool(m) and 1 <= int(m[2]) < int(m[3]) and gcd(int(m[2]), int(m[3])) == 1
    if kind == "form":
        return bool(re.fullmatch(r"(\(−\d+\)|−?\d+)/(\(−\d+\)|\d+)", text))
    raise AssertionError(kind)


# ---------------------------------------------------------------------------------------------
# Own prompt reader. Returns a dict: fam, kind (choice kind), form (dec | frac), truth, steps, args.
# steps are (op, x, y): ('+', x, y) is x + y with y signed (so a difference is x + (-y)), ('×' | '÷', x, y).
# ---------------------------------------------------------------------------------------------
class Expr:
    """Recursive-descent reader for + − × ÷ ( ) with unary minus; records every binary step in order."""

    def __init__(self, text):
        self.toks = re.findall(rf"{NUM}|[+−×÷()]", text)
        assert "".join(self.toks) == text.replace(" ", ""), text
        self.i = 0
        self.steps = []

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def expr(self):
        v = self.term()
        while self.peek() in ("+", "−"):
            op = self.take()
            w = self.term()
            e = w if op == "+" else -w
            self.steps.append(("+", v, e))
            v = v + e
        return v

    def term(self):
        v = self.factor()
        while self.peek() in ("×", "÷"):
            op = self.take()
            w = self.factor()
            self.steps.append((op, v, w))
            v = v * w if op == "×" else v / w
        return v

    def factor(self):
        t = self.peek()
        if t == M:
            self.take()
            return -self.factor()
        if t == "(":
            self.take()
            v = self.expr()
            assert self.take() == ")"
            return v
        return num(self.take())


def run_expr(text):
    e = Expr(text)
    v = e.expr()
    assert e.i == len(e.toks), text
    return v, e.steps


def py_value(text):
    """Cross-check of the parser: Python's own eval on the same text with Fraction literals."""
    def sub(m):
        t = m.group(0)
        if "/" in t:
            n, d = t.split("/")
            return f"F({n},{d})"
        return f'F("{t}")'
    s = re.sub(NUM, sub, text).replace(M, "-").replace("×", "*").replace("÷", "/")
    assert re.fullmatch(r'[F()0-9",.+\-*/ ]+', s), s
    return eval(s, {"__builtins__": {}}, {"F": Fraction})


OPD = rf"(?:−?{NUM}|\(−{NUM}\))"  # an operand, parenthesised when negative after an operator
STORIES = [
    # (regex, fam, kind-of-choices); named groups a, b, r, n; 'w' is the direction word
    (rf"^Temp is (?P<a>−?\d+(?:\.\d+)?) degrees, then (?P<w>rises|drops) (?P<b>\d+(?:\.\d+)?) degrees\. Now\?$",
     "story_add", "dec"),
    (rf"^Diver at (?P<a>−{NUM}) m swims up (?P<b>{NUM}) m\. New elevation\?$", "story_add", "up"),
    (rf"^Diver at (?P<a>−{NUM}) m dives (?P<b>{NUM}) m deeper\. New elevation\?$", "story_add", "down"),
    (r"^Balance is (?P<a>−?\$\d+(?:\.\d\d)?)\. You (?P<w>deposit|spend) (?P<b>\$\d+(?:\.\d\d)?)\. New balance\?$",
     "story_add", "money"),
    (r"^Temp changes (?P<r>−\d+\.\d+) degrees an hour for (?P<n>\d+) hours\. Total\?$", "rate_dec", "dec"),
    (r"^Account changes (?P<r>−\$\d+(?:\.\d\d)?) a day for (?P<n>\d+) days\. Total\?$", "rate_dec", "money"),
    (r"^Water level changes (?P<r>−\d+/\d+) inch a day for (?P<n>\d+) days\. Total\?$", "rate_frac", "frac"),
    (rf"^Temps are (?P<a>−{NUM}) and (?P<b>{NUM}) degrees\. How far apart\?$", "dist", "dec"),
    (rf"^A diver at (?P<a>−{NUM}) m and a bird at (?P<b>{NUM}) m\. Distance apart\?$", "dist", "dec"),
]
CONV = [rf"^(?P<f>−?\d+/\d+) as a decimal\?$", rf"^Write (?P<f>−?\d+/\d+) as a decimal\.$",
        rf"^Convert (?P<f>−?\d+/\d+) to a decimal\.$"]
E1 = re.compile(rf"^(?P<a>−?{NUM}) × \((?P<b>−?\d+) (?P<op>[+−]) (?P<c>\(−\d+\)|\d+)\)$")
E2 = re.compile(rf"^(?P<a>−?{NUM}) (?P<op>[+−]) (?P<b>{OPD}) × (?P<c>\(−\d+\)|\d+)$")
E3 = re.compile(rf"^\((?P<a>−?{NUM}) (?P<op>[+−]) (?P<b>{OPD})\) ÷ (?P<c>\(−\d+\)|\d+)$")
TWO = re.compile(rf"^(?P<a>−?{NUM}) (?P<op>[+−×÷]) (?P<b>{OPD})$")


def read(item):
    p, tier = item["prompt"], item["tier"]
    out = {"prompt": p, "tier": tier}
    if tier in (1, 2, 3):
        m = TWO.match(p)
        assert m, p
        a, op, b = sval(m["a"]), m["op"], sval(m["b"])
        v, steps = run_expr(p)
        assert v == py_value(p), p
        frac_form = "/" in p
        if tier == 1:
            fam, kind = "add_dec", "dec"
        elif tier == 2:
            fam, kind = "add_frac", "frac"
        elif frac_form:
            fam, kind = ("fmul" if op == "×" else "fdiv"), "frac"
        else:
            fam, kind = ("dmul" if op == "×" else "ddiv"), "dec"
        out.update(fam=fam, kind=kind, form="frac" if frac_form else "dec", truth=v, steps=steps,
                   args=(a, op, b))
        return out
    if tier == 4:
        for rx in CONV:
            m = re.match(rx, p)
            if m:
                f = sval(m["f"])
                rep_ = F(abs(f)).denominator in (3, 9)
                out.update(fam="rep" if rep_ else "term", kind="decrep", form="frac", truth=f, steps=[],
                           args=(f,))
                return out
        m = re.match(rf"^Which equals (?P<s>−?)(?P<n>\d+)/(?P<d>\d+)\?$", p)
        assert m, p
        t = Fraction(int(m["n"]), int(m["d"])) * (-1 if m["s"] else 1)
        out.update(fam="formA" if m["s"] else "formB", kind="form", form="frac", truth=t, steps=[], args=(t,))
        return out
    # tier 5: stories first
    for rx, fam, sub in STORIES:
        m = re.match(rx, p)
        if not m:
            continue
        g = m.groupdict()
        if fam == "story_add":
            a, b = sval(g["a"]), sval(g["b"])
            plus = sub == "up" or g.get("w") in ("rises", "deposit")
            op = "+" if plus else "−"
            e = b if plus else -b
            is_frac = "/" in p
            out.update(fam="story_add_frac" if is_frac else "story_add", kind="frac" if is_frac else
                       ("money" if sub == "money" else "dec"), form="frac" if is_frac else "dec", truth=a + e,
                       steps=[("+", a, e)], args=(a, op, b, is_frac))
        elif fam in ("rate_dec", "rate_frac"):
            r_, n = sval(g["r"]), int(g["n"])
            out.update(fam=fam, kind="money" if sub == "money" else ("frac" if sub == "frac" else "dec"),
                       form="frac" if sub == "frac" else "dec", truth=r_ * n, steps=[("×", r_, Fraction(n))],
                       args=(r_, n, "frac" if sub == "frac" else "dec"))
        else:
            a, b = sval(g["a"]), sval(g["b"])
            out.update(fam="dist", kind="dec", form="dec", truth=b - a, steps=[("+", b, -a)], args=(a, b))
        return out
    for rx, fam in ((E1, "e1"), (E2, "e2"), (E3, "e3")):
        m = rx.match(p)
        if m:
            v, steps = run_expr(p)
            assert v == py_value(p), p
            a, op, c = sval(m["a"]), m["op"], sval(m["c"])
            b = sval(m["b"])
            frac_form = "/" in p
            out.update(fam=fam, kind="frac" if frac_form else "dec", form="frac" if frac_form else "dec",
                       truth=v, steps=steps, args=(a, op, b, c) if fam != "e2" else (a, op, b, c))
            return out
    raise AssertionError(f"unreadable prompt {p!r}")


PARSED = {it["id"]: read(it) for it in ITEMS}


def rules_for(info):
    """The generator's misconception rules for a parsed prompt (consistency check, not the answer)."""
    fam, args = info["fam"], info["args"]
    if fam == "add_dec":
        return G.add_rules(*args, False)
    if fam == "add_frac":
        return G.add_rules(*args, True)
    if fam == "story_add":
        return G.story_add_rules(*args)
    if fam == "story_add_frac":
        return G.story_add_rules(*args)
    if fam in ("fmul", "fdiv"):
        return G.muldiv_rules(*args, "frac")
    if fam in ("dmul", "ddiv"):
        return G.muldiv_rules(*args, "dec")
    if fam in ("term", "rep"):
        return G.conv_rules(*args)
    if fam in ("formA", "formB"):
        return G.form_rules(*args)
    if fam == "e1":
        a, op, b, c = args
        return G.e1_rules(a, b, op, c)
    if fam == "e2":
        a, op, b, c = args
        return G.e2_rules(a, op, b, c)
    if fam == "e3":
        a, op, b, c = args
        return G.e3_rules(a, op, b, c)
    if fam in ("rate_dec", "rate_frac"):
        return G.rate_rules(*args)
    if fam == "dist":
        return G.dist_rules(*args)
    raise AssertionError(fam)


# ---------------------------------------------------------------------------------------------
# Golden cases: each misconception's wrong value on a hand-worked prompt
# ---------------------------------------------------------------------------------------------
GOLDEN_ADD = [
    # a, op, b, is_frac, correct, {label: wrong}   (all hand-worked)
    ("-0.5", "+", "0.8", False, "0.3", {"WRONG_SIGN": "-0.3", "ADD_SIZES": "1.3", "KEEP_FIRST_SIGN": "-1.3"}),
    ("-0.2", "-", "-0.7", False, "0.5", {"SUB_NEG": "-0.9", "WRONG_SIGN": "-0.5", "ADD_SIZES": "0.9",
                                         "KEEP_FIRST_SIGN": "-0.9"}),
    ("-0.3", "+", "-0.4", False, "-0.7", {"NEG_NEG_ADD": "0.7", "SAME_SIGN_SUB": "-0.1", "WRONG_SIGN": "0.7"}),
    ("0.3", "-", "0.8", False, "-0.5", {"WRONG_SIGN": "0.5", "ADD_SIZES": "-1.1", "KEEP_FIRST_SIGN": "1.1"}),
    ("1.2", "-", "-0.4", False, "1.6", {"SUB_NEG": "0.8", "WRONG_SIGN": "-1.6", "SAME_SIGN_SUB": "0.8"}),
    ("-1/2", "+", "3/4", True, "1/4", {"WRONG_SIGN": "-1/4", "ADD_ACROSS": "1/3", "ADD_SIZES": "5/4",
                                       "NO_SCALE": "1/2", "KEEP_FIRST_SIGN": "-5/4"}),
    ("1/3", "-", "2/3", True, "-1/3", {"ADD_SIZES": "-1", "ADD_ACROSS": "-1/6", "WRONG_SIGN": "1/3",
                                       "KEEP_FIRST_SIGN": "1"}),
    ("-3/8", "+", "1/8", True, "-1/4", {"ADD_ACROSS": "-1/8", "ADD_SIZES": "-1/2", "WRONG_SIGN": "1/4",
                                        "KEEP_FIRST_SIGN": "-1/2"}),
    ("2/3", "-", "-1/6", True, "5/6", {"SUB_NEG": "1/2", "ADD_ACROSS": "1/3", "NO_SCALE": "1/2",
                                       "SAME_SIGN_SUB": "1/2", "WRONG_SIGN": "-5/6"}),
]


@pytest.mark.parametrize("a,op,b,is_frac,correct,wrong", GOLDEN_ADD, ids=[f"{g[0]}{g[1]}{g[2]}" for g in GOLDEN_ADD])
def test_golden_add_rules(a, op, b, is_frac, correct, wrong):
    a, b = F(a), F(b)
    assert (a + (b if op == "+" else -b)) == F(correct)
    got = G.add_rules(a, "+" if op == "+" else M, b, is_frac)
    assert set(got) == set(wrong), (sorted(got), sorted(wrong))
    for label, v in wrong.items():
        assert got[label] == F(v), label


@pytest.mark.parametrize("a,op,b,is_frac,absent", [
    ("0.4", "+", "0.3", False, ["NEG_NEG_ADD", "SUB_NEG", "ADD_SIZES", "KEEP_FIRST_SIGN"]),     # no negative
    ("-0.3", "+", "0.3", False, ["WRONG_SIGN", "ADD_SIZES", "SAME_SIGN_SUB"]),                  # sum 0
    ("-0.3", "+", "-0.3", False, ["SAME_SIGN_SUB", "ADD_SIZES", "KEEP_FIRST_SIGN"]),             # equal sizes
    ("-1/4", "+", "-3/4", True, ["NO_SCALE", "ADD_SIZES", "SUB_NEG"]),                           # like bottoms
    ("-0.5", "+", "0.8", False, ["NEG_NEG_ADD", "SUB_NEG", "SAME_SIGN_SUB", "ADD_ACROSS"]),      # decimals
])
def test_add_rule_does_not_fire_where_it_does_not_apply(a, op, b, is_frac, absent):
    got = G.add_rules(F(a), "+" if op == "+" else M, F(b), is_frac)
    for label in absent:
        assert label not in got, label


GOLDEN_MULDIV = [
    # a, op, b, form, correct, {label: wrong}
    ("-2/3", "×", "3/4", "frac", "-1/2", {"SIGN_RULE": "1/2", "FLIP_MULT": "-8/9", "ADD_FOR_MUL": "1/12",
                                          "ADD_BOTTOMS": "-6/7"}),
    ("-1/2", "÷", "-1/4", "frac", "2", {"SIGN_RULE": "-2", "NO_FLIP": "1/8", "FLIP_FIRST": "1/2"}),
    ("-3/4", "×", "8", "frac", "-6", {"SIGN_RULE": "6", "WHOLE_ON_BOTTOM": "-3/32", "FLIP_MULT": "-3/32",
                                      "ADD_FOR_MUL": "29/4"}),
    ("3/4", "÷", "-3", "frac", "-1/4", {"SIGN_RULE": "1/4", "NO_FLIP": "-9/4", "FLIP_FIRST": "-4"}),
    ("-0.6", "÷", "0.2", "dec", "-3", {"SIGN_RULE": "3", "POINT_PLACE": "-0.3", "MUL_FOR_DIV": "-0.12",
                                       "WRONG_ORDER": "-1/3"}),
    ("-0.4", "×", "6", "dec", "-2.4", {"SIGN_RULE": "2.4", "POINT_PLACE": "-0.24", "ADD_FOR_MUL": "5.6"}),
    ("0.3", "×", "-0.4", "dec", "-0.12", {"SIGN_RULE": "0.12", "POINT_PLACE": "-1.2", "ADD_FOR_MUL": "-0.1"}),
    ("-0.8", "÷", "4", "dec", "-0.2", {"SIGN_RULE": "0.2", "MUL_FOR_DIV": "-3.2", "WRONG_ORDER": "-5"}),
]


@pytest.mark.parametrize("a,op,b,form,correct,wrong", GOLDEN_MULDIV, ids=[f"{g[0]}{g[1]}{g[2]}" for g in GOLDEN_MULDIV])
def test_golden_muldiv_rules(a, op, b, form, correct, wrong):
    a, b = F(a), F(b)
    assert (a * b if op == "×" else a / b) == F(correct)
    got = G.muldiv_rules(a, op, b, form)
    assert set(got) == set(wrong), (sorted(got), sorted(wrong))
    for label, v in wrong.items():
        assert got[label] == F(v), label


GOLDEN_CONV = [
    ("-3/4", {"DROPPED_SIGN": "0.75", "FLIPPED": "-4/3", "DIGITS_AS_DECIMAL": "-0.34", "DENOM_ONLY": "-0.4",
              "UNIT_ONLY": "-0.25", "POINT_PLACE": "-7.5"}),
    ("2/3", {"FLIPPED": "3/2", "DIGITS_AS_DECIMAL": "0.23", "DENOM_ONLY": "0.3", "UNIT_ONLY": "1/3",
             "TRUNCATED": "0.6"}),
    ("7/20", {"FLIPPED": "20/7", "DIGITS_AS_DECIMAL": "0.72", "UNIT_ONLY": "1/20", "POINT_PLACE": "3.5"}),
    ("-5/9", {"DROPPED_SIGN": "5/9", "FLIPPED": "-9/5", "DIGITS_AS_DECIMAL": None, "DENOM_ONLY": "-0.9",
              "UNIT_ONLY": "-1/9", "TRUNCATED": "-0.5"}),  # -0.59 is within 0.05 of -0.5555...: dropped
    ("1/3", {"FLIPPED": "3", "DIGITS_AS_DECIMAL": "0.13", "DENOM_ONLY": None}),  # 0.3 is within 0.05: dropped
]


@pytest.mark.parametrize("f,wrong", GOLDEN_CONV, ids=[g[0] for g in GOLDEN_CONV])
def test_golden_conversion_rules(f, wrong):
    got = G.conv_rules(F(f))
    for label, v in wrong.items():
        if v is None:
            assert label not in got, label
        else:
            assert got[label] == F(v), label
    assert all(abs(v - F(f)) >= F(1, 20) for v in got.values())


def test_golden_form_rules():
    assert G.form_rules(F("-3/5")) == {"FLIPPED": F("-5/3"), "DOUBLE_NEG": F("3/5"), "DROPPED_SIGN": F("3/5")}
    assert G.form_rules(F("3/5")) == {"FLIPPED": F("5/3"), "NEG_STAYS": F("-3/5")}


def test_golden_two_step_rules():
    # −1/2 × (6 − 10) = 2
    r = G.e1_rules(F("-1/2"), F(6), M, F(10))
    assert r == {"ORDER": F(-13), "ADD_SIZES": F(8), "SIGN_RULE": F(-2)}
    # 2 × ... with a negative subtrahend: 0.5 × (3 − (−5)) = 4; SUB_NEG reads the inner as 3 − 5
    r = G.e1_rules(F("0.5"), F(3), M, F(-5))
    assert r["SUB_NEG"] == F(-1) and r["ORDER"] == F("0.5") * 3 + 5 and r["SIGN_RULE"] == F(-4)
    # −0.2 + 0.3 × 4 = 1
    r = G.e2_rules(F("-0.2"), "+", F("0.3"), F(4))
    assert r == {"ORDER": F("0.4"), "ADD_SIZES": F("1.4"), "SIGN_RULE": F("-1.4"), "WRONG_SIGN": F(-1)}
    # (−3/4 + 1/4) ÷ 2 = −1/4
    r = G.e3_rules(F("-3/4"), "+", F("1/4"), F(2))
    assert r == {"ORDER": F("-5/8"), "MUL_FOR_DIV": F(-1), "ADD_SIZES": F("-1/2"), "SIGN_RULE": F("1/4")}


def test_golden_story_rules():
    # Temp is −1.5, then drops 2. Now −3.5.
    r = G.story_add_rules(F("-1.5"), M, F(2), False)
    assert r["DIRECTION"] == F("0.5") and r["NEG_NEG_ADD"] == F("3.5") and r["SAME_SIGN_SUB"] == F("-0.5")
    assert r["WRONG_SIGN"] == F("3.5")
    assert G.rate_rules(F("-0.5"), 6, "dec") == {"SIGN_RULE": F(3), "ADD_FOR_MUL": F("5.5"), "POINT_PLACE": F("-0.3")}
    assert G.rate_rules(F("-3/4"), 4, "frac") == {"SIGN_RULE": F(3), "ADD_FOR_MUL": F("13/4"),
                                                  "WHOLE_ON_BOTTOM": F("-3/16")}
    assert G.dist_rules(F("-2.5"), F("1.5")) == {"SUBTRACT_SIZES": F(1), "NEG_DISTANCE": F(-4), "ONE_SIDE": F("2.5")}


def test_golden_number_text():
    assert G.dec(F("-3/4")) == "−0.75" and G.dec(F(5, 2)) == "2.5" and G.dec(F(3)) == "3" and G.dec(F(1, 3)) is None
    assert G.rep(F(2, 3)) == "0.666..." and G.rep(F(-1, 3)) == "−0.333..." and G.rep(F(4, 3)) == "1.333..."
    assert G.rep(F(1, 2)) is None and G.rep(F(1, 6)) is None
    assert G.frac(F(-5, 4)) == "−1 1/4" and G.frac(F(3, 8)) == "3/8" and G.frac(F(-6, 3)) == "−2"
    assert G.money(F(-7, 2)) == "−$3.50" and G.money(F(6)) == "$6" and G.money(F(1, 3)) is None


# ---------------------------------------------------------------------------------------------
# Whole-file checks
# ---------------------------------------------------------------------------------------------
def test_baked_file_is_valid_and_complete():
    assert validate_baked(BAKED, CID) == []
    assert len(ITEMS) == 200 and BAKED["grade"] == "7" and BAKED["items_per_tier"] == 40
    assert all(len(by_tier(t)) == 40 for t in range(1, 6))
    assert BAKED["standards"] == [f"CCSS.MATH.CONTENT.7.NS.{s}" for s in
                                  ("A.1.C", "A.1.D", "A.2.B", "A.2.C", "A.2.D", "A.3")]
    assert BAKED["bounds"].startswith("Rational numbers (PROTOCOL 4b)")


def test_emits_to_clean_verse_in_memory():
    # The slot file is regenerated by the parent; this proves the strings (− × ÷ $ ( ) ... and the 3-choice
    # items) survive the Verse escaper and lint, without writing any shared file.
    from fnm.emit import verse_source
    from verse_lint import lint
    for profile in ("unicode", "ascii"):
        assert lint(verse_source([BAKED], profile)) == [], profile


def test_generation_is_deterministic():
    manifest = {k: v for k, v in BAKED.items() if k not in ("baked_with", "items")}
    a = G.generate(manifest, random.Random(manifest["seed"]))
    b = G.generate(manifest, random.Random(manifest["seed"]))
    assert a == b
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == a


def test_every_manifest_label_is_used_and_fits():
    cat = BAKED["misconceptions"]
    used = {m for it in ITEMS for m in it["misconceptions"] if m}
    assert used - {"ARITH"} == set(cat), (sorted(used - set(cat)), sorted(set(cat) - used))
    for key, m in cat.items():
        assert len(m["student"]) <= 80, key
    for order in G.ORDERS.values():
        for lab in order:
            assert lab in cat, lab


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked item
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    info = PARSED[item["id"]]
    ans = read_choice(item["choices"][item["answer"]])
    assert ans == info["truth"], (item["prompt"], item["choices"])
    want = item["choices"][item["answer"]]
    assert want in item["explanation"], item["explanation"]
    if info["kind"] != "form":  # the working ends on the answer
        assert item["explanation"].rstrip(".").endswith(want.rstrip(".")), item["explanation"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_no_two_choices_equal_in_value_and_forms_are_canonical(item):
    info = PARSED[item["id"]]
    vals = [read_choice(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert len(item["choices"]) == (3 if info["kind"] == "form" else 4)
    for c in item["choices"]:
        assert canonical(c, info["kind"]), (c, info["kind"], item["prompt"])


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    info = PARSED[item["id"]]
    produced = rules_for(info)
    order = G.ORDERS[info["fam"]]
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one real misconception distractor"
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        v = read_choice(c)
        if m == "ARITH":
            assert v not in produced.values(), f"ARITH {c} is really a misconception value"
            continue
        assert m in order, f"{m} is not one of {info['fam']}'s labels"
        assert produced[m] == v, (c, m, produced[m])
        if info["kind"] != "form":  # forms: two labels share a value on purpose, one is offered
            for lab in order[:order.index(m)]:
                assert produced.get(lab) != v, f"{c}: {lab} outranks {m}"


def test_arith_share_at_most_a_quarter():
    labels = [m for it in ITEMS for m in it["misconceptions"] if m]
    assert labels.count("ARITH") <= len(labels) / 4, labels.count("ARITH") / len(labels)
    assert all(sum(m == "ARITH" for m in it["misconceptions"]) <= 2 for it in ITEMS)


def test_prompts_unique_per_tier():
    for t in range(1, 6):
        prompts = [it["prompt"] for it in by_tier(t)]
        assert len(set(prompts)) == len(prompts)


# ---------------------------------------------------------------------------------------------
# Tier shapes
# ---------------------------------------------------------------------------------------------
def fams(t):
    return [PARSED[it["id"]]["fam"] for it in by_tier(t)]


def test_tier_shapes():
    assert set(fams(1)) == {"add_dec"} and set(fams(2)) == {"add_frac"}
    assert set(fams(3)) == {"fmul", "fdiv", "dmul", "ddiv"}
    assert set(fams(4)) == {"term", "rep", "formA", "formB"}
    # T1: every item has a negative among its two addends (b is flipped by a minus)
    for it in by_tier(1):
        a, op, b = PARSED[it["id"]]["args"]
        e = b if op == "+" else -b
        assert a < 0 or b < 0 or e < 0, it["prompt"]
    # T2 has both like and unlike bottoms
    dens = [(PARSED[it["id"]]["args"][0].denominator, PARSED[it["id"]]["args"][2].denominator) for it in by_tier(2)]
    assert sum(x == y for x, y in dens) >= 10 and sum(x != y for x, y in dens) >= 15
    # T3: every item has a negative, fractions and decimals both present, all four operations
    for it in by_tier(3):
        a, op, b = PARSED[it["id"]]["args"]
        assert a < 0 or b < 0, it["prompt"]
    assert sum(f in ("fmul", "fdiv") for f in fams(3)) >= 20 and sum(f in ("dmul", "ddiv") for f in fams(3)) >= 12
    assert sum(f in ("fmul", "dmul") for f in fams(3)) >= 12 and sum(f in ("fdiv", "ddiv") for f in fams(3)) >= 12
    # T4: terminating, repeating and the sign-placement forms
    assert fams(4).count("rep") >= 8 and fams(4).count("term") >= 18
    assert fams(4).count("formA") >= 3 and fams(4).count("formB") >= 3
    # T5: stories and two-step expressions, decimals and fractions
    f5 = fams(5)
    assert sum(f.startswith(("story", "rate", "dist")) for f in f5) >= 15
    assert sum(f in ("e1", "e2", "e3") for f in f5) >= 15
    assert {"e1", "e2", "e3", "story_add", "story_add_frac", "rate_dec", "rate_frac", "dist"} <= set(f5)


def test_tier4_has_no_close_wrong_door():
    # PROTOCOL / LIBRARY: never 0.67 beside 2/3 -- a sharp kid argues. No wrong decimal within 0.05 of the answer.
    for it in by_tier(4):
        info = PARSED[it["id"]]
        if info["fam"] in ("term", "rep"):
            for k, c in enumerate(it["choices"]):
                if k != it["answer"]:
                    assert abs(read_choice(c) - info["truth"]) >= F(1, 20), (it["prompt"], c)


def test_tier4_repeating_written_with_dots():
    for it in by_tier(4):
        info = PARSED[it["id"]]
        if info["fam"] == "rep":
            ans = it["choices"][it["answer"]]
            assert re.fullmatch(r"−?0\.(\d)\1\1\.\.\.", ans), ans
            for c in it["choices"]:  # no hand-rounded 0.67 or 0.66 as a door
                if re.fullmatch(r"−?0\.\d\d", c):
                    assert abs(read_choice(c) - info["truth"]) >= F(1, 20), c


# ---------------------------------------------------------------------------------------------
# Bounds (manifest "bounds", PROTOCOL §4b) walked independently on baked.json
# ---------------------------------------------------------------------------------------------
def dec_facts(v):
    """(decimal places, non-zero digit count) of v written as a decimal, via the decimal module."""
    d = (Decimal(v.numerator) / Decimal(v.denominator)).normalize()
    t = d.as_tuple()
    places_ = max(0, -t.exponent)
    nz = sum(1 for x in t.digits if x != 0)
    return places_, nz


def digit_sum(n):
    return sum(int(c) for c in str(n))


def carry_count(x, y):
    """Carries (same signs) or borrows (different signs) in x + y, by the digit-sum identity."""
    k = max(dec_facts(x)[0], dec_facts(y)[0])
    X, Y = int(abs(x) * 10 ** k), int(abs(y) * 10 ** k)
    if (x < 0) == (y < 0):
        return (digit_sum(X) + digit_sum(Y) - digit_sum(X + Y)) // 9
    big, small = max(X, Y), min(X, Y)
    return (digit_sum(big - small) + digit_sum(small) - digit_sum(big)) // 9


def digits_of(v):
    """The digits with the point removed: 0.35 -> 35, 10 -> 10, 4 -> 4."""
    return int(abs(v) * 10 ** dec_facts(v)[0])


def value_problems(form, v):
    bad = []
    if abs(v) > 12:
        bad.append(f"{v} larger than 12")
    if v.denominator == 1:
        return bad
    if form == "dec":
        places_, nz = dec_facts(v)
        if places_ > 2:
            bad.append(f"{v} has more than 2 decimal places")
        elif nz > 2:
            bad.append(f"{v} has more than 2 non-zero digits")
    else:
        if not 2 <= v.denominator <= 12:
            bad.append(f"{v} denominator outside 2..12")
        if abs(v) >= 11:
            bad.append(f"{v} mixed whole part above 10")
    return bad


def step_problems(form, steps):
    bad = []
    for op, x, y in steps:
        z = x + y if op == "+" else (x * y if op == "×" else (x / y if y else None))
        if z is None:
            bad.append("division by zero")
            continue
        for v in (x, y, z):
            bad += value_problems(form, v)
        if op == "+":
            if form == "dec":
                if carry_count(x, y) > 1:
                    bad.append(f"{x} + {y} has more than one carry or borrow")
            elif x.denominator != 1 and y.denominator != 1:
                lo, hi = sorted((x.denominator, y.denominator))
                if hi % lo:
                    bad.append(f"bottoms {lo} and {hi}: neither is a multiple of the other")
        elif form == "dec":
            dx, dy = digits_of(x), digits_of(y)
            if op == "×":
                if not (2 <= dx <= 10 and 2 <= dy <= 10):
                    bad.append(f"digit factors {dx} × {dy} outside 2..10")
            else:
                if not (2 <= dy <= 10 and dx % dy == 0 and 2 <= dx // dy <= 10 and dx <= 100):
                    bad.append(f"digit division {dx} ÷ {dy} is not a times-table fact")
        else:
            nums = [abs(x.numerator), x.denominator, abs(y.numerator), y.denominator]
            if max(nums) > 10:
                bad.append(f"{x} {op} {y} uses a number above 10")
    return bad


def tier_problems(info):
    """The per-tier lines of the bounds string."""
    t, bad = info["tier"], []
    v = info["truth"]
    if t == 1:
        a, op, b = info["args"]
        for o in (a, b):
            tenths = abs(o) * 10
            if tenths.denominator != 1 or not 1 <= tenths <= 19 or tenths == 10:
                bad.append(f"T1 operand {o} is not tenths 0.1-1.9")
        if abs(v) > 2 or v == 0:
            bad.append(f"T1 answer {v} outside 0 < size <= 2")
    elif t == 2:
        a, op, b = info["args"]
        for o in (a, b):
            if not (abs(o) < 1 and 2 <= o.denominator <= 12):
                bad.append(f"T2 operand {o} is not a proper fraction")
        if abs(v) >= 2 or v == 0 or v.denominator > 12:
            bad.append(f"T2 answer {v} out of range")
    elif t == 3:
        a, op, b = info["args"]
        if info["form"] == "frac":
            for o in (a, b):
                if o.denominator == 1:
                    if not 2 <= abs(o) <= 10:
                        bad.append(f"T3 whole {o} outside 2..10")
                elif not (abs(o).numerator <= 9 and o.denominator <= 10 and abs(o) < 1):
                    bad.append(f"T3 fraction {o} not proper with numerator <= 9, denominator <= 10")
            if v.denominator != 1 and (abs(v.numerator) > 12 or v.denominator > 12):
                bad.append(f"T3 answer {v} has numerator or denominator above 12")
        else:
            for o in (a, b):
                if o.denominator == 1:
                    if not 2 <= abs(o) <= 10:
                        bad.append(f"T3 whole {o} outside 2..10")
                else:
                    pl, _ = dec_facts(o)
                    if pl != 1:
                        bad.append(f"T3 decimal {o} is not tenths")
    elif t == 4:
        if info["fam"] in ("term", "rep"):
            f = info["truth"]
            d = abs(f).denominator
            want = (2, 4, 5, 10, 20, 25) if info["fam"] == "term" else (3, 9)
            if d not in want or abs(f.numerator) > 12:
                bad.append(f"T4 {f}: denominator {d} / numerator not allowed")
        else:
            n, d = abs(info["truth"]).numerator, abs(info["truth"]).denominator
            if not (3 <= d <= 12 and 2 <= n < d):
                bad.append(f"T4 form {info['truth']} outside denominators 3-12")
    return bad


def bounds_violations(info):
    if info["tier"] == 4 and info["fam"] in ("term", "rep", "formA", "formB"):
        return tier_problems(info)
    return step_problems(info["form"], info["steps"]) + tier_problems(info)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    assert bounds_violations(PARSED[item["id"]]) == [], item["prompt"]


def _parse_prompt(prompt, tier):
    return read({"prompt": prompt, "tier": tier, "id": "x", "choices": [], "answer": 0})


@pytest.mark.parametrize("prompt,tier,expect_bad", [
    ("−0.5 + 0.8", 1, False),
    ("−2.5 + 0.8", 1, True),               # operand above 1.9
    ("−0.55 + 0.8", 1, True),              # hundredths in T1
    ("1.9 + (−0.1)", 1, False),
    ("−1.9 − 1.2", 1, True),               # answer 3.1
    ("−1/2 + 3/4", 2, False),
    ("−1/2 + 3/5", 2, True),               # bottoms 2 and 5
    ("−1/3 + 4/9", 2, False),
    ("−1/2 + 3/13", 2, True),              # bottom 13
    ("−2/3 × 3/4", 3, False),
    ("−7/9 × 8/9", 3, True),               # answer 56/81
    ("−1/2 ÷ (−1/4)", 3, False),
    ("−5/6 ÷ (−3/5)", 3, True),            # answer 25/18
    ("−0.6 ÷ 0.2", 3, False),
    ("−0.6 ÷ 0.4", 3, True),               # 6 ÷ 4 is not a times-table fact
    ("−0.12 × 0.3", 3, True),              # digit factor 12, hundredths
    ("−0.4 × 6", 3, False),
    ("−2.4 + 0.6 × (−9)", 5, False),
    ("−1.5 + 0.5 × 12", 5, True),          # factor 12
    ("Temp is −10.5 degrees, then rises 0.7 degrees. Now?", 5, True),   # 105 − 7: two borrows
    ("Temp is −3.5 degrees, then rises 0.7 degrees. Now?", 5, False),
    ("−1/2 × (6 − 10)", 5, False),
    ("−1/2 × (12 − 14)", 5, True),         # inner literal 14
    ("(−3/4 + 1/4) ÷ 2", 5, False),
    ("(−1/2 + 1/3) ÷ 2", 5, True),         # bottoms 2 and 3
])
def test_bounds_checker_catches(prompt, tier, expect_bad):
    assert bool(bounds_violations(_parse_prompt(prompt, tier))) == expect_bad, prompt


def test_t4_bounds_checker_catches():
    def bad(prompt):
        return bool(bounds_violations(_parse_prompt(prompt, 4)))
    assert not bad("−3/4 as a decimal?") and not bad("2/3 as a decimal?") and not bad("Which equals −3/5?")
    assert bad("7/8 as a decimal?") and bad("5/6 as a decimal?") and bad("−3/7 as a decimal?")
    assert bad("Which equals −3/13?") and bad("3/25 as a decimal?") is False


def test_generator_bounds_agree_with_checker_on_samples():
    for prompt, tier, form in (("−0.5 + 0.8", 1, "dec"), ("−2.5 + 0.8", 1, "dec"), ("−1/2 + 3/5", 2, "frac"),
                               ("−0.6 ÷ 0.4", 3, "dec"), ("−2.4 + 0.6 × (−9)", 5, "dec")):
        info = _parse_prompt(prompt, tier)
        if tier == 1:
            continue  # the generator checks the tier-1 range in the builder, not in steps_ok
        assert G.steps_ok(form, info["steps"]) == (not step_problems(form, info["steps"])), prompt


# ---------------------------------------------------------------------------------------------
# Concept coverage the plan promised
# ---------------------------------------------------------------------------------------------
def test_signs_cover_every_case_in_tier_1_and_2():
    for t in (1, 2):
        seen = set()
        for it in by_tier(t):
            a, op, b = PARSED[it["id"]]["args"]
            seen.add((a < 0, op, b < 0))
        assert len(seen) >= 7, (t, sorted(seen))  # all 7 sign patterns (a plain positive sum is not offered)


def test_tier_3_covers_repeated_misconception_keys():
    got = {m for it in by_tier(3) for m in it["misconceptions"] if m}
    assert {"SIGN_RULE", "NO_FLIP", "FLIP_FIRST", "POINT_PLACE", "MUL_FOR_DIV", "FLIP_MULT"} <= got


def test_stories_and_two_steps_cover_their_labels():
    got = {m for it in by_tier(5) for m in it["misconceptions"] if m}
    assert {"ORDER", "DIRECTION", "SUB_NEG", "WRONG_SIGN", "SUBTRACT_SIZES", "NEG_DISTANCE", "ONE_SIDE"} <= got
