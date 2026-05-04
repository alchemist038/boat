# Rolling 10-Day Forward 1-2/1-3 No-Grace Backtest

## Method

- Train period: previous `3` full months only.
- Grace period: day `1` to `10` of the cycle month is not used for training or scoring.
- Forward period: day `11` of the cycle month through day `10` of the next month.
- Candidate combos: `1-2`, `1-3` only.
- Candidate filters: sample >= `300`, ROI >= `108.0`, ROI lift >= `25.0`, profit > 0.
- Monthly stability: at least `2` positive months, and no sampled month below `98.0` ROI.
- Selection: max `10` candidates, max `5` per combo, duplicate race-set removal.
- Portfolio accounting deduplicates only by `race_id + combo`; `1-2` and `1-3` in the same race are both kept.

## Total

- bets: `21156`
- hits: `4949`
- hit rate: `23.39%`
- profit: `141,560 yen`
- ROI: `106.69%`

## Rolling Summary

| target_month | train_start | train_end | target_start | target_end | quality_candidate_count | selected_logic_count | dedup_bets | dedup_hits | dedup_hit_rate_pct | dedup_profit_yen | dedup_roi_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-01-11_to_2025-02-10 | 2024-10-01 | 2024-12-31 | 2025-01-11 | 2025-02-10 | 43 | 10 | 2534 | 587 | 23.16 | 26130 | 110.31 |
| 2025-02-11_to_2025-03-10 | 2024-11-01 | 2025-01-31 | 2025-02-11 | 2025-03-10 | 41 | 10 | 2294 | 570 | 24.85 | 35860 | 115.63 |
| 2025-03-11_to_2025-04-10 | 2024-12-01 | 2025-02-28 | 2025-03-11 | 2025-04-10 | 30 | 10 | 3081 | 748 | 24.28 | 8880 | 102.88 |
| 2025-04-11_to_2025-05-10 | 2025-01-01 | 2025-03-31 | 2025-04-11 | 2025-05-10 | 32 | 8 | 1738 | 359 | 20.66 | -25460 | 85.35 |
| 2025-05-11_to_2025-06-10 | 2025-02-01 | 2025-04-30 | 2025-05-11 | 2025-06-10 | 21 | 5 | 656 | 131 | 19.97 | -12680 | 80.67 |
| 2025-06-11_to_2025-07-10 | 2025-03-01 | 2025-05-31 | 2025-06-11 | 2025-07-10 | 1 | 1 | 212 | 60 | 28.3 | 6500 | 130.66 |
| 2025-07-11_to_2025-08-10 | 2025-04-01 | 2025-06-30 | 2025-07-11 | 2025-08-10 | 1 | 1 | 239 | 61 | 25.52 | 8970 | 137.53 |
| 2025-08-11_to_2025-09-10 | 2025-05-01 | 2025-07-31 | 2025-08-11 | 2025-09-10 | 3 | 3 | 656 | 88 | 13.41 | -6850 | 89.56 |
| 2025-09-11_to_2025-10-10 | 2025-06-01 | 2025-08-31 | 2025-09-11 | 2025-10-10 | 38 | 10 | 2171 | 552 | 25.43 | 41810 | 119.26 |
| 2025-10-11_to_2025-11-10 | 2025-07-01 | 2025-09-30 | 2025-10-11 | 2025-11-10 | 27 | 10 | 2654 | 573 | 21.59 | -18400 | 93.07 |
| 2025-11-11_to_2025-12-10 | 2025-08-01 | 2025-10-31 | 2025-11-11 | 2025-12-10 | 21 | 10 | 1978 | 536 | 27.1 | 60540 | 130.61 |
| 2025-12-11_to_2026-01-10 | 2025-09-01 | 2025-11-30 | 2025-12-11 | 2026-01-10 | 30 | 10 | 2943 | 684 | 23.24 | 16260 | 105.52 |

## By Combo

| combo | bets | hits | hit_rate_pct | profit_yen | roi_pct |
|---|---|---|---|---|---|
| 1-2 | 11915 | 3020 | 25.35 | 117730 | 109.88 |
| 1-3 | 9241 | 1929 | 20.87 | 23830 | 102.58 |

## Files

- `rolling_summary.csv`
- `all_target_logic_results.csv`
- `portfolio_by_combo.csv`
- one subfolder per forward window
