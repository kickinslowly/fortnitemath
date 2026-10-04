# FNM console runtime -- per-player HUD (Verse UI: canvas + stack_box + text_blocks).
# One fnm_hud instance per player; only that player sees it.

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

fnm_hud := class:
    # Width (px at 1080p) at which long lines wrap. Explanations are up to 160 chars (PROTOCOL 5 rule 6).
    WrapAt : float = 1500.0

    TitleText : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    StageText : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 26.0, DefaultJustification := text_justification.Center}
    PromptText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 44.0, DefaultJustification := text_justification.Center}
    ChoicesText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    FeedbackText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    # Streak and speed boost, big, at the bottom of the top panel (Aaron 2026-10-04: the small left line went unnoticed).
    StreakBig : text_block = text_block{DefaultTextColor := NamedColors.Orange, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
    # Verdict: a big check mark or cross (textures; the HUD font has no such glyphs) over CORRECT! or the
    # penalty's name. FNM_Art.T_fnm_check / T_fnm_cross are imported into each map's project by
    # tools/import_art.py.
    VerdictImage : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_check, DefaultDesiredSize := vector2{X := 240.0, Y := 240.0}}
    VerdictLabel : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 96.0, DefaultJustification := text_justification.Center}
    # Race clock and the run's target time ("Beat 1:20.1"), left side.
    ClockText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 52.0, DefaultJustification := text_justification.Left}
    TargetText : text_block = text_block{DefaultTextColor := NamedColors.Orange, DefaultTextSize := 30.0, DefaultJustification := text_justification.Left}
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

    var MaybePlayerUI : ?player_ui = false
    var MaybeRoot : ?canvas = false
    var MaybeResults : ?widget = false
    # Bumped on every feedback message so an older timer never clears a newer message.
    var FeedbackGeneration : int = 0
    var VerdictGeneration : int = 0

    # Builds the widget tree and adds it to Player's screen. Safe to call once per player.
    Attach(Player:player):void =
        if (PlayerUI := GetPlayerUI[Player]):
            set PromptText.WrapWidth = WrapAt
            set ChoicesText.WrapWidth = WrapAt
            set FeedbackText.WrapWidth = WrapAt
            Lines : stack_box = stack_box:
                Orientation := orientation.Vertical
                Slots := array:
                    stack_box_slot:
                        Widget := TitleText
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := StageText
                        HorizontalAlignment := horizontal_alignment.Center
                    stack_box_slot:
                        Widget := PromptText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 12.0}
                    stack_box_slot:
                        Widget := ChoicesText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 8.0}
                    stack_box_slot:
                        Widget := FeedbackText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 16.0}
                    stack_box_slot:
                        Widget := StreakBig
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 10.0}
            # A dark translucent panel behind the text: the pale walls and sky washed out coloured text.
            Panel : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.55}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := Lines
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Left := 32.0, Top := 12.0, Right := 32.0, Bottom := 14.0}
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
                        Widget := color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.78}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := ResultsLines
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Left := 40.0, Top := 28.0, Right := 40.0, Bottom := 28.0}
            Root : canvas = canvas:
                Slots := array:
                    canvas_slot:
                        Widget := BlackScreen
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 1.0, Y := 1.0}}
                        Offsets := margin{Left := 0.0, Top := 0.0, Right := 0.0, Bottom := 0.0}
                    canvas_slot:
                        Widget := Panel
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.0}, Maximum := vector2{X := 0.5, Y := 0.0}}
                        Alignment := vector2{X := 0.5, Y := 0.0}
                        Offsets := margin{Left := 0.0, Top := 40.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
                    # The finish board, centre screen; before the verdict slot so GO! / a check draw on top.
                    canvas_slot:
                        Widget := Results
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.45}, Maximum := vector2{X := 0.5, Y := 0.45}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
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
                                    Widget := stack_box:
                                        Orientation := orientation.Vertical
                                        Slots := array:
                                            stack_box_slot:
                                                Widget := ClockText
                                                HorizontalAlignment := horizontal_alignment.Left
                                            stack_box_slot:
                                                Widget := TargetText
                                                HorizontalAlignment := horizontal_alignment.Left
                                    Padding := margin{Left := 24.0, Top := 8.0, Right := 24.0, Bottom := 10.0}
                        # Left, under Fortnite's GAME MODE box: top right is the minimap's (it hid the clock).
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 0.0, Y := 0.0}}
                        Alignment := vector2{X := 0.0, Y := 0.0}
                        Offsets := margin{Left := 20.0, Top := 230.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
            VerdictImage.SetVisibility(widget_visibility.Collapsed)
            Results.SetVisibility(widget_visibility.Collapsed)
            StreakBig.SetVisibility(widget_visibility.Collapsed)
            TargetText.SetVisibility(widget_visibility.Collapsed)
            set MaybeResults = option{Results}
            PlayerUI.AddWidget(Root, player_ui_slot{InputMode := ui_input_mode.None})
            set MaybePlayerUI = option{PlayerUI}
            set MaybeRoot = option{Root}

    # Removes the HUD (used when the player leaves; harmless if already gone).
    Detach():void =
        if (PlayerUI := MaybePlayerUI?, Root := MaybeRoot?):
            PlayerUI.RemoveWidget(Root)
        set MaybePlayerUI = false
        set MaybeRoot = false

    SetTitle(Title:string, Subtitle:string):void =
        if (Subtitle = ""):
            TitleText.SetText(FnmText(Title))
        else:
            TitleText.SetText(FnmText(Title + "  -  " + Subtitle))

    # Shows one question: "Stage s/S - <tier name>", the prompt, the lettered choices; clears feedback.
    ShowQuestion(StageLine:string, Prompt:string, ChoicesLine:string):void =
        for (Block : array{StageText, PromptText, ChoicesText, FeedbackText}):
            Block.SetVisibility(widget_visibility.Visible)
        StageText.SetText(FnmText(StageLine))
        PromptText.SetText(FnmText(Prompt))
        ChoicesText.SetText(FnmText(ChoicesLine))
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

    ClearFeedbackNow():void =
        set FeedbackGeneration += 1
        FeedbackText.SetText(FnmText(""))

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

    # The big streak / speed-boost line in the top panel ("" collapses it, so the panel doesn't grow).
    SetStreak(Text:string):void =
        SetOrCollapse(StreakBig, Text)

    # The run's target under the clock ("Beat 1:20.1"; "" collapses it).
    SetTarget(Text:string):void =
        SetOrCollapse(TargetText, Text)

    SetOrCollapse(Block:text_block, Text:string):void =
        Block.SetText(FnmText(Text))
        if (Text = "") then Block.SetVisibility(widget_visibility.Collapsed) else Block.SetVisibility(widget_visibility.Visible)

    # Screen to black (On) or back. The HUD text and the verdict stay on top of it.
    SetBlack(On:logic):void =
        if (On?) then BlackScreen.SetOpacity(1.0) else BlackScreen.SetOpacity(0.0)

    # Empties the question panel (stage, prompt, choices, feedback) and collapses those blocks, so the panel
    # shrinks to the title instead of leaving a tall dark box behind the finish board. ShowQuestion reopens them.
    ClearQuestion():void =
        StageText.SetText(FnmText(""))
        PromptText.SetText(FnmText(""))
        ChoicesText.SetText(FnmText(""))
        ClearFeedbackNow()
        for (Block : array{StageText, PromptText, ChoicesText, FeedbackText}):
            Block.SetVisibility(widget_visibility.Collapsed)

    # The finish board. Medal "" leaves its row blank. Rows: the session's top times, best first; OwnRow is the
    # viewing player's row (-1 = not on the board), drawn orange. The countdown row starts empty (SetCountdown).
    ShowResults(Medal:string, MedalColor:color, TimeLine:string, BestLine:string, RecordLine:message, AccuracyLine:string, Rows:[]message, OwnRow:int):void =
        ResultsTitle.SetTextColor(MedalColor)
        ResultsTitle.SetText(FnmText("FINISH!"))
        ResultsMedal.SetTextColor(MedalColor)
        ResultsMedal.SetText(FnmText(if (Medal = "") then "" else "{Medal} MEDAL"))
        ResultsTime.SetText(FnmText(TimeLine))
        ResultsBest.SetText(FnmText(BestLine))
        ResultsRecord.SetText(RecordLine)
        ResultsAccuracy.SetText(FnmText(AccuracyLine))
        ResultsBoardHead.SetText(FnmText("TOP TIMES THIS SESSION"))
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
