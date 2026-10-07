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
   ┤ A ├ B ├ C ├ D ├       real doors, E to open (grey, blue, dark stone + wood, orange); letters on a board above
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
| 10 | long straight, 2 speed plates, to the finish | 0 |

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
- **Generic A–D doors:** each player's question is on their own HUD, so a whole class can play at once.
- **Every hallway faces +Y; the variety lives in the connectors:** the director's arrival direction, Yeet aim,
  penalty return spot and debug hooks all assume a +Y hallway, so none of them had to change. Only the sliding
  containers moved from "mirror across X = 0" to "slide along their own forward axis" (`SliderTravel`).

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
- **Skip guard** (director `WatchSkip`, every 0.25 s): a Shockwave Grenade clears a 6 m door wall, so a player found
  in a hallway past their stage (the finish hallway included) is sent back to their own station's entry with a
  NO SKIPPING! flash. Walking back into an earlier hallway stays harmless. `DebugSkipTest` proves it: it drops the
  player at station 3 on stage 1 (sent back within 0.12 s on 2026-10-06).
- A shockwaved player who lands in a vestibule answers through that door like anyone walking in: part of the fun.

## Victory area (2026-10-05, `tools/build_finish.py`)
The finish board stays up until the player clicks CLOSE (Aaron: "x it and enjoy themself in the victory area");
there is no automatic restart. The end wall's board is a giant ALL-TIME BEST screen: the director cycles it through
the skills, ranking every player on the island by their saved best (Verse persistence, `fnm_save.verse`; nobody's
names can be stored, so only players present are listed). Two lecterns in front: NEW RACE and CHANGE SKILL buttons
(E). Fireworks burst in the sky behind the end wall. Seen in play 2026-10-05.

## Still to do (GOALS G4)
- Decor seen only in editor captures: torch flames, fireworks and the chalk text are play-time and unverified.
