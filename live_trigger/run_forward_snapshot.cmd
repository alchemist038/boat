@echo off
pushd "%~dp0"
chcp 65001 > nul
if exist ".\.venv\Scripts\python.exe" (
  call .\.venv\Scripts\python.exe forward_test_snapshot.py %*
) else (
  python forward_test_snapshot.py %*
)
popd
