"""Volt's reaction cards (G9 V, 2026-10-13): the HUD card (fnm_ui.verse ShowVolt / HideVolt), where it sits at 1920 x 1080 against
everything else the HUD draws, which texture each mood shows, the generation counter that keeps an old timer from hiding a newer
card, every call site in the director and boss mode, and the two new sound cue ids."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"
ART = ROOT / "tools" / "art"
KINDS = ("go", "thumbs", "fire", "wag", "shocked", "think")


def src(name):
    return (VERSE / f"{name}.verse").read_text(encoding="utf-8")


def ui():
    return src("fnm_ui")


def code(text):
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def method_body(text, header):
    """The indented body of the method whose header line starts with `header` (up to the next blank line)."""
    return text.split("    " + header, 1)[1].split("\n\n", 1)[0]


# ---------------------------------------------------------------- the card widget and its art

def test_enum_has_the_six_moods_and_each_mood_shows_its_own_texture():
    text = ui()
    body = text.split("fnm_volt := enum:\n", 1)[1].split("\n\n", 1)[0]
    assert [line.strip() for line in body.splitlines()] == ["Go", "Thumbs", "Fire", "Wag", "Shocked", "Think"]
    show = method_body(text, "ShowVolt(Kind:fnm_volt):void =\n")
    pairs = re.findall(r"(?:if|else if) \(Kind = fnm_volt\.(\w+)\):\n\s+set Name = \"(\w+)\"\n\s+VoltCard\.SetImage\(FNM_Art\.T_fnm_volt_(\w+)\)", show)
    assert pairs == [("Thumbs", "thumbs", "thumbs"), ("Fire", "fire", "fire"), ("Wag", "wag", "wag"),
                     ("Shocked", "shocked", "shocked"), ("Think", "think", "think")]
    for mood, name, texture in pairs:
        assert mood.lower() == name == texture          # the enum member, the logged name and the texture agree
    assert "else:\n            VoltCard.SetImage(FNM_Art.T_fnm_volt_go)" in show      # Go is the fall-through
    assert 'var Name : string = "go"' in show
    # every call shows the card and proves itself in the log
    assert "VoltCard.SetVisibility(widget_visibility.Visible)" in show and 'Print("FNM: volt {Name}")' in show


def test_the_six_pngs_come_from_the_six_raws():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import make_medal_art as mm
    jobs = dict(mm.JOBS)
    for kind in KINDS:
        assert jobs[f"art/mascot/reactions/{kind}_raw.png"] == f"fnm_volt_{kind}.png"
        assert (ART / f"fnm_volt_{kind}.png").exists()
    names = [(ART / f"fnm_volt_{k}.png").read_bytes() for k in KINDS] + [(ART / "fnm_volt.png").read_bytes()]
    assert len(set(names)) == 7                           # six distinct moods, none a copy of the finish board's cheer


def test_card_is_one_180px_square_with_the_corrected_tint():
    text = ui()
    line = re.search(r"^    VoltCard : texture_block = texture_block\{(.*)\}$", text, re.M).group(1)
    assert re.search(r"DefaultDesiredSize := vector2\{X := 180\.0, Y := 180\.0\}", line)          # brief: about 170-190 px, square
    assert "DefaultHorizontalTiling := image_tiling.Stretch" in line
    assert "            VoltCard.SetTint(FnmUi(NamedColors.White))" in text          # CLAUDE.md "HUD colours"
    assert "VoltSeconds : float = 1.8" in text
    assert "VoltCard.SetVisibility(widget_visibility.Collapsed)" in code(text.split("    Attach(Player:player):void =", 1)[1].split("    Detach", 1)[0])


def test_newer_card_wins_and_an_old_timer_never_hides_it():
    text = ui()
    show = method_body(text, "ShowVolt(Kind:fnm_volt):void =\n")
    assert show.lstrip().startswith("set VoltGeneration += 1")                 # bumped before anything is drawn
    assert "spawn{ HideVoltLater(VoltGeneration) }" in show                  # the timer carries the generation it started under
    hide_now = method_body(text, "HideVolt():void =\n")
    assert "set VoltGeneration += 1" in hide_now and "widget_visibility.Collapsed" in hide_now
    later = method_body(text, "HideVoltLater(Generation:int)<suspends>:void =\n")
    assert "Sleep(VoltSeconds)" in later
    assert "if (Generation = VoltGeneration):" in later and "widget_visibility.Collapsed" in later.split("if (Generation = VoltGeneration):", 1)[1]


def test_finish_board_hides_the_card():
    results = method_body(ui(), "ShowResults(")
    assert "        HideVolt()\n" in results


def test_hud_api_is_new_methods_only():
    text = ui()
    assert "    ShowVolt(Kind:fnm_volt):void =" in text and "    HideVolt():void =" in text
    # the existing seams the director and boss mode call keep their signatures
    for sig in ("ShowRecap(Prompt:string, Choices:[]string, RightIndex:int, Steps:string, Verdict:string):int =",
                "FlashVerdict(Correct:logic, Label:string):void =", "FlashBig(Text:string, TextColor:color, Seconds:float):void =",
                "ClearVerdictNow():void ="):
        assert "    " + sig in text, sig


# ---------------------------------------------------------------- where the card sits (1920 x 1080)

SCREEN_W, SCREEN_H = 1920.0, 1080.0
LINE = 1.24                                           # line height / font size, calibrated on the 2026-10-13 frames


def num(pattern, text, group=1):
    return float(re.search(pattern, text).group(group))


def slot_after(text, widget_line):
    """The canvas_slot block that starts with `Widget := <widget_line>` (up to its SizeToContent)."""
    return text.split(widget_line, 1)[1].split("SizeToContent", 1)[0]


def anchored_rect(slot, width, height):
    """Rect (x0, y0, x1, y1) of a canvas slot anchored at a point: Anchors X/Y, Alignment X/Y, Offsets Left/Top."""
    ax, ay = (num(r"Anchors := anchors\{Minimum := vector2\{X := ([\d.]+), Y := ([\d.]+)\}", slot, g) for g in (1, 2))
    lx, ly = (num(r"Alignment := vector2\{X := ([\d.]+), Y := ([\d.]+)\}", slot, g) for g in (1, 2))
    offsets = re.search(r"Offsets := margin\{Left := (-?[\d.]+), Top := (-?[\d.]+)", slot)
    left, top = (float(offsets.group(1)), float(offsets.group(2))) if offsets else (0.0, 0.0)      # no Offsets = none
    x = ax * SCREEN_W + left - lx * width
    y = ay * SCREEN_H + top - ly * height
    return (x, y, x + width, y + height)


def overlap(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def hud_rects():
    """Every other thing the HUD draws, worst case, at 1080p, named. Sizes come from the Verse constants where there are any."""
    text = ui()
    k = LINE
    rects = {}
    # the slate: 1180 art + 6 px rim each side, hung from Top 40; ~305 px tall (measured 2026-10-13)
    slate_w = num(r"SlateArt : texture_block = .*?DefaultDesiredSize := vector2\{X := ([\d.]+)", text) + 12
    rects["slate"] = anchored_rect(slot_after(text, "Widget := Slate\n"), slate_w, 305.0)
    # the tag: two short lines, a 32-char title at 24 px
    tag_w = 32 * 0.6 * 24 + 32
    rects["tag"] = anchored_rect(slot_after(text, "Widget := Tag\n"), tag_w, k * (24 + 20) + 14)
    # the left panel: clock, target, delta, RACE head, eight rival rows (24 px), widest row ~30 chars
    left_h = k * (52 + 30 + 30 + 24) + 8 + 8 * k * 24 + 18
    left_slot = text.split("Widget := LeftLines", 1)[1].split("SizeToContent", 1)[0]
    rects["left panel"] = anchored_rect(left_slot, 30 * 0.55 * 24 + 48, left_h)
    # the feed: FeedWrap + 2 x 20 padding wide, three 24 px rows
    rects["feed"] = anchored_rect(slot_after(text, "Widget := Feed\n"), num(r"    FeedWrap : float = ([\d.]+)", text) + 40, 8 + 3 * k * 24 + 10)
    # the boss-mode banner: 900 x 200 centred at (0.5, 0.52)
    rects["banner"] = anchored_rect(slot_after(text, "Widget := Banner\n"), 900.0, 200.0)
    # the verdict stack (check / cross + big label): 240 px image over a 96 px label; ~1250 px wide for the longest verdicts
    # ("DIRECT HIT!  1 TO GO", "STUCK IN MUD!  +3 s"). Anchored (0.5, 0.68), centred.
    tail = text.split("Widget := VerdictImage\n", 1)[1]
    verdict_slot = tail[tail.index("Anchors := "):tail.index("SizeToContent")]
    verdict_h = 240 + k * 96 + 14
    rects["verdict (check + label)"] = anchored_rect(verdict_slot, 1250.0, verdict_h)
    # FlashBig has no image: the label alone, and the arena instruction "STEP ON THE RIGHT ANSWER PAD!" is ~28 glyphs at 96 px
    rects["verdict (label only, arena instruction)"] = anchored_rect(verdict_slot, 28 * 0.6 * 96, k * 96 + 14)
    # the finish board: ResultsWrap + 2 x 40, from Top 130 to the buttons' top (test_finish_board_stays_above_the_finish_buttons)
    board_w = num(r"    ResultsWrap : float = ([\d.]+)", text) + 80
    board_slot = text.split("                        Widget := Results\n", 1)[1].split("SizeToContent", 1)[0]
    rects["finish board"] = anchored_rect(board_slot, board_w, 875 - 130)
    # CLOSE / PLAY AGAIN / NEW SKILL, anchored at (0.5, 0.81) by their top edge (~620 px for three buttons)
    rects["finish buttons"] = (960 - 310, 0.81 * SCREEN_H, 960 + 310, 0.81 * SCREEN_H + 70)
    # the boss bar: centred at x 900, bottom edge 16 px above the screen bottom, ~720 x 100
    rects["boss bar"] = anchored_rect(slot_after(text, "Widget := BossBar\n"), 720.0, 100.0)
    # Fortnite's own HUD: the minimap (from x 1603, to y ~335) and the hotbar (from x 1230, y 930 down)
    rects["Fortnite minimap"] = (1603.0, 0.0, SCREEN_W, 335.0)
    rects["Fortnite hotbar"] = (1230.0, 930.0, SCREEN_W, SCREEN_H)
    rects["Fortnite game mode box"] = (0.0, 0.0, 356.0, 125.0)
    return rects


def card_rect():
    text = ui()
    return anchored_rect(slot_after(text, "Widget := VoltCard\n"), 180.0, 180.0)


def test_card_spot_is_stated_and_inside_the_screen():
    x0, y0, x1, y1 = card_rect()
    assert (x0, y0, x1, y1) == (1720.0, 480.0, 1900.0, 660.0)       # reported to the manager: right edge, under the feed
    assert 0 <= x0 and x1 <= SCREEN_W and 0 <= y0 and y1 <= SCREEN_H


def test_card_overlaps_nothing_the_hud_draws():
    card = card_rect()
    rects = hud_rects()
    assert len(rects) >= 12
    for name, rect in rects.items():
        if name == "finish board":
            # G10 (H): the finish card docks to the right edge and covers this spot, so the two never draw together: ShowResults
            # takes the card off and ShowVolt returns while the board is up (ResultsUp).
            ui_text = ui()
            assert "if (ResultsUp?):\n            return" in ui_text.split("    ShowVolt(Kind:fnm_volt):void =", 1)[1].split("var Name", 1)[0]
            assert "HideVolt()" in ui_text.split("    ShowResults(", 1)[1].split("\n\n", 1)[0]
            continue
        assert not overlap(card, rect, gap=4.0), (name, rect, card)           # the closest is the arena instruction: 7.9 px below


def test_the_overlap_check_can_fail():
    """Disproof of the check itself: a card dropped onto the feed's spot, or onto the verdict, must be reported."""
    rects = hud_rects()
    on_feed = (1720.0, 380.0, 1900.0, 560.0)
    assert any(overlap(on_feed, r) for r in rects.values())
    assert overlap(on_feed, rects["feed"], gap=8.0)
    on_verdict = (900.0, 600.0, 1080.0, 780.0)
    assert overlap(on_verdict, rects["verdict (check + label)"], gap=8.0)


def test_card_sits_after_the_feed_slot_in_the_root_canvas():
    text = ui()
    assert text.index("Widget := Feed\n") < text.index("Widget := VoltCard\n") < text.index("Widget := BossBar\n")


# ---------------------------------------------------------------- who shows which card, and when

def count(text, needle):
    return code(text).count(needle)


def test_director_call_sites():
    d = src("fnm_director")
    door = method_body(d, "HandleDoor(State:fnm_player_state, StationIndex:int, DoorIndex:int)<suspends>:void =\n")
    right, wrong = door.split("            else:\n                set State.MissedCurrent = true", 1)
    # right door: after the verdict, fire when the answer made a streak of 3+ (a right-after-miss leaves the streak at 0: thumbs)
    assert "State.Hud.FlashVerdict(true, Label)\n                # Volt's card" in right
    assert "State.Hud.ShowVolt(if (State.Streak >= 3) then fnm_volt.Fire else fnm_volt.Thumbs)" in right
    assert right.index("set State.Streak += 1") < right.index("ShowVolt(")                    # the streak is already counted
    # wrong door: the moment it is judged, right after the verdict
    assert "State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind) + Tail)\n                State.Hud.ShowVolt(fnm_volt.Wag)\n" in wrong
    # wrong pad in the race arena, the same
    pad = method_body(d, "HandlePad(State:fnm_player_state, A:fnm_arena, DoorIndex:int)<suspends>:void =\n")
    assert "State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind) + Tail)\n                State.Hud.ShowVolt(fnm_volt.Wag)\n" in pad
    # run start, on the GO
    assert 'State.Hud.FlashBig("GO!", NamedColors.Lime, 1.0)\n        State.Hud.ShowVolt(fnm_volt.Go)\n' in d
    # race finale: a hit that leaves the titan standing; the killing hit (Left = 0) shows nothing (the board follows)
    hit = method_body(d, "BossHit(State:fnm_player_state, A:fnm_arena):void =\n")
    assert "        if (Left > 0):\n            State.Hud.ShowVolt(fnm_volt.Thumbs)\n" in hit
    assert hit.index('"DIRECT HIT!') < hit.index("ShowVolt(")
    # the penalty landing and the retry spot
    punish = method_body(d, "Punish(Player:player, Station:fnm_station, DoorIndex:int, Kind:fnm_penalty)<suspends>:void =\n")
    assert "spawn{ VoltLater(Player, fnm_volt.Shocked, PenaltyVoiceDelaySeconds) }" in punish
    retry = punish.split("        if (Wide?, Viewer := PlayerStates[Player]):\n", 1)[1]
    assert retry.index("Viewer.Hud.ShowVolt(fnm_volt.Think)") < retry.index("Sound(Player, fnm_cue.VoltHmm)") < retry.index("WideLook(")
    # each kind's total: go 1, fire 1, thumbs 2 (right door, finale), wag 2 (door, pad), shocked 1, think 1 in the director
    for kind, n in (("Go", 1), ("Fire", 1), ("Thumbs", 2), ("Wag", 2), ("Shocked", 1), ("Think", 1)):
        assert count(d, f"fnm_volt.{kind}") == n, kind


def test_voltlater_is_ui_only_and_drops_when_the_player_has_moved_on():
    d = src("fnm_director")
    later = method_body(d, "VoltLater(Player:player, Kind:fnm_volt, Seconds:float)<suspends>:void =\n")
    assert "Sleep(Seconds)" in later
    assert "if (State := PlayerStates[Player], not State.Finished?, not State.Picking?):\n            State.Hud.ShowVolt(Kind)" in later
    assert later.strip().splitlines()[-1].strip() == "State.Hud.ShowVolt(Kind)"            # nothing else happens in it


def test_boss_mode_call_sites():
    b = src("fnm_bossmode")
    hit = method_body(b, "Hit(State:fnm_player_state):void =\n")
    assert "State.Hud.ShowVolt(fnm_volt.Thumbs)" in hit
    assert hit.index("ShowVolt(") < hit.index("L := Level")                     # both branches (boss up or not) get the card
    wrong = method_body(b, "Wrong(State:fnm_player_state, Item:fnm_item, Choice:int, DoorIndex:int)<suspends>:void =\n")
    assert "State.Hud.FlashVerdict(false, FnmPenaltyLabel(Kind))\n        State.Hud.ShowVolt(fnm_volt.Wag)\n" in wrong
    assert count(b, "ShowVolt(") == 2


def test_the_card_is_a_picture_only_nothing_else_in_the_director_depends_on_it():
    """ShowVolt returns void and is only ever called as a statement: no `:=` capture, no condition on it."""
    for name in ("fnm_director", "fnm_bossmode"):
        for line in code(src(name)).splitlines():
            if "ShowVolt(" in line:
                assert line.strip().startswith(("State.Hud.ShowVolt(", "Viewer.Hud.ShowVolt(")), line
                assert ":=" not in line.split("ShowVolt(", 1)[0]


# ---------------------------------------------------------------- the two cue ids

MORE = ("VoltYay", "VoltHmm")


def test_new_cue_ids_are_appended_in_the_same_order_everywhere():
    a = src("fnm_audio")
    body = a.split("fnm_cue := enum:\n", 1)[1].split("\n\n", 1)[0]
    members = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]
    k = members.index("BmWeapon")                     # (G9 D2 appended six more after them: tests/test_audio_cues.py MEMBERS)
    assert members[k:k + 3] == ["BmWeapon", "VoltYay", "VoltHmm"]
    cues = re.findall(r"fnm_cue\.(\w+)", re.search(r"FnmCues\(\)<transacts>:\[\]fnm_cue = array\{(.*)\}", a).group(1))
    ids = re.findall(r'"([a-z0-9_]+)"', re.search(r"FnmCueIds\(\)<transacts>:\[\]string = array\{(.*)\}", a).group(1))
    assert cues == members and len(ids) == len(members)
    assert ids[k + 1:k + 3] == ["volt_yay", "volt_hmm"]


def test_volt_hmm_plays_at_the_retry_spot_only_and_volt_yay_nowhere():
    allcode = "\n".join(code(src(n)) for n in ("fnm_director", "fnm_bossmode", "fnm_ui"))
    assert allcode.count("fnm_cue.VoltHmm") == 1
    assert "Sound(Player, fnm_cue.VoltHmm)" in allcode
    assert "fnm_cue.VoltYay" not in allcode.replace("fnm_cue.VoltYay,", "")        # only FnmCues()'s table names it (in fnm_audio)
