# B3 — Boss mode assets: voice lines, HUD art, cue rows (Sonnet, parallel with B1 and B2, after B0)

Repetitive, well-specified work: render 19 new voice lines, draw two textures, add 19 rows to the audio builder and the
docs. Read first: `briefs/bossmode/README.md`; `BOSS_MODE.md` §9 (textures) and §10 (the cue table: ids, order, stock
sounds, voice lines — copy them exactly); `tools/make_announcer.py` (all of it: `LINES`, the profiles, `render`,
`qa_sheet`); `tools/audio/README.md`; `tools/make_hud_art.py` (the no-PIL PNG writer and the antialiased shapes; copy its
style); `tools/build_audio.py` (`ANNOUNCER_CUES`, `CUES`, `BASE`, the `--announcer` path, `label()`); `console/AUDIO.md`
("Cues" table, "Announcer", "Rewire a cue"); `tests/test_audio_cues.py`; `tests/test_hud_layout.py`.

Precondition (B0 landed): `grep -c BmWeapon console/verse/fnm_audio.verse` → 2 (the enum and the lists have the 19 ids).

You own: `tools/make_announcer.py`, `tools/make_boss_art.py` (new), `tools/art/fnm_banner.png`, `tools/art/fnm_nuke.png`,
`tools/audio/announcer/**` (new wavs, `manifest.json`, `QA.md`), `tools/audio/README.md`, `tools/build_audio.py`,
`console/AUDIO.md`, `tests/test_hud_layout.py` (only the PNG size dict and the determinism test). Nothing in
`console/verse/`, no other `tools/build_*.py`, not `tools/import_art.py`. You never call the UEFN MCP (importing wavs and
textures is B4's GUI step). Do not commit.

## Repo facts
See README. Kokoro runs from the `michael` venv: `"D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py --cue <id>`
(repeatable `--cue`; `--voice` repeatable; default renders all three voices; needs ffmpeg on PATH — `ffmpeg -version`).
A rerun is byte-identical (the QA sheet and manifest are regenerated). Tests: `.venv/Scripts/python -m pytest -q`.
No PIL in `make_hud_art.py` by design (plain zlib PNG writer, deterministic, seeded); keep that.

## Deliverables

1. **`tools/make_announcer.py`**: add a `"boss"` tail profile (deeper and bigger than `big`: in `stage1_chain` an extra
   `asetrate` pitch drop of about 18 % (document the exact factor), the `big` echo, a gentle `acrusher`/saturation or a
   second compressor stage for grit; keep the rest of the mastering) and these `LINES` rows (cue id, canonical text, spoken
   text, speed, profile, cap):
   - announcer (am_michael style, `std`/`big`): `bm_start` "Boss battle!" (big, 2.0); `bm_level2` "Level two!" (std);
     `bm_level3` "Level three!"; `bm_level4` "Level four!"; `bm_level5` "Final level!" (big); `bm_mega_nuke` "MEGA NUKE!"
     (big, spoken "Mega nuke!"); `bm_level_clear` "Level cleared!" (big); `bm_victory` "VICTORY! Boss defeated!" (big, spoken
     "Victory! Boss defeated!", cap 3.0).
   - boss (`boss` profile, speed 0.85-0.9): `bm_boss_l1` "You dare challenge ME?!" (spoken "You dare challenge me?!", cap 3.0);
     `bm_boss_l2` "Minions! GET THEM!" ("Minions! Get them!", 3.0); `bm_boss_l3` "Is that all you've got?!" (3.0);
     `bm_boss_l4` "Now I'm ANGRY!" ("Now I'm angry!", 2.0); `bm_boss_l5` "NO MORE GAMES! EVERYONE, ATTACK!" ("No more games!
     Everyone, attack!", 4.0); `bm_boss_wrong` "HA! WRONG!" ("Ha! Wrong!", 2.0); `bm_boss_hit` "ARGH!" ("Argh!", 2.0);
     `bm_boss_dead` "NOOOOO!" ("Noooo!", 3.0).
   Render all three voices for the new cues only (`--cue` x16), check `QA.md` flags (no LEN, LOUD within 2 LU), listen-proxy:
   print each new wav's duration and peak from the manifest. The recommended boss voice is **am_onyx** (deepest of the three);
   say in `tools/audio/README.md` how to pick another.
2. **`tools/make_boss_art.py`** (new; `python tools/make_boss_art.py [OUTDIR]` writes `fnm_banner.png` and `fnm_nuke.png`,
   deterministic, seeded, no PIL; reuse `make_hud_art.png`, `cover`, `rounded_dist` by import):
   - `fnm_banner.png` 1024 x 256 RGBA: a comic speech-burst. Outline as a star polygon in polar form around the centre with
     radius r(θ) = R(θ) · (1 + 0.16 · |sin(11 θ)| + small seeded jitter) where R stretches to an ellipse 480 x 108; fill a red
     core (200, 30, 30) to orange rim (255, 140, 20) radial gradient, 6 px dark outline (40, 10, 10), antialiased edge,
     transparent outside. Alpha 245 inside.
   - `fnm_nuke.png` 256 x 256 RGBA: a mushroom cloud: a cap (circle centre (128, 92), r 70, with three smaller bumps on top),
     a stem (rounded rect 60 wide from y 120 to 210), a base ring (ellipse 170 x 40 at y 205); fill pale yellow (255, 236, 150)
     with a lighter top, 6 px dark outline (40, 30, 10), transparent outside. Must read at 240 px on a dark slate and over
     the arena.
   Write both to `tools/art/`. Add the two sizes to `tests/test_hud_layout.py::test_png_sizes_and_format` and extend
   `test_hud_art_is_deterministic` to run `make_boss_art.py` twice and compare with the committed files (same shape as the
   existing test). `test_every_texture_has_a_png_and_every_png_is_used` turns green only when B1 references the textures;
   until then it is red because of the PNGs you added — expected, say so, do not touch the test's logic.
3. **`tools/build_audio.py`**: 19 `CUES` rows appended in BOSS_MODE.md §10 order with the stock sounds named there (voice-only
   cues get `None`), full asset paths in the house style (`f"{STING}/Stinger_Threat_01.Stinger_Threat_01"` etc.; check each
   package/object name casing against the existing rows — `test_builder_table_matches_and_is_allowed` pins the prefix and
   the package = object rule); `ANNOUNCER_CUES` gains `bm_start`, `bm_level2..5`, `bm_mega_nuke`, `bm_level_clear`,
   `bm_victory`; new `BOSS_CUES = ["bm_boss_l1", ..., "bm_boss_l5", "bm_boss_wrong", "bm_boss_hit", "bm_boss_dead"]` and a
   `--boss-voice <voice>` flag that puts `/<mount>/FNM_Audio/<voice>/<cue>.<cue>` on those devices at `VO_VOLUME` (mirror the
   `--announcer` code path; a cue whose wave is not imported logs `NOT IMPORTED, stock kept` or is skipped when it has no
   stock, exactly as the announcer-only cues behave today). `--list` must accept a boss wave only on a BOSS_CUES device.
   Do not run the builder (no MCP).
4. **`console/AUDIO.md`**: the 19 rows in the Cues table (moment column names the director function from BOSS_MODE.md §6/§7),
   a "Boss voice" paragraph under "Announcer" (the `boss` profile, `--boss-voice am_onyx`, the import folder), and the
   commands. **`tools/audio/README.md`**: the boss profile and the new line count.

## Non-goals
No Verse, no UEFN. Do not change existing lines' text or mastering (the 46 shipped wavs must stay byte-identical: check with
`git status tools/audio` — only new files and the regenerated manifest/QA may differ, and the manifest's existing entries
must be unchanged). Do not rename cue ids. Do not restyle the slate art.

## Concurrency
B1 edits `console/verse/*` (it references `FNM_Art.T_fnm_banner` / `T_fnm_nuke` — your filenames must be exactly
`fnm_banner.png` / `fnm_nuke.png`). B2 edits `tools/build_bossmode.py`, `build_cannon.py`, `import_art.py`, `LAYOUT.md`,
`tests/test_bossmode_layout.py`. Nobody else touches your files.

## Verification (paste outputs)
- `"D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py --cue bm_boss_l1` twice → identical bytes
  (`cmp`), then the full new-cue render; `ls tools/audio/announcer/am_onyx | wc -l` → 37 + 16 = 53 (check the count against the
  folder's current 37).
- `python tools/make_boss_art.py` twice into scratch dirs → byte-identical; `python -c` print the IHDR sizes (1024 x 256,
  256 x 256, 8-bit RGBA).
- Look at both PNGs (Read them): the burst must have visible spikes and a readable dark outline; the cloud must read as a
  mushroom cloud at a glance. Say what you see.
- `.venv/Scripts/python -m pytest -q tests/test_audio_cues.py tests/test_hud_layout.py`: `test_builder_table_matches_and_is_allowed`
  green (B0 extended MEMBERS), `test_png_sizes_and_format` and `test_hud_art_is_deterministic` green,
  `test_every_texture...` red only if B1 has not landed (precondition `grep -c T_fnm_nuke console/verse/fnm_ui.verse`).
- One disproof: swap two CUES rows (`bm_gates` and `bm_weapon`) in a scratch copy → `test_builder_table_matches_and_is_allowed`
  red; restore.
- `python tools/build_audio.py --help` shows `--boss-voice`.

## Report
README format, plus: durations and peaks of the 16 new lines per voice, the exact `boss` profile chain, the PNGs described in
words, anything you decided differently and why, your shakiest assumption stated plainly (the planner's: that the stock
sounds named in §10 exist at those exact paths — `--probe` is B4's to run, so flag any you could not confirm from the
existing rows).
