from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

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
    / "rolling_10day_train_forward_2025_train3m_20260503"
)
STAKE_YEN = 100


def _load_rolling_module():
    script_path = REPO_ROOT / "workspace_codex" / "scripts" / "rolling_monthly_distortion_extract_forward.py"
    spec = importlib.util.spec_from_file_location("rolling_monthly_distortion_for_10day_forward", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_window(rolling_mod, cycle_month: str, *, train_months: int):
    cycle_start = pd.Timestamp(f"{cycle_month}-01")
    train_start = (cycle_start - pd.DateOffset(months=train_months)).replace(day=1)
    train_end = cycle_start.replace(day=10)
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


def _portfolio_by_combo(output_dir: Path) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for month_dir in sorted(path for path in output_dir.iterdir() if path.is_dir()):
        path = month_dir / "target_dedup_bets.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path)
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


def _portfolio_for_combos(output_dir: Path, combos: set[str], *, label: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for month_dir in sorted(path for path in output_dir.iterdir() if path.is_dir()):
        path = month_dir / "target_dedup_bets.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        focus = frame[frame["combo"].isin(combos)].copy()
        bets = int(len(focus))
        hits = int(focus["is_hit"].sum()) if bets else 0
        returned = int(focus["return_yen"].sum()) if bets else 0
        stake = bets * STAKE_YEN
        rows.append(
            {
                "portfolio_label": label,
                "target_window": month_dir.name,
                "bets": bets,
                "hits": hits,
                "hit_rate_pct": round(hits * 100.0 / bets, 2) if bets else 0.0,
                "profit_yen": returned - stake,
                "roi_pct": round(returned * 100.0 / stake, 2) if stake else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _table(frame: pd.DataFrame, cols: list[str]) -> str:
    view = frame[cols].copy()
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def _write_readme(
    output_dir: Path,
    summary: pd.DataFrame,
    by_combo: pd.DataFrame,
    focus_12_13: pd.DataFrame,
    *,
    train_months: int,
    warmup_days: int,
) -> None:
    total_bets = int(summary["dedup_bets"].sum())
    total_hits = int(summary["dedup_hits"].sum())
    total_profit = int(summary["dedup_profit_yen"].sum())
    total_stake = total_bets * STAKE_YEN
    total_roi = round((total_profit + total_stake) * 100.0 / total_stake, 2) if total_stake else 0.0
    total_hit_rate = round(total_hits * 100.0 / total_bets, 2) if total_bets else 0.0
    focus_total = focus_12_13.agg({"bets": "sum", "hits": "sum", "profit_yen": "sum"}).to_dict()
    focus_bets = int(focus_total.get("bets", 0) or 0)
    focus_hits = int(focus_total.get("hits", 0) or 0)
    focus_profit = int(focus_total.get("profit_yen", 0) or 0)
    focus_stake = focus_bets * STAKE_YEN
    focus_roi = round((focus_profit + focus_stake) * 100.0 / focus_stake, 2) if focus_stake else 0.0
    focus_hit_rate = round(focus_hits * 100.0 / focus_bets, 2) if focus_bets else 0.0

    readme = f"""# Rolling 10-Day Train Forward Distortion Backtest

## Method

- Train on the previous `{train_months}` months plus the first `{warmup_days}` days of the cycle month.
- Forward/practice period: day `11` of the cycle month through day `10` of the next month.
- Candidate extraction is the same exacta `1-X` distortion scan used by the monthly rolling test.
- Portfolio accounting deduplicates only by `race_id + combo`; different combos in the same race are both kept.

## Overall Portfolio

- bets: `{total_bets}`
- hits: `{total_hits}`
- hit rate: `{total_hit_rate:.2f}%`
- profit: `{total_profit:,} yen`
- ROI: `{total_roi:.2f}%`

## 1-2 / 1-3 Focus

- bets: `{focus_bets}`
- hits: `{focus_hits}`
- hit rate: `{focus_hit_rate:.2f}%`
- profit: `{focus_profit:,} yen`
- ROI: `{focus_roi:.2f}%`

## Rolling Summary

{_table(summary, ['target_month', 'train_start', 'train_end', 'target_start', 'target_end', 'selected_logic_count', 'dedup_bets', 'dedup_hits', 'dedup_hit_rate_pct', 'dedup_profit_yen', 'dedup_roi_pct'])}

## By Combo

{_table(by_combo, ['combo', 'bets', 'hits', 'hit_rate_pct', 'profit_yen', 'roi_pct'])}

## 1-2 / 1-3 Monthly

{_table(focus_12_13, ['target_window', 'bets', 'hits', 'hit_rate_pct', 'profit_yen', 'roi_pct'])}

## Files

- `rolling_summary.csv`
- `all_target_logic_results.csv`
- `portfolio_by_combo.csv`
- `portfolio_12_13_monthly.csv`
- one subfolder per forward window
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def run(
    *,
    db_path: Path,
    output_dir: Path,
    cycle_months: list[str],
    train_months: int,
    warmup_days: int,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    max_candidates: int,
    max_per_combo: int,
) -> dict[str, object]:
    if warmup_days != 10:
        raise ValueError("This backtest currently implements the fixed 10-day warmup requested by the operator.")
    output_dir.mkdir(parents=True, exist_ok=True)
    rolling_mod = _load_rolling_module()
    scan_mod = rolling_mod._load_scan_module()
    distortion_mod = rolling_mod._load_distortion_module()

    summary_rows: list[dict[str, object]] = []
    logic_parts: list[pd.DataFrame] = []
    for cycle_month in cycle_months:
        window = _build_window(rolling_mod, cycle_month, train_months=train_months)
        row = rolling_mod._run_window(
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
        row["cycle_month"] = cycle_month
        summary_rows.append(row)
        logic_path = output_dir / window.target_month / "target_logic_results.csv"
        if logic_path.exists():
            logic = pd.read_csv(logic_path)
            if not logic.empty:
                logic.insert(0, "target_window", window.target_month)
                logic.insert(0, "cycle_month", cycle_month)
                logic_parts.append(logic)

    summary = pd.DataFrame(summary_rows)
    all_logic = pd.concat(logic_parts, ignore_index=True) if logic_parts else pd.DataFrame()
    by_combo = _portfolio_by_combo(output_dir)
    focus_12_13 = _portfolio_for_combos(output_dir, {"1-2", "1-3"}, label="1-2_1-3")

    summary.to_csv(output_dir / "rolling_summary.csv", index=False, encoding="utf-8-sig")
    all_logic.to_csv(output_dir / "all_target_logic_results.csv", index=False, encoding="utf-8-sig")
    by_combo.to_csv(output_dir / "portfolio_by_combo.csv", index=False, encoding="utf-8-sig")
    focus_12_13.to_csv(output_dir / "portfolio_12_13_monthly.csv", index=False, encoding="utf-8-sig")
    _write_readme(
        output_dir,
        summary,
        by_combo,
        focus_12_13,
        train_months=train_months,
        warmup_days=warmup_days,
    )

    total_bets = int(summary["dedup_bets"].sum())
    total_profit = int(summary["dedup_profit_yen"].sum())
    total_roi = round((total_profit + total_bets * STAKE_YEN) * 100.0 / (total_bets * STAKE_YEN), 2) if total_bets else 0.0
    focus_bets = int(focus_12_13["bets"].sum()) if not focus_12_13.empty else 0
    focus_profit = int(focus_12_13["profit_yen"].sum()) if not focus_12_13.empty else 0
    focus_roi = round((focus_profit + focus_bets * STAKE_YEN) * 100.0 / (focus_bets * STAKE_YEN), 2) if focus_bets else 0.0
    return {
        "output_dir": str(output_dir),
        "cycle_months": ",".join(cycle_months),
        "train_months": train_months,
        "warmup_days": warmup_days,
        "total_bets": total_bets,
        "total_profit_yen": total_profit,
        "total_roi_pct": total_roi,
        "focus_12_13_bets": focus_bets,
        "focus_12_13_profit_yen": focus_profit,
        "focus_12_13_roi_pct": focus_roi,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="3-month + first-10-days train, day11-to-next-day10 forward distortion backtest.")
    parser.add_argument("--db-path", type=Path, default=default_results_db_path())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cycle-months", nargs="+", default=DEFAULT_CYCLE_MONTHS)
    parser.add_argument("--train-months", type=int, default=3)
    parser.add_argument("--warmup-days", type=int, default=10)
    parser.add_argument("--min-sample", type=int, default=300)
    parser.add_argument("--min-roi", type=float, default=108.0)
    parser.add_argument("--min-roi-lift", type=float, default=25.0)
    parser.add_argument("--min-positive-months", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--max-per-combo", type=int, default=4)
    args = parser.parse_args()
    result = run(
        db_path=args.db_path,
        output_dir=args.output_dir,
        cycle_months=args.cycle_months,
        train_months=args.train_months,
        warmup_days=args.warmup_days,
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
