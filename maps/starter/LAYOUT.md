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
  (`fnm_ice_floor`, ground friction 0.4 and braking 60 instead of 6 and 800) and removes it on exit.
- **Rules a connector must keep:** its turns sum to 0 (it ends facing +Y: the director's arrival facing is fixed),
  a staircase joins straight segments only, and the level never goes below 0. The builder exits on a violation.
- Connector walls and stair steps take the tier colour of the station they lead into; floors stay white.

## Why these choices
- **Barriers, not teleports, for right answers:** the race never stops; Aaron's "success must never stall".
- **Vestibule triggers, not door-open events:** a door is a prop, so opening it fires nothing. The trigger
  sits just past the door; the barrier at the vestibule's far end is past the trigger, so a wrong door's
  penalty always fires before the player could reach a barrier.
- **Generic A–D doors:** each player's question is on their own HUD, so a whole class can play at once.
- **Every hallway faces +Y; the variety lives in the connectors:** the director's arrival direction, Yeet aim,
  penalty return spot and debug hooks all assume a +Y hallway, so none of them had to change. Only the sliding
  containers moved from "mirror across X = 0" to "slide along their own forward axis" (`SliderTravel`).

## Hallway obstacles (2026-10-04)
Per station, between 9 m and 20 m into the hallway (`OBSTACLES` in `tools/build_course.py`): station 1 is
clear; then a 70 cm gold hurdle, baffles (a full-height wall from one side, 9 m gap on the other), and from
station 5 shipping containers that slide across the hallway (Verse, `fnm_slider`). Later stations mix all three.

## Still to do (GOALS G4)
- Themed prop kit beyond the tier colours, if wanted.
