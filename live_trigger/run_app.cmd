@echo off
pushd "%~dp0"
chcp 65001 > nul
if exist ".\.venv\Scripts\streamlit.exe" (
  call .\.venv\Scripts\streamlit.exe run app.py
) else (
  streamlit run app.py
)
popd
