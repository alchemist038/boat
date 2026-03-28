# H-B Racer-Index Overlay Backtest Aligned Period

## Purpose

- test `H-B = exacta 4-2` on `2025-04-01..2026-03-09`
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

- settled races with predictions: `51833`
- baseline H-B races: `586`
- overlay races (`pred6_lane != 2` inside H-B): `530`
- overlay share inside H-B: `90.44%`

## Prediction Monthly Quality

| month | races | winner hit | top3 set hit | rank MAE | pairwise acc |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025-04 | 4221 | 56.36% | 24.29% | 1.180 | 0.721 |
| 2025-05 | 5027 | 54.80% | 24.19% | 1.183 | 0.718 |
| 2025-06 | 4766 | 55.36% | 23.96% | 1.196 | 0.715 |
| 2025-07 | 5140 | 56.78% | 24.88% | 1.170 | 0.724 |
| 2025-08 | 5046 | 57.24% | 25.97% | 1.155 | 0.727 |
| 2025-09 | 4247 | 58.09% | 25.41% | 1.158 | 0.727 |
| 2025-10 | 4128 | 58.20% | 25.26% | 1.147 | 0.730 |
| 2025-11 | 3936 | 59.35% | 25.67% | 1.143 | 0.732 |
| 2025-12 | 4768 | 59.06% | 26.05% | 1.144 | 0.730 |
| 2026-01 | 5162 | 59.54% | 25.69% | 1.143 | 0.731 |
| 2026-02 | 4170 | 58.72% | 25.52% | 1.140 | 0.731 |
| 2026-03 | 1259 | 53.97% | 21.52% | 1.246 | 0.704 |

## Scope Summary

### baseline_h_b_4-2

- bets: `586`
- hits: `27`
- investment: `58,600 yen`
- return: `78,670 yen`
- profit: `20,070 yen`
- ROI: `134.25%`
- hit rate: `4.61%`
- average hit payout: `2,913.70 yen`
- max drawdown: `-19,070 yen`
- drawdown peak race: `202510022308`
- drawdown bottom race: `202603080809`
- longest losing streak: `118`
- losing streak start: `202504211010`
- losing streak end: `202506141007`
- lane4 actual win rate inside scope: `24.40%`
- lane2 actual second rate inside scope: `20.99%`
- wave>=6 rate inside scope: `100.00%`

### overlay_pred6_not2_h_b_4-2

- bets: `530`
- hits: `27`
- investment: `53,000 yen`
- return: `78,670 yen`
- profit: `25,670 yen`
- ROI: `148.43%`
- hit rate: `5.09%`
- average hit payout: `2,913.70 yen`
- max drawdown: `-15,370 yen`
- drawdown peak race: `202510022308`
- drawdown bottom race: `202603080809`
- longest losing streak: `113`
- losing streak start: `202504211010`
- losing streak end: `202506141007`
- lane4 actual win rate inside scope: `23.58%`
- lane2 actual second rate inside scope: `22.26%`
- wave>=6 rate inside scope: `100.00%`
