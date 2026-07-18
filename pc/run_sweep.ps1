# E1 + E2 + E3 za jednu masinu: trening svih AE varijanti (100 epoha) + PTQ int8.
# Upotreba:  .\run_sweep.ps1 -Machine fan   (iz pc/ direktorijuma)
# Rezultati se dopisuju u results\results.csv; modeli u models\.
param(
    [Parameter(Mandatory = $true)][string]$Machine,
    [int]$Epochs = 100,
    [int]$Seed = 0,
    [string[]]$Variants = @("baseline", "tiny64", "tiny32", "tiny16", "tiny32b4")
)
$py = (Resolve-Path (Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe")).Path
$data = "..\data\dcase2026_dev\$Machine"

foreach ($v in $Variants) {
    Write-Host "=== $Machine / $v : trening ($Epochs epoha, seed $Seed) ==="
    & $py -m asd.train --data $data --variant $v --epochs $Epochs --seed $Seed
    if ($LASTEXITCODE -ne 0) { Write-Host "TRAIN FAIL: $v" ; continue }
    Write-Host "=== $Machine / $v : PTQ int8 ==="
    & $py -m asd.quantize --data $data --tag "${Machine}_${v}_s${Seed}"
    if ($LASTEXITCODE -ne 0) { Write-Host "QUANT FAIL: $v" }
}
Write-Host "=== GOTOVO: $Machine - vidi results\results.csv ==="

