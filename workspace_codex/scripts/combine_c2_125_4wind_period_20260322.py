from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(r"D:\boat")
START_DATE = date.fromisoformat("2025-04-01")
END_DATE = date.fromisoformat("2026-03-09")

C2_SOURCE = ROOT / "GPT" / "output" / "20260313_refined_c2_candidates" / "best_roi_near_double_race_results.csv"
FOUR_STADIUM_X20_SOURCE = (
    ROOT
    / "workspace_codex"
    / "analysis"
    / "combined"
    / "c2_plus_four_stadium_x20_20260314"
    / "four_stadium_local_best_exgap_x20_race_results.csv"
)
FOUR_WIND_SOURCE = (
    ROOT
    / "reports"
    / "strategies"
    / "gemini_registry"
    / "4wind"
    / "odds_backtest_20260322"
    / "backtest_bets.csv"
)
OUTPUT_DIR = (
    ROOT
    / "reports"
    / "strategies"
    / "combined"
    / "c2_125_4wind_2025-04-01_to_2026-03-09_20260322"
)


@dataclass(frozen=True)
class RaceResult:
    strategy: str
    race_id: str
    race_date: date
    bet_amount: int
    payout: int
    profit: int

    @property
    def is_hit(self) -> bool:
        return self.payout > 0

    @property
    def is_profit(self) -> bool:
        return self.profit > 0


def _parse_date(text: str) -> date:
    return date.fromisoformat(text)


def _in_period(text: str) -> bool:
    d = _parse_date(text)
    return START_DATE <= d <= END_DATE


def _load_c2() -> list[RaceResult]:
    rows: list[RaceResult] = []
    with C2_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not _in_period(row["race_date"]):
                continue
            rows.append(
                RaceResult(
                    strategy="C2_provisional_v1",
                    race_id=row["race_id"],
                    race_date=_parse_date(row["race_date"]),
                    bet_amount=int(row["bet_amount"]),
                    payout=int(row["payout"]),
                    profit=int(row["profit"]),
                )
            )
    return rows


def _load_125_x1() -> list[RaceResult]:
    rows: list[RaceResult] = []
    with FOUR_STADIUM_X20_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not _in_period(row["race_date"]):
                continue
            rows.append(
                RaceResult(
                    strategy="125_four_stadium_x1",
                    race_id=row["race_id"],
                    race_date=_parse_date(row["race_date"]),
                    bet_amount=int(round(int(row["bet_amount"]) / 20)),
                    payout=int(round(int(row["payout"]) / 20)),
                    profit=int(round(int(row["profit"]) / 20)),
                )
            )
    return rows


def _load_4wind() -> list[RaceResult]:
    rows: list[RaceResult] = []
    with FOUR_WIND_SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["strategy_name"] != "only_wind_5_6_415":
                continue
            if not _in_period(row["race_date"]):
                continue
            rows.append(
                RaceResult(
                    strategy="4wind_only_wind_5_6_415",
                    race_id=row["race_id"],
                    race_date=_parse_date(row["race_date"]),
                    bet_amount=int(row["stake_yen"]),
                    payout=int(row["realized_payout"]),
                    profit=int(row["realized_payout"]) - int(row["stake_yen"]),
                )
            )
    return rows


def _sort_rows(rows: list[RaceResult]) -> list[RaceResult]:
    return sorted(rows, key=lambda row: (row.race_date, row.race_id, row.strategy))


def _combine_rows(name: str, *groups: list[RaceResult]) -> list[RaceResult]:
    by_race: dict[tuple[date, str], dict[str, int | date | str]] = {}
    for group in groups:
        for row in group:
            key = (row.race_date, row.race_id)
            current = by_race.setdefault(
                key,
                {
                    "race_date": row.race_date,
                    "race_id": row.race_id,
                    "bet_amount": 0,
                    "payout": 0,
                    "profit": 0,
                },
            )
            current["bet_amount"] += row.bet_amount
            current["payout"] += row.payout
            current["profit"] += row.profit

    combined = [
        RaceResult(
            strategy=name,
            race_id=current["race_id"],  # type: ignore[arg-type]
            race_date=current["race_date"],  # type: ignore[arg-type]
            bet_amount=current["bet_amount"],  # type: ignore[arg-type]
            payout=current["payout"],  # type: ignore[arg-type]
            profit=current["profit"],  # type: ignore[arg-type]
        )
        for current in by_race.values()
    ]
    return _sort_rows(combined)


def _scale_rows(rows: list[RaceResult], factor: int, strategy_name: str) -> list[RaceResult]:
    return [
        RaceResult(
            strategy=strategy_name,
            race_id=row.race_id,
            race_date=row.race_date,
            bet_amount=row.bet_amount * factor,
            payout=row.payout * factor,
            profit=row.profit * factor,
        )
        for row in rows
    ]


def _max_drawdown(rows: list[RaceResult]) -> tuple[int, str, str]:
    cumulative = 0
    peak = 0
    max_dd = 0
    peak_date = ""
    trough_date = ""
    current_peak_date = ""
    for row in rows:
        cumulative += row.profit
        if cumulative > peak:
            peak = cumulative
            current_peak_date = row.race_date.isoformat()
        drawdown = peak - cumulative
        if drawdown > max_dd:
            max_dd = drawdown
            peak_date = current_peak_date
            trough_date = row.race_date.isoformat()
    return max_dd, peak_date, trough_date


def _max_losing_streak(rows: list[RaceResult]) -> int:
    current = 0
    best = 0
    for row in rows:
        if row.profit > 0:
            current = 0
        else:
            current += 1
            if current > best:
                best = current
    return best


def _summarize(rows: list[RaceResult]) -> dict[str, object]:
    races = len(rows)
    hit_count = sum(1 for row in rows if row.is_hit)
    bet_total = sum(row.bet_amount for row in rows)
    payout_total = sum(row.payout for row in rows)
    profit_total = sum(row.profit for row in rows)
    roi_pct = (payout_total / bet_total * 100.0) if bet_total else 0.0
    pf = (payout_total / bet_total) if bet_total else 0.0
    max_dd, dd_start, dd_end = _max_drawdown(rows)
    max_ls = _max_losing_streak(rows)
    return {
        "races": races,
        "hits": hit_count,
        "hit_rate_pct": round(hit_count / races * 100.0, 4) if races else 0.0,
        "bet_total_yen": bet_total,
        "payout_total_yen": payout_total,
        "profit_yen": profit_total,
        "roi_pct": round(roi_pct, 2),
        "pf": round(pf, 4),
        "max_dd_yen": max_dd,
        "max_dd_start": dd_start,
        "max_dd_end": dd_end,
        "max_losing_streak": max_ls,
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_race_results(path: Path, rows: list[RaceResult]) -> None:
    cumulative = 0
    peak = 0
    output_rows: list[dict[str, object]] = []
    for row in rows:
        cumulative += row.profit
        if cumulative > peak:
            peak = cumulative
        output_rows.append(
            {
                "strategy": row.strategy,
                "race_id": row.race_id,
                "race_date": row.race_date.isoformat(),
                "bet_amount": row.bet_amount,
                "payout": row.payout,
                "profit": row.profit,
                "cumulative_profit": cumulative,
                "drawdown": peak - cumulative,
            }
        )
    _write_csv(
        path,
        ["strategy", "race_id", "race_date", "bet_amount", "payout", "profit", "cumulative_profit", "drawdown"],
        output_rows,
    )


def _overlap_rows(
    c2_rows: list[RaceResult],
    rows_125: list[RaceResult],
    rows_4wind: list[RaceResult],
) -> list[dict[str, object]]:
    c2_ids = {row.race_id for row in c2_rows}
    ids_125 = {row.race_id for row in rows_125}
    ids_4wind = {row.race_id for row in rows_4wind}
    overlap_rows = [
        {"pair": "C2 ∩ 125", "shared_races": len(c2_ids & ids_125)},
        {"pair": "C2 ∩ 4wind", "shared_races": len(c2_ids & ids_4wind)},
        {"pair": "125 ∩ 4wind", "shared_races": len(ids_125 & ids_4wind)},
        {"pair": "C2 ∩ 125 ∩ 4wind", "shared_races": len(c2_ids & ids_125 & ids_4wind)},
    ]
    return overlap_rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    c2_rows = _sort_rows(_load_c2())
    rows_125 = _sort_rows(_load_125_x1())
    rows_4wind = _sort_rows(_load_4wind())
    rows_125_x20 = _sort_rows(_scale_rows(rows_125, 20, "125_four_stadium_x20"))
    rows_4wind_x5 = _sort_rows(_scale_rows(rows_4wind, 5, "4wind_only_wind_5_6_415_x5"))

    combined_c2_125 = _combine_rows("C2_plus_125_natural", c2_rows, rows_125)
    combined_all = _combine_rows("C2_plus_125_plus_4wind_natural", c2_rows, rows_125, rows_4wind)
    combined_c2_125_x20 = _combine_rows("C2_plus_125_x20", c2_rows, rows_125_x20)
    combined_all_weighted = _combine_rows(
        "C2_plus_125_x20_plus_4wind_x5",
        c2_rows,
        rows_125_x20,
        rows_4wind_x5,
    )

    groups = {
        "C2_provisional_v1": c2_rows,
        "125_four_stadium_x1": rows_125,
        "125_four_stadium_x20": rows_125_x20,
        "4wind_only_wind_5_6_415": rows_4wind,
        "4wind_only_wind_5_6_415_x5": rows_4wind_x5,
        "C2_plus_125_natural": combined_c2_125,
        "C2_plus_125_plus_4wind_natural": combined_all,
        "C2_plus_125_x20": combined_c2_125_x20,
        "C2_plus_125_x20_plus_4wind_x5": combined_all_weighted,
    }

    summary_rows: list[dict[str, object]] = []
    for name, rows in groups.items():
        row = {"strategy": name}
        row.update(_summarize(rows))
        summary_rows.append(row)

    _write_csv(
        OUTPUT_DIR / "summary.csv",
        [
            "strategy",
            "races",
            "hits",
            "hit_rate_pct",
            "bet_total_yen",
            "payout_total_yen",
            "profit_yen",
            "roi_pct",
            "pf",
            "max_dd_yen",
            "max_dd_start",
            "max_dd_end",
            "max_losing_streak",
        ],
        summary_rows,
    )

    _write_csv(OUTPUT_DIR / "overlaps.csv", ["pair", "shared_races"], _overlap_rows(c2_rows, rows_125, rows_4wind))

    for name, rows in groups.items():
        _write_race_results(OUTPUT_DIR / f"{name}_race_results.csv", rows)

    readme_lines = [
        "# C2 + 125 + 4wind Combined Snapshot 2026-03-22",
        "",
        f"- aligned period: `{START_DATE.isoformat()}` to `{END_DATE.isoformat()}`",
        "- note: `C2` canonical race results currently end on `2026-03-09`, so the combination is aligned to that common end date.",
        "- C2 definition: `Strategy_C2_Provisional_v1`",
        "- 125 definition: existing four-stadium `local_best_exgap` line, converted back to natural `x1` stake",
        "- 4wind definition: `only_wind_5_6_415` from the 2026-03-22 odds backtest",
        "",
        "## Stake Note",
        "- `C2`: `4,000円 / race`",
        "- `125`: `100円 / race`",
        "- `4wind`: `200円 / race`",
        "- This is a natural-stake combination, so `C2` contributes most of the portfolio risk and return.",
        "",
        "## Files",
        "- `summary.csv`",
        "- `overlaps.csv`",
        "- `*_race_results.csv` for each individual strategy and the combined portfolios",
        "",
        "## Weighted Variant",
        "- `125 x20R`, `4wind x5R`, `C2` unchanged is included in the same `summary.csv` as `C2_plus_125_x20` and `C2_plus_125_x20_plus_4wind_x5`.",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
