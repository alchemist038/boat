# Forward Test 対応手順書

`live_trigger/` をフォワードテストで回すときに、起きた事象へすぐ対応するための運用メモです。

通常手順は [AUTO_BET_SYSTEM_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AUTO_BET_SYSTEM_RUNBOOK.md) を基準にし、この MD では「異常が起きたときにどこを見るか」を先に整理します。

## まず使うもの

- 状態スナップショット

```bat
C:\CODEX_WORK\boat_clone\live_trigger\run_forward_snapshot.cmd
```

- auto loop の末尾ログ

```powershell
Get-Content C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\auto_run.log -Tail 80
```

- 1 サイクルだけ手動実行

```bat
C:\CODEX_WORK\boat_clone\live_trigger\auto_system\run_system.bat
```

## 開始前チェック

フォワードテスト開始前は最低限ここだけ確認します。

1. `run_forward_snapshot.cmd` を実行する
2. `system_running` と `execution_mode` を確認する
3. `active_profiles` が想定どおりか確認する
4. `next_targets` に今日の対象が出ることを確認する
5. `assist_real` / `armed_real` のときは `session_status=verified` と `resident_browser=running` を確認する
6. `auto_run.log` の更新時刻が進み続けていることを確認する

補足:

- launcher (`run_auto_ui.cmd`, `run_auto_cycle.cmd`) から再起動した場合、`execution_mode` は安全側で `air` に戻ります
- `settings.json` に `assist_real` が残っていても、再起動後は UI で保存し直さない限り復帰しません

## 正常系の見え方

### `air`

1. `imported`
2. `monitoring`
3. `checked_waiting` または `checked_skip`
4. `intent_created`
5. `air_bet_logged`

### `assist_real`

1. `intent_created`
2. `Teleboat ログイン確認 = verified`
3. 確認画面到達
4. 人が送信
5. `submitted` または `assist_timeout`

### `armed_real`

1. `intent_created`
2. `Teleboat ログイン確認 = verified`
3. 自動送信
4. `submitted`

## 事象別の初動

### 1. 何も起きない

症状:

- `checked=0`
- `no pending intents for today`
- UI でも対象が進まない

見る場所:

- `run_forward_snapshot.cmd` の `next_targets`
- `auto_run.log`
- `当日対象` タブ

切り分け:

- `next_targets` の締切がまだ監視開始前なら正常待機
- 監視ウィンドウ内なのに `status=imported` のままなら `02_evaluate_targets.py` 側を疑う
- `system_running=false` なら単純停止

対応:

1. `run_system.bat` で 1 サイクルだけ手動実行する
2. `auto_run.log` が更新されるか確認する
3. それでも進まなければ `watchlist` 日付と `active_profiles` を確認する

### 2. `waiting_beforeinfo` / `checked_waiting` から進まない

症状:

- `row_status=waiting_beforeinfo`
- `checked_waiting` が続く

見る場所:

- `run_forward_snapshot.cmd` の `next_targets`
- `raw\beforeinfo`
- `target_races.payload_json`
- `execution_events`

意味:

- `beforeinfo` がまだ揃っていない
- 取得はできたが最終判定に必要な値が足りていない

対応:

1. まず 1 サイクルだけ再実行する
2. 期限が迫っているなら当該 profile は `air` へ落として観測優先にする
3. 事象保存のため、対象レースの `payload_json` と `auto_run.log` を残す

### 3. Teleboat が `verified` にならない

症状:

- `session_status != verified`
- `login_required`
- 期限切れページ

見る場所:

- `TELEBOAT_LOGIN_STATUS.md`
- `Session` タブ
- `teleboat_session_state.json`
- `teleboat_resident_browser.json`

対応:

1. `assist_real` / `armed_real` ならいったん `システム停止`
2. `Teleboat セッション準備`
3. resident browser 上でログイン
4. 不要な Teleboat タブを閉じて `トップ画面 1 タブ` にする
5. `Teleboat ログイン確認`
6. `verified` を取ってから再開

ルール:

- ログイン画面タブとトップ画面タブが両方ある状態では進めない
- 期限切れページが出たら実セッション切れ前提で扱う

### 4. `assist_timeout`

症状:

- `bet_executions.execution_status=assist_timeout`

意味:

- 確認画面までは到達したが、人の送信待ちで時間切れ

対応:

1. まず異常ではなく「間に合わなかった」扱いかを確認する
2. 実機確認フェーズなら `assist_real` 継続でよい
3. 確認画面に早く出したい場合は `manual_action_timeout_seconds` を見直す
4. 連発するならその日は `air` に戻して、送信タイミングより手前の安定確認に切り替える

### 5. `real_bet_error` / 画面要素が見つからない

症状:

- `レース場 ... に使える要素が見つかりません`
- `Teleboat ログイン後のトップ画面へ移動できませんでした`

見る場所:

- `teleboat_screenshots`
- `teleboat_html`
- `Session` タブ
- `recent_session_events`

対応:

1. 即 `air` へ落とすか、対象 profile を OFF にする
2. `Teleboat ログイン確認` を取り直す
3. 常駐ブラウザのタブを 1 枚へ整理する
4. 保存された HTML / screenshot を見て selector 崩れかセッション崩れかを切り分ける

### 6. 資金不足

症状:

- `TeleboatInsufficientFundsError`
- 購入限度額 0 円系
- 自動停止

対応:

1. `system_running=false` になっていないか確認する
2. 残高または購入限度額を確認する
3. その日を続行するなら `air` で監査だけ継続する
4. 復帰後に実投票へ戻す場合は `Teleboat ログイン確認` をやり直す

### 7. loop が止まった / ログが更新されない

症状:

- `auto_run.log` の更新時刻が止まる
- UI は開いているが中身が進まない

対応:

1. `run_forward_snapshot.cmd` で `auto_run.log last_updated_at` を確認する
2. `システム停止` 後に再起動する
3. 必要なら `run_auto_cycle.cmd` ではなく UI から再開し、`execution_mode` を再確認する
4. 再起動後、最初の数サイクルで `sync_watchlists completed` と `evaluate_targets completed` が出るか確認する

## その場で保存しておく証跡

事象が起きたら次を残しておくと、後で原因を追いやすいです。

- `auto_run.log` の末尾 80 行
- `run_forward_snapshot.cmd` の出力
- `teleboat_screenshots\`
- `teleboat_html\`
- `teleboat_session_state.json`
- `teleboat_resident_browser.json`
- `bet_executions`, `session_events`, `execution_events` の該当行

## 安全側へ戻す判断

迷ったら次の順で安全側へ戻します。

1. 問題の profile を OFF
2. `assist_real` / `armed_real` から `air` へ戻す
3. `システム停止`
4. Teleboat セッションを整え直してから再開

## 今日の運用で特に見る点

現状の `live_trigger` は、通常手順よりも次の 2 点が事象化しやすいです。

- Teleboat 常駐ブラウザのタブ状態が崩れて、自動側が誤タブを掴む
- 監視自体は回っているのに、対象がまだ監視開始前で `何も起きていない` ように見える

この 2 つを最初に切り分けるために、フォワードテスト中はまず `run_forward_snapshot.cmd` を先に見る運用に寄せるのが安全です。
