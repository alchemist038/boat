@echo off
pushd "%~dp0"
chcp 65001 > nul
set "ROOT_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%ROOT_PYTHON%" (
  call "%ROOT_PYTHON%" auto_system\app\modules\00_reset_execution_mode.py
) else (
  if exist ".\.venv\Scripts\python.exe" (
    call .\.venv\Scripts\python.exe auto_system\app\modules\00_reset_execution_mode.py
  ) else (
    python auto_system\app\modules\00_reset_execution_mode.py
  )
)
if exist "%ROOT_PYTHON%" (
  call "%ROOT_PYTHON%" auto_system\auto_run.py
) else (
  if exist ".\.venv\Scripts\python.exe" (
    call .\.venv\Scripts\python.exe auto_system\auto_run.py
  ) else (
    python auto_system\auto_run.py
  )
)
popd
