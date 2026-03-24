# Racer Index Schema Notes

The recommended persisted units are the five objects below.

## 1. racer_indicator_snapshot

One row per `snapshot_date x racer_id`

### Key

- `snapshot_date`
- `racer_id`
- `window_months`
- `profile_version`

### Minimum Columns

- `snapshot_date`
- `racer_id`
- `window_months`
- `profile_version`
- `hist_avg_finish`
- `hist_win_rate`
- `hist_top3_rate`
- `national_win_rate_mean`
- `local_win_rate_mean`
- `class_point_mean`
- `lane1_win_rate`
- `lane1_top3_rate`
- `lane1_avg_finish`
- `lane2_win_rate`
- `lane2_top3_rate`
- `lane2_avg_finish`
- `lane3_win_rate`
- `lane3_top3_rate`
- `lane3_avg_finish`
- `lane4_win_rate`
- `lane4_top3_rate`
- `lane4_avg_finish`
- `lane5_win_rate`
- `lane5_top3_rate`
- `lane5_avg_finish`
- `lane6_win_rate`
- `lane6_top3_rate`
- `lane6_avg_finish`
- `lane1_escape_rate`
- `inner_sashi_like_rate`
- `outer_attack_rate`
- `sample_race_count`

## 2. daily_score_output

One row per `race_id x lane`

### Key

- `race_id`
- `lane`
- `score_version`

### Minimum Columns

- `race_id`
- `race_date`
- `stadium_code`
- `race_no`
- `lane`
- `racer_id`
- `window_months`
- `weight_version`
- `score_version`
- `base_score_100`
- `racer_adjustment`
- `lane_adjustment`
- `style_adjustment`
- `same_day_adjustment`
- `lane_coef`
- `final_score`
- `pred_rank`
- `pred_gap_vs_lane1`
- `pred_gap_vs_pred2`

## 3. daily_pred6

One row per `race_id`

### Key

- `race_id`
- `score_version`

### Minimum Columns

- `race_id`
- `race_date`
- `score_version`
- `pred6_lane`
- `pred6_racer_id`
- `pred6_score`
- `pred5_lane`
- `pred5_score`
- `score_gap_5v6`

## 4. daily_pred1_signal

One row per `race_id`

### Key

- `race_id`
- `score_version`

### Minimum Columns

- `race_id`
- `race_date`
- `score_version`
- `pred1_lane`
- `pred1_racer_id`
- `pred1_score`
- `pred2_lane`
- `pred2_score`
- `pred3_lane`
- `pred3_score`
- `lane1_score`
- `pred1_is_not_lane1`
- `lane1_pred_rank`
- `score_gap_pred1_vs_lane1`
- `score_gap_pred1_vs_pred2`

## 5. prediction_settlement

One row per `race_id x signal_name`

### Key

- `race_id`
- `signal_name`
- `score_version`

### Minimum Columns

- `race_id`
- `race_date`
- `signal_name`
- `score_version`
- `bet_style`
- `bet_count`
- `stake_yen`
- `hit_flag`
- `return_yen`
- `roi_pct`
- `first_place_lane`
- `second_place_lane`
- `third_place_lane`
- `exacta_combo`
- `exacta_payout`
- `trifecta_combo`
- `trifecta_payout`

## Design Notes

- keep `snapshot` and `score` separate
- keep `signal` and `settlement` separate
- always store `window_months` and `weight_version`
- later we can add `run_id` or `input_hash` for stronger replayability
