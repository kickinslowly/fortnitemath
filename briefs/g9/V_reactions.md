# Brief V: Volt reaction cards on the HUD (Meshy art bought 2026-10-13 evening)

Read `briefs/g9/TEAM.md` first (the UEFN lock, the machine rules, the report format; the test baseline there is old:
it is now **17320 passed**). Then `briefs/g9/H2_medals.md` (how the medal art and the Volt portrait went in: the same
path you will use). You are **V**, model Sonnet. The manager (Opus 5.5) wrote this brief and audits your diff. Two other
builders work at the same time and share the UEFN lock: **A** (audio, `tools/build_audio.py`) and **P** (volcano +
trophy, scene only). Neither touches Verse.

## You own (may edit)
`console/verse/fnm_ui.verse`, `console/verse/fnm_director.verse`, `console/verse/fnm_bossmode.verse`,
`console/verse/fnm_audio.verse`; `tests/test_hud_layout.py` (+ a new `tests/test_volt_reactions.py` if cleaner);
`tools/make_medal_art.py`; new PNGs `tools/art/fnm_volt_{wag,thumbs,fire,shocked,go,think}.png`. Nothing else. No
commits. Ship values of the debug hooks restored when you report (`git diff console/verse/fnm_director.verse` shows
only your feature, no hook flips).

## Inputs (bought, in the repo, untracked)
`art/mascot/reactions/{wag,thumbs,fire,shocked,go,think}_raw.png`: 1024x1024 RGBA, transparent, Volt in the same
sticker style and framing as `art/mascot/hud_portrait_raw.png` (which became `tools/art/fnm_volt.png`, the cheering one
on the finish board). Task ids in `art/mascot/reactions/meshy_tasks.json`.
- wag: finger wag "nope", scolding LED face. thumbs: thumbs up + wink. fire: both fists up, cartoon flames, star eyes.
- shocked: hands on helmet, sweat drop. go: pointing forward, determined. think: hand on chin, a cyan "?" over him.

## Deliverables
1. **Art.** Extend `tools/make_medal_art.py` (same treatment: alpha floor, crop to bbox, pad square, 256 px LANCZOS) to
   write the six `tools/art/fnm_volt_<kind>.png`. Look at them composited on a dark background (Read the PNG).
   Import under the lock: `.venv/Scripts/python tools/import_art.py volt_wag volt_thumbs volt_fire volt_shocked volt_go
   volt_think` (plain run, never `--force`; read its docstring first). Confirm the six `T_fnm_volt_*` exist.
2. **HUD card** (`fnm_ui.verse`): one Volt reaction card per player, about 170-190 px, in ONE fixed screen spot that
   overlaps nothing the HUD already draws at 1920x1080 (slate, tiles, strip, clock, recap card, captions, banners, boss
   bar, finish board): find the free spot from the layout code and `tests/test_hud_layout.py`, state the coordinates,
   add a layout test that fails if it overlaps the others. New method(s) only (seam rule in TEAM.md), e.g.
   `ShowVolt(Player:agent, Kind:string)` + `HideVolt(Player)`. Shows for ~1.8 s; a newer call swaps the image and
   restarts the timer (a generation counter, so an old timer never hides a newer card). Picture only, no caption.
   **Colour rule:** `SetTint(FnmUi(NamedColors.White))` like every other texture (CLAUDE.md "HUD colours"; the test
   enforces it). The finish board already shows Volt: `ShowResults` hides the card.
3. **Director / boss mode calls** (the only director change in this round; pure UI side effects, no game logic touched):
   | moment | card |
   |---|---|
   | run start, on the GO | go |
   | right door, streak below 3 | thumbs |
   | right door that makes the streak 3 or more | fire |
   | wrong door (the moment it is judged) | wag |
   | a penalty landing on the player ("You got frozen" etc.) | shocked |
   | the retry spot (the wide camera on the four doors) | think |
   | race finale: a direct hit on the titan (not the killing hit: the board follows it) | thumbs |
   | boss mode: right pad / wrong pad | thumbs / wag |
   Only to the player the event is about (the HUD is per player). If two land within a second, the later one wins.
4. **Sound hooks (ids only).** Add two cue ids to `fnm_audio.verse` (enum + `FnmCues()` + `FnmCueIds()`, same order in
   both): `VoltYay` / `"volt_yay"` and `VoltHmm` / `"volt_hmm"`. Play `volt_hmm` at the retry spot only (a quiet moment;
   anywhere else it would stack on `correct`/`wrong`/voice lines, see `console/AUDIO.md` mix rules). Builder A adds the
   matching `CUES` rows in `tools/build_audio.py`; until the waves are imported a cue with no device is a logged no-op
   (check the director really treats a missing cue device that way: say what you saw in the log).
5. **Compile:** copy only your changed Verse files into the Verse root (TEAM.md "Compiling"), `BuildAll` must be `[]`.
6. **Seen in play** (under the lock): ONE session, `DebugAutoPick 7` + `DebugAutoRightAnswers true` +
   `DebugAutoWrongAnswers 8` (run 1: two wrong doors at each of stations 1-4; run 2: none, so the streak reaches 3).
   Bursts (`tools/burst.py`) to catch, and READ: go, wag, shocked, think, thumbs, fire. Each card: right image, tinted
   like the PNG (not washed out, not dark), overlapping nothing. Restore the hooks, copy, `BuildAll` clean, stop the
   session. If a card never shows in frames, find out why (log a `FNM: volt <kind>` line from `ShowVolt` to prove the
   call happened).

## Disproof (one at least)
Map one kind to the wrong texture (e.g. wag shows thumbs) and see it in a frame or a test go red; or drop one
`SetTint`; restore by re-applying the original text.

## Report (TEAM.md format), plus
The card position and size, the method signatures added, each director/boss call site (file:line, which event), the
frame paths (best first, at most 8), and whether `volt_hmm` with no device logged a no-op or anything worse.
