# Live Trigger CLI

`live_trigger_cli/` は、既存の `live_trigger/` と `live_trigger_fresh_exec/` を変更せずに追加した、
CLI 主導の独立ベットラインです。

目的は次の 2 点です。

- 既存ラインを壊さずに、`sync -> evaluate -> execute` を CLI で通せるようにする
- Teleboat の実行部分は既存資産を流用しつつ、状態管理は新ライン側で分離する

## このラインの特徴

このラインは、既存の運用資産を再利用しつつ、自分専用の状態ファイルを持ちます。

再利用するもの:

- `live_trigger/boxes/`
  - shared strategy BOX の正本
- `live_trigger/watchlists/`
  - shared watchlist
- `live_trigger/raw/`
  - trigger 側 raw cache
- `live_trigger/auto_system/app/core/bets.py`
  - bet 展開ロジック
- `live_trigger_fresh_exec/auto_system/app/core/fresh_executor.py`
  - Teleboat 実行ロジック

このラインが独自に持つもの:

- `live_trigger_cli/boxes/`
  - 既存ラインを触らずに追加したいローカル runtime profile
- `live_trigger_cli/data/settings.json`
  - CLI ライン専用設定
- `live_trigger_cli/data/system.db`
  - CLI ライン専用 DB
- `live_trigger_cli/data/auto_run.log`
  - CLI ライン専用ログ

## 4wind について

このラインでは、`4wind` を `live_trigger_cli/boxes/4wind/` にローカル実装しています。

- 既存の `live_trigger/boxes/` は変更しない
- `4wind` は exacta `4-1 / 4-5`
- 判定には風速、展示 ST 差、展示タイム順位、3 号艇級別、2 連単オッズを使う

現時点の `4wind` profile は次です。

- `4wind_base_415`

## 重複買い目の扱い

同一レースで `125 / c2 / 4wind` が同時に GO した場合でも、このラインでは 1 レース単位でまとめて実行します。

- grouping は `(race_id, execution_mode)` 単位
- 同じ `(bet_type, combo)` が重なった場合は Teleboat へ送る前に金額を合算
- execution 記録は元の intent ごとに残す

## コマンド一覧

```powershell
python -m live_trigger_cli show-settings
python -m live_trigger_cli configure --execution-mode air --setting default_bet_amount=100
python -m live_trigger_cli sync-watchlists --race-date 2026-03-22
python -m live_trigger_cli evaluate-targets --race-date 2026-03-22
python -m live_trigger_cli execute-bets --race-date 2026-03-22
python -m live_trigger_cli run-cycle --race-date 2026-03-22
python -m live_trigger_cli manual-test --test-mode confirm_only --stadium-code 01 --race-no 12 --bet trifecta:1-2-5:100
python -m live_trigger_cli summary
```

## UI 起動

新ライン専用の Streamlit UI も用意しています。

```powershell
live_trigger_cli\run_ui.cmd
```

または:

```powershell
cd C:\CODEX_WORK\boat_clone
.\.venv\Scripts\streamlit.exe run live_trigger_cli\app.py
```

## 主なコマンドの意味

- `show-settings`
  - 現在の設定を表示する
- `configure`
  - 実行モード、金額、各種設定を更新する
- `sync-watchlists`
  - shared watchlist を CLI ラインの DB に取り込む
- `evaluate-targets`
  - `beforeinfo` を取得して GO 判定し、必要なら intent を作る
- `execute-bets`
  - pending intent を処理する
- `run-cycle`
  - `sync -> evaluate -> execute` を 1 回まとめて実行する
- `auto-loop`
  - `system_running=true` の間、一定間隔で `run-cycle` を繰り返す
- `manual-test`
  - Teleboat の手動検証や確認画面到達テストを行う
- `summary`
  - 現在の DB の簡易集計を表示する

## 使い始め

まず設定確認:

```powershell
python -m live_trigger_cli show-settings
```

shared watchlist の取り込み:

```powershell
python -m live_trigger_cli sync-watchlists --race-date 2026-03-22
```

1 サイクル実行:

```powershell
python -m live_trigger_cli run-cycle --race-date 2026-03-22
```

状態確認:

```powershell
python -m live_trigger_cli summary
```

混在買い目の確認画面テスト:

その時点で発売中の場・レースに置き換えて実行します。

```powershell
python -m live_trigger_cli manual-test --test-mode confirm_only --stadium-code 24 --race-no 12 `
  --bet trifecta:1-2-5:100 `
  --bet trifecta:2-ALL-ALL:100 `
  --bet trifecta:3-ALL-ALL:100 `
  --bet exacta:4-1:100 `
  --bet exacta:4-5:100 `
  --cleanup-after-test
```

## ループ実行

`system_running=true` にしてから `auto-loop` を起動します。

```powershell
python -m live_trigger_cli configure --setting system_running=true
python -m live_trigger_cli auto-loop
```

停止するときは:

```powershell
python -m live_trigger_cli configure --setting system_running=false
```

## 注意

- このラインは `live_trigger/` や `live_trigger_fresh_exec/` の DB や設定を直接書き換えません
- 実投票の実装は既存の Teleboat 実装を流用しています
- shared strategy 条件の正本は引き続き `live_trigger/boxes/` です
- ただし `4wind` は「既存ラインを触らない」という方針のため、この新ライン内の `live_trigger_cli/boxes/4wind/` に置いています
- 発売中ではない場・レースを指定した場合は、別レースへ流さずエラーで止めます
