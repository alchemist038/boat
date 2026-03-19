from pathlib import Path
from typing import Any, Dict, List, Optional
from .base_logic import BaseLogic

# trigger engine のインポート (パス調整が必要な場合を想定)
from boat_race_data.live_trigger import (
    load_trigger_profiles,
    build_watchlist_row,
    compute_best_gap,
    _matches_final_filters # 内部関数だがロジック共有のため使用
)
from boat_race_data.constants import get_default_live_trigger_root

class Logic125(BaseLogic):
    logic_name: str = "125_line_provisional"
    display_name: str = "125 Line (Delegated)"
    
    # trigger 側の BOX パス
    BOX_ROOT = Path(get_default_live_trigger_root()) / "boxes"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        # 125 box の profile のみ読み込み
        all_profiles = load_trigger_profiles(self.BOX_ROOT / "125")
        self.profiles = [p for p in all_profiles if p.enabled]

    def pre_check(self, race_info: Dict[str, Any]) -> bool:
        entry_rows = race_info.get("entries", [])
        if not entry_rows: return False
        
        for p in self.profiles:
            # engine の事前フィルタを呼び出し
            if build_watchlist_row(race_info, entry_rows, p) is not None:
                return True
        return False

    def just_in_time_check(self, race_info: Dict[str, Any], live_info: Dict[str, Any]) -> bool:
        live_entries = live_info.get("entries", [])
        if not live_entries: return False
        
        # exhibition データのパース済み dict 形式を想定
        # live_trigger engine の計算関数を利用
        best_gap = compute_best_gap(live_entries, lane=1)
        
        for p in self.profiles:
            # engine の最終フィルタ（展示タイム差等）を呼び出し
            if _matches_final_filters(
                best_gap=best_gap,
                lane2_gap=None, # 125 では未使用
                lane3_gap=None, # 125 では未使用
                start_gap=None, # 125 では未使用
                profile=p
            ):
                return True
        return False

    def build_bet(self, race_info: Dict[str, Any], live_info: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        base_amount = self.config.get("bet_amount", 100)
        return [{"bet_type": "trifecta", "combo": "1-2-5", "amount": base_amount}]
