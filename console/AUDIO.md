# Sound layer

GOALS G6 item 1, the library-SFX half (2026-10-07). The announcer VO is a separate pack, imported later through the
UEFN GUI; it reuses these cue ids.

Runtime: `verse/fnm_audio.verse` (the `fnm_cue` enum, `FnmCueTag`, class `fnm_audio`) + one-line hooks in
`fnm_director.verse` (`Sound`, `SoundLater`, `SetMusic`, `Music`, `FinishSounds`). Devices: `tools/build_audio.py`
places one Creative **Audio Player** per wired cue, parked underground at `(-4000, -17000, -1500)` stepping +800 in X,
tagged `fnm_cue_<id>` (Verse tag, `fnm_tags.verse`) and `fnm_audio` (actor tag), labelled `FNM_Cue_<Id>`. The
director's `fnm_audio` finds them at OnBegin and logs `FNM: audio: N of M cues wired, missing: ...`; every play logs
`FNM: cue <id>` (`(not wired)` for a cue with no device), every stop `FNM: cue stop <id>`.

## Device options (every cue)
Set on the audio player ACTOR (its `creativeAudio` component holds only `stereoSpreadScaleFactor`), one property per
`set_properties` call, read back, then saved (the save refreshes the options cache the Creative panel shows,
`toyOptionsComponent.playerOptionData.propertyOverrides`; `--list` checks both).

| Option (property) | Value | Why |
|---|---|---|
| `audio` | the sound (SoundCue) | |
| `can Be Heard By` | Instigator Only | Verse `Play(Agent)` / `Stop(Agent)` only work in this mode; heard by that player alone |
| `play Location` | Instigating Player | at the player, wherever they are |
| `enable Spatialization` | false | flat 2D, no panning |
| `enable Volume Attenuation` | false | no distance fall-off |
| `volume` | 1.0 (music 0.5) | |
| `loopAudio` | false (music true) | |
| `restart Audio When Activated` | true | a repeat restarts the sound |
| `play On Hit` / `visible In Game` / `autoPlay - Gameplay` | false | only Verse plays them |

## Cues
Durations are the asset's `duration` (10000 = a looping cue). All sounds come from `/Game/Sounds/Creative` (the
Creative radio, toys and modes library) or `/CRD_SkilledInteractionDevice`: island validation refuses everything else
it was offered (below).

| Cue (`fnm_cue_*`) | Moment (director) | Sound | s |
|---|---|---|---|
| `countdown3/2/1` | each countdown beat (`Countdown`) | Toys/Floor_Siren/Timer_UI_Tick_Minigame_Cue | 0.51 |
| `go` | GO! (`Countdown`) | Toys/Floor_Siren/Timer_UI_Minigame_Go_Cue | 2.00 |
| `correct` | right door, first try (`HandleDoor`) | CRD_SkilledInteractionDevice SkilledInteract_Success_Cue | 1.20 |
| `correct_retry` | right door after a miss | SkilledInteract_Good_Cue | 0.30 |
| `wrong` | wrong door | Gadgets/Scoring/Scoring_Point_Subtracted_Cue | 2.28 |
| `door_open` | the barrier opens for the player (`AdvancePlayer`) | Gadgets/SlidingDoor/SlidingDoor_Open_Cue | 1.57 |
| `boost` | a speed boost starts, 0.4 s after the chime (`Boost`) | Gadgets/SpeedBoost/Trap_Speed_Alt_Increase_Cue | 3.50 |
| `streak2` .. `streak7` | first-try streak 2..7, 0.9 s after the chime; `streak7` again above 7 | Target_Impact_Success_2D, Target_Impact_Bullseye, Creative_PowerUp_Collect, CaptureDevice_Capture_Finish, Stinger_Success_02, Stinger_Success_03 | 0.54 .. 3.09 |
| `finish` | the finish (`FinishSounds`); after the race arena's kill at the podium arrival, `PodiumSeconds` later (G9 D2) | Modes/Match/Match_Win_01_Cue | 3.93 |
| `new_record` / else `new_best` | today's record (the session's best for the skill; the HUD says "Today's record" since G9, but the stock voice line still says "NEW ISLAND RECORD!") / new personal best (only when there was an earlier best, like the HUD's NEW BEST!) | Music_Fantasy_Lrg_Victory_Stinger_02 / Music_Fantasy_Sml_Victory_Stinger_01 | 3.18 / 2.81 |
| `medal_gold/silver/bronze` | the medal | Music_Fantasy_Acceptance_Stinger_03 / Scoring_Point_Added / Match_Round_Change_01 | 3.00 / 2.46 / 2.31 |
| `perfect` | every answer first try | Music_Fantasy_Sml_Victory_Stinger_03 | 3.91 |
| `penalty_freeze` | ice cube appears (`Punish`) | Gadgets/Traps/Trap_IceBlock_Placed_cue | 1.89 |
| `penalty_spike` | spears burst up | Toys/Generic/DestructionObject_Impact_Cue | 2.84 |
| `penalty_mud` | stuck in the mud (then the retry spot, slowed) | Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_Stink_Cue | 2.82 |
| `penalty_dizzy` | before the spin (then the retry spot) | Gadgets/GhostMode/GhostMode_Enter_Cue | 2.04 |
| `penalty_blackout` | the screen goes black | Toys/ActionTrigger/ActionTrigger_PowerOff_Cue | 1.45 |
| `penalty_yeet` | the vent throws them | Toys/Cube/Cube_LaunchPlayer_Creative_Cue | 2.67 |
| `no_skip` | the skip guard sends a player back (`WatchSkip`) | Toys/ShootingTargets/Target_Error_Cue | 0.77 |
| `guards_up` | a station's guards switch on, for the players on it (`GuardLoop`) | Toys/ActionTrigger/ActionTrigger_PlayerSpotted_Cue | 1.22 |
| `welcome` | a player joins (`StartPlayer`) | Modes/Match/Match_Start_01_Cue | 3.83 |
| `choose` | the skill picker first opens for a player, 2.0 s after `welcome` (`ChooseLater`, G9: the two voice lines overlapped; not with `DebugAutoPick`) | SkilledInteract_Open_Cue | 1.00 |
| `boss_fight` | a player walks into the boss arena's hall (`ArenaArrival`, G9; it fired at the station-10 door, 44 m early) | Gadgets/Radio/Stingers/Stinger_Threat_01 | 7.36 |
| `boss_hit` | a right pad hits the boss (`BossHit`) | Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_01 | 3.97 |
| `boss_dead` | the boss goes down, for every player in the arena (`BossDown`) | Gadgets/Radio/Stingers/BlackMonday/Stinger_BlackMonday_Win_01 | 6.14 |
| `bm_start` | Boss Battle starts, level-1 summon (`Summon(1)`), as `boss_fight` | Gadgets/Radio/Stingers/Stinger_Threat_01 | 7.36 |
| `bm_level2` .. `bm_level5` | level 2..5 summon (`Summon(L)`) | Modes/Match/Match_Round_Change_01 | 2.31 |
| `bm_boss_l1` .. `bm_boss_l5` | the boss's line `RoarToLineSeconds` (0.9) after the summon's roar (`Summon(L)`, +2.35 s; G9 D2) | none: voice only (`BOSS_CUES`) | - |
| `bm_boss_wrong` | wrong pad: 0.9 s after the crowd's aww, with the titan's scream (`PenaltyLines` -> `fnm_boss_mode.Taunt`; G9 D2) | none: voice only | - |
| `bm_boss_hit` | right pad, +0.4 s, not on the killing hit (`OnBmPad`, correct) | none: voice only | - |
| `bm_boss_dead` | final kill, +0.5 s (`OnBmPad`, boss dead) | none: voice only | - |
| `bm_nuke` | right pad, at once (`OnBmPad`) | Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_01 | 3.97 |
| `bm_mega_nuke` | right pad, +0.9 s when Left is above 4 or 0 (`OnBmPad`; else the `hits_left` line) | none: voice only (announcer) | - |
| `bm_level_clear` | level clear | Gadgets/Radio/Stingers/Stinger_Success_03 | 3.09 |
| `bm_victory` | victory (`Victory`) | Modes/Match/Match_Win_01_Cue | 3.93 |
| `bm_gates` | the gates open at a summon (`Summon(L)`, 0.9 s after the boss's line, +3.25 s; G9 D2) | Gadgets/SlidingDoor/SlidingDoor_Open_Cue | 1.57 |
| `bm_weapon` | a weapon is granted on a perch (`OnBmPerch`) | Toys/PowerUp/Creative_PowerUp_Collect_Cue | as `streak4` |
| `music_t1` .. `music_t5` | music bed per station tier: on at GO, swapped when the tier changes, off at the finish and while the picker is up | Gadgets/Radio/Music_Loops: Music_StW_Ambient_Morning01, _Medium_Exploration01, _Low_Combat01, _High_Action01, _High_Combat01 | loop |

The Sound column is the stock sound. With `--announcer <voice>` the 31 `ANNOUNCER_CUES` carry a voice line instead,
and with `--boss-voice <voice>` the 8 `BOSS_CUES` (`bm_boss_*`) carry the boss's (next section). The 19 `bm_*` rows
are Boss Battle mode (BOSS_MODE.md section 10); their stock paths reuse sounds that already passed validation under other
cue ids, except `bm_gates` / `bm_weapon` / `bm_nuke` / `bm_level2..5`, which reuse the paths of `door_open` / `streak4` /
`boss_hit` / `medal_bronze` (not yet re-probed as new cues).

Refused by island validation on 2026-10-07 (`UEFNValidation: Error: ... illegally references`, the session never
starts; `find_assets` lists them all the same): Rocket Racing (`/DelMarUI`, `/DelMarCosmetics`), `/FNGameplayCues`,
`/PoppySoap`, `/ShockwaveMace`, `/MudGameplay`, `/SpireSharedAssets`, `/CRD_HenchmanSpawner`, and `/Game` outside
`Sounds/Creative` (`Fort_Traps`, `Fort_GamePlay_Sounds`, `Fort_Music`, `Fort_Human_Barks`, `Athena`). The failed
start leaves an "Unable to Play" dialog that hangs every MCP call: close it with `WM_CLOSE` (PostMessage to its
window, found with the uefn-mcp skill's `gui_windows.ps1`), no focus needed. The errors are in
`%LOCALAPPDATA%/UnrealEditorFortnite/Saved/Logs/UnrealEditorFortnite.log`.

## Announcer

The voice pack (`tools/audio/announcer/<voice>/<cue>.wav`, 53 lines, `tools/audio/README.md`) is imported once per UEFN
project through the GUI, then `tools/build_audio.py --announcer <voice>` puts it on the devices. Live since 2026-10-07
with `am_michael`.

**Asset path:** `/<mount>/FNM_Audio/<voice>/<cue>.<cue>` (SoundWave; mount = the project's plugin id from VerseToolset
`ListFiles("")`, e.g. `/c498eed2-96c5-4757-91a1-edb374b16d67/FNM_Audio/am_michael/streak2.streak2`). Island validation
accepts the project's own SoundWaves: the session started with all 23 swapped (2026-10-07).

**Which cues carry the voice:** `ANNOUNCER_CUES` at the top of `tools/build_audio.py`: `go`, `streak2`..`streak7`,
`perfect`, `new_best`, `new_record`, `medal_gold/silver/bronze`, the six `penalty_*`, `no_skip`, `guards_up`, `welcome`,
`choose`, and the boss-hit lines `direct_hit`, `hits_left4..1` ("Direct hit! Three to go!") and `boss_down` (2026-10-08;
these six have NO stock stand-in: an announcer-only cue is placed only once its wave is imported, else it logs
"(not wired)"; am_michael's six were imported and wired the same evening, 46 of 46 cues). Stock (the table above): the countdown ticks, `correct` / `correct_retry`, `wrong`, `door_open`, `boost`,
`finish`, the music beds and the three boss cues. The pack's `countdown1..3`, `correct`, `wrong`, `finish`, `boss_fight`
and `lifeline` lines are imported but unused.

**Boss voice (Boss Battle mode, 2026-10-09):** the eight `bm_boss_*` lines ("You dare challenge ME?!" ... "NOOOOO!") are
a different character: they use the `boss` mastering profile in `tools/make_announcer.py` (the normal chain with a further
18 % pitch drop, a tanh soft clip, a second compressor and the `big` echo; `tools/audio/README.md` "Mastering") and are
wired by their own flag, `--boss-voice`, onto `BOSS_CUES`. The recommended boss voice is **am_onyx** (deepest of the three;
all three are rendered). The eight announcer-style mode lines (`bm_start`, `bm_level2..5`, `bm_mega_nuke`,
`bm_level_clear`, `bm_victory`) ride `ANNOUNCER_CUES` as usual (am_michael). Import both voices' folders the same way
(`/<mount>/FNM_Audio/am_michael/` and `/<mount>/FNM_Audio/am_onyx/`; the import steps below are per folder, 16 new waves
in each, or all 53 again), then:

    python tools/build_audio.py --announcer am_michael --boss-voice am_onyx

A boss line whose wave is not imported has no stock sound: the run says `NOT IMPORTED, not wired: ...` and the cue logs
`(not wired)` in play. `--list` accepts a boss wave only on a `BOSS_CUES` device for the same cue id (source column `boss`).
To pick another boss voice, pass it instead of `am_onyx` (`--boss-voice bm_george`) after importing that folder.

**Boss hit timing (director):** `boss_hit` (the stock barrel explosion) at the pad, the counted line
`HitVoiceDelaySeconds` (0.9 s) later (`FnmHitCue`: 4..1 hits to go get their own line, any other count "Direct hit!",
nothing on the killing hit), then on the kill `boss_dead` and `boss_down` 1.0 s after it (`SoundAfter`, which plays even
though the player has just finished).

**Commands:**

    python tools/build_audio.py --announcer am_michael   # rebuild every player; ANNOUNCER_CUES get the voice
    python tools/build_audio.py --announcer am_michael --boss-voice am_onyx   # ... and BOSS_CUES get the boss voice
    python tools/build_audio.py                          # rebuild all stock again
    python tools/build_audio.py --list                   # source column: stock / announcer per device

A line that was not imported keeps its stock sound and the run says `NOT IMPORTED, stock kept: <cues>`. `--list` accepts
a voice wave only on an `ANNOUNCER_CUES` device for the same cue id (anything else is a mismatch).

**Import procedure (UEFN 42.30, worked first try 2026-10-07; again 2026-10-08 for the six boss-hit lines, and 2026-10-13 for
the Mint waves and the re-rendered `welcome`):** no headless route exists (a wav dropped into `Content/` is never picked up, even
with the editor's auto-import settings switched on, see "Mint music and SFX"; `AssetTools` has no import). Screenshots
`imp_*.png` in `%TEMP%`.
0. If a play session is running, MINIMIZE the Fortnite client first (`ShowWindow(h, 6)`): a foreground client clips the
   cursor to its own window, so `SetCursorPos` to the left monitor lands at x 320 inside the game and every "UEFN click"
   fires the pistol instead (2026-10-08: three clicks did nothing until the client was minimized). Verify with
   `GetCursorPos` after a `SetCursorPos(-1845, 1016)`.
1. Copy the voice's wavs to a short path (`%TEMP%\fnm_vo`).
2. MCP: `AssetTools.create_folder /<mount>/FNM_Audio/<voice>`, then `EditorAppToolset.SetContentBrowserPath` to it.
3. GUI (`~/.claude/skills/uefn-mcp/scripts/gui_act.ps1`; on this PC UEFN is maximized on the LEFT monitor, x -1920..0,
   so capture that monitor, not the primary): click **Content Drawer** in the status bar (bottom left, screen
   (-1845, 1016)). The first click only focuses UEFN; the second opens the drawer. The drawer closes when UEFN loses focus.
4. Click **Import** in the drawer's toolbar (screen (-1539, 679)): a Windows "Import" file dialog opens top-left.
5. Click the File name box ((-1455, 472)), type the folder path, Enter (the dialog navigates there).
6. Click the first file ((-1595, 160)), `Ctrl+A` (the File name box fills with the quoted list), click **Open**
   ((-1129, 502)).
7. A progress box ("Importing ...") runs ~10 s; no import-options dialog for wav. The drawer shows one Sound Wave item per wav in the folder (37 per voice before Boss Battle mode, 53 after).
8. MCP: `AssetTools.find_assets` (folder `/<mount>/FNM_Audio`, class `/Script/Engine.SoundWave`) = the file count, names = cue ids;
   `save_assets` on them.

## Mint music and SFX (G9, 2026-10-13)

Bought on Aaron's Mint account (project "First Project"; every asset id and the one-line ask for each is in `SOURCES` at the top
of `tools/make_mint_audio.py`). **Aaron's ear has not judged any of it yet.** `tools/audio/mint/LISTEN.md` is the sheet to listen
with: which take is in, which is the alt, the measured numbers, and why.

**Files.** `art/audio/mint/<stem>.mp3` (tracked: the bought originals, 192 kbps, 60 s / 90 s beds) ->
`python tools/make_mint_audio.py` -> `tools/audio/mint/<cue>.wav` (44.1 kHz, 16-bit, stereo; git-ignored, rebuilt byte for
byte; the other take of a pair is `<cue>_alt.wav`), `LISTEN.md`, `vocal_check.json` (`vocal_check.py`, Whisper small.en).
`--stage` / `--stage-only` copy the wavs that get imported to `%TEMP%\fnm_mint`; `--pick music_t3=b` forces a take;
`--bad-loops music_t3_b` is the disproof (deliberately bad loop points, scored).

**How a bed becomes a loop.** The tempo comes from the audio (autocorrelation of the onset envelope near the ask, a comb filter to
0.01 BPM), not from the prompt: every 120 BPM ask came back 120.00 except `music_t4_a`, which is 144 BPM. The loop is N bars
(a multiple of 4) from a bar line; its true repeat length is found by cross-correlating the amplitude envelope of the first bar
with the audio N bars on (so L is the music's own repeat, e.g. 55.9999 s, not 28 x 2.0 s on trust). The first bar is replaced by an
equal-power crossfade of the audio that follows the loop end (out) into the audio at the start (in), so the wrap is continuous
by construction. A candidate is rejected when a half-second of its body sits 15 dB under the median (a gap, an intro, a fade-out;
`music_t1_a` has a 1 s rest every 4 s for its first 16 s, `music_t2_b` / `music_t4_b` / `music_t1_a` fade out in their last
seconds) or a bar strays more than 6 dB from the median. The take of a tier is the one with the better numbers (envelope
repeatability, timbre match of the two crossfaded bars, seam against the music's own bar lines, level steadiness, tempo near the
ask, no speech); the numbers and the reason per tier are in `LISTEN.md`.
What the numbers prove: the wrap is continuous and no rougher than the music's own bar lines; the beds sit at -18 LUFS integrated
(BS.1770-4, checked against ffmpeg `ebur128` in `tests/test_mint_audio.py`) and <= -1 dBTP; one-shots at -16 LUFS short-term,
leading silence under 10 ms. What they do not prove: that a loop sounds right, that two bars with the same rhythm share a chord,
or anything about the choir and guitar in `music_boss_*` (Whisper only says it heard no speech). A through-composed bed
(`music_menu`, `music_t5_b`) has no loop that is truly seamless: the crossfade morphs between unlike bars. The loops are
short where the numbers preferred it (t3 and t4 16 s, the menu 17 s, t2 24 s, boss 34 s, t5 48 s, t1 56 s): the other take (and
`--pick`) is the way to a longer one, e.g. `music_t3_a` is 40 s. About 80 MB of wav in total; the island's memory calculation has
not been run with them.

**Mix.** Beds: -18 LUFS at device volume 0.5 (about -24 in play), under the voice lines (announcer -13 LUFS at volume 2.5 = `VO_VOLUME`).
One-shots: -16 LUFS short-term at volume 1.0. A Mint wave is never `is_vo` (the folder name `mint` is reserved), so it never gets
the voice volume.

**Cues and moments** (`MINT_CUES` in `tools/build_audio.py`; waves in `/<mount>/FNM_Audio/mint/<cue>.<cue>`):

| Cue | Source take | Moment | Stock until imported |
|---|---|---|---|
| `music_t1` .. `music_t5` | tier beds | the tier's bed (on at GO, swapped on a tier change) | the Save the World loops |
| `finish` | victory fanfare | the finish (`FinishSounds`); after the race arena's kill, at the podium arrival with `crowd_cheer`. 5.46 s against the stock 3.93 s: a quiet 1.75 s lead-in and a loud body to ~4.25 s, so the record / best, medal and perfect lines start `FinishVoiceSeconds` (4.2) after it, then `FinishCueGapSeconds` (1.6) apart (G9 D2; at 1.6 the first line sat on the body) | Match_Win_01 |
| `door_open` | portal whoosh | the barrier opens (`AdvancePlayer`) | SlidingDoor_Open |
| `volt_yay`, `volt_hmm` | Volt chirp (0.38 s of sound in the 1.2 s Mint file) / warble | Volt reaction cards (`volt_hmm` at the retry spot; `volt_yay` has no call site: see below) | none: not wired |
| `music_boss` | boss bed | the race arena from its stage on (`Music`: `AtArena`, the bed swaps at the station-10 door) and all of Boss Battle mode (`fnm_boss_mode.Start`, `Summon`; it played the tier beds by level until G9 D2) | none |
| `music_menu` | lobby loop | the grade picker (`BeginPicking`, only when the picker is shown: not under `DebugAutoPick` / `DebugAutoBoss`); off at the run's countdown (`Countdown`), swapped for the boss bed by BOSS BATTLE | none |
| `titan_roar` | roar | with the titan's jump-slam, as the slam lands (`fnm_titan.SlamLandsSeconds` 1.15 s into the clip): the race arena when a player walks into the hall (`ArenaArrival`, 1.15 s after `boss_fight`), boss mode's level start (`Summon`, +1.45 s: level line 0, roar 1.45, boss line 2.35, gates 3.25) | none |
| `volt_oops` | "uh-oh" | no call site: see below | none |
| `crowd_cheer` | cheer | the podium arrival after the race arena's kill (`PodiumLater`), with the finish fanfare; not on the kill (`boss_dead` + `boss_down` fill it) | none |
| `crowd_aww` | aww | a wrong pad in an arena (the race's boss arena, Boss Battle mode): 0.9 s after the penalty's voice line (`PenaltyLines`, `CrowdAfterVoiceSeconds`); in boss mode the boss's taunt and the titan's scream follow 0.9 s later. Race stations: no aww | none |

**Timelines (G9 D2), against the mix rules** (no voice on the same instant as a stinger: 0.9 s apart; at most two sounds starting
in any 1 s window; nothing new on a kill). `tests/test_mix_rules.py` reads these out of the Verse.
- Race arena walk-in: `boss_fight` 0, the jump-slam 0, `titan_roar` 1.15.
- Wrong pad, race arena: `wrong` 0 (and the titan's stomp), the penalty's line 0.9 (the yeet's 1.4), `crowd_aww` 1.8 (2.3).
  Boss mode: the same, then `bm_boss_wrong` with the titan's scream 2.7 (3.2). Until G9 D2 the taunt came at a fixed 2.5 s
  after the buzzer and the titan stomped at once.
- Race kill: `boss_dead` 0, `boss_down` 1.0, podium arrival 3.0: `crowd_cheer` + `finish` together (two non-voice sounds meant
  to start together), then today's record / new best 7.2, the medal 8.8, PERFECT 10.4 (the lines are dropped if a new run or a
  skill change starts first). The FINISH board is up from the kill to 10 s.
- Boss mode summon (Scale 1): the level line 0, the jump-slam 0.3 (or once the last level's fall has played out: everything
  after it moves by `fnm_titan.ReadyIn`, up to ~1.7 s at levels 2-5), `titan_roar` 1.45, the boss's line 2.35, `bm_gates` 3.25,
  the chests 4.25, the banner down 5.05 (the old order: boss line 1.5, gates 2.5).

**`volt_yay` and `volt_oops` stay unused** (no free window): Volt's cards show at the answer instants, which already carry the
chime / buzzer at 0 and a voice line at 0.9 (streak, hit count, penalty), the boost at 0.4, and on a wrong door `volt_hmm` at
the retry spot. A chirp at ~1.8 s after a right door with no streak line would pass the rules by the letter but makes three
sounds per door. Their devices are placed (`--mint`) so a call site needs only Verse.

**Seen in play (G9 D2, 2026-10-13, editor log; nobody listened):** `audio: 73 of 73 cues wired, missing: none` and no
`(not wired)` line in either session. Race (`DebugAutoPick 7` + `DebugPickerSeconds 25` + `DebugAutoRightAnswers` +
`DebugAutoWrongAnswers 8`): `cue music_menu` with `picker shown`, `cue stop music_menu` at the pick; `cue music_boss` at `arena stage
reached`, stopped at the kill; `cue boss_fight` + `titan jump-slam`, then `cue titan_roar`; a wrong pad (YEET): `cue wrong`,
`cue penalty_yeet`, `cue crowd_aww`; the kill: `boss_dead`, `boss_down`, then at `to the podium` `cue finish` and `cue crowd_cheer` in the
same millisecond, `new_record` 4.2 s and the medal 1.6 s later. Boss mode (`DebugAutoBoss` + `DebugAutoRightAnswers` +
`DebugAutoWrongAnswers 2`, VICTORY): `cue music_boss` at the start, no tier bed; every summon `bm_levelN` / `bm_start`, `titan_roar`,
`bm_boss_lN`, `bm_gates` in that order; both wrong pads `wrong`, the penalty line, `crowd_aww`, `bm_boss_wrong` + `titan scream`.
The editor log's stamps jitter: `Sleep(0.9)` gaps read 0.42 to 1.09 s, so the log proves the order, and `tests/test_mix_rules.py`
the gaps.

Boss mode's own victory and level clear still stack voices on the kill (not changed here): at the killing pad `bm_nuke` 0,
`bm_victory` (voice) 0, `bm_boss_dead` 0.5, the MEGA NUKE line 0.9 (`FnmBmHitVoice(0)`), the medal 1.6; a level clear has
`bm_nuke` 0, `bm_level_clear` (voice) 0 and MEGA NUKE 0.9.

The six rows were `PENDING_CUES` in `tools/build_audio.py` until G9 D2 (no enum id, tag class or call site); now they are in `CUES`
and `PENDING_CUES` is empty. A future cue with no Verse side waits there the same way: `tests/test_audio_cues.py` asserts
`list(CUES)` equals the Verse enum. `build()` places a cue only when the project's Verse root declares its `fnm_cue_<id>` tag class
(VerseToolset `Grep`), because a device cannot be tagged with a class the project has not compiled (2026-10-13:
`set_properties` answered "_Verse.fnm_cue_volt_yay is not valid Class for property 'InternalTag'" and the run died with
a half-built device and nothing saved; now it is caught, the device removed and the cue skipped with a message). `volt_yay` /
`volt_hmm` are declared in the repo's `fnm_tags.verse` but were not compiled until the next sync + BuildAll, so they wait:
rerun the `--mint` command after that compile.

**Wire them** (after the waves are imported; the full live command):

    python tools/build_audio.py --announcer am_michael --boss-voice am_onyx --mint
    python tools/build_audio.py --list            # source column: stock / announcer / boss / mint

A cue whose wave is missing keeps its stock sound and the run says `NOT IMPORTED, stock kept: ...`; a Mint-only cue says
`not wired: ...` and is a logged no-op in play. `--list` accepts a Mint wave only on a `MINT_CUES` device for the same cue id.

**Import route (2026-10-13): the GUI, same as the announcer; headless does not work.** Tried under the UEFN lock: the editor
settings object `/Script/UnrealEd.Default__EditorLoadingSavingSettings` reads and writes through ObjectTools `get_properties` /
`set_properties` (found `bMonitorContentDirectories` false, `bAutoCreateAssets` false, `bPromptBeforeAutoImporting` true,
`autoReimportDirectorySettings` one rule, `/Game/`). With monitoring and auto-create on, the prompt off and a rule for the
project's Content (the virtual path `/<mount>/`; then the absolute `.../FortniteMath/Content/` with that mount point),
`Content/FNM_Audio/mint/volt_yay.wav` was not imported after 100 s / 75 s, and the editor log never mentions the monitor. All
four properties were put back and read back identical. So the 15 waves went in through the Import dialog:

1. `python tools/make_mint_audio.py --stage-only` (the wavs to `%TEMP%nm_mint`); MCP `AssetTools create_folder
   /<mount>/FNM_Audio/mint`, `EditorAppToolset SetContentBrowserPath` to it.
2. Minimize the Fortnite client (`ShowWindow(h, 6)`, no focus needed). UEFN was a 1292x766 window on the PRIMARY monitor this time
   (the 2026-10-08 coordinates were stale): `ShowWindow` minimize + restore brings it to the front; a floating Message Log hid
   the Content Drawer, closed with `WM_CLOSE`. Screenshot every step (`PrintWindow` is not enough for dialogs: a virtual-screen
   `CopyFromScreen`, then crop and Read).
3. Click the drawer's **Import** button (window-relative (390, 498)), a Windows "Import" dialog opens. Type the folder path +
   Enter, then the quoted file list (`"a.wav" "b.wav" ...`) + Enter: no Ctrl+A needed. A progress bar runs about 30 s for 15 waves.
4. `AssetTools find_assets` (folder `/<mount>/FNM_Audio/mint`, class `/Script/Engine.SoundWave`) lists 15; every asset's
   `duration` / `sampleRate` / `numChannels` matches its wav; `save_assets`.

**Replacing a wave in place** (done for `am_michael/welcome`, re-rendered "Welcome to Doors of Doom!"): the same dialog into the
voice's folder. UEFN asks "Do you want to overwrite the existing asset?" (Yes) and then "overwrite its existing settings?"
(No). The asset is replaced in place: `duration` 1.860 s -> 1.901 s, the `FNM_Cue_Welcome` device still points at the same
path, nothing nulled. Never delete the asset first (that nulls the device's reference).


## Rewire a cue
1. `python tools/build_audio.py --probe Name1,Name2` lists matching SoundCues / SoundWaves with class and duration.
   Pick from `/Game/Sounds/Creative` (one-shot ≤ 2.5 s, stinger ≤ 4 s).
2. Change its row in `CUES` (`tools/build_audio.py`; the asset path's object name is case-sensitive, `--list` flags
   a mismatch).
3. `python tools/build_audio.py` (deletes and re-places every player, reads each option back, saves), then
   `python tools/build_audio.py --list` (0 mismatches).
4. A session start is the only validation check: `tools/playtest.py --until "audio:"` and read the log.

A new cue id: add the enum member (`fnm_audio.verse`: `fnm_cue`, `FnmCues`, `FnmCueIds`), its tag class and
`FnmCueTags` entry (`fnm_tags.verse`), the `CUES` row, then `fnm sync starter` + BuildAll.
`tests/test_audio_cues.py` checks the four lists agree.

## Hear it (ear proxy)
`tools/hear.py` records the default speaker's WASAPI loopback and lists sound onsets (50 ms RMS rising ≥ 12 dB over
the previous 500 ms), then matches the run's `FNM: cue` lines:

    python tools/hear.py --seconds 300 --out %TEMP%/hear.wav      # in the background (run_in_background)
    python tools/playtest.py --until "finished run 2" > run.txt   # in the foreground
    python tools/hear.py --analyze --out %TEMP%/hear.wav --log run.txt

Editor-log stamps are UTC to the millisecond; the recording's UTC start is saved beside the WAV. A silent recording
prints the default speaker's audio sessions (`tools/audio_sessions.ps1`): on 2026-10-07 every recording was flat because
`FortniteClient-Win64-Shipping` and `UnrealEditorFortnite-Win64-Shipping` were **muted in the Windows volume mixer**
(the client did render to the default Realtek speakers, focused or not). The mute COMES BACK on a session relaunch,
so run `python tools/audio_meter.py 230 %TEMP%/meter.csv unmute` in the background too: it keeps the client session unmuted
at 0.25 and logs its own peak meter (2026-10-07: 44 of 59 cue lines matched a loopback onset within 0.5 s, session peak 0.34).
Re-mute afterwards if Aaron had it muted. Also:
the player's own Fortnite Music slider is 0 on this PC, so the music beds are inaudible to that account even unmuted.

## Did the voice play? (2026-10-07)
Aaron heard the stock sounds and no announcer. `tools/hear_voice.py` (a matched filter of each voice wav against a
`hear.py` recording at its cue time) showed why: GO 0.96 and WELCOME 0.77 in the clear, the penalty lines 0.17-0.32
(noise floor 0.08-0.11) because they fired on the same instant as the 2.3 s wrong buzzer and the effect's own sound.
Now: announcer devices at `VO_VOLUME` 2.5 (the volume property takes values past 1), the penalty line
`PenaltyVoiceDelaySeconds` (0.9) after the buzzer, `wrong` = the 0.77 s Target_Error, no boost whoosh on a streak,
finish gap 1.6 s. Measured after: penalty_freeze 0.94, penalty_yeet 0.90. Rig rules: record with the client FOCUSED
(Fortnite mutes itself in the background: every background recording was digital silence), and after a BuildAll or a
device rebuild with a live session wait for the push to finish cooking (`playtest.wait_for_push`) before a relaunch or a
StopSession: a relaunch inside that window started from a stale snapshot (16 of 40 cue devices, ship Verse).
