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
   ┤ A ├ B ├ C ├ D ├       real doors, E to open; each panel in its letter's colour with a HUD-tile sign on it
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
- Connector walls and stair steps take the tier colour of the station they lead into; floors stay white.

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
`PAD_SPOTS`, `BOSS_SETTINGS`, `ADDS_SETTINGS`). A station-wide hall 30 m long, walls in the tier-5 colour, every actor
labelled `FNM_Arena_*` (the connector into it too, so it is painted tier 5 and lidded like a station).

```
   ═════════════════════   y+3000  gate barrier (fnm_boss_gate): opens per player at the kill, then a 10 m connector
   │       ┌─────┐       │          to the unchanged finish hallway
   │       │  B  │       │   y+2600  boss platform, 6 x 4 m, 1 m high; the boss's guard spawner on it (fnm_boss_spawner)
   │ [C]   └─────┘   [D] │   y+2200  answer pads C (left) and D (right)
   │         a           │   y+1800  adds spawner (fnm_boss_adds): 2 guards with pistols on a wrong pad
   │ [A]             [B] │   y+800   answer pads A (left) and B (right)
   │ S                   │   S = "BOSS ARENA" sign on the left wall
   │        E ↑          │   y+150   entry teleporter (fnm_boss + fnm_entry): arrival and retry point
   └──  ←connector 10──  ┘
```

Each answer pad is a `PAD_SIZE` (4.5 m) square tile in its letter's colour (`M_fnm_wall_pad_a..d`, `tools/import_art.py`)
with a hidden trigger sensing the whole tile, 1.5 m tall (`trigger_fit`; fnm_boss + fnm_door_a..d), and its letter on a
board above. A is on the player's left, like door A, so the pads read A B / C D as the HUD lists the choices. Until
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
- The boss's max health is 100000: the device's option schema says 1..10000 and the Verse digest says "clamped between
  1 and 10000", but a write of 100000 read back 100000 and the spawned boss reported 100000 of 100000 in play
  (2026-10-07). A station-10 rocket launcher cannot kill it without the math, so it is not Invincible: the director's
  `Damage` takes 20000 a hit.
- **Laser cannons** (2026-10-08, `tools/build_cannon.py`; Aaron: "epic laser cannon blast the boss and the boss flail or
  get knocked back"): one on each wall `CANNON_Y` (18 m) into the hall, 3.3 m up, aimed at the platform: a gunmetal
  bracket, turret ball and barrel with a glowing muzzle ring (engine shapes painted `M_fnm_wall_steel` / `_glow`), and
  at each muzzle a VFX Spawner (LaserBeams burst, Beam_Attack sound; tag `fnm_cannon_fx`). Parked under the platform:
  a VFX Spawner (LightningBolt_01, Electric_Blast; `fnm_cannon_strike`) and two explosive devices (no damage, medium
  knockback, audio + VFX; `fnm_cannon_blast`). On every right pad the director (`FireCannons`) enables the muzzle bursts,
  moves the strike and a blast to the boss's feet and sets them off, knocks the boss back (`ApplyLinearImpulse`, or a
  1.5 m teleport stagger if the impulse does not move it) and freezes it 0.8 s; the HUD reads DIRECT HIT! N TO GO and the
  announcer counts the team's hits down. The engine shapes are scenery: Verse cannot find or move them, so the muzzle
  VFX spawner is the muzzle the director knows about. Rerun after a course rebuild.

## Boss battle arena (2026-10-09, BOSS_MODE.md)
The BOSS BATTLE mode's own arena (`tools/build_bossmode.py`, actor tag `fnm_bossmode`, every actor labelled `FNM_BM_*`;
spec BOSS_MODE.md §3). It sits 140 m east of the course start, x 12000..16000, y -14000..-10000, floor top z 2, on its own
slab past the template ground; the race arena is untouched. Coordinates below are relative to O = (14000, -14000, 0), the
south wall's inner face on the centre line. The player enters facing +Y, so **+X is their LEFT**. Walls 800 high, 40
thick (`M_fnm_wall_bm_wall`), floor `M_fnm_wall_bm_floor`, one hidden collision lid (underside z 780).

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

| Piece | Labels | Verse tags |
|---|---|---|
| Floor, walls (side walls in three segments + a lintel over each gate), lid | `FNM_BM_Floor`, `_WallS/N`, `_WallL1..3`, `_WallR1..3`, `_LintelL1/2`, `_LintelR1/2`, `_Lid` | — |
| Entry teleporter (yaw 90, both group knobs Group_None), sign | `FNM_BM_Entry`, `FNM_BM_Sign` | `fnm_bm` + `fnm_entry` |
| Answer pads: tile (`M_fnm_wall_pad_x`), 450 x 450 x 150 hidden trigger, letter board | `FNM_BM_PadA..D`, `_TriggerA..D`, `_LabelA..D` | trigger: `fnm_bm` + `fnm_door_a..d` |
| Boss platform (steel) + one guard spawner per level (BOSS_SETTINGS, health 100000, weapon by level) | `FNM_BM_Platform`, `FNM_BM_Boss1..5` | `fnm_bm_boss` + `fnm_bm_slot_L` |
| Gates: 400 x 350 opening, 300-deep steel alcove (floor, back, sides, roof), spawner at its centre facing in, VFX at the mouth | `FNM_BM_Gate1..4_Floor/Back/SideA/SideB/Roof`, `_Spawner`, `_Fx` | spawner `fnm_bm_gate` + slot; fx `fnm_bm_gate_fx` + slot |
| Perches: gold block, stepping stones, hidden 300 x 300 x 200 trigger on top, beacon VFX | `FNM_BM_Perch1..4`, `_StoneN`, `_Trigger`, `_Fx` | trigger `fnm_bm_perch` + slot; fx `fnm_bm_perch_fx` + slot |
| Item granters (one per level, parked z -598) bound to a parked trigger each | `FNM_BM_Grant1..5_Granter` / `_Trigger` | trigger `fnm_bm_grant` + slot |
| Cannons (build_cannon.cannon, prefix `FNM_BM_Cannon`), strike, nuke, 2 blasts (parked z -598) | `FNM_BM_CannonL/R_*`, `FNM_BM_Strike`, `_Nuke`, `_Blast1/2` | `fnm_bm_cannon_fx`, `fnm_bm_strike`, `fnm_bm_nuke_fx`, `fnm_bm_blast` |
| Anger ring, 5 VFX at radius 650 round the platform | `FNM_BM_Anger1..5` | `fnm_bm_anger_fx` + slot |
| Creature spawners (B5), one per kind, invisible, just inside a gate alcove's mouth (x = side 2090): Fiend G1, Brute G2, Ranged G3, Red Fiend + Exploding Brute G4 | `FNM_BM_Creature1..5` | `fnm_bm_creature` + slot = kind |

122 actors. The perch stones are 120 cm long (along the climb) and 300 cm wide (as wide as the perch), 50 cm rises,
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

## Decor (2026-10-05, `tools/build_decor.py`)
A giant 3D station number on each door wall's lintel; wall torches above head height; a chalkboard with a chalk
math line on the right wall facing the station sign; potted plants in the entry corners; six giant digits floating
outside each station, 25-50 m off the centre line (no collision: a Yeet skydive may pass them); at the finish a
"100" above the FINISH! sign, a podium, flowers, fireworks props. Nothing stands in the run line, the doors or the
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
