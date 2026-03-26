# H-B Racer-Index Overlay Backtest 2024

## Purpose

- test `H-B = exacta 4-2` on `2024-01-01..2024-12-31`
- baseline condition:
  - `wave_6p`
  - `lane4_ahead_lane1_005`
- apply racer-index point-in-time overlay:
  - exclude races where `pred6_lane = 2`
- settle with official `results.exacta_combo` / `results.exacta_payout`

## Assumptions

- racer-index profile window: `5M`
- walk-forward shape: prior `5 months` history + prior `1 month` tuning + current month forward
- this is an `official settle proxy`, not an original quoted-odds recreation

## Coverage

- settled races with predictions: `55274`
- baseline H-B races: `523`
- overlay races (`pred6_lane != 2` inside H-B): `471`
- overlay share inside H-B: `90.06%`

## Prediction Monthly Quality

| month | races | winner hit | top3 set hit | rank MAE | pairwise acc |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024-01 | 4992 | 57.69% | 25.34% | 1.158 | 0.728 |
| 2024-02 | 4409 | 57.63% | 25.59% | 1.142 | 0.732 |
| 2024-03 | 4476 | 57.71% | 26.89% | 1.131 | 0.734 |
| 2024-04 | 4450 | 58.75% | 26.47% | 1.123 | 0.735 |
| 2024-05 | 4792 | 60.06% | 26.81% | 1.126 | 0.734 |
| 2024-06 | 4662 | 58.12% | 25.41% | 1.163 | 0.725 |
| 2024-07 | 4889 | 56.52% | 24.02% | 1.180 | 0.721 |
| 2024-08 | 4839 | 56.73% | 24.55% | 1.172 | 0.723 |
| 2024-09 | 4382 | 59.23% | 25.81% | 1.161 | 0.726 |
| 2024-10 | 4366 | 59.67% | 25.16% | 1.153 | 0.727 |
| 2024-11 | 4133 | 59.10% | 26.26% | 1.143 | 0.730 |
| 2024-12 | 4951 | 58.77% | 26.31% | 1.147 | 0.731 |

## Scope Summary

### baseline_h_b_4-2

- bets: `523`
- hits: `33`
- investment: `52,300 yen`
- return: `104,170 yen`
- profit: `51,870 yen`
- ROI: `199.18%`
- hit rate: `6.31%`
- average hit payout: `3,156.67 yen`
- max drawdown: `-6,210 yen`
- drawdown peak race: `202412231406`
- drawdown bottom race: `202408271003`
- longest losing streak: `46`
- losing streak start: `202401231908`
- losing streak end: `202402231508`
- lane4 actual win rate inside scope: `28.49%`
- lane2 actual second rate inside scope: `23.33%`
- wave>=6 rate inside scope: `100.00%`

### overlay_pred6_not2_h_b_4-2

- bets: `471`
- hits: `32`
- investment: `47,100 yen`
- return: `100,990 yen`
- profit: `53,890 yen`
- ROI: `214.42%`
- hit rate: `6.79%`
- average hit payout: `3,155.94 yen`
- max drawdown: `-5,110 yen`
- drawdown peak race: `202412231406`
- drawdown bottom race: `202408271003`
- longest losing streak: `41`
- losing streak start: `202406280305`
- losing streak end: `202408271003`
- lane4 actual win rate inside scope: `28.24%`
- lane2 actual second rate inside scope: `24.42%`
- wave>=6 rate inside scope: `100.00%`
