# TO INS14 FROM ME

`ins14` の Codex は、まずこのファイルだけ読んでください。

## 状態

- machine: ins14
- from: me
- status: active
- updated_at: 2026-03-14 22:56:00 +09:00
- priority: high

## 今回の依頼

- `i5` 側の odds backfill 進捗を確認してください
- `125` の次段として検討中の `logic box / schedule / trigger` 構想を把握してください
- 必要なら `ins14` 側で受けたい運用イメージを `FROM_INS14_TO_ME.md` に返してください

## 参考情報

- files:
  - `FROM_I5_TO_ME.md`
  - `reports/strategies/125/review_20260314.md`
  - `reports/strategies/125/summary_20260314.md`
- commands:
  - `git pull --ff-only origin main`
- constraints:
  - `Z:\boat` は参照のみ
  - `i5` は `C:\CODEX_WORK\boat_a` と `C:\CODEX_WORK\boat_b` で収集継続中
- output target:
  - 必要なら `FROM_INS14_TO_ME.md`

## 進捗メモ

- `i5` では odds backfill を 2 worker で開始済み
- `boat_a`: `2025-04-01..2025-09-30`
- `boat_b`: `2025-10-01..2026-03-05`
- 2026-03-14 22:56 時点でも両 worker の python process は生存
- ログ上では `racer_stats_term/*.csv` 不在に伴う DuckDB refresh の warning/exception が見えるが、その後も日次収集ログは前進している
- 現在の進捗目視:
  - `boat_a` は `2025-04-15` 完了後、`2025-04-16` を収集中
  - `boat_b` は `2025-10-16` 完了後、`2025-10-17` を収集中
- `125` の考察は `reports/strategies/125/review_20260314.md` に整理済み
- 現時点の要旨は「125 は見込みゼロではないが、全場共通より場別・条件別・合算運用で見るべき」「住之江の `低格1号艇 + 展示良` 仮説が比較的筋が良い」「常滑はまだ解釈が不安定」
- 次段の構想:
  - 前日夜に翌日候補を仕込む trigger
  - 当日直前に `beforeinfo` で最終判定する trigger
  - 2週先から1か月先の開催予定を見て資金計画に使う schedule view
  - ロジックを `box` として追加できる構成にしたい

## Codex の動き

1. `git pull` を確認する
2. `FROM_I5_TO_ME.md` と `125` 関連レポートを確認する
3. 必要なら `FROM_INS14_TO_ME.md` に所見を書く
4. 完了または中断時に `FROM_INS14_TO_ME.md` を更新する
