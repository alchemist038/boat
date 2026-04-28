from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

src_text = str(SRC_ROOT)
while src_text in sys.path:
    sys.path.remove(src_text)
sys.path.insert(0, src_text)

boat_race_data = importlib.import_module("boat_race_data")
boat_race_data_path = Path(getattr(boat_race_data, "__file__", "")).resolve()
if SRC_ROOT not in boat_race_data_path.parents:
    raise RuntimeError(f"boat_race_data did not resolve from src: {boat_race_data_path}")
