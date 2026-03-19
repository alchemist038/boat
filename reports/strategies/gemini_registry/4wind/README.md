# 4Wind

## Identity

- source hypothesis: `H-002`
- normalized strategy: `Gemini_H002_Exacta_L4_WindyAttack`
- bet type: `2連単`
- combos: `4-1`, `4-5`, `4-6`

Nickname meaning:

- `4wind` = lane 4 attack under windy conditions

## Logic

Play only when all of the following are true:

- `wind_speed_m >= 4`
- `lane4_st_diff_from_inside <= -0.05`
- `lane4_exhibition_time_rank <= 3`

Interpretation:

- wind is strong enough to disturb a normal race shape
- lane 4 is stepping ahead of lane 3 at the exhibition ST line
- lane 4 is also not weak on same-race exhibition performance

This is a lane-4 attack idea rather than a generic windy-race rule.

## Backtest Snapshot

2024 exploratory:

- played races: `1534`
- bet count: `4602`
- ROI: `201.58%`
- hit count: `403`
- max drawdown: `9,350 yen`
- max losing streak: `90`

Source:

- [backtest_strategy_summary.csv](/d:/boat/reports/strategies/gemini_zero_base_2024/backtest_strategy_summary.csv)

2025 follow-up:

- played races: `1676`
- bet count: `5028`
- ROI: `146.5%`
- hit count: `338`
- max drawdown: `99,430 yen`
- max losing streak: `994`

Source:

- [backtest_strategy_summary.csv](/d:/boat/reports/strategies/gemini_zero_base_2025/backtest_strategy_summary.csv)

## Current View

- strongest branch from the Gemini set so far
- stayed clearly positive in both 2024 and 2025
- still needs slicing because the edge may be concentrated in certain stadium and wind contexts

## Suggested Next Analysis

- stadium x wind-bucket split
- monthly stability by stadium
- wave bucket interaction
- whether some stadiums should be excluded rather than included

