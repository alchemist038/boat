# 4Wind Partner Analysis

Target rule: `4wind only_wind_5_6`

Core condition:
- `wind_speed_m BETWEEN 5 AND 6`
- `lane4_st_diff_from_inside <= -0.05`
- `lane4_exhibition_time_rank <= 3`

Coverage: `2024-01-01..2026-03-18`
- qualified races: `1489`
- lane 4 head races: `487`

Second-place share when lane 4 wins:
- lane 5: `141` races, `28.95%`
- lane 1: `138` races, `28.34%`
- lane 6: `82` races, `16.84%`
- lane 2: `68` races, `13.96%`
- lane 3: `58` races, `11.91%`

Key read:
- lane 2 + 3 combined: `126` races, `25.87%`
- lane 1 + 5 + 6 combined: `361` races, `74.13%`
- lanes 2 and 3 are not dominant, but they are not dead either.

Single-combo ROI across all qualified races:
- `4-5`: hits `136`, ROI `238.7%`
- `4-1`: hits `131`, ROI `158.43%`
- `4-6`: hits `80`, ROI `158.35%`
- `4-2`: hits `65`, ROI `140.91%`
- `4-3`: hits `52`, ROI `108.87%`

Variant evaluation:
- `current_4156`: played `1489`, hit races `347`, ROI `185.16%`
- `add_42`: played `1489`, hit races `412`, ROI `174.1%`
- `add_43`: played `1489`, hit races `399`, ROI `166.08%`
- `add_423`: played `1489`, hit races `464`, ROI `161.05%`

Interpretation:
- `4-2` is not dead. It has enough hit volume and a positive single-combo ROI.
- Even so, adding `4-2` lowers the portfolio ROI versus the current `4-1/4-5/4-6` set in `2024`, `2025`, and `2026`.
- `4-3` is weaker than `4-2` and should stay behind it in priority.
- Current view: lane 2 and lane 3 are structurally alive, but the present `1/5/6` partner set is still the sharper betting package.
