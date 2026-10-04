param([string]$proc = "FortniteClient-Win64-Shipping", [string]$out = "$env:TEMP\wincap.png", [int]$count = 1, [double]$interval = 0.3)
# Captures one process's main window via PrintWindow(PW_RENDERFULLCONTENT) without focusing it or sending input.
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WC {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public struct RECT { public int L, T, R, B; }
}
"@
[WC]::SetProcessDPIAware() | Out-Null
$p = Get-Process -Name $proc -ErrorAction Stop | ? { $_.MainWindowHandle -ne 0 } | select -First 1
$h = $p.MainWindowHandle
if ([WC]::IsIconic($h)) { Write-Output "MINIMIZED"; exit 2 }
$r = New-Object WC+RECT
[WC]::GetClientRect($h, [ref]$r) | Out-Null
$w = $r.R - $r.L; $hh = $r.B - $r.T
$sw = [Diagnostics.Stopwatch]::StartNew()
for ($k = 0; $k -lt $count; $k++) {
  $file = if ($count -gt 1) { $out -replace '\.png$', ('_{0:D2}.png' -f $k) } else { $out }
  $bmp = New-Object System.Drawing.Bitmap $w, $hh
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $dc = $g.GetHdc()
  $ok = [WC]::PrintWindow($h, $dc, 3)
  $g.ReleaseHdc($dc); $g.Dispose()
  $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
  Write-Output ("{0:F2}s ok=$ok $file" -f $sw.Elapsed.TotalSeconds)
  if ($k -lt $count - 1) { Start-Sleep -Milliseconds ([int]($interval * 1000)) }
}
