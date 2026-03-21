from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from app.core.settings import load_settings

SYSTEM_ROOT = Path(__file__).resolve().parent
MODULES = [
    "app/modules/01_sync_watchlists.py",
    "app/modules/02_evaluate_targets.py",
    "app/modules/03_execute_fresh_bets.py",
]


def run_modules() -> bool:
    for module in MODULES:
        if not load_settings().get("system_running", False):
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] system_running=false, stopping")
            return False

        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] start: {module}")
        try:
            subprocess.run([sys.executable, "-u", module], check=True, cwd=SYSTEM_ROOT)
        except subprocess.CalledProcessError as exc:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] error: {module} -> {exc}")
    return True


def main() -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] fresh auto loop started")

    while True:
        settings = load_settings()
        if not settings.get("system_running", False):
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] system_running=false, exiting loop")
            break

        run_modules()

        poll_seconds = max(5, int(settings.get("poll_seconds", 30)))
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] sleeping {poll_seconds}s until next cycle")
        remaining = poll_seconds
        while remaining > 0:
            chunk = min(5, remaining)
            time.sleep(chunk)
            remaining -= chunk
            if not load_settings().get("system_running", False):
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] stop requested while sleeping")
                return


if __name__ == "__main__":
    main()
