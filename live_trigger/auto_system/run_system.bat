@echo off
pushd "%~dp0"
chcp 65001 > nul

echo.
echo === Auto Bet Control ===
echo.

echo [1/3] Starting: 01_sync_watchlists.py
python app\modules\01_sync_watchlists.py
echo.

echo [2/3] Starting: 02_evaluate_targets.py
python app\modules\02_evaluate_targets.py
echo.

echo [3/3] Starting: 03_execute_air_bets.py
python app\modules\03_execute_air_bets.py
echo.

echo === All tasks completed ===
echo.
pause
popd
