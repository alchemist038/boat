# H-B Racer-Index Overlay Backtest 2025H1

## Purpose

- test `H-B = exacta 4-2` on `2025-01-01..2025-06-30`
- baseline condition:
  - `wave_6p`
  - `lane4_ahead_lane1_005`
- apply racer-index point-in-time overlay:
  - lane 4 is `pred1`
- settle with official `results.exacta_combo` / `results.exacta_payout`

## Assumptions

- racer-index profile window: `5M`
- walk-forward shape: prior `5 months` history + prior `1 month` tuning + current month forward
- this is an `official settle proxy`, not an original quoted-odds recreation

## Coverage

- settled races with predictions: `27856`
- baseline H-B races: `442`
- overlay races (`pred1 = lane4` inside H-B): `43`
- overlay share inside H-B: `9.73%`

## Prediction Monthly Quality

| month | races | winner hit | top3 set hit | rank MAE | pairwise acc |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025-01 | 5000 | 58.96% | 24.60% | 1.148 | 0.729 |
| 2025-02 | 4345 | 59.04% | 24.42% | 1.154 | 0.726 |
| 2025-03 | 4520 | 60.95% | 26.11% | 1.122 | 0.736 |
| 2025-04 | 4221 | 56.36% | 24.29% | 1.180 | 0.721 |
| 2025-05 | 5027 | 54.80% | 24.19% | 1.183 | 0.718 |
| 2025-06 | 4766 | 55.36% | 23.96% | 1.196 | 0.715 |

## Scope Summary

### baseline_h_b_4-2

- bets: `442`
- hits: `23`
- investment: `44,200 yen`
- return: `82,670 yen`
- profit: `38,470 yen`
- ROI: `187.04%`
- hit rate: `5.20%`
- average hit payout: `3,594.35 yen`
- max drawdown: `-11,800 yen`
- drawdown peak race: `202506211007`
- drawdown bottom race: `202506141007`
- longest losing streak: `118`
- losing streak start: `202504211010`
- losing streak end: `202506141007`
- lane4 actual win rate inside scope: `23.76%`
- lane2 actual second rate inside scope: `19.91%`
- wave>=6 rate inside scope: `100.00%`

### overlay_pred1_lane4_h_b_4-2

- bets: `43`
- hits: `3`
- investment: `4,300 yen`
- return: `2,780 yen`
- profit: `-1,520 yen`
- ROI: `64.65%`
- hit rate: `6.98%`
- average hit payout: `926.67 yen`
- max drawdown: `-1,820 yen`
- drawdown peak race: `start-phase`
- drawdown bottom race: `202503170204`
- longest losing streak: `17`
- losing streak start: `202501062010`
- losing streak end: `202502081405`
- lane4 actual win rate inside scope: `41.86%`
- lane2 actual second rate inside scope: `18.60%`
- wave>=6 rate inside scope: `100.00%`
