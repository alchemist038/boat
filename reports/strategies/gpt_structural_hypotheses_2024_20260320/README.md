# GPT Structural Hypotheses Backtest 2024-01-01 to 2024-12-31

## Purpose
- First-pass backtest of 3 GPT-generated structural hypotheses.
- All three were interpreted as trifecta ideas because the buy notation used `-ALL-ALL`.
- Stake is fixed at 100 yen per combo.

## Caveat
- This is an exploratory 2024-only test, not an out-of-sample validation.
- Hypotheses A and B are very wide spray structures, so raw ROI alone can overstate practical usability.

## Summary
| strategy_name | played_races | bet_count | roi_pct | hit_race_pct | max_drawdown_yen | max_losing_streak | top_skip_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GPT_HA_Trifecta_WeakInsideBias | 1085 | 43400 | 64.98 | 31.24 | 1645930 | 14 | lane1_win_rate_rank_not_3plus |
| GPT_HB_Trifecta_OuterExTop | 12835 | 256700 | 62.39 | 6.74 | 10011340 | 243 | exhibition_top_not_outer |
| GPT_HC_Trifecta_B2Simplification | 522 | 4176 | 57.38 | 23.75 | 179750 | 18 | b2_count_not_1 |

## Interpretation
- H-A is broad and expensive: 40 points per race.
- H-B is even broader structurally: 20 points per race and fires very often.
- H-C is the most practical of the three from a combination-count perspective.