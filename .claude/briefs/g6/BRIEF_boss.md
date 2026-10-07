# Brief D — Boss finale, "math as damage" (G6 item 3)

You are building GOALS.md **G6 item 3** in `D:\PyCharm Projects\fortnitemath`: a boss arena between the last
station and the finish hallway. Right answers hurt the boss; the run ends on the kill. Read first, in order:

1. `CLAUDE.md` (whole), `~/.claude/skills/uefn-mcp/SKILL.md` (whole), `GOALS.md` §G6, `maps/starter/LAYOUT.md`,
   `console/README.md`, `console/PENALTIES.md` (how rigs/penalties work), `console/AUDIO.md`
2. `tools/build_course.py` (whole: `station`, `connector`, `finish`, `build`, helpers `box/device/board/props/
   verse_tags/clear`), `tools/build_guards.py` (spawner asset, `SETTINGS`, `WEAPONS`, the probe), `tools/build_lids.py`,
   `tools/build_decor.py`, `tools/build_finish.py`, `tools/build_pickups.py` (what each reads from the course actors,
   so the arena does not break them), `tools/build_audio.py` (`CUES`)
3. `console/verse/fnm_director.verse` (whole; especially `fnm_station`, `BuildStations`, `FindStationParts`,
   `BuildHallways`/`WatchSkip`, `OnDoor`/`HandleDoor`/`AdvancePlayer`, `WatchLife`/`Respawned`, `GuardLoop`,
   `FinishPlayer`, `DebugAutoRight`, `DebugStartStage`), `fnm_tags.verse`, `fnm_audio.verse`, `fnm_ui.verse`
4. Verse digest facts (42.30): `guard_spawner_device` has `var MaxHealth/InitialHealth/Invincible/ShowHealthBar`,
   `SpawnedEvent:listenable(agent)`, `EliminatedEvent:listenable(device_ai_interaction_result)`, `Spawn()`,
   `Despawn()`, `GetAgents()`, `ForceAttackTarget(Target)`, `Enable/Disable`. A `fort_character` has `Damage(Amount)`,
   `GetHealth()`, `GetMaxHealth()` (the director already uses `Damage(1000)` on players for Spike).

## Repo facts (checked 2026-10-07)
- Windows 11, Git Bash, `master`. Python `.venv/Scripts/python`; tests `.venv/Scripts/python -m pytest -q` (read the
  count before changing anything; keep it green). UEFN 42.30 open; MCP via `tools/uefn_mcp.py` (`MSYS_NO_PATHCONV=1`
  for args starting with `/`). Verse edits: Edit tool or `tools/patch.py` (LF files). After Verse edits:
  `python -m fnm sync starter` + `tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'`.
- Course facts: stations face +Y; `DOOR_W` 553 so a 4-door station is 2212 cm wide; `WALL_H` 600; `FINISH_LEN` 1500;
  `CONN_W` 1000 with `FUNNEL` 600; connector 10 today is "long straight, 2 speed plates, to the finish". The finish
  hallway's entry teleporter is tagged `fnm_finish`; the director declares a finish in `AdvancePlayer` when
  `Stage > Stations.Length` (the clock stops at the LAST DOOR today, before the final straight).
- The tier formula (PROTOCOL §6) uses `Stations.Length`: the arena must NOT be a numbered station or every
  station's tier shifts. It is found by its own tag `fnm_boss` and always plays the hardest tier.
- Headless: `tools/playtest.py --until "…" --timeout N`; hooks `DebugAutoPick`, `DebugAutoRightAnswers`,
  `DebugStartStage`. Screenshots in `%TEMP%/pt_*.png`; `tools/capture.py` for an editor viewport PNG. LOOK at them.

## Design (fixed)
**Geometry** (`tools/build_course.py`, part of the normal `build()` so one rebuild makes it; everything tagged
with the course TAG so a rebuild clears it): after connector 10, the **arena**: 30 m long, station width, walls
`WALL_H`, floor `FNM_Arena_Floor` (name every arena actor `FNM_Arena_*` and make sure `build_lids.py`,
`build_decor.py` and `paint()` regexes either include or deliberately skip them: arena walls painted with the
`tier5` material). Entry teleporter `FNM_Arena_Entry` at y+150 tagged `fnm_boss` + `fnm_entry` (yaw like a station
entry). Four **answer pads**: trigger devices (`TRIGGER` asset) scaled to a 3 × 3 m, 1.5 m tall zone, tagged
`fnm_boss` + `fnm_door_a..d`, each on a 300 × 300 × 10 floor tile in that letter's colour (`LETTER_COLOURS`) with the
letter on a board 3 m above (`board()` style): A at (−700, +800), B at (+700, +800), C at (−700, +2200), D at
(+700, +2200) relative to the arena origin (x centre, y start). **Boss platform**: a 600 × 400 slab 100 cm high at
y+2600, centred; a guard spawner (`build_guards.SPAWNER`) at its centre facing −Y, tagged `fnm_boss_spawner`,
settings like `build_guards.SETTINGS` but ONE guard, health bar on, the highest `MaxHealth` the device accepts
(probe: write 100000, read back; report the real cap), weapon: a legendary AR from `WEAPONS`. **Adds spawner**:
a second spawner at y+1800 tagged `fnm_boss_adds`, 2 guards, pistols, disabled at start. **Gate**: a `BARRIER`
across the arena's exit at y+3000 spanning the exit width, tagged `fnm_boss_gate`; then a short straight connector
(`connector("Arena", [seg(1000)], …)`: it funnels to `CONN_W` and flares back) into the unchanged finish hallway.
A "BOSS ARENA" sign on the entry wall like the station signs. Keep `--paint-only`, `--doors-only`,
`--triggers-only`, `--ice-only` working.

**Runtime** (`fnm_director.verse` + `fnm_tags.verse`): at OnBegin build `Arena : ?fnm_arena` from the tags
(`FindStationParts(fnm_boss)` gives the entry + the 4 pad triggers; add the gate barrier and the two spawners),
log `FNM: arena: 4 pads, gate yes, boss yes, adds yes` (or what is missing). With no arena (another map) nothing
changes. The arena stage is `Stations.Length + 1`:
- Last station's right door → `AdvancePlayer` sends them on as today but instead of `FinishPlayer` calls
  `EnterArena(State)`: draws a hardest-tier item, shows it with the stage line `BOSS  -  hits 0/5`, plays cue
  `BossFight`, feed `{Who} reached the boss!`, and makes sure a boss is alive (`BossLoop`).
- Pads answer on ENTER like doors (`OnDoor` with the arena as station index −1 or a flag). Right →
  `BossHit(State)`: `Hits += 1`, damage the boss by `MaxHealth / 5` (`GetFortCharacter[].Damage`; if `Invincible`
  blocks Verse damage, keep the boss `Invincible` and toggle it off around the call; if `MaxHealth` caps low enough
  that a station-10 rocket launcher could kill it without math, use the Invincible route; say which), flash the
  green verdict with `HIT!`, cue `BossHit`, teleport the player back to the arena entry (`SendTo`), draw the next
  item. Wrong → the normal `Punish` with the arena as the station (penalties return to the arena entry), AND enable
  + `Spawn()` the adds, feed `{Who} got {Past} by the boss`. The door backstop (`WatchDoors`) is OFF in the arena:
  a pad answers on entry only (the player is moved off it after every answer).
- The boss is SHARED: health is one bar for everyone in the arena, so a class kills it together. `EliminatedEvent`
  → `BossDown()`: for every player at the arena stage: `Gate.AddToIgnoreList(Player)`, `FinishPlayer(State)` (the
  clock stops at the kill), cue `BossDead`; feed `{Who} landed the final hit!` for the last hitter; despawn adds;
  then, after 4 s, respawn the boss if anyone is at the arena stage or when the next player enters. The player then
  WALKS through the gate into the finish hallway and the victory area; `FinishPlayer`'s results board and podium
  flow are unchanged. Medal and accuracy stay course-only (`Total = Stations.Length`); hits are time only.
- HUD: a `BossText` line (top centre, under the question panel) for players at the arena stage:
  `BOSS  ████████░░  80%   -   your hits 1/5`, refreshed every 0.25 s from `GetHealth()/GetMaxHealth()`; hidden
  elsewhere. Add it to `fnm_ui.verse` without moving anything else.
- Eliminated by the boss: `WatchLife`/`Respawned` must return an arena-stage player to the ARENA entry with the
  pistol (today it indexes `Stations[Stage − 1]`: handle the arena stage). `WatchSkip`: add the arena as a hallway
  (a player below the arena stage found in it is sent back; an arena-stage player is legit; the finish hallway
  needs the arena stage or higher).
- `DebugAutoRight` must carry a run THROUGH the arena: teleport onto the right pad until the boss dies (cap 12
  tries, log `debug auto-right boss hit N`). `DebugStartStage = Stations.Length + 1` starts in the arena.
- Audio: extend `fnm_cue` with `BossFight`, `BossHit`, `BossDead` (tags `fnm_cue_boss_fight` …), add them to
  `CUES` in `tools/build_audio.py` with library sounds (`IP_SC_PoppySoap_Announcer_VO_Fight` for BossFight,
  `Music_S22_Freaky_Boss_Elim_Stinger_Cue` for BossDead, a solid hit cue for BossHit: search "Hit", "Impact",
  "Damage"), and rerun `build_audio.py`.

## Deliverables
1. `tools/build_course.py`: the arena + its connector in `build()`, constants `ARENA_LEN`, `PAD_SIZE`, `PAD_SPOTS`,
   `BOSS_SETTINGS`, `ADDS_SETTINGS`; `maps/starter/LAYOUT.md` gets a "Boss arena" section (shape sketch, tags,
   why the arena is not a station).
2. Verse: `fnm_director.verse` (arena build, EnterArena/BossHit/BossDown/BossLoop, HUD refresh, WatchSkip,
   Respawned, DebugAutoRight, DebugStartStage), `fnm_tags.verse` (`fnm_boss`, `fnm_boss_spawner`, `fnm_boss_adds`,
   `fnm_boss_gate`), `fnm_ui.verse` (`BossText`, `SetBoss(Text)`/`ClearBoss`), `fnm_audio.verse` (3 cues).
3. `tools/build_audio.py` CUES rows for the 3 cues.
4. Rebuild and rerun, in this order, and record each run's wall time and final line: `build_course.py` (full),
   `build_decor.py`, `build_finish.py`, `build_guards.py`, `build_pickups.py`, `build_lids.py`, `build_audio.py`,
   `build_island.py --check`. Then `build_rigs.py` is NOT needed (rigs are parked, not geometry); say so.
5. Docs: `console/README.md` §2/§3 (arena tags), `CLAUDE.md` §Gotchas: one line on the arena (stage
   `Stations.Length + 1`, tag `fnm_boss`, not a station). `GOALS.md` is NOT yours.

## Verification
- BuildAll clean; pytest green. `build_island.py --check` clean.
- `DebugAutoPick 0` + `DebugStartStage 11` (= arena) + `DebugAutoRightAnswers`: log shows `arena:` line, `boss
  spawned`, 5 `boss hit` lines with falling health %, `boss eliminated`, `finished run 1`, gate open; a screenshot
  from the arena showing the pads with their letters, the boss on the platform with its health bar, the HUD boss
  line. Then a FULL run from stage 1 (`DebugStartStage 1`) through all 10 doors and the arena to the finish board.
- `DebugAutoWrongAnswers 2` in the arena (DebugStartStage 11): a penalty + the adds spawning (`guard spawned` lines
  after the wrong answer), feed line.
- Editor capture (`tools/capture.py`) of the arena from above: pads, platform, gate, sign, lids over it, walls
  painted tier5.
- Sabotage once: make `BossHit` deal 0 damage; the auto-run must report the boss NOT dying (stuck/cap reached);
  restore by re-applying the original text, rebuild, confirm the kill again.
- Restore every debug `@editable` to its ship value, sync, rebuild. Leave no probe actors.

## Non-goals / do NOT
- Do NOT commit. Do NOT edit `GOALS.md`, `PROTOCOL.md`, `cartridges/**`, `emulator/**`, `fnm/**`, `tools/audio/**`,
  `tools/make_announcer.py`, penalties' behaviour, the skill picker, the race layer's strip/feed code except to add
  the feed lines named above.
- Do NOT change station geometry, connectors 1–10, door logic or the tier formula. Do NOT lower guard counts or
  weapons (balance is Aaron's). Checkpoint every file to disk as soon as it compiles.

## Report
Files edited; BuildAll result; pytest before/after; each builder's wall time; the real `MaxHealth` cap and which
damage route you used; the log excerpts (arena line, hits, elimination, finish, gate); the screenshot/capture
file names and what they show; the sabotage result. Then **"Anything I decided differently from this brief and
why"** and **"Shakiest assumption, stated plainly"**, and anything in the docs that turned out untrue.
