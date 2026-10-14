"""The HUD slate agrees with the course and its art: the tile colours are the door paint's hues and draw as the sRGB they
are typed as (FnmSrgb undoes the Verse UI's brightening), the tile letter is 40 px, the recap card API exists, every
texture the Verse names has a PNG (and no PNG is dead), the PNGs have the sizes the widgets expect, the director hands
the slate the choices themselves, the HUD copy is the agreed wording, and the art script is deterministic."""
import ast
import colorsys
import re
import statistics
import struct
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert {"check", "cross", "slate", "tile", "medal_gold", "medal_silver", "medal_bronze", "volt",
            "volt_wag", "volt_thumbs", "volt_fire", "volt_shocked", "volt_go", "volt_think"} <= referenced
    assert referenced == pngs


def ihdr(path):
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert raw[12:16] == b"IHDR"
    width, height, depth, colour = struct.unpack(">IIBB", raw[16:26])
    return width, height, depth, colour


def test_png_sizes_and_format():
    expected = {"fnm_slate.png": (1024, 256), "fnm_tile.png": (560, 240), "fnm_logo.png": (512, 284),
                "fnm_check.png": (256, 256), "fnm_cross.png": (256, 256),
                "fnm_banner.png": (1024, 256), "fnm_nuke.png": (256, 256),
                "fnm_medal_gold.png": (256, 256), "fnm_medal_silver.png": (256, 256),
                "fnm_medal_bronze.png": (256, 256), "fnm_volt.png": (256, 256),
                **{f"fnm_volt_{k}.png": (256, 256) for k in ("wag", "thumbs", "fire", "shocked", "go", "think")}}
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
    """A texture draws lifted by the same gain (the slate PNG (34, 38, 40) came out near (94, 98, 101)): the plain
    texture_blocks (slate, banner, verdict, the finish board's Volt and medal, Volt's reaction card, the picker's logo) get the
    corrected white as their tint; the tiles take their own tint. Every texture_block in the file is one of these or a tile."""
    src = ui_src()
    plain = {"SlateArt", "BannerArt", "VerdictImage", "VoltArt", "MedalArt", "VoltCard", "LogoArt"}
    for art in plain:
        assert f"{art}.SetTint(FnmUi(NamedColors.White))" in src
    # no texture_block escapes the rule: a new one must be added here (and tinted) or it draws 3.86x too bright
    assert set(re.findall(r"^    (\w+) : texture_block = ", src, re.M)) == plain
    assert "    TileArt : []texture_block = array:" in src and "Art.SetTint(FnmUi(TileColor))" in src
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
    # (the headline and the medal word sit in the header row beside Volt and the medal: they wrap at HeaderWrap, below)
    assert src.count("WrapWidth = ResultsWrap") == 7 and "set Row.WrapWidth = FeedWrap" in src
    assert "set Row.WrapWidth = ResultsWrap" in src
    assert "set ResultsTitle.WrapWidth = HeaderWrap" in src and "set ResultsMedal.WrapWidth = HeaderWrap" in src
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


# ---------------------------------------------------------------- finish board art: medals and Volt (G9 H2, 2026-10-13)

def desired_size(name):
    line = re.search(r"^    " + name + r" : texture_block = texture_block\{(.*)\}$", ui_src(), re.M).group(1)
    x, y = re.search(r"DefaultDesiredSize := vector2\{X := ([\d.]+), Y := ([\d.]+)\}", line).groups()
    return float(x), float(y)


def text_size(field):
    return float(re.search(field + r" : text_block = .*?DefaultTextSize := ([\d.]+)", ui_src()).group(1))


def test_finish_board_header_holds_volt_and_the_medal_without_overlapping_text():
    """Volt (left) and the medal (right) are IN the header row with the headline over the medal word between them, so they
    cannot sit on a text line by construction; the row's width is VoltArt + gap + HeaderWrap + gap + MedalArt and must stay
    inside ResultsWrap, the content width every other board line already fits (so the board is no wider than before and the
    feed / minimap clearances in test_feed_and_finish_board_never_overlap still hold)."""
    src = ui_src()
    volt, medal = desired_size("VoltArt"), desired_size("MedalArt")
    assert volt[0] == volt[1] and medal[0] == medal[1]            # square PNGs drawn square, never stretched
    assert 180 <= volt[0] <= 220 and 150 <= medal[0] <= 180       # brief H2
    wrap, gap = verse_float("HeaderWrap"), verse_float("HeaderGap")
    assert volt[0] + gap + wrap + gap + medal[0] <= verse_float("ResultsWrap")
    # the words in the middle column fit their wrap (a loose 0.65 em per glyph: the widest are VICTORY! and SILVER MEDAL)
    for field, word in (("ResultsTitle", "VICTORY!"), ("ResultsMedal", "SILVER MEDAL")):
        assert len(word) * 0.65 * text_size(field) <= wrap, (field, word)
    # layout: header = Volt | (headline over medal word) | medal; ResultsLines holds the row, never the art or those words itself
    header = src.split("ResultsHeader : stack_box = stack_box:", 1)[1].split("            ResultsLines : stack_box", 1)[0]
    order = [header.index(f"Widget := {w}") for w in ("VoltArt", "ResultsTitle", "ResultsMedal", "MedalArt")]
    assert order == sorted(order)
    lines = src.split("ResultsLines : stack_box = stack_box:", 1)[1].split("for (Row : ResultsRows):", 1)[0]
    assert "Widget := ResultsHeader" in lines
    for widget in ("VoltArt", "MedalArt", "ResultsTitle", "ResultsMedal"):
        assert f"Widget := {widget}" not in lines, widget


def test_finish_board_stays_above_the_finish_buttons():
    """CLOSE / NEW SKILL (a map without a podium) hang from 0.81 of the screen height; the taller header (Volt) must not push
    a board with all five time rows into them. Line height 1.24 x font size, calibrated on the 2026-10-13 play frame: a
    one-row board with a 200 px Volt measured 592 px tall (y 130-722); the estimate for that board is 593. A 200 px Volt
    with five rows came out at ~881, over the buttons' 875, hence 180."""
    src = ui_src()
    k = 1.24
    header = max(desired_size("VoltArt")[1], k * (text_size("ResultsTitle") + text_size("ResultsMedal")), desired_size("MedalArt")[1])
    body = k * sum(text_size(f) for f in ("ResultsTime", "ResultsBest", "ResultsRecord", "ResultsAccuracy", "ResultsBoardHead"))
    body += 18 + 5 * k * 32 + k * text_size("ResultsCountdown") + 18          # board head's and countdown's top paddings, 5 rows
    slot = src.split("                        Widget := Results\n", 1)[1].split("SizeToContent", 1)[0]
    top = float(re.search(r"Offsets := margin\{Left := 0\.0, Top := ([\d.]+)", slot).group(1))
    bottom = top + 28 + header + body + 28
    buttons_slot = src.split("                            Widget := stack_box:\n                                Orientation := orientation.Horizontal\n"
                             "                                Slots := array:\n                                    stack_box_slot{Widget := CloseButton", 1)[1]
    buttons = float(re.search(r"Anchors := anchors\{Minimum := vector2\{X := 0\.5, Y := ([\d.]+)\}", buttons_slot).group(1)) * 1080
    assert bottom <= buttons - 8, (bottom, buttons)


def test_show_results_picks_the_medal_texture_for_the_medal_word():
    src = ui_src()
    logic = (VERSE / "fnm_logic.verse").read_text(encoding="utf-8")
    medal_fn = logic.split("FnmMedal(", 1)[1].split("\n\n", 1)[0]
    for word in ("GOLD", "SILVER", "BRONZE"):
        assert f'"{word}"' in medal_fn                                  # the words FnmMedal hands to ShowResults
    body = src.split("    ShowMedalArt(Medal:string):void =\n", 1)[1].split("\n\n", 1)[0]
    pairs = re.findall(r'(?:if|else if) \(Medal = "(\w+)"\):\n\s+MedalArt\.SetImage\(FNM_Art\.T_fnm_medal_(\w+)\)\n'
                       r'\s+MedalArt\.SetVisibility\(widget_visibility\.Visible\)', body)
    assert pairs == [("GOLD", "gold"), ("SILVER", "silver"), ("BRONZE", "bronze")]
    # anything else, "" included (boss mode may pass it), collapses the picture
    assert body.rstrip().endswith("else:\n            MedalArt.SetVisibility(widget_visibility.Collapsed)")
    show = src.split("    ShowResults(", 1)[1].split("\n\n", 1)[0]
    assert "        ShowMedalArt(Medal)" in show
    assert 'SetOrCollapse(ResultsMedal, if (Medal = "") then "" else "{Medal} MEDAL")' in show   # the word stays, collapses on ""
    assert "ResultsMedal.SetTextColor(FnmUi(MedalColor))" in show
    # ShowResults keeps its signature (the director and boss mode call it)
    assert ("    ShowResults(Title:string, Medal:string, MedalColor:color, TimeLine:string, BestLine:string, RecordLine:message, "
            "AccuracyLine:string, BoardHead:string, Rows:[]message, OwnRow:int):void =") in src


def medal_stats(name):
    """(median hue, mean saturation) of the medal disc's lit pixels in a committed PNG (the ribbon at the top and the black
    outline are left out)."""
    Image = pytest.importorskip("PIL.Image")
    im = Image.open(ART / name).convert("RGBA")
    hs, ss = [], []
    for y in range(110, 250):
        for x in range(40, 216):
            r, g, b, a = im.getpixel((x, y))
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if a >= 200 and v >= 0.35:
                hs.append(h * 360)
                ss.append(s)
    assert len(hs) > 5000, name
    return statistics.median(hs), statistics.mean(ss)


def test_the_three_medal_pngs_are_the_three_metals():
    """What a kid sees: gold is yellow-orange and saturated, bronze a redder orange, silver nearly grey. If a PNG were
    swapped or regenerated from the wrong raw, one of these fails."""
    gold, silver, bronze = (medal_stats(f"fnm_medal_{m}.png") for m in ("gold", "silver", "bronze"))
    assert 30 <= gold[0] <= 50 and gold[1] > 0.7, gold
    assert 8 <= bronze[0] <= 28 and 0.4 < bronze[1] < 0.8, bronze
    assert silver[1] < 0.35, silver
    assert bronze[0] < gold[0] - 10


def test_art_pngs_are_square_with_a_transparent_surround():
    Image = pytest.importorskip("PIL.Image")
    for name in ("fnm_medal_gold.png", "fnm_medal_silver.png", "fnm_medal_bronze.png", "fnm_volt.png",
                 *(f"fnm_volt_{k}.png" for k in ("wag", "thumbs", "fire", "shocked", "go", "think"))):
        im = Image.open(ART / name).convert("RGBA")
        assert im.size == (256, 256), name
        assert all(im.getpixel(c)[3] == 0 for c in ((0, 0), (255, 0), (0, 255), (255, 255))), name   # transparent corners
        alpha = im.getchannel("A")
        box = alpha.getbbox()
        assert box[1] == 0 and (box[3] == 256 or name == "fnm_volt.png"), (name, box)               # subject fills the height
        assert abs(box[0] + box[2] - 256) <= 40, (name, box)                                        # and sits near the middle


def test_make_medal_art_crops_to_the_subject_and_ignores_a_stray_pixel():
    """The raw silver and bronze carry a stray near-transparent pixel at the image edge: the alpha bbox started at 0,0 and the
    medal came out small and off-centre. A synthetic raw with the same flaw must still come out centred and filling the height."""
    Image = pytest.importorskip("PIL.Image")
    sys.path.insert(0, str(ROOT / "tools"))
    import make_medal_art as mm
    raw = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    raw.paste(Image.new("RGBA", (400, 800), (200, 120, 30, 254)), (300, 100))      # subject: 400 x 800, off-centre
    raw.putpixel((0, 0), (255, 255, 255, 3))                                       # stray pixel below the cut
    raw.putpixel((1023, 1023), (255, 255, 255, 15))                                # and one at the cut's edge
    out = mm.prepare(raw)
    assert out.size == (256, 256)
    left, top, right, bottom = out.getchannel("A").getbbox()                       # 800 square -> 256: 400 wide = 128, centred
    assert (top, bottom) == (0, 256) and abs(left + right - 256) <= 2 and 120 <= right - left <= 140, (left, top, right, bottom)
    assert out.getpixel((0, 0))[3] == 0 and out.getpixel((255, 255))[3] == 0
    assert all(abs(a - b) <= 2 for a, b in zip(out.getpixel((128, 128))[:3], (200, 120, 30)))   # premultiplied rounding


def test_committed_art_is_what_make_medal_art_makes_from_the_raws():
    """The four PNGs are reproducible from the raw Meshy renders (kept under art/, outside tools/art/): skipped when the raws
    are not in this checkout."""
    Image = pytest.importorskip("PIL.Image")
    sys.path.insert(0, str(ROOT / "tools"))
    import make_medal_art as mm
    raws = [(ROOT / src, name) for src, name in mm.JOBS]
    if not all(path.exists() for path, _ in raws):
        pytest.skip("raw Meshy renders not in this checkout")
    for path, name in raws:
        made = mm.prepare(Image.open(path))
        assert made.tobytes() == Image.open(ART / name).convert("RGBA").tobytes(), name


# ---------------------------------------------------------------- the DOORS OF DOOM logo on the picker (G9 D2, 2026-10-13)

# Measured on 1920 x 1080 play frames of the picker before the logo (2026-10-13, %TEMP% pick0.png / grade6.png): the grade
# step's dark panel ran y 235-738 (503 px: heading, step line, BOSS BATTLE + its caption, GRADE 6, GRADE 7) and the grade-6
# skill step's y 51-921 (870 px: ten skills in two columns, captions, BACK). The panel is centred on 0.45 of the height.
PICKER_PANEL_PX = {"ShowGradeStep": 503, "ShowSkillStep": 870}
PICKER_CENTRE_Y = 0.45 * 1080
# 20 px clear of the screen's top and bottom edges. (The skill step's 921 already touches the top 11 px of the hotbar's first
# slot, x 1418-1496 from y 910, in grade6.png: it was so before the logo, which is not on that step.)
PICKER_TOP_MIN, PICKER_BOTTOM_MAX = 20, 1060


def logo_slot():
    src = ui_src()
    stack = src.split("PickerPanel : overlay = overlay:", 1)[1].split("set MaybePickerRoot", 1)[0]
    return stack


def logo_visible_on(step):
    """True when the picker step method `step` shows the logo, False when it collapses it (it must say which)."""
    body = ui_src().split(f"    {step}(", 1)[1].split("\n\n", 1)[0]
    shown = "LogoArt.SetVisibility(widget_visibility.Visible)" in body
    hidden = "LogoArt.SetVisibility(widget_visibility.Collapsed)" in body
    assert shown != hidden, step
    return shown


def test_logo_png_is_the_logo_cropped_with_its_aspect():
    Image = pytest.importorskip("PIL.Image")
    im = Image.open(ART / "fnm_logo.png").convert("RGBA")
    assert im.size == (512, 284)
    assert im.getchannel("A").getbbox() == (0, 0, 512, 284)            # cropped to the letters, no empty margin
    assert all(im.getpixel(c)[3] == 0 for c in ((0, 0), (511, 0), (0, 283), (511, 283)))   # rounded backing: corners clear
    sys.path.insert(0, str(ROOT / "tools"))
    import make_medal_art as mm
    raw = ROOT / mm.LOGO_JOB[0]
    if raw.exists():                                                   # reproducible from the raw Aaron chose (logo b)
        assert mm.prepare_logo(Image.open(raw)).tobytes() == im.tobytes()
        w, h = mm.crop_to_alpha(Image.open(raw)).size
        assert abs(512 / 284 - w / h) < 0.01                           # aspect kept, not squared


def test_logo_sits_over_the_grade_heading_and_the_picker_fits_1080p():
    """The logo is the first thing in the picker panel, over PICK YOUR GRADE (never among the buttons), drawn at its PNG's
    size, shown on the grade step and collapsed on the skill step; with it, every step still fits a 1080p screen."""
    src = ui_src()
    size = desired_size("LogoArt")
    assert size == (512.0, 284.0)                                      # the PNG pixel for pixel
    stack = logo_slot()
    order = [stack.index(f"Widget := {w}") for w in ("LogoArt", "PickerHeading", "PickerStep", "PickerButtons")]
    assert order == sorted(order)
    pad = float(re.search(r"Widget := LogoArt\n\s+HorizontalAlignment := horizontal_alignment.Center\n\s+Padding := "
                          r"margin\{Bottom := ([\d.]+)\}", stack).group(1))
    assert "PickerButtons.AddWidget(stack_box_slot{Widget := LogoArt" not in src
    assert logo_visible_on("ShowGradeStep") and not logo_visible_on("ShowSkillStep")
    for step, base in PICKER_PANEL_PX.items():
        height = base + (size[1] + pad if logo_visible_on(step) else 0)
        top, bottom = PICKER_CENTRE_Y - height / 2, PICKER_CENTRE_Y + height / 2
        assert top >= PICKER_TOP_MIN and bottom <= PICKER_BOTTOM_MAX, (step, top, bottom)
    # the logo is no wider than the grade step's widest line (the BOSS BATTLE caption, ~575 px), so the panel keeps its width
    assert size[0] <= 575
