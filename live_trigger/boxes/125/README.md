# BOX 125

Runtime ownership for `125` lives here.

References:

- `projects/125/README.md`
- `projects/125/status_notebooklm_20260313.txt`
- `reports/strategies/125/summary_20260314.md`
- `reports/strategies/125/review_20260314.md`
- `LOGIC_ALIGNMENT_20260321.md`

Current runtime profiles:

- `125_suminoe_main`
  - Canonical Suminoe-only branch for `1-2-5`
  - `lane1=B1`, `lane6=B2`, `lane5!=B2`, `exgap<=0.02`
  - Kept as the closest memo-style profile
  - Still `enabled=false`
- `125_broad_four_stadium`
  - Adopted runtime profile for the current four-stadium branch
  - Stadiums: Suminoe, Naruto, Ashiya, Edogawa
  - Current runtime filters: `lane1=B1`, `lane6=B2`, `lane5!=B2`, `exgap<=0.02`

Notes:

- The broad profile is no longer the old loose proxy that allowed `lane6=A1`.
- One simplification still remains versus the project summary: Ashiya is still handled under the shared `lane5!=B2` branch instead of a dedicated `lane5=B1` split.
- Shared ownership is defined in `live_trigger/PROJECT_RULES.md`.
