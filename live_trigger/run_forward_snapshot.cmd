@echo off
pushd "%~dp0"
chcp 65001 > nul
set "ROOT_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%ROOT_PYTHON%" (
  call "%ROOT_PYTHON%" forward_test_snapshot.py %*
) else (
  if exist ".\.venv\Scripts\python.exe" (
    call .\.venv\Scripts\python.exe forward_test_snapshot.py %*
  ) else (
    python forward_test_snapshot.py %*
  )
)
popd
