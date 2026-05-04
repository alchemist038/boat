from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from runtime_paths import REPO_ROOT, default_results_db_path

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "reports" / "strategies" / "rolling_1x_live_candidates"
DEFAULT_PROFILE_PATH = (
    REPO_ROOT
    / "live_trigger"
    / "boxes"
    / "rolling_1x"
    / "profiles"
    / "rolling_1x_12_13_train3m_v1.json"
)


def _load_10day_module():
    script_path = REPO_ROOT / "workspace_codex" / "scripts" / "rolling_10day_train_forward_distortion.py"
    spec = importlib.util.spec_from_file_location("rolling_10day_live_candidate_builder", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _upsert_profile_window(
    profile_path: Path,
    *,
    label: str,
    valid_from: str,
    valid_to: str,
    selected_path: Path,
    train_start: str,
    train_end: str,
) -> None:
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    windows = list(payload.get("candidate_windows", []) or [])
    next_window = {
        "label": label,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "path": _relative_to_repo(selected_path),
        "train_start": train_start,
        "train_end": train_end,
    }
    windows = [window for window in windows if str(window.get("label")) != label]
    windows.append(next_window)
    windows.sort(key=lambda window: str(window.get("valid_from", "")))
    payload["candidate_windows"] = windows
    profile_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(
    *,
    cycle_month: str,
    db_path: Path,
    output_root: Path,
    update_profile: bool,
    profile_path: Path,
    train_months: int,
    min_sample: int,
    min_roi: float,
    min_roi_lift: float,
    min_positive_months: int,
    max_candidates: int,
    max_per_combo: int,
) -> dict[str, object]:
    ten_day = _load_10day_module()
    rolling = ten_day._load_rolling_module()
    scan_mod = rolling._load_scan_module()
    distortion_mod = rolling._load_distortion_module()
    window = ten_day._build_window(rolling, cycle_month, train_months=train_months)
    output_root.mkdir(parents=True, exist_ok=True)
    summary = rolling._run_window(
        scan_mod,
        distortion_mod,
        db_path,
        window,
        output_root,
        min_sample=min_sample,
        min_roi=min_roi,
        min_roi_lift=min_roi_lift,
        min_positive_months=min_positive_months,
        max_candidates=max_candidates,
        max_per_combo=max_per_combo,
    )
    selected_path = output_root / window.target_month / "selected_candidates.csv"
    if update_profile:
        _upsert_profile_window(
            profile_path,
            label=window.target_month,
            valid_from=window.target_start,
            valid_to=window.target_end,
            selected_path=selected_path,
            train_start=window.train_start,
            train_end=window.train_end,
        )
    selected_count = 0
    focus_count = 0
    if selected_path.exists():
        selected = pd.read_csv(selected_path)
        selected_count = int(len(selected))
        focus_count = int(selected["combo"].astype(str).isin(["1-2", "1-3"]).sum()) if not selected.empty else 0
    return {
        "cycle_month": cycle_month,
        "target_window": window.target_month,
        "train_start": window.train_start,
        "train_end": window.train_end,
        "target_start": window.target_start,
        "target_end": window.target_end,
        "selected_path": str(selected_path),
        "selected_count": selected_count,
        "focus_12_13_count": focus_count,
        "profile_updated": update_profile,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a live candidate pack for the rolling 1-2/1-3 product.")
    parser.add_argument("--cycle-month", required=True, help="Cycle month in YYYY-MM. Example: 2026-05 for 2026-05-11_to_2026-06-10.")
    parser.add_argument("--db-path", type=Path, default=default_results_db_path())
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--update-profile", action="store_true")
    parser.add_argument("--profile-path", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--train-months", type=int, default=3)
    parser.add_argument("--min-sample", type=int, default=300)
    parser.add_argument("--min-roi", type=float, default=108.0)
    parser.add_argument("--min-roi-lift", type=float, default=25.0)
    parser.add_argument("--min-positive-months", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--max-per-combo", type=int, default=4)
    args = parser.parse_args()
    result = run(
        cycle_month=args.cycle_month,
        db_path=args.db_path,
        output_root=args.output_root,
        update_profile=args.update_profile,
        profile_path=args.profile_path,
        train_months=args.train_months,
        min_sample=args.min_sample,
        min_roi=args.min_roi,
        min_roi_lift=args.min_roi_lift,
        min_positive_months=args.min_positive_months,
        max_candidates=args.max_candidates,
        max_per_combo=args.max_per_combo,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
