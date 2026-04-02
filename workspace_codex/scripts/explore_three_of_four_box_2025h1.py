from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd


CLASS_POINTS = {"A1": 4, "A2": 3, "B1": 2, "B2": 1}


def load_wide_frame(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    query = f"""
    with race_wide as (
      select
        e.race_id,
        cast(e.race_date as varchar) as race_date,
        r.stadium_code,
        r.race_no,
        r.first_place_lane as p1,
        r.second_place_lane as p2,
        r.third_place_lane as p3,
        r.trifecta_payout,
        max(case when e.lane=1 then e.racer_class end) as l1_class,
        max(case when e.lane=2 then e.racer_class end) as l2_class,
        max(case when e.lane=3 then e.racer_class end) as l3_class,
        max(case when e.lane=4 then e.racer_class end) as l4_class,
        max(case when e.lane=1 then e.national_win_rate end) as l1_nat,
        max(case when e.lane=2 then e.national_win_rate end) as l2_nat,
        max(case when e.lane=3 then e.national_win_rate end) as l3_nat,
        max(case when e.lane=4 then e.national_win_rate end) as l4_nat,
        max(case when e.lane=1 then e.motor_top3_rate end) as l1_motor,
        max(case when e.lane=2 then e.motor_top3_rate end) as l2_motor,
        max(case when e.lane=3 then e.motor_top3_rate end) as l3_motor,
        max(case when e.lane=4 then e.motor_top3_rate end) as l4_motor,
        max(case when b.lane=1 then b.exhibition_time end) as l1_exh,
        max(case when b.lane=2 then b.exhibition_time end) as l2_exh,
        max(case when b.lane=3 then b.exhibition_time end) as l3_exh,
        max(case when b.lane=4 then b.exhibition_time end) as l4_exh,
        max(case when b.lane=1 then b.start_exhibition_st end) as l1_st,
        max(case when b.lane=2 then b.start_exhibition_st end) as l2_st,
        max(case when b.lane=3 then b.start_exhibition_st end) as l3_st,
        max(case when b.lane=4 then b.start_exhibition_st end) as l4_st,
        max(case when b.lane=1 then b.course_entry end) as l1_course,
        max(case when b.lane=2 then b.course_entry end) as l2_course,
        max(case when b.lane=3 then b.course_entry end) as l3_course,
        max(case when b.lane=4 then b.course_entry end) as l4_course,
        max(b.wind_speed_m) as wind_speed_m,
        max(b.wave_height_cm) as wave_height_cm,
        max(m.is_final_day) as is_final_day
      from entries e
      join results r using (race_id)
      left join beforeinfo_entries b using (race_id, lane)
      left join race_meta m using (race_id)
      where e.race_date between date '{start_date}' and date '{end_date}'
        and e.lane between 1 and 4
      group by 1,2,3,4,5,6,7,8
    )
    select * from race_wide
    """
    df = con.execute(query).fetch_df()
    numeric_columns = [
        "l1_nat",
        "l2_nat",
        "l3_nat",
        "l4_nat",
        "l1_motor",
        "l2_motor",
        "l3_motor",
        "l4_motor",
        "l1_exh",
        "l2_exh",
        "l3_exh",
        "l4_exh",
        "l1_st",
        "l2_st",
        "l3_st",
        "l4_st",
        "wind_speed_m",
        "wave_height_cm",
        "trifecta_payout",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def add_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    for lane in range(1, 5):
        work[f"l{lane}_class_pt"] = work[f"l{lane}_class"].map(CLASS_POINTS).fillna(0)

    for miss in range(1, 5):
        target = {1, 2, 3, 4} - {miss}
        work[f"exclude_{miss}_hit"] = (
            work["p1"].isin(target)
            & work["p2"].isin(target)
            & work["p3"].isin(target)
            & (work["p1"] != work["p2"])
            & (work["p1"] != work["p3"])
            & (work["p2"] != work["p3"])
        ).astype(int)

    for family, asc in [
        ("class_pt", False),
        ("nat", False),
        ("motor", False),
        ("exh", True),
        ("st", True),
    ]:
        columns = [f"l{lane}_{family}" for lane in range(1, 5)]
        ranks = work[columns].rank(axis=1, method="min", ascending=asc, na_option="bottom")
        for lane in range(1, 5):
            work[f"l{lane}_{family}_rank"] = ranks[f"l{lane}_{family}"]

    best_exh = work[[f"l{lane}_exh" for lane in range(1, 5)]].min(axis=1)
    best_st = work[[f"l{lane}_st" for lane in range(1, 5)]].min(axis=1)

    features: dict[str, pd.Series] = {}
    for lane in range(1, 5):
        features[f"l{lane}_class_le_B1"] = work[f"l{lane}_class_pt"] <= 2
        features[f"l{lane}_class_eq_B2"] = work[f"l{lane}_class_pt"] == 1
        features[f"l{lane}_worst_class"] = work[f"l{lane}_class_pt_rank"] == 4
        features[f"l{lane}_worst_nat"] = work[f"l{lane}_nat_rank"] == 4
        features[f"l{lane}_worst_motor"] = work[f"l{lane}_motor_rank"] == 4
        features[f"l{lane}_slowest_exh"] = work[f"l{lane}_exh_rank"] == 4
        features[f"l{lane}_worst_st"] = work[f"l{lane}_st_rank"] == 4
        course = pd.to_numeric(work[f"l{lane}_course"], errors="coerce")
        features[f"l{lane}_course_back"] = course > lane
        features[f"l{lane}_course_front"] = course < lane
        features[f"l{lane}_exh_gap_ge_002"] = (work[f"l{lane}_exh"] - best_exh) >= 0.02
        features[f"l{lane}_st_gap_ge_005"] = (work[f"l{lane}_st"] - best_st) >= 0.05

    features["wind_ge_4"] = work["wind_speed_m"] >= 4
    features["wind_3_4"] = work["wind_speed_m"].between(3, 4)
    features["wave_ge_4"] = work["wave_height_cm"] >= 4
    features["wave_5_6"] = work["wave_height_cm"].between(5, 6)
    features["final_day"] = work["is_final_day"] == 1
    feature_frame = pd.DataFrame(features).fillna(False)
    return work, feature_frame


def evaluate_rule(df: pd.DataFrame, mask: pd.Series, hit_column: str) -> tuple[int, int, float, float]:
    sample = int(mask.sum())
    hits = int(df.loc[mask, hit_column].sum())
    payouts = pd.to_numeric(df.loc[mask & (df[hit_column] == 1), "trifecta_payout"], errors="coerce").dropna()
    hit_rate = hits / sample * 100 if sample else 0.0
    roi = payouts.sum() / (sample * 600) * 100 if sample else 0.0
    return sample, hits, hit_rate, roi


def scan_singles(df: pd.DataFrame, feature_frame: pd.DataFrame, min_sample: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for miss in range(1, 5):
        hit_column = f"exclude_{miss}_hit"
        baseline = df[hit_column].mean() * 100
        for feature in feature_frame.columns:
            mask = feature_frame[feature]
            sample, hits, hit_rate, roi = evaluate_rule(df, mask, hit_column)
            if sample < min_sample or hits == 0:
                continue
            rows.append(
                {
                    "exclude_lane": miss,
                    "rule": feature,
                    "sample": sample,
                    "hits": hits,
                    "hit_rate_pct": round(hit_rate, 2),
                    "baseline_hit_rate_pct": round(baseline, 2),
                    "lift_vs_baseline": round(hit_rate / baseline, 2) if baseline else None,
                    "roi_pct": round(roi, 2),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["exclude_lane", "roi_pct", "hit_rate_pct", "sample"],
        ascending=[True, False, False, False],
    )


def build_candidate_feature_sets() -> dict[int, list[str]]:
    return {
        1: [
            *(f"l1_{name}" for name in [
                "class_le_B1",
                "class_eq_B2",
                "worst_class",
                "worst_nat",
                "worst_motor",
                "slowest_exh",
                "worst_st",
                "course_back",
                "exh_gap_ge_002",
                "st_gap_ge_005",
            ]),
            "wind_ge_4",
            "wind_3_4",
            "wave_ge_4",
            "wave_5_6",
            "final_day",
            "l4_class_eq_B2",
        ],
        2: [
            *(f"l2_{name}" for name in [
                "class_le_B1",
                "class_eq_B2",
                "worst_class",
                "worst_nat",
                "worst_motor",
                "slowest_exh",
                "worst_st",
                "course_back",
                "exh_gap_ge_002",
                "st_gap_ge_005",
            ]),
            "wind_ge_4",
            "wind_3_4",
            "wave_ge_4",
            "wave_5_6",
            "final_day",
            "l4_course_front",
            "l1_worst_st",
        ],
        3: [
            *(f"l3_{name}" for name in [
                "class_le_B1",
                "class_eq_B2",
                "worst_class",
                "worst_nat",
                "worst_motor",
                "slowest_exh",
                "worst_st",
                "course_back",
                "exh_gap_ge_002",
                "st_gap_ge_005",
            ]),
            "wind_ge_4",
            "wind_3_4",
            "wave_ge_4",
            "wave_5_6",
            "final_day",
            "l2_course_front",
            "l1_course_back",
        ],
        4: [
            *(f"l4_{name}" for name in [
                "class_le_B1",
                "class_eq_B2",
                "worst_class",
                "worst_nat",
                "worst_motor",
                "slowest_exh",
                "worst_st",
                "course_back",
                "exh_gap_ge_002",
                "st_gap_ge_005",
            ]),
            "wind_ge_4",
            "wind_3_4",
            "wave_ge_4",
            "wave_5_6",
            "final_day",
            "l1_class_le_B1",
            "l2_class_eq_B2",
            "l3_class_eq_B2",
        ],
    }


def scan_pairs(df: pd.DataFrame, feature_frame: pd.DataFrame, min_sample: int) -> pd.DataFrame:
    candidate_sets = build_candidate_feature_sets()
    rows: list[dict[str, object]] = []
    for miss in range(1, 5):
        hit_column = f"exclude_{miss}_hit"
        baseline = df[hit_column].mean() * 100
        candidates = candidate_sets[miss]
        for left_idx, left in enumerate(candidates):
            for right in candidates[left_idx + 1 :]:
                mask = feature_frame[left] & feature_frame[right]
                sample, hits, hit_rate, roi = evaluate_rule(df, mask, hit_column)
                if sample < min_sample or hits < 20:
                    continue
                rows.append(
                    {
                        "exclude_lane": miss,
                        "rule": f"{left} & {right}",
                        "sample": sample,
                        "hits": hits,
                        "hit_rate_pct": round(hit_rate, 2),
                        "baseline_hit_rate_pct": round(baseline, 2),
                        "lift_vs_baseline": round(hit_rate / baseline, 2) if baseline else None,
                        "roi_pct": round(roi, 2),
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["exclude_lane", "roi_pct", "hit_rate_pct", "sample"],
        ascending=[True, False, False, False],
    )


def build_baseline(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_races = len(df)
    for miss in range(1, 5):
        hit_column = f"exclude_{miss}_hit"
        mask = df[hit_column] == 1
        sample = total_races
        hits = int(mask.sum())
        payouts = pd.to_numeric(df.loc[mask, "trifecta_payout"], errors="coerce").dropna()
        hit_rate = hits / sample * 100 if sample else 0.0
        roi = payouts.sum() / (sample * 600) * 100 if sample else 0.0
        rows.append(
            {
                "exclude_lane": miss,
                "sample": sample,
                "hits": hits,
                "hit_rate_pct": round(hit_rate, 2),
                "roi_pct": round(roi, 2),
                "avg_hit_payout_yen": round(payouts.mean(), 1) if not payouts.empty else None,
            }
        )
    return pd.DataFrame(rows)


def write_summary(
    output_dir: Path,
    df: pd.DataFrame,
    baseline: pd.DataFrame,
    singles: pd.DataFrame,
    pairs: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> None:
    summary_path = output_dir / "three_of_four_box_summary_2025h1.md"
    lines = [
        "# 3-of-4 Box Exploration (`2025-01-01 .. 2025-06-30`)",
        "",
        "## Scope",
        "",
        f"- period: `{start_date}` .. `{end_date}`",
        f"- races: `{len(df):,}`",
        "- target framing: remove one boat from lanes `1..4`, then treat the remaining three lanes as a `trifecta 3-boat box` (`6` tickets / `600 yen`)",
        "- settle: `results.trifecta_payout`",
        "- features: pre-race class / national win rate / motor / exhibition time / exhibition ST / course entry / wind / wave / final-day flag",
        "",
        "## Baseline",
        "",
        "| excluded lane | hit rate | ROI | avg hit payout |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in baseline.itertuples(index=False):
        lines.append(
            f"| `{row.exclude_lane}` | `{row.hit_rate_pct:.2f}%` | `{row.roi_pct:.2f}%` | `{row.avg_hit_payout_yen}` |"
        )

    lines.extend(
        [
            "",
            "## Best Single Features",
            "",
        ]
    )
    for miss in range(1, 5):
        lines.append(f"### Exclude `{miss}`")
        lines.append("")
        lines.append("| rule | sample | hit rate | ROI | lift |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        top = singles[singles["exclude_lane"] == miss].head(6)
        for row in top.itertuples(index=False):
            lines.append(
                f"| `{row.rule}` | `{row.sample}` | `{row.hit_rate_pct:.2f}%` | `{row.roi_pct:.2f}%` | `{row.lift_vs_baseline}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## Best Pair Features",
            "",
        ]
    )
    for miss in range(1, 5):
        lines.append(f"### Exclude `{miss}`")
        lines.append("")
        lines.append("| rule | sample | hit rate | ROI | lift |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        top = pairs[pairs["exclude_lane"] == miss].head(6)
        for row in top.itertuples(index=False):
            lines.append(
                f"| `{row.rule}` | `{row.sample}` | `{row.hit_rate_pct:.2f}%` | `{row.roi_pct:.2f}%` | `{row.lift_vs_baseline}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## Working Read",
            "",
            "- `exclude 1` tends to appear when lane 1 is both weak in ST and visually late in exhibition. This is the cleanest high-ROI outside-inside reversal candidate.",
            "- `exclude 2` appears when lane 2 is clearly the weakest among `1..4`, especially `B2` plus worst ST. The read is usable but the sample is smaller.",
            "- `exclude 3` looks practical when lane 3 is both slow in exhibition and worst in exhibition ST. This shape keeps a much larger sample than the lane-2 branch.",
            "- `exclude 4` is already common as a baseline event, but the upside mostly comes from weak-lane4 plus mild environmental filters. It is less surprising than the other three.",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore 3-of-4 trifecta box hypotheses on 2025H1 data.")
    parser.add_argument(
        "--db-path",
        default="\\\\038INS\\boat\\data\\silver\\boat_race.duckdb",
        help="DuckDB path.",
    )
    parser.add_argument(
        "--output-dir",
        default="C:\\CODEX_WORK\\boat_clone\\reports\\strategies\\recent_checks\\three_of_four_box_2025h1_20260402",
        help="Output directory.",
    )
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--end-date", default="2025-06-30")
    parser.add_argument("--min-single-sample", type=int, default=150)
    parser.add_argument("--min-pair-sample", type=int, default=200)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_wide_frame(args.db_path, args.start_date, args.end_date)
    df, feature_frame = add_features(df)
    baseline = build_baseline(df)
    singles = scan_singles(df, feature_frame, args.min_single_sample)
    pairs = scan_pairs(df, feature_frame, args.min_pair_sample)

    baseline.to_csv(output_dir / "three_of_four_box_baseline_2025h1.csv", index=False, encoding="utf-8-sig")
    singles.to_csv(output_dir / "three_of_four_box_single_scan_2025h1.csv", index=False, encoding="utf-8-sig")
    pairs.to_csv(output_dir / "three_of_four_box_pair_scan_2025h1.csv", index=False, encoding="utf-8-sig")
    write_summary(output_dir, df, baseline, singles, pairs, args.start_date, args.end_date)

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
