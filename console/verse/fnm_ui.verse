# FNM console runtime -- per-player HUD (Verse UI: canvas + stack_box + text_blocks + texture_blocks).
# One fnm_hud instance per player; only that player sees it. The question sits on "the slate", top centre: a framed
# dark chalk slate (texture FNM_Art.T_fnm_slate inside a pale color_block rim) hung like a sign above the door wall,
# with the station caption, the prompt, and the answers as four tiles laid out left to right like the doors, each in its
# own colour (FnmTileSrgb; texture FNM_Art.T_fnm_tile tinted per tile). After a right door the slate
# holds the solved item as a recap card (ShowRecap). The skill's title and subtitle are a small
# tag top left under Fortnite's GAME MODE box. Every player draws their own item and letter shuffle, and UEFN has no
# per-player world text, so the slate is HUD, not a world sign (Aaron 2026-10-08: the flat black panel "feels like
# alpha version"). The skill picker and the finish board's NEW SKILL
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
# Today's record: the best time of this session's board (the session is one server run), not an island-wide record.
FnmHolder<localizes>(Time:string, Who:agent, Tail:string):message = "Today's record   {Time}  by {Who}{Tail}"
# Rivals strip row (the viewer's own row is plain text, "YOU  station 4").
FnmRivalRow<localizes>(Who:agent, Tail:string):message = "{Who}  {Tail}"
# Public feed lines (fnm_director Broadcast), shown to every player.
FnmFeedPenalty<localizes>(Who:agent, Past:string, Station:int):message = "{Who} got {Past} at station {Station}"
# The medal stays out of the public line (a bronze is not announced to the room); Medal stays in the signature for the callers.
FnmFeedFinish<localizes>(Who:agent, Time:string, Medal:string):message = "{Who} finished in {Time}"
FnmFeedRecord<localizes>(Who:agent, Time:string):message = "{Who} set today's record  {Time}"
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

# Verse UI colour, measured in play 2026-10-13 (UEFN 42.30): a `color` is ACES 2065-1 linear, and the HUD draws every
# colour it is given (text, color_block, texture tint) about 3.86x too bright in linear light. A raw door tint B
# (0.3, 0.55, 1.0) came out (0, 255, 255), C (0.2, 0.9, 0.3) (0, 255, 246), D (1.0, 0.55, 0.1) (255, 255, 30), and
# NamedColors.Orange drew yellow. A texture is lifted the same way: its default white tint multiplies it by that gain
# (the slate PNG, drawn (34, 38, 40), came out near (94, 98, 101)). FnmUi takes the gain back out, so a colour draws as
# the colour it names: FnmUi(NamedColors.Orange) draws (255, 165, 0). EVERY colour that reaches a widget in this file
# goes through that correction at the point it is set, so callers pass plain NamedColors and nothing double-corrects:
# a SetTextColor / SetColor / SetTint argument is wrapped in FnmUi(...); a field default (a user function cannot be called
# in a class field initialiser: error 3582) is written `NamedColors.Gold * FnmUiGain`, the same factor. FnmSrgb turns a plain sRGB triple (what you would type in a paint
# program) into the same colour space as the presets, for colours that are not a preset. White stays white
# (FnmUi(NamedColors.White) draws 255). tests/test_hud_layout.py pins that no widget colour skips FnmUi.
# (The corrected colours are darker than the lifted ones were: the small panels' black backing went from 0.55 to 0.72, because
# Orange / Aqua text on 0.55 over a bright sky lost its contrast in the first frames.)
FnmUiGain : float = 0.259
FnmUi(C:color):color = C * FnmUiGain
FnmSrgb(R:float, G:float, B:float):color = MakeColorFromSRGB(R, G, B)

# The answer tiles' colours, A..D, as plain sRGB triples (FnmSrgb, then FnmUi where they are set): white, blue, green, orange, the door
# paint's four hues but four colours that stay apart on screen. tests/test_hud_layout.py pins them.
FnmTileSrgb : []color = array:
    color{R := 1.0, G := 1.0, B := 1.0}
    color{R := 0.25, G := 0.55, B := 1.0}
    color{R := 0.2, G := 0.85, B := 0.25}
    color{R := 1.0, G := 0.58, B := 0.08}

# What a picker / finish-board button reports (PROTOCOL 6b): a grade (Index = position in the director's grade
# list), a skill (Index = cartridge index in the slot), Back to the grade step, or NEW SKILL / CLOSE on the finish
# board; BOSS BATTLE on the grade step and PLAY AGAIN on the boss-mode win board (BOSS_MODE.md section 1).
fnm_pick := enum:
    Grade
    Skill
    Back
    ChangeSkill
    Close
    Boss
    Again

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
    TitleText : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
    SubtitleText : text_block = text_block{DefaultTextColor := NamedColors.Aqua * FnmUiGain, DefaultTextSize := 20.0, DefaultJustification := text_justification.Left}
    # The slate's caption row ("Station 1/10  -  Rectangles"), top left of the slate, then the prompt.
    StageText : text_block = text_block{DefaultTextColor := NamedColors.Aqua * FnmUiGain, DefaultTextSize := 22.0, DefaultJustification := text_justification.Left}
    PromptText : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 46.0, DefaultJustification := text_justification.Center}
    # The slate's chalk texture (stretched; the 6 px rim round it is a color_block, so the frame stays crisp). 1180
    # wide (1192 with the rim, x 364-1556 at 1080p) clears Fortnite's GAME MODE box (ends x 356) and the minimap (from
    # x 1603). Measured 2026-10-13 at 1080p: the slate is ~305 px tall (bottom y ~345) with or without a recap card, because the
    # caption row (CaptionHeight) and the band under the tiles (BandHeight) keep their height; the old one moved 225 <-> 335.
    SlateArt : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_slate, DefaultDesiredSize := vector2{X := 1180.0, Y := 210.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    # The answer tiles, A..D left to right like the doors, 256 x 112. The four doors are the same prop: only the paint
    # and letters tell them apart, so each tile's ring, letter (40 px: the key to the game) and value take its own
    # colour (FnmTileSrgb through FnmSrgb and FnmUi, set in Attach). Tiles past the item's choice count are collapsed.
    TileArt : []texture_block = array:
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 256.0, Y := 112.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 256.0, Y := 112.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 256.0, Y := 112.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
        texture_block{DefaultImage := FNM_Art.T_fnm_tile, DefaultDesiredSize := vector2{X := 256.0, Y := 112.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    TileLetter : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
    TileValue : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    # A wash in the tile's colour over a tile's dark interior: 0 except on the right tile of a recap card, where it lights up.
    TileGlow : []color_block = array:
        color_block{DefaultColor := NamedColors.White * FnmUiGain, DefaultOpacity := 0.0}
        color_block{DefaultColor := NamedColors.White * FnmUiGain, DefaultOpacity := 0.0}
        color_block{DefaultColor := NamedColors.White * FnmUiGain, DefaultOpacity := 0.0}
        color_block{DefaultColor := NamedColors.White * FnmUiGain, DefaultOpacity := 0.0}
    # Recap card (ShowRecap): the solved item's worked steps on the slate's band under the tiles, and the verdict
    # ("CORRECT!  -1.8 s") on the caption row, right.
    RecapSteps : text_block = text_block{DefaultTextColor := MakeColorFromSRGB(0.82, 0.96, 0.82) * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Center}
    RecapVerdict : text_block = text_block{DefaultTextColor := NamedColors.Lime * FnmUiGain, DefaultTextSize := 28.0, DefaultJustification := text_justification.Right}
    # The band under the tiles (steps, feedback, streak, boss line) keeps at least this height, so the slate does not
    # jump between a bare question and a recap (ux_critique P2: it moved between ~225 and ~335 px).
    BandHeight : float = 60.0
    # The caption row's height: the station caption on the left, the recap's verdict on the right.
    CaptionHeight : float = 34.0
    var RecapGeneration : int = 0
    FeedbackText : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 28.0, DefaultJustification := text_justification.Center}
    # Streak and speed boost, big, at the bottom of the slate (Aaron 2026-10-04: the small left line went unnoticed).
    StreakBig : text_block = text_block{DefaultTextColor := NamedColors.Orange * FnmUiGain, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
    # Boss arena: the shared boss health bar and the viewer's own hits, the last line of the slate, shown only to a
    # player at the arena stage (fnm_director BossLoop refreshes it; collapsed otherwise, so nothing else moves).
    BossText : text_block = text_block{DefaultTextColor := NamedColors.Red * FnmUiGain, DefaultTextSize := 36.0, DefaultJustification := text_justification.Center}
    # Boss mode's boss bar, at the bottom like a classic boss fight (Aaron 2026-10-10: "make healthbar more noticeable"):
    # the boss's name and mood over a 680 x 44 red bar on a gold frame, its health and the team's hits on the bar.
    # Collapsed until SetBossBar; ClearBoss collapses it again.
    BossBarName : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
    BossBarFill : color_block = color_block{DefaultColor := MakeColorFromSRGB(0.85, 0.06, 0.04) * FnmUiGain, DefaultOpacity := 1.0, DefaultDesiredSize := vector2{X := 680.0, Y := 44.0}}
    BossBarValue : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    BossBarWidth : float = 680.0
    BossBarHeight : float = 44.0
    var MaybeBossBar : ?widget = false
    var BossBarGeneration : int = 0
    # Verdict: a big check mark or cross (textures; the HUD font has no such glyphs) over CORRECT! or the
    # penalty's name. FNM_Art.T_fnm_check / T_fnm_cross are imported into each map's project by
    # tools/import_art.py.
    VerdictImage : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_check, DefaultDesiredSize := vector2{X := 240.0, Y := 240.0}}
    # The big verdict text (CORRECT!, STUCK IN MUD!  +3 s, the countdown, FINISH!) must read over ANY background: a red verdict
    # over the red / pink hazard-striped barrier behind the doors measured contrast 1.05 : 1 (Q frame w1_4_stuck_in_mud,
    # 2026-10-13). So it has a hard black shadow (text_block shadow, 4 px down-right) and a black backing behind it
    # (VerdictBack, opacity 0.8 while there is text, 0 when empty): red text on that backing over the brightest (white)
    # stripe is 3.2 : 1, over the stripes' mean 4.4 : 1. SetVerdictText sets the text and the backing together.
    VerdictLabel : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 96.0, DefaultJustification := text_justification.Center, DefaultShadowOffset := option{vector2{X := 4.0, Y := 4.0}}, DefaultShadowColor := NamedColors.Black * FnmUiGain, DefaultShadowOpacity := 1.0}
    VerdictBack : color_block = color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.0}
    # Race clock and the run's target time ("Beat 1:20.1"), left side.
    ClockText : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 52.0, DefaultJustification := text_justification.Left}
    TargetText : text_block = text_block{DefaultTextColor := NamedColors.Orange * FnmUiGain, DefaultTextSize := 30.0, DefaultJustification := text_justification.Left}
    # Pace delta under the target at each right answer ("-1.8 s" ahead, "+3.2 s" behind, a real minus sign;
    # collapsed with no pace target).
    DeltaText : text_block = text_block{DefaultTextColor := NamedColors.LightGreen * FnmUiGain, DefaultTextSize := 30.0, DefaultJustification := text_justification.Left}
    # Rivals strip, under the delta in the same left panel: a RACE heading and one row per player (fnm_director
    # RaceLoop, sorted by progress), the viewer's own row gold. Unused rows are collapsed; all of it while picking.
    RivalsHead : text_block = text_block{DefaultTextColor := NamedColors.Aqua * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
    RivalRows : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Left}
    # Public feed, top right under the minimap: up to 3 lines, newest on top, each gone after FeedSeconds.
    FeedRows : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Right}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Right}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 24.0, DefaultJustification := text_justification.Right}
    FeedSeconds : float = 7.0
    # The feed and the finish board must never overlap (frame d3/f_135, 2026-10-13: the record line ran from x 1370 into a board
    # that ends at 1460). The board is centred and its widest line wraps at ResultsWrap, so it spans at most
    # 960 +- (ResultsWrap + 80) / 2 = 460 .. 1460; the feed hangs from x 1900 and its lines wrap at FeedWrap, so its panel
    # (FeedWrap + 40) starts at x 1480 or more. Both stay clear of the minimap (from x 1603) because the feed sits under it
    # (Top 358: below its player-count icons, y ~335, and 12 px under the slate's bottom edge at ~346). tests/test_hud_layout.py pins the numbers.
    FeedWrap : float = 380.0
    ResultsWrap : float = 920.0
    # Finish board (centre screen, hidden until a finish): headline, medal, this run, personal best, today's record,
    # accuracy, the session's top times (one row per player) and the next-run countdown.
    ResultsTitle : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 72.0, DefaultJustification := text_justification.Center}
    ResultsMedal : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 52.0, DefaultJustification := text_justification.Center}
    ResultsTime : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 44.0, DefaultJustification := text_justification.Center}
    ResultsBest : text_block = text_block{DefaultTextColor := NamedColors.Aqua * FnmUiGain, DefaultTextSize := 36.0, DefaultJustification := text_justification.Center}
    ResultsRecord : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 36.0, DefaultJustification := text_justification.Center}
    ResultsAccuracy : text_block = text_block{DefaultTextColor := NamedColors.LightGreen * FnmUiGain, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    ResultsBoardHead : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 34.0, DefaultJustification := text_justification.Center}
    # Room for 5 top-time rows (the director's BoardSize); unused ones are collapsed.
    ResultsRows : []text_block = array:
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
        text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 32.0, DefaultJustification := text_justification.Center}
    ResultsCountdown : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    # The board's header row (Meshy art, tools/make_medal_art.py; 256 x 256 PNGs drawn square): Volt cheering at its left, the
    # headline and the "GOLD MEDAL" word stacked in the middle, the medal itself at its right (ShowResults swaps its texture to
    # the run's metal; Medal "" collapses it). They sit IN the row, never over the lines below, so nothing overlaps text: the
    # row is VoltArt 180 + HeaderGap + HeaderWrap + HeaderGap + MedalArt 160 = 888 <= ResultsWrap (tests/test_hud_layout.py). Volt is
    # 180, not 200: the board with its five time rows reaches y ~860, and the no-podium CLOSE / NEW SKILL buttons start at y 875.
    # The two texture sizes are the literals in their DefaultDesiredSize (a field initialiser cannot read another field).
    HeaderWrap : float = 500.0
    HeaderGap : float = 24.0
    VoltArt : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_volt, DefaultDesiredSize := vector2{X := 180.0, Y := 180.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    MedalArt : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_medal_gold, DefaultDesiredSize := vector2{X := 160.0, Y := 160.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    # Full-screen black for the Blackout penalty (the post-process "Dark" effect only tinted the view).
    BlackScreen : color_block = color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.0}
    # Boss mode (BOSS_MODE.md section 9): a full-screen white flash on a MEGA NUKE (above the slate, below the verdict),
    # and the level banner, a comic burst (FNM_Art.T_fnm_banner) with "LEVEL 3" over the anger line, centre at y 0.33.
    WhiteFlash : color_block = color_block{DefaultColor := NamedColors.White * FnmUiGain, DefaultOpacity := 0.0}
    BannerArt : texture_block = texture_block{DefaultImage := FNM_Art.T_fnm_banner, DefaultDesiredSize := vector2{X := 900.0, Y := 200.0}, DefaultHorizontalTiling := image_tiling.Stretch, DefaultVerticalTiling := image_tiling.Stretch}
    BannerText : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 84.0, DefaultJustification := text_justification.Center}
    BannerSub : text_block = text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 40.0, DefaultJustification := text_justification.Center}
    # Seconds the verdict stays up.
    VerdictSeconds : float = 1.5
    # Skill picker (PROTOCOL 6b), centre screen on its own root: heading, step line, one button per grade or skill.
    PickerHeading : text_block = text_block{DefaultTextColor := NamedColors.Gold * FnmUiGain, DefaultTextSize := 60.0, DefaultJustification := text_justification.Center}
    PickerStep : text_block = text_block{DefaultTextColor := NamedColors.Aqua * FnmUiGain, DefaultTextSize := 30.0, DefaultJustification := text_justification.Center}
    PickerButtons : stack_box = stack_box{Orientation := orientation.Vertical, Slots := array{}}
    # A step with more buttons than this shows them in two columns.
    PickerColumnAfter : int = 5
    # Under the finish board, on their own root, shown with the board: CLOSE (the board stays until the player closes
    # it; Aaron 2026-10-05: "x it and enjoy themself in the victory area") and NEW SKILL (more than one skill only).
    # (Their text is set in Attach: a localized call can't initialise a field.)
    CloseButton : button_loud = button_loud{}
    ChangeSkillButton : button_regular = button_regular{}
    # Boss mode's win board: PLAY AGAIN (fnm_pick.Again) in CLOSE's place, beside NEW SKILL.
    AgainButton : button_loud = button_loud{}

    var MaybePlayerUI : ?player_ui = false
    # The boss-mode level banner (collapsed until ShowBanner) and the white flash's generation (a newer flash wins).
    var MaybeBanner : ?widget = false
    # While the banner is up the verdict shows its label only: the check / cross / mushroom image would sit behind the
    # banner (they share the screen's middle band).
    var BannerUp : logic = false
    var FlashGeneration : int = 0
    var MaybeRoot : ?canvas = false
    var MaybeResults : ?widget = false
    # The whole slate (collapsed by ClearQuestion, reopened by ShowQuestion) and the four tile overlays, A..D.
    var MaybeSlate : ?widget = false
    var TileBoxes : []overlay = array{}
    # The four tile colours (FnmTileSrgb through FnmSrgb), built in Attach; FnmUi is applied where a widget takes one.
    var TileTints : []color = array{}
    var MaybeOwner : ?player = false
    var MaybeListener : ?fnm_picker_listener = false
    # The picker's and the NEW SKILL button's roots. Each is added (InputMode All: the mouse cursor and clicks go
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
            set RecapSteps.WrapWidth = WrapAt
            for (Row : FeedRows):
                set Row.WrapWidth = FeedWrap
            for (Row : ResultsRows):
                set Row.WrapWidth = ResultsWrap
            set ResultsTitle.WrapWidth = HeaderWrap
            set ResultsMedal.WrapWidth = HeaderWrap
            set ResultsTime.WrapWidth = ResultsWrap
            set ResultsBest.WrapWidth = ResultsWrap
            set ResultsRecord.WrapWidth = ResultsWrap
            set ResultsAccuracy.WrapWidth = ResultsWrap
            set ResultsBoardHead.WrapWidth = ResultsWrap
            set ResultsCountdown.WrapWidth = ResultsWrap
            # Textures draw lifted by the same gain (the default white tint multiplies them 3.86x in linear light): tint the slate,
            # the banner and the verdict image back down. (The tiles are tinted per tile below.)
            SlateArt.SetTint(FnmUi(NamedColors.White))
            BannerArt.SetTint(FnmUi(NamedColors.White))
            VerdictImage.SetTint(FnmUi(NamedColors.White))
            VoltArt.SetTint(FnmUi(NamedColors.White))
            MedalArt.SetTint(FnmUi(NamedColors.White))
            # The answer tiles: the tile texture tinted with the tile's colour (its white ring takes the colour, the
            # dark interior stays near-black) under the letter and the choice, both in that colour.
            Tiles : stack_box = stack_box{Orientation := orientation.Horizontal, Slots := array{}}
            var Tints : []color = array{}
            for (S : FnmTileSrgb):
                set Tints += array{FnmSrgb(S.R, S.G, S.B)}
            set TileTints = Tints
            for (K -> Art : TileArt, TileColor := Tints[K], Letter := TileLetter[K], Value := TileValue[K], Glow := TileGlow[K]):
                Art.SetTint(FnmUi(TileColor))
                Letter.SetTextColor(FnmUi(TileColor))
                Value.SetTextColor(FnmUi(TileColor))
                Glow.SetColor(FnmUi(TileColor))
                Letter.SetText(FnmText(FnmChoiceLetter(K)))
                Box : overlay = overlay:
                    Slots := array:
                        overlay_slot:
                            Widget := Art
                            HorizontalAlignment := horizontal_alignment.Fill
                            VerticalAlignment := vertical_alignment.Fill
                        overlay_slot:
                            Widget := Glow
                            HorizontalAlignment := horizontal_alignment.Fill
                            VerticalAlignment := vertical_alignment.Fill
                            Padding := margin{Left := 8.0, Top := 8.0, Right := 8.0, Bottom := 8.0}
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
                        Widget := overlay:
                            Slots := array:
                                # A fixed-height caption row (the verdict is taller than the caption), so the slate is the same
                                # height with or without a recap.
                                overlay_slot:
                                    Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.0, DefaultDesiredSize := vector2{X := 1.0, Y := CaptionHeight}}
                                overlay_slot:
                                    Widget := StageText
                                    HorizontalAlignment := horizontal_alignment.Left
                                    VerticalAlignment := vertical_alignment.Center
                                overlay_slot:
                                    Widget := RecapVerdict
                                    HorizontalAlignment := horizontal_alignment.Right
                                    VerticalAlignment := vertical_alignment.Center
                        HorizontalAlignment := horizontal_alignment.Fill
                    stack_box_slot:
                        Widget := PromptText
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 4.0}
                    stack_box_slot:
                        Widget := Tiles
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 10.0}
                    stack_box_slot:
                        Widget := overlay:
                            Slots := array:
                                overlay_slot:
                                    Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.0, DefaultDesiredSize := vector2{X := 1.0, Y := BandHeight}}
                                overlay_slot:
                                    Widget := stack_box:
                                        Orientation := orientation.Vertical
                                        Slots := array:
                                            stack_box_slot:
                                                Widget := RecapSteps
                                                HorizontalAlignment := horizontal_alignment.Center
                                            stack_box_slot:
                                                Widget := FeedbackText
                                                HorizontalAlignment := horizontal_alignment.Center
                                            stack_box_slot:
                                                Widget := StreakBig
                                                HorizontalAlignment := horizontal_alignment.Center
                                                Padding := margin{Top := 4.0}
                                            stack_box_slot:
                                                Widget := BossText
                                                HorizontalAlignment := horizontal_alignment.Center
                                                Padding := margin{Top := 4.0}
                                    HorizontalAlignment := horizontal_alignment.Center
                                    VerticalAlignment := vertical_alignment.Top
                        HorizontalAlignment := horizontal_alignment.Center
                        Padding := margin{Top := 6.0}
            # The slate: a pale rim (the frame), the dark chalk texture inset 6 px inside it, the lines on top. Dark and
            # neutral because the hallway walls are tier-coloured (green, blue, purple, orange, red), and the pale walls
            # and sky washed out coloured text on no backing at all.
            Slate : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := MakeColorFromSRGB(0.86, 0.82, 0.74) * FnmUiGain, DefaultOpacity := 0.95}
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
                        Padding := margin{Left := 30.0, Top := 10.0, Right := 30.0, Bottom := 14.0}
            # The tag: the skill's title and subtitle on a small dark backing.
            Tag : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.72}
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
            # The header row: Volt, the headline over the medal word, the medal (see HeaderWrap).
            ResultsHeader : stack_box = stack_box:
                Orientation := orientation.Horizontal
                Slots := array:
                    stack_box_slot:
                        Widget := VoltArt
                        VerticalAlignment := vertical_alignment.Center
                    stack_box_slot:
                        Widget := stack_box:
                            Orientation := orientation.Vertical
                            Slots := array:
                                stack_box_slot:
                                    Widget := ResultsTitle
                                    HorizontalAlignment := horizontal_alignment.Center
                                stack_box_slot:
                                    Widget := ResultsMedal
                                    HorizontalAlignment := horizontal_alignment.Center
                        VerticalAlignment := vertical_alignment.Center
                        Padding := margin{Left := HeaderGap, Right := HeaderGap}
                    stack_box_slot:
                        Widget := MedalArt
                        VerticalAlignment := vertical_alignment.Center
            ResultsLines : stack_box = stack_box:
                Orientation := orientation.Vertical
                Slots := array:
                    stack_box_slot:
                        Widget := ResultsHeader
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
            # 0.88, not 0.62: at the podium the world ALL-TIME billboard sits right behind the header, and at 0.62 its text
            # read through FINISH! and the medal word (H2 frames, 2026-10-13).
            Results : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.88}
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
                        Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.72}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := FeedLinesBox
                        HorizontalAlignment := horizontal_alignment.Right
                        Padding := margin{Left := 20.0, Top := 8.0, Right := 20.0, Bottom := 10.0}
            # The boss-mode banner: the burst texture stretched to 900 x 200, the two lines centred on it.
            Banner : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := BannerArt
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := stack_box:
                            Orientation := orientation.Vertical
                            Slots := array:
                                stack_box_slot:
                                    Widget := BannerText
                                    HorizontalAlignment := horizontal_alignment.Center
                                stack_box_slot:
                                    Widget := BannerSub
                                    HorizontalAlignment := horizontal_alignment.Center
                        HorizontalAlignment := horizontal_alignment.Center
                        VerticalAlignment := vertical_alignment.Center
            BossBar : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.72}
                        HorizontalAlignment := horizontal_alignment.Fill
                        VerticalAlignment := vertical_alignment.Fill
                    overlay_slot:
                        Widget := stack_box:
                            Orientation := orientation.Vertical
                            Slots := array:
                                stack_box_slot:
                                    Widget := BossBarName
                                    HorizontalAlignment := horizontal_alignment.Center
                                stack_box_slot:
                                    Widget := overlay:
                                        Slots := array:
                                            # Gold frame, a dark trough 4 px inside it, the fill from the left, the text.
                                            overlay_slot:
                                                Widget := color_block{DefaultColor := MakeColorFromSRGB(1.0, 0.78, 0.1) * FnmUiGain, DefaultOpacity := 1.0, DefaultDesiredSize := vector2{X := 688.0, Y := 52.0}}
                                            overlay_slot:
                                                Widget := color_block{DefaultColor := MakeColorFromSRGB(0.1, 0.02, 0.02) * FnmUiGain, DefaultOpacity := 1.0, DefaultDesiredSize := vector2{X := 680.0, Y := 44.0}}
                                                HorizontalAlignment := horizontal_alignment.Center
                                                VerticalAlignment := vertical_alignment.Center
                                            overlay_slot:
                                                Widget := BossBarFill
                                                HorizontalAlignment := horizontal_alignment.Left
                                                VerticalAlignment := vertical_alignment.Center
                                                Padding := margin{Left := 4.0}
                                            overlay_slot:
                                                Widget := BossBarValue
                                                HorizontalAlignment := horizontal_alignment.Center
                                                VerticalAlignment := vertical_alignment.Center
                                    HorizontalAlignment := horizontal_alignment.Center
                                    Padding := margin{Top := 4.0}
                        Padding := margin{Left := 16.0, Top := 4.0, Right := 16.0, Bottom := 10.0}
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
                    # Boss mode's MEGA NUKE flash: full screen, over the slate and the board, under the verdict.
                    canvas_slot:
                        Widget := WhiteFlash
                        Anchors := anchors{Minimum := vector2{X := 0.0, Y := 0.0}, Maximum := vector2{X := 1.0, Y := 1.0}}
                        Offsets := margin{Left := 0.0, Top := 0.0, Right := 0.0, Bottom := 0.0}
                    # Boss mode's level banner (collapsed until ShowBanner), in the open band between the slate (bottom near
                    # y 430 at 1080p) and the verdict label (near y 680..790): centred at y 0.52 (562), it spans 462..662.
                    # At 0.33 it drew over the slate's STREAK and BOSS rows (frame, 2026-10-09).
                    canvas_slot:
                        Widget := Banner
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.52}, Maximum := vector2{X := 0.5, Y := 0.52}}
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
                                    Widget := overlay:
                                        Slots := array:
                                            overlay_slot:
                                                Widget := VerdictBack
                                                HorizontalAlignment := horizontal_alignment.Fill
                                                VerticalAlignment := vertical_alignment.Fill
                                            overlay_slot:
                                                Widget := VerdictLabel
                                                HorizontalAlignment := horizontal_alignment.Center
                                                Padding := margin{Left := 30.0, Top := 4.0, Right := 30.0, Bottom := 10.0}
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
                                    Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.72}
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
                        Offsets := margin{Left := -20.0, Top := 358.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
                    # The boss bar along the bottom edge (at 1080p y ~950..1060), under the MEGA NUKE label (which ends
                    # near y 900: 160 px higher the bar covered it, 2026-10-10 frame), centred at x 900 so its ~720 px
                    # run (x ~540..1260) clears the health bars (end x ~445) and the hotbar's ammo line (from x ~1230,
                    # y 930..995, mostly above the bar's top).
                    canvas_slot:
                        Widget := BossBar
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 1.0}, Maximum := vector2{X := 0.5, Y := 1.0}}
                        Alignment := vector2{X := 0.5, Y := 1.0}
                        Offsets := margin{Left := -60.0, Top := -16.0, Right := 0.0, Bottom := 0.0}
                        SizeToContent := true
            VerdictImage.SetVisibility(widget_visibility.Collapsed)
            Results.SetVisibility(widget_visibility.Collapsed)
            StreakBig.SetVisibility(widget_visibility.Collapsed)
            BossText.SetVisibility(widget_visibility.Collapsed)
            RecapSteps.SetVisibility(widget_visibility.Collapsed)
            RecapVerdict.SetVisibility(widget_visibility.Collapsed)
            TargetText.SetVisibility(widget_visibility.Collapsed)
            DeltaText.SetVisibility(widget_visibility.Collapsed)
            SubtitleText.SetVisibility(widget_visibility.Collapsed)
            # No question yet: the slate opens with the first ShowQuestion.
            Slate.SetVisibility(widget_visibility.Collapsed)
            Banner.SetVisibility(widget_visibility.Collapsed)
            set MaybeBanner = option{Banner}
            BossBar.SetVisibility(widget_visibility.Collapsed)
            set MaybeBossBar = option{BossBar}
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
            PickerHeading.SetText(FnmText("PICK YOUR GRADE"))
            PickerPanel : overlay = overlay:
                Slots := array:
                    overlay_slot:
                        Widget := color_block{DefaultColor := NamedColors.Black * FnmUiGain, DefaultOpacity := 0.78}
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
            # CLOSE and NEW SKILL, just under the finish board (anchored by their top edge).
            CloseButton.SetText(FnmText("CLOSE"))
            CloseButton.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.Close, Index := 0}.OnClick)
            ChangeSkillButton.SetText(FnmText("NEW SKILL"))
            ChangeSkillButton.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.ChangeSkill, Index := 0}.OnClick)
            AgainButton.SetText(FnmText("PLAY AGAIN"))
            AgainButton.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.Again, Index := 0}.OnClick)
            AgainButton.SetVisibility(widget_visibility.Collapsed)
            set MaybeChangeRoot = option:
                canvas:
                    Slots := array:
                        canvas_slot:
                            Widget := stack_box:
                                Orientation := orientation.Horizontal
                                Slots := array:
                                    stack_box_slot{Widget := CloseButton, Padding := margin{Right := 16.0}}
                                    stack_box_slot{Widget := AgainButton, Padding := margin{Right := 16.0}}
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

    # Opens the slate on one question: the caption ("Station s/S - <tier name>"), the prompt, and Choices[K] on tile K
    # (in the order shown, so tile K is door K); tiles with no choice collapse. Clears feedback.
    ShowQuestion(StageLine:string, Prompt:string, Choices:[]string):void =
        if (Slate := MaybeSlate?):
            Slate.SetVisibility(widget_visibility.Visible)
        ClearRecap()
        StageText.SetText(FnmText(StageLine))
        PromptText.SetText(FnmText(Prompt))
        for (K -> Box : TileBoxes):
            if (Value := TileValue[K], Choice := Choices[K]):
                Value.SetText(FnmText(Choice))
                Box.SetVisibility(widget_visibility.Visible)
            else:
                Box.SetVisibility(widget_visibility.Collapsed)
        ClearFeedbackNow()

    # The recap card: the SOLVED item stays on the slate with its right tile lit (Choices[RightIndex]) and the others
    # dimmed, Steps (the worked explanation) on the band under the tiles and Verdict ("CORRECT!  -1.8 s", green) on
    # the caption row. Returns a generation for EndRecapIf; the director calls ShowQuestion for the next item, which
    # replaces the card (and makes an older EndRecapIf a no-op).
    ShowRecap(Prompt:string, Choices:[]string, RightIndex:int, Steps:string, Verdict:string):int =
        ClearRecap()
        ClearFeedbackNow()
        if (Slate := MaybeSlate?):
            Slate.SetVisibility(widget_visibility.Visible)
        PromptText.SetText(FnmText(Prompt))
        for (K -> Box : TileBoxes):
            if (Value := TileValue[K], Choice := Choices[K]):
                Value.SetText(FnmText(Choice))
                Box.SetVisibility(widget_visibility.Visible)
            else:
                Box.SetVisibility(widget_visibility.Collapsed)
        for (K -> Art : TileArt, TileColor := TileTints[K], Letter := TileLetter[K], Value := TileValue[K], Glow := TileGlow[K]):
            if (K = RightIndex):
                Glow.SetOpacity(0.7)
                Letter.SetTextColor(FnmUi(NamedColors.White))
                Value.SetTextColor(FnmUi(NamedColors.White))
            else:
                Art.SetTint(FnmUi(Dimmed(TileColor, 0.3)))
                Letter.SetTextColor(FnmUi(Dimmed(TileColor, 0.4)))
                Value.SetTextColor(FnmUi(Dimmed(TileColor, 0.4)))
        SetOrCollapse(RecapSteps, Steps)
        SetOrCollapse(RecapVerdict, Verdict)
        RecapGeneration

    # Takes the recap's steps and verdict off the slate and puts every tile back in its own colour, only if no newer
    # ShowRecap / ShowQuestion happened since Generation.
    EndRecapIf(Generation:int):void =
        if (Generation = RecapGeneration):
            ClearRecap()

    # Back to a plain question: no recap lines, every tile in its door colour with no glow. Bumps the generation, so
    # every older EndRecapIf is a no-op.
    ClearRecap():void =
        set RecapGeneration += 1
        SetOrCollapse(RecapSteps, "")
        SetOrCollapse(RecapVerdict, "")
        for (K -> Art : TileArt, TileColor := TileTints[K], Letter := TileLetter[K], Value := TileValue[K], Glow := TileGlow[K]):
            Art.SetTint(FnmUi(TileColor))
            Letter.SetTextColor(FnmUi(TileColor))
            Value.SetTextColor(FnmUi(TileColor))
            Glow.SetOpacity(0.0)

    Dimmed(Source:color, Factor:float):color =
        color{R := Source.R * Factor, G := Source.G * Factor, B := Source.B * Factor}

    # Shows Message in TextColor; returns the generation number to pass to ClearFeedbackIf.
    ShowFeedback(Message:string, TextColor:color):int =
        set FeedbackGeneration += 1
        FeedbackText.SetVisibility(widget_visibility.Visible)
        FeedbackText.SetTextColor(FnmUi(TextColor))
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

    # The verdict text, with its black backing (0.8 while there is text, 0 when the text is empty).
    SetVerdictText(Text:string):void =
        VerdictLabel.SetText(FnmText(Text))
        if (Text = "") then VerdictBack.SetOpacity(0.0) else VerdictBack.SetOpacity(0.8)

    # Takes the verdict (check / cross / big text) off the screen now.
    ClearVerdictNow():void =
        set VerdictGeneration += 1
        VerdictImage.SetVisibility(widget_visibility.Collapsed)
        SetVerdictText("")

    # Flashes a green check over CORRECT! (or Label, if given) or a red cross over Label, for VerdictSeconds.
    FlashVerdict(Correct:logic, Label:string):void =
        set VerdictGeneration += 1
        Color := if (Correct?) then NamedColors.Lime else NamedColors.Red
        VerdictLabel.SetTextColor(FnmUi(Color))
        if (Correct?) then VerdictImage.SetImage(FNM_Art.T_fnm_check) else VerdictImage.SetImage(FNM_Art.T_fnm_cross)
        if (not BannerUp?) then VerdictImage.SetVisibility(widget_visibility.Visible) else VerdictImage.SetVisibility(widget_visibility.Collapsed)
        SetVerdictText(if (Correct?, Label = "") then "CORRECT!" else Label)
        spawn{ ClearVerdictLater(VerdictGeneration, VerdictSeconds) }

    ClearVerdictLater(Generation:int, Seconds:float)<suspends>:void =
        Sleep(Seconds)
        if (Generation = VerdictGeneration):
            VerdictImage.SetVisibility(widget_visibility.Collapsed)
            SetVerdictText("")

    # Big text in the verdict spot with no image (countdown, FINISH!), for Seconds (0 = until replaced).
    FlashBig(Text:string, TextColor:color, Seconds:float):void =
        set VerdictGeneration += 1
        VerdictImage.SetVisibility(widget_visibility.Collapsed)
        VerdictLabel.SetTextColor(FnmUi(TextColor))
        SetVerdictText(Text)
        if (Seconds > 0.0):
            spawn{ ClearVerdictLater(VerdictGeneration, Seconds) }

    # Boss mode's right answer: the mushroom cloud (FNM_Art.T_fnm_nuke) over Label in lime, for Seconds.
    FlashNuke(Label:string, Seconds:float):void =
        set VerdictGeneration += 1
        VerdictLabel.SetTextColor(FnmUi(NamedColors.Lime))
        VerdictImage.SetImage(FNM_Art.T_fnm_nuke)
        if (not BannerUp?) then VerdictImage.SetVisibility(widget_visibility.Visible) else VerdictImage.SetVisibility(widget_visibility.Collapsed)
        SetVerdictText(Label)
        spawn{ ClearVerdictLater(VerdictGeneration, Seconds) }

    # A white flash over the whole screen: opacity 0.85 fading to 0 in 0.05 s steps over Seconds. A newer flash takes
    # over from an older one.
    Flash(Seconds:float)<suspends>:void =
        set FlashGeneration += 1
        Generation := FlashGeneration
        Steps := Max(1, if (N := Ceil[Seconds / 0.05]) then N else 1)
        for (K := 0..Steps):
            if (Generation = FlashGeneration):
                if (Op := type{_X:float where 0.0 <= _X, _X <= 1.0}[0.85 * (Steps - K) / (Steps * 1.0)]) then WhiteFlash.SetOpacity(Op)
                Sleep(0.05)
        if (Generation = FlashGeneration):
            WhiteFlash.SetOpacity(0.0)

    # The boss-mode level banner: Big ("LEVEL 3") over Sub ("HE'S FURIOUS!"); HideBanner collapses it. While it is up
    # the verdict's image stays collapsed (BannerUp), so a MEGA NUKE mushroom never stacks behind it.
    ShowBanner(Big:string, Sub:string):void =
        set BannerUp = true
        VerdictImage.SetVisibility(widget_visibility.Collapsed)
        BannerText.SetText(FnmText(Big))
        BannerSub.SetText(FnmText(Sub))
        if (Banner := MaybeBanner?):
            Banner.SetVisibility(widget_visibility.Visible)

    HideBanner():void =
        set BannerUp = false
        if (Banner := MaybeBanner?):
            Banner.SetVisibility(widget_visibility.Collapsed)

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
        if (Bar := MaybeBossBar?):
            Bar.SetVisibility(widget_visibility.Collapsed)

    # The boss bar: Name over the bar filled to Percent (0..100), Detail on it.
    SetBossBar(Name:string, Percent:int, Detail:string):void =
        BossBarName.SetText(FnmText(Name))
        BossBarValue.SetText(FnmText(Detail))
        BossBarFill.SetDesiredSize(vector2{X := BossBarWidth * (Clamp(Percent, 0, 100) * 1.0) / 100.0, Y := BossBarHeight})
        if (Bar := MaybeBossBar?):
            Bar.SetVisibility(widget_visibility.Visible)

    # A hit: the fill flashes white, then back to red.
    HitBossBar()<suspends>:void =
        set BossBarGeneration += 1
        Generation := BossBarGeneration
        for (K := 1..3):
            BossBarFill.SetColor(FnmUi(NamedColors.White))
            Sleep(0.08)
            BossBarFill.SetColor(FnmUi(FnmSrgb(1.0, 0.85, 0.1)))
            Sleep(0.08)
        if (Generation = BossBarGeneration):
            BossBarFill.SetColor(FnmUi(FnmSrgb(0.85, 0.06, 0.04)))

    # The run's target under the clock ("Beat 1:20.1"; "" collapses it).
    SetTarget(Text:string):void =
        SetOrCollapse(TargetText, Text)

    # The pace delta under the target, in TextColor (green ahead, red behind); ClearDelta collapses it.
    SetDelta(Text:string, TextColor:color):void =
        DeltaText.SetTextColor(FnmUi(TextColor))
        SetOrCollapse(DeltaText, Text)

    ClearDelta():void =
        SetOrCollapse(DeltaText, "")

    # The rivals strip: Rows top to bottom (at most RivalRows.Length; the rest collapse), OwnRow = the viewer's row
    # (-1 none), drawn gold. No rows hides the strip, heading included.
    SetRivals(Rows:[]message, OwnRow:int):void =
        for (K -> Block : RivalRows):
            if (Row := Rows[K]):
                Block.SetText(Row)
                Block.SetTextColor(FnmUi(if (K = OwnRow) then NamedColors.Gold else NamedColors.White))
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
        ClearRecap()
        StageText.SetText(FnmText(""))
        PromptText.SetText(FnmText(""))
        for (Value : TileValue):
            Value.SetText(FnmText(""))
        ClearFeedbackNow()
        if (Slate := MaybeSlate?):
            Slate.SetVisibility(widget_visibility.Collapsed)

    # The finish board. Medal "GOLD" / "SILVER" / "BRONZE" shows that medal's picture and "<Medal> MEDAL"; "" collapses both
    # (the header's Volt stays). Rows: the session's top times, best first; OwnRow is the
    # viewing player's row (-1 = not on the board), drawn orange. The countdown row starts empty (SetCountdown).
    # BoardHead names the board ("TOP TIMES THIS SESSION  -  <skill>": boards and bests are per skill). Title is the
    # headline: "FINISH!" for a race, "VICTORY!" in boss mode.
    ShowResults(Title:string, Medal:string, MedalColor:color, TimeLine:string, BestLine:string, RecordLine:message, AccuracyLine:string, BoardHead:string, Rows:[]message, OwnRow:int):void =
        ResultsTitle.SetTextColor(FnmUi(MedalColor))
        ResultsTitle.SetText(FnmText(Title))
        ResultsMedal.SetTextColor(FnmUi(MedalColor))
        SetOrCollapse(ResultsMedal, if (Medal = "") then "" else "{Medal} MEDAL")
        ShowMedalArt(Medal)
        ResultsTime.SetText(FnmText(TimeLine))
        ResultsBest.SetText(FnmText(BestLine))
        ResultsRecord.SetText(RecordLine)
        ResultsAccuracy.SetText(FnmText(AccuracyLine))
        ResultsBoardHead.SetText(FnmText(BoardHead))
        for (K -> Block : ResultsRows):
            if (Row := Rows[K]):
                Block.SetText(Row)
                Block.SetTextColor(FnmUi(if (K = OwnRow) then NamedColors.Orange else NamedColors.White))
                Block.SetVisibility(widget_visibility.Visible)
            else:
                Block.SetText(FnmText(""))
                Block.SetVisibility(widget_visibility.Collapsed)
        SetCountdown("")
        if (Results := MaybeResults?):
            Results.SetVisibility(widget_visibility.Visible)

    # The finish board's medal picture: the texture for ShowResults' Medal string (fnm_logic FnmMedal: "GOLD", "SILVER",
    # "BRONZE"). "" (boss mode may pass it) or any other word collapses the picture; the "<Medal> MEDAL" word stays beside it.
    ShowMedalArt(Medal:string):void =
        if (Medal = "GOLD"):
            MedalArt.SetImage(FNM_Art.T_fnm_medal_gold)
            MedalArt.SetVisibility(widget_visibility.Visible)
        else if (Medal = "SILVER"):
            MedalArt.SetImage(FNM_Art.T_fnm_medal_silver)
            MedalArt.SetVisibility(widget_visibility.Visible)
        else if (Medal = "BRONZE"):
            MedalArt.SetImage(FNM_Art.T_fnm_medal_bronze)
            MedalArt.SetVisibility(widget_visibility.Visible)
        else:
            MedalArt.SetVisibility(widget_visibility.Collapsed)

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

    # Grade step: one loud button per grade, labelled "Grade G", in the order given (the director's grade order). With
    # WithBoss, the BOSS BATTLE button and its caption come first (BOSS_MODE.md section 1); focus stays on the first
    # grade button.
    ShowGradeStep(Grades:[]string, WithBoss:logic):void =
        Labels := for (Grade : Grades) { "Grade {Grade}" }
        Indices := for (K -> Grade : Grades) { K }
        var Lead : []widget = array{}
        if (WithBoss?):
            BossButton := button_loud{DefaultText := FnmText("BOSS BATTLE")}
            BossButton.OnClick().Subscribe(fnm_pick_handler{Hud := Self, Kind := fnm_pick.Boss, Index := 0}.OnClick)
            set Lead = array{MakeCell(BossButton, "Every grade, every skill. Right answers NUKE the boss!")}
        PickerHeading.SetText(FnmText("PICK YOUR GRADE"))
        ShowPickerStep("Step 1 of 2", Labels, array{}, fnm_pick.Grade, Indices, false, Lead)

    # Skill step for Grade: one button per skill, its title on the button and its subtitle in small text under it
    # (button K picks cartridge Indices[K]), plus Back when WithBack. A stock button sets its own text size and grows
    # to fit its label, so "Title  -  Subtitle" labels in two columns ran past the edges of a 1080p screen (Aaron,
    # 2026-10-06: "words are cut off"); a text_block caption has a size we choose.
    ShowSkillStep(Grade:string, Titles:[]string, Subtitles:[]string, Indices:[]int, WithBack:logic):void =
        PickerHeading.SetText(FnmText("PICK YOUR SKILL"))
        ShowPickerStep(if (WithBack?) then "Grade {Grade}  -  step 2 of 2" else "Grade {Grade}", Titles, Subtitles, fnm_pick.Skill, Indices, WithBack, array{})

    # Replaces the picker's buttons with this step's (Captions[K], when present and not empty, goes under button K),
    # puts the picker on screen if it isn't, and focuses the first button (so a gamepad or keyboard can press it too).
    # Lead: widgets shown above the buttons (the BOSS BATTLE cell), full width.
    ShowPickerStep(Step:string, Labels:[]string, Captions:[]string, Kind:fnm_pick, Indices:[]int, WithBack:logic, Lead:[]widget):void =
        ClearPickerButtons()
        PickerStep.SetText(FnmText(Step))
        var Made : []widget = array{}
        for (Cell : Lead):
            PickerButtons.AddWidget(stack_box_slot{Widget := Cell, HorizontalAlignment := horizontal_alignment.Fill, Padding := margin{Top := 10.0, Bottom := 10.0}})
            set Made += array{Cell}
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
        Text := text_block{DefaultTextColor := NamedColors.White * FnmUiGain, DefaultTextSize := 22.0, DefaultJustification := text_justification.Center}
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

    # CLOSE (and NEW SKILL when WithChange) under the finish board. While they are up the mouse drives the buttons
    # and the player can't move; CLOSE hands control back. Again (boss mode's win board): PLAY AGAIN in CLOSE's place.
    ShowFinishButtons(WithChange:logic, Again:logic):void =
        ChangeSkillButton.SetVisibility(if (WithChange?) then widget_visibility.Visible else widget_visibility.Collapsed)
        CloseButton.SetVisibility(if (Again?) then widget_visibility.Collapsed else widget_visibility.Visible)
        AgainButton.SetVisibility(if (Again?) then widget_visibility.Visible else widget_visibility.Collapsed)
        if (not ChangeShown?, PlayerUI := MaybePlayerUI?, ChangeRoot := MaybeChangeRoot?):
            PlayerUI.AddWidget(ChangeRoot, player_ui_slot{ZOrder := 4, InputMode := ui_input_mode.All})
            set ChangeShown = true
            if (Again?) then PlayerUI.SetFocus(AgainButton) else PlayerUI.SetFocus(CloseButton)

    HideFinishButtons():void =
        if (ChangeShown?, PlayerUI := MaybePlayerUI?, ChangeRoot := MaybeChangeRoot?):
            PlayerUI.RemoveWidget(ChangeRoot)
        set ChangeShown = false
