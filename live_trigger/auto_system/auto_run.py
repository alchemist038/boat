from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SYSTEM_ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = SYSTEM_ROOT / "data" / "settings.json"
MODULES = [
    "app/modules/01_pre_scheduler.py",
    "app/modules/02_just_in_time.py",
    "app/modules/03_executor.py",
]


def load_settings() -> dict[str, object]:
    if not SETTINGS_FILE.exists():
        return {"system_running": False}
    return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))


def run_modules() -> bool:
    for module in MODULES:
        if not load_settings().get("system_running", False):
            print(f"[{datetime.now()}] system_running=false のため自動実行を停止します")
            return False

        print(f"[{datetime.now()}] start: {module}")
        try:
            subprocess.run(
                [sys.executable, "-u", module],
                check=True,
                cwd=SYSTEM_ROOT,
            )
        except subprocess.CalledProcessError as exc:
            print(f"[{datetime.now()}] error: {module} -> {exc}")
    return True


def main() -> None:
    print(f"[{datetime.now()}] auto system loop started")

    while True:
        if not load_settings().get("system_running", False):
            print(f"[{datetime.now()}] system_running=false のためループを終了します")
            break

        run_modules()

        print(f"[{datetime.now()}] next cycleまで180秒待機します")
        for _ in range(180 // 5):
            time.sleep(5)
            if not load_settings().get("system_running", False):
                print(f"[{datetime.now()}] 待機中に停止指示を受けたため終了します")
                return


if __name__ == "__main__":
    main()
