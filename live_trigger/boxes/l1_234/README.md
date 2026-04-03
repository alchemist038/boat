# BOX l1_234

Runtime ownership for the weak lane-1 branch lives here.

References:

- `projects/l1_234/README.md`
- `projects/l1_234/logic_considerations.md`
- `reports/strategies/recent_checks/l1_weak_234_box_v1_20260403.md`
- `reports/strategies/recent_checks/three_of_four_box_followup_20260402.md`

Current runtime profile:

- `l1_weak_234_box_v1`
  - forward-test candidate
  - disabled by default
  - lane 1 must be the slowest exhibition lane among lanes 1-4
  - lane 1 must also be the worst ST lane among lanes 1-4
  - runtime ticket shape keeps the full six-ticket trifecta box on `2,3,4`

Notes:

- `live_trigger/boxes/` is the shared runtime source of truth.
- This box is intentionally separated from the existing promoted lines so the forward test can run without disturbing them.
