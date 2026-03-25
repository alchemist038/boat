# H-A 2024 Official Settle Proxy

## Purpose

- re-run `H-A` on full-year `2024`
- keep the rule interpretation aligned with the canonical hypothesis note
- use official `results.exacta_payout` because shared `odds_2t` coverage starts on `2025-04-01`

## Canonical H-A Definition

Source:

- [README.md](C:/CODEX_WORK/boat_clone/reports/strategies/zero_base_period_2025-03-11_to_2025-06-16_20260324/README.md)

Interpretation used for this proxy run:

- `lane1_st_top3`
  - implemented as `lane1` exhibition ST rank `<= 3`
- `lane4_ahead_lane1_005`
  - implemented as `lane1_st - lane4_st >= 0.05`
- target combo:
  - exacta `4-1`

## Important Caveat

This is **not** the original quoted-odds scan.

Reason:

- shared `odds_2t` starts on `2025-04-01`
- `2024` can only be re-run with:
  - `beforeinfo_entries`
  - `results.exacta_payout`

So this note should be read as:

- `official settle proxy`
- not a perfect reproduction of the original quoted-odds discovery row
- exacta combo matching is normalized so both `4-1` and `4 - 1` are treated as the same settle result

## 2024 Result

- period:
  - `2024-01-01` to `2024-12-31`
- bets:
  - `922`
- hits:
  - `134`
- investment:
  - `92,200 yen`
- return:
  - `214,110 yen`
- profit:
  - `121,910 yen`
- ROI:
  - `232.22%`
- average hit payout:
  - `1,597.84 yen`
- max drawdown:
  - `-4,140 yen`
- longest losing streak:
  - `30`

## Drawdown / Streak Landmarks

- drawdown peak race:
  - `202402151202`
- drawdown bottom race:
  - `202403281712`
- longest losing streak start:
  - `202403150204`
- longest losing streak end:
  - `202403281712`

## Monthly View

| month | bets | hits | return_yen |
| --- | ---: | ---: | ---: |
| 2024-01 | 91 | 11 | 13,490 |
| 2024-02 | 79 | 14 | 13,550 |
| 2024-03 | 71 | 6 | 6,320 |
| 2024-04 | 67 | 11 | 23,470 |
| 2024-05 | 88 | 15 | 22,220 |
| 2024-06 | 76 | 11 | 24,070 |
| 2024-07 | 71 | 10 | 12,130 |
| 2024-08 | 94 | 10 | 18,060 |
| 2024-09 | 61 | 5 | 7,670 |
| 2024-10 | 73 | 15 | 23,300 |
| 2024-11 | 76 | 13 | 22,050 |
| 2024-12 | 75 | 13 | 27,780 |

## 2025 Proxy Calibration

For the original bounded evaluation slice `2025-04-01` to `2025-06-16`, the same proxy implementation gives:

- bets:
  - `244`
- hits:
  - `15`
- return:
  - `35,860 yen`
- ROI:
  - `146.97%`
- max drawdown:
  - `-19,670 yen`

This is directionally close to the original note, but not an exact row-level reproduction.
