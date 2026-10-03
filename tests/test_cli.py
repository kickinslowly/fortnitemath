"""CLI end-to-end in a temp repo: insert, insert-stops-on-invalid, new, list, validate exit codes."""
import json

from conftest import CID, write_json
from fnm import cli


def run(root, *args):
    return cli.main(["--root", str(root), *args])


def test_insert_and_list(tmp_repo, capsys):
    assert run(tmp_repo, "insert", CID) == 0
    assert (tmp_repo / "maps" / "starter" / "generated" / "fnm_active_cartridge.verse").exists()
    assert (tmp_repo / "emulator" / "carts.js").exists()
    assert run(tmp_repo, "list") == 0
    out = capsys.readouterr().out
    assert "t1:40" in out and "slot: order-of-ops-exponents 1.0.0 (unicode)" in out


def test_insert_stops_before_emit_on_invalid(tmp_repo, capsys):
    m_path = tmp_repo / "cartridges" / CID / "cartridge.json"
    m = json.loads(m_path.read_text(encoding="utf-8"))
    m["title"] = "Ordre des opérations"  # é: rule 7
    write_json(m_path, m)
    assert run(tmp_repo, "insert", CID) == 1
    out = capsys.readouterr().out
    assert "rule 7" in out and "stopped before emit" in out
    assert not (tmp_repo / "maps" / "starter" / "generated").exists()
    assert not (tmp_repo / "emulator" / "carts.js").exists()


def test_validate_exit_codes(tmp_repo):
    assert run(tmp_repo, "bake", CID) == 0
    assert run(tmp_repo, "validate", CID) == 0
    p = tmp_repo / "cartridges" / CID / "baked.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["items"][0]["answer"] = 9
    write_json(p, d)
    assert run(tmp_repo, "validate", CID) == 1


def test_new_scaffold_round_trips(tmp_repo, capsys):
    assert run(tmp_repo, "new", "fractions-basics") == 0
    d = tmp_repo / "cartridges" / "fractions-basics"
    assert (d / "cartridge.json").exists() and (d / "generator.py").exists()
    assert run(tmp_repo, "insert", "fractions-basics") == 0
    js = (tmp_repo / "emulator" / "carts.js").read_text(encoding="utf-8")
    assert '"fractions-basics"' in js and f'"{CID}"' in js  # carts.js holds every baked cart
    assert run(tmp_repo, "new", "fractions-basics") == 2  # already exists
    assert run(tmp_repo, "new", "Bad_Id") == 2
