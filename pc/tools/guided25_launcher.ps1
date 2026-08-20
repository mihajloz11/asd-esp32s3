[CmdletBinding()]
param(
    [ValidateSet("Menu", "Preview", "Test", "Logs", "Preflight")]
    [string]$Mode = "Menu",
    [string]$Port = "COM3",
    [ValidateRange(1, 3)]
    [int]$Attempt = 1,
    [string]$FanId = "fan02",
    [string]$SessionId = "",
    [ValidateRange(1024, 65535)]
    [int]$HttpPort = 8772
)

$ErrorActionPreference = "Stop"
$TaskRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $TaskRoot ".venv\Scripts\python.exe"
$Results = Join-Path $TaskRoot "results\physical_fan"
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $TaskRoot

function Test-TcpPortFree([int]$Number) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Number)
        if ($task.Wait(250) -and $client.Connected) { return $false }
        return $true
    } catch {
        return $true
    } finally {
        $client.Dispose()
    }
}

function Get-Sha256([string]$Path) {
    $stream = [System.IO.File]::OpenRead($Path)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha.ComputeHash($stream)
        return ([System.BitConverter]::ToString($bytes)).Replace("-", "")
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}

function Get-LiveFlags([string]$PortName) {
    $serial = [System.IO.Ports.SerialPort]::new()
    $serial.PortName = $PortName
    $serial.BaudRate = 115200
    $serial.ReadTimeout = 500
    $serial.DtrEnable = $false
    $serial.RtsEnable = $false
    try {
        $serial.Open()
        $deadline = [DateTime]::UtcNow.AddSeconds(8)
        while ([DateTime]::UtcNow -lt $deadline) {
            try {
                $line = $serial.ReadLine().Trim()
                if ($line.StartsWith("FLAGS ")) { return $line }
            } catch [System.TimeoutException] {
                # FLAGS se ponavlja svakih pet sekundi; nastavi do ukupnog roka.
            }
        }
        throw "Nema FLAGS telemetrije sa $PortName u roku od 8 s."
    } finally {
        if ($serial.IsOpen) { $serial.Close() }
        $serial.Dispose()
    }
}

function Invoke-SoftwarePreflight {
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Nedostaje projektni Python: $Python"
    }
    $ports = [System.IO.Ports.SerialPort]::GetPortNames()
    if ($Port -notin $ports) {
        throw "Uredjaj $Port nije pronadjen. Dostupno: $($ports -join ', ')"
    }
    if (-not (Test-TcpPortFree $HttpPort)) {
        throw "Lokalni port $HttpPort je zauzet. Zatvori stari panel/preview prozor."
    }
    & $Python -c "import numpy, serial; print('Python paketi: OK')"
    if ($LASTEXITCODE -ne 0) { throw "Python preflight nije prosao." }
    $firmware = Join-Path $TaskRoot "firmware\esp32s3_asd\build\esp32s3_asd.bin"
    if (-not (Test-Path -LiteralPath $firmware)) {
        throw "Nedostaje izgradjeni firmware: $firmware"
    }
    $flags = Get-LiveFlags $Port
    $requiredFlags = @(
        "protocol=asd-quality-v1.5.0",
        "mode=IDLE",
        "waiting=1",
        "guided25_available=1",
        "workflow_pending=DEFAULT",
        "research_telemetry=1",
        "profile_persistence_allowed=0",
        "dropped=0"
    )
    foreach ($required in $requiredFlags) {
        if ($flags -notmatch "(^| )$([regex]::Escape($required))( |$)") {
            throw "Firmware preflight nije prosao: nedostaje '$required'. FLAGS: $flags"
        }
    }
    $hash = Get-Sha256 $firmware
    Write-Host "COM port: $Port" -ForegroundColor Green
    Write-Host "Dashboard port: $HttpPort (slobodan)" -ForegroundColor Green
    Write-Host "Firmware SHA256: $hash" -ForegroundColor Green
    Write-Host "Firmware FLAGS: $flags" -ForegroundColor Green
    Write-Host "Softverski preflight: PASS" -ForegroundColor Green
}

if ($Mode -eq "Menu") {
    Write-Host ""
    Write-Host "GUIDED25" -ForegroundColor Cyan
    Write-Host "1 - Sigurni read-only pregled dashboarda (ne pokrece test)"
    Write-Host "2 - Pokreni pravi test i sve logove"
    Write-Host "3 - Prati serial.log posljednjeg runa"
    Write-Host "4 - Samo softverski preflight"
    $choice = Read-Host "Izaberi 1, 2, 3 ili 4"
    $Mode = switch ($choice) {
        "1" { "Preview" }
        "2" { "Test" }
        "3" { "Logs" }
        "4" { "Preflight" }
        default { throw "Nepoznat izbor: $choice" }
    }
}

if ($Mode -eq "Logs") {
    $run = Get-ChildItem -LiteralPath $Results -Directory -Filter "run_*" |
        Sort-Object LastWriteTimeUtc | Select-Object -Last 1
    if ($null -eq $run) { throw "Nema nijednog run direktorija u $Results" }
    $log = Join-Path $run.FullName "serial.log"
    if (-not (Test-Path -LiteralPath $log)) { throw "Nedostaje $log" }
    Write-Host "Pratim: $log" -ForegroundColor Cyan
    Write-Host "Prekid pracenja: Ctrl+C (to samo zatvara prikaz, ne test)."
    Get-Content -LiteralPath $log -Wait -Tail 40
    exit 0
}

Invoke-SoftwarePreflight
if ($Mode -eq "Preflight") { exit 0 }

if ($Mode -eq "Preview") {
    Write-Host "Otvaram read-only dashboard. Sve komande su blokirane na serveru." -ForegroundColor Cyan
    Write-Host "Preview se sam zatvara za 15 minuta i ne trosi pokusaj."
    & $Python "pc\tools\asd_panel.py" --port $Port --plan guided25 --attempt $Attempt `
        --read-only-preview --preview-auto-stop-seconds 900 --http-port $HttpPort
    exit $LASTEXITCODE
}

if ([string]::IsNullOrWhiteSpace($SessionId)) {
    $SessionId = "guided25-" + (Get-Date -Format "yyyyMMdd-HHmmss")
}
$enteredFan = Read-Host "Fan ID [$FanId]"
if (-not [string]::IsNullOrWhiteSpace($enteredFan)) { $FanId = $enteredFan.Trim() }
$enteredAttempt = Read-Host "Broj pokusaja 1-3 [$Attempt]"
if (-not [string]::IsNullOrWhiteSpace($enteredAttempt)) {
    $Attempt = [int]$enteredAttempt
    if ($Attempt -lt 1 -or $Attempt -gt 3) { throw "Pokusaj mora biti 1, 2 ili 3." }
}
Write-Host "Session ID: $SessionId"
Write-Host "Provjeri fizicku postavku. Test se jos nije pokrenuo."
$confirmation = Read-Host "Upisi DA ako je ventilator bezbjedno montiran i radi normalno"
if ($confirmation.Trim().ToUpperInvariant() -ne "DA") {
    throw "Nema operaterove potvrde; nista nije pokrenuto."
}

$mountNote = "$env:USERNAME; potvrdjeno prije $SessionId"
Write-Host "Pokrecem host, sve logove i dashboard..." -ForegroundColor Cyan
& $Python "pc\tools\start_fan_run.py" --port $Port --fan-id $FanId `
    --session-id $SessionId --attempt $Attempt --plan guided25 `
    --montaza-potvrdio $mountNote --http-port $HttpPort
exit $LASTEXITCODE
