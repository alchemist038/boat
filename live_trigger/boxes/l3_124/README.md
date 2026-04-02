# BOX l3_124

Runtime ownership for the weak lane-3 branch lives here.

References:

- `projects/l3_124/README.md`
- `projects/l3_124/logic_considerations.md`
- `reports/strategies/recent_checks/l3_weak_124_box_one_a_v1_20260402.md`
- `reports/strategies/recent_checks/three_of_four_box_followup_20260402.md`

Current runtime profile:

- `l3_weak_124_box_one_a_ex241_v1`
  - forward-test candidate
  - disabled by default
  - lane 3 must be the slowest exhibition lane among lanes 1-4
  - lane 3 must also be the worst ST lane among lanes 1-4
  - exactly one of lanes 5/6 is A-class
  - runtime ticket shape keeps the five-ticket trifecta slice and excludes `2-4-1`

Notes:

- `live_trigger/boxes/` is the shared runtime source of truth.
- This box is intentionally separated from the existing promoted lines so the forward test can run without disturbing them.
