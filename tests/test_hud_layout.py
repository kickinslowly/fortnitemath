"""The HUD slate agrees with the course and its art: the tile colours are the door letter boards' colours, every
texture the Verse names has a PNG (and no PNG is dead), the PNGs have the sizes the widgets expect, the director hands
the slate the choices themselves, and the art script is deterministic."""
import ast
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"
ART = ROOT / "tools" / "art"


def ui_src():
    return (VERSE / "fnm_ui.verse").read_text(encoding="utf-8")


def test_door_colours_match_letter_boards():
    block = ui_src().split("FnmDoorColors : []color = array:\n", 1)[1].split("\n\n", 1)[0]
    literals = re.findall(r"color\{R := ([\d.]+), G := ([\d.]+), B := ([\d.]+)\}", block)
    hud = [tuple(float(v) for v in rgb) for rgb in literals]
    tree = ast.parse((ROOT / "tools" / "build_course.py").read_text(encoding="utf-8"))
    course = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "LETTER_COLOURS" for t in node.targets))
    assert hud == [tuple(c) for c in course]
    assert len(hud) == 4


def test_every_texture_has_a_png_and_every_png_is_used():
    referenced = set()
    for path in VERSE.glob("*.verse"):
        referenced |= set(re.findall(r"FNM_Art\.T_fnm_(\w+)", path.read_text(encoding="utf-8")))
    pngs = {p.stem[len("fnm_"):] for p in ART.glob("fnm_*.png")}
    assert {"check", "cross", "slate", "tile"} <= referenced
    assert referenced == pngs


def ihdr(path):
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert raw[12:16] == b"IHDR"
    width, height, depth, colour = struct.unpack(">IIBB", raw[16:26])
    return width, height, depth, colour


def test_png_sizes_and_format():
    expected = {"fnm_slate.png": (1024, 256), "fnm_tile.png": (560, 240),
                "fnm_check.png": (256, 256), "fnm_cross.png": (256, 256)}
    for name, size in expected.items():
        width, height, depth, colour = ihdr(ART / name)
        assert (width, height) == size, name
        assert (depth, colour) == (8, 6), name     # 8-bit RGBA


def test_director_passes_the_choices():
    director = (VERSE / "fnm_director.verse").read_text(encoding="utf-8")
    assert "State.Hud.ShowQuestion(StageLine, Item.Prompt, Shown)" in director
    assert "FnmChoicesLine(" not in director
    assert "ShowQuestion(StageLine:string, Prompt:string, Choices:[]string):void =" in ui_src()


def test_hud_art_is_deterministic(tmp_path):
    for out in ("a", "b"):
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_hud_art.py"), str(tmp_path / out)], check=True,
                       capture_output=True)
    for name in ("fnm_slate.png", "fnm_tile.png"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
        assert (tmp_path / "a" / name).read_bytes() == (ART / name).read_bytes(), name   # committed art is current


def test_verse_files_are_lf():
    for path in VERSE.glob("*.verse"):
        assert b"\r" not in path.read_bytes(), path.name
