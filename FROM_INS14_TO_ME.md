# FROM INS14 TO ME

This note is for the i5-side agent to read and execute.

## Context

- machine: ins14
- status: action_required
- updated_at: 2026-03-19 19:10 JST
- branch: main
- commit: e98e083

## Summary

- Shared bronze was checked for `odds_2t` and `odds_3t` day coverage.
- The main missing middle block is `2025-06-08 .. 2025-12-10`.
- The same missing block exists in both `odds_2t` and `odds_3t`.
- `2026-03-15 .. 2026-03-18` is part of the current recent run on ins14, so i5 does not need to own that range now.
- There is also an older missing block `2023-03-11 .. 2025-03-31`, but the first priority is the middle gap.

## What Was Confirmed

- `races` day files exist for `2023-03-11 .. 2026-03-18`
- `odds_2t` day files exist for:
  - `2025-04-01 .. 2025-06-07`
  - `2025-12-11 .. 2026-03-14`
- `odds_3t` day files exist for:
  - `2025-04-01 .. 2025-06-07`
  - `2025-12-11 .. 2026-03-14`
- internal gap in both tables:
  - `2025-06-08 .. 2025-12-10` (`186` days)

## Requested Work On i5

Goal:

- collect the missing odds block on i5
- run two scripts in parallel
- make the run safe to stop, safe to resume, and safe to rerun

Priority range split:

1. worker A: `2025-06-08 .. 2025-09-08`
2. worker B: `2025-09-09 .. 2025-12-10`

## Safety Rules

- Do not let two running jobs write to the same `raw` tree.
- Do not let two running jobs write to the same `bronze` tree.
- Do not let two running jobs write to the same DuckDB file.
- Always keep `--resume-existing-days`.
- Always keep `--refresh-every-days 1`.
- Use local worker trees on i5, not the shared drive as a Git workspace.
- It is fine to use `--skip-term-stats`.
- It is fine to use `--skip-quality-report`.
- After clean startup, active monitoring is not required.
- Working estimate is about `40 minutes per day`.
- If a run stops, rerun the exact same command.
- Do not delete partial `raw` or `bronze` output unless corruption is confirmed.

## Suggested Local Layout

Example:

- `C:\CODEX_WORK\boat_gap_a`
- `C:\CODEX_WORK\boat_gap_b`

Each worker should have its own:

- `data\raw`
- `data\bronze`
- `data\silver`

## Commands

Worker A:

```powershell
cd C:\CODEX_WORK\boat_gap_a
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20250608 `
  --end-date 20250908 `
  --raw-root data\raw `
  --bronze-root data\bronze `
  --db-path data\silver\boat_race_gap_a.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

Worker B:

```powershell
cd C:\CODEX_WORK\boat_gap_b
.\.venv\Scripts\python -m boat_race_data collect-range `
  --start-date 20250909 `
  --end-date 20251210 `
  --raw-root data\raw `
  --bronze-root data\bronze `
  --db-path data\silver\boat_race_gap_b.duckdb `
  --sleep-seconds 0.5 `
  --refresh-every-days 1 `
  --resume-existing-days `
  --skip-term-stats `
  --skip-quality-report
```

## Resume Procedure

If a run stops:

1. check the latest day file under `data\bronze\odds_2t`
2. check the latest day file under `data\bronze\odds_3t`
3. rerun the exact same command

The resume behavior is day-based, so already completed dates should be skipped.

If you stop a run manually:

1. stop the process only
2. keep the existing local `raw/bronze/silver`
3. rerun the same command later

## Completion Handoff Back To Ins14

When i5 finishes, write back to `FROM_I5_TO_ME.md` with:

- the range completed by worker A
- the range completed by worker B
- latest completed day for `odds_2t`
- latest completed day for `odds_3t`
- which `raw/` folders were copied
- which `bronze/` folders were copied
- copy destination
- any remaining missing dates if the job was partial

## Secondary Backlog

After the middle gap is done, the next large missing block is:

- `2023-03-11 .. 2025-03-31`

Do not start this secondary block until the middle gap handoff is complete.
