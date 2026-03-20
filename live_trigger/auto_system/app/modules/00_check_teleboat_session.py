from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.settings import DATA_DIR, load_settings
from app.core.teleboat import (
    TeleboatClient,
    TeleboatConfigurationError,
    TeleboatError,
    TeleboatPreparationPending,
)


def _load_input_settings() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return load_settings()
    return dict(load_settings()) | dict(json.loads(raw))


def main() -> int:
    settings = _load_input_settings()
    setup_mode = bool(settings.get("teleboat_setup_mode", False))
    try:
        with TeleboatClient(data_dir=DATA_DIR, settings=settings) as client:
            state = client.prepare_session() if setup_mode else client.ensure_session()
        label = "Teleboat セッション準備完了" if setup_mode else "Teleboat セッション確認完了"
        print(json.dumps({"ok": True, "message": f"{label}: {state}"}, ensure_ascii=False))
        return 0
    except TeleboatPreparationPending as exc:
        print(json.dumps({"ok": True, "message": str(exc)}, ensure_ascii=False))
        return 0
    except TeleboatConfigurationError as exc:
        print(json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False))
        return 0
    except TeleboatError as exc:
        print(json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "message": f"Teleboat session check failed: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
