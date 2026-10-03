# FNM console — UEFN wiring guide

The Verse runtime that plays the active cartridge on a linear course of question stations.
Contract: `PROTOCOL.md` §6 / §6a. Nothing here has been compiled yet (UEFN was not installed when it
was written); see **First compile checklist** at the bottom.

## Files

| File | What it is |
|---|---|
| `verse/fnm_cartridge.verse` | Protocol types (§8). Fixed. |
| `verse/fnm_logic.verse` | Pure logic: station tier, per-tier pools, draw without replacement, choice letters, accuracy line. |
| `verse/fnm_ui.verse` | Per-player HUD (`fnm_hud`): canvas → vertical stack_box → 5 text lines. |
| `verse/fnm_director.verse` | The device: `fnm_director`, `fnm_station`, per-player state, door handling. |
| `maps/<map-id>/generated/fnm_active_cartridge.verse` | The cartridge slot. Defines `FnmActiveCartridge():fnm_cartridge`. Written by `fnm insert`. |

## 1. Put the Verse files in the UEFN project

All five files go **flat, in one folder** — the project's Verse source folder (in UEFN: *Verse → Verse
Explorer*, right-click the project → *Open in File Explorer*; typically
`Documents\Fortnite Projects\<Project>\Plugins\<Project>\Content\`).

- `fnm sync <map-id>` does this: copies `console/verse/*.verse` plus
  `maps/<map-id>/generated/fnm_active_cartridge.verse` into the project's Verse folder (needs
  `uefn_project` set in `maps/<map-id>/map.json`).
- Keep them in the **same folder**. In Verse every folder is a module; putting the cartridge file in a
  `generated/` subfolder would make it a separate module and the types would need `<public>` and a
  `using` (PROTOCOL O3). Flat avoids that.

Then **Verse → Build Verse Code** (Ctrl+Shift+B). A clean build makes `fnm_director` appear in the
Content Browser under the project's *CreativeDevices* folder.

Swapping cartridges later: `fnm insert <cartridge>` → `fnm sync <map-id>` → Build Verse Code → push
changes. No device or level edits.

## 2. Build each station (repeat S times)

| Device | Count | Settings to change |
|---|---|---|
| **Trigger** (`trigger_device`) | one per door: 2, 3 or 4 (the map's `max_choices`) | *Times Can Trigger*: **Unlimited** (or 0 / ∞ — whatever the dropdown calls it). *Triggered by Player*: **On**. *Triggered by Vehicles*/*Sequencers*/*Water*: **Off**. *Trigger Delay* and *Reset Delay*: **0**. *Visible in Game*: **Off**. Scale it to fill the doorway. |
| **Teleporter** — retry point | 1 | Placed in front of this station's doors, facing them. **No** *Teleporter Group* / *Target Group* (it is only a destination). *Visible in Game*: **Off**. Turn off anything that lets a player walking over it get teleported (e.g. leave target group empty). |
| **Teleporter** — next point | 1 (can be shared: station k's next point = station k+1's start) | Same as above. For the **last** station this is the **finish area**. |
| Door labels A/B/C/D | per door | Static signs/billboards. Not driven by Verse. Left-to-right order must match the Doors array order. |

Verse never reads the teleporters' own groups: it calls `Teleport(Player)` on the device you assign,
which moves the player *to that device*.

Also place:
- **Player Spawn Pads** at station 1's start (mid-game joiners start at stage 1).
- Optional **End Game** device for the finish (see `UseEndGameDevice`).

## 3. Place and fill `fnm_director`

Drag one `fnm_director` into the level. In its Details panel:

| Property | Fill with |
|---|---|
| `Stations` | Add one element per station, **in course order** (element 0 = stage 1). |
| `Stations[i].Doors` | Add 2–4 elements and pick that station's triggers in order **A, B, C, D**. |
| `Stations[i].RetryTeleporter` | That station's retry teleporter. |
| `Stations[i].NextTeleporter` | Next station's start teleporter (last station: finish-area teleporter). |
| `Stations[i].DifficultyOverride` | `-1` (default) = automatic, evenly from tier 1 at the first station to tier T at the last. `0..100` = this station's difficulty position in percent (0 = easiest tier, 100 = hardest). |
| `WrongFeedbackSeconds` | How long a wrong answer's feedback stays up (player is teleported back immediately). Default 4. |
| `CorrectFeedbackSeconds` | How long the explanation shows before the player is moved on. Default 3. |
| `NoticeSeconds` | "No choice D here" / "not your station" notices. Default 2. |
| `UseEndGameDevice` + `EndGameDevice` | Tick and pick an End Game device to fire `EndGameDelaySeconds` after a player finishes. Check that device's own settings — it can end the round for everyone. |

Automatic difficulty (PROTOCOL §6, T = 5 tiers): 10 stations → tiers 1,1,2,2,3,3,4,4,5,5; 5 → 1..5;
3 → 1,3,5.

## 4. What players see

Top-centre HUD, per player: `Title - Subtitle`, `Stage s/S - <tier name>`, the prompt, the lettered
choices (`A: 11     B: 14     C: 10`), and a feedback line. A wrong door shows that choice's feedback
in red and teleports the player to the retry point with the same question still up. A right door shows
the explanation in green, then the next question and a teleport to the next station. A door letter the
item does not use shows "No choice D here". Doors of a station the player is not on show "This is
not your station". After the last station: "Course complete!" and first-try accuracy.

Output log (`Print`) messages starting with `FNM:` mean misconfiguration: no stations, a cartridge
with no tiers, or a station with fewer doors than the cartridge's items have choices.

## Known limits

- A player who is eliminated respawns at a spawn pad but keeps their stage. If eliminations are
  possible on the course, either disable them (Island Settings) or add a spawn pad per station.
- Text uses the Fortnite UI font; whether `×`, `÷`, `−`, superscripts render decides the map's
  `render_profile` (PROTOCOL O1). Check it on first play-test.

## First compile checklist

Signatures were checked against the **v42.20 digest files** (`Fortnite.digest.verse`,
`UnrealEngine.digest.verse`, `Verse.digest.verse`, mirror at github.com/kbfngg/uefn,
`Modules/FortniteGame/`) and idioms against a corpus of UEFN-compiled examples
(github.com/uefncentral/uefn-verse-examples). Least certain first — if the build fails, look here:

1. **`set PromptText.WrapWidth = WrapAt`** (fnm_ui.verse, `Attach`). Digest: `var WrapWidth<public>: float`
   on `text_base`. No compiled example uses it. If rejected, delete the three `set ...WrapWidth` lines
   (long explanations then won't wrap — try `text_block{..., WrapWidth := 1500.0}` instead).
2. **`FnmActiveCartridge()` effects.** Called only from `OnBegin` (any effect allowed there). If the
   generated file adds `<computes>`/`<transacts>` that still works.
3. **Cross-file visibility.** All files flat in one folder = one module, no `<public>` needed. If the
   generated file lands in a subfolder, expect "unknown identifier fnm_cartridge / FnmActiveCartridge".
4. **`for` as an expression** returning arrays (`FnmPoolForTier`, `FnmBuildTierPools`, `FnmDraw` rest).
5. **`set State.Decks[Tier - 1] = Draw.Rest`** inside `if (...) {}` — element write through an object
   field; same shape as compiled `if (set PetPurchaseData.AvailablePetProps[I] = true){}`.
6. **`"...({Percent}%)"`** — `%` in a string literal (fnm_logic.verse, `FnmAccuracyLine`). Remove the `%`
   if the lexer objects.
7. **`TriggeredEvent` payload is `?agent`** (digest: `TriggeredEvent<public>: listenable(?agent)`); the
   handler signature is `OnTriggered(MaybeAgent:?agent):void`.
8. **`fnm_station := class<concrete>`** with `@editable` device fields inside an `@editable` array — the
   compiled LaserDoors example uses exactly this shape.
