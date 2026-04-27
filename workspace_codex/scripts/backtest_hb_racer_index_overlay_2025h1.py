from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path, default_workspace_script_path

ROOT = REPO_ROOT
DB_PATH = default_results_db_path()
BASE100_SCRIPT_PATH = default_workspace_script_path("evaluate_base100_lane_multiplier_20260324.py")

PROFILE_MONTHS = 5
EVAL_START = date.fromisoformat("2025-01-01")
EVAL_END = date.fromisoformat("2025-06-30")
TARGET_COMBO = "4-2"
OUTPUT_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "zero_base_period_2025-01-01_to_2025-06-30_h_b_racer_index_overlay_5m_20260326"
)


@dataclass(frozen=True)
class ScopeSummary:
    scope: str
    qualifying_races: int
    bets: int
    hits: int
    investment_yen: int
    return_yen: int
    profit_yen: int
    roi_pct: float
    hit_rate_pct: float
    avg_hit_payout_yen: float
    max_dd_yen: int
    dd_peak_race_id: str
    dd_bottom_race_id: str
    longest_losing_streak: int
    losing_streak_start_race_id: str
    losing_streak_end_race_id: str
    lane4_win_rate_pct: float
    lane2_second_rate_pct: float
    wave_ge6_rate_pct: float


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


def load_all_raw(eval_mod, raw_start: date) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        raw = eval_mod.load_period(con, raw_start.isoformat(), EVAL_END.isoformat())
    finally:
        con.close()
    raw["race_date"] = pd.to_datetime(raw["race_date"])
    return raw


def build_walkforward_predictions(eval_mod) -> tuple[pd.DataFrame, pd.DataFrame]:
    windows = build_month_windows(EVAL_START, EVAL_END)
    raw_start = windows[0]["history_start"]
    raw = load_all_raw(eval_mod, raw_start)

    prediction_frames: list[pd.DataFrame] = []
    monthly_rows: list[dict[str, object]] = []

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

        monthly_rows.append(
            {
                "forward_month": window["forward_start"].isoformat(),
                "predicted_races": int(forward_pred_bundle.feature_matrix.shape[0] / 6),
                "forward_rank_mae": forward_metrics["rank_mae"],
                "forward_pairwise_accuracy": forward_metrics["pairwise_accuracy"],
                "forward_winner_hit_rate_pct": forward_metrics["winner_hit_rate"] * 100.0,
                "forward_top3_set_hit_rate_pct": forward_metrics["top3_set_hit_rate"] * 100.0,
            }
        )

    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(monthly_rows)


def normalize_combo(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value))


def load_settlements_and_conditions() -> pd.DataFrame:
    query = f"""
    WITH race_base AS (
      SELECT
        e.race_id,
        CAST(e.race_date AS DATE) AS race_date,
        MIN(e.stadium_code) AS stadium_code,
        MIN(e.race_no) AS race_no,
        MAX(COALESCE(bi.wave_height_cm, res.wave_height_cm)) AS wave_height_cm,
        MAX(CASE WHEN e.lane = 1 THEN bi.start_exhibition_st END) AS lane1_start_exhibition_st,
        MAX(CASE WHEN e.lane = 4 THEN bi.start_exhibition_st END) AS lane4_start_exhibition_st,
        MAX(res.first_place_lane) AS first_place_lane,
        MAX(res.second_place_lane) AS second_place_lane,
        MAX(res.exacta_combo) AS exacta_combo,
        MAX(res.exacta_payout) AS exacta_payout
      FROM entries e
      LEFT JOIN beforeinfo_entries bi ON bi.race_id = e.race_id AND bi.lane = e.lane
      LEFT JOIN results res ON res.race_id = e.race_id
      WHERE e.race_date BETWEEN DATE '{EVAL_START.isoformat()}' AND DATE '{EVAL_END.isoformat()}'
      GROUP BY e.race_id, CAST(e.race_date AS DATE)
    )
    SELECT *
    FROM race_base
    WHERE exacta_combo IS NOT NULL
      AND exacta_payout IS NOT NULL
    ORDER BY race_date, race_id
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = con.execute(query).fetchdf()
    finally:
        con.close()
    df["race_date"] = pd.to_datetime(df["race_date"])
    df["exacta_combo_norm"] = df["exacta_combo"].map(normalize_combo)
    return df


def build_race_level_frame(predictions: pd.DataFrame, settlements: pd.DataFrame) -> pd.DataFrame:
    base = predictions[["race_id", "race_date", "stadium_code", "race_no"]].drop_duplicates("race_id").copy()
    pred1 = (
        predictions.loc[predictions["pred_rank"] == 1, ["race_id", "lane", "racer_id", "racer_name", "pred_score"]]
        .rename(
            columns={
                "lane": "pred1_lane",
                "racer_id": "pred1_racer_id",
                "racer_name": "pred1_racer_name",
                "pred_score": "pred1_score",
            }
        )
        .copy()
    )

    race_level = base.merge(pred1, on="race_id", how="left")
    race_level = race_level.merge(settlements, on=["race_id", "race_date", "stadium_code", "race_no"], how="inner")

    race_level["wave_6p_flag"] = race_level["wave_height_cm"].fillna(0).astype(float) >= 6.0
    race_level["lane4_ahead_lane1_005_flag"] = (
        race_level["lane1_start_exhibition_st"].astype(float) - race_level["lane4_start_exhibition_st"].astype(float)
    ) >= 0.05
    race_level["baseline_flag"] = race_level["wave_6p_flag"] & race_level["lane4_ahead_lane1_005_flag"]
    race_level["overlay_flag"] = race_level["baseline_flag"] & (race_level["pred1_lane"] == 4)
    race_level["is_target_hit"] = race_level["exacta_combo_norm"] == TARGET_COMBO
    race_level["lane4_win"] = race_level["first_place_lane"] == 4
    race_level["lane2_second"] = race_level["second_place_lane"] == 2

    return race_level.sort_values(["race_date", "race_id"]).reset_index(drop=True)


def make_scope_frame(name: str, race_level: pd.DataFrame) -> pd.DataFrame:
    if name == "baseline_h_b_4-2":
        played = race_level.loc[race_level["baseline_flag"]].copy()
    elif name == "overlay_pred1_lane4_h_b_4-2":
        played = race_level.loc[race_level["overlay_flag"]].copy()
    else:
        raise ValueError(f"unknown scope: {name}")

    played["scope"] = name
    played["bet_amount"] = 100
    played["payout"] = played["exacta_payout"].where(played["is_target_hit"], 0).astype(int)
    played["profit"] = played["payout"] - played["bet_amount"]
    return played


def compute_drawdown_details(played: pd.DataFrame) -> tuple[int, str, str]:
    cumulative = 0
    peak_value = 0
    peak_race_id = "start-phase"
    best_drawdown = 0
    bottom_race_id = "start-phase"

    for row in played.itertuples(index=False):
        cumulative += int(row.profit)
        if cumulative > peak_value:
            peak_value = cumulative
            peak_race_id = str(row.race_id)
        drawdown = peak_value - cumulative
        if drawdown > best_drawdown:
            best_drawdown = drawdown
            bottom_race_id = str(row.race_id)

    return best_drawdown, peak_race_id, bottom_race_id


def compute_losing_streak_details(played: pd.DataFrame) -> tuple[int, str, str]:
    current = 0
    current_start = ""
    best = 0
    best_start = ""
    best_end = ""

    for row in played.itertuples(index=False):
        if int(row.profit) > 0:
            current = 0
            current_start = ""
            continue
        if current == 0:
            current_start = str(row.race_id)
        current += 1
        if current > best:
            best = current
            best_start = current_start
            best_end = str(row.race_id)

    return best, best_start, best_end


def summarize_scope(name: str, played: pd.DataFrame) -> ScopeSummary:
    bets = int(len(played))
    hits = int(played["is_target_hit"].sum())
    investment = int(played["bet_amount"].sum())
    returned = int(played["payout"].sum())
    profit = returned - investment
    roi = round(returned / investment * 100.0, 2) if investment else 0.0
    hit_rate = round(hits / bets * 100.0, 2) if bets else 0.0
    avg_hit_payout = round(returned / hits, 2) if hits else 0.0
    max_dd, dd_peak_race_id, dd_bottom_race_id = compute_drawdown_details(played)
    streak, streak_start, streak_end = compute_losing_streak_details(played)

    return ScopeSummary(
        scope=name,
        qualifying_races=bets,
        bets=bets,
        hits=hits,
        investment_yen=investment,
        return_yen=returned,
        profit_yen=profit,
        roi_pct=roi,
        hit_rate_pct=hit_rate,
        avg_hit_payout_yen=avg_hit_payout,
        max_dd_yen=max_dd,
        dd_peak_race_id=dd_peak_race_id,
        dd_bottom_race_id=dd_bottom_race_id,
        longest_losing_streak=streak,
        losing_streak_start_race_id=streak_start,
        losing_streak_end_race_id=streak_end,
        lane4_win_rate_pct=round(played["lane4_win"].mean() * 100.0, 2) if bets else 0.0,
        lane2_second_rate_pct=round(played["lane2_second"].mean() * 100.0, 2) if bets else 0.0,
        wave_ge6_rate_pct=round(played["wave_6p_flag"].mean() * 100.0, 2) if bets else 0.0,
    )


def build_monthly_scope_summary(played: pd.DataFrame) -> pd.DataFrame:
    if played.empty:
        return pd.DataFrame()
    frame = played.copy()
    frame["month"] = frame["race_date"].dt.strftime("%Y-%m")
    grouped = (
        frame.groupby(["scope", "month"], observed=True)
        .agg(
            bets=("race_id", "size"),
            hits=("is_target_hit", "sum"),
            investment_yen=("bet_amount", "sum"),
            return_yen=("payout", "sum"),
            lane4_win_rate_pct=("lane4_win", lambda s: float(s.mean() * 100.0)),
            lane2_second_rate_pct=("lane2_second", lambda s: float(s.mean() * 100.0)),
        )
        .reset_index()
    )
    grouped["profit_yen"] = grouped["return_yen"] - grouped["investment_yen"]
    grouped["roi_pct"] = grouped.apply(
        lambda row: round(float(row["return_yen"]) / float(row["investment_yen"]) * 100.0, 2)
        if row["investment_yen"]
        else 0.0,
        axis=1,
    )
    grouped["hit_rate_pct"] = grouped.apply(
        lambda row: round(float(row["hits"]) / float(row["bets"]) * 100.0, 2) if row["bets"] else 0.0,
        axis=1,
    )
    return grouped


def write_readme(
    path: Path,
    prediction_quality: pd.DataFrame,
    summary_rows: list[ScopeSummary],
    race_level: pd.DataFrame,
) -> None:
    baseline_count = int(race_level["baseline_flag"].sum())
    overlay_count = int(race_level["overlay_flag"].sum())
    total_count = int(len(race_level))
    overlay_share = round(overlay_count / baseline_count * 100.0, 2) if baseline_count else 0.0

    lines = [
        "# H-B Racer-Index Overlay Backtest 2025H1",
        "",
        "## Purpose",
        "",
        "- test `H-B = exacta 4-2` on `2025-01-01..2025-06-30`",
        "- baseline condition:",
        "  - `wave_6p`",
        "  - `lane4_ahead_lane1_005`",
        "- apply racer-index point-in-time overlay:",
        "  - lane 4 is `pred1`",
        "- settle with official `results.exacta_combo` / `results.exacta_payout`",
        "",
        "## Assumptions",
        "",
        "- racer-index profile window: `5M`",
        "- walk-forward shape: prior `5 months` history + prior `1 month` tuning + current month forward",
        "- this is an `official settle proxy`, not an original quoted-odds recreation",
        "",
        "## Coverage",
        "",
        f"- settled races with predictions: `{total_count}`",
        f"- baseline H-B races: `{baseline_count}`",
        f"- overlay races (`pred1 = lane4` inside H-B): `{overlay_count}`",
        f"- overlay share inside H-B: `{overlay_share}%`",
        "",
        "## Prediction Monthly Quality",
        "",
        "| month | races | winner hit | top3 set hit | rank MAE | pairwise acc |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in prediction_quality.itertuples(index=False):
        lines.append(
            f"| {row.forward_month[:7]} | {int(row.predicted_races)} | "
            f"{float(row.forward_winner_hit_rate_pct):.2f}% | "
            f"{float(row.forward_top3_set_hit_rate_pct):.2f}% | "
            f"{float(row.forward_rank_mae):.3f} | "
            f"{float(row.forward_pairwise_accuracy):.3f} |"
        )
    lines.extend(["", "## Scope Summary", ""])
    for row in summary_rows:
        lines.extend(
            [
                f"### {row.scope}",
                "",
                f"- bets: `{row.bets}`",
                f"- hits: `{row.hits}`",
                f"- investment: `{row.investment_yen:,} yen`",
                f"- return: `{row.return_yen:,} yen`",
                f"- profit: `{row.profit_yen:,} yen`",
                f"- ROI: `{row.roi_pct:.2f}%`",
                f"- hit rate: `{row.hit_rate_pct:.2f}%`",
                f"- average hit payout: `{row.avg_hit_payout_yen:,.2f} yen`",
                f"- max drawdown: `-{row.max_dd_yen:,} yen`",
                f"- drawdown peak race: `{row.dd_peak_race_id}`",
                f"- drawdown bottom race: `{row.dd_bottom_race_id}`",
                f"- longest losing streak: `{row.longest_losing_streak}`",
                f"- losing streak start: `{row.losing_streak_start_race_id}`",
                f"- losing streak end: `{row.losing_streak_end_race_id}`",
                f"- lane4 actual win rate inside scope: `{row.lane4_win_rate_pct:.2f}%`",
                f"- lane2 actual second rate inside scope: `{row.lane2_second_rate_pct:.2f}%`",
                f"- wave>=6 rate inside scope: `{row.wave_ge6_rate_pct:.2f}%`",
                "",
            ]
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dir(OUTPUT_DIR)
    eval_mod = load_base100_module()
    predictions, prediction_quality = build_walkforward_predictions(eval_mod)
    settlements = load_settlements_and_conditions()
    race_level = build_race_level_frame(predictions, settlements)

    baseline = make_scope_frame("baseline_h_b_4-2", race_level)
    overlay = make_scope_frame("overlay_pred1_lane4_h_b_4-2", race_level)

    summary_rows = [
        summarize_scope("baseline_h_b_4-2", baseline),
        summarize_scope("overlay_pred1_lane4_h_b_4-2", overlay),
    ]
    summary_df = pd.DataFrame([row.__dict__ for row in summary_rows])
    monthly_scope_df = pd.concat(
        [
            build_monthly_scope_summary(baseline),
            build_monthly_scope_summary(overlay),
        ],
        ignore_index=True,
    )

    race_level.to_csv(OUTPUT_DIR / "race_level_results.csv", index=False, encoding="utf-8-sig")
    overlay.to_csv(OUTPUT_DIR / "overlay_race_results.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(OUTPUT_DIR / "summary.csv", index=False, encoding="utf-8-sig")
    monthly_scope_df.to_csv(OUTPUT_DIR / "monthly_summary.csv", index=False, encoding="utf-8-sig")
    prediction_quality.to_csv(OUTPUT_DIR / "prediction_monthly_quality.csv", index=False, encoding="utf-8-sig")
    write_readme(OUTPUT_DIR / "README.md", prediction_quality, summary_rows, race_level)


if __name__ == "__main__":
    main()
