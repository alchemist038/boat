# Live Trigger

前日候補抽出と当日直前判定を行うための trigger 基盤です。

目的:

- 前日に翌日の候補レースを抽出する
- 当日に `beforeinfo` を取り直して直前判定する
- 通知そのものは後で足せるように、まず `trigger_ready` までを作る

## 構成

- `boxes/`
  - `125/`, `c2/` のように logic/project ごとに分離する
  - 各 box の `profiles/*.json` に trigger 条件を書く
  - box を追加すると logic board と batch watchlist に載る
- `watchlists/`
  - 前日抽出の CSV 出力
- `ready/`
  - 直前判定で `trigger_ready` になった CSV 出力
- `plans/`
  - 2週間から1か月先の予定表示
  - logic board の Markdown / HTML 出力

## ルール

- `125` と `c2` は別 BOX として管理する
- batch watchlist は `enabled: true` の profile だけ使う
- logic board は無効 profile も一覧表示して、待機中ロジックを見える化する
- `template` は雛形であり、実際の読み込み対象からは外す

## 主な CLI

- `build-watchlist`
  - 単一 profile で前日候補抽出
- `build-watchlist-batch`
  - `boxes/` 配下の有効 profile をまとめて前日候補抽出
- `resolve-watchlist`
  - 単一 profile で `beforeinfo` を見て直前判定
- `resolve-watchlist-batch`
  - batch watchlist を profile ごとに直前判定
- `build-schedule-window`
  - 2週間から1か月先の開催予定を出力
- `build-logic-board`
  - BOX 一覧とカレンダーをまとめて出力
