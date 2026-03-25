# C2 `pred1 != lane1` Overlay Walk-Forward

## Scope

- evaluation period: `2025-04-01` .. `2026-03-09`
- racer-index window: `5M`
- prediction generation: monthly walk-forward
- history window: prior months ending 2 months before target month
- tuning window: previous month
- target strategy: `C2` current-ish proxy (`women6`, `B2 cut`, `final day cut`)
- overlay rule: if `pred1_lane = 1`, skip the race

## Pred1 Quality

- predicted races: `51870`
- evaluable races: `51545`
- pred1 actual win rate: `57.39%`
- pred1 top3 rate: `86.06%`

## Strategy Overlay

| baseline ROI | overlay ROI | delta profit | baseline DD | overlay DD | removed races | removed hit races |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 129.71% | 150.19% | -126090 | 163280 | 32840 | 227 | 55 |

## Pred1 Monthly

| month | predicted_races | evaluable_races | pred1_win_rate | pred1_top3_rate | forward_rank_mae | forward_pairwise_acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025-04-01 | 4221 | 3964 | 56.41% | 86.42% | 1.1805 | 0.7215 |
| 2025-05-01 | 5027 | 4697 | 54.97% | 84.98% | 1.1830 | 0.7180 |
| 2025-06-01 | 4766 | 4516 | 55.38% | 84.37% | 1.1955 | 0.7151 |
| 2025-07-01 | 5140 | 4824 | 57.01% | 85.47% | 1.1703 | 0.7240 |
| 2025-08-01 | 5046 | 4771 | 57.30% | 85.88% | 1.1545 | 0.7273 |
| 2025-09-01 | 4247 | 3963 | 57.88% | 86.15% | 1.1583 | 0.7267 |
| 2025-10-01 | 4128 | 3864 | 57.81% | 87.66% | 1.1470 | 0.7295 |
| 2025-11-01 | 3936 | 3658 | 59.06% | 86.50% | 1.1431 | 0.7315 |
| 2025-12-01 | 4768 | 4392 | 58.89% | 86.59% | 1.1436 | 0.7303 |
| 2026-01-01 | 5162 | 4765 | 59.25% | 86.55% | 1.1430 | 0.7307 |
| 2026-02-01 | 4170 | 3876 | 58.68% | 87.33% | 1.1400 | 0.7312 |
| 2026-03-01 | 1259 | 1171 | 53.91% | 83.64% | 1.2462 | 0.7038 |
