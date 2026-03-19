# Air Bet 監査運用手順書

## この手順書の対象

この手順書は、`Auto Bet Control` を `execution_mode=air` で運用する場合のものです。

現在の `auto_system` は次の 3 モードを持っています。

- `air`
  - 実ベットせず、Air Bet 実行時刻だけを監査する
- `assist_real`
  - 確認画面まで自動で進み、最後は人が送信する
- `armed_real`
  - Teleboat へ自動送信する

この MD では **`air` モードだけ** を扱います。  
実ベットの運用は [AUTO_BET_SYSTEM_RUNBOOK.md](/c:/CODEX_WORK/boat_clone/live_trigger/AUTO_BET_SYSTEM_RUNBOOK.md) を見てください。

## 目的

Air Bet 監査で確認したいのは次の 3 点です。

- 締切 10 分前から 5 分前の監視ウィンドウで動いていたか
- その時間帯に状態確認を行えたか
- `Air Bet` を何時に記録したか

監査の正本は `system.db` の `air_bet_audits` テーブルです。

## 主なファイル

- 前日準備 UI  
  `C:\CODEX_WORK\boat_clone\live_trigger\run_app_ui.cmd`
- 当日監査 UI  
  `C:\CODEX_WORK\boat_clone\live_trigger\run_auto_ui.cmd`
- 1 サイクルだけ手動実行  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\run_system.bat`
- 監査 DB  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\system.db`
- 自動ループのログ  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\auto_run.log`
- 前日作成される候補ファイル  
  `C:\CODEX_WORK\boat_clone\live_trigger\watchlists\`

## 前日の作業

### 目的

翌日の `watchlist` を作成します。

### 手順

1. 前日準備 UI を起動します。

```bat
C:\CODEX_WORK\boat_clone\live_trigger\run_app_ui.cmd
```

2. `翌日候補抽出` タブを開きます。
3. `対象日` に翌日の開催日を入れます。
4. `使う profile` を選びます。
5. `候補を抽出` を押します。
6. `watchlists` 配下に CSV ができたことを確認します。

### 前日チェック

- `watchlists` に CSV がある
- 対象日が正しい
- 使いたい profile が入っている

## 当日の作業

### 目的

`air` モードで監査ループを動かし、正しい時間帯に `Air Bet` が記録されたことを確認します。

### 手順

1. 当日監査 UI を起動します。

```bat
C:\CODEX_WORK\boat_clone\live_trigger\run_auto_ui.cmd
```

2. サイドバーで次を確認します。

- `実行モード` = `Air Bet 監査`
- `ポーリング秒数`
- `監視開始(締切何分前)`  
  通常は `10`
- `監視終了(締切何分前)`  
  通常は `5`
- `既定金額`
- 各 profile の ON/OFF
- 各 profile の金額

3. `設定を保存` を押します。
4. `システム起動` を押します。
5. 動作中の表示になったことを確認します。

### 1 サイクルだけ動かしたい場合

常時ループではなく 1 回だけ実行したい場合は、次のどちらかを使います。

- UI の `1サイクルだけ実行`
- 手動実行

```bat
C:\CODEX_WORK\boat_clone\live_trigger\auto_system\run_system.bat
```

## 当日に自動で行われること

1 サイクルごとに、次の処理が順番に走ります。

1. `01_sync_watchlists.py`  
   当日分の `watchlist` を DB に取り込みます。
2. `02_evaluate_targets.py`  
   締切 10 分前から 5 分前のレースだけを監視し、状態確認を行います。
3. `03_execute_air_bets.py`  
   `GO` になったものだけ `Air Bet` の実行時刻を記録します。

## 当日に確認する画面

### 1. `当日対象`

ここでは、当日レースの状態遷移を確認します。

- 取り込み済みか
- 監視中に入ったか
- `intent_created` まで進んだか
- `air_bet_logged` まで進んだか

### 2. `Air Bet監査ログ`

この画面が一番重要です。  
ここで `Air Bet` が何時に記録されたかを確認します。

主に見る項目は次です。

- `Air Bet時刻`
- `締切何秒前`
- profile
- combo
- amount
- status

### 3. `ベット実行ログ`

`air` モードでも `bet_executions` には実行ログが残ります。  
ここでは `mode=air` の行と `実行時刻`、`締切何秒前` を確認します。

### 4. `イベント`

処理の流れを時系列で確認できます。

- watchlist 取り込み
- 監視開始
- 状態確認待ち
- GO 判定
- Air Bet 記録
- 期限切れ

## 正常系の見え方

正常に動いたときの代表的な流れは次です。

1. `imported`
2. `monitoring`
3. `intent_created`
4. `air_bet_logged`

正常動作と判断するポイントは次です。

- `Air Bet監査ログ` に行が出る
- `Air Bet時刻` が入っている
- `締切何秒前` が概ね `300` から `600` の範囲に入っている

## ステータスの意味

- `imported`  
  当日分の watchlist 行が DB に入った状態
- `monitoring`  
  当日監視ウィンドウに入った状態
- `checked_waiting`  
  状態確認のための情報がまだ揃っていない状態
- `checked_skip`  
  条件不一致で見送りになった状態
- `intent_created`  
  Air Bet 候補が作られた状態
- `air_bet_logged`  
  Air Bet 実行時刻の記録が完了した状態
- `expired`  
  監視可能な時間帯を過ぎた状態

## 停止手順

通常停止は、当日監査 UI で `システム停止` を押します。

## 異常時の確認先

挙動がおかしいときは、次を確認します。

- `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\auto_run.log`
- `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\system.db`
- `watchlist` の日付が正しいか
- 対象レースがすでに監視ウィンドウ外になっていないか

## 監査の正本

監査の正本は次です。

- DB: `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\system.db`
- 主要テーブル: `air_bet_audits`

このテーブルに `Air Bet` の実行時刻が残っていれば、当日システムが所定のタイミングで稼働した証跡になります。
