# Hold a key in the focused game window (scan code; W = 0x11), e.g. to walk a player in a test:
#   powershell -File tools/holdkey.ps1 -scan 0x11 -secs 3
# Optionally tap a second key while holding (e.g. jump while running): -tap 0x39 -tapEvery 0.6
param([int]$scan = 0x11, [double]$secs = 3.0, [int]$tap = 0, [double]$tapEvery = 0.6)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class K { [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra); }
"@
[K]::keybd_event(0, [byte]$scan, 0x8, [UIntPtr]::Zero)
if ($tap -eq 0) {
    Start-Sleep -Milliseconds ([int]($secs * 1000))
} else {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $secs) {
        [K]::keybd_event(0, [byte]$tap, 0x8, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 80
        [K]::keybd_event(0, [byte]$tap, 0xA, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds ([int]($tapEvery * 1000))
    }
}
[K]::keybd_event(0, [byte]$scan, 0xA, [UIntPtr]::Zero)
"held"
