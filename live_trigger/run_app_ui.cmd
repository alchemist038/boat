@echo off
pushd "%~dp0"
chcp 65001 > nul
set "ROOT_STREAMLIT=%~dp0..\.venv\Scripts\streamlit.exe"
if exist "%ROOT_STREAMLIT%" (
  call "%ROOT_STREAMLIT%" run app.py
) else (
  if exist ".\.venv\Scripts\streamlit.exe" (
    call .\.venv\Scripts\streamlit.exe run app.py
  ) else (
    streamlit run app.py
  )
)
popd
