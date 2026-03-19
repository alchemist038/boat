# 2Press

## Identity

- source hypothesis: `H-001`
- normalized strategy: `Gemini_H001_Exacta_L2_Pressure`
- bet type: `2連単`
- combos: `2-1`, `2-3`, `2-4`

Nickname meaning:

- `2press` = lane 2 pressing through a weak lane 1

## Logic

Play only when all of the following are true:

- `lane1_exhibition_time_rank >= 4`
- `lane2_exhibition_time_rank <= 2`
- `lane2_st_diff_from_inside <= -0.05`

Interpretation:

- lane 1 looks weak on same-race exhibition rank
- lane 2 looks strong on same-race exhibition rank
- lane 2 is also stepping ahead of lane 1 in exhibition ST shape

This is basically a lane-2 pressure / puncture idea against a soft inside boat.

## Backtest Snapshot

2024 exploratory:

- played races: `1084`
- bet count: `3252`
- ROI: `153.36%`
- hit count: `325`
- max drawdown: `7,190 yen`
- max losing streak: `51`

Source:

- [backtest_strategy_summary.csv](/d:/boat/reports/strategies/gemini_zero_base_2024/backtest_strategy_summary.csv)

2025 follow-up:

- played races: `1201`
- bet count: `3603`
- ROI: `105.18%`
- hit count: `252`
- max drawdown: `90,770 yen`
- max losing streak: `890`

Source:

- [backtest_strategy_summary.csv](/d:/boat/reports/strategies/gemini_zero_base_2025/backtest_strategy_summary.csv)

## Current View

- survived 2025, but edge shrank a lot
- probably not a pure all-stadium final rule yet
- better treated as a branch that needs context slicing

## Suggested Next Analysis

- stadium x meeting-day split
- stadium x wind-bucket split
- compare day1-2 vs day3-4 vs day5+

