"""validate passes on the real cartridge and fails on targeted mutations."""
import json

import pytest

from conftest import CID, write_json
from fnm.validate import validate


def test_real_cartridge_valid():
    fails = validate(CID)  # includes rule 9 (rebakes twice, compares to the file)
    assert fails == [], [str(f) for f in fails]


def _mutate(tmp_repo, fn):
    path = tmp_repo / "cartridges" / CID / "baked.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    write_json(path, data)
    return validate(CID, tmp_repo, check_determinism=False)


def _flip_answer(d):
    it = d["items"][0]
    it["answer"] = (it["answer"] + 1) % len(it["choices"])


def _dup_choice(d):
    it = d["items"][0]
    other = (it["answer"] + 1) % 4
    it["choices"][other] = " " + it["choices"][it["answer"]] + " "


def _long_prompt(d):
    d["items"][0]["prompt"] = "1 + " * 14 + "12345"  # 61 chars


def _undeclared(d):
    it = d["items"][0]
    it["misconceptions"][(it["answer"] + 1) % 4] = "NOT_A_RULE"


def _tier_23(d):
    t1 = [it for it in d["items"] if it["tier"] == 1]
    drop = {it["id"] for it in t1[23:]}
    d["items"] = [it for it in d["items"] if it["id"] not in drop]


def _ipt_23(d):
    d["items_per_tier"] = 23


def _accent(d):
    d["items"][0]["explanation"] = "Café: " + d["items"][0]["explanation"]


def _accent_title(d):
    d["title"] = "Opérations"


def _bad_protocol(d):
    d["protocol"] = "fnm-cart/2"


def _tier_gap(d):
    d["tiers"][1]["tier"] = 7


def _dup_prompt(d):
    d["items"][1]["prompt"] = d["items"][0]["prompt"]


def _unbalanced(d):
    for it in d["items"]:
        if it["tier"] == 2 and it["answer"] != 0:
            a = it["answer"]
            for k in ("choices", "misconceptions"):
                it[k][0], it[k][a] = it[k][a], it[k][0]
            it["answer"] = 0


@pytest.mark.parametrize("mutation,rule,needle", [
    (_flip_answer, 5, "null"),
    (_dup_choice, 5, "duplicate choices"),
    (_long_prompt, 6, "prompt is 61 chars"),
    (_undeclared, 5, "'NOT_A_RULE' is not declared"),
    (_tier_23, 3, "has 23 items"),
    (_ipt_23, 3, "items_per_tier 23"),
    (_accent, 7, "'é'"),
    (_accent_title, 7, "'é'"),
    (_bad_protocol, 1, "fnm-cart/2"),
    (_tier_gap, 2, "contiguously"),
    (_dup_prompt, 4, "duplicates"),
    (_unbalanced, 8, "position 0"),
])
def test_mutation_fails(tmp_repo, mutation, rule, needle):
    fails = _mutate(tmp_repo, mutation)
    hits = [f for f in fails if f.rule == rule and needle in str(f)]
    assert hits, [str(f) for f in fails]


def test_failure_names_item(tmp_repo):
    fails = _mutate(tmp_repo, _long_prompt)
    assert any(f.where == f"{CID}/t1/001" for f in fails)


def test_stale_baked_fails_rule9(tmp_repo):
    path = tmp_repo / "cartridges" / CID / "baked.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["items"][0]["explanation"] = data["items"][0]["explanation"].replace(", then", ", and then", 1)
    write_json(path, data)
    fails = validate(CID, tmp_repo)
    assert any(f.rule == 9 and "stale" in f.msg for f in fails)
