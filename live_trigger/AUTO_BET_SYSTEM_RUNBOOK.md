# Auto Bet System 運用手順書

## 目的

`live_trigger/auto_system` を使って、当日の締切 10 分前から 5 分前に状態確認を行い、`Air Bet` 監査または実ベットを実行するための手順書です。

前日までは `watchlist` を作り、当日は `auto_system` が次を行います。

- `watchlist` を DB に取り込む
- 締切 10 分前から 5 分前だけ状態確認する
- `GO` のときだけ `BetIntent` を作る
- `execution_mode` に応じて Air Bet または実ベットを実行する

## 実行モード

重要:

- `run_auto_ui.cmd` と `run_auto_cycle.cmd` で起動した直後は、安全のため `execution_mode` を必ず `air` に戻します
- `assist_real` / `armed_real` を使う場合は、UI でモードを選んだあと **`設定を保存`** を押したときだけ切り替わります
- つまり、再起動直後に前回の実ベットモードがそのまま復活しないようにしています

### `air`

- 実ベットしません
- Air Bet 実行時刻を監査します
- 新しい profile の初期運用に向いています

### `assist_real`

- 確認画面まで自動で進みます
- 最後の送信は人が行います
- 本番導入前の実機確認に向いています

### `armed_real`

- Teleboat へ自動送信します
- 一番強いモードです
- `assist_real` の確認後にのみ使う前提です

## 主なファイル

- 前日準備 UI  
  `C:\CODEX_WORK\boat_clone\live_trigger\run_app_ui.cmd`
- 当日運用 UI  
  `C:\CODEX_WORK\boat_clone\live_trigger\run_auto_ui.cmd`
- 1 サイクルだけ手動実行  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\run_system.bat`
- 当日設定  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\settings.json`
- 当日 DB  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\system.db`
- 自動ループログ  
  `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\auto_run.log`
- Teleboat 環境変数ひな形  
  `C:\CODEX_WORK\boat_clone\live_trigger\.env.example`

## 事前準備

### 1. 環境変数を用意する

`assist_real` または `armed_real` を使う場合は、`live_trigger` 直下に `.env` を作成します。

```env
TELEBOAT_SUBSCRIBER_NO=
TELEBOAT_PIN=
TELEBOAT_PASSWORD=
TELEBOAT_VOTE_PASSWORD=
```

補足:

- `TELEBOAT_PASSWORD` は認証用パスワードです
- `TELEBOAT_VOTE_PASSWORD` は投票用パスワードです
- `armed_real` では `TELEBOAT_VOTE_PASSWORD` が必須です

### 2. Playwright の保存先を確認する

既定では次を使います。

`C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\playwright_user_data`

ここに Teleboat の persistent profile が保存されます。

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
6. `watchlists` に CSV ができたことを確認します。

## 当日の開始前

### 推奨の進め方

1. 新しい profile はまず `air`
2. 次に `assist_real`
3. 問題がないことを確認したら `armed_real`

### 当日 UI を起動する

```bat
C:\CODEX_WORK\boat_clone\live_trigger\run_auto_ui.cmd
```

## 当日の設定

サイドバーで次を設定します。

- `実行モード`
- `ポーリング秒数`
- `監視開始(締切何分前)`  
  通常は `10`
- `監視終了(締切何分前)`  
  通常は `5`
- `既定金額`
- 各 profile の ON/OFF
- 各 profile の金額

`assist_real` / `armed_real` のときは追加で次を確認します。

- `Playwright を headless で起動する`
- `常駐ブラウザを使う`
- `常駐ブラウザのデバッグポート`
- `Teleboat user data dir`
- `手動確認待ち秒数`
- `ログイン待ち秒数`

設定後は `設定を保存` を押します。

## 当日の運用

### 常時ループで運用する場合

1. `システム起動` を押します
2. `当日対象` で状態を確認します
3. 必要に応じて `ベット実行ログ` と `Session` を確認します

### 1 サイクルだけ実行する場合

- UI の `1サイクルだけ実行`

または:

```bat
C:\CODEX_WORK\boat_clone\live_trigger\auto_system\run_system.bat
```

## モードごとの動き

### `air`

- `GO` の intent に対して Air Bet 実行時刻を記録します
- `air_bet_audits` に証跡が残ります
- 実送信は行いません

### `assist_real`

- Teleboat にログインします
- 対象場・対象レースへ進みます
- bet list と確認画面まで進みます
- 人が送信したあと、結果画面を検知できた場合は `submitted` として記録します
- タイムアウトした場合は `assist_timeout` になります

### `armed_real`

- Teleboat にログインします
- 対象場・対象レースへ進みます
- bet list と確認画面へ進みます
- 投票用パスワードを入れて自動送信します
- 成功時は `bet_executions` に `submitted` が残ります

## Teleboat 常駐セッション運用

### 現在の仕様

- Teleboat は `storage_state` の再利用より、常駐ブラウザ方式を優先します
- `Teleboat セッション準備` を押すと、`Google Chrome for Testing` を Teleboat 用の常駐ブラウザとして起動または再接続します
- `assist_real` / `armed_real` は、この常駐ブラウザの同じセッションを使って動作します

### 運用ルール

- Teleboat 用の常駐ブラウザは **1ウィンドウ / 1タブ** を基本にします
- ログイン後にログイン画面タブが残っていたら閉じて、**トップ画面だけ残す** ようにします
- 自動操作前に `Teleboat ログイン確認` を行い、`verified` を確認します
- Teleboat 用の常駐ブラウザは、他の用途に使わない前提です

### 補足

- 現時点では、ログイン後に古いログイン画面タブが残ることがあります
- このため、運用上は「トップ画面だけ残す」を仕様とします
- 将来的には、ログイン後の不要タブ整理をさらに自動化する余地があります

## 当日に見る画面

### 1. `当日対象`

ここでは、当日レースの状態遷移を見ます。

- `imported`
- `monitoring`
- `intent_created`
- `air_bet_logged`
- `real_bet_placed`

### 2. `ベット実行ログ`

ここで実行結果を確認します。

主に見る項目:

- `mode`
- `状態`
- `実行時刻`
- `締切何秒前`
- `契約番号`
- `スクリーンショット`
- `error`

### 3. `Air Bet監査ログ`

`air` モードのときに見ます。

### 4. `イベント`

処理の時系列を見ます。

### 5. `Session`

Teleboat セッションに関する記録を見ます。

- ログイン成功
- 実行失敗
- 環境変数不足

## 正常系の見え方

### `air`

1. `intent_created`
2. `air_bet_logged`

### `assist_real`

1. `intent_created`
2. 確認画面に到達
3. 手動送信後に `ベット実行ログ` へ `submitted`

### `armed_real`

1. `intent_created`
2. 自動送信
3. `ベット実行ログ` へ `submitted`

## 停止手順

通常停止は UI の `システム停止` を押します。

## 異常時の確認先

- `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\auto_run.log`
- `C:\CODEX_WORK\boat_clone\live_trigger\auto_system\data\system.db`
- `Session` タブ
- `ベット実行ログ` の `error`
- `Teleboat user data dir` が正しいか
- `.env` が正しいか

## 注意点

- `armed_real` は実送信します
- `assist_real` は headless を使わない方が確認しやすいです
- 最初の実機確認は `assist_real` を推奨します
- Teleboat 常駐ブラウザは、ログイン後トップ画面だけ残すのが安全です
- ログイン後画面の変更があった場合は `teleboat_screenshots` と `teleboat_html` を確認してください

## 毎日の最小運用

### 前日

1. `run_app_ui.cmd` を開く
2. `翌日候補抽出` で翌日の watchlist を作る
3. `watchlists` に CSV ができたことを確認する

### 当日

1. `run_auto_ui.cmd` を開く
2. `実行モード` を選ぶ
3. 監視開始、監視終了、profile、金額を確認する
4. `設定を保存` を押す
5. `システム起動` を押す
6. `当日対象` と `ベット実行ログ` を確認する
7. 終了後に `システム停止` を押す
