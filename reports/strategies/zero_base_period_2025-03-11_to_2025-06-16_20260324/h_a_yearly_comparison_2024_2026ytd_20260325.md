# H-A Yearly Comparison 2024 to 2026 YTD

## Rule

- target combo: `exacta 4-1`
- `lane1_st_top3`
  - implemented as `lane1` exhibition ST rank `<= 3`
- `lane4_ahead_lane1_005`
  - implemented as `lane1_st - lane4_st >= 0.05`
- settle source: `results.exacta_payout`

## Important Caveat

- this is an `official settle proxy` comparison
- it is not the original quoted-odds discovery scan
- `2026_ytd` ends at shared DB max result date: `2026-03-24`
- exacta combo matching is normalized so both `4-1` and `4 - 1` are treated as the same settle result

## Summary

| period | bets | hits | investment_yen | return_yen | profit_yen | ROI | avg_hit_payout | max_dd_yen | max_losing_streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024 | 922 | 134 | 92,200 | 214,110 | 121,910 | 232.22% | 1597.84 | -4,140 | 30 |
| 2025 | 1015 | 107 | 101,500 | 212,290 | 110,790 | 209.15% | 1984.02 | -13,770 | 44 |
| 2026_ytd | 263 | 26 | 26,300 | 39,720 | 13,420 | 151.03% | 1527.69 | -6,660 | 32 |

## Read

- `2024` is the strongest year in this proxy run and shows broad month-to-month persistence.
- `2025` is still profitable, but the profile is more volatile than `2024` and the weak window is concentrated in late April to mid June.
- `2026_ytd` should be treated as partial-year only, but it is still positive so far.

## DD Weak-Window Findings

The current read is that `H-A` does **not** mainly fail because `4-1` narrowly misses second place.

The larger failure mode is:

- lane 4 stops taking the head often enough
- lane 1 reverts to `head` too frequently

### 2025 max-DD window

Window:

- `2025-04-17` to `2025-06-14`

Observed shape:

- bets:
  - `202`
- hits:
  - `13`
- ROI:
  - `40.89%`
- lane 4 head rate:
  - `12.38%`
- lane 1 head rate:
  - `59.41%`
- final day rate:
  - `20.3%`

Top miss pattern:

- many misses are `1-*`
- the dominant read is:
  - `4` does not complete the head takeover
  - `1` remains too strong as the actual winner

### 2026 max-DD window

Window:

- `2026-02-28` to `2026-03-24`

Observed shape:

- lane 4 head rate:
  - `12.22%`
- lane 1 head rate:
  - `51.11%`
- final day rate:
  - `16.67%`

This looks directionally similar to the `2025` weak window.

### 2024 max-DD window

Window:

- `2024-02-15` to `2024-03-28`

Observed shape:

- lane 4 head rate:
  - `41.59%`
- lane 1 head rate:
  - `29.20%`
- final day rate:
  - `0%`

Interpretation:

- `2024` drawdown looks more like normal variance
- `2025` and `2026_ytd` look more like structural regime breaks

## Current Working Hypotheses

The next refinement pass should test these first:

1. final-day cut
2. lane-4 weakness cut
   - especially when `lane4_class = B1`
3. stronger lane-4 head confirmation
   - not only `lane4 ahead lane1`
   - but also some direct `lane4 head viability` confirmation

## Next Start Point

If the next review thread resumes from this note, start in this order:

1. re-test `H-A` with `final day cut`
2. re-test `H-A` with `lane4_class != B1`
3. test the intersection:
   - `final day cut`
   - plus `lane4_class != B1`
4. only after that, look for a stronger lane-4 head confirmation signal

## Detail

### 2024

- period: `2024-01-01` to `2024-12-31`
- bets: `922`
- hits: `134`
- ROI: `232.22%`
- max drawdown: `-4140 yen`
- drawdown peak race: `202402151202`
- drawdown bottom race: `202403281712`
- longest losing streak: `30`
- losing streak start: `202403150204`
- losing streak end: `202403281712`

### 2025

- period: `2025-01-01` to `2025-12-31`
- bets: `1015`
- hits: `107`
- ROI: `209.15%`
- max drawdown: `-13770 yen`
- drawdown peak race: `202504240402`
- drawdown bottom race: `202506141710`
- longest losing streak: `44`
- losing streak start: `202509181501`
- losing streak end: `202510052209`

### 2026_ytd

- period: `2026-01-01` to `2026-03-24`
- bets: `263`
- hits: `26`
- ROI: `151.03%`
- max drawdown: `-6660 yen`
- drawdown peak race: `202602280309`
- drawdown bottom race: `202603241608`
- longest losing streak: `32`
- losing streak start: `202602280310`
- losing streak end: `202603100201`
