# Racer Index Operations

## Core Rules

- Build every prediction `point-in-time`
- Do not use the target race result or any future-date aggregate
- Keep all prediction outputs `append-only`
- Stamp every output with `window_months` and `weight_version`
- Do not change weights mid-month except for an emergency fix

## Current Operating Window

- The provisional operating window is `5M`
- Meaning:
  - history window: `5 months`
  - tuning window: `previous month`
  - forward window: `current month`

Example for `2026-03`:

- history: `2025-09-01..2026-01-31`
- tune: `2026-02-01..2026-02-28`
- forward: `2026-03-01..2026-03-31`

## Daily Run

1. Refresh data through the current day
2. Load the approved `weight_version`
3. build `racer_indicator_snapshot`
4. build `daily_score_output`
5. derive `daily_pred6` and `daily_pred1_signal`
6. append `prediction_settlement` after results are final

## Weekly Review

- Refit candidate weights on the latest `5M` window
- Review:
  - `pred6 actual 6th rate`
  - `pred6 top3-out rate`
  - `pred1 win / top2 / top3`
  - ROI when `pred1 != lane1`
  - overlay impact on `125`, `4wind`, and `C2`
- Weekly review is for candidate creation only, not promotion

## Monthly Promote

1. Compare `5M / 8M / 12M`
2. Choose one `weight_version` for the next month
3. Record the reason in [../RACER_INDEX_STATUS.md](../RACER_INDEX_STATUS.md)
4. Freeze that version for daily operation during the month

## Current Practical Read

- `pred6` is useful as a remove-candidate signal
- A universal `6-cut` overlay is not adopted yet
  - `125` can benefit
  - `C2` is hurt too much
- `pred1` is useful as a head candidate
- The strongest immediate use-case is `pred1 != lane1`

## Recommended Output Tags

- `weight_version`: `ri_5m_YYYY-MM`
- `score_version`: `ri_5m_YYYY-MM[a-z]`
- example `signal_name` values:
  - `pred6`
  - `pred1_non_lane1_exacta_12`
  - `pred1_non_lane1_trifecta_fixed`
