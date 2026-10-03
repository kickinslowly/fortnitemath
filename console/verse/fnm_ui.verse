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
    StageText : text_block = text_block{DefaultTextColor := NamedColors.LightSkyBlue, DefaultTextSize := 26.0, DefaultJustification := text_justification.Center}
    PromptText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 44.0, DefaultJustification := text_justification.Center}
    ChoicesText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    FeedbackText : text_block = text_block{DefaultTextColor := NamedColors.White, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}

    var MaybePlayerUI : ?player_ui = false
    var MaybeRoot : ?canvas = false
    # Bumped on every feedback message so an older timer never clears a newer message.
    var FeedbackGeneration : int = 0

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
            Root : canvas = canvas:
                Slots := array:
                    canvas_slot:
                        Widget := Lines
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.0}, Maximum := vector2{X := 0.5, Y := 0.0}}
                        Alignment := vector2{X := 0.5, Y := 0.0}
                        Offsets := margin{Left := 0.0, Top := 40.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
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

    # End-of-run screen.
    ShowFinished(Headline:string, Detail:string):void =
        StageText.SetText(FnmText(""))
        PromptText.SetText(FnmText(Headline))
        ChoicesText.SetText(FnmText(Detail))
        ClearFeedbackNow()
