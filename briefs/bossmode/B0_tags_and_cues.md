# B0 — Verse tags and cue enum for boss mode (serial, first)

Read first: `briefs/bossmode/README.md` (repo facts, ownership), `BOSS_MODE.md` §3 (tag table), §8 (tag list), §10 (the
19 cues, exact order), `CLAUDE.md` "Gotchas", `console/AUDIO.md` "Rewire a cue" (last paragraph: how a new cue id is added),
`console/verse/fnm_tags.verse`, `console/verse/fnm_audio.verse` (the enum, `FnmCues`, `FnmCueIds`, `FnmCueTags` in tags),
`tests/test_audio_cues.py`.

You own: `console/verse/fnm_tags.verse`, `console/verse/fnm_audio.verse` (the enum and `FnmCues` / `FnmCueIds` only),
`tests/test_audio_cues.py` (the `MEMBERS` string only). Nothing else. Do not commit.

## Deliverables

1. `fnm_tags.verse`: after the pickup tags block, a commented block "Boss battle mode (tools/build_bossmode.py, BOSS_MODE.md
   §3)" declaring exactly these tag classes:
   `fnm_bm`, `fnm_bm_boss`, `fnm_bm_gate`, `fnm_bm_gate_fx`, `fnm_bm_perch`, `fnm_bm_perch_fx`, `fnm_bm_grant`,
   `fnm_bm_cannon_fx`, `fnm_bm_strike`, `fnm_bm_blast`, `fnm_bm_nuke_fx`, `fnm_bm_anger_fx`, `fnm_bm_slot_1` .. `fnm_bm_slot_5`
   (each `name := class(tag){}` on its own line, the shape the file already uses), and
   `FnmBmSlotTags()<transacts>:[]castable_subtype(tag) = array{fnm_bm_slot_1, fnm_bm_slot_2, fnm_bm_slot_3, fnm_bm_slot_4, fnm_bm_slot_5}`.
   Also the 19 cue tag classes `fnm_cue_bm_start` .. `fnm_cue_bm_weapon` (ids in §10 order) appended to the cue tag block,
   and the same 19 appended to `FnmCueTags()` in order.
2. `fnm_audio.verse`: the 19 enum members appended after `BossDown` in §10 order (`BmStart`, `BmLevel2`, `BmLevel3`,
   `BmLevel4`, `BmLevel5`, `BmBossL1`..`BmBossL5`, `BmBossWrong`, `BmBossHit`, `BmBossDead`, `BmNuke`, `BmMegaNuke`,
   `BmLevelClear`, `BmVictory`, `BmGates`, `BmWeapon`), each with a one-line comment; the same appended to `FnmCues()` and
   their snake ids to `FnmCueIds()` (`bm_start`, `bm_level2`, ..., `bm_boss_l1`, ..., `bm_mega_nuke`, `bm_level_clear`,
   `bm_victory`, `bm_gates`, `bm_weapon`).
3. `tests/test_audio_cues.py`: extend `MEMBERS` with the 19 names in order. `test_builder_table_matches_and_is_allowed`
   will then be RED (B3 adds the CUES rows); say so in the report, do not touch `tools/build_audio.py`.
4. Sync and compile: `.venv/Scripts/python -m fnm sync starter` then
   `.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'` → `[]`. Before the first MCP call,
   screenshot the left monitor and dismiss any UEFN dialog (README). Prove the build is real once: temporarily add a line
   `FnmBmBogus := class(tag){}}` (unbalanced) to the synced copy in the project, BuildAll → an error; restore (re-sync), BuildAll → `[]`.

## Verification
- `.venv/Scripts/python -m pytest -q tests/test_audio_cues.py tests/test_hud_layout.py -q`: `test_enum_members_exact`,
  `test_snake_ids_follow_enum`, `test_tags_declared_in_enum_order`, `test_verse_files_are_lf` green;
  `test_builder_table_matches_and_is_allowed` red for the expected reason only.
- `grep -c "fnm_bm_slot_" console/verse/fnm_tags.verse` → 10 (5 classes + 5 in the array).
- `git diff --stat` touches exactly the three files.

## Report
README format. Say the BuildAll result verbatim and whether a dialog had to be dismissed.
