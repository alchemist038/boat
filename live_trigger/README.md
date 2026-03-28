# Live Trigger

`live_trigger/` は、前日候補抽出から当日直前判定、Air Bet 監査、実ベット運用までをまとめた運用ルートです。

## できること

- 前日に候補を抽出する
- 当日直前に `beforeinfo` で最終判定する
- `auto_system` で `air / assist_real / armed_real` を切り替えて運用する

## フォルダ構成

- `boxes/`
  - logic / project ごとの shared BOX
  - 各 BOX の `profiles/*.json` に条件を書く
  - `trigger / auto / replay / fresh_exec` が共有する単一の条件ソース
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
- `app.py` で `watchlist` を作っただけでは `auto_system` 画面にはまだ出ません
- `auto_system` は `watchlists/*.csv` を `auto_system/data/system.db` に同期してから当日対象として表示します
- そのため、当日候補を `auto` 側へ反映したいときは `システム起動` または `1サイクルだけ実行` を少なくとも 1 回動かします
- `boxes/` は runtime の single source of truth です
- 新ラインは [live_trigger_fresh_exec/README.md](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec/README.md) を参照してください
- `trigger` は当日 watchlist の元データを作成し、`fresh_exec` はその当日分を取り込んで `beforeinfo` を自動取得し、shared BOX で GO 判定します
- `fresh_exec` は `watchlists/raw/boxes` を共有しつつ、`settings.json/system.db/auto_run.log` は新ライン専用です
- 2026-03-21 時点で、新ラインは `sync -> evaluate -> execute` の単独ループ、手動 Fresh テスト、確認画面到達、テスト後ログアウトまで確認済みです
- 共有ルールは [PROJECT_RULES.md](/c:/CODEX_WORK/boat_clone/live_trigger/PROJECT_RULES.md) を参照してください
- 実ベットを使う場合は `live_trigger\.env` を用意します
- フォワードテスト中の現況確認は `run_forward_snapshot.cmd` でまとめて確認できます
- 手順書は次を参照してください
  - [AUTO_BET_SYSTEM_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AUTO_BET_SYSTEM_RUNBOOK.md)
  - [AIR_BET_AUDIT_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AIR_BET_AUDIT_RUNBOOK.md)
  - [FORWARD_TEST_RESPONSE_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/FORWARD_TEST_RESPONSE_RUNBOOK.md)
  - [SELF_HEALING_AUTO_BET_VISION.md](/c:/CODEX_WORK/boat_clone/live_trigger/SELF_HEALING_AUTO_BET_VISION.md)
  - [IMPROVEMENT_NOTES.md](/c:/CODEX_WORK/boat_clone/live_trigger/IMPROVEMENT_NOTES.md)
  - [BOX_GO_RUNTIME_CONCEPT.md](/c:/CODEX_WORK/boat_clone/live_trigger/BOX_GO_RUNTIME_CONCEPT.md)
