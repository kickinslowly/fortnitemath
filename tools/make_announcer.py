"""Announcer voice pack: Kokoro TTS -> ffmpeg "arena" mastering -> UEFN-ready wavs.

Run with the michael project's venv (it has kokoro_onnx; this repo's .venv does not):

    "D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py
    "D:/PyCharm Projects/michael/.venv/Scripts/python" tools/make_announcer.py --voice am_onyx --out tools/audio/announcer

Writes tools/audio/announcer/<voice>/<cue_id>.wav (mono, 48 kHz, 16-bit PCM) plus manifest.json and QA.md.
Add a line: add a row to LINES (cue id = the Verse enum name) and rerun. Deterministic: same inputs, same bytes.
Needs ffmpeg on PATH. Never plays audio.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parent.parent
MICHAEL = Path("D:/PyCharm Projects/michael/models/cache")
MODEL = MICHAEL / "kokoro-v1.0.onnx"
VOICES = MICHAEL / "voices-v1.0.bin"
DEFAULT_VOICES = ["am_michael", "am_onyx", "bm_george"]

# cue id -> (canonical text, what Kokoro is fed, speed, tail profile, length cap s)
# A voice that overruns the cap at this speed is re-spoken faster automatically (manifest "speed" = what was used).
# The canonical text is the line as written (and shown in the manifest); "say" is the delivery tweak.
LINES: dict[str, tuple[str, str, float, str, float]] = {
    "streak2":          ("Double!",                           "Double!",                           0.90, "std", 2.0),
    "streak3":          ("Triple!",                           "Triple!",                           0.90, "std", 2.0),
    "streak4":          ("Mega streak!",                      "Mega streak!",                      0.90, "std", 2.0),
    "streak5":          ("Ultra streak!",                     "Ultra streak!",                     0.90, "std", 2.0),
    "streak6":          ("Monster streak!",                   "Monster streak!",                   0.90, "std", 2.0),
    "streak7":          ("UNSTOPPABLE!",                      "Unstoppable!",                      0.85, "big", 2.0),
    "perfect":          ("Flawless! Perfect run!",            "Flawless! Perfect run!",            0.95, "std", 2.0),
    "go":               ("Go!",                               "Go!",                               0.90, "std", 2.0),
    "countdown3":       ("Three",                             "Three!",                            0.90, "dry", 2.0),
    "countdown2":       ("Two",                               "Two!",                              0.90, "dry", 2.0),
    "countdown1":       ("One",                               "One!",                              0.90, "dry", 2.0),
    "correct":          ("Correct!",                          "Correct!",                          1.00, "dry", 2.0),
    "wrong":            ("Wrong door!",                       "Wrong door!",                       0.95, "std", 2.0),
    "finish":           ("Finish!",                           "Finish!",                           0.90, "std", 2.0),
    "new_best":         ("New personal best!",                "New personal best!",                0.95, "std", 2.0),
    "new_record":       ("NEW ISLAND RECORD!",                "New island record!",                0.90, "big", 2.0),
    "medal_gold":       ("Gold medal!",                       "Gold medal!",                       0.90, "std", 2.0),
    "medal_silver":     ("Silver medal!",                     "Silver medal!",                     0.90, "std", 2.0),
    "medal_bronze":     ("Bronze medal!",                     "Bronze medal!",                     0.90, "std", 2.0),
    "penalty_freeze":   ("Frozen!",                           "Frozen!",                           0.90, "std", 2.0),
    "penalty_spike":    ("Spiked!",                           "Spiked!",                           0.90, "std", 2.0),
    "penalty_mud":      ("Stuck in the mud!",                 "Stuck in the mud!",                 0.95, "std", 2.0),
    "penalty_dizzy":    ("Dizzy!",                            "Dizzy!",                            0.90, "std", 2.0),
    "penalty_blackout": ("Lights out!",                       "Lights out!",                       0.90, "std", 2.0),
    "penalty_yeet":     ("Yeet!",                             "Yeeeet!",                           0.85, "std", 2.0),
    "no_skip":          ("No skipping!",                      "No skipping!",                      0.95, "std", 2.0),
    "guards_up":        ("Guards ahead!",                     "Guards ahead!",                     0.95, "std", 2.0),
    "welcome":          ("Welcome to Fortnite Math!",         "Welcome to Fortnite Math!",         0.95, "std", 4.0),
    "choose":           ("Choose your grade and your skill.", "Choose your grade and your skill.", 1.00, "dry", 4.0),
    "boss_fight":       ("Boss fight!",                       "Boss fight!",                       0.90, "std", 2.0),
    "lifeline":         ("Lifeline!",                         "Lifeline!",                         0.90, "std", 2.0),
}
# door_open has no line (sound effect only), so it is not in the table.

SR_TTS = 24000
SR_OUT = 48000
PITCH = 0.96          # 4 % pitch drop (asetrate; also 4 % slower, which suits an announcer)
PAD_S = 0.040         # silence at both ends of the final file
PEAK_DB = -1.0        # final peak
TARGET_LUFS = -13.0   # loudness of every final file (gain into a -1 dBFS limiter, iterated)
TRIM_DB = -60.0       # silence threshold (keeps the reverb decay)
FADE = int(0.003 * SR_OUT)

# aecho in_gain:out_gain:delays(ms):decays. Low mix; "big" = the UNSTOPPABLE / record tail.
ECHO = {
    "dry": "aecho=0.9:0.9:60:0.12",
    "std": "aecho=0.9:0.9:70|120:0.20|0.12",
    "big": "aecho=0.9:0.9:90|160|240:0.30|0.20|0.12",
}
TAIL_PAD = {"dry": 0.25, "std": 0.35, "big": 0.6}

TRIM_IN = ("silenceremove=start_periods=1:start_threshold=-60dB,areverse,"
           "silenceremove=start_periods=1:start_threshold=-60dB,areverse")
COMPRESS = "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:knee=4"
LIMIT = "alimiter=limit=0.891:attack=5:release=50:level=0:latency=1"


def stage1_chain(profile: str) -> str:
    """Raw TTS (24 kHz float) -> trimmed, pitched-down, compressed, echoed 48 kHz float."""
    return ",".join([
        TRIM_IN,
        "highpass=f=70",
        f"asetrate={int(SR_TTS * PITCH)}",
        f"aresample={SR_OUT}",
        COMPRESS,
        f"apad=pad_dur={TAIL_PAD[profile]}",
        ECHO[profile],
    ])


def stage2_chain(gain_db: float) -> str:
    return f"volume={gain_db:.3f}dB,{LIMIT}"


def ffmpeg(src: Path, dst: Path, af: str, extra: list[str] | None = None) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", af,
           "-ac", "1", "-c:a", "pcm_f32le", "-bitexact", "-fflags", "+bitexact", *(extra or []), str(dst)]
    subprocess.run(cmd, check=True)


def lufs(path: Path) -> float | None:
    """EBU R128 integrated loudness (None when the clip is too short to gate)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", r.stderr)
    if not m or m[-1] in ("-inf",) or float(m[-1]) <= -69.9:
        return None
    return float(m[-1])


def rms_db(x: np.ndarray) -> float:
    return 20 * math.log10(max(float(np.sqrt(np.mean(x.astype(np.float64) ** 2))), 1e-9))


def trim(x: np.ndarray, db: float) -> np.ndarray:
    thr = 10 ** (db / 20)
    idx = np.flatnonzero(np.abs(x) > thr)
    return x[idx[0]: idx[-1] + 1] if idx.size else x


def write_pcm16(path: Path, x: np.ndarray) -> None:
    pcm = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR_OUT)
        w.writeframes(pcm.tobytes())


def render(k, voice: str, cue: str, tmp: Path, out_dir: Path, speed: float | None = None) -> dict:
    text, say, base_speed, profile, cap = LINES[cue]
    speed = base_speed if speed is None else speed
    lang = "en-gb" if voice.startswith("b") else "en-us"   # bm_/bf_ voices are trained on British phonemes
    samples, sr = k.create(say, voice=voice, speed=speed, lang=lang)
    assert sr == SR_TTS, sr
    raw, s1, s2 = tmp / f"{cue}_raw.wav", tmp / f"{cue}_s1.wav", tmp / f"{cue}_s2.wav"
    sf.write(raw, samples.astype(np.float32), SR_TTS, subtype="FLOAT")
    ffmpeg(raw, s1, stage1_chain(profile))
    x1, _ = sf.read(s1, dtype="float32")
    x1 = trim(x1, TRIM_DB)
    sf.write(s1, x1, SR_OUT, subtype="FLOAT")
    loud = lufs(s1)
    gain = TARGET_LUFS - (loud if loud is not None else rms_db(x1) + 0.7)  # RMS fallback for very short clips
    pad = np.zeros(int(round(PAD_S * SR_OUT)))
    s3 = tmp / f"{cue}_s3.wav"
    for _ in range(6):  # gain -> limit -> exact peak normalise, re-aimed until the final file hits TARGET_LUFS
        ffmpeg(s1, s2, stage2_chain(gain))
        x, _ = sf.read(s2, dtype="float32")
        x = trim(x, TRIM_DB).astype(np.float64)
        x *= 10 ** (PEAK_DB / 20) / float(np.max(np.abs(x)))
        x[:FADE] *= np.linspace(0.0, 1.0, FADE)   # 3 ms edge fades: no click where the pad meets the cut
        x[-FADE:] *= np.linspace(1.0, 0.0, FADE)
        x = np.concatenate([pad, x, pad])
        sf.write(s3, x.astype(np.float32), SR_OUT, subtype="FLOAT")
        got = lufs(s3)
        if got is None or abs(got - TARGET_LUFS) <= 0.3:
            break
        gain += TARGET_LUFS - got
    pre_peak = 20 * math.log10(float(np.max(np.abs(x1)))) + gain   # what the limiter had to squash
    dst = out_dir / voice / f"{cue}.wav"
    write_pcm16(dst, x)
    pcm = np.frombuffer(dst.read_bytes()[44:], dtype="<i2")
    peak = 20 * math.log10(int(np.max(np.abs(pcm.astype(np.int32)))) / 32768.0)
    dur = len(pcm) / SR_OUT
    if dur > cap and speed < 1.3:  # a slow voice overran the cap: re-speak faster (deterministic, recorded below)
        return render(k, voice, cue, tmp, out_dir, round(min(1.3, speed * 1.05), 3))
    return {"text": text, "spoken": say, "lang": lang, "speed": speed, "tail": profile,
            "file": dst.relative_to(out_dir).as_posix(), "duration_s": round(dur, 3),
            "cap_s": cap, "peak_dbfs": round(peak, 2), "lufs": lufs(dst),
            "limiting_db": round(max(0.0, pre_peak - PEAK_DB), 1)}


RECOMMENDATION = """## Recommendation: am_michael

Argued from the numbers (nobody listened while building this; Aaron picks by ear):
- **Punch.** Shortest lines at the same authored speeds (median duration in the summary above): the streak calls land
  fastest, which is what an Unreal-style announcer needs between doors.
- **Fits as written.** Every line fits its cap at the authored speed. am_onyx overran the 2 s cap on `perfect` and was
  re-spoken faster automatically (see `speed` in manifest.json); bm_george runs longest throughout.
- **Even level.** michael (and onyx) hold every line within 0.3 LU of -13 LUFS. bm_george's lines have so little peak-to-loudness range
  that several stay louder than the target even with the peak held at -1 dBFS (spread up to ~1.1 LU). Within the 2 LU
  limit, but less even.
- **Accent.** am_ voices get en-us phonemes; bm_george is fed en-gb ("record" = ɹˈɛkɔːd, "Math" = mˈaθ), which suits a
  British arena announcer but sounds less like Fortnite.
- **Model card (not on disk, from memory, unverified):** Kokoro's VOICES.md grades am_michael C+, bm_george C,
  am_onyx D. On that list, michael is the strongest of the three.
- Pronunciation risk shared by all three: Kokoro phonemises "Yeeeet!" as jˈiːiːt (a doubled long vowel, so it is drawn
  out as asked) and "Perfect" as pˈɜːfɛkt (no r-colouring even in en-us), so `perfect` may sound slightly British.
"""


def qa_sheet(manifest: dict) -> str:
    out = ["# Announcer QA", "",
           "Generated by `tools/make_announcer.py` (do not hand-edit; rerun). Loudness = `ffmpeg -af ebur128` integrated",
           "LUFS of the final wav. Flags: **LEN** over the length cap, **LOUD** more than 2 LU from the voice's median.",
           "Limiter dB = how far the line's peak sat above -1 dBFS before the limiter (higher = more squashed).", ""]
    out.append("| voice | lines | median dur s | total s | LUFS spread | median limiter dB | flags |")
    out.append("|---|---|---|---|---|---|---|")
    for voice, cues in manifest["voices"].items():
        c = list(cues.values())
        lv = [x["lufs"] for x in c if x["lufs"] is not None]
        nflag = sum(1 for x in c if x["duration_s"] > x["cap_s"] or x["lufs"] is None
                    or abs(x["lufs"] - statistics.median(lv)) > 2.0)
        out.append(f"| {voice} | {len(c)} | {statistics.median(x['duration_s'] for x in c):.2f} "
                   f"| {sum(x['duration_s'] for x in c):.1f} | {min(lv):.1f} to {max(lv):.1f} "
                   f"| {statistics.median(x['limiting_db'] for x in c):.1f} | {nflag} |")
    out += ["", RECOMMENDATION]
    for voice, cues in manifest["voices"].items():
        vals = [c["lufs"] for c in cues.values() if c["lufs"] is not None]
        med = statistics.median(vals) if vals else float("nan")
        out += [f"## {voice}", "", f"Median {med:.1f} LUFS; spread {min(vals):.1f} to {max(vals):.1f}.", "",
                "| cue | text | dur s | cap | peak dBFS | LUFS | limiter dB | flag |", "|---|---|---|---|---|---|---|---|"]
        for cue, c in cues.items():
            flags = []
            if c["duration_s"] > c["cap_s"]:
                flags.append("LEN")
            if c["lufs"] is None:
                flags.append("UNGATED")
            elif abs(c["lufs"] - med) > 2.0:
                flags.append("LOUD")
            l = "n/a" if c["lufs"] is None else f"{c['lufs']:.1f}"
            out.append(f"| {cue} | {c['text']} | {c['duration_s']:.2f} | {c['cap_s']:.0f} | {c['peak_dbfs']:.2f} "
                       f"| {l} | {c['limiting_db']:.1f} | {' '.join(flags)} |")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", action="append", help="Kokoro voice id (repeatable)")
    ap.add_argument("--out", default=str(REPO / "tools" / "audio" / "announcer"))
    ap.add_argument("--cue", action="append", help="only these cue ids (default: all)")
    args = ap.parse_args()
    from kokoro_onnx import Kokoro

    voices = args.voice or DEFAULT_VOICES
    cues = args.cue or list(LINES)
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    k = Kokoro(str(MODEL), str(VOICES))
    mpath = out_dir / "manifest.json"
    manifest = json.loads(mpath.read_text("utf-8")) if mpath.exists() else {}
    manifest = {"format": "wav mono 48000 Hz pcm_s16le", "voices": manifest.get("voices", {})}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for voice in voices:
            (out_dir / voice).mkdir(parents=True, exist_ok=True)
            entry = manifest["voices"].setdefault(voice, {})
            for cue in cues:
                entry[cue] = render(k, voice, cue, tmp, out_dir)
                c = entry[cue]
                print(f"{voice:11s} {cue:17s} {c['duration_s']:5.2f}s peak {c['peak_dbfs']:6.2f} "
                      f"lufs {c['lufs']}", flush=True)
            manifest["voices"][voice] = {c: entry[c] for c in LINES if c in entry}
    out_dir.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out_dir / "QA.md").write_text(qa_sheet(manifest) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {mpath}")


if __name__ == "__main__":
    sys.exit(main())
