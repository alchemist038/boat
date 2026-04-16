# Live Trigger CLI Real Trade Performance

- generated_at: 2026-04-17 00:05:59 JST
- system_db: `C:\CODEX_WORK\boat_clone\live_trigger_cli\data\system.db`
- results_db: `\\038INS\boat\data\silver\boat_race.duckdb`
- scope: `bet_executions.execution_status=submitted` and `execution_mode in (assist_real, armed_real)`
- note: `live_trigger_fresh_exec` validation DB is excluded from this report

## Overall

- sample_races: `146`
- submitted_bet_rows: `760`
- winning_races: `14`
- winning_bet_rows: `14`
- race_hit_rate: `9.59%`
- bet_row_hit_rate: `1.84%`
- stake: `87,400 yen`
- return: `53,740 yen`
- pnl: `-33,660 yen`
- ROI: `61.49%`
- max_drawdown: `-36,060 yen`
- max_drawdown_window: `None` -> `2026-04-14`
- unsettled_sample_races: `12`

## By Profile

| profile_id | sample_races | bet_rows | winning_races | race_hit_rate | winning_bet_rows | bet_row_hit_rate | stake | return | pnl | ROI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 125_broad_four_stadium | 7 | 7 | 0 | 0.00% | 0 | 0.00% | 7,800 yen | 0 yen | -7,800 yen | 0.00% |
| 4wind_base_415 | 5 | 10 | 0 | 0.00% | 0 | 0.00% | 1,000 yen | 0 yen | -1,000 yen | 0.00% |
| c2_provisional_v1 | 8 | 240 | 2 | 25.00% | 2 | 0.83% | 24,000 yen | 2,770 yen | -21,230 yen | 11.54% |
| h_a_final_day_cut_v1 | 43 | 43 | 1 | 2.33% | 1 | 2.33% | 8,600 yen | 1,060 yen | -7,540 yen | 12.33% |
| l1_weak_234_box_v1 | 45 | 270 | 3 | 6.67% | 3 | 1.11% | 27,000 yen | 22,310 yen | -4,690 yen | 82.63% |
| l3_weak_124_box_one_a_ex241_v1 | 38 | 190 | 8 | 21.05% | 8 | 4.21% | 19,000 yen | 27,600 yen | 8,600 yen | 145.26% |

## Unsettled Sample Races

| race_date | race_id | profile_id |
| --- | --- | --- |
| 2026-04-16 | 202604160210 | l1_weak_234_box_v1 |
| 2026-04-16 | 202604160307 | h_a_final_day_cut_v1 |
| 2026-04-16 | 202604160803 | 4wind_base_415 |
| 2026-04-16 | 202604160807 | l1_weak_234_box_v1 |
| 2026-04-16 | 202604160808 | h_a_final_day_cut_v1 |
| 2026-04-16 | 202604160810 | l3_weak_124_box_one_a_ex241_v1 |
| 2026-04-16 | 202604160908 | c2_provisional_v1 |
| 2026-04-16 | 202604161206 | l3_weak_124_box_one_a_ex241_v1 |
| 2026-04-16 | 202604161606 | l1_weak_234_box_v1 |
| 2026-04-16 | 202604161612 | l1_weak_234_box_v1 |
| 2026-04-16 | 202604162006 | l3_weak_124_box_one_a_ex241_v1 |
| 2026-04-16 | 202604162101 | l1_weak_234_box_v1 |
