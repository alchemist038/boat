# Long-Run Backfill Runbook

This runbook is for long collection jobs split between `ins14` and `i5`.

## Recommended Model

- `ins14` handles current and recent data plus final integration
- `i5` handles older backfill windows
- `i5` works from a local clone, not from the shared drive as a Git workspace
- each running process uses its own local `data/` tree

## Why This Resumes Cleanly

The collection commands already support day-based resume:

- `--resume-existing-days`
- `--refresh-every-days 1`

This means a stopped run can be resumed without restarting from day one, as long
as the same local `data/bronze` tree is preserved.

## Safe Rules

1. Never let two running jobs write into the same `data/bronze` tree.
2. Never let two running jobs write into the same DuckDB file.
3. Split by non-overlapping date ranges.
4. Run `term_stats` on only one machine, usually `ins14`.
5. Keep one job file per long run under `coordination/jobs/active/`.

## Suggested i5 Layout

- `C:\CODEX_WORK\boat_a`
- `C:\CODEX_WORK\boat_b`

Example split:

- `boat_a`: `2025-04-01` to `2025-09-30`
- `boat_b`: `2025-10-01` to `2026-03-05`

## Suggested Command Pattern

Use machine-local DB outputs and resume by day.

```powershell
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20250401 `
  --end-date 20250930 `
  --db-path data/silver/boat_race_i5_a.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

## Resume Procedure

If the process stops:

1. open the job file
2. check `last_log_path`
3. verify the last completed bronze day file
4. rerun the exact `Resume Command`
5. update `updated_at`, `last_completed_date`, and `last_run_note`

Do not delete partial local data unless the run is known to be corrupt.

## Copy Completion Rule

If `i5` owns the job until copy completion, then `i5` is not done at collection end.

The job remains active until:

1. collection is complete
2. the assigned `raw/` and `bronze/` files are copied to `ins14`
3. copy verification is recorded
4. a handoff is written for `ins14`

## Copy Verification

At minimum, verify:

- first date copied
- last date copied
- number of day files copied per table
- target path on `ins14`

If manual copy is used, record the exact folders copied.

## Ins14 Finalization

After `i5` copy completion:

1. `ins14` imports the copied day files into its main bronze tree
2. `ins14` runs one final DB refresh
3. `ins14` runs quality checks
4. `ins14` closes the handoff

## Good Default Split

For now:

- `ins14`: current and recent dates
- `i5`: historical odds backfill

That keeps the highest-churn data on the main machine and uses `i5` for low-risk
throughput work.
