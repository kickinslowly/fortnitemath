"""Reference prompt pools for the Facts range cartridges (briefs/facts2, Aaron 2026-10-16).

The spec, as code. Builders COPY the parts for their operation into their generator (cartridges import nothing
from outside themselves); `tests` here are the lead's counts. Run: `.venv/Scripts/python briefs/facts2/pools.py`.

A fact is an ordered pair (a, b). Three prompt FORMS read it:
  R  result unknown          C  second number unknown     S  first number unknown
  Addition       a + b = s:  "a + b = ?" -> s             "a + ? = s" -> b            "? + b = s" -> a
  Subtraction    s − a = b:  "s − a = ?" -> b             "s − ? = b" -> a            "? − a = b" -> s
  Multiplication a × b = p:  "a × b = ?" -> p             "a × ? = p" -> b            "? × b = p" -> a
  Division       p ÷ a = b:  "p ÷ a = ?" -> b             "p ÷ ? = b" -> a            "? ÷ a = b" -> p
Subtraction reads the addition pools backwards (same pairs, same tiers); division reads multiplication's.

A tier is a list of PARTS: (form, pairs, at_least). The generator draws ITEMS_PER_TIER unique prompts per tier
from the union of the tier's parts (a prompt is form + pair, so `3 × 7 = ?` and `7 × 3 = ?` are two prompts, and one
pair may appear in two forms), such that at least `at_least` of the tier's items lie in each part. Parts may overlap:
an item counts toward every part that contains it (add_20 T5: S one-digit >= 6 and S any >= 12 means >= 12 S items,
>= 6 of them one digit + one digit). Fill each part's floor in list order, then draw the rest from the union at random.
Division and missing factors skip pairs that `div_ok` / `mul_ok` reject before drawing.
"""
from __future__ import annotations

ITEMS_PER_TIER = 24


# ------------------------------------------------------------------------------------------------ addition
def regroups(a: int, b: int) -> bool:
    """Addition: the ones make a new ten (subtraction mirror: s's ones are smaller than a's: a trade)."""
    return a % 10 + b % 10 >= 10


def is_tens(a: int, b: int) -> bool:
    """An operand is a non-zero multiple of 10."""
    return (a > 0 and a % 10 == 0) or (b > 0 and b % 10 == 0)


def add_pairs(lo: int, hi: int, low: int = 0) -> list:
    """Every (a, b) with lo <= a + b <= hi and a, b >= low."""
    return [(a, b) for s in range(lo, hi + 1) for a in range(low, s - low + 1) for b in [s - a]]


def add_10() -> dict:
    p = add_pairs(1, 10)
    make_ten = [(a, 10 - a) for a in range(1, 10)]
    return {
        1: [("R", [x for x in p if min(x) <= 2], 0)],
        2: [("R", [x for x in p if min(x) >= 2], 0)],
        3: [("R", [x for x in p if min(x) >= 3], 8), ("C", make_ten, 4), ("S", make_ten, 4)],
        4: [("C", [x for x in p if min(x) >= 1], 0)],
        5: [("S", [x for x in add_pairs(5, 10, 2)], 12), ("C", add_pairs(5, 10, 2), 0)],
    }


def add_20() -> dict:
    p = add_pairs(11, 20, 1)
    one_digit = [x for x in p if max(x) <= 9]
    t1 = [x for x in p if max(x) >= 10 and not regroups(*x)]
    t2 = [x for x in p if min(x) >= 2 and (x[0] == x[1] or abs(x[0] - x[1]) == 1 or (9 in x and max(x) <= 9))]
    missing = [x for x in p if min(x) >= 2]
    return {
        1: [("R", t1, 0)],
        2: [("R", t2, 0)],
        3: [("R", one_digit, 0)],
        4: [("C", [x for x in missing if max(x) <= 9], 12), ("C", missing, 0)],
        5: [("S", [x for x in missing if max(x) <= 9], 6), ("S", missing, 12), ("C", [x for x in missing if max(x) <= 9], 0)],
    }


def add_big(lo: int, hi: int) -> dict:
    """Addition to 50 (sums 21-50) and to 100 (sums 51-100)."""
    p = add_pairs(lo, hi, 2)
    plain = [x for x in p if not is_tens(*x)]
    two_one = lambda xs: [x for x in xs if min(x) <= 9]
    no_reg = [x for x in plain if not regroups(*x)]
    reg = [x for x in plain if regroups(*x)]
    return {
        1: [("R", [x for x in add_pairs(lo, hi, 1) if is_tens(*x)], 0)],
        2: [("R", two_one(no_reg), 8), ("R", [x for x in no_reg if min(x) >= 10], 8)],
        3: [("R", two_one(reg), 8), ("R", [x for x in reg if min(x) >= 10], 8)],
        4: [("C", reg, 12), ("C", plain, 0)],
        5: [("S", reg, 6), ("S", plain, 12), ("C", reg, 6), ("C", plain, 0)],
    }


ADD = {10: add_10, 20: add_20, 50: lambda: add_big(21, 50), 100: lambda: add_big(51, 100)}
ADD_TIER_NAMES = {
    10: ["Plus 0, 1, 2", "Sums to 10", "Make ten", "Missing numbers", "Missing first numbers"],
    20: ["Ten and more", "Doubles and nines", "Cross ten", "Missing numbers", "Missing first numbers"],
    50: ["Tens and ones", "No regrouping", "Regrouping", "Missing numbers", "Missing first numbers"],
    100: ["Tens and ones", "No regrouping", "Regrouping", "Missing numbers", "Missing first numbers"],
}
SUB_TIER_NAMES = {
    10: ["Minus 0, 1, 2", "From 10 or less", "Ten take away", "Missing numbers", "Missing first numbers"],
    20: ["Teens, no trading", "Doubles and nines", "Back across ten", "Missing numbers", "Missing first numbers"],
    50: ["Tens and ones", "No trading", "Trading a ten", "Missing numbers", "Missing first numbers"],
    100: ["Tens and ones", "No trading", "Trading a ten", "Missing numbers", "Missing first numbers"],
}


# ------------------------------------------------------------------------------------------------ multiplication
def mul_pairs(n: int, low: int = 0) -> list:
    return [(a, b) for a in range(low, n + 1) for b in range(low, n + 1)]


EASY = {0, 1, 2, 5, 10}
MID = {3, 4, 9}
HARD = {6, 7, 8}
CORE = MID | HARD  # 3, 4, 6, 7, 8, 9


def big(x, n_from: int = 11) -> bool:
    return max(x) >= n_from


def easy_fact(x) -> bool:
    """Times 0, 1, 2, 5, 10, and 11 x a single digit (the digit twice)."""
    a, b = x
    return bool(EASY & {a, b}) or (11 in x and min(x) <= 9)


def mul_5() -> dict:
    p = mul_pairs(5)
    one_five = mul_pairs(5, 1)
    two_five = mul_pairs(5, 2)
    return {
        1: [("R", [x for x in p if {0, 1, 2, 5} & set(x)], 0)],
        2: [("R", one_five, 0)],
        3: [("R", two_five, 12), ("C", [x for x in one_five if x[0] in (2, 5)], 8)],
        4: [("C", one_five, 0)],
        5: [("S", two_five, 12), ("C", two_five, 0)],
    }


def mul_10() -> dict:
    p = mul_pairs(10)
    core = [x for x in p if set(x) <= CORE]
    return {
        1: [("R", [x for x in p if EASY & set(x)], 0)],
        2: [("R", [x for x in core if set(x) <= MID], 8), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", [x for x in core if set(x) <= HARD], 8), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", core, 12), ("C", mul_pairs(10, 2), 0)],
        5: [("S", core, 12), ("C", core, 0)],
    }


def mul_12() -> dict:
    """Factors 0-12: mul_10's ladder plus the 11 and 12 rows; every tier >= 6 items with an 11 or a 12."""
    p = mul_pairs(12)
    core = [x for x in p if set(x) <= CORE]
    t1 = [x for x in p if easy_fact(x)]
    t2_new = [x for x in p if 12 in x and min(x) in MID]
    t3_new = [x for x in p if not easy_fact(x) and big(x) and (HARD & set(x) or min(x) >= 11)]
    core12 = [x for x in mul_pairs(12, 3) if not easy_fact(x)]
    return {
        1: [("R", [x for x in t1 if big(x)], 8), ("R", t1, 0)],
        2: [("R", t2_new, 6), ("R", [x for x in core if set(x) <= MID], 6), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", t3_new, 8), ("R", [x for x in core if set(x) <= HARD], 6), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", [x for x in core12 if big(x)], 6), ("C", core, 8), ("C", mul_pairs(12, 2), 0)],
        5: [("S", [x for x in core12 if big(x)], 6), ("S", core12, 6), ("C", [x for x in core12 if big(x)], 4), ("C", core12, 0)],
    }


def mul_15() -> dict:
    """Factors 0-15: the 11-15 rows are the point; every tier >= half its items with a factor 11-15."""
    p = mul_pairs(15)
    t1 = [x for x in p if easy_fact(x)]
    teen = lambda x: max(x) >= 11
    t2 = [x for x in p if teen(x) and not easy_fact(x) and min(x) in (3, 4)]
    t3 = [x for x in p if teen(x) and not easy_fact(x) and (min(x) in (6, 7, 8, 9) or min(x) >= 11)]
    core = [x for x in p if set(x) <= CORE]
    hard15 = [x for x in mul_pairs(15, 3) if not easy_fact(x)]
    return {
        1: [("R", [x for x in t1 if teen(x)], 12), ("R", t1, 0)],
        2: [("R", t2, 12), ("R", [x for x in core if MID & set(x)], 0)],
        3: [("R", t3, 12), ("R", [x for x in core if HARD & set(x)], 0)],
        4: [("C", [x for x in hard15 if teen(x)], 12), ("C", hard15, 0)],
        5: [("S", [x for x in hard15 if teen(x)], 8), ("S", hard15, 4), ("C", [x for x in hard15 if teen(x)], 4), ("C", hard15, 0)],
    }


MUL = {5: mul_5, 10: mul_10, 12: mul_12, 15: mul_15}
MUL_TIER_NAMES = {
    5: ["Times 0, 1, 2, 5", "All to 5 × 5", "Times 2 to 5", "Missing factors", "Missing first factors"],
    10: ["Times 0, 1, 2, 5, 10", "Times 3, 4, 9", "Times 6, 7, 8", "Missing factors", "Missing first factors"],
    12: ["Easy rows and 11s", "Times 3, 4, 9, 12", "Times 6, 7, 8, 12", "Missing factors", "Missing first factors"],
    15: ["Easy rows to 15", "Teens times 3 and 4", "Teens times 6 to 15", "Missing factors", "Missing first factors"],
}
DIV_TIER_NAMES = {
    5: ["Easy: 0, 1, 2, 5", "All to 25 ÷ 5", "Facts with 2 to 5", "Missing divisors", "Missing dividends"],
    10: ["Easy: 0, 1, 2, 5, 10", "Facts with 3, 4, 9", "Facts with 6, 7, 8", "Missing divisors", "Missing dividends"],
    12: ["Easy rows and 11s", "Facts with 3, 4, 9, 12", "Facts with 6, 7, 8, 12", "Missing divisors", "Missing dividends"],
    15: ["Easy rows to 15", "Teens and 3s, 4s", "Teens and 6 to 15", "Missing divisors", "Missing dividends"],
}


def div_ok(form: str, x) -> bool:
    """Division reads (a, b) as p ÷ a = b: never divide by 0; a missing number is never ambiguous (no 0 ÷ ? = 0)."""
    a, b = x
    if a == 0:
        return False
    return form == "R" or b >= 1


def mul_ok(form: str, x) -> bool:
    """A missing factor is never ambiguous: no 0 × ? = 0."""
    return form == "R" or min(x) >= 1


# ------------------------------------------------------------------------------------------------ counts
def check(name: str, tiers: dict, ok=lambda form, x: True) -> list:
    problems = []
    for t, parts in sorted(tiers.items()):
        union = set()
        for form, pairs, need in parts:
            usable = {(form, x) for x in pairs if ok(form, x)}
            if len(usable) < need:
                problems.append(f"{name} T{t}: part {form} has {len(usable)} < {need}")
            union |= usable
        need_total = sum(n for _, _, n in parts)
        if need_total > ITEMS_PER_TIER:
            problems.append(f"{name} T{t}: parts ask {need_total} > {ITEMS_PER_TIER}")
        print(f"  {name:8} T{t}: {len(union):4} prompts  " + ", ".join(f"{f}:{len({x for x in ps if ok(f, x)})}>={n}" for f, ps, n in parts))
        if len(union) < ITEMS_PER_TIER:
            problems.append(f"{name} T{t}: only {len(union)} prompts")
    return problems


if __name__ == "__main__":
    bad = []
    for r, f in ADD.items():
        bad += check(f"add-{r}", f())
        bad += check(f"sub-{r}", f())  # the same pairs read backwards
    for r, f in MUL.items():
        bad += check(f"mul-{r}", f(), mul_ok)
        bad += check(f"div-{r}", f(), div_ok)
    for names in (ADD_TIER_NAMES, SUB_TIER_NAMES, MUL_TIER_NAMES, DIV_TIER_NAMES):
        for r, ns in names.items():
            for n in ns:
                if len(n) > 24:
                    bad.append(f"tier name over 24: {n!r}")
    print("\n".join(bad) if bad else "every tier has enough prompts")
