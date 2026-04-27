@echo off
setlocal
pushd "%~dp0"
chcp 65001 > nul

set "ROOT_DIR=%CD%"
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

if exist "%ROOT_DIR%\data\silver\boat_race.duckdb" (
  set "BOAT_CANONICAL_ROOT=%ROOT_DIR%"
  set "BOAT_DATA_ROOT=%ROOT_DIR%\data"
  set "BOAT_RAW_ROOT=%ROOT_DIR%\data\raw"
  set "BOAT_BRONZE_ROOT=%ROOT_DIR%\data\bronze"
  set "BOAT_DB_PATH=%ROOT_DIR%\data\silver\boat_race.duckdb"
  set "BOAT_REPORTS_ROOT=%ROOT_DIR%\reports\strategies"
  set "BOAT_PREDICT_SCRIPT_PATH=%ROOT_DIR%\workspace_codex\scripts\predict_racer_rank_live.py"
)

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" -m live_trigger_cli auto-loop
) else (
  python -m live_trigger_cli auto-loop
)

popd
endlocal