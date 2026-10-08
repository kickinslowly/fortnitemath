"""Did a voice line actually play? Matched filter: each announcer line (tools/audio/announcer/<voice>/<cue>.wav) against a
tools/hear.py speaker recording at its cue time (editor-log 'cue <id>' lines, stamps + text, as playtest.py prints them)
and at a control window 8 s earlier. A line in the clear scores ~0.9 (GO 0.96), a line buried under a same-instant stock
sound 0.2-0.3, the noise floor ~0.1 (2026-10-07). Fortnite is SILENT when its window is not in the foreground: record
with the client focused (playtest.py --keys brings it forward).

    python tools/hear_voice.py %TEMP%/hear.wav cues.txt [voice]
    (cues.txt: grep "FNM: " the editor log | sed -E 's/^\[([^]]+)\]\[ *[0-9]+\]LogVerse: : FNM: /  /')
"""

import json
import re
import sys
import wave

import numpy as np

D = 6  # 48 kHz -> 8 kHz
wav_path, cues_path = sys.argv[1:3]
voice = sys.argv[3] if len(sys.argv) > 3 else "am_michael"


def load(path):
    w = wave.open(path); sr = w.getframerate(); ch = w.getnchannels(); n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x[:len(x) // D * D].reshape(-1, D).mean(axis=1), sr // D


def parse(s):
    h, mi, se, ms = re.search(r"(\d\d)\.(\d\d)\.(\d\d)[.:](\d+)", s).groups()
    return int(h) * 3600 + int(mi) * 60 + int(se) + int(ms[:3].ljust(3, "0")) / 1000


def ncc(t, seg):
    t = t - t.mean(); t /= (np.linalg.norm(t) + 1e-9); n = len(seg) + len(t)
    corr = np.fft.irfft(np.fft.rfft(seg, n) * np.fft.rfft(t[::-1], n), n)[len(t) - 1:len(seg)]
    cs = np.concatenate([[0], np.cumsum(seg ** 2)]); e = np.sqrt(cs[len(t):] - cs[:len(seg) - len(t) + 1]) + 1e-9
    c = corr[:len(e)] / e; k = int(np.argmax(c)); return float(c[k]), k / sr


rec, sr = load(wav_path)
t0 = parse(json.load(open(wav_path + ".json"))["start_utc"].split("-")[1])
events = [(parse(m.group(1).split("-")[1]) - t0, m.group(2)) for line in open(cues_path, encoding="utf-8", errors="replace")
          for m in [re.match(r"(\S+)\s+cue (\S+)$", line.strip())] if m]
print(f"{'cue':<18} {'t':>6} {'ncc@cue':>8} {'lag':>5} {'control':>8}")
for t, cue in events:
    if 0 < t < len(rec) / sr and (cue.startswith("penalty_") or cue in ("go", "welcome", "guards_up", "streak2", "streak3")):
        try:
            tpl, _ = load(f"tools/audio/announcer/{voice}/{cue}.wav")
        except FileNotFoundError:
            continue
        a, b = int((t - 0.3) * sr), int((t + 2.5) * sr); c1, lag = ncc(tpl, rec[a:b])
        a2, b2 = int((t - 8.3) * sr), int((t - 5.5) * sr); c0 = ncc(tpl, rec[a2:b2])[0] if a2 > 0 else float("nan")
        print(f"{cue:<18} {t:6.1f} {c1:8.2f} {lag - 0.3:5.2f} {c0:8.2f}")
