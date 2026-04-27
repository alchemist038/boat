# Live Trigger CLI Forward Logic Performance

- generated_at: 2026-04-23 22:47:28 JST
- cutoff_date: `2026-04-22`
- scope: `bet_executions.execution_status=submitted` and `execution_mode in (assist_real, armed_real)`
- normalization: `100 yen flat per expanded bet row`
- unit: race-level performance, not bet-row hit rate
- system_db: `C:\CODEX_WORK\boat_clone\live_trigger_cli\data\system.db`
- settings_json: `C:\CODEX_WORK\boat_clone\live_trigger_cli\data\settings.json`
- results_db: `\\038INS\boat\data\silver\boat_race.duckdb`
- active_forward_profiles: `125_broad_four_stadium, 4wind_base_415, c2_provisional_v1, h_a_final_day_cut_v1, l3_weak_124_box_one_a_ex241_v1, l1_weak_234_box_v1`
- include_inactive_profiles: `False`

## Overall

- sample_races: `211`
- hit_races: `19`
- race_hit_rate: `9.00%`
- avg_tickets_per_race: `4.99`
- flat_stake: `105,300 yen`
- flat_return: `69,910 yen`
- flat_pnl: `-35,390 yen`
- flat_roi: `66.39%`
- unsettled_sample_races: `0`

## By Logic

| logic | profile_id | sample_races | hit_races | race_hit_rate | avg_tickets_per_race | flat_stake | flat_return | flat_pnl | flat_roi | avg_hit_payout |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 125 | 125_broad_four_stadium | 8 | 0 | 0.00% | 1.00 | 800 yen | 0 yen | -800 yen | 0.00% | 0 yen |
| 4wind | 4wind_base_415 | 6 | 0 | 0.00% | 2.00 | 1,200 yen | 0 yen | -1,200 yen | 0.00% | 0 yen |
| c2 | c2_provisional_v1 | 9 | 2 | 22.22% | 28.67 | 25,800 yen | 2,770 yen | -23,030 yen | 10.74% | 1,385 yen |
| H-A | h_a_final_day_cut_v1 | 59 | 1 | 1.69% | 1.00 | 5,900 yen | 1,060 yen | -4,840 yen | 17.97% | 1,060 yen |
| l3_124 | l3_weak_124_box_one_a_ex241_v1 | 58 | 10 | 17.24% | 5.00 | 29,000 yen | 30,270 yen | 1,270 yen | 104.38% | 3,027 yen |
| l1_234 | l1_weak_234_box_v1 | 71 | 6 | 8.45% | 6.00 | 42,600 yen | 35,810 yen | -6,790 yen | 84.06% | 5,968 yen |

## Files

- `logic_summary.csv`: one row per current logic/profile
- `daily_logic_equity.csv`: daily forward progression per logic
- `overall_summary.json`: top-line summary for automation

## Refresh

Run this command to overwrite the latest report:

```powershell
.\.venv\Scripts\python.exe workspace_codex\scripts\report_live_trigger_cli_forward_logic_performance.py
```
