from __future__ import annotations

import argparse
import importlib.util
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path


DEFAULT_START_DATE = "2025-07-01"
DEFAULT_END_DATE = "2025-12-31"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "reports"
    / "strategies"
    / "exacta_1x_h2_2025_distortion_extract_no_index_20260503"
)
STAKE_YEN = 100
SECOND_LANES = (2, 3, 4, 5, 6)


def _load_12_scan_module():
    script_path = REPO_ROOT / "workspace_codex" / "scripts" / "scan_exacta_1_2_h1_2025_no_index.py"
    spec = importlib.util.spec_from_file_location("scan_1_2_no_index_for_distortion", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_combo(value: object) -> str:
    return str(value or "").replace(" ", "")


def _bucket_rate_diff(value: object) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number <= -1.00:
        return "target_plus_1.00+"
    if number <= -0.35:
        return "target_plus_0.35_1.00"
    if number < 0.35:
        return "near_equal"
    if number < 1.00:
        return "lane1_plus_0.35_1.00"
    return "lane1_plus_1.00+"


def _bucket_place_diff(value: object) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number <= -10.0:
        return "target_plus_10+"
    if number <= -4.0:
        return "target_plus_4_10"
    if number < 4.0:
        return "near_equal"
    if number < 10.0:
        return "lane1_plus_4_10"
    return "lane1_plus_10+"


def _bucket_time_diff(value: object, *, tight: float, wide: float) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number <= -wide:
        return f"lane1_faster_{wide:.2f}+"
    if number <= -tight:
        return f"lane1_faster_{tight:.2f}_{wide:.2f}"
    if number < tight:
        return "near_equal"
    if number < wide:
        return f"target_faster_{tight:.2f}_{wide:.2f}"
    return f"target_faster_{wide:.2f}+"


def _bucket_count(value: object) -> str:
    if pd.isna(value):
        return "missing"
    return str(int(value))


def _lane_zone(lane: int) -> str:
    if lane in {2, 3}:
        return "inner_2_3"
    if lane == 4:
        return "center_4"
    return "outer_5_6"


def _metric(frame: pd.DataFrame, *, combo: str, feature: str, value: str) -> dict[str, object]:
    sample = int(len(frame))
    hits_frame = frame[frame["exacta_combo_norm"] == combo]
    hits = int(len(hits_frame))
    stake = sample * STAKE_YEN
    returned = int(hits_frame["exacta_payout"].sum())
    return {
        "combo": combo,
        "slice_family": feature,
        "slice_value": value,
        "sample_races": sample,
        "hits": hits,
        "hit_rate_pct": round(hits * 100.0 / sample, 2) if sample else 0.0,
        "stake_yen": stake,
        "return_yen": returned,
        "profit_yen": returned - stake,
        "roi_pct": round(returned * 100.0 / stake, 2) if stake else 0.0,
        "avg_hit_payout_yen": round(returned / hits, 2) if hits else 0.0,
    }


def _overall_by_combo(frame: pd.DataFrame) -> pd.DataFrame:
    rows = [_metric(frame, combo=f"1-{lane}", feature="overall", value="all") for lane in SECOND_LANES]
    return pd.DataFrame(rows)


def _prepare_target_frame(base: pd.DataFrame, target_lane: int) -> pd.DataFrame:
    df = base.copy()
    combo = f"1-{target_lane}"
    other_lanes = [lane for lane in SECOND_LANES if lane != target_lane]
    df["combo"] = combo
    df["target_lane"] = str(target_lane)
    df["target_lane_zone"] = _lane_zone(target_lane)

    for suffix in [
        "class",
        "class_group",
        "national_win_rank_bucket",
        "national_place_rank_bucket",
        "local_win_rank_bucket",
        "local_place_rank_bucket",
        "motor_rank_bucket",
        "boat_rank_bucket",
        "avg_start_rank_bucket",
        "exhibition_rank_bucket",
        "exhibition_st_rank_bucket",
        "national_win_rate_bucket",
        "local_win_rate_bucket",
        "motor_place_rate_bucket",
        "boat_place_rate_bucket",
        "national_place_rate_bucket",
        "local_place_rate_bucket",
        "exhibition_gap_bucket",
        "start_exhibition_gap_bucket",
    ]:
        df[f"target_{suffix}"] = df[f"lane{target_lane}_{suffix}"].astype(str)

    df["lane1_target_class_pair"] = df["lane1_class"].astype(str) + "-" + df["target_class"]
    df["lane1_target_group_pair"] = df["lane1_class_group"].astype(str) + "-" + df["target_class_group"]
    df["lane1_target_national_rank_pair"] = (
        df["lane1_national_win_rank_bucket"].astype(str) + "-" + df["target_national_win_rank_bucket"]
    )
    df["lane1_target_exhibition_st_rank_pair"] = (
        df["lane1_exhibition_st_rank_bucket"].astype(str) + "-" + df["target_exhibition_st_rank_bucket"]
    )
    df["lane1_target_start_gap_pair"] = (
        df["lane1_start_exhibition_gap_bucket"].astype(str) + "-" + df["target_start_exhibition_gap_bucket"]
    )

    df["lane1_target_national_win_diff"] = (
        df["lane1_national_win_rate"] - df[f"lane{target_lane}_national_win_rate"]
    ).round(3)
    df["lane1_target_local_win_diff"] = (
        df["lane1_local_win_rate"] - df[f"lane{target_lane}_local_win_rate"]
    ).round(3)
    df["lane1_target_motor_place_diff"] = (
        df["lane1_motor_place_rate"] - df[f"lane{target_lane}_motor_place_rate"]
    ).round(3)
    df["lane1_target_boat_place_diff"] = (
        df["lane1_boat_place_rate"] - df[f"lane{target_lane}_boat_place_rate"]
    ).round(3)
    df["lane1_target_exhibition_time_diff"] = (
        df["lane1_exhibition_time"] - df[f"lane{target_lane}_exhibition_time"]
    ).round(3)
    df["lane1_target_start_exhibition_st_diff"] = (
        df["lane1_start_exhibition_st"] - df[f"lane{target_lane}_start_exhibition_st"]
    ).round(3)
    df["lane1_target_national_win_diff_bucket"] = df["lane1_target_national_win_diff"].map(_bucket_rate_diff)
    df["lane1_target_local_win_diff_bucket"] = df["lane1_target_local_win_diff"].map(_bucket_rate_diff)
    df["lane1_target_motor_place_diff_bucket"] = df["lane1_target_motor_place_diff"].map(_bucket_place_diff)
    df["lane1_target_boat_place_diff_bucket"] = df["lane1_target_boat_place_diff"].map(_bucket_place_diff)
    df["lane1_target_exhibition_time_diff_bucket"] = df["lane1_target_exhibition_time_diff"].map(
        lambda v: _bucket_time_diff(v, tight=0.05, wide=0.10)
    )
    df["lane1_target_start_exhibition_st_diff_bucket"] = df["lane1_target_start_exhibition_st_diff"].map(
        lambda v: _bucket_time_diff(v, tight=0.03, wide=0.06)
    )

    df["other_a_count"] = df[[f"lane{lane}_class_group" for lane in other_lanes]].eq("A").sum(axis=1)
    df["other_b2_count"] = df[[f"lane{lane}_class" for lane in other_lanes]].eq("B2").sum(axis=1)
    df["other_a_count_bucket"] = df["other_a_count"].map(_bucket_count)
    df["other_b2_count_bucket"] = df["other_b2_count"].map(_bucket_count)
    df["other_group_pattern"] = df[[f"lane{lane}_class_group" for lane in other_lanes]].agg("-".join, axis=1)

    for source_col, target_col in [
        ("national_win_rate", "other_national_better_than_target_count"),
        ("local_win_rate", "other_local_better_than_target_count"),
        ("motor_place_rate", "other_motor_better_than_target_count"),
        ("boat_place_rate", "other_boat_better_than_target_count"),
    ]:
        other_cols = [f"lane{lane}_{source_col}" for lane in other_lanes]
        df[target_col] = df[other_cols].gt(df[f"lane{target_lane}_{source_col}"], axis=0).sum(axis=1)
        df[f"{target_col}_bucket"] = df[target_col].map(_bucket_count)

    df["other_exhibition_faster_than_target_count"] = df[
        [f"lane{lane}_exhibition_time" for lane in other_lanes]
    ].lt(df[f"lane{target_lane}_exhibition_time"], axis=0).sum(axis=1)
    df["other_st_faster_than_target_count"] = df[
        [f"lane{lane}_start_exhibition_st" for lane in other_lanes]
    ].lt(df[f"lane{target_lane}_start_exhibition_st"], axis=0).sum(axis=1)
    df["other_exhibition_faster_than_target_count_bucket"] = df[
        "other_exhibition_faster_than_target_count"
    ].map(_bucket_count)
    df["other_st_faster_than_target_count_bucket"] = df["other_st_faster_than_target_count"].map(_bucket_count)
    df["target_outer_pressure_bucket"] = np.select(
        [
            df["other_national_better_than_target_count"].ge(2)
            | df["other_exhibition_faster_than_target_count"].ge(2),
            df["other_national_better_than_target_count"].eq(1)
            | df["other_exhibition_faster_than_target_count"].eq(1),
        ],
        ["high_other_pressure", "some_other_pressure"],
        default="low_other_pressure",
    )
    df["target_hit"] = (df["exacta_combo_norm"] == combo).astype(int)
    df["target_return_yen"] = np.where(df["target_hit"] == 1, df["exacta_payout"], 0).astype(int)
    return df


def _scan_target(target: pd.DataFrame, features: list[str], pair_features: list[tuple[str, str]], min_sample: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    combo = str(target["combo"].iloc[0])
    for feature in features:
        for value, group in target.groupby(feature, dropna=False, observed=True):
            value_text = "missing" if pd.isna(value) else str(value)
            row = _metric(group, combo=combo, feature=feature, value=value_text)
            if int(row["sample_races"]) >= min_sample:
                rows.append(row)
    for left, right in pair_features:
        for values, group in target.groupby([left, right], dropna=False, observed=True):
            left_value, right_value = values
            row = _metric(
                group,
                combo=combo,
                feature=f"{left} x {right}",
                value=(
                    f"{'missing' if pd.isna(left_value) else left_value}"
                    f" | {'missing' if pd.isna(right_value) else right_value}"
                ),
            )
            if int(row["sample_races"]) >= min_sample:
                rows.append(row)
    return pd.DataFrame(rows)


def _add_baseline(slices: pd.DataFrame, overall: pd.DataFrame) -> pd.DataFrame:
    baseline = overall[["combo", "hit_rate_pct", "roi_pct", "avg_hit_payout_yen"]].rename(
        columns={
            "hit_rate_pct": "baseline_hit_rate_pct",
            "roi_pct": "baseline_roi_pct",
            "avg_hit_payout_yen": "baseline_avg_hit_payout_yen",
        }
    )
    out = slices.merge(baseline, on="combo", how="left")
    out["roi_lift_pct"] = (out["roi_pct"] - out["baseline_roi_pct"]).round(2)
    out["hit_rate_lift_pct"] = (out["hit_rate_pct"] - out["baseline_hit_rate_pct"]).round(2)
    out["avg_payout_lift_yen"] = (out["avg_hit_payout_yen"] - out["baseline_avg_hit_payout_yen"]).round(2)
    out["distortion_type"] = np.select(
        [
            (out["roi_lift_pct"] >= 25) & (out["avg_payout_lift_yen"] >= 80),
            (out["roi_lift_pct"] >= 25) & (out["hit_rate_lift_pct"] >= 5),
        ],
        ["price_distortion", "probability_plus_price"],
        default="mixed_edge",
    )
    return out


def _monthly_summary(base: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if candidates.empty:
        return pd.DataFrame()
    target_frames = {lane: _prepare_target_frame(base, lane) for lane in SECOND_LANES}
    for candidate in candidates.itertuples(index=False):
        target_lane = int(str(candidate.combo).split("-")[1])
        target = target_frames[target_lane]
        if " x " in candidate.slice_family:
            left, right = str(candidate.slice_family).split(" x ", 1)
            left_value, right_value = str(candidate.slice_value).split(" | ", 1)
            mask = target[left].astype(str).eq(left_value) & target[right].astype(str).eq(right_value)
        else:
            mask = target[str(candidate.slice_family)].astype(str).eq(str(candidate.slice_value))
        focus = target[mask].copy()
        focus["month"] = pd.to_datetime(focus["race_date"]).dt.strftime("%Y-%m")
        positive_months = 0
        months_with_sample = 0
        monthly_parts: list[str] = []
        for month, group in focus.groupby("month", observed=True):
            row = _metric(group, combo=str(candidate.combo), feature="month", value=str(month))
            months_with_sample += 1
            if float(row["roi_pct"]) >= 100.0:
                positive_months += 1
            monthly_parts.append(
                f"{month}:{row['sample_races']}r/{row['roi_pct']:.2f}%/{row['profit_yen']:+d}"
            )
        rows.append(
            {
                "combo": candidate.combo,
                "slice_family": candidate.slice_family,
                "slice_value": candidate.slice_value,
                "positive_months": positive_months,
                "months_with_sample": months_with_sample,
                "monthly_detail": "; ".join(monthly_parts),
            }
        )
    return pd.DataFrame(rows)


def _write_readme(
    output_dir: Path,
    *,
    start_date: str,
    end_date: str,
    overall: pd.DataFrame,
    candidates_min300: pd.DataFrame,
    candidates_min100: pd.DataFrame,
    monthly: pd.DataFrame,
) -> None:
    def table(frame: pd.DataFrame, cols: list[str], limit: int = 14) -> str:
        view = frame[cols].head(limit).copy()
        lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
        for row in view.itertuples(index=False):
            values = [str(v).replace("|", "\\|") for v in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    main_cols = [
        "combo",
        "slice_family",
        "slice_value",
        "sample_races",
        "hits",
        "hit_rate_pct",
        "roi_pct",
        "roi_lift_pct",
        "profit_yen",
        "avg_hit_payout_yen",
        "distortion_type",
    ]
    readme = f"""# Exacta 1-X Distortion Extract, 2025H2, No Racer Index

## Scope

- period: `{start_date}` to `{end_date}`
- bet shapes: `1-2`, `1-3`, `1-4`, `1-5`, `1-6`
- stake model: 100 yen per exacta combo
- no racer-index
- extraction read: ROI lift vs each combo baseline, hit-rate lift, average hit payout
- note: this is in-sample discovery for 2025H2, not a forward result

## Combo Baselines

{table(overall, ['combo', 'sample_races', 'hits', 'hit_rate_pct', 'return_yen', 'profit_yen', 'roi_pct', 'avg_hit_payout_yen'])}

## Main Distortion Candidates, Min 300 Races

{table(candidates_min300, main_cols)}

## Smaller Distortion Candidates, Min 100 Races

{table(candidates_min100, main_cols)}

## Monthly Persistence For Main Candidates

{table(monthly, ['combo', 'slice_family', 'slice_value', 'positive_months', 'months_with_sample', 'monthly_detail'], limit=10)}

## Files

- `overall_by_combo.csv`
- `all_slices_min30.csv`
- `distortion_candidates_min300.csv`
- `distortion_candidates_min100.csv`
- `monthly_persistence_top_candidates.csv`
- `race_level_h2_2025.csv`
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def run(db_path: Path, output_dir: Path, start_date: str, end_date: str) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scan_mod = _load_12_scan_module()
    lane_level = scan_mod._load_lane_level(db_path, start_date, end_date)
    base = scan_mod._add_features(scan_mod._build_race_level(lane_level))
    base["exacta_combo_norm"] = base["exacta_combo"].map(_normalize_combo)
    overall = _overall_by_combo(base)

    features = [
        "month",
        "stadium_code",
        "race_no_bucket",
        "grade_group",
        "meeting_phase_bucket",
        "wind_bucket",
        "wave_bucket",
        "lane1_class",
        "lane1_class_group",
        "lane1_national_win_rank_bucket",
        "lane1_local_win_rank_bucket",
        "lane1_motor_rank_bucket",
        "lane1_boat_rank_bucket",
        "lane1_exhibition_rank_bucket",
        "lane1_exhibition_st_rank_bucket",
        "lane1_start_exhibition_gap_bucket",
        "target_lane",
        "target_lane_zone",
        "target_class",
        "target_class_group",
        "target_national_win_rank_bucket",
        "target_local_win_rank_bucket",
        "target_motor_rank_bucket",
        "target_boat_rank_bucket",
        "target_exhibition_rank_bucket",
        "target_exhibition_st_rank_bucket",
        "target_start_exhibition_gap_bucket",
        "lane1_target_class_pair",
        "lane1_target_group_pair",
        "lane1_target_national_rank_pair",
        "lane1_target_exhibition_st_rank_pair",
        "lane1_target_start_gap_pair",
        "lane1_target_national_win_diff_bucket",
        "lane1_target_local_win_diff_bucket",
        "lane1_target_motor_place_diff_bucket",
        "lane1_target_boat_place_diff_bucket",
        "lane1_target_exhibition_time_diff_bucket",
        "lane1_target_start_exhibition_st_diff_bucket",
        "other_a_count_bucket",
        "other_b2_count_bucket",
        "other_group_pattern",
        "other_national_better_than_target_count_bucket",
        "other_exhibition_faster_than_target_count_bucket",
        "other_st_faster_than_target_count_bucket",
        "target_outer_pressure_bucket",
    ]
    pair_features = [
        ("target_lane", "target_class_group"),
        ("target_lane", "target_exhibition_st_rank_bucket"),
        ("target_lane", "target_start_exhibition_gap_bucket"),
        ("target_lane", "lane1_target_start_gap_pair"),
        ("target_lane", "lane1_target_national_rank_pair"),
        ("target_lane", "target_outer_pressure_bucket"),
        ("target_lane", "other_a_count_bucket"),
        ("target_class_group", "target_outer_pressure_bucket"),
        ("lane1_target_group_pair", "target_outer_pressure_bucket"),
        ("lane1_target_group_pair", "other_a_count_bucket"),
        ("lane1_exhibition_st_rank_bucket", "target_exhibition_st_rank_bucket"),
        ("lane1_start_exhibition_gap_bucket", "target_start_exhibition_gap_bucket"),
        ("lane1_target_national_rank_pair", "target_outer_pressure_bucket"),
        ("lane1_target_start_gap_pair", "target_outer_pressure_bucket"),
        ("lane1_target_exhibition_time_diff_bucket", "lane1_target_start_exhibition_st_diff_bucket"),
        ("target_exhibition_st_rank_bucket", "other_st_faster_than_target_count_bucket"),
        ("target_exhibition_rank_bucket", "other_exhibition_faster_than_target_count_bucket"),
        ("target_national_win_rank_bucket", "other_national_better_than_target_count_bucket"),
        ("race_no_bucket", "target_lane"),
        ("stadium_code", "target_lane"),
        ("meeting_phase_bucket", "target_lane"),
    ]

    slice_parts = []
    for lane in SECOND_LANES:
        target = _prepare_target_frame(base, lane)
        slice_parts.append(_scan_target(target, features, pair_features, min_sample=30))
    slices = _add_baseline(pd.concat(slice_parts, ignore_index=True), overall).sort_values(
        ["roi_pct", "sample_races"],
        ascending=[False, False],
    )

    candidates_min300 = (
        slices[
            (slices["sample_races"] >= 300)
            & (slices["roi_pct"] >= 108.0)
            & (slices["roi_lift_pct"] >= 25.0)
            & (slices["profit_yen"] > 0)
        ]
        .sort_values(["roi_pct", "sample_races"], ascending=[False, False])
        .head(80)
    )
    candidates_min100 = (
        slices[
            (slices["sample_races"] >= 100)
            & (slices["sample_races"] < 300)
            & (slices["roi_pct"] >= 120.0)
            & (slices["roi_lift_pct"] >= 35.0)
            & (slices["profit_yen"] > 0)
        ]
        .sort_values(["roi_pct", "sample_races"], ascending=[False, False])
        .head(80)
    )
    monthly_source = candidates_min300.head(20)
    monthly = _monthly_summary(base, monthly_source)
    if not monthly.empty:
        candidates_min300 = candidates_min300.merge(
            monthly[["combo", "slice_family", "slice_value", "positive_months", "months_with_sample"]],
            on=["combo", "slice_family", "slice_value"],
            how="left",
        )

    overall.to_csv(output_dir / "overall_by_combo.csv", index=False, encoding="utf-8-sig")
    slices.to_csv(output_dir / "all_slices_min30.csv", index=False, encoding="utf-8-sig")
    candidates_min300.to_csv(output_dir / "distortion_candidates_min300.csv", index=False, encoding="utf-8-sig")
    candidates_min100.to_csv(output_dir / "distortion_candidates_min100.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(output_dir / "monthly_persistence_top_candidates.csv", index=False, encoding="utf-8-sig")
    base.to_csv(output_dir / "race_level_h2_2025.csv", index=False, encoding="utf-8-sig")
    _write_readme(
        output_dir,
        start_date=start_date,
        end_date=end_date,
        overall=overall,
        candidates_min300=candidates_min300,
        candidates_min100=candidates_min100,
        monthly=monthly,
    )

    return {
        "output_dir": str(output_dir),
        "race_count": int(len(base)),
        "slice_rows": int(len(slices)),
        "candidates_min300": int(len(candidates_min300)),
        "candidates_min100": int(len(candidates_min100)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract 2025H2 exacta 1-X distortion candidates without racer-index.")
    parser.add_argument("--db-path", type=Path, default=default_results_db_path())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    args = parser.parse_args()
    result = run(args.db_path, args.output_dir, args.start_date, args.end_date)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
