# 5-seed finalne tabele. Prvo fan seeds 1-4 (brz, kompletan 5-seed za fan),
# zatim ostale masine seeds 1-4 (dugo - preko noci). Rezultati u results.csv.
$root = "C:\Users\mihaj\Desktop\master new"
$py = (Resolve-Path "$root\.venv\Scripts\python.exe").Path
# cekaj da MAHALA-int8 zavrsi (izbjegni konflikt pri upisu results.csv)
while (-not (Test-Path "$root\results\mahala_int8_done.txt")) { Start-Sleep 30 }
# fan prvo (kompletan 5-seed primjer)
foreach ($s in 1..4) {
    foreach ($v in @("baseline","tiny64","tiny32","tiny16","tiny32b4")) {
        & $py -m asd.train --data "$root\data\dcase2026_dev\fan" --variant $v --epochs 100 --seed $s
        & $py -m asd.quantize --data "$root\data\dcase2026_dev\fan" --tag "fan_${v}_s${s}"
    }
    "fan seed $s gotov" | Out-File "$root\results\seed_progress.log" -Append
}
# ostale masine seeds 1-4 (preko noci)
foreach ($m in @("bearingEmu","gearboxEmu","sliderEmu","ToyCar","ToyCarEmu","valveEmu")) {
    foreach ($s in 1..4) {
        foreach ($v in @("baseline","tiny64","tiny32","tiny16","tiny32b4")) {
            & $py -m asd.train --data "$root\data\dcase2026_dev\$m" --variant $v --epochs 100 --seed $s
            & $py -m asd.quantize --data "$root\data\dcase2026_dev\$m" --tag "${m}_${v}_s${s}"
        }
        "$m seed $s gotov" | Out-File "$root\results\seed_progress.log" -Append
    }
}
"SVI SEEDOVI GOTOVI" | Out-File "$root\results\seed_progress.log" -Append
