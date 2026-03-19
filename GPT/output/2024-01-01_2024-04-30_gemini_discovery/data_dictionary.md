# Data Dictionary

## Package Scope

- discovery period: `2024-01-01` to `2024-04-30`
- sample size: `1000` races
- sampling rule: deterministic hash order by `race_id` with seed `20260319`
- included files:
  - `races_sample.csv`
  - `entries_sample.csv`
  - `data_dictionary.md`
  - `package_note.md`
  - `gemini_request_2024-01-01_2024-04-30_discovery.md`

## Join Key

- `race_id` is the primary join key between race-level and entry-level files.

## races_sample.csv

- `race_id`: unique race key
- `race_date`: race date
- `stadium_code`: 2-digit stadium code
- `stadium_name`: stadium name
- `race_no`: race number
- `distance_m`: course distance in meters
- `grade`: meeting grade such as SG/G1/general
- `meeting_day_no`: numeric day index within the meeting
- `meeting_day_label`: text label for meeting day
- `is_final_day`: 1 if final day, else 0
- `weather_condition`: resolved weather text
- `weather_temp_c`: air temperature in Celsius
- `wind_speed_m`: wind speed in m/s
- `wind_direction_code`: official wind-direction code
- `water_temp_c`: water temperature in Celsius
- `wave_height_cm`: wave height in cm
- `first_place_lane`: winning lane
- `second_place_lane`: second-place lane
- `third_place_lane`: third-place lane
- `exacta_combo`: official 2T combo
- `exacta_payout`: official 2T payout in yen
- `trifecta_combo`: official 3T combo
- `trifecta_payout`: official 3T payout in yen
- `winning_technique`: official kimarite
- `a1_count`: number of A1 racers in the field
- `a2_count`: number of A2 racers in the field
- `b1_count`: number of B1 racers in the field
- `b2_count`: number of B2 racers in the field
- `avg_national_win_rate`: race-level average of national win rate across 6 boats
- `max_national_win_rate`: highest national win rate in the race
- `lane1_national_win_rate`: lane-1 racer national win rate
- `lane1_local_win_rate`: lane-1 racer local win rate
- `lane1_motor_place_rate`: lane-1 racer motor place rate
- `best_exhibition_time`: fastest exhibition time in the race
- `best_exhibition_lane`: lane with fastest exhibition time
- `lane1_vs_best_exhibition_diff`: lane-1 exhibition time minus best exhibition time
- `is_rough_race`: 1 if exacta payout >= 5000 or trifecta payout >= 10000, else 0

## entries_sample.csv

- `race_id`: foreign key to race-level file
- `race_date`: race date
- `stadium_code`: 2-digit stadium code
- `stadium_name`: stadium name
- `race_no`: race number
- `grade`: meeting grade
- `meeting_day_no`: numeric day index within the meeting
- `meeting_day_label`: text label for meeting day
- `is_final_day`: 1 if final day, else 0
- `lane`: official lane number
- `racer_id`: racer id
- `racer_name`: racer name
- `racer_class`: A1/A2/B1/B2
- `branch`: branch text from source
- `hometown`: hometown text from source
- `age`: racer age
- `weight_kg`: listed racer weight
- `weight_kg_before`: pre-race weight
- `adjust_weight_kg`: adjustment weight
- `f_count`: F count
- `l_count`: L count
- `avg_start_timing`: average start timing
- `national_win_rate`: national win rate
- `national_place_rate`: national place rate
- `national_top3_rate`: national top-3 rate
- `local_win_rate`: local win rate
- `local_place_rate`: local place rate
- `local_top3_rate`: local top-3 rate
- `motor_no`: motor number
- `motor_place_rate`: motor place rate
- `motor_top3_rate`: motor top-3 rate
- `boat_no`: boat number
- `boat_place_rate`: boat place rate
- `boat_top3_rate`: boat top-3 rate
- `exhibition_time`: exhibition time
- `tilt`: tilt
- `course_entry`: exhibition course entry
- `start_exhibition_st`: exhibition ST
- `start_exhibition_status`: exhibition status text
- `weather_condition`: resolved weather text
- `weather_temp_c`: air temperature in Celsius
- `wind_speed_m`: wind speed in m/s
- `wind_direction_code`: official wind-direction code
- `water_temp_c`: water temperature in Celsius
- `wave_height_cm`: wave height in cm
- `first_place_lane`: winning lane
- `second_place_lane`: second-place lane
- `third_place_lane`: third-place lane
- `is_winner`: 1 if this lane won
- `is_top2`: 1 if this lane finished top 2
- `is_top3`: 1 if this lane finished top 3
- `exhibition_time_rank`: race-internal rank of exhibition time, smaller is better
- `exhibition_time_diff_from_top`: exhibition time minus best exhibition time in the same race
- `win_rate_rank`: race-internal rank of national win rate, smaller is stronger
- `st_diff_from_inside`: exhibition ST minus inside-adjacent lane ST; null for lane 1
- `is_hometown`: 1 if `branch == stadium_code`, else 0

## Notes

- This package is for discovery only.
- Existing human strategy names and ROI summaries should not be used.
- These files are intentionally compact to stay well under a 10-file upload limit.
