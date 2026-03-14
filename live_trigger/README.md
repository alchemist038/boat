# Live Trigger

前日候補抽出と当日直前判定を、既存の収集基盤とは分離して扱うための作業フォルダです。

## 目的

- 前日に翌日の候補レースを抽出する
- 候補レースだけを当日 `beforeinfo` で再確認する
- 通知そのものは後回しにして、まず `trigger_ready` まで作る

## 構成

- `profiles/`
  - 事前条件と直前条件の定義
  - `*.json` を追加すると logic box の対象として自動読込される
- `watchlists/`
  - 前日抽出結果の出力先
- `ready/`
  - 直前条件通過結果の出力先
- `plans/`
  - 2週先から1か月先の予定確認用 CSV / Markdown / HTML 出力先

## 直近の対象

まずは `125` の住之江向けプロファイルから着手する。

## 追加された CLI

- `build-watchlist-batch`
  - `profiles/` 内の enabled profile をまとめて watchlist 化
- `resolve-watchlist-batch`
  - batch watchlist を profile ごとに最終判定
- `build-logic-board`
  - profile を logic box として読み込み、予定カレンダーに重ねて表示
