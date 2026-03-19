# Gemini Request: 2024-01-01 to 2024-04-30 Discovery

## Goal

Use only the discovery period from `2024-01-01` to `2024-04-30` to define what data package you need for zero-base BOAT RACE hypothesis generation.

Important: do not use or infer from any existing human-created strategies, past adopted logic, or prior ROI results. This request is only for data-package design and later hypothesis generation from scratch.

## Constraints

- File upload limit is `10 files` maximum in one batch.
- Prefer fewer, denser files over many small files.
- Markdown is acceptable for instructions and metadata.
- CSV is preferred for numeric/tabular data.
- The next human step after your answer will be out-of-sample backtesting in a separate period, so avoid designing a package that leaks future information.

## Available Source Information

The local DuckDB contains these categories of information:

### 1. races

- `race_id`
- `race_date`
- `stadium_code`, `stadium_name`
- `race_no`
- `meeting_title`, `race_title`
- `distance_m`
- `deadline_time`

### 2. entries

- `lane`
- `racer_id`, `racer_name`
- `racer_class`
- `branch`, `hometown`
- `age`, `weight_kg`
- `f_count`, `l_count`
- `avg_start_timing`
- `national_win_rate`, `national_place_rate`, `national_top3_rate`
- `local_win_rate`, `local_place_rate`, `local_top3_rate`
- `motor_no`, `motor_place_rate`, `motor_top3_rate`
- `boat_no`, `boat_place_rate`, `boat_top3_rate`

### 3. beforeinfo_entries

- `weight_kg_before`
- `adjust_weight_kg`
- `exhibition_time`
- `tilt`
- `course_entry`
- `start_exhibition_st`
- `start_exhibition_status`
- `weather_condition`
- `weather_temp_c`
- `wind_speed_m`
- `wind_direction_code`
- `water_temp_c`
- `wave_height_cm`

### 4. race_meta

- `grade`
- `meeting_day_no`
- `meeting_day_label`
- `is_final_day`

### 5. results

- `first_place_lane`, `second_place_lane`, `third_place_lane`
- `exacta_combo`, `exacta_payout`
- `trifecta_combo`, `trifecta_payout`
- `winning_technique`
- `weather_condition`
- `wind_speed_m`
- `wave_height_cm`

### 6. odds

- `odds_2t`
- `odds_3t`

Odds may be incomplete depending on the period. It is acceptable to prioritize result-based hypothesis generation first.

## Your Task

Please answer the following:

### A. Best input design for you

Tell me what structure is easiest for you to analyze under the 10-file limit:

- one combined package vs multiple files
- race-level file vs entry-level file split
- whether sampled data should be used first
- whether full 4-month data should be sent at once
- which metadata should stay in Markdown

### B. Required files in priority order

List the exact files you want first, within the 10-file limit.

For each file, provide:

- filename
- purpose
- format (`CSV` or `Markdown`)
- must-have columns
- optional columns

### C. Recommended minimal package

Propose the smallest practical first package that I should generate now.

Please keep it realistic for the 10-file upload limit and optimize for fast first-pass hypothesis generation rather than perfect completeness.

### D. Hypothesis output format

When I later give you the actual data package, I want hypotheses in a form that can be backtested mechanically.

Please specify the exact output template you want to use, for example:

- hypothesis id
- condition block
- target ticket type
- ticket pattern
- expected mechanism
- minimum sample guardrail
- why it might generalize

## Hard Rules

- Do not refer to existing human logic, named strategies, or known ROI summaries.
- Do not try to optimize against unseen future data.
- Focus first on data design, not final strategy ideas.
- Favor conditions that can later be expressed in SQL or Python without ambiguity.

## Output Format

Please respond in this order:

1. Short overall recommendation
2. Priority file list as a table
3. Minimal first package recommendation
4. Preferred hypothesis-output template
5. Any warnings about information leakage or overfitting

