import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(r"C:\CODEX_WORK\boat_clone\src")))

from boat_race_data.live_trigger import print_air_bet_stats

def test_print():
    dummy_stats = {
        "TOTAL": {
            "race_count": 10,
            "win_count": 2,
            "investment": 1000,
            "payout": 1500,
            "balance": 500,
            "win_rate": 20.0,
            "recovery_rate": 150.0
        },
        "125_suminoe": {
            "race_count": 5,
            "win_count": 1,
            "investment": 500,
            "payout": 800,
            "balance": 300,
            "win_rate": 20.0,
            "recovery_rate": 160.0
        }
    }
    
    print("Testing print_air_bet_stats output:")
    print_air_bet_stats(dummy_stats)

if __name__ == "__main__":
    test_print()
