# Fresh Execution Flow

## 目的

- `air` は常時動かす
- `GO` のときだけ fresh executor を起動する
- ログイン後に安定したトップページ 1 枚へ収束させる
- 実投票の処理後はログアウトして閉じる
- 次の real target が近いときだけ短時間再利用する

## shared contract

- `fresh_exec` は strategy BOX を持たない
- runtime BOX は `live_trigger/boxes/` のみを使う
- bet 展開は `live_trigger/auto_system/app/core/bets.py` を共有する
- ownership rule は [PROJECT_RULES.md](/c:/CODEX_WORK/boat_clone/live_trigger/PROJECT_RULES.md) を参照する

## フロー

1. `air` は fresh ライン上で常時監視する
2. 対象が `GO` になる
3. fresh executor が専用 browser を起動する
4. ログインして stable な top page を待つ
5. 余分ページを閉じ、top 1 枚へ収束させる
6. 場とレースを選び、bet list を作る
7. `assist_real` は確認画面で購入金額と投票パスを入れて止まる
8. `armed_real` はそのまま送信する
9. 実行後はログアウトし、browser を閉じる
10. 次の real target が近い場合だけ短時間再利用する

## このモデルを使う理由

- resident browser の stale 状態を引きずりにくい
- timeout page や古い tab を掴む事故を減らせる
- 1 回ごとの real execution を disposable にできる
- `air` 監視と Teleboat session を切り離せる

## 実装メモ

- fresh ラインは独自の `settings.json`、`system.db`、`auto_run.py`、Streamlit UI を持つ
- `watchlists/raw/boxes` は `live_trigger/` から読む
- local BOX copy は作らない
- `trigger` が watchlist を作成し、fresh がその当日分を取り込んで判定する

## 現状メモ

- 2026-03-21 時点で `sync -> evaluate -> execute` ループは動作確認済み
- `1-2-5` と `2-ALL-ALL` の確認画面到達を手動 Fresh テストで確認済み
- テスト後の logout popup 追従とログイン画面復帰確認まで実装済み
