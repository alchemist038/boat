from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.bets import bet_point_count, bet_total_amount
from app.core.database import AirBetAudit, BetExecution, BetIntent, ExecutionEvent, SessionEvent, SessionLocal, TargetRace
from app.core.settings import (
    DATA_DIR,
    execution_mode,
    load_settings,
    profile_amount,
    profile_enabled,
    save_settings,
    bootstrap_runtime_path,
)
from app.core.teleboat import (
    SESSION_KEEP_LOGIN_DAYS,
    STADIUM_CODE_TO_NAME,
    load_teleboat_resident_state,
    load_teleboat_session_state,
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

MANUAL_TEST_MODE_LABELS = {
    "confirm_only": "確認画面まで",
    "confirm_prefill": "金額・投票パス入力まで",
    "submit_expect_insufficient": "送信して資金不足確認",
}


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


def _run_teleboat_session_probe(settings: dict[str, object], *, setup_mode: bool) -> tuple[bool, str]:
    script_path = SYSTEM_ROOT / "app" / "modules" / "00_check_teleboat_session.py"
    probe_settings = dict(settings)
    probe_settings["teleboat_setup_mode"] = setup_mode
    if setup_mode:
        probe_settings["real_headless"] = False
        probe_settings["login_timeout_seconds"] = max(
            int(probe_settings.get("login_timeout_seconds", 120)),
            int(probe_settings.get("manual_action_timeout_seconds", 180)),
        )
    completed = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        input=json.dumps(probe_settings, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=SYSTEM_ROOT,
        timeout=max(60, int(probe_settings.get("login_timeout_seconds", 120)) + 30),
        check=False,
    )
    output = (completed.stdout or "").strip().splitlines()
    if not output:
        message = (completed.stderr or "").strip() or f"Teleboat session check failed: exit={completed.returncode}"
        return False, message

    try:
        payload = json.loads(output[-1])
    except json.JSONDecodeError:
        message = output[-1]
        if completed.stderr:
            message = f"{message} / {completed.stderr.strip()}"
        return False, message

    return bool(payload.get("ok")), str(payload.get("message", "Teleboat session check failed"))


def _check_teleboat_session(settings: dict[str, object]) -> tuple[bool, str]:
    return _run_teleboat_session_probe(settings, setup_mode=False)


def _prepare_teleboat_session(settings: dict[str, object]) -> tuple[bool, str]:
    return _run_teleboat_session_probe(settings, setup_mode=True)


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


def _run_manual_teleboat_test(settings: dict[str, object], *, payload: dict[str, object]) -> dict[str, object]:
    script_path = SYSTEM_ROOT / "app" / "modules" / "04_manual_teleboat_test.py"
    request_payload = dict(payload)
    request_payload["settings"] = dict(settings)

    completed = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        input=json.dumps(request_payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=SYSTEM_ROOT,
        timeout=max(
            120,
            int(settings.get("manual_action_timeout_seconds", 180)) + 60,
        ),
        check=False,
    )
    output = (completed.stdout or "").strip().splitlines()
    if not output:
        return {
            "ok": False,
            "status": "error",
            "message": (completed.stderr or "").strip() or f"manual test failed: exit={completed.returncode}",
        }

    try:
        return json.loads(output[-1])
    except json.JSONDecodeError:
        message = output[-1]
        if completed.stderr:
            message = f"{message} / {completed.stderr.strip()}"
        return {"ok": False, "status": "error", "message": message}


def _teleboat_session_summary() -> list[str]:
    state = load_teleboat_session_state(DATA_DIR)
    resident = load_teleboat_resident_state(DATA_DIR)
    if not state:
        lines = [f"Teleboat セッション状態: 未準備 (ログイン保持は最長 {SESSION_KEEP_LOGIN_DAYS} 日想定)"]
        if resident:
            lines.append(f"常駐ブラウザ: {resident.get('status', 'unknown')} / {resident.get('debug_url', '-')}")
        return lines

    lines = [
        f"Teleboat セッション状態: {state.get('status', 'unknown')}",
        f"最終メッセージ: {state.get('message', '-')}",
    ]
    if resident:
        lines.append(f"常駐ブラウザ: {resident.get('status', 'unknown')} / {resident.get('debug_url', '-')}")
    if state.get("prepared_at"):
        lines.append(f"前回準備: {state['prepared_at']}")
    if state.get("last_verified_at"):
        lines.append(f"最終確認: {state['last_verified_at']}")
    if state.get("assumed_valid_until"):
        lines.append(f"保持想定期限: {state['assumed_valid_until']}")
    if state.get("storage_state_path"):
        lines.append(f"storage_state: {state['storage_state_path']}")
    return lines


def _render_manual_test_panel(settings: dict[str, object]) -> None:
    with st.expander("Teleboat 手動テスト", expanded=False):
        st.caption("トリガーと切り離して、確認画面到達と資金不足検知だけを試すための手動テストです。")

        if bool(settings.get("system_running", False)) and execution_mode(settings) != "air":
            st.warning("自動系が実投票モード中です。手動テスト前に `air` へ戻すか自動系を停止するのが安全です。")

        stadium_codes = sorted(STADIUM_CODE_TO_NAME.keys(), key=int)
        default_stadium_index = stadium_codes.index("01") if "01" in stadium_codes else 0

        row1 = st.columns(3)
        stadium_code = row1[0].selectbox(
            "場",
            options=stadium_codes,
            index=default_stadium_index,
            format_func=lambda code: f"{STADIUM_CODE_TO_NAME.get(code, code)} ({code})",
            key="manual_test_stadium_code",
        )
        race_no = int(
            row1[1].number_input(
                "R",
                min_value=1,
                max_value=12,
                value=12,
                step=1,
                key="manual_test_race_no",
            )
        )
        unit_amount = int(
            row1[2].number_input(
                "単価",
                min_value=100,
                max_value=10000,
                value=100,
                step=100,
                key="manual_test_unit_amount",
            )
        )

        row2 = st.columns(2)
        include_125 = row2[0].checkbox("125 を含める (1-2-5)", value=True, key="manual_test_include_125")
        include_c2 = row2[1].checkbox(
            "C2 を含める (2-ALL-ALL / 3-ALL-ALL)",
            value=True,
            key="manual_test_include_c2",
        )
        test_mode = st.selectbox(
            "テスト内容",
            options=list(MANUAL_TEST_MODE_LABELS.keys()),
            format_func=lambda item: MANUAL_TEST_MODE_LABELS[item],
            key="manual_test_mode",
        )

        bets = _build_manual_test_bets(
            include_125=include_125,
            include_c2=include_c2,
            unit_amount=unit_amount,
        )
        if not bets:
            st.info("少なくとも 1 つのロジックを選んでください。")
        else:
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
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            st.caption(f"合計見込み金額: {int(preview_df['total_amount'].sum())} 円")

        if test_mode == "confirm_prefill":
            st.info("このモードは確認画面の `購入金額` と `投票用パスワード` を入力して停止します。安全のため、スクリーンショットと HTML は保存しません。")

        if test_mode == "submit_expect_insufficient":
            st.warning("送信テストは Teleboat の購入限度額が 0 円と判定できたときだけ実行します。0 円以外なら自動中止します。")

        if st.button("手動テスト実行", disabled=not bets, key="manual_test_run"):
            payload = {
                "test_mode": test_mode,
                "stadium_code": stadium_code,
                "stadium_name": STADIUM_CODE_TO_NAME.get(stadium_code, stadium_code),
                "race_no": race_no,
                "race_id": f"manual_{datetime.now():%Y%m%d}_{stadium_code}_{race_no:02d}",
                "bets": bets,
            }
            st.session_state["manual_test_result"] = _run_manual_teleboat_test(settings, payload=payload)
            st.rerun()

        manual_result = st.session_state.get("manual_test_result")
        if manual_result:
            status = str(manual_result.get("status", "unknown"))
            message = str(manual_result.get("message", "-"))
            if bool(manual_result.get("ok")):
                st.success(f"{status}: {message}")
            else:
                st.error(f"{status}: {message}")
            details = manual_result.get("details") or {}
            if details:
                st.json(details)
            if manual_result.get("screenshot_path"):
                st.caption(f"screenshot: {manual_result['screenshot_path']}")
            if manual_result.get("html_path"):
                st.caption(f"html: {manual_result['html_path']}")


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
                    "単価": intent.amount,
                    "点数": bet_point_count(bet_type=intent.bet_type, combo=intent.combo),
                    "合計金額": bet_total_amount(
                        bet_type=intent.bet_type,
                        combo=intent.combo,
                        unit_amount=intent.amount,
                    ),
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
                    "単価": audit.amount,
                    "点数": bet_point_count(bet_type=audit.bet_type, combo=audit.combo),
                    "合計金額": bet_total_amount(
                        bet_type=audit.bet_type,
                        combo=audit.combo,
                        unit_amount=audit.amount,
                    ),
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


def _render_dashboard() -> None:
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
        settings["ui_auto_refresh"] = st.checkbox(
            "監視表示を自動更新する",
            value=bool(settings.get("ui_auto_refresh", True)),
        )
        settings["ui_refresh_seconds"] = st.number_input(
            "自動更新秒数",
            min_value=5,
            max_value=60,
            value=int(settings.get("ui_refresh_seconds", 10)),
            step=1,
            disabled=not bool(settings["ui_auto_refresh"]),
        )

        if mode != "air":
            settings["real_headless"] = st.checkbox(
                "Playwright を headless で起動する",
                value=bool(settings.get("real_headless", False)),
            )
            settings["stop_on_insufficient_funds"] = st.checkbox(
                "資金不足時は自動停止する",
                value=bool(settings.get("stop_on_insufficient_funds", True)),
            )
            settings["teleboat_resident_browser"] = st.checkbox(
                "常駐ブラウザを使う",
                value=bool(settings.get("teleboat_resident_browser", True)),
                help="Google Chrome for Testing を 1 枚立てたまま、ログイン状態のページを使い回します。",
            )
            settings["teleboat_resident_debug_port"] = st.number_input(
                "常駐ブラウザのデバッグポート",
                min_value=1024,
                max_value=65535,
                value=int(settings.get("teleboat_resident_debug_port", 9333)),
                step=1,
                disabled=not bool(settings["teleboat_resident_browser"]),
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

            if st.button("Teleboat ログイン確認"):
                ok, message = _check_teleboat_session(settings)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
            if st.button("Teleboat セッション準備"):
                st.info("常駐ブラウザを開きます。Google Chrome for Testing が開いたら、必要に応じて手動ログインを完了してください。")
                ok, message = _prepare_teleboat_session(settings)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
            for line in _teleboat_session_summary():
                st.caption(line)

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

    _render_manual_test_panel(settings)

    if bool(settings.get("ui_auto_refresh", True)):
        refresh_seconds = int(settings.get("ui_refresh_seconds", 10))
        st.caption(f"監視表示は {refresh_seconds} 秒ごとに自動更新します。")

        @st.fragment(run_every=f"{refresh_seconds}s")
        def _dashboard_fragment() -> None:
            _render_dashboard()

        _dashboard_fragment()
    else:
        _render_dashboard()


if __name__ == "__main__":
    main()
