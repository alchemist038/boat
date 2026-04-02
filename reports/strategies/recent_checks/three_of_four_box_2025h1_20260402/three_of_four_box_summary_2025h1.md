# 3-of-4 Box Exploration (`2025-01-01 .. 2025-06-30`)

## Scope

- period: `2025-01-01` .. `2025-06-30`
- races: `27,879`
- target framing: remove one boat from lanes `1..4`, then treat the remaining three lanes as a `trifecta 3-boat box` (`6` tickets / `600 yen`)
- settle: `results.trifecta_payout`
- features: pre-race class / national win rate / motor / exhibition time / exhibition ST / course entry / wind / wave / final-day flag

## Baseline

| excluded lane | hit rate | ROI | avg hit payout |
| --- | ---: | ---: | ---: |
| `1` | `3.36%` | `63.77%` | `11384.8` |
| `2` | `10.88%` | `65.90%` | `3634.2` |
| `3` | `12.91%` | `70.00%` | `3252.4` |
| `4` | `17.90%` | `73.62%` | `2468.7` |

## Best Single Features

### Exclude `1`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l1_worst_st` | `5163` | `7.65%` | `130.89%` | `2.28` |
| `l3_class_eq_B2` | `916` | `2.40%` | `128.99%` | `0.71` |
| `l1_st_gap_ge_005` | `8572` | `5.65%` | `109.66%` | `1.68` |
| `l4_class_eq_B2` | `1556` | `2.12%` | `105.31%` | `0.63` |
| `l1_slowest_exh` | `3909` | `6.55%` | `92.37%` | `1.95` |
| `l1_worst_nat` | `4708` | `8.60%` | `86.65%` | `2.56` |

### Exclude `2`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l2_worst_st` | `6442` | `15.01%` | `85.33%` | `1.38` |
| `l4_course_front` | `831` | `10.35%` | `84.64%` | `0.95` |
| `l1_worst_motor` | `1772` | `11.17%` | `82.01%` | `1.03` |
| `l3_course_back` | `1588` | `7.18%` | `78.14%` | `0.66` |
| `l2_course_back` | `1314` | `8.83%` | `77.29%` | `0.81` |
| `l2_worst_class` | `2098` | `19.92%` | `77.14%` | `1.83` |

### Exclude `3`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l2_course_front` | `187` | `6.95%` | `138.21%` | `0.54` |
| `l1_course_back` | `250` | `8.00%` | `137.68%` | `0.62` |
| `l2_class_eq_B2` | `836` | `8.25%` | `92.63%` | `0.64` |
| `l3_worst_st` | `5392` | `17.51%` | `91.25%` | `1.36` |
| `l1_worst_class` | `1108` | `13.27%` | `86.13%` | `1.03` |
| `l1_worst_nat` | `4708` | `12.55%` | `83.92%` | `0.97` |

### Exclude `4`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l4_worst_st` | `8133` | `24.33%` | `89.29%` | `1.36` |
| `l4_st_gap_ge_005` | `10774` | `21.59%` | `84.89%` | `1.21` |
| `l4_course_back` | `2262` | `14.28%` | `84.59%` | `0.8` |
| `l2_class_eq_B2` | `836` | `13.40%` | `84.06%` | `0.75` |
| `l4_class_eq_B2` | `1556` | `22.37%` | `79.11%` | `1.25` |
| `l1_class_le_B1` | `11306` | `15.78%` | `77.99%` | `0.88` |

## Best Pair Features

### Exclude `1`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l1_st_gap_ge_005 & l4_class_eq_B2` | `543` | `4.42%` | `236.69%` | `1.32` |
| `l1_slowest_exh & l1_worst_st` | `985` | `12.59%` | `169.60%` | `3.75` |
| `l1_worst_nat & l1_worst_motor` | `273` | `15.75%` | `166.39%` | `4.69` |
| `l1_worst_st & wave_ge_4` | `1277` | `8.85%` | `159.11%` | `2.63` |
| `l1_worst_st & wind_ge_4` | `1771` | `8.41%` | `158.78%` | `2.5` |
| `l1_worst_st & wave_5_6` | `588` | `9.86%` | `141.09%` | `2.93` |

### Exclude `2`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l2_class_eq_B2 & l2_worst_st` | `209` | `22.01%` | `147.19%` | `2.02` |
| `l2_course_back & l1_worst_st` | `306` | `8.50%` | `121.28%` | `0.78` |
| `l2_worst_st & wave_5_6` | `662` | `15.11%` | `115.53%` | `1.39` |
| `l2_course_back & l4_course_front` | `341` | `14.66%` | `113.61%` | `1.35` |
| `l2_worst_class & wave_5_6` | `225` | `18.67%` | `107.43%` | `1.72` |
| `l2_worst_class & l2_worst_st` | `581` | `26.33%` | `106.56%` | `2.42` |

### Exclude `3`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `l3_class_eq_B2 & l3_worst_st` | `209` | `28.71%` | `116.24%` | `2.22` |
| `l3_slowest_exh & l3_worst_st` | `1647` | `21.98%` | `111.29%` | `1.7` |
| `l3_class_eq_B2 & l3_slowest_exh` | `258` | `25.58%` | `102.22%` | `1.98` |
| `l3_worst_st & l3_course_back` | `395` | `16.96%` | `95.54%` | `1.31` |
| `l3_slowest_exh & l3_st_gap_ge_005` | `2755` | `17.79%` | `93.00%` | `1.38` |
| `l3_worst_st & l3_exh_gap_ge_002` | `3587` | `17.70%` | `91.63%` | `1.37` |

### Exclude `4`

| rule | sample | hit rate | ROI | lift |
| --- | ---: | ---: | ---: | ---: |
| `wind_3_4 & l2_class_eq_B2` | `287` | `12.89%` | `117.97%` | `0.72` |
| `l4_course_back & l4_st_gap_ge_005` | `1035` | `16.71%` | `105.24%` | `0.93` |
| `l4_class_eq_B2 & wind_3_4` | `527` | `24.86%` | `102.26%` | `1.39` |
| `l4_st_gap_ge_005 & l2_class_eq_B2` | `342` | `16.67%` | `102.26%` | `0.93` |
| `l4_worst_motor & wind_ge_4` | `565` | `19.47%` | `101.98%` | `1.09` |
| `l4_worst_st & l2_class_eq_B2` | `236` | `19.07%` | `100.20%` | `1.07` |

## Working Read

- `exclude 1` tends to appear when lane 1 is both weak in ST and visually late in exhibition. This is the cleanest high-ROI outside-inside reversal candidate.
- `exclude 2` appears when lane 2 is clearly the weakest among `1..4`, especially `B2` plus worst ST. The read is usable but the sample is smaller.
- `exclude 3` looks practical when lane 3 is both slow in exhibition and worst in exhibition ST. This shape keeps a much larger sample than the lane-2 branch.
- `exclude 4` is already common as a baseline event, but the upside mostly comes from weak-lane4 plus mild environmental filters. It is less surprising than the other three.