# C2 + 125 + 4wind Combined Snapshot 2026-03-22

- aligned period: `2025-04-01` to `2026-03-09`
- note: `C2` canonical race results currently end on `2026-03-09`, so the combination is aligned to that common end date.
- C2 definition: `Strategy_C2_Provisional_v1`
- 125 definition: existing four-stadium `local_best_exgap` line, converted back to natural `x1` stake
- 4wind definition: `only_wind_5_6_415` from the 2026-03-22 odds backtest

## Stake Note
- `C2`: `4,000円 / race`
- `125`: `100円 / race`
- `4wind`: `200円 / race`
- This is a natural-stake combination, so `C2` contributes most of the portfolio risk and return.

## Files
- `summary.csv`
- `overlaps.csv`
- `*_race_results.csv` for each individual strategy and the combined portfolios

## Weighted Variant
- `125 x20R`, `4wind x5R`, `C2` unchanged is included in the same `summary.csv` as `C2_plus_125_x20` and `C2_plus_125_x20_plus_4wind_x5`.
