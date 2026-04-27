@echo off
pushd "%~dp0"
chcp 65001 > nul
set "ROOT_PYTHON=%~dp0..\.venv\Scripts\python.exe"
set "ROOT_STREAMLIT=%~dp0..\.venv\Scripts\streamlit.exe"
if exist "%ROOT_PYTHON%" (
  call "%ROOT_PYTHON%" auto_system\app\modules\00_reset_execution_mode.py
) else (
  if exist ".\.venv\Scripts\python.exe" (
    call .\.venv\Scripts\python.exe auto_system\app\modules\00_reset_execution_mode.py
  ) else (
    python auto_system\app\modules\00_reset_execution_mode.py
  )
)
if exist "%ROOT_STREAMLIT%" (
  call "%ROOT_STREAMLIT%" run auto_system\web_app.py
) else (
  if exist ".\.venv\Scripts\streamlit.exe" (
    call .\.venv\Scripts\streamlit.exe run auto_system\web_app.py
  ) else (
    streamlit run auto_system\web_app.py
  )
)
popd
