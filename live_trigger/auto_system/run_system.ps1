# Auto Bet Control one-cycle runner
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Auto Bet Control " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Host "[1/3] watchlist 同期 (01_sync_watchlists.py)..." -ForegroundColor Yellow
python app\modules\01_sync_watchlists.py

Write-Host "[2/3] 締切ウィンドウ判定 (02_evaluate_targets.py)..." -ForegroundColor Yellow
python app\modules\02_evaluate_targets.py

Write-Host "[3/3] ベット実行 (03_execute_air_bets.py)..." -ForegroundColor Yellow
python app\modules\03_execute_air_bets.py

Write-Host "=========================================" -ForegroundColor Green
Write-Host " すべての処理が完了しました " -ForegroundColor Green
Read-Host "閉じるには Enter キーを押してください..."
