# Starter Course — "Gate Run" (as built)

The first console map: 10 stations, 4 doors each, plus a finish room. **Source of truth is
`tools/build_course.py`** (all dimensions live there); this page explains the shape. Wiring/tagging per
`console/README.md`; contract per PROTOCOL §6/§6a. Units: cm.

## Shape

Walled rooms on the template's ground, on a 4-column grid (`SPACING` 2800, `COLS` 4): stations 1–4 in
row 0, 5–8 in row 1, 9–10 + finish in row 2. Rooms are closed (walls 8 m tall), so the only way between
them is teleporting: a right door sends you to the next room's entry, a wrong door back to your own.

```
        door wall: 4 doorways, letters A B C D above them, left to right as the player faces them
   ┌────┬─A─┬────┬─B─┬────┬─C─┬────┬─D─┬────┐
   │    │ ▓ │    │ ▓ │    │ ▓ │    │ ▓ │    │   ▓ = hidden trigger in a sealed pocket behind each doorway
   │    └───┘    └───┘    └───┘    └───┘    │
   │ S                                       │   S = "STATION N" sign on the left wall
   │                  E ↑                    │   E = entry teleporter (where you arrive / retry)
   └─────────────────────────────────────────┘
```

## Why these choices
- **Ground-level closed rooms**, not the originally planned sky platforms: the Blank template has solid
  ground at z=0, so a fall from a platform would strand a player instead of eliminating them.
- **10 stations:** with T = 5 tiers each tier gets two (1,1,2,2,3,3,4,4,5,5).
- **Generic A–D doors:** each player's question is on their own HUD, so a whole class can play at once.
- **Grid kept tight:** the template floor ends around x≈13000; a 5-wide grid at 4096 put a column over water.

## Still to do (GOALS G2)
- First playtest (blocked on Easy Anti-Cheat install), font test O1 → `render_profile` in `map.json`.
- Visual pass: the rooms are plain white engine cubes; colour or a themed kit later.
