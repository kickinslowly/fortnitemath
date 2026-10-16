# X: two spare voice takes still say "Fortnite Math" (Haiku)

Read `briefs/g10/TEAM.md` "Roster" and "Report format" only. You own `tools/audio/announcer/am_onyx/`,
`tools/audio/announcer/bm_george/`, `tools/audio/announcer/manifest.json`, `tools/audio/announcer/QA.md`. Nothing else.
No UEFN, no lock, no commits.

## Task

The game was renamed DOORS OF DOOM. `tools/make_announcer.py` already has the new welcome line ("Welcome to Doors of
Doom!") and the live voice (am_michael) was regenerated, but the two spare voices' `welcome` takes and their manifest
rows still say "Welcome to Fortnite Math!" (manifest.json around lines 1048 and 1739).

1. Save a copy of `manifest.json` to your scratch folder (TEAM.md) first.
2. Regenerate only the welcome cue for the two spare voices, with the michael project's venv (it has kokoro):
   `cd "D:/PyCharm Projects/fortnitemath" && "D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py --voice am_onyx --voice bm_george --cue welcome`
   Read the script's `main()` first to confirm `--cue` does not drop the other rows from manifest.json or overwrite
   am_michael. If it would, stop and report instead of running it.
3. Verify:
   - `grep -c "Fortnite Math" tools/audio/announcer/manifest.json` is 0.
   - `git diff --stat` shows only the two `welcome.wav` files, `manifest.json` and maybe `QA.md` changed; nothing under
     `am_michael/`.
   - `git diff tools/audio/announcer/manifest.json` changes only the two welcome rows (text, spoken, and any
     duration/peak fields). Paste the diff into your report.
   - Each new wav is mono 48 kHz 16-bit (`python -c "import wave; w=wave.open(p); print(w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes()/w.getframerate())"`)
     and 1-4 s long.
4. Report per TEAM.md (short).
