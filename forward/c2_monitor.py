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

# C2戦略の定義
C2_PROFILE = {
    "meeting_title_keywords": ["女子", "ヴィーナス", "レディース", "オールレディース", "Lady", "Venus"],
    "lane1_start_gap_over_rest_min": 0.12,
    "ex1_vs_ex2_max_gap": 0.02,
    "ex1_vs_ex3_max_gap": 0.02
}

def monitor_c2(days=7):
    raw_root = Path("d:/boat/data/raw")
    results_root = raw_root / "results"
    beforeinfo_root = raw_root / "beforeinfo"
    racelist_root = raw_root / "racelist"

    end_date = datetime.now()
    # ユーザーの実行環境が2026年想定なので、固定日からの相対にすることも可能だが、
    # ここでは実行時からの相対とする。ただし、生データの最新が2026-03-15なので、
    # 引数で開始日を指定できるように拡張する。
    
    start_date = end_date - timedelta(days=days)
    date_list = [(start_date + timedelta(days=x)).strftime("%Y%m%d") for x in range(days + 1)]

    # 実際のデータがある範囲に限定 (デバッグ/検証用)
    # date_list = ["20260308", "20260309", "20260310", "20260311", "20260312", "20260313", "20260314", "20260315"]

    matches = []

    for date_str in date_list:
        date_beforeinfo_dir = beforeinfo_root / date_str
        if not date_beforeinfo_dir.exists():
            continue

        print(f"Scanning {date_str}...")
        for b_file in date_beforeinfo_dir.glob("*.html"):
            prefix = b_file.stem
            stadium_code = prefix.split("_")[0]
            race_no = int(prefix.split("_")[1])

            # 1. Racelist 取得 (タイトル判定のため)
            r_file = racelist_root / date_str / f"{prefix}.html"
            if not r_file.exists(): continue
            
            with r_file.open("r", encoding="utf-8") as f: html_r = f.read()
            race_meta, _ = parse_racelist(html_r, date_str, stadium_code, STADIUMS.get(stadium_code, ""), race_no, "", "")
            if not race_meta: continue

            meeting_title = race_meta.get("meeting_title", "")
            if not any(kw in meeting_title for kw in C2_PROFILE["meeting_title_keywords"]):
                continue

            # 2. Beforeinfo 取得
            with b_file.open("r", encoding="utf-8") as f: html_b = f.read()
            beforeinfo_rows = parse_beforeinfo(html_b, date_str, stadium_code, race_no, "", "")
            if not beforeinfo_rows: continue

            lane1 = next((r for r in beforeinfo_rows if r["lane"] == 1), None)
            if not lane1 or lane1.get("exhibition_time") is None or lane1.get("start_exhibition_st") is None:
                continue

            ex1 = lane1["exhibition_time"]
            lane2 = next((r for r in beforeinfo_rows if r["lane"] == 2), None)
            lane3 = next((r for r in beforeinfo_rows if r["lane"] == 3), None)
            ex2 = lane2["exhibition_time"] if lane2 else 99.99
            ex3 = lane3["exhibition_time"] if lane3 else 99.99

            st1 = lane1["start_exhibition_st"]
            others_st = [r["start_exhibition_st"] for r in beforeinfo_rows if r["lane"] != 1 and r.get("start_exhibition_st") is not None]
            if not others_st: continue
            min_other_st = min(others_st)
            st_gap = st1 - min_other_st

            if (st_gap >= C2_PROFILE["lane1_start_gap_over_rest_min"] and 
                ex1 <= ex2 + C2_PROFILE["ex1_vs_ex2_max_gap"] and 
                ex1 <= ex3 + C2_PROFILE["ex1_vs_ex3_max_gap"]):
                
                res_file = results_root / date_str / f"{prefix}.html"
                result_data = None
                if res_file.exists():
                    with res_file.open("r", encoding="utf-8") as f: html_res = f.read()
                    result_data = parse_result(html_res, date_str, stadium_code, race_no, "", "")

                matches.append({
                    "date": date_str,
                    "stadium": STADIUMS.get(stadium_code, stadium_code),
                    "race_no": race_no,
                    "st_gap": round(st_gap, 3),
                    "trifecta_combo": result_data.get("trifecta_combo") if result_data else "N/A",
                    "trifecta_payout": result_data.get("trifecta_payout") if result_data else 0,
                })

    if not matches:
        print("No C2 matches found.")
        return

    total_races = len(matches)
    total_investment = total_races * 24 * 100
    total_payout = 0
    hit_count = 0

    print(f"\n--- C2 Strategy Monitor Result ({date_list[0]} - {date_list[-1]}) ---")
    header = f"{'Date':<10} {'Stadium':<10} {'R#':<3} {'STGap':<6} {'Combo':<10} {'Payout':<10}"
    print(header); print("-" * len(header))

    for m in matches:
        combo = m["trifecta_combo"]
        payout = int(m["trifecta_payout"]) if m["trifecta_payout"] else 0
        is_hit = False
        if combo:
            clean_combo = combo.replace(" ", "")
            if clean_combo.startswith("2-") or clean_combo.startswith("3-"):
                is_hit = True; hit_count += 1; total_payout += payout
        row_payout = payout if is_hit else 0
        print(f"{m['date']:<10} {m['stadium']:<10} {m['race_no']:<3} {m['st_gap']:<6} {combo:<10} {row_payout:<10,}")

    roi = (total_payout / total_investment * 100) if total_investment > 0 else 0
    print(f"\nStats: {hit_count}/{total_races} hits, ROI: {roi:.2f}%, Payout: {total_payout:,} yen")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Number of days to scan back from today")
    args = parser.parse_args()
    monitor_c2(args.days)
