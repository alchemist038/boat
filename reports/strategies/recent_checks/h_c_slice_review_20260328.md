# H-C Slice Review 2026-03-28

## Baseline Definition

- exacta `3-2`
- `lane3_class in (A1, A2)`
- `lane4_class = B2`
- latest exacta `3-2` quoted odds window: `15-60`

This is the simple proxy that reproduces the bounded discovery note.

## Baseline By Period

| period | bets | hits | avg_odds | ROI | profit_yen |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2025-04-01 .. 2025-06-16` | 153 | 7 | 31.07 | 122.29% | 3,410 |
| `2025-06-17 .. 2026-03-27` | 563 | 14 | 30.65 | 62.08% | -21,350 |

## Split By Major Time Block

| period | bets | hits | avg_odds | ROI | profit_yen |
| --- | ---: | ---: | ---: | ---: | ---: |
| bounded `2025-04-01 .. 2025-06-16` | 153 | 7 | 31.07 | 122.29% | 3,410 |
| `2025_h2` | 399 | 6 | 30.10 | 32.63% | -26,880 |
| `2026_ytd` | 164 | 8 | 31.99 | 133.72% | 5,530 |

Read:

- the main collapse is concentrated in `2025_h2`
- `2026_ytd` itself is not weak
- so `H-C` currently looks more like a period-fragile branch than a permanently dead branch

## lane3 Class Slice

| period | lane3_class | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bounded | `A1` | 57 | 5 | 30.27 | 199.12% | 5,650 |
| bounded | `A2` | 96 | 2 | 31.54 | 76.67% | -2,240 |
| post | `A1` | 185 | 6 | 29.41 | 72.97% | -5,000 |
| post | `A2` | 378 | 8 | 31.26 | 56.75% | -16,350 |
| `2026_ytd` | `A1` | 51 | 3 | 31.47 | 164.71% | 3,300 |
| `2026_ytd` | `A2` | 113 | 5 | 32.22 | 119.73% | 2,230 |

Read:

- `lane3=A1` is clearly the stronger side
- but `A1 only` is still not enough to save the weak post-period by itself

## lane2 Class Slice

| period | lane2_class | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bounded | `B1` | 99 | 7 | 30.58 | 188.99% | 8,810 |
| bounded | `A1` | 28 | 0 | 33.02 | 0.00% | -2,800 |
| bounded | `A2` | 20 | 0 | 29.61 | 0.00% | -2,000 |
| bounded | `B2` | 6 | 0 | 34.80 | 0.00% | -600 |
| post | `A1` | 65 | 2 | 27.69 | 158.00% | 3,770 |
| post | `A2` | 99 | 3 | 29.57 | 60.00% | -3,960 |
| post | `B1` | 369 | 9 | 31.01 | 50.79% | -18,160 |
| post | `B2` | 30 | 0 | 36.15 | 0.00% | -3,000 |
| `2026_ytd` | `A1` | 15 | 1 | 36.09 | 394.00% | 4,410 |
| `2026_ytd` | `A2` | 29 | 2 | 27.38 | 167.59% | 1,960 |
| `2026_ytd` | `B1` | 108 | 5 | 31.97 | 103.33% | 360 |
| `2026_ytd` | `B2` | 12 | 0 | 38.12 | 0.00% | -1,200 |

Read:

- bounded slice was actually strongest when `lane2 = B1`
- post-period improved only when `lane2` shifted toward `A1`
- this means the original `sticky 2` story is not captured by a single stable class filter

## Final Day Slice

| period | final_day_flag | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bounded | `not_final_day` | 132 | 7 | 30.02 | 141.74% | 5,510 |
| bounded | `final_day` | 21 | 0 | 37.65 | 0.00% | -2,100 |
| post | `not_final_day` | 551 | 14 | 30.61 | 63.43% | -20,150 |
| post | `final_day` | 12 | 0 | 32.62 | 0.00% | -1,200 |

Read:

- `final day cut` is directionally correct
- but it is too small an effect to rescue the post-period collapse on its own

## Odds Bucket Slice

| period | odds_bucket | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bounded | `15-25` | 58 | 5 | 18.97 | 153.28% | 3,090 |
| bounded | `25-40` | 61 | 0 | 32.60 | 0.00% | -6,100 |
| bounded | `40-60` | 34 | 2 | 48.95 | 288.82% | 6,420 |
| post | `15-25` | 241 | 10 | 19.61 | 76.31% | -5,710 |
| post | `25-40` | 186 | 2 | 31.61 | 33.82% | -12,310 |
| post | `40-60` | 136 | 2 | 48.91 | 75.51% | -3,330 |

Read:

- `25-40` is the weakest bucket in both phases
- the bounded edge came mostly from `15-25` and `40-60`

## `lane3=A1` And `pred1_lane=3`

`pred1_lane=3` is treated here as the racer-index head confirmation variant for `H-C`.

| period | scope | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2025-04-01 .. 2025-06-16` | baseline | 153 | 7 | 31.07 | 122.29% | 3,410 |
| `2025-04-01 .. 2025-06-16` | `lane3=A1` | 57 | 5 | 30.27 | 199.12% | 5,650 |
| `2025-04-01 .. 2025-06-16` | `pred1_lane=3` | 14 | 2 | 22.27 | 250.71% | 2,110 |
| `2025-04-01 .. 2025-06-16` | `lane3=A1 & pred1_lane=3` | 7 | 2 | 20.96 | 501.43% | 2,810 |
| `2025-06-17 .. 2026-03-27` | baseline | 563 | 14 | 30.65 | 62.08% | -21,350 |
| `2025-06-17 .. 2026-03-27` | `lane3=A1` | 185 | 6 | 29.41 | 72.97% | -5,000 |
| `2025-06-17 .. 2026-03-27` | `pred1_lane=3` | 87 | 4 | 26.21 | 96.21% | -330 |
| `2025-06-17 .. 2026-03-27` | `lane3=A1 & pred1_lane=3` | 39 | 2 | 27.26 | 113.08% | 510 |
| `2025_h2` | `lane3=A1 & pred1_lane=3` | 30 | 1 | 26.63 | 58.00% | -1,260 |
| `2026_ytd` | `lane3=A1 & pred1_lane=3` | 9 | 1 | 29.33 | 296.67% | 1,770 |

Read:

- both `lane3=A1` and `pred1_lane=3` improve the baseline directionally
- the combined slice is the cleanest small-sample refinement found so far
- but it is still fragile:
  - `2025_h2` remains negative
  - `2026_ytd` is positive, but only `9` bets
- current interpretation:
  - preserve this as the most interesting `H-C` refinement candidate
  - keep it on `hold`, not promotion-ready

## Stadium Slice

### Post Period `2025-06-17 .. 2026-03-27` with `bets >= 10`

| stadium | bets | hits | ROI | profit_yen |
| --- | ---: | ---: | ---: | ---: |
| `唐津` | 20 | 2 | 323.50% | 4,470 |
| `びわこ` | 21 | 1 | 281.43% | 3,810 |
| `蒲郡` | 25 | 2 | 178.40% | 1,960 |
| `福岡` | 15 | 1 | 116.00% | 240 |
| `芦屋` | 33 | 1 | 109.70% | 320 |
| `三国` | 31 | 0 | 0.00% | -3,100 |
| `江戸川` | 30 | 0 | 0.00% | -3,000 |
| `若松` | 29 | 0 | 0.00% | -2,900 |
| `浜名湖` | 28 | 0 | 0.00% | -2,800 |
| `下関` | 24 | 0 | 0.00% | -2,400 |

### `2026_ytd` with `bets >= 5`

| stadium | bets | hits | ROI | profit_yen |
| --- | ---: | ---: | ---: | ---: |
| `びわこ` | 9 | 1 | 656.67% | 5,010 |
| `蒲郡` | 7 | 2 | 637.14% | 3,760 |
| `芦屋` | 10 | 1 | 362.00% | 2,620 |
| `唐津` | 7 | 1 | 301.43% | 1,410 |
| `平和島` | 7 | 1 | 235.71% | 950 |
| `宮島` | 9 | 1 | 221.11% | 1,090 |
| `桐生` | 13 | 1 | 168.46% | 890 |
| `多摩川` | 13 | 0 | 0.00% | -1,300 |
| `浜名湖` | 12 | 0 | 0.00% | -1,200 |
| `江戸川` | 10 | 0 | 0.00% | -1,000 |

## Working Read

1. `H-C` is not stable as a global class-only branch.
2. The worst damage is concentrated in `2025_h2`, not `2026_ytd`.
3. If this branch is reopened, the best next slices are:
   - stadium-first review
   - `lane3=A1` emphasis
   - `lane3=A1 & pred1_lane=3`
   - avoiding the `25-40` odds bucket
4. `final day cut` is helpful but too weak to be the main refinement.
5. The current best small-sample refinement is `lane3=A1 & pred1_lane=3`, but it should remain `hold`.
