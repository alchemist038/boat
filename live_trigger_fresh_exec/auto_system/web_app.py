from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

SYSTEM_ROOT = Path(__file__).resolve().parent
FRESH_ROOT = SYSTEM_ROOT.parent
for import_root in (SYSTEM_ROOT, FRESH_ROOT):
    import_text = str(import_root)
    if import_text not in sys.path:
        sys.path.append(import_text)

from app.core.bets import bet_point_count, bet_total_amount
from app.core.database import (
    AirBetAudit,
    BetExecution,
    BetIntent,
    ExecutionEvent,
    SessionEvent,
    SessionLocal,
    TargetRace,
    initialize_database,
)
from app.core.fresh_executor import STADIUM_CODE_TO_NAME
from app.core.settings import (
    AUTO_RUN_LOG_FILE,
    SHARED_BOX_ROOT,
    execution_mode,
    load_settings,
    profile_amount,
    profile_enabled,
    save_settings,
    bootstrap_runtime_path,
)

bootstrap_runtime_path()

from boat_race_data.live_trigger import load_trigger_profiles

MODULES = [
    "app/modules/01_sync_watchlists.py",
    "app/modules/02_evaluate_targets.py",
    "app/modules/03_execute_fresh_bets.py",
]

EXECUTION_MODE_LABELS = {
    "air": "Air",
    "assist_real": "アシスト実投票",
    "armed_real": "自動実投票",
}
REAL_STRATEGY_LABELS = {
    "fresh_per_execution": "毎回新規ログイン",
    "burst_reuse": "短時間だけ再利用",
}
MANUAL_TEST_MODE_LABELS = {
    "login_only": "ログインのみ",
    "confirm_only": "確認画面まで",
    "confirm_prefill": "確認画面+事前入力",
    "assist_real": "アシスト実投票",
    "armed_real": "自動実投票",
}
STATUS_VALUE_LABELS = {
    "imported": "取込済み",
    "monitoring": "監視中",
    "checked_waiting": "待機中",
    "checked_go": "GO判定",
    "intent_created": "Intent作成済み",
    "checked_skip": "見送り",
    "air_bet_logged": "Air記録済み",
    "real_bet_placed": "実投票完了",
    "expired": "期限切れ",
    "error": "エラー",
    "withdrawn": "対象除外",
    "cancelled": "取消",
    "executed": "実行済み",
    "pending": "待機",
    "submitted": "送信完了",
    "logged": "記録済み",
    "insufficient_funds": "残高不足",
    "assist_timeout": "手動待ちタイムアウト",
    "assist_window_closed": "締切通過で終了",
    "waiting_beforeinfo": "beforeinfo待ち",
    "trigger_ready": "発火準備完了",
    "filtered_out": "条件外",
    "watchlist_removed": "watchlist除外",
    "air": "Air",
    "assist_real": "アシスト実投票",
    "armed_real": "自動実投票",
}

TARGET_COLUMNS_JA = {
    "id": "ID",
    "race_date": "日付",
    "stadium": "場",
    "race_no": "R",
    "profile_id": "PROFILE",
    "deadline_at": "締切",
    "status": "状態",
    "row_status": "判定状態",
    "reason": "理由",
    "go_decided_at": "GO時刻",
    "checked_at": "確認時刻",
}
INTENT_COLUMNS_JA = {
    "id": "ID",
    "target_id": "target_id",
    "profile_id": "PROFILE",
    "bet_type": "券種",
    "combo": "組番",
    "unit_amount": "単位額",
    "points": "点数",
    "total_amount": "合計額",
    "mode": "モード",
    "status": "状態",
    "created_at": "作成時刻",
}
EXECUTION_COLUMNS_JA = {
    "id": "ID",
    "target_id": "target_id",
    "intent_id": "intent_id",
    "mode": "モード",
    "status": "実行状態",
    "executed_at": "実行時刻",
    "seconds_before_deadline": "締切前秒数",
    "contract_no": "受付番号",
    "screenshot_path": "スクリーンショット",
    "error": "エラー",
}
AUDIT_COLUMNS_JA = {
    "id": "ID",
    "race_date": "日付",
    "stadium": "場",
    "race_no": "R",
    "profile_id": "PROFILE",
    "bet_type": "券種",
    "combo": "組番",
    "unit_amount": "単位額",
    "deadline_at": "締切",
    "air_bet_at": "記録時刻",
    "seconds_before_deadline": "締切前秒数",
    "status": "状態",
    "reason": "理由",
}
EVENT_COLUMNS_JA = {
    "event_at": "時刻",
    "event_type": "イベント",
    "target_id": "target_id",
    "intent_id": "intent_id",
    "message": "内容",
}
SESSION_EVENT_COLUMNS_JA = {
    "event_at": "時刻",
    "event_type": "イベント",
    "message": "内容",
}

st.set_page_config(page_title="Fresh Auto 管理", layout="wide")


def _run_single_cycle() -> None:
    for module in MODULES:
        subprocess.run([sys.executable, "-u", module], check=True, cwd=SYSTEM_ROOT)


def _spawn_auto_loop() -> None:
    AUTO_RUN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUTO_RUN_LOG_FILE.open("a", encoding="utf-8") as handle:
        subprocess.Popen(
            [sys.executable, "-u", "auto_run.py"],
            cwd=SYSTEM_ROOT,
            stdout=handle,
            stderr=handle,
        )


def _profile_rows(settings: dict[str, object]) -> list[dict[str, object]]:
    profiles = load_trigger_profiles(SHARED_BOX_ROOT, include_disabled=True)
    rows: list[dict[str, object]] = []
    for profile in profiles:
        rows.append(
            {
                "profile_id": profile.profile_id,
                "display_name": profile.display_name,
                "box_id": profile.box_id,
                "enabled": profile_enabled(settings, profile.profile_id),
                "amount": profile_amount(settings, profile.profile_id),
                "runtime_enabled": profile.enabled,
            }
        )
    return rows


def _build_manual_test_bets(*, include_125: bool, include_c2: bool, unit_amount: int) -> list[dict[str, object]]:
    bets: list[dict[str, object]] = []
    if include_125:
        bets.append({"bet_type": "trifecta", "combo": "1-2-5", "amount": int(unit_amount), "source": "125"})
    if include_c2:
        bets.extend(
            [
                {"bet_type": "trifecta", "combo": "2-ALL-ALL", "amount": int(unit_amount), "source": "c2"},
                {"bet_type": "trifecta", "combo": "3-ALL-ALL", "amount": int(unit_amount), "source": "c2"},
            ]
        )
    return bets


def _run_manual_fresh_test(settings: dict[str, object], *, payload: dict[str, object]) -> dict[str, object]:
    script_path = SYSTEM_ROOT / "app" / "modules" / "01_manual_fresh_executor_test.py"
    request_payload = dict(payload)
    request_payload["settings"] = dict(settings)

    completed = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        input=json.dumps(request_payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=SYSTEM_ROOT,
        timeout=max(120, int(settings.get("manual_action_timeout_seconds", 180)) + 60),
        check=False,
    )
    output = (completed.stdout or "").strip().splitlines()
    if not output:
        return {
            "ok": False,
            "status": "error",
            "message": (completed.stderr or "").strip() or f"fresh manual test failed: exit={completed.returncode}",
        }

    try:
        return json.loads(output[-1])
    except json.JSONDecodeError:
        message = output[-1]
        if completed.stderr:
            message = f"{message} / {completed.stderr.strip()}"
        return {"ok": False, "status": "error", "message": message}


def _collect_frames():
    session = SessionLocal()
    try:
        targets = session.query(TargetRace).order_by(TargetRace.deadline_at.desc(), TargetRace.id.desc()).all()
        intents = session.query(BetIntent).order_by(BetIntent.created_at.desc(), BetIntent.id.desc()).all()
        executions = session.query(BetExecution).order_by(BetExecution.executed_at.desc(), BetExecution.id.desc()).all()
        audits = session.query(AirBetAudit).order_by(AirBetAudit.air_bet_at.desc(), AirBetAudit.id.desc()).all()
        events = (
            session.query(ExecutionEvent)
            .order_by(ExecutionEvent.event_at.desc(), ExecutionEvent.id.desc())
            .limit(300)
            .all()
        )
        session_events = (
            session.query(SessionEvent)
            .order_by(SessionEvent.event_at.desc(), SessionEvent.id.desc())
            .limit(200)
            .all()
        )

        target_df = pd.DataFrame(
            [
                {
                    "id": target.id,
                    "race_date": target.race_date,
                    "stadium": target.stadium_name or target.stadium_code,
                    "race_no": target.race_no,
                    "profile_id": target.profile_id,
                    "deadline_at": target.deadline_at,
                    "status": target.status,
                    "row_status": target.row_status,
                    "reason": target.last_reason,
                    "go_decided_at": target.go_decided_at,
                    "checked_at": target.beforeinfo_checked_at,
                }
                for target in targets
            ]
        )
        intent_df = pd.DataFrame(
            [
                {
                    "id": intent.id,
                    "target_id": intent.target_race_id,
                    "profile_id": intent.target.profile_id if intent.target else "",
                    "bet_type": intent.bet_type,
                    "combo": intent.combo,
                    "unit_amount": intent.amount,
                    "points": bet_point_count(bet_type=intent.bet_type, combo=intent.combo),
                    "total_amount": bet_total_amount(
                        bet_type=intent.bet_type,
                        combo=intent.combo,
                        unit_amount=intent.amount,
                    ),
                    "mode": intent.execution_mode,
                    "status": intent.status,
                    "created_at": intent.created_at,
                }
                for intent in intents
            ]
        )
        execution_df = pd.DataFrame(
            [
                {
                    "id": execution.id,
                    "target_id": execution.target_race_id,
                    "intent_id": execution.intent_id,
                    "mode": execution.execution_mode,
                    "status": execution.execution_status,
                    "executed_at": execution.executed_at,
                    "seconds_before_deadline": execution.seconds_before_deadline,
                    "contract_no": execution.contract_no,
                    "screenshot_path": execution.screenshot_path,
                    "error": execution.error_message,
                }
                for execution in executions
            ]
        )
        audit_df = pd.DataFrame(
            [
                {
                    "id": audit.id,
                    "race_date": audit.race_date,
                    "stadium": audit.stadium_name or audit.stadium_code,
                    "race_no": audit.race_no,
                    "profile_id": audit.profile_id,
                    "bet_type": audit.bet_type,
                    "combo": audit.combo,
                    "unit_amount": audit.amount,
                    "deadline_at": audit.deadline_at,
                    "air_bet_at": audit.air_bet_at,
                    "seconds_before_deadline": audit.seconds_before_deadline,
                    "status": audit.execution_status,
                    "reason": audit.reason,
                }
                for audit in audits
            ]
        )
        event_df = pd.DataFrame(
            [
                {
                    "event_at": event.event_at,
                    "event_type": event.event_type,
                    "target_id": event.target_race_id,
                    "intent_id": event.intent_id,
                    "message": event.message,
                }
                for event in events
            ]
        )
        session_event_df = pd.DataFrame(
            [
                {
                    "event_at": event.event_at,
                    "event_type": event.event_type,
                    "message": event.message,
                }
                for event in session_events
            ]
        )
        return target_df, intent_df, execution_df, audit_df, event_df, session_event_df
    finally:
        session.close()


def _log_tail(lines: int = 40) -> str:
    if not AUTO_RUN_LOG_FILE.exists():
        return ""
    content = AUTO_RUN_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(content[-lines:])


def _rename_columns(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    columns = [column for column in mapping if column in frame.columns]
    if not columns:
        return frame
    return frame.loc[:, columns].rename(columns={column: mapping[column] for column in columns})


def _localize_values(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    localized = frame.copy()
    for column in ("status", "row_status", "mode"):
        if column in localized.columns:
            localized[column] = localized[column].map(lambda value: STATUS_VALUE_LABELS.get(str(value), value))
    return localized


def _style_target_row(row: pd.Series) -> list[str]:
    status = str(row.get("status", ""))
    row_status = str(row.get("row_status", ""))

    if status in {"imported", "monitoring", "checked_waiting"} and row_status in {"", "waiting_beforeinfo"}:
        return [""] * len(row)

    if status in {"checked_go", "intent_created"} or row_status == "trigger_ready":
        return ["background-color: #dfe7dc; color: #2e3b2e;"] * len(row)

    return ["background-color: #e3e3e3; color: #666666;"] * len(row)


def _render_today_target_table(today_targets: pd.DataFrame) -> None:
    if today_targets.empty:
        st.info("本日の対象はまだありません。")
        return

    ordered = today_targets.sort_values(["deadline_at", "id"], ascending=[True, True]).copy()
    display_df = _rename_columns(_localize_values(ordered), TARGET_COLUMNS_JA)
    styler = display_df.style.apply(_style_target_row, axis=1)
    st.caption("本日分のみ表示しています。判定前は通常表示、判定後は色を落として表示します。")
    st.dataframe(styler, use_container_width=True, hide_index=True)


def _render_manual_test_panel(settings: dict[str, object]) -> None:
    with st.expander("手動 Fresh テスト", expanded=False):
        row1 = st.columns(4)
        test_mode = row1[0].selectbox(
            "テスト内容",
            options=list(MANUAL_TEST_MODE_LABELS.keys()),
            format_func=lambda item: MANUAL_TEST_MODE_LABELS[item],
            key="fresh_manual_test_mode",
        )
        stadium_codes = sorted(STADIUM_CODE_TO_NAME.keys(), key=int)
        default_stadium_index = stadium_codes.index("14") if "14" in stadium_codes else 0
        stadium_code = row1[1].selectbox(
            "場",
            options=stadium_codes,
            index=default_stadium_index,
            format_func=lambda code: f"{STADIUM_CODE_TO_NAME.get(code, code)} ({code})",
            key="fresh_manual_stadium_code",
        )
        race_no = int(
            row1[2].number_input(
                "R",
                min_value=1,
                max_value=12,
                value=12,
                step=1,
                key="fresh_manual_race_no",
            )
        )
        unit_amount = int(
            row1[3].number_input(
                "単位額",
                min_value=100,
                max_value=10000,
                value=100,
                step=100,
                key="fresh_manual_unit_amount",
            )
        )

        row2 = st.columns(4)
        include_125 = row2[0].checkbox("125 を含む", value=True, key="fresh_manual_include_125")
        include_c2 = row2[1].checkbox("C2 を含む", value=True, key="fresh_manual_include_c2")
        cleanup_after_test = row2[2].checkbox("テスト後に後始末", value=False, key="fresh_manual_cleanup")
        hold_open_seconds = int(
            row2[3].number_input(
                "保持秒数",
                min_value=0,
                max_value=600,
                value=0,
                step=10,
                key="fresh_manual_hold_open_seconds",
            )
        )

        bets = [] if test_mode == "login_only" else _build_manual_test_bets(
            include_125=include_125,
            include_c2=include_c2,
            unit_amount=unit_amount,
        )

        if bets:
            preview_df = pd.DataFrame(
                [
                    {
                        "source": row["source"],
                        "bet_type": row["bet_type"],
                        "combo": row["combo"],
                        "unit_amount": row["amount"],
                        "points": bet_point_count(bet_type=str(row["bet_type"]), combo=str(row["combo"])),
                        "total_amount": bet_total_amount(
                            bet_type=str(row["bet_type"]),
                            combo=str(row["combo"]),
                            unit_amount=int(row["amount"]),
                        ),
                    }
                    for row in bets
                ]
            )
            st.dataframe(
                preview_df.rename(
                    columns={
                        "source": "元ロジック",
                        "bet_type": "券種",
                        "combo": "組番",
                        "unit_amount": "単位額",
                        "points": "点数",
                        "total_amount": "合計額",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        run_disabled = test_mode != "login_only" and not bets
        if st.button("手動 Fresh テスト実行", disabled=run_disabled, key="fresh_manual_run"):
            payload: dict[str, object] = {
                "test_mode": test_mode,
                "cleanup_after_test": cleanup_after_test,
                "hold_open_seconds": hold_open_seconds,
            }
            if test_mode != "login_only":
                payload.update(
                    {
                        "stadium_code": stadium_code,
                        "stadium_name": STADIUM_CODE_TO_NAME.get(stadium_code, stadium_code),
                        "race_no": race_no,
                        "race_id": f"fresh_manual_{datetime.now():%Y%m%d}_{stadium_code}_{race_no:02d}",
                        "bets": bets,
                    }
                )
            st.session_state["fresh_manual_test_result"] = _run_manual_fresh_test(settings, payload=payload)
            st.rerun()

        result = st.session_state.get("fresh_manual_test_result")
        if result:
            status = str(result.get("status", "unknown"))
            message = str(result.get("message", "-"))
            if bool(result.get("ok")):
                st.success(f"{status}: {message}")
            else:
                st.error(f"{status}: {message}")
            details = result.get("details") or {}
            if details:
                st.json(details)
            if result.get("screenshot_path"):
                st.caption(f"screenshot: {result['screenshot_path']}")
            if result.get("html_path"):
                st.caption(f"html: {result['html_path']}")


def _render_dashboard() -> None:
    target_df, intent_df, execution_df, audit_df, event_df, session_event_df = _collect_frames()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_targets = target_df[target_df["race_date"] == today_str] if not target_df.empty else pd.DataFrame()
    today_executions = (
        execution_df[pd.to_datetime(execution_df["executed_at"]).dt.strftime("%Y-%m-%d") == today_str]
        if not execution_df.empty
        else pd.DataFrame()
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("本日対象", int(len(today_targets)))
    metric_cols[1].metric(
        "GO",
        int((today_targets["status"] == "intent_created").sum() if not today_targets.empty else 0),
    )
    metric_cols[2].metric(
        "Air 記録済み",
        int((today_targets["status"] == "air_bet_logged").sum() if not today_targets.empty else 0),
    )
    metric_cols[3].metric(
        "実投票完了",
        int((today_executions["status"] == "submitted").sum() if not today_executions.empty else 0),
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["対象", "Intent", "実行", "Air 監査", "イベント", "ログ"]
    )
    with tab1:
        _render_today_target_table(today_targets)
    with tab2:
        st.dataframe(
            _rename_columns(_localize_values(intent_df), INTENT_COLUMNS_JA),
            use_container_width=True,
            hide_index=True,
        )
    with tab3:
        st.dataframe(
            _rename_columns(_localize_values(execution_df), EXECUTION_COLUMNS_JA),
            use_container_width=True,
            hide_index=True,
        )
    with tab4:
        st.dataframe(
            _rename_columns(_localize_values(audit_df), AUDIT_COLUMNS_JA),
            use_container_width=True,
            hide_index=True,
        )
    with tab5:
        st.dataframe(_rename_columns(event_df, EVENT_COLUMNS_JA), use_container_width=True, hide_index=True)
        st.dataframe(
            _rename_columns(session_event_df, SESSION_EVENT_COLUMNS_JA),
            use_container_width=True,
            hide_index=True,
        )
    with tab6:
        st.code(_log_tail() or "まだ auto_run ログはありません。", language="text")


def main() -> None:
    initialize_database()
    st.title("Fresh Auto 管理")
    st.caption("共有 watchlist / raw / BOX を使い、実投票だけ Fresh ログインで動かすラインです。")
    st.info(
        "このラインは trigger 側の watchlist を共有して読みます。"
        "当日候補の元データは `live_trigger/watchlists/`、beforeinfo の取得は評価時に自動で行います。"
    )

    settings = load_settings()
    profile_rows = _profile_rows(settings)

    with st.sidebar:
        st.header("制御")
        running = bool(settings.get("system_running", False))
        st.write(f"状態: {'稼働中' if running else '停止中'}")
        st.write(f"モード: {EXECUTION_MODE_LABELS.get(execution_mode(settings), execution_mode(settings))}")

        if running:
            if st.button("システム停止"):
                settings["system_running"] = False
                save_settings(settings)
                st.rerun()
        else:
            if st.button("システム起動"):
                settings["system_running"] = True
                save_settings(settings)
                _spawn_auto_loop()
                st.rerun()

        if st.button("1サイクル実行"):
            _run_single_cycle()
            st.rerun()

        st.divider()
        st.subheader("設定")
        mode = st.selectbox(
            "実行モード",
            options=list(EXECUTION_MODE_LABELS.keys()),
            format_func=lambda item: EXECUTION_MODE_LABELS[item],
            index=list(EXECUTION_MODE_LABELS.keys()).index(execution_mode(settings)),
        )
        settings["execution_mode"] = mode
        settings["poll_seconds"] = st.number_input(
            "ポーリング秒数",
            min_value=5,
            max_value=300,
            value=int(settings["poll_seconds"]),
            step=5,
        )
        settings["check_window_start_minutes"] = st.number_input(
            "監視開始分",
            min_value=1,
            max_value=60,
            value=int(settings["check_window_start_minutes"]),
            step=1,
        )
        settings["check_window_end_minutes"] = st.number_input(
            "監視終了分",
            min_value=0,
            max_value=59,
            value=int(settings["check_window_end_minutes"]),
            step=1,
        )
        settings["default_bet_amount"] = st.number_input(
            "既定単位額",
            min_value=0,
            max_value=100000,
            value=int(settings["default_bet_amount"]),
            step=100,
        )
        settings["ui_auto_refresh"] = st.checkbox(
            "自動更新",
            value=bool(settings.get("ui_auto_refresh", True)),
        )
        settings["ui_refresh_seconds"] = st.number_input(
            "更新秒数",
            min_value=5,
            max_value=60,
            value=int(settings.get("ui_refresh_seconds", 10)),
            step=1,
            disabled=not bool(settings["ui_auto_refresh"]),
        )

        if mode != "air":
            settings["real_headless"] = st.checkbox(
                "ヘッドレス",
                value=bool(settings.get("real_headless", False)),
            )
            settings["stop_on_insufficient_funds"] = st.checkbox(
                "残高不足で停止",
                value=bool(settings.get("stop_on_insufficient_funds", True)),
            )
            settings["manual_action_timeout_seconds"] = st.number_input(
                "手動待ち秒数",
                min_value=30,
                max_value=900,
                value=int(settings.get("manual_action_timeout_seconds", 180)),
                step=30,
            )
            settings["login_timeout_seconds"] = st.number_input(
                "ログイン待ち秒数",
                min_value=30,
                max_value=300,
                value=int(settings.get("login_timeout_seconds", 120)),
                step=10,
            )
            settings["real_session_strategy"] = st.selectbox(
                "セッション方針",
                options=list(REAL_STRATEGY_LABELS.keys()),
                format_func=lambda item: REAL_STRATEGY_LABELS[item],
                index=list(REAL_STRATEGY_LABELS.keys()).index(
                    str(settings.get("real_session_strategy", "fresh_per_execution"))
                ),
            )
            settings["reuse_when_next_real_within_seconds"] = st.number_input(
                "再利用閾値秒数",
                min_value=0,
                max_value=600,
                value=int(settings.get("reuse_when_next_real_within_seconds", 180)),
                step=10,
            )
            settings["post_login_settle_seconds"] = st.number_input(
                "ログイン後安定待ち秒数",
                min_value=1,
                max_value=60,
                value=int(settings.get("post_login_settle_seconds", 10)),
                step=1,
            )
            settings["top_stable_confirm_seconds"] = st.number_input(
                "トップ安定確認秒数",
                min_value=1,
                max_value=30,
                value=int(settings.get("top_stable_confirm_seconds", 3)),
                step=1,
            )
            settings["logout_after_execution"] = st.checkbox(
                "実行後ログアウト",
                value=bool(settings.get("logout_after_execution", True)),
            )
            settings["close_browser_after_execution"] = st.checkbox(
                "実行後ブラウザ終了",
                value=bool(settings.get("close_browser_after_execution", True)),
            )

        st.divider()
        st.subheader("プロファイル")
        active_profiles = dict(settings.get("active_profiles", {}))
        profile_amounts = dict(settings.get("profile_amounts", {}))
        for row in profile_rows:
            pid = str(row["profile_id"])
            label = f"{row['display_name']} ({pid})"
            if not row["runtime_enabled"]:
                label = f"{label} [runtime無効]"
            active_profiles[pid] = st.checkbox(
                label,
                value=bool(profile_enabled(settings, pid)),
                key=f"active_{pid}",
            )
            profile_amounts[pid] = st.number_input(
                f"金額 / {pid}",
                min_value=0,
                max_value=100000,
                value=int(profile_amount(settings, pid)),
                step=100,
                key=f"amount_{pid}",
            )
        settings["active_profiles"] = active_profiles
        settings["profile_amounts"] = profile_amounts

        if st.button("設定を保存"):
            save_settings(settings)
            st.success("保存しました")
            st.rerun()

    _render_manual_test_panel(settings)

    if bool(settings.get("ui_auto_refresh", True)):
        refresh_seconds = int(settings.get("ui_refresh_seconds", 10))
        st.caption(f"画面は {refresh_seconds} 秒ごとに自動更新します。")

        @st.fragment(run_every=f"{refresh_seconds}s")
        def _dashboard_fragment() -> None:
            _render_dashboard()

        _dashboard_fragment()
    else:
        _render_dashboard()


if __name__ == "__main__":
    main()
