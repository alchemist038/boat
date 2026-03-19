# Live Trigger

`125` や `c2` のような BOX を使って、
- 前日に候補を抽出
- 当日直前に `beforeinfo` で最終判定
するための土台です。

## フォルダ構成

- `boxes/`
  - logic / project ごとの BOX
  - 各 BOX の `profiles/*.json` に条件を書く
- `watchlists/`
  - 前日候補抽出の CSV
- `ready/`
  - 直前判定後の CSV
- `plans/`
  - 予定ボードや logic board の出力
- `app.py`
  - Streamlit アプリ本体
- `run_app.cmd`
  - 起動用ランチャー

## 起動方法

リポジトリ直下で:

```powershell
cd C:\CODEX_WORK\boat_clone
& .\.venv\Scripts\streamlit.exe run live_trigger\app.py
```

または:

```powershell
live_trigger\run_app.cmd
```

## 画面でできること

- `予定ボード`
  - 2週間から1か月先の予定と BOX 一覧を見る
- `翌日候補抽出`
  - 指定日の候補レースを watchlist に出す
- `直前判定`
  - `beforeinfo` を見て `trigger_ready` を確定する

## 補足

- batch 抽出は通常 `enabled: true` の profile が対象です
- ただしアプリ上では無効 profile も手動で選んで試せます
- `python live_trigger\app.py` ではなく、必ず `streamlit run` で起動してください

## Portable Bundle

This folder is the portable holder for trigger operations. The code now resolves paths from this root, so the same tree can be copied to another machine and used as-is.

- `boxes/`: trigger logic profiles
- `raw/`: cached HTML for trigger-side fetches
- `watchlists/`: pre-day outputs
- `ready/`: trigger-ready and Air Bet inputs
- `plans/`: monthly and pre-day planning outputs
- `air_bet_log.csv`: outcome history for Air Bet

The flow is:

1. Monthly planning with `build-schedule-window`
2. Pre-day planning with `build-logic-board`
3. Day-before watchlist creation with `build-watchlist`
4. Day-of trigger resolution with `resolve-watchlist`
5. Air Bet execution and settlement with the `Air Bet` tab or `run_air_bet_flow_cli`
6. Result aggregation in `ready/` and `air_bet_log.csv`

If you need to relocate the bundle, set `BOAT_LIVE_TRIGGER_ROOT` to the new folder. Otherwise the default is this repository's `live_trigger/` directory.

The one-folder bundle now also includes:

- `runtime/boat_race_data/` for the vendored trigger engine
- `auto_system/` for unattended operation and betting history
- `PORTABLE_BUNDLE.md` for the current portable workflow
