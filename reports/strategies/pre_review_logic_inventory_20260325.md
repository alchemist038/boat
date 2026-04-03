# Pre-Review Logic Inventory 2026-03-25

This note is the holding inventory for logic branches that are not part of the current main forward trio, but should still remain reachable from the parent logic status.

Use this file as the entry point for:

- branches that are still `検討前`
- dormant hypotheses that may deserve a next review pass
- branches that are preserved but not promoted

## 1. Current Status Label

For this note, `検討前` means:

- not part of the current forward trio
- not adopted into the shared live runtime
- still preserved because the branch may contain reusable structure or context

Current main forward trio remains:

- `125_broad_four_stadium`
- `c2_provisional_v1`
- `4wind_base_415`

See:

- [LOGIC_STATUS.md](/c:/CODEX_WORK/boat_clone/LOGIC_STATUS.md)
- [main_forward_trio_snapshot_20260325.md](/c:/CODEX_WORK/boat_clone/reports/strategies/combined/main_forward_trio_snapshot_20260325.md)

## 2. Priority Order

### Priority 1: `2025-04-01..2025-06-16` bounded discovery slice

Current status:

- `検討前`
- highest dormant-review priority

Canonical note:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/README.md)

Contained branches:

- `H-A`
  - `4-1`
- `H-C`
  - `3-2`
- `H-B`
  - `4-2`
- `H-D`
  - `5-2`

Current review order inside this slice:

1. `H-A`
2. `H-C`
3. `H-B`
4. `H-D`

Current first-branch note:

- [h_a_yearly_comparison_2024_2026ytd_20260325.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_yearly_comparison_2024_2026ytd_20260325.md)

Current `H-A` working read:

- simple and high-sample exacta branch
- positive in `2024`, `2025`, and `2026_ytd` under official-settle proxy
- weak windows are not random only
- the main failure mode is:
  - lane 4 stops taking the head
  - lane 1 remains the actual winner too often
- completed first refinements:
  - `final day cut` helps without damaging the shape too much
  - `lane4_class != B1` improves DD, but cuts away too much edge
  - `pred1 = lane4` looks directionally useful as head confirmation, but is still too small-sample

Current next-step order for `H-A`:

1. keep `final day cut` as the first refined baseline
2. search for selective lane-4 weakness cuts instead of full `B1` removal
3. test stronger lane-4 head confirmation
4. only then consider runtime promotion

Current `H-B` working read:

- baseline `H-B` is still positive as a rough-water `4-2` branch
- `pred1 = lane4` is too strong and removes too much edge
- `pred6_lane != 2` is the cleanest current racer-index refinement
- that refinement also works on `2024`
- however, the aligned equity shape against the current forward set still has long weak periods
- fresh `2026-01-01 .. 2026-03-27` rerun is weak even on the best preserved version
  - `pred6_lane != 2 + final_day_cut`: `ROI 39.31%`
- so `H-B` should remain:
  - `保留`
  - `skip for now`
  - not a promotion-first branch

Updated review implication:

- keep `H-B` preserved with `pred6_lane != 2` as the current best version
- record `final day cut` as the next add-on only if the branch is reopened
- move the next deep review focus to `H-C`

Current `H-C` working read:

- baseline `H-C` does not survive as a stable global class-only branch
- the main collapse is concentrated in `2025_h2`
- `2026_ytd` itself is not weak, so this looks period-fragile rather than permanently dead
- `lane3=A1` improves the branch directionally
- the cleanest current small-sample refinement is:
  - `lane3=A1 & pred1_lane=3`
- but it should still remain:
  - `保留`
  - not promotion-ready
  - a later-review candidate only

Updated `H-C` implication:

- preserve the branch context
- keep `lane3=A1 & pred1_lane=3` as the leading refinement candidate
- if reopened later, start from:
  - stadium split
  - then the combined `lane3=A1 & pred1_lane=3` slice
  - and avoid relying on simple class-only cuts alone

Current closed exploratory note outside the bounded slice:

- [high_hit_candidate1_outer_pressure_review_20260329.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/high_hit_candidate1_outer_pressure_review_20260329.md)
- source:
  - oldest-6m high-hit Gemini candidate 1
- strongest preserved read:
  - `lane5_class = A1`
  - `lane6_class != A1`
  - buy `1-2`
- current interpretation:
  - record and preserve the slice work
  - do not keep it in the active re-open queue right now
  - it is weaker than the current bounded `H-A / H-C / H-B / H-D` queue
  - treat it as a closed exploratory note, not as a promotion candidate

Second closed exploratory note outside the bounded slice:

- [high_hit_candidate2_lane2_pressure_review_20260329.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/high_hit_candidate2_lane2_pressure_review_20260329.md)
- source:
  - oldest-6m high-hit Gemini candidate 2
- strongest preserved read:
  - `lane1_national_win_rate < 5.0`
  - `best_exhibition_lane = 2`
  - `wind_speed_m = 3-4`
  - `lane2_start_exhibition_st <= 0.14`
  - buy `2-1 / 2-3`
- current interpretation:
  - exacta looked usable on `2024` and `2025`
  - but the same branch collapses on `2026-01-01 .. 2026-03-27`
  - so it should remain:
    - `菫晉蕗`
    - preserved only
    - not a promotion or runtime-adoption candidate

Third exploratory note outside the bounded slice:

- [three_of_four_box_followup_20260402.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/three_of_four_box_followup_20260402.md)
- [three_of_four_box_candidate_c_one_a_watch_20260402.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/three_of_four_box_candidate_c_one_a_watch_20260402.md)
- [l3_weak_124_box_one_a_v1_20260402.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/l3_weak_124_box_one_a_v1_20260402.md)
- [l1_weak_234_box_v1_20260403.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/l1_weak_234_box_v1_20260403.md)
- [projects/l3_124/README.md](/c:/CODEX_WORK/boat_clone/projects/l3_124/README.md)
- [README.md](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/l3_124/README.md)
- [projects/l1_234/README.md](/c:/CODEX_WORK/boat_clone/projects/l1_234/README.md)
- [README.md](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/l1_234/README.md)
- source:
  - `2025-01-01 .. 2025-06-30` direct scan:
    - remove one lane from `1..4`
    - buy the remaining three lanes as a `3連単 BOX`
- strongest preserved reads:
  - `exclude 1`
    - `lane1_slowest_exh & lane1_worst_st`
    - `2-3-4 BOX`
  - `exclude 3`
    - `lane3_slowest_exh & lane3_worst_st`
    - `1-2-4 BOX`
  - `exclude 2`
    - `lane2_class_eq_B2 & lane2_worst_st`
    - `1-3-4 BOX`
- current interpretation:
  - the framing is interesting and reusable
  - `exclude 2` is the most developed cross-period read, and it weakens on `2026`
  - `exclude 1` has now cleared the same cross-period check:
    - `2024`: `2007 races`, `ROI 176.90%`
    - `2025_h2`: `952 races`, `ROI 186.96%`
    - `2026_ytd`: `460 races`, `ROI 167.83%`
    - formal candidate memo:
      - `l1_weak_234_box_v1`
  - the strongest current branch is now refined `exclude 3`:
    - `lane3_slowest_exh & lane3_worst_st`
    - plus `lane5/lane6 one-A-only`
    - `2025_h2`: `713 races`, `ROI 116.57%`
    - `2026_ytd`: `368 races`, `ROI 108.79%`
  - this branch is not adopted yet, but it is now the first `3-of-4` read worth line consideration
  - `exclude 1` is now a second worth-line-consideration branch in the same family
  - recommended logic id:
    - `l3_weak_124_box_one_a_v1`
    - `l1_weak_234_box_v1`
  - implementation status as of `2026-04-02`:
    - shared project and box scaffolding now exist
    - shared runtime support is implemented
    - forward runtime profile:
      - `l3_weak_124_box_one_a_ex241_v1`
      - `l1_weak_234_box_v1`
    - current runtime state:
      - `disabled`
    - current runtime ticket shape:
      - `5-ticket` slice excluding `2-4-1`
  - the only current racer-index confirmation that helps there is:
    - model top-3 = `{1,3,4}`
  - not:
    - `pred6_lane = 2`
  - keep the full area preserved
  - but no longer treat refined `exclude 3` as a closed dead-end note
  - reopen this branch in this order:
    - watch the disabled shared candidate in forward
    - verify the `ex241` ticket slice operationally
    - only then add deeper structural refinements

Reason for top priority:

- current trio DD / ROI comparison is anchored on the aligned period `2025-04-01 .. 2026-03-09`
- [main_forward_trio_snapshot_20260325.md](/c:/CODEX_WORK/boat_clone/reports/strategies/combined/main_forward_trio_snapshot_20260325.md) is the current cross-trio reference
- `125` has an explicitly recorded BT max-DD interval of `2025-03-11 -> 2025-06-16`
- [summary_20260314.md](/c:/CODEX_WORK/boat_clone/reports/strategies/125/summary_20260314.md) identifies that interval directly
- this means the bounded exacta discovery slice `2025-04-01 .. 2025-06-16` sits inside the early stress zone that already matters for the current main logic set
- therefore this slice is the most natural place to look for the next branch before expanding into broader dormant inventory

Working interpretation:

- this slice should be treated as the first dormant branch review area because it may explain, complement, or hedge the trio's early drawdown regime
- it is now stored as a shared disabled candidate at [final_day_cut_v1.json](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/h_a/profiles/final_day_cut_v1.json)
- runtime adoption is still pending, so it remains the best current `検討前` source

### Priority 2: `2press`

Current status:

- `検討前`
- alive, but not promoted

Canonical note:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/gemini_registry/2press/README.md)

Reason:

- still alive in `2025`, but weakened materially
- current read is that it needs context slicing before any promotion
- this makes it weaker than the bounded `2025-04-01..2025-06-16` slice, but still stronger than fully rejected Gemini branches

### Priority 3: `H-003 / H-004 / H-005`

Current status:

- `検討前`
- preserved, but not current promotion targets

Canonical note:

- [non_selected_hypotheses.md](/c:/CODEX_WORK/boat_clone/reports/strategies/gemini_registry/non_selected_hypotheses.md)

Reason:

- these are useful as preserved zero-base exploration history
- but they are already negative or clearly weak in the retained cross-year read
- they should remain reachable, but not consume review priority ahead of the two groups above

## 3. Practical Reading Rule

If a new review thread wants to inspect dormant logic, use this order:

1. read this file
2. read the bounded slice note for `H-A / H-C / H-B / H-D`
3. only then move to `2press`
4. look at `H-003 / H-004 / H-005` last unless a very specific structural question requires them

## 4. Update Rule

Update this note when any of the following happens:

- one of these branches is promoted into project-level logic
- one of these branches is explicitly rejected and archived
- a newer dormant-review priority is chosen from a more relevant trio-DD period
