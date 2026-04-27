# Logic Status

This file is the parent status doc for logic research, adopted forward logic, and logic-adjacent signal work.

## Companion Docs

- [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- [BET_PROJECT_STATUS.md](./BET_PROJECT_STATUS.md)
- [README.md](./reports/live_trade/live_trigger_cli_forward_logic_performance_latest/README.md)
- [R_CONCEPT.md](./R_CONCEPT.md)
- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)
- [main_forward_trio_snapshot_20260325.md](./reports/strategies/combined/main_forward_trio_snapshot_20260325.md)
- [pre_review_logic_inventory_20260325.md](./reports/strategies/pre_review_logic_inventory_20260325.md)
- [h_a_yearly_comparison_2024_2026ytd_20260325.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_yearly_comparison_2024_2026ytd_20260325.md)
- [README.md](./reports/strategies/combined/h_a_vs_main_forward_trio_2025-04-01_to_2026-03-09_20260326/README.md)
- [h_b_2025_h1_official_settle_proxy_20260326.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_b_2025_h1_official_settle_proxy_20260326.md)
- [README.md](./reports/strategies/zero_base_period_2025-01-01_to_2025-06-30_h_b_racer_index_overlay_5m_20260326/README.md)
- [README.md](./reports/strategies/zero_base_period_2024-01-01_to_2024-12-31_h_b_racer_index_overlay_pred6_not2_5m_20260327/README.md)
- [README.md](./reports/strategies/combined/h_b_vs_current_four_2025-04-01_to_2026-03-09_20260327/README.md)
- [summary.md](./reports/strategies/c2/c2_pred1_non_lane1_overlay_walkforward_2025-04-01_to_2026-03-09_5m_20260325/summary.md)
- [high_hit_candidate1_outer_pressure_review_20260329.md](./reports/strategies/recent_checks/high_hit_candidate1_outer_pressure_review_20260329.md)
- [high_hit_candidate2_lane2_pressure_review_20260329.md](./reports/strategies/recent_checks/high_hit_candidate2_lane2_pressure_review_20260329.md)
- [three_of_four_box_followup_20260402.md](./reports/strategies/recent_checks/three_of_four_box_followup_20260402.md)
- [three_of_four_box_candidate_c_one_a_watch_20260402.md](./reports/strategies/recent_checks/three_of_four_box_candidate_c_one_a_watch_20260402.md)
- [l3_weak_124_box_one_a_v1_20260402.md](./reports/strategies/recent_checks/l3_weak_124_box_one_a_v1_20260402.md)
- [l1_weak_234_box_v1_20260403.md](./reports/strategies/recent_checks/l1_weak_234_box_v1_20260403.md)
- [projects/l3_124/README.md](./projects/l3_124/README.md)
- [README.md](./live_trigger/boxes/l3_124/README.md)
- [projects/l1_234/README.md](./projects/l1_234/README.md)
- [README.md](./live_trigger/boxes/l1_234/README.md)
- [projects/125/README.md](./projects/125/README.md)
- [projects/discovery/README.md](./projects/discovery/README.md)
- [projects/4wind/README.md](./projects/4wind/README.md)
- [LOGIC_ASSET_MODEL.md](./LOGIC_ASSET_MODEL.md)
- [projects/README.md](./projects/README.md)
- [workspace_codex/analysis/README.md](./workspace_codex/analysis/README.md)
- [live_trigger/PROJECT_RULES.md](./live_trigger/PROJECT_RULES.md)

- updated_at: 2026-04-27 JST

## 0. Logic Asset Storage Rule

The active auto line is only the forward operating subset.

But the repo also contains important non-forward logic assets:

- dormant logic concepts
- candidate filters
- cross-project structural reads
- zero-base discovery outputs
- walk-forward and comparison evidence

Use this storage model:

- `projects/`
  - concept ownership shelf
- `workspace_codex/analysis/`
  - raw exploration shelf
- `reports/strategies/`
  - curated summary archive
- `live_trigger/boxes/`
  - runtime logic shelf only after forward/adoption

Reference:

- [LOGIC_ASSET_MODEL.md](./LOGIC_ASSET_MODEL.md)

Practical rule:

- not on auto does not mean disposable
- if a concept is worth remembering, it should at least have a `projects/`
  home and a pointer to its evidence

## 1. Logic Ownership

- runtime logic source of truth:
  - `live_trigger/boxes/`
- shared bet expansion source:
  - `live_trigger/auto_system/app/core/bets.py`
- local execution lines may consume this logic, but should not silently fork it

Current adopted shared boxes:

- `live_trigger/boxes/125/`
- `live_trigger/boxes/c2/`
- `live_trigger/boxes/4wind/`
- `live_trigger/boxes/h_a/`
- `live_trigger/boxes/l3_124/`
- `live_trigger/boxes/l1_234/`

## 2. Current Active Forward Set

These are the six active forward logic tracks currently enabled in `live_trigger_cli/data/settings.json`.

Current daily forward report:

- [README.md](./reports/live_trade/live_trigger_cli_forward_logic_performance_latest/README.md)

Current point-in-time snapshot from the daily report (`2026-04-19` cutoff):

- active set overall:
  - `190 races`
  - `18 hit races`
  - race hit rate `9.47%`
  - flat ROI `70.77%`
- strongest current read:
  - `l3_124`: flat ROI `110.71%`
- next strongest current read:
  - `l1_234`: flat ROI `96.26%`

Historical trio DD / ROI snapshot:

- [main_forward_trio_snapshot_20260325.md](./reports/strategies/combined/main_forward_trio_snapshot_20260325.md)

### `4wind_base_415`

- current main project axis
- current runtime shape:
  - windy outside-head structure
  - partner focus `4-1 / 4-5`
  - `lane3_class in ('A1', 'A2')`
- current shared runtime profile lives in:
  - `live_trigger/boxes/4wind/profiles/base_415.json`

### `c2_provisional_v1`

- target idea:
  - women-race structure with lane-1 weakness confirmation
- current watchlist entry path:
  - title proxy
  - or `women6_proxy`
- current execution refinement:
  - `B2 cut` in `2-ALL-ALL / 3-ALL-ALL`
  - racer-index contradiction cut:
    - skip when `pred1_lane = 1`

### `125_broad_four_stadium`

- target idea:
  - fixed `1-2-5`
- scope:
  - `Suminoe / Naruto / Ashiya / Edogawa`
- current structural gate:
  - `lane1 = B1`
  - `lane5 != B2`
  - `lane6 = B2`

### `h_a_final_day_cut_v1`

- target idea:
  - exacta `4-1`
- current structural gate:
  - `lane1_st_top3`
  - `lane4_ahead_lane1_005`
  - final meeting day excluded
- current shared runtime profile lives in:
  - `live_trigger/boxes/h_a/profiles/final_day_cut_v1.json`

### `l3_weak_124_box_one_a_ex241_v1`

- target idea:
  - weak lane-3 path into `1-2-4` box
- current structural gate:
  - `lane3_slowest_exh`
  - `lane3_worst_st`
  - exactly one of `lane5/lane6` is `A-class`
  - runtime uses the `5-ticket` slice excluding `2-4-1`
- current shared runtime profile lives in:
  - `live_trigger/boxes/l3_124/profiles/l3_weak_124_box_one_a_ex241_v1.json`

### `l1_weak_234_box_v1`

- target idea:
  - weak lane-1 path into `2-3-4` box
- current structural gate:
  - `lane1_slowest_exh`
  - `lane1_worst_st`
  - runtime uses the full `2-3-4` six-ticket trifecta box
- current shared runtime profile lives in:
  - `live_trigger/boxes/l1_234/profiles/l1_weak_234_box_v1.json`

## 3. Common Adopted Filters

These should now be treated as adopted shared reads across the current active forward set.

- exclude final meeting day
- keep logic point-in-time
- do not let execution-specific state redefine logic truth

## 4. Not Main But Still Present

- `125_suminoe_main`
  - valid profile
  - not part of the current active six-logic forward set
- universal `pred6` overlay
  - not adopted yet
  - remains conditional / project-specific

## 5. Pre-Review / 検討前 Inventory

For dormant logic that should remain reachable but is not part of the current active six-logic forward set, use:

- [pre_review_logic_inventory_20260325.md](./reports/strategies/pre_review_logic_inventory_20260325.md)

Current review priority there is:

1. `2025-04-01..2025-06-16` bounded slice:
   - `H-A / H-C / H-B / H-D`
2. `2press`
3. `H-003 / H-004 / H-005`

Why the bounded slice is first:

- the historical trio DD / ROI comparison is anchored on `2025-04-01 .. 2026-03-09`
- `125` has a recorded BT max-DD interval of `2025-03-11 -> 2025-06-16`
- so the bounded exacta slice `2025-04-01 .. 2025-06-16` overlaps the early stress regime that already mattered for the then-current trio benchmark
- this makes it the best current `検討前` review zone

Current first-pass review result:

- `H-A` has now been re-checked on `2024`, `2025`, and `2026_ytd` under official-settle proxy
- shared runtime ownership now exists at [final_day_cut_v1.json](/c:/CODEX_WORK/boat_clone/live_trigger/boxes/h_a/profiles/final_day_cut_v1.json)
  - historical note:
    - this profile started as a disabled candidate in shared runtime, but it is part of the current active six-logic forward set
- note:
  - [h_a_yearly_comparison_2024_2026ytd_20260325.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_yearly_comparison_2024_2026ytd_20260325.md)
  - [h_a_final_day_cut_2024_2026ytd_20260325.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_final_day_cut_2024_2026ytd_20260325.md)
  - [h_a_lane4_not_b1_2024_2026ytd_20260325.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_lane4_not_b1_2024_2026ytd_20260325.md)
- working read:
  - `H-A` is simple, high-sample, and still positive across years
  - its weak windows are tied more to `lane4 head failure` than to normal partner variance
  - `final day cut` is the current best first refinement candidate
  - `lane4_class != B1` improves DD, but is too strong as a universal cut
  - first racer-index head-confirmation check (`pred1 = lane4`) is now recorded, but sample is still too small for adoption
  - H-A is now also plotted against the then-current main forward trio:
    - [README.md](./reports/strategies/combined/h_a_vs_main_forward_trio_2025-04-01_to_2026-03-09_20260326/README.md)
  - next review order is:
    - keep `final day cut` as the first refined baseline
    - search for selective lane-4 weakness cuts instead of full `B1` removal
    - test stronger lane-4 head confirmation

Current second-pass review result:

- `H-B` has now been checked on `2025-01-01 .. 2025-06-30` under official-settle proxy
- note:
  - [h_b_2025_h1_official_settle_proxy_20260326.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_b_2025_h1_official_settle_proxy_20260326.md)
  - [README.md](./reports/strategies/zero_base_period_2025-01-01_to_2025-06-30_h_b_racer_index_overlay_5m_20260326/README.md)
  - [README.md](./reports/strategies/zero_base_period_2024-01-01_to_2024-12-31_h_b_racer_index_overlay_pred6_not2_5m_20260327/README.md)
  - [README.md](./reports/strategies/combined/h_b_vs_current_four_2025-04-01_to_2026-03-09_20260327/README.md)
- working read:
  - baseline `H-B` is still positive and structurally looks like a rough-water `4-2` branch
  - `pred1 = lane4` is too strong and removes the payout edge
  - the cleanest current racer-index candidate is:
    - `pred6_lane != 2`
  - `pred6_lane != 2` also holds up on `2024`
  - but the aligned `2025-04-01 .. 2026-03-09` equity shape is still rough, with long flat / down periods
  - a fresh `2026-01-01 .. 2026-03-27` rerun is weak across all tested variants:
    - baseline: `ROI 31.61%`
    - `pred6_lane != 2`: `ROI 37.22%`
    - `pred6_lane != 2 + final_day_cut`: `ROI 39.31%`
  - so the branch should now remain `hold / skip`, not promotion-ready
  - next review order is:
    - keep `H-B + pred6_lane != 2` as the preserved rough-water reference
    - record `final day cut` as the next add-on only if the branch is reopened later
    - move next full review priority to `H-C`

Current third-pass review result:

- `H-C` has now been re-sliced across period / class / odds / stadium conditions
- note:
  - [h_c_slice_review_20260328.md](./reports/strategies/recent_checks/h_c_slice_review_20260328.md)
  - [h_b_h_c_refresh_20260328.md](./reports/strategies/recent_checks/h_b_h_c_refresh_20260328.md)
- working read:
  - baseline `H-C` does not survive as a stable global class-only branch
  - the worst damage is concentrated in `2025_h2`, while `2026_ytd` is not weak by itself
  - `lane3=A1` is directionally better
  - the cleanest current small-sample refinement is:
    - `lane3=A1 & pred1_lane=3`
  - but that refinement is still too small to promote:
    - `2025_h2`: `ROI 58.00%`
    - `2026_ytd`: `9 bets`, `ROI 296.67%`
  - so the branch should remain `hold`, preserved for later review rather than promotion
  - next review order is:
    - keep stadium split as the first reopening lens
    - keep `lane3=A1 & pred1_lane=3` as the leading refinement candidate
    - avoid treating simple class-only cuts as sufficient

Another closed exploratory check:

- note:
  - [high_hit_candidate1_outer_pressure_review_20260329.md](./reports/strategies/recent_checks/high_hit_candidate1_outer_pressure_review_20260329.md)
- source:
  - oldest-6m high-hit Gemini candidate 1
  - original lane-1 trust exacta branch
- strongest sub-read found during the recheck:
  - keep the lane-1 trust conditions
  - add `lane5_class = A1`
  - add `lane6_class != A1`
  - narrow to `1-2`
- cross-year result is still not strong enough:
  - `2023`: `ROI 103.46%`
  - `2024`: `ROI 88.28%`
  - `2025`: `ROI 88.52%`
  - `2025-04-01 .. 2025-12-31` with `1-2 odds >= 3.0`: `ROI 87.26%`
- supporting read:
  - `pred6_lane = 4` worsens the branch
  - `pred1` adds no extra selection value because the branch already collapses to `pred1_lane = 1`
- current interpretation:
  - preserve as a recorded exploratory branch
  - stop pushing it for now
  - do not change the live bet-line set for this idea

Current closed exploratory check:

- note:
  - [high_hit_candidate2_lane2_pressure_review_20260329.md](./reports/strategies/recent_checks/high_hit_candidate2_lane2_pressure_review_20260329.md)
- source:
  - oldest-6m high-hit Gemini candidate 2
  - lane-1 weakness plus lane-2 exhibition-lead structure
- strongest preserved read:
  - `lane1_national_win_rate < 5.0`
  - `best_exhibition_lane = 2`
  - `wind_speed_m = 3-4`
  - `lane2_start_exhibition_st <= 0.14`
  - buy `2-1 / 2-3`
- cross-year read:
  - `2024`: `498 races`, `ROI 116.62%`
  - `2025`: `540 races`, `ROI 107.05%`
  - `2026-01-01 .. 2026-03-27`: `149 races`, `ROI 72.21%`
- current interpretation:
  - preserve as a recorded exploratory branch
  - exacta is the only useful expression; trifecta does not survive
  - the branch should remain `hold`, not promotion-ready
  - do not change the live bet-line set for this idea

Current `3-of-4` exploratory check:

- note:
  - [three_of_four_box_followup_20260402.md](./reports/strategies/recent_checks/three_of_four_box_followup_20260402.md)
- source:
  - direct `2025-01-01 .. 2025-06-30` scan:
    - remove one lane from `1..4`
    - buy the remaining three lanes as a `3連単 BOX`
- strongest preserved reads:
  - `exclude 1`
    - `lane1_slowest_exh & lane1_worst_st`
    - `2-3-4 BOX`
  - `exclude 3`
    - `lane3_slowest_exh & lane3_worst_st`
    - `1-2-4 BOX`
    - refined line-watch version:
      - [three_of_four_box_candidate_c_one_a_watch_20260402.md](./reports/strategies/recent_checks/three_of_four_box_candidate_c_one_a_watch_20260402.md)
      - add `lane5/lane6 one-A-only`
      - formal candidate memo:
        - [l3_weak_124_box_one_a_v1_20260402.md](./reports/strategies/recent_checks/l3_weak_124_box_one_a_v1_20260402.md)
  - `exclude 2`
    - `lane2_class_eq_B2 & lane2_worst_st`
    - `1-3-4 BOX`
- current interpretation:
  - the frame is useful as a research lens
  - `exclude 2` survives `2025_h2`, but weakens on `2026`
  - the strongest current cross-period read is now refined `exclude 3`:
    - `2025_h2`: `713 races`, `ROI 116.57%`
    - `2026_ytd`: `368 races`, `ROI 108.79%`
  - `exclude 1` has now also cleared the same cross-period check:
    - `2024`: `2007 races`, `ROI 176.90%`
    - `2025_h2`: `952 races`, `ROI 186.96%`
    - `2026_ytd`: `460 races`, `ROI 167.83%`
  - this is the first branch in the `3-of-4` area that now deserves line consideration
  - recommended working logic id:
    - `l3_weak_124_box_one_a_v1`
    - `l1_weak_234_box_v1`
  - shared forward implementation now exists:
    - project:
      - `projects/l3_124/`
      - `projects/l1_234/`
    - shared box:
      - `live_trigger/boxes/l3_124/`
      - `live_trigger/boxes/l1_234/`
    - runtime profile:
      - `l3_weak_124_box_one_a_ex241_v1`
      - `l1_weak_234_box_v1`
    - current state:
      - implemented in shared runtime
      - originally disabled by default in shared runtime
      - now active in the current six-logic forward set
    - runtime ticket expression:
      - `5-ticket` slice excluding `2-4-1`
      - full `2-3-4` six-ticket box for `l1_234`
  - the best current racer-index read inside that branch is:
    - keep only races where model top-3 is `{1,3,4}`
  - not:
    - `pred6_lane = 2`
  - preserve all three branches
  - keep the area outside the active live set for now
  - but move refined `exclude 3` and now-validated `exclude 1` from pure exploratory status to `watch / possible next-line candidate`
  - next review should be:
    - forward stability under the current active six-logic set
    - execution realism of the `ex241` 5-ticket slice
    - whether this branch remains operationally clean inside the current set

## 6. Racer Index Position

`racer_index` is a logic substrate.

It is not:

- the main bet line
- the DB owner
- a standalone operational line

It is:

- a persistent racer-ability layer
- a source of candidate conditional filters and head signals
- an input into future logic refinement
- first concrete uses are now:
  - `C2` contradiction filtering
  - `H-A` head-confirmation research

Current racer-index status lives in:

- [RACER_INDEX_STATUS.md](./RACER_INDEX_STATUS.md)

## 7. Forward Discipline

For the current active six-logic forward set:

- keep forward operation on `live_trigger_cli`
- keep logic ownership under the shared source
- record adopted filters and scope changes here
- keep strategy-specific backtest and refinement notes in the relevant project/readme files

## 8. Portfolio Sizing Layer

- `R_CONCEPT.md` defines the shared meaning of `R`
- `R` belongs to logic-side portfolio sizing
- execution lines should consume precomputed `R`
- execution lines should not redefine `R` ad hoc

## 9. 4wind Promotion Decision

Current recommendation:

- completed: `4wind` now lives in shared `live_trigger/boxes`

Reason:

- `4wind` is now part of the historical trio benchmark and remains part of the current six-logic forward set
- the project rule is still "shared logic source, local execution line"
- keeping `4wind` under shared boxes keeps the current active set under one logic owner

What this does not mean:

- it does not require changing the main bet line away from `live_trigger_cli`
- it does not require changing runtime state ownership
- it does not require moving `4wind` out of the CLI execution flow

Migration result:

- `base_415` is stored under shared `live_trigger/boxes/4wind/`
- `live_trigger_cli` consumes the shared profile
- the old line-local `live_trigger_cli/boxes/4wind/` profile JSON is deprecated and no longer used as the active source
