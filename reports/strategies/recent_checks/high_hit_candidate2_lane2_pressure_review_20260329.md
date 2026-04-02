# High-Hit Candidate 2 Lane-2 Pressure Review 2026-03-29

## Source

- source package:
  - [README.md](/c:/CODEX_WORK/boat_clone/GPT/output/2023-03-11_2023-09-10_high_hit_discovery/README.md)
- source idea:
  - Gemini high-hit candidate 2
  - lane-1 weakness plus lane-2 exhibition leadership
  - original exacta buy:
    - `2-1`
    - `2-3`
  - original trifecta buy:
    - `2-1-3`
    - `2-3-1`
    - `2-1-4`
    - `2-4-1`

## Original Candidate Shape

Initial zero-base read used:

- `lane1_national_win_rate < 5.0`
- `best_exhibition_lane = 2`

Initial sample-side read from the Gemini thread:

- `65 races`
- exacta `2-1 / 2-3` hit rate `21.5%`
- trifecta 4-point hit rate `7.7%`
- exacta hit avg payout about `915円`

Interpretation:

- lane 1 is not dominant enough
- lane 2 looks strongest on exhibition
- so a lane-2 head branch may be worth checking before adding heavier structure

## Broad 2024 Recheck

### `2024-01-01 .. 2024-12-31`

Condition:

- `lane1_national_win_rate < 5.0`
- `best_exhibition_lane = 2`

Result:

- exacta `2-1 / 2-3`:
  - `3,345 races`
  - `689 hits`
  - hit rate `20.60%`
  - `ROI 101.25%`
  - average hit payout `983円`
- trifecta 4-point:
  - `3,345 races`
  - `393 hits`
  - hit rate `11.75%`
  - `ROI 96.19%`

Read:

- the exacta branch is real
- the trifecta branch is weaker and should not be treated as the main expression of the idea

## 2024 Useful Slices

### Single-axis reads

- `wind_speed_m = 3-4`:
  - `1,172 races`
  - exacta `ROI 110.84%`
- `lane2_start_exhibition_st <= 0.14`:
  - `1,466 races`
  - exacta `ROI 118.10%`
- `lane2_course_entry = 2`:
  - `3,079 races`
  - exacta `ROI 102.76%`
- `lane2_course_entry != 2`:
  - `266 races`
  - exacta `ROI 83.76%`

Read:

- moderate wind looks better than calm or rougher conditions
- lane-2 exhibition ST is the most natural confirmation axis
- course-entry deformation does not help; clean `2` entry is better

### Combined exacta branch

Working refinement:

- `lane1_national_win_rate < 5.0`
- `best_exhibition_lane = 2`
- `wind_speed_m = 3-4`
- `lane2_start_exhibition_st <= 0.14`
- buy:
  - `2-1`
  - `2-3`

`2024-01-01 .. 2024-12-31` result:

- `498 races`
- `123 hits`
- hit rate `24.70%`
- `ROI 116.62%`

Ticket split:

- `2-1`: `74 hits`, `ROI 119.64%`
- `2-3`: `49 hits`, `ROI 113.59%`

Read:

- this is the cleanest exacta version found in the first recheck
- sample is still large enough to treat as more than a tiny slice

## Extra 2024 Side Slice

### `lane6_class = A1`

On top of the combined exacta branch above:

- `95 races`
- `16 hits`
- `ROI 119.89%`

But the ticket shape becomes unstable:

- `2-1`: `ROI 55.47%`
- `2-3`: `ROI 184.32%`

Read:

- lane 6 strong does not improve the branch cleanly
- it changes partner behavior too much
- keep this only as a side observation, not as the main refinement

## 2025 Recheck

### `2025-01-01 .. 2025-12-31`

Using the same combined exacta refinement:

- `lane1_national_win_rate < 5.0`
- `best_exhibition_lane = 2`
- `wind_speed_m = 3-4`
- `lane2_start_exhibition_st <= 0.14`

Result:

- exacta `2-1 / 2-3`:
  - `540 races`
  - `131 hits`
  - hit rate `24.26%`
  - `ROI 107.05%`
- trifecta 4-point:
  - `540 races`
  - `77 hits`
  - hit rate `14.26%`
  - `ROI 89.76%`

Half split:

- `2025_h1` exacta:
  - `311 races`
  - `ROI 93.83%`
- `2025_h2` exacta:
  - `229 races`
  - `ROI 125.00%`

Read:

- exacta still survives
- trifecta still does not
- `2025` alone would justify keeping the branch open

## 2026 Stress Check

### `2026-01-01 .. 2026-03-27`

Using the same combined exacta refinement:

- exacta `2-1 / 2-3`:
  - `149 races`
  - `32 hits`
  - hit rate `21.48%`
  - `ROI 72.21%`
- trifecta 4-point:
  - `149 races`
  - `16 hits`
  - hit rate `10.74%`
  - `ROI 71.59%`

Split:

- `2026_janfeb` exacta:
  - `74 races`
  - `ROI 78.18%`
- `2026_mar` exacta:
  - `75 races`
  - `ROI 66.33%`

Read:

- the branch does not carry into the 2026 forward-side period
- this is too weak for promotion, even though `2024` and `2025` looked workable

## Final Read

Preserve this as a recorded exploratory exacta branch, but do not promote it.

Current interpretation:

- the best simple version found was:
  - `lane1_national_win_rate < 5.0`
  - `best_exhibition_lane = 2`
  - `wind_speed_m = 3-4`
  - `lane2_start_exhibition_st <= 0.14`
  - buy `2-1 / 2-3`
- exacta was positive in:
  - `2024`: `ROI 116.62%`
  - `2025`: `ROI 107.05%`
- but the same branch fails the 2026 stress check:
  - `2026-01-01 .. 2026-03-27`: `ROI 72.21%`
- trifecta never became strong enough to keep

Decision:

- record the branch and slices
- keep it as `hold`
- do not promote it into the live bet-line set
- do not create runtime / shared-box ownership from this branch
