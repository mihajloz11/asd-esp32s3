# Wakelock — drzi racun budnim dok traje (NE mijenja trajne postavke).
# Prekid: zatvori ovaj proces (Stop-Process) i sistem se vraca na normalno.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Awake {
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
# ES_CONTINUOUS(0x80000000) | ES_SYSTEM_REQUIRED(0x1) | ES_AWAYMODE_REQUIRED(0x40)
[Awake]::SetThreadExecutionState(0x80000041) | Out-Null
"KEEP-AWAKE aktivan: $(Get-Date)" | Out-File "$PSScriptRoot\..\results\keep_awake.log"
while ($true) {
  Start-Sleep 60
  [Awake]::SetThreadExecutionState(0x80000041) | Out-Null
}
