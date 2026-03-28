# boat-race-data

## Documentation Entry Points

- Root index: [ROOT_DOC_MAP.md](./ROOT_DOC_MAP.md)
- Startup checklist: [CODEX_START_HERE.md](./CODEX_START_HERE.md)
- High-level project status: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- Bet / trigger status: [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- Shared DB status: [DB_STATUS.md](./DB_STATUS.md)
- Risk-scaling concept: [R_CONCEPT.md](./R_CONCEPT.md)

BOAT RACE公式サイトを主軸にした、`raw -> bronze -> silver` の収集基盤です。目的は予想ロジックではなく、後から統計分析・バックテスト・期待値計算に回せる再取得可能なデータを作ることです。

## 対象データ

- 公式ダウンロードのレーサー期別成績
- 現行の出走表
- 2連単/2連複オッズ
- 3連単オッズ
- 結果ページ

## ディレクトリ

- `data/raw`: 生HTML、LZH、展開後TXT
- `data/bronze`: 抽出済みCSV
- `data/silver`: DuckDB
- `reports/data_quality`: 品質レポート
- `src`: 実装
- `tests`: 最低限のテスト

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

`期別成績` は公式配布が `.lzh` なので、展開には `tar` が必要です。Windows 11 標準の `bsdtar` を前提にしています。

## 実行

まずは過去日の1場だけで動作確認するのが安全です。例として **2026年3月6日** の桐生 (`01`) を取得します。

```powershell
.\.venv\Scripts\python -m boat_race_data collect-day --date 20260306 --stadiums 01
```

開催場を自動判定したい場合は `--stadiums` を省略します。

```powershell
.\.venv\Scripts\python -m boat_race_data collect-day --date 20260306
```

## 出力

実行後に少なくとも次ができます。

- `data/raw/...` にHTML/LZH/TXTが保存される
- `data/bronze/...` に `races`, `entries`, `odds_2t`, `odds_3t`, `results`, `racer_stats_term` のCSVが保存される
- `data/silver/boat_race.duckdb` に同名テーブルが作られる
- `reports/data_quality/YYYYMMDD.md` に品質レポートが出る
- オッズ表の `欠場` は `odds_status` として残る

## 確認用SQL

DuckDBでテーブル件数を確認:

```sql
SELECT
  (SELECT COUNT(*) FROM races) AS races,
  (SELECT COUNT(*) FROM entries) AS entries,
  (SELECT COUNT(*) FROM odds_2t) AS odds_2t,
  (SELECT COUNT(*) FROM odds_3t) AS odds_3t,
  (SELECT COUNT(*) FROM results) AS results,
  (SELECT COUNT(*) FROM racer_stats_term) AS racer_stats_term;
```

`race_id` で結合できることを確認:

```sql
SELECT
  e.race_id,
  e.lane,
  e.racer_name,
  r.first_place_lane,
  r.trifecta_combo,
  r.trifecta_payout
FROM entries e
JOIN results r USING (race_id)
ORDER BY e.race_id, e.lane
LIMIT 12;
```

出走表とオッズを合わせて確認:

```sql
SELECT
  e.race_id,
  e.lane,
  e.racer_name,
  o.bet_type,
  o.first_lane,
  o.second_lane,
  o.odds
FROM entries e
JOIN odds_2t o USING (race_id)
WHERE e.lane = o.first_lane
ORDER BY e.race_id, o.bet_type, o.odds
LIMIT 20;
```

## 品質チェック

レポートでは次を見ます。

- `races` の `race_id` 重複
- 1レース6艇でない `entries`
- `results` だけあって `entries` が無いケース
- `odds_2t` の 30/15 件不足
- `odds_3t` の 120 件不足
## Range Collection Notes

Use `collect-range` for longer runs. By default it collects:

- `racelist`
- `odds_2t`
- `odds_3t`
- `beforeinfo`
- `results`

For safety, `collect-range` enforces a minimum effective sleep of `0.5` seconds even if a smaller value is passed.

For recent odds collection, assume roughly `40 minutes per day` as a working estimate when collecting both `odds_2t` and `odds_3t`.
After the command starts cleanly, continuous monitoring is not required. Let it run and verify the produced day files or DuckDB date range after completion or when you are ready to resume.

Example:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range --start-date 20260306 --end-date 20260310 --refresh-every-days 1 --resume-existing-days --sleep-seconds 0.5
```

For parallel workers or resumable long runs, point each process at its own working roots:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range --start-date 20250401 --end-date 20250930 --raw-root work\boat_a\raw --bronze-root work\boat_a\bronze --db-path work\boat_a\silver\boat_race.duckdb --refresh-every-days 1 --resume-existing-days --sleep-seconds 0.5 --skip-term-stats --skip-quality-report
```

If 3T odds are not needed, skip them explicitly:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range --start-date 20260306 --end-date 20260310 --refresh-every-days 1 --resume-existing-days --skip-odds-3t
```
## Fast Multi-Month Collection

For multi-month collection, prefer `collect-mbrace-range`.

This command uses official mbrace daily `B` and `K` downloads and fills:

- `races`
- `entries`
- `race_meta`
- `results`
- `beforeinfo_entries`

As with other long runs, continuous monitoring is not required once the command has started normally. For long windows, just budget time, keep resume-safe flags, and check completion afterward.

Example:

```powershell
.\.venv\Scripts\python -m boat_race_data collect-mbrace-range --start-date 20251201 --end-date 20260310 --refresh-every-days 20 --sleep-seconds 0.5 --skip-term-stats
```

## Canonical Shared Data Root

To treat a shared location as the canonical `raw -> bronze -> silver` root, set `BOAT_DATA_ROOT` before running the CLI. This keeps the repo portable while letting one machine write directly to a network share such as `\\038INS\boat\data`.

```powershell
$env:BOAT_DATA_ROOT="\\038INS\boat\data"
.\.venv\Scripts\python -m boat_race_data refresh-silver
.\.venv\Scripts\python -m boat_race_data collect-range --start-date 20260314 --end-date 20260319 --refresh-every-days 1 --resume-existing-days --sleep-seconds 0.5
```

You can still override individual paths with `BOAT_RAW_ROOT`, `BOAT_BRONZE_ROOT`, and `BOAT_DB_PATH`.

## Daily Racer-Index Live CSV

The current racer-index live signal is not yet persisted as `daily_pred1_signal` or `daily_pred6` tables in DuckDB.
Operationally, it is produced as a daily CSV bundle from the shared DB and shared raw cache.

Current flow:

1. shared canonical DB lives at `\\038INS\boat\data\silver\boat_race.duckdb`
2. target-day raw pages are collected into `\\038INS\boat\data\raw`
3. `predict_racer_rank_live.py` builds predictions for one target day
4. outputs are written under `\\038INS\boat\reports\strategies\racer_rank_live_YYYYMMDD\`

Daily output files:

- `predictions.csv`
- `race_summary.csv`
- `confidence_tier_stats.csv`
- `summary.md`

Current live consumption note:

- `live_trigger` currently reads `race_summary.csv`
- it does not read a persisted `daily_pred1_signal` table from DuckDB yet

Current helper script for daily generation:

- `workspace_codex/scripts/run_racer_rank_live_daily.ps1`

Current schedule on this machine:

- task name: `\BoatRacerIndexLiveCsvDaily`
- start time: `07:00`
- intent: wait for prior-day `results` to exist in shared DuckDB, then collect target-day raw pages and generate `racer_rank_live_YYYYMMDD`
