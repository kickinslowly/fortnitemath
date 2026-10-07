"""Poll the Fortnite client's Windows audio session (mute, volume, state, its own peak meter) every 0.5 s to a CSV,
optionally keeping it unmuted at a low volume, so a tools/hear.py recording can be judged: a session peak with a flat
loopback means the recorder listens on the wrong endpoint; a flat session peak means the game emitted nothing; a
`mute` flipping to 1 means Windows re-applied the saved per-app mute (seen 2026-10-07: the client session came back
MUTED on a session relaunch, which is why the first recorded run was silent while the Verse log showed every cue).

    python tools/audio_meter.py 230 %TEMP%/meter.csv unmute     # in the background, before playtest.py
    (restore afterwards: tools/audio_sessions.ps1 lists; the unmute is per app and persists in the mixer)

Needs `pycaw` + `comtypes` (pip, in .venv). Run it in its own process: importing `soundcard` first sets the COM
thread mode and pycaw then fails with "Cannot change thread mode after it is set".
"""
import csv
import sys
import time
from datetime import datetime, timezone

from pycaw.api.endpointvolume import IAudioMeterInformation
from pycaw.pycaw import AudioUtilities

PROCESS = "FortniteClient"
UNMUTED_VOLUME = 0.25   # loud enough for the loopback onsets, quiet in the room


def client_sessions():
    return [s for s in AudioUtilities.GetAllSessions() if s.Process and s.Process.name().startswith(PROCESS)]


def main():
    seconds = float(sys.argv[1])
    out = sys.argv[2]
    unmute = len(sys.argv) > 3 and sys.argv[3] == "unmute"
    rows = []
    t0 = time.time()
    pids = set()
    while time.time() - t0 < seconds:
        for s in client_sessions():
            v = s.SimpleAudioVolume
            if unmute and (v.GetMute() or v.GetMasterVolume() < UNMUTED_VOLUME - 0.05):
                v.SetMute(0, None)
                v.SetMasterVolume(UNMUTED_VOLUME, None)
            try:
                peak = s._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue()
            except Exception:  # noqa: BLE001 - a session that just closed
                peak = -1.0
            rows.append((round(time.time() - t0, 2), datetime.now(timezone.utc).strftime("%H.%M.%S.%f")[:-3],
                         s.Process.pid, s.State, int(v.GetMute()), round(v.GetMasterVolume(), 2), round(peak, 4)))
            pids.add(s.Process.pid)
        time.sleep(0.5)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "utc", "pid", "state", "mute", "vol", "peak"])
        w.writerows(rows)
    loud = [r for r in rows if r[6] > 0.002]
    muted = [r for r in rows if r[4] == 1]
    print(f"{len(rows)} samples, pids {sorted(pids)}, {len(loud)} with session peak > 0.002, {len(muted)} muted samples")
    if loud:
        print("first loud:", loud[0], "max peak:", max(r[6] for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
