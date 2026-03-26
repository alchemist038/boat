# H-B vs Current Four Equity Overlay

## Scope

- aligned period: `2025-04-01` .. `2026-03-09`
- current four used in this note:
  - `125_broad_four_stadium`
  - `c2_provisional_v1`
  - `4wind_base_415`
  - `H-A`
- candidate branch:
  - `H-B`

## Plot Files

- `h_b_vs_current_four_equity.png`
- `h_b_vs_current_four_equity_summary.csv`
- `h_b_vs_current_four_equity_race_results.csv`

## Assumptions

- `H-A` is shown as the current first refinement candidate: `final day cut` applied
- `H-B` is shown as the current rough-water candidate: `pred6_lane != 2`
- `C2` uses the current walk-forward overlay file with `pred1 != lane1`
- `125` and `4wind` use the best aligned race-result files, then apply current shared `final day cut` by `race_meta.is_final_day`
- because source stakes differ, the figure contains:
  - raw cumulative profit in source yen
  - `100-yen normalized` cumulative profit for shape comparison

## Summary

| logic | variant | races | hits | hit rate | profit | ROI | max DD | max losing streak | 100-yen normalized profit |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 125_broad_four_stadium | existing_aligned_x1 + final_day_cut | 219 | 13 | 5.94% | 28,060円 | 228.13% | -3,700円 | 38 | 28,060.00円 |
| c2_provisional_v1 | walkforward_pred1_non_lane1_overlay | 113 | 54 | 47.79% | 145,050円 | 150.19% | -32,840円 | 5 | 4,848.90円 |
| 4wind_base_415 | existing_aligned_4-1_4-5 + final_day_cut | 572 | 92 | 16.08% | 69,940円 | 161.14% | -23,000円 | 115 | 34,970.00円 |
| H-A | final_day_cut_proxy | 931 | 99 | 10.63% | 102,280円 | 209.86% | -12,400円 | 44 | 102,280.00円 |
| H-B | pred6_not2_overlay | 530 | 27 | 5.09% | 25,670円 | 148.43% | -15,370円 | 113 | 25,670.00円 |

## Notes

- `125_broad_four_stadium`: best aligned 125 race-results with final-day rows removed by current shared filter
- `c2_provisional_v1`: current-ish C2 proxy with B2 cut, final-day cut, and racer-index pred1!=lane1 overlay
- `4wind_base_415`: best aligned 4wind race-results with final-day rows removed by current shared filter
- `H-A`: H-A exacta 4-1 official-settle proxy with final-day cut
- `H-B`: H-B exacta 4-2 official-settle proxy with racer-index pred6_lane != 2
