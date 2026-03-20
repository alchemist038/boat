from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal, initialize_database, log_session_event
from app.core.settings import DATA_DIR
from app.core.teleboat import (
    STADIUM_CODE_TO_NAME,
    TeleboatClient,
    TeleboatConfigurationError,
    TeleboatError,
    TeleboatExecutionError,
    TeleboatInsufficientFundsError,
)


def _build_target(payload: dict[str, Any]) -> SimpleNamespace:
    stadium_code = str(payload["stadium_code"]).zfill(2)
    race_no = int(payload["race_no"])
    race_id = str(payload.get("race_id") or f"manual_{stadium_code}_{race_no:02d}")
    stadium_name = str(payload.get("stadium_name") or STADIUM_CODE_TO_NAME.get(stadium_code, stadium_code))
    return SimpleNamespace(
        stadium_code=stadium_code,
        stadium_name=stadium_name,
        race_no=race_no,
        race_id=race_id,
    )


def _build_intents(payload: dict[str, Any]) -> list[SimpleNamespace]:
    intents: list[SimpleNamespace] = []
    for index, row in enumerate(payload.get("bets") or [], start=1):
        intents.append(
            SimpleNamespace(
                id=index,
                bet_type=str(row["bet_type"]),
                combo=str(row["combo"]),
                amount=int(row["amount"]),
            )
        )
    return intents


def _result_payload(
    *,
    ok: bool,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
    screenshot_path: str | None = None,
    html_path: str | None = None,
) -> dict[str, Any]:
    payload = {
        "ok": ok,
        "status": status,
        "message": message,
        "details": details or {},
    }
    if screenshot_path:
        payload["screenshot_path"] = screenshot_path
    if html_path:
        payload["html_path"] = html_path
    return payload


def main() -> None:
    initialize_database()
    raw_input = sys.stdin.read().strip()
    payload = json.loads(raw_input or "{}")
    settings = dict(payload.get("settings") or {})
    test_mode = str(payload.get("test_mode") or "confirm_only")
    target = _build_target(payload)
    intents = _build_intents(payload)

    if not intents:
        print(
            json.dumps(
                _result_payload(
                    ok=False,
                    status="error",
                    message="手動テストの買い目がありません。",
                ),
                ensure_ascii=False,
            )
        )
        return

    session = SessionLocal()
    try:
        log_session_event(
            session,
            event_type="manual_test_started",
            message=f"{target.stadium_name} {target.race_no}R / {test_mode}",
            details={
                "stadium_code": target.stadium_code,
                "stadium_name": target.stadium_name,
                "race_no": target.race_no,
                "test_mode": test_mode,
                "bets": [
                    {"bet_type": intent.bet_type, "combo": intent.combo, "amount": intent.amount}
                    for intent in intents
                ],
            },
        )
        session.commit()

        with TeleboatClient(data_dir=DATA_DIR, settings=settings) as client:
            if test_mode == "confirm_only":
                result = client.prepare_target_confirmation(target=target, intents=intents)
                output = _result_payload(
                    ok=True,
                    status=result.execution_status,
                    message=result.message,
                    details=result.details,
                    screenshot_path=result.screenshot_path,
                    html_path=result.html_path,
                )
            elif test_mode == "confirm_prefill":
                result = client.prepare_target_confirmation_prefill(target=target, intents=intents)
                output = _result_payload(
                    ok=True,
                    status=result.execution_status,
                    message=result.message,
                    details=result.details,
                )
            elif test_mode == "submit_expect_insufficient":
                purchase_limit = client.current_purchase_limit()
                if purchase_limit is None:
                    raise TeleboatExecutionError("購入限度額を読み取れませんでした。送信テストを中止しました。")
                if purchase_limit != 0:
                    raise TeleboatExecutionError(
                        f"購入限度額が {purchase_limit} 円のため、送信テストを中止しました。"
                    )
                try:
                    result = client.place_target(target=target, intents=intents, mode="armed_real")
                except TeleboatInsufficientFundsError as exc:
                    output = _result_payload(
                        ok=True,
                        status="insufficient_funds_detected",
                        message=str(exc),
                        details={"purchase_limit": purchase_limit, **getattr(exc, "details", {})},
                        screenshot_path=getattr(exc, "screenshot_path", None),
                        html_path=getattr(exc, "html_path", None),
                    )
                else:
                    output = _result_payload(
                        ok=False,
                        status="unexpected_submitted",
                        message="想定外: 実送信が成立しました。残高を再確認してください。",
                        details={
                            "purchase_limit": purchase_limit,
                            "contract_no": result.contract_no,
                            **result.details,
                        },
                        screenshot_path=result.screenshot_path,
                        html_path=result.html_path,
                    )
            else:
                raise TeleboatExecutionError(f"未対応の手動テスト種別です: {test_mode}")

        log_session_event(
            session,
            event_type="manual_test_result",
            message=output["message"],
            details={
                "status": output["status"],
                "ok": output["ok"],
                "stadium_code": target.stadium_code,
                "race_no": target.race_no,
                "test_mode": test_mode,
                **output.get("details", {}),
            },
        )
        session.commit()
        print(json.dumps(output, ensure_ascii=False))
    except (TeleboatConfigurationError, TeleboatExecutionError, TeleboatError) as exc:
        output = _result_payload(
            ok=False,
            status="error",
            message=str(exc),
            details=getattr(exc, "details", {}),
            screenshot_path=getattr(exc, "screenshot_path", None),
            html_path=getattr(exc, "html_path", None),
        )
        log_session_event(
            session,
            event_type="manual_test_error",
            message=output["message"],
            details={
                "stadium_code": target.stadium_code,
                "race_no": target.race_no,
                "test_mode": test_mode,
                **output.get("details", {}),
            },
        )
        session.commit()
        print(json.dumps(output, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        output = _result_payload(
            ok=False,
            status="error",
            message=f"manual test crashed: {exc}",
        )
        log_session_event(
            session,
            event_type="manual_test_error",
            message=output["message"],
            details={
                "stadium_code": target.stadium_code,
                "race_no": target.race_no,
                "test_mode": test_mode,
            },
        )
        session.commit()
        print(json.dumps(output, ensure_ascii=False))
    finally:
        session.close()


if __name__ == "__main__":
    main()
