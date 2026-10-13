"""Wait for a fresh director log line, then PrintWindow-burst the Fortnite client: COUNT frames, INTERVAL s apart.

    python tools/burst.py "picked " 90 1.0 %TEMP%\\fnm_burst wrong     # wrong_00.png .. wrong_89.png

Why: the editor log can reach us ~10 s after the event, so `playtest.py --frames` fires late. A wall-clock burst started on
an early line (e.g. "picked ") and matched afterwards by file time against the log's UTC timestamps catches the moment
(2026-10-13: all six penalties). Run it in the background next to `playtest.py --until ...`. Never takes the foreground.
"""
import datetime
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import playtest as pt  # noqa: E402

if __name__ == "__main__":
    text, count, interval, outdir, prefix = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
    outdir.mkdir(parents=True, exist_ok=True)
    start = datetime.datetime.utcnow()
    deadline = datetime.datetime.utcnow() + datetime.timedelta(seconds=400)
    while datetime.datetime.utcnow() < deadline:
        hits = [line for line in pt.fnm_lines(text) if (pt.log_time(line) or start) > start]
        if hits:
            print("trigger:", hits[0][:120], flush=True)
            break
        time.sleep(1)
    else:
        sys.exit("no trigger line")
    r = subprocess.run(["powershell", "-NoProfile", "-File", str(Path(__file__).parent / "wincap.ps1"),
                        "-out", str(outdir / f"{prefix}.png"), "-count", str(count), "-interval", str(interval)],
                       capture_output=True, text=True)
    print(r.stdout[-400:], r.stderr[-400:])
