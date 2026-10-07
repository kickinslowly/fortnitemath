# Audio: announcer voice pack

Short arena-announcer lines in the Unreal Tournament style (DOUBLE... TRIPLE... UNSTOPPABLE) for GOALS.md G6 item 1.
Generated locally by Kokoro TTS (the `michael` project's model) and mastered by ffmpeg into UEFN-ready wavs. One folder
per voice so Aaron can pick by ear; the cue ids are the Verse enum names.

```
announcer/
  am_michael/<cue_id>.wav   recommended (see announcer/QA.md)
  am_onyx/<cue_id>.wav
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
audio. A rerun is byte-identical (checked: all 93 wavs plus manifest.json and QA.md).

## Add a line

Add a row to `LINES` at the top of `tools/make_announcer.py`: cue id (must match the Verse enum), the canonical text,
what Kokoro is actually fed (punctuation and spelling tweaks for delivery, e.g. "Yeeeet!"), speed (0.85 to 1.0), tail
(`dry`, `std`, `big`) and length cap (2 s; 4 s for long lines). Rerun. If a voice overruns the cap it is re-spoken
5 % faster until it fits (up to 1.3x); the manifest records the speed used.

## Mastering

TTS 24 kHz float -> trim silence at -60 dB -> 70 Hz high-pass -> 4 % pitch drop (`asetrate`, so also 4 % slower) ->
48 kHz -> gentle compression -> short echo tail (60 to 240 ms, low mix) -> gain to -13 LUFS into a -1 dBFS limiter
(iterated until the final file reads -13 LUFS within 0.3 LU, or as close as the peak allows) -> trim at -60 dB ->
exact -1 dBFS peak -> 3 ms edge fades -> 40 ms silence at both ends -> mono 48 kHz 16-bit PCM wav.
The filter strings are constants at the top of the script.

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

Durations include the 40 ms pads and the echo tail. manifest.json is the live source; this table is a snapshot.

## Importing into UEFN (later, a GUI step)

The wavs are 48 kHz, mono, 16-bit PCM: UEFN imports them as Sound Waves as they are. Copy the chosen voice's folder into
the UEFN project's Content (drag into the Content Browser, or Import), make a Sound Cue or point an
`audio_player_device` at each wave, and play it per player (`Play(Agent)`). Importing is not done by the generator.

## Licence

Kokoro-82M is Apache-2.0. The lines are generated speech: no attribution needed.
