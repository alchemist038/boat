# Rolling 10-Day Train Forward Distortion Backtest

## Method

- Train on the previous `3` months plus the first `10` days of the cycle month.
- Forward/practice period: day `11` of the cycle month through day `10` of the next month.
- Candidate extraction is the same exacta `1-X` distortion scan used by the monthly rolling test.
- Portfolio accounting deduplicates only by `race_id + combo`; different combos in the same race are both kept.

## Overall Portfolio

- bets: `7341`
- hits: `1214`
- hit rate: `16.54%`
- profit: `-8,490 yen`
- ROI: `98.84%`

## 1-2 / 1-3 Focus

- bets: `3947`
- hits: `950`
- hit rate: `24.07%`
- profit: `33,110 yen`
- ROI: `108.39%`

## Rolling Summary

| target_month | train_start | train_end | target_start | target_end | selected_logic_count | dedup_bets | dedup_hits | dedup_hit_rate_pct | dedup_profit_yen | dedup_roi_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01-11_to_2026-02-10 | 2025-10-01 | 2026-01-10 | 2026-01-11 | 2026-02-10 | 12 | 2988 | 648 | 21.69 | 70370 | 123.55 |
| 2026-02-11_to_2026-03-10 | 2025-11-01 | 2026-02-10 | 2026-02-11 | 2026-03-10 | 12 | 1577 | 236 | 14.97 | 4710 | 102.99 |
| 2026-03-11_to_2026-04-10 | 2025-12-01 | 2026-03-10 | 2026-03-11 | 2026-04-10 | 12 | 1392 | 159 | 11.42 | -45340 | 67.43 |
| 2026-04-11_to_2026-05-10 | 2026-01-01 | 2026-04-10 | 2026-04-11 | 2026-05-10 | 12 | 1384 | 171 | 12.36 | -38230 | 72.38 |

## By Combo

| combo | bets | hits | hit_rate_pct | profit_yen | roi_pct |
|---|---|---|---|---|---|
| 1-2 | 1654 | 435 | 26.3 | 6670 | 104.03 |
| 1-3 | 2293 | 515 | 22.46 | 26440 | 111.53 |
| 1-4 | 600 | 83 | 13.83 | -4120 | 93.13 |
| 1-5 | 961 | 68 | 7.08 | -28750 | 70.08 |
| 1-6 | 1833 | 113 | 6.16 | -8730 | 95.24 |

## 1-2 / 1-3 Monthly

| target_window | bets | hits | hit_rate_pct | profit_yen | roi_pct |
|---|---|---|---|---|---|
| 2026-01-11_to_2026-02-10 | 1995 | 549 | 27.52 | 47810 | 123.96 |
| 2026-02-11_to_2026-03-10 | 797 | 182 | 22.84 | 12100 | 115.18 |
| 2026-03-11_to_2026-04-10 | 561 | 101 | 18.0 | -16280 | 70.98 |
| 2026-04-11_to_2026-05-10 | 594 | 118 | 19.87 | -10520 | 82.29 |

## Files

- `rolling_summary.csv`
- `all_target_logic_results.csv`
- `portfolio_by_combo.csv`
- `portfolio_12_13_monthly.csv`
- one subfolder per forward window
