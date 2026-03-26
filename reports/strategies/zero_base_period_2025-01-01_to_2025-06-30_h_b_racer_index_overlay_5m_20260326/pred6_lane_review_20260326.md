# H-B pred6 Lane Review 2025H1

## Purpose

- inspect where the racer-index `weakest lane` signal helps inside the `H-B` baseline
- baseline:
  - `exacta 4-2`
  - `wave_height_cm >= 6`
  - `lane1_st - lane4_st >= 0.05`
- period:
  - `2025-01-01 .. 2025-06-30`

## pred6 Lane Split

| pred6_lane | bets | hits | ROI | profit_yen | max_dd_yen |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4 | 35 | 2 | 580.29% | 16,810 | -3,000 |
| 3 | 28 | 3 | 412.50% | 8,750 | -1,400 |
| 6 | 217 | 10 | 150.51% | 10,960 | -6,220 |
| 5 | 115 | 7 | 149.83% | 5,730 | -4,500 |
| 2 | 44 | 1 | 20.91% | -3,480 | -3,480 |
| 1 | 3 | 0 | 0.00% | -300 | -300 |

## Practical Overlay Candidates

| scope | bets | hits | ROI | profit_yen | max_dd_yen |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 442 | 23 | 187.04% | 38,470 | -11,800 |
| pred6_not_2 | 398 | 22 | 205.40% | 41,950 | -11,300 |
| pred6_in_5_6 | 332 | 17 | 150.27% | 16,690 | -9,300 |
| pred6_in_3_4_5_6 | 395 | 22 | 206.96% | 42,250 | -11,200 |
| pred1_4_and_pred6_not_2 | 41 | 2 | 45.37% | -2,240 | -2,240 |

## Read

- the cleanest negative signal is:
  - `pred6_lane = 2`
- this is structurally plausible because `H-B = 4-2` needs lane 2 to survive second
- if the model already pushes lane 2 to the weakest slot, the branch loses its second-place partner

- `pred1 = 4` alone is too strong:
  - it shrinks the sample too much
  - and kills the payout edge

- the most practical first overlay candidate is:
  - `exclude pred6_lane = 2`

## Current Decision

If `H-B` moves to the next review pass, test in this order:

1. `H-B + pred6_lane != 2`
2. `H-B + final day cut`
3. `H-B + pred6_lane != 2 + final day cut`
4. only after that, revisit any stronger `pred1 = 4` style head-confirmation
