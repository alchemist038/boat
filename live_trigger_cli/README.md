# Live Trigger CLI

`live_trigger_cli/` は、既存の `live_trigger/` と `live_trigger_fresh_exec/` を触らずに運用するための独立ラインです。  
UI は `http://localhost:8502` 固定で起動し、このライン専用の `settings.json / system.db / auto_run.log` を使います。

## このラインの役割

- UI から設定、watchlist 生成、GO 判定、ベット実行、状態確認まで通せます
- `125` と `c2` は shared BOX を流用します
- `4wind` はこのライン固有の local profile を使います
- Teleboat 実行は既存の fresh executor を流用します

## 起動方法

もっとも簡単なのは次です。

```powershell
live_trigger_cli\run_ui.cmd
```

直接起動する場合は次です。

```powershell
cd C:\CODEX_WORK\boat_clone
.\.venv\Scripts\streamlit.exe run live_trigger_cli\app.py --server.port 8502 --server.headless true --server.fileWatcherType none
```

## UI の基本フロー

1. `設定` タブで `execution_mode` と profile の `ON/OFF / 金額` を決めます
2. 必要なら `system_running = ON` にします
3. `実行` タブで対象日を入れて `sync-watchlists` を押します
4. 次に `evaluate-targets` で GO 判定と intent を作ります
5. `execute-bets` で実行します。まとめて通すなら `run-cycle` を使います
6. 常時待受にするなら `auto-loop を起動` を押します
7. `概要` と `データ` タブで状態を確認します

## execution_mode の意味

- `air`
  - 監視と記録のみ。実投票はしません
- `assist_real`
  - 実投票前に人の確認を入れます
- `armed_real`
  - 自動投票待受です

## 5秒自動更新

- 画面上部の `5秒自動更新` を ON にすると、状態表示を 5 秒ごとに読み直します
- loop の待受確認には ON が便利です
- 設定入力や手動テストを触るときは OFF を推奨します

## タブの見方

### `概要`

- status summary
- loop PID
- 最新 target
- auto_run.log

### `設定`

- `execution_mode`
- `system_running`
- polling 間隔
- 実投票関連設定
- profile ごとの有効化と金額

### `実行`

- `sync-watchlists`
  - shared BOX と local BOX から watchlist を生成します
- `evaluate-targets`
  - beforeinfo / odds を見て GO 判定します
- `execute-bets`
  - pending intent を処理します
- `run-cycle`
  - 上の 3 つをまとめて 1 回流します
- `auto-loop を起動`
  - 定期巡回を開始します

### `手動テスト`

- `login_only`
- `confirm_only`
- `confirm_prefill`
- `assist_real`
- `armed_real`

まずは `confirm_only` で確認画面まで試すのを推奨します。

### `データ`

- `Targets`
- `Intents`
- `Executions`
- `Events`
- `Session`

## フォルダ構成

- `live_trigger_cli/boxes/4wind`
  - このライン固有の `4wind` profile
- `live_trigger_cli/raw`
  - `racelist / beforeinfo / odds2t` のキャッシュ
  - git には含めません
- `live_trigger_cli/data`
  - `settings.json / system.db / auto_run.log / auto_loop.pid / UI ログ`
  - git には含めません
- `live_trigger_cli/run_ui.cmd`
  - `8502` 固定で UI を起動します

## 共有しているもの

- `live_trigger/boxes/125`
- `live_trigger/boxes/c2`
- `live_trigger/auto_system/app/core/bets.py`
- `live_trigger_fresh_exec/auto_system/app/core/fresh_executor.py`

## よくある見え方

### `auto-loop は起動していません` と見える

まず次の 3 つを確認してください。

- `設定` タブの `system_running` が `ON`
- `execution_mode` が意図どおり
- `概要` の `loop PID` が `-` ではない

5秒自動更新が OFF のときは、実体が動いていても表示が古いままのことがあります。

### `125` を ON にしているのに、その日 `4wind` しか出ない

設定の問題ではなく、その日の実データで `125` 条件一致が `0件` のことがあります。  
その場合、active target には `4wind` だけが出ます。

## 補足

このラインは UI 主導で使う前提です。  
CLI コマンドも残していますが、日常運用は UI から触る想定です。
