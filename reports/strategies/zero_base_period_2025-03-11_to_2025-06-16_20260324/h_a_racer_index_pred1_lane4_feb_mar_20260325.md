# H-A With Racer Index `pred1=lane4`

## Scope

- base logic: `H-A` exacta `4-1`
- base conditions:
  - `lane1_st_top3`
  - `lane4_ahead_lane1_005`
- settle source: `results.exacta_payout` official-settle proxy
- overlay: keep only races where the current racer-index prototype predicts `pred1_lane = 4`

## Caveat

- this is **not** a full multi-year walkforward backtest
- it uses the currently available prototype outputs only:
  - `tuning_feb_predictions.csv`
  - `forward_march_predictions.csv`
- so this should be read as an initial compatibility check between `H-A` and the current racer-index prototype

## Summary

| period | base bets | base ROI | base profit | base max DD | base max losing streak | overlay bets | keep rate | overlay ROI | overlay profit | overlay max DD | overlay max losing streak | overlay hits / base hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026_feb_tuning | 86 | 300.47% | 17,240 | -1,270 | 12 | 9 | 10.47% | 0.00% | -900 | -800 | 9 | 0 / 15 |
| 2026_mar_forward | 82 | 26.10% | -6,060 | -5,960 | 30 | 5 | 6.10% | 160.00% | 300 | -400 | 4 | 1 / 3 |

## Read

- if `pred1=lane4` works, it should reduce `H-A` DD by confirming that lane 4 is a real head candidate
- the most important read is whether it helps the weak 2026 forward slice without killing sample size too aggressively

## Files

- yearly-ish comparison: `h_a_racer_index_pred1_lane4_feb_mar_20260325.csv`
- race-level joined rows: `h_a_racer_index_pred1_lane4_feb_mar_races_20260325.csv`
