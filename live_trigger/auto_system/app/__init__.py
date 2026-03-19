from __future__ import annotations

from pathlib import Path
import sys

AUTO_SYSTEM_ROOT = Path(__file__).resolve().parents[1]
LIVE_TRIGGER_ROOT = AUTO_SYSTEM_ROOT.parent
RUNTIME_ROOT = LIVE_TRIGGER_ROOT / "runtime"

for candidate in (AUTO_SYSTEM_ROOT, RUNTIME_ROOT):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)
