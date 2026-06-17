# DB Quality Allowed Missing Policy

## Purpose

Officially cancelled races should not be treated as broken data. They are
scheduled races that did not settle, so `results`, `odds_2t`, and `odds_3t`
can be absent by design.

The operating rule is:

- keep cancelled races in `races`, `entries`, and `race_meta`
- do not insert dummy `results` rows
- do not invent zero-payout odds or settlement rows
- classify missing settlement/odds for official cancellations as
  `allowed_missing`
- keep all other missing settlement/odds rows as `true_missing`

This keeps the historical schedule intact while preventing daily DB audits
from reporting official cancellations as repairable defects.

## Exception Record

The lightweight exception record is generated as CSV by
`workspace_codex/scripts/audit_db_allowed_missing.py`.

Columns:

- `race_date`
- `stadium_code`
- `stadium_name`
- `race_no`
- `race_id`
- `exception_type`
- `reason`
- `source`
- `verified_at`
- `allowed_missing_tables`

Example:

```csv
2026-06-16,01,桐生,12,202606160112,cancelled,official result page says race cancelled,official_result_page,2026-06-17 19:31:00,results|odds_2t|odds_3t
```

## Current Known Allowed Missing Races

After the 2026-06-17 repair run, the remaining recent missing settlement/odds
rows were re-fetched and confirmed as official cancellation pages.

| Date | Stadium | Races | Count |
|---|---|---:|---:|
| 2026-06-02 | 大村 | 3R-12R | 10 |
| 2026-06-03 | 江戸川 | 1R-12R | 12 |
| 2026-06-03 | 蒲郡 | 1R-12R | 12 |
| 2026-06-03 | 津 | 1R-12R | 12 |
| 2026-06-03 | 三国 | 1R-12R | 12 |
| 2026-06-16 | 桐生 | 12R | 1 |

Total: 59 allowed missing races.

## Audit Command

```powershell
cd C:\boat
.\.venv\Scripts\python.exe .\workspace_codex\scripts\audit_db_allowed_missing.py `
  --start-date 2026-06-01 `
  --end-date 2026-06-16 `
  --output-dir .\workspace_codex\reports\data_quality\allowed_missing_20260617
```

Expected interpretation:

- `race_exceptions.csv`: official cancellations; OK to remain missing from
  settlement/odds tables
- `true_missing.csv`: rows that still need repair
- `summary.csv`: daily totals split into allowed vs true missing
- `README.md`: human-readable audit summary

## Promotion Path

Keep the exception list as generated CSV first. If the exception types remain
stable, promote it later into DuckDB as a formal `race_exceptions` table and
join it inside recurring quality checks.
