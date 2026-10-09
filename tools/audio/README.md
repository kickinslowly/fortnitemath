# Audio: announcer voice pack

Short arena-announcer lines in the Unreal Tournament style (DOUBLE... TRIPLE... UNSTOPPABLE) for GOALS.md G6 item 1.
Generated locally by Kokoro TTS (the `michael` project's model) and mastered by ffmpeg into UEFN-ready wavs. One folder
per voice so Aaron can pick by ear; the cue ids are the Verse enum names.

```
announcer/
  am_michael/<cue_id>.wav   recommended (see announcer/QA.md)
  am_onyx/<cue_id>.wav      recommended boss voice (the bm_boss_* lines, `boss` profile)
  bm_george/<cue_id>.wav
  manifest.json             per voice and cue: text, file, duration, peak, loudness, speed actually used
  QA.md                     duration / peak / LUFS per line, flags, the voice recommendation
```

## Regenerate

```
"D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py
"D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py --voice am_fenrir   # another voice
"D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py --cue penalty_yeet  # one line
```

Needs the michael venv (`kokoro_onnx`, `soundfile`, `numpy`), the model and voices in
`D:/PyCharm Projects/michael/models/cache/`, and `ffmpeg` on PATH. About a minute for all three voices. It never plays
audio. A rerun is byte-identical (checked: every wav plus manifest.json and QA.md; the 16 Boss Battle lines were rerun twice and compared).

## Add a line

Add a row to `LINES` at the top of `tools/make_announcer.py`: cue id (must match the Verse enum), the canonical text,
what Kokoro is actually fed (punctuation and spelling tweaks for delivery, e.g. "Yeeeet!"), speed (0.85 to 1.0), tail
(`dry`, `std`, `big`, `boss`) and length cap (2 s; 4 s for long lines). Rerun. If a voice overruns the cap it is re-spoken
5 % faster until it fits (up to 1.3x); the manifest records the speed used.

## Mastering

TTS 24 kHz float -> trim silence at -60 dB -> 70 Hz high-pass -> 4 % pitch drop (`asetrate`, so also 4 % slower) ->
48 kHz -> gentle compression -> short echo tail (60 to 240 ms, low mix) -> gain to -13 LUFS into a -1 dBFS limiter
(iterated until the final file reads -13 LUFS within 0.3 LU, or as close as the peak allows) -> trim at -60 dB ->
exact -1 dBFS peak -> 3 ms edge fades -> 40 ms silence at both ends -> mono 48 kHz 16-bit PCM wav.
The filter strings are constants at the top of the script.

### The `boss` profile (Boss Battle mode, 53 lines in all)

The eight `bm_boss_*` lines use a fourth tail profile, `boss`, deeper and grittier than `big`. Chain, in `stage1_chain`:
trim -> 70 Hz high-pass -> **one `asetrate` of 24000 x 0.96 x 0.82 = 18892** (the usual 4 % drop plus a further **18 %**
drop in one step, `BOSS_PITCH = 0.82`; the voice is also 18 % slower, so lines are spoken at 0.85 to 0.88 and still fit
their caps) -> 48 kHz -> the normal compressor -> `BOSS_GRIT` (`volume=6dB,asoftclip=type=tanh`, then a harder second
`acompressor=threshold=-18dB:ratio=4:attack=3:release=60:knee=3`) -> 0.6 s pad -> the `big` echo (`aecho=0.9:0.9:90|160|240:0.30|0.20|0.12`).
Stage 2 (-13 LUFS, limiter, -1 dBFS) is shared. Nothing was listened to; the numbers (all within 0.3 LU of -13 except
bm_george's boss lines, up to 1.3 LU) are in `announcer/QA.md`.

**Pick another boss voice:** all three voices are rendered for every line. Import the folder you want and pass it to
`python tools/build_audio.py --boss-voice <voice>` (recommended: am_onyx). Change the profile's depth with `BOSS_PITCH`
or the grit with `BOSS_GRIT`, then rerun with `--cue bm_boss_l1 ...` (repeatable) and `--voice`.

## Cues and durations (seconds)

`door_open` has no line (sound effect only).

| cue | text | am_michael | am_onyx | bm_george |
|---|---|---|---|---|
| streak2 | Double! | 0.84 | 0.83 | 0.95 |
| streak3 | Triple! | 0.90 | 0.90 | 1.02 |
| streak4 | Mega streak! | 1.25 | 1.23 | 1.40 |
| streak5 | Ultra streak! | 1.28 | 1.35 | 1.43 |
| streak6 | Monster streak! | 1.40 | 1.39 | 1.58 |
| streak7 | UNSTOPPABLE! | 1.47 | 1.64 | 1.61 |
| perfect | Flawless! Perfect run! | 1.73 | 1.93 | 1.97 |
| go | Go! | 0.81 | 0.78 | 0.96 |
| countdown3 | Three | 0.84 | 0.80 | 0.89 |
| countdown2 | Two | 0.73 | 0.75 | 0.85 |
| countdown1 | One | 0.73 | 0.71 | 0.81 |
| correct | Correct! | 0.82 | 0.89 | 0.91 |
| wrong | Wrong door! | 1.05 | 1.14 | 1.21 |
| finish | Finish! | 0.94 | 0.90 | 1.01 |
| new_best | New personal best! | 1.54 | 1.58 | 1.73 |
| new_record | NEW ISLAND RECORD! | 1.75 | 1.80 | 1.90 |
| medal_gold | Gold medal! | 1.06 | 1.15 | 1.25 |
| medal_silver | Silver medal! | 1.18 | 1.26 | 1.35 |
| medal_bronze | Bronze medal! | 1.14 | 1.33 | 1.45 |
| penalty_freeze | Frozen! | 1.05 | 1.06 | 1.15 |
| penalty_spike | Spiked! | 0.96 | 0.98 | 0.99 |
| penalty_mud | Stuck in the mud! | 1.27 | 1.39 | 1.53 |
| penalty_dizzy | Dizzy! | 0.83 | 0.88 | 0.94 |
| penalty_blackout | Lights out! | 1.10 | 1.13 | 1.28 |
| penalty_yeet | Yeet! | 1.03 | 0.97 | 1.14 |
| no_skip | No skipping! | 1.16 | 1.31 | 1.41 |
| guards_up | Guards ahead! | 1.14 | 1.24 | 1.28 |
| welcome | Welcome to Fortnite Math! | 1.86 | 2.10 | 2.19 |
| choose | Choose your grade and your skill. | 1.75 | 2.21 | 2.44 |
| boss_fight | Boss fight! | 1.10 | 1.12 | 1.26 |
| lifeline | Lifeline! | 1.09 | 1.22 | 1.22 |
| bm_start | Boss battle! | 1.22 | 1.38 | 1.48 |
| bm_level2 | Level two! | 1.20 | 1.12 | 1.33 |
| bm_level3 | Level three! | 1.22 | 1.27 | 1.33 |
| bm_level4 | Level four! | 1.21 | 1.20 | 1.37 |
| bm_level5 | Final level! | 1.28 | 1.41 | 1.40 |
| bm_mega_nuke | MEGA NUKE! | 1.32 | 1.35 | 1.57 |
| bm_level_clear | Level cleared! | 1.32 | 1.33 | 1.52 |
| bm_victory | VICTORY! Boss defeated! | 2.11 | 2.36 | 2.37 |
| bm_boss_l1 | You dare challenge ME?! | 2.12 | 2.73 | 2.44 |
| bm_boss_l2 | Minions! GET THEM! | 1.95 | 2.44 | 2.35 |
| bm_boss_l3 | Is that all you've got?! | 2.27 | 2.10 | 2.55 |
| bm_boss_l4 | Now I'm ANGRY! | 1.79 | 1.96 | 1.94 |
| bm_boss_l5 | NO MORE GAMES! EVERYONE, ATTACK! | 3.31 | 3.56 | 3.81 |
| bm_boss_wrong | HA! WRONG! | 1.45 | 1.64 | 1.77 |
| bm_boss_hit | ARGH! | 1.16 | 1.17 | 1.34 |
| bm_boss_dead | NOOOOO! | 1.25 | 1.22 | 1.47 |

Durations include the 40 ms pads and the echo tail. manifest.json is the live source; this table is a snapshot.

## Importing into UEFN (a GUI step)

Procedure and device wiring: `console/AUDIO.md` "Announcer" (Content Drawer > Import, a voice's whole folder in one go,
then `tools/build_audio.py --announcer <voice> --boss-voice <voice>`). Importing is not done by the generator.

UEFN's verdict on the 48 kHz mono 16-bit PCM wavs (am_michael, UEFN 42.30, 2026-10-07): one Sound Wave per file, named
after it, no options dialog. Read back from the assets: `importedSampleRate` 48000 and `sampleRate` 48000 (kept, not
resampled), `numChannels` 1, `sampleRateQuality` Max, `soundAssetCompressionType` PlatformSpecific with
`compressionQuality` 40 (UEFN's default lossy compression at cook), `loadingBehavior` Inherited, no sound class, not
looping. Durations match the manifest (streak2 0.837 s, welcome 1.860 s); UEFN's own analysis reads -13.26 LUFS and a
-1.0 dB sample peak, matching the mastering. A Sound Cue is not needed: the Creative audio player takes the SoundWave
directly.

## Licence

Kokoro-82M is Apache-2.0. The lines are generated speech: no attribution needed.
