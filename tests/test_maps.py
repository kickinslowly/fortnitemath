"""Map profiles (PROTOCOL §6a): choice reduction, map validation, per-map emit, sync."""
import json

import pytest

from conftest import CID, write_json
from fnm import cli
from fnm.emit import emit_maps, verse_source
from fnm.maps import UEFN_VERSE_SUBPATH, read_slot, reduce_item, sync, validate_map
from verse_lint import lint, string_literals

ITEM = {
    "id": "x/t1/001", "tier": 1, "prompt": "3 + 4 × 2",
    "choices": ["14", "12", "11", "9"],
    "answer": 2,
    "misconceptions": ["ADD_FIRST", "ARITH", None, "ARITH"],
    "explanation": "4 × 2 = 8, then 3 + 8 = 11.",
}
ITEM2 = {  # two misconceptions, one ARITH, answer first
    "id": "x/t1/002", "tier": 1, "prompt": "2 × 3 + 4 × 5",
    "choices": ["26", "50", "27", "70"],
    "answer": 0,
    "misconceptions": [None, "LTR", "ARITH", "ADD_FIRST"],
    "explanation": "",
}


def test_reduce_golden_three():
    r = reduce_item(ITEM, 3)  # drop the LAST ARITH ("9")
    assert r["choices"] == ["14", "12", "11"]
    assert r["misconceptions"] == ["ADD_FIRST", "ARITH", None]
    assert r["answer"] == 2


def test_reduce_golden_two():
    r = reduce_item(ITEM, 2)  # both ARITH go
    assert r["choices"] == ["14", "11"]
    assert r["misconceptions"] == ["ADD_FIRST", None]
    assert r["answer"] == 1


def test_reduce_misconceptions_last_first():
    assert reduce_item(ITEM2, 3)["choices"] == ["26", "50", "70"]
    r = reduce_item(ITEM2, 2)  # ARITH, then last misconception (ADD_FIRST)
    assert r["choices"] == ["26", "50"] and r["misconceptions"] == [None, "LTR"] and r["answer"] == 0


def test_reduce_noop_and_no_mutation():
    before = json.dumps(ITEM)
    assert reduce_item(ITEM, 4) == ITEM
    reduce_item(ITEM, 2)
    assert json.dumps(ITEM) == before


@pytest.mark.parametrize("k", [2, 3])
def test_reduce_all_baked_items_keep_answer(baked, k):
    for it in baked["items"]:
        r = reduce_item(it, k)
        assert len(r["choices"]) == k
        assert r["choices"][r["answer"]] == it["choices"][it["answer"]]
        assert r["misconceptions"][r["answer"]] is None
        assert [c for c in it["choices"] if c in r["choices"]] == r["choices"]  # order kept


def test_verse_reduced_feedback_reindexed(baked):
    b = dict(baked, items=baked["items"][:5])
    src = verse_source(b, "unicode", max_choices=2, map_id="tiny")
    assert lint(src) == []
    lines = [l for l in src.splitlines() if l.strip().startswith("fnm_item{")]
    for it, line in zip(b["items"], lines):
        r = reduce_item(it, 2)
        lits = string_literals(line)
        assert lits[2:4] == r["choices"]
        assert lits[4:6][r["answer"]] == ""
        assert f"Answer := {r['answer']}," in line


GOOD_MAP = {"protocol": "fnm-cart/1", "id": "tiny", "title": "Tiny", "max_choices": 2,
            "render_profile": "ascii", "uefn_project": None}


@pytest.mark.parametrize("patch,needle", [
    ({"protocol": "fnm-cart/2"}, "protocol"),
    ({"id": "Other"}, "id"),
    ({"max_choices": 1}, "max_choices"),
    ({"max_choices": 5}, "max_choices"),
    ({"render_profile": "fancy"}, "render_profile"),
    ({"uefn_project": "relative/path"}, "uefn_project"),
])
def test_map_validation(patch, needle):
    assert validate_map(GOOD_MAP, "tiny") == []
    fails = validate_map({**GOOD_MAP, **patch}, "tiny")
    assert any(needle in f for f in fails), fails


def test_emit_every_map(tmp_repo):
    (tmp_repo / "maps" / "tiny").mkdir()
    write_json(tmp_repo / "maps" / "tiny" / "map.json", GOOD_MAP)
    out = emit_maps(CID, tmp_repo)
    assert [m for m, _, _ in out] == ["starter", "tiny"]
    tiny = (tmp_repo / "maps" / "tiny" / "generated" / "fnm_active_cartridge.verse").read_text(encoding="utf-8")
    assert "profile: ascii" in tiny and "max_choices: 2" in tiny and lint(tiny) == []
    version = json.loads((tmp_repo / "cartridges" / CID / "cartridge.json").read_text(encoding="utf-8"))["version"]
    assert read_slot("tiny", tmp_repo) == {"id": CID, "version": version, "profile": "ascii"}
    # --profile override
    emit_maps(CID, tmp_repo, profile_override="unicode")
    assert read_slot("tiny", tmp_repo)["profile"] == "unicode"


def test_emit_refuses_invalid_map(tmp_repo):
    (tmp_repo / "maps" / "bad").mkdir()
    write_json(tmp_repo / "maps" / "bad" / "map.json", {**GOOD_MAP, "id": "bad", "max_choices": 9})
    with pytest.raises(ValueError, match="max_choices"):
        emit_maps(CID, tmp_repo)


def test_sync_null_project(tmp_repo, capsys):
    m = json.loads((tmp_repo / "maps" / "starter" / "map.json").read_text(encoding="utf-8"))
    m["uefn_project"] = None
    write_json(tmp_repo / "maps" / "starter" / "map.json", m)
    assert cli.main(["--root", str(tmp_repo), "sync", "starter"]) == 0
    assert "uefn_project is null" in capsys.readouterr().out


def test_sync_copies(tmp_repo, tmp_path_factory):
    proj = tmp_path_factory.mktemp("uefn") / "MyIsland"
    proj.mkdir()
    m = json.loads((tmp_repo / "maps" / "starter" / "map.json").read_text(encoding="utf-8"))
    m["uefn_project"] = str(proj)
    write_json(tmp_repo / "maps" / "starter" / "map.json", m)
    emit_maps(CID, tmp_repo)
    copied = sync("starter", tmp_repo)
    dest = proj / UEFN_VERSE_SUBPATH.format(project="MyIsland")
    names = sorted(p.name for p in dest.iterdir())
    assert "fnm_active_cartridge.verse" in names and "fnm_cartridge.verse" in names
    assert all(p.parent == dest for p in copied)
