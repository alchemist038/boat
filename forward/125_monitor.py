import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import csv

# 既存のモジュールのインポートを可能にするためのパス設定
sys.path.append(str(Path(__file__).parent.parent / "src"))

from boat_race_data.parsers import parse_beforeinfo, parse_racelist, parse_result
from boat_race_data.constants import STADIUMS

# 125戦略の定義 (住之江、鳴門、芦屋、江戸川)
TARGET_STADIUMS = ["12", "14", "21", "03"]
LANE1_CLASS_TARGET = ["B1"]
LANE6_CLASS_TARGET = ["B2"]
LANE5_CLASS_EXCLUDE = ["B2"]
EX_BEST_GAP_MAX = 0.02

def monitor_125(days=7):
    raw_root = Path("d:/boat/data/raw")
    results_root = raw_root / "results"
    beforeinfo_root = raw_root / "beforeinfo"
    racelist_root = raw_root / "racelist"

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_list = [(start_date + timedelta(days=x)).strftime("%Y%m%d") for x in range(days + 1)]

    matches = []

    for date_str in date_list:
        date_beforeinfo_dir = beforeinfo_root / date_str
        if not date_beforeinfo_dir.exists(): continue

        print(f"Scanning {date_str}...")
        for b_file in date_beforeinfo_dir.glob("*.html"):
            prefix = b_file.stem
            stadium_code = prefix.split("_")[0]
            race_no = int(prefix.split("_")[1])

            if stadium_code not in TARGET_STADIUMS: continue

            # 1. Racelist 取得
            r_file = racelist_root / date_str / f"{prefix}.html"
            if not r_file.exists(): continue
            with r_file.open("r", encoding="utf-8") as f: html_r = f.read()
            race_meta, entry_rows = parse_racelist(html_r, date_str, stadium_code, STADIUMS.get(stadium_code, ""), race_no, "", "")
            if not race_meta or not entry_rows: continue

            lane1_entry = next((e for e in entry_rows if e["lane"] == 1), None)
            lane5_entry = next((e for e in entry_rows if e["lane"] == 5), None)
            lane6_entry = next((e for e in entry_rows if e["lane"] == 6), None)

            if not lane1_entry or not lane5_entry or not lane6_entry: continue
            if lane1_entry.get("racer_class") not in LANE1_CLASS_TARGET: continue
            if lane6_entry.get("racer_class") not in LANE6_CLASS_TARGET: continue
            if lane5_entry.get("racer_class") in LANE5_CLASS_EXCLUDE: continue
            if stadium_code == "21" and lane5_entry.get("racer_class") != "B1": continue

            # 2. Beforeinfo 取得
            with b_file.open("r", encoding="utf-8") as f: html_b = f.read()
            beforeinfo_rows = parse_beforeinfo(html_b, date_str, stadium_code, race_no, "", "")
            if not beforeinfo_rows: continue

            ex_times = [r["exhibition_time"] for r in beforeinfo_rows if r.get("exhibition_time") is not None]
            if not ex_times: continue
            best_ex = min(ex_times)
            lane1_bi = next((r for r in beforeinfo_rows if r["lane"] == 1), None)
            if not lane1_bi or lane1_bi.get("exhibition_time") is None: continue
            ex_gap = lane1_bi["exhibition_time"] - best_ex

            if ex_gap > EX_BEST_GAP_MAX: continue

            # 3. Result 取得
            res_file = results_root / date_str / f"{prefix}.html"
            result_data = None
            if res_file.exists():
                with res_file.open("r", encoding="utf-8") as f: html_res = f.read()
                result_data = parse_result(html_res, date_str, stadium_code, race_no, "", "")

            matches.append({
                "date": date_str,
                "stadium": STADIUMS.get(stadium_code, stadium_code),
                "race_no": race_no,
                "ex_gap": round(ex_gap, 3),
                "trifecta_combo": result_data.get("trifecta_combo") if result_data else "N/A",
                "trifecta_payout": result_data.get("trifecta_payout") if result_data else 0,
            })

    if not matches:
        print("No 125 matches found.")
        return

    total_races = len(matches)
    total_investment = total_races * 100
    total_payout = 0
    hit_count = 0

    print(f"\n--- 125 Strategy Monitor Result ({date_list[0]} - {date_list[-1]}) ---")
    header = f"{'Date':<10} {'Stadium':<10} {'R#':<3} {'ExGap':<6} {'Combo':<10} {'Payout':<10}"
    print(header); print("-" * len(header))

    for m in matches:
        combo = m["trifecta_combo"]
        payout = int(m["trifecta_payout"]) if m["trifecta_payout"] else 0
        is_hit = False
        if combo:
            clean_combo = combo.replace(" ", "")
            if clean_combo == "1-2-5":
                is_hit = True; hit_count += 1; total_payout += payout
        row_payout = payout if is_hit else 0
        print(f"{m['date']:<10} {m['stadium']:<10} {m['race_no']:<3} {m['ex_gap']:<6} {combo:<10} {row_payout:<10,}")

    roi = (total_payout / total_investment * 100) if total_investment > 0 else 0
    print(f"\nStats: {hit_count}/{total_races} hits, ROI: {roi:.2f}%, Payout: {total_payout:,} yen")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Number of days to scan back from today")
    args = parser.parse_args()
    monitor_125(args.days)
