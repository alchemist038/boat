# H-B / H-C Refresh 2026-03-28

## H-B

Existing preserved read before this refresh:

- baseline branch:
  - exacta `4-2`
  - `wave_6p`
  - `lane4_ahead_lane1_005`
- current best preserved overlay:
  - `pred6_lane != 2`

Reference notes:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-01-01_to_2025-06-30_h_b_racer_index_overlay_5m_20260326/README.md)
- [pred6_lane_review_20260326.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-01-01_to_2025-06-30_h_b_racer_index_overlay_5m_20260326/pred6_lane_review_20260326.md)
- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-04-01_to_2026-03-09_h_b_racer_index_overlay_pred6_not2_5m_20260327/README.md)

### Additional quick check on `2025-04-01 .. 2026-03-09`

Using the preserved `pred6_not2` overlay race results and joining shared `race_meta.is_final_day`:

| variant | bets | hits | ROI | profit_yen | max_dd_yen | longest_losing_streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `pred6_not2` | 530 | 27 | 148.43% | 25,670 | -15,370 | 113 |
| `pred6_not2 + final_day_cut` | 514 | 27 | 153.05% | 27,270 | -14,970 | 101 |

Read:

- final-day removal helps a little even after the `pred6_not2` overlay
- it keeps all `27` hits while removing `16` low-value races
- this makes `final day cut` the clean next add-on to test after `pred6_not2`

### Fresh `2026-01-01 .. 2026-03-27` re-run

Recomputed from the current shared DB through `2026-03-27`:

| variant | bets | hits | ROI | profit_yen | max_dd_yen | longest_losing_streak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 199 | 6 | 31.61% | -13,610 | -14,580 | 74 |
| baseline + `final_day_cut` | 189 | 6 | 33.28% | -12,610 | -13,780 | 74 |
| `pred6_not2` | 169 | 6 | 37.22% | -10,610 | -11,680 | 63 |
| `pred6_not2 + final_day_cut` | 160 | 6 | 39.31% | -9,710 | -10,880 | 63 |

Read:

- `2026` alone is clearly weak for `H-B`
- the ranking of variants stays consistent:
  - `pred6_not2 + final_day_cut` is the least bad
- but even the best `2026` version remains deeply negative
- current interpretation:
  - preserve the branch context
  - do not promote
  - do not even treat it as an active forward-check candidate right now

## H-C

Canonical bounded-discovery read:

- exacta `3-2`
- `lane3_a`
- `lane4_b2`
- quoted-odds window: `15-60`
- shorthand:
  - `strong 3, dead 4, sticky 2`

Reference note:

- [README.md](/c:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/README.md)

### Condition replication check

The bounded note matches the simple interpretation:

- `lane3_class in (A1, A2)`
- `lane4_class = B2`
- exacta `3-2`
- latest quoted odds `15-60`

That exact proxy reproduces the note:

| period | variant | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2025-04-01 .. 2025-06-16` | baseline `lane3 in A1/A2, lane4=B2` | 153 | 7 | 31.07 | 122.29% | 3,410 |

### Post-period quick re-test

| period | variant | bets | hits | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: |
| `2025-06-17 .. 2026-03-25` | baseline `lane3 in A1/A2, lane4=B2` | 556 | 14 | 62.86% | -20,650 |
| `2025-06-17 .. 2026-03-25` | `lane3=A1 only, lane4=B2` | 184 | 6 | 73.37% | -4,900 |
| `2025-06-17 .. 2026-03-25` | baseline + `final_day_cut` | 544 | 14 | 64.25% | -19,450 |
| `2025-06-17 .. 2026-03-25` | baseline + `lane2 in A1/A2` | 161 | 5 | 100.68% | 110 |

Read:

- the original `H-C` shape does **not** survive the post-`2025-06-16` period
- `lane3=A1 only` looks stronger in the original bounded slice, but still stays negative afterward
- `lane2 in A1/A2` almost flattens the later period, but it failed completely in the original slice, so it is not yet a stable refinement

### Additional `lane3=A1 & pred1_lane=3` check

| period | variant | bets | hits | avg_odds | ROI | profit_yen |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2025-04-01 .. 2025-06-16` | `lane3=A1 & pred1_lane=3` | 7 | 2 | 20.96 | 501.43% | 2,810 |
| `2025-06-17 .. 2026-03-27` | `lane3=A1 & pred1_lane=3` | 39 | 2 | 27.26 | 113.08% | 510 |
| `2025_h2` | `lane3=A1 & pred1_lane=3` | 30 | 1 | 26.63 | 58.00% | -1,260 |
| `2026_ytd` | `lane3=A1 & pred1_lane=3` | 9 | 1 | 29.33 | 296.67% | 1,770 |

Read:

- this is the cleanest `H-C` refinement found so far
- but it is still too small-sample for promotion
- `2025_h2` remains negative, so it should be preserved only as a hold candidate

## Current Working Conclusion

1. `H-B`
   - preserve `pred6_lane != 2` as the reference refinement
   - record `final day cut` as the next add-on if this branch is ever reopened
   - current state is:
     - `hold`
     - `skip for now`
2. `H-C`
   - do not promote the raw branch
   - do not assume a simple class-only refinement is enough
   - preserve `lane3=A1 & pred1_lane=3` as the most interesting small-sample refinement
   - current state is:
     - `hold`
     - not promotion-ready
   - next review should probably be:
     - stadium split
     - meeting/grade split
     - or a stronger lane-2 survivability condition instead of another simple class cut
