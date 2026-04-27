from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import permutations
from pathlib import Path

import duckdb
import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path, default_workspace_script_path

ROOT = REPO_ROOT
DB_PATH = default_results_db_path()
BASE100_SCRIPT_PATH = default_workspace_script_path("evaluate_base100_lane_multiplier_20260324.py")
PROFILE_MONTHS = int(os.environ.get("RI_PROFILE_MONTHS", "5"))
OUTPUT_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "c2"
    / f"c2_pred1_non_lane1_overlay_walkforward_2025-04-01_to_2026-03-09_{PROFILE_MONTHS}m_20260325"
)

EVAL_START = date.fromisoformat("2025-04-01")
EVAL_END = date.fromisoformat("2026-03-09")
RAW_START = date.fromisoformat("2024-10-01")

CLASS_COLS = {
    1: "lane1_class",
    2: "lane2_class",
    3: "lane3_class",
    4: "lane4_class",
    5: "lane5_class",
    6: "lane6_class",
}

QUERY_C2 = """
WITH female_races AS (
  SELECT
    e.race_id,
    count(*) AS entry_count,
    sum(case when br.sex = '2' then 1 else 0 end) AS female_count
  FROM entries e
  LEFT JOIN bronze_racer_stats_term br
    ON cast(e.racer_id AS varchar) = br.racer_id
  WHERE e.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
  GROUP BY e.race_id
), base AS (
  SELECT
    cast(rm.race_date AS date) AS race_date,
    cast(rm.race_id as varchar) AS race_id,
    coalesce(rm.is_final_day, false) AS is_final_day,
    e1.racer_class AS lane1_class,
    e2.racer_class AS lane2_class,
    e3.racer_class AS lane3_class,
    e4.racer_class AS lane4_class,
    e5.racer_class AS lane5_class,
    e6.racer_class AS lane6_class,
    r.first_place_lane,
    r.second_place_lane,
    r.third_place_lane,
    cast(r.trifecta_payout AS bigint) AS trifecta_payout
  FROM race_meta rm
  JOIN female_races fr USING(race_id)
  JOIN entries e1 ON rm.race_id = e1.race_id AND e1.lane = 1
  JOIN entries e2 ON rm.race_id = e2.race_id AND e2.lane = 2
  JOIN entries e3 ON rm.race_id = e3.race_id AND e3.lane = 3
  JOIN entries e4 ON rm.race_id = e4.race_id AND e4.lane = 4
  JOIN entries e5 ON rm.race_id = e5.race_id AND e5.lane = 5
  JOIN entries e6 ON rm.race_id = e6.race_id AND e6.lane = 6
  JOIN beforeinfo_entries b1 ON rm.race_id = b1.race_id AND b1.lane = 1
  JOIN beforeinfo_entries b2 ON rm.race_id = b2.race_id AND b2.lane = 2
  JOIN beforeinfo_entries b3 ON rm.race_id = b3.race_id AND b3.lane = 3
  JOIN beforeinfo_entries b4 ON rm.race_id = b4.race_id AND b4.lane = 4
  JOIN beforeinfo_entries b5 ON rm.race_id = b5.race_id AND b5.lane = 5
  JOIN beforeinfo_entries b6 ON rm.race_id = b6.race_id AND b6.lane = 6
  JOIN results r USING(race_id)
  WHERE rm.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
    AND fr.entry_count = 6 AND fr.female_count = 6
    AND b1.start_exhibition_st - least(
      b2.start_exhibition_st,
      b3.start_exhibition_st,
      b4.start_exhibition_st,
      b5.start_exhibition_st,
      b6.start_exhibition_st
    ) >= 0.12
    AND b1.exhibition_time <= b2.exhibition_time + 0.02
    AND b1.exhibition_time <= b3.exhibition_time + 0.02
)
SELECT *
FROM base
ORDER BY race_date, race_id
"""


@dataclass(frozen=True)
class OverlayRace:
    race_id: str
    race_date: date
    is_final_day: bool
    pred1_lane: int | None
    baseline_bet: int
    baseline_payout: int
    overlay_bet: int
    overlay_payout: int

    @property
    def changed(self) -> bool:
        return (self.baseline_bet != self.overlay_bet) or (self.baseline_payout != self.overlay_payout)

    @property
    def skipped_by_overlay(self) -> bool:
        return self.baseline_bet > 0 and self.overlay_bet == 0


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_base100_module():
    spec = importlib.util.spec_from_file_location("base100_eval_20260324", BASE100_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {BASE100_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def add_months(base: date, delta_months: int) -> date:
    month_index = (base.year * 12 + (base.month - 1)) + delta_months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def month_end(base: date) -> date:
    return add_months(base, 1) - timedelta(days=1)


def date_mask(frame: pd.DataFrame, start_date: date, end_date: date) -> pd.Series:
    return (frame["race_date"] >= pd.Timestamp(start_date)) & (frame["race_date"] <= pd.Timestamp(end_date))


def build_month_windows(start_date: date, end_date: date) -> list[dict[str, date]]:
    windows: list[dict[str, date]] = []
    target_start = date(start_date.year, start_date.month, 1)
    final_start = date(end_date.year, end_date.month, 1)
    while target_start <= final_start:
        target_end = min(month_end(target_start), end_date)
        tune_start = add_months(target_start, -1)
        tune_end = month_end(tune_start)
        history_start = add_months(target_start, -(PROFILE_MONTHS + 1))
        history_end = month_end(add_months(target_start, -2))
        windows.append(
            {
                "history_start": history_start,
                "history_end": history_end,
                "tune_start": tune_start,
                "tune_end": tune_end,
                "forward_start": target_start,
                "forward_end": target_end,
            }
        )
        target_start = add_months(target_start, 1)
    return windows


def load_all_raw(eval_mod) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        raw = eval_mod.load_period(con, RAW_START.isoformat(), EVAL_END.isoformat())
    finally:
        con.close()
    raw["race_date"] = pd.to_datetime(raw["race_date"])
    return raw


def prepare_prediction_bundle(eval_mod, name: str, df: pd.DataFrame, medians: pd.Series, means: pd.Series, stds: pd.Series):
    frame = df.sort_values(["race_date", "race_id", "lane"]).reset_index(drop=True).copy()
    race_sizes = frame.groupby("race_id", observed=True)["lane"].transform("size")
    frame = frame[race_sizes == 6].reset_index(drop=True)

    feature_frame = frame[eval_mod.ADDITIVE_FEATURES].astype("float64").copy()
    feature_frame = feature_frame.fillna(medians)
    feature_frame = (feature_frame - means) / stds

    feature_matrix = feature_frame.to_numpy(dtype="float64")
    lanes = frame["lane"].astype("int16").to_numpy().reshape(-1, 6)
    finish_pos = frame["finish_pos"].fillna(0).astype("int16").to_numpy().reshape(-1, 6)
    race_ids = frame["race_id"].to_numpy().reshape(-1, 6)[:, 0]

    return eval_mod.DatasetBundle(
        name=name,
        frame=frame,
        feature_matrix=feature_matrix,
        lanes=lanes,
        finish_pos=finish_pos,
        race_ids=race_ids,
    )


def build_pred1_predictions(eval_mod, raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    windows = build_month_windows(EVAL_START, EVAL_END)
    monthly_rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []

    for window in windows:
        history_raw = raw.loc[date_mask(raw, window["history_start"], window["history_end"])].copy()
        tuning_raw = raw.loc[date_mask(raw, window["tune_start"], window["tune_end"])].copy()
        forward_raw = raw.loc[date_mask(raw, window["forward_start"], window["forward_end"])].copy()
        if history_raw.empty or tuning_raw.empty or forward_raw.empty:
            raise RuntimeError(f"missing data for window {window}")

        profiles = eval_mod.build_racer_profiles(history_raw)
        history_enriched = eval_mod.enrich_with_profiles(history_raw, profiles)
        tuning_enriched = eval_mod.enrich_with_profiles(tuning_raw, profiles)
        forward_enriched = eval_mod.enrich_with_profiles(forward_raw, profiles)

        medians, means, stds = eval_mod.build_standardization(history_enriched)
        tuning_bundle = eval_mod.prepare_bundle("tune", tuning_enriched, medians, means, stds)
        forward_eval_bundle = eval_mod.prepare_bundle("forward_eval", forward_enriched, medians, means, stds)
        forward_pred_bundle = prepare_prediction_bundle(eval_mod, "forward_pred", forward_enriched, medians, means, stds)

        lane_base_coefficients = eval_mod.build_lane_base_coefficients(profiles)
        weights, lane_alpha, tuning_metrics = eval_mod.optimize_params(
            tuning_bundle,
            lane_base_coefficients,
            allow_lane_alpha=True,
        )
        forward_metrics = eval_mod.evaluate_params(
            forward_eval_bundle,
            weights,
            lane_base_coefficients,
            lane_alpha,
        )
        forward_predictions = eval_mod.build_predictions(
            forward_pred_bundle,
            weights,
            lane_base_coefficients,
            lane_alpha,
        ).copy()
        forward_predictions["window_forward_month"] = window["forward_start"].isoformat()
        prediction_frames.append(forward_predictions)

        pred1_rows = forward_predictions.loc[
            (forward_predictions["pred_rank"] == 1) & forward_predictions["finish_pos"].notna()
        ].copy()
        monthly_rows.append(
            {
                "forward_month": window["forward_start"].isoformat(),
                "history_start": window["history_start"].isoformat(),
                "history_end": window["history_end"].isoformat(),
                "tune_start": window["tune_start"].isoformat(),
                "tune_end": window["tune_end"].isoformat(),
                "forward_start": window["forward_start"].isoformat(),
                "forward_end": window["forward_end"].isoformat(),
                "predicted_races": int(forward_pred_bundle.feature_matrix.shape[0] / 6),
                "evaluable_races": int(forward_metrics["races"]),
                "tuning_rank_mae": tuning_metrics["rank_mae"],
                "tuning_pairwise_accuracy": tuning_metrics["pairwise_accuracy"],
                "forward_rank_mae": forward_metrics["rank_mae"],
                "forward_pairwise_accuracy": forward_metrics["pairwise_accuracy"],
                "pred1_win_rate_pct": float((pred1_rows["finish_pos"] == 1).mean() * 100.0),
                "pred1_top3_rate_pct": float((pred1_rows["finish_pos"] <= 3).mean() * 100.0),
                "lane_alpha": lane_alpha,
            }
        )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    monthly_summary = pd.DataFrame(monthly_rows)
    return predictions, monthly_summary


def pred1_map_from_predictions(predictions: pd.DataFrame) -> dict[str, int]:
    pred1_rows = predictions.loc[predictions["pred_rank"] == 1, ["race_id", "lane"]].copy()
    if pred1_rows["race_id"].duplicated().any():
        dupes = pred1_rows.loc[pred1_rows["race_id"].duplicated(), "race_id"].tolist()
        raise RuntimeError(f"duplicate pred1 race ids: {dupes[:5]}")
    return {str(row.race_id): int(row.lane) for row in pred1_rows.itertuples(index=False)}


def ticket_count_excluding_b2(row: pd.Series) -> int:
    total = 0
    for first in (2, 3):
        allowed = [
            lane
            for lane in range(1, 7)
            if lane != first and row[CLASS_COLS[lane]] != "B2"
        ]
        total += len(list(permutations(allowed, 2)))
    return total


def hit_with_b2_excluded(row: pd.Series) -> bool:
    if pd.isna(row["first_place_lane"]) or pd.isna(row["second_place_lane"]) or pd.isna(row["third_place_lane"]):
        return False
    first_lane = int(row["first_place_lane"])
    second_lane = int(row["second_place_lane"])
    third_lane = int(row["third_place_lane"])
    if first_lane not in (2, 3):
        return False
    return row[CLASS_COLS[second_lane]] != "B2" and row[CLASS_COLS[third_lane]] != "B2"


def load_c2_overlay_rows(pred1_by_race: dict[str, int]) -> list[OverlayRace]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = con.execute(
            QUERY_C2.format(
                start_date=EVAL_START.isoformat(),
                end_date=EVAL_END.isoformat(),
            )
        ).fetchdf()
    finally:
        con.close()

    df["bet_points"] = df.apply(ticket_count_excluding_b2, axis=1)
    df["baseline_bet"] = df["bet_points"] * 100
    df["baseline_hit"] = df.apply(hit_with_b2_excluded, axis=1)
    df["baseline_payout"] = df.apply(
        lambda row: int(row["trifecta_payout"]) if row["baseline_hit"] and pd.notna(row["trifecta_payout"]) else 0,
        axis=1,
    )

    rows: list[OverlayRace] = []
    for _, row in df.iterrows():
        if bool(row["is_final_day"]):
            continue
        race_id = str(row["race_id"])
        pred1_lane = pred1_by_race.get(race_id)
        if pred1_lane is None:
            continue
        overlay_keep = pred1_lane != 1
        rows.append(
            OverlayRace(
                race_id=race_id,
                race_date=row["race_date"].date(),
                is_final_day=bool(row["is_final_day"]),
                pred1_lane=pred1_lane,
                baseline_bet=int(row["baseline_bet"]),
                baseline_payout=int(row["baseline_payout"]),
                overlay_bet=int(row["baseline_bet"]) if overlay_keep else 0,
                overlay_payout=int(row["baseline_payout"]) if overlay_keep else 0,
            )
        )
    return sorted(rows, key=lambda item: (item.race_date, item.race_id))


def max_drawdown(profits: list[int]) -> int:
    cumulative = 0
    peak = 0
    best = 0
    for profit in profits:
        cumulative += profit
        peak = max(peak, cumulative)
        best = max(best, peak - cumulative)
    return best


def max_losing_streak(profits: list[int]) -> int:
    current = 0
    best = 0
    for profit in profits:
        if profit > 0:
            current = 0
        else:
            current += 1
            best = max(best, current)
    return best


def summarize_overlay_rows(rows: list[OverlayRace]) -> dict[str, object]:
    baseline_profits = [row.baseline_payout - row.baseline_bet for row in rows]
    overlay_profits = [row.overlay_payout - row.overlay_bet for row in rows]

    baseline_bet_total = sum(row.baseline_bet for row in rows)
    baseline_payout_total = sum(row.baseline_payout for row in rows)
    overlay_bet_total = sum(row.overlay_bet for row in rows)
    overlay_payout_total = sum(row.overlay_payout for row in rows)

    baseline_hits = sum(1 for row in rows if row.baseline_payout > 0)
    overlay_hits = sum(1 for row in rows if row.overlay_payout > 0)

    return {
        "evaluated_races": len(rows),
        "removed_races": sum(1 for row in rows if row.skipped_by_overlay),
        "removed_hit_races": sum(1 for row in rows if row.baseline_payout > 0 and row.overlay_payout == 0),
        "baseline_bet_total_yen": baseline_bet_total,
        "baseline_payout_total_yen": baseline_payout_total,
        "baseline_profit_yen": baseline_payout_total - baseline_bet_total,
        "baseline_roi_pct": round(baseline_payout_total / baseline_bet_total * 100.0, 2) if baseline_bet_total else 0.0,
        "baseline_max_dd_yen": max_drawdown(baseline_profits),
        "baseline_max_losing_streak": max_losing_streak(baseline_profits),
        "baseline_hits": baseline_hits,
        "overlay_bet_total_yen": overlay_bet_total,
        "overlay_payout_total_yen": overlay_payout_total,
        "overlay_profit_yen": overlay_payout_total - overlay_bet_total,
        "overlay_roi_pct": round(overlay_payout_total / overlay_bet_total * 100.0, 2) if overlay_bet_total else 0.0,
        "overlay_max_dd_yen": max_drawdown(overlay_profits),
        "overlay_max_losing_streak": max_losing_streak(overlay_profits),
        "overlay_hits": overlay_hits,
        "delta_profit_yen": (overlay_payout_total - overlay_bet_total) - (baseline_payout_total - baseline_bet_total),
    }


def write_overlay_race_results(path: Path, rows: list[OverlayRace]) -> None:
    cumulative_baseline = 0
    peak_baseline = 0
    cumulative_overlay = 0
    peak_overlay = 0
    output_rows: list[dict[str, object]] = []
    for row in rows:
        baseline_profit = row.baseline_payout - row.baseline_bet
        overlay_profit = row.overlay_payout - row.overlay_bet
        cumulative_baseline += baseline_profit
        cumulative_overlay += overlay_profit
        peak_baseline = max(peak_baseline, cumulative_baseline)
        peak_overlay = max(peak_overlay, cumulative_overlay)
        output_rows.append(
            {
                "race_id": row.race_id,
                "race_date": row.race_date.isoformat(),
                "pred1_lane": row.pred1_lane,
                "baseline_bet": row.baseline_bet,
                "baseline_payout": row.baseline_payout,
                "baseline_profit": baseline_profit,
                "baseline_cumulative_profit": cumulative_baseline,
                "baseline_drawdown": peak_baseline - cumulative_baseline,
                "overlay_bet": row.overlay_bet,
                "overlay_payout": row.overlay_payout,
                "overlay_profit": overlay_profit,
                "overlay_cumulative_profit": cumulative_overlay,
                "overlay_drawdown": peak_overlay - cumulative_overlay,
                "changed": int(row.changed),
                "skipped_by_overlay": int(row.skipped_by_overlay),
            }
        )
    pd.DataFrame(output_rows).to_csv(path, index=False, encoding="utf-8-sig")


def write_summary(path: Path, pred1_monthly_summary: pd.DataFrame, pred1_predictions: pd.DataFrame, strategy_summary: dict[str, object]) -> None:
    pred1_rows = pred1_predictions.loc[pred1_predictions["pred_rank"] == 1].copy()
    pred1_eval_rows = pred1_rows.loc[pred1_rows["finish_pos"].notna()].copy()
    lines = [
        "# C2 `pred1 != lane1` Overlay Walk-Forward",
        "",
        "## Scope",
        "",
        f"- evaluation period: `{EVAL_START.isoformat()}` .. `{EVAL_END.isoformat()}`",
        f"- racer-index window: `{PROFILE_MONTHS}M`",
        "- prediction generation: monthly walk-forward",
        "- history window: prior months ending 2 months before target month",
        "- tuning window: previous month",
        "- target strategy: `C2` current-ish proxy (`women6`, `B2 cut`, `final day cut`)",
        "- overlay rule: if `pred1_lane = 1`, skip the race",
        "",
        "## Pred1 Quality",
        "",
        f"- predicted races: `{pred1_rows['race_id'].nunique()}`",
        f"- evaluable races: `{len(pred1_eval_rows)}`",
        f"- pred1 actual win rate: `{(pred1_eval_rows['finish_pos'] == 1).mean() * 100.0:.2f}%`",
        f"- pred1 top3 rate: `{(pred1_eval_rows['finish_pos'] <= 3).mean() * 100.0:.2f}%`",
        "",
        "## Strategy Overlay",
        "",
        "| baseline ROI | overlay ROI | delta profit | baseline DD | overlay DD | removed races | removed hit races |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {strategy_summary['baseline_roi_pct']:.2f}% | {strategy_summary['overlay_roi_pct']:.2f}% | {strategy_summary['delta_profit_yen']} | {strategy_summary['baseline_max_dd_yen']} | {strategy_summary['overlay_max_dd_yen']} | {strategy_summary['removed_races']} | {strategy_summary['removed_hit_races']} |",
        "",
        "## Pred1 Monthly",
        "",
        "| month | predicted_races | evaluable_races | pred1_win_rate | pred1_top3_rate | forward_rank_mae | forward_pairwise_acc |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in pred1_monthly_summary.itertuples(index=False):
        lines.append(
            f"| {row.forward_month} | {row.predicted_races} | {row.evaluable_races} | {row.pred1_win_rate_pct:.2f}% | {row.pred1_top3_rate_pct:.2f}% | {row.forward_rank_mae:.4f} | {row.forward_pairwise_accuracy:.4f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dir(OUTPUT_DIR)

    eval_mod = load_base100_module()
    raw = load_all_raw(eval_mod)
    pred1_predictions, pred1_monthly_summary = build_pred1_predictions(eval_mod, raw)
    pred1_by_race = pred1_map_from_predictions(pred1_predictions)

    rows = load_c2_overlay_rows(pred1_by_race)
    strategy_summary = summarize_overlay_rows(rows)

    pred1_predictions.to_csv(OUTPUT_DIR / "pred1_walkforward_predictions.csv", index=False, encoding="utf-8-sig")
    pred1_monthly_summary.to_csv(OUTPUT_DIR / "pred1_walkforward_monthly_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([strategy_summary]).to_csv(OUTPUT_DIR / "overlay_summary.csv", index=False, encoding="utf-8-sig")
    write_overlay_race_results(OUTPUT_DIR / "C2_pred1_non_lane1_overlay_race_results.csv", rows)
    write_summary(
        OUTPUT_DIR / "summary.md",
        pred1_monthly_summary=pred1_monthly_summary,
        pred1_predictions=pred1_predictions,
        strategy_summary=strategy_summary,
    )
    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(
            {
                "evaluation_start": EVAL_START.isoformat(),
                "evaluation_end": EVAL_END.isoformat(),
                "raw_start": RAW_START.isoformat(),
                "profile_months": PROFILE_MONTHS,
                "db_path": str(DB_PATH),
                "base100_script": str(BASE100_SCRIPT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(strategy_summary)
    print(f"wrote outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
