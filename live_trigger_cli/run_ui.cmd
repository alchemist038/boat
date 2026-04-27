@echo off
setlocal
pushd "%~dp0.."
chcp 65001 > nul
title Live Trigger UI Server

set "REPO_ROOT=%CD%"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
set "URL=http://localhost:8502"
if exist "%REPO_ROOT%\data\silver\boat_race.duckdb" (
  set "BOAT_CANONICAL_ROOT=%REPO_ROOT%"
  set "BOAT_DATA_ROOT=%REPO_ROOT%\data"
  set "BOAT_RAW_ROOT=%REPO_ROOT%\data\raw"
  set "BOAT_BRONZE_ROOT=%REPO_ROOT%\data\bronze"
  set "BOAT_DB_PATH=%REPO_ROOT%\data\silver\boat_race.duckdb"
  set "BOAT_REPORTS_ROOT=%REPO_ROOT%\reports\strategies"
  set "BOAT_PREDICT_SCRIPT_PATH=%REPO_ROOT%\workspace_codex\scripts\predict_racer_rank_live.py"
  set "BOAT_ACTIVE_RUNTIME_ROOT=%REPO_ROOT%"
  set "BOAT_ACTIVE_WORKTREE=%REPO_ROOT%"
)
if not defined BOAT_CANONICAL_ROOT if exist "C:\boat\data\silver\boat_race.duckdb" (
  set "BOAT_CANONICAL_ROOT=C:\boat"
  set "BOAT_DATA_ROOT=C:\boat\data"
  set "BOAT_RAW_ROOT=C:\boat\data\raw"
  set "BOAT_BRONZE_ROOT=C:\boat\data\bronze"
  set "BOAT_DB_PATH=C:\boat\data\silver\boat_race.duckdb"
  set "BOAT_REPORTS_ROOT=C:\boat\reports\strategies"
  set "BOAT_PREDICT_SCRIPT_PATH=C:\boat\workspace_codex\scripts\predict_racer_rank_live.py"
  set "BOAT_ACTIVE_RUNTIME_ROOT=C:\boat"
  set "BOAT_ACTIVE_WORKTREE=C:\boat"
)

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8502 .*LISTENING"') do (
  set "EXISTING_PID=%%P"
  goto :already_running
)

echo Starting live_trigger_cli UI in foreground on %URL%
echo Close this window to stop the UI server.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process '%URL%'"

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" -m streamlit run live_trigger_cli\app.py --server.port 8502 --server.headless true --server.fileWatcherType none
) else (
  python -m streamlit run live_trigger_cli\app.py --server.port 8502 --server.headless true --server.fileWatcherType none
)

popd
endlocal
exit /b 0

:already_running
echo live_trigger_cli UI is already running on %URL% ^(PID %EXISTING_PID%^)
start "" "%URL%"
popd
endlocal
exit /b 0
