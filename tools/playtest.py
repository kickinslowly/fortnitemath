"""Relaunch the UEFN play session, screenshot the game, and print the director's FNM log lines.

    python tools/playtest.py                 # relaunch, wait for the match, one screenshot, FNM lines
    python tools/playtest.py --no-relaunch   # just screenshot + FNM lines from the running session
    python tools/playtest.py --until "finished run 1,stuck at stage"
                                             # relaunch, wait (--timeout s) for a director line holding any of
                                             # the comma-separated texts, no keys; then the FNM lines
    python tools/playtest.py --watch 3       # also catch N "FNM: debug auto-wrong" events, 4 frames each
    python tools/playtest.py --after "FNM: debug door" --keys W:0.8,E:0.3,W:2.5
                                             # wait for a director log line, then hold keys in turn
                                             # (W walk, E interact, ...), one screenshot after each;
                                             # W+SPACE:4 holds W and taps jump (run and jump hurdles)

Pair --watch with the director's DebugAutoWrongAnswers @editable (set it in the Verse default, sync,
BuildAll) to see every penalty fire without walking. Screenshots land in %TEMP% as pt_*.png. Look at them.
Verse Print output is server-side, so it is read from the EDITOR log, not the client log.
Screenshots come from PrintWindow on the Fortnite client (tools/wincap.ps1), so they never touch the foreground:
Aaron may be in another game on this PC. Only --keys brings the client forward (simulated keys need it) — say so
before using it while he is at the keyboard. A background client renders at ~10 fps.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

# The editor log carries real minus signs (pace deltas) and the cartridges' × ÷; a cp1252 console would crash on them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SESSION = "ValkyrieToolset.SessionToolset"
GUI = Path.home() / ".claude/skills/uefn-mcp/scripts/gui_act.ps1"
# Brings the game client forward without the taskbar: clicking its taskbar icon while it is ALREADY in front
# minimizes it (2026-10-05). Restores a minimized client; if it is not the foreground window, minimizes and restores
# it (a click inside the game would fire the weapon). Prints the client's state.
PS_FOCUS = r'''
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WF {
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Ri, B; }
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
}
"@
[WF]::SetProcessDPIAware() | Out-Null
$p = Get-Process FortniteClient-Win64-Shipping -ErrorAction SilentlyContinue | ?{ $_.MainWindowHandle -ne 0 } | select -first 1
if (-not $p) { "no-client"; exit }
$h = $p.MainWindowHandle
if ([WF]::IsIconic($h)) { [WF]::ShowWindow($h, 9) | Out-Null; Start-Sleep -Milliseconds 800 }
if ([WF]::GetForegroundWindow() -eq $h) { "already-front"; exit }
# Minimize then restore: a restored window comes to the front (a click on its title bar hit whatever covered it).
[WF]::ShowWindow($h, 6) | Out-Null; Start-Sleep -Milliseconds 300
[WF]::ShowWindow($h, 9) | Out-Null; Start-Sleep -Milliseconds 800
if ([WF]::GetForegroundWindow() -eq $h) { "focused" } else { "not-focused" }
'''
HOLDKEY = Path(__file__).parent / "holdkey.ps1"
WINCAP = Path(__file__).parent / "wincap.ps1"
# Keyboard scan codes for --keys.
SCANCODES = {"W": 0x11, "A": 0x1E, "S": 0x1F, "D": 0x20, "E": 0x12, "SPACE": 0x39}


def shot(name, steps=None):
    """PNG of the Fortnite client window without focusing it. steps (gui_act.ps1 syntax) forces the old
    full-screen capture after clicks/keys; the full-screen path is also the fallback when the client has no
    window yet. A MINIMIZED client gets no screenshot (returns None): a full-screen capture then shows the
    desktop, not the game (2026-10-06: it caught Aaron's Zoom meeting)."""
    out = Path(os.environ["TEMP"]) / f"{name}.png"
    if steps is None:
        r = subprocess.run(["powershell", "-NoProfile", "-File", str(WINCAP), "-out", str(out)],
                           capture_output=True, text=True)
        if r.returncode == 0 and "ok=True" in r.stdout:
            return out
        state = (r.stdout or r.stderr).strip()[:80]
        if "MINIMIZED" in state:
            print("  wincap:", state, "- no screenshot")
            return None
        print("  wincap:", state, "- full-screen fallback")
        steps = "w:0.05"
    subprocess.run(["powershell", "-NoProfile", "-File", str(GUI), "-steps", steps, "-name", name],
                   capture_output=True)
    return out


def focus_client():
    """Bring the game forward (restore if minimized, else minimize + restore): needed for simulated keys and HUD
    clicks only. Steals the foreground. Returns the state PS_FOCUS printed."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", PS_FOCUS], capture_output=True, text=True)
    state = r.stdout.strip()
    print("  focus:", state)
    return state


def log_time(line):
    """UTC timestamp of an editor log line ("[2026.10.06-03.40.11:776]..."), or None."""
    try:
        return datetime.datetime.strptime(line[1:20], "%Y.%m.%d-%H.%M.%S")
    except ValueError:
        return None


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
    # Also newer than this call: after a relaunch the log listing can return older lines that were missing from the
    # baseline, and a "new" line from a previous session once ended a wait at once (2026-10-05).
    since = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    start = time.time()
    while time.time() - start < timeout:
        new = [line for line in fnm_lines(pattern) if line not in baseline and (log_time(line) or since) >= since]
        if new:
            return new[-1]
        time.sleep(0.25)
    return None


def play_keys(spec):
    """spec like "W:0.8,E:0.3,W:2.5": hold each key that many seconds in turn, screenshot after each."""
    for k, step in enumerate(spec.split(",")):
        key, secs = step.split(":")
        hold, _, tap = key.upper().partition("+")   # "W+SPACE": hold W, tap SPACE (run and jump)
        extra = ["-tap", str(SCANCODES[tap])] if tap else []
        subprocess.run(["powershell", "-NoProfile", "-File", str(HOLDKEY), "-scan", str(SCANCODES[hold]),
                        "-secs", secs, *extra], capture_output=True)
        time.sleep(0.3)
        print(f"  {step} ->", shot(f"pt_keys{k}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-relaunch", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--after", help="director log pattern to wait for before --keys")
    ap.add_argument("--keys", help='key holds after --after, e.g. "W:0.8,E:0.3,W:2.5"')
    ap.add_argument("--until", help='comma-separated texts; wait for a director line holding any of them (no keys)')
    ap.add_argument("--timeout", type=float, default=200, help="seconds to wait for --until")
    ap.add_argument("--frames", help='with --until: "text:delay,text:delay"; on the first director line holding each text, wait '
                    'delay s and screenshot pt_frame<k> (mid-run HUD checks)')
    args = ap.parse_args()
    started = time.time()
    until_baseline = set(fnm_lines()) if args.until else set()
    since_dt = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    after_baseline = set(fnm_lines(args.after)) if args.after else set()
    if not args.no_relaunch:
        relaunch()
        time.sleep(6)
    print("screenshot", shot("pt_now"))
    if args.watch:
        watch(args.watch)
    if args.keys:
        if args.after:
            line = wait_for(args.after, after_baseline)
            print("after:", line.split("FNM:", 1)[1][:120] if line else "TIMED OUT")
            time.sleep(0.5)
        focus_client()
        play_keys(args.keys)
        time.sleep(6)
    if args.until:
        texts = args.until.split(",")
        frames = [[p.rpartition(":")[0], float(p.rpartition(":")[2]), False] for p in args.frames.split(",")] if args.frames else []
        seen = set()
        hit = None
        while hit is None and time.time() - started < args.timeout:
            new = [l for l in fnm_lines() if l not in until_baseline and (log_time(l) or since_dt) >= since_dt]
            for l in new:
                if l in seen:
                    continue
                seen.add(l)
                for k, frame in enumerate(frames):
                    if not frame[2] and frame[0] in l:
                        frame[2] = True
                        time.sleep(frame[1])
                        print(f"  frame {k} after '{frame[0]}' +{frame[1]}s ->", shot(f"pt_frame{k}"), flush=True)
            hit = next((l for l in new if any(t in l for t in texts)), None)
            if hit is None:
                time.sleep(0.5 if frames else 2)
        print("until:", hit.split("FNM:", 1)[1][:120] if hit else "TIMED OUT")
    since = time.strftime("%Y.%m.%d-%H.%M.%S", time.gmtime(started - 5))
    for line in fnm_lines():
        if line[1:20] >= since[:19]:
            print(line[1:24], line.split("FNM:", 1)[1][:160])


if __name__ == "__main__":
    main()
