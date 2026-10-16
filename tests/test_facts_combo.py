"""facts-combo cartridge: golden misconception values, an independent re-check of every baked item (answer, the
meaning of every misconception key, near distractors, bands), the mix rules per operation, the anti-tell rules,
agreement with the four single-operation cartridges, and checker self-tests (disproofs)."""
import json
import random
import re
from collections import Counter

import pytest

from fnm.cart import REPO_ROOT, load_generator, load_manifest

CID = "facts-combo"
G = load_generator(CID)
MANIFEST = load_manifest(CID)


def _load(cid):
    with open(REPO_ROOT / "cartridges" / cid / "baked.json", encoding="utf-8") as f:
        return json.load(f)["items"]


ITEMS = _load(CID)
PROMPT_RE = re.compile(r"^(\d+) ([+−×÷]) (\d+) = \?$")
ADD_BANDS = {1: (2, 10), 2: (11, 20), 3: (21, 40), 4: (41, 70), 5: (71, 100)}
MUL_BANDS = {1: (1, 5, 1), 2: (6, 8, 2), 3: (9, 10, 2), 4: (11, 12, 2), 5: (13, 15, 2)}
OP_NAME = {"+": "ADD", "−": "SUB", "×": "MUL", "÷": "DIV"}
OP_CART = {"+": "facts-addition", "−": "facts-subtraction", "×": "facts-multiplication", "÷": "facts-division"}


def parse(prompt):
    m = PROMPT_RE.match(prompt)
    assert m, prompt
    return int(m.group(1)), m.group(2), int(m.group(3))


def truth(prompt):
    """(answer, operands) by plain Python."""
    x, op, y = parse(prompt)
    if op == "+":
        return x + y, (x, y)
    if op == "−":
        return x - y, (x, y)
    if op == "×":
        return x * y, (x, y)
    assert x % y == 0, prompt
    return x // y, (x, y)


def tier_items(t, op=None):
    out = [it for it in ITEMS if it["tier"] == t]
    return [it for it in out if op is None or parse(it["prompt"])[1] == op]


def smaller_from_larger(s, a):
    out, place = 0, 1
    while s or a:
        out += abs(s % 10 - a % 10) * place
        s //= 10
        a //= 10
        place *= 10
    return out


def key_meaning_ok(op, key, x, y, v):
    """Does wrong value v mean what its key says, for prompt `x op y`? Independent of the generator."""
    if key == "ARITH":
        return True
    name = key.split("_", 1)[0]
    if name != OP_NAME[op]:
        return False
    k = key.split("_", 1)[1]
    if op == "+":
        s = x + y
        return {
            "ONE_OFF": abs(v - s) == 1,
            "SUBTRACTED": v == abs(x - y),
            "NO_CARRY": v == s - 10 and x % 10 + y % 10 >= 10,
            "TENS_SLIP": abs(v - s) == 10,
        }[k]
    if op == "−":
        b = x - y
        return {
            "ONE_OFF": abs(v - b) == 1,
            "ADDED": v == x + y,
            "SMALLER_FROM_LARGER": v == smaller_from_larger(x, y) and x % 10 < y % 10,
            "FORGOT_TRADE": v == b + 10 and x % 10 < y % 10,
            "TENS_SLIP": abs(v - b) == 10,
        }[k]
    if op == "×":
        p = x * y
        return {
            "GROUP_OFF": v in (x * (y + 1), (x + 1) * y, x * (y - 1), (x - 1) * y),
            "ADDED": v == x + y,
            "DROPPED_CARRY": v == p - 10 and max(x, y) >= 10 > min(x, y) and (max(x, y) % 10) * min(x, y) >= 10,
            "TENS_SLIP": abs(v - p) == 10,
            "PARTIAL_PRODUCTS": min(x, y) >= 10 and v == (x // 10) * (y // 10) * 100 + (x % 10) * (y % 10),
        }[k]
    b = x // y
    return {
        "GROUP_OFF": abs(v - b) in (1, 2),
        "SUBTRACTED": v == x - y,
        "MULTIPLIED": v == x * y,
        "TENS_SLIP": abs(v - b) == 10,
    }[k]


def is_near(op, x, y, ans, v):
    if op in "+−":
        return abs(v - ans) in (1, 2, 10)
    if op == "×":
        return abs(v - ans) <= max(x, y)
    return abs(v - ans) in (1, 2)  # division: quotient +- 1 or 2


def check_item(it):
    """Problems with one baked item (empty = fine)."""
    bad = []
    m = PROMPT_RE.match(it["prompt"])
    if not m:
        return ["prompt shape"]
    x, op, y = int(m.group(1)), m.group(2), int(m.group(3))
    if op == "÷" and (y == 0 or x % y):
        return ["inexact division"]
    ans, _ = truth(it["prompt"])
    ch = it["choices"]
    if len(ch) != 4 or len(set(ch)) != 4:
        bad.append("four distinct choices")
    if not all(c.isdigit() for c in ch):
        return bad + ["non-integer choice"]
    vals = [int(c) for c in ch]
    if vals[it["answer"]] != ans:
        bad.append("answer is wrong")
    if sum(v == ans for v in vals) != 1:
        bad.append("not exactly one right choice")
    if any(v < 0 or v > 999 for v in vals):
        bad.append("choice out of 0..999")
    miscs = it["misconceptions"]
    if miscs[it["answer"]] is not None:
        bad.append("answer carries a key")
    wrong = [(k, v) for k, v in enumerate(vals) if k != it["answer"]]
    if sum(is_near(op, x, y, ans, v) for _, v in wrong) < 2:
        bad.append("fewer than 2 near distractors")
    for k, v in wrong:
        if miscs[k] is None or not key_meaning_ok(op, miscs[k], x, y, v):
            bad.append(f"key {miscs[k]} does not give {v}")
    t = it["tier"]
    if op in "+−":
        lo, hi = ADD_BANDS[t]
        s = ans if op == "+" else x
        a_, b_ = (x, y) if op == "+" else (y, x - y)
        if not lo <= s <= hi:
            bad.append("outside tier band")
        if min(a_, b_) < (1 if t == 1 else 2):
            bad.append("operand below minimum")
        if t == 2 and min(a_, b_) > 9:
            bad.append("tier 2 operand over 9")
    else:
        lo, hi, low = MUL_BANDS[t]
        f1, f2 = (x, y) if op == "×" else (y, ans)
        if not lo <= max(f1, f2) <= hi or min(f1, f2) < low:
            bad.append("outside tier band")
    return bad


# ---------------------------------------------------------------------------------------------
# Golden cases
# ---------------------------------------------------------------------------------------------
def test_golden_addition():
    c = G.add_candidates(4, 38, 47)
    assert (c[75], c[95], c[84], c[9]) == ("NO_CARRY", "TENS_SLIP", "ONE_OFF", "SUBTRACTED")
    c = G.add_candidates(4, 34, 52)
    assert (c[76], c[96], c[18]) == ("TENS_SLIP", "TENS_SLIP", "SUBTRACTED")
    c = G.add_candidates(2, 8, 5)
    assert c[3] == "SUBTRACTED" and c[12] == "ONE_OFF" and c[23] == "TENS_SLIP"  # first key wins value 3
    assert 85 not in G.add_candidates(4, 38, 47)


def test_golden_subtraction():
    c = dict(G.sub_candidates(14, 6, 2))
    assert c[12] == "SMALLER_FROM_LARGER" and c[18] == "FORGOT_TRADE" and c[20] == "ADDED" and c[9] == "ONE_OFF"
    c = dict(G.sub_candidates(52, 38, 4))
    assert c[26] == "SMALLER_FROM_LARGER" and c[24] == "FORGOT_TRADE" and c[90] == "ADDED" and 14 not in c
    assert c[13] == "ONE_OFF" and c[4] == "TENS_SLIP"
    c = dict(G.sub_candidates(52, 37, 4))  # 52-37=15: SMALLER_FROM_LARGER and FORGOT_TRADE both 25: first listed wins
    assert c[25] == "SMALLER_FROM_LARGER"


def test_golden_multiplication():
    c = {v: k for k, v in G.mul_candidates(13, 6, 4)}
    assert c[68] == "DROPPED_CARRY" and c[88] == "TENS_SLIP" and c[91] == "GROUP_OFF" and c[84] == "GROUP_OFF"
    assert c[65] == "GROUP_OFF" and c[72] == "GROUP_OFF" and c[19] == "ADDED" and 78 not in c
    c = {v: k for k, v in G.mul_candidates(13, 14, 5)}
    assert c[112] == "PARTIAL_PRODUCTS" and c[27] == "ADDED"
    c = {v: k for k, v in G.mul_candidates(12, 3, 4)}  # 36: ones product 6 does not carry
    assert c[26] == "TENS_SLIP" and "DROPPED_CARRY" not in c.values()
    c = {v: k for k, v in G.mul_candidates(2, 2, 1)}
    assert 4 not in c and c[6] == "GROUP_OFF" and c[2] == "GROUP_OFF"  # ADDED (4) is the answer: dropped


def test_golden_division():
    c = G.div_candidates(56, 7, 3)
    assert {v: c[v][0] for v in (9, 7, 10, 6)} == {9: "GROUP_OFF", 7: "GROUP_OFF", 10: "GROUP_OFF", 6: "GROUP_OFF"}
    assert c[49][0] == "SUBTRACTED" and c[392][0] == "MULTIPLIED" and 8 not in c
    c = G.div_candidates(144, 12, 4)
    assert c[22][0] == "TENS_SLIP" and c[2][0] == "TENS_SLIP" and c[132][0] == "SUBTRACTED"
    assert 1728 not in c  # over 999: MULTIPLIED dropped


def test_golden_keys_prefixed():
    s = G.sub_sets(52, 38, 4)
    assert all(k.startswith("SUB_") or k == "ARITH" for _, _, trio in s for _, k in trio)


def test_every_declared_key_is_used_and_every_used_key_declared():
    used = {k for it in ITEMS for k in it["misconceptions"] if k}
    declared = set(MANIFEST["misconceptions"]) | {"ARITH"}
    assert used <= declared
    assert set(MANIFEST["misconceptions"]) <= used
    assert all(k[:4] in ("ADD_", "SUB_", "MUL_", "DIV_") for k in MANIFEST["misconceptions"])


# ---------------------------------------------------------------------------------------------
# Independent re-check
# ---------------------------------------------------------------------------------------------
def test_every_baked_item_is_right():
    problems = [(it["prompt"], check_item(it)) for it in ITEMS if check_item(it)]
    assert not problems, problems[:5]


def test_checker_rejects_planted_bad_items():
    """Disproof: the checker can fail."""
    good = next(it for it in ITEMS if it["tier"] == 4 and parse(it["prompt"])[1] == "×")
    assert check_item(good) == []
    ans, _ = truth(good["prompt"])
    wrong_answer = dict(good, answer=(good["answer"] + 1) % 4)
    assert check_item(wrong_answer)
    shifted = dict(good, choices=[str(int(c) + 1) for c in good["choices"]])
    assert "answer is wrong" in check_item(shifted)
    far = dict(good, choices=list(good["choices"]))
    for k in range(4):
        if k != good["answer"]:
            far["choices"][k] = str(ans + 300 + k)
    assert "fewer than 2 near distractors" in check_item(far)
    assert "four distinct choices" in check_item(dict(good, choices=[good["choices"][good["answer"]]] * 4))
    wrong_key = dict(good, misconceptions=[None if k is None else "ADD_ONE_OFF" for k in good["misconceptions"]])
    assert any("does not give" in b for b in check_item(wrong_key))
    x, _, y = parse(good["prompt"])
    assert check_item(dict(good, prompt=f"{x} + {y} = ?"))  # operation swapped: answer no longer matches
    assert check_item(dict(good, prompt=f"{x + 100} × {y} = ?"))  # out of band
    inexact = dict(good, prompt="7 ÷ 2 = ?")
    assert check_item(inexact) == ["inexact division"]
    assert check_item(dict(good, prompt="7 * 2 = ?")) == ["prompt shape"]


def test_combo_prompt_matches_operation_cartridges():
    """A prompt that also appears in an operation's own baked.json at the same tier has the same answer."""
    seen = 0
    for op, cid in OP_CART.items():
        theirs = {(it["tier"], it["prompt"]): it for it in _load(cid)}
        for it in ITEMS:
            other = theirs.get((it["tier"], it["prompt"]))
            if other is None:
                continue
            seen += 1
            assert other["choices"][other["answer"]] == it["choices"][it["answer"]], it["prompt"]
            assert other["explanation"] == it["explanation"] or parse(it["prompt"])[1] == "−", it["prompt"]
    assert seen > 0


def test_student_text_matches_operation_cartridges():
    for pre, cid in (("ADD", "facts-addition"), ("SUB", "facts-subtraction"), ("MUL", "facts-multiplication"),
                     ("DIV", "facts-division")):
        theirs = load_manifest(cid)["misconceptions"]
        for k, v in theirs.items():
            assert MANIFEST["misconceptions"][f"{pre}_{k}"]["student"] == v["student"]


# ---------------------------------------------------------------------------------------------
# Counts, mix, determinism, balance
# ---------------------------------------------------------------------------------------------
def test_counts_and_unique_prompts():
    assert MANIFEST["grade"] == "Facts" and MANIFEST["picker_order"] == 5
    assert [t["name"] for t in MANIFEST["tiers"]][0] == "Within 10 & 5 × 5"
    assert [t["name"] for t in MANIFEST["tiers"]][-1] == "Within 100 & 15 × 15"
    for t in range(1, 6):
        its = tier_items(t)
        assert len(its) == MANIFEST["items_per_tier"] == 40
        assert len({it["prompt"] for it in its}) == 40
        for op in "+−×÷":
            assert len(tier_items(t, op)) == 10, (t, op)


def test_generator_is_deterministic():
    a = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    b = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    assert a == b


@pytest.mark.parametrize("t", range(1, 6))
def test_answer_positions_balanced(t):
    pos = Counter(it["answer"] for it in tier_items(t))
    assert all(8 <= pos[p] <= 12 for p in range(4)), pos


def test_wrong_choices_distinct_nonnegative_bounded():
    for it in ITEMS:
        vals = [int(c) for c in it["choices"]]
        assert len(set(vals)) == 4 and all(0 <= v <= 999 for v in vals)


@pytest.mark.parametrize("t", range(1, 6))
def test_mixed_order_not_grouped_by_operation(t):
    ops = [parse(it["prompt"])[1] for it in tier_items(t)]
    runs = sum(1 for i in range(1, len(ops)) if ops[i] != ops[i - 1])
    assert runs >= 15, ops


def test_tier2_crossing_ten_share():
    its = tier_items(2, "+")
    cross = [it for it in its if max(parse(it["prompt"])[0], parse(it["prompt"])[2]) <= 9
             and truth(it["prompt"])[0] >= 11]
    assert len(cross) * 2 >= len(its)
    its = tier_items(2, "−")
    cross = [it for it in its if parse(it["prompt"])[2] < 10 and parse(it["prompt"])[0] % 10 < parse(it["prompt"])[2]]
    assert len(cross) * 2 >= len(its)


@pytest.mark.parametrize("t", [3, 4, 5])
def test_upper_tier_mix_add_sub(t):
    adds = [parse(it["prompt"]) for it in tier_items(t, "+")]
    n = len(adds)
    assert sum(x % 10 + y % 10 >= 10 for x, _, y in adds) * 2 >= n
    assert sum(min(x, y) <= 9 and max(x, y) >= 10 for x, _, y in adds) * 4 >= n
    assert sum(x % 10 == 0 or y % 10 == 0 for x, _, y in adds) * 4 <= n
    subs = [parse(it["prompt"]) for it in tier_items(t, "−")]
    n = len(subs)
    assert sum(s % 10 < a % 10 for s, _, a in subs) * 2 >= n
    assert sum(a <= 9 and s >= 10 for s, _, a in subs) * 4 >= n
    assert sum(s % 10 == 0 or a % 10 == 0 or (s - a) % 10 == 0 for s, _, a in subs) * 4 <= n


# ---------------------------------------------------------------------------------------------
# Anti-tell rules
# ---------------------------------------------------------------------------------------------
def rank_of_answer(it):
    vals = [int(c) for c in it["choices"]]
    return sum(v < vals[it["answer"]] for v in vals)


@pytest.mark.parametrize("t", range(1, 6))
def test_no_middle_tell_rank_spread(t):
    its = tier_items(t)
    rc = Counter(rank_of_answer(it) for it in its)
    for r in range(4):
        assert 0.15 <= rc[r] / len(its) <= 0.35, (t, r, rc)


@pytest.mark.parametrize("t", range(1, 6))
def test_not_always_consecutive_neighbours(t):
    its = tier_items(t)
    tri = 0
    for it in its:
        vals = {int(c) for c in it["choices"]}
        s = int(it["choices"][it["answer"]])
        tri += {s - 1, s + 1} <= vals
    assert tri / len(its) <= 0.5


def ones_alone(it):
    vals = [int(c) for c in it["choices"]]
    s = vals[it["answer"]]
    return all(v % 10 != s % 10 for k, v in enumerate(vals) if k != it["answer"])


@pytest.mark.parametrize("t,ops", [(3, "+−"), (4, "+−×÷"), (5, "+−×÷")])
def test_no_ones_digit_tell(t, ops):
    its = [it for op in ops for it in tier_items(t, op)]
    # add / subtract from tier 3, multiply / divide from tier 4: the tier's items of those operations
    assert sum(ones_alone(it) for it in its) / len(its) <= 0.25, t
    if t >= 4:
        for op in "×÷":
            sub = tier_items(t, op)
            assert sum(ones_alone(it) for it in sub) / len(sub) <= 0.25, (t, op)


def test_ones_digit_checker_can_fail():
    tell = {"choices": ["81", "82", "83", "85"], "answer": 3}
    ok = {"choices": ["75", "84", "85", "95"], "answer": 2}
    assert ones_alone(tell) and not ones_alone(ok)
    assert sum(ones_alone(it) for it in [tell] * 20 + [ok] * 20) / 40 > 0.25
    assert sum(ones_alone(it) for it in [tell] * 10 + [ok] * 30) / 40 <= 0.25


def test_text_limits():
    for it in ITEMS:
        assert len(it["prompt"]) <= 60 and len(it["explanation"]) <= 160
        assert all(len(c) <= 14 for c in it["choices"])
    for m in MANIFEST["misconceptions"].values():
        assert len(m["student"]) <= 80
    assert len(MANIFEST["title"]) <= 32 and len(MANIFEST["subtitle"]) <= 40
    assert all(len(t["name"]) <= 24 for t in MANIFEST["tiers"])


def test_sabotaged_generator_is_caught(monkeypatch):
    """Disproof on the generator: drop the ones-digit requirement and the baked-style checks must trip."""
    real = G.mul_sets

    def lazy(a, b, tier, use_added):
        # offer only the group-off values: no ones-digit wrong value on tiers 4-5
        return [s for s in real(a, b, tier, use_added)
                if not any(k in ("MUL_TENS_SLIP", "MUL_DROPPED_CARRY", "MUL_PARTIAL_PRODUCTS") for _, k in s[2])]

    monkeypatch.setattr(G, "mul_sets", lazy)
    try:
        items = G.generate(MANIFEST, random.Random(MANIFEST["seed"]))
    except RuntimeError:
        return  # the generator itself refused: also a catch
    t5 = [it for it in items if it["tier"] == 5 and parse(it["prompt"])[1] == "×"]
    assert sum(ones_alone(it) for it in t5) / len(t5) > 0.25
