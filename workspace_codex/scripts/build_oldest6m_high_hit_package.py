from __future__ import annotations

import csv
from pathlib import Path

import duckdb


DB_PATH = Path(r"D:\boat\data\silver\boat_race.duckdb")
OUTPUT_DIR = Path(r"D:\boat\GPT\output\2023-03-11_2023-09-10_high_hit_discovery")

START_DATE = "2023-03-11"
END_DATE = "2023-09-10"
SAMPLE_RACES = 1200
SEED = 20260322


def write_csv(con: duckdb.DuckDBPyConnection, query: str, path: Path) -> int:
    result = con.execute(query)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def values_sql(race_ids: list[str]) -> str:
    return ", ".join(f"('{race_id}')" for race_id in race_ids)


def build_entry_features_query(*, start_date: str, end_date: str) -> str:
    return f"""
WITH base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    r.stadium_name,
    e.race_no,
    rm.meeting_title,
    r.race_title,
    rm.grade,
    rm.meeting_day_no,
    rm.meeting_day_label,
    rm.is_final_day,
    e.lane,
    e.racer_id,
    e.racer_name,
    e.racer_class,
    e.branch,
    e.hometown,
    e.age,
    e.weight_kg,
    bi.weight_kg_before,
    bi.adjust_weight_kg,
    e.f_count,
    e.l_count,
    e.avg_start_timing,
    e.national_win_rate,
    e.national_place_rate,
    e.national_top3_rate,
    e.local_win_rate,
    e.local_place_rate,
    e.local_top3_rate,
    e.motor_no,
    e.motor_place_rate,
    e.motor_top3_rate,
    e.boat_no,
    e.boat_place_rate,
    e.boat_top3_rate,
    bi.exhibition_time,
    bi.tilt,
    bi.course_entry,
    bi.start_exhibition_st,
    bi.start_exhibition_status,
    COALESCE(bi.weather_condition, res.weather_condition) AS weather_condition,
    COALESCE(bi.weather_temp_c, res.weather_temp_c) AS weather_temp_c,
    COALESCE(bi.wind_speed_m, res.wind_speed_m) AS wind_speed_m,
    COALESCE(bi.wind_direction_code, res.wind_direction_code) AS wind_direction_code,
    COALESCE(bi.water_temp_c, res.water_temp_c) AS water_temp_c,
    COALESCE(bi.wave_height_cm, res.wave_height_cm) AS wave_height_cm,
    res.first_place_lane,
    res.second_place_lane,
    res.third_place_lane,
    res.exacta_combo,
    res.exacta_payout,
    res.trifecta_combo,
    res.trifecta_payout,
    res.winning_technique,
    CASE WHEN res.first_place_lane = e.lane THEN 1 ELSE 0 END AS is_winner,
    CASE WHEN e.lane IN (res.first_place_lane, res.second_place_lane) THEN 1 ELSE 0 END AS is_top2,
    CASE WHEN e.lane IN (res.first_place_lane, res.second_place_lane, res.third_place_lane) THEN 1 ELSE 0 END AS is_top3
  FROM entries e
  JOIN races r USING (race_id)
  LEFT JOIN race_meta rm USING (race_id)
  LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
  LEFT JOIN results res USING (race_id)
  WHERE e.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
),
enriched AS (
  SELECT
    *,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN exhibition_time IS NULL THEN 1 ELSE 0 END,
        exhibition_time ASC,
        lane ASC
    ) AS exhibition_time_rank,
    ROUND(
      exhibition_time - MIN(exhibition_time) OVER (PARTITION BY race_id),
      3
    ) AS exhibition_time_diff_from_top,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN national_win_rate IS NULL THEN 1 ELSE 0 END,
        national_win_rate DESC,
        lane ASC
    ) AS win_rate_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN start_exhibition_st IS NULL THEN 1 ELSE 0 END,
        start_exhibition_st ASC,
        lane ASC
    ) AS exhibition_st_rank
  FROM base
)
SELECT *
FROM enriched
ORDER BY race_date, stadium_code, race_no, lane
"""


def build_race_context_query(feature_query: str) -> str:
    return f"""
WITH feature_base AS ({feature_query}),
race_base AS (
  SELECT
    race_id,
    MIN(race_date) AS race_date,
    MIN(stadium_code) AS stadium_code,
    MIN(stadium_name) AS stadium_name,
    MIN(race_no) AS race_no,
    MIN(meeting_title) AS meeting_title,
    MIN(race_title) AS race_title,
    MAX(grade) AS grade,
    MAX(meeting_day_no) AS meeting_day_no,
    MIN(meeting_day_label) AS meeting_day_label,
    MAX(is_final_day) AS is_final_day,
    MIN(weather_condition) AS weather_condition,
    MAX(wind_speed_m) AS wind_speed_m,
    MAX(wave_height_cm) AS wave_height_cm,
    MAX(first_place_lane) AS first_place_lane,
    MAX(second_place_lane) AS second_place_lane,
    MAX(third_place_lane) AS third_place_lane,
    MAX(exacta_combo) AS exacta_combo,
    MAX(exacta_payout) AS exacta_payout,
    MAX(trifecta_combo) AS trifecta_combo,
    MAX(trifecta_payout) AS trifecta_payout,
    MAX(winning_technique) AS winning_technique,
    SUM(CASE WHEN racer_class = 'A1' THEN 1 ELSE 0 END) AS a1_count,
    SUM(CASE WHEN racer_class = 'A2' THEN 1 ELSE 0 END) AS a2_count,
    SUM(CASE WHEN racer_class = 'B1' THEN 1 ELSE 0 END) AS b1_count,
    SUM(CASE WHEN racer_class = 'B2' THEN 1 ELSE 0 END) AS b2_count,
    MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
    MAX(CASE WHEN lane = 2 THEN racer_class END) AS lane2_class,
    MAX(CASE WHEN lane = 3 THEN racer_class END) AS lane3_class,
    ROUND(MAX(CASE WHEN lane = 1 THEN national_win_rate END), 3) AS lane1_national_win_rate,
    ROUND(MAX(CASE WHEN lane = 2 THEN national_win_rate END), 3) AS lane2_national_win_rate,
    ROUND(MAX(CASE WHEN lane = 3 THEN national_win_rate END), 3) AS lane3_national_win_rate,
    ROUND(MAX(CASE WHEN lane = 1 THEN motor_place_rate END), 3) AS lane1_motor_place_rate,
    ROUND(MAX(CASE WHEN lane = 2 THEN motor_place_rate END), 3) AS lane2_motor_place_rate,
    ROUND(MAX(CASE WHEN lane = 3 THEN motor_place_rate END), 3) AS lane3_motor_place_rate,
    ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time END), 3) AS lane1_exhibition_time,
    ROUND(MAX(CASE WHEN lane = 2 THEN exhibition_time END), 3) AS lane2_exhibition_time,
    ROUND(MAX(CASE WHEN lane = 3 THEN exhibition_time END), 3) AS lane3_exhibition_time,
    MAX(CASE WHEN lane = 1 THEN exhibition_time_rank END) AS lane1_exhibition_rank,
    MAX(CASE WHEN lane = 2 THEN exhibition_time_rank END) AS lane2_exhibition_rank,
    MAX(CASE WHEN lane = 3 THEN exhibition_time_rank END) AS lane3_exhibition_rank,
    ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time_diff_from_top END), 3) AS lane1_exhibition_diff_from_top,
    ROUND(MAX(CASE WHEN lane = 1 THEN start_exhibition_st END), 3) AS lane1_start_exhibition_st,
    ROUND(MAX(CASE WHEN lane = 2 THEN start_exhibition_st END), 3) AS lane2_start_exhibition_st,
    ROUND(MAX(CASE WHEN lane = 3 THEN start_exhibition_st END), 3) AS lane3_start_exhibition_st,
    SUM(CASE WHEN lane IN (2, 3) AND racer_class IN ('A1', 'A2') THEN 1 ELSE 0 END) AS lane23_a_count,
    SUM(CASE WHEN lane IN (2, 3) AND racer_class = 'B2' THEN 1 ELSE 0 END) AS lane23_b2_count,
    CASE WHEN MAX(first_place_lane) = 1 THEN 1 ELSE 0 END AS lane1_win,
    CASE WHEN MAX(first_place_lane) = 1 OR MAX(second_place_lane) = 1 THEN 1 ELSE 0 END AS lane1_top2,
    CASE WHEN MAX(first_place_lane) = 1 AND MAX(second_place_lane) = 2 THEN 1 ELSE 0 END AS exacta_12_hit,
    CASE WHEN MAX(first_place_lane) = 1 AND MAX(second_place_lane) = 3 THEN 1 ELSE 0 END AS exacta_13_hit,
    CASE
      WHEN MAX(exacta_payout) >= 5000 OR MAX(trifecta_payout) >= 10000 THEN 1
      ELSE 0
    END AS rough_race_flag
  FROM feature_base
  GROUP BY race_id
),
with_l23 AS (
  SELECT
    *,
    CASE
      WHEN lane2_start_exhibition_st IS NULL THEN lane3_start_exhibition_st
      WHEN lane3_start_exhibition_st IS NULL THEN lane2_start_exhibition_st
      ELSE LEAST(lane2_start_exhibition_st, lane3_start_exhibition_st)
    END AS best_l23_start_exhibition_st
  FROM race_base
),
bucketed AS (
  SELECT
    *,
    ROUND(
      lane1_start_exhibition_st - best_l23_start_exhibition_st,
      3
    ) AS lane1_st_vs_best_l23,
    CASE
      WHEN grade IN ('SG', 'G1') THEN grade
      ELSE 'general'
    END AS grade_group,
    CASE
      WHEN meeting_day_no IS NULL THEN 'unknown'
      WHEN is_final_day = 1 THEN 'final'
      WHEN meeting_day_no <= 2 THEN 'day1-2'
      WHEN meeting_day_no <= 4 THEN 'day3-4'
      ELSE 'day5+'
    END AS meeting_phase_bucket,
    CASE
      WHEN wind_speed_m IS NULL THEN 'unknown'
      WHEN wind_speed_m <= 2 THEN '0-2'
      WHEN wind_speed_m <= 4 THEN '3-4'
      WHEN wind_speed_m <= 6 THEN '5-6'
      ELSE '7+'
    END AS wind_bucket,
    CASE
      WHEN wave_height_cm IS NULL THEN 'unknown'
      WHEN wave_height_cm <= 4 THEN '0-4'
      WHEN wave_height_cm <= 9 THEN '5-9'
      ELSE '10+'
    END AS wave_bucket,
    CASE
      WHEN lane1_exhibition_rank IS NULL THEN 'missing'
      WHEN lane1_exhibition_rank = 1 THEN '1'
      WHEN lane1_exhibition_rank = 2 THEN '2'
      ELSE '3+'
    END AS lane1_exrank_bucket,
    CASE
      WHEN lane1_exhibition_diff_from_top IS NULL THEN 'missing'
      WHEN lane1_exhibition_diff_from_top <= 0.02 THEN '<=0.02'
      WHEN lane1_exhibition_diff_from_top <= 0.05 THEN '0.021-0.05'
      WHEN lane1_exhibition_diff_from_top <= 0.10 THEN '0.051-0.10'
      ELSE '>0.10'
    END AS lane1_exgap_bucket,
    CASE
      WHEN lane1_start_exhibition_st IS NULL OR best_l23_start_exhibition_st IS NULL THEN 'missing'
      WHEN lane1_start_exhibition_st - best_l23_start_exhibition_st <= -0.03 THEN 'lane1_faster'
      WHEN lane1_start_exhibition_st - best_l23_start_exhibition_st <= 0.02 THEN 'near_even'
      ELSE 'lane1_slower'
    END AS lane1_st_bucket,
    CASE
      WHEN lane23_a_count = 0 THEN 'lane23_weak'
      WHEN lane23_a_count = 1 THEN 'lane23_one_A'
      ELSE 'lane23_two_A'
    END AS lane23_pressure_group
  FROM with_l23
)
SELECT *
FROM bucketed
ORDER BY race_date, stadium_code, race_no, race_id
"""


def build_readme(file_count: int) -> str:
    return f"""# Oldest 6M High-Hit Discovery Package

## Scope

- discovery period: `{START_DATE}` to `{END_DATE}`
- purpose: generate zero-base, high-hit-rate candidate betting logic from the oldest 6-month slice
- design priority:
  - preserve as much forward period as possible
  - reject systems that break quickly
  - prefer stable race-shape logic over market-distortion logic

## Hard Isolation Rule

- Treat the LLM session as a fully isolated thread.
- The LLM must not use any previous conversation, previous upload batch, prior named strategy, earlier hypothesis, or memory from another thread.
- If a fact is not present in the uploaded files, it must be treated as unknown.

## File Budget

- total files in this package: `{file_count}`
- all package files are Markdown or CSV
- this package stays under the `10-file` upload limit

## File List

1. `README.md`
2. `llm_prompt_high_hit_oldest6m.md`
3. `thread_gate_01_schema_manifest.md`
4. `thread_gate_02_hypothesis_request.md`
5. `data_dictionary.md`
6. `races_sample.csv`
7. `entries_sample.csv`
8. `summary_lane_baseline.csv`
9. `summary_lane1_context_scan.csv`
10. `summary_lane1_partner_scan.csv`

## Recommended Upload

- upload all files in this folder together in one batch
- the two sample files provide raw discovery context
- the three summary files make the high-hit-rate lens easier to infer
- for a fresh thread, use `thread_gate_01_schema_manifest.md` first
- only after that passes, use `thread_gate_02_hypothesis_request.md`

## Important Note

- payout-based rough-race fields in this package are discovery labels only
- they are included to help identify stable vs chaotic contexts
- they should not automatically become future runtime conditions
"""


def build_prompt() -> str:
    return f"""# LLM Request: Oldest 6M High-Hit Discovery

## Goal

Using only the uploaded package from the discovery period `{START_DATE}` to `{END_DATE}`, generate a small set of zero-base BOAT RACE betting hypotheses that prioritize hit rate and stability.

This is intentionally a different lens from market-distortion logic.

## Thread Isolation Rule

- Treat this as a fully isolated thread.
- Do not use any prior conversation, prior uploaded package, previous strategy names, earlier hypotheses, old notes, or memory from another thread.
- Do not refer to known human-created logic.
- If something is not explicitly present in the uploaded files, treat it as unknown.

## Core Direction

- prioritize high hit rate over flashy payout
- prioritize stable race shapes over market mispricing
- prefer simple, mechanical, testable rules
- preserve as much forward period as possible
- assume that a system that breaks quickly after discovery is not useful

## What Not To Do

- do not build the core logic around odds mispricing
- do not optimize around one-off longshots
- do not use payout bands as the main future betting condition
- do not propose wide, low-hit trifecta coverage unless it is strongly justified

## Files You Have

- `README.md`
- `data_dictionary.md`
- `races_sample.csv`
- `entries_sample.csv`
- `summary_lane_baseline.csv`
- `summary_lane1_context_scan.csv`
- `summary_lane1_partner_scan.csv`

## Mandatory Grounding Step

Before generating hypotheses, inspect the actual CSV headers and the data dictionary.

- do not rely on memory
- do not infer missing columns
- do not invent bucket values
- if a column name or bucket value is not explicitly present in the uploaded files, do not use it

## How To Read The Package

- `races_sample.csv`
  - deterministic race-level sample for qualitative pattern reading
- `entries_sample.csv`
  - entry-level sample for race-internal comparisons
- `summary_lane_baseline.csv`
  - lane/class/exhibition-rank/wind baselines across the full discovery period
- `summary_lane1_context_scan.csv`
  - full-period scan of lane-1 stability contexts
- `summary_lane1_partner_scan.csv`
  - full-period scan of lane-1 win contexts and second-place partner concentration

## Discovery Philosophy

Use the package to find logic that answers questions like:

- when is lane 1 truly stable enough to trust?
- when is the second-place partner naturally narrow?
- what contexts look quiet rather than chaotic?
- are there any non-lane1 head situations that still keep a good hit rate?

## Output Target

Please return exactly `5` candidate hypotheses.

### Requirements

- at least `4` of the `5` should be exacta / 2T-style ideas
- at least `3` should be low complexity
- at least `3` should be one-point or two-point ticket patterns
- at least `1` may be a narrow trifecta idea only if the hit-rate story is still reasonable
- every hypothesis must be implementable later in SQL or Python without ambiguity

## Output Format

For each hypothesis, use exactly this structure:

```markdown
### Hypothesis ID: [H-001]

**Target Ticket Type:** [exacta / trifecta]

**Ticket Pattern:** [example: 1-2 or 1-2,1-3]

**Condition Block:**
- [condition 1]
- [condition 2]
- [condition 3]

**Why This Looks High-Hit:**
[short explanation]

**Why It Might Hold In Forward:**
[short explanation]

**Main Failure Risk:**
[short explanation]

**Complexity Check:**
[low / medium / high]
```

## Additional Rules

- if you use a payout-derived rough-race label, treat it as a discovery aid rather than an automatic live rule
- favor race-internal relationships such as:
  - lane class balance
  - exhibition rank
  - exhibition gap
  - start-shape comparison
  - wind / wave quietness vs roughness
  - partner concentration after a likely winner
- avoid tiny-sample artifacts

## Final Section

After the 5 hypotheses, add:

```markdown
## Screening Note
```

In that section, briefly say:

- which `2` hypotheses look most forward-safe
- which `1` hypothesis is most likely to be overfit
- what single extra aggregated file would help improve the next round
"""


def build_schema_gate_prompt() -> str:
    return """# Thread Gate 01: Schema Manifest

## Use This In A Fresh Thread

This step is a gate check. Do not generate hypotheses yet.

## Hard Isolation Rule

- Treat this as a fully isolated thread.
- Do not use any prior conversation, prior uploaded package, previous strategy names, earlier hypotheses, old notes, or memory from another thread.
- If something is not explicitly present in the uploaded files, treat it as unknown.

## Mandatory Grounding

- inspect the actual uploaded CSV headers
- inspect the uploaded data dictionary
- do not infer missing columns
- do not invent bucket values
- do not normalize strings
- preserve every column name and bucket value exactly as written

## Your Task

Return only the following:

1. uploaded file name list
2. exact CSV header list for each CSV file
3. bucket values explicitly documented in the uploaded files
4. a short mismatch report if the CSV headers and the data dictionary disagree

## Forbidden In This Step

- no interpretation
- no evaluation
- no ranking
- no hypothesis generation
- no mention of prior projects or known strategy names

## Output Format

```markdown
## Files
- [file name]

## CSV Headers
### [file name]
- [exact header string]

## Buckets
### [bucket name]
- [exact bucket value]

## Mismatch Report
- [none or exact issue]
```
"""


def build_hypothesis_gate_prompt() -> str:
    return f"""# Thread Gate 02: Hypothesis Request

## Use This Only After Gate 01 Passes

Only continue if the schema manifest matched the uploaded files exactly.

## Hard Isolation Rule

- Treat this as a fully isolated thread.
- Do not use any prior conversation, prior uploaded package, previous strategy names, earlier hypotheses, old notes, or memory from another thread.
- If something is not explicitly present in the uploaded files, treat it as unknown.

## Literal String Rule

- use only exact column names from the uploaded CSV headers
- use only exact bucket values from the uploaded files
- do not normalize or reformat strings
- do not add or remove whitespace inside bucket strings

## Goal

Using only the uploaded package from the discovery period `{START_DATE}` to `{END_DATE}`, generate a small set of zero-base BOAT RACE betting hypotheses that prioritize hit rate and stability.

This is intentionally a different lens from market-distortion logic.

## Core Direction

- prioritize high hit rate over flashy payout
- prioritize stable race shapes over market mispricing
- prefer simple, mechanical, testable rules
- preserve as much forward period as possible
- assume that a system that breaks quickly after discovery is not useful

## What Not To Do

- do not build the core logic around odds mispricing
- do not optimize around one-off longshots
- do not use payout bands as the main future betting condition
- do not propose wide, low-hit trifecta coverage unless it is strongly justified

## Output Target

Please return exactly `5` candidate hypotheses.

### Requirements

- at least `4` of the `5` should be exacta / 2T-style ideas
- at least `3` should be low complexity
- at least `3` should be one-point or two-point ticket patterns
- at least `1` may be a narrow trifecta idea only if the hit-rate story is still reasonable
- every hypothesis must be implementable later in SQL or Python without ambiguity

## Output Format

For each hypothesis, use exactly this structure:

```markdown
### Hypothesis ID: [H-001]

**Target Ticket Type:** [exacta / trifecta]

**Ticket Pattern:** [example: 1-2 or 1-2,1-3]

**Exact Condition Block:**
- file: [exact file name]
  column: [exact column name]
  condition: [exact literal value or numeric comparison]

**Why This Looks High-Hit:**
[short explanation]

**Why It Might Hold In Forward:**
[short explanation]

**Main Failure Risk:**
[short explanation]

**Sample Risk:**
[short explanation]

**Implementation Readiness:**
[ready / needs one more summary / too vague]
```

## Final Section

After the 5 hypotheses, add:

```markdown
## Screening Note
```

In that section, briefly say:

- which `2` hypotheses look most forward-safe
- which `2` hypotheses look mergeable
- which `1` hypothesis is most likely to be overfit
- what single extra aggregated file would help improve the next round
"""


def build_dictionary(sample_races: int, race_rows: int, entry_rows: int) -> str:
    return f"""# Data Dictionary

## Package Scope

- discovery period: `{START_DATE}` to `{END_DATE}`
- full discovery races available in DB: `28848`
- deterministic sample races in raw sample files: `{sample_races}`
- `races_sample.csv` rows: `{race_rows}`
- `entries_sample.csv` rows: `{entry_rows}`
- file budget target: `<= 10`

## Hard Isolation Rule

- the LLM should use only the uploaded files in the current batch
- no previous thread, previous package, prior strategy registry, or earlier human notes may be used

## Sample Files

### races_sample.csv

- one row per race from the sampled subset
- contains race-level results plus lane-1 to lane-3 summary features
- useful for qualitative pattern reading

Key columns:

- `race_id`: unique race key
- `race_date`: race date
- `stadium_code`, `stadium_name`: venue
- `race_no`: race number
- `meeting_title`, `race_title`: race labels
- `grade`: meeting grade
- `meeting_day_no`, `meeting_day_label`, `is_final_day`: meeting progress
- `weather_condition`, `wind_speed_m`, `wave_height_cm`: race environment
- `first_place_lane`, `second_place_lane`, `third_place_lane`: actual finish
- `exacta_combo`, `exacta_payout`, `trifecta_combo`, `trifecta_payout`: settled results
- `a1_count`, `a2_count`, `b1_count`, `b2_count`: class composition
- `lane1_class`, `lane2_class`, `lane3_class`: class of inner boats
- `lane1_national_win_rate`, `lane2_national_win_rate`, `lane3_national_win_rate`: base strength
- `lane1_motor_place_rate`, `lane2_motor_place_rate`, `lane3_motor_place_rate`: motor quality proxy
- `lane1_exhibition_time`, `lane2_exhibition_time`, `lane3_exhibition_time`: exhibition times
- `lane1_exhibition_rank`, `lane2_exhibition_rank`, `lane3_exhibition_rank`: rank within race
- `lane1_exhibition_diff_from_top`: lane1 minus best exhibition time
- `lane1_start_exhibition_st`, `lane2_start_exhibition_st`, `lane3_start_exhibition_st`: exhibition ST
- `lane1_st_vs_best_l23`: lane1 ST minus the better of lane2/lane3 ST
- `lane23_a_count`: count of A1/A2 among lanes 2 and 3
- `exacta_12_hit`, `exacta_13_hit`: label columns
- `rough_race_flag`: 1 if exacta payout >= 5000 or trifecta payout >= 10000

### entries_sample.csv

- six rows per sampled race, one per lane
- includes racer strength, motor, exhibition, and finish labels

Key columns:

- `lane`: official lane
- `racer_class`: A1 / A2 / B1 / B2
- `national_win_rate`, `local_win_rate`: ability measures
- `motor_place_rate`, `boat_place_rate`: equipment proxies
- `exhibition_time`: exhibition time
- `start_exhibition_st`: exhibition ST
- `exhibition_time_rank`: rank inside the race
- `exhibition_time_diff_from_top`: gap to best exhibition time
- `win_rate_rank`: rank inside the race by national win rate
- `exhibition_st_rank`: rank inside the race by exhibition ST
- `is_winner`, `is_top2`, `is_top3`: label columns

## Summary Files

### summary_lane_baseline.csv

- full-period baseline grouped by:
  - `lane`
  - `racer_class`
  - `exrank_bucket`
  - `wind_bucket`
- shows how often each lane/class/rank bucket wins or finishes top-2/top-3

Metric columns:

- `boats`
- `wins`
- `win_rate_pct`
- `top2_rate_pct`
- `top3_rate_pct`
- `avg_national_win_rate`
- `avg_local_win_rate`
- `avg_motor_place_rate`

Bucket columns:

- `exrank_bucket`
  - `1`, `2`, `3+`, `missing`
- `wind_bucket`
  - `0-2`, `3-4`, `5-6`, `7+`, `unknown`

### summary_lane1_context_scan.csv

- full-period lane-1 stability scan
- each row is an aggregated race context
- meant to help infer conditions for high-hit exacta logic

Group columns:

- `grade_group`
  - `SG`, `G1`, `general`
- `meeting_phase_bucket`
  - `day1-2`, `day3-4`, `day5+`, `final`, `unknown`
- `wind_bucket`
  - `0-2`, `3-4`, `5-6`, `7+`, `unknown`
- `wave_bucket`
  - `0-4`, `5-9`, `10+`, `unknown`
- `lane1_class`
- `lane1_exrank_bucket`
  - `1`, `2`, `3+`, `missing`
- `lane1_exgap_bucket`
  - `<=0.02`, `0.021-0.05`, `0.051-0.10`, `>0.10`, `missing`
- `lane1_st_bucket`
  - `lane1_faster`: lane1 ST is at least 0.03 faster than the better of lane2/lane3
  - `near_even`: lane1 is roughly even with the better of lane2/lane3
  - `lane1_slower`: lane1 is clearly slower than the better of lane2/lane3
  - `missing`
- `lane23_pressure_group`
  - `lane23_weak`: neither lane2 nor lane3 is A1/A2
  - `lane23_one_A`: one of lane2/lane3 is A1/A2
  - `lane23_two_A`: both lane2 and lane3 are A1/A2

Metric columns:

- `races`
- `lane1_win_rate_pct`
- `lane1_top2_rate_pct`
- `exacta_12_rate_pct`
- `exacta_13_rate_pct`
- `exacta_12_or_13_rate_pct`
- `rough_race_pct`
- `avg_lane1_national_win_rate`
- `avg_lane1_motor_place_rate`
- `avg_exacta_payout_on_12_13_hits`

### summary_lane1_partner_scan.csv

- full-period partner concentration scan for lane-1-win contexts
- helps determine whether the second-place lane is naturally narrow

Group columns:

- `grade_group`
  - `SG`, `G1`, `general`
- `wind_bucket`
  - `0-2`, `3-4`, `5-6`, `7+`, `unknown`
- `lane1_class`
- `lane1_exgap_bucket`
  - `<=0.02`, `0.021-0.05`, `0.051-0.10`, `>0.10`, `missing`
- `lane1_st_bucket`
  - `lane1_faster`, `near_even`, `lane1_slower`, `missing`
- `lane23_pressure_group`
  - `lane23_weak`, `lane23_one_A`, `lane23_two_A`

Metric columns:

- `races`
- `lane1_win_count`
- `lane1_win_rate_pct`
- `partner2_share_when_lane1_wins_pct`
- `partner3_share_when_lane1_wins_pct`
- `partner4_share_when_lane1_wins_pct`
- `partner5_share_when_lane1_wins_pct`
- `partner6_share_when_lane1_wins_pct`
- `best_partner_lane`
- `best_partner_share_pct`
- `exacta_12_rate_pct`
- `exacta_13_rate_pct`
- `exacta_14_rate_pct`
- `rough_race_pct`

## Discovery Guidance

- use summary files for hypothesis direction
- use sample files to sanity-check whether the conditions feel mechanically real
- do not treat `rough_race_flag` or payout-related fields as automatic live conditions without separate validation
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        sampled_race_ids_query = f"""
        WITH eligible AS (
          SELECT DISTINCT race_id
          FROM races
          WHERE race_date BETWEEN DATE '{START_DATE}' AND DATE '{END_DATE}'
        )
        SELECT race_id
        FROM eligible
        ORDER BY hash(race_id || '{SEED}')
        LIMIT {SAMPLE_RACES}
        """
        sampled_race_ids = [row[0] for row in con.execute(sampled_race_ids_query).fetchall()]
        if len(sampled_race_ids) != SAMPLE_RACES:
            raise RuntimeError(f"expected {SAMPLE_RACES} sampled races, got {len(sampled_race_ids)}")

        sample_values = values_sql(sampled_race_ids)
        feature_query = build_entry_features_query(start_date=START_DATE, end_date=END_DATE)
        race_context_query = build_race_context_query(feature_query)

        entries_sample_query = f"""
        WITH feature_base AS ({feature_query}),
        sample_races AS (
          SELECT race_id
          FROM (VALUES {sample_values}) AS t(race_id)
        )
        SELECT *
        FROM feature_base
        WHERE race_id IN (SELECT race_id FROM sample_races)
        ORDER BY race_date, stadium_code, race_no, lane
        """

        races_sample_query = f"""
        WITH feature_base AS ({feature_query}),
        sample_races AS (
          SELECT race_id
          FROM (VALUES {sample_values}) AS t(race_id)
        ),
        sampled AS (
          SELECT *
          FROM feature_base
          WHERE race_id IN (SELECT race_id FROM sample_races)
        )
        SELECT
          race_id,
          MIN(race_date) AS race_date,
          MIN(stadium_code) AS stadium_code,
          MIN(stadium_name) AS stadium_name,
          MIN(race_no) AS race_no,
          MIN(meeting_title) AS meeting_title,
          MIN(race_title) AS race_title,
          MAX(grade) AS grade,
          MAX(meeting_day_no) AS meeting_day_no,
          MIN(meeting_day_label) AS meeting_day_label,
          MAX(is_final_day) AS is_final_day,
          MIN(weather_condition) AS weather_condition,
          MAX(wind_speed_m) AS wind_speed_m,
          MAX(wave_height_cm) AS wave_height_cm,
          MAX(first_place_lane) AS first_place_lane,
          MAX(second_place_lane) AS second_place_lane,
          MAX(third_place_lane) AS third_place_lane,
          MAX(exacta_combo) AS exacta_combo,
          MAX(exacta_payout) AS exacta_payout,
          MAX(trifecta_combo) AS trifecta_combo,
          MAX(trifecta_payout) AS trifecta_payout,
          MAX(winning_technique) AS winning_technique,
          SUM(CASE WHEN racer_class = 'A1' THEN 1 ELSE 0 END) AS a1_count,
          SUM(CASE WHEN racer_class = 'A2' THEN 1 ELSE 0 END) AS a2_count,
          SUM(CASE WHEN racer_class = 'B1' THEN 1 ELSE 0 END) AS b1_count,
          SUM(CASE WHEN racer_class = 'B2' THEN 1 ELSE 0 END) AS b2_count,
          MAX(CASE WHEN lane = 1 THEN racer_class END) AS lane1_class,
          MAX(CASE WHEN lane = 2 THEN racer_class END) AS lane2_class,
          MAX(CASE WHEN lane = 3 THEN racer_class END) AS lane3_class,
          ROUND(MAX(CASE WHEN lane = 1 THEN national_win_rate END), 3) AS lane1_national_win_rate,
          ROUND(MAX(CASE WHEN lane = 2 THEN national_win_rate END), 3) AS lane2_national_win_rate,
          ROUND(MAX(CASE WHEN lane = 3 THEN national_win_rate END), 3) AS lane3_national_win_rate,
          ROUND(MAX(CASE WHEN lane = 1 THEN motor_place_rate END), 3) AS lane1_motor_place_rate,
          ROUND(MAX(CASE WHEN lane = 2 THEN motor_place_rate END), 3) AS lane2_motor_place_rate,
          ROUND(MAX(CASE WHEN lane = 3 THEN motor_place_rate END), 3) AS lane3_motor_place_rate,
          ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time END), 3) AS lane1_exhibition_time,
          ROUND(MAX(CASE WHEN lane = 2 THEN exhibition_time END), 3) AS lane2_exhibition_time,
          ROUND(MAX(CASE WHEN lane = 3 THEN exhibition_time END), 3) AS lane3_exhibition_time,
          MAX(CASE WHEN lane = 1 THEN exhibition_time_rank END) AS lane1_exhibition_rank,
          MAX(CASE WHEN lane = 2 THEN exhibition_time_rank END) AS lane2_exhibition_rank,
          MAX(CASE WHEN lane = 3 THEN exhibition_time_rank END) AS lane3_exhibition_rank,
          ROUND(MAX(CASE WHEN lane = 1 THEN exhibition_time_diff_from_top END), 3) AS lane1_exhibition_diff_from_top,
          ROUND(MAX(CASE WHEN lane = 1 THEN start_exhibition_st END), 3) AS lane1_start_exhibition_st,
          ROUND(MAX(CASE WHEN lane = 2 THEN start_exhibition_st END), 3) AS lane2_start_exhibition_st,
          ROUND(MAX(CASE WHEN lane = 3 THEN start_exhibition_st END), 3) AS lane3_start_exhibition_st,
          ROUND(
            MAX(CASE WHEN lane = 1 THEN start_exhibition_st END) - CASE
              WHEN MAX(CASE WHEN lane = 2 THEN start_exhibition_st END) IS NULL THEN MAX(CASE WHEN lane = 3 THEN start_exhibition_st END)
              WHEN MAX(CASE WHEN lane = 3 THEN start_exhibition_st END) IS NULL THEN MAX(CASE WHEN lane = 2 THEN start_exhibition_st END)
              ELSE LEAST(
                MAX(CASE WHEN lane = 2 THEN start_exhibition_st END),
                MAX(CASE WHEN lane = 3 THEN start_exhibition_st END)
              )
            END,
            3
          ) AS lane1_st_vs_best_l23,
          SUM(CASE WHEN lane IN (2, 3) AND racer_class IN ('A1', 'A2') THEN 1 ELSE 0 END) AS lane23_a_count,
          CASE WHEN MAX(first_place_lane) = 1 AND MAX(second_place_lane) = 2 THEN 1 ELSE 0 END AS exacta_12_hit,
          CASE WHEN MAX(first_place_lane) = 1 AND MAX(second_place_lane) = 3 THEN 1 ELSE 0 END AS exacta_13_hit,
          CASE
            WHEN MAX(exacta_payout) >= 5000 OR MAX(trifecta_payout) >= 10000 THEN 1
            ELSE 0
          END AS rough_race_flag
        FROM sampled
        GROUP BY race_id
        ORDER BY race_date, stadium_code, race_no, race_id
        """

        lane_baseline_query = f"""
        WITH feature_base AS ({feature_query}),
        bucketed AS (
          SELECT
            *,
            CASE
              WHEN exhibition_time_rank IS NULL THEN 'missing'
              WHEN exhibition_time_rank = 1 THEN '1'
              WHEN exhibition_time_rank = 2 THEN '2'
              ELSE '3+'
            END AS exrank_bucket,
            CASE
              WHEN wind_speed_m IS NULL THEN 'unknown'
              WHEN wind_speed_m <= 2 THEN '0-2'
              WHEN wind_speed_m <= 4 THEN '3-4'
              WHEN wind_speed_m <= 6 THEN '5-6'
              ELSE '7+'
            END AS wind_bucket
          FROM feature_base
        )
        SELECT
          lane,
          racer_class,
          exrank_bucket,
          wind_bucket,
          COUNT(*) AS boats,
          SUM(is_winner) AS wins,
          ROUND(AVG(is_winner) * 100, 2) AS win_rate_pct,
          ROUND(AVG(is_top2) * 100, 2) AS top2_rate_pct,
          ROUND(AVG(is_top3) * 100, 2) AS top3_rate_pct,
          ROUND(AVG(national_win_rate), 3) AS avg_national_win_rate,
          ROUND(AVG(local_win_rate), 3) AS avg_local_win_rate,
          ROUND(AVG(motor_place_rate), 3) AS avg_motor_place_rate
        FROM bucketed
        GROUP BY 1, 2, 3, 4
        HAVING COUNT(*) >= 60
        ORDER BY lane, racer_class, exrank_bucket, wind_bucket
        """

        lane1_context_scan_query = f"""
        WITH race_ctx AS ({race_context_query})
        SELECT
          grade_group,
          meeting_phase_bucket,
          wind_bucket,
          wave_bucket,
          lane1_class,
          lane1_exrank_bucket,
          lane1_exgap_bucket,
          lane1_st_bucket,
          lane23_pressure_group,
          COUNT(*) AS races,
          ROUND(AVG(lane1_win) * 100, 2) AS lane1_win_rate_pct,
          ROUND(AVG(lane1_top2) * 100, 2) AS lane1_top2_rate_pct,
          ROUND(AVG(exacta_12_hit) * 100, 2) AS exacta_12_rate_pct,
          ROUND(AVG(exacta_13_hit) * 100, 2) AS exacta_13_rate_pct,
          ROUND(AVG(CASE WHEN exacta_12_hit = 1 OR exacta_13_hit = 1 THEN 1 ELSE 0 END) * 100, 2) AS exacta_12_or_13_rate_pct,
          ROUND(AVG(rough_race_flag) * 100, 2) AS rough_race_pct,
          ROUND(AVG(lane1_national_win_rate), 3) AS avg_lane1_national_win_rate,
          ROUND(AVG(lane1_motor_place_rate), 3) AS avg_lane1_motor_place_rate,
          ROUND(AVG(CASE WHEN exacta_12_hit = 1 OR exacta_13_hit = 1 THEN exacta_payout END), 1) AS avg_exacta_payout_on_12_13_hits
        FROM race_ctx
        WHERE lane1_class IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
        HAVING COUNT(*) >= 50
        ORDER BY lane1_win_rate_pct DESC, exacta_12_or_13_rate_pct DESC, races DESC
        LIMIT 400
        """

        lane1_partner_scan_query = f"""
        WITH race_ctx AS ({race_context_query}),
        aggregated AS (
          SELECT
            grade_group,
            wind_bucket,
            lane1_class,
            lane1_exgap_bucket,
            lane1_st_bucket,
            lane23_pressure_group,
            COUNT(*) AS races,
            SUM(lane1_win) AS lane1_win_count,
            SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 2 THEN 1 ELSE 0 END) AS partner2_hits,
            SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 3 THEN 1 ELSE 0 END) AS partner3_hits,
            SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 4 THEN 1 ELSE 0 END) AS partner4_hits,
            SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 5 THEN 1 ELSE 0 END) AS partner5_hits,
            SUM(CASE WHEN lane1_win = 1 AND second_place_lane = 6 THEN 1 ELSE 0 END) AS partner6_hits,
            ROUND(AVG(lane1_win) * 100, 2) AS lane1_win_rate_pct,
            ROUND(AVG(exacta_12_hit) * 100, 2) AS exacta_12_rate_pct,
            ROUND(AVG(exacta_13_hit) * 100, 2) AS exacta_13_rate_pct,
            ROUND(AVG(CASE WHEN first_place_lane = 1 AND second_place_lane = 4 THEN 1 ELSE 0 END) * 100, 2) AS exacta_14_rate_pct,
            ROUND(AVG(rough_race_flag) * 100, 2) AS rough_race_pct
          FROM race_ctx
          WHERE lane1_class IS NOT NULL
          GROUP BY 1, 2, 3, 4, 5, 6
        )
        SELECT
          grade_group,
          wind_bucket,
          lane1_class,
          lane1_exgap_bucket,
          lane1_st_bucket,
          lane23_pressure_group,
          races,
          lane1_win_count,
          lane1_win_rate_pct,
          ROUND(partner2_hits * 100.0 / NULLIF(lane1_win_count, 0), 2) AS partner2_share_when_lane1_wins_pct,
          ROUND(partner3_hits * 100.0 / NULLIF(lane1_win_count, 0), 2) AS partner3_share_when_lane1_wins_pct,
          ROUND(partner4_hits * 100.0 / NULLIF(lane1_win_count, 0), 2) AS partner4_share_when_lane1_wins_pct,
          ROUND(partner5_hits * 100.0 / NULLIF(lane1_win_count, 0), 2) AS partner5_share_when_lane1_wins_pct,
          ROUND(partner6_hits * 100.0 / NULLIF(lane1_win_count, 0), 2) AS partner6_share_when_lane1_wins_pct,
          CASE
            WHEN partner2_hits >= partner3_hits AND partner2_hits >= partner4_hits AND partner2_hits >= partner5_hits AND partner2_hits >= partner6_hits THEN 2
            WHEN partner3_hits >= partner4_hits AND partner3_hits >= partner5_hits AND partner3_hits >= partner6_hits THEN 3
            WHEN partner4_hits >= partner5_hits AND partner4_hits >= partner6_hits THEN 4
            WHEN partner5_hits >= partner6_hits THEN 5
            ELSE 6
          END AS best_partner_lane,
          ROUND(
            GREATEST(partner2_hits, partner3_hits, partner4_hits, partner5_hits, partner6_hits) * 100.0 / NULLIF(lane1_win_count, 0),
            2
          ) AS best_partner_share_pct,
          exacta_12_rate_pct,
          exacta_13_rate_pct,
          exacta_14_rate_pct,
          rough_race_pct
        FROM aggregated
        WHERE races >= 60 AND lane1_win_count >= 20
        ORDER BY best_partner_share_pct DESC, lane1_win_rate_pct DESC, races DESC
        LIMIT 300
        """

        race_rows = write_csv(con, races_sample_query, OUTPUT_DIR / "races_sample.csv")
        entry_rows = write_csv(con, entries_sample_query, OUTPUT_DIR / "entries_sample.csv")
        write_csv(con, lane_baseline_query, OUTPUT_DIR / "summary_lane_baseline.csv")
        write_csv(con, lane1_context_scan_query, OUTPUT_DIR / "summary_lane1_context_scan.csv")
        write_csv(con, lane1_partner_scan_query, OUTPUT_DIR / "summary_lane1_partner_scan.csv")

        file_count = 10
        write_text(OUTPUT_DIR / "README.md", build_readme(file_count))
        write_text(OUTPUT_DIR / "llm_prompt_high_hit_oldest6m.md", build_prompt())
        write_text(OUTPUT_DIR / "thread_gate_01_schema_manifest.md", build_schema_gate_prompt())
        write_text(OUTPUT_DIR / "thread_gate_02_hypothesis_request.md", build_hypothesis_gate_prompt())
        write_text(
            OUTPUT_DIR / "data_dictionary.md",
            build_dictionary(SAMPLE_RACES, race_rows, entry_rows),
        )

        print(f"output_dir={OUTPUT_DIR}")
        print(f"file_count={file_count}")
        print(f"sample_races={SAMPLE_RACES}")
        print(f"races_sample_rows={race_rows}")
        print(f"entries_sample_rows={entry_rows}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
