# FNM console — UEFN wiring guide

The Verse runtime that plays the inserted cartridges on a linear course of question stations; each player picks
their own skill on an in-game menu. Contract: `PROTOCOL.md` §6 / §6a / §6b. Compiles clean on UEFN 42.30 (first compile 2026-10-03; the checklist at the
bottom is kept for history).

## Files

| File | What it is |
|---|---|
| `verse/fnm_cartridge.verse` | Protocol types (§8). Fixed. |
| `verse/fnm_logic.verse` | Pure logic: station tier, per-tier pools, draw without replacement, choice letters, accuracy line, race clock text, medal. |
| `verse/fnm_ui.verse` | Per-player HUD (`fnm_hud`): question panel (with the big streak / boost line), verdict / countdown text, clock + target panel, the finish board, blackout screen; the skill picker (its own root, real Verse buttons, `InputMode All` only while shown) and the CHANGE SKILL button under the finish board. Clicks go to the director through `fnm_picker_listener`. |
| `verse/fnm_director.verse` | The device: `fnm_director`, `fnm_station`, per-player state (including the player's own cartridge, tier pools and decks), the picker flow (`BeginPicking` → grade → skill → `Pick` → countdown; `ChangeSkill` from the finish board), doors, penalties, race layer, sliders. |
| `verse/fnm_tags.verse` | Verse tags the director finds the course, rigs and effect devices by. |
| `verse/fnm_rig.verse` | Penalty rigs: parked props/devices moved onto a punished player. |
| `verse/fnm_penalties.verse` | The penalty enum and labels (catalog: `PENALTIES.md`). |
| `verse/fnm_audio.verse` | Sound layer: the `fnm_cue` enum, `FnmCueTag`, and `fnm_audio` (finds one audio player per cue by tag, `Play`/`Stop` per player, music bed per tier). Cue table: `AUDIO.md`. |
| `maps/<map-id>/generated/fnm_active_cartridge.verse` | The cartridge slot: one `FnmCartridge_<id>()` per inserted cartridge plus `FnmCartridges():[]fnm_cartridge` in picker order (PROTOCOL §7). Written by `fnm insert`. |

## 1. Put the Verse files in the UEFN project

All Verse files go **flat, in one folder** — the project's Verse root, `<project>\Content\` (verified on UEFN 42.30).

- `fnm sync <map-id>` does this: copies `console/verse/*.verse` plus
  `maps/<map-id>/generated/fnm_active_cartridge.verse` into the project's Verse folder (needs
  `uefn_project` set in `maps/<map-id>/map.json`).
- Keep them in the **same folder**. In Verse every folder is a module; putting the cartridge file in a
  `generated/` subfolder would make it a separate module and the types would need `<public>` and a
  `using` (PROTOCOL O3). Flat avoids that.

Then **Verse → Build Verse Code** (Ctrl+Shift+B). A clean build makes `fnm_director` appear in the
Content Browser under the project's *CreativeDevices* folder.

Swapping cartridges later: `fnm insert <cartridge>` → `fnm sync <map-id>` → Build Verse Code → push
changes. No device or level edits.

## 2. Build the course

The fast path is `python tools/build_course.py [--stations 10] [--doors 4] [--hall 3000]` with UEFN open: it
builds every hallway, door, vestibule, barrier, sign and teleporter, tags them, and places the director
(idempotent: it first removes every actor tagged `fnm_course`). Once per UEFN project, before the first build:
`python tools/import_art.py` (the verdict check/cross textures the HUD needs to compile, and the wall colours).
Penalty props and effect devices: `python tools/build_rigs.py`. Sound: `python tools/build_audio.py` (one tagged audio
player per cue; `AUDIO.md`).
Layout: `maps/starter/LAYOUT.md`. To build by hand instead, per station:

| Device | Count | Settings |
|---|---|---|
| **Trigger** (`PID_Device_Trigger`, not the legacy one) | 2–4, one per door, in the vestibule just past the door | *Visible in Game* off, *Reset Delay* 0, unlimited triggers, vehicles/water/physics off |
| **Barrier** (`PID_Device_Barrier`), optional | one per door, across the far end of its vestibule | *Invisible To Ignored Players* on, *Collide With Camera* off. Without barriers a right answer teleports to the next entry |
| **Teleporter** — station entry | 1 | *Teleporter Group* / *Target Group* = None (it is only a destination) |
| Door labels A–D | per door | Static billboards. A is on the player's LEFT when facing the doors. |

Plus one **finish** teleporter, and **Player Spawn Pads** in station 1.

## 3. Tag the devices (no wiring)

The director finds the course at runtime by Verse tags (`verse/fnm_tags.verse`). In each device's Details
panel add a **Verse Tag Markup** component and set its tags:

| Device | Tags |
|---|---|
| Station N entry teleporter | `fnm_station_NN` + `fnm_entry` |
| Station N door trigger | `fnm_station_NN` + `fnm_door_a` / `_b` / `_c` / `_d` |
| Station N door barrier | the same two tags as that door's trigger |
| Finish teleporter | `fnm_finish` |
| Audio player per cue (`tools/build_audio.py`, `AUDIO.md`) | `fnm_cue_<id>`: `fnm_cue_countdown3` .. `fnm_cue_music_t5`, one per `fnm_cue` member |

Stations are read 01, 02, ... until the first number with no entry teleporter (max 20). Then place one
`fnm_director` anywhere. Optional settings: `DifficultyOverrides` (percent per station, -1 = automatic,
spread evenly from tier 1 at the first station to tier T at the last), feedback/notice seconds, End Game device.

Why tags: in UEFN 42.30 a Verse device's @editable `trigger_device` / `teleporter_device` arrays refused
these devices from both MCP and the Details panel ("is not valid trigger_device"); tags set cleanly.

Automatic difficulty (PROTOCOL §6, T = 5 tiers): 10 stations → tiers 1,1,2,2,3,3,4,4,5,5; 5 → 1..5;
3 → 1,3,5.

## 4. What players see

On joining, the player is held still at station 1 under a centre-screen menu, CHOOSE YOUR SKILL: a button per
grade, then a button per skill of that grade (`Title  -  Subtitle`, with Back). One grade skips the grade step; one
cartridge skips the menu. Picking starts the countdown. The finish board has a CHANGE SKILL button (shown when the
slot holds more than one skill): it cancels the auto-restart and opens the menu again. Personal bests, the
session board and the island record are kept per skill (the board is headed with the skill's title); timings of
different skills are never compared. Test hook: `DebugAutoPick` (−1 = menu; N = pick
`Cartridges[N]` on join, also after CHANGE SKILL) so automated runs skip the menu; the other debug hooks start
when the first skill is picked.

Top-centre HUD, per player: `Title - Subtitle`, `Stage s/S - <tier name>`, the prompt, the lettered
choices (`A: 11     B: 14     C: 10`), and a feedback line, on a dark panel. A wrong door shows a big red cross, the
penalty's name and that choice's feedback, fires the penalty, and puts the player back at the retry point
with the same question still up. A right door shows a big green check over CORRECT!, the explanation, and the next
question, and that door's barrier opens for that player (no barrier: a teleport to the next station). A door letter the
item does not use shows "No choice D here". Doors of a station the player is not on show "This is
not your station". After the last station: FINISH!, the run time, a medal (GOLD = every answer right first try,
SILVER = 70%+, BRONZE), first-try accuracy, personal best, the island record with its holder's name and the session's top times (best per
player, `BoardSize` rows) on a centre-screen finish board; 12 s later the player starts a fresh
run from station 1 (unless an End Game device is set).

Race layer: the clock and the run's target ("Beat 1:20.1") sit left, under the GAME MODE box; a 3-2-1-GO countdown
(player held in stasis) starts each run's clock. A first-try right answer builds a streak ("3 IN A ROW!") and a
speed boost (the `fnm_boost` movement modulator at 2.0x, 3 s + 1 s per streak step, max 7 s), shown big in the top
panel as "STREAK x3  -  SPEED BOOST 4s"; a wrong door ends both, an elimination ends only the boost. Shipping containers tagged `fnm_slider` sweep across the hallways
(placed X to mirrored X and back); hurdles and baffles are static. Obstacle plan: `OBSTACLES` in
`tools/build_course.py`.

Live race (G6): under the clock, a RACE strip lists everyone on the island by progress (finished fastest first as
`FIN 1:23.4`, then racers by station, then `picking` / `lobby`), the viewer's own row `YOU` in gold; top 7 + the viewer
past 8 players; refreshed every 0.5 s (`RaceLoop`), hidden while picking. Pace: each run records a split per right
answer; at GO! it is measured against the session island record's splits for that skill (`Record 1:23.4`) or else the
player's own saved best run (`Beat 1:23.4`), and each right answer shows the delta under the target (`−1.8 s` green
ahead, `+3.2 s` red behind). Public feed, top right under the minimap, to every player, 3 lines newest on top, 7 s
each: penalties (`Nova got yeeted at station 4`), finishes with the medal, island records, streaks of 3/5/7/10 and
skip-guard catches; each logs `FNM: feed ...`.

Output log (`Print`) messages starting with `FNM:` trace the run; these mean misconfiguration: no stations, a slot
with no cartridges, a cartridge with no tiers, or a station with fewer doors than any cartridge's items have choices.

## Known limits

- A player who is eliminated respawns at a spawn pad but keeps their stage. If eliminations are
  possible on the course, either disable them (Island Settings) or add a spawn pad per station.
- Text uses the Fortnite UI font: `×`, `÷`, `−` and superscripts render (PROTOCOL O1, `unicode` profile); ✓ and ✗
  do not, so the verdict uses textures.

## First compile checklist

Signatures were checked against the **v42.20 digest files** (`Fortnite.digest.verse`,
`UnrealEngine.digest.verse`, `Verse.digest.verse`, mirror at github.com/kbfngg/uefn,
`Modules/FortniteGame/`) and idioms against a corpus of UEFN-compiled examples
(github.com/uefncentral/uefn-verse-examples). Least certain first — if the build fails, look here:

1. **`set PromptText.WrapWidth = WrapAt`** (fnm_ui.verse, `Attach`). Digest: `var WrapWidth<public>: float`
   on `text_base`. No compiled example uses it. If rejected, delete the three `set ...WrapWidth` lines
   (long explanations then won't wrap — try `text_block{..., WrapWidth := 1500.0}` instead).
2. **`FnmCartridges()` effects** (was `FnmActiveCartridge()` before the picker). Called only from `OnBegin` (any effect allowed there). If the
   generated file adds `<computes>`/`<transacts>` that still works.
3. **Cross-file visibility.** All files flat in one folder = one module, no `<public>` needed. If the
   generated file lands in a subfolder, expect "unknown identifier fnm_cartridge / FnmActiveCartridge".
4. **`for` as an expression** returning arrays (`FnmPoolForTier`, `FnmBuildTierPools`, `FnmDraw` rest).
5. **`set State.Decks[Tier - 1] = Draw.Rest`** inside `if (...) {}` — element write through an object
   field; same shape as compiled `if (set PetPurchaseData.AvailablePetProps[I] = true){}`.
6. **`"...({Percent}%)"`** — `%` in a string literal (fnm_logic.verse, `FnmAccuracyLine`). Remove the `%`
   if the lexer objects.
7. **`TriggeredEvent` payload is `?agent`** (digest: `TriggeredEvent<public>: listenable(?agent)`); the
   handler signature is `OnTriggered(MaybeAgent:?agent):void`.
8. **`fnm_station := class<concrete>`** with `@editable` device fields inside an `@editable` array — the
   compiled LaserDoors example uses exactly this shape.
