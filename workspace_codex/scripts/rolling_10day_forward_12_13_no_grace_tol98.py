from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path


DEFAULT_CYCLE_MONTHS = [
    "2025-01",
    "2025-02",
    "2025-03",
    "2025-04",
    "2025-05",
    "2025-06",
    "2025-07",
    "2025-08",
    "2025-09",
    "2025-10",
    "2025-11",
    "2025-12",
]
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "reports"
    / "strategies"
    / "rolling_10day_forward_2025_train3m_no_grace_12_13_tol98_max10_20260504"
)
FOCUS_COMBOS = {"1-2", "1-3"}
STAKE_YEN = 100


def _load_rolling_module():
    script_path = REPO_ROOT / "workspace_codex" / "scripts" / "rolling_monthly_distortion_extract_forward.py"
    spec = importlib.util.spec_from_file_location("rolling_monthly_distortion_no_grace_12_13", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_window(rolling_mod, cycle_month: str, *, train_months: int):
    cycle_start = pd.Timestamp(f"{cycle_month}-01")
    train_start = (cycle_start - pd.DateOffset(months=train_months)).replace(day=1)
    train_end = cycle_start - pd.Timedelta(days=1)
    target_start = cycle_start.replace(day=11)
    target_end = (cycle_start + pd.DateOffset(months=1)).replace(day=10)
    label = f"{target_start:%Y-%m-%d}_to_{target_end:%Y-%m-%d}"
    return rolling_mod.RollingWindow(
        target_month=label,
        train_start=train_start.strftime("%Y-%m-%d"),
        train_end=train_end.strftime("%Y-%m-%d"),
        target_start=target_start.strftime("%Y-%m-%d"),
        target_end=target_end.strftime("%Y-%m-%d"),
    )


def _monthly_stats(rolling_mod, target_frames: dict[int, pd.DataFrame], candidate: pd.Series) -> dict[str, Any]:
    combo = str(candidate["combo"])
    target_lane = int(combo.split("-")[1])
    target = target_frames[target_lane]
    mask = rolling_mod._mask_for_candidate(target, str(candidate["slice_family"]), str(candidate["slice_value"]))
    focus = target[mask].copy()
    if focus.empty:
        return {
            "positive_months": 0,
            "months_with_sample": 0,
            "bad_loss_months": 0,
            "worst_month_roi_pct": 0.0,
            "monthly_detail": "",
        }
    focus["month"] = focus["race_date"].dt.strftime("%Y-%m")
    positive = 0
    bad_loss = 0
    worst_roi: float | None = None
    details: list[str] = []
    for month, group in focus.groupby("month", observed=True):
        row = rolling_mod._metric(group, combo=combo)
        roi = float(row["roi_pct"])
        profit = int(row["profit_yen"])
        bets = int(row["bets"])
        if roi >= 100.0:
            positive += 1
        if roi < 98.0:
            bad_loss += 1
        worst_roi = roi if worst_roi is None else min(worst_roi, roi)
        details.append(f"{month}:{bets}r/{roi:.2f}%/{profit:+d}")
    return {
        "positive_months": positive,
        "months_with_sample": len(details),
        "bad_loss_months": bad_loss,
        "worst_month_roi_pct": round(float(worst_roi or 0.0), 2),
        "monthly_detail": "; ".join(details),
    }


def _select_candidates(
    rolling_mod,
    distortion_mod,
    train_base: pd.DataFrame,
    slices: pd.DataFrame,
    *,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    min_months_with_sample: int,
    loss_tolerance_roi: float,
    max_candidates: int,
    max_per_combo: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pool = slices[
        slices["combo"].astype(str).isin(FOCUS_COMBOS)
        & (slices["sample_races"] >= min_sample)
        & (slices["roi_pct"] >= min_roi)
        & (slices["roi_lift_pct"] >= min_roi_lift)
        & (slices["profit_yen"] > 0)
    ].copy()
    if pool.empty:
        return pool, pool

    target_frames = {
        lane: distortion_mod._prepare_target_frame(train_base, lane)
        for lane in rolling_mod.SECOND_LANES
    }
    month_rows = [
        _monthly_stats(rolling_mod, target_frames, pd.Series(row._asdict()))
        for row in pool.itertuples(index=False)
    ]
    for key in ("positive_months", "months_with_sample", "bad_loss_months", "worst_month_roi_pct", "monthly_detail"):
        pool[key] = [item[key] for item in month_rows]

    tolerated_floor = float(loss_tolerance_roi)
    pool = pool[
        (pool["positive_months"] >= min_positive_months)
        & (pool["months_with_sample"] >= min_months_with_sample)
        & (pool["bad_loss_months"] == 0)
        & (pool["worst_month_roi_pct"] >= tolerated_floor)
    ].copy()
    if pool.empty:
        return pool, pool

    pool = pool.sort_values(
        ["positive_months", "worst_month_roi_pct", "roi_pct", "sample_races"],
        ascending=[False, False, False, False],
    )

    selected_rows: list[dict[str, Any]] = []
    seen_sets: set[tuple[str, tuple[str, ...]]] = set()
    per_combo_counts: dict[str, int] = {}
    for row in pool.itertuples(index=False):
        combo = str(row.combo)
        if per_combo_counts.get(combo, 0) >= max_per_combo:
            continue
        target_lane = int(combo.split("-")[1])
        target = target_frames[target_lane]
        mask = rolling_mod._mask_for_candidate(target, str(row.slice_family), str(row.slice_value))
        race_ids = tuple(sorted(target.loc[mask, "race_id"].astype(str).unique()))
        key = (combo, race_ids)
        if key in seen_sets:
            continue
        seen_sets.add(key)
        per_combo_counts[combo] = per_combo_counts.get(combo, 0) + 1
        selected_rows.append(row._asdict())
        if len(selected_rows) >= max_candidates:
            break
    return pool, pd.DataFrame(selected_rows)


def _portfolio_by_combo(output_dir: Path) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for month_dir in sorted(path for path in output_dir.iterdir() if path.is_dir()):
        path = month_dir / "target_dedup_bets.csv"
        if not path.exists():
            continue
        if path.stat().st_size == 0:
            continue
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if frame.empty:
            continue
        frame["target_window"] = month_dir.name
        parts.append(frame)
    if not parts:
        return pd.DataFrame(columns=["combo", "bets", "hits", "hit_rate_pct", "profit_yen", "roi_pct"])
    bets = pd.concat(parts, ignore_index=True)
    combo = (
        bets.groupby("combo", observed=True)
        .agg(bets=("combo", "size"), hits=("is_hit", "sum"), return_yen=("return_yen", "sum"))
        .reset_index()
    )
    combo["stake_yen"] = combo["bets"] * STAKE_YEN
    combo["profit_yen"] = combo["return_yen"] - combo["stake_yen"]
    combo["hit_rate_pct"] = (combo["hits"] * 100.0 / combo["bets"]).round(2)
    combo["roi_pct"] = (combo["return_yen"] * 100.0 / combo["stake_yen"]).round(2)
    return combo[["combo", "bets", "hits", "hit_rate_pct", "profit_yen", "roi_pct"]].sort_values("combo")


def _safe_load_base(rolling_mod, scan_mod, db_path: Path, start_date: str, end_date: str) -> pd.DataFrame:
    lane_level = scan_mod._load_lane_level(db_path, start_date, end_date)
    if lane_level.empty:
        return pd.DataFrame()
    return rolling_mod._load_base(scan_mod, db_path, start_date, end_date)


def _empty_target_logic_result(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(selected.itertuples(index=False), start=1):
        rows.append(
            {
                "logic_id": f"L{idx:02d}",
                "combo": str(row.combo),
                "slice_family": row.slice_family,
                "slice_value": row.slice_value,
                "train_sample_races": int(row.sample_races),
                "train_hits": int(row.hits),
                "train_hit_rate_pct": float(row.hit_rate_pct),
                "train_roi_pct": float(row.roi_pct),
                "train_roi_lift_pct": float(row.roi_lift_pct),
                "train_positive_months": int(row.positive_months),
                "target_bets": 0,
                "target_hits": 0,
                "target_hit_rate_pct": 0.0,
                "target_return_yen": 0,
                "target_profit_yen": 0,
                "target_roi_pct": 0.0,
                "target_avg_hit_payout_yen": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _table(frame: pd.DataFrame, cols: list[str]) -> str:
    view = frame[cols].copy()
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def _write_readme(output_dir: Path, summary: pd.DataFrame, by_combo: pd.DataFrame, *, params: dict[str, Any]) -> None:
    total_bets = int(summary["dedup_bets"].sum())
    total_hits = int(summary["dedup_hits"].sum())
    total_profit = int(summary["dedup_profit_yen"].sum())
    total_stake = total_bets * STAKE_YEN
    total_roi = round((total_profit + total_stake) * 100.0 / total_stake, 2) if total_stake else 0.0
    total_hit_rate = round(total_hits * 100.0 / total_bets, 2) if total_bets else 0.0
    readme = f"""# Rolling 10-Day Forward 1-2/1-3 No-Grace Backtest

## Method

- Train period: previous `{params['train_months']}` full months only.
- Grace period: day `1` to `10` of the cycle month is not used for training or scoring.
- Forward period: day `11` of the cycle month through day `10` of the next month.
- Candidate combos: `1-2`, `1-3` only.
- Candidate filters: sample >= `{params['min_sample']}`, ROI >= `{params['min_roi']}`, ROI lift >= `{params['min_roi_lift']}`, profit > 0.
- Monthly stability: at least `{params['min_positive_months']}` positive months, and no sampled month below `{params['loss_tolerance_roi']}` ROI.
- Selection: max `{params['max_candidates']}` candidates, max `{params['max_per_combo']}` per combo, duplicate race-set removal.
- Portfolio accounting deduplicates only by `race_id + combo`; `1-2` and `1-3` in the same race are both kept.

## Total

- bets: `{total_bets}`
- hits: `{total_hits}`
- hit rate: `{total_hit_rate:.2f}%`
- profit: `{total_profit:,} yen`
- ROI: `{total_roi:.2f}%`

## Rolling Summary

{_table(summary, ['target_month', 'train_start', 'train_end', 'target_start', 'target_end', 'quality_candidate_count', 'selected_logic_count', 'dedup_bets', 'dedup_hits', 'dedup_hit_rate_pct', 'dedup_profit_yen', 'dedup_roi_pct'])}

## By Combo

{_table(by_combo, ['combo', 'bets', 'hits', 'hit_rate_pct', 'profit_yen', 'roi_pct'])}

## Files

- `rolling_summary.csv`
- `all_target_logic_results.csv`
- `portfolio_by_combo.csv`
- one subfolder per forward window
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def run(
    *,
    db_path: Path,
    output_dir: Path,
    cycle_months: list[str],
    train_months: int,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    min_months_with_sample: int,
    loss_tolerance_roi: float,
    max_candidates: int,
    max_per_combo: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rolling_mod = _load_rolling_module()
    scan_mod = rolling_mod._load_scan_module()
    distortion_mod = rolling_mod._load_distortion_module()

    summary_rows: list[dict[str, Any]] = []
    logic_parts: list[pd.DataFrame] = []
    for cycle_month in cycle_months:
        window = _build_window(rolling_mod, cycle_month, train_months=train_months)
        month_dir = output_dir / window.target_month
        month_dir.mkdir(parents=True, exist_ok=True)

        print(f"running {window.target_month} train={window.train_start}..{window.train_end}", flush=True)
        train_base = rolling_mod._load_base(scan_mod, db_path, window.train_start, window.train_end)
        target_base = _safe_load_base(rolling_mod, scan_mod, db_path, window.target_start, window.target_end)
        train_overall, train_slices = rolling_mod._scan_slices(distortion_mod, train_base)
        quality_pool, selected = _select_candidates(
            rolling_mod,
            distortion_mod,
            train_base,
            train_slices,
            min_sample=min_sample,
            min_roi=min_roi,
            min_roi_lift=min_roi_lift,
            min_positive_months=min_positive_months,
            min_months_with_sample=min_months_with_sample,
            loss_tolerance_roi=loss_tolerance_roi,
            max_candidates=max_candidates,
            max_per_combo=max_per_combo,
        )
        if target_base.empty:
            logic_result = _empty_target_logic_result(selected)
            raw_bets = pd.DataFrame()
        else:
            logic_result, raw_bets = rolling_mod._validate_selected(distortion_mod, selected, target_base)
        dedup_bets = (
            raw_bets.sort_values(["race_date", "race_id", "combo", "logic_id"])
            .drop_duplicates(["race_id", "combo"])
            .reset_index(drop=True)
            if not raw_bets.empty
            else raw_bets
        )
        portfolio = pd.DataFrame(
            [
                rolling_mod._portfolio_metric(raw_bets, label="raw_with_overlap"),
                rolling_mod._portfolio_metric(dedup_bets, label="dedup_race_combo"),
            ]
        )

        train_overall.to_csv(month_dir / "train_overall_by_combo.csv", index=False, encoding="utf-8-sig")
        train_slices.to_csv(month_dir / "train_all_slices_min30.csv", index=False, encoding="utf-8-sig")
        quality_pool.to_csv(month_dir / "quality_candidate_pool.csv", index=False, encoding="utf-8-sig")
        selected.to_csv(month_dir / "selected_candidates.csv", index=False, encoding="utf-8-sig")
        logic_result.to_csv(month_dir / "target_logic_results.csv", index=False, encoding="utf-8-sig")
        raw_bets.to_csv(month_dir / "target_raw_bets.csv", index=False, encoding="utf-8-sig")
        dedup_bets.to_csv(month_dir / "target_dedup_bets.csv", index=False, encoding="utf-8-sig")
        portfolio.to_csv(month_dir / "target_portfolio_summary.csv", index=False, encoding="utf-8-sig")

        dedup = portfolio[portfolio["portfolio_label"] == "dedup_race_combo"].iloc[0]
        summary_rows.append(
            {
                "cycle_month": cycle_month,
                "target_month": window.target_month,
                "train_start": window.train_start,
                "train_end": window.train_end,
                "target_start": window.target_start,
                "target_end": window.target_end,
                "train_races": int(len(train_base)),
                "target_races": int(len(target_base)),
                "train_slice_rows": int(len(train_slices)),
                "focus_slice_rows": int(train_slices["combo"].astype(str).isin(FOCUS_COMBOS).sum()),
                "quality_candidate_count": int(len(quality_pool)),
                "selected_logic_count": int(len(selected)),
                "dedup_bets": int(dedup["bets"]),
                "dedup_unique_races": int(dedup["unique_races"]),
                "dedup_hits": int(dedup["hits"]),
                "dedup_hit_rate_pct": float(dedup["hit_rate_pct"]),
                "dedup_profit_yen": int(dedup["profit_yen"]),
                "dedup_roi_pct": float(dedup["roi_pct"]),
                "month_dir": str(month_dir),
            }
        )
        if not logic_result.empty:
            logic = logic_result.copy()
            logic.insert(0, "target_window", window.target_month)
            logic.insert(0, "cycle_month", cycle_month)
            logic_parts.append(logic)

    summary = pd.DataFrame(summary_rows)
    all_logic = pd.concat(logic_parts, ignore_index=True) if logic_parts else pd.DataFrame()
    by_combo = _portfolio_by_combo(output_dir)
    summary.to_csv(output_dir / "rolling_summary.csv", index=False, encoding="utf-8-sig")
    all_logic.to_csv(output_dir / "all_target_logic_results.csv", index=False, encoding="utf-8-sig")
    by_combo.to_csv(output_dir / "portfolio_by_combo.csv", index=False, encoding="utf-8-sig")
    _write_readme(
        output_dir,
        summary,
        by_combo,
        params={
            "train_months": train_months,
            "min_sample": min_sample,
            "min_roi": min_roi,
            "min_roi_lift": min_roi_lift,
            "min_positive_months": min_positive_months,
            "loss_tolerance_roi": loss_tolerance_roi,
            "max_candidates": max_candidates,
            "max_per_combo": max_per_combo,
        },
    )

    total_bets = int(summary["dedup_bets"].sum())
    total_profit = int(summary["dedup_profit_yen"].sum())
    total_hits = int(summary["dedup_hits"].sum())
    total_stake = total_bets * STAKE_YEN
    return {
        "output_dir": str(output_dir),
        "cycle_months": ",".join(cycle_months),
        "total_bets": total_bets,
        "total_hits": total_hits,
        "total_profit_yen": total_profit,
        "total_roi_pct": round((total_profit + total_stake) * 100.0 / total_stake, 2) if total_stake else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest 1-2/1-3 rolling slices with no grace-period training.")
    parser.add_argument("--db-path", type=Path, default=default_results_db_path())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cycle-months", nargs="+", default=DEFAULT_CYCLE_MONTHS)
    parser.add_argument("--train-months", type=int, default=3)
    parser.add_argument("--min-sample", type=int, default=300)
    parser.add_argument("--min-roi", type=float, default=108.0)
    parser.add_argument("--min-roi-lift", type=float, default=25.0)
    parser.add_argument("--min-positive-months", type=int, default=2)
    parser.add_argument("--min-months-with-sample", type=int, default=2)
    parser.add_argument("--loss-tolerance-roi", type=float, default=98.0)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--max-per-combo", type=int, default=5)
    args = parser.parse_args()
    result = run(
        db_path=args.db_path,
        output_dir=args.output_dir,
        cycle_months=args.cycle_months,
        train_months=args.train_months,
        min_sample=args.min_sample,
        min_roi=args.min_roi,
        min_roi_lift=args.min_roi_lift,
        min_positive_months=args.min_positive_months,
        min_months_with_sample=args.min_months_with_sample,
        loss_tolerance_roi=args.loss_tolerance_roi,
        max_candidates=args.max_candidates,
        max_per_combo=args.max_per_combo,
    )
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
