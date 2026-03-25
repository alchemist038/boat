# Racer Index Status

This file is the owner doc for racer-index research as a logic substrate under [LOGIC_STATUS.md](./LOGIC_STATUS.md).

## Current Decision as of 2026-03-26

- Adopt `5M` as the first operating window
- `5M` means the prior `5 months`
- Keep `8M` and `12M` as monthly benchmarks
- Keep all predictions `point-in-time`
- Keep all prediction outputs `append-only`
- Persist these five layers:
  - `racer_indicator_snapshot`
  - `daily_score_output`
  - `daily_pred6`
  - `daily_pred1_signal`
  - `prediction_settlement`

See [racer_index/README.md](./racer_index/README.md), [racer_index/OPERATIONS.md](./racer_index/OPERATIONS.md), and [racer_index/SCHEMA.md](./racer_index/SCHEMA.md) for the detailed layout.

## Why This Track Exists

The goal is to store racer ability as a persistent layer and keep it separate from same-day scoring.

Two core questions drive this track:

- `pred6`
  - can it work as a remove-candidate signal
- `pred1`
  - can it work as a head signal, especially when the model prefers a non-lane1 boat

## Data Availability Confirmed in DB

As of `2026-03-24`, the DB already provides the core inputs:

- `entries`
  - class, national/local win rate, average ST, F/L, motor and boat stats
- `beforeinfo_entries`
  - exhibition time and exhibition ST
- `results`
  - finish order, winning technique, exacta and trifecta payouts
- `racer_stats_term`
  - term-level course snapshots

## Current Score Shape

The current base shape is:

```text
score = (100 + racer_add_subtract) * lane_coef + same_day_adjustment
```

### racer_add_subtract

- `hist_avg_finish`
- `class_point`
- `national/local win rate`
- `lane fit`
- `style fit`

### same_day_adjustment

- `exhibition_time rank`
- `exhibition_st rank`
- `motor rank`

### provisional lane_coef seed

- lane1: `1.261`
- lane2: `1.038`
- lane3: `1.019`
- lane4: `0.962`
- lane5: `0.886`
- lane6: `0.806`

These are current seeds, not frozen production values.

## Backtest Discipline

This track only makes sense if prediction uses information that was visible at the time.

Rules:

- do not use the target race `results`
- do not use aggregates that contain future dates
- save the prediction when it is generated
- settle it later against actual results

## Window Meaning

`5M / 8M / 12M` means how many months of history are used to build racer indicators.

Example for the `2026-03` forward month:

- `5M`
  - history: `2025-09-01..2026-01-31`
  - tune: `2026-02-01..2026-02-28`
  - forward: `2026-03-01..2026-03-31`
- `8M`
  - history: `2025-06-01..2026-01-31`
  - tune: `2026-02-01..2026-02-28`
  - forward: `2026-03-01..2026-03-31`
- `12M`
  - history: `2025-02-01..2026-01-31`
  - tune: `2026-02-01..2026-02-28`
  - forward: `2026-03-01..2026-03-31`

## Current Comparison Read

Walk-forward comparison showed that `pred6` quality is close across all three windows.

- `5M`
  - `pred6 actual 6th rate`: `40.86%`
  - `pred6 top3-out rate`: `83.62%`
- `8M`
  - `pred6 actual 6th rate`: `40.99%`
  - `pred6 top3-out rate`: `83.66%`
- `12M`
  - `pred6 actual 6th rate`: `40.95%`
  - `pred6 top3-out rate`: `83.59%`

Current interpretation:

- `5M`
  - easiest starting point for a recent-form operating version
- `8M`
  - the most balanced profile
- `12M`
  - slightly more stable

The current choice is to start storing daily outputs with `5M`.

## pred6 Read

`pred6` is useful as a remove-candidate signal.

But a universal `6-cut` overlay is not adopted yet because the impact differs by strategy:

- `125`
  - can benefit
- `4wind`
  - drawdown can improve, but ROI tends to drop
- `C2`
  - damage is too large at the moment

So `pred6` should be treated as a conditional filter, not as a universal portfolio rule.

## pred1 Read vs Simple lane1

On the same `51,541` races:

- simple `lane1`
  - average finish `2.0704`
  - win rate `54.95%`
  - top2 rate `72.37%`
  - top3 rate `81.64%`
- model `pred1`
  - average finish `1.9057`
  - win rate `57.51%`
  - top2 rate `76.33%`
  - top3 rate `86.13%`

So the model `pred1` is stronger than blindly using lane1 as the head.

## Key Signal Found in This Thread

The model placed a non-lane1 boat at `pred1` in `22.01%` of races.

In those races, the actual lane1 result dropped to:

- win rate `26.43%`
- top2 rate `45.52%`
- top3 rate `59.27%`

This is the current edge:

- not only finding strong lane1 cases
- but also identifying weak lane1 cases
- then moving the head to another boat

## ROI Read on pred1 != lane1

On `11,378` races where `pred1 != lane1`, head-fixed bets moved into the black.

- `exacta pred1 -> pred2`
  - `ROI 103.50%`
- `exacta pred1 -> pred2 or pred3`
  - `ROI 105.59%`
- `trifecta pred1 -> pred2 -> pred3`
  - `ROI 100.97%`
- `trifecta pred1 fixed 2 points`
  - `ROI 105.24%`

`BOX` and `trio` shapes did not improve as much.

Current interpretation:

- `pred1 != lane1` is a strong candidate condition
- the first use-case should be head-fixed betting logic

## First Live Overlay Decision

The first concrete live overlay now adopted from this track is:

- `C2`
  - skip when `pred1_lane = 1`
  - treat this as a contradiction filter for weak-lane1 logic
  - do not treat this as a universal portfolio overlay rule

Walk-forward read for the current `C2` proxy (`women6 + B2 cut + final day cut`):

- note:
  - [summary.md](./reports/strategies/c2/c2_pred1_non_lane1_overlay_walkforward_2025-04-01_to_2026-03-09_5m_20260325/summary.md)
- baseline:
  - `340 races`
  - `ROI 129.71%`
  - `profit +271,140 yen`
  - `max DD 163,280 yen`
- overlay `pred1 != lane1`:
  - `113 races`
  - `ROI 150.19%`
  - `profit +145,050 yen`
  - `max DD 32,840 yen`

Current interpretation:

- this materially compresses drawdown
- it also removes a large amount of gross profit
- so it should be read as a risk-compression overlay for `C2`, not as a general rule for every strategy

## Current H-A Compatibility Read

`H-A` is still research-only, but racer-index has now been checked as a possible head-confirmation layer.

- note:
  - [h_a_racer_index_pred1_lane4_feb_mar_20260325.md](./reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_racer_index_pred1_lane4_feb_mar_20260325.md)
- current read:
  - `pred1 = lane4` supports the idea of stronger lane-4 head confirmation
  - the sample is still too small for adoption
  - keep this in logic research, not in live runtime, for now

## Operating Method

### Daily

1. refresh raw, bronze, and silver through the current day
2. build `racer_indicator_snapshot` with the approved `weight_version`
3. save `daily_score_output` for the target races
4. save `daily_pred6` and `daily_pred1_signal`
5. append `prediction_settlement` after results are final

### Weekly

- fit new `5M` candidate weights
- do not promote them yet
- review `pred6` quality and ROI when `pred1 != lane1`

### Monthly

- compare `5M / 8M / 12M`
- choose one `weight_version` for the next month
- record the promotion reason in this file

## Current External Experiment Sources

The current scripts and reports still live mainly on the shared operational side.

- scripts:
  - `\\038INS\boat\workspace_codex\scripts\evaluate_base100_lane_multiplier_20260324.py`
  - `\\038INS\boat\workspace_codex\scripts\fit_racer_finish_score_20260324.py`
  - `\\038INS\boat\workspace_codex\scripts\backtest_three_projects_pred6_overlay_walkforward_20260324.py`
  - `workspace_codex/scripts/backtest_c2_pred1_non_lane1_overlay_walkforward_20260325.py`
  - `workspace_codex/scripts/evaluate_h_a_racer_index_overlay_20260325.py`
- reports:
  - `\\038INS\boat\reports\strategies\base100_lane_multiplier_20260324\summary.md`
  - `\\038INS\boat\reports\strategies\combined\three_projects_pred6_overlay_walkforward_2025-04-01_to_2026-03-09_profile5m_20260324\summary.md`
  - `\\038INS\boat\reports\strategies\combined\three_projects_pred6_overlay_walkforward_2025-04-01_to_2026-03-09_profile8m_20260324\summary.md`
  - `\\038INS\boat\reports\strategies\combined\three_projects_pred6_overlay_walkforward_2025-04-01_to_2026-03-09_20260324\summary.md`
  - `reports/strategies/c2/c2_pred1_non_lane1_overlay_walkforward_2025-04-01_to_2026-03-09_5m_20260325/summary.md`
  - `reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/h_a_racer_index_pred1_lane4_feb_mar_20260325.md`
