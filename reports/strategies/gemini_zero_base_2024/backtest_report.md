# Gemini Zero-Base Backtest 2024-01-01 to 2024-12-31

## Purpose
- Human-side normalization and first-pass 2024 backtest for Gemini-generated zero-base hypotheses.
- Gemini conversation itself was left untouched and preserved separately.
- Settlement uses official exacta/trifecta result combos and payouts from `results`.
- Stake is fixed at 100 yen per combo.

## Important Caveat
- This is not a clean out-of-sample validation because the Gemini sample package came from `2024-01-01..2024-04-30`.
- Treat this as a first 2024 exploratory screen, not a final adoption test.

## Summary
| strategy_name | bet_type | played_races | bet_count | roi_pct | hit_count | max_drawdown_yen | max_losing_streak | top_skip_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gemini_H001_Exacta_L2_Pressure | 2連単 | 1084 | 3252 | 153.36 | 325 | 7190 | 51 | lane1_not_weak_enough |
| Gemini_H002_Exacta_L4_WindyAttack | 2連単 | 1534 | 4602 | 201.58 | 403 | 9350 | 90 | wind_not_target |
| Gemini_H003_Trifecta_InnerA1Wall | 3連単 | 1491 | 4473 | 76.67 | 437 | 105860 | 46 | a1_count_not_2 |
| Gemini_H004_Exacta_HometownRoughWater | 2連単 | 1147 | 2294 | 92.78 | 399 | 28260 | 37 | wave_not_target |
| Gemini_H005_Trifecta_L5_OverlookedRocket | 3連単 | 671 | 1342 | 36.94 | 4 | 84630 | 639 | lane5_not_best_ex |