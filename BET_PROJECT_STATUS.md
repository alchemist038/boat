# Bet Project Status

- updated_at: 2026-03-19 19:30 JST
- scope: `C:\CODEX_WORK\boat_clone\live_trigger`
- purpose: trigger 現状整理と、自動ベット完成に向けた次構造の整理

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

### 2-1. 良い点

- `01_pre_scheduler.py`
  - 全場スキャンして target 候補を作る流れはある
- `02_just_in_time.py`
  - 当日直前判定して GO / SKIP を残す流れはある
- `03_executor.py`
  - Playwright で実ベット実行層を置く方向性はある

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

### Phase 1

- DB 再設計
- `02_just_in_time.py` を `BetIntent` 出力に変更
- `03_executor.py` を intent 消化型に変更

### Phase 2

- Playwright persistent context 化
- Teleboat のレース遷移、勝式入力、金額入力の実装
- 確認画面停止まで実装

### Phase 3

- 契約番号保存
- スクリーンショット保存
- 投票照会との突合

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
