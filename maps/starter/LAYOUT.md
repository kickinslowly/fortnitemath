# Starter Course — "Gate Run" v2: hallway race (as built)

10 stations, 4 doors each, joined by connector corridors, plus a finish hallway. **Source of truth is `tools/build_course.py`** (all
dimensions live there); this page explains the shape. Wiring/tagging per `console/README.md`; contract per
PROTOCOL §6/§6a. Units: cm. (v1, walled rooms joined only by teleports, is in git history before 2026-10-03.)

## Shape

Every station hallway faces +Y; the course starts at y = −12000 and runs about 740 m toward +Y on its own floor
slabs (well past the template's ground, which ends near ±13000). Per station: a 30 m hallway (`--hall`), then a
wall of four real doors, then four vestibules that open onto a **connector** (2026-10-04, below) leading to the
next hallway, which may sit higher, lower or off to one side.

```
            next hallway
   ═══╪═══╪═══╪═══╪═══     ═ = barrier (red stripes): blocks everyone but the player whose right answer opened it
   │ ▓ │ ▓ │ ▓ │ ▓ │       ▓ = hidden trigger: walking in answers with that door
   ┤ A ├ B ├ C ├ D ├       real doors, E to open; each panel in its letter's colour with a HUD-tile sign on it,
                            and over each a 3D letter on the lintel with a letter-colour arch light (2026-10-13)
   │                 │
   │ S               │     S = "STATION N" board on the left wall
   │        E ↑      │     E = entry teleporter (arrival / retry point; the player lands 3 m past it)
   └─────────────────┘
```

A right door opens that door's barrier for that player alone (`barrier_device.AddToIgnoreList`, and the
barrier turns invisible to them), so they run on into the next hallway without stopping. It stays open for
them; walking back through is harmless. A wrong door fires a random penalty from the director's pool, then
puts them back at their hallway's entry. The finish hallway ends in a wall with a FINISH! board.

## Connectors (2026-10-04)
Aaron: "hallways sometimes up stairs, down stairs, winding to left, winding to right, sometimes straight", speed
plates on the straights, one icy floor. `CONNECTORS` in `tools/build_course.py`, one per gap (the last leads to the
finish). Each funnels from the 22 m vestibule exits down to a 10 m corridor, runs its segments, and flares back out.

| After station | Connector | Level after (cm) |
|---|---|---|
| 1 | straight, 1 speed plate | 0 |
| 2 | stairs up 4 m (16 steps) | 400 |
| 3 | winding left (two 45° jogs, 17 m sideways) | 400 |
| 4 | stairs up 4 m | 800 |
| 5 | straight, 2 speed plates | 800 |
| 6 | winding right | 800 |
| 7 | stairs down 4 m | 400 |
| 8 | winding left | 400 |
| 9 | stairs down 4 m | 0 |
| 10 | long straight, 2 speed plates, into the boss arena | 0 |
| arena | short straight (10 m), out of the arena to the finish | 0 |

- **Speed plates:** visible movement modulators (speed 1.8 for 3 s plus a forward push along the corridor).
- **Ice:** station 6 (`ICE_STATIONS`), pale blue floor, sign "STATION 6 - ICE!", a baffle slalom. A mutator zone
  over the hallway (`fnm_ice_zone`) tells the director who is on it; it applies a player movement device
  (`fnm_ice_floor`: ground friction 0.05 instead of 6, acceleration capped at 500 cm/s²; braking stays 800, the
  device clamps it) and removes it on exit, with a 0.25 s position poll as the backstop. The device's "add to
  players on start" is off (it was on until 2026-10-06, which put every station on faint ice).
- **Rules a connector must keep:** its turns sum to 0 (it ends facing +Y: the director's arrival facing is fixed),
  a staircase joins straight segments only, and the level never goes below 0. The builder exits on a violation.
- Connector walls and stair steps take the tier colour of the station they lead into; so do the connector's floor pieces
  (funnel, straights, flare), in the dark floor tone of that tier (see Floors).

## Why these choices
- **Barriers, not teleports, for right answers:** the race never stops; Aaron's "success must never stall".
- **Vestibule triggers, not door-open events:** a door is a prop, so opening it fires nothing. The trigger
  fills the vestibule from the door wall's back face to 20 cm short of the barrier (`TRIGGER_DEPTH`): until
  2026-10-06 it was 60% deep, and a player who stopped against the barrier stood past it (and past the
  director's backstop zone), so a right door did nothing until they moved. The director's `WatchDoors` now
  watches the whole vestibule, trigger front face to barrier, as the backstop for a missed trigger event.
  Every trigger's detection box is its StepBox, sized by `trigger_fit` (see "Boss battle" below); the vestibule's is
  `VEST_TRIGGER_H` (300 cm) tall from the floor. `--triggers-only` refits them in place.
- **Generic A–D doors:** each player's question is on their own HUD, so a whole class can play at once.
- **Every hallway faces +Y; the variety lives in the connectors:** the director's arrival direction, Yeet aim,
  penalty return spot and debug hooks all assume a +Y hallway, so none of them had to change. Only the sliding
  containers moved from "mirror across X = 0" to "slide along their own forward axis" (`SliderTravel`).

## Boss arena (2026-10-07, G6 item 3)
Between connector 10 and the finish hallway (`arena()` in `tools/build_course.py`; constants `ARENA_LEN`, `PAD_SIZE`,
`PAD_SPOTS`, `ENTRY_Y`, `ADDS_SETTINGS`). A station-wide hall 30 m long (2212 cm wide inside), walls in the tier-5 colour,
every actor labelled `FNM_Arena_*` (the connector into it too, so it is painted tier 5 and lidded like a station). The
boss rig on it is `tools/build_race_boss.py`'s (actor tag `fnm_race_boss`, labels `FNM_RaceBoss_*`, BOSS_MODE.md §16):
rerun it after a course rebuild.

```
   ═════════════════════   y+3000  gate barrier (fnm_boss_gate): opens per player at the kill, then a 10 m connector
   │                     │          to the unchanged finish hallway
   │ ==L>  ┌─────┐  <R== │   y+2700  mega cannons L and R (scale 3), barrels on the titan's waist (lasers 5.0 m)
   │       │  T  │       │   y+2600  boss platform, 6 x 4 m, 1 m high: the Magma Titan (T, 6.3 m) over the hidden Megabrute
   │ [C]   └─────┘   [D] │   y+2200  answer pads C (left) and D (right), a floating letter over each
   │         a           │   y+1800  adds spawner (fnm_boss_adds): 2 guards with pistols on a wrong pad
   │ [A]             [B] │   y+800   answer pads A (left) and B (right), a floating letter over each
   │ S                   │   S = "BOSS ARENA" sign on the left wall
   │        E ↑          │   y+150   entry teleporter (fnm_boss + fnm_entry): arrival and retry point
   └──  ←connector 10──  ┘
```

Each answer pad is a `PAD_SIZE` (4.5 m) square tile in its letter's colour (`M_fnm_wall_pad_a..d`, `tools/import_art.py`)
with a hidden trigger sensing the whole tile, 1.5 m tall (`trigger_fit`; fnm_boss + fnm_door_a..d), and a floating 3D
letter over it (build_race_boss; until 2026-10-11 a letter billboard). A is on the player's left, like door A, so the pads read A B / C D as the HUD lists the choices. Until
2026-10-09 each pad sensed a 96 cm square 7 cm thick, 80 cm off the floor, in the middle of its tile (the 600 cm per unit
scale assumption); `DebugAutoRightAnswers` now drops the player `DebugPadOffset` (180 cm) off the centre in x and y.
A wrong pad brings the adds up to two (`SummonAdds`): it resets the adds spawner only when fewer than two are up, since a
reset refills its spawn limit and its timer then replaced every add a player killed.

- **Why the arena is not a station:** the tier formula (PROTOCOL §6) spreads tiers over `Stations.Length`; a station 11
  would shift every station's tier. The director finds the arena by its own tag (`fnm_boss`), plays it as stage
  `Stations.Length + 1` with the hardest tier, and keeps medal and accuracy course-only.
- **Play:** right pad = a hit (1/5 of the shared boss's health), back to the entry, next question; wrong pad = a normal
  penalty (back to the arena entry) plus the adds. Five team hits kill the boss: every player in the arena finishes
  (the clock stops at the kill), the gate opens for each of them, and they walk on through the finish hallway to the
  victory area. The boss returns 4 s later for the next player.
- The boss's max health is 100000 (the director's `MegabossHealth`, set in Verse on the Megabrute since 2026-10-11; the
  old guard spawner took the same value against its 1..10000 schema). Only a pad's `Damage` takes it down (20000 a hit);
  every other hit is healed straight back.
- **The boss rig** (2026-10-11, `tools/build_race_boss.py`; what changed and why: BOSS_MODE.md §16). Positions are from
  the arena's centre line (+X left) and the start of its floor:
  - Megabrute creature spawner (`fnm_race_megaboss`) on the platform top at (0, 2600), hidden; four titan clips
    (`fnm_race_titan` + `fnm_bm_slot_1..4`) with it at `TITAN_SCALE` 2.1 (2.4 put the head against the question panel in play), facing the entry. The beams aim at the waist,
    `BEAM_AIM` 236 cm over the platform top.
  - Mega cannons (`FNM_CannonArt/SM_fnm_megacannon`) at (±780, 2700), `CANNON_SCALE` 3, barrels on the waist: footprint
    x 480..1080, y 2525..2875, so 1.8 m of lane beside the platform, 1 m behind the far pads, 26 cm off the wall, 17°
    off the view's centre from the entry. Cyan point lights at the coils and the muzzle. A beam marker per cannon
    (`fnm_race_beam` + slot, the Alphabet "I", hidden in play) from the muzzle point to the waist: 5.0 m
    (`build_fx.RACE_LENGTH`, NS_fnm_laser_race).
  - Strike VFX (LightningBolt_03, scale 4; `fnm_cannon_strike`) and two explosive devices (no damage, medium knockback;
    `fnm_cannon_blast`) parked 6 m under the platform, moved to the boss's feet per hit.
  - Floating letters (`fnm_race_letter` + slot 1..4) over the pads at 2.3 m, scale 1.5 (3 m tall): with the 40 cm bob
    the top stays under the lid (5.8 m) and the bottom over a player's head.
  - On every right pad the director (`FireCannons`) fires three muzzle discharges and Niagara lasers per cannon, the
    impact at the waist, the strike and a blast at the feet, and knocks the Megabrute (pinned back on the platform after
    1.5 s); the titan flails; the HUD reads DIRECT HIT! N TO GO and the announcer counts the team's hits down.
- **Laser cannons, 2026-10-08 to 2026-10-11** (`tools/build_cannon.py`, retired): engine-shape cannons on the walls 18 m
  in, 3.3 m up, with a VFX Spawner burst at each muzzle (`fnm_cannon_fx`). `build_race_boss.py` removes what is left of
  them (actor tag `fnm_cannon_rig`).

## Boss battle arena (2026-10-09, BOSS_MODE.md; colosseum pass the same day)
The BOSS BATTLE mode's own arena: a round colosseum 140 m east of the course start, on its own slab past the template
ground; the race arena is untouched. Two tools, two actor tags: `tools/build_bossmode.py` (tag `fnm_bossmode`, labels
`FNM_BM_*`) builds everything play touches (floor, podium ring, gates, lid, every device); `tools/build_colosseum.py` (tag
`fnm_bm_colosseum`, labels `FNM_BMC_*`) dresses it (stands, colonnade, pylons, tribune, statues, torches) and reruns on
its own. Both are built from Fortnite's Coliseum playset kit plus engine cubes. Coordinates are relative to
O = (14000, -14000, 0), the podium's inner face due south; the centre is C = (0, 3200) (world (14000, -10800)), floor top
z 2. The player enters facing +Y, so **+X is their LEFT**. Angles are degrees from +X round C: 270 is the entry, 90 the
boss end.

```
                                90 (boss end): tribune over the "BOSS BATTLE" sign
                       .-----------------[ TRIBUNE ]-----------------.
                 G4 20 /         [P4 240]   ┌────────┐   [P3 240]     \ 160 G3      gates: arch bays in the podium
                      /            ○        │ BOSS   │        ○                  cannon L 0 |                ○     └────────┘     ○            | 180 cannon R   (y 3200, on the podium face)
                     |                         (C)                      |
                     |      [ C ]                            [ D ]      |   pads C D at y 2900
                 G2 340\    [ A ]                            [ B ]     /200 G1           A B at y 1900
                        \  [P2 180]             E ↑           [P1 180]/
                         '------------------[ MAIN GATE ]-------------'
                                270 (entry): the kit's main gate under a stone tower
```

Sand floor radius 3200 (a 120 cm stone band at the podium's foot, a marble medallion r 520-600 round C). Podium: 36 bays
of 10° (slot 0 due south), each a kit stone bay (`Coliseum_Wall_01`) under a marble one (`Coliseum_Wall_02`), 768 tall,
80 deep, a plain stone skin behind; a gate bay is a marble arch (`Coliseum_Arch_02`, stretched 1.4 tall, opening ~380 x
400) under a marble strip; slot 0 is `CP_Coliseum_ExtWall_MainGate_01` with a stone wall 4.5 m behind its open leaf. One
hidden collision lid (underside z 750) over the whole floor. Kit props are set indestructible (`bCanBeDamaged` off).

Dressing (`build_colosseum.py`): four rings of the kit's stone seating block (`Coliseum_Seats_02`, 48 / 54 / 62 / 68
blocks, 384 rise, 537 deep, alternate blocks 1 cm higher so overlapping treads never z-fight) rising to z 2306 at r 5428;
over the main gate (270 ± 11°) and at the boss end (90 ± 16°) the first two rings are flat stone terraces faced with the
podium's bays (the entry tower; the tribune deck at z 1538). Crown: a stone walkway, 40 fluted marble columns
(`Coliseum_Column_02` x 1.3) under a marble entablature at r 5690, eight pylons (`CP_Coliseum_ExtWall_Column_01` x 0.75,
45° apart, off the entry axis) each flying a pennant to ~52 m. Tribune: balcony and railings, four columns, canopy, back
wall, curtains, the kit's giant gladiator statue and two small ones. Podium: a pilaster (`Coliseum_Column_04`) each side
of every arch with a wall torch beside it, a llama statue over each gate, curtains on six marble bays, eight braziers on
the podium top.

| Piece | Labels | Verse tags |
|---|---|---|
| Slab, sand, podium bays (+ skins), main gate and the wall behind it, gate arches, lid | `FNM_BM_Floor`, `_Sand`, `_BayNN_Low/High/Backing`, `_BayNN_Arch/Fill`, `_MainGate`, `_EntryBack`, `_Lid` | — |
| Entry teleporter (0, 250), yaw 90, both group knobs Group_None | `FNM_BM_Entry` | `fnm_bm` + `fnm_entry` |
| Sign on the podium due north (0, 6395, 430), yaw 180, scale 2.5 | `FNM_BM_Sign` | — |
| Answer pads (±900, 1900) and (±900, 2900): tile (`M_fnm_wall_pad_x`), 450 x 450 x 150 hidden trigger, a giant 3D letter over it (`build_bossmode.dress`, turned to the player in play) | `FNM_BM_PadA..D`, `_TriggerA..D`, `_LetterA..D` | trigger: `fnm_bm` + `fnm_door_a..d`; letter `fnm_bm_letter` + slot |
| Boss platform (marble, 1 m) at (0, 4500) + a hidden Megabrute creature spawner on it + the 12 m Magma Titan (3 Animated Mesh clips) + a laser beam prop per cannon (BOSS_MODE §15, §15b; `build_bossmode.py --boss`) | `FNM_BM_Platform`, `FNM_BM_Megaboss`, `FNM_BM_Titan1..3`, `FNM_BM_BeamL/R` | `fnm_bm_megaboss`; titan `fnm_bm_titan` + slot; beams `fnm_bm_beam` + slot |
| Gates G1 200°, G2 340°, G3 160°, G4 20°: the arch, a 300-deep stone alcove (back, sides, roof; 400 wide, 420 tall) on the slab, spawner at its centre facing C, VFX at the mouth | `FNM_BM_Gate1..4_Back/SideA/SideB/Roof`, `_Spawner`, `_Fx` | spawner `fnm_bm_gate` + slot; fx `fnm_bm_gate_fx` + slot |
| Perches at r 2850: P1 235° (-1635, 865) and P2 305° (1635, 865) top 180, P3 125° and P4 55° (±1635, 5535) top 240; gold block, stepping stones toward x 0, hidden 300 x 300 x 200 trigger on top, beacon VFX, a gold weapon chest (scale 2.5, lock toward the stones) with a hidden button in it (`dress`) | `FNM_BM_Perch1..4`, `_StoneN`, `_Trigger`, `_Fx`, `FNM_BM_Chest1..4` (+ `_Button`) | trigger `fnm_bm_perch` + slot; fx `fnm_bm_perch_fx` + slot; button `fnm_bm_chest` + slot |
| Item granters (one per level, parked z -598) bound to a parked trigger each | `FNM_BM_Grant1..5_Granter` / `_Trigger` | trigger `fnm_bm_grant` + slot |
| Cannons on the podium face due left / right (y 3200), strike, nuke, 2 blasts (parked z -598) | `FNM_BM_CannonL/R_*`, `FNM_BM_Strike`, `_Nuke`, `_Blast1/2` | `fnm_bm_cannon_fx`, `fnm_bm_strike`, `fnm_bm_nuke_fx`, `fnm_bm_blast` |
| Anger ring, 5 VFX at radius 650 round the platform | `FNM_BM_Anger1..5` | `fnm_bm_anger_fx` + slot |
| Creature spawners, one per kind, just inside a gate alcove's mouth: Fiend G1, Brute G2, Ranged G3, Red Fiend + Exploding Brute G4 | `FNM_BM_Creature1..5` | `fnm_bm_creature` + slot = kind |

210 gameplay actors and ~470 dressing actors. The perch stones are 120 cm long (along the climb) and 300 cm wide (as wide as the perch), 50 cm rises,
100 cm edge gaps, laid from the perch toward the centre line (P1/P2: tops 30, 80, 130 then the perch at 180; P3/P4: 40,
90, 140, 190 then 240). B6 (2026-10-09) changed them from 120 x 120 / 60 / 150: a keyed run-and-jump climbs the new chain
(acceptance 5, below). Every hidden trigger (pads, perches) is sized by `trigger_fit`: a trigger senses only its StepBox
component (64 x 64 x 15 cm half-extents at +32 cm, scaled with the actor), not a 600 cm zone per unit scale, so the
device's origin now sits under the floor or inside the perch block. Each gate alcove has its own floor (the brief
listed back, sides and roof only; without a floor the spawner would stand over the void).

**Probe answers** (`python tools/build_bossmode.py --probe`, 2026-10-09, UEFN 42.30):
- Creature / wildlife devices exist: `/CRD_Creatures/SetupAssets/PID_Device_CreatureSpawner_V2` (creature Type: Cube Random,
  Fiend, Red Fiend, Brute, Red Brute, Ranged, Megabrute, Ice Fiend, Major Ice Fiend, Ice Brute, Major Ice Brute, Ice Ranged,
  Poison Fiend, Exploding Brute, Ice Random, Rush Random, All Random; Total Spawn Limit 1..100), `PID_Device_CreatureManager_V2`,
  `PID_Device_CreaturePlacer_V2`, `/CRD_WildlifeSpawner/SetupAssets/PID_Device_WildlifeSpawnerV2` (+ V1), Sentry
  `/CRD_SentryDevice/SetupAssets/Creative_Device_SentryProp_V2`. The creature spawner placed from MCP and listed its
  options (the others were only listed); nothing built with them this round.
- VFX `visual_Effect` (current entries): DiscoBalls, LaserBeams, AreaOfFog, SpookyGhosts, Balloons, Snow, FloatingSpaceRocks,
  Bubbles, FallingSparkles, Confetti, FlyingSpaceRocks, DustClouds, Rain, SmallTornado, LightFog, SkyLanterns, RainLight,
  WaterfallCrash/Splash/Mist, MusicalNotes_*, Small_Fire, Insect_Flies, Ambient_Dust, Eyes, LightningBolt_01..03, Bats, Embers,
  Fireworks, Fog, Leaves, Sparkles, FireworksLarge, RainConcert, SparkRain, Ash (+ 15 `_Deprecated`). No explosion or smoke;
  the nuke takes the first fire entry, **Small_Fire** (scale 6, sound `Explosion`). `effectType`: Continuous, Burst.
  `sound_Effect` includes Explosion, Explosion_02/03, Lightning_Strike*, Electric_Blast.
- Explosive `knockback`: None, Low, Medium, High, Very High, Super High. No "Large"; the blasts now ask **High** (B5,
  Aaron's harder knock; read back High on both).
- **Creature spawner in play (B5, headless, 2026-10-09):** `SpawnAt` is refused unless the device stands on the ground
  (40 m down or 5 m under the slab: refused), a player is inside its `activation Range` (1: refused; 100: works from 45 m),
  and it has been on for a moment (refused in the tick of its `Enable()`); when it takes, the creature appears at once but
  the call did not return within 30 s and a second creature followed. With `limit Spawned Creatures` off, `GetSpawnLimit()`
  reads 0. Its `wave Timer` (and the timing override) are not settable from MCP. What the director does instead: a pulse,
  `Enable()` → the device's own first wave (one creature, 0.5-2.6 s later, out of the alcove) on its `SpawnedEvent` →
  `Disable()`; the creature stays (Disable does not remove it) until `EliminateCreatures()` at the level clear. At the back
  of the alcove (60 cm off its wall) a Brute never came; at the mouth it came in 0.5 s. Creatures and the gate guards are
  on different sides: creatures were seen eliminated "by something else" 6-16 s after coming out.
- **Guard spawner in play (B5):** `Enable()` on a gate spawner sends one guard by itself; `SpawnAt` on an enabled one
  returns at once with the guard (refused while disabled, `GetSpawnLimit()` 1); `Spawn()` on a disabled one does nothing.
  The director switches a gate on at its first guard and counts guards by `GetAgents()`.
- Item granter accepted all five weapons (read back): AutoHeavyPDW R, Shotgun_Standard VR, Assault_AutoHigh VR, Sniper_Heavy
  SR, Launcher_Rocket SR. The guard spawners kept every boss and gate weapon, and max/starting health 100000 on all five
  bosses.
- Climb (B6 keys test, 2026-10-09): from the entry, `D:1.6,D+SPACE:1.0,D+SPACE:1.0,D+SPACE:1.0` (strafe right, then
  run-jump) stands the player on P1 (traced at x -1576, y 590, feet z 182) and grants the SMG.

Rerun after: nothing. It reads no course geometry, so a course rebuild does not move it; rerun `build_bossmode.py` only
after changing its own constants (idempotent: two runs leave the same 122 actors).

## Hallway obstacles (2026-10-04)
Per station, between 9 m and 20 m into the hallway (`OBSTACLES` in `tools/build_course.py`): station 1 is
clear; then a 70 cm gold hurdle, baffles (a full-height wall from one side, 9 m gap on the other), and from
station 5 shipping containers that slide across the hallway (Verse, `fnm_slider`). Later stations mix all three.
Guards (`tools/build_guards.py`, `GUARDS`): station 1 has none since 2026-10-13 (G9: it is the tutorial; no spawner is
placed for a count of 0, so the director finds no `fnm_guards` + `fnm_station_01` object and must tolerate that); stations
2 to 10 keep 1, 2, 2, 3, 3, 4, 4, 5, 5 guards.

## Decor (2026-10-05, `tools/build_decor.py`)
A giant 3D station number on each door wall's lintel; wall torches above head height; a chalkboard with a chalk
math line on the right wall facing the station sign; potted plants in the entry corners; six giant digits floating
outside each station, 25-50 m off the centre line (no collision: a Yeet skydive may pass them); at the finish
torches, flowers, plants and fireworks props behind the end wall (the ALL-TIME BEST screen and the podium buttons are
`tools/build_finish.py`'s; the old "100" sign is gone). Nothing stands in the run line, the doors or the
vestibules.

## Pickups (2026-10-06, `tools/build_pickups.py`)
Aaron: players pick up Boogie Bombs and Shockwave Grenades to use on each other. Every EVEN station (2, 4, 6, 8, 10)
has a trail of four holo pads along each side wall between where players land (450 cm in) and the first obstacle
(900 cm): one wall's pads hold Boogie Bombs (5 s forced dance: no weapons, no building; any damage ends it), the
other's Shockwave Grenades (punt a rival, or launch yourself over a hurdle), and the sides swap at each armed station
so no lane is always the good one (station 2: bombs left, shockwaves right). A pad is picked up by running over it,
holds one grenade, and respawns it 8 s later, so a chaser finds them stocked. Device: the Item Spawner pad
(`PID_CP_Devices_ItemSpawnerProp`; the item definitions are `Athena_DanceGrenade` and `Athena_ShockGrenade`).
- **Skip guard** (director `WatchSkip`, every 0.25 s): a player found in a hallway past their stage (the finish
  hallway included) is sent back to their own station's entry with a NO SKIPPING! flash. Walking back into an earlier
  hallway stays harmless. `DebugSkipTest` proves it: it drops the player at station 3 on stage 1 (sent back within
  0.12 s on 2026-10-06). With the glass lids below it is the backstop, not the fence.
- A shockwaved player who lands in a vestibule answers through that door like anyone walking in: part of the fun.

## Glass lids (2026-10-06, `tools/build_lids.py`)
Aaron: "add a ceiling with collision so players can't launch out and over ... maybe transparent". Every floor piece of
the course (station hallways with their vestibules, the finish hallway, each connector's funnel, flare and corridor
segments, each staircase as one sloped sheet) carries a 40 cm glass slab (Creative glass-gallery glass,
`MI_CP_GlassGallery`) whose underside sits 20 cm down into the wall tops at WALL_H, so the course is a closed
glass-topped tube: nothing can be jumped out of or into, the sky and the floating digits stay visible, and from inside
the glass is almost invisible (a faint band where it meets the door wall; from above it reads as a tinted roof). 61
slabs for 10 stations. The Yeet still lands at the entry under it (seen 2026-10-06: 18.4 m back, 0.9 s flight; the
vent throws flat). Not yet seen: a real Shockwave jump against the glass, and whether Aaron wants the glass more
visible (a tinted gallery variant such as `MI_CP_GlassGallery_Cerulean` is a one-line swap).
2026-10-08, Aaron: "make the glass top completely transparent, it's obscuring some things I'd like to see". The lids
are now invisible in the editor and in play (`VISIBLE = False`: component hidden, collision untouched, the same body
as every wall); the glass material stays on them, so flipping `VISIBLE` restores the look.

## Door colours and signs (2026-10-08, `tools/build_course.py` door_dress)
Aaron: "make the doors the same colors as the letters and styling for each answer, and place the letters on the
doors". Each door panel is painted with its own texture (`M_door_face_a..d`: `tools/make_door_signs.py`, imported by
`tools/import_art.py signs`): the letter's colour all over (A white, B blue, C green, D orange, the HUD tile colours)
with a dark 96 cm tile and the letter in that colour, centred 165 cm up. The letter is part of the door, so it swings
away when the door opens and has no collision of its own. The texture is drawn mirrored and offset to fit how the door
mesh maps its front face (measured with calibration textures, constants in `make_door_signs.py`). The wall frame round
each door stays stock: it is a runtime material instance that ignores overrides. `--doors-only` repaints in place.
2026-10-09: the first version, a separate sign actor on each door, stayed in the doorway when the door opened and blocked
players (Aaron's test): the editor's NoCollision on a placed mesh does not hold in play.

### The paint was lost (found 2026-10-13, G9) and what keeps it now
Read back on 2026-10-13: every one of the 40 doors had `doorAnimatingMaterial` null and an empty `DoorComponent` override
(identical doors in the editor and in play), and so did every painted wall: the whole course was unpainted. Cause: a
full `python tools/import_art.py` run deleted and re-imported every `M_door_face_*` and `M_fnm_wall_*` asset at its own
path, and **deleting an asset empties every reference to it**; the actors do not repaint themselves. It was most likely
the run that brought `T_fnm_nuke` / `T_fnm_banner` in on 2026-10-09 (their PNGs date 08:11, the doors were painted at 06:51).
Evidence: `get_referencers` of the repainted materials was empty while `M_fnm_wall_bm_stone`, never replaced since, had
over 100 users; reproduced on a throwaway material and cube (override set before, null after the old `materials()`).
No `build_course.py` path was at fault: `station()` and `doors_only()` both call `door_dress`.
The fix is in `tools/import_art.py`: an existing material or door face is KEPT (the default run only imports what is
missing); `--force` replaces one and then repaints the course itself (`paint()` + `door_paint()`). `door_dress` now reads
the door back and stops the build on a miss; `build_course.py --door-paint` re-applies all 40 in place, saves and reads them
back; `--check-paint` is the read-only guard (every door, wall and floor against what the build wants, exit 1 if off).
The boss arenas' materials (`bm_*`, `pad_*`) are not covered by that repaint: rerun their builders after forcing them.

### Lintel letters and arch lights (2026-10-13, `tools/build_door_marks.py`)
Nothing told a runner which door was which until they were at the panel. Over every door, on the lintel's runner-side face
(door top 384 to wall top 600, so below the station number that `build_decor.py` stands on the wall top), stands the Alphabet
prop of its letter (CRG_Props, 206 x 201 x 50 cm, yaw 180 so it reads from -Y) in the nearest stock colour (White, Sky Blue,
Apple Green, Orange; the boss arena's pad letters use the same), no collision, indestructible. The lintel itself is
painted a near-black band (`M_fnm_wall_lintel`) so the letters read against it: on the pale tier wall a white A and a green
C were weak (editor frames 2026-10-13). A Customizable Light in the letter's own colour hangs 1 m in front of the lintel at
3.5 m: `lightSizePercentage` 25, intensity 40. The brief's 50 / 60-100 bleached the white doors and the pale walls in
daylight; the lights earn their keep at dusk, which the parent judges in play. Geometry is read from each station's Lintel
bounds and Door transforms. Tag `fnm_door_marks`, labels `FNM_Sxx_MarkA..D` / `FNM_Sxx_MarkALight..`; 80 actors; rerun
after a course rebuild (the lintels are re-placed).
Doors are also made indestructible (`door_dress` sets `bCanBeDamaged` false and reads it back): all 40 read damageable on
2026-10-13 because the 2026-10-09 door re-placement came after `build_island.py` hardened the props.

### Floors (2026-10-13)
The engine-cube floors were white and glared by day. `paint()` now paints every hallway's floor, each connector's floor
pieces (funnel, straights, flare AND stair treads, which took the pale wall colour before) and the arena's by tier in a dark
mid-tone of the tier's wall colour (`floor_tier1..5`; a connector takes the hallway it leads into, the arena tier 5, the
finish a dark gold-brown `floor_finish`); the ice station's floor stays ice. A flat Kd renders much lighter than its numbers:
the first values (0.05 0.14 0.07 for tier 1, wall x 0.2) still read mid-bright in the editor, so they were halved to the
`WALL_COLOURS` values now (tier 1 `0.03 0.085 0.04`). `paint()` saves and reads every actor back.
The final look is judged in play under a locked time of day (`build_island.py --time list` shows the choices; the island
still reads `NoOverride`).

### Titan Peak surfaces (2026-10-13 evening, G9 wave 5, `tools/import_titanpeak.py --materials`)
The flat tier colours gave way to the Titan Peak world (spectacle review section 3): each tier's station hallways and the
connectors into them wear that tier's tiling Mint material, the arena floor iron plates.

| tier (stations) | place | floor | wall |
|---|---|---|---|
| 1 (1-2) | BASE CAMP | `t1_floor` mossy flagstones | `t1_wall` carved green-grey blocks |
| 2 (3-4) | WATERFALL GORGE | `t2_floor` river stone | `t2_wall` blue slate strata |
| 3 (5-6) | FROST RIDGE | `t3_floor` snow + violet ice (also the ice station's floor) | `t3_wall` purple rock, snow |
| 4 (7-8) | OBSIDIAN DESCENT | `t4_floor` basalt hex tiles | `t4_wall` obsidian, lava cracks |
| 5 (9-10) | MAGMA CORE | `t5_floor` lava crust | `t5_wall` red rock, lava veins |
| arena | TITAN'S FORGE | `forge_floor` iron plates | flat tier 5 (left as it was) |

Kept flat: the lintels (the dark band the door letters read against), hurdles (gold), the arena's pads and platform, the
finish. **Tiling:** every course piece is a scaled engine cube whose UVs run 0..1 per face, so a plain material stretches with
the actor. `M_fnm_tp_surface` (a Material built over MCP with MaterialTools) takes its UVs from the world position measured
along the actor's own X / Y axes and picks the projection from the pixel's local-space normal (exactly one axis on a box face),
so the stone keeps its real size on every face at any yaw (45-degree connector walls too): `TileSize` cm per repeat (250-400),
a `Tint` that darkens the pale textures (t3_floor snow 0.3, t1_floor 0.5: the white floors glared before), `RoughnessMin` 0.6
(the Mint roughness maps are glossy), the normal map re-expressed in world space. Each surface `M_fnm_tp_<key>` is a material
instance of it. `build_course.py --paint-only` paints them (`SURFACES`); `--paint-only --flat` puts the flat colours back and
`--check-paint [--flat]` checks either.
**Variation (same evening, after Aaron played: "tiled too monotonously like wallpaper").** The master also multiplies the
texture by a macro map: the same texture turned 37 degrees, 2.7 tiles across, read 5 mips blurred and divided by its own average
colour (its last mip), so the tier's own light, dark and mossy patches drift over metres and never line up with the repeat
(`VariationBlend`, 1-2 per tier). A first probe that blended the sharp turned sample in by a sine mask ghosted a second paving
pattern over the station 1 flagstones, so the second sample now carries only light and colour. On top: a +-12% colour jitter
over ~13 m, grime at a wall's foot (80 cm towards `GrimeTint`) and a lighter weathered band at its top (35 cm), floors 30%
darker within 1.4 m of the walls (short side only, so floor pieces join cleanly; not on stair treads), and a per-actor UV
offset on wall faces so facing walls do not mirror. Cost: 8 texture fetches over 3 samplers, 344 pixel instructions (was 6 and
248). Knobs per tier: `import_titanpeak.surface_knobs`; rerun `import_titanpeak.py --materials` after changing one.
**Second layer (wave 5c, same night: the base pattern still dominated).** Each tier got an organic, gridless Mint material blended
over the first in irregular patches, like terrain blending: t1 floor earth, leaves and grass tufts, t1 wall dense ivy; t2 floor
wet sand, pebbles and algae, t2 wall teal moss and ferns; t3 floor snow drifts, t3 wall glacier ice; t4 floor ash and cinders,
t4 wall pumice; t5 floor lava rubble (t5 wall's scorched rock was still generating: coverage 0 until a rerun). The arena's
forge floor has no patch layer. The mask is a periodic band-limited noise (`art/titanpeak/materials/patch_noise.png`, made by
`make_patch_noise`) read twice over each face at 24 m and ~10 m per repeat, turned 23 and -61 degrees, thresholded for 35-40 %
coverage (`PATCH_COVERAGE`; the threshold is the analytic quantile, checked against the real noise) with a soft edge, plus a
bias toward a wall's foot (more ivy, moss, ice low on a wall) and along a floor's long sides (more leaves, drift, ash at the
walls). The first try in offline previews (1.6 m noise) read as busy camouflage. Cost now 13 texture samples over 7 samplers,
408 pixel instructions.

### Door arches (2026-10-13 evening, `tools/build_arches.py`)
A Meshy stone arch (`SM_fnm_tp_arch`, 8195 triangles, no collision) frames every door in its tier's skin (`M_fnm_tp_arch_t1..t5`:
mossy grey, river teal, frost violet, obsidian with orange runes, dark slate with red runes). 520 wide x 590 tall on the floor,
centred on the door, back 6 cm inside the door wall and front 40 cm proud of it (scale 0.839 x 2.931 x 3.103, yaw -90: the
mesh's width is its local Y). The opening (47% of the width between the pillars, 78% of the height up to the keystone) is
244 x 460 cm against the door prop's ~190 x 250 white frame, so nothing is in the doorway; the keystone sits on the lintel
band behind the 3D letter (the letter's front is 52 cm out, the arch's 40). Geometry is read from each station's Lintel and
Door bounds. Tag `fnm_arches`, labels `FNM_Sxx_ArchA..D`, 40 actors; rerun after a course rebuild.

## Victory area (2026-10-05, `tools/build_finish.py`)
The finish board stays up until the player clicks CLOSE (Aaron: "x it and enjoy themself in the victory area");
there is no automatic restart. The end wall's board is a giant ALL-TIME BEST screen: the director cycles it through
the skills, ranking every player on the island by their saved best (Verse persistence, `fnm_save.verse`; nobody's
names can be stored, so only players present are listed). Two lecterns in front: NEW RACE and CHANGE SKILL buttons
(E). Fireworks burst in the sky behind the end wall. Seen in play 2026-10-05.

## Still to do (GOALS G4)
- Decor seen only in editor captures: torch flames, fireworks and the chalk text are play-time and unverified.
- Boss battle (2026-10-09, B4), still unverified:
  - Done by B6 (2026-10-09): perch climb + SMG grant by keys (acceptance 5, after the stone and trigger fix), picker
    click (acceptance 3), the 16 voice lines imported and heard (65 of 65 wired), timed gate spawns seen (B5).
  - Only P1 was climbed by keys; P2..P4 share the recipe but were not climbed.
  - The race arena's pad triggers and the station vestibule triggers used the 600 cm per unit scale assumption; fixed
    2026-10-09 (`trigger_fit`, see the arena above).
  - Two players have never shared a fight (team hits, late joiners).
