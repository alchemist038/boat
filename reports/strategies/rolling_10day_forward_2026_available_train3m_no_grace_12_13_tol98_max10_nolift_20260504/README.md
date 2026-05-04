# Rolling 10-Day Forward 1-2/1-3 No-Grace Backtest

## Method

- Train period: previous `3` full months only.
- Grace period: day `1` to `10` of the cycle month is not used for training or scoring.
- Forward period: day `11` of the cycle month through day `10` of the next month.
- Candidate combos: `1-2`, `1-3` only.
- Candidate filters: sample >= `300`, ROI >= `108.0`, ROI lift >= `-9999.0`, profit > 0.
- Monthly stability: at least `2` positive months, and no sampled month below `98.0` ROI.
- Selection: max `10` candidates, max `5` per combo, duplicate race-set removal.
- Portfolio accounting deduplicates only by `race_id + combo`; `1-2` and `1-3` in the same race are both kept.

## Total

- bets: `5953`
- hits: `1444`
- hit rate: `24.26%`
- profit: `56,480 yen`
- ROI: `109.49%`

## Rolling Summary

| target_month | train_start | train_end | target_start | target_end | quality_candidate_count | selected_logic_count | dedup_bets | dedup_hits | dedup_hit_rate_pct | dedup_profit_yen | dedup_roi_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01-11_to_2026-02-10 | 2025-10-01 | 2025-12-31 | 2026-01-11 | 2026-02-10 | 34 | 10 | 3103 | 816 | 26.3 | 54590 | 117.59 |
| 2026-02-11_to_2026-03-10 | 2025-11-01 | 2026-01-31 | 2026-02-11 | 2026-03-10 | 43 | 10 | 1661 | 401 | 24.14 | 19520 | 111.75 |
| 2026-03-11_to_2026-04-10 | 2025-12-01 | 2026-02-28 | 2026-03-11 | 2026-04-10 | 34 | 10 | 1108 | 210 | 18.95 | -15690 | 85.84 |
| 2026-04-11_to_2026-05-10 | 2026-01-01 | 2026-03-31 | 2026-04-11 | 2026-05-10 | 3 | 1 | 81 | 17 | 20.99 | -1940 | 76.05 |
| 2026-05-11_to_2026-06-10 | 2026-02-01 | 2026-04-30 | 2026-05-11 | 2026-06-10 | 0 | 0 | 0 | 0 | 0.0 | 0 | 0.0 |

## By Combo

| combo | bets | hits | hit_rate_pct | profit_yen | roi_pct |
|---|---|---|---|---|---|
| 1-2 | 2985 | 788 | 26.4 | 29000 | 109.72 |
| 1-3 | 2968 | 656 | 22.1 | 27480 | 109.26 |

## Files

- `rolling_summary.csv`
- `all_target_logic_results.csv`
- `portfolio_by_combo.csv`
- one subfolder per forward window
