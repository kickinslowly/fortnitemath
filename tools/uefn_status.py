"""Report whether Unreal Editor for Fortnite is installed, downloading, or queued.

Reads the Epic Games Launcher manifests. Exit code: 0 installed, 1 downloading, 2 not started.
"""
import glob
import json
import os
import sys

MANIFESTS = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
EDITOR_EXE = "UnrealEditorFortnite"


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _is_uefn(d):
    text = f"{d.get('DisplayName', '')} {d.get('LaunchExecutable', '')}".lower()
    return "editor for fortnite" in text or EDITOR_EXE.lower() in text


def main():
    found = []
    for path in glob.glob(os.path.join(MANIFESTS, "*.item")) + glob.glob(os.path.join(MANIFESTS, "Pending", "*.item")):
        d = _load(path)
        if d and _is_uefn(d):
            found.append((path, d))
    installed = [d for p, d in found if "Pending" not in p and not d.get("bIsIncompleteInstall")]
    if installed:
        d = installed[0]
        exe = os.path.join(d.get("InstallLocation", ""), d.get("LaunchExecutable", ""))
        print(f"INSTALLED {d.get('AppVersionString')} at {d.get('InstallLocation')} exe_exists={os.path.exists(exe)} exe={exe}")
        return 0
    if found:
        d = found[0][1]
        print(f"DOWNLOADING {d.get('DisplayName')} -> {d.get('InstallLocation')}")
        return 1
    print("NOT STARTED (queued, no manifest yet)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
