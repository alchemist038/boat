from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AirBetAudit, BetExecution, BetIntent, ExecutionEvent, SessionEvent, SessionLocal, TargetRace
from app.core.settings import (
    execution_mode,
    load_settings,
    profile_amount,
    profile_enabled,
    save_settings,
    bootstrap_runtime_path,
)

bootstrap_runtime_path()

from boat_race_data.live_trigger import load_trigger_profiles

SYSTEM_ROOT = Path(__file__).resolve().parent
MODULES = [
    "app/modules/01_sync_watchlists.py",
    "app/modules/02_evaluate_targets.py",
    "app/modules/03_execute_air_bets.py",
]

EXECUTION_MODE_LABELS = {
    "air": "Air Bet 監査",
    "assist_real": "Assist Real",
    "armed_real": "Armed Real",
}

st.set_page_config(page_title="Auto Bet Control", layout="wide")


def _run_single_cycle() -> None:
    for module in MODULES:
        subprocess.run([sys.executable, "-u", module], check=True, cwd=SYSTEM_ROOT)


def _profile_rows(settings: dict[str, object]) -> list[dict[str, object]]:
    profiles = load_trigger_profiles(SYSTEM_ROOT.parent / "boxes", include_disabled=True)
    rows: list[dict[str, object]] = []
    for profile in profiles:
        rows.append(
            {
                "profile_id": profile.profile_id,
                "display_name": profile.display_name,
                "box_id": profile.box_id,
                "enabled": profile_enabled(settings, profile.profile_id),
                "amount": profile_amount(settings, profile.profile_id),
            }
        )
    return rows


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
                    "ID": target.id,
                    "日付": target.race_date,
                    "場": target.stadium_name or target.stadium_code,
                    "R": target.race_no,
                    "PROFILE": target.profile_id,
                    "締切": target.deadline_at,
                    "状態": target.status,
                    "row_status": target.row_status,
                    "監視開始": target.monitoring_started_at,
                    "beforeinfo確認": target.beforeinfo_checked_at,
                    "GO判定": target.go_decided_at,
                    "Air Bet記録": target.air_bet_executed_at,
                    "理由": target.last_reason,
                }
                for target in targets
            ]
        )

        intent_df = pd.DataFrame(
            [
                {
                    "ID": intent.id,
                    "target_id": intent.target_race_id,
                    "PROFILE": intent.target.profile_id if intent.target else "",
                    "券種": intent.bet_type,
                    "組番": intent.combo,
                    "金額": intent.amount,
                    "mode": intent.execution_mode,
                    "状態": intent.status,
                    "作成時刻": intent.created_at,
                }
                for intent in intents
            ]
        )

        execution_df = pd.DataFrame(
            [
                {
                    "ID": execution.id,
                    "target_id": execution.target_race_id,
                    "intent_id": execution.intent_id,
                    "mode": execution.execution_mode,
                    "状態": execution.execution_status,
                    "実行時刻": execution.executed_at,
                    "締切何秒前": execution.seconds_before_deadline,
                    "契約番号": execution.contract_no,
                    "スクリーンショット": execution.screenshot_path,
                    "error": execution.error_message,
                }
                for execution in executions
            ]
        )

        audit_df = pd.DataFrame(
            [
                {
                    "ID": audit.id,
                    "日付": audit.race_date,
                    "場": audit.stadium_name or audit.stadium_code,
                    "R": audit.race_no,
                    "PROFILE": audit.profile_id,
                    "券種": audit.bet_type,
                    "組番": audit.combo,
                    "金額": audit.amount,
                    "締切": audit.deadline_at,
                    "Air Bet時刻": audit.air_bet_at,
                    "締切何秒前": audit.seconds_before_deadline,
                    "状態": audit.execution_status,
                    "理由": audit.reason,
                }
                for audit in audits
            ]
        )

        event_df = pd.DataFrame(
            [
                {
                    "時刻": event.event_at,
                    "event": event.event_type,
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
                    "時刻": event.event_at,
                    "event": event.event_type,
                    "message": event.message,
                }
                for event in session_events
            ]
        )
        return target_df, intent_df, execution_df, audit_df, event_df, session_event_df
    finally:
        session.close()


def main() -> None:
    st.title("Auto Bet Control")
    st.caption("締切 5〜10 分前の判定フローから Air Bet 監査と実ベット実行を切り替える当日運用 UI")

    settings = load_settings()
    profile_rows = _profile_rows(settings)

    with st.sidebar:
        st.header("Control")
        running = bool(settings.get("system_running", False))
        st.write(f"現在状態: {'稼働中' if running else '停止中'}")
        st.write(f"実行モード: {EXECUTION_MODE_LABELS.get(execution_mode(settings), execution_mode(settings))}")

        if running:
            if st.button("システム停止"):
                settings["system_running"] = False
                save_settings(settings)
                st.rerun()
        else:
            if st.button("システム起動"):
                settings["system_running"] = True
                save_settings(settings)
                log_path = SYSTEM_ROOT / "data" / "auto_run.log"
                with log_path.open("a", encoding="utf-8") as handle:
                    subprocess.Popen(
                        [sys.executable, "-u", "auto_run.py"],
                        cwd=SYSTEM_ROOT,
                        stdout=handle,
                        stderr=handle,
                    )
                st.rerun()

        if st.button("1サイクルだけ実行"):
            _run_single_cycle()
            st.rerun()

        st.divider()
        st.subheader("実行設定")
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
            "監視開始(締切何分前)",
            min_value=1,
            max_value=60,
            value=int(settings["check_window_start_minutes"]),
            step=1,
        )
        settings["check_window_end_minutes"] = st.number_input(
            "監視終了(締切何分前)",
            min_value=0,
            max_value=59,
            value=int(settings["check_window_end_minutes"]),
            step=1,
        )
        settings["default_bet_amount"] = st.number_input(
            "既定金額",
            min_value=0,
            max_value=100000,
            value=int(settings["default_bet_amount"]),
            step=100,
        )

        if mode != "air":
            settings["real_headless"] = st.checkbox(
                "Playwright を headless で起動する",
                value=bool(settings.get("real_headless", False)),
            )
            settings["teleboat_user_data_dir"] = st.text_input(
                "Teleboat user data dir",
                value=str(settings.get("teleboat_user_data_dir", SYSTEM_ROOT / "data" / "playwright_user_data")),
            )
            settings["manual_action_timeout_seconds"] = st.number_input(
                "手動確認待ち秒数",
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

            if mode == "assist_real":
                st.warning("Assist Real は確認画面まで自動で進みます。手動送信を検知した場合のみ成立として記録します。")
            if mode == "armed_real":
                st.error("Armed Real は Teleboat へ自動送信します。環境変数と user data dir を必ず確認してください。")

        st.divider()
        st.subheader("Profiles")
        active_profiles = dict(settings.get("active_profiles", {}))
        profile_amounts = dict(settings.get("profile_amounts", {}))
        for row in profile_rows:
            pid = str(row["profile_id"])
            active_profiles[pid] = st.checkbox(
                f"{row['display_name']} ({pid})",
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

    target_df, intent_df, execution_df, audit_df, event_df, session_event_df = _collect_frames()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_targets = target_df[target_df["日付"] == today_str] if not target_df.empty else pd.DataFrame()
    today_executions = (
        execution_df[pd.to_datetime(execution_df["実行時刻"]).dt.strftime("%Y-%m-%d") == today_str]
        if not execution_df.empty
        else pd.DataFrame()
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("本日対象", int(len(today_targets)))
    metric_cols[1].metric(
        "GO済み",
        int((today_targets["状態"] == "intent_created").sum() if not today_targets.empty else 0),
    )
    metric_cols[2].metric(
        "Air Bet記録",
        int((today_targets["状態"] == "air_bet_logged").sum() if not today_targets.empty else 0),
    )
    metric_cols[3].metric(
        "Real Bet成立",
        int((today_executions["状態"] == "submitted").sum() if not today_executions.empty else 0),
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["当日対象", "ベット実行ログ", "Air Bet監査ログ", "イベント", "Session"]
    )

    with tab1:
        st.subheader("当日ターゲット")
        if target_df.empty:
            st.info("まだターゲットはありません。")
        else:
            st.dataframe(target_df, use_container_width=True, hide_index=True)

        st.subheader("Bet Intents")
        if intent_df.empty:
            st.info("まだ intent はありません。")
        else:
            st.dataframe(intent_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("ベット実行ログ")
        if execution_df.empty:
            st.info("まだ実行ログはありません。")
        else:
            st.dataframe(execution_df, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Air Bet 実行時刻ログ")
        if audit_df.empty:
            st.info("まだ Air Bet 実行ログはありません。")
        else:
            st.dataframe(audit_df, use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Execution Events")
        if event_df.empty:
            st.info("まだイベントはありません。")
        else:
            st.dataframe(event_df, use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("Teleboat Session Events")
        if session_event_df.empty:
            st.info("まだ session event はありません。")
        else:
            st.dataframe(session_event_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
