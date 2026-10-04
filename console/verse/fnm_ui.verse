# FNM console runtime -- per-player HUD (Verse UI: canvas + stack_box + text_blocks).
# One fnm_hud instance per player; only that player sees it.

using { /Fortnite.com/UI }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/UI }
using { /Verse.org/Colors }
using { /Verse.org/Simulation }

# string -> message (SetText / DefaultText take a `message`, not a `string`).
FnmText<localizes>(Value:string):message = "{Value}"

fnm_hud := class:
    # Width (px at 1080p) at which long lines wrap. Explanations are up to 160 chars (PROTOCOL 5 rule 6).
    WrapAt : float = 1500.0

    TitleText : text_block = text_block{DefaultTextColor := NamedColors.Gold, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    StageText : text_block = text_block{DefaultTextColor := NamedColors.Aqua, DefaultTextSize := 26.0, DefaultJustification := text_justification.Center}
    PromptText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 44.0, DefaultJustification := text_justification.Center}
    ChoicesText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    FeedbackText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    # Verdict: a big check mark or cross (textures; the HUD font has no such glyphs) over CORRECT! or the
    # penalty's name. FNM_Art.T_fnm_check / T_fnm_cross are imported into each map's project by
    # tools/import_art.py.
    VerdictImage : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_check, DefaultDesiredSize := vector2{X := 240.0, Y := 240.0}}
    VerdictLabel : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 96.0, DefaultJustification := text_justification.Center}
    # Race clock and streak, left side.
    ClockText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 52.0, DefaultJustification := text_justification.Left}
    StreakText : text_block = text_block{DefaultTextColor := NamedColors.Orange, DefaultTextSize := 30.0, DefaultJustification := text_justification.Left}
    # Full-screen black for the Blackout penalty (the post-process "Dark" effect only tinted the view).
    BlackScreen : color_block = color_block{DefaultColor := NamedColors.Black, DefaultOpacity := 0.0}
    # Seconds the verdict stays up.
    VerdictSeconds : float = 1.5

    var MaybePlayerUI : ?player_ui = false
    var MaybeRoot : ?canvas = false
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
                                                Widget := StreakText
                                                HorizontalAlignment := horizontal_alignment.Left
                                    Padding := margin{Left := 24.0, Top := 8.0, Right := 24.0, Bottom := 10.0}
                        # Left, under Fortnite's GAME MODE box: top right is the minimap's (it hid the clock).
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 0.0, Y := 0.0}}
                        Alignment := vector2{X := 0.0, Y := 0.0}
                        Offsets := margin{Left := 20.0, Top := 230.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
            VerdictImage.SetVisibility(widget_visibility.Collapsed)
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
        StageText.SetText(FnmText(StageLine))
        PromptText.SetText(FnmText(Prompt))
        ChoicesText.SetText(FnmText(ChoicesLine))
        ClearFeedbackNow()

    # Shows Message in TextColor; returns the generation number to pass to ClearFeedbackIf.
    ShowFeedback(Message:string, TextColor:color):int =
        set FeedbackGeneration += 1
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

    SetStreak(Text:string):void =
        StreakText.SetText(FnmText(Text))

    # Screen to black (On) or back. The HUD text and the verdict stay on top of it.
    SetBlack(On:logic):void =
        if (On?) then BlackScreen.SetOpacity(1.0) else BlackScreen.SetOpacity(0.0)

    # End-of-run screen.
    ShowFinished(Headline:string, Detail:string):void =
        StageText.SetText(FnmText(""))
        PromptText.SetText(FnmText(Headline))
        ChoicesText.SetText(FnmText(Detail))
        ClearFeedbackNow()
