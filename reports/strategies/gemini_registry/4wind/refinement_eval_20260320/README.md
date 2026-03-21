# 4Wind Refinement Evaluation

- Compared the base rule against three Gemini-suggested refinement directions.
- Periods tested: `2024` and `2025`.
- Stake remains `300 yen per played race`.

## Variants
- `base`: original 4wind
- `exclude_wind_7_plus`: keep only wind `<= 6`
- `exclude_wave56_wind34`: exclude wave `5-6cm` with wind in `3-4` bucket
- `only_wind_5_6`: keep only wind `5-6m`
- `2024-01-01_to_2024-12-31 / base`: played `1534`, ROI `201.58%`, maxDD `9030`, hit_race_pct `26.27%`
- `2024-01-01_to_2024-12-31 / exclude_wind_7_plus`: played `1359`, ROI `208.98%`, maxDD `8430`, hit_race_pct `26.49%`
- `2024-01-01_to_2024-12-31 / exclude_wave56_wind34`: played `1500`, ROI `203.98%`, maxDD `8950`, hit_race_pct `26.47%`
- `2024-01-01_to_2024-12-31 / only_wind_5_6`: played `639`, ROI `238.0%`, maxDD `7420`, hit_race_pct `27.07%`
- `2025-01-01_to_2025-12-31 / base`: played `1676`, ROI `146.5%`, maxDD `99030`, hit_race_pct `20.17%`
- `2025-01-01_to_2025-12-31 / exclude_wind_7_plus`: played `1451`, ROI `150.3%`, maxDD `90710`, hit_race_pct `20.61%`
- `2025-01-01_to_2025-12-31 / exclude_wave56_wind34`: played `1634`, ROI `146.34%`, maxDD `95130`, hit_race_pct `20.2%`
- `2025-01-01_to_2025-12-31 / only_wind_5_6`: played `664`, ROI `153.35%`, maxDD `39470`, hit_race_pct `21.54%`
- `2026-01-01_to_2026-03-18 / base`: played `399`, ROI `118.73%`, maxDD `39150`, hit_race_pct `16.04%`
- `2026-01-01_to_2026-03-18 / exclude_wind_7_plus`: played `331`, ROI `111.13%`, maxDD `33690`, hit_race_pct `14.8%`
- `2026-01-01_to_2026-03-18 / exclude_wave56_wind34`: played `395`, ROI `119.93%`, maxDD `38850`, hit_race_pct `16.2%`
- `2026-01-01_to_2026-03-18 / only_wind_5_6`: played `186`, ROI `117.19%`, maxDD `17790`, hit_race_pct `16.67%`