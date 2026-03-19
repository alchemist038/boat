# Portable Live Trigger Bundle

`live_trigger/` は、前日準備と当日自動運用を 1 つにまとめた portable bundle です。  
このフォルダを単位として持ち運び、相対配置を崩さず使う前提です。

## Folder map

- `app.py`
  - 前日準備と手動側の Streamlit UI
- `runtime/boat_race_data/`
  - vendored trigger engine
- `auto_system/`
  - 当日自動運用 UI とループ
- `boxes/`
  - logic profiles
- `plans/`
  - monthly / pre-day planning outputs
- `watchlists/`
  - day-before target lists
- `ready/`
  - manual resolve results
- `raw/`
  - trigger-side cached HTML
- `air_bet_log.csv`
  - 手動側 Air Bet 履歴
- `auto_system/data/system.db`
  - 自動運用の state / execution history
- `.env.example`
  - Teleboat 環境変数ひな形

## Unified flow

1. 前日準備
   - `app.py` を起動する
   - `翌日候補抽出` で `watchlists/` を作る
2. 当日運用
   - `auto_system/web_app.py` を起動する
   - `air / assist_real / armed_real` を選ぶ
   - `watchlist` を DB に取り込み、締切 10〜5 分前だけ判定する
3. 実行
   - `air`: Air Bet 実行時刻を記録
   - `assist_real`: 確認画面まで自動で進行
   - `armed_real`: Teleboat へ自動送信
4. 記録
   - Auto side は `auto_system/data/system.db`
   - Manual side は `air_bet_log.csv`

## Launchers

- `run_app_ui.cmd`
  - 前日準備 UI
- `run_auto_ui.cmd`
  - 当日自動運用 UI
- `run_auto_cycle.cmd`
  - 当日ループ起動

## Setup notes

- Python dependencies は `requirements.txt`
- 実ベットを使う場合は `live_trigger/.env` を作る
- Playwright の persistent profile は既定で `auto_system/data/playwright_user_data`
- このフォルダを移動しても、相対パス前提の構成はそのまま使える

## Documents

- [AUTO_BET_SYSTEM_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AUTO_BET_SYSTEM_RUNBOOK.md)
- [AIR_BET_AUDIT_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AIR_BET_AUDIT_RUNBOOK.md)
