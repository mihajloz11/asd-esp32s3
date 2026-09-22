param([string]$IdfPath = 'C:\Espressif\frameworks\esp-idf-v5.5.5')
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
# ESP-IDF/CMake needs a short project path without spaces on this machine.
$mappedRoot = 'R:\'
if (Test-Path $mappedRoot) {
    if (-not (Test-Path 'R:\results\mjerenje_2026-09-21\POVEZIVANJE.md')) {
        throw 'R: is already occupied by another directory. Choose a free drive before building.'
    }
} else { subst R: $repoPath }
. (Join-Path $IdfPath 'export.ps1')
foreach ($flagName in @('ASD_INA_TEST','ASD_MIC_TEST','ASD_EVAL_MODE','ASD_LIVE_CAPTURE','ASD_LIVE_ADAPT','ASD_PSD_VERIFY')) {
    Remove-Item "Env:$flagName" -ErrorAction SilentlyContinue
}
$env:ASD_PSD_LIVE='1'
$env:ASD_RESEARCH_TELEMETRY='1'
$env:ASD_E5_MEASURE='1'
$env:IDF_TARGET='esp32s3'
Push-Location 'R:\firmware\esp32s3_asd'
try {
    idf.py -B 'R:\results\mjerenje_2026-09-21\build' build
    if ($LASTEXITCODE -ne 0) { throw 'E5 firmware build failed' }
    python 'R:\results\mjerenje_2026-09-21\make_manifest.py'
    if ($LASTEXITCODE -ne 0) { throw 'Firmware manifest/protected-source verification failed' }
} finally { Pop-Location }
# This script builds only. Flash the APP at 0x10000; preserve bootloader/NVS.
