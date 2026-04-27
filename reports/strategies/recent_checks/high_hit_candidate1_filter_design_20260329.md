# High-Hit Candidate 1 Filter Design 2026-03-29

## Scope

This note intentionally uses data only through `2025-12-31`.

- `2026` is excluded on purpose
- treat this as a filter-design memo for later forward use
- do not read it as a `2026` evaluation note

## Base Branch

Start from the cleaned exacta branch:

- `lane1_national_win_rate >= 6.0`
- `best_exhibition_lane = 1`
- `lane1_win_rate_rank = 1`
- `lane5_class = A1`
- `lane6_class != A1`
- buy:
  - `1-2`

Reference note:

- [high_hit_candidate1_outer_pressure_review_20260329.md](/c:/CODEX_WORK/boat_clone/reports/strategies/recent_checks/high_hit_candidate1_outer_pressure_review_20260329.md)

## Search Rule

Keep the added filter simple.

Allowed axes:

- lane class
  - mainly lanes `2/3/4`
- water / wind
- optional price gate from `2025-04-01` onward only

Avoid:

- stadium-specific whitelists
- racer-index overlays
- anything that would force a `2026` look

## Best Structural Filter Found

Selected structural filter:

- `lane2_class = A2`
- `wind_speed_m <= 2`

Why this was chosen:

- it stays simple
- it matches the story of the branch:
  - lane 1 is trusted
  - lane 5 still applies outside pressure
  - lane 6 is not equally strong
  - a clean `A2` lane 2 is the most natural inside partner
  - calm water reduces random partner spread

## Structural Performance

Using only the structural filter above on top of the base branch:

| period | bets | ROI |
| --- | ---: | ---: |
| `2023-03-11 .. 2023-12-31` | 51 | `92.35%` |
| `2024-01-01 .. 2024-12-31` | 62 | `95.16%` |
| `2025-01-01 .. 2025-12-31` | 63 | `112.06%` |
| `2024-01-01 .. 2025-12-31` | 125 | `103.68%` |
| `2023-03-11 .. 2025-12-31` | 176 | `100.40%` |

Read:

- this is not a magic filter
- but it is the cleanest simple refinement found in the `2023..2025` search
- it improves the recent `2024+2025` combined read above break-even
- it does so without needing racer-index or stadium-specific fitting

## Optional Price Gate

Because shared `odds_2t` starts on `2025-04-01`, price gating was checked only on the `2025-04-01 .. 2025-12-31` subperiod.

For the same structural filter:

| variant | bets | ROI |
| --- | ---: | ---: |
| structural only | 54 | `124.07%` |
| structural + `1-2 odds >= 3.0` | 27 | `186.67%` |

Interpretation:

- if this branch is ever used in a live forward setting, the first optional price gate should be:
  - quoted `1-2` odds `>= 3.0`
- this is only a `2025` read
- so the price gate should be treated as an optional execution refinement, not as a fully proven structural truth

## Rejected Near-Miss Alternatives

These were directionally good, but not chosen as the first filter:

- `lane4 != A2 & wind <= 2`
  - larger sample
  - but weaker story and worse `2023`
- `lane3 = A1 & wind <= 2`
  - strong on `2023/2024`
  - too fragile on `2025`

## Proposed Forward Candidate

If this branch is reopened later, the first candidate version should be:

- structure:
  - `lane1_national_win_rate >= 6.0`
  - `best_exhibition_lane = 1`
  - `lane1_win_rate_rank = 1`
  - `lane5_class = A1`
  - `lane6_class != A1`
  - `lane2_class = A2`
  - `wind_speed_m <= 2`
- ticket:
  - `1-2`
- optional execution-side gate:
  - `1-2 odds >= 3.0`

## Current Recommendation

This is the best simple filter found using only data through `2025`.

Current status:

- preserve as the best current refinement for this branch
- do not backfit further right now
- if the branch is reopened for a future forward test, start from this version first
