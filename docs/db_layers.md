# DB Layers

This project now keeps two database layers in DuckDB:

- `bronze_*`
  - Raw extracted rows loaded from `data/bronze/*.csv`
  - Values stay as strings so reparsing and audits are easy
  - Tables:
    - `bronze_races`
    - `bronze_entries`
    - `bronze_odds_2t`
    - `bronze_odds_3t`
    - `bronze_results`
    - `bronze_beforeinfo_entries`
    - `bronze_race_meta`
    - `bronze_racer_stats_term`

- typed analysis tables
  - Normalized tables for joins and backtests
  - Tables:
    - `races`
    - `entries`
    - `odds_2t`
    - `odds_3t`
    - `results`
    - `beforeinfo_entries`
    - `race_meta`
    - `racer_stats_term`

There is also a monitoring view:

- `collection_day_summary`
  - One row per `race_date`
  - Shows race, entry, odds, and result row counts
  - Useful for resume checks and missing-day detection

## Why raw files are still kept on disk

The filesystem `data/raw` remains the source of truth for HTML, LZH, and TXT files.
Keeping those binaries inside DuckDB would make the DB large and slower to refresh.
The practical split is:

- `data/raw`: original source files
- `bronze_*` in DuckDB: raw extracted rows
- typed tables in DuckDB: analysis-ready tables

## Useful SQL

```sql
SHOW TABLES;
```

```sql
SELECT *
FROM collection_day_summary
ORDER BY race_date;
```

```sql
SELECT *
FROM bronze_entries
WHERE race_date = '2025-12-17'
LIMIT 20;
```

```sql
SELECT
  e.race_id,
  e.lane,
  e.racer_name,
  o.first_lane,
  o.second_lane,
  o.odds
FROM entries e
JOIN odds_2t o USING (race_id)
WHERE e.race_date = DATE '2025-12-17'
ORDER BY e.race_id, o.odds
LIMIT 20;
```
