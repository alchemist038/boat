# Live Trigger CLI

`live_trigger_cli/` は、今後の主運用ラインです。  
既存の [live_trigger](/c:/CODEX_WORK/boat_clone/live_trigger) と [live_trigger_fresh_exec](/c:/CODEX_WORK/boat_clone/live_trigger_fresh_exec) は残しますが、通常の待受と実行はこの新ラインを優先します。

## 位置づけ

- 主系: `live_trigger_cli`
- 予備系: `live_trigger/` と `live_trigger_fresh_exec/`
- shared の正本:
  - `live_trigger/boxes/125`
  - `live_trigger/boxes/c2`
  - `live_trigger/auto_system/app/core/bets.py`
- 新ライン固有:
  - `live_trigger_cli/data/settings.json`
  - `live_trigger_cli/data/system.db`
  - `live_trigger_cli/data/auto_run.log`
  - `live_trigger_cli/raw/`
  - `live_trigger_cli/boxes/4wind/`

つまり、ロジック正本は shared に置きつつ、運用状態と UI は新ラインで持ちます。

## 現在の対象

- `125_broad_four_stadium`
- `c2_provisional_v1`
- `4wind_base_415`

補足:

- 3本とも `開催最終日` は watchlist 生成段階で除外します
- `c2` は `B2 cut` を実装済みです
- 意味は `2-ALL-ALL / 3-ALL-ALL` の `ALL` から `B2` 艇を外すことです
- 当日 watchlist が持つ lane class を使うので、ライブ時にもそのまま効きます

## 起動

UI は次で起動します。

```powershell
live_trigger_cli\run_ui.cmd
```

ブラウザは `http://localhost:8502` を使います。

手動で起動する場合:

```powershell
cd C:\CODEX_WORK\boat_clone
.\.venv\Scripts\streamlit.exe run live_trigger_cli\app.py --server.port 8502 --server.headless true --server.fileWatcherType none
```

## 基本フロー

1. `設定` タブで `execution_mode` と profile の `ON/OFF / 金額` を決める
2. `system_running` を `ON`
3. `実行` タブで対象日を入れて `sync-watchlists`
4. `evaluate-targets` で GO 判定と intent を作る
5. `execute-bets` で実行する。まとめてやるなら `run-cycle`
6. 常時待受するなら `auto-loop を起動`

最初の確認は `手動テスト -> confirm_only` がおすすめです。

## execution_mode

- `air`
  - 監視と記録のみ。実投票しない
- `assist_real`
  - 実投票直前で人の確認を入れる
- `armed_real`
  - 自動投票まで進む

## タブの見方

### `概要`

- 状態サマリー
- loop 状態
- 最新 target
- 自動更新の ON/OFF

### `設定`

- `execution_mode`
- `system_running`
- polling 秒数
- profile ごとの有効化と金額

### `実行`

- `sync-watchlists`
  - 新ライン自身が `125 / c2 / 4wind` を生成します
- `evaluate-targets`
  - beforeinfo / odds を見て GO 判定します
- `execute-bets`
  - pending intent を処理します
- `run-cycle`
  - 上の 3 つをまとめて 1 周回します
- `auto-loop を起動`
  - 定期周回を開始します

### `手動テスト`

- `confirm_only`
- `confirm_prefill`
- `assist_real`
- `armed_real`

Teleboat の動作確認は、まず `confirm_only` で確認画面到達まで試してください。

### `データ`

- Targets
- Intents
- Executions
- Events
- Session

## 主系運用の考え方

- 通常運用は新ラインを使う
- shared BOX の修正は shared 側へ入れる
- 旧ラインは障害時の退避先として残す
- 新ライン固有の UI や DB は旧ラインへ持ち込まない

## トラブル時

### `auto-loop が動いているか分からない`

次を見れば確認できます。

- `概要` タブの loop 状態
- `live_trigger_cli/data/auto_loop.pid`
- `live_trigger_cli/data/auto_run.log`

### `125 を ON にしているのに今日は 4wind だけ見える`

設定異常とは限りません。  
その日の実データで `125` 条件一致が `0件` なら、active target は `4wind` だけになります。

### `C2 の点数が以前より少ない`

正常です。  
`B2 cut` により、`ALL` 展開から `B2` 艇を外すようになっています。

## メモ

- UI は 5 秒自動更新を使えます
- `run_ui.cmd` は `8502` 固定です
- 新ラインの loop や DB は旧ラインと共有しません
