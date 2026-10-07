"""Ear-proxy: record what the PC's speakers play (WASAPI loopback of the default speaker) and list where sounds start,
so a play session's `FNM: cue ...` log lines can be matched to real audio.

    python tools/hear.py --seconds 150                      # record to %TEMP%/hear.wav, print the onset table
    python tools/hear.py --seconds 150 --log run.txt        # ... then match every "FNM: cue <id>" line in run.txt
    python tools/hear.py --analyze --log run.txt            # re-analyse the last recording (no new recording)
    python tools/hear.py --analyze --marks "12.5,14.0"      # marks: seconds from the recording start, or UTC
                                                            #   2026.10.07-18.04.11:250 (editor-log stamps)

Run it in the background while a playtest runs in the foreground; it needs no focus. Onsets: times where the
RMS over 50 ms rises more than --threshold dB (default 12) above the mean RMS of the 500 ms before it (and clears an
absolute floor of -60 dBFS), with 250 ms of dead time after each. A log file is any text holding editor-log
timestamps ([YYYY.MM.DD-HH.MM.SS:mmm], UTC) on its "FNM: cue <id>" lines, e.g. tools/playtest.py's output; "cue stop"
and "(not wired)" lines are skipped. The recording's UTC start is saved beside the WAV (hear.wav.json).
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import wave
from pathlib import Path

import subprocess

import numpy as np

RATE = 48000
CHUNK = 4800                    # 0.1 s per read
WIN = 0.05                      # RMS window
LOOKBACK = 0.5                  # baseline window before an onset
FLOOR_DB = -60.0
DEAD = 0.25
STAMP = re.compile(r"(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d:\d{3})")
DEFAULT_OUT = Path(os.environ.get("TEMP", ".")) / "hear.wav"


def record(seconds, out):
    import soundcard as sc  # imported here so --analyze runs without an audio stack
    mic = sc.get_microphone(sc.default_speaker().id, include_loopback=True)
    chunks = []
    with mic.recorder(samplerate=RATE, channels=2, blocksize=CHUNK) as rec:
        first = rec.record(numframes=CHUNK)
        # The first block ends now: the recording started one block earlier.
        start = time.time() - CHUNK / RATE
        chunks.append(first)
        need = int(seconds * RATE) - CHUNK
        while need > 0:
            block = rec.record(numframes=min(CHUNK, need))
            chunks.append(block)
            need -= len(block)
    data = np.concatenate(chunks)
    pcm = (np.clip(data, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    meta = {"start_utc": datetime.datetime.fromtimestamp(start, datetime.timezone.utc).strftime("%Y.%m.%d-%H.%M.%S.%f"),
            "start_epoch": start, "seconds": len(data) / RATE, "peak": float(np.abs(data).max())}
    Path(str(out) + ".json").write_text(json.dumps(meta, indent=1))
    print(f"recorded {meta['seconds']:.1f} s to {out}, peak {meta['peak']:.3f}, start {meta['start_utc']} UTC")
    return meta


def load(path):
    with wave.open(str(path), "rb") as w:
        raw = w.readframes(w.getnframes())
        rate, ch = w.getframerate(), w.getnchannels()
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return data.reshape(-1, ch).mean(axis=1), rate


def onsets(mono, rate, threshold):
    hop = int(WIN * rate)
    n = len(mono) // hop
    frames = mono[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    back = int(LOOKBACK / WIN)
    found, last = [], -1e9
    for i in range(back, n):
        base = 20 * np.log10(np.sqrt((rms[i - back:i] ** 2).mean()) + 1e-9)
        t = i * WIN
        if db[i] > FLOOR_DB and db[i] - base >= threshold and t - last >= DEAD:
            found.append((t, float(db[i]), float(db[i] - base)))
            last = t
    return found, db


def utc(text):
    return datetime.datetime.strptime(text, "%Y.%m.%d-%H.%M.%S:%f").replace(tzinfo=datetime.timezone.utc).timestamp()


def marks_from_log(path, start_epoch):
    out = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = STAMP.search(line)
        cue = re.search(r"cue (?!stop)([a-z0-9_]+)(?! \(not wired\))", line)
        if m and cue and "(not wired)" not in line:
            out.append((utc(m.group(1)) - start_epoch, cue.group(1)))
    return out


def parse_marks(text, start_epoch):
    out = []
    for item in [s.strip() for s in text.split(",") if s.strip()]:
        out.append(((utc(item) - start_epoch) if STAMP.fullmatch(item) else float(item), item))
    return out


def match(marks, found, tolerance):
    times = np.array([t for t, _, _ in found]) if found else np.array([])
    hits = 0
    print(f"\n{'mark s':>8}  {'what':24} {'onset s':>8} {'delta':>7}")
    for t, what in marks:
        if len(times):
            k = int(np.abs(times - t).argmin())
            near, delta = times[k], times[k] - t
            ok = abs(delta) <= tolerance
            hits += ok
            print(f"{t:8.2f}  {what:24} {near:8.2f} {delta:+7.2f} {'HIT' if ok else ''}")
        else:
            print(f"{t:8.2f}  {what:24} {'-':>8}")
    print(f"\n{hits} of {len(marks)} marks have an onset within {tolerance} s")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--threshold", type=float, default=12.0, help="dB rise over the previous 500 ms")
    ap.add_argument("--analyze", action="store_true", help="analyse the existing --out recording, do not record")
    ap.add_argument("--log", help="text file with editor-log stamped 'FNM: cue <id>' lines")
    ap.add_argument("--marks", help="comma-separated seconds from start, or UTC editor-log stamps")
    ap.add_argument("--tolerance", type=float, default=0.5)
    a = ap.parse_args()
    out = Path(a.out)
    if a.analyze:
        meta = json.loads(Path(str(out) + ".json").read_text())
    else:
        meta = record(a.seconds, out)
    mono, rate = load(out)
    found, db = onsets(mono, rate, a.threshold)
    if db.max() < FLOOR_DB:
        # Flat: first suspect a muted app in the Windows volume mixer (2026-10-07: the Fortnite client was).
        print("recording is silent; Windows audio sessions on the default speaker:")
        ps = Path(__file__).parent / "audio_sessions.ps1"
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps)],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[:300])
    start = meta["start_epoch"]
    print(f"\n{len(found)} onsets (threshold {a.threshold} dB), loudest 50 ms {db.max():.1f} dBFS")
    print(f"{'t s':>8}  {'UTC':23} {'dBFS':>6} {'rise':>6}")
    for t, level, rise in found:
        stamp = datetime.datetime.fromtimestamp(start + t, datetime.timezone.utc).strftime("%H.%M.%S.%f")[:12]
        print(f"{t:8.2f}  {stamp:23} {level:6.1f} {rise:+6.1f}")
    marks = []
    if a.log:
        marks += marks_from_log(a.log, start)
    if a.marks:
        marks += parse_marks(a.marks, start)
    if marks:
        inside = [(t, w) for t, w in marks if 0 <= t <= meta["seconds"]]
        if len(inside) < len(marks):
            print(f"({len(marks) - len(inside)} marks fall outside the recording and are skipped)")
        match(inside, found, a.tolerance)


if __name__ == "__main__":
    sys.exit(main())
