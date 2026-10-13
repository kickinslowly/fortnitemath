"""The HUD slate agrees with the course and its art: the tile colours are the door paint's hues and draw as the sRGB they
are typed as (FnmSrgb undoes the Verse UI's brightening), the tile letter is 40 px, the recap card API exists, every
texture the Verse names has a PNG (and no PNG is dead), the PNGs have the sizes the widgets expect, the director hands
the slate the choices themselves, the HUD copy is the agreed wording, and the art script is deterministic."""
import ast
import colorsys
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
                "fnm_check.png": (256, 256), "fnm_cross.png": (256, 256),
                "fnm_banner.png": (1024, 256), "fnm_nuke.png": (256, 256)}
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
    for out in ("a", "b"):
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_boss_art.py"), str(tmp_path / out)], check=True,
                       capture_output=True)
    for name in ("fnm_banner.png", "fnm_nuke.png"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
        assert (tmp_path / "a" / name).read_bytes() == (ART / name).read_bytes(), name


def test_verse_files_are_lf():
    for path in VERSE.glob("*.verse"):
        assert b"\r" not in path.read_bytes(), path.name


# ---------------------------------------------------------------- tile colours (G9 H, 2026-10-13)

def srgb_encode(v):
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def tile_srgb():
    block = ui_src().split("FnmTileSrgb : []color = array:\n", 1)[1].split("\n\n", 1)[0]
    literals = re.findall(r"color\{R := ([\d.]+), G := ([\d.]+), B := ([\d.]+)\}", block)
    return [tuple(float(v) for v in rgb) for rgb in literals]


def hue(rgb):
    return colorsys.rgb_to_hsv(*rgb)[0] * 360


def hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def test_tiles_are_drawn_through_the_srgb_correction():
    """Measured in play: a raw `color{}` draws ~3.86x too bright (B and C both came out cyan, D yellow). The tiles' ring,
    letter, value and glow take FnmTileSrgb through FnmSrgb (= MakeColorFromSRGB) and FnmUi (x 0.259 at the widget),
    never FnmDoorColors."""
    src = ui_src()
    assert "FnmUiGain : float = 0.259" in src
    assert "FnmUi(C:color):color = C * FnmUiGain" in src
    assert "FnmSrgb(R:float, G:float, B:float):color = MakeColorFromSRGB(R, G, B)" in src
    assert "set Tints += array{FnmSrgb(S.R, S.G, S.B)}" in src
    assert "set TileTints = Tints" in src
    # no tile code reads the raw door colours any more (they stay defined and pinned for the course)
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    assert code.count("FnmDoorColors") == 1       # the table's own definition
    assert "TileTints[K]" in src and "Tints[K]" in src


def test_tile_colours_are_four_distinct_hues_near_the_door_paint():
    tiles = tile_srgb()
    assert tiles == [(1.0, 1.0, 1.0), (0.25, 0.55, 1.0), (0.2, 0.85, 0.25), (1.0, 0.58, 0.08)]
    tree = ast.parse((ROOT / "tools" / "build_course.py").read_text(encoding="utf-8"))
    doors = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "LETTER_COLOURS" for t in n.targets))
    # the door paint is a linear material colour, drawn as its sRGB encoding: that is the hue the tile has to match
    for K in (1, 2, 3):
        door = tuple(srgb_encode(v) for v in doors[K])
        assert hue_gap(hue(tiles[K]), hue(door)) <= 15, (K, hue(tiles[K]), hue(door))
    hues = [hue(tiles[K]) for K in (1, 2, 3)]
    assert min(hue_gap(a, b) for i, a in enumerate(hues) for b in hues[i + 1:]) >= 60   # B, C, D never collapse
    assert tiles[0] == (1.0, 1.0, 1.0)                                                 # A stays white


def test_tile_letter_is_40px_and_the_tile_fits_it():
    src = ui_src()
    block = src.split("    TileLetter : []text_block = array:\n", 1)[1].split("    TileValue", 1)[0]
    assert block.count("DefaultTextSize := 40.0") == 4 and "20.0" not in block
    art = src.split("    TileArt : []texture_block = array:\n", 1)[1].split("    TileLetter", 1)[0]
    sizes = re.findall(r"DefaultDesiredSize := vector2\{X := ([\d.]+), Y := ([\d.]+)\}", art)
    assert sizes == [("256.0", "112.0")] * 4
    # 40 px letter + 34 px value stacked (line heights ~1.2 x) must fit inside the ring: 48 + 41 + 2 = 91 < 112
    assert 40 * 1.2 + 34 * 1.2 + 2 < 112 - 2 * 6
    # four tiles with their 16 px gaps stay inside the slate's 1180 px (and so inside the HUD clear zone, x 364-1556)
    assert 4 * (256 + 16) + 2 * 30 <= 1180


# ---------------------------------------------------------------- recap card

def test_recap_card_api():
    src = ui_src()
    assert "    ShowRecap(Prompt:string, Choices:[]string, RightIndex:int, Steps:string, Verdict:string):int =" in src
    assert "    EndRecapIf(Generation:int):void =" in src
    # a newer ShowRecap / ShowQuestion / ClearQuestion bumps the generation, so a late EndRecapIf is a no-op
    assert "        if (Generation = RecapGeneration):\n            ClearRecap()" in src
    clear = src.split("    ClearRecap():void =\n", 1)[1].split("\n\n", 1)[0]
    assert "set RecapGeneration += 1" in clear
    for method in ("ShowQuestion(StageLine:string, Prompt:string, Choices:[]string):void =", "ClearQuestion():void ="):
        body = src.split("    " + method + "\n", 1)[1].split("\n\n", 1)[0]
        assert "ClearRecap()" in body, method
    show = src.split("    ShowRecap(", 1)[1].split("\n\n", 1)[0]
    assert "RecapGeneration" in show.splitlines()[-1]                       # returns the generation it made
    assert "Glow.SetOpacity(" in show and "FnmUi(Dimmed(TileColor" in show         # right tile lit, the others dimmed


def test_slate_height_is_stable_between_question_and_recap():
    """The caption row and the band under the tiles have fixed minimum heights (the verdict is taller than the
    caption, the steps up to two lines), so the slate does not jump when a recap opens (it moved 225 <-> 335 px)."""
    src = ui_src()
    assert "CaptionHeight : float = 34.0" in src and "BandHeight : float = 60.0" in src
    assert "Y := CaptionHeight" in src and "Y := BandHeight" in src
    # two 24 px lines of steps (1.2 x line height) fit the band
    assert 2 * 24 * 1.2 <= 60
    # the steps, feedback, streak and boss lines all live in the band
    band = src.split("Y := BandHeight}}", 1)[1].split("Padding := margin{Top := 6.0}", 1)[0]
    for widget in ("RecapSteps", "FeedbackText", "StreakBig", "BossText"):
        assert f"Widget := {widget}" in band, widget


# ---------------------------------------------------------------- copy

def test_hud_copy():
    src = ui_src()
    assert 'FnmFeedFinish<localizes>(Who:agent, Time:string, Medal:string):message = "{Who} finished in {Time}"' in src
    assert "{Medal}" not in src.split("FnmFeedFinish<localizes>", 1)[1].split("\n", 1)[0]
    assert "FnmFeedRecord<localizes>(Who:agent, Time:string):message = \"{Who} set today's record  {Time}\"" in src
    assert "Today's record   {Time}  by {Who}{Tail}" in src
    assert "island record" not in src.lower()
    assert 'PickerHeading.SetText(FnmText("PICK YOUR GRADE"))' in src
    assert 'PickerHeading.SetText(FnmText("PICK YOUR SKILL"))' in src
    assert "CHOOSE YOUR SKILL" not in src
    assert 'ChangeSkillButton.SetText(FnmText("NEW SKILL"))' in src
    assert 'CHANGE SKILL"' not in src
    # no player-facing "stage": every quoted string avoids the word
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    strings = re.findall(r'"([^"\n]*)"', code)
    assert not [s for s in strings if re.search(r"\bstage\b", s, re.I)]



# ---------------------------------------------------------------- HUD-wide colour correction (G9 H, follow-up)

def ui_code_lines():
    return [line for line in ui_src().splitlines() if not line.lstrip().startswith("#")]


def test_every_widget_colour_goes_through_fnmui():
    """Every colour that reaches a widget is corrected at the point it is set: a SetTextColor / SetColor / SetTint
    argument is wrapped in FnmUi(...), and a field default (DefaultTextColor / DefaultColor; a user function cannot be
    called in a class field initialiser, error 3582) is `<colour> * FnmUiGain`, the same factor. A raw NamedColors.* or
    color{} there draws ~3.86x too bright (Orange draws yellow, a door tint B cyan)."""
    lines = ui_code_lines()
    fields = [line for line in lines if re.search(r"\b(DefaultTextColor|DefaultColor|DefaultShadowColor) :=", line)]
    assert len(fields) > 40
    for line in fields:
        for hit in re.finditer(r"\b(DefaultTextColor|DefaultColor|DefaultShadowColor) := ", line):
            rest = line[hit.end():]
            assert rest.startswith("FnmUi(") or re.match(r"[^{}]*? \* FnmUiGain[,}]", rest), line.strip()
    setters = [line for line in lines if re.search(r"\.(SetTextColor|SetColor|SetTint)\(", line)]
    assert len(setters) > 20
    for line in setters:
        assert re.search(r"\.(SetTextColor|SetColor|SetTint)\(FnmUi\(", line), line.strip()
    # raw colour literals live only in the pinned tables and Dimmed's arithmetic; everywhere else an sRGB triple is
    # MakeColorFromSRGB / FnmSrgb, never a raw color{}
    for line in lines:
        if "color{R :=" in line:
            assert line.startswith("    color{R :=") or "color{R := Source.R" in line, line.strip()


def test_textures_are_tinted_back_down():
    """A texture draws lifted by the same gain (the slate PNG (34, 38, 40) came out near (94, 98, 101)): the three plain
    texture_blocks get the corrected white as their tint; the tiles take their own tint."""
    src = ui_src()
    for art in ("SlateArt", "BannerArt", "VerdictImage"):
        assert f"{art}.SetTint(FnmUi(NamedColors.White))" in src
    # white stays white: 1.0 x 0.259 x 3.86 ~ 1.0
    assert abs(1.0 * 0.259 * 3.86 - 1.0) < 0.01


# ---------------------------------------------------------------- feed vs finish board (G9 H, follow-up 2)

def verse_float(name):
    return float(re.search(r"^    " + name + r" : float = ([\d.]+)$", ui_src(), re.M).group(1))


def test_feed_and_finish_board_never_overlap():
    """Frame d3/f_135 (2026-10-13): the feed's record line ran from x 1370 into the finish board (right edge 1460). The board
    is centred and its lines wrap at ResultsWrap (+ 2 x 40 px padding); the feed hangs 20 px in from the right edge and wraps
    at FeedWrap (+ 2 x 20 px padding). The widest board and the widest feed panel must leave a gap, and the feed stays
    under the minimap (x 1603+, to y ~335) and under the slate (bottom y ~346) at Top 358."""
    src = ui_src()
    screen = 1920
    board_half = (verse_float("ResultsWrap") + 2 * 40) / 2
    board_right = screen / 2 + board_half
    feed_left = screen - 20 - (verse_float("FeedWrap") + 2 * 20)
    assert feed_left - board_right >= 16, (board_right, feed_left)
    # the paddings the arithmetic assumes
    assert "Padding := margin{Left := 40.0, Top := 28.0, Right := 40.0, Bottom := 28.0}" in src
    assert "Padding := margin{Left := 20.0, Top := 8.0, Right := 20.0, Bottom := 10.0}" in src
    assert "Offsets := margin{Left := -20.0, Top := 358.0, Right := 0.0, Bottom := 0.0}" in src
    # every board line and every feed row actually wraps at those widths
    assert src.count("WrapWidth = ResultsWrap") == 9 and "set Row.WrapWidth = FeedWrap" in src
    assert "set Row.WrapWidth = ResultsWrap" in src
    # the board still fits its widest agreed line (the accuracy line is ~917 px at 30 px)
    assert verse_float("ResultsWrap") >= 917


# ---------------------------------------------------------------- import_art textures(): keep what exists (G9 H, follow-up 3)

class RecordingUefn:
    """A stand-in for uefn_mcp.call: records every (tool, args), answers from canned replies; no UEFN is touched."""

    def __init__(self, existing=()):
        self.calls, self.existing = [], set(existing)

    def __call__(self, toolset, tool, args=None, **_):
        args = args or {}
        self.calls.append((tool, args))
        if tool == "exists":
            return {"returnValue": args["path"] in self.existing}
        if tool == "get_referencers":
            return {"returnValue": ["/proj/__ExternalActors__/FortStaticMeshActor_1"] * 2}
        return {"returnValue": [] if tool in ("import_file", "find_assets") else True}

    def tools(self):
        return [t for t, _ in self.calls]


def _with_fake(fake, fn):
    sys.path.insert(0, str(ROOT / "tools"))
    import import_art as ia
    saved = ia.u.call
    ia.u.call = fake
    ia.REPLACED.clear()
    try:
        return fn(ia)
    finally:
        ia.u.call = saved
        ia.REPLACED.clear()


def _all_textures(folder):
    return {f"{folder}/T_{p.stem}" for p in ART.glob("fnm_*.png")}


def test_default_import_keeps_existing_hud_textures(tmp_path):
    """The delete-then-reimport that emptied the course's materials (2026-10-13) also ran on every T_fnm_* texture on every
    default run. Now an existing texture is kept: a default run over a project that has them all makes no delete, no
    import, no move."""
    folder = "/proj/FNM_Art"
    fake = RecordingUefn(_all_textures(folder))
    _with_fake(fake, lambda ia: ia.textures(folder, tmp_path))
    assert "delete" not in fake.tools(), "the default run deleted an existing HUD texture"
    assert not {"import_file", "move", "save_assets", "set_properties"} & set(fake.tools()), fake.tools()


def test_default_import_brings_in_only_the_missing_texture(tmp_path):
    folder = "/proj/FNM_Art"
    fake = RecordingUefn(_all_textures(folder) - {f"{folder}/T_fnm_slate"})
    _with_fake(fake, lambda ia: ia.textures(folder, tmp_path))
    assert "delete" not in fake.tools()
    assert fake.tools().count("import_file") == 1 and fake.tools().count("save_assets") == 1
    assert any(a.get("asset_name") == "SM_fnm_slate" for t, a in fake.calls if t == "import_file")


def test_force_replaces_the_named_hud_texture_and_only_that_one(tmp_path):
    """A changed PNG needs --force <key>: the HUD keys are the PNG stems, and S's refusal of keys the course repaint does
    not cover must not block them (a texture has no course actors to repaint)."""
    folder = "/proj/FNM_Art"

    def run(ia):
        assert set(ia.HUD_KEYS) == {p.stem[len("fnm_"):] for p in ART.glob("fnm_*.png")} >= {"check", "cross", "slate", "tile"}
        ia.check_force(["tile"], True, False)              # no SystemExit: a HUD key is allowed
        ia.check_force(["tile", "banner", "nuke"], True, False)
        ia.textures(folder, tmp_path, ["tile"], True)
        return ia.REPLACED

    fake = RecordingUefn(_all_textures(folder))
    replaced = _with_fake(fake, run)
    assert fake.tools().count("import_file") == 1 and fake.tools().count("delete") == 1, fake.tools()
    assert any(t == "delete" and a["path"] == f"{folder}/T_fnm_tile" for t, a in fake.calls)
    assert not replaced, "a texture replace must not trigger the course repaint"


def test_force_still_refuses_what_the_course_repaint_does_not_cover():
    def run(ia):
        for keys in (["bm_stone"], ["tile", "bm_stone"], None):
            try:
                ia.check_force(keys, True, False)
            except SystemExit:
                continue
            raise AssertionError(f"--force {keys} was accepted")
    fake = RecordingUefn()
    _with_fake(fake, run)
    assert fake.tools() == []


def test_main_with_hud_keys_runs_textures_only(tmp_path):
    folder_tmp = "/proj"
    fake = RecordingUefn({f"{folder_tmp}/FNM_Art/T_fnm_tile"})

    def run(ia):
        orig = ia.mount
        ia.mount = lambda: folder_tmp
        try:
            ia.main(["tile"], True)
        finally:
            ia.mount = orig
    _with_fake(fake, run)
    assert fake.tools().count("import_file") == 1                      # the tile, not a door face or a wall material
    assert not any("door_face" in str(a) or "fnm_wall" in str(a) for t, a in fake.calls if t == "import_file")


# ---------------------------------------------------------------- big verdict text legibility (G9 H, follow-up 4)

def lum(srgb):
    lin = [(c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in srgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def test_big_verdict_text_has_a_shadow_and_a_backing_that_make_red_readable():
    """Q frame w1_4_stuck_in_mud (2026-10-13): the red verdict over the red / pink striped barrier measured contrast 1.05 : 1
    (stripes' mean luminance 0.20 against the text's 0.2126). The label has a text_block shadow and a black backing, 0.8
    while it has text; red text over the brightest (white) stripe through that backing must stay >= 3 : 1 (large-text AA)."""
    src = ui_src()
    label = re.search(r"    VerdictLabel : text_block = text_block\{(.*)\}\n", src).group(1)
    assert "DefaultShadowOffset := option{vector2{X := 4.0, Y := 4.0}}" in label
    assert "DefaultShadowColor := NamedColors.Black * FnmUiGain" in label and "DefaultShadowOpacity := 1.0" in label
    assert "DefaultTextSize := 96.0" in label
    # the backing: a black color_block under the label, shown at the same opacity everywhere the text is set
    assert "VerdictBack : color_block = color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.0}" in src
    opacities = re.findall(r"VerdictBack\.SetOpacity\(([\d.]+)\)", src)
    assert sorted(opacities) == ["0.0", "0.8"], opacities
    shown = float(max(opacities))
    assert shown >= 0.75
    red, white_stripe = lum((255, 0, 0)), lum((255 * (1 - shown),) * 3)
    assert (red + 0.05) / (white_stripe + 0.05) >= 3.0
    # the backing sits behind the label in the verdict stack, and the label's text is only ever set through SetVerdictText
    assert "Widget := VerdictBack" in src and src.index("Widget := VerdictBack") < src.index("Widget := VerdictLabel")
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    assert code.count("VerdictLabel.SetText(") == 1                    # the one inside SetVerdictText
    assert code.count("SetVerdictText(") >= 5
    for method in ("FlashVerdict(", "FlashBig(", "FlashNuke(", "ClearVerdictNow(", "ClearVerdictLater("):
        body = src.split("    " + method, 1)[1].split("\n\n", 1)[0]
        assert "SetVerdictText(" in body, method


def test_verdict_signatures_are_unchanged():
    src = ui_src()
    for sig in ("FlashVerdict(Correct:logic, Label:string):void =", "FlashBig(Text:string, TextColor:color, Seconds:float):void =",
                "FlashNuke(Label:string, Seconds:float):void =", "ClearVerdictNow():void =",
                "ClearVerdictLater(Generation:int, Seconds:float)<suspends>:void ="):
        assert "    " + sig in src, sig
