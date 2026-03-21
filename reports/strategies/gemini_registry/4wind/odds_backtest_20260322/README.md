# 4Wind Odds Backtest 2025-04-01 to 2026-03-20

## Purpose
- Re-run 4wind with the expanded `odds_2t` coverage.
- All filtering uses quoted 2-exacta odds aggregated as the average per race/combo because `odds_2t` still contains duplicate combo rows.
- Settlement uses official exacta payouts from `results`.
- Stake is fixed at 100 yen per combo.

## Summary
| strategy_name | played_races | bet_count | roi_pct | hit_race_pct | avg_min_odds_played | max_drawdown_yen | max_losing_streak | top_skip_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_4156 | 1528 | 4584 | 122.2 | 17.47 | 23.04 | 98130 | 327 | wind_not_target |
| only_wind_5_6_4156 | 623 | 1869 | 135.06 | 18.94 | 22.76 | 39470 | 130 | wind_not_target |
| only_wind_5_6_415 | 623 | 1246 | 147.95 | 14.77 | 24.39 | 27600 | 138 | wind_not_target |
| only_wind_5_6_415_skip_lt15 | 353 | 706 | 160.88 | 8.5 | 36.17 | 15440 | 76 | wind_not_target |
| only_wind_5_6_415_skip_lt18 | 300 | 600 | 176.57 | 8.67 | 39.66 | 14200 | 71 | wind_not_target |
| only_wind_5_6_415_skip_lt20 | 259 | 518 | 190.95 | 8.88 | 42.93 | 12000 | 60 | wind_not_target |