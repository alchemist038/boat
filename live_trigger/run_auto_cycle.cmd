@echo off
pushd "%~dp0"
chcp 65001 > nul
if exist ".\.venv\Scripts\python.exe" (
  call .\.venv\Scripts\python.exe auto_system\app\modules\00_reset_execution_mode.py
) else (
  python auto_system\app\modules\00_reset_execution_mode.py
)
if exist ".\.venv\Scripts\python.exe" (
  call .\.venv\Scripts\python.exe auto_system\auto_run.py
) else (
  python auto_system\auto_run.py
)
popd
