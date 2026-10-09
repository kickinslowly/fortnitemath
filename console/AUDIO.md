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
| `finish` | the finish (`FinishSounds`, then +1.2 s steps) | Modes/Match/Match_Win_01_Cue | 3.93 |
| `new_record` / else `new_best` | island record / new personal best (only when there was an earlier best, like the HUD's NEW BEST!) | Music_Fantasy_Lrg_Victory_Stinger_02 / Music_Fantasy_Sml_Victory_Stinger_01 | 3.18 / 2.81 |
| `medal_gold/silver/bronze` | the medal | Music_Fantasy_Acceptance_Stinger_03 / Scoring_Point_Added / Match_Round_Change_01 | 3.00 / 2.46 / 2.31 |
| `perfect` | every answer first try | Music_Fantasy_Sml_Victory_Stinger_03 | 3.91 |
| `penalty_freeze` | ice cube appears (`Punish`) | Gadgets/Traps/Trap_IceBlock_Placed_cue | 1.89 |
| `penalty_spike` | spears burst up | Toys/Generic/DestructionObject_Impact_Cue | 2.84 |
| `penalty_mud` | sent back, slowed | Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_Stink_Cue | 2.82 |
| `penalty_dizzy` | sent back, before the spin | Gadgets/GhostMode/GhostMode_Enter_Cue | 2.04 |
| `penalty_blackout` | the screen goes black | Toys/ActionTrigger/ActionTrigger_PowerOff_Cue | 1.45 |
| `penalty_yeet` | the vent throws them | Toys/Cube/Cube_LaunchPlayer_Creative_Cue | 2.67 |
| `no_skip` | the skip guard sends a player back (`WatchSkip`) | Toys/ShootingTargets/Target_Error_Cue | 0.77 |
| `guards_up` | a station's guards switch on, for the players on it (`GuardLoop`) | Toys/ActionTrigger/ActionTrigger_PlayerSpotted_Cue | 1.22 |
| `welcome` | a player joins (`StartPlayer`) | Modes/Match/Match_Start_01_Cue | 3.83 |
| `choose` | the skill picker first opens for a player (`BeginPicking`; not with `DebugAutoPick`) | SkilledInteract_Open_Cue | 1.00 |
| `boss_fight` | a player enters the boss arena (`EnterArena`) | Gadgets/Radio/Stingers/Stinger_Threat_01 | 7.36 |
| `boss_hit` | a right pad hits the boss (`BossHit`) | Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_01 | 3.97 |
| `boss_dead` | the boss goes down, for every player in the arena (`BossDown`) | Gadgets/Radio/Stingers/BlackMonday/Stinger_BlackMonday_Win_01 | 6.14 |
| `music_t1` .. `music_t5` | music bed per station tier: on at GO, swapped when the tier changes, off at the finish and while the picker is up | Gadgets/Radio/Music_Loops: Music_StW_Ambient_Morning01, _Medium_Exploration01, _Low_Combat01, _High_Action01, _High_Combat01 | loop |

The Sound column is the stock sound. With `--announcer <voice>` the 23 `ANNOUNCER_CUES` carry a voice line instead
(next section).

Refused by island validation on 2026-10-07 (`UEFNValidation: Error: ... illegally references`, the session never
starts; `find_assets` lists them all the same): Rocket Racing (`/DelMarUI`, `/DelMarCosmetics`), `/FNGameplayCues`,
`/PoppySoap`, `/ShockwaveMace`, `/MudGameplay`, `/SpireSharedAssets`, `/CRD_HenchmanSpawner`, and `/Game` outside
`Sounds/Creative` (`Fort_Traps`, `Fort_GamePlay_Sounds`, `Fort_Music`, `Fort_Human_Barks`, `Athena`). The failed
start leaves an "Unable to Play" dialog that hangs every MCP call: close it with `WM_CLOSE` (PostMessage to its
window, found with the uefn-mcp skill's `gui_windows.ps1`), no focus needed. The errors are in
`%LOCALAPPDATA%/UnrealEditorFortnite/Saved/Logs/UnrealEditorFortnite.log`.

## Announcer

The voice pack (`tools/audio/announcer/<voice>/<cue>.wav`, 31 lines, `tools/audio/README.md`) is imported once per UEFN
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

**Boss hit timing (director):** `boss_hit` (the stock barrel explosion) at the pad, the counted line
`HitVoiceDelaySeconds` (0.9 s) later (`FnmHitCue`: 4..1 hits to go get their own line, any other count "Direct hit!",
nothing on the killing hit), then on the kill `boss_dead` and `boss_down` 1.0 s after it (`SoundAfter`, which plays even
though the player has just finished).

**Commands:**

    python tools/build_audio.py --announcer am_michael   # rebuild every player; ANNOUNCER_CUES get the voice
    python tools/build_audio.py                          # rebuild all stock again
    python tools/build_audio.py --list                   # source column: stock / announcer per device

A line that was not imported keeps its stock sound and the run says `NOT IMPORTED, stock kept: <cues>`. `--list` accepts
a voice wave only on an `ANNOUNCER_CUES` device for the same cue id (anything else is a mismatch).

**Import procedure (UEFN 42.30, worked first try 2026-10-07; again 2026-10-08 for the six boss-hit lines):** no
headless route exists (a wav dropped into `Content/` is never picked up; `AssetTools` has no import). Screenshots
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
7. A progress box ("Importing ...") runs ~10 s; no import-options dialog for wav. The drawer shows 31 Sound Wave items.
8. MCP: `AssetTools.find_assets` (folder `/<mount>/FNM_Audio`, class `/Script/Engine.SoundWave`) = 31, names = cue ids;
   `save_assets` on them.

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
