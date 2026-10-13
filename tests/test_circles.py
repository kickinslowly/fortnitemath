"""circles cartridge: golden misconception values, an independent re-check of every baked answer, the manifest
bounds walked on baked.json, and value-distinct choices.

The independent check below reads each prompt with its own regexes and keywords and computes with
``fractions.Fraction`` (exact, π kept symbolic) and with ``math.pi`` floats (a second, numeric path). It never
calls the generator's ``solve``. Choices are compared as canonical polynomials in π and r, so ``πd`` and ``2πr``
are the same value and ``0.5`` and ``1/2`` are the same value.
"""
import json
import math
import re
from collections import Counter
from fractions import Fraction as F

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "circles"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Canonical values: polynomials in π and r (d = 2r), parsed from choice text
# ---------------------------------------------------------------------------------------------
def _mono_mul(m1, m2):
    d = dict(m1)
    for s, p in m2:
        d[s] = d.get(s, 0) + p
    return tuple(sorted((s, p) for s, p in d.items() if p))


def _poly_mul(a, b):
    out = {}
    for m1, c1 in a.items():
        for m2, c2 in b.items():
            m = _mono_mul(m1, m2)
            out[m] = out.get(m, 0) + c1 * c2
    return {m: c for m, c in out.items() if c}


def _poly_add(a, b):
    out = dict(a)
    for m, c in b.items():
        out[m] = out.get(m, 0) + c
    return {m: c for m, c in out.items() if c}


def _poly_inv(a):
    assert len(a) == 1, "can only divide by a single term"
    (m, c), = a.items()
    return {tuple((s, -p) for s, p in m): 1 / c}


def _poly_pow(a, n):
    out = {(): F(1)}
    for _ in range(n):
        out = _poly_mul(out, a)
    return out


def _sym(name, coef=1):
    return {((name, 1),): F(coef)}


ATOMS = {"π": _sym("π"), "r": _sym("r"), "d": _sym("r", 2), "radius": _sym("r"), "diameter": _sym("r", 2),
         "area": _sym("area"), "circumference": _sym("circumference")}


def _tokens(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == " ":
            i += 1
            continue
        m = re.match(r"\d+(?:\.\d+)?", s[i:])
        if m:
            out.append(("num", m[0]))
            i += m.end()
            continue
        for w in ("circumference", "diameter", "radius", "area"):
            if s.startswith(w, i):
                out.append(("sym", w))
                i += len(w)
                break
        else:
            ch = s[i]
            if ch in "πrd":
                out.append(("sym", ch))
            elif ch in "^/()+":
                out.append((ch, ch))
            else:
                raise ValueError(f"cannot read {ch!r} in {s!r}")
            i += 1
    return out


class _Parser:
    def __init__(self, text):
        self.t, self.i = _tokens(text), 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expr(self):
        out = self.term()
        while self.peek() == "+":
            self.take()
            out = _poly_add(out, self.term())
        return out

    def term(self):
        out = self.atom()
        while True:
            if self.peek() == "/":
                self.take()
                out = _poly_mul(out, _poly_inv(self.atom()))
            elif self.peek() in ("num", "sym", "("):
                out = _poly_mul(out, self.atom())
            else:
                return out

    def atom(self):
        kind, val = self.take()
        if kind == "num":
            a = {(): F(val)}
        elif kind == "sym":
            a = ATOMS[val]
        else:
            assert kind == "("
            a = self.expr()
            assert self.take()[0] == ")"
        if self.peek() == "^":
            self.take()
            a = _poly_pow(a, int(self.take()[1]))
        return a


def poly_of(text):
    p = _Parser(text)
    out = p.expr()
    assert p.i == len(p.t), f"trailing tokens in {text!r}"
    return out


def canon(text):
    return tuple(sorted(poly_of(text).items()))


def evalpoly(poly, pi_value, r=None):
    """Numeric value; raises for opaque words (area, circumference)."""
    total = 0.0
    for mono, c in poly.items():
        v = float(c)
        for s, p in mono:
            if s == "π":
                v *= pi_value ** p
            elif s == "r":
                assert r is not None
                v *= r ** p
            else:
                raise ValueError(s)
        total += v
    return total


def pi_(c):
    return {(("π", 1),): F(c)}


def num_(v):
    return {(): F(v)}


def pi_plus(a, b):
    return _poly_add(pi_(a), num_(b))


def test_canon_sees_equal_values():
    assert canon("πd") == canon("2πr")
    assert canon("0.5") == canon("1/2")
    assert canon("πd/2") == canon("πr")
    assert canon("1/(2π)") != canon("1/π")
    assert canon("5π + 10") == canon("10 + 5π")
    assert canon("8π") != canon("8")
    assert canon("πr^2") != canon("πd^2")
    assert canon("diameter^2") == canon("4r^2")


# ---------------------------------------------------------------------------------------------
# Golden cases: hand-worked wrong values per misconception
# ---------------------------------------------------------------------------------------------
GOLDEN = [
    # prompt, correct, {label: wrong text}
    ("Circle: radius 7. Diameter?", "14", {"HALVED_FOR_DOUBLED": "3.5", "SAME_NUMBER": "7", "C_FOR_D": "14π"}),
    ("Circle: diameter 10. Radius?", "5",
     {"DOUBLED_FOR_HALVED": "20", "SAME_NUMBER": "10", "HALVED_TWICE": "2.5"}),
    ("Circle: radius 4. Circumference ÷ diameter?", "π", {"SIZE_MATTERS": "4", "TWO_PI": "2π", "INVERTED": "1/π"}),
    ("Circle: radius 4. Circumference ÷ radius?", "2π",
     {"DIAMETER_RATIO": "π", "SIZE_MATTERS": "4", "INVERTED": "1/(2π)"}),
    ("A string around a circle is about how many diameters?", "3", {"RADII_COUNT": "6", "SQUARE_AROUND": "4"}),
    ("A string around a circle is about how many radii?", "6", {"DIAMETER_COUNT": "3", "SQUARE_AROUND": "8"}),
    ("Pi (π) is circumference divided by what?", "diameter",
     {"R_FOR_D": "radius", "AREA_FOR_C": "radius^2", "VOCAB_MIX": "area"}),
    ("Circle: radius 5. Circumference?", "10π",
     {"R_FOR_D": "5π", "AREA_FOR_C": "25π", "DOUBLED_D": "20π", "NO_PI": "10"}),
    ("Circle: diameter 6. Circumference?", "6π",
     {"DOUBLED_D": "12π", "R_FOR_D": "3π", "AREA_FOR_C": "9π", "NO_PI": "6"}),
    ("Radius doubles. Circumference is how many times as long?", "2", {"SQUARED_SCALE": "4", "CUBED_SCALE": "8"}),
    ("Radius is halved. Circumference is how many times as long?", "1/2",
     {"SQUARED_SCALE": "1/4", "CUBED_SCALE": "1/8"}),
    ("Circle: diameter 7. Circumference?", "7π", {"DOUBLED_D": "14π", "R_FOR_D": None, "AREA_FOR_C": "49π", "NO_PI": "7"}),
    ("Circle: radius 3. Area?", "9π",
     {"C_FOR_AREA": "6π", "DOUBLED_RADIUS": "36π", "NO_SQUARE": "3π", "NO_PI": "9"}),
    ("Circle: diameter 10. Area?", "25π",
     {"D_FOR_R": "100π", "C_FOR_AREA": "10π", "NO_SQUARE": "5π", "NO_PI": "25"}),
    ("Radius triples. Area is how many times as big?", "9", {"SAME_SCALE": "3", "CUBED_SCALE": "27"}),
    ("Two circles: radius 3 and radius 4. Total area?", "25π",
     {"SUM_RADII": "49π", "C_FOR_AREA": "14π", "ONE_CIRCLE": "16π"}),
    ("Circle: circumference 12π. Radius?", "6", {"GAVE_DIAMETER": "12", "WRONG_WAY": "24", "HALVED_TWICE": "3"}),
    ("Circle: circumference 7π. Diameter?", "7", {"GAVE_RADIUS": "3.5", "WRONG_WAY": "14"}),
    ("Circle: circumference 12π. Area?", "36π",
     {"D_FOR_R": "144π", "C_FOR_AREA": "12π", "NO_SQUARE": "6π", "NO_PI": "36"}),
    ("Radius 5. Circumference? Use 3 for π.", "30",
     {"AREA_FOR_C": "75", "R_FOR_D": "15", "DOUBLED_D": "60", "NO_PI": "10"}),
    ("Diameter 8. Circumference? Use 3 for π.", "24",
     {"DOUBLED_D": "48", "R_FOR_D": "12", "AREA_FOR_C": "48", "NO_PI": "8"}),
    ("Radius 3. Area? Use 3 for π.", "27",
     {"C_FOR_AREA": "18", "NO_SQUARE": "9", "DOUBLED_RADIUS": "108", "NO_PI": "9"}),
    ("Diameter 6. Area? Use 3 for π.", "27",
     {"C_FOR_AREA": "18", "NO_SQUARE": "9", "D_FOR_R": "108", "NO_PI": "9"}),
    ("Circle: circumference 36. Radius? Use 3 for π.", "6",
     {"GAVE_DIAMETER": "12", "FORGOT_PI": "18", "HALVED_TWICE": "3"}),
    ("Circle: circumference 24. Diameter? Use 3 for π.", "8",
     {"GAVE_RADIUS": "4", "FORGOT_PI": "24", "WRONG_WAY": "72"}),
    ("Semicircle: radius 6. Area?", "18π", {"WHOLE_CIRCLE": "36π", "HALVED_RADIUS": "9π", "ARC_FOR_AREA": "6π"}),
    ("Quarter circle: radius 8. Area?", "16π",
     {"WHOLE_CIRCLE": "64π", "HALF_FOR_QUARTER": "32π", "NO_SQUARE": "4π", "QUARTERED_RADIUS": "4π"}),
    ("Semicircle: radius 6. Length of the curved edge?", "6π",
     {"WHOLE_CIRCLE": "12π", "PERIMETER_NOT_ARC": "6π + 12", "AREA_FOR_ARC": "18π"}),
    ("Quarter circle: radius 6. Length of the curved edge?", "3π",
     {"HALF_FOR_QUARTER": "6π", "WHOLE_CIRCLE": "12π", "AREA_FOR_ARC": "9π"}),
    ("Semicircle: radius 5. Perimeter, flat side included?", "5π + 10",
     {"ARC_ONLY": "5π", "WHOLE_C_PLUS": "10π + 10", "HALF_C_PLUS_R": "5π + 5"}),
]


@pytest.mark.parametrize("prompt,correct,wrong", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(prompt, correct, wrong):
    sol = G.solve(prompt)
    assert sol["correct"][0] == correct
    got = {}
    for lab, v in sol["wrong"]:
        got.setdefault(lab, v[0] if v else None)
    for label, text in wrong.items():
        assert got[label] == text, label


def test_golden_vocab_mix_and_odd_cases():
    sol = G.solve("Distance around a circle is its?")
    assert sol["correct"][0] == "circumference"
    assert [(lab, v[0]) for lab, v in sol["wrong"]] == [("VOCAB_MIX", "diameter"), ("VOCAB_MIX", "radius"),
                                                       ("VOCAB_MIX", "area")]
    # a non-whole coefficient is simply not offered: a semicircle of radius 5 has area 12.5π
    sol = G.solve("Semicircle: radius 5. Length of the curved edge?")
    assert dict(sol["wrong"])["AREA_FOR_ARC"] is None
    # Two modelled values that coincide keep the first label (radius 4: 2π·... both 16π)
    vals = G.misconception_values(G.solve("Circle: radius 4. Circumference?"))
    assert [(lab, v[0]) for lab, v in vals] == [("R_FOR_D", "4π"), ("AREA_FOR_C", "16π"), ("NO_PI", "8")]


def test_every_misconception_has_a_golden_case():
    covered = {lab for g in GOLDEN for lab in g[2]}
    assert covered == set(BAKED["misconceptions"])


def test_every_misconception_is_used_in_the_baked_items():
    used = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    for key in BAKED["misconceptions"]:
        assert used[key] >= 1, key  # concept-bank labels (RADII_COUNT...) appear once by design


def test_student_text_fits():
    for k, m in BAKED["misconceptions"].items():
        assert m["teacher"] and 0 < len(m["student"]) <= 80, k


# a radius of 2 makes the circumference 2πr and the area πr^2 the same number; the generator must not use it
@pytest.mark.parametrize("prompt", [
    "Circle: radius 2. Circumference?",
    "Circle: diameter 4. Circumference?",
    "Circle: radius 2. Area?",
    "Circle: diameter 4. Area?",
    "Radius 2. Area? Use 3 for π.",
    "Semicircle: radius 2. Area?",
    "Semicircle: radius 2. Length of the curved edge?",
    "Circle: circumference 4π. Area?",
])
def test_two_right_doors_prompts_are_refused(prompt):
    assert G.check(prompt) is None


# ---------------------------------------------------------------------------------------------
# Independent solver + bounds walker (own regexes, Fraction and math.pi arithmetic)
# ---------------------------------------------------------------------------------------------
BANK_TRUTH = {
    "Circumference ÷ diameter = ?": "π",
    "Pi (π) is circumference divided by what?": "diameter",
    "A string around a circle is about how many diameters?": "3",
    "A string around a circle is about how many radii?": "6",
    "Circumference ÷ radius = ?": "2π",
    "Distance around a circle is its?": "circumference",
    "A line across a circle through its center is called?": "diameter",
    "A line from the center to the edge is called?": "radius",
    "Circumference formula, using radius r?": "2πr",
    "Circumference formula, using diameter d?": "πd",
    "Area formula, using radius r?": "πr^2",
    "Area of a circle is π times what?": "radius^2",
    "Radius × radius × π gives a circle's what?": "area",
}
EST = " Use 3 for π."
K_WORD = {"doubles": F(2), "triples": F(3), "quadruples": F(4), "is halved": F(1, 2)}


def independent(prompt):
    """dict(poly, float, pival, bad, q): the answer as a polynomial, the same answer as a float from the geometry,
    the manifest-bounds violations, and the question class. Everything comes from the prompt's own words."""
    if prompt in BANK_TRUTH:
        return dict(poly=poly_of(BANK_TRUTH[prompt]), float=None, pival=None, bad=[], q="bank")
    est = prompt.endswith(EST)
    text = prompt[: -len(EST)] if est else prompt
    pival = 3 if est else math.pi
    bad = []

    if m := re.fullmatch(r"Radius (doubles|triples|quadruples|is halved)\. (Circumference|Area) is how many "
                         r"times as (?:long|big)\?", text):
        k = K_WORD[m[1]]
        circ = m[2] == "Circumference"
        return dict(poly=num_(k if circ else k * k), float=float(k) if circ else float(k) ** 2, pival=None,
                    bad=bad, q="scale")

    low = text.lower()
    head, q = text.rsplit(". ", 1)
    radii = [int(x) for x in re.findall(r"radius (\d+)", head, flags=re.I)]
    diams = [int(x) for x in re.findall(r"diameter (\d+)", head, flags=re.I)]
    for x in radii + diams:
        if not 2 <= x <= 10:
            bad.append(f"given length {x} outside 2-10")

    if "total area" in q.lower():
        a, b = radii
        for x in (a, b):
            if x * x > 20:
                bad.append(f"{x}^2 = {x * x} is a + literal over 20")
        if a == b:
            bad.append("two equal circles")
        v = a * a + b * b
        if v > 100:
            bad.append("sum over 100")
        return dict(poly=pi_(v), float=math.pi * a ** 2 + math.pi * b ** 2, pival=math.pi, bad=bad, q="two")

    shape = F(1, 2) if re.search(r"semicircle|half[- ]circle|half of a circle", low) else \
        F(1, 4) if "quarter" in low else F(1)
    qq = q.lower()
    if "÷" in qq:
        qc = "ratio_d" if qq.split("÷")[1].strip().startswith("diameter") else "ratio_r"
    elif re.search(r"curved edge|curve", qq):
        qc = "arc"
    elif re.search(r"perimeter|all the way around", qq):
        qc = "perim"
    elif "area" in qq:
        qc = "area"
    elif "diameter" in qq:
        qc = "diameter"
    elif "radius" in qq:
        qc = "radius"
    elif re.search(r"circumference|how far|ribbon length|distance around", qq):
        qc = "circumference"
    else:
        raise AssertionError(f"unknown question in {prompt!r}")

    mc = re.search(r"(\d+)π", head)
    mp = None if mc else re.search(r"(?:circumference|distance around)(?: is)? (\d+)(?![\dπ])", head, flags=re.I)
    if mc:
        c = int(mc[1])
        if not 3 <= c <= 20:
            bad.append(f"π coefficient {c} outside 3-20")
        r = F(c, 2)  # C = 2πr
    elif mp:
        c = int(mp[1])
        if not est:
            bad.append("a plain circumference needs 'Use 3 for π'")
        if c > 60:
            bad.append("circumference over 60")
        r = F(c, 6)
    elif radii:
        r = F(radii[0])
    else:
        r = F(diams[0], 2)
    rf = float(r)
    needs_r = qc in ("radius", "area", "arc", "perim")
    if diams and needs_r:
        d = diams[0]
        if qc != "radius" and d % 2:
            bad.append(f"odd diameter {d} halves to {d / 2}")
        if d < 4:
            bad.append("halving gives a radius below 2")
    if mc and needs_r and qc != "diameter":
        if c % 2:
            bad.append(f"odd π coefficient {c} halves to a half")
        if not 2 <= r <= 10:
            bad.append("÷ 2 quotient outside 2-10")
    if mp:
        want = 6 if qc in ("radius", "area") else 3
        if c % want:
            bad.append(f"circumference {c} is not a multiple of {want}")

    if qc == "ratio_d":
        poly, fl = pi_(1), (2 * pival * rf) / (2 * rf)
    elif qc == "ratio_r":
        poly, fl = pi_(2), (2 * pival * rf) / rf
    elif qc == "diameter":
        d = 2 * r if not (mc or mp) else (F(c) if mc else F(c, 3))
        poly, fl = num_(d), float(d)
        if mc:
            fl = (c * math.pi) / math.pi  # C = πd
        if d.denominator != 1:
            bad.append("diameter not whole")
    elif qc == "radius":
        poly, fl = num_(r), rf
        if r.denominator not in (1, 2):
            bad.append("radius not whole or half")
        if r.denominator == 2 and (mc or mp):
            bad.append("half radius only allowed from a given diameter")
        if r.denominator == 2 and not diams:
            bad.append("half radius only allowed from a given diameter")
    elif qc == "circumference":
        fl = 2 * pival * rf
        poly = num_(6 * r) if est else pi_(2 * r)
        if est and diams:
            poly = num_(3 * diams[0])
    elif qc == "area":
        a = shape * r * r
        fl = pival * float(a)
        poly = num_(3 * a) if est else pi_(a)
        if est and r * r > 10:
            bad.append(f"3 × {r * r} leaves the times tables")
        if shape == F(1, 2) and (r % 2):
            bad.append(f"half of {r}^2 is not whole")
        if shape == F(1, 4) and (r % 2 or r < 4):
            bad.append("quarter circle needs an even radius of 4+")
    elif qc == "arc":
        a = shape * 2 * r
        fl = pival * float(a)
        poly = pi_(a)
        if shape == F(1, 4) and (r % 2 or r < 4):
            bad.append("quarter arc needs an even radius of 4+")
    else:  # perim
        if shape != F(1, 2):
            bad.append("perimeter only for a semicircle")
        fl = pival * rf + 2 * rf
        poly = pi_plus(r, 2 * r)
        if r.denominator != 1 or 2 * r > 20:
            bad.append("flat side not a whole number of 20 or less")

    # whole-number, size checks on the polynomial
    for mono, coef in poly.items():
        if coef.denominator != 1 and not (qc == "radius" and coef.denominator == 2):
            bad.append(f"answer coefficient {coef} is not whole")
        if mono == (("π", 1),) and not 1 <= coef <= 100:
            bad.append(f"π coefficient {coef} outside 1-100")
        if mono == () and qc != "perim" and not 0 < coef <= 100:
            bad.append(f"answer {coef} outside 1-100")
    return dict(poly=poly, float=fl, pival=pival, bad=bad, q=qc)


def parse_choice(c):
    return canon(c)


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_answer_independent(item):
    got = independent(item["prompt"])
    assert canon(item["choices"][item["answer"]]) == tuple(sorted(got["poly"].items())), item["prompt"]
    if got["float"] is not None:
        # the same answer as a float: π symbolic evaluated numerically must equal the geometry's float
        assert abs(evalpoly(got["poly"], got["pival"] or math.pi) - got["float"]) < 1e-9, item["prompt"]


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_bounds(item):
    got = independent(item["prompt"])
    assert got["bad"] == [], item["prompt"]
    for c in item["choices"]:
        assert len(c) <= 14
        for coef in poly_of(c).values():
            assert 0 < coef <= 999, c


@pytest.mark.parametrize("prompt,expect_bad", [
    ("Circle: radius 7. Area?", False),
    ("Circle: radius 12. Circumference?", True),                      # given length over 10
    ("Circle: diameter 14. Area?", True),                             # given diameter over 10
    ("Circle: diameter 9. Area?", True),                              # odd diameter: radius 4.5
    ("Circle: diameter 7. Radius?", False),                           # 3.5 is allowed in tier 1's shape
    ("Semicircle: radius 3. Area?", True),                            # 4.5π
    ("Semicircle: radius 4. Area?", False),
    ("Quarter circle: radius 2. Area?", True),                        # 2 ÷ 2 = 1: quotient below 2
    ("Quarter circle: radius 6. Area?", False),
    ("Radius 5. Area? Use 3 for π.", True),                           # 3 × 25: factor over 10
    ("Radius 3. Area? Use 3 for π.", False),
    ("Radius 7. Circumference? Use 3 for π.", False),                 # 6 × 7 = 42
    ("Circle: circumference 13π. Radius?", True),                     # 6.5
    ("Circle: circumference 12π. Radius?", False),
    ("Circle: circumference 40π. Area?", True),                       # coefficient over 20
    ("Circle: circumference 22. Radius? Use 3 for π.", True),         # not a multiple of 6
    ("Circle: circumference 24. Radius? Use 3 for π.", False),
    ("Two circles: radius 5 and radius 3. Total area?", True),        # 25 is a + literal over 20
    ("Two circles: radius 3 and radius 4. Total area?", False),
    ("Semicircle: radius 5. Perimeter, flat side included?", False),
    ("Quarter circle: radius 5. Length of the curved edge?", True),   # needs an even radius
    ("Radius 3. Area?", False),
])
def test_bounds_checker_catches(prompt, expect_bad):
    assert bool(independent(prompt)["bad"]) == expect_bad, prompt


def test_bounds_checker_rejects_something():
    """Disproof: the checker can fail."""
    assert independent("Circle: radius 12. Circumference?")["bad"]
    assert independent("Radius 5. Area? Use 3 for π.")["bad"]


def test_planted_bad_item_is_caught():
    """Disproof: a planted wrong answer and a planted twin-door item fail the checks the real items pass."""
    item = next(it for it in ITEMS if it["prompt"].startswith("Circle: radius 5. Circumference?"))
    truth = tuple(sorted(independent(item["prompt"])["poly"].items()))
    assert canon(item["choices"][item["answer"]]) == truth
    wrong = (item["answer"] + 1) % 4
    assert canon(item["choices"][wrong]) != truth  # a planted answer index is caught
    assert len({canon(c) for c in ["8π", "4π", "16π", "8π"]}) == 3  # a planted repeated door is seen
    assert len({canon(c) for c in ["πd", "2πr", "16π", "4π"]}) == 3  # equal value, different look


# ---------------------------------------------------------------------------------------------
# Formula questions: check the formula itself at a sample radius
# ---------------------------------------------------------------------------------------------
FORMULA_VALUE = {
    "Circumference formula, using radius r?": lambda r: 2 * math.pi * r,
    "Circumference formula, using diameter d?": lambda r: 2 * math.pi * r,
    "Area formula, using radius r?": lambda r: math.pi * r * r,
    "Area of a circle is π times what?": lambda r: r * r,
    "Pi (π) is circumference divided by what?": lambda r: 2 * r,
}


@pytest.mark.parametrize("prompt", sorted(FORMULA_VALUE))
def test_formula_answers_evaluate_right_and_wrong_ones_do_not(prompt):
    items = [it for it in ITEMS if it["prompt"] == prompt]
    assert items, prompt
    for it in items:
        want = FORMULA_VALUE[prompt](3)
        for i, c in enumerate(it["choices"]):
            try:
                val = evalpoly(poly_of(c), math.pi, r=3)
            except ValueError:
                assert i != it["answer"]  # opaque words (area) are never the answer here
                continue
            assert (abs(val - want) < 1e-9) == (i == it["answer"]), (prompt, c)


def test_pi_estimates_in_the_string_questions():
    assert round(math.pi) == 3          # about 3 diameters
    assert round(2 * math.pi) == 6      # about 6 radii


def test_bank_prompts_match_the_generators_bank():
    gen = set(G.BANK1) | set(G.BANK2) | set(G.BANK3)
    assert gen == set(BANK_TRUTH)


# ---------------------------------------------------------------------------------------------
# Choices: never two right doors; labels honest; shape of the content
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_choices_distinct_in_value(item):
    vals = [canon(c) for c in item["choices"]]
    assert len(set(vals)) == len(vals), item["choices"]
    assert len(item["choices"]) == 4


def test_choice_value_parser_sees_equal_values():
    assert canon("1/2") == canon("0.5") == canon("2/4")
    assert canon("3π") != canon("3")
    assert len({canon(c) for c in ["1/2", "0.5", "1/4", "2"]}) == 3  # a planted twin pair is seen


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_labels_are_produced_by_their_rule(item):
    sol = G.solve(item["prompt"])
    produced = {(lab, v[0]) for lab, v in sol["wrong"] if v}
    produced_canon = {canon(v[0]) for _, v in sol["wrong"] if v}
    assert canon(sol["correct"][0]) not in produced_canon, "a wrong rule lands on the answer"
    labels = [m for m in item["misconceptions"] if m]
    assert any(m != "ARITH" for m in labels), "needs at least one misconception distractor"
    for c, m in zip(item["choices"], item["misconceptions"]):
        if m is None:
            continue
        if m == "ARITH":
            assert canon(c) not in produced_canon, f"ARITH {c} is really a misconception value"
        else:
            assert (m, c) in produced, (m, c)


def test_arith_share_overall_at_most_a_third():
    c = Counter(m for it in ITEMS for m in it["misconceptions"] if m)
    assert c["ARITH"] / sum(c.values()) <= 1 / 3


@pytest.mark.parametrize("item", ITEMS, ids=IDS)
def test_each_prompt_is_read_by_exactly_one_template(item):
    p = item["prompt"]
    hits = [k.name for k in G.KINDS.values()
            if (k.entries is not None and p in k.entries) or (k.entries is None and any(rx.match(p) for _, rx in k.regexes))]
    assert len(hits) == 1, (p, hits)


def test_every_usable_prompt_agrees_with_the_independent_solver():
    """Not only the 200 baked items: every wording the generator could ever pick, in every tier's pool."""
    seen = 0
    for k in G.KINDS.values():
        for _, prompt in k.candidates():
            sol = G.check(prompt)
            if sol is None:
                continue
            got = independent(prompt)
            assert got["bad"] == [], prompt
            assert canon(sol["correct"][0]) == tuple(sorted(got["poly"].items())), prompt
            seen += 1
    assert seen > 500  # 580 today


def test_every_possible_prompt_fits_the_screen():
    for k in G.KINDS.values():
        for _, prompt in k.candidates():
            assert len(prompt) <= 60, prompt


def test_tier_shapes():
    for t in range(1, 6):
        ts = by_tier(t)
        assert len(ts) == 40
        assert len({it["prompt"] for it in ts}) == 40
    q = {t: Counter(independent(it["prompt"])["q"] for it in by_tier(t)) for t in range(1, 6)}
    assert q[1]["diameter"] >= 10 and q[1]["radius"] >= 8 and q[1]["ratio_d"] >= 5 and q[1]["bank"] >= 6
    assert q[2]["circumference"] >= 30 and q[2]["scale"] == 4 and q[2]["bank"] == 2
    assert q[3]["area"] >= 25 and q[3]["two"] >= 4 and q[3]["scale"] == 4 and q[3]["bank"] == 3
    est4 = [it for it in by_tier(4) if it["prompt"].endswith("Use 3 for π.")]
    assert len(est4) >= 18
    assert q[4]["radius"] >= 10 and q[4]["area"] >= 10 and q[4]["diameter"] >= 3
    assert set(q[5]) == {"area", "arc", "perim"}
    assert q[5]["area"] >= 16 and q[5]["arc"] >= 9 and q[5]["perim"] >= 9
    # tier 1 only halves odd diameters, so only tier 1 has a ".5" answer
    for t in (2, 3, 4, 5):
        for it in by_tier(t):
            assert "." not in it["choices"][it["answer"]], it["prompt"]
    # every tier-2/3/5 choice list shows π (answers in terms of π), except scale questions and tier 4 estimates
    for it in by_tier(5):
        assert "π" in it["choices"][it["answer"]]


def test_no_grade_eight_drift_in_prompts():
    banned = re.compile(r"square root|√|Pythagor|slope|scientific|cylinder|cone|sphere|\^", re.I)
    for it in ITEMS:
        assert not banned.search(it["prompt"]), it["prompt"]


def test_bounds_string_declared():
    b = BAKED["bounds"]
    assert "2-10" in b and "1-100" in b and "Use 3 for π" in b
    assert BAKED["grade"] == "7" and BAKED["standards"] == ["CCSS.MATH.CONTENT.7.G.B.4"]


def test_generate_is_deterministic():
    import random
    m = {k: BAKED[k] for k in ("items_per_tier", "tiers")}
    a = G.generate(m, random.Random(BAKED["seed"]))
    b = G.generate(m, random.Random(BAKED["seed"]))
    assert a == b
    assert [{k: v for k, v in it.items() if k != "id"} for it in ITEMS] == a
