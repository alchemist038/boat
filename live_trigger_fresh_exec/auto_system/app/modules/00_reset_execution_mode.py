from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.settings import load_settings, save_settings


def main() -> None:
    settings = load_settings()
    if str(settings.get("execution_mode", "air")).strip().lower() == "air":
        print("execution_mode is already air")
        return

    settings["execution_mode"] = "air"
    save_settings(settings)
    print("execution_mode reset to air")


if __name__ == "__main__":
    main()
