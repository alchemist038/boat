from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseLogic(ABC):
    logic_name: str = "base"
    display_name: str = "Base Logic"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    @abstractmethod
    def pre_check(self, race_info: Dict[str, Any]) -> bool:
        """出走表ベースの事前抽出 (dictを受け取りboolを返す)"""
        raise NotImplementedError

    @abstractmethod
    def just_in_time_check(self, race_info: Dict[str, Any], live_info: Dict[str, Any]) -> bool:
        """直前情報を使った最終判定 (dictを受け取りboolを返す)"""
        raise NotImplementedError

    @abstractmethod
    def build_bet(self, race_info: Dict[str, Any], live_info: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """買い目リストの生成"""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, str]:
        return {
            "logic_name": self.logic_name,
            "display_name": self.display_name,
        }
