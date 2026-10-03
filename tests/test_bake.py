"""Bake determinism and file format (PROTOCOL §4, §5 rule 9)."""
import json

from conftest import CID
from fnm.cart import bake, bake_bytes, REPO_ROOT


def test_bake_twice_byte_identical(tmp_repo):
    a = bake(CID, tmp_repo).read_bytes()
    b = bake(CID, tmp_repo).read_bytes()
    assert a == b


def test_committed_baked_matches_fresh_bake():
    assert bake_bytes(CID) == (REPO_ROOT / "cartridges" / CID / "baked.json").read_bytes()


def test_format(tmp_repo):
    raw = bake(CID, tmp_repo).read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert b"\r" not in raw
    text = raw.decode("utf-8")
    assert "×" in text  # ensure_ascii=False
    data = json.loads(text)
    manifest = json.loads((tmp_repo / "cartridges" / CID / "cartridge.json").read_text(encoding="utf-8"))
    assert list(data)[: len(manifest)] == list(manifest)
    assert list(data)[len(manifest):] == ["baked_with", "items"]
    assert list(data["items"][0]) == ["id", "tier", "prompt", "choices", "answer", "misconceptions",
                                      "explanation"]
    assert data["items"][0]["id"] == f"{CID}/t1/001"
    assert data["items"][-1]["id"] == f"{CID}/t5/040"
