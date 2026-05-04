from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path


DEFAULT_TARGET_MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04"]
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "reports"
    / "strategies"
    / "rolling_monthly_distortion_extract_forward_20260503"
)
STAKE_YEN = 100
SECOND_LANES = (2, 3, 4, 5, 6)
DEFAULT_TRAIN_MONTHS = 6


@dataclass(frozen=True)
class RollingWindow:
    target_month: str
    train_start: str
    train_end: str
    target_start: str
    target_end: str


def _load_module(name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_scan_module():
    return _load_module(
        "scan_1_2_for_rolling_distortion",
        REPO_ROOT / "workspace_codex" / "scripts" / "scan_exacta_1_2_h1_2025_no_index.py",
    )


def _load_distortion_module():
    return _load_module(
        "distortion_extract_for_rolling_forward",
        REPO_ROOT / "workspace_codex" / "scripts" / "extract_h2_2025_exacta_1x_distortions_no_index.py",
    )


def _normalize_combo(value: object) -> str:
    return str(value or "").replace(" ", "")


def _window_for_month(month: str, *, train_months: int) -> RollingWindow:
    target_start_ts = pd.Timestamp(f"{month}-01")
    target_end_ts = target_start_ts + pd.offsets.MonthEnd(0)
    train_start_ts = (target_start_ts - pd.DateOffset(months=train_months)).replace(day=1)
    train_end_ts = target_start_ts - pd.Timedelta(days=1)
    return RollingWindow(
        target_month=month,
        train_start=train_start_ts.strftime("%Y-%m-%d"),
        train_end=train_end_ts.strftime("%Y-%m-%d"),
        target_start=target_start_ts.strftime("%Y-%m-%d"),
        target_end=target_end_ts.strftime("%Y-%m-%d"),
    )


def _features() -> list[str]:
    return [
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


def _pair_features() -> list[tuple[str, str]]:
    return [
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


def _load_base(scan_mod, db_path: Path, start_date: str, end_date: str) -> pd.DataFrame:
    lane_level = scan_mod._load_lane_level(db_path, start_date, end_date)
    base = scan_mod._add_features(scan_mod._build_race_level(lane_level))
    base["race_date"] = pd.to_datetime(base["race_date"])
    base["exacta_combo_norm"] = base["exacta_combo"].map(_normalize_combo)
    return base


def _metric(frame: pd.DataFrame, *, combo: str) -> dict[str, object]:
    sample = int(len(frame))
    hits_frame = frame[frame["exacta_combo_norm"] == combo]
    hits = int(len(hits_frame))
    stake = sample * STAKE_YEN
    returned = int(hits_frame["exacta_payout"].sum())
    return {
        "bets": sample,
        "hits": hits,
        "hit_rate_pct": round(hits * 100.0 / sample, 2) if sample else 0.0,
        "stake_yen": stake,
        "return_yen": returned,
        "profit_yen": returned - stake,
        "roi_pct": round(returned * 100.0 / stake, 2) if stake else 0.0,
        "avg_hit_payout_yen": round(returned / hits, 2) if hits else 0.0,
    }


def _overall_by_combo(distortion_mod, base: pd.DataFrame) -> pd.DataFrame:
    return distortion_mod._overall_by_combo(base)


def _scan_slices(distortion_mod, train_base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    overall = _overall_by_combo(distortion_mod, train_base)
    slice_parts = []
    for lane in SECOND_LANES:
        target = distortion_mod._prepare_target_frame(train_base, lane)
        slice_parts.append(distortion_mod._scan_target(target, _features(), _pair_features(), min_sample=30))
    slices = distortion_mod._add_baseline(pd.concat(slice_parts, ignore_index=True), overall).sort_values(
        ["roi_pct", "sample_races"],
        ascending=[False, False],
    )
    return overall, slices


def _mask_for_candidate(target: pd.DataFrame, slice_family: str, slice_value: str) -> pd.Series:
    if " x " not in slice_family:
        return target[slice_family].astype(str).eq(str(slice_value))
    left, right = slice_family.split(" x ", 1)
    left_value, right_value = str(slice_value).split(" | ", 1)
    return target[left].astype(str).eq(left_value) & target[right].astype(str).eq(right_value)


def _candidate_months(target_frames: dict[int, pd.DataFrame], candidate: pd.Series) -> tuple[int, int]:
    target_lane = int(str(candidate["combo"]).split("-")[1])
    target = target_frames[target_lane]
    mask = _mask_for_candidate(target, str(candidate["slice_family"]), str(candidate["slice_value"]))
    focus = target[mask].copy()
    focus["month"] = focus["race_date"].dt.strftime("%Y-%m")
    positive = 0
    months = 0
    for _, group in focus.groupby("month", observed=True):
        months += 1
        row = _metric(group, combo=str(candidate["combo"]))
        if float(row["roi_pct"]) >= 100.0:
            positive += 1
    return positive, months


def _select_candidates(
    distortion_mod,
    train_base: pd.DataFrame,
    slices: pd.DataFrame,
    *,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    max_candidates: int,
    max_per_combo: int,
) -> pd.DataFrame:
    pool = slices[
        (slices["sample_races"] >= min_sample)
        & (slices["roi_pct"] >= min_roi)
        & (slices["roi_lift_pct"] >= min_roi_lift)
        & (slices["profit_yen"] > 0)
    ].copy()
    if pool.empty:
        return pool

    target_frames = {lane: distortion_mod._prepare_target_frame(train_base, lane) for lane in SECOND_LANES}
    month_rows = []
    for row in pool.itertuples(index=False):
        positive, months = _candidate_months(target_frames, pd.Series(row._asdict()))
        month_rows.append((positive, months))
    pool["positive_months"] = [item[0] for item in month_rows]
    pool["months_with_sample"] = [item[1] for item in month_rows]
    pool = pool[
        (pool["positive_months"] >= min_positive_months)
        & (pool["months_with_sample"] >= min_positive_months)
    ].copy()
    if pool.empty:
        return pool

    pool = pool.sort_values(
        ["positive_months", "roi_pct", "sample_races"],
        ascending=[False, False, False],
    )

    selected_rows = []
    seen_sets: set[tuple[str, tuple[str, ...]]] = set()
    per_combo_counts: dict[str, int] = {}
    for row in pool.itertuples(index=False):
        combo = str(row.combo)
        if per_combo_counts.get(combo, 0) >= max_per_combo:
            continue
        target_lane = int(combo.split("-")[1])
        target = target_frames[target_lane]
        mask = _mask_for_candidate(target, str(row.slice_family), str(row.slice_value))
        race_ids = tuple(sorted(target.loc[mask, "race_id"].astype(str).unique()))
        key = (combo, race_ids)
        if key in seen_sets:
            continue
        seen_sets.add(key)
        per_combo_counts[combo] = per_combo_counts.get(combo, 0) + 1
        selected_rows.append(row._asdict())
        if len(selected_rows) >= max_candidates:
            break
    return pd.DataFrame(selected_rows)


def _validate_selected(
    distortion_mod,
    selected: pd.DataFrame,
    target_base: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if selected.empty:
        return pd.DataFrame(), pd.DataFrame()
    target_frames = {lane: distortion_mod._prepare_target_frame(target_base, lane) for lane in SECOND_LANES}
    logic_rows = []
    bet_rows = []
    for idx, row in enumerate(selected.itertuples(index=False), start=1):
        combo = str(row.combo)
        target_lane = int(combo.split("-")[1])
        target = target_frames[target_lane]
        mask = _mask_for_candidate(target, str(row.slice_family), str(row.slice_value))
        focus = target[mask].copy()
        metric = _metric(focus, combo=combo)
        logic_id = f"L{idx:02d}"
        logic_rows.append(
            {
                "logic_id": logic_id,
                "combo": combo,
                "slice_family": row.slice_family,
                "slice_value": row.slice_value,
                "train_sample_races": int(row.sample_races),
                "train_hits": int(row.hits),
                "train_hit_rate_pct": float(row.hit_rate_pct),
                "train_roi_pct": float(row.roi_pct),
                "train_roi_lift_pct": float(row.roi_lift_pct),
                "train_positive_months": int(row.positive_months),
                "target_bets": metric["bets"],
                "target_hits": metric["hits"],
                "target_hit_rate_pct": metric["hit_rate_pct"],
                "target_return_yen": metric["return_yen"],
                "target_profit_yen": metric["profit_yen"],
                "target_roi_pct": metric["roi_pct"],
                "target_avg_hit_payout_yen": metric["avg_hit_payout_yen"],
            }
        )
        if not focus.empty:
            bets = focus[
                [
                    "race_id",
                    "race_date",
                    "stadium_code",
                    "race_no",
                    "exacta_combo_norm",
                    "exacta_payout",
                ]
            ].copy()
            bets["logic_id"] = logic_id
            bets["combo"] = combo
            bets["is_hit"] = (bets["exacta_combo_norm"] == combo).astype(int)
            bets["return_yen"] = bets["exacta_payout"].where(bets["is_hit"] == 1, 0).astype(int)
            bet_rows.append(bets)
    logic_df = pd.DataFrame(logic_rows)
    bet_df = pd.concat(bet_rows, ignore_index=True) if bet_rows else pd.DataFrame()
    return logic_df, bet_df


def _portfolio_metric(bets: pd.DataFrame, *, label: str) -> dict[str, object]:
    if bets.empty:
        return {
            "portfolio_label": label,
            "bets": 0,
            "unique_races": 0,
            "hits": 0,
            "hit_rate_pct": 0.0,
            "stake_yen": 0,
            "return_yen": 0,
            "profit_yen": 0,
            "roi_pct": 0.0,
        }
    sample = int(len(bets))
    hits = int(bets["is_hit"].sum())
    stake = sample * STAKE_YEN
    returned = int(bets["return_yen"].sum())
    return {
        "portfolio_label": label,
        "bets": sample,
        "unique_races": int(bets["race_id"].nunique()),
        "hits": hits,
        "hit_rate_pct": round(hits * 100.0 / sample, 2) if sample else 0.0,
        "stake_yen": stake,
        "return_yen": returned,
        "profit_yen": returned - stake,
        "roi_pct": round(returned * 100.0 / stake, 2) if stake else 0.0,
    }


def _run_window(
    scan_mod,
    distortion_mod,
    db_path: Path,
    window: RollingWindow,
    output_dir: Path,
    *,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    max_candidates: int,
    max_per_combo: int,
) -> dict[str, object]:
    month_dir = output_dir / window.target_month
    month_dir.mkdir(parents=True, exist_ok=True)

    train_base = _load_base(scan_mod, db_path, window.train_start, window.train_end)
    target_base = _load_base(scan_mod, db_path, window.target_start, window.target_end)
    train_overall, train_slices = _scan_slices(distortion_mod, train_base)
    selected = _select_candidates(
        distortion_mod,
        train_base,
        train_slices,
        min_sample=min_sample,
        min_roi=min_roi,
        min_roi_lift=min_roi_lift,
        min_positive_months=min_positive_months,
        max_candidates=max_candidates,
        max_per_combo=max_per_combo,
    )
    logic_result, raw_bets = _validate_selected(distortion_mod, selected, target_base)
    dedup_bets = (
        raw_bets.sort_values(["race_date", "race_id", "combo", "logic_id"])
        .drop_duplicates(["race_id", "combo"])
        .reset_index(drop=True)
        if not raw_bets.empty
        else raw_bets
    )
    portfolio_rows = [
        _portfolio_metric(raw_bets, label="raw_with_overlap"),
        _portfolio_metric(dedup_bets, label="dedup_race_combo"),
    ]
    portfolio = pd.DataFrame(portfolio_rows)

    train_overall.to_csv(month_dir / "train_overall_by_combo.csv", index=False, encoding="utf-8-sig")
    train_slices.to_csv(month_dir / "train_all_slices_min30.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(month_dir / "selected_candidates.csv", index=False, encoding="utf-8-sig")
    logic_result.to_csv(month_dir / "target_logic_results.csv", index=False, encoding="utf-8-sig")
    raw_bets.to_csv(month_dir / "target_raw_bets.csv", index=False, encoding="utf-8-sig")
    dedup_bets.to_csv(month_dir / "target_dedup_bets.csv", index=False, encoding="utf-8-sig")
    portfolio.to_csv(month_dir / "target_portfolio_summary.csv", index=False, encoding="utf-8-sig")

    dedup = portfolio[portfolio["portfolio_label"] == "dedup_race_combo"].iloc[0]
    return {
        "target_month": window.target_month,
        "train_start": window.train_start,
        "train_end": window.train_end,
        "target_start": window.target_start,
        "target_end": window.target_end,
        "train_races": int(len(train_base)),
        "target_races": int(len(target_base)),
        "train_slice_rows": int(len(train_slices)),
        "selected_logic_count": int(len(selected)),
        "dedup_bets": int(dedup["bets"]),
        "dedup_unique_races": int(dedup["unique_races"]),
        "dedup_hits": int(dedup["hits"]),
        "dedup_hit_rate_pct": float(dedup["hit_rate_pct"]),
        "dedup_profit_yen": int(dedup["profit_yen"]),
        "dedup_roi_pct": float(dedup["roi_pct"]),
        "month_dir": str(month_dir),
    }


def _write_readme(output_dir: Path, summary: pd.DataFrame, all_logic: pd.DataFrame, *, train_months: int) -> None:
    def table(frame: pd.DataFrame, cols: list[str], limit: int | None = None) -> str:
        view = frame[cols].copy()
        if limit is not None:
            view = view.head(limit)
        lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
        for row in view.itertuples(index=False):
            values = [str(v).replace("|", "\\|") for v in row]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    total_bets = int(summary["dedup_bets"].sum())
    total_hits = int(summary["dedup_hits"].sum())
    total_profit = int(summary["dedup_profit_yen"].sum())
    total_stake = total_bets * STAKE_YEN
    roi = round((total_profit + total_stake) * 100.0 / total_stake, 2) if total_stake else 0.0
    hit_rate = round(total_hits * 100.0 / total_bets, 2) if total_bets else 0.0
    top_logic = all_logic.sort_values(["target_roi_pct", "target_bets"], ascending=[False, False]).head(12)
    readme = f"""# Rolling Monthly Distortion Extract Forward

## Method

- For each target month, scan the previous `{train_months}` settled months.
- Automatically extract exacta `1-X` distortion slices without racer-index.
- Select candidates mechanically: min sample, ROI, ROI lift, positive train months, duplicate-race-set removal.
- Apply selected candidates to only the next month.
- Portfolio accounting uses one bet per `race_id + combo` after deduplication.

## Rolling Portfolio Summary

{table(summary, ['target_month', 'train_start', 'train_end', 'selected_logic_count', 'dedup_bets', 'dedup_hits', 'dedup_hit_rate_pct', 'dedup_profit_yen', 'dedup_roi_pct'])}

## Total

- bets: `{total_bets}`
- hits: `{total_hits}`
- hit rate: `{hit_rate:.2f}%`
- profit: `{total_profit:,} yen`
- ROI: `{roi:.2f}%`

## Top Target-Month Logic Results

{table(top_logic, ['target_month', 'logic_id', 'combo', 'slice_family', 'slice_value', 'train_roi_pct', 'target_bets', 'target_hits', 'target_hit_rate_pct', 'target_profit_yen', 'target_roi_pct'])}

## Files

- `rolling_summary.csv`
- `all_target_logic_results.csv`
- one subfolder per target month with selected candidates, bets, and portfolio summary
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def run(
    *,
    db_path: Path,
    output_dir: Path,
    target_months: list[str],
    train_months: int,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    max_candidates: int,
    max_per_combo: int,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scan_mod = _load_scan_module()
    distortion_mod = _load_distortion_module()
    summary_rows = []
    logic_parts = []
    for month in target_months:
        window = _window_for_month(month, train_months=train_months)
        row = _run_window(
            scan_mod,
            distortion_mod,
            db_path,
            window,
            output_dir,
            min_sample=min_sample,
            min_roi=min_roi,
            min_roi_lift=min_roi_lift,
            min_positive_months=min_positive_months,
            max_candidates=max_candidates,
            max_per_combo=max_per_combo,
        )
        summary_rows.append(row)
        logic_path = output_dir / month / "target_logic_results.csv"
        if logic_path.exists():
            logic = pd.read_csv(logic_path)
            if not logic.empty:
                logic.insert(0, "target_month", month)
                logic_parts.append(logic)
    summary = pd.DataFrame(summary_rows)
    all_logic = pd.concat(logic_parts, ignore_index=True) if logic_parts else pd.DataFrame()
    summary.to_csv(output_dir / "rolling_summary.csv", index=False, encoding="utf-8-sig")
    all_logic.to_csv(output_dir / "all_target_logic_results.csv", index=False, encoding="utf-8-sig")
    _write_readme(output_dir, summary, all_logic, train_months=train_months)
    total_bets = int(summary["dedup_bets"].sum())
    total_profit = int(summary["dedup_profit_yen"].sum())
    total_roi = round((total_profit + total_bets * STAKE_YEN) * 100.0 / (total_bets * STAKE_YEN), 2) if total_bets else 0.0
    return {
        "output_dir": str(output_dir),
        "target_months": ",".join(target_months),
        "train_months": train_months,
        "total_bets": total_bets,
        "total_profit_yen": total_profit,
        "total_roi_pct": total_roi,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rolling monthly distortion extraction and next-month forward test.")
    parser.add_argument("--db-path", type=Path, default=default_results_db_path())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-months", nargs="+", default=DEFAULT_TARGET_MONTHS)
    parser.add_argument("--train-months", type=int, default=DEFAULT_TRAIN_MONTHS)
    parser.add_argument("--min-sample", type=int, default=300)
    parser.add_argument("--min-roi", type=float, default=108.0)
    parser.add_argument("--min-roi-lift", type=float, default=25.0)
    parser.add_argument("--min-positive-months", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--max-per-combo", type=int, default=4)
    args = parser.parse_args()
    result = run(
        db_path=args.db_path,
        output_dir=args.output_dir,
        target_months=args.target_months,
        train_months=args.train_months,
        min_sample=args.min_sample,
        min_roi=args.min_roi,
        min_roi_lift=args.min_roi_lift,
        min_positive_months=args.min_positive_months,
        max_candidates=args.max_candidates,
        max_per_combo=args.max_per_combo,
    )
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
