# Hold a key in the focused game window (scan code; W = 0x11), e.g. to walk a player in a test:
#   powershell -File tools/holdkey.ps1 -scan 0x11 -secs 3
param([int]$scan = 0x11, [double]$secs = 3.0)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class K { [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra); }
"@
[K]::keybd_event(0, [byte]$scan, 0x8, [UIntPtr]::Zero)
Start-Sleep -Milliseconds ([int]($secs * 1000))
[K]::keybd_event(0, [byte]$scan, 0xA, [UIntPtr]::Zero)
"held"
