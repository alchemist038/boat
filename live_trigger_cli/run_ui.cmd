@echo off
setlocal
pushd "%~dp0.."
chcp 65001 > nul

set "REPO_ROOT=%CD%"
set "DATA_DIR=%REPO_ROOT%\live_trigger_cli\data"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
set "STDOUT_LOG=%DATA_DIR%\ui_stdout.log"
set "STDERR_LOG=%DATA_DIR%\ui_stderr.log"
set "STREAMLIT_EXE=%REPO_ROOT%\.venv\Scripts\streamlit.exe"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$repo = [System.IO.Path]::GetFullPath('%REPO_ROOT%');" ^
  "$stdout = [System.IO.Path]::GetFullPath('%STDOUT_LOG%');" ^
  "$stderr = [System.IO.Path]::GetFullPath('%STDERR_LOG%');" ^
  "$streamlit = if (Test-Path '%STREAMLIT_EXE%') { [System.IO.Path]::GetFullPath('%STREAMLIT_EXE%') } else { 'streamlit' };" ^
  "$existing = Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1;" ^
  "if (-not $existing) { Start-Process -FilePath $streamlit -ArgumentList @('run','live_trigger_cli\\app.py','--server.port','8502','--server.headless','true','--server.fileWatcherType','none') -WorkingDirectory $repo -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden | Out-Null }"

start "" "http://localhost:8502"
popd
endlocal
