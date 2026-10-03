# Starter Course — "Gate Run" layout plan

The first console map. Linear, 10 stations, 4 doors each. Wiring per `console/README.md`; contract per
PROTOCOL §6/§6a. Built in UEFN once installed (GOALS G2). Units: cm (UEFN), 1 tile = 512 cm.

## Shape

```
  spawn                                                                         finish
 ┌──────┐   gap    ┌──────┐   gap          ┌──────┐   gap    ┌────────┐
 │ S1   │ ──────── │ S2   │ ──── … ─────── │ S10  │ ──────── │ podium │
 └──────┘ (no walk) └──────┘                └──────┘          └────────┘
   +X →  station k origin = (4096 * (k - 1), 0, 2048)   finish = (4096 * 10, 0, 2048)
```

Floating sky platforms, separated by gaps, so the only way forward is the correct door (teleport).

## One station (origin O = platform centre, floor level)

```
        back wall (y = +768), 4 doorways, A–D left to right as the player faces the wall
   ┌────┬─A─┬────┬─B─┬────┬─C─┬────┬─D─┬────┐
   │    │ ▓ │    │ ▓ │    │ ▓ │    │ ▓ │    │   ▓ = trigger volume just behind each doorway,
   │    └───┘    └───┘    └───┘    └───┘    │       enclosed so it can only be reached through the door
   │                                        │
   │                 R ↑                    │   R = retry teleporter (also this station's entry),
   │                                        │       at O + (0, -512, 0), facing +Y (the wall)
   └────────────────────────────────────────┘   platform 2048 (x) × 1536 (y), glass rail on 3 sides
```

| Piece | Position relative to O | Notes |
|---|---|---|
| Platform | centred | 4 × 3 tiles |
| Back wall | y = +768, full width, 512 tall | doorway openings 384 wide × 448 tall |
| Doorway centres A, B, C, D | x = −768, −256, +256, +768 | 512 apart |
| Trigger (per door) | doorway centre, y = +896 | scaled to fill the opening; sealed pocket behind |
| Letter sign (billboard, static "A"…"D") | above each doorway, z = +480 | large, high contrast |
| Retry/entry teleporter | (0, −512, 0) facing +Y | `Stations[k].RetryTeleporter`; also `Stations[k-1].NextTeleporter` |
| Glass rails | three open sides | stops falls; eliminations are off anyway |

## Totals

| Device | Count | Wiring |
|---|---|---|
| `fnm_director` | 1 | anywhere (hidden) |
| Trigger | 40 | `Stations[k].Doors` = [A, B, C, D] |
| Teleporter | 11 | 10 station entries + 1 finish |
| Billboard (letters) | 40 | static text, not driven by Verse |
| Player Spawn Pad | 4 | on S1, behind the retry teleporter |
| End Game device | 0–1 | optional, on the podium |

## Island settings
- Eliminations / fall damage off (README "Known limits": an eliminated player keeps their stage but
  respawns at S1).
- Max players: a full class (≥ 30).
- HUD: hide the default elements that cover the top-centre Verse HUD (storm timer, etc.).

## Why these choices
- **Sky platforms + teleport-only progress:** no walking shortcuts, no terrain to build, and the
  station layout is identical, so the whole course can be placed from a formula (MCP or editor Python).
- **10 stations:** with T = 5 tiers, each tier gets exactly 2 stations (1,1,2,2,3,3,4,4,5,5).
- **Doors are generic A–D:** each player's question is on their own HUD, so a whole class can play
  the same course at once, each on a different question.

## Build path once UEFN is up
1. Build station 1 by hand (or by MCP), check scale and readability in a playtest.
2. Duplicate it to S2–S10 at the formula positions (MCP/editor Python batch).
3. Place director, fill the `Stations` array, Build Verse, playtest with `order-of-ops-exponents`.
4. Font test (PROTOCOL O1): read `×`, `÷`, `−`, `²` on the HUD; set `render_profile` in `map.json`.
