# H-A With Racer Index `pred6_lane` Slice

## Scope

- base logic: `H-A` exacta `4-1`
- base conditions:
  - `lane1_st_top3`
  - `lane4_ahead_lane1_005`
- settle source: `results.exacta_payout` official-settle proxy
- slice axis: current racer-index prototype `pred6_lane`
- periods:
  - `2026_feb_tuning`
  - `2026_mar_forward`

## Caveat

- this is not a full multi-year walkforward
- it uses only the currently available prototype prediction files for Feb and Mar 2026
- read this as a compatibility slice, not an adoption-ready overlay

## Overall Slice

| pred6_lane | bets | hits | profit_yen | ROI | max_dd_yen | max_losing_streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 13 | 3 | 1,700 | 230.77% | -600 | 6 |
| 3 | 17 | 0 | -1,700 | 0.00% | -1,600 | 17 |
| 4 | 2 | 0 | -200 | 0.00% | -100 | 2 |
| 5 | 44 | 6 | 8,790 | 299.77% | -2,250 | 17 |
| 6 | 75 | 7 | 2,490 | 133.20% | -2,600 | 19 |

## Period Slice

| period | pred6_lane | bets | hits | profit_yen | ROI | max_dd_yen | max_losing_streak |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026_feb_tuning | 2 | 8 | 3 | 2,200 | 375.00% | -300 | 3 |
| 2026_feb_tuning | 3 | 9 | 0 | -900 | 0.00% | -800 | 9 |
| 2026_feb_tuning | 4 | 1 | 0 | -100 | 0.00% | 0 | 1 |
| 2026_feb_tuning | 5 | 18 | 5 | 10,840 | 702.22% | -1,000 | 10 |
| 2026_feb_tuning | 6 | 39 | 5 | 4,500 | 215.38% | -1,100 | 11 |
| 2026_mar_forward | 2 | 5 | 0 | -500 | 0.00% | -400 | 5 |
| 2026_mar_forward | 3 | 8 | 0 | -800 | 0.00% | -700 | 8 |
| 2026_mar_forward | 4 | 1 | 0 | -100 | 0.00% | 0 | 1 |
| 2026_mar_forward | 5 | 26 | 1 | -2,050 | 21.15% | -1,950 | 17 |
| 2026_mar_forward | 6 | 36 | 2 | -2,010 | 44.17% | -2,100 | 15 |

## Read

- `pred6_lane = 3` is the cleanest weak bucket in this slice:
  - `17 bets`
  - `0 hits`
  - `ROI 0%`
- `pred6_lane = 5` is the strongest bucket overall, but the good result is mostly carried by the Feb tuning slice.
- `pred6_lane = 6` keeps the largest sample, but March is weak:
  - Feb: `ROI 215.38%`
  - Mar: `ROI 44.17%`
- `pred6_lane = 2` is too small to trust yet:
  - Feb is strong
  - Mar is `0 hits`

## Current Working Read

- if a `pred6`-side overlay is explored for `H-A`, the first candidate should be a weakness cut, not a universal keep rule
- the most plausible first check from this slice is:
  - exclude when `pred6_lane = 3`
- `pred6_lane = 6` is not clean enough to treat as a remove-candidate from this first pass
- this should remain research-only until a longer aligned window confirms it
