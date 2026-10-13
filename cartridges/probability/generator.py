"""Procedural generator for the probability cartridge (fnm-cart/1, CCSS 7.SP.A.2, C.5-C.8).

Contract (PROTOCOL.md §3): ``generate(manifest, rng) -> list[dict]`` returning items in the §4 shape
without ``id``. Stdlib only, deterministic for a given ``rng``, imports nothing from other cartridges.

Design
------
* Every item starts as a ``Spec``: the prompt, the correct choice, an ORDERED list of modelled wrong
  choices (label, value) and an explanation. Each tier is a list of *families* (a builder that returns
  every Spec of one kind) with a quota; the tier takes ``quota`` valid specs from each family.
* A wrong choice comes from a *rule* (a function like ``uniform_wrongs`` or ``expect_wrongs``) that
  returns ``[(label, value)]`` in collision priority: when two rules give the same value the first
  label wins and the later one is dropped, so a value never appears twice. ``None`` means the rule
  does not apply to this item. ``ARITH`` (a near value) only fills up to 4 choices and never equals
  any modelled value.
* Values are ``Fraction``s (probabilities), ints (counts) or strings (words, lists). A choice's
  identity is its value, so two choices can never be equal in value (``1/2`` and ``2/4`` are the same
  Fraction). Each item writes its choices in ONE form (fractions, decimals, percents, counts, words).
* Probabilities are always in simplest form with denominators of 12 or less; improper or negative
  wrong values appear only where the modelled misconception produces them (T1 range questions, T3
  complements and estimates).
* Pools that would be huge (colors, contexts, scale factors) draw their free parameters from the
  rng, so the bake is deterministic and nothing iterates a set of strings.

Bounds: see the manifest's ``bounds`` string; tests/test_probability.py walks every baked item.
"""
from __future__ import annotations

import random
from collections import Counter
from fractions import Fraction as Fr
from math import gcd
from typing import Callable, List, NamedTuple, Optional

MINUS = "−"  # U+2212
MAX_CHOICE = 14  # PROTOCOL §5 rule 6
MAX_PROMPT = 60
MAX_EXPL = 160
MAX_DISTRACTOR = 999


# ---------------------------------------------------------------------------------------------
# Text for values
# ---------------------------------------------------------------------------------------------
def ftxt(v) -> str:
    """Fraction text: ``3/8``, ``1/2``, ``0``, ``1``, ``−1/4`` (improper stays improper: ``7/6``)."""
    v = Fr(v)
    n, d = abs(v.numerator), v.denominator
    s = str(n) if d == 1 else f"{n}/{d}"
    return MINUS + s if v < 0 else s


def dtxt(v) -> str:
    """Decimal text with at most 2 places: ``0.3``, ``0.25``, ``1.5``, ``0``."""
    v = Fr(v)
    x = abs(v) * 100
    assert x.denominator == 1, v
    whole, rest = divmod(int(x), 100)
    if rest == 0:
        s = str(whole)
    elif rest % 10 == 0:
        s = f"{whole}.{rest // 10}"
    else:
        s = f"{whole}.{rest:02d}"
    return MINUS + s if v < 0 else s


def ptxt(v) -> str:
    """Percent text: ``30%``, ``125%``, ``−10%``."""
    v = Fr(v)
    x = abs(v) * 100
    assert x.denominator == 1, v
    s = f"{int(x)}%"
    return MINUS + s if v < 0 else s


def itxt(n) -> str:
    n = int(n)
    return MINUS + str(-n) if n < 0 else str(n)


def stxt(s) -> str:
    return s


class Cand(NamedTuple):
    label: Optional[str]  # misconception key, "ARITH", or None for the correct choice
    key: object  # identity of the VALUE (Fraction / int / str); None = rule does not apply
    text: str


class Spec(NamedTuple):
    prompt: str
    correct: Cand
    wrongs: list  # [Cand] in label priority order
    expl: str
    fill: Optional[Callable] = None  # rng -> [Cand("ARITH", ...)]
    min_real: int = 2  # modelled wrong choices required (the rest is ARITH)


def W(rules, fmt) -> list:
    """[(label, value)] -> [Cand]; a value of None (rule not applicable) stays None."""
    return [Cand(lab, v, fmt(v) if v is not None else "") for lab, v in rules]


def lt1(v):
    """A modelled wrong probability is kept only if it is strictly between 0 and 1."""
    return v if v is not None and 0 < v < 1 else None


def fr_expl(k: int, n: int) -> str:
    """``3/8`` or ``2/6 = 1/3``: the fraction as counted, then simplified when it simplifies."""
    f = Fr(k, n)
    return f"{k}/{n}" if (f.numerator, f.denominator) == (k, n) else f"{k}/{n} = {ftxt(f)}"


# ---------------------------------------------------------------------------------------------
# ARITH fillers
# ---------------------------------------------------------------------------------------------
ALL_FRACS = sorted({Fr(n, d) for d in range(2, 13) for n in range(1, d)})


def frac_fill(correct: Fr, n: Optional[int] = None) -> Callable:
    """Near fractions: first the same count over the same total (k +/- 1..3 out of n), then the
    nearest fractions with denominators up to 12."""
    def fill(rng: random.Random) -> list:
        m = n or correct.denominator
        k = int(correct * m)
        same = []
        for dn in (1, -1, 2, -2, 3, -3):
            f = Fr(k + dn, m)
            if 0 < k + dn < m and f not in same and f != correct:
                same.append(f)
        rng.shuffle(same)
        # then the nearest fractions whose denominator is a divisor or multiple of the total
        kin = [f for f in ALL_FRACS if f != correct and (m % f.denominator == 0 or f.denominator % m == 0)]
        near = sorted(kin, key=lambda f: (abs(f - correct), f))[:5]
        rng.shuffle(near)
        return [Cand("ARITH", f, ftxt(f)) for f in same + near]

    return fill


def step_fill(correct: Fr, text_fn, steps=(Fr(1, 10), Fr(-1, 10), Fr(2, 10), Fr(-2, 10))) -> Callable:
    def fill(rng: random.Random) -> list:
        near = [correct + s for s in steps]
        rng.shuffle(near)
        return [Cand("ARITH", v, text_fn(v)) for v in near if 0 < v < 1]

    return fill


def int_fill(correct: int) -> Callable:
    def fill(rng: random.Random) -> list:
        near = [correct + d for d in (1, -1, 2, -2)]
        far = [correct + d for d in (3, -3, 5, -5, 10)]
        rng.shuffle(near)
        rng.shuffle(far)
        return [Cand("ARITH", v, str(v)) for v in near + far if 1 <= v <= MAX_DISTRACTOR]

    return fill


# ---------------------------------------------------------------------------------------------
# T1: how likely?
# ---------------------------------------------------------------------------------------------
IMPOSSIBLE, UNLIKELY, EQUALLY, LIKELY, CERTAIN = "Impossible", "Unlikely", "Equally likely", "Likely", "Certain"


def word_for(v: Fr) -> str:
    """The likelihood word for a probability (the T1 items only use clear cases)."""
    if v == 0:
        return IMPOSSIBLE
    if v == 1:
        return CERTAIN
    if v == Fr(1, 2):
        return EQUALLY
    return UNLIKELY if v < Fr(1, 2) else LIKELY


# Per correct word: the wrong words in priority order. No wrong word ever overlaps the right one
# (never "Unlikely" beside "Impossible", never "Likely" beside "Certain").
WORD_WRONGS = {
    IMPOSSIBLE: [("SCALE_FLIP", CERTAIN), ("HALF_WORD", EQUALLY), ("WORD_MIXUP", LIKELY)],
    CERTAIN: [("SCALE_FLIP", IMPOSSIBLE), ("HALF_WORD", EQUALLY), ("WORD_MIXUP", UNLIKELY)],
    UNLIKELY: [("SCALE_FLIP", LIKELY), ("HALF_WORD", EQUALLY), ("ROUNDED", IMPOSSIBLE)],
    LIKELY: [("SCALE_FLIP", UNLIKELY), ("HALF_WORD", EQUALLY), ("ROUNDED", CERTAIN)],
    EQUALLY: [("HALF_LEANS", LIKELY), ("HALF_LEANS", UNLIKELY), ("WORD_MIXUP", IMPOSSIBLE)],
}

WHERE = {IMPOSSIBLE: "exactly 0", CERTAIN: "exactly 1", EQUALLY: "exactly half",
         LIKELY: "well over half", UNLIKELY: "well under half"}


def word_spec(prompt: str, word: str, expl: str) -> Spec:
    return Spec(prompt, Cand(None, word, word),
                [Cand(lab, w, w) for lab, w in WORD_WRONGS[word]], expl, None, min_real=3)


def _a_expl(x: str, word: str) -> str:
    return {
        IMPOSSIBLE: f"{x} means it can never happen: impossible.",
        CERTAIN: f"{x} means it always happens: certain.",
        EQUALLY: f"{x} is halfway between 0 and 1: equally likely.",
        LIKELY: f"{x} is well over half, near 1, so the event is likely.",
        UNLIKELY: f"{x} is well under half, near 0, so the event is unlikely.",
    }[word]


A_DEC = ["0", "0.1", "0.2", "0.25", "0.5", "0.75", "0.8", "0.9", "1"]
A_PCT = ["0%", "10%", "20%", "25%", "50%", "75%", "80%", "90%", "100%"]
A_FRAC = ["0", "1/12", "1/10", "1/5", "1/4", "1/2", "3/4", "4/5", "9/10", "11/12", "1"]


def _parse_chance(x: str) -> Fr:
    return Fr(x[:-1]) / 100 if x.endswith("%") else Fr(x)


def t1_numbers(rng) -> list:
    out = []
    forms = ((lambda x: f"A probability of {x} means the event is?", A_DEC),
             (lambda x: f"A {x} chance means the event is?", A_PCT),
             (lambda x: f"P(event) = {x}. How likely is the event?", A_FRAC))
    for tmpl, xs in forms:
        for x in xs:
            w = word_for(_parse_chance(x))
            out.append(word_spec(tmpl(x), w, _a_expl(x, w)))
    return out


# (text, probability). Probabilities stay out of the (1/4, 3/4) gap, so each has one clear word.
T1_EVENTS = [
    ("Roll a die. Get a 7.", Fr(0)),
    ("Roll a die. Get a 0.", Fr(0)),
    ("Bag has only blue marbles. Pick red.", Fr(0)),
    ("Cards 1 to 5. Pick a 9.", Fr(0)),
    ("Roll a die. Get a number from 1 to 6.", Fr(1)),
    ("Roll a die. Get a number under 7.", Fr(1)),
    ("Bag has only red marbles. Pick red.", Fr(1)),
    ("Cards 1 to 5. Pick a number under 10.", Fr(1)),
    ("Flip a fair coin. Get heads.", Fr(1, 2)),
    ("Roll a die. Get an even number.", Fr(1, 2)),
    ("Roll a die. Get an odd number.", Fr(1, 2)),
    ("Bag: 5 red, 5 blue. Pick red.", Fr(1, 2)),
    ("Spinner is half red. Land on red.", Fr(1, 2)),
    ("Cards 1 to 10. Pick an even number.", Fr(1, 2)),
    ("Bag: 9 red, 1 blue. Pick red.", Fr(9, 10)),
    ("Bag: 8 red, 2 blue. Pick red.", Fr(4, 5)),
    ("Bag: 7 red, 1 blue. Pick red.", Fr(7, 8)),
    ("Roll a die. Get a number under 6.", Fr(5, 6)),
    ("Roll a die. Get a number over 1.", Fr(5, 6)),
    ("Cards 1 to 10. Pick a number over 1.", Fr(9, 10)),
    ("Spinner is 3/4 red. Land on red.", Fr(3, 4)),
    ("Bag: 1 red, 9 blue. Pick red.", Fr(1, 10)),
    ("Bag: 1 red, 7 blue. Pick red.", Fr(1, 8)),
    ("Roll a die. Get a 6.", Fr(1, 6)),
    ("Roll a die. Get a number over 5.", Fr(1, 6)),
    ("Cards 1 to 10. Pick a 7.", Fr(1, 10)),
    ("Spinner is 1/4 red. Land on red.", Fr(1, 4)),
    ("Bag: 2 red, 8 blue. Pick red.", Fr(1, 5)),
    ("Cards 1 to 10. Pick a number over 8.", Fr(1, 5)),
]


def t1_events(rng) -> list:
    out = []
    for text, p in T1_EVENTS:
        w = word_for(p)
        out.append(word_spec(f"{text} How likely?", w, f"P = {ftxt(p)}, {WHERE[w]}: {w.lower()}."))
    return out


# --- range questions: which could / can't be a probability ----------------------------------------
_VALID = [Fr(0), Fr(1, 10), Fr(1, 5), Fr(1, 4), Fr(2, 5), Fr(1, 2), Fr(3, 5), Fr(3, 4), Fr(9, 10), Fr(1)]
_VALID_FRAC = [Fr(0), Fr(1, 10), Fr(1, 5), Fr(1, 4), Fr(1, 3), Fr(2, 5), Fr(1, 2), Fr(3, 5), Fr(2, 3),
               Fr(3, 4), Fr(9, 10), Fr(1)]
RANGE_FORMS = {
    "dec": (dtxt, _VALID, [Fr(11, 10), Fr(6, 5), Fr(3, 2), Fr(2), Fr(3)],
            [Fr(-1, 10), Fr(-3, 10), Fr(-1, 2), Fr(-1)]),
    "pct": (ptxt, _VALID, [Fr(11, 10), Fr(6, 5), Fr(3, 2), Fr(2), Fr(3)],
            [Fr(-1, 10), Fr(-3, 10), Fr(-1, 2), Fr(-1)]),
    "frac": (ftxt, _VALID_FRAC, [Fr(6, 5), Fr(5, 4), Fr(4, 3), Fr(3, 2), Fr(5, 3), Fr(2), Fr(3)],
             [Fr(-1, 4), Fr(-1, 2), Fr(-3, 4), Fr(-1)]),
}
RANGE_CTX = ["a probability", "the chance of rain", "the chance of winning", "the chance of a hit",
             "the chance of drawing red", "the chance of a goal", "the chance of snow", "the chance of a tie"]


def range_could(rng) -> list:
    out = []
    for ctx in RANGE_CTX:
        form = rng.choice(sorted(RANGE_FORMS))
        txt, valid, over, neg = RANGE_FORMS[form]
        right = rng.choice(valid)
        wrongs = ([Cand("OVER_ONE", v, txt(v)) for v in over] +
                  [Cand("NEGATIVE", v, txt(v)) for v in neg])
        rng.shuffle(wrongs)
        out.append(Spec(f"Which could be {ctx}?", Cand(None, right, txt(right)), wrongs,
                        f"A probability is from 0 to 1, so the one that fits is {txt(right)}.", None, 3))
    return out


def range_cant(rng) -> list:
    out = []
    for ctx in RANGE_CTX:
        form = rng.choice(sorted(RANGE_FORMS))
        txt, valid, over, neg = RANGE_FORMS[form]
        right = rng.choice(over + neg)
        why = "more than 1" if right > 1 else "less than 0"
        wrongs = [Cand("EDGE_EXCLUDED" if v in (0, 1) else "RANGE_CHECK", v, txt(v)) for v in valid]
        out.append(Spec(f"Which can't be {ctx}?", Cand(None, right, txt(right)), wrongs,
                        f"{txt(right)} is {why}, and a probability is from 0 to 1. It can't be {txt(right)}.",
                        None, 3))
    return out


def range_extremes(rng) -> list:
    def c(lab, text):
        return Cand(lab, text, text)

    return [
        Spec("As a decimal, the greatest a probability can be?", c(None, "1"),
             [c("PERCENT_MIX", "100"), c("OVER_ONE", "No limit"), c("ARITH", "10")],
             "A sure thing has probability 1, and nothing is more likely than sure: 1.", None, 3),
        Spec("As a decimal, the least a probability can be?", c(None, "0"),
             [c("SCALE_FLIP", "1"), c("NEGATIVE", MINUS + "1"), c("NEGATIVE", "No limit")],
             "An impossible event has probability 0, and nothing is less likely: 0.", None, 3),
        Spec("As a decimal, a probability is between which numbers?", c(None, "0 and 1"),
             [c("PERCENT_MIX", "0 and 100"), c("NEGATIVE", MINUS + "1 and 1"), c("ARITH", "0 and 10")],
             "Impossible is 0 and certain is 1, so it is always between 0 and 1.", None, 3),
    ]


# ---------------------------------------------------------------------------------------------
# T2: simple probability
# ---------------------------------------------------------------------------------------------
def members(kind: str, t: int, N: int) -> list:
    """The outcomes 1..N that make an event: the single source of event truth in this generator."""
    r = range(1, N + 1)
    if kind == "even":
        return [x for x in r if x % 2 == 0]
    if kind == "odd":
        return [x for x in r if x % 2 == 1]
    if kind == "prime":
        return [x for x in r if x > 1 and all(x % d for d in range(2, x))]
    if kind == "mult":
        return [x for x in r if x % t == 0]
    if kind == "factor":
        return [x for x in r if t % x == 0]
    if kind == "square":
        return [x for x in r if int(x ** 0.5) ** 2 == x]
    if kind == "face":
        return [t]
    if kind == "gt":
        return [x for x in r if x > t]
    if kind == "lt":
        return [x for x in r if x < t]
    if kind == "ge":
        return [x for x in r if x >= t]
    if kind == "le":
        return [x for x in r if x <= t]
    raise ValueError(kind)


def event_phrase(kind: str, t: int) -> str:
    return {"even": "even", "odd": "odd", "prime": "prime", "mult": f"a multiple of {t}",
            "factor": f"a factor of {t}", "square": "a square number", "face": f"a {t}",
            "gt": f"more than {t}", "lt": f"less than {t}", "ge": f"at least {t}",
            "le": f"at most {t}"}[kind]


def uniform_wrongs(k: int, n: int, boundary=None, prime_one=None, distinct=None) -> list:
    """Wrong values for P = k/n (equally likely outcomes), in priority order, each only if a real
    probability strictly between 0 and 1. ``boundary`` / ``prime_one`` are the (wrong) favorable
    counts under those slips; ``distinct`` is (letters in the event, letters in the word)."""
    out = []
    if boundary is not None and boundary >= 1:
        out.append(("BOUNDARY", lt1(Fr(boundary, n))))
    if prime_one is not None:
        out.append(("PRIME_ONE", lt1(Fr(prime_one, n))))
    if distinct is not None:
        out.append(("DISTINCT_OUTCOMES", lt1(Fr(distinct[0], distinct[1]))))
    out.append(("PART_TO_PART", lt1(Fr(k, n - k)) if n > k else None))
    out.append(("OTHER_EVENT", lt1(Fr(n - k, n))))
    out.append(("EQUAL_CHANCE", Fr(1, 2)))
    out.append(("ONE_OVER_TOTAL", lt1(Fr(1, n))))
    return out


def _set_event_spec(prompt: str, kind: str, t: int, N: int, ones: str) -> Optional[Spec]:
    mem = members(kind, t, N)
    k = len(mem)
    if k == 0 or k == N:
        return None
    boundary = {"gt": k + 1, "lt": k + 1, "ge": k - 1, "le": k - 1}.get(kind)
    prime_one = k + 1 if kind == "prime" else None
    correct = Fr(k, N)
    cap = event_phrase(kind, t)
    cap = cap[0].upper() + cap[1:]
    if kind == "face":
        expl = f"Only the {t} counts. That is 1 of {N}: {fr_expl(k, N)}."
    else:
        expl = f"{cap}: {', '.join(map(str, mem))}. That is {k} of {N}: {fr_expl(k, N)}."
    return Spec(prompt, Cand(None, correct, ftxt(correct)),
                W(uniform_wrongs(k, N, boundary, prime_one), ftxt), expl, frac_fill(correct, N))


DIE_EVENTS = [("face", 6), ("face", 3), ("even", 0), ("odd", 0), ("gt", 4), ("lt", 3),
              ("ge", 5), ("le", 2), ("gt", 2), ("lt", 5), ("ge", 3), ("le", 4), ("gt", 1), ("lt", 6),
              ("mult", 3), ("factor", 6), ("square", 0)]


def t2_die(rng) -> list:
    out = []
    for kind, t in DIE_EVENTS:
        s = _set_event_spec(f"Roll a die. P({event_phrase(kind, t)})?", kind, t, 6, "")
        if s:
            out.append(s)
    return out


def t2_prime(rng) -> list:
    """The prime events on their own, so the 'is 1 prime?' slip is always in the tier."""
    out = [_set_event_spec("Roll a die. P(prime)?", "prime", 0, 6, "")]
    for N in (8, 10, 12):
        out.append(_set_event_spec(f"Cards 1 to {N}, pick one. P(prime)?", "prime", 0, N, ""))
    return [s for s in out if s]


def t2_cards(rng) -> list:
    out = []
    for N in (8, 10, 12):
        evs = [("even", 0), ("odd", 0), ("mult", 3), ("mult", 4), ("mult", 5), ("square", 0)]
        for t in range(2, N - 1):
            evs += [("gt", t), ("lt", t + 1), ("ge", t + 1), ("le", t)]
        for kind, t in evs:
            s = _set_event_spec(f"Cards 1 to {N}, pick one. P({event_phrase(kind, t)})?", kind, t, N, "")
            if s:
                out.append(s)
    return out


COLORS2 = [("red", "blue"), ("red", "green"), ("green", "blue"), ("white", "black"), ("red", "yellow"),
           ("blue", "yellow")]
COLORS3 = [("red", "blue", "green"), ("red", "yellow", "green"), ("blue", "white", "black")]


def t2_bag2(rng) -> list:
    out = []
    for a in range(1, 11):
        for b in range(a + 1, 13 - a):  # a < b, a + b <= 12
            for which in (0, 1):  # ask the first or the second listed color
                c1, c2 = rng.choice(COLORS2)
                if rng.random() < 0.5:
                    c1, c2 = c2, c1
                x, y = (a, b) if rng.random() < 0.5 else (b, a)  # counts in prompt order
                fav, ask = (x, c1) if which == 0 else (y, c2)
                n = a + b
                correct = Fr(fav, n)
                wr = uniform_wrongs(fav, n)
                prompt = f"Bag: {x} {c1}, {y} {c2}. P({ask})?"
                expl = f"{fav} of {n} marbles are {ask}: {fr_expl(fav, n)}."
                out.append(Spec(prompt, Cand(None, correct, ftxt(correct)), W(wr, ftxt), expl,
                                frac_fill(correct, n)))
    return out


def t2_bag3(rng) -> list:
    out = []
    for a in range(1, 9):
        for b in range(1, 9):
            for c in range(1, 9):
                if a + b + c > 12 or len({a, b, c}) < 2:
                    continue
                cs = rng.choice(COLORS3)
                which = rng.randrange(3)
                cnt = (a, b, c)
                fav, n = cnt[which], a + b + c
                correct = Fr(fav, n)
                wr = uniform_wrongs(fav, n)
                wr = [(lab, Fr(1, 3) if lab == "EQUAL_CHANCE" else v) for lab, v in wr]
                prompt = f"Bag: {a} {cs[0]}, {b} {cs[1]}, {c} {cs[2]}. P({cs[which]})?"
                expl = f"{fav} of {n} marbles are {cs[which]}: {fr_expl(fav, n)}."
                out.append(Spec(prompt, Cand(None, correct, ftxt(correct)), W(wr, ftxt), expl,
                                frac_fill(correct, n)))
    return out


def t2_spinner(rng) -> list:
    out = []
    for n in (4, 5, 6, 8, 10, 12):
        for k in range(1, n):
            color = rng.choice(["red", "blue", "green", "yellow"])
            correct = Fr(k, n)
            wr = uniform_wrongs(k, n)
            prompt = f"Spinner: {n} equal parts, {k} {color}. P({color})?"
            expl = f"{k} of {n} parts are {color}: {fr_expl(k, n)}."
            out.append(Spec(prompt, Cand(None, correct, ftxt(correct)), W(wr, ftxt), expl,
                            frac_fill(correct, n)))
    return out


LETTER_WORDS = ["ROBOT", "SCHOOL", "BANANA", "ROBOTICS", "FORTNITE", "TEACHER", "CIRCLE", "MISSISSIPPI",
                "BALLOON", "SUMMER", "PEPPER"]
VOWELS = "AEIOU"


def t2_letters(rng) -> list:
    out = []
    for word in LETTER_WORDS:
        n = len(word)
        letters = list(dict.fromkeys(word))
        events = [(f"P({x})", word.count(x), 1) for x in letters]
        for label, test in (("a vowel", lambda ch: ch in VOWELS), ("a consonant", lambda ch: ch not in VOWELS)):
            kk = sum(1 for ch in word if test(ch))
            dd = sum(1 for ch in letters if test(ch))
            events.append((f"P({label})", kk, dd))
        for text, k, dk in events:
            if k == 0 or k == n:
                continue
            correct = Fr(k, n)
            wr = uniform_wrongs(k, n, distinct=(dk, len(letters)))
            what = text[2:-1]
            if len(what) == 1:
                has = f"{k} {what}" if k == 1 else f"{k} {what}'s"
            else:
                noun = what.split()[1]
                has = f"{k} {noun}" if k == 1 else f"{k} {noun}s"
            expl = f"{word} has {has} among {n} letters: {fr_expl(k, n)}."
            out.append(Spec(f"A letter is picked from {word}. {text}?", Cand(None, correct, ftxt(correct)),
                            W(wr, ftxt), expl, frac_fill(correct, n)))
    return out


# ---------------------------------------------------------------------------------------------
# T3: complement, predict, sample, estimate
# ---------------------------------------------------------------------------------------------
def comp_bag_wrongs(asked: int, others: List[int]) -> list:
    """P(not asked color) from marble counts: ``asked`` marbles of the asked color, ``others`` the
    counts of the other colors in prompt order."""
    n = asked + sum(others)
    out = [("SAME_AS_EVENT", Fr(asked, n))]
    if len(others) > 1:
        out.append(("ONE_OTHER", Fr(others[0], n)))
    out.append(("PART_TO_PART", lt1(Fr(n - asked, asked))))
    return out


def t3_comp_bag2(rng) -> list:
    out = []
    for a in range(1, 11):
        for b in range(1, 12 - a):
            if a == b:
                continue
            c1, c2 = rng.choice(COLORS2)
            n = a + b
            correct = Fr(b, n)
            wr = comp_bag_wrongs(a, [b])
            expl = f"{b} of {n} marbles are not {c1}: {fr_expl(b, n)}."
            out.append(Spec(f"Bag: {a} {c1}, {b} {c2}. P(not {c1})?", Cand(None, correct, ftxt(correct)),
                            W(wr, ftxt), expl, frac_fill(correct, n)))
    return out


def t3_comp_bag3(rng) -> list:
    out = []
    for a in range(1, 9):
        for b in range(1, 9):
            for c in range(1, 9):
                if a + b + c > 12 or len({a, b, c}) < 2:
                    continue
                cs = rng.choice(COLORS3)
                n = a + b + c
                correct = Fr(b + c, n)
                wr = comp_bag_wrongs(a, [b, c])
                expl = f"{b + c} of {n} marbles are not {cs[0]}: {fr_expl(b + c, n)}."
                out.append(Spec(f"Bag: {a} {cs[0]}, {b} {cs[1]}, {c} {cs[2]}. P(not {cs[0]})?",
                                Cand(None, correct, ftxt(correct)), W(wr, ftxt), expl,
                                frac_fill(correct, n)))
    return out


COMP_CTX = [("rain", "no rain"), ("snow", "no snow"), ("win", "not win"), ("hit", "not hit"),
            ("goal", "no goal"), ("late", "not late"), ("tie", "no tie"), ("sunny", "not sunny")]
COMP_FRACS = [Fr(1, 4), Fr(3, 4), Fr(1, 5), Fr(2, 5), Fr(3, 5), Fr(4, 5), Fr(1, 10), Fr(3, 10), Fr(7, 10),
              Fr(9, 10), Fr(1, 3), Fr(2, 3), Fr(1, 6), Fr(5, 6), Fr(1, 8), Fr(3, 8), Fr(5, 8), Fr(7, 8),
              Fr(5, 12), Fr(7, 12)]
COMP_DECS = [Fr(1, 10), Fr(1, 5), Fr(1, 4), Fr(3, 10), Fr(2, 5), Fr(3, 5), Fr(7, 10), Fr(3, 4), Fr(4, 5),
             Fr(9, 10)]


def comp_given_wrongs(p: Fr, with_p2p: bool) -> list:
    """P(not) from P(event) = p: the event's own chance, 1 plus p, and (fractions) part-to-part."""
    out = [("SAME_AS_EVENT", p)]
    if with_p2p:
        out.append(("PART_TO_PART", lt1(Fr(p.numerator, p.denominator - p.numerator))))
    out.append(("ADD_TO_ONE", 1 + p))
    return out


def _comp_given(form: str):
    txt = {"frac": ftxt, "dec": dtxt, "pct": ptxt}[form]
    pool = COMP_FRACS if form == "frac" else COMP_DECS

    def build(rng) -> list:
        out = []
        for p in pool:
            ev, nev = rng.choice(COMP_CTX)
            q = 1 - p
            wr = comp_given_wrongs(p, form == "frac")
            if form == "frac":
                expl = f"1 − {txt(p)} = {txt(q)}."
                fill = frac_fill(q)
            else:
                expl = (f"100% − {txt(p)} = {txt(q)}." if form == "pct" else f"1 − {txt(p)} = {txt(q)}.")
                fill = step_fill(q, txt)
            out.append(Spec(f"P({ev}) = {txt(p)}. P({nev})?", Cand(None, q, txt(q)), W(wr, txt), expl, fill))
        return out

    return build


t3_comp_frac, t3_comp_dec, t3_comp_pct = _comp_given("frac"), _comp_given("dec"), _comp_given("pct")


def expect_wrongs(a: int, d: int, n: int) -> list:
    """About how many in n tries when the chance is a/d (n = d * k): the slips."""
    k = n // d
    ans = a * k
    inv = Fr(n * d, a)
    return [("IGNORED_NUMERATOR", k if a > 1 else None),
            ("INVERTED_P", int(inv) if inv.denominator == 1 and inv <= MAX_DISTRACTOR else None),
            ("OTHER_EVENT", n - ans)]


EXPECT_CTX = [("win", "Play", "wins"), ("hit", "Shoot", "hits"), ("goal", "Kick", "goals"),
              ("strike", "Bowl", "strikes"), ("catch", "Throw", "catches"), ("pass", "Throw", "passes")]
EXPECT_FRACS = [Fr(1, 3), Fr(2, 3), Fr(1, 4), Fr(3, 4), Fr(1, 5), Fr(2, 5), Fr(3, 5), Fr(4, 5), Fr(1, 6),
                Fr(5, 6), Fr(1, 8), Fr(3, 8), Fr(1, 10), Fr(3, 10), Fr(7, 10), Fr(9, 10)]
EXPECT_DECS = [Fr(1, 10), Fr(1, 5), Fr(1, 4), Fr(3, 10), Fr(2, 5), Fr(3, 5), Fr(7, 10), Fr(3, 4), Fr(4, 5),
               Fr(9, 10)]


def expect_p(rng) -> list:
    out = []
    forms = [("frac", ftxt, EXPECT_FRACS), ("dec", dtxt, EXPECT_DECS), ("pct", ptxt, EXPECT_DECS)]
    for form, txt, pool in forms:
        for p in pool:
            a, d = p.numerator, p.denominator
            for _ in range(2):
                k = rng.randint(2, 10)
                ctx, verb, plural = rng.choice(EXPECT_CTX)
                n, ans = d * k, a * k
                if n > 100 or ans > 100:
                    continue
                if form == "frac":
                    expl = f"{n} ÷ {d} = {k}, then {k} × {a} = {ans}."
                else:
                    expl = f"{txt(p)} = {a}/{d}. {n} ÷ {d} = {k}, then {k} × {a} = {ans}."
                prompt = f"P({ctx}) = {txt(p)}. {verb} {n} times. About how many {plural}?"
                out.append(Spec(prompt, Cand(None, ans, str(ans)), W(expect_wrongs(a, d, n), itxt), expl,
                                int_fill(ans)))
    return out


DIE_PLURALS = [("6s", 1), ("3s", 1), ("even numbers", 3), ("odd numbers", 3), ("numbers over 4", 2),
               ("numbers under 3", 2), ("multiples of 3", 2), ("primes", 3), ("numbers over 2", 4),
               ("numbers under 5", 4)]


def expect_die(rng) -> list:
    out = []
    for plural, fav in DIE_PLURALS:
        for k in range(2, 11):
            n = 6 * k
            ans = fav * k
            expl = f"{fav} of 6 faces: {n} ÷ 6 = {k}, then {k} × {fav} = {ans}."
            out.append(Spec(f"Roll a die {n} times. About how many {plural}?", Cand(None, ans, str(ans)),
                            W(expect_wrongs(fav, 6, n), itxt), expl, int_fill(ans)))
    return out


def sample_wrongs(c: int, s: int, N: int) -> list:
    k = N // s
    return [("SAMPLE_COUNT", c), ("ADDITIVE", c + N - s), ("SCALE_ONLY", k), ("OTHER_EVENT", N - c * k)]


SAMPLE_ACTS = ["like jazz", "own a bike", "have a pet", "play chess", "ride a bus", "like soccer",
               "bring lunch", "play piano", "walk to school"]
SAMPLE_SIZES = [(4, (5, 10)), (5, (4, 6, 8, 10)), (6, (5, 10)), (8, (5, 10)),
                (10, (2, 3, 4, 5, 6, 8, 9, 10)), (20, (2, 3, 4, 5)), (25, (2, 3, 4))]


def t3_sample(rng) -> list:
    out = []
    for s, ks in SAMPLE_SIZES:
        for k in ks:
            N = s * k
            if N > 100:
                continue
            for c in range(2, min(s, 11)):
                if rng.random() < 0.6:
                    continue
                act = rng.choice(SAMPLE_ACTS)
                ans = c * k
                expl = f"{N} ÷ {s} = {k}, so {c} × {k} = {ans}."
                out.append(Spec(f"Sample of {s} kids: {c} {act}. About how many of {N}?",
                                Cand(None, ans, str(ans)), W(sample_wrongs(c, s, N), itxt), expl,
                                int_fill(ans)))
    return out


def estimate_wrongs(c: int, n: int) -> list:
    return [("PART_TO_PART", lt1(Fr(c, n - c))), ("OTHER_EVENT", Fr(n - c, n)), ("FLIPPED", Fr(n, c))]


ESTIMATE_FMT = [
    "Spinner: red {c} of {n} spins. Estimate P(red)?",
    "Shots: {c} of {n} went in. Estimate P(make)?",
    "Bus was late {c} of {n} days. Estimate P(late)?",
    "Seeds: {c} of {n} sprouted. Estimate P(sprout)?",
    "Darts: {c} of {n} hit the target. Estimate P(hit)?",
]
ESTIMATE_TOTALS = (12, 15, 20, 24, 25, 30, 40, 50)


def t3_estimate(rng) -> list:
    """Experimental probability: c of n simplifies by g = gcd(c, n) (2..10) to a/d, d <= 12, not 1/2."""
    out = []
    for n in ESTIMATE_TOTALS:
        for c in range(1, n):
            g = gcd(c, n)
            p = Fr(c, n)
            if g < 2 or g > 10 or p.denominator > 12 or p == Fr(1, 2):
                continue
            fmt = rng.choice(ESTIMATE_FMT)
            expl = f"Divide both by {g}: {c}/{n} = {ftxt(p)}."
            out.append(Spec(fmt.format(c=c, n=n), Cand(None, p, ftxt(p)), W(estimate_wrongs(c, n), ftxt),
                            expl, frac_fill(p)))
    return out


# ---------------------------------------------------------------------------------------------
# T4: sample spaces
# ---------------------------------------------------------------------------------------------
def prod2_wrongs(a: int, b: int) -> list:
    return [("ADDED_COUNTS", a + b), ("ONE_STAGE", max(a, b))]


def prod3_wrongs(a: int, b: int, c: int) -> list:
    return [("ADDED_COUNTS", a + b + c), ("FORGOT_ONE", a * b), ("MIXED_OPS", (a + b) * c)]


def flip_wrongs(n: int) -> list:
    return [("ORDER_BLIND", n + 1), ("POWER_FLIP", n * n), ("MULT_BY_COUNT", 2 * n), ("ONE_STAGE", 2)]


def twice_wrongs(m: int) -> list:
    return [("ORDER_BLIND", m * (m + 1) // 2), ("ADDED_COUNTS", 2 * m), ("ONE_STAGE", m)]


def _count_spec(prompt: str, ans: int, rules: list, expl: str, min_real: int = 2) -> Spec:
    return Spec(prompt, Cand(None, ans, str(ans)), W(rules, itxt), expl, int_fill(ans), min_real)


PROD2_CTX = [("shirts", "pants", "outfits"), ("hats", "scarves", "outfits"), ("flavors", "cones", "treats"),
             ("breads", "fillings", "sandwiches"), ("crusts", "toppings", "pizzas"),
             ("mains", "sides", "meals"), ("bodies", "arms", "robots"), ("caps", "jerseys", "uniforms")]


def t4_prod2(rng) -> list:
    out = []
    for a in range(2, 9):
        for b in range(2, 9):
            if a == b and a == 2:
                continue
            x, y, z = rng.choice(PROD2_CTX)
            out.append(_count_spec(f"{a} {x} and {b} {y}. How many {z}?", a * b, prod2_wrongs(a, b),
                                   f"Pair each of {a} with each of {b}: {a} × {b} = {a * b}."))
    return out


SIM_STAGES = [("flip a coin", 2), ("roll a die", 6), ("spin a 3-part spinner", 3), ("spin a 4-part spinner", 4),
              ("spin a 5-part spinner", 5)]


def t4_prod2_sim(rng) -> list:
    out = []
    for i, (t1, a) in enumerate(SIM_STAGES):
        for t2, b in SIM_STAGES[i + 1:]:
            head = f"{t1[0].upper()}{t1[1:]} and {t2}."
            out.append(_count_spec(f"{head} How many outcomes?", a * b, prod2_wrongs(a, b),
                                   f"Pair each of {a} with each of {b}: {a} × {b} = {a * b}."))
    return out


PROD3_CTX = [("shirts", "pants", "hats", "outfits"), ("breads", "meats", "cheeses", "sandwiches"),
             ("crusts", "sauces", "toppings", "pizzas"), ("bodies", "arms", "wheels", "robots"),
             ("mains", "sides", "drinks", "meals")]
PROD3_FIXED = [("Roll a die and flip two coins. How many outcomes?", (6, 2, 2)),
               ("Flip two coins and spin a 3-part spinner. Outcomes?", (2, 2, 3)),
               ("Flip a coin, roll a die, spin a 4-part spinner. Outcomes?", (2, 6, 4)),
               ("Flip a coin, spin a 3-part spinner twice. Outcomes?", (2, 3, 3))]


def _p3_ok(a: int, b: int, c: int) -> bool:
    lo, mid, hi = sorted((a, b, c))
    return lo * mid <= 10 and hi <= 10


def _prod3_spec(prompt: str, stages: tuple) -> Spec:
    a, b, c = stages
    x, y, z = sorted(stages)
    ans = a * b * c
    return _count_spec(prompt, ans, prod3_wrongs(a, b, c), f"{x} × {y} × {z} = {x * y} × {z} = {ans}.")


def t4_prod3(rng) -> list:
    out = []
    for a in range(2, 6):
        for b in range(2, 6):
            for c in range(2, 6):
                if not _p3_ok(a, b, c):
                    continue
                x, y, z, w = rng.choice(PROD3_CTX)
                out.append(_prod3_spec(f"{a} {x}, {b} {y}, {c} {z}. How many {w}?", (a, b, c)))
    for prompt, stages in PROD3_FIXED:
        out.append(_prod3_spec(prompt, stages))
    return out


def t4_flips(rng) -> list:
    out = []
    for n in (2, 3, 4):
        ans = 2 ** n
        why = " × ".join(["2"] * n) + f" = {ans}"
        for prompt in (f"Flip a coin {n} times. How many outcomes?", f"Flip {n} coins. How many outcomes?",
                       f"Toss a coin {n} times. How many outcomes?"):
            out.append(_count_spec(prompt, ans, flip_wrongs(n), f"Each flip has 2 outcomes: {why}.", 2))
    return out


def t4_twice(rng) -> list:
    out = []
    for m in (2, 3, 4, 5):
        out.append(_count_spec(f"Spin a {m}-part spinner twice. How many outcomes?", m * m, twice_wrongs(m),
                               f"Order matters, so (1, 2) and (2, 1) differ: {m} × {m} = {m * m}."))
    out.append(_count_spec("Roll a die twice. How many outcomes?", 36, twice_wrongs(6),
                           "Order matters, so (1, 2) and (2, 1) differ: 6 × 6 = 36."))
    out.append(_count_spec("Roll two dice. How many outcomes?", 36, twice_wrongs(6),
                           "Each die has 6 faces and order matters: 6 × 6 = 36."))
    return out


def coin_outcomes(n: int) -> list:
    out = [""]
    for _ in range(n):
        out = [s + ch for s in out for ch in "HT"]
    return out


COIN2_EVENTS = [("exactly one head", lambda s: s.count("H") == 1), ("at least one head", lambda s: "H" in s),
                ("at least one tail", lambda s: "T" in s), ("the same side up", lambda s: len(set(s)) == 1),
                ("different sides up", lambda s: len(set(s)) == 2)]
COIN3_EVENTS = [("exactly one head", lambda s: s.count("H") == 1), ("exactly two heads", lambda s: s.count("H") == 2),
                ("at least one head", lambda s: s.count("H") >= 1), ("at least two heads", lambda s: s.count("H") >= 2),
                ("at most one head", lambda s: s.count("H") <= 1), ("at most two heads", lambda s: s.count("H") <= 2),
                ("exactly one tail", lambda s: s.count("T") == 1), ("at least one tail", lambda s: s.count("T") >= 1),
                ("two or more tails", lambda s: s.count("T") >= 2)]


def coin_count_wrongs(n: int, k: int, heads_seen: int) -> list:
    """Counting the outcomes of n coin flips that fit an event with k outcomes, ``heads_seen`` distinct
    head totals among them (HT and TH merged)."""
    return [("ORDER_BLIND", heads_seen), ("COUNTED_ALL", 2 ** n), ("ONE_OUTCOME", 1)]


def _coin_event_family(n: int, events) -> Callable:
    def build(rng) -> list:
        out = []
        for desc, test in events:
            outs = [s for s in coin_outcomes(n) if test(s)]
            heads = len({s.count("H") for s in outs})
            word = "two" if n == 2 else "three"
            out.append(_count_spec(f"Flip {word} coins. How many outcomes have {desc}?", len(outs),
                                   coin_count_wrongs(n, len(outs), heads), f"{', '.join(outs)}: {len(outs)}."))
        return out

    return build


t4_coin2, t4_coin3 = _coin_event_family(2, COIN2_EVENTS), _coin_event_family(3, COIN3_EVENTS)

DIE_SETS = [("an even number", "even", 0), ("an odd number", "odd", 0), ("a prime number", "prime", 0),
            ("a number over 4", "gt", 4), ("a number under 3", "lt", 3), ("a multiple of 3", "mult", 3),
            ("a number over 2", "gt", 2), ("a number under 5", "lt", 5)]


def coin_die_count_wrongs(s: int) -> list:
    return [("ADDED_COUNTS", 1 + s), ("IGNORED_PART", 2 * s), ("IGNORED_PART", 6), ("TOTAL_NOT_EVENT", 12)]


def t4_coin_die(rng) -> list:
    out = []
    for coin, ch in (("heads", "H"), ("tails", "T")):
        for desc, kind, t in DIE_SETS:
            faces = members(kind, t, 6)
            s = len(faces)
            outs = ", ".join(f"{ch}{f}" for f in faces)
            out.append(_count_spec(f"Coin and die. How many outcomes: {coin} and {desc}?", s,
                                   coin_die_count_wrongs(s), f"{outs}: {s}."))
    return out


def t4_lists(rng) -> list:
    def lst(correct, wrongs, prompt, expl):
        return Spec(prompt, Cand(None, correct, correct), [Cand(l, w, w) for l, w in wrongs], expl, None, 3)

    return [
        lst("HH, HT, TH, TT", [("ORDER_BLIND", "HH, HT, TT"), ("MATCHING_ONLY", "HH, TT"),
                               ("ONE_STAGE", "H, T")],
            "Flip two coins. Which lists every outcome?",
            "HT and TH are different outcomes: HH, HT, TH, TT."),
        lst("H1, H2, T1, T2", [("NOT_PAIRED", "H, T, 1, 2"), ("MISSED_ONE", "H1, H2, T1"),
                               ("MISSED_ONE", "H1, T2")],
            "Flip a coin and spin 1 or 2. Which lists every outcome?",
            "Pair each coin side with each number: H1, H2, T1, T2."),
    ]


# ---------------------------------------------------------------------------------------------
# T5: compound events
# ---------------------------------------------------------------------------------------------
def coin_die_prob_wrongs(f: int) -> list:
    """P(side and a die event with f faces): the die event has chance f/6, the coin 1/2."""
    return [("ADDED_PROBS", lt1(Fr(1, 2) + Fr(f, 6))), ("ADD_DENOMS", lt1(Fr(f, 8))),
            ("FORGOT_STAGE", lt1(Fr(f, 6))), ("FORGOT_STAGE", Fr(1, 2))]


T5_DIE = [("a 6", "face", 6), ("a 3", "face", 3), ("an even number", "even", 0), ("an odd number", "odd", 0),
          ("a prime", "prime", 0), ("a number over 4", "gt", 4), ("a number under 3", "lt", 3),
          ("a multiple of 3", "mult", 3), ("a number over 1", "gt", 1), ("a number under 5", "lt", 5)]


def t5_coin_die(rng) -> list:
    out = []
    for coin in ("heads", "tails"):
        for desc, kind, t in T5_DIE:
            f = len(members(kind, t, 6))
            p = Fr(f, 12)
            expl = f"{f} of 12 outcomes: {fr_expl(f, 12)}."
            out.append(Spec(f"Flip a coin, roll a die. P({coin} and {desc})?", Cand(None, p, ftxt(p)),
                            W(coin_die_prob_wrongs(f), ftxt), expl, frac_fill(p, 12)))
    return out


def coins_prob_wrongs(n: int, outs: list) -> list:
    """P of an event of n coin flips with the given favorable outcomes (as strings like ``HT``)."""
    heads = len({s.count("H") for s in outs})
    classes = n + 1
    out = [("ORDER_BLIND", lt1(Fr(heads, classes)))]
    if n == 3:
        out.append(("ADD_DENOMS", lt1(Fr(len(outs), 6))))
    out.append(("OTHER_EVENT", lt1(Fr(2 ** n - len(outs), 2 ** n))))
    out.append(("FORGOT_STAGE", Fr(1, 2)))
    out.append(("ONE_OUTCOME", lt1(Fr(1, 2 ** n))))
    return out


COIN2_PROB = [("two heads", lambda s: s == "HH"), ("two tails", lambda s: s == "TT"),
              ("one head, one tail", lambda s: s.count("H") == 1), ("at least one head", lambda s: "H" in s),
              ("at least one tail", lambda s: "T" in s), ("no heads", lambda s: "H" not in s),
              ("the coins match", lambda s: len(set(s)) == 1), ("different sides", lambda s: len(set(s)) == 2)]
COIN3_PROB = [("all heads", lambda s: s == "HHH"), ("no heads", lambda s: "H" not in s),
              ("exactly one head", lambda s: s.count("H") == 1), ("exactly two heads", lambda s: s.count("H") == 2),
              ("at least one head", lambda s: "H" in s), ("at least one tail", lambda s: "T" in s),
              ("two or more heads", lambda s: s.count("H") >= 2), ("at most one head", lambda s: s.count("H") <= 1),
              ("heads on the first flip", lambda s: s[0] == "H"), ("all three match", lambda s: len(set(s)) == 1),
              ("not all heads", lambda s: s != "HHH"), ("H, H, T in that order", lambda s: s == "HHT")]


def _coins_prob_family(n: int, events) -> Callable:
    def build(rng) -> list:
        out = []
        for desc, test in events:
            outs = [s for s in coin_outcomes(n) if test(s)]
            p = Fr(len(outs), 2 ** n)
            expl = f"{len(outs)} of {2 ** n} outcomes ({', '.join(outs)}): {fr_expl(len(outs), 2 ** n)}."
            word = "two" if n == 2 else "three"
            out.append(Spec(f"Flip {word} coins. P({desc})?", Cand(None, p, ftxt(p)),
                            W(coins_prob_wrongs(n, outs), ftxt), expl, frac_fill(p, 2 ** n)))
        return out

    return build


t5_coin2, t5_coin3 = _coins_prob_family(2, COIN2_PROB), _coins_prob_family(3, COIN3_PROB)


def spin_coin_wrongs(m: int, s: int) -> list:
    """Spinner with m equal parts (event has s of them) and a coin (event has 1 of 2)."""
    return [("ADDED_PROBS", lt1(Fr(s, m) + Fr(1, 2))), ("ADD_DENOMS", lt1(Fr(s, m + 2))),
            ("FORGOT_STAGE", lt1(Fr(s, m))), ("FORGOT_STAGE", Fr(1, 2))]


def t5_spin_coin(rng) -> list:
    out = []
    three = [("red", 1), ("blue", 1), ("green", 1), ("red or blue", 2), ("blue or green", 2)]
    four = [("a 1", 1), ("a 4", 1), ("even", 2), ("odd", 2), ("over 2", 2), ("under 4", 3)]
    for coin in ("heads", "tails"):
        for desc, s in three:
            p = Fr(s, 6)
            sp = ftxt(Fr(s, 3))
            expl = f"{sp} × 1/2 = {ftxt(p)}."
            out.append(Spec(f"3-part spinner (red, blue, green), coin. P({desc} and {coin})?",
                            Cand(None, p, ftxt(p)), W(spin_coin_wrongs(3, s), ftxt), expl,
                            frac_fill(p, 6)))
        for desc, s in four:
            p = Fr(s, 8)
            sp = ftxt(Fr(s, 4))
            expl = f"{sp} × 1/2 = {ftxt(p)}."
            out.append(Spec(f"4-part spinner (1 to 4), coin. P({desc} and {coin})?", Cand(None, p, ftxt(p)),
                            W(spin_coin_wrongs(4, s), ftxt), expl, frac_fill(p, 8)))
    return out


def bag_draw_wrongs(x1: int, x2: int, n: int, ordered: bool) -> list:
    """Two draws with replacement from a bag of n: the first condition has x1 marbles, the second x2.
    ``ordered`` means a given order (red then blue); otherwise either order counts."""
    p = Fr(x1 * x2, n * n)
    out = []
    if not ordered:
        out.append(("ONE_ORDER", lt1(p)))
    elif x1 != x2:
        out.append(("ORDER_OVER", lt1(2 * p)))
    out.append(("ADDED_PROBS", lt1(Fr(x1 + x2, n))))
    out.append(("ADD_DENOMS", lt1(Fr(x1 * x2, 2 * n))))
    out.append(("FORGOT_STAGE", lt1(Fr(x1, n))))
    return out


BAG_COLORS = [("red", "blue"), ("red", "green"), ("red", "white")]


def _bag_draws(want_ordered: bool) -> Callable:
    def build(rng) -> list:
        out = []
        for (r, b) in ((1, 1), (1, 2), (2, 1)):
            for c1, c2 in BAG_COLORS:
                n = r + b
                head = f"Bag: {r} {c1}, {b} {c2}. Draw, replace, draw."
                kinds = [(f"{c1} twice", r, r, True), (f"{c2} twice", b, b, True),
                         (f"{c1} then {c2}", r, b, True), (f"{c2} then {c1}", b, r, True),
                         ("one of each", r, b, False)]
                for desc, x1, x2, ordered in kinds:
                    if ordered != want_ordered:
                        continue
                    p = Fr(x1 * x2, n * n) * (1 if ordered else 2)
                    pa, pb = ftxt(Fr(x1, n)), ftxt(Fr(x2, n))
                    expl = f"{pa} × {pb}" + ("" if ordered else " × 2 orders") + f" = {ftxt(p)}."
                    out.append(Spec(f"{head} P({desc})?", Cand(None, p, ftxt(p)),
                                    W(bag_draw_wrongs(x1, x2, n, ordered), ftxt), expl,
                                    frac_fill(p, n * n)))
        return out

    return build


t5_bag_ordered, t5_bag_either = _bag_draws(True), _bag_draws(False)


# ---------------------------------------------------------------------------------------------
# Tier assembly
# ---------------------------------------------------------------------------------------------
TIERS = {
    1: [(t1_numbers, 13), (t1_events, 12), (range_could, 6), (range_cant, 6), (range_extremes, 3)],
    2: [(t2_bag2, 9), (t2_bag3, 4), (t2_spinner, 4), (t2_die, 7), (t2_cards, 7), (t2_letters, 7),
        (t2_prime, 2)],
    3: [(t3_comp_bag2, 3), (t3_comp_bag3, 2), (t3_comp_frac, 3), (t3_comp_dec, 3), (t3_comp_pct, 2),
        (expect_p, 7), (expect_die, 4), (t3_sample, 9), (t3_estimate, 7)],
    4: [(t4_prod2, 9), (t4_prod2_sim, 5), (t4_prod3, 5), (t4_flips, 4), (t4_twice, 4), (t4_coin2, 3),
        (t4_coin3, 4), (t4_coin_die, 4), (t4_lists, 2)],
    5: [(t5_coin_die, 10), (t5_coin2, 5), (t5_coin3, 7), (t5_spin_coin, 8), (t5_bag_ordered, 7),
        (t5_bag_either, 3)],
}


def pick(spec: Spec, rng: random.Random):
    """Choose the three wrong choices for a spec, or None when it cannot make a valid item."""
    if len(spec.prompt) > MAX_PROMPT or len(spec.expl) > MAX_EXPL or len(spec.correct.text) > MAX_CHOICE:
        return None
    seen = {spec.correct.key}
    real = []
    for c in spec.wrongs:
        if c.key is None or c.key in seen:
            continue
        seen.add(c.key)
        if len(c.text) <= MAX_CHOICE and (not isinstance(c.key, int) or abs(c.key) <= MAX_DISTRACTOR):
            real.append(c)
    if len(real) < spec.min_real:
        return None
    take = list(real) if len(real) <= 3 else rng.sample(real, 3)
    if len(take) < 3 and spec.fill is not None:
        for c in spec.fill(rng):
            if len(take) == 3:
                break
            if c.key in seen or len(c.text) > MAX_CHOICE:
                continue
            seen.add(c.key)
            take.append(c)
    if len(take) < 3:
        return None
    return spec.correct, take


def _balanced(count: int, k: int, rng: random.Random) -> list:
    xs = [i % k for i in range(count)]
    rng.shuffle(xs)
    return xs


def gen_tier(tier: int, count: int, rng: random.Random) -> list:
    picked, leftovers, prompts = [], [], set()
    for builder, quota in TIERS[tier]:
        specs = builder(rng)
        rng.shuffle(specs)
        got, rest = 0, []
        for s in specs:
            if s.prompt in prompts:
                continue
            r = pick(s, rng)
            if r is None:
                continue
            if got < quota:
                picked.append((s, r))
                prompts.add(s.prompt)
                got += 1
            else:
                rest.append((s, r))
        leftovers.append(rest)
    i = 0
    while len(picked) < count and any(leftovers):
        rest = leftovers[i % len(leftovers)]
        i += 1
        while rest:
            s, r = rest.pop(0)
            if s.prompt not in prompts:
                picked.append((s, r))
                prompts.add(s.prompt)
                break
    if len(picked) < count:
        raise RuntimeError(f"tier {tier}: only {len(picked)} valid specs for {count} items")
    rng.shuffle(picked)
    picked = picked[:count]
    positions = _balanced(count, 4, rng)
    items = []
    for (s, (correct, wrongs)), pos in zip(picked, positions):
        wrongs = list(wrongs)
        rng.shuffle(wrongs)
        cs = wrongs[:pos] + [correct] + wrongs[pos:]
        items.append({
            "tier": tier,
            "prompt": s.prompt,
            "choices": [c.text for c in cs],
            "answer": pos,
            "misconceptions": [c.label for c in cs],
            "explanation": s.expl,
        })
    return items


def generate(manifest: dict, rng: random.Random) -> list:
    n = manifest["items_per_tier"]
    items = []
    for t in manifest["tiers"]:
        items.extend(gen_tier(t["tier"], n, rng))
    return items
