import os
import sys
from pathlib import Path
import csv

# Add src to sys.path
sys.path.append(str(Path(r"C:\CODEX_WORK\boat_clone\src")))

from boat_race_data.live_trigger import record_air_bets

def test_logging():
    tmp_ready = Path("test_ready.csv")
    tmp_log = Path("test_air_bet_log.csv")
    
    if tmp_log.exists():
        tmp_log.unlink()

    # Create dummy ready.csv
    fields = ["box_id", "profile_id", "strategy_id", "race_id", "race_date", "stadium_code", "stadium_name", "race_no", "status"]
    rows = [
        {"box_id": "125", "profile_id": "p1", "strategy_id": "s1", "race_id": "20260318_12_01", "race_date": "2026-03-18", "stadium_code": "12", "stadium_name": "Suminoe", "race_no": "1", "status": "trigger_ready"},
        {"box_id": "125", "profile_id": "p1", "strategy_id": "s1", "race_id": "20260318_12_02", "race_date": "2026-03-18", "stadium_code": "12", "stadium_name": "Suminoe", "race_no": "2", "status": "filtered_out"},
    ]
    
    with tmp_ready.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print("--- First recording ---")
    count = record_air_bets(tmp_ready, tmp_log)
    print(f"Recorded: {count}")

    print("--- Second recording (duplicate check) ---")
    count2 = record_air_bets(tmp_ready, tmp_log)
    print(f"Recorded: {count2}")

    if tmp_log.exists():
        print("Log content:")
        print(tmp_log.read_text(encoding="utf-8"))
    
    # Cleanup
    tmp_ready.unlink()
    # tmp_log.unlink() # Keep for final check

if __name__ == "__main__":
    test_logging()
