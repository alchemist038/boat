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
- [4wind_refinement_summary.csv](/d:/boat/reports/strategies/gemini_registry/4wind/refinement_eval_20260320/4wind_refinement_summary.csv)

## Structural Signal

Refined focus:

- `only_wind_5_6`
- partner candidates concentrated toward `4-1` and `4-5`

What the rule is really saying:

- under `wind 5-6m`, when lane 4 has a clear exhibition ST edge and still ranks top-3 on exhibition time, lane 4 becomes much stronger than normal
- this is better treated as a structural signal about lane 4 strength than as a finished standalone betting rule

Observed lane-4 strength under the refined condition:

- same-period baseline with `wind 5-6m`: lane 4 head rate `10.97%` (`1677 / 15294`)
- `4wind only_wind_5_6`: lane 4 head rate `32.71%` (`487 / 1489`)
- when lane 4 wins, 2nd place is led by lane 5 `28.95%` and lane 1 `28.34%`

Source:

- [partner_analysis_20260320/README.md](/d:/boat/reports/strategies/gemini_registry/4wind/partner_analysis_20260320/README.md)

## Current View

- useful discovery, but no longer a standalone adoption candidate
- standalone operation was rejected because hit rate stayed too low for practical use
- keep it as an auxiliary theory:
- when another logic already has a reason to like a race, `4wind only_wind_5_6` can strengthen a lane-4 head view
- if lane-4 partners are needed, start from `4-1 / 4-5` before considering wider coverage

## Suggested Next Analysis

- use as a sub-signal inside another rule rather than reviving it alone
- test whether `lane 4 head strength` improves an existing rule's ranking model
- test whether `4-1 / 4-5` should be treated as partner priors, not direct fixed bets

