# TO INS14 FROM ME

`ins14` の Codex は、まずこのファイルだけ読んでください。

## 状態

- machine: ins14
- from: me
- status: active
- updated_at: 2026-03-14 17:31:00 +09:00
- priority: medium

## 今回の依頼

- `i5` 側の long-run odds backfill 進捗を確認してください
- `i5` 側の `125` 考察メモを読んで、今後の検討方針の材料として受け取ってください

## 参考情報

- files:
  - `FROM_I5_TO_ME.md`
  - `reports/125line_review_20260314.md`
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
- 2026-03-14 17:30 時点で両 worker の python process は生存
- ログ上では `racer_stats_term/*.csv` 不在に伴う DuckDB refresh の warning/exception が見えるが、その後も日次収集ログは前進している
- `125` の考察は `reports/125line_review_20260314.md` に整理済み
- 現時点の要旨は「125 は見込みゼロではないが、全場共通より場別・条件別・合算運用で見るべき」「住之江の `低格1号艇 + 展示良` 仮説が比較的筋が良い」「常滑はまだ解釈が不安定」

## Codex の動き

1. `git pull` を確認する
2. `FROM_I5_TO_ME.md` と `reports/125line_review_20260314.md` を確認する
3. 必要なら `FROM_INS14_TO_ME.md` に所見を書く
4. 完了または中断時に `FROM_INS14_TO_ME.md` を更新する
