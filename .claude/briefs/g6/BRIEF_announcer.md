# Brief B — Announcer voice pack for the fortnitemath island (local TTS, no UEFN)

You are building the announcer half of GOALS.md **G6 item 1** in `D:\PyCharm Projects\fortnitemath`: a pack of
short voice lines in the Unreal Tournament announcer spirit ("DOUBLE… TRIPLE… UNSTOPPABLE"), generated with the
local Kokoro TTS and mastered with ffmpeg into UEFN-ready wavs. Another builder is wiring the Verse/UEFN side at
the same time and never touches your files; you never touch theirs. Read first: `GOALS.md` §G6 (the plan),
`console/PENALTIES.md` (penalty names and tone), `~/.claude/skills/sfx-sourcing/SKILL.md` §"Trim + encode".

## Repo facts (checked 2026-10-07)
- Windows 11, Git Bash. The repo's own venv is `.venv/Scripts/python` (no TTS in it). Tests:
  `.venv/Scripts/python -m pytest -q` → 8685 passed; you add none of the repo's Python modules, so this stays as is.
- Kokoro lives in the sibling project: `D:\PyCharm Projects\michael\.venv\Scripts\python` has `kokoro_onnx`,
  `soundfile`, `numpy`; model `D:\PyCharm Projects\michael\models\cache\kokoro-v1.0.onnx`, voices
  `...\models\cache\voices-v1.0.bin`. Verified today:
  ```python
  from kokoro_onnx import Kokoro
  k = Kokoro(model_path, voices_path)
  samples, sr = k.create("Double! Triple! Unstoppable!", voice="am_michael", speed=1.0, lang="en-us")  # sr 24000
  ```
  2 s of audio in 0.6 s. Male voices available: `am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael,
  am_onyx, am_puck, am_santa, bm_daniel, bm_fable, bm_george, bm_lewis`.
- `ffmpeg` 8.1 (essentials build: no `rubberband`; pitch shift via `asetrate` + `aresample`, or `atempo`).
- Do NOT copy the model or voices into this repo. Do NOT add python packages to `.venv`.

## Deliverables (numbered; names fixed)
1. **`tools/make_announcer.py`**: deterministic generator. `LINES` table at the top: cue id → spoken text (below).
   `--voice NAME` (repeatable; default: the three voices in deliverable 3), `--out tools/audio/announcer`.
   For each voice × line: synthesize at the given `speed`, then master with ffmpeg into
   `tools/audio/announcer/<voice>/<cue_id>.wav`: mono, 48 kHz, 16-bit PCM, leading/trailing silence trimmed at
   -60 dB (keep the decay), 40 ms pad at both ends, peak-normalised to -1 dBFS, with an "arena" treatment:
   a slight pitch drop (3–5 %), a short reverb/echo tail (`aecho`, ≈ 60–120 ms, low mix) and gentle compression
   so every line sits at the same loudness (`loudnorm` or `acompressor` + normalise). Keep each line ≤ 2.0 s
   except `welcome` / `choose` (≤ 4 s). Write `tools/audio/announcer/manifest.json`: for each voice and cue id the
   text, file, duration (s), peak dBFS. Re-running must produce byte-identical files (fix every seed/param; if
   Kokoro is not bit-deterministic, say so and make the manifest's durations the stable check instead).
   Invocation documented at the top: `"D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py`.
2. **Lines** (cue ids are shared with the Verse enum; keep them exactly):
   | id | text | note |
   |---|---|---|
   | streak2 | Double! | |
   | streak3 | Triple! | |
   | streak4 | Mega streak! | |
   | streak5 | Ultra streak! | |
   | streak6 | Monster streak! | |
   | streak7 | UNSTOPPABLE! | the loudest, longest tail |
   | perfect | Flawless! Perfect run! | every door first try |
   | go | Go! | |
   | countdown3 / countdown2 / countdown1 | Three / Two / One | |
   | correct | Correct! | short, bright |
   | wrong | Wrong door! | |
   | door_open | (none) | no line; skip |
   | finish | Finish! | |
   | new_best | New personal best! | |
   | new_record | NEW ISLAND RECORD! | |
   | medal_gold / medal_silver / medal_bronze | Gold medal! / Silver medal! / Bronze medal! | |
   | penalty_freeze | Frozen! | |
   | penalty_spike | Spiked! | |
   | penalty_mud | Stuck in the mud! | |
   | penalty_dizzy | Dizzy! | |
   | penalty_blackout | Lights out! | |
   | penalty_yeet | Yeet! | drawn out: "Yeeeet!" if the voice can |
   | no_skip | No skipping! | |
   | guards_up | Guards ahead! | |
   | welcome | Welcome to Fortnite Math! | |
   | choose | Choose your grade and your skill. | |
   | boss_fight | Boss fight! | for G6 item 3 |
   | lifeline | Lifeline! | for G6 item 4 |
   Exclamation and capitals are hints for delivery: experiment with punctuation, `speed` 0.85–1.0 per line and
   a trailing "!" vs "." to get the punch; Kokoro reacts to them. Keep the text in the table as the canonical line.
3. **Three voice renders** so Aaron can pick by ear: `am_michael`, `am_onyx`, `bm_george` (if one is clearly weak —
   e.g. flat or mispronounces "Yeet" — swap it for `am_adam` or `am_fenrir` and say so). Same mastering for all.
4. **`tools/audio/README.md`**: what the pack is, the regenerate command, the cue table with durations, how a
   line is added (table row + rerun), import notes for UEFN (48 kHz mono 16-bit wav; import is a later GUI step,
   NOT yours), and the licence line (Kokoro is Apache-2.0; generated speech, no attribution needed).
5. **A quick QA sheet** `tools/audio/announcer/QA.md`: for each voice a table of duration, peak, loudness
   (`ffmpeg -af ebur128` integrated LUFS) per line; flag lines over the length cap or more than 2 LU from the
   voice's median. Pick the voice YOU would ship and say why (you cannot listen; argue from the numbers, the
   pronunciation risks you can see in Kokoro's phonemisation if it exposes them, and a one-line description of
   each voice from the model card if you can find it on disk — do not web-search).

## Non-goals / do NOT
- Do NOT touch anything outside `tools/make_announcer.py`, `tools/audio/**`. In particular not `console/**`,
  `tools/build_*.py`, `GOALS.md`, `CLAUDE.md`. Do NOT commit. Do NOT run UEFN MCP calls or any `tools/*.py`
  other than yours. Do NOT play audio through the speakers (Aaron may be in another app).
- Checkpoint every deliverable to disk the moment it exists.

## Report
Files created; the manifest summary (lines × voices, total size on disk); the QA table for your recommended voice;
the determinism result (byte-identical rerun, or not and why); the ffmpeg filter chain you settled on, verbatim.
Then two mandatory sections: **"Anything I decided differently from this brief and why"** and **"Shakiest
assumption, stated plainly"**.
