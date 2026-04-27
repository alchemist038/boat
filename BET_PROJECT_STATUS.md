# Bet Project Status

## Companion Docs

- root index: [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- operating model: [OPERATING_MODEL.md](./OPERATING_MODEL.md)
- main trigger overview: [live_trigger/README.md](./live_trigger/README.md)
- main CLI line: [live_trigger_cli/README.md](./live_trigger_cli/README.md)
- current forward performance: [README.md](./reports/live_trade/live_trigger_cli_forward_logic_performance_latest/README.md)
- portable trigger bundle: [live_trigger/PORTABLE_BUNDLE.md](./live_trigger/PORTABLE_BUNDLE.md)
- next runtime concept: [live_trigger/BOX_GO_RUNTIME_CONCEPT.md](./live_trigger/BOX_GO_RUNTIME_CONCEPT.md)
- fresh exec overview: [live_trigger_fresh_exec/README.md](./live_trigger_fresh_exec/README.md)
- fresh execution flow: [live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md](./live_trigger_fresh_exec/FRESH_EXECUTION_FLOW.md)
- shared runtime rules: [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)

## 2026-04-27 C:\boat Self-Contained Runtime Cutover

The main bet line is now running from the `C:\boat` tree on this machine.

- runtime / execution base:
  - `C:\boat`
- Git / research workspace:
  - `C:\CODEX_WORK\boat_clone`
- canonical data root:
  - `C:\boat\data`
- canonical DuckDB:
  - `C:\boat\data\silver\boat_race.duckdb`
- canonical reports root:
  - `C:\boat\reports\strategies`
- runtime-hot state:
  - `C:\boat\live_trigger_cli\data`
  - `C:\boat\live_trigger_cli\raw`
  - `C:\boat\live_trigger_fresh_exec\auto_system\data`
- legacy rollback / fallback share:
  - `\\038INS\boat`

Operational status:

- `live_trigger_cli` loop was restarted from `C:\boat` on
  `2026-04-27 22:24:22 JST`
- the restarted loop completed its first full cycle at
  `2026-04-27 22:24:50 JST`
- `auto_run.log` continued advancing after restart
- UI server on port `8502` was restarted from `C:\boat`
- daily DB refresh and racer-index task actions now point to `C:\boat`
- `C:\boat\.venv` was created and populated for runtime launch

Important scope boundary:

- this cutover now includes runtime-hot state for the current main line
- `C:\CODEX_WORK\boat_clone` remains the edit/test/research worktree
- `C:\boat` is the active execution copy

Practical read:

- the main operating line no longer depends on `C:\CODEX_WORK\boat_clone` for
  its live runtime state on this machine
- the share remains a rollback path, not the intended live writer root
- if `C:\boat` is moved to another machine, `setup_runtime.cmd` plus the task
  registration script are the intended bootstrap path

## 2026-04-27 Auto-Loop PID Note

Observed on this machine:

- the UI and the bet-line loop are separate by design
- one logical `auto-loop` can appear as two Windows processes
  - launcher PID from `C:\CODEX_WORK\boat_clone\.venv\Scripts\python.exe`
  - actual worker PID from the base Python interpreter
- this was reproduced outside the bet line with a plain
  `C:\CODEX_WORK\boat_clone\.venv\Scripts\python.exe -c ...` launch, so it is
  not evidence that `live_trigger_cli` intentionally forks a second loop

Current practical read:

- this is mainly a PID-display / monitoring ambiguity
- it is not current evidence of duplicate bet execution
- stopping via `system_running=false` remains the intended control path
- the active worker should be judged by `auto_run.log` freshness and the
  `auto-loop started on PID ...` line, not by the launcher PID alone

Specific 2026-04-27 confirmation:

- `auto_loop.pid` pointed to launcher PID `1308`
- `auto_run.log` recorded `auto-loop started on PID 7372`
- the latest `GO` for `202604271506` was actually submitted successfully at
  `2026-04-27 17:38:30 JST`
- therefore the parent/child PID view was not the cause of that case

Follow-up candidate:

- refine PID discovery in `live_trigger_cli/runtime.py` and UI display in
  `live_trigger_cli/app.py` so the worker PID is preferred over the launcher PID
  when both command lines look like `auto-loop`

## 2026-04-20 Current Bet Line Direction

### Main Line

- `live_trigger_cli` is the current main bet line.
- `live_trigger` remains the shared logic owner and portable backup line.
- `live_trigger_fresh_exec` remains the fresh execution engine.

### Current Active Forward Set

- `125_broad_four_stadium`
- `4wind_base_415`
- `c2_provisional_v1`
- `h_a_final_day_cut_v1`
- `l3_weak_124_box_one_a_ex241_v1`
- `l1_weak_234_box_v1`

These six should now be treated as the current forward-running set in `live_trigger_cli`.

`125_suminoe_main` remains valid, but it is not part of the active set in the current runtime settings.

### Current Forward Tracking

- current daily report:
  - [README.md](./reports/live_trade/live_trigger_cli_forward_logic_performance_latest/README.md)
- refresh command:
  - `.\.venv\Scripts\python.exe workspace_codex\scripts\report_live_trigger_cli_forward_logic_performance.py`
- current cutoff:
  - `2026-04-19`
- current active-set snapshot:
  - `190` sample races
  - `18` hit races
  - race hit rate `9.47%`
  - flat ROI `70.77%`
- current leaders on the logic side:
  - `l3_124`: `51 races`, `17.65%` hit rate, flat ROI `110.71%`
  - `l1_234`: `62 races`, `9.68%` hit rate, flat ROI `96.26%`

### Active Set Notes

- `H-A`, `l3_124`, and `l1_234` are now active forward-test lines, not dormant candidates.
- older trio-only notes in this file are historical references from the `2026-03-24 .. 2026-03-26` state and should not be treated as the current operating read.

### Waiting Logic

Current main-line waiting policy:

- `assist_real`
  - send `GO`
  - open fresh confirmation
  - wait for Telegram approval or reject
  - submit only if approved in time
  - reject or deadline timeout discards the attempt
- `armed_real`
  - submit automatically
- `air`
  - evaluate and notify only

### Source-Of-Truth Reminder

- logic ownership remains in shared `live_trigger/boxes/`
- shared bet expansion remains in `live_trigger/auto_system/app/core/bets.py`
- execution-specific runtime state must not redefine logic truth

- updated_at: 2026-04-20 JST
- scope:
  - `C:\CODEX_WORK\boat_clone\live_trigger`
  - `C:\CODEX_WORK\boat_clone\live_trigger_cli`
  - `C:\CODEX_WORK\boat_clone\live_trigger_fresh_exec`
- purpose:
  - current bet-line status
  - waiting / execution policy
  - shared logic vs main CLI execution boundaries

## 2026-03-26 Recent Main-Line Changes

### C2 racer-index overlay

- `c2_provisional_v1` now reads the shared `racer_index_overlay` block from:
  - `live_trigger/boxes/c2/profiles/provisional_v1.json`
- current live rule:
  - if `pred1_lane = 1`, mark the race `filtered_out`
- this runs before `beforeinfo` confirmation
- target payload now keeps:
  - `racer_index_pred1_lane`
  - `racer_index_signal_date`
- purpose:
  - reduce contradiction cases where the strategy wants to fade lane1, but racer-index still places lane1 at `pred1`

### Monitoring window and stale beforeinfo handling

- main-line monitoring window now runs:
  - `deadline - 10 minutes`
  - through `deadline - 3 minutes`
- `beforeinfo` and `4wind odds2t` now refresh during the monitoring window when the cached file is stale
- purpose:
  - avoid holding an incomplete early HTML snapshot until the internal window closes

### CLI UI summary cleanup

- the top summary now separates:
  - `today targets`
  - `all targets`
- the overview tab also shows:
  - per-profile target counts for the current `race_date`

### Real-trade performance reporting

- `live_trigger_cli` real-trade performance can now be regenerated from:
  - `workspace_codex/scripts/report_live_trigger_cli_real_trade_performance.py`
- current forward-logic performance can now be regenerated from:
  - `workspace_codex/scripts/report_live_trigger_cli_forward_logic_performance.py`
- the report joins:
  - `live_trigger_cli/data/system.db`
  - canonical `results` in `C:\boat\data\silver\boat_race.duckdb`
- the generated report keeps:
  - `sample_races`
  - `race_hit_rate`
  - `avg_tickets_per_race`
  - `flat_stake / flat_return / flat_pnl / flat_roi`
  - `daily_logic_equity`
  - `logic_summary.csv`
  - `unsettled_sample_races`
- current output root:
  - `reports/live_trade/`

### Logic review note

- `H-A`, `l3_124`, and `l1_234` now sit inside the current live forward set through `live_trigger_cli/data/settings.json`
- the current point-in-time operational read should come from:
  - [README.md](./reports/live_trade/live_trigger_cli_forward_logic_performance_latest/README.md)
- older trio-only wording in this file should be read as historical context, not as the current active-set definition

## 2026-03-26 Loop Stability Read And Next Runtime Direction

### What Was Actually Going Wrong

- the visible `auto-loop` did not mainly fail because of bet execution
- the main cost sat in `sync_watchlists`
- `H-A` made this more visible because it is a broad-scan exacta branch and increased the number of candidate rows
- the practical symptom was:
  - the console looked frozen
  - cycle spacing drifted far beyond the nominal `poll_seconds=30`

### What Was Changed In The Current Main Line

- reduced repeated `racelist` fetch / parse work during sync
- added `sync / evaluate / execute` phase timing logs to `auto_run.log`
- added `sync_interval_seconds = 300`
- current main line now behaves as:
  - `evaluate / execute` every normal poll
  - `sync` only every few minutes

### Current Read

- the problem was primarily a loop-structure issue, not a raw PC-capacity issue
- `H-A` can be carried in the current line after the sync reduction
- but adding more broad-scan branches into the same combined loop will likely make the same pressure visible again

### Adopted Next Direction

- keep `live_trigger_cli` as the current protected main operating line
- do not mix the next broad-scan logic additions directly into the same combined loop by default
- prepare a separate next box where:
  - `live_trigger_cli_split/`
  - `sync_loop`
    - updates watchlists every `3-5` minutes
  - `bet_loop`
    - runs `evaluate + execute` every `30` seconds
- keep logic ownership and bet expansion shared:
  - `live_trigger/boxes/`
  - `live_trigger/auto_system/app/core/bets.py`

This means the runtime structure may split, while logic truth remains shared.

Current status:

- the first minimal scaffold now exists under `live_trigger_cli_split/`
- the current main line is still `live_trigger_cli`
- the split box is not promoted yet

## 0. 2026-03-21 時点のスナップショット

### 0-1. できるようになったこと

- 当日自動系は `締切 10 分前〜3 分前` の window driven で動作する
- `beforeinfo` は監視中に再取得するようになり、古いキャッシュ固定で `waiting_beforeinfo` のまま落ちる問題は緩和済み
- `GO -> intent_created -> air_bet_logged` と `target_skipped` の両方を実レースで確認済み
- `C2` の点数計算は `2-ALL-ALL = 20 点`、`3-ALL-ALL = 20 点` として扱い、合計金額も UI / DB 側で反映済み
- Teleboat 手動テスト導線を追加し、`桐生 12R / 1-2-5 + 2-ALL-ALL + 3-ALL-ALL` で確認画面までの到達を確認済み
- 確認画面の金額入力バグは修正済み
  - 修正前: `41 点 / 410,000 円`
  - 修正後: `41 点 / 4,100 円`
- 再起動時は `execution_mode=air` に戻す安全装置を追加済み

### 0-2. Teleboat 実投票系の現状

- 常駐ブラウザ方式を主経路に変更済み
- `Teleboat セッション準備` と `Teleboat ログイン確認` は別導線に整理済み
- resident browser のタブ整理を強化し、`トップ画面が生きていればそれを優先し、不要なログイン画面タブは閉じる` 方向へ改善済み
- セッション期限切れページ
  - `一定時間が経過したため、処理できませんでした。再度ログインして、操作をやり直してください。`
  を検知できる
- 期限切れ時は、即失敗ではなく `復旧 -> 自動再ログイン試行 -> それでもだめなら login_required` の流れへ寄せ始めている

### 0-3. まだ未完成な点

- Teleboat のログイン保持は不安定
  - `ログイン情報を保持する (7 日間有効)` は入力補助 cookie は残るが、実セッションは維持されないことがある
- resident browser は「トップ画面 1 タブ」に収束させる方向へ改善したが、完全自動で毎回安定とはまだ言えない
- `Assist Real` / `Armed Real` の本流で、セッション切れからの自動復旧が十分かは継続確認が必要
- `Auto Bet Control` UI と `auto_run.py` は再起動時の挙動を都度確認する必要がある

### 0-4. 現時点の判断

- `Air Bet` の当日運用基盤は、かなり実戦投入できる状態
- ただし `Real Bet` は、まだ「常駐セッション安定化」と「再ログイン自動化の詰め」が必要
- 実運用へ上げる前に、最低でも次は再確認したい
  - セッション切れ時の自動復旧
  - `金額入力 -> 投票用パスワード入力 -> 確認画面 -> 資金不足` の一連動作
  - resident browser が複数タブになった時の自動収束

## 1. 現在の到達点

### 1-1. trigger フォルダの状態

`live_trigger/` は単一持ち運びフォルダとして再構成済み。

- `app.py`
  - 予定ボード
  - 翌日候補抽出
  - 直前判定
  - Air Bet
  - 成績管理
- `runtime/boat_race_data/`
  - trigger engine を vendor 済み
- `auto_system/`
  - 自動運用 UI
  - 自動ループ
  - SQLite 管理
- `boxes/`
  - ロジック profile の正本
- `plans/`
  - 月間管理、前日管理の出力
- `watchlists/`
  - 翌日候補抽出の出力
- `ready/`
  - 当日直前判定の出力
- `raw/`
  - trigger 側のキャッシュ
- `air_bet_log.csv`
  - Air Bet 履歴

### 1-2. UI の状態

`trigger_A` / `trigger_B` は廃止済み。
現在は watchlist に含まれる採用ロジック名をそのまま表示する。

直前判定タブの Air Bet 設定は次の最小構成に整理済み。

- ロジックごとの ON/OFF
- ロジックごとの金額

削除済み項目:

- 損失上限
- 自動配分

### 1-3. データ補完の別系統ジョブ

2026-03-19 19:20 JST 前後に、`boat_a` / `boat_b` で odds 欠損補完ジョブを開始済み。

- `boat_a`
  - `2025-06-08 .. 2025-09-08`
- `boat_b`
  - `2025-09-09 .. 2025-12-10`

このジョブは bet システムとは別系統で進行中。

## 2. 現在の auto_system の評価

### 2-1. 現在の構成

- `01_sync_watchlists.py`
  - 当日分の `watchlist` を DB に取り込む
- `02_evaluate_targets.py`
  - 締切 10 分前から 3 分前で状態確認し、`BetIntent` を作る
- `03_execute_air_bets.py`
  - `execution_mode` に応じて `air / assist_real / armed_real` を処理する

### 2-2. 未完成な点

- 実ベットの画面遷移は未実装
- session 管理が未設計
- 契約番号の保存がない
- 確認画面保存がない
- 実投票とローカル記録の突合がない
- 失敗時の再送・重複防止が弱い

### 2-3. DB 上の大きな問題

現行の `BetHistory.target_race_id` は `unique` なので、1レース1レコードしか持てない。
これは複数点買いロジックと衝突する。

例:

- `c2_provisional_v1` は複数ベットを返す
- 現DBのままだと 1 レース複数組番を正しく保存できない

このため、実ベット完成前に DB の再設計が必要。

## 3. テレボート前提の整理

2026-03-19 時点で、公式確認から次を前提にする。

### 3-1. PC版ログイン

PC版ログイン画面は次を要求する。

- 加入者番号
- 暗証番号
- 認証用パスワード

さらに:

- ログイン情報保持は 7 日間有効
- reCAPTCHA がある

したがって、毎回の完全自動ログイン前提より、
`ログイン済みセッションを維持する構造` の方が現実的。

### 3-2. ネット投票の運用上の前提

スマホ版操作マニュアルから見える運用前提:

- 投票前に入金が必要
- 残高は夜間に自動精算される
- 1 日の契約件数は最大 500 件
- 1 日の取引件数は最大 9,999 ベット
- ログイン情報は他人に知られないよう管理が必要

### 3-3. スマホ版 / アプリ限定機能

2023-02-13 の公式案内では、次はスマホ版 / アプリ限定。

- 投票照会時間の延長
- 翌日レース情報の表示

つまり、前日管理・翌日情報の整備は、こちらのローカル trigger 基盤で持つ判断が正しい。

### 3-4. 銀行・精算まわり

2025-04-21 の公式案内では:

- 前日発売の開始時刻は開催により異なる
- 一括最終精算は概ね 24 時以降
- 銀行メンテ情報の確認が必要

したがって、完成形でも次は避けるべき。

- 自動入金まで一気にやる
- 自動精算までローカル制御しようとする

まずは:

- 残高不足なら停止
- 銀行メンテなら停止
- 実ベットは session が正常な時だけ進める

この方針が安全。

## 4. 自動ベットの完成形イメージ

### 4-1. 基本方針

完成形は「無人フル自動」ではなく、
まずは「半自動実ベット」を正解とする。

第一段階:

- trigger が `BetIntent` を作る
- Teleboat 画面にベット内容を投入する
- 最終確認は人が行う

第二段階:

- 当日 session が生きている
- 事前 arm 済み
- 条件一致時のみ自動確定

この順が現実的。

### 4-2. 推奨レイヤ構成

#### A. Trigger Layer

役割:

- 月間管理
- 前日管理
- 当日管理
- ready 生成

出力:

- `plans/`
- `watchlists/`
- `ready/`
- `air_bet_log.csv`

#### B. Bet Intent Layer

役割:

- `trigger_ready` を実ベット用の intent に変換
- 1 レース 1 ロジックを、複数 ticket に展開
- 重複実行を防ぐ一意キーを付与

最低限持つべき項目:

- race_date
- stadium_code
- race_no
- logic_name
- bet_type
- combo
- amount
- source_ready_file
- intent_key
- status

#### C. Teleboat Session Layer

役割:

- Playwright の persistent profile を使う
- ログイン済み session を流用
- session 失効時は停止
- reCAPTCHA や再認証が必要なら人へ戻す

ここでは `毎回ログインし直す設計` を採らない。

#### D. Bet Execution Layer

役割:

- 対象レースを開く
- 勝式、組番、金額を入力
- 確認画面まで進む
- Assist Real では停止
- Armed Real では最終送信

#### E. Reconcile Layer

役割:

- 契約番号を保存
- 実行時刻を保存
- スクリーンショット保存
- テレボートの投票照会とローカル記録を照合
- 不一致を検出したら再送せずアラート

## 5. DB 再設計案

### 5-1. いまの `TargetRace` は残してよい

ただし、その下に `BetIntent` と `BetExecution` を分ける。

### 5-2. 推奨テーブル

#### `target_races`

- 1 レース x 1 ロジック
- 候補レース管理

#### `bet_intents`

- 1 組番 x 1 金額
- 実行前のベット単位
- `target_race_id` は非 unique

#### `bet_executions`

- 送信結果
- contract_no
- execution_status
- executed_at
- screenshot_path
- error_message

#### `session_events`

- session alive
- session expired
- captcha required
- manual re-login required

## 6. 実装順

### 実装済み

- DB 再設計
- `watchlist` 同期
- `BetIntent` 生成
- Playwright persistent context 化
- Teleboat ログイン入口対応
- `assist_real` / `armed_real` の実行器追加
- 契約番号、スクリーンショット、session event 記録の土台追加

### 残作業

- Teleboat ログイン後画面の実機確認
- 投票照会との突合
- 実運用時の例外分岐調整

### Phase 4

- Assist Real 運用
- その後に Armed Real を追加

## 7. 今はやらない方がいいこと

- 毎回 headless でログインから完全自動実行
- 自動入金 / 自動精算まで同時に仕上げる
- secrets を repo 内に固定保存する
- 実投票前に照合・証跡なしで送信する

## 8. 直近の次アクション

次に着手するなら、順番はこれ。

1. `auto_system` の DB を再設計する
2. `BetIntent` ベースに executor を作り直す
3. Teleboat 画面の「確認画面まで」を実装する
4. Assist Real で 1 レース実地確認する

## 9. 参考リンク

- PC版ログイン
  - https://ib.mbrace.or.jp/
- PC版ログイン画面の確認事項
  - 加入者番号、暗証番号、認証用パスワード、7日保持、reCAPTCHA
- スマホ版 / アプリ限定の照会時間延長・翌日情報表示
  - https://www.boatrace.jp/owpc/pc/site/news/2023/02/25713/
- 前日発売開始時間・一括最終精算・銀行メンテ参照
  - https://www.boatrace.jp/owpc/pc/site/news/2025/04/36828/
- 即時対応銀行メンテ情報
  - https://www.boatrace.jp/extent/pc/bankinfo/
- 入金限度額の照会・変更
  - https://register.mbrace.or.jp/kyotei/member/nyukinsetlogin
- スマホ版操作マニュアル
  - https://www.boatrace.jp/extent/pc/new_ib/image/manual_all.pdf
