$root = "C:\Users\mihaj\Desktop\master new"
while (-not (Select-String -Path "$root\results\sweep_bearingEmu.log" -Pattern "GOTOVO" -Quiet -ErrorAction SilentlyContinue)) { Start-Sleep 60 }
foreach ($m in @("gearboxEmu","sliderEmu","ToyCar","ToyCarEmu","valveEmu")) {
    cd "$root\pc"
    & .\run_sweep.ps1 -Machine $m *>> "$root\results\sweep_$m.log"
}
"SVE MASINE GOTOVE" *>> "$root\results\sweep_queue.log"
