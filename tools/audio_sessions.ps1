# Lists the default speaker's Windows audio sessions (process, state, per-app volume, mute): the boring reason a
# tools/hear.py recording comes back flat. 2026-10-07: FortniteClient and UnrealEditorFortnite were both MUTED in the
# Windows volume mixer, so every loopback recording of a play session was silent.
#     powershell -NoProfile -ExecutionPolicy Bypass -File tools/audio_sessions.ps1
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator { int NotImpl1(); [PreserveSig] int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice); }
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice { [PreserveSig] int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface); }
[Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionManager2 { int NotImpl1(); int NotImpl2(); [PreserveSig] int GetSessionEnumerator(out IAudioSessionEnumerator SessionEnum); }
[Guid("E2F5BB11-0570-40CA-ACDD-3AA01277DEE8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionEnumerator { [PreserveSig] int GetCount(out int SessionCount); [PreserveSig] int GetSession(int SessionCount, out IAudioSessionControl2 Session); }
[Guid("bfb7ff88-7239-4fc9-8fa2-07c950be9c6d"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionControl2 { [PreserveSig] int GetState(out int s); int A(); int B(); int C(); int D(); int E(); int F(); int G(); int H(); int I(); int J(); [PreserveSig] int GetProcessId(out uint pid); }
[Guid("87CE5498-68D6-44E5-9215-6DA47EF883D8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface ISimpleAudioVolume { [PreserveSig] int SetMasterVolume(float f, ref Guid g); [PreserveSig] int GetMasterVolume(out float f); [PreserveSig] int SetMute(bool m, ref Guid g); [PreserveSig] int GetMute(out bool m); }
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumerator {}
public class S {
  public static string List() {
    var en = (IMMDeviceEnumerator)(new MMDeviceEnumerator());
    IMMDevice dev; en.GetDefaultAudioEndpoint(0, 1, out dev);
    Guid iid = typeof(IAudioSessionManager2).GUID; object o; dev.Activate(ref iid, 23, IntPtr.Zero, out o);
    var mgr = (IAudioSessionManager2)o; IAudioSessionEnumerator se; mgr.GetSessionEnumerator(out se);
    int n; se.GetCount(out n); var sb = new System.Text.StringBuilder();
    for (int i = 0; i < n; i++) {
      IAudioSessionControl2 c; se.GetSession(i, out c); uint pid; c.GetProcessId(out pid); int st; c.GetState(out st);
      var v = (ISimpleAudioVolume)c; float vol; bool mute; v.GetMasterVolume(out vol); v.GetMute(out mute);
      string name = "?"; try { name = System.Diagnostics.Process.GetProcessById((int)pid).ProcessName; } catch {}
      sb.AppendLine(pid + " " + name + " state=" + st + " vol=" + vol + " mute=" + mute);
    }
    return sb.ToString();
  }
}
"@
[S]::List()
