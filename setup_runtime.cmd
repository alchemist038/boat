@echo off
setlocal
pushd "%~dp0"
chcp 65001 > nul
title Boat Runtime Setup

set "ROOT_DIR=%CD%"
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"
set "BOOTSTRAP_CMD="

if exist "%VENV_PYTHON%" goto :venv_ready

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "BOOTSTRAP_CMD=py -3.14"
  goto :create_venv
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  set "BOOTSTRAP_CMD=python"
  goto :create_venv
)

echo No Python bootstrap command was found. Install Python 3.14 or add it to PATH.
popd
endlocal
exit /b 1

:create_venv
echo Creating local runtime venv under "%ROOT_DIR%\.venv"
call %BOOTSTRAP_CMD% -m venv "%ROOT_DIR%\.venv"
if errorlevel 1 (
  echo Failed to create .venv
  popd
  endlocal
  exit /b 1
)

:venv_ready
echo Upgrading pip tooling
call "%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :failed

echo Installing runtime dependencies
call "%VENV_PYTHON%" -m pip install -e ".[app,runtime]"
if errorlevel 1 goto :failed

echo Installing Playwright Chromium
call "%VENV_PYTHON%" -m playwright install chromium
if errorlevel 1 goto :failed

echo Runtime setup completed.
popd
endlocal
exit /b 0

:failed
echo Runtime setup failed.
popd
endlocal
exit /b 1