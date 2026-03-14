# Collection Log 2026-03-12

## Command

```powershell
.\.venv\Scripts\python -m boat_race_data collect-mbrace-range `
  --start-date 20230311 `
  --end-date 20250414 `
  --sleep-seconds 0.5 `
  --refresh-every-days 60 `
  --resume-existing-days `
  --skip-term-stats
```

## Purpose

- Extend the existing trusted research DB from `2025-04-15..2026-03-10`
- Fill the missing historical range for long-horizon fixed-payout backtests

## Result Summary

- Added historical mbrace coverage for `2023-03-11..2025-04-14`
- Connected with the already collected `2025-04-15..2026-03-10`
- Trusted range after run: `2023-03-11..2026-03-10`
- Distinct race dates after run: `1096`

## Key Output Counts After Run

- `races=168036`
- `entries=1008216`
- `results=165771`
- `beforeinfo_entries=980531`
- `race_meta=168036`

## Notes

- Collection used official mbrace daily `B/K` downloads only
- `odds_2t / odds_3t` were not the target of this run
- This run is intended for fixed-payout backtests, not full expectation-based odds backtests
