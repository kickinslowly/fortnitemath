"""Relaunch the UEFN play session, screenshot the game, and print the director's FNM log lines.

    python tools/playtest.py                 # relaunch, wait for the match, one screenshot, FNM lines
    python tools/playtest.py --no-relaunch   # just screenshot + FNM lines from the running session
    python tools/playtest.py --watch 3       # also catch N "FNM: debug auto-wrong" events, 4 frames each

Pair --watch with the director's DebugAutoWrongAnswers @editable (set it in the Verse default, sync,
BuildAll) to see every penalty fire without walking. Screenshots land in %TEMP% as pt_*.png. Look at them.
Verse Print output is server-side, so it is read from the EDITOR log, not the client log.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

SESSION = "ValkyrieToolset.SessionToolset"
GUI = Path.home() / ".claude/skills/uefn-mcp/scripts/gui_act.ps1"
# Physical-pixel position of the Fortnite taskbar icon; clicking it brings the game window forward.
FOCUS_CLICK = "c:1677,1416"


def shot(name, steps="w:0.05"):
    subprocess.run(["powershell", "-NoProfile", "-File", str(GUI), "-steps", steps, "-name", name],
                   capture_output=True)
    return Path(os.environ["TEMP"]) / f"{name}.png"


def fnm_lines(pattern="FNM:"):
    log = u.call("EditorToolset.LogsToolset", "GetLogEntries", {"category": "", "pattern": pattern})
    return log.get("returnValue", []) if isinstance(log, dict) else []


def relaunch():
    try:
        u.call(SESSION, "StopSession", {})
        time.sleep(8)
    except RuntimeError as e:  # "No session is active."
        print("StopSession:", e)
    print("StartSession:", u.call(SESSION, "StartSession", {"location": {"x": 0, "y": -300, "z": 100}}))
    for _ in range(60):
        if "Running" in str(u.call(SESSION, "GetGameState", {})):
            print("match running")
            return
        time.sleep(5)
    sys.exit("match never reached Running")


def watch(count, timeout=150):
    """Screenshot each new 'debug auto-wrong N' event at +0.3 / 1 / 2.5 / 4.5 s."""
    baseline = {line for line in fnm_lines("FNM: debug auto-wrong")}
    seen, start = 0, time.time()
    while seen < count and time.time() - start < timeout:
        new = [line for line in fnm_lines("FNM: debug auto-wrong") if line not in baseline]
        for line in new:
            baseline.add(line)
            seen += 1
            last = 0.0
            for k, at in enumerate((0.3, 1.0, 2.5, 4.5)):
                time.sleep(at - last)
                last = at
                print("  frame", shot(f"pt_wrong{seen}_{k}"))
        time.sleep(0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-relaunch", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    args = ap.parse_args()
    started = time.time()
    if not args.no_relaunch:
        relaunch()
        time.sleep(6)
    print("screenshot", shot("pt_now", FOCUS_CLICK + ";w:0.3"))
    if args.watch:
        watch(args.watch)
    since = time.strftime("%Y.%m.%d-%H.%M.%S", time.gmtime(started - 5))
    for line in fnm_lines():
        if line[1:20] >= since[:19]:
            print(line[1:24], line.split("FNM:", 1)[1][:160])


if __name__ == "__main__":
    main()
