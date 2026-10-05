"""Click the director's HUD buttons (skill menu, CHANGE SKILL) in a play session: launch, screenshot, click.

    python tools/click_hud.py launch            # relaunch, wait for 'FNM: picker shown', restore a minimized client,
                                                # screenshot %TEMP%\\pick0.png (read it to find the buttons)
    python tools/click_hud.py shot <name>       # wincap screenshot now (focus-free)
    python tools/click_hud.py click <x> <y> <name> [wait_pattern]
                                                # focus the client, click at CLIENT-AREA pixels (as read off the
                                                # PNG), wait for a new director log line, screenshot
    python tools/click_hud.py log <pattern>     # new FNM lines since the last call with that pattern
    python tools/click_hud.py origin            # the client area's screen origin (physical px) and minimized flag

Clicks take the foreground (gui_act.ps1 taskbar click + mouse click): ask first if Aaron may be in another app.
Screen position = client origin (ClientToScreen, DPI-aware) + pixel in the PNG; a left monitor gives negative x.
Verified 2026-10-04: grade -> skill -> CHANGE SKILL all reached the buttons' OnClick.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import playtest as pt  # noqa: E402

GUI = Path.home() / ".claude/skills/uefn-mcp/scripts/gui_act.ps1"
TEMP = Path(os.environ["TEMP"])
STATE = TEMP / "click_hud_state.json"

PS_ORIGIN = r'''
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WO {
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  public struct POINT { public int X, Y; }
}
"@
[WO]::SetProcessDPIAware() | Out-Null
$p = Get-Process -Name FortniteClient-Win64-Shipping -ErrorAction Stop | ? { $_.MainWindowHandle -ne 0 } | select -First 1
$pt = New-Object WO+POINT
[WO]::ClientToScreen($p.MainWindowHandle, [ref]$pt) | Out-Null
"$($pt.X),$($pt.Y),$([WO]::IsIconic($p.MainWindowHandle))"
'''

# A relaunched session reuses a minimized client window; PrintWindow cannot capture one. SW_RESTORE = 9.
PS_RESTORE = r'''
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WR { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n); }
"@
$p = Get-Process -Name FortniteClient-Win64-Shipping | ? { $_.MainWindowHandle -ne 0 } | select -First 1
[WR]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
'''


def origin():
    """(client x, client y, minimized) of the Fortnite client's main window, physical pixels."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", PS_ORIGIN], capture_output=True, text=True)
    x, y, iconic = r.stdout.strip().split(",")
    return int(x), int(y), iconic.strip().lower() == "true"


def restore():
    subprocess.run(["powershell", "-NoProfile", "-Command", PS_RESTORE], capture_output=True)


def shot(name):
    out = TEMP / f"{name}.png"
    r = subprocess.run(["powershell", "-NoProfile", "-File", str(pt.WINCAP), "-out", str(out)],
                       capture_output=True, text=True)
    print("shot:", (r.stdout or r.stderr).strip()[:100])
    return out


def new_lines(pattern):
    """Director log lines matching pattern that were not there at the previous call with that pattern."""
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    seen = set(st.get(pattern, []))
    lines = list(pt.fnm_lines(pattern))
    new = [line for line in lines if line not in seen]
    st[pattern] = lines[-400:]
    STATE.write_text(json.dumps(st))
    return new


def tail(line):
    return line.split("FNM:", 1)[-1].strip()[:150]


def wait_for(pattern, limit):
    start = time.time()
    while time.time() - start < limit:
        got = new_lines(pattern)
        if got:
            print(f"[{time.time() - start:5.1f}s] {tail(got[-1])}")
            return got[-1]
        time.sleep(1)
    print("TIMEOUT waiting for", pattern)
    return None


def cmd_launch():
    new_lines("FNM: picker shown")  # baseline before the relaunch: the director logs within seconds
    pt.relaunch()
    wait_for("FNM: picker shown", 120)
    time.sleep(4)
    if origin()[2]:
        restore()
        time.sleep(3)
    print("origin:", origin())
    print(shot("pick0"))


def cmd_click(x, y, name, wait_pattern=None):
    ox, oy, iconic = origin()
    if iconic:
        sys.exit("client is minimized; not clicking (run `launch`, or restore it)")
    sx, sy = ox + int(x), oy + int(y)
    if wait_pattern:
        new_lines(wait_pattern)  # baseline
    steps = f"{pt.FOCUS_CLICK};w:1;c:{sx},{sy};w:1"
    print("click at screen", sx, sy)
    subprocess.run(["powershell", "-NoProfile", "-File", str(GUI), "-steps", steps, "-name", "click_hud"],
                   capture_output=True)
    time.sleep(1.5)
    if wait_pattern:
        wait_for(wait_pattern, 10)
    print(shot(name))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "origin"
    if cmd == "launch":
        cmd_launch()
    elif cmd == "shot":
        print(shot(sys.argv[2]))
    elif cmd == "click":
        cmd_click(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None)
    elif cmd == "log":
        for line in new_lines(sys.argv[2]):
            print(tail(line))
    elif cmd == "origin":
        print(origin())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
