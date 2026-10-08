# FNM console runtime -- per-player HUD (Verse UI: canvas + stack_box + text_blocks + texture_blocks).
# One fnm_hud instance per player; only that player sees it. The question sits on "the slate", top centre: a framed
# dark chalk slate (texture FNM_Art.T_fnm_slate inside a pale color_block rim) hung like a sign above the door wall,
# with the stage caption, the prompt, and the answers as four tiles laid out left to right like the doors, each in its
# door's colour (FnmDoorColors; texture FNM_Art.T_fnm_tile tinted per door). The skill's title and subtitle are a small
# tag top left under Fortnite's GAME MODE box. Every player draws their own item and letter shuffle, and UEFN has no
# per-player world text, so the slate is HUD, not a world sign (Aaron 2026-10-08: the flat black panel "feels like
# alpha version"). The skill picker and the finish board's CHANGE SKILL
# and CLOSE buttons are real Verse buttons on their own roots (InputMode All only while shown); clicks go to the director
# through fnm_picker_listener (PROTOCOL 6b). With a podium on the map the finish board shows WITHOUT those buttons, so
# it never takes the player's movement (Aaron 2026-10-06).

using { /Fortnite.com/UI }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/UI }
using { /Verse.org/Colors }
using { /Verse.org/Simulation }

# string -> message (SetText / DefaultText take a `message`, not a `string`).
FnmText<localizes>(Value:string):message = "{Value}"
# Finish-board lines with a player's name: a localized message shows an interpolated agent as its display name.
FnmRow<localizes>(Rank:int, Who:agent, Time:string):message = "{Rank}.  {Who}   {Time}"
FnmHolder<localizes>(Time:string, Who:agent, Tail:string):message = "Island record   {Time}  by {Who}{Tail}"
# Rivals strip row (the viewer's own row is plain text, "YOU  station 4").
FnmRivalRow<localizes>(Who:agent, Tail:string):message = "{Who}  {Tail}"
# Public feed lines (fnm_director Broadcast), shown to every player.
FnmFeedPenalty<localizes>(Who:agent, Past:string, Station:int):message = "{Who} got {Past} at station {Station}"
FnmFeedFinish<localizes>(Who:agent, Time:string, Medal:string):message = "{Who} finished in {Time}  ({Medal})"
FnmFeedRecord<localizes>(Who:agent, Time:string):message = "{Who} set the island record  {Time}"
FnmFeedStreak<localizes>(Who:agent, Streak:int):message = "{Who} is on a {Streak} streak!"
FnmFeedSkip<localizes>(Who:agent):message = "{Who} tried to skip and was sent back"
FnmFeedBoss<localizes>(Who:agent):message = "{Who} reached the boss!"
FnmFeedBossPenalty<localizes>(Who:agent, Past:string):message = "{Who} got {Past} by the boss"
FnmFeedFinalHit<localizes>(Who:agent):message = "{Who} landed the final hit!"

# The four door colours, A..D: the letter boards over the doors and the arena pads use the same ones. Must equal
# tools/build_course.py LETTER_COLOURS (tests/test_hud_layout.py pins it).
FnmDoorColors : []color = array:
    color{R := 1.0, G := 1.0, B := 1.0}
    color{R := 0.3, G := 0.55, B := 1.0}
    color{R := 0.2, G := 0.9, B := 0.3}
    color{R := 1.0, G := 0.55, B := 0.1}

# What a picker / finish-board button reports (PROTOCOL 6b): a grade (Index = position in the director's grade
# list), a skill (Index = cartridge index in the slot), Back to the grade step, or CHANGE SKILL / CLOSE on the finish
# board.
fnm_pick := enum:
    Grade
    Skill
    Back
    ChangeSkill
    Close

# Who hears the HUD's button clicks (the director). The HUD only reports; the listener decides what shows next.
fnm_picker_listener := interface:
    OnPickerChoice(Player:player, Kind:fnm_pick, Index:int):void

# Binds one button to what it means, so a single callback signature serves every button (like fnm_door_handler).
fnm_pick_handler := class:
    Hud : fnm_hud
    Kind : fnm_pick
    Index : int

    OnClick(Message:widget_message):void =
        Hud.Clicked(Message.Player, Kind, Index)

fnm_hud := class:
    # Width (px at 1080p) at which the slate's long lines wrap: the slate's 1192 less its side padding. Explanations
    # are up to 160 chars (PROTOCOL 5 rule 6), two lines at this width.
    WrapAt : float = 1120.0

    # The tag, top left: the skill's title and subtitle, one line each (title <= 32 chars, subtitle <= 40; PROTOCOL 5
    # rule 6). Out of the slate so the question is the first thing on it.
    TitleText : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
    SubtitleText : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 20.0, DefaultJustification := text_justification.Left}
    # The slate's caption row ("Stage 1/10  -  Rectangles"), top left of the slate, then the prompt.
    StageText : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 22.0, DefaultJustification := text_justification.Left}
    PromptText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 46.0, DefaultJustification := text_justification.Center}
    # The slate's chalk texture (stretched; the 6 px rim round it is a color_block, so the frame stays crisp). 1180
    # wide (1192 with the rim, x 364-1556 at 1080p) clears Fortnite's GAME MODE box (ends x 356) and the minimap (from
    # x 1603); the slate's height is kept so its bottom stays above the door lintel (y ~330) and the letter boards on it.
    SlateArt : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_slate, DefaultDesiredSize := vector2{X := 1180.0, Y := 210.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    # The answer tiles, A..D left to right like the doors. The four doors are the same prop: only the letter boards'
    # colours tell them apart, so each tile's ring, letter and value take its door's colour (FnmDoorColors, set in
    # Attach). Tiles past the item's choice count are collapsed.
    TileArt : []texture_block = array:
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 240.0, Y := 100.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 240.0, Y := 100.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 240.0, Y := 100.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 240.0, Y := 100.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    TileLetter : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 20.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 20.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 20.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 20.0, DefaultJustification := text_justification.Center}
    TileValue : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    FeedbackText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 28.0, DefaultJustification := text_justification.Center}
    # Streak and speed boost, big, at the bottom of the slate (Aaron 2026-10-04: the small left line went unnoticed).
    StreakBig : text_block = text_block{DefaultTextColor := NamedColors.Orange, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
    # Boss arena: the shared boss health bar and the viewer's own hits, the last line of the slate, shown only to a
    # player at the arena stage (fnm_director BossLoop refreshes it; collapsed otherwise, so nothing else moves).
    BossText : text_block = text_block{DefaultTextColor := NamedColors.Red, DefaultTextSize := 36.0, DefaultJustification := text_justification.Center}
    # Verdict: a big check mark or cross (textures; the HUD font has no such glyphs) over CORRECT! or the
    # penalty's name. FNM_Art.T_fnm_check / T_fnm_cross are imported into each map's project by
    # tools/import_art.py.
    VerdictImage : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_check, DefaultDesiredSize := vector2{X := 240.0, Y := 240.0}}
    VerdictLabel : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 96.0, DefaultJustification := text_justification.Center}
    # Race clock and the run's target time ("Beat 1:20.1"), left side.
    ClockText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 52.0, DefaultJustification := text_justification.Left}
    TargetText : text_block = text_block{DefaultTextColor := NamedColors.Orange, DefaultTextSize := 30.0, DefaultJustification := text_justification.Left}
    # Pace delta under the target at each right answer ("-1.8 s" ahead, "+3.2 s" behind, a real minus sign;
    # collapsed with no pace target).
    DeltaText : text_block = text_block{DefaultTextColor := NamedColors.LightGreen, DefaultTextSize := 30.0, DefaultJustification := text_justification.Left}
    # Rivals strip, under the delta in the same left panel: a RACE heading and one row per player (fnm_director
    # RaceLoop, sorted by progress), the viewer's own row gold. Unused rows are collapsed; all of it while picking.
    RivalsHead : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
    RivalRows : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
    # Public feed, top right under the minimap: up to 3 lines, newest on top, each gone after FeedSeconds.
    FeedRows : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 26.0, DefaultJustification := text_justification.Right}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 26.0, DefaultJustification := text_justification.Right}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 26.0, DefaultJustification := text_justification.Right}
    FeedSeconds : float = 7.0
    # Finish board (centre screen, hidden until a finish): headline, medal, this run, personal best, island record,
    # accuracy, the session's top times (one row per player) and the next-run countdown.
    ResultsTitle : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 72.0, DefaultJustification := text_justification.Center}
    ResultsMedal : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 52.0, DefaultJustification := text_justification.Center}
    ResultsTime : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 44.0, DefaultJustification := text_justification.Center}
    ResultsBest : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 36.0, DefaultJustification := text_justification.Center}
    ResultsRecord : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 36.0, DefaultJustification := text_justification.Center}
    ResultsAccuracy : text_block = text_block{DefaultTextColor := NamedColors.LightGreen, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    ResultsBoardHead : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    # Room for 5 top-time rows (the director's BoardSize); unused ones are collapsed.
    ResultsRows : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
    ResultsCountdown : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    # Full-screen black for the Blackout penalty (the post-process "Dark" effect only tinted the view).
    BlackScreen : color_block = color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.0}
    # Seconds the verdict stays up.
    VerdictSeconds : float = 1.5
    # Skill picker (PROTOCOL 6b), centre screen on its own root: heading, step line, one button per grade or skill.
    PickerHeading : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 60.0, DefaultJustification := text_justification.Center}
    PickerStep : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    PickerButtons : stack_box = stack_box{Orientation := orientation.Vertical, Slots := array{}}
    # A step with more buttons than this shows them in two columns.
    PickerColumnAfter : int = 5
    # Under the finish board, on their own root, shown with the board: CLOSE (the board stays until the player closes
    # it; Aaron 2026-10-05: "x it and enjoy themself in the victory area") and CHANGE SKILL (more than one skill only).
    # (Their text is set in Attach: a localized call can't initialise a field.)
    CloseButton : button_loud = button_loud{}
    ChangeSkillButton : button_regular = button_regular{}

    var MaybePlayerUI : ?player_ui = false
    var MaybeRoot : ?canvas = false
    var MaybeResults : ?widget = false
    # The whole slate (collapsed by ClearQuestion, reopened by ShowQuestion) and the four tile overlays, A..D.
    var MaybeSlate : ?widget = false
    var TileBoxes : []overlay = array{}
    var MaybeOwner : ?player = false
    var MaybeListener : ?fnm_picker_listener = false
    # The picker's and the CHANGE SKILL button's roots. Each is added (InputMode All: the mouse cursor and clicks go
    # to the buttons, the player can't move) only while shown and removed when hidden, so movement comes back.
    var MaybePickerRoot : ?canvas = false
    var MaybeChangeRoot : ?canvas = false
    var PickerShown : logic = false
    var ChangeShown : logic = false
    # The buttons on the picker's current step (removed from PickerButtons when the step changes).
    var PickerButtonList : []widget = array{}
    # Bumped on every feedback message so an older timer never clears a newer message.
    var FeedbackGeneration : int = 0
    var VerdictGeneration : int = 0
    # The feed's lines, newest first, and the id of the push behind each (a fader removes only its own line).
    var MaybeFeed : ?widget = false
    var FeedLines : []message = array{}
    var FeedIds : []int = array{}
    var FeedSerial : int = 0

    # Builds the widget tree and adds it to Player's screen. Safe to call once per player.
    Attach(Player:player):void =
        if (PlayerUI := GetPlayerUI[Player]):
            set PromptText.WrapWidth = WrapAt
            set FeedbackText.WrapWidth = WrapAt
            # The answer tiles: the tile texture tinted with the door's colour (its white ring takes the colour, the
            # dark interior stays near-black) under the door letter and the choice, both in the door's colour.
            Tiles : stack_box = stack_box{Orientation := orientation.Horizontal, Slots := array{}}
            for (K -> Art : TileArt, DoorColor := FnmDoorColors[K], Letter := TileLetter[K], Value := TileValue[K]):
                Art.SetTint(DoorColor)
                Letter.SetTextColor(DoorColor)
                Value.SetTextColor(DoorColor)
                Letter.SetText(FnmText(FnmChoiceLetter(K)))
                Box : overlay = overlay:
                    Slots := array:
                        overlay_slot:
                            Widget := Art
                            HorizontalAlignment := horizontal_alignment.Fill
                            VerticalAlignment := vertical_alignment.Fill
                        overlay_slot:
                            Widget := stack_box:
                                Orientation := orientation.Vertical
                                Slots := array:
                                    stack_box_slot:
                                        Widget := Letter
                                        HorizontalAlignment := horizontal_alignment.Center
                                    stack_box_slot:
                                        Widget := Value
                                        HorizontalAlignment := horizontal_alignment.Center
                                        Padding := margin{Top := 2.0}
                            HorizontalAlignment := horizontal_alignment.Center
                            VerticalAlignment := vertical_alignment.Center
                Tiles.AddWidget(stack_box_slot{Widget := Box, Padding := margin{Left := 8.0, Right := 8.0}})
                set TileBoxes += array{Box}
            Lines : stack_box = stack_box:
                Orientation := orientation.Vertical
                Slots := array:
                    stack_box_slot:
                        Widget := StageText
                        HorizontalAlignment := horizontal_alignment.Left
                    stack_box_slot:
                        Widget := PromptText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 4.0}
                    stack_box_slot:
                        Widget := Tiles
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 12.0}
                    stack_box_slot:
                        Widget := FeedbackText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 12.0}
                    stack_box_slot:
                        Widget := StreakBig
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 10.0}
                    stack_box_slot:
                        Widget := BossText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 8.0}
            # The slate: a pale rim (the frame), the dark chalk texture inset 6 px inside it, the lines on top. Dark and
            # neutral because the hallway walls are tier-coloured (green, blue, purple, orange, red), and the pale walls
            # and sky washed out coloured text on no backing at all.
            Slate : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := color{R := 0.86, G := 0.82, B := 0.74}, DefaultOpacity := 0.95}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := SlateArt
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                        Padding := margin{Left := 6.0, Top := 6.0, Right := 6.0, Bottom := 6.0}
                    overlay_slot:
                        Widget := Lines
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Left := 30.0, Top := 14.0, Right := 30.0, Bottom := 16.0}
            # The tag: the skill's title and subtitle on a small dark backing.
            Tag : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.55}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := stack_box:
                            Orientation := orientation.Vertical
                            Slots := array:
                                stack_box_slot:
                                    Widget := TitleText
                                    HorizontalAlignment := horizontal_alignment.Left
                                stack_box_slot:
                                    Widget := SubtitleText
                                    HorizontalAlignment := horizontal_alignment.Left
                        Padding := margin{Left := 16.0, Top := 6.0, Right := 16.0, Bottom := 8.0}
            ResultsLines : stack_box = stack_box:
                Orientation := orientation.Vertical
                Slots := array:
                    stack_box_slot:
                        Widget := ResultsTitle
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := ResultsMedal
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := ResultsTime
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := ResultsBest
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := ResultsRecord
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := ResultsAccuracy
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := ResultsBoardHead
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 18.0}
            for (Row : ResultsRows):
                ResultsLines.AddWidget(stack_box_slot{Widget := Row, HorizontalAlignment := horizontal_alignment.Center})
            ResultsLines.AddWidget(stack_box_slot{Widget := ResultsCountdown, HorizontalAlignment := horizontal_alignment.Center, Padding := margin{Top := 18.0}})
            Results : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.62}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := ResultsLines
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Left := 40.0, Top := 28.0, Right := 40.0, Bottom := 28.0}
            # Left panel: clock, target, pace delta, then the rivals strip.
            RivalsHead.SetText(FnmText("RACE"))
            LeftLines : stack_box = stack_box:
                Orientation := orientation.Vertical
                Slots := array:
                    stack_box_slot:
                        Widget := ClockText
                        HorizontalAlignment := horizontal_alignment.Left
                    stack_box_slot:
                        Widget := TargetText
                        HorizontalAlignment := horizontal_alignment.Left
                    stack_box_slot:
                        Widget := DeltaText
                        HorizontalAlignment := horizontal_alignment.Left
                    stack_box_slot:
                        Widget := RivalsHead
                        HorizontalAlignment := horizontal_alignment.Left
                        Padding := margin{Top := 8.0}
            for (Row : RivalRows):
                LeftLines.AddWidget(stack_box_slot{Widget := Row, HorizontalAlignment := horizontal_alignment.Left})
            FeedLinesBox : stack_box = stack_box{Orientation := orientation.Vertical, Slots := array{}}
            for (Row : FeedRows):
                FeedLinesBox.AddWidget(stack_box_slot{Widget := Row, HorizontalAlignment := horizontal_alignment.Right})
            Feed : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.55}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := FeedLinesBox
                        HorizontalAlignment := horizontal_alignment.Right
                        Padding := margin{Left := 20.0, Top := 8.0, Right := 20.0, Bottom := 10.0}
            Root : canvas = canvas:
                Slots := array:
                    canvas_slot:
                        Widget := BlackScreen
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 1.0, Y := 1.0}}
                        Offsets := margin{Left := 0.0, Top := 0.0, Right := 0.0, Bottom := 0.0}
                    # The slate, top centre, hung above the door wall (Top 40: lower and it covered the letter boards).
                    canvas_slot:
                        Widget := Slate
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.0}, Maximum := vector2{X := 0.5, Y := 0.0}}
                        Alignment := vector2{X := 0.5, Y := 0.0}
                        Offsets := margin{Left := 0.0, Top := 40.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
                    # The tag, under Fortnite's GAME MODE box (ends near y 125) and above the clock panel (Top 230).
                    canvas_slot:
                        Widget := Tag
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 0.0, Y := 0.0}}
                        Alignment := vector2{X := 0.0, Y := 0.0}
                        Offsets := margin{Left := 20.0, Top := 138.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
                    # The finish board, hung from the top (ClearQuestion collapses the slate, so nothing sits behind it)
                    # so a finisher walking on into the victory area still sees where they are going (Aaron 2026-10-06: a
                    # centred board hid it). Before the verdict slot so GO! / a check draw on top.
                    canvas_slot:
                        Widget := Results
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.0}, Maximum := vector2{X := 0.5, Y := 0.0}}
                        Alignment := vector2{X := 0.5, Y := 0.0}
                        Offsets := margin{Left := 0.0, Top := 130.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
                    canvas_slot:
                        Widget := stack_box:
                            Orientation := orientation.Vertical
                            Slots := array:
                                stack_box_slot:
                                    Widget := VerdictImage
                                    HorizontalAlignment := horizontal_alignment.Center
                                stack_box_slot:
                                    Widget := VerdictLabel
                                    HorizontalAlignment := horizontal_alignment.Center
                        # Lower third: under the penalty camera the player stands mid-screen, and a centred X
                        # hid the spears (Aaron, 2026-10-03).
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.68}, Maximum := vector2{X := 0.5, Y := 0.68}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                    canvas_slot:
                        Widget := overlay:
                            Slots := array:
                                overlay_slot:
                                    Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.55}
                                    HorizontalAlignment := horizontal_alignment.Fill
                                    VerticalAlignment := vertical_alignment.Fill
                                overlay_slot:
                                    Widget := LeftLines
                                    Padding := margin{Left := 24.0, Top := 8.0, Right := 24.0, Bottom := 10.0}
                        # Left, under Fortnite's GAME MODE box: top right is the minimap's (it hid the clock).
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 0.0, Y := 0.0}}
                        Alignment := vector2{X := 0.0, Y := 0.0}
                        Offsets := margin{Left := 20.0, Top := 230.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
                    # The public feed, top right under Fortnite's minimap and its player-count icons (seen clipping them at
                    # Top 300 on 2026-10-07; a point anchor: Left -20 = 20 px in from the right edge). Not part of the finish board.
                    canvas_slot:
                        Widget := Feed
                        Anchors := anchors{Minimum := vector2{X := 1.0, Y := 0.0}, Maximum := vector2{X := 1.0, Y := 0.0}}
                        Alignment := vector2{X := 1.0, Y := 0.0}
                        Offsets := margin{Left := -20.0, Top := 348.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
            VerdictImage.SetVisibility(widget_visibility.Collapsed)
            Results.SetVisibility(widget_visibility.Collapsed)
            StreakBig.SetVisibility(widget_visibility.Collapsed)
            BossText.SetVisibility(widget_visibility.Collapsed)
            TargetText.SetVisibility(widget_visibility.Collapsed)
            DeltaText.SetVisibility(widget_visibility.Collapsed)
            SubtitleText.SetVisibility(widget_visibility.Collapsed)
            # No question yet: the slate opens with the first ShowQuestion.
            Slate.SetVisibility(widget_visibility.Collapsed)
            set MaybeSlate = option{Slate}
            set MaybeResults = option{Results}
            set MaybeFeed = option{Feed}
            SetRivals(array{}, -1)
            DrawFeed()
            PlayerUI.AddWidget(Root, player_ui_slot{InputMode := ui_input_mode.None})
            set MaybePlayerUI = option{PlayerUI}
            set MaybeRoot = option{Root}
            set MaybeOwner = option{Player}
            # The skill picker: like the finish board, centre screen on a darker panel. Built once, added on demand.
            PickerHeading.SetText(FnmText("CHOOSE YOUR SKILL"))
            PickerPanel : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.78}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := stack_box:
                            Orientation := orientation.Vertical
                            Slots := array:
                                stack_box_slot:
                                    Widget := PickerHeading
                                    HorizontalAlignment := horizontal_alignment.Center
                                stack_box_slot:
                                    Widget := PickerStep
                                    HorizontalAlignment := horizontal_alignment.Center
                                    Padding := margin{Top := 6.0}
                                stack_box_slot:
                                    Widget := PickerButtons
                                    HorizontalAlignment := horizontal_alignment.Fill
                                    Padding := margin{Top := 14.0}
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Left := 48.0, Top := 28.0, Right := 48.0, Bottom := 32.0}
            set MaybePickerRoot = option:
                canvas:
                    Slots := array:
                        canvas_slot:
                            Widget := PickerPanel
                            Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.45}, Maximum := vector2{X := 0.5, Y := 0.45}}
                            Alignment := vector2{X := 0.5, Y := 0.5}
                            SizeToContent := true
            # CLOSE and CHANGE SKILL, just under the finish board (anchored by their top edge).
            CloseButton.SetText(FnmText("CLOSE"))
            CloseButton.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.Close, Index := 0}.OnClick)
            ChangeSkillButton.SetText(FnmText("CHANGE SKILL"))
            ChangeSkillButton.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.ChangeSkill, Index := 0}.OnClick)
            set MaybeChangeRoot = option:
                canvas:
                    Slots := array:
                        canvas_slot:
                            Widget := stack_box:
                                Orientation := orientation.Horizontal
                                Slots := array:
                                    stack_box_slot{Widget := CloseButton, Padding := margin{Right := 16.0}}
                                    stack_box_slot{Widget := ChangeSkillButton, Padding := margin{Left := 16.0}}
                            Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.81}, Maximum := vector2{X := 0.5, Y := 0.81}}
                            Alignment := vector2{X := 0.5, Y := 0.0}
                            SizeToContent := true

    # Removes the HUD (used when the player leaves; harmless if already gone).
    Detach():void =
        HidePicker()
        HideFinishButtons()
        if (PlayerUI := MaybePlayerUI?, Root := MaybeRoot?):
            PlayerUI.RemoveWidget(Root)
        set MaybePlayerUI = false
        set MaybeRoot = false

    # The tag: Title on its line, Subtitle under it ("" collapses the subtitle line).
    SetTitle(Title:string, Subtitle:string):void =
        TitleText.SetText(FnmText(Title))
        SetOrCollapse(SubtitleText, Subtitle)

    # Opens the slate on one question: the caption ("Stage s/S - <tier name>"), the prompt, and Choices[K] on tile K
    # (in the order shown, so tile K is door K); tiles with no choice collapse. Clears feedback.
    ShowQuestion(StageLine:string, Prompt:string, Choices:[]string):void =
        if (Slate := MaybeSlate?):
            Slate.SetVisibility(widget_visibility.Visible)
        StageText.SetText(FnmText(StageLine))
        PromptText.SetText(FnmText(Prompt))
        for (K -> Box : TileBoxes):
            if (Value := TileValue[K], Choice := Choices[K]):
                Value.SetText(FnmText(Choice))
                Box.SetVisibility(widget_visibility.Visible)
            else:
                Box.SetVisibility(widget_visibility.Collapsed)
        ClearFeedbackNow()

    # Shows Message in TextColor; returns the generation number to pass to ClearFeedbackIf.
    ShowFeedback(Message:string, TextColor:color):int =
        set FeedbackGeneration += 1
        FeedbackText.SetVisibility(widget_visibility.Visible)
        FeedbackText.SetTextColor(TextColor)
        FeedbackText.SetText(FnmText(Message))
        FeedbackGeneration

    # Clears the feedback line only if nothing newer was shown since generation Generation.
    ClearFeedbackIf(Generation:int):void =
        if (Generation = FeedbackGeneration):
            ClearFeedbackNow()

    # Empties the feedback line and collapses it, so an idle slate is a line shorter (ShowFeedback reopens it).
    ClearFeedbackNow():void =
        set FeedbackGeneration += 1
        SetOrCollapse(FeedbackText, "")

    # Takes the verdict (check / cross / big text) off the screen now.
    ClearVerdictNow():void =
        set VerdictGeneration += 1
        VerdictImage.SetVisibility(widget_visibility.Collapsed)
        VerdictLabel.SetText(FnmText(""))

    # Flashes a green check over CORRECT! (or Label, if given) or a red cross over Label, for VerdictSeconds.
    FlashVerdict(Correct:logic, Label:string):void =
        set VerdictGeneration += 1
        Color := if (Correct?) then NamedColors.Lime else NamedColors.Red
        VerdictLabel.SetTextColor(Color)
        if (Correct?) then VerdictImage.SetImage(FNM_Art.T_fnm_check) else VerdictImage.SetImage(FNM_Art.T_fnm_cross)
        VerdictImage.SetVisibility(widget_visibility.Visible)
        VerdictLabel.SetText(FnmText(if (Correct?, Label = "") then "CORRECT!" else Label))
        spawn{ ClearVerdictLater(VerdictGeneration, VerdictSeconds) }

    ClearVerdictLater(Generation:int, Seconds:float)<suspends>:void =
        Sleep(Seconds)
        if (Generation = VerdictGeneration):
            VerdictImage.SetVisibility(widget_visibility.Collapsed)
            VerdictLabel.SetText(FnmText(""))

    # Big text in the verdict spot with no image (countdown, FINISH!), for Seconds (0 = until replaced).
    FlashBig(Text:string, TextColor:color, Seconds:float):void =
        set VerdictGeneration += 1
        VerdictImage.SetVisibility(widget_visibility.Collapsed)
        VerdictLabel.SetTextColor(TextColor)
        VerdictLabel.SetText(FnmText(Text))
        if (Seconds > 0.0):
            spawn{ ClearVerdictLater(VerdictGeneration, Seconds) }

    SetClock(Text:string):void =
        ClockText.SetText(FnmText(Text))

    # The big streak / speed-boost line on the slate ("" collapses it, so the slate doesn't grow).
    SetStreak(Text:string):void =
        SetOrCollapse(StreakBig, Text)

    # The boss line ("BOSS  ...  80%   -   your hits 1/5"); ClearBoss collapses it.
    SetBoss(Text:string):void =
        SetOrCollapse(BossText, Text)

    ClearBoss():void =
        SetOrCollapse(BossText, "")

    # The run's target under the clock ("Beat 1:20.1"; "" collapses it).
    SetTarget(Text:string):void =
        SetOrCollapse(TargetText, Text)

    # The pace delta under the target, in TextColor (green ahead, red behind); ClearDelta collapses it.
    SetDelta(Text:string, TextColor:color):void =
        DeltaText.SetTextColor(TextColor)
        SetOrCollapse(DeltaText, Text)

    ClearDelta():void =
        SetOrCollapse(DeltaText, "")

    # The rivals strip: Rows top to bottom (at most RivalRows.Length; the rest collapse), OwnRow = the viewer's row
    # (-1 none), drawn gold. No rows hides the strip, heading included.
    SetRivals(Rows:[]message, OwnRow:int):void =
        for (K -> Block : RivalRows):
            if (Row := Rows[K]):
                Block.SetText(Row)
                Block.SetTextColor(if (K = OwnRow) then NamedColors.Gold else NamedColors.White)
                Block.SetVisibility(widget_visibility.Visible)
            else:
                Block.SetText(FnmText(""))
                Block.SetVisibility(widget_visibility.Collapsed)
        RivalsHead.SetVisibility(if (Rows.Length > 0) then widget_visibility.Visible else widget_visibility.Collapsed)

    # A public feed line on top of the feed (the oldest drops past FeedRows.Length); it goes after FeedSeconds. Each
    # push has its own id, so a fader only ever removes its own line, never a newer one.
    PushFeed(Line:message):void =
        set FeedSerial += 1
        Id := FeedSerial
        Lines := array{Line} + FeedLines
        Ids := array{Id} + FeedIds
        set FeedLines = for (K -> Each : Lines, K < FeedRows.Length) { Each }
        set FeedIds = for (K -> Each : Ids, K < FeedRows.Length) { Each }
        DrawFeed()
        spawn{ FadeFeed(Id) }

    FadeFeed(Id:int)<suspends>:void =
        Sleep(FeedSeconds)
        var Lines : []message = array{}
        var Ids : []int = array{}
        for (K -> Each : FeedIds, Each <> Id, Line := FeedLines[K]):
            set Lines += array{Line}
            set Ids += array{Each}
        set FeedLines = Lines
        set FeedIds = Ids
        DrawFeed()

    # Feed lines into their blocks; the panel collapses when the feed is empty.
    DrawFeed():void =
        for (K -> Block : FeedRows):
            if (Line := FeedLines[K]):
                Block.SetText(Line)
                Block.SetVisibility(widget_visibility.Visible)
            else:
                Block.SetText(FnmText(""))
                Block.SetVisibility(widget_visibility.Collapsed)
        if (Feed := MaybeFeed?):
            Feed.SetVisibility(if (FeedLines.Length > 0) then widget_visibility.Visible else widget_visibility.Collapsed)

    SetOrCollapse(Block:text_block, Text:string):void =
        Block.SetText(FnmText(Text))
        if (Text = "") then Block.SetVisibility(widget_visibility.Collapsed) else Block.SetVisibility(widget_visibility.Visible)

    # Screen to black (On) or back. The HUD text and the verdict stay on top of it.
    SetBlack(On:logic):void =
        if (On?) then BlackScreen.SetOpacity(1.0) else BlackScreen.SetOpacity(0.0)

    # Empties the slate (caption, prompt, tiles, feedback) and collapses the whole slate, so nothing sits behind the
    # finish board or the picker. The tag stays. ShowQuestion reopens it.
    ClearQuestion():void =
        StageText.SetText(FnmText(""))
        PromptText.SetText(FnmText(""))
        for (Value : TileValue):
            Value.SetText(FnmText(""))
        ClearFeedbackNow()
        if (Slate := MaybeSlate?):
            Slate.SetVisibility(widget_visibility.Collapsed)

    # The finish board. Medal "" leaves its row blank. Rows: the session's top times, best first; OwnRow is the
    # viewing player's row (-1 = not on the board), drawn orange. The countdown row starts empty (SetCountdown).
    # BoardHead names the board ("TOP TIMES THIS SESSION  -  <skill>": boards and bests are per skill).
    ShowResults(Medal:string, MedalColor:color, TimeLine:string, BestLine:string, RecordLine:message, AccuracyLine:string, BoardHead:string, Rows:[]message, OwnRow:int):void =
        ResultsTitle.SetTextColor(MedalColor)
        ResultsTitle.SetText(FnmText("FINISH!"))
        ResultsMedal.SetTextColor(MedalColor)
        ResultsMedal.SetText(FnmText(if (Medal = "") then "" else "{Medal} MEDAL"))
        ResultsTime.SetText(FnmText(TimeLine))
        ResultsBest.SetText(FnmText(BestLine))
        ResultsRecord.SetText(RecordLine)
        ResultsAccuracy.SetText(FnmText(AccuracyLine))
        ResultsBoardHead.SetText(FnmText(BoardHead))
        for (K -> Block : ResultsRows):
            if (Row := Rows[K]):
                Block.SetText(Row)
                Block.SetTextColor(if (K = OwnRow) then NamedColors.Orange else NamedColors.White)
                Block.SetVisibility(widget_visibility.Visible)
            else:
                Block.SetText(FnmText(""))
                Block.SetVisibility(widget_visibility.Collapsed)
        SetCountdown("")
        if (Results := MaybeResults?):
            Results.SetVisibility(widget_visibility.Visible)

    # "Next run in 12" on the finish board ("" collapses the row).
    SetCountdown(Text:string):void =
        SetOrCollapse(ResultsCountdown, Text)

    HideResults():void =
        if (Results := MaybeResults?):
            Results.SetVisibility(widget_visibility.Collapsed)

    # ---------------------------------------------------------------- skill picker (PROTOCOL 6b)

    # The director, told about every click on this HUD's buttons.
    SetListener(Listener:fnm_picker_listener):void =
        set MaybeListener = option{Listener}

    # A button was clicked. Only this HUD's own player counts (a widget_message names who clicked).
    Clicked(Player:player, Kind:fnm_pick, Index:int):void =
        if (Owner := MaybeOwner?, Player = Owner, Listener := MaybeListener?):
            Listener.OnPickerChoice(Player, Kind, Index)

    # Grade step: one loud button per grade, labelled "Grade G", in the order given (the director's grade order).
    ShowGradeStep(Grades:[]string):void =
        Labels := for (Grade : Grades) { "Grade {Grade}" }
        Indices := for (K -> Grade : Grades) { K }
        ShowPickerStep("Pick a grade", Labels, array{}, fnm_pick.Grade, Indices, false)

    # Skill step for Grade: one button per skill, its title on the button and its subtitle in small text under it
    # (button K picks cartridge Indices[K]), plus Back when WithBack. A stock button sets its own text size and grows
    # to fit its label, so "Title  -  Subtitle" labels in two columns ran past the edges of a 1080p screen (Aaron,
    # 2026-10-06: "words are cut off"); a text_block caption has a size we choose.
    ShowSkillStep(Grade:string, Titles:[]string, Subtitles:[]string, Indices:[]int, WithBack:logic):void =
        ShowPickerStep("Grade {Grade}  -  pick a skill", Titles, Subtitles, fnm_pick.Skill, Indices, WithBack)

    # Replaces the picker's buttons with this step's (Captions[K], when present and not empty, goes under button K),
    # puts the picker on screen if it isn't, and focuses the first button (so a gamepad or keyboard can press it too).
    ShowPickerStep(Step:string, Labels:[]string, Captions:[]string, Kind:fnm_pick, Indices:[]int, WithBack:logic):void =
        ClearPickerButtons()
        PickerStep.SetText(FnmText(Step))
        var Made : []widget = array{}
        var Buttons : []widget = array{}
        var Cells : []widget = array{}
        for (K -> Label : Labels, Index := Indices[K]):
            Button := MakeButton(Kind, Label)
            Button.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := Kind, Index := Index}.OnClick)
            set Buttons += array{Button}
            set Cells += array{MakeCell(Button, if (Caption := Captions[K]) then Caption else "")}
        # More than PickerColumnAfter buttons go in two columns (left column first, top to bottom): ten skills in one
        # column ran off a 1080p screen.
        if (Cells.Length > PickerColumnAfter):
            Left : stack_box = stack_box{Orientation := orientation.Vertical, Slots := array{}}
            Right : stack_box = stack_box{Orientation := orientation.Vertical, Slots := array{}}
            for (K -> Cell : Cells):
                Slot := stack_box_slot{Widget := Cell, HorizontalAlignment := horizontal_alignment.Fill, Padding := margin{Top := 10.0}}
                if (2 * K < Cells.Length) then Left.AddWidget(Slot) else Right.AddWidget(Slot)
            Columns : stack_box = stack_box:
                Orientation := orientation.Horizontal
                Slots := array:
                    stack_box_slot{Widget := Left, VerticalAlignment := vertical_alignment.Top, Padding := margin{Right := 12.0}}
                    stack_box_slot{Widget := Right, VerticalAlignment := vertical_alignment.Top, Padding := margin{Left := 12.0}}
            PickerButtons.AddWidget(stack_box_slot{Widget := Columns, HorizontalAlignment := horizontal_alignment.Center})
            set Made += array{Columns}
        else:
            for (Cell : Cells):
                PickerButtons.AddWidget(stack_box_slot{Widget := Cell, HorizontalAlignment := horizontal_alignment.Fill, Padding := margin{Top := 10.0}})
                set Made += array{Cell}
        if (WithBack?):
            Back := button_quiet{DefaultText := FnmText("Back")}
            Back.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.Back, Index := 0}.OnClick)
            PickerButtons.AddWidget(stack_box_slot{Widget := Back, HorizontalAlignment := horizontal_alignment.Center, Padding := margin{Top := 22.0}})
            set Made += array{Back}
        set PickerButtonList = Made
        if (PlayerUI := MaybePlayerUI?, PickerRoot := MaybePickerRoot?):
            if (not PickerShown?):
                PlayerUI.AddWidget(PickerRoot, player_ui_slot{ZOrder := 5, InputMode := ui_input_mode.All})
                set PickerShown = true
            if (First := Buttons[0]):
                PlayerUI.SetFocus(First)

    # Grade buttons are loud, skill buttons regular.
    MakeButton(Kind:fnm_pick, Label:string):text_button_base =
        if (Kind = fnm_pick.Grade) then button_loud{DefaultText := FnmText(Label)}
        else button_regular{DefaultText := FnmText(Label)}

    # The button with Caption (a skill's subtitle) in small text under it; the button alone when Caption is empty.
    # The button fills the cell's width, so every button in a column is as wide as the widest.
    MakeCell(Button:widget, Caption:string):widget =
        if (Caption = ""):
            return Button
        Text := text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 22.0, DefaultJustification := text_justification.Center}
        Text.SetText(FnmText(Caption))
        stack_box:
            Orientation := orientation.Vertical
            Slots := array:
                stack_box_slot{Widget := Button, HorizontalAlignment := horizontal_alignment.Fill}
                stack_box_slot{Widget := Text, HorizontalAlignment := horizontal_alignment.Center, Padding := margin{Top := 2.0}}

    ClearPickerButtons():void =
        for (Old : PickerButtonList):
            PickerButtons.RemoveWidget(Old)
        set PickerButtonList = array{}

    # Takes the picker off the screen (input goes back to the game).
    HidePicker():void =
        if (PickerShown?, PlayerUI := MaybePlayerUI?, PickerRoot := MaybePickerRoot?):
            PlayerUI.RemoveWidget(PickerRoot)
        set PickerShown = false
        ClearPickerButtons()

    # CLOSE (and CHANGE SKILL when WithChange) under the finish board. While they are up the mouse drives the buttons
    # and the player can't move; CLOSE hands control back.
    ShowFinishButtons(WithChange:logic):void =
        ChangeSkillButton.SetVisibility(if (WithChange?) then widget_visibility.Visible else widget_visibility.Collapsed)
        if (not ChangeShown?, PlayerUI := MaybePlayerUI?, ChangeRoot := MaybeChangeRoot?):
            PlayerUI.AddWidget(ChangeRoot, player_ui_slot{ZOrder := 4, InputMode := ui_input_mode.All})
            set ChangeShown = true
            PlayerUI.SetFocus(CloseButton)

    HideFinishButtons():void =
        if (ChangeShown?, PlayerUI := MaybePlayerUI?, ChangeRoot := MaybeChangeRoot?):
            PlayerUI.RemoveWidget(ChangeRoot)
        set ChangeShown = false
