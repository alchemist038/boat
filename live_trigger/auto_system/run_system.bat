@echo off
pushd "%~dp0"
chcp 65001 > nul

echo.
echo === Boat Auto System ===
echo.

echo [1/3] Starting: 01_pre_scheduler.py
python app\modules\01_pre_scheduler.py
echo.

echo [2/3] Starting: 02_just_in_time.py
python app\modules\02_just_in_time.py
echo.

echo [3/3] Starting: 03_executor.py
python app\modules\03_executor.py
echo.

echo === All tasks completed ===
echo.
pause
popd
