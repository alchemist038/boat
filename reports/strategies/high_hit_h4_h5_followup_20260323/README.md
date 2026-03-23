# H-004 / H-005 Follow-Up 2026-03-23

## Scope

- source package: `GPT/output/2023-03-11_2023-09-10_high_hit_discovery`
- origin note: `H-001/H-002/H-003` drove the later `1-2 / 1-3` structural exploration
- this follow-up checks the two deferred ideas:
  - `H-004`: exacta `1-3`
  - `H-005`: trifecta `1-2-3`

## Translation Rule

- `H-004` came from `summary_lane1_partner_scan.csv`, so it is evaluated by:
  - selecting discovery-time partner groups that satisfy:
    - `lane1_exgap_bucket = '>0.10'`
    - `lane1_st_bucket = 'near_even'`
    - `best_partner_lane = 3`
  - then applying those same group keys to later periods
- `H-005` came from `summary_lane1_context_scan.csv`, so it is evaluated directly on raw race rows with:
  - `lane1_exrank_bucket = '1'`
  - `lane23_pressure_group = 'lane23_weak'`
  - `wind_bucket = '0-2'`

## H-004 Discovery Partner Groups

| grade_group | wind_bucket | lane1_class | lane1_exgap_bucket | lane1_st_bucket | lane23_pressure_group | races | lane1_win_count | partner2_hits | partner3_hits | partner4_hits | partner5_hits | partner6_hits | lane1_win_rate_pct | exacta_12_rate_pct | exacta_13_rate_pct | exacta_14_rate_pct | rough_race_pct | best_partner_lane | best_partner_share_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| general | 3-4 | B1 | >0.10 | near_even | lane23_one_A | 89 | 35.0 | 7.0 | 13.0 | 12.0 | 0.0 | 3.0 | 39.33 | 7.87 | 14.61 | 13.48 | 20.22 | 3 | 37.14 |

## H-004 Summary

| period | races | unique_races | lane1_win_rate_pct | exacta_12_rate_pct | exacta_13_rate_pct | exacta_12_or_13_rate_pct | roi_13_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| discovery_6m | 89 | 89 | 39.33 | 7.87 | 14.61 | 22.47 | 108.09 |
| y2023_extended | 142 | 142 | 38.73 | 14.08 | 12.68 | 26.76 | 107.68 |
| y2024_forward | 167 | 167 | 31.14 | 7.19 | 10.78 | 17.96 | 91.44 |

## H-005 Summary

| period | races | exacta_12_rate_pct | exacta_13_rate_pct | trifecta_123_rate_pct | trifecta_132_rate_pct | trifecta_123_or_132_rate_pct | roi_123_pct | roi_123_132_pair_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| discovery_6m | 1343 | 21.3 | 16.6 | 7.82 | 5.96 | 13.78 | 103.73 | 93.16 |
| y2023_extended | 2213 | 19.97 | 17.22 | 7.37 | 5.2 | 12.56 | 96.78 | 88.47 |
| y2024_forward | 2753 | 18.96 | 17.84 | 6.25 | 6.07 | 12.31 | 82.91 | 87.48 |
