# Starter Course — "Gate Run" v2: hallway race (as built)

10 stations, 4 doors each, plus a finish hallway. **Source of truth is `tools/build_course.py`** (all
dimensions live there); this page explains the shape. Wiring/tagging per `console/README.md`; contract per
PROTOCOL §6/§6a. Units: cm. (v1, walled rooms joined only by teleports, is in git history before 2026-10-03.)

## Shape

One straight run toward +Y from y = −12000, on its own floor slabs (it runs past the template's ground,
which ends near ±13000). Per station: a 30 m hallway (`--hall`), then a wall of four real doors, then four
vestibules that open straight onto the next hallway.

```
            next hallway
   ═══╪═══╪═══╪═══╪═══     ═ = barrier: blocks everyone, except the player whose right answer opened it
   │ ▓ │ ▓ │ ▓ │ ▓ │       ▓ = hidden trigger: walking in answers with that door
   ┤ A ├ B ├ C ├ D ├       real doors (grey, blue, grey hatch, orange); coloured letters on a dark board above
   │                 │
   │ S               │     S = "STATION N" board on the left wall
   │        E ↑      │     E = entry teleporter (arrival / retry point; the player lands 3 m past it)
   └─────────────────┘
```

A right door opens that door's barrier for that player alone (`barrier_device.AddToIgnoreList`, and the
barrier turns invisible to them), so they run on into the next hallway without stopping. It stays open for
them; walking back through is harmless. A wrong door fires a random penalty from the director's pool, then
puts them back at their hallway's entry. The finish hallway ends in a wall with a FINISH! board.

## Why these choices
- **Barriers, not teleports, for right answers:** the race never stops; Aaron's "success must never stall".
- **Vestibule triggers, not door-open events:** a door is a prop, so opening it fires nothing. The trigger
  sits just past the door; the barrier at the vestibule's far end is past the trigger, so a wrong door's
  penalty always fires before the player could reach a barrier.
- **Generic A–D doors:** each player's question is on their own HUD, so a whole class can play at once.
- **Straight line on own slabs:** simplest geometry; the director's arrival direction is fixed at +Y.

## Still to do (GOALS G2/G4)
- Visual pass: walls are plain white engine cubes; colour per tier or a themed kit.
- Doors B (blue) and C (hatch) read alike from a distance; the letter boards carry the meaning.
