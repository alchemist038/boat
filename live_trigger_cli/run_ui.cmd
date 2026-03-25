@echo off
setlocal
pushd "%~dp0.."
chcp 65001 > nul

set "REPO_ROOT=%CD%"
set "STREAMLIT_EXE=%REPO_ROOT%\.venv\Scripts\streamlit.exe"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$existing = Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1;" ^
  "if ($existing) { exit 10 } else { exit 0 }"

if "%ERRORLEVEL%"=="10" (
  echo live_trigger_cli UI is already running on http://localhost:8502
  start "" "http://localhost:8502"
  popd
  endlocal
  exit /b 0
)

echo Starting live_trigger_cli UI in foreground on http://localhost:8502
start "" "http://localhost:8502"

if exist "%STREAMLIT_EXE%" (
  "%STREAMLIT_EXE%" run live_trigger_cli\app.py --server.port 8502 --server.headless true --server.fileWatcherType none
) else (
  streamlit run live_trigger_cli\app.py --server.port 8502 --server.headless true --server.fileWatcherType none
)

popd
endlocal
