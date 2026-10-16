"""cylinders-cones-spheres cartridge: golden misconception values, an independent re-check of every baked answer,
the manifest bounds walked on baked.json, and value-distinct choices.

The independent check reads each prompt with its own regexes and keywords and computes with ``fractions.Fraction``
(π kept as a coefficient) and ``math.isqrt``. It never calls the generator's ``solve_*`` functions or its step
search: ``reachable`` below is a second, separately written route search for the §4a times-table bound.
"""
import itertools
import json
import math
import re
from collections import Counter
from fractions import Fraction as F

import pytest

from fnm.cart import REPO_ROOT, load_generator

CID = "cylinders-cones-spheres"
G = load_generator(CID)
with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    BAKED = json.load(_f)
with open(REPO_ROOT / "cartridges" / CID / "cartridge.json", encoding="utf-8") as _f:
    MANIFEST = json.load(_f)
ITEMS = BAKED["items"]
IDS = [it["id"] for it in ITEMS]


def by_tier(t):
    return [it for it in ITEMS if it["tier"] == t]


# ---------------------------------------------------------------------------------------------
# Choice text -> exact value
# ---------------------------------------------------------------------------------------------
def parse_choice(t):
    m = re.fullmatch(r"\((\d+)/(\d+)\)π", t)
    if m:
        return ("pi", F(int(m.group(1)), int(m.group(2))))
    m = re.fullmatch(r"(\d*)π", t)
    if m:
        return ("pi", F(int(m.group(1) or 1)))
    m = re.fullmatch(r"(\d+)/(\d+)", t)
    if m:
        return ("num", F(int(m.group(1)), int(m.group(2))))
    if re.fullmatch(r"\d+", t):
        return ("num", F(int(t)))
    return ("txt", t)


# ---------------------------------------------------------------------------------------------
# Independent times-table route search (separate code from the generator's)
# ---------------------------------------------------------------------------------------------
def reachable(vals, div=None):
    """Can prod(vals)/div be built with × steps (both operands <= 10, product <= 100) and one exact ÷ (divisor
    and quotient 2-10)?  Ones are free."""
    vals = [v for v in vals if v != 1]

    def go(vs, d):
        if len(vs) <= 1 and d is None:
            return True
        if d is not None and 2 <= d <= 10:
            for i, v in enumerate(vs):
                if v <= 100 and v % d == 0 and 2 <= v // d <= 10 and go(vs[:i] + vs[i + 1:] + [v // d], None):
                    return True
        for i, j in itertools.combinations(range(len(vs)), 2):
            a, b = vs[i], vs[j]
            if a <= 10 and b <= 10 and a * b <= 100:
                if go([x for k, x in enumerate(vs) if k not in (i, j)] + [a * b], d):
                    return True
        return False

    return go(vals, div)


BANK_ANSWERS = {
    "Cylinder volume = base area × ?": "Height",
    "A cylinder's base is a circle. Its area is?": "π × r × r",
    "Same base area; B is taller. Which cylinder holds more?": "B (taller)",
    "Same base and height: how many cones fill one cylinder?": "3",
    "Cone and cylinder, same base and height. Cone is what part?": "1/3",
    "Same base and height: a cone is what part of the cylinder?": "1/3",
    "A ball fits a can exactly. The ball is what part of the can?": "2/3",
    "A cone fits a can exactly. The cone is what part of the can?": "1/3",
}
VERB = {"double": F(2), "doubled": F(2), "triple": F(3), "tripled": F(3), "halve": F(1, 2), "halved": F(1, 2)}


def solid_of(q):
    q = q.lower()
    if re.search(r"hemisphere|half", q):
        return "hemi"
    if re.search(r"sphere|ball|marble|globe|bubble|planet", q):
        return "sphere"
    if "cone" in q:
        return "cone"
    if re.search(r"cylinder|\bcan\b|tank|drum|silo|jar", q):
        return "cyl"
    raise AssertionError(f"no solid in {q!r}")


def num(s):
    m = re.fullmatch(r"\((\d+)/(\d+)\)", s)
    return F(int(m.group(1)), int(m.group(2))) if m else F(int(s))


def analyze(prompt):
    """(expected answer (type, value), bounds_ok) read from the prompt text alone."""
    if prompt in BANK_ANSWERS:
        return ("txt", BANK_ANSWERS[prompt]) if prompt in (
            "Cylinder volume = base area × ?", "A cylinder's base is a circle. Its area is?",
            "Same base area; B is taller. Which cylinder holds more?") else parse_choice(BANK_ANSWERS[prompt]), True

    m = re.search(r"(\d+) cups", prompt)
    if m:  # a can and a ball or cone that fits it
        n = int(m.group(1))
        ok = n % 3 == 0 and 2 <= n // 3 <= 10 and n <= 100
        return ("num", F(2 * n, 3) if "ball" in prompt else F(n, 3)), ok

    m = re.search(r"\b(Double|Triple|Halve|doubled|tripled|halved)\b", prompt)
    if m:  # scaling
        s = VERB[m.group(1).lower()]
        q = prompt.lower()
        solid = "sphere" if re.search(r"sphere|ball", q) else ("cone" if "cone" in q else "cyl")
        if "radius and height" in q:
            e = 3
        elif "radius" in q:
            e = 3 if solid == "sphere" else 2
        else:
            e = 1
        mv = re.search(r"(\d+)π", prompt)
        v = int(mv.group(1)) if mv else None
        mult = s ** e
        if s >= 2:
            facs = ([v] if v else []) + [int(s)] * e
            ok = reachable(facs) and mult * (v or 1) <= 100
        else:
            D = int(1 / mult)
            ok = v is None and mult >= F(1, 8) or (v is not None and v % D == 0 and 2 <= D <= 10 and 2 <= v // D <= 10)
        return ("pi", v * mult) if v else ("num", mult), ok

    if "base and height" in prompt:  # cone <-> cylinder with equal base and height
        n = int(re.search(r"(\d+)π", prompt).group(1))
        q = prompt.lower()
        if q.index("cylinder") < q.index("cone"):
            return ("pi", F(n, 3)), n % 3 == 0 and 2 <= n // 3 <= 10
        return ("pi", F(3 * n)), n <= 10

    solid = solid_of(prompt)
    mr = re.search(r"radius (\d+)", prompt)
    md = re.search(r"diameter (\d+)", prompt)
    mh = re.search(r"height (\d+)", prompt)
    r = None
    halve_ok = True
    if mr:
        r = int(mr.group(1))
    elif md:
        d = int(md.group(1))
        r = d // 2
        halve_ok = d % 2 == 0 and 2 <= d <= 10 and 1 <= r <= 5
    h = int(mh.group(1)) if mh else None

    if "using 3 for π" in prompt:
        facs = {"cyl": lambda: [3, r, r, h], "cone": lambda: [r, r, h], "sphere": lambda: [4, r, r, r],
                "hemi": lambda: [2, r, r, r]}[solid]()
        val = {"cyl": lambda: 3 * r * r * h, "cone": lambda: r * r * h, "sphere": lambda: 4 * r ** 3,
               "hemi": lambda: 2 * r ** 3}[solid]()
        ok = halve_ok and r <= 5 and (h is None or 1 <= h <= 10) and val <= 100 and reachable(facs)
        return ("num", F(val)), ok

    mv = re.search(r"(?:volume|holds) (\(\d+/\d+\)|\d+)π", prompt)
    if mv:  # work backward from the volume
        c = num(mv.group(1))
        q = prompt.lower()
        if solid in ("sphere", "hemi"):
            k = F(4, 3) if solid == "sphere" else F(2, 3)
            cube = c / k
            rr = round(cube ** F(1, 3)) if cube.denominator == 1 else None
            assert rr and rr ** 3 == cube, prompt
            ans = 2 * rr if "iameter" in prompt else rr
            ok = rr in (1, 3) and c in (F(36), F(4, 3), F(18), F(2, 3))
            return ("num", F(ans)), ok
        assert c.denominator == 1
        c = int(c)
        if solid == "cyl":
            if h is None:  # height asked, radius given
                ok = c <= 100 and c % (r * r) == 0 and r * r <= 10 and 2 <= c // (r * r) <= 10
                return ("num", F(c, r * r)), ok
            sq = F(c, h)
            rr = math.isqrt(int(sq))
            ok = c <= 100 and c % h == 0 and 2 <= h <= 10 and rr * rr == sq and 2 <= sq <= 10
            return ("num", F(rr)), ok
        # cone
        assert h is None
        hh = F(3 * c, r * r)
        ok = c <= 100 and ((r == 3 and c % 3 == 0 and 2 <= c // 3 <= 10) or
                           (r == 2 and c % 4 == 0 and 2 <= c // 4 <= 10 and hh <= 10))
        return ("num", hh), ok

    # plain volume: π coefficient
    mk = re.search(r"base area (?:is )?(\d+)π", prompt)
    if mk:
        k = int(mk.group(1))
        return ("pi", F(k * h)), halve_ok and 1 <= h <= 10 and reachable([k, h]) and k * h <= 100
    if solid == "cyl":
        coef, facs, div = F(r * r * h), [r, r, h], None
    elif solid == "cone":
        coef, facs, div = F(r * r * h, 3), [r, r, h], 3
    elif solid == "sphere":
        coef, facs, div = F(4 * r ** 3, 3), [4, r, r, r], 3
    else:
        coef, facs, div = F(2 * r ** 3, 3), [2, r, r, r], 3
    ok = halve_ok and r <= 5 and (h is None or 1 <= h <= 10)
    if solid in ("sphere", "hemi"):
        ok = ok and r in (1, 3)
        ok = ok and (r == 1 or (coef.denominator == 1 and 1 <= coef <= 100 and reachable(facs, div)))
    else:
        ok = ok and coef.denominator == 1 and 1 <= coef <= 100 and reachable(facs, div)
    return ("pi", coef), ok


def problems(it):
    """Everything wrong with one baked item, found independently of the generator."""
    out = []
    want, ok = analyze(it["prompt"])
    got = parse_choice(it["choices"][it["answer"]])
    if got != want:
        out.append(f"answer {got} != {want}")
    if not ok:
        out.append("bounds")
    vals = [parse_choice(c) for c in it["choices"]]
    if len(set(vals)) != len(vals):
        out.append("equal-value choices")
    if any(v[0] != got[0] for v in vals):
        out.append("mixed value types")
    if it["prompt"] in BANK_ANSWERS and it["choices"][it["answer"]] != BANK_ANSWERS[it["prompt"]]:
        out.append("word answer")
    for v in vals:
        if v[0] != "txt" and not 0 < v[1] <= 999:
            out.append(f"choice size {v}")
    return out


# ---------------------------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------------------------
def test_item_counts_and_manifest():
    assert len(ITEMS) == 200
    for t in range(1, 6):
        assert len(by_tier(t)) == 40
    assert MANIFEST["grade"] == "8" and MANIFEST["standards"] == ["CCSS.MATH.CONTENT.8.G.C.9"]
    assert "bounds" in MANIFEST and "PROTOCOL §4b" in MANIFEST["bounds"]
    assert MANIFEST["seed"] == 20261039


def test_catalog_complete_and_short():
    used = {k for it in ITEMS for k in it["misconceptions"] if k not in (None, "ARITH")}
    assert used <= set(MANIFEST["misconceptions"])
    for k, v in MANIFEST["misconceptions"].items():
        assert len(v["student"]) <= 80 and v["teacher"], k


def test_at_most_one_arith_and_real_misconceptions():
    for it in ITEMS:
        keys = [k for k in it["misconceptions"] if k is not None]
        assert keys.count("ARITH") <= 1, it["id"]
        assert len([k for k in keys if k != "ARITH"]) >= 2, it["id"]


def test_deterministic():
    again = G.generate(MANIFEST, __import__("random").Random(MANIFEST["seed"]))
    assert [(a["prompt"], a["choices"], a["answer"]) for a in again] == \
           [(b["prompt"], b["choices"], b["answer"]) for b in ITEMS]


# ---------------------------------------------------------------------------------------------
# Golden misconception cases (hand-worked)
# ---------------------------------------------------------------------------------------------
def case(kind, frame=0, **p):
    c = G.KINDS[kind].case(frame, **p)
    assert c is not None, (kind, p)
    return c


def scale_case(kind, solid, dim, s, frame=0, **extra):
    for p in G.KINDS[kind].params:
        if p["solid"] == solid and p["dim"] == dim and p["s"] == s and all(p.get(k) == v for k, v in extra.items()):
            return case(kind, frame, **p)
    raise AssertionError((kind, solid, dim, s))


GOLDEN = [
    # tier 1
    (lambda: case("cyl", dim="radius", x=3, h=4), "36π",
     {"NO_SQUARE": "12π", "LATERAL_AREA": "24π", "FORGOT_HEIGHT": "9π", "ADDED_HEIGHT": "13π"}),
    (lambda: case("cyl", dim="diameter", x=4, h=5), "20π",
     {"DIAMETER_AS_RADIUS": "80π", "NO_SQUARE": "10π", "HALVED_AFTER_SQUARE": "40π", "FORGOT_HEIGHT": "4π"}),
    (lambda: case("cyl_area", k=4, h=5), "20π",
     {"ADDED_HEIGHT": "9π", "FORGOT_HEIGHT": "4π", "AREA_AS_RADIUS": "80π"}),
    # tier 2
    (lambda: case("cone", dim="radius", x=3, h=4), "12π",
     {"NO_THIRD": "36π", "HALF_FOR_THIRD": "18π", "NO_SQUARE": "4π", "TIMES_THREE": "108π"}),
    (lambda: case("cone", dim="diameter", x=6, h=4), "12π", {"DIAMETER_AS_RADIUS": "48π", "NO_THIRD": "36π"}),
    (lambda: case("cone_from_cyl", c=30), "10π",
     {"SAME_AS_CYLINDER": "30π", "HALF_FOR_THIRD": "15π", "TIMES_THREE": "90π"}),
    (lambda: case("cyl_from_cone", v=5), "15π",
     {"SAME_AS_CONE": "5π", "DIVIDED_BY_THREE": "(5/3)π", "ADDED_THREE": "8π", "HALF_FOR_THIRD": "10π"}),
    # tier 3
    (lambda: case("sphere", dim="radius", x=3), "36π",
     {"NO_FOUR_THIRDS": "27π", "SQUARED_NOT_CUBED": "12π", "FOUR_NOT_THIRD": "108π", "HEMI_FORMULA": "18π"}),
    (lambda: case("sphere", dim="radius", x=1), "(4/3)π", {"NO_FOUR_THIRDS": "π", "FOUR_NOT_THIRD": "4π"}),
    (lambda: case("sphere", dim="diameter", x=6), "36π", {"DIAMETER_AS_RADIUS": "288π"}),
    (lambda: case("sphere", dim="diameter", x=2), "(4/3)π", {"DIAMETER_AS_RADIUS": "(32/3)π"}),
    (lambda: case("hemi", dim="radius", x=3), "18π",
     {"WHOLE_FOR_HALF": "36π", "NO_TWO_THIRDS": "27π", "SQUARED_NOT_CUBED": "6π"}),
    (lambda: case("hemi", dim="radius", x=1), "(2/3)π", {"WHOLE_FOR_HALF": "(4/3)π", "NO_TWO_THIRDS": "π"}),
    (lambda: case("sphere3", shape="sphere", dim="radius", x=2), "32",
     {"NO_FOUR_THIRDS": "24", "SQUARED_NOT_CUBED": "16", "FOUR_NOT_THIRD": "96"}),
    (lambda: case("sphere3", shape="sphere", dim="diameter", x=4), "32", {"DIAMETER_AS_RADIUS": "256"}),
    (lambda: case("hemi3", shape="hemi", dim="radius", x=2), "16",
     {"NO_TWO_THIRDS": "24", "WHOLE_FOR_HALF": "32", "SQUARED_NOT_CUBED": "8"}),
    # tier 4
    (lambda: case("cyl_height", C=45, r=3), "5",
     {"FORGOT_SQUARE": "15", "RADIUS_AS_DIAMETER": "20", "RADIUS_FOR_HEIGHT": "3"}),
    (lambda: case("cyl_radius", C=45, h=5), "3",
     {"STOPPED_AT_SQUARE": "9", "DIAMETER_FOR_RADIUS": "6", "HEIGHT_FOR_RADIUS": "5"}),
    (lambda: case("cone_height", V=12, r=3), "4",
     {"FORGOT_THIRD": "4/3", "NO_SQUARE": "12", "DIVIDED_NOT_MULTIPLIED": "4/9"}),
    (lambda: case("cone_height", V=8, r=2), "6",
     {"FORGOT_THIRD": "2", "NO_SQUARE": "12", "DIVIDED_NOT_MULTIPLIED": "2/3"}),
    (lambda: case("sphere_radius", shape="sphere", V="36π", ask="radius"), "3",
     {"STOPPED_AT_CUBE": "27", "DIAMETER_FOR_RADIUS": "6", "DIVIDED_NOT_ROOTED": "9", "COEFFICIENT_AS_RADIUS": "36"}),
    (lambda: case("sphere_diam", shape="sphere", V="36π", ask="diameter"), "6",
     {"RADIUS_FOR_DIAMETER": "3", "STOPPED_AT_CUBE": "27", "COEFFICIENT_AS_RADIUS": "36"}),
    (lambda: case("hemi_radius", shape="hemi", V="18π", ask="radius"), "3",
     {"STOPPED_AT_CUBE": "27", "DIVIDED_NOT_ROOTED": "9", "COEFFICIENT_AS_RADIUS": "18"}),
    (lambda: case("cyl3", r=3, h=2), "54",
     {"NO_SQUARE": "18", "LEFT_OUT_PI": "18", "LATERAL_AREA": "36", "ADDED_HEIGHT": "33"}),
    (lambda: case("cone3", r=2, h=5), "20", {"NO_THIRD": "60", "LEFT_OUT_PI": None, "NO_SQUARE": "10"}),
    (lambda: case("cone3", r=3, h=4), "36", {"NO_THIRD": "108", "LEFT_OUT_PI": "12", "NO_SQUARE": "12"}),
    # tier 5
    (lambda: scale_case("scale", "sphere", "radius", 2), "8",
     {"LINEAR_SCALE": "2", "SQUARE_FOR_CUBE": "4", "MULT_BY_EXPONENT": "6"}),
    (lambda: scale_case("scale", "cylinder", "radius", 2), "4", {"LINEAR_SCALE": "2", "CUBE_FOR_SQUARE": "8"}),
    (lambda: scale_case("scale", "cylinder", "height", 3), "3", {"SQUARE_FOR_LINEAR": "9", "CUBE_FOR_LINEAR": "27"}),
    (lambda: scale_case("scale", "cylinder", "radius", F(1, 2)), "1/4", {"LINEAR_SCALE": "1/2", "CUBE_FOR_SQUARE": "1/8"}),
    (lambda: scale_case("scale", "cone", "both", 2), "8",
     {"LINEAR_SCALE": "2", "SQUARE_FOR_CUBE": "4", "MULT_BY_EXPONENT": "6"}),
    (lambda: scale_case("scale_v", "cylinder", "radius", 2, v=3), "12π", {"LINEAR_SCALE": "6π", "CUBE_FOR_SQUARE": "24π"}),
    (lambda: scale_case("scale_v", "cone", "height", 3, v=4), "12π", {"SQUARE_FOR_LINEAR": "36π", "CUBE_FOR_LINEAR": "108π"}),
    (lambda: case("can_ball", n=12, shape="ball"), "8",
     {"CONE_FOR_SPHERE": "4", "HALF_RULE": "6", "TIMES_THREE": "36"}),
    (lambda: case("can_cone", n=12, shape="cone"), "4",
     {"SPHERE_FOR_CONE": "8", "HALF_RULE": "6", "TIMES_THREE": "36"}),
]


@pytest.mark.parametrize("make,correct,wrong", GOLDEN, ids=[str(i) for i in range(len(GOLDEN))])
def test_golden_cases(make, correct, wrong):
    c = make()
    assert c.text == correct
    for key, text in wrong.items():
        assert c.wrong[key] == text, key


def test_hand_worked_prompts_read_back():
    """The prompts the golden cases build read back to the same answers through the independent parser."""
    assert analyze(case("cyl", dim="radius", x=3, h=4).prompt)[0] == ("pi", F(36))
    assert analyze(case("cone", dim="diameter", x=6, h=4).prompt)[0] == ("pi", F(12))
    assert analyze(case("sphere", dim="radius", x=1).prompt)[0] == ("pi", F(4, 3))
    assert analyze(case("cyl_height", C=45, r=3).prompt)[0] == ("num", F(5))
    assert analyze(case("sphere_diam", shape="sphere", V="36π", ask="diameter").prompt)[0] == ("num", F(6))


def test_colliding_misconception_is_never_offered():
    """r = 2: the edge formula 6rh equals the right 3·r·r·h, so a student holding it would pass: never a choice."""
    import random
    c = case("cyl3", r=2, h=5)
    assert c.wrong["LATERAL_AREA"] == c.text
    text, correct, wrongs, expl = G.build_item(c, random.Random(1))
    assert "LATERAL_AREA" not in [k for _, k in wrongs]
    assert correct not in [t for t, _ in wrongs]


# ---------------------------------------------------------------------------------------------
# Independent re-check of every baked item
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("it", ITEMS, ids=IDS)
def test_item_answer_bounds_and_distinct_choices(it):
    assert problems(it) == []


def test_word_choice_items_have_exactly_one_true_answer():
    for it in ITEMS:
        if it["prompt"] in BANK_ANSWERS:
            assert it["choices"].count(BANK_ANSWERS[it["prompt"]]) == 1
            assert len(set(it["choices"])) == len(it["choices"])


def test_every_tier_kind_mix():
    """Each tier shows the question types the plan promises."""
    def has(t, pat):
        return any(re.search(pat, it["prompt"]) for it in by_tier(t))
    assert has(1, r"diameter") and has(1, r"base area") and has(1, r"radius")
    assert has(2, r"cone") and has(2, r"base and height") and has(2, r"diameter")
    assert has(3, r"(?i)hemisphere|half") and has(3, r"using 3 for π") and has(3, r"diameter")
    assert has(4, r"Height\?|height\?|tall") and has(4, r"(?i)radius\?|find the radius") and has(4, r"using 3")
    assert has(5, r"(?i)double") and has(5, r"(?i)halve") and has(5, r"cups")


def test_answer_values_stay_inside_bounds_summary():
    """Spot the headline bounds on the baked answers themselves."""
    for it in ITEMS:
        typ, v = parse_choice(it["choices"][it["answer"]])
        if typ == "pi" and it["tier"] <= 3:
            assert v in (F(4, 3), F(2, 3)) or (v.denominator == 1 and 1 <= v <= 100), it["prompt"]
        if "using 3 for π" in it["prompt"]:
            assert typ == "num" and v.denominator == 1 and 1 <= v <= 100


# ---------------------------------------------------------------------------------------------
# The checker can fail (disproof)
# ---------------------------------------------------------------------------------------------
BAD_PROMPTS = [
    "Cylinder: radius 5, height 10. Volume?",            # 250π: past 100
    "Cylinder: radius 4, height 3. Volume?",             # 48π, but 16 × 3 needs a two-digit factor
    "Sphere: radius 2. Volume?",                         # (32/3)π is no whole coefficient
    "Cone: radius 4, height 9. Volume?",                 # 48π has no times-table route
    "Cone: radius 4, height 3. Volume?",                 # control: 12 ÷ 3 = 4 then 4 × 4, so 16π is reachable
    "Cylinder volume 40π, radius 4. Height?",            # divisor 16 is no times-table fact
    "Cylinder volume 50π, height 2. Radius?",            # 25 is not 4 or 9
    "Cone volume 12π, radius 5. Height?",                # radius 5 has no route
    "Sphere volume (32/3)π. Radius?",                    # not a promised volume
    "Cylinder: radius 3, height 10. Volume, using 3 for π?",  # 270 > 100
    "Cylinder: diameter 5, height 4. Volume?",           # odd diameter
    "Cylinder volume 10π. Double the radius. New volume?",   # 10 × 4 fine, 40 ... (kept as a control below)
    "Cylinder volume 12π. Double the radius. New volume?",   # 12 is a two-digit factor
    "A can holds 20 cups. A ball just fits inside it. Ball holds?",  # 20 is no multiple of 3
]


def test_checker_rejects_bad_prompts():
    """The bounds checker is not a rubber stamp: it rejects prompts that break each bound."""
    expected_ok = {"Cone: radius 4, height 3. Volume?", "Cylinder volume 10π. Double the radius. New volume?"}
    for p in BAD_PROMPTS:
        _, ok = analyze(p)
        assert ok == (p in expected_ok), p


def test_problems_flags_planted_bad_items():
    good = next(it for it in ITEMS if it["prompt"].startswith("Cylinder: radius"))
    assert problems(good) == []
    wrong_answer = dict(good, answer=(good["answer"] + 1) % len(good["choices"]))
    assert any(p.startswith("answer") for p in problems(wrong_answer))
    dup = dict(good, choices=[good["choices"][good["answer"]]] * len(good["choices"]))
    assert "equal-value choices" in problems(dup)
    out_of_bounds = dict(good, prompt="Cylinder: radius 5, height 10. Volume?", choices=["250π", "50π", "25π", "10π"],
                         answer=0)
    assert "bounds" in problems(out_of_bounds)
    equal_value = dict(good, choices=["2π", "4π/2", "3π", "5π"], answer=0)
    assert parse_choice("4π/2")[0] == "txt"  # unparseable text never passes as a number
    assert problems(equal_value)
    same = dict(good, choices=["(4/3)π", "(8/6)π", "π", "2π"], answer=0)
    assert parse_choice("(4/3)π") == parse_choice("(8/6)π")
    assert "equal-value choices" in problems(same)


def test_steps_ok_rejects_what_it_should():
    assert not G.steps_ok([("×", 11, 2, 22)])
    assert not G.steps_ok([("×", 9, 9, 81)] + [("×", 81, 2, 162)])
    assert not G.steps_ok([("÷", 9, 3, 3), ("÷", 3, 3, 1)])
    assert not G.steps_ok([("half", 12, 2, 6)])
    assert not G.steps_ok([("root3", 125, 0, 5)])
    assert G.steps_ok([("×", 3, 3, 9), ("÷", 9, 3, 3), ("half", 6, 2, 3), ("root3", 27, 0, 3), ("root2", 9, 0, 3)])


def test_generator_cannot_reach_forbidden_routes():
    for factors, div in (([4, 4, 3], None), ([5, 5, 3], None), ([4, 4, 9], 3)):
        assert G.find_steps(factors, div) is None, (factors, div)
        assert not reachable(factors, div), (factors, div)
    for factors, div in (([3, 3, 4], 3), ([4, 4, 3], 3)):
        assert G.find_steps(factors, div) is not None and reachable(factors, div)
