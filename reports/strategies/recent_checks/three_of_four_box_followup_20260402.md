# 3-of-4 Box Follow-Up 2026-04-02

This note records the follow-up read from the `2025-01-01 .. 2025-06-30` exploration where one lane is removed from `1..4` and the remaining three lanes are treated as a `3連単 3艇BOX` (`6` tickets / `600円`).

Parent exploration outputs:

- [three_of_four_box_summary_2025h1.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/three_of_four_box_2025h1_20260402/three_of_four_box_summary_2025h1.md)
- [three_of_four_box_baseline_2025h1.csv](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/three_of_four_box_2025h1_20260402/three_of_four_box_baseline_2025h1.csv)
- [three_of_four_box_single_scan_2025h1.csv](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/three_of_four_box_2025h1_20260402/three_of_four_box_single_scan_2025h1.csv)
- [three_of_four_box_pair_scan_2025h1.csv](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/three_of_four_box_2025h1_20260402/three_of_four_box_pair_scan_2025h1.csv)

## Working Candidates

### Candidate A: Exclude Lane 1

- rule:
  - `lane1_slowest_exh`
  - `lane1_worst_st`
- bet expression:
  - `2-3-4 BOX`
- `2025-01-01 .. 2025-06-30`:
  - `sample 985`
  - `hits 124`
  - `hit rate 12.59%`
  - `ROI 169.60%`

Working read:

- lane 1 looks weak both visually and in ST among lanes `1..4`
- the clean interpretation is:
  - lane 1 can be removed from the top-3 frame
  - outside-inside reshuffle among `2,3,4` becomes the main path
- this is the strongest raw ROI read from the first-pass `3-of-4` scan

Current status:

- preserved as a high-interest exploratory branch
- not yet promoted
- next needed check is `2025_h2` and `2026_ytd`

### Candidate B: Exclude Lane 2

- rule:
  - `lane2_class_eq_B2`
  - `lane2_worst_st`
- bet expression:
  - `1-3-4 BOX`

Cross-period read:

- `2025-01-01 .. 2025-06-30`:
  - `sample 209`
  - `hits 46`
  - `hit rate 22.01%`
  - `ROI 147.19%`
- `2025-07-01 .. 2025-12-31`:
  - `sample 297`
  - `hits 70`
  - `hit rate 23.57%`
  - `ROI 137.18%`
- `2026-01-01 .. 2026-04-01`:
  - `sample 155`
  - `hits 25`
  - `hit rate 16.13%`
  - `ROI 70.61%`

Racer-index overlay read on `2026` index-covered dates:

- structural branch only:
  - `sample 116`
  - `ROI 84.99%`
- add `pred6_lane = 2`:
  - `sample 53`
  - `ROI 87.14%`
  - almost no improvement
- add `pred top3 = {1,3,4}`:
  - `sample 41`
  - `hits 10`
  - `hit rate 24.39%`
  - `ROI 106.22%`

Working read:

- the structural branch survives both `2025_h1` and `2025_h2`
- it weakens clearly in `2026`
- `pred6_lane = 2` is not the right overlay
- the more natural index confirmation is:
  - the model top-3 itself should already be `1,3,4`

Current status:

- preserved as the most developed `3-of-4` branch
- still `hold`, not promotion-ready
- if reopened later, start from:
  - `pred1/pred2/pred3 = {1,3,4}`
  - not from `pred6_lane = 2`

### Candidate C: Exclude Lane 3

- rule:
  - `lane3_slowest_exh`
  - `lane3_worst_st`
- bet expression:
  - `1-2-4 BOX`
- `2025-01-01 .. 2025-06-30`:
  - `sample 1647`
  - `hits 362`
  - `hit rate 21.98%`
  - `ROI 111.29%`

Working read:

- lane 3 looks weak both in exhibition time and ST among lanes `1..4`
- compared with the lane-2 branch, this one keeps a larger sample and a cleaner practical shape
- it is weaker in raw ROI than Candidate A, but more usable than many small-sample slices

Current status:

- extended follow-up now exists at:
  - [three_of_four_box_candidate_c_one_a_watch_20260402.md](./three_of_four_box_candidate_c_one_a_watch_20260402.md)
- the refined branch
  - `lane3_slowest_exh & lane3_worst_st`
  - plus `lane5/lane6 one-A-only`
  - now survives on both `2025_h2` and `2026_ytd`
- this moves `exclude 3` from a medium-priority exploratory branch to a line-watch candidate

## Current Interpretation

- the `3-of-4` framing itself is useful as a search lens
- the strongest immediate branch from the first scan was `exclude 1`
- `exclude 2` is still useful context, but it weakens in `2026`
- the current strongest practical branch is now:
  - `exclude 3`
  - `lane3_slowest_exh & lane3_worst_st`
  - plus `lane5/lane6 one-A-only`

Practical holding order if this area is reopened:

1. `exclude 1`: `lane1_slowest_exh & lane1_worst_st -> 2-3-4 BOX`
2. `exclude 3`: `lane3_slowest_exh & lane3_worst_st + lane5/lane6 one-A-only -> 1-2-4 BOX`
3. `exclude 2`: `lane2_class_eq_B2 & lane2_worst_st -> 1-3-4 BOX`, but only with a better `2026` confirmation rule

Current decision:

- preserve all three reads
- keep the whole `3-of-4` area outside the active live set for now
- but treat refined `exclude 3` as a real line-watch candidate rather than a closed exploratory note
