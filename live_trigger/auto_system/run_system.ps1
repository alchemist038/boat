# Boat Auto System 実行
# このスクリプトは3つのモジュールを順番に実行します。

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " ボートレース自動購入＆検証システム " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Host "[1/3] 事前抽出 (01_pre_scheduler.py)..." -ForegroundColor Yellow
python app\modules\01_pre_scheduler.py

Write-Host "[2/3] 直前判定 (02_just_in_time.py)..." -ForegroundColor Yellow
python app\modules\02_just_in_time.py

Write-Host "[3/3] 投票処理 (03_executor.py)..." -ForegroundColor Yellow
python app\modules\03_executor.py

Write-Host "=========================================" -ForegroundColor Green
Write-Host " 全ての処理が完了しました。" -ForegroundColor Green
Read-Host "閉じるには Enter キーを押してください..."
