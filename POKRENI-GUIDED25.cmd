@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc\tools\guided25_launcher.ps1" %*
set "GUIDED25_EXIT=%ERRORLEVEL%"
if not "%GUIDED25_EXIT%"=="0" (
  echo.
  echo GUIDED25 launcher je zavrsio sa greskom. Procitaj poruku iznad.
  if "%~1"=="" pause
  exit /b %GUIDED25_EXIT%
)
exit /b 0
