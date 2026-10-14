# Brief D2: the new sounds in the game, the titan's entrance, the DOORS OF DOOM logo on the picker (2026-10-13 night)

Read `briefs/g9/TEAM.md` first (lock, machine rules, report format, the "Wave 4-5" section: foreground only under the
lock). Then `console/AUDIO.md` (cue table, mix rules, the new "Mint music and SFX" section), `BOSS_MODE.md` §15b-15c and
§16 (the titan: Meshy clips on Animated Mesh devices, why each clip has its own mesh), the project `CLAUDE.md`, and the
`uefn-mcp` skill. You are **D2**, model Opus, the only builder in this round. The manager (Opus 5.5) audits you. The
game is now called **DOORS OF DOOM** (Aaron, 2026-10-13); the HUD title already says so.

## You own (may edit)
All `console/verse/*.verse`; `tools/build_audio.py`, `console/AUDIO.md`; `tools/import_boss.py`, `tools/build_race_boss.py`,
`tools/build_bossmode.py` (titan parts only); `tools/make_medal_art.py`, `tools/art/fnm_logo.png`; the matching tests
(`tests/test_audio_cues.py`, `tests/test_mint_audio.py`, `tests/test_hud_layout.py`, `tests/test_volt_reactions.py`,
`tests/test_bossmode*.py`, `tests/test_race_boss*.py`, new tests as needed). No commits. Ship debug hooks restored.

## 1. Six new cues, Verse side (the waves are imported and waiting)
`tools/build_audio.py` holds them in `PENDING_CUES` (music_boss, music_menu, titan_roar, volt_oops, crowd_cheer,
crowd_aww): give each an enum value + `FnmCues()` + `FnmCueIds()` entry in `fnm_audio.verse` and a tag class +
`FnmCueTags()` entry in `fnm_tags.verse` (V did the same for volt_yay / volt_hmm: copy that shape), then move the rows
from `PENDING_CUES` into `CUES` in the same order (`tests/test_audio_cues.py` pins the order). After compiling, run
`python tools/build_audio.py --announcer am_michael --boss-voice am_onyx --mint` and `--list`: all of them placed with
source `mint`, 0 mismatches; the director's startup line must say every cue is wired (73 of 73 or whatever the count is).

## 2. Where they play (director / boss mode). Mix rules first (AUDIO.md): no voice on the same instant as a stinger
(0.9 s offset), at most 2 sounds in any 1 s window, never stack on the kill
- `music_menu`: the music bed while a player is on the grade picker (today it is silence: `SetMusic(Player, 0)`); stops
  at the run's countdown.
- `music_boss`: the bed in the race arena (stage `Stations.Length + 1`) and in Boss Battle mode (today boss mode reuses
  tier beds by level).
- `titan_roar`: when the titan appears: the race arena entry and boss mode's level start, offset from `boss_fight` /
  the boss voice lines by the 0.9 s rule.
- `crowd_cheer`: on the podium arrival (NOT on the kill instant: `boss_dead` + `boss_down` already fill it).
- `crowd_aww`: a wrong pad in the race arena and boss mode, after the penalty voice line (or instead of nothing where
  the window is free; say which).
- `volt_oops` / `volt_yay` (yay has no call site yet): only where they fit the mix rules; if no free window exists, leave
  them unused and say so. Do not put them under `correct` / `wrong`.
- `finish`: the Mint fanfare is 5.5 s (stock was 3.9 s) and `FinishCueGapSeconds` (1.6 s) puts the record / medal /
  perfect stingers on top of it. Decide (move them after the fanfare's peak, or shorten the gap logic) and state it.

## 3. The titan's entrance (Meshy clips bought, in `art/boss/raw/`)
`jumpslam_382.fbx` (Jump and Slam Back Down), `scream_386.fbx` (Zombie Scream), `shout_51.fbx` (Shouting Angrily); task
ids in `art/boss/meshy_tasks.json`. Memory matters (every clip imported with its own mesh is a full mesh copy): FIRST
try importing them as animation-only on the existing titan skeleton (Volt's clips all work that way:
`tools/import_mascot.py`); keep a clip that way only if it plays upright and in place in play frames; otherwise import
it with its own mesh the `import_boss.py` way. Then:
- Race arena: when the player enters, the titan plays the jump-slam once (the entrance) with `titan_roar`, then idles.
- Boss mode: the scream or the shout on a wrong pad (with or instead of `bm_boss_wrong`'s voice: mix rule), the
  jump-slam at each level start.
- Root motion: the jump-slam may move the mesh; check he lands where he started (frames).

## 4. The logo on the picker
`art/logo/logo_b_raw.png` (1024², transparent; DOORS in white / blue / green / orange, OF DOOM in lava) is the chosen
logo. Make `tools/art/fnm_logo.png` (crop to alpha, keep the aspect, ~512 px wide), import it like the other HUD
textures (`import_art.py logo`, never `--force`), and show it on the grade picker above "PICK YOUR GRADE" (colour rule:
`SetTint(FnmUi(White))`), sized so the picker still fits at 1080p with no overlap (layout test). Keep the small
"DOORS OF DOOM" title tag or drop it if the logo makes it redundant (say which).

## 5. Seen in play (under the lock; foreground allowed while you hold it)
One session per mode at most: race (`DebugAutoPick 7` + `DebugAutoRightAnswers true` + `DebugAutoWrongAnswers 8`) for
the picker logo + menu music log line, the arena entrance (frames of the jump-slam, upright, landing in place), the arena
music, crowd_aww on a wrong pad, crowd_cheer at the podium; boss mode (`DebugAutoBoss true` + `DebugAutoRightAnswers`)
for the level-start entrance and music_boss. Audio is proven by the director's `cue <id>` log lines plus no `(not
wired)` lines (nobody can listen). Restore hooks, `BuildAll` clean, session stopped.

## Disproof (one at least per section)
E.g. swap two cue ids in `FnmCueIds()` and see `tests/test_audio_cues.py` go red; a frame with the clip on the wrong
skeleton if it misplays; the logo pushed onto the buttons and the layout test red.

## Report (TEAM.md format), plus
Each cue's call site (file:line, the moment, the timing vs the mix rules), shared-skeleton yes/no per titan clip (and the
memory consequence), the logo size/position, frame paths (best first, at most 8), and anything for Aaron's ear.
