from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from .settings import SHARED_BETS_PATH


def _load_shared_bets_module() -> ModuleType:
    module_name = "live_trigger_shared_bets"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, Path(SHARED_BETS_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared bets module: {SHARED_BETS_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_SHARED = _load_shared_bets_module()

bet_point_count = _SHARED.bet_point_count
bet_total_amount = _SHARED.bet_total_amount
build_bet_rows = _SHARED.build_bet_rows
