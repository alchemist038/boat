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
