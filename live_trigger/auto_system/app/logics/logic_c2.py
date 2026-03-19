from pathlib import Path
from typing import Any, Dict, List, Optional
from .base_logic import BaseLogic

# trigger engine のインポート
from boat_race_data.live_trigger import (
    load_trigger_profiles,
    build_watchlist_row,
    compute_lane_gap,
    compute_start_gap_over_rest,
    _matches_final_filters
)
from boat_race_data.constants import get_default_live_trigger_root

class LogicC2(BaseLogic):
    logic_name: str = "c2_provisional_v1"
    display_name: str = "C2 Provisional (Delegated)"
    
    # trigger 側の BOX パス
    BOX_ROOT = Path(get_default_live_trigger_root()) / "boxes"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        # C2 box の profile のみ読み込み
        all_profiles = load_trigger_profiles(self.BOX_ROOT / "c2")
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
        
        # live_trigger engine の計算関数を利用
        lane2_gap = compute_lane_gap(live_entries, lane=1, reference_lane=2)
        lane3_gap = compute_lane_gap(live_entries, lane=1, reference_lane=3)
        start_gap = compute_start_gap_over_rest(live_entries, lane=1)

        for p in self.profiles:
            # engine の最終フィルタを呼び出し
            if _matches_final_filters(
                best_gap=None, # C2 では未使用
                lane2_gap=lane2_gap,
                lane3_gap=lane3_gap,
                start_gap=start_gap,
                profile=p
            ):
                return True
        return False

    def build_bet(self, race_info: Dict[str, Any], live_info: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        base_amount = self.config.get("bet_amount", 100)
        return [
            {"bet_type": "trifecta", "combo": "2-ALL-ALL", "amount": base_amount},
            {"bet_type": "trifecta", "combo": "3-ALL-ALL", "amount": base_amount}
        ]
