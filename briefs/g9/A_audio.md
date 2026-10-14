# Brief A: Mint music and sound effects, processed, staged and wired (bought 2026-10-13 evening)

Read `briefs/g9/TEAM.md` first (the UEFN lock, the machine rules, the report format; the test baseline there is old:
it is now **17320 passed**), then `console/AUDIO.md` (the cue table, the announcer import procedure and why it is GUI
only, the mix rules) and the top of `tools/build_audio.py`. You are **A**, model Sonnet. The manager (Opus 5.5) wrote
this brief and audits your work. Two other builders work at the same time and share the UEFN lock: **V** (Verse: it
adds the cue ids `volt_yay` and `volt_hmm` to `fnm_audio.verse`) and **P** (volcano + trophy, scene only).

## You own (may edit)
`tools/build_audio.py`, `console/AUDIO.md`, new `tools/make_mint_audio.py`, new `tests/test_mint_audio.py`, files
under `art/audio/mint/` and `tools/audio/mint/`, `.gitignore` (one block for the processed wavs, if you keep them out of
git). No Verse, no other files, no commits. **Do not start any Mint generation** (the manager controls spend); read-only
Mint calls are fine (`list_asset_artifacts`, `get_asset_artifact`, `get_credits_balance`). Never take the foreground.

## Inputs: finished or finishing Mint audio (project "First Project"), by asset id
Already downloaded: `art/audio/mint/ice_crack.mp3` (xd7d6sbfy7pg6xp32z841r82dh8g9h8h, 2 s).
Music beds, 60 s each, all asked for at 120 BPM in D minor, "no intro, no ending, loops seamlessly" (a request, not a
promise), two takes per tier where one exists:
| file stem | asset id | ask |
|---|---|---|
| music_t1_a | xd71rr31w3h6m58s4tn7a98wm98g9vf4 | calmest: hand drums, shaker, marimba, half-time |
| music_t1_b | xd75a5pgczb0k7atgndyqexca58g92dq | calmest: bongos, kalimba |
| music_t2_a | xd79dmvtma4dcvjkh8cht8hva58g987w | light kit, synth arp, pizzicato |
| music_t2_b | xd78j22dr35cy8j9jarxjy9cg58g8wn7 | bouncy, flute |
| music_t3_a | xd7f9q8kq4nkvkvrgf7a7jbrm98g9c9c | kit groove, synth bass, brass stabs |
| music_t3_b | xd7d2zs2dp982d2g7gz93x4skd8g8dvc | icy ridge, bells |
| music_t4_a | xd7cspz53054jb3ennv25r0z258g8x2v | intense: strings ostinato, brass |
| music_t4_b | xd7e446ffypgzjhhfx6hr927sh8g993w | intense: toms, distorted bass |
| music_t5_a | xd7e5v6x790v11q47rtzahev0n8g8ps7 | peak: orchestra, choir pads |
| fanfare_a | xd72am8cq6b154hsfapf2hzny58g901d | 7 s victory fanfare, brass + timpani |
| fanfare_b | xd733f5w0j86zafg92bg3zej558g9awm | 7 s victory fanfare, brass + snare |
| volt_yay | xd7azm9yjv2tf5vaggrm7jj7js8g9vkd | 1.2 s happy robot chirp |
| volt_hmm | xd7cxvexwrt63zk8md2sx70bw18g854q | 1.5 s thinking robot warble |
| portal_whoosh | xd7bzyjep5a9xa8pcdghcv6m198g86rr | 1.5 s sparkle whoosh |
Fetch each with `list_asset_artifacts` (artifact `audio_file`, mp3) then `get_asset_artifact` (a durable `downloadUrl`)
and `curl` it to `art/audio/mint/<stem>.mp3`. If one is not finished yet, do the rest and come back to it; if
`wait_for_status` is refused by the permission checker, poll with `list_asset_artifacts` instead.

## Deliverables
1. **`tools/make_mint_audio.py`** (ffmpeg is on PATH; stdlib + numpy if you need it): mp3 in `art/audio/mint/` ->
   44.1 kHz 16-bit wav in `tools/audio/mint/<cue>.wav`, re-runnable, prints a table (duration, integrated LUFS, true
   peak, loop seam score).
   - **Music:** a seamless loop. Find the downbeat grid (120 BPM = 2.0 s a bar; verify the tempo from onsets, do not
     trust the prompt), cut to a whole number of bars (e.g. 28 bars = 56 s) avoiding any intro/fade, and crossfade the
     last bar into the first (equal power) so the seam is inaudible. Score the seam (RMS jump and spectral distance
     across the wrap) and print it. Loudness: every bed to the same integrated loudness (about -18 LUFS; they play
     under voice lines at device volume 0.5, like the stock beds today), true peak <= -1 dBTP.
   - **SFX / fanfare:** trim leading silence (<= 10 ms left), fade the tail, peak -1 dBTP, loudness matched to each
     other (about -16 LUFS short-term at their loudest).
   - Choose ONE take per tier for `music_t<N>.wav` by the numbers you can measure (seam score, no silence gaps, steady
     loudness, tempo close to 120, no vocals: a Whisper pass with `tools/hear_voice.py`'s approach is a fair check), and
     keep the other take as `music_t<N>_alt.wav`. Say why each was chosen. Aaron picks by ear later.
   - Write `tools/audio/mint/LISTEN.md`: the table, which take is in, and the one-line ask for each file.
2. **`tools/build_audio.py --mint`**: like `--announcer`, put the project's imported Mint waves
   (`/<mount>/FNM_Audio/mint/<cue>.<cue>`) on these cues when imported, and keep stock (or "not wired") otherwise:
   `music_t1..music_t5` (looping, the LOOP props the stock beds use), `finish` (the chosen fanfare), `door_open`
   (portal_whoosh), and the two new cue ids `volt_yay`, `volt_hmm` (new `CUES` rows with no stock stand-in, like
   `direct_hit`: placed only once imported, else a logged "(not wired)"). Combinable with `--announcer` and
   `--boss-voice` (the full live command is in AUDIO.md). `--list` reports source `mint` for those devices. A run
   reports `NOT IMPORTED, stock kept: ...` for each Mint cue whose wave is missing. Tests in `tests/test_mint_audio.py`
   (pure Python: the cue list, path building, the flag's composition with the other two, the loop-length maths).
3. **Import probe (time-box 30 min, under the lock, NO foreground):** AUDIO.md says a wav dropped into `Content/` is
   never picked up. Try to make it so, headlessly: UE's auto-import lives in the editor settings object
   `/Script/UnrealEd.Default__EditorLoadingSavingSettings` (`bMonitorContentDirectories`, `AutoReimportDirectorySettings`
   with `SourceDirectory`, `MountPoint`, `Wildcards`, and the "auto create assets" flag). Read it with ObjectTools
   `get_properties`; if writable via `set_properties`, point a rule at the project's Content folder for this project's
   mount (`/<mount>/`, see `build_audio.project_id()`), drop ONE small wav (`volt_yay.wav`) into
   `C:/Users/kicki/Documents/Fortnite Projects/FortniteMath/Content/FNM_Audio/mint/`, wait, `find_assets` for it. Put
   every setting you changed back exactly as you found it (read back to prove it). Report what happened either way.
   If it works: import all the chosen waves that way, `save_assets`, then run
   `python tools/build_audio.py --announcer am_michael --boss-voice am_onyx --mint` and `--list`.
   If it does not: stop there; the GUI import (AUDIO.md steps, folder `FNM_Audio/mint`) waits for the manager to
   schedule it when Aaron is away. Copy the chosen wavs to a short path `%TEMP%\fnm_mint` ready for it.
4. **AUDIO.md**: a "Mint music and SFX" section (where the files are, how they were made, the `--mint` command, the import
   route that works, which cues they cover, that Aaron's ear has not judged them yet).

## Disproof (one at least)
E.g. feed `make_mint_audio.py` a deliberately bad loop point and show the seam score flag it; or run `--mint` with one
wave missing and show it keeps stock for that cue only.

## Report (TEAM.md format), plus
The table from `make_mint_audio.py`, which take you chose per tier and why, the import probe result (exact settings
read and restored), the Mint balance you read at the start and end (it should not change: you start nothing), and the
command that wires everything once the waves are in.
