# Live Trigger

`live_trigger/` は、前日候補抽出から当日直前判定、Air Bet 監査、実ベット運用までをまとめた運用ルートです。

## できること

- 前日に候補を抽出する
- 当日直前に `beforeinfo` で最終判定する
- `auto_system` で `air / assist_real / armed_real` を切り替えて運用する

## フォルダ構成

- `boxes/`
  - logic / project ごとの BOX
  - 各 BOX の `profiles/*.json` に条件を書く
- `watchlists/`
  - 前日候補抽出の CSV
- `ready/`
  - 手動側の直前判定 CSV
- `plans/`
  - 予定ボードや logic board の出力
- `auto_system/`
  - 当日自動運用 UI とループ
- `app.py`
  - 前日準備と手動側の Streamlit アプリ
- `run_app_ui.cmd`
  - 前日準備 UI のランチャー
- `run_auto_ui.cmd`
  - 当日運用 UI のランチャー

## 起動方法

前日準備 UI:

```powershell
cd C:\CODEX_WORK\boat_clone
& .\.venv\Scripts\streamlit.exe run live_trigger\app.py
```

または:

```powershell
live_trigger\run_app_ui.cmd
```

当日運用 UI:

```powershell
cd C:\CODEX_WORK\boat_clone
& .\.venv\Scripts\streamlit.exe run live_trigger\auto_system\web_app.py
```

または:

```powershell
live_trigger\run_auto_ui.cmd
```

## 画面でできること

### `app.py`

- `予定ボード`
  - 2 週間から 1 か月先の予定と BOX 一覧を見る
- `翌日候補抽出`
  - 指定日の候補レースを `watchlist` に出す
- `直前判定`
  - `beforeinfo` を見て `trigger_ready` を確定する

### `auto_system/web_app.py`

- `air`
  - Air Bet 実行時刻を監査する
- `assist_real`
  - 確認画面まで自動で進める
- `armed_real`
  - Teleboat へ自動送信する

## 補足

- batch 抽出は通常 `enabled: true` の profile が対象です
- 実ベットを使う場合は `live_trigger\.env` を用意します
- 手順書は次を参照してください
  - [AUTO_BET_SYSTEM_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AUTO_BET_SYSTEM_RUNBOOK.md)
  - [AIR_BET_AUDIT_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AIR_BET_AUDIT_RUNBOOK.md)
  - [SELF_HEALING_AUTO_BET_VISION.md](/c:/CODEX_WORK/boat_clone/live_trigger/SELF_HEALING_AUTO_BET_VISION.md)
  - [IMPROVEMENT_NOTES.md](/c:/CODEX_WORK/boat_clone/live_trigger/IMPROVEMENT_NOTES.md)
