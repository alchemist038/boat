@echo off
setlocal
cd /d %~dp0\..
call .\.venv\Scripts\python.exe -m live_trigger_cli_split sync-loop

