@echo off
pushd "%~dp0"
chcp 65001 > nul
if exist ".\.venv\Scripts\python.exe" (
  call .\.venv\Scripts\python.exe auto_system\app\modules\00_reset_execution_mode.py
) else (
  python auto_system\app\modules\00_reset_execution_mode.py
)
if exist ".\.venv\Scripts\streamlit.exe" (
  call .\.venv\Scripts\streamlit.exe run auto_system\web_app.py
) else (
  streamlit run auto_system\web_app.py
)
popd
