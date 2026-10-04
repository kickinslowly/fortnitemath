"""Relaunch the UEFN play session, screenshot the game, and print the director's FNM log lines.

    python tools/playtest.py                 # relaunch, wait for the match, one screenshot, FNM lines
    python tools/playtest.py --no-relaunch   # just screenshot + FNM lines from the running session
    python tools/playtest.py --watch 3       # also catch N "FNM: debug auto-wrong" events, 4 frames each
    python tools/playtest.py --after "FNM: debug door" --keys W:0.8,E:0.3,W:2.5
                                             # wait for a director log line, then hold keys in turn
                                             # (W walk, E interact, ...), one screenshot after each

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
HOLDKEY = Path(__file__).parent / "holdkey.ps1"
# Keyboard scan codes for --keys.
SCANCODES = {"W": 0x11, "A": 0x1E, "S": 0x1F, "D": 0x20, "E": 0x12, "SPACE": 0x39}


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
        state = str(u.call(SESSION, "GetGameState", {}))
        if "Running" in state:
            print("match running")
            return
        if "CanStart" in state:  # sometimes the session sits in Edit Mode until the game is started
            try:
                print("StartGame:", u.call(SESSION, "StartGame", {}))
            except RuntimeError as e:  # "not currently available" while the client is still loading
                print("StartGame:", e)
        time.sleep(5)
    sys.exit("match never reached Running")


def watch(count, timeout=150):
    """Screenshot each new 'debug auto-wrong N' event at +0.5 .. 5 s (its penalty fires at +1 s)."""
    baseline = {line for line in fnm_lines("FNM: debug auto-wrong")}
    seen, start = 0, time.time()
    while seen < count and time.time() - start < timeout:
        new = [line for line in fnm_lines("FNM: debug auto-wrong") if line not in baseline]
        for line in new:
            baseline.add(line)
            seen += 1
            last = 0.0
            for k, at in enumerate((0.5, 1.4, 1.9, 2.4, 3.5, 5.0)):
                time.sleep(at - last)
                last = at
                print("  frame", shot(f"pt_wrong{seen}_{k}"))
        time.sleep(0.3)


def wait_for(pattern, baseline, timeout=120):
    """Block until an editor log line matching pattern that is not in baseline appears; return it (or
    None on timeout). Take the baseline BEFORE relaunching: a director hook can log within seconds."""
    start = time.time()
    while time.time() - start < timeout:
        new = [line for line in fnm_lines(pattern) if line not in baseline]
        if new:
            return new[-1]
        time.sleep(0.25)
    return None


def play_keys(spec):
    """spec like "W:0.8,E:0.3,W:2.5": hold each key that many seconds in turn, screenshot after each."""
    for k, step in enumerate(spec.split(",")):
        key, secs = step.split(":")
        subprocess.run(["powershell", "-NoProfile", "-File", str(HOLDKEY), "-scan", str(SCANCODES[key.upper()]),
                        "-secs", secs], capture_output=True)
        time.sleep(0.3)
        print(f"  {step} ->", shot(f"pt_keys{k}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-relaunch", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--after", help="director log pattern to wait for before --keys")
    ap.add_argument("--keys", help='key holds after --after, e.g. "W:0.8,E:0.3,W:2.5"')
    args = ap.parse_args()
    started = time.time()
    after_baseline = set(fnm_lines(args.after)) if args.after else set()
    if not args.no_relaunch:
        relaunch()
        time.sleep(6)
    print("screenshot", shot("pt_now", FOCUS_CLICK + ";w:0.3"))
    if args.watch:
        watch(args.watch)
    if args.keys:
        if args.after:
            line = wait_for(args.after, after_baseline)
            print("after:", line.split("FNM:", 1)[1][:120] if line else "TIMED OUT")
            time.sleep(0.5)
        play_keys(args.keys)
        time.sleep(6)
    since = time.strftime("%Y.%m.%d-%H.%M.%S", time.gmtime(started - 5))
    for line in fnm_lines():
        if line[1:20] >= since[:19]:
            print(line[1:24], line.split("FNM:", 1)[1][:160])


if __name__ == "__main__":
    main()
