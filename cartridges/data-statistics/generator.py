"""Procedural generator for the data-statistics cartridge (fnm-cart/1, grade 6, 6.SP.A.2/A.3/B.5c).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every item is built from a small data list, and every value (correct and wrong) is computed from
  that list by a named rule in this file. A wrong choice is the value a student holding one
  misconception gets; ``ARITH`` (near misses) only fills an item up to 4 choices.
* Candidates are listed most specific first; a value already taken (or equal to the answer) is
  skipped, so the first rule that produced a value owns its label.
* PROTOCOL §4b data bounds: 3-7 values, each 0-20, sum <= 100; every mean/median/MAD that needs a
  division is an integer 2-10 (a times-table fact). ``check_bounds`` is the gate every item passes.

Tiers
-----
1. Range & Mode   2. Median (odd and even counts)   3. Mean
4. Missing value from a mean (4 choices) + outlier: which measure moves more/less (2 choices)
5. Mean absolute deviation
"""
from __future__ import annotations

import random
from collections import Counter
from fractions import Fraction

LO, HI = 0, 20  # each data value
MAX_SUM = 100
Q_LO, Q_HI = 2, 10  # quotient of every division the correct working needs


# ---------------------------------------------------------------------------------------------
# Statistics (Fractions, so nothing is silently rounded)
# ---------------------------------------------------------------------------------------------
def mean(xs) -> Fraction:
    return Fraction(sum(xs), len(xs))


def median(xs) -> Fraction:
    s = sorted(xs)
    n = len(s)
    if n % 2:
        return Fraction(s[n // 2])
    return Fraction(s[n // 2 - 1] + s[n // 2], 2)


def mad(xs) -> Fraction:
    m = mean(xs)
    return Fraction(sum(abs(x - m) for x in xs), len(xs))


def _int(v):
    """int(v) when v is a whole number, else None."""
    v = Fraction(v)
    return int(v) if v.denominator == 1 else None


def fmt(xs) -> str:
    return ", ".join(str(x) for x in xs)


# ---------------------------------------------------------------------------------------------
# Bounds gate (PROTOCOL §4b, data)
# ---------------------------------------------------------------------------------------------
def _q_ok(v) -> bool:
    """A quotient the correct working needs: integer 2..10."""
    v = Fraction(v)
    return v.denominator == 1 and Q_LO <= v <= Q_HI


def check_bounds(kind: str, xs, extra=None) -> list:
    """Violations (empty = fine) for one item's data. ``kind`` names what the correct working
    computes; ``extra`` is the missing value (missing) or the new value (outlier)."""
    bad = []
    full = list(xs) + ([extra] if kind in ("missing", "outlier") else [])
    if not 3 <= len(full) <= 7:
        bad.append(f"{len(full)} values (want 3-7)")
    if any(not LO <= x <= HI for x in full):
        bad.append(f"value outside {LO}-{HI}: {full}")
    if sum(full) > MAX_SUM:
        bad.append(f"sum {sum(full)} > {MAX_SUM}")
    if kind == "median" and len(xs) % 2 == 0 and not _q_ok(median(xs)):
        bad.append(f"even-count median {median(xs)} not an integer 2-10")
    if kind in ("mean", "missing", "mad") and not _q_ok(mean(full)):
        bad.append(f"mean {mean(full)} not an integer 2-10")
    if kind == "mad" and not _q_ok(mad(xs)):
        bad.append(f"MAD {mad(xs)} not an integer 2-10")
    if kind == "outlier":
        for m in (mean(xs), mean(full)):
            if not _q_ok(m):
                bad.append(f"outlier mean {m} not an integer 2-10")
        for m, data in ((median(xs), xs), (median(full), full)):
            if len(data) % 2 == 0 and not _q_ok(m):
                bad.append(f"outlier median {m} not an integer 2-10")
            elif m.denominator != 1:
                bad.append(f"outlier median {m} not an integer")
        if any(abs(extra - x) < 10 for x in xs):
            bad.append(f"new value {extra} within 10 of the data")
        if not abs(mean(full) - mean(xs)) > abs(median(full) - median(xs)):
            bad.append("mean does not move more than the median")
    return bad


# ---------------------------------------------------------------------------------------------
# Item assembly
# ---------------------------------------------------------------------------------------------
def _arith(correct: int):
    return [correct + d for d in (1, -1, 2, -2, 3, -3, 4)]


def make_item(tier, prompt, correct, cands, pos, expl, rng, n_choices=4, fill=True, avoid=()):
    """``cands`` = [(label, value)] most specific first. Wrong values distinct from each other and
    the answer; ARITH fills only when ``fill`` and never takes a value any misconception reading
    produces (``cands`` plus ``avoid``). None if the item cannot be built."""
    wrong, seen = [], {correct}
    for lab, v in cands:
        if v is None or v in seen or (isinstance(v, int) and not 0 <= v <= 999):
            continue
        seen.add(v)
        wrong.append((lab, v))
        if len(wrong) == n_choices - 1:
            break
    if fill:
        seen |= {v for _, v in cands} | set(avoid)
        for v in _arith(correct):
            if len(wrong) == n_choices - 1:
                break
            if 0 <= v and v not in seen:
                seen.add(v)
                wrong.append(("ARITH", v))
    if len(wrong) != n_choices - 1 or len(prompt) > 60 or len(expl) > 160:
        return None
    rng.shuffle(wrong)
    pairs = wrong[:pos] + [(None, correct)] + wrong[pos:]
    return {
        "tier": tier,
        "prompt": prompt,
        "choices": [str(v) for _, v in pairs],
        "answer": pos,
        "misconceptions": [lab for lab, _ in pairs],
        "explanation": expl,
    }


def _distinct(rng, n, lo=LO, hi=HI):
    return rng.sample(range(lo, hi + 1), n)


# --- T1: range and mode -------------------------------------------------------------------------
def t1_range(rng, pos):
    n = rng.randint(5, 7)
    xs = _distinct(rng, n, 1, HI)
    if check_bounds("range", xs):
        return None
    hi, lo = max(xs), min(xs)
    fl = abs(xs[0] - xs[-1])
    if fl in (0, hi - lo):  # the ends must not already be the max and min
        return None
    prompt = f"Find the range: {fmt(xs)}"
    expl = f"Largest {hi} − smallest {lo} = {hi - lo}."
    return make_item(1, prompt, hi - lo, [("LARGEST", hi), ("FIRST_LAST", fl)], pos, expl, rng)


MODE_PATTERNS = ((3, 2, 1, 1), (3, 2, 1), (4, 2, 1), (3, 2, 1, 1))


def t1_mode(rng, pos):
    pattern = rng.choice(MODE_PATTERNS)
    vals = _distinct(rng, len(pattern), 1, HI)
    xs = [v for v, k in zip(vals, pattern) for _ in range(k)]
    rng.shuffle(xs)
    if check_bounds("mode", xs):
        return None
    mode, runner, top = vals[0], vals[1], max(xs)
    count = pattern[0]
    if top in (mode, runner) or count in (mode, runner, top):
        return None
    prompt = f"Find the mode: {fmt(xs)}"
    expl = (f"{mode} shows up {count} times, more than any other value ({runner} shows up 2 times). "
            f"Mode = {mode}.")
    cands = [("MOST_FOR_MODE", top), ("COUNT_FOR_MODE", count), ("MISCOUNT", runner)]
    return make_item(1, prompt, mode, cands, pos, expl, rng, fill=False)


# --- T2: median -----------------------------------------------------------------------------------
def t2_median(rng, pos, even):
    n = rng.choice((4, 6)) if even else rng.choice((5, 7))
    xs = _distinct(rng, n, 1, HI)
    if check_bounds("median", xs) or mean(xs) == median(xs):
        return None  # the MEAN_FOR_MEDIAN reading must not be accidentally right
    s = sorted(xs)
    med = _int(median(xs))
    if med is None:
        return None
    k = n // 2
    if even:
        listed = _int(Fraction(xs[k - 1] + xs[k], 2))
        cands = [("ONE_MIDDLE", s[k - 1]), ("ONE_MIDDLE", s[k]),
                 ("UNSORTED", listed), ("MEAN_FOR_MEDIAN", _int(mean(xs)))]
        expl = (f"In order: {fmt(s)}. Middle two {s[k - 1]} and {s[k]}: "
                f"({s[k - 1]} + {s[k]}) ÷ 2 = {med}.")
    else:
        if xs[k] == med:
            return None  # the list as written must not already put the median in the middle
        nxt = s[k + rng.choice((-1, 1))]
        cands = [("UNSORTED", xs[k]), ("MEAN_FOR_MEDIAN", _int(mean(xs))), ("NEXT_TO_MIDDLE", nxt)]
        avoid = (s[k - 1], s[k + 1])
        expl = f"In order: {fmt(s)}. The middle one is {med}."
    if (cands[2][1] if even else cands[0][1]) in (None, med):
        return None  # the unsorted reading must give a wrong value
    prompt = f"Find the median: {fmt(xs)}"
    return make_item(2, prompt, med, cands, pos, expl, rng, avoid=avoid if not even else ())


# --- T3: mean -------------------------------------------------------------------------------------
def _with_mean(rng, n, m):
    """n values 0..20 with mean m (rejection sampled), or None."""
    xs = [rng.randint(LO, HI) for _ in range(n - 1)]
    last = n * m - sum(xs)
    if not LO <= last <= HI:
        return None
    return xs + [last]


def t3_mean(rng, pos):
    n = rng.randint(3, 5)
    m = rng.randint(Q_LO, Q_HI)
    xs = _with_mean(rng, n, m)
    if xs is None or len(set(xs)) < n - 1 or check_bounds("mean", xs) or median(xs) == m:
        return None  # median == mean would make the MEDIAN_FOR_MEAN reading accidentally right
    total = sum(xs)
    wc = [("WRONG_COUNT", _int(Fraction(total, c))) for c in (n - 1, n + 1)]
    rng.shuffle(wc)
    cands = [("SUM_ONLY", total), ("MEDIAN_FOR_MEAN", _int(median(xs)))] + wc
    prompt = f"Find the mean: {fmt(xs)}"
    expl = f"{' + '.join(map(str, xs))} = {total}, and {total} ÷ {n} = {m}."
    return make_item(3, prompt, m, cands, pos, expl, rng)


# --- T4: missing value and outliers ----------------------------------------------------------------
def t4_missing(rng, pos):
    n = rng.randint(3, 5)
    m = rng.randint(Q_LO, Q_HI)
    xs = _with_mean(rng, n, m)
    if xs is None:
        return None
    rng.shuffle(xs)
    gap = rng.randrange(n)
    missing, known = xs[gap], xs[:gap] + xs[gap + 1:]
    if check_bounds("missing", known, missing) or missing == m or sum(known) == 0:
        return None  # stopping at the mean (or at the total) must not be accidentally right
    shown = [str(x) for x in known]
    shown.insert(gap, "?")
    total = m * n
    cands = [("MEAN_AS_MISSING", m), ("TOTAL_ONLY", total),
             ("MISSING_NOT_COUNTED", m * (n - 1) - sum(known))]
    prompt = f"The mean of {', '.join(shown)} is {m}. What is ?"
    expl = (f"Total = {m} × {n} = {total}. Known: {' + '.join(map(str, known))} = {sum(known)}. "
            f"{total} − {sum(known)} = {missing}.")
    return make_item(4, prompt, missing, cands, pos, expl, rng)


def t4_outlier(rng, pos, ask_more):
    xs = sorted(_distinct(rng, 4, LO, HI))
    new = rng.randint(LO, HI)
    if check_bounds("outlier", xs, new):
        return None
    full = xs + [new]
    m0, m1 = _int(mean(xs)), _int(mean(full))
    d0, d1 = _int(median(xs)), _int(median(full))
    word = "more" if ask_more else "less"
    prompt = f"New value {new} joins {fmt(xs)}. Which changes {word}?"
    expl = (f"Mean {m0} to {m1}, median {d0} to {d1}. The far-off {new} pulls the mean a lot; "
            f"the median barely moves.")
    correct, wrong = ("Mean", "Median") if ask_more else ("Median", "Mean")
    return make_item(4, prompt, correct, [("MEDIAN_MOVES", wrong)], pos, expl, rng,
                     n_choices=2, fill=False)


# --- T5: mean absolute deviation ----------------------------------------------------------------
def t5_mad(rng, pos):
    n = rng.randint(3, 5)
    m = rng.randint(Q_LO, Q_HI)
    xs = _with_mean(rng, n, m)
    if xs is None or len(set(xs)) < n or check_bounds("mad", xs):
        return None
    if mad(xs) in (m, max(xs) - min(xs)):
        return None  # stopping at the mean (or giving the range) must not be accidentally right
    rng.shuffle(xs)
    devs = [abs(x - m) for x in xs]
    d = _int(mad(xs))
    cands = [("RANGE_FOR_MAD", max(xs) - min(xs)), ("MEAN_FOR_MAD", m),
             ("SUM_DEVIATIONS", sum(devs))]
    prompt = f"Mean absolute deviation (MAD): {fmt(xs)}"
    expl = (f"Mean {sum(xs)} ÷ {n} = {m}. Distances {fmt(devs)} sum to {sum(devs)}. "
            f"{sum(devs)} ÷ {n} = {d}.")
    item = make_item(5, prompt, d, cands, pos, expl, rng)
    if item and item["misconceptions"].count("ARITH") > 1:
        return None
    return item


# ---------------------------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------------------------
def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def _plan(tier: int, count: int, rng):
    """[(builder, n_choices)] for one tier, in a shuffled order."""
    if tier == 1:
        kinds = [(t1_range, 4)] * (count // 2) + [(t1_mode, 4)] * (count - count // 2)
    elif tier == 2:
        n_even = count * 3 // 10
        kinds = ([(lambda r, p: t2_median(r, p, True), 4)] * n_even
                 + [(lambda r, p: t2_median(r, p, False), 4)] * (count - n_even))
    elif tier == 3:
        kinds = [(t3_mean, 4)] * count
    elif tier == 4:
        n_out = count * 3 // 10
        n_out -= n_out % 2
        kinds = ([(lambda r, p: t4_outlier(r, p, True), 2)] * (n_out // 2)
                 + [(lambda r, p: t4_outlier(r, p, False), 2)] * (n_out // 2)
                 + [(t4_missing, 4)] * (count - n_out))
    else:
        kinds = [(t5_mad, 4)] * count
    rng.shuffle(kinds)
    return kinds


def gen_tier(tier: int, count: int, rng: random.Random, max_attempts: int = 500000):
    kinds = _plan(tier, count, rng)
    # balanced answer positions, separately for each choice count
    pos_by_n = {}
    for n in sorted({k for _, k in kinds}):
        pos_by_n[n] = _balanced(sum(1 for _, k in kinds if k == n), n, rng)
    used_by_n = {n: 0 for n in pos_by_n}
    items, prompts, attempts = [], set(), 0
    while len(items) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"tier {tier}: could not generate {count} items")
        build, n = kinds[len(items)]
        item = build(rng, pos_by_n[n][used_by_n[n]])
        if item is None or item["prompt"] in prompts:
            continue
        prompts.add(item["prompt"])
        used_by_n[n] += 1
        items.append(item)
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
