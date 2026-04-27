from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from runtime_paths import REPO_ROOT, default_results_db_path


DB_PATH = default_results_db_path()
OUTPUT_DIR = REPO_ROOT / "reports" / "strategies" / "racer_finish_score_feb_candidate_march_forward_20260324"

HISTORY_START = "2025-02-01"
HISTORY_END = "2026-01-31"
TUNE_START = "2026-02-01"
TUNE_END = "2026-02-28"
FORWARD_START = "2026-03-01"
FORWARD_END = "2026-03-23"

RANDOM_SEED = 20260324
RANDOM_TRIALS = 240
OVERALL_SHRINKAGE = 36.0
LANE_SHRINKAGE = 18.0
STYLE_SHRINKAGE = 18.0
TIE_BREAK_EPSILON = 1e-9

CLASS_POINTS = {
    "A1": 3.0,
    "A2": 2.0,
    "B1": 1.0,
    "B2": 0.0,
}

FEATURE_COLUMNS = [
    "class_point",
    "national_win_rate",
    "local_win_rate",
    "avg_start_timing_neg",
    "f_count_neg",
    "l_count_neg",
    "motor_place_rate",
    "boat_place_rate",
    "exhibition_rank_score",
    "exhibition_st_rank_score",
    "national_win_rank_score",
    "motor_rank_score",
    "hist_win_rate",
    "hist_top3_rate",
    "hist_avg_finish_score",
    "lane_win_rate",
    "lane_top3_rate",
    "lane_avg_finish_score",
    "style_fit_rate",
]


@dataclass
class DatasetBundle:
    name: str
    frame: pd.DataFrame
    feature_matrix: np.ndarray
    lanes: np.ndarray
    finish_pos: np.ndarray
    race_ids: np.ndarray


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_entry_query(start_date: str, end_date: str) -> str:
    return f"""
WITH base AS (
  SELECT
    e.race_id,
    e.race_date,
    e.stadium_code,
    e.race_no,
    e.lane,
    e.racer_id,
    e.racer_name,
    e.racer_class,
    e.f_count,
    e.l_count,
    e.avg_start_timing,
    e.national_win_rate,
    e.local_win_rate,
    e.motor_place_rate,
    e.boat_place_rate,
    bi.exhibition_time,
    bi.start_exhibition_st,
    CASE
      WHEN e.lane = res.first_place_lane THEN 1
      WHEN e.lane = res.second_place_lane THEN 2
      WHEN e.lane = res.third_place_lane THEN 3
      WHEN e.lane = res.fourth_place_lane THEN 4
      WHEN e.lane = res.fifth_place_lane THEN 5
      WHEN e.lane = res.sixth_place_lane THEN 6
      ELSE NULL
    END AS finish_pos,
    CASE WHEN res.first_place_lane = e.lane THEN 1 ELSE 0 END AS is_win,
    CASE
      WHEN e.lane IN (res.first_place_lane, res.second_place_lane, res.third_place_lane) THEN 1
      ELSE 0
    END AS is_top3,
    CASE
      WHEN res.first_place_lane = e.lane THEN COALESCE(res.winning_technique, '')
      ELSE ''
    END AS winner_technique
  FROM entries e
  JOIN results res USING (race_id)
  LEFT JOIN beforeinfo_entries bi
    ON bi.race_id = e.race_id
   AND bi.lane = e.lane
  WHERE e.race_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
),
ranked AS (
  SELECT
    *,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN exhibition_time IS NULL THEN 1 ELSE 0 END,
        exhibition_time ASC,
        lane ASC
    ) AS exhibition_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN start_exhibition_st IS NULL THEN 1 ELSE 0 END,
        start_exhibition_st ASC,
        lane ASC
    ) AS exhibition_st_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN national_win_rate IS NULL THEN 1 ELSE 0 END,
        national_win_rate DESC,
        lane ASC
    ) AS national_win_rank,
    DENSE_RANK() OVER (
      PARTITION BY race_id
      ORDER BY
        CASE WHEN motor_place_rate IS NULL THEN 1 ELSE 0 END,
        motor_place_rate DESC,
        lane ASC
    ) AS motor_rank
  FROM base
)
SELECT *
FROM ranked
QUALIFY COUNT(*) OVER (PARTITION BY race_id) = 6
ORDER BY race_date, race_id, lane
"""


def load_period(con: duckdb.DuckDBPyConnection, start_date: str, end_date: str) -> pd.DataFrame:
    return con.execute(build_entry_query(start_date, end_date)).fetchdf()


def smooth_series(raw: pd.Series, counts: pd.Series, prior: pd.Series | float, strength: float) -> pd.Series:
    raw_filled = raw.fillna(prior)
    return (raw_filled * counts + prior * strength) / (counts + strength)


def build_racer_profiles(train_df: pd.DataFrame) -> dict[str, object]:
    lane_globals = (
        train_df.groupby("lane", observed=True)
        .agg(
            lane_global_win_rate=("is_win", lambda s: float(s.mean() * 100.0)),
            lane_global_top3_rate=("is_top3", lambda s: float(s.mean() * 100.0)),
            lane_global_avg_finish=("finish_pos", "mean"),
        )
        .reset_index()
    )

    global_priors = {
        "hist_win_rate": float(train_df["is_win"].mean() * 100.0),
        "hist_top3_rate": float(train_df["is_top3"].mean() * 100.0),
        "hist_avg_finish": float(train_df["finish_pos"].mean()),
        "lane1_escape_rate": float(
            100.0
            * (
                ((train_df["lane"] == 1) & (train_df["winner_technique"] == "逃げ")).sum()
                / max((train_df["lane"] == 1).sum(), 1)
            )
        ),
        "inner_sashi_like_rate": float(
            100.0
            * (
                (
                    train_df["lane"].isin([2, 3])
                    & train_df["winner_technique"].isin(["差し", "まくり差し"])
                ).sum()
                / max(train_df["lane"].isin([2, 3]).sum(), 1)
            )
        ),
        "outer_attack_rate": float(
            100.0
            * (
                (
                    train_df["lane"].isin([4, 5, 6])
                    & train_df["winner_technique"].isin(["まくり", "まくり差し"])
                ).sum()
                / max(train_df["lane"].isin([4, 5, 6]).sum(), 1)
            )
        ),
    }

    overall = (
        train_df.groupby("racer_id", observed=True)
        .agg(
            hist_starts=("race_id", "size"),
            hist_win_rate_raw=("is_win", lambda s: float(s.mean() * 100.0)),
            hist_top3_rate_raw=("is_top3", lambda s: float(s.mean() * 100.0)),
            hist_avg_finish_raw=("finish_pos", "mean"),
        )
        .reset_index()
    )
    overall["hist_win_rate"] = smooth_series(
        overall["hist_win_rate_raw"],
        overall["hist_starts"],
        global_priors["hist_win_rate"],
        OVERALL_SHRINKAGE,
    )
    overall["hist_top3_rate"] = smooth_series(
        overall["hist_top3_rate_raw"],
        overall["hist_starts"],
        global_priors["hist_top3_rate"],
        OVERALL_SHRINKAGE,
    )
    overall["hist_avg_finish"] = smooth_series(
        overall["hist_avg_finish_raw"],
        overall["hist_starts"],
        global_priors["hist_avg_finish"],
        OVERALL_SHRINKAGE,
    )

    lane_profile = (
        train_df.groupby(["racer_id", "lane"], observed=True)
        .agg(
            lane_starts=("race_id", "size"),
            lane_win_rate_raw=("is_win", lambda s: float(s.mean() * 100.0)),
            lane_top3_rate_raw=("is_top3", lambda s: float(s.mean() * 100.0)),
            lane_avg_finish_raw=("finish_pos", "mean"),
        )
        .reset_index()
        .merge(lane_globals, on="lane", how="left")
    )
    lane_profile["lane_win_rate"] = smooth_series(
        lane_profile["lane_win_rate_raw"],
        lane_profile["lane_starts"],
        lane_profile["lane_global_win_rate"],
        LANE_SHRINKAGE,
    )
    lane_profile["lane_top3_rate"] = smooth_series(
        lane_profile["lane_top3_rate_raw"],
        lane_profile["lane_starts"],
        lane_profile["lane_global_top3_rate"],
        LANE_SHRINKAGE,
    )
    lane_profile["lane_avg_finish"] = smooth_series(
        lane_profile["lane_avg_finish_raw"],
        lane_profile["lane_starts"],
        lane_profile["lane_global_avg_finish"],
        LANE_SHRINKAGE,
    )

    style_base = train_df.assign(
        lane1_start=(train_df["lane"] == 1).astype(int),
        lane1_escape_win=((train_df["lane"] == 1) & (train_df["winner_technique"] == "逃げ")).astype(int),
        inner_start=train_df["lane"].isin([2, 3]).astype(int),
        inner_sashi_like_win=(
            train_df["lane"].isin([2, 3])
            & train_df["winner_technique"].isin(["差し", "まくり差し"])
        ).astype(int),
        outer_start=train_df["lane"].isin([4, 5, 6]).astype(int),
        outer_attack_win=(
            train_df["lane"].isin([4, 5, 6])
            & train_df["winner_technique"].isin(["まくり", "まくり差し"])
        ).astype(int),
    )
    style_profile = (
        style_base.groupby("racer_id", observed=True)
        .agg(
            lane1_start=("lane1_start", "sum"),
            lane1_escape_win=("lane1_escape_win", "sum"),
            inner_start=("inner_start", "sum"),
            inner_sashi_like_win=("inner_sashi_like_win", "sum"),
            outer_start=("outer_start", "sum"),
            outer_attack_win=("outer_attack_win", "sum"),
        )
        .reset_index()
    )
    style_profile["lane1_escape_rate"] = smooth_series(
        100.0 * style_profile["lane1_escape_win"] / style_profile["lane1_start"].replace(0, np.nan),
        style_profile["lane1_start"],
        global_priors["lane1_escape_rate"],
        STYLE_SHRINKAGE,
    )
    style_profile["inner_sashi_like_rate"] = smooth_series(
        100.0 * style_profile["inner_sashi_like_win"] / style_profile["inner_start"].replace(0, np.nan),
        style_profile["inner_start"],
        global_priors["inner_sashi_like_rate"],
        STYLE_SHRINKAGE,
    )
    style_profile["outer_attack_rate"] = smooth_series(
        100.0 * style_profile["outer_attack_win"] / style_profile["outer_start"].replace(0, np.nan),
        style_profile["outer_start"],
        global_priors["outer_attack_rate"],
        STYLE_SHRINKAGE,
    )

    return {
        "overall": overall,
        "lane": lane_profile,
        "style": style_profile,
        "lane_globals": lane_globals,
        "global_priors": global_priors,
    }


def enrich_with_profiles(df: pd.DataFrame, profiles: dict[str, object]) -> pd.DataFrame:
    overall = profiles["overall"]
    lane_profile = profiles["lane"]
    style_profile = profiles["style"]
    lane_globals = profiles["lane_globals"]
    global_priors = profiles["global_priors"]

    enriched = df.merge(
        overall[
            [
                "racer_id",
                "hist_starts",
                "hist_win_rate",
                "hist_top3_rate",
                "hist_avg_finish",
            ]
        ],
        on="racer_id",
        how="left",
    )
    enriched = enriched.merge(
        lane_profile[
            [
                "racer_id",
                "lane",
                "lane_starts",
                "lane_win_rate",
                "lane_top3_rate",
                "lane_avg_finish",
            ]
        ],
        on=["racer_id", "lane"],
        how="left",
    )
    enriched = enriched.merge(
        style_profile[
            [
                "racer_id",
                "lane1_escape_rate",
                "inner_sashi_like_rate",
                "outer_attack_rate",
            ]
        ],
        on="racer_id",
        how="left",
    )
    enriched = enriched.merge(lane_globals, on="lane", how="left")

    enriched["class_point"] = enriched["racer_class"].map(CLASS_POINTS).fillna(1.0)
    enriched["avg_start_timing_neg"] = -enriched["avg_start_timing"]
    enriched["f_count_neg"] = -enriched["f_count"]
    enriched["l_count_neg"] = -enriched["l_count"]
    enriched["exhibition_rank_score"] = 7.0 - enriched["exhibition_rank"]
    enriched["exhibition_st_rank_score"] = 7.0 - enriched["exhibition_st_rank"]
    enriched["national_win_rank_score"] = 7.0 - enriched["national_win_rank"]
    enriched["motor_rank_score"] = 7.0 - enriched["motor_rank"]

    enriched["hist_win_rate"] = enriched["hist_win_rate"].fillna(global_priors["hist_win_rate"])
    enriched["hist_top3_rate"] = enriched["hist_top3_rate"].fillna(global_priors["hist_top3_rate"])
    enriched["hist_avg_finish"] = enriched["hist_avg_finish"].fillna(global_priors["hist_avg_finish"])

    enriched["lane_win_rate"] = enriched["lane_win_rate"].fillna(enriched["lane_global_win_rate"])
    enriched["lane_top3_rate"] = enriched["lane_top3_rate"].fillna(enriched["lane_global_top3_rate"])
    enriched["lane_avg_finish"] = enriched["lane_avg_finish"].fillna(enriched["lane_global_avg_finish"])

    enriched["lane1_escape_rate"] = enriched["lane1_escape_rate"].fillna(global_priors["lane1_escape_rate"])
    enriched["inner_sashi_like_rate"] = enriched["inner_sashi_like_rate"].fillna(global_priors["inner_sashi_like_rate"])
    enriched["outer_attack_rate"] = enriched["outer_attack_rate"].fillna(global_priors["outer_attack_rate"])
    enriched["style_fit_rate"] = np.select(
        [
            enriched["lane"] == 1,
            enriched["lane"].isin([2, 3]),
        ],
        [
            enriched["lane1_escape_rate"],
            enriched["inner_sashi_like_rate"],
        ],
        default=enriched["outer_attack_rate"],
    )

    enriched["hist_avg_finish_score"] = 7.0 - enriched["hist_avg_finish"]
    enriched["lane_avg_finish_score"] = 7.0 - enriched["lane_avg_finish"]

    return enriched


def build_standardization(train_df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    feature_frame = train_df[FEATURE_COLUMNS].astype(np.float64).copy()
    medians = feature_frame.median(numeric_only=True).fillna(0.0)
    feature_frame = feature_frame.fillna(medians)
    means = feature_frame.mean().fillna(0.0)
    stds = feature_frame.std(ddof=0).replace(0, 1.0).fillna(1.0)
    return medians, means, stds


def prepare_bundle(
    name: str,
    df: pd.DataFrame,
    medians: pd.Series,
    means: pd.Series,
    stds: pd.Series,
) -> DatasetBundle:
    frame = df.sort_values(["race_date", "race_id", "lane"]).reset_index(drop=True).copy()
    frame = frame[frame["finish_pos"].notna()].reset_index(drop=True)
    race_sizes = frame.groupby("race_id", observed=True)["lane"].transform("size")
    frame = frame[race_sizes == 6].reset_index(drop=True)

    feature_frame = frame[FEATURE_COLUMNS].astype(np.float64).copy()
    feature_frame = feature_frame.fillna(medians)
    feature_frame = (feature_frame - means) / stds

    row_count = len(frame)
    if row_count % 6 != 0:
        raise ValueError(f"{name}: row count {row_count} is not divisible by 6")

    feature_matrix = feature_frame.to_numpy(dtype=np.float64)
    lanes = frame["lane"].to_numpy(dtype=np.float64).astype(np.int16).reshape(-1, 6)
    finish_pos = frame["finish_pos"].to_numpy(dtype=np.float64).astype(np.int16).reshape(-1, 6)
    race_ids = frame["race_id"].to_numpy().reshape(-1, 6)[:, 0]

    return DatasetBundle(
        name=name,
        frame=frame,
        feature_matrix=feature_matrix,
        lanes=lanes,
        finish_pos=finish_pos,
        race_ids=race_ids,
    )


def fit_initial_weights(train_bundle: DatasetBundle) -> np.ndarray:
    target = (7 - train_bundle.frame["finish_pos"].to_numpy(dtype=np.float64)).reshape(-1, 1)
    weights, *_ = np.linalg.lstsq(train_bundle.feature_matrix, target, rcond=None)
    return weights[:, 0]


def ranks_from_scores(score_matrix: np.ndarray, lanes: np.ndarray) -> np.ndarray:
    tie_break_adjusted = score_matrix + (7 - lanes) * TIE_BREAK_EPSILON
    order = np.argsort(-tie_break_adjusted, axis=1, kind="mergesort")
    pred_rank = np.empty_like(order) + 1
    pred_rank[np.arange(score_matrix.shape[0])[:, None], order] = np.arange(1, score_matrix.shape[1] + 1)
    return pred_rank


def evaluate_weights(bundle: DatasetBundle, weights: np.ndarray) -> dict[str, float]:
    score_matrix = (bundle.feature_matrix @ weights).reshape(-1, 6)
    pred_rank = ranks_from_scores(score_matrix, bundle.lanes)
    finish_pos = bundle.finish_pos

    rank_mae = float(np.mean(np.abs(pred_rank - finish_pos)))
    rank_rmse = float(np.sqrt(np.mean((pred_rank - finish_pos) ** 2)))
    winner_hit_rate = float(np.mean(np.any((pred_rank == 1) & (finish_pos == 1), axis=1)))
    top2_set_hit_rate = float(np.mean(np.all((pred_rank <= 2) == (finish_pos <= 2), axis=1)))
    top3_set_hit_rate = float(np.mean(np.all((pred_rank <= 3) == (finish_pos <= 3), axis=1)))
    exact_order_rate = float(np.mean(np.all(pred_rank == finish_pos, axis=1)))

    pair_mask = np.triu(np.ones((6, 6), dtype=bool), 1)
    pred_diff = pred_rank[:, :, None] - pred_rank[:, None, :]
    actual_diff = finish_pos[:, :, None] - finish_pos[:, None, :]
    pairwise_accuracy = float(np.mean((pred_diff[:, pair_mask] * actual_diff[:, pair_mask]) > 0))

    return {
        "races": int(score_matrix.shape[0]),
        "rank_mae": rank_mae,
        "rank_rmse": rank_rmse,
        "winner_hit_rate": winner_hit_rate,
        "top2_set_hit_rate": top2_set_hit_rate,
        "top3_set_hit_rate": top3_set_hit_rate,
        "exact_order_rate": exact_order_rate,
        "pairwise_accuracy": pairwise_accuracy,
    }


def metric_key(metrics: dict[str, float]) -> tuple[float, float, float, float]:
    return (
        metrics["rank_mae"],
        -metrics["pairwise_accuracy"],
        -metrics["winner_hit_rate"],
        -metrics["top3_set_hit_rate"],
    )


def optimize_weights(initial_weights: np.ndarray, valid_bundle: DatasetBundle) -> tuple[np.ndarray, dict[str, float]]:
    rng = np.random.default_rng(RANDOM_SEED)
    best_weights = initial_weights.copy()
    best_metrics = evaluate_weights(valid_bundle, best_weights)

    for scale in (0.75, 0.45, 0.25):
        for _ in range(RANDOM_TRIALS):
            candidate = best_weights + rng.normal(0.0, scale, size=best_weights.shape[0])
            candidate_metrics = evaluate_weights(valid_bundle, candidate)
            if metric_key(candidate_metrics) < metric_key(best_metrics):
                best_weights = candidate
                best_metrics = candidate_metrics

    for step in (0.40, 0.20, 0.10, 0.05):
        improved = True
        while improved:
            improved = False
            for index in range(best_weights.shape[0]):
                for direction in (-1.0, 1.0):
                    candidate = best_weights.copy()
                    candidate[index] += direction * step
                    candidate_metrics = evaluate_weights(valid_bundle, candidate)
                    if metric_key(candidate_metrics) < metric_key(best_metrics):
                        best_weights = candidate
                        best_metrics = candidate_metrics
                        improved = True

    return best_weights, best_metrics


def build_predictions(bundle: DatasetBundle, weights: np.ndarray) -> pd.DataFrame:
    score_matrix = (bundle.feature_matrix @ weights).reshape(-1, 6)
    pred_rank = ranks_from_scores(score_matrix, bundle.lanes)

    frame = bundle.frame.copy()
    frame["pred_score"] = score_matrix.reshape(-1)
    frame["pred_rank"] = pred_rank.reshape(-1)
    return frame


def make_feature_weight_table(weights: np.ndarray) -> pd.DataFrame:
    table = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "weight": weights,
        }
    )
    table["abs_weight"] = table["weight"].abs()
    table = table.sort_values("abs_weight", ascending=False).reset_index(drop=True)
    return table


def write_summary(
    path: Path,
    metrics_by_split: dict[str, dict[str, float]],
    weight_table: pd.DataFrame,
) -> None:
    lines = [
        "# Racer Finish Score Fit",
        "",
        "## Split",
        "",
        f"- history window: `{HISTORY_START}` .. `{HISTORY_END}`",
        f"- candidate extraction month: `{TUNE_START}` .. `{TUNE_END}`",
        f"- forward month: `{FORWARD_START}` .. `{FORWARD_END}`",
        "",
        "## Metrics",
        "",
        "| split | races | rank_mae | rank_rmse | winner_hit | top2_set_hit | top3_set_hit | exact_order | pairwise_acc |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for split_name in (
        "tuning_feb_baseline",
        "tuning_feb_initial",
        "tuning_feb_optimized",
        "forward_march_baseline",
        "forward_march_optimized",
    ):
        metrics = metrics_by_split[split_name]
        lines.append(
            "| {label} | {races} | {rank_mae:.4f} | {rank_rmse:.4f} | {winner_hit_rate:.4f} | {top2_set_hit_rate:.4f} | {top3_set_hit_rate:.4f} | {exact_order_rate:.4f} | {pairwise_accuracy:.4f} |".format(
                label=split_name,
                **metrics,
            )
        )

    lines.extend(
        [
            "",
            "## Top Weights",
            "",
            "| feature | weight |",
            "| --- | ---: |",
        ]
    )
    for row in weight_table.head(12).itertuples(index=False):
        lines.append(f"| {row.feature} | {row.weight:.4f} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dir(OUTPUT_DIR)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        history_raw = load_period(con, HISTORY_START, HISTORY_END)
        tuning_raw = load_period(con, TUNE_START, TUNE_END)
        forward_raw = load_period(con, FORWARD_START, FORWARD_END)
    finally:
        con.close()

    profiles = build_racer_profiles(history_raw)
    tuning_enriched = enrich_with_profiles(tuning_raw, profiles)
    forward_enriched = enrich_with_profiles(forward_raw, profiles)

    medians, means, stds = build_standardization(tuning_enriched)

    tuning_bundle = prepare_bundle("tuning_feb", tuning_enriched, medians, means, stds)
    forward_bundle = prepare_bundle("forward_march", forward_enriched, medians, means, stds)

    initial_weights = fit_initial_weights(tuning_bundle)
    baseline_weights = np.zeros_like(initial_weights)
    lane_feature_index = FEATURE_COLUMNS.index("lane_win_rate")
    baseline_weights[lane_feature_index] = 1.0

    tuning_feb_baseline = evaluate_weights(tuning_bundle, baseline_weights)
    tuning_feb_initial = evaluate_weights(tuning_bundle, initial_weights)
    optimized_weights, tuning_feb_optimized = optimize_weights(initial_weights, tuning_bundle)

    forward_march_baseline = evaluate_weights(forward_bundle, baseline_weights)
    forward_march_optimized = evaluate_weights(forward_bundle, optimized_weights)

    weight_table = make_feature_weight_table(optimized_weights)
    tuning_predictions = build_predictions(tuning_bundle, optimized_weights)
    forward_predictions = build_predictions(forward_bundle, optimized_weights)

    metrics_payload = {
        "tuning_feb_baseline": tuning_feb_baseline,
        "tuning_feb_initial": tuning_feb_initial,
        "tuning_feb_optimized": tuning_feb_optimized,
        "forward_march_baseline": forward_march_baseline,
        "forward_march_optimized": forward_march_optimized,
    }

    weight_table.to_csv(OUTPUT_DIR / "feature_weights.csv", index=False, encoding="utf-8-sig")
    tuning_predictions.to_csv(OUTPUT_DIR / "tuning_feb_predictions.csv", index=False, encoding="utf-8-sig")
    forward_predictions.to_csv(OUTPUT_DIR / "forward_march_predictions.csv", index=False, encoding="utf-8-sig")
    (OUTPUT_DIR / "metrics.json").write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_summary(
        OUTPUT_DIR / "summary.md",
        metrics_by_split=metrics_payload,
        weight_table=weight_table,
    )

    print(f"wrote outputs to {OUTPUT_DIR}")
    print(json.dumps(metrics_payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
