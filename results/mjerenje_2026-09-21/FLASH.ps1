param(
    [Parameter(Mandatory=$true)][string]$Port,
    [switch]$RestoreOriginal,
    [string]$Python = (Join-Path $env:USERPROFILE '.espressif\python_env\idf5.5_py3.13_env\Scripts\python.exe')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python)) { throw 'ESP-IDF Python not found. Supply -Python with its full path.' }
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'firmware-manifest.json') -Raw | ConvertFrom-Json
$imagePath = Join-Path $PSScriptRoot 'firmware-e5.bin'
$expectedHash = $manifest.app_sha256
if ($RestoreOriginal) {
    $imagePath = Join-Path $PSScriptRoot 'backup\original-app.bin'
    $original = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'backup\manifest.json') -Raw | ConvertFrom-Json
    $expectedHash = $original.original_app_sha256
}
if ((Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'Firmware hash differs from the verified manifest. Rebuild/verify before flashing.'
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$backupPath = Join-Path $PSScriptRoot "backup\preflash-$stamp.bin"
Write-Host 'USB power only; external power supply must be disconnected. Saving current bootloader/NVS/app first.'
& $Python -m esptool --chip esp32s3 --port $Port --baud 921600 read_flash 0x0 0x410000 $backupPath
if ($LASTEXITCODE -ne 0 -or (Get-Item -LiteralPath $backupPath).Length -ne 0x410000) { throw 'Backup failed. Nothing flashed.' }
(Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash | Set-Content -LiteralPath ($backupPath + '.sha256')
& $Python -m esptool --chip esp32s3 --port $Port --baud 921600 write_flash 0x10000 $imagePath
if ($LASTEXITCODE -ne 0) { throw 'Application flash failed. Keep USB attached and inspect the error.' }
& $Python -m esptool --chip esp32s3 --port $Port --baud 921600 verify_flash 0x10000 $imagePath
if ($LASTEXITCODE -ne 0) { throw 'Application flash verification failed.' }
Write-Host 'App flashed and verified at 0x10000. Bootloader, partition table and NVS were not flashed.'
