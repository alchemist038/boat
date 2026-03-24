# BOX 4wind

Runtime ownership for `4wind` now lives here.

References:

- `projects/4wind/README.md`
- `reports/strategies/gemini_registry/4wind/README.md`
- `LOGIC_STATUS.md`

Current runtime profile:

- `4wind_base_415`
  - adopted forward profile for the current `4-1 / 4-5` branch
  - `lane3_class in ('A1', 'A2')`
  - `wind_speed 5-6m`
  - `lane4_st_diff_from_inside <= -0.05`
  - `lane4_exhibition_time_rank <= 3`
  - `min_quoted_odds in [10, 50)`

Notes:

- `4wind` is now part of the shared logic owner set together with `125` and `c2`.
- The main execution line remains `live_trigger_cli`.
- Execution innovation may continue in the CLI line, but the profile definition itself should now be updated here.
