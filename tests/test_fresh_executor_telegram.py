from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRESH_AUTO_SYSTEM_ROOT = ROOT / "live_trigger_fresh_exec" / "auto_system"

for module_name in [name for name in list(sys.modules) if name == "app" or name.startswith("app.")]:
    sys.modules.pop(module_name, None)

for import_root in (ROOT, FRESH_AUTO_SYSTEM_ROOT):
    import_text = str(import_root)
    while import_text in sys.path:
        sys.path.remove(import_text)
    sys.path.insert(0, import_text)

from app.core.fresh_executor import FreshTeleboatExecutor


def test_consume_telegram_assist_action_accepts_once_and_clears_markup(monkeypatch, tmp_path: Path) -> None:
    executor = FreshTeleboatExecutor(
        data_dir=tmp_path,
        settings={
            "telegram_enabled": True,
            "telegram_bot_token": "token-123",
            "telegram_chat_id": "6170007244",
        },
    )

    calls: list[tuple[str, dict[str, object]]] = []

    def fake_request(self, method: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((method, payload))
        if method == "getUpdates":
            return {
                "ok": True,
                "result": [
                    {
                        "update_id": 101,
                        "callback_query": {
                            "id": "cb-1",
                            "from": {"username": "masa_masao"},
                            "message": {
                                "message_id": 9,
                                "chat": {"id": 6170007244},
                            },
                            "data": "approve:202603240512",
                        },
                    }
                ],
            }
        return {"ok": True, "result": True}

    monkeypatch.setattr(FreshTeleboatExecutor, "_telegram_request", fake_request)

    action = executor._consume_telegram_assist_action(race_id="202603240512")

    assert action is not None
    assert action["action"] == "approve"
    assert action["username"] == "masa_masao"
    state = json.loads((tmp_path / "telegram_state.json").read_text(encoding="utf-8"))
    assert state["last_update_id"] == 101
    assert calls == [
        ("getUpdates", {}),
        (
            "answerCallbackQuery",
            {
                "callback_query_id": "cb-1",
                "text": "承認を受け付けました。",
                "show_alert": False,
            },
        ),
        (
            "editMessageReplyMarkup",
            {
                "chat_id": 6170007244,
                "message_id": 9,
                "reply_markup": {"inline_keyboard": []},
            },
        ),
    ]
