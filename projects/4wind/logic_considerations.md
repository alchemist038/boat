# 4wind Logic Considerations

## Promoted View

`4wind` is now treated as a project-level logic.

The current read is no longer just:

- windy race
- lane 4 has an ST edge

The promoted shape is:

- `wind_speed_m in [5, 6]`
- lane 4 structural strength
- partner focus on `4-1 / 4-5`
- `3L = A`
- quoted `min_odds 10-50`

## Formal Definition

Current project definition:

- wind:
  - `wind_speed_m >= 5`
  - `wind_speed_m <= 6`
- structure:
  - `lane4_st_diff_from_inside <= -0.05`
  - `lane4_exhibition_time_rank <= 3`
- inner pressure:
  - `lane3_class in ('A1', 'A2')`
- ticket:
  - `4-1`
  - `4-5`
- price filter:
  - quoted `min_odds >= 10`
  - quoted `min_odds < 50`

## Why 3L = A Became Formal

The lane-3 cut was discovered after the rule had already been narrowed to:

- `only_wind_5_6`
- `4-1 / 4-5`
- `min_odds 10-50`

At that stage, lane-2 and lane-3 classes were sliced.

Lane 3 was much cleaner than lane 2:

- `B2`: ROI `0%`
- `B1`: ROI `151.75%`
- `A2`: ROI `181.0%`
- `A1`: ROI `230.11%`

This natural ordering made `3L = A` a structural component rather than a side hint.

The key confirmation was that the improvement still remained after removing the odds filter:

- `4-1 / 4-5 + wind 5-6`: `662 races`, ROI `142.11%`
- plus `lane3_class in ('A1', 'A2')`: `269 races`, ROI `156.41%`

That is why `3L = A` is now fixed into the promoted project definition.

## Why The Odds Filter Is Formal

Market slicing showed that the bad pockets were the price extremes.

For base `4wind`:

- `<10` was too compressed
- `50+` was too thin

The middle zone was cleaner, so the promoted project shape keeps:

- `min_odds 10-50`

This should be read as part of the current formal definition, not as a temporary convenience filter.

## Current Role

Current role is:

- promoted project logic
- usable as a standalone tracked module
- also usable as a structural component inside combined portfolios

It is still not a high-hit-rate style rule, so practical usage should remain aware of long losing streaks.
