# Gemini Zero-Base Hypotheses Normalized For Backtest

- source period used by Gemini sample: `2024-01-01..2024-04-30`
- first backtest window here: `2024-01-01..2024-12-31`
- Gemini conversation is kept untouched in `GPT/gemini.md`.
- This file is the human-side normalization layer for mechanical backtesting.

## Notes
- `H-004` used a broken sample-side `is_hometown` flag. For backtest, it is corrected by mapping each stadium code to its venue branch prefecture and comparing against `lane1_branch`.
- The first 2024 run is exploratory, not a clean OOS validation, because the Gemini sample was drawn from `2024-01-01..2024-04-30`.

## Normalized Rules

### H-001 -> Gemini_H001_Exacta_L2_Pressure
- bet type: `2連単`
- combos: `2-1`, `2-3`, `2-4`
- conditions:
- `lane1_exhibition_time_rank >= 4`
- `lane2_exhibition_time_rank <= 2`
- `lane2_st_diff_from_inside <= -0.05`

### H-002 -> Gemini_H002_Exacta_L4_WindyAttack
- bet type: `2連単`
- combos: `4-1`, `4-5`, `4-6`
- conditions:
- `wind_speed_m >= 4`
- `lane4_st_diff_from_inside <= -0.05`
- `lane4_exhibition_time_rank <= 3`

### H-003 -> Gemini_H003_Trifecta_InnerA1Wall
- bet type: `3連単`
- combos: `1-2-3`, `1-3-2`, `1-2-4`
- conditions:
- `a1_count = 2`
- `lane1_class = 'A1'`
- `(lane2_class = 'A1' OR lane3_class = 'A1')`
- `lane4_exhibition_time_rank >= 3`

### H-004 -> Gemini_H004_Exacta_HometownRoughWater
- bet type: `2連単`
- combos: `1-2`, `1-3`
- conditions:
- `wave_height_cm >= 5`
- `lane1_is_hometown = 1` using corrected venue-branch mapping
- `lane1_exhibition_time_rank <= 3`

### H-005 -> Gemini_H005_Trifecta_L5_OverlookedRocket
- bet type: `3連単`
- combos: `5-1-2`, `5-1-6`
- conditions:
- `lane5_win_rate_rank >= 4`
- `lane5_exhibition_time_rank = 1`
- `lane4_st_diff_from_inside >= 0.05`