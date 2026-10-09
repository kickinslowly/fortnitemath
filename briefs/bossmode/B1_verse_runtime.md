# B1 — Boss mode Verse runtime (Opus, parallel with B2 and B3, after B0)

You build the mode's game logic. Read first, in this order: `briefs/bossmode/README.md`; `BOSS_MODE.md` (the whole file,
it is the spec; §1, §2, §4-§10, §12 are yours); `CLAUDE.md` "Gotchas"; `PROTOCOL.md` §6, §6b, §7, §8;
`console/verse/fnm_director.verse` (all of it: the picker `BeginPicking` / `OnPickerChoice` / `Pick` / `ChangeSkill`, the
door path `OnDoor` / `HandleDoor` / `AdvancePlayer` / `Punish`, the race arena `EnterArena` / `HandlePad` / `BossHit` /
`BossDown` / `BossLoop` / `FireCannons` / `KnockBoss`, `WatchLife` / `Respawned`, `FinishPlayer`, `DebugAutoRight` /
`DebugBossRun`, `GuardLoop` / `StationOccupied`, `RaceEntry`, `Sound` / `SoundLater` / `SoundAfter` / `Music`),
`console/verse/fnm_ui.verse` (the slate, verdict, picker, finish buttons), `fnm_logic.verse`, `fnm_rig.verse`,
`fnm_audio.verse`, `fnm_tags.verse` (B0 added `fnm_bm_*` and the 19 cues), `fnm_cartridge.verse`, `fnm_save.verse`;
`tests/test_audio_cues.py`, `tests/test_hud_layout.py` (what it pins in the Verse); global skill
`~/.claude/skills/uefn-mcp/SKILL.md` sections "Verse", "Verse UI buttons and HUD menus", and the two 42.30 gotcha lists.

Precondition (B0 landed): `grep -c "fnm_bm_slot_5" console/verse/fnm_tags.verse` → 2 and `grep -c BmWeapon console/verse/fnm_audio.verse` → 2.
If not, do the read-only part of this brief (design notes, test scaffolding that does not import the tags) and re-check.

You own: `console/verse/fnm_bossmode.verse` (new), `console/verse/fnm_director.verse`, `console/verse/fnm_ui.verse`,
`console/verse/fnm_audio.verse` **below** the enum / `FnmCues` / `FnmCueIds` lists (helper functions like `FnmHitCue` live
there; you may add `FnmBmLevelCue`-style helpers), `tests/test_bossmode.py` (new). You do NOT touch `fnm_tags.verse`,
anything in `tools/`, `maps/`, docs, or other tests. You never call the UEFN MCP (B2 is driving the editor; B4 compiles and
plays). Do not commit. Edit Verse with the Edit tool or `tools/patch.py` only (eol=lf).

## Repo facts
See README. Tests: `.venv/Scripts/python -m pytest -q` (8699 green before you; `test_audio_cues::test_builder_table...`
and `test_hud_layout::test_every_texture...` may be red until B3 lands, README says why). Verse cannot be compiled on this
machine without UEFN; B4 compiles. So write Verse the way the surrounding code does, copy proven shapes, and keep each
function small. Known compiler traps (skill): a function called in a `for`/`if` header needs `<transacts>`; a local named
`Tags` clashes with the Tags module; a `<localizes>` call cannot initialise a class field (set text in Attach); a file that
imports both SpatialMath modules cannot name `vector3` (use `FnmImpulse` in `fnm_math.verse` for impulses);
`GetFortCharacter[]` is `<decides>`. `Print` strings may hold `×` etc.; logic does not interpolate (`FnmYesNo`).

## Deliverables (names and copy are fixed by BOSS_MODE.md; use them verbatim)

1. **`console/verse/fnm_bossmode.verse`** (new, module-level in the same flat folder):
   - `fnm_bm_level := struct` with `Hits : int`, `SpawnSeconds : float`, `Gates : int`, `MaxAlive : int`, `Anger : string`,
     `Banner : string`, `Perches : []int`, `WeaponName : string`; `FnmBmLevels()<transacts>:[]fnm_bm_level` = the §4 table
     exactly (2/3/3/4/4 hits; 20/15/12/9/7 s; gates 1/2/3/4/4; alive 2/3/4/5/6; GRUMPY ANGRY FURIOUS RAGING UNHINGED;
     banners "HERE HE COMES!" "HE'S ANGRY!" "HE'S FURIOUS!" "HE'S RAGING!" "FINAL LEVEL. UNHINGED!"; perches {1} {2} {3} {4} {3,4};
     weapons "SMG" "Pump Shotgun" "Assault Rifle" "Heavy Sniper" "Rocket Launcher").
   - `FnmBmLevelCount()<transacts>:int = 5`, `FnmBmLevel(L)` (clamped lookup), `FnmBmPerchName(P)<transacts>:string`
     (1 "FRONT-RIGHT PERCH", 2 "FRONT-LEFT PERCH", 3 "BACK-RIGHT PERCH", 4 "BACK-LEFT PERCH"; the L5 hint says "BACK PERCHES"),
     `FnmBmBossLineText(L)` (§4 boss lines), `FnmBmLevelCue(L)<transacts>:fnm_cue` (1 → BmStart, 2..5 → BmLevel2..5),
     `FnmBmBossCue(L)` (BmBossL1..5), `FnmBmBannerSub(L)`.
   - `fnm_cannon_rig := class` { `Fx : []vfx_spawner_device`, `Strike : ?vfx_spawner_device`, `StrikeHome : ?transform`,
     `Blasts : fnm_rig`, `Nuke : ?vfx_spawner_device` } — the race arena's existing `CannonFx` / `StrikeFx` / `StrikeHome` /
     `BlastRig` fields become one `RaceRig : fnm_cannon_rig` (Nuke false) and `FireCannons` takes the rig as a parameter.
     Race behaviour and its log line `FNM: cannons fired ({N} muzzles, blast {B}) at {Feet}, {Left} hits to go` stay identical.
   - `fnm_bm_arena := class`: `Station : fnm_station` (from `Director.FindStationParts(fnm_bm)`: pads as Doors, entry as
     RetryTeleporter and NextTeleporter, Passages empty, DifficultyOverride -1), `BossSpawners : []?guard_spawner_device` (5,
     by `fnm_bm_slot_L`), `Gates : []?guard_spawner_device` (4), `GateFx : []?vfx_spawner_device` (4), `PerchTriggers :
     []?trigger_device` (4), `PerchFx : []?vfx_spawner_device` (4), `GrantTriggers : []?trigger_device` (5), `AngerFx :
     []?vfx_spawner_device` (5), `Rig : fnm_cannon_rig`. A helper `SlotOf(Object)<transacts>:int` reads which
     `fnm_bm_slot_N` an object carries (1..5, else -1), the way `DoorLetter` reads door tags. Devices found by tag at
     OnBegin are `Disable()`d (spawners, VFX) as the race arena does.
   - `fnm_boss_mode := class` with `Director : fnm_director`, `Arena : fnm_bm_arena`, shared state `var Level : int = 0`
     (0 = idle), `var TeamHits : int`, `var BossAlive : logic`, `var BossAgent : ?agent`, `var BossRequestedAt : float`,
     `var AliveMonsters : int`, `var NextSpawnAt : float`, `var GateCursor : int`, `var Summoning : logic`,
     `var LevelDownAt : float`, and the functions: `Build()` (log `FNM: boss mode: arena found: {Pads} pads, {Gates} gates,
     {Perches} perches, {Bosses} boss spawners, {Granters} granters, {Cannons} cannons`), `Start(State)`, `Leave(State)`,
     `OnPad(State, DoorIndex)<suspends>`, `OnPerch(State, P)`, `Summon(L)<suspends>`, `LevelCleared()`, `Victory()`,
     `SpawnLoop()<suspends>`, `BossLoop()<suspends>`, `Fighters():int`, `DrawBmItem(State)`, `BossLine(State):string`,
     `Wave()` (the wrong-answer spawn on every active gate, cap + 2; log `FNM: boss mode wave: {N} monsters spawned`).
     Feed messages as `<localizes>` functions at module level (`FnmFeedBmJoin`, `FnmFeedBmHit`, `FnmFeedBmWrong`,
     `FnmFeedBmWeapon`, `FnmFeedBmFinal`, `FnmFeedBmClear` with the §4/§7 copy).
   - Behaviour per BOSS_MODE.md §2 (draw), §4 (levels, clear, victory, multiplayer, Partial), §5 (SpawnLoop), §6 (Summon
     timeline and copy), §7 (hit and perch). Timings: `Director.BmRespawnSeconds` (4.0), `Director.BmSummonSeconds`
     (5.0), hit voice delays as the race (`HitVoiceDelaySeconds` 0.9; the grunt at +0.4). Pads answer on the trigger event
     only (as the race arena pads do: no position backstop). A `Busy` guard per player exactly like `OnDoor`.
     `OnPad` correct path also books `State.Answered += 1`, first-try accuracy, streak + cues + boost, feed milestones, the
     split is NOT recorded (no stations), and after the kill-hit of level 5 it leaves `Finished` to `Victory()`.
   - Start: `Mode := Boss`, `Stage := 0`, `Level` shared (if `Fighters() = 0` → reset shared state, `Level = 1` or
     `DebugBossLevel` on the player's first start with `Partial := true`), decks built, `SetTitle("BOSS BATTLE", "Every skill,
     every grade")`, HidePicker, release stasis, `SendTo(entry)`, `GiveLoadout`, first question, `FlashBig("STEP ON THE RIGHT
     ANSWER!", Gold, 4.0)` + the §9 feedback line, `StartTime` now, the clock loop (reuse `Countdown`? no: boss mode has no
     3-2-1; start the clock directly with a small `BmClock(State)` loop like the tail of `Countdown`), feed
     `FnmFeedBmJoin`, log `FNM: boss mode start for the player (level {L})`; if nobody was fighting → `spawn{ Summon(Level) }`.
     With `DebugAutoRightAnswers` → `spawn{ Director.DebugBossModeRun(State) }` (first start only).
2. **`fnm_director.verse`** edits (minimal, surgical; keep the race path byte-identical in behaviour):
   - `fnm_mode := enum{Race, Boss}` (module level, this file). `fnm_player_state` gains `var Mode : fnm_mode = fnm_mode.Race`,
     `var Level : int = 0`, `var Deaths : int = 0`, `var Answered : int = 0`, `var BmDecks : [][][]int = array{}`,
     `var TakenLevels : [int]logic = map{}`, `var BossBest : float = -1.0`.
   - @editables (ship values): `DebugAutoBoss : logic = false`, `DebugBossLevel : int = 0`, `BmRespawnSeconds : float = 4.0`,
     `BmSummonSeconds : float = 5.0`, `NukeSeconds : float = 2.5`; constant `BossBoardKey : int = 9999`. Add them to the header
     comment's test-hook list.
   - `var BossMode : ?fnm_boss_mode = false`; at OnBegin, after `BuildArena()`: build it when `FindStationParts(fnm_bm)` has an
     entry (else log `FNM: boss mode: none (no fnm_bm entry teleporter)`); subscribe its pad triggers through a new
     `fnm_bm_pad_handler` (Director, DoorIndex → `OnBmPad`) and perch triggers through `fnm_bm_perch_handler`; subscribe the
     boss and gate spawners' events; `spawn{ BM.SpawnLoop() }`, `spawn{ BM.BossLoop() }`.
   - `BeginPicking`: `DebugAutoBoss?` → `BM.Start(State)` first; the grade step is shown when `Grades.Length > 1 or BossMode?`
     (`State.Hud.ShowGradeStep(Grades, WithBoss)`). `OnPickerChoice`: `fnm_pick.Boss` while Picking → `BM.Start(State)`;
     `fnm_pick.Again` while Finished in boss mode → `BM.Start(State)` (after hiding the board and buttons).
   - `ChangeSkill`: if `Mode = Boss` → `BM.Leave(State)` first (Mode → Race, Level 0, boss line cleared, HideBanner).
   - `ShowCurrent`: caption by Mode (`"BOSS BATTLE  -  Level {L}/5  -  {Title}"`). `Music(State)`: boss mode → level.
   - `StationOccupied`, `WatchDoors`, `WatchSkip`, `WatchIce`: skip boss-mode players (they are outside every hallway anyway;
     make it explicit). `RaceEntry`: tail `"BOSS L{Level}"` with Score between finished and racers. `Respawned`: boss mode →
     the bm entry, `Deaths += 1`, notice `"Knocked out! Back to the arena entry."`. `OnPlayerRemoved`: `BM.Leave`.
   - `FireCannons(Rig:fnm_cannon_rig, Shooter, Character, At, Left, Nuke:logic)`: the race call passes `RaceRig`, false; boss
     mode passes its rig, true (nuke VFX at the feet + both blasts + `State.Hud.Flash(0.5)` for every boss-mode player).
   - `DebugAutoRight`: when `State.Mode = Boss` at the top, hand off to `DebugBossModeRun(State)` (spec §8) and return.
   - `GiveLoadout` / `RefreshVitals` reused as they are.
3. **`fnm_ui.verse`** edits: `fnm_pick` gains `Boss`, `Again`; `ShowGradeStep(Grades:[]string, WithBoss:logic)` (the BOSS
   BATTLE `button_loud` + caption cell first, then the grade buttons; focus stays on the first grade button);
   banner widgets (`BannerArt : texture_block` `FNM_Art.T_fnm_banner`, DesiredSize 900 x 200, Stretch/Stretch; `BannerText`
   84 px Gold centre; `BannerSub` 40 px White centre) in an overlay slot anchored (0.5, 0.33), collapsed; `ShowBanner(Big,
   Sub)` / `HideBanner()`; `FlashNuke(Label:string, Seconds:float)` = the verdict slot with `FNM_Art.T_fnm_nuke`, Lime;
   `WhiteFlash : color_block` (White, opacity 0, full-screen slot above the slate but below the verdict) + `Flash(Seconds)
   <suspends>` stepping opacity 0.85 → 0 every 0.05 s; `ShowResults(Title:string, ...)` (race passes "FINISH!"; boss mode
   "VICTORY!"); `AgainButton : button_loud` "PLAY AGAIN" (`fnm_pick.Again`) beside CHANGE SKILL on the finish-buttons root;
   `ShowFinishButtons(WithChange:logic, Again:logic)` (Again shows PLAY AGAIN and collapses CLOSE; the race passes false).
   Mind `tests/test_hud_layout.py::test_director_passes_the_choices`: `ShowQuestion`'s signature and the director's call
   must stay exactly as pinned.
4. **`tests/test_bossmode.py`** (new; regex over the Verse, like `test_audio_cues.py`): the level table parses to 5 rows with
   hits (2,3,3,4,4), spawn seconds strictly decreasing, gates non-decreasing and ≤ 4, alive cap non-decreasing and ≤ 6,
   sum of hits 16; perches of L5 = {3,4}; every `fnm_bm_*` tag the runtime names is declared in `fnm_tags.verse`;
   `FnmBmSlotTags` has 5 entries; ship defaults (`DebugAutoBoss : logic = false`, `DebugBossLevel : int = 0`,
   `DebugAutoRightAnswers : logic = false`, `DebugAutoPick : int = -1`) are present verbatim; `fnm_pick` has `Boss` and
   `Again`; `FNM_Art.T_fnm_banner` and `T_fnm_nuke` are referenced; the race arena's cannon log line text is unchanged;
   every player-facing string in §9 that you emit (BOSS BATTLE, Every grade, every skill. Right answers NUKE the boss!,
   MEGA NUKE!, STEP ON THE RIGHT ANSWER!, VICTORY!, PLAY AGAIN, TOP BOSS TIMES THIS SESSION) appears in the Verse.

## Non-goals
No new content, no cartridge changes, no PROTOCOL change (`fnm_cartridge.verse` untouched). No tools/ edits: if you need a
device setting changed, write it in the report for B2. Do not restyle the race HUD. Do not add a position backstop for the
pads. Do not try to colour or scale the NPC boss. Do not touch `tests/test_arena_layout.py`, `test_hud_layout.py`,
`test_audio_cues.py`.

## Concurrency
B2 edits `tools/**` and `maps/starter/LAYOUT.md`; B3 edits `tools/make_announcer.py`, `tools/build_audio.py`, `tools/art/`,
`tests/test_hud_layout.py`, `console/AUDIO.md`. None of them touch `console/verse/*`. `test_hud_layout::test_every_texture...`
is red until B3's PNGs land (precondition `ls tools/art/fnm_nuke.png`); `test_audio_cues::test_builder_table...` until B3's
CUES rows (`grep -c bm_weapon tools/build_audio.py`). Note red siblings in the report, never edit their files.

## Verification (run and paste the output)
- `.venv/Scripts/python -m pytest -q` — all green except the two sibling-gated tests if B3 has not landed.
- `tests/test_bossmode.py` has at least 10 asserts and **two disproofs you run by hand**: (a) change L5's `Perches` to `{4}`
  in a scratch copy → `test_bossmode` red (name the failing test); (b) flip `DebugAutoBoss : logic = false` to `true` with
  `tools/patch.py` → the ship-defaults test red; restore with `patch.py` (never `git checkout`: the tree is uncommitted).
- Race path sabotage check, static: `git diff console/verse/fnm_director.verse | grep -c "^-"` — list every removed line and
  justify each in the report (expected: only the lines you refactored into the rig and the `ShowResults` / `ShowGradeStep`
  signature changes). `grep -n "FNM: cannons fired" console/verse/fnm_director.verse` must still show the exact race line.
- Lint by eye for the compiler traps above: grep every `for (` and `if (` header you wrote for calls to functions without
  `<transacts>`; grep for `vector3{X :=` in files that `using { /Verse.org/SpatialMath }`.
- `tests/test_hud_layout.py::test_verse_files_are_lf` green (no CRLF).

## Report
README format, plus: the exact list of `FNM:` log lines the mode emits (B4 waits on them; §12 names the shapes), the
@editable names and ship values you added, every place the race path is touched (file:function), the things in the docs or
this brief that turned out untrue, anything you decided differently and why, your shakiest assumption stated plainly.
