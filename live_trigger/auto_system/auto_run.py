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
    "app/modules/03_execute_air_bets.py",
]


def run_modules() -> bool:
    for module in MODULES:
        if not load_settings().get("system_running", False):
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] system_running=false のため停止します")
            return False

        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] start: {module}")
        try:
            subprocess.run([sys.executable, "-u", module], check=True, cwd=SYSTEM_ROOT)
        except subprocess.CalledProcessError as exc:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] error: {module} -> {exc}")
    return True


def main() -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] auto system loop started")

    while True:
        settings = load_settings()
        if not settings.get("system_running", False):
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] system_running=false のためループを終了します")
            break

        run_modules()

        poll_seconds = max(5, int(settings.get("poll_seconds", 30)))
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 次サイクルまで {poll_seconds} 秒待機します")
        remaining = poll_seconds
        while remaining > 0:
            chunk = min(5, remaining)
            time.sleep(chunk)
            remaining -= chunk
            if not load_settings().get("system_running", False):
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 待機中に停止指示を検知したため終了します")
                return


if __name__ == "__main__":
    main()
