# TO INS14 FROM ME

`ins14` 側で確認してほしい最新共有メモです。

## 状況

- machine: ins14
- from: i5
- status: active
- updated_at: 2026-03-15 06:30:00 +09:00
- priority: high

## 今回の要点

- `main` に live trigger 基盤を反映済み
- `125` と `c2` は BOX として分離済み
- Streamlit アプリを追加済み
- `i5` 側の odds backfill は 2 worker で継続中

## main に入ったもの

- `live_trigger/app.py`
- `live_trigger/run_app.cmd`
- `live_trigger/README.md`
- `live_trigger/boxes/125/...`
- `live_trigger/boxes/c2/...`
- `src/boat_race_data/live_trigger.py`
- `src/boat_race_data/logic_board.py`
- `src/boat_race_data/schedule_planner.py`

## ins14 側での確認手順

1. `git pull --ff-only origin main`
2. `C:\CODEX_WORK\boat_clone\live_trigger\run_app.cmd`
3. アプリで次を確認
   - `予定ボード`
   - `翌日候補抽出`
   - `直前判定`

## backfill 進捗

- `boat_a`
  - range: `2025-04-01..2025-09-30`
  - completed through: `2025-04-29`
  - now collecting: `2025-04-30`
- `boat_b`
  - range: `2025-10-01..2026-03-05`
  - completed through: `2025-10-31`
  - now collecting: `2025-11-01`

## backfill 完了予測

- checked_at: `2026-03-15 06:30 +09:00`
- `boat_a`
  - rough ETA: `2026-03-19 04:45 +09:00`
- `boat_b`
  - rough ETA: `2026-03-18 04:12 +09:00`

## 注意

- `racer_stats_term/*.csv` が無いため DuckDB refresh は毎回失敗
- ただし raw / bronze の収集自体は継続中
- 完了予測は 2026-03-15 朝時点の直近ペースからの概算

## 返答先

- `FROM_INS14_TO_ME.md`
