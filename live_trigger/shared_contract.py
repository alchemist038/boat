from __future__ import annotations

from pathlib import Path

LIVE_TRIGGER_ROOT = Path(__file__).resolve().parent
SHARED_BOX_ROOT = LIVE_TRIGGER_ROOT / "boxes"
SHARED_BETS_PATH = LIVE_TRIGGER_ROOT / "auto_system" / "app" / "core" / "bets.py"
PROJECT_RULES_FILE = LIVE_TRIGGER_ROOT / "PROJECT_RULES.md"
