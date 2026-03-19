@echo off
pushd "%~dp0"
chcp 65001 > nul
if exist ".\.venv\Scripts\python.exe" (
  call .\.venv\Scripts\python.exe auto_system\auto_run.py
) else (
  python auto_system\auto_run.py
)
popd
