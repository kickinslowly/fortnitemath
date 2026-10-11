# BOSS BATTLE mode — plan (2026-10-09, Fable)

Aaron: "create new boss battle mode, as an option in beginning. that pulls from all question categories. this is an
arena fight, just like the boss battle, but it's only a boss battle, can answer by stepping on correct platform. mega
nukes and laser attack the boss for correct. correct is obvious and celebrated. monsters and npcs spawn at increasing
intervals from gates in the walls of the arena, as the boss yells and gets more angry, he calls to them and summons them
using fun engaging graphics at the start of each new level. weapons spawn around map each level but in set places the
player must reach. like elevated platforms that must be jumped to etc."

This file is the spec. Builder briefs: `briefs/bossmode/` (README has the order). Goal entry: GOALS.md G8.
Everything marked **UNVERIFIED** is a belief, not a checked fact; the brief that depends on it names the fallback.

## 0. Decisions (one line each)

| # | Decision | Why |
|---|---|---|
| 1 | A gold **BOSS BATTLE** button on the picker's grade step (shown whenever the map has a boss-mode arena, even with one grade); no skill step. Debug hook `DebugAutoBoss` (ship false) starts it on join with no menu. | "An option in the beginning" = the one menu every run already starts with; CHANGE SKILL reopens it, so the mode is always reachable. |
| 2 | Questions come from **every** baked cartridge: each question picks a cartridge at random, then draws from that cartridge's deck for the tier the level maps to (PROTOCOL §6 tier formula with Stage = level, StageCount = 5). Per-player decks per cartridge, no new content. | Reuses the registry and the tier formula verbatim; §4a bounds hold because the items are the baked ones. |
| 3 | A **new dedicated arena** 150 m east of the course (`tools/build_bossmode.py`, tag `fnm_bossmode`, Verse tags `fnm_bm_*`); the race arena is untouched. | The race arena is a 30 m hall sized for one boss; the mode needs gates, perches and room to fight, and Aaron's race playtests must not move. |
| 4 | **5 levels, 16 team hits** (2/3/3/4/4); a right pad = a hit; the level clears when the boss drops; health and shield refill every level; a wrong pad = the normal penalty + a monster wave; no lose state (eliminated = respawn at the arena entry, counted); win screen with PLAY AGAIN / CHANGE SKILL. Shared boss and level for everyone in the mode, like the race arena. | 16 questions is a 3-5 minute fight; the refill is what made the race boss beatable (G6 3a); no lose state because a 6th grader must be able to finish. |
| 5 | Escalation per level: more gates active (1→4), faster spawns (20 s→7 s), alive cap 2→6, stronger monster weapons by gate, boss weapon by level (pistol→heavy AR); the level clear despawns every monster. | Monotonic and capped so the arena never fills; the cap is enforced by the director, not trusted to the device. |
| 6 | Level-start **summon**: HUD banner ("LEVEL 3" / "HE'S FURIOUS!"), announcer level line, boss voice line as a subtitle, anger VFX ring round the platform (L of 5 lit), lightning at each active gate as its spawner comes on, weapon-drop hint and a beacon on the live perch. | Everything here is a device the repo already drives (VFX spawner, guard spawner, audio player, HUD) plus two textures; nothing new to validate. |
| 7 | Right answer = **MEGA NUKE**: the arena's own cannon rig (wall lasers + strike, the proven FireCannons) plus a nuke (big VFX + two no-damage blasts at the boss's feet), a white screen flash, a mushroom-cloud verdict icon "MEGA NUKE!  N TO GO", the boss knocked back and stunned, announcer "Mega nuke!" + the existing hit countdown, boss grunt. Wrong = red X + penalty name + boss taunt in the feed. | "Correct is obvious and celebrated": image, text, sound, screen flash and world VFX all fire at once. |
| 8 | **Weapons**: one per level, in a gold **weapon chest** on that level's lit **perch** (a 1.8-2.4 m platform reached by jumping up stepping stones): holding E on it (a hidden button in the chest, on only while the perch is lit) grants the weapon with its ammo through the proven hidden-trigger + Item Granter path (`giveExtraAmmo`). A VFX beacon marks the live perch; the HUD says which. (Aaron, 2026-10-09: he could not tell weapons were spawning; chest asked for.) | The pad device cannot be toggled from Verse (unverified), the granter path is proven and handles a full inventory. |
| 9 | Verse: new `console/verse/fnm_bossmode.verse` (level table, copy, arena class, the mode's loops) owned by a `fnm_boss_mode` object the director builds at OnBegin when an `fnm_bm` entry exists; the director gets a `Mode` per player and routes picks, pads, respawns and finish to it. Race code paths unchanged (sabotage check in B1). | Keeps the 2455-line director from growing a second game inside it; the race path stays byte-stable. |

Defaults picked without asking (Aaron wants autonomy): 5 levels / 16 hits; no lose state; shared team boss; guards plus
Fortnite creatures from level 2 (B5, §5; no Megabrute); the arena east of the course; am_onyx as the boss voice.

## 1. Where the mode starts (picker)

- `fnm_pick` gains `Boss` and `Again`. `ShowGradeStep(Grades, WithBoss)` adds, above the grade buttons, a `button_loud`
  **"BOSS BATTLE"** with the 22 px caption **"Every grade, every skill. Right answers NUKE the boss!"**.
- `BeginPicking`: when the map has a boss-mode arena the grade step is shown even with one grade (today the slot has
  grades 6 and 7, so nothing changes for the race).
- `OnPickerChoice(Boss)` → `BossMode.Start(State)`. `DebugAutoBoss : logic = false` (@editable, ship false): a joining
  player starts boss mode with no menu (wins over `DebugAutoPick`).
- Win screen buttons: **PLAY AGAIN** (`fnm_pick.Again`, a `button_loud` shown only in boss mode; CLOSE collapsed) and
  **CHANGE SKILL** (existing; `ChangeSkill` also leaves boss mode: Mode → Race, back to station 1, picker).
- HUD tag while in the mode: title **"BOSS BATTLE"**, subtitle **"Every skill, every grade"**.

## 2. Questions across every cartridge

Per player, on Start: `BmDecks : [][][]int` = one shuffled deck per cartridge per tier
(`for (Pools : Director.CartridgePools) { FnmShuffleAll(Pools) }`). Per question:
`C := GetRandomInt(0, Cartridges.Length - 1)`; `Tier := FnmTierForStage(Level, 5, Cartridges[C].Tiers.Length, -1)`
(T = 5 → levels 1..5 = tiers 1..5; T = 3 → 1,2,2,3,3); `Draw := FnmDraw(BmDecks[C][Tier - 1], CartridgePools[C][Tier - 1])`;
`set State.Cartridge = Cartridges[C]`, `set State.CartridgeIndex = C`, `set State.CurrentItem = Draw.ItemIndex`,
`set State.Order = Shuffle(...)`. Everything downstream (`ChoiceAt`, `AnswerDoor`, `FeedbackFor`, `ShowCurrent`) reads
`State.Cartridge`, so the per-question swap needs no other change. Slate caption:
**"BOSS BATTLE  -  Level {L}/5  -  {Cartridge.Title}"** (the kid sees which skill the question is from).

## 3. Arena (new, `tools/build_bossmode.py`, LAYOUT.md "Boss battle arena")

**Superseded geometry (colosseum pass, 2026-10-09):** the arena is now round (radius 32 m, a Coliseum-kit podium, stands,
colonnade and tribune by `tools/build_colosseum.py`); gates, perches, pads, platform and cannons moved. The current layout
and every position live in LAYOUT.md "Boss battle arena". The devices, settings and tags below are unchanged; read the
positions in this section as the B2 history.

Units cm. Arena centre line x = 14000, south (entry) wall inner face y = -14000, floor top z = 2 (slab under it like the
course). Player enters at the south end facing +Y (`ArrivalYaw` 90), so **+X is the player's LEFT**. Coordinates below
are relative to O = (14000, -14000, 0). Walls 800 high, 40 thick; one hidden collision lid (build_lids recipe).

```
          x = +2000 (player's LEFT)                                   x = -2000 (RIGHT)
 y+4000  ┌─────────────────────────────────────────────────────────────────┐  north wall
         │ [P4 BL 240]                                       [P3 BR 240]   │  perches: 3 x 3 m tops, stepping stones below
         │                      ┌───────────────┐                          │
   G4 ▓▓ │                      │  BOSS  (5 sp) │                          │ ▓▓ G3   gates in the side walls at y+3000
 y+3000  │   ○                  └───────────────┘                  ○       │  platform 8 x 5 m, top +100, centre (0, 3200)
         │        ○                                            ○           │  ○ = anger VFX ring (5, lit L of 5)
         │                                                                 │
         │  ⊕ cannon L (wall, y+2200, 3.3 m up)         cannon R ⊕         │  wall lasers aimed at the platform
 y+2000  │      [ C ]                                     [ D ]            │  pads C (x+900) D (x-900) at y+2100
         │                                                                 │
   G2 ▓▓ │                                                                 │ ▓▓ G1   gates at y+1200
 y+1000  │      [ A ]                                     [ B ]            │  pads A (x+900) B (x-900) at y+1100
         │ [P2 FL 180]                  E ↑               [P1 FR 180]      │  E entry teleporter (0, +250)
 y+0     └─────────────────────────────────────────────────────────────────┘  south wall, "BOSS BATTLE" sign on the left wall
```

| Piece | Where (x, y, z) | Device / asset | Verse tags | Count |
|---|---|---|---|---|
| Floor slab, walls, lid | 4000 x 4000; walls to z 800 | engine cubes (`M_fnm_wall_bm_wall` / `_bm_floor`, new colours in `import_art.WALL_COLOURS`) | — | ~14 cubes |
| Entry teleporter | (0, 250, 0), yaw 90, both group knobs Group_None | `PID_Device_Teleporter` | `fnm_bm` + `fnm_entry` | 1 |
| Answer pads A..D | (900, 1100) (-900, 1100) (900, 2100) (-900, 2100); tile 450 sq, 10 thick, `M_fnm_wall_pad_a..d`; trigger 450 x 450 x 150 on it; a giant 3D letter (CRG_Props Alphabet, scale 1.8, bottom 250 up, pad colour, no collision) that turns to face the nearest boss-mode player and bobs (`FaceLetter`; Aaron 2026-10-09: the boards were hard to see from some angles) | `PID_Device_Trigger`, Alphabet prop | `fnm_bm` + `fnm_door_a..d`; letter `fnm_bm_letter` + slot | 4 + 4 |
| Boss platform | 1 m high, 800 x 500 (§15b; 3.5 m in §15) | engine cube, `M_fnm_wall_bm_marble` | — | 1 |
| Titan (§15b) | the boss players see: one Animated Mesh device per clip (idle, flail, stomp, dead) on the platform, scale 4 (12 m), facing the entry; Meshy art in `FNM_BossArt/Clip_<clip>` (`tools/import_boss.py`) | `Device_AnimatedMesh` | `fnm_bm_titan` + slot | 4 |
| Boss (since 2026-10-10, §15) | a Megabrute creature spawner on the platform centre (`build_bossmode.boss_rig`) | `PID_Device_CreatureSpawner_V2` | `fnm_bm_megaboss` | 1 |
| Cannon beams (§15) | an Alphabet "I" per cannon laid from its muzzle to the titan's waist, Aqua (§15d; was Neon Green), no collision | Alphabet prop | `fnm_bm_beam` + slot | 2 |
| Gates G1..G4 | side walls at y 1200 (G1 right x-2000, G2 left x+2000) and y 3000 (G3 right, G4 left): a 400-wide, 350-tall opening, a 300-deep alcove (back, two sides, roof) in `M_fnm_wall_steel`; monster spawner at the alcove centre facing into the arena; VFX spawner at the mouth, scale 2, LightningBolt_02 + Electric_Blast, Burst, enabled On Phase None | spawner `PID_Device_GuardSpawner_V2`, fx `PID_Device_VFX_Spawner_V2` | spawner `fnm_bm_gate` + `fnm_bm_slot_G`; fx `fnm_bm_gate_fx` + `fnm_bm_slot_G` | 4 + 4 |
| Perches P1..P4 | P1 FR (-1600, 500) top 180; P2 FL (1600, 500) top 180; P3 BR (-1600, 3500) top 240; P4 BL (1600, 3500) top 240. Top 300 sq (`M_fnm_wall_bm_perch`, gold); stepping stones 120 sq, tops at 60, 120 (and 180 for the 240 perches), 150 edge gap, laid toward the arena centre; hidden trigger 300 x 300 x 200 on the top; beacon VFX on the top, LightningBolt_01, scale 2, enabled On Phase None | trigger, VFX | trigger `fnm_bm_perch` + `fnm_bm_slot_P`; fx `fnm_bm_perch_fx` + `fnm_bm_slot_P` | 4 + 4 |
| Weapon granters, one per level | parked under the floor (z -600), x = -1200 + 300 L; each bound (`grantItem` ← its trigger's OnTriggered with `TRIGGER_CLASS` memberParent) to a hidden trigger parked beside it; `GRANT_SETTINGS` from build_pickups (Keep All, Only if Not Owned, drop at feet when full) + `equipItemOnGrant` 1; item = the level's weapon | `PID_CP_Devices_ItemGranter`, `PID_Device_Trigger` | trigger `fnm_bm_grant` + `fnm_bm_slot_L` | 5 + 5 |
| Mega cannons (§15d) | the Meshy mesh `SM_fnm_megacannon` at scale 4 (7.6 m) on the sand, 27.2 m from CENTRE at 36° and 144°, barrel on the titan's waist; per cannon a muzzle laser (`_Fx`, where the beam starts) and a lightning zap (`_Zap`) fired with the shot, a coil crackle (LightningBolt_02, Continuous, always on) and two cyan point lights (coils, muzzle) | static mesh, VFX, `PID_Device_PointLight` | `fnm_bm_cannon_fx` (laser + zap) | 2 x (1 mesh + 3 fx + 2 lights) |
| Strike, blasts, nuke | parked under the platform (z -600): strike VFX (LightningBolt_03, Electric_Blast, scale 5); 2 explosive devices (`build_cannon.BLAST`, knockback "High" (B5; the enum has no "Large"), else Medium); nuke VFX (scale 6; effect: a smoke / explosion / fire entry of the `visual_Effect` enum if one exists, else LightningBolt_01) | VFX, `PID_Device_ExplosiveBarrel` | `fnm_bm_strike`, `fnm_bm_blast`, `fnm_bm_nuke_fx` | 1 + 2 + 1 |
| Creature spawners (B5) | one per creature kind, just inside a gate's alcove mouth (x = side 2090): Fiend G1, Brute G2, Ranged G3, Red Fiend + Exploding Brute G4 (y -100 / +100); invisible, invincible, off at start, activation range 100, Do Not Despawn, spawn limit on (100), 1 per wave | `PID_Device_CreatureSpawner_V2` | `fnm_bm_creature` + `fnm_bm_slot_K` (K = kind) | 5 |
| Anger ring | 5 VFX spawners round the platform at radius 650 (angles 198°, 234°, 270°, 306°, 342° from +X, i.e. the near half), floor level, scale 1.5, LightningBolt_01, enabled On Phase None | VFX | `fnm_bm_anger_fx` + `fnm_bm_slot_L` | 5 |
| Sign | left wall (x +1995, y 600, z 250), yaw -90, scale 2: "BOSS BATTLE" | billboard | — | 1 |

Monster spawner settings (`GATE_SETTINGS`): `build_guards.SETTINGS` + `spawnCount 2` (alive per gate), `allowInfiniteSpawn True`,
`spawnOnTimer False` (the director calls `Spawn()`), `spawnRadius_InMeter 2.0`, `spawnThroughWalls False`, `enablePatrol True`,
`maxPatrolDistance_InMeter 30.0`, `visibilityRange_InMeter 45.0`, `accuracy LOW`, `despawnGuardsWhenDisabled True`,
`dropInventoryOnElimination True`, team Wildlife & Creatures. Gate weapons: G1 `WID_Pistol_SemiAuto_Athena_R_Ore_T03`,
G2 `WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03`, G3 `WID_Shotgun_Standard_Athena_VR_Ore_T03`, G4 `WID_Assault_Heavy_Athena_R_Ore_T03`
(all in `build_guards.WEAPONS` / its accepted list).

**UNVERIFIED (B2 probes, with fallbacks):** a jump chain of 60 cm rises over 150 cm gaps is comfortable (fallback: 50 / 100;
B4's keys test confirms); `Spawn()` on a spawner with `spawnOnTimer False` spawns (fallback: `spawnOnTimer True`,
`spawnTimer 999`, and still `Spawn()`); explosive `knockback` accepts "Large"; the VFX `visual_Effect` enum has a
smoke/explosion/fire effect (known: LaserBeams, LightningBolt_01..03); a creature/wildlife spawner is placeable
(`ListDeviceAssets nameFilter "Creature"` / `"Wildlife"`; if one exists B2 reports its path and settings, nothing is
built with it this round); the item granter accepts the five weapon WIDs (proven only for the pistol; read the list back).

## 4. Levels

| L | Hits to clear | Spawn every | Gates active | Alive cap (all gates) | Boss weapon | Monster gates' weapons | Creatures (every other monster) | Weapon perch | Anger | Banner sub | Boss line (cue) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 20 s | 1 | 2 | `WID_Pistol_SemiAuto_Athena_R_Ore_T03` | G1 pistol | none (guards only) | P1 FR: **SMG** (`WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03`) | GRUMPY | HERE HE COMES! | "You dare challenge ME?!" (`bm_boss_l1`) |
| 2 | 3 | 15 s | 2 | 3 | `WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03` | + G2 SMG | Fiend | P2 FL: **Pump Shotgun** (`WID_Shotgun_Standard_Athena_VR_Ore_T03`) | ANGRY | HE'S ANGRY! | "Minions! GET THEM!" (`bm_boss_l2`) |
| 3 | 3 | 12 s | 3 | 4 | `WID_Pistol_AutoHeavyPDW_Athena_VR_Ore_T03` | + G3 pump shotgun | Fiend, Brute | P3 BR: **Assault Rifle** (`WID_Assault_AutoHigh_Athena_VR_Ore_T03`) | FURIOUS | HE'S FURIOUS! | "Is that all you've got?!" (`bm_boss_l3`) |
| 4 | 4 | 9 s | 4 | 5 | `WID_Shotgun_Combat_Athena_VR_Ore_T03` | + G4 heavy AR | Ranged, Brute | P4 BL: **Heavy Sniper** (`WID_Sniper_Heavy_Athena_SR_Ore_T03`) | RAGING | HE'S RAGING! | "Now I'm ANGRY!" (`bm_boss_l4`) |
| 5 | 4 | 7 s | 4 | 6 | `WID_Assault_Heavy_Athena_VR_Ore_T03` | all four | Red Fiend, Exploding Brute | P3 + P4 (either): **Rocket Launcher** (`WID_Launcher_Rocket_Athena_SR_Ore_T03`) | UNHINGED | FINAL LEVEL. UNHINGED! | "NO MORE GAMES! EVERYONE, ATTACK!" (`bm_boss_l5`) |

- Boss health per level: the level's spawner spawns with the asked 100000 (the race arena proved the device keeps it);
  each hit deals `MaxHealth / Hits(L)` (the last hit health + shield + 100, as `BossDamage` does). The HUD bar therefore
  reads 50 % / 0 % at L1, 67 / 33 / 0 at L2, 25 % steps at L4-5.
- What advances a level: the boss's `EliminatedEvent` after the team's last hit (backstop: health ≤ 0 polled, as `BossLoop`
  does). Level clear: `RefreshVitals` for every boss-mode player; every gate spawner `Disable()` (monsters vanish in the
  blast); announcer `bm_level_clear`; FlashBig **"LEVEL {L} CLEARED!"** lime 2.5 s; feed **"LEVEL {L} CLEARED!"**;
  `BmRespawnSeconds` (4.0) later `Summon(L + 1)`. L = 5 → Victory.
- Wrong pad: `MissedCurrent`, streak reset, the normal penalty (`Punish` with the arena's station), `Spawn()` once on every
  active gate (respecting cap + 2), feed **"{Who} got {past}  -  BOSS: HA! WRONG!"**, boss cue `bm_boss_wrong` 0.9 s after
  the buzzer. Same question again after the penalty (as the race does).
- Eliminated: `WatchLife` → `Respawned` sends a boss-mode player to the arena entry with the loadout; notice
  **"Knocked out! Back to the arena entry."**; `State.Deaths += 1` (shown on the win screen). No lose state.
- Victory (team): for every boss-mode player not finished: clock stops, `Finished`, medal by first-try accuracy
  (`FnmMedal(FirstTryCorrect, Answered)`), best time saved under id **`boss-battle`** (`FnmSaveBest`), session board
  `Boards[BossBoardKey]` (`BossBoardKey := 9999`), cues `bm_victory` → medal cue (1.6 s apart), `bm_boss_dead` 0.5 s after
  the kill. Board: title **"VICTORY!"**, **"{Medal} MEDAL"**, **"Boss defeated in {Clock}"**, **"Your best   {Clock}   NEW BEST!"**,
  **"Island record   {Clock}  by {Who}"**, **"Right first try: {N} / {Total} ({Pct}%)   -   Best streak {S}   -   Knocked out {D}x"**,
  head **"TOP BOSS TIMES THIS SESSION"**, buttons PLAY AGAIN / CHANGE SKILL. The board holds input (no podium here), like
  the no-podium race board.
- Multiplayer: one shared `Level`, `TeamHits`, boss and monsters for everyone whose `Mode = Boss`; a player who starts
  while a fight is on joins at the current level (their own clock starts then); when the last boss-mode player leaves or
  finishes, everything despawns and the next Start begins at level 1. A run started at `DebugBossLevel > 1` is `Partial`
  (never saved or boarded), like `DebugStartStage`.
- Streak and speed boost work as in the race (first-try right pads build the streak; the streak cues and boost are fun and
  proven). Medal: GOLD all first try, SILVER ≥ 70 %, BRONZE.

## 5. Escalation and caps

A level opens light: at the summon a guard comes out of gate 1 and, on a level with creature kinds (§4), the level's
first creature out of its own gate. The rest come one at a time: `SpawnLoop` (every 0.5 s), while anyone fights, the boss
is up and `Now >= NextSpawnAt`, takes the next open gate round-robin; if `Alive() < MaxAlive(L)` → `SpawnMonster(gate)`
and `NextSpawnAt = Now + SpawnSeconds(L)`; else the gate keeps its turn and `FNM: boss mode monster cap reached at level
{L} ({Alive}/{Max} alive)` is logged once. So the arena fills one monster per 20 s at L1 and per 7 s at L5.
`SpawnMonster` is the only way a monster comes out (the summon and the wrong-answer wave use it too): on a level with
creature kinds the monsters alternate guard, creature, guard, ... and the creatures take the level's kinds in turn; log
`FNM: boss mode monster at gate {G} (kind guard|creature, {Alive}/{Max} alive)` (+ `: {Creature}`), then
`guard up at gate G` / `creature up: {Creature} at gate G`.
- **Guards:** a gate's guard spawner is OFF until its first guard: `Reset()` + `Enable()` (an enabled guard spawner sends
  one guard by itself, seen in play), later guards `SpawnAt(alcove)` (returns at once), a refused `SpawnAt` falls back to
  `Spawn()`.
- **Creatures** (`creature_spawner_device`, which has no `Spawn()` and no Verse type setter, so one device per kind, tag
  `fnm_bm_creature` + slot = kind, standing just inside a gate's alcove mouth: Fiend G1, Brute G2, Ranged G3, Red Fiend
  and Exploding Brute G4 = `FnmBmCreatureGate`, so a kind always comes out of its own gate, which every level that uses it
  opens): a **pulse**: `Enable()`, the device's own first wave (one creature, 0.5-2.6 s later) is awaited on its
  `SpawnedEvent`, `Disable()` at once so no second wave follows; nothing in 6 s → a guard instead. `SpawnAt` was tried and
  dropped (§14).
- `Alive()` = the gate guard spawners' living agents (`GetAgents()` + `IsActive`) + guards and creatures on their way +
  the creature agents the pulses returned that have not been eliminated. Level clear: guard spawners `Disable()`
  (despawn), creature spawners `Enable()` + `EliminateCreatures()` + `Disable()`, counts zeroed. Island cap: 30 guards
  alive; boss mode uses at most 1 + 6 + the wrong-answer wave (+2).

## 6. Level-start summon (`Summon(L)`, about 5 s, every boss-mode player sees and hears it)

| t | What | Device / HUD |
|---|---|---|
| 0.0 | Banner **"LEVEL {L}"** (84 px gold) over the burst texture, sub line (table §4) 40 px white; music bed = level (`SetMusic(Player, L)`); anger ring: slots 1..L `Enable()` + `Restart()`, the rest `Disable()`; log `FNM: boss level {L} summon` | HUD banner (new), `fnm_bm_anger_fx` |
| 0.0 | Announcer: L1 `bm_start` "Boss battle!", else `bm_level{L}` ("Level two!", "Level three!", "Level four!", "Final level!") | audio |
| 0.8 | Boss spawner for L: `Reset()`, `Enable()` (+ `Spawn()` nudge after 5 s as `BossLoop` does); the strike VFX moved to the platform and `Restart()` | `fnm_bm_boss` + slot L, `fnm_bm_strike` |
| 1.5 | Boss line: cue `bm_boss_l{L}`; subtitle (feedback line, orange, 6 s) **"BOSS: {line}"** | audio, HUD |
| 2.5 | Gates 1..Gates(L): gate VFX `Enable()` + `Restart()`; cue `bm_gates`; the first guard out of gate 1 and (L ≥ 2) the first creature out of its gate (§5); feed **"The boss summons his minions!"**; gate VFX `Disable()` 1.5 s later | `fnm_bm_gate_fx`, `fnm_bm_gate`, `fnm_bm_creature` |
| 4.0 | Weapon drop: beacons on the level's perches `Enable()` + `Restart()` (re-`Restart()` every 2 s while lit; others `Disable()`); chest buttons on the lit perches `Enable()`, others `Disable()`; hint (feedback, gold, 6 s) **"WEAPON CHEST: {perch} - jump up and open it!"** with perch names **FRONT-RIGHT PERCH / FRONT-LEFT PERCH / BACK-RIGHT PERCH / BACK-LEFT PERCH / BACK PERCHES** | `fnm_bm_perch_fx` |
| 5.0 | Banner hides; log `FNM: boss level {L} summoned: {Gates} gates, every {Seconds} s, max {Alive} alive, {Weapon} at {perch}` | |

Boss anger that is visible: the weapon climbs, the anger ring grows, the boss line label (**GRUMPY / ANGRY / FURIOUS /
RAGING / UNHINGED**) and the subtitle. (NPC scale, colour and emotes are not controllable from Verse: not attempted.)

## 7. Correct and wrong answers

Right pad (`OnBmPad`, correct): `TeamHits += 1`, `State.Hits += 1`, first-try bookkeeping (streak, cues, boost, feed
milestones as `HandleDoor`); damage the boss; cue `bm_nuke` (stock blast) now, `bm_boss_hit` grunt at +0.4 s (not on the
killing hit), `bm_mega_nuke` + the existing `FnmHitCue(Left)` countdown at +0.9 s (only one voice line: `hits_left1..4`
when Left is 1..4, else `bm_mega_nuke`); HUD `FlashNuke(**"MEGA NUKE!  {Left} TO GO"**)` 2.5 s (last hit of a level:
**"MEGA NUKE!  LEVEL {L} CLEARED!"**; final: **"MEGA NUKE!  BOSS DEFEATED!"**); white screen flash 0.5 s; player back to
the entry; `FireCannons(BmRig, ...)` + nuke VFX at the boss's feet + both blasts; `KnockBoss` (existing); feed
**"{Who} nuked the boss!  Level {L}: {Team}/{Need}"**; next question; log
`FNM: boss mode hit {N} by the player (level {L}, team {T}/{Need}), damage {D}, health {P}%`.

Weapon grab (`OnChest`, the chest button's `InteractedWithEvent`, 1 s hold): a boss-mode player opens perch P's chest
when P is lit for the level and they have not taken this level's weapon: fire grant trigger L for them,
`TakenLevels[L] = true`, cue `bm_weapon`, FlashVerdict-style notice **"{Weapon} GET!"** (gold, via FlashBig 1.5 s), feed
**"{Who} grabbed the {Weapon}!"**, log `FNM: boss mode weapon {Weapon} granted from chest {P} (level {L})`; taken
already: **"You already have the {Weapon}!"**. Standing on a lit perch without it (`OnPerch`): **"OPEN THE CHEST! (hold E)"**.
Seen in play 2026-10-10: the prompt OPEN WEAPON CHEST, the SMG equipped in slot 3 with its ammo, the feed line.

Wrong pad: §4.

## 8. Verse architecture

- `console/verse/fnm_bossmode.verse` (new): `fnm_bm_level` struct + `FnmBmLevels()` (the §4 table), `FnmBmPerchName(P)`,
  `FnmBmBossLineText(L)`, `FnmBmLevelCue(L)`, `FnmBmBossCue(L)`, `FnmBmPerchesFor(L)`, `FnmBmWeaponName(L)`,
  `fnm_bm_arena := class` (Station: fnm_station from `FindStationParts(fnm_bm)`, BossSpawners[5], GateSpawners[4],
  GateFx[4], PerchTriggers[4], PerchFx[4], GrantTriggers[5], AngerFx[5], the cannon rig), `fnm_boss_mode := class`
  with `Director : fnm_director`, the shared state (`Level`, `TeamHits`, `BossAlive`, `BossAgent`, `AliveMonsters`,
  `NextSpawnAt`, `Fighting : int`), `Build()`, `Start(State)`, `OnPad(State, DoorIndex)`, `OnPerch(State, P)`,
  `Summon(L)`, `LevelCleared()`, `Victory()`, `SpawnLoop()`, `BossLoop()` (boss line refresh, backstops), `Leave(State)`.
  Feed `<localizes>` messages for the mode. Verse tags `fnm_bm_*` in `fnm_tags.verse`; cues in `fnm_audio.verse`.
- `fnm_director.verse` edits: `fnm_mode := enum{Race, Boss}`; `fnm_player_state` gains `var Mode`, `var Level`, `var Deaths`,
  `var Answered`, `var BmDecks`, `var TakenLevels : [int]logic`, `var BossBest : float`; `var BossMode : ?fnm_boss_mode`
  built at OnBegin; `DebugAutoBoss`, `DebugBossLevel`, `BmRespawnSeconds`, `BmSummonSeconds`, `NukeSeconds` @editables;
  `BeginPicking` / `OnPickerChoice` routing; `fnm_bm_pad_handler` / `fnm_bm_perch_handler` classes; `ShowCurrent` caption
  by Mode; `StationOccupied`, `RaceEntry` ("BOSS L{L}" tail), `Respawned`, `WatchDoors`, `WatchSkip`, `OnPlayerRemoved`
  honour Mode; `FireCannons` takes a rig (`fnm_cannon_rig` class: Fx, Strike, StrikeHome, Blasts, Nuke) so the race arena
  and boss mode share it; `ChangeSkill` leaves the mode; `DebugAutoRight` → `DebugBossModeRun` when `Mode = Boss`.
- `fnm_ui.verse` edits: `fnm_pick.Boss`, `fnm_pick.Again`; `ShowGradeStep(Grades, WithBoss)`; banner widgets
  (`BannerArt` = `FNM_Art.T_fnm_banner` 1024x256 stretched to 900x200, `BannerText`, `BannerSub`; canvas slot anchored
  (0.5, 0.52) since B5, collapsed) with `ShowBanner(Big, Sub)` / `HideBanner()` (while it is up the verdict image is
  collapsed: `BannerUp`); `FlashNuke(Label)` (verdict slot, image
  `FNM_Art.T_fnm_nuke`, lime, `NukeSeconds`); `WhiteFlash : color_block` + `Flash(Seconds)` (opacity 0.85 → 0 in 0.05 s
  steps); `ShowResults` gains a `Title` parameter ("FINISH!" at the race call site, "VICTORY!" in boss mode);
  `AgainButton : button_loud` "PLAY AGAIN" on the finish-buttons root, `ShowFinishButtons(WithChange, Again)`.
- Test hooks (ship values): `DebugAutoBoss` false, `DebugBossLevel` 0. `DebugAutoRightAnswers` + `DebugAutoBoss`
  = `DebugBossModeRun`: 8 s after the start, step on the right pad every 5 s (wait up to 12 s for a boss), until Victory
  (`FNM: debug boss mode done: victory=yes level=5`) or three pads in a row that moved no hit
  (`FNM: debug boss mode stuck at level {L}`), cap 40 pads.

## 9. HUD elements (new)

| Element | Where | Copy |
|---|---|---|
| Picker button | grade step, top | **BOSS BATTLE** / caption **Every grade, every skill. Right answers NUKE the boss!** |
| Tag | top left | **BOSS BATTLE** / **Every skill, every grade** |
| Slate caption | slate | **BOSS BATTLE  -  Level {L}/5  -  {Title}** |
| Boss line | slate last line | **BOSS  ████------  40%   -   LEVEL 3: FURIOUS   -   hits 1/3**; no boss: **BOSS  is getting up ...   -   LEVEL 3: FURIOUS** |
| Banner | centre, y 0.52 (between the slate and the verdict label), ~900 x 200 burst texture; the verdict image hides while it is up | **LEVEL {L}** / sub from §4 |
| Nuke verdict | verdict slot | mushroom-cloud icon + **MEGA NUKE!  {Left} TO GO** |
| Start flash | verdict slot 4 s | **STEP ON THE RIGHT ANSWER!** + feedback **Bullets can't hurt the boss. Step on the pad with the RIGHT ANSWER to nuke it!** |
| Weapon hint | feedback line, gold, 6 s | **WEAPON CHEST: FRONT-RIGHT PERCH - jump up and open it!** |
| Win board | finish board | title **VICTORY!** + lines in §4; buttons **PLAY AGAIN**, **CHANGE SKILL** |

Textures (B3, `tools/make_boss_art.py`, no PIL, deterministic, imported by the existing `python tools/import_art.py`
which takes every `tools/art/fnm_*.png`): `fnm_banner.png` 1024 x 256 RGBA (a jagged comic burst, red core to orange
spikes, dark 6 px outline, transparent outside) and `fnm_nuke.png` 256 x 256 RGBA (a mushroom cloud: cap, stem, base
ring in pale yellow with a dark outline, transparent outside).

## 10. Audio: new cues (append to the `fnm_cue` enum after `BossDown`, exactly this order)

| # | Enum / id | Moment | Stock sound (`tools/build_audio.py` CUES) | Voice (`ANNOUNCER_CUES` / `BOSS_CUES`) |
|---|---|---|---|---|
| 47 | `BmStart` / `bm_start` | mode start, L1 summon | `/Game/Sounds/Creative/Gadgets/Radio/Stingers/Stinger_Threat_01` (as boss_fight) | announcer **"Boss battle!"** |
| 48 | `BmLevel2` / `bm_level2` | L2 summon | `Modes/Match/Match_Round_Change_01_Cue` | announcer **"Level two!"** |
| 49 | `BmLevel3` / `bm_level3` | L3 summon | same | announcer **"Level three!"** |
| 50 | `BmLevel4` / `bm_level4` | L4 summon | same | announcer **"Level four!"** |
| 51 | `BmLevel5` / `bm_level5` | L5 summon | same | announcer **"Final level!"** |
| 52 | `BmBossL1` / `bm_boss_l1` | boss line L1 | none (voice only) | boss **"You dare challenge ME?!"** |
| 53 | `BmBossL2` / `bm_boss_l2` | L2 | none | boss **"Minions! GET THEM!"** |
| 54 | `BmBossL3` / `bm_boss_l3` | L3 | none | boss **"Is that all you've got?!"** |
| 55 | `BmBossL4` / `bm_boss_l4` | L4 | none | boss **"Now I'm ANGRY!"** |
| 56 | `BmBossL5` / `bm_boss_l5` | L5 | none | boss **"NO MORE GAMES! EVERYONE, ATTACK!"** |
| 57 | `BmBossWrong` / `bm_boss_wrong` | wrong pad, +0.9 s | none | boss **"HA! WRONG!"** |
| 58 | `BmBossHit` / `bm_boss_hit` | right pad, +0.4 s | none | boss **"ARGH!"** |
| 59 | `BmBossDead` / `bm_boss_dead` | final kill, +0.5 s | none | boss **"NOOOOO!"** |
| 60 | `BmNuke` / `bm_nuke` | right pad, at once | `Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_01` | — |
| 61 | `BmMegaNuke` / `bm_mega_nuke` | right pad, +0.9 s when Left > 4 or 0 | none | announcer **"MEGA NUKE!"** |
| 62 | `BmLevelClear` / `bm_level_clear` | level clear | `Gadgets/Radio/Stingers/Stinger_Success_03_Cue` | announcer **"Level cleared!"** |
| 63 | `BmVictory` / `bm_victory` | victory | `Modes/Match/Match_Win_01_Cue` | announcer **"VICTORY! Boss defeated!"** |
| 64 | `BmGates` / `bm_gates` | gates open at a summon | `Gadgets/SlidingDoor/SlidingDoor_Open_Cue` | — |
| 65 | `BmWeapon` / `bm_weapon` | weapon granted on a perch | `Toys/PowerUp/Creative_PowerUp_Collect_Cue` | — |

Rules: snake ids follow `tests/test_audio_cues.py::snake` (`BmBossL1` → `bm_boss_l1`); the four lists (enum, `FnmCueIds`,
`FnmCueTags`, `CUES`) stay in this order; music beds are the existing `music_t1..t5` by level. Announcer lines: Kokoro
`am_michael`, the existing `std`/`big` profiles. Boss lines: a new `boss` mastering profile in `tools/make_announcer.py`
(pitch about 18 % down via `asetrate`, the `big` echo, a touch of saturation) rendered for all three voices; the wired boss
voice is **`am_onyx`** (`build_audio.py --boss-voice am_onyx`, `BOSS_CUES` = the eight `bm_boss_*` ids). Importing wavs is
the GUI step in `console/AUDIO.md` "Announcer" (B4 does it, as 2026-10-07 and 10-08 did); until imported, voice-only cues log
`(not wired)` and the mode still plays.

## 11. Builder tool: `tools/build_bossmode.py`

Idempotent via actor tag `fnm_bossmode` (deletes everything with it first), imports helpers from `build_course` (box, device,
props, verse_tags, ref, SCENE/ACTOR/OBJ/DEV, TRIGGER/TELEPORTER/BILLBOARD, LETTER_COLOURS, PAD_SIZE, PAD_H), `build_guards`
(SPAWNER, SETTINGS, WEAPONS), `build_rigs` (GRANTER, TRIGGER_CLASS), `build_pickups` (GRANT_SETTINGS), `build_cannon`
(shape, aim, settings, VFX, EXPLOSIVE, BLAST, STRIKE_FX, MUZZLE_FX, cannon with a prefix). Materials needed:
`python tools/import_art.py bm_wall bm_floor bm_perch` (new `WALL_COLOURS` keys: `bm_wall` (0.12, 0.10, 0.14),
`bm_floor` (0.22, 0.20, 0.24), `bm_perch` (1.0, 0.8, 0.1)) plus the existing `steel`, `glow`, `pad_a..d`. `--check` lists
what is placed with read-back options; `--probe` runs the §3 UNVERIFIED probes and prints answers (no build).
Needs the `fnm_bm_*` tags compiled in the project first (B0): `verse_tags` references `/<module>/_Verse.fnm_bm_gate` etc.

## 12. Acceptance (headless; B4 runs them; the parent re-runs the first two)

Before: `fnm_director.verse` defaults flipped with `tools/patch.py`: `DebugAutoBoss` → true, `DebugAutoRightAnswers` → true;
`.venv/Scripts/python -m fnm sync starter`; `.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'` → `[]`.

1. **Full run to victory.**
   `.venv/Scripts/python tools/playtest.py --until "boss mode victory,debug boss mode stuck" --timeout 420 --frames "boss mode start:2,boss level 2 summoned:1.5,boss mode hit 3:0.8,boss mode victory:2.5"`
   (the auto-run never climbs a perch, so no weapon frame here; acceptance 5 covers it)
   Expected log, in order: `FNM: boss mode: arena found: 4 pads, 4 gates, 4 perches, 5 boss spawners, 5 granters, 2 cannons`
   (at OnBegin), `FNM: boss mode start for the player (level 1)`, `FNM: boss level 1 summoned: 1 gates, every 20 s, max 2 alive, SMG at FRONT-RIGHT PERCH`,
   `FNM: boss spawned` lines, `FNM: boss mode hit 1 ... (level 1, team 1/2)`, `FNM: boss mode monster at gate 1 (1/2 alive)`,
   `FNM: boss level 1 cleared`, `FNM: boss level 2 summoned: 2 gates, every 15 s, max 3 alive, Pump Shotgun at FRONT-LEFT PERCH`,
   ... `FNM: boss level 5 cleared`, `FNM: boss mode victory in M:SS.s, GOLD, right first try 16/16, best streak 16, deaths 0, new best yes, record yes`,
   `FNM: debug boss mode done: victory=yes level=5`. Cue lines: `FNM: cue bm_start`, `bm_level2`.. `bm_level5`, `bm_nuke` x16,
   `bm_mega_nuke` or `hits_left*` per hit, `bm_level_clear` x4, `bm_victory`, `bm_boss_dead`.
   SEEN in the frames: frame 0 the STEP ON THE RIGHT ANSWER! flash with the BOSS BATTLE tag and the slate caption
   "BOSS BATTLE  -  Level 1/5  -  <a skill title>"; frame 1 the LEVEL 2 banner over the burst texture with "HE'S ANGRY!";
   frame 2 the mushroom-cloud icon with "MEGA NUKE!  N TO GO" and the laser beams / strike in the arena; frame 3 the VICTORY!
   board with PLAY AGAIN and CHANGE SKILL.
2. **Race untouched (sabotage-style regression).** With `DebugAutoBoss` false and `DebugAutoPick 0` + `DebugAutoRightAnswers`
   true: `tools/playtest.py --until "finished run 2,stuck at stage" --timeout 400` finishes run 2 as before and the arena lines
   `FNM: cannons fired (2 muzzles, blast N)` still appear 5 times per run; `tests/` 8699 → more, none red.
3. **Picker shows the mode.** All hooks at ship values: `python tools/click_hud.py launch` → read `%TEMP%\pick0.png`: a gold
   BOSS BATTLE button above "Grade 6" / "Grade 7" with its caption; click it → log `FNM: boss mode start for the player (level 1)`
   (asks Aaron first: it takes the foreground).
4. **Wrong pad.** `DebugAutoBoss` true, `DebugAutoWrongAnswers 2`: two `FNM: debug auto-wrong` lines each followed by
   `FNM: penalty ...`, `FNM: boss mode wave: N monsters spawned`, `FNM: cue bm_boss_wrong`; the player is back at the arena entry.
5. **Weapon perch (keys).** `DebugAutoBoss` true, `DebugBossLevel 1`: `tools/playtest.py --after "boss level 1 summoned" --keys "D:1.2,W+SPACE:3"`
   (or whatever B4 finds reaches P1 from the entry; ask Aaron first); expect `FNM: boss mode weapon SMG granted at perch 1 (level 1)`
   and the frame shows the SMG in the hotbar. If the keys cannot climb it, that is the §3 jump assumption failing: lower
   `STONE_RISE` / `STONE_GAP` and rebuild.
6. **Unit tests.** `.venv/Scripts/python -m pytest -q`: `tests/test_bossmode.py` (B1), `tests/test_bossmode_layout.py` (B2),
   `tests/test_audio_cues.py` (extended MEMBERS), `tests/test_hud_layout.py` (two new PNGs) all green.

## 13. Open / UNVERIFIED list (collected)

- UEFN's MCP did not answer during planning (port 8000 listening, every call timed out after 600 s): a modal dialog in the
  editor is the usual cause (uefn-mcp skill). B0 must screenshot UEFN and dismiss it before the first BuildAll.
- Device catalog: creature / wildlife spawner (not used this round), VFX `visual_Effect` entries beyond LaserBeams and
  LightningBolt_01..03, explosive `knockback` "Large", `item_spawner_device` control from Verse (not used).
- `guard_spawner_device.Spawn()` with `spawnOnTimer False` (fallback in §3); `spawnCount` as an alive cap (the director caps anyway).
- The granter accepts the five weapon WIDs (read back; else swap for the nearest accepted rarity).
- A kid can chain 60 cm / 150 cm hops (B4 keys test; fallback 50 / 100).
- `fort_character.SetMaxHealth` is not relied on; boss health per level is the spawner's asked 100000.
- Camera shake and NPC colour/scale: no Verse API known; not attempted.
- The burst-texture banner and the mushroom icon are only judged in B4's frames; the `visual_Effect` of the nuke is whatever
  the enum offers.

## 14. Shipped — where it differs (fill in after the build)

(B4 and the parent write here what landed differently from this plan and why.)

B4, 2026-10-09 (UEFN 42.30, headless; frames are `%TEMP%\pt_frame*.png`, logs `%TEMP%m_run1/2/4.txt`):
- **Compile fix (one line, fnm_ui.verse `Flash`):** `SetOpacity` takes `type{_X:float where 0.0 <= _X, _X <= 1.0}`, not
  `float` (error 3509). Now `if (Op := type{_X:float where 0.0 <= _X, _X <= 1.0}[0.85 * (Steps - K) / (Steps * 1.0)]) then
  WhiteFlash.SetOpacity(Op)`: a failable refinement cast, which compiles. B1's other two worries were fine: the
  `FnmBmLevels()` `array:` block and the mixed int/float expression both compiled.
- **Acceptance 1 (full run) passed:** victory in 1:23.2, GOLD, 16/16, `debug boss mode done: victory=yes level=5`, five
  levels summoned and cleared in order, 16 `cannons fired` + `mega nuke` pairs. SEEN: the slate caption `BOSS BATTLE - Level
  N/5 - <skill>`, the BOSS BATTLE tag under GAME MODE ("Every skill, every grade"), the boss bar (`BOSS ### 67% - LEVEL 2:
  ANGRY - hits 1/3`), the LEVEL 2 banner on the orange burst with "HE'S ANGRY!", the cream mushroom-cloud icon with
  `MEGA NUKE!  N TO GO`, a cannon beam crossing the arena, and the VICTORY! / GOLD MEDAL board with PLAY AGAIN and CHANGE
  SKILL. **Not seen:** the start flash. The frames land about 5 s after their log line, so frame 0 (`boss mode start`
  +2 s) shows LEVEL 1 CLEARED.
- **No `boss mode monster at gate` line in any run.** `OpenGates` spawns one monster per gate without logging it, and wrong
  pads add waves. Those fill the alive cap: the level-1 minimap showed 2 red markers, and the cap is 2. In the auto-run a
  level also clears 8-11 s after its summon, before most `SpawnSeconds` run out. `AliveMonsters` is not logged, so the
  timed spawns are still unproven.
- **Layout and HUD, seen in frames:** the LEVEL banner overlaps the slate's STREAK and boss rows (frame 2 of run 1). On the
  frame after the killing hit, the boss bar still read `50% - hits 1/2` while the log said health 0%; it is refreshed by
  BossLoop, not on the hit.
- **Audio:** `build_audio.py --announcer am_michael --boss-voice am_onyx` placed every cue device: 56 of 65 wired, 0
  read-back mismatches. The 9 with no stock stand-in (`bm_boss_*`, `bm_mega_nuke`) log `(not wired)` until the wavs are
  imported. The GUI wav import was NOT run, because Aaron was at the keyboard (idle 9-48 s at every check).
- B2's probe answers (LAYOUT.md "Boss battle arena"): the nuke VFX is Small_Fire at scale 6 (the enum has no explosion);
  the blast knockback is Medium (there is no "Large"); the granters accepted all five WIDs; creature spawners exist but
  are not used.

B5, 2026-10-09 (UEFN 42.30, headless; logs in the session scratchpad `run2_keep.txt` / `race.txt`, frames `%TEMP%\pt_frame*.png`):
- **Creatures from the gates (Aaron's "monsters and npcs").** Level kinds (§4): L1 guards only, L2 Fiend, L3 Fiend +
  Brute, L4 Ranged + Brute, L5 Red Fiend + Exploding Brute; no Megabrute. Five `creature_spawner_device`s, one per kind
  (the Verse API has no `Spawn()` and no type setter), just inside a gate alcove's mouth (Fiend G1, Brute G2, Ranged G3,
  Red Fiend + Exploding Brute G4), tag `fnm_bm_creature` + slot = kind. **Differs from the brief:** not one creature spawner
  per gate, and no `SpawnAt`: in play `SpawnAt` was refused unless the device stood on the ground (40 m down and 5 m under
  the slab: refused), a player was inside its activation range (1: refused; 100: fine) and it had been on for a moment;
  when it took, the call never returned (30 s) and a second creature followed. What works: a **pulse**, `Enable()` → the
  device's own first wave (one creature; 18 of 18 in the full run, 0.27-1.47 s after the Enable, 2.6 s in an earlier test) → `Disable()`; the creature stays
  until `EliminateCreatures()` at the level clear (logged eliminated at every clear). A creature that does not come in 6 s
  becomes a guard (happened 0 times in the full run after the devices moved from the alcove back to the mouth; at the back
  the Brute failed twice).
- **Guards:** `Enable()` on a gate's guard spawner sends one guard by itself (so the old "Reset + Enable + Spawn" put 2 out
  of each gate and every level opened at its cap: L3 read 5/4 alive in the first run). Now a level opens with one guard
  (gate 1) and, from L2, one creature; the rest come one per `SpawnSeconds`, round the gates, alternating guard and
  creature, up to the cap. A gate's spawner is switched on at its first guard; later guards are `SpawnAt` (returns at once).
  `Alive()` counts the gate spawners' living agents (`GetAgents`), pending spawns and the creature agents. One guard
  `SpawnAt` was refused in the full run (`spawn limit 1`, L5) and fell back to `Spawn()`.
- **Timed spawns proven** (full run, hold 20 s): L1 `monster at gate 1 (kind guard, 2/2 alive)` 20.0 s after the summon
  line, then `cap reached at level 1 (2/2)`; L4 a monster every 9 s (`19.4`, `28.4`, `37.4`, `46.5`, `55.4`, `04.5`) to
  `cap reached at level 4 (5/5 alive)`; L5 every 7 s to `6/6`. Victory 9:13.4, GOLD 16/16, `debug boss mode done:
  victory=yes level=5`.
- **New hook** `DebugBossHold` (float, ship 0.0): the boss auto-run waits that long with the boss up before each pad.
- **Banner** moved from y 0.33 to 0.52 (between the slate and the verdict label); while it is up the verdict image (check,
  cross, mushroom) stays collapsed (`BannerUp`). SEEN: LEVEL 2 / HE'S ANGRY! and LEVEL 3 / HE'S FURIOUS! burst at about
  y 470-655 at 1080p, the slate's bottom row at about 350-380 above it, nothing overlapping.
- **Boss bar** refreshes on every hit and on the kill (`RefreshBossLines`); after a kill it reads `BOSS ---------- 0% -
  LEVEL 4 CLEARED!` (SEEN in the frame after the L4 kill), until the next summon.
- **Blasts** knockback High (read back on both). Arena now 118 actors.
- **Seen but not changed:** creatures were logged `eliminated by something else` 6-16 s after coming out, most likely by
  the gate guards (Wildlife & Creatures team) or the boss: so creatures often die before reaching the player. Kid-friendly,
  but a creature-heavy level reads lighter than its cap. In the hold run the auto-player was knocked out 10 times (it never
  fights back).

B6, 2026-10-09 (UEFN 42.30; logs and frames in the session scratchpad `b6_*.txt`, `%TEMP%\b6_a10\`, `%TEMP%\pick1.png`):
- **Teams: already allied; the deaths were friendly fire.** Gate guards and bosses were already on `Team Wildlife &
  Creatures` (read back), and the creature spawner has no team option. New log lines (`boss mode team: ...`, from
  `fort_team_collection`) show the boss, the guards and every creature on the same team (2), `friendly` to each other and
  `hostile` to the player. A new killer classifier (`creature eliminated by a gate guard / the boss / a creature / itself /
  no source / a player`) then showed what B5 logged as "something else": in a level-5 hold run, 3 Red Fiends were killed
  by a gate guard. The guards' LOW-accuracy shots at the player hit the melee creatures chasing the player. The
  island's `bAllowFriendlyFire` is already false and does not cover AI. **Fix:** `OnAllyDamaged` heals a gate guard or a
  creature straight back after damage from any agent that is not a player (their `fort_character.DamagedEvent`). The
  level-clear line now reads `boss level L cleared (friendly fire healed N hits)`. Same hold run after the fix: 0 kills
  by a gate guard (393 hits healed). The kills left are Exploding Brutes blowing themselves up (`no source`), one Red
  Fiend caught in that blast (`a creature`; a single lethal hit cannot be healed), and the clear's own
  `EliminateCreatures` (`itself`). The race guards (`build_guards.py`) are unchanged.
- **Dropped guns:** Verse cannot remove a dropped pickup (Fortnite digest 42.30 has no call for one), so the gate guards
  now drop nothing (`GATE_SETTINGS dropInventoryOnElimination False`; §3 said True). The boss already dropped nothing.
  The player's weapons come from the perches. The race guards still drop theirs.
- **Perch climb (acceptance 5) passed after two fixes.** (1) The hidden triggers sensed only their StepBox component
  (64 x 64 x 15 cm half-extents at +32 cm, scaled with the actor), not a 600 cm zone per unit scale. On the 3 m perch,
  the trigger therefore covered a 64 cm square, 10 cm thick. A player traced standing on P1 89 cm from its centre for
  7 s never triggered it. `trigger_fit` now sizes every pad and perch trigger to the box asked for. The boss auto-run
  teleported the player to the pad trigger's origin, which is now under the floor, so `DebugAutoBoss` now teleports to
  the pad's x/y at the entry's floor + 1 m. (2) Stones: 50 cm rises, 100 cm gaps, and stones 300 cm wide (as wide as the
  perch). The old setup was 60 / 150 with 120 cm stones. On the old chain the keyed player reached the top stone and then
  stood against the perch's face, most likely after falling into the 150 cm gap. That cause is not proven: it is read
  from the frames, not traced. Keys `D:1.6,D+SPACE:1.0,D+SPACE:1.0,D+SPACE:1.0` from the entry produced
  `boss mode perch 1 reached (level 1)` and then `boss mode weapon SMG granted at perch 1 (level 1)`. SEEN: "SMG GET!",
  the SUBMACHINE GUN equipped in hotbar slot 3, and the feed line "grabbed the SMG!". New log line on every perch touch:
  `boss mode perch P reached (level L)`. Arena now 122 actors.
- **Picker click (acceptance 3) passed:** all hooks at ship values. SEEN: the BOSS BATTLE button above GRADE 6 / GRADE 7
  with its caption. After the click: `boss battle chosen`, then `boss mode start for the player (level 1)`. The next frame
  shows the LEVEL 1 / HERE HE COMES! burst, the STEP ON THE RIGHT ANSWER! flash (seen for the first time), the slate
  caption, and the boss subtitle "BOSS: You dare challenge ME?!".
- **Voice:** the 16 waves were imported through the GUI (am_michael now holds 45, am_onyx 8, all saved).
  `build_audio.py --announcer am_michael --boss-voice am_onyx` wired 65 of 65 cues with 0 mismatches, and `--list` reads
  back the same. Heard on the loopback (matched filter `hear_voice.py` with a 4.8 s window; noise / control 0.00-0.13):
  bm_mega_nuke 0.67-0.78; bm_boss_l1 0.64 and bm_start 0.50 after a real picker click; bm_boss_l2 0.57, l3 0.47,
  l4 0.41, l5 0.49; bm_boss_hit 0.37-0.48; bm_level_clear 0.37-0.45; bm_level2-4 0.36-0.43. With `DebugAutoBoss`,
  bm_start and bm_boss_l1 score 0.06: they fire in the same second as the join (welcome, music_t1 and the client's audio
  start-up). That is a debug-hook artefact, because the picker flow plays both. The repo's `hear_voice.py` window
  (t + 2.5 s) is shorter than the 2.4-3.6 s boss lines and scores them near 0; the B6 copy widens it to t + 4.5 s.
- Full run with the new arena: victory in 1:23.3, GOLD, 16/16. Race regression: two finished runs (1:29.8, 1:26.7, GOLD
  10/10), only the three OnBegin boss-mode lines, and 10 `cannons fired` lines.

## 15. Bigger boss, boss bar, visible lasers (2026-10-10)

Aaron: "make boss bigger and more epic model if possible. hard to even tell he is the boss. and make healthbar more
noticeable. and attacks on him more obviously coming from the side laser cannons".

- **The boss is a Megabrute.** A guard cannot be made bigger: Guard Spawner V2 has no size option, and the 42.30 Verse
  digest has no character scale. The five per-level guard boss spawners are gone. In their place is one creature spawner
  (`Megabrute`, tag `fnm_bm_megaboss`) on a platform raised from 1 m to 3.5 m. `SpawnBoss` pulses it (Enable, then
  Disable on its SpawnedEvent). `OnBossSpawned` sets its max and current health to 100000 and pins it in place
  (`PinBoss`: teleport home, `PutInStasis` with turning allowed). Any damage that does not come from a pad is healed
  straight back (`OnMegabossDamaged`; `PadHitting` lets the pad's own `Damage` through), so bullets do nothing and a
  player who shoots it gets the pad hint. `KnockBoss` releases the pin for the knock and pins it again after the stun.
  `BossLoop` puts it back on its spot when it ends up more than 1.5 m away, 1.5 s or more after a hit. The boss weapon
  per level (table §4) no longer applies: the Megabrute has no gun and its melee cannot reach a pad.
- **Boss bar** (`fnm_hud.SetBossBar` / `HitBossBar`): along the bottom edge, centred at x 900. It reads
  "MEGABRUTE BOSS - LEVEL L: <ANGER>" over a 680 x 44 red bar on a gold frame, with "40% - hits 1/3" on the bar. The fill
  flashes white and gold on every hit. The slate's old BOSS text line is no longer used in boss mode; the race arena
  still uses it.
- **Beams** (`fnm_director.FireBeam`): each cannon fires 3 shots per hit. A shot grows out of the muzzle to the boss in
  0.15 s, holds for 0.35 s, then goes dark. The strike and the blasts land as the first shot arrives. The beam is a
  gallery prop because Verse can move only creative props. The Glow Rings beam materials render as a checker on a
  gallery prop, and the Tech primitives refuse a colour (both probed), so the beam uses the Alphabet "I" in its own
  Neon Green, scale 2.
- `python tools/build_bossmode.py --boss` re-places the platform, the boss and the beams on their own (idempotent via
  `fnm_bm_bossrig`).
- **Seen in play** (headless, `DebugAutoBoss` + `DebugAutoRightAnswers` + `DebugBossHold 4`):
  - The Megabrute spawns on the pedestal with health 100000.
  - Hit 1 takes it to 50% and the bar shows it. The first run healed the pad's own hit back, so the bar stayed at 100%;
    `PadHitting` fixed that.
  - Hit 2 clears level 1 and the level-2 boss spawns.
  - The thick green beams from both sides meet at the boss during the nuke.
  - The knock moves it 64 cm and it stays on the pedestal.
- **Not seen yet:**
  - Hits 3 to 16 since the pedestal.
  - A whole run to VICTORY.
  - A player shooting the boss (heal plus hint).
  - Whether `MoveTo` animates the beam's scale or the beam pops to full length.
  - A full `build_bossmode.py` (only `--boss` ran).
  - How big the boss reads to Aaron: about 3 m tall on the pedestal, 45 m from the entry.

### 15a. Making the boss bigger: what works (2026-10-10, Aaron: "investigate ways to scale the model, there must be some way")

All probes ran in play. The general findings are in the `uefn-mcp` skill, "Scaling characters and custom skeletal meshes".

| Route | Result |
| --- | --- |
| Scale the Megabrute through its entity (`fort_character.GetEntity` + `SetGlobalTransform`, scale 3 and 6) | Reads back 6, looks unchanged, back to 1 within 3 s |
| Scale the creature spawner actor 3x | The spawned creature is still scale 1 and looks unchanged |
| Animated Mesh device with Fortnite's Swarm Boss mesh (`TidalCrane_Boss_Creature`) at 2.5x | Looks right in the editor (a ~10 m alien over the letters), but play is refused: "Validation failed", illegal asset |
| Animated Mesh device with a **mesh imported into the project** (Blender test column, 2.5x) | **Passes validation and renders in play, 7.5 m tall** over the Megabrute |

**The plan.** A giant stand-in shows on the pedestal and the real Megabrute stays inside it, hidden. The Megabrute keeps
the health, the bar and the clear logic.
- The stand-in is an imported, rigged monster on an Animated Mesh device, scaled to ~8-10 m.
- Animations: idle, a roar on each hit, death on the clear. These are separate devices swapped by Verse with
  `TeleportTo`; the device's Verse API is only Play, Pause and PlayReverse.
- The knock moves the device with `MoveTo`.
- The model comes from Meshy. That needs Aaron's go-ahead on credits.
- Import the art into a folder that is not a Verse identifier: `FNM_BossArt`, not `fnm_boss`, which collided with the tag.

### 15b. The Magma Titan (2026-10-10)

Aaron: "the chests are really big so i dont understand why we cant scale if the chests appeared to be scaled. proceed with
creating awesome boss monster for us to fight. make it epic. and get it idle and flailing and angry animations."

A chest is a placed actor, and a placed actor keeps its scale. A character is spawned by the game at a fixed size and
does not (§15a). So the titan uses the chest's trick: it is placed devices, scaled.

- **The art.** Meshy, 62 credits:
  - a concept image (nano-banana-pro, 9);
  - image to 3D, textured, 40k triangles (30);
  - a rig (5);
  - six animations at 3 each (18): idle 0, Electrocution Reaction 172 (the flail), Angry Ground Stomp 255,
    Chest Pound Taunt 88, Knock Down 187, and (later the same night) Dead 8 (the fall).

  Task ids are in `art/boss/meshy_tasks.json`, the concept in `art/boss/concept.png`, the clips used in
  `art/boss/raw`. A horned obsidian-and-lava demon, 3 m tall as imported.
- **Import.** `python tools/import_boss.py` brings each clip FBX in with its own mesh and skeleton
  (`FNM_BossArt/Clip_<clip>`: `SK_fnm_titan_<clip>`, `A_fnm_titan_<clip>`). Then `build_bossmode.py --boss` places
  `FNM_BM_Titan1..4` on the platform, scale 4, facing the entry. The platform is back down to 1 m: on the 3.5 m
  pedestal the 12 m titan's head and chest sat behind the question panel at the player's eye line.
- **Runtime** (`console/verse/fnm_titan.verse`). The Megabrute still spawns, pinned and hidden (`Hide()`), and keeps the
  health, the bar and the level clears. The titan shows one clip at a time:
  - stomp when a level's boss arrives;
  - flail for 4 s from each right pad, then stomp;
  - stomp on a wrong pad;
  - at a level clear, the killing hit's flail for 1.5 s, then the fall (3 s); it lies at least 1.5 s more, and the next
    level's Arrive waits for that before its stomp (the next boss is summoned 4 s after a clear). The victory's reset
    leaves it lying;
  - idle otherwise.

  A right pad's explanation shows 2.5 s after the hit (`ExplainDelaySeconds`), so the nuke and the flail are not
  behind the grown answer panel (Aaron: "yes delay the explanation"); it is skipped if they answered again meanwhile.

  The boss bar reads THE MAGMA TITAN. The beams aim at its waist (`BEAM_AIM` 450): higher up, they met behind the answer
  panel, which grows for the first seconds after a right pad.
- **Device findings** (titan self-test frames; the general ones are in the `uefn-mcp` skill):
  - Verse `Play()` never started a device placed Stopped.
  - `PlayReverse` threw a looping clip flat and upside down.
  - A clip parked 30 m under the floor came back in a broken pose.

  So every clip starts Playing and loops. Verse only swaps them with `TeleportTo`, and a resting clip is shrunk to
  0.001 at home. The fall is the exception: placed Playing with loop off, it plays itself down at the session start and
  holds. `Play()` does not restart a finished clip (four frames after `Play()`, all lying), but `PlayReverse()` runs it
  back to standing and `Play()` then falls again (self-test frames). So the titan rewinds it, shrunk, at the build and
  after each fall, and `Play()`s it at the next clear.
- **Not used:** Chest Pound and Knock Down (Dead 8 replaced it as the defeat and plays correctly). On the device the chest pound tipped the titan flat for about 2 s of every
  loop. The knockdown turned on the spot and never fell. Both happened imported against the rig file's skeleton and
  against their own, and after a Blender round trip (which also turned the mesh around). The cause is not found; the
  FBX files are sound in Blender. Their files are in `art/boss/unused` (git-ignored).
- **Seen in play** (headless, `DebugAutoBoss` + `DebugAutoRightAnswers`):
  - A full run to VICTORY, 16/16 hits.
  - The titan standing over the pads, under the panel, when no answer feedback is up.
  - Idle, flail and stomp each sampled over 12 s, upright throughout.
  - The flail on a hit, with the blast.
  - A beam reaching the waist, thin from the entry's angle.
- **Seen in play, second pass** (same night): a VICTORY run with the titan lying after level 1 and caught mid-fall at
  level 4 (so the rewind works across levels); the wrong-pad stomp under a FROZEN penalty; every explanation up 2.4 to
  3.0 s after its hit (log `boss mode explanation up`).
- **Not seen yet:**
  - Two players.
  - How the titan reads to Aaron in a real session (the camera there is not fixed level).

### 15c. Wrong-answer effects after a right answer (2026-10-10)

Aaron: "sometimes i think im getting an incorrect answer debuff even though its right and counted right".

Mud (8 s, re-applied every 2.5 s) and Dizzy (6 s of blur pulses) ran on after their penalty returned, so a player who
answered the retry right inside that time stayed slowed or blurred, in the race and in boss mode alike; the mud's
re-apply also landed on top of the right answer's speed boost. Freeze, Yeet, Spike and Blackout end before the player
can answer again (Busy), so they never did this.

- Every right answer now calls `Cleanse` (fnm_director): it switches the mud and both screen effects off and bumps the
  player's `PenaltyEpoch`, which the mud and dizzy loops check and stop on. Log `penalty effects cleared by a right
  answer`; seen twice in a `DebugAutoWrongAnswers 5` + `DebugAutoRightAnswers` boss run (after Mud, after Dizzy).
- A second guard against a late trigger event: a door or pad event within 1.5 s (`RightCooldownSeconds`) of a right
  answer is dropped, logged `<pad X> event dropped ... after a right answer`. A late event from the pad a player was
  just teleported off would be checked against the next question and come out wrong. Not seen to happen; if that log
  line ever shows up in a play log, it was this.

### 15d. Mega laser cannons (2026-10-10)

Aaron: "use same meshy process or mint to create the weapons systems that attack the boss, the ones you have right now are
not styled or cool at all. make them mega cannon lasers. and consider if you can add any fx to them like glowing areas,
lightning fx etc".

- **The art.** Meshy, 39 credits (1507 -> 1468): a concept image (nano-banana-pro, 9) and image to 3D, meshy-7.1,
  textured 2K, 40k triangles (30). A gunmetal turret with hazard stripes, gold trim, a plasma-window power core, glowing
  cyan coils round the barrel and a three-prong muzzle. Task ids in `art/cannon/meshy_tasks.json`, the concept in
  `art/cannon/concept.png`.
- **Import** (`python tools/import_cannon.py`, once per UEFN project): `FNM_CannonArt/SM_fnm_megacannon`, a static mesh.
  - The FBX is the GLB re-exported by Blender (`tools/glb_to_fbx.py`); the importer takes FBX and OBJ only, not GLB.
  - The texture needs LOD bias 0. Meshy packs it as thousands of small UV islands, and at the import's bias 1 they blurred
    into brown and teal blotches. Never Stream or NoMipmaps fixes that too, but fails session validation ("Texture needs to
    support streaming").
  - Validation warns that LOD0's vertex count is high. It is a warning, not an error.
  - A deleted static mesh can stay registered under its name ("already exists" on re-import, `exists` true after
    `delete`), so the mesh is `SM_fnm_megacannon`, not the first try's `SM_fnm_cannon`.
- **Placement** (`python tools/build_bossmode.py --cannons`, then the boss rig, which re-lays the beams from the new
  muzzles): one cannon at 36° and one at 144° round CENTRE, 27.2 m out, on the sand, turned onto the titan.
  - At 0° and 180° (due left and right, where the old wall cannons were) they sat 46° off the view's centre for a player at
    the entry, out of frame. At 36° they are 27° off and in frame, and the beams cross the view sideways.
  - 36° keeps clear of gate 4's mouth (20°) and the back perch (55°).
  - The muzzle is 18.3 m from the titan's waist.
- **FX.**
  - Fired with each shot (tag `fnm_bm_cannon_fx`, so `FireCannons` needs no change): the LaserBeams burst at the muzzle and
    a LightningBolt_03 zap with a lightning-strike sound. The boss-mode log now says `4 muzzles` (2 lasers, 2 zaps).
  - Always on: a LightningBolt_02 Continuous crackle at the coils, and cyan point lights at the coils and the muzzle (size
    50%, intensity 60%).
  - The light's `lightSize` enum refuses writes, but `lightSizePercentage` takes them. At 100 it flooded the bay white.
  - The beams are Aqua, to match the coils.
  - The old shapes (bracket, ball, barrel, ring) are gone from the boss arena. The race arena keeps `build_cannon.py`.
- **Seen in play** (headless, `DebugAutoBoss` + `DebugAutoRightAnswers` + `DebugBossHold 3`): a VICTORY run, 16/16, with
  `cannons fired (4 muzzles ...)` on every hit. Both cannons are in frame beside the titan, the coils glow cyan, the two
  Aqua beams meet at the waist, and there are bursts at the muzzles under the nuke flash. Ship defaults restored and
  compiled.
- **Not seen yet:**
  - The coil crackle. It is not visible in any play frame (the cannons are about 38 m from the player there).
  - The zap on its own, as distinct from the laser burst.
  - How the cannons read to Aaron up close.

### 15e. Active chest marks (2026-10-10)

Aaron: "i can't tell when a chest is active. can we make it glow or have an arrow over it or something?"

- Each perch's chest has a Beacon device in its Arrow style, gold, 2.6 m over the perch top, plus a gold Customizable
  Light 2.2 m over it (`build_bossmode.py --dress`; tags `fnm_bm_chest_beacon` / `fnm_bm_chest_light` + slot).
- `LightPerches` switches them with the chest's button through `MarkChest(P, On)`; the reset turns them all off. The setup
  log line now reads `4 chests (8 chest beacons + lights)`.
- At 4 m the arrow sat behind the question panel from the ground.
- **Seen in play** (`DebugBossChest 1`, `DebugChestDistance` 150, 1200 and 2000):
  - From 20 m, a gold chevron arrow over the chest with a gold halo round it, and the perch washed gold.
  - At level 2 chest 1 is dark again.
- **Not seen:** the beacon's HUD marker "WEAPON" (with distance, through walls). It did not appear in any frame.

### 15f. Niagara lasers (2026-10-10)

Aaron: "the fx we use as laser rays ... are just simple 3d shapes. do we have a particle fx library to pull from to really
make that tasty?"

- **The library.** The VFX Spawner's own Niagara systems (53, in `/CRD_VFX_Spawner/Assets/Niagara`) cannot be copied
  into the project, and Fortnite's `/Game/Effects` fails validation. UEFN's MCP can author Niagara systems, though, and
  Verse can spawn any system in the project (`SpawnParticleSystem`). So we build our own.
- **`tools/build_fx.py`** (Opus-built from a brief; engine `/Niagara` content only) makes two systems:
  - `FNM_FX/NS_fnm_laser`: a 3 m soft cyan glow tube, a 90 cm white-hot core, two jagged lightning strands, and flashes
    and sparks at the muzzle and at the hit. It runs 18.3 m along local +X, on for 0.5 s and gone by 0.8 s.
  - `FNM_FX/NS_fnm_impact`: a flash, a shock ring about 5 m across, sparks and four arcs, lasting 1.6 s.
- **Runtime.** `console/verse/fnm_fx.verse` holds `FnmSpawnLaser(At, Dir)` and `FnmSpawnImpact(At)`.
  - When `NiagaraLaser` is set (the default), `FireBeam` fires one laser per shot (3 per hit) along each beam prop's axis,
    and the prop stays hidden.
  - The first beam's first shot also fires the impact at the beam's far end.
  - The Alphabet-"I" path stays as a fallback (`NiagaraLaser` false).
- The laser's length is baked, because Verse cannot set user parameters.
  `test_niagara_laser_length_matches_the_cannons` ties `build_fx.LENGTH` to the cannons' geometry. Rebuild the systems
  after moving a cannon.
- **Seen in play** (`DebugAutoBoss` + `DebugAutoRightAnswers` + `DebugBossHold 8`):
  - Both lasers glow cyan with lightning strands and sparks, and meet at the titan's waist with the impact flash there.
  - The session validates.
  - The titan's lava cracks are crisp.
- **The titan's texture.** The blotchy titan in editor captures is an editor streaming artifact, not the texture (see the
  `uefn-mcp` skill). `import_boss.py` and `import_cannon.py` now set LOD bias 0, so the top mip is kept in play.

