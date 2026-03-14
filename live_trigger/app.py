from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import traceback

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html
from streamlit.runtime.scriptrunner import get_script_run_ctx

from boat_race_data.live_trigger import (
    build_watchlist_for_profiles,
    load_trigger_profiles,
    read_watchlist,
    resolve_watchlist_for_profiles,
)
from boat_race_data.logic_board import build_logic_board

APP_ROOT = Path(__file__).resolve().parent
PROFILE_ROOT = APP_ROOT / "boxes"
PLANS_ROOT = APP_ROOT / "plans"
RAW_ROOT = APP_ROOT / "raw"
WATCHLIST_ROOT = APP_ROOT / "watchlists"
READY_ROOT = APP_ROOT / "ready"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RACE_NO = 12
DEFAULT_SLEEP_SECONDS = 0.5

PROFILE_COLUMNS_JA = {
    "box_id": "BOX",
    "profile_id": "PROFILE",
    "strategy_id": "戦略",
    "display_name": "表示名",
    "enabled": "有効",
    "stadiums": "対象場",
    "watch_minutes_before_deadline": "監視開始(分前)",
    "description": "説明",
}

WATCHLIST_COLUMNS_JA = {
    "box_id": "BOX",
    "profile_id": "PROFILE",
    "strategy_id": "戦略",
    "race_id": "race_id",
    "race_date": "日付",
    "stadium_code": "場コード",
    "stadium_name": "場名",
    "race_no": "R",
    "meeting_title": "開催名",
    "race_title": "レース名",
    "deadline_time": "締切",
    "watch_start_time": "監視開始",
    "status": "状態",
    "pre_reason": "事前条件",
    "final_reason": "直前条件",
    "lane1_racer_name": "1号艇選手",
    "lane1_racer_class": "1号艇級別",
    "lane1_motor_place_rate": "1号艇モーター2連率",
    "lane1_motor_top3_rate": "1号艇モーター3連率",
    "lane1_exhibition_time": "1号艇展示",
    "lane1_exhibition_best_gap": "1号艇最速差",
    "lane2_exhibition_time": "2号艇展示",
    "lane3_exhibition_time": "3号艇展示",
    "lane1_start_exhibition_st": "1号艇ST展示",
    "min_other_start_exhibition_st": "他艇最小ST展示",
    "lane1_start_gap_over_rest": "1号艇ST差",
    "beforeinfo_fetched_at": "beforeinfo取得時刻",
}


def _profile_label(profile) -> str:
    status = "有効" if profile.enabled else "無効"
    return f"{profile.box_id} / {profile.display_name} ({status})"


def _profile_summary_rows(profiles: list) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile in profiles:
        rows.append(
            {
                "box_id": profile.box_id,
                "profile_id": profile.profile_id,
                "strategy_id": profile.strategy_id,
                "display_name": profile.display_name,
                "enabled": profile.enabled,
                "stadiums": ",".join(profile.stadiums) if profile.stadiums else "all",
                "watch_minutes_before_deadline": profile.watch_minutes_before_deadline,
                "description": profile.description,
            }
        )
    return rows


def _watchlist_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = read_watchlist(path)
    return pd.DataFrame(rows)


def _available_watchlists() -> list[Path]:
    if not WATCHLIST_ROOT.exists():
        return []
    return sorted(WATCHLIST_ROOT.glob("*.csv"), reverse=True)


def _default_watchlist_name(target_date: date) -> str:
    return f"{target_date:%Y%m%d}_app_batch.csv"


def _rename_columns(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    columns = [column for column in mapping if column in frame.columns]
    if not columns:
        return frame
    return frame.loc[:, columns].rename(columns={column: mapping[column] for column in columns})


def _render_exception(message: str, exc: Exception) -> None:
    st.error(message)
    with st.expander("詳細"):
        st.code("".join(traceback.format_exception(exc)), language="text")


def main() -> None:
    st.set_page_config(
        page_title="BOAT Live Trigger",
        layout="wide",
    )
    st.title("BOAT Live Trigger")
    st.caption("予定確認、翌日候補抽出、直前判定を1画面で扱うためのローカルアプリです。")

    try:
        profiles = load_trigger_profiles(PROFILE_ROOT, include_disabled=True)
    except Exception as exc:
        _render_exception("BOX 設定の読み込みに失敗しました。", exc)
        return

    label_to_profile = {_profile_label(profile): profile for profile in profiles}
    enabled_labels = [label for label, profile in label_to_profile.items() if profile.enabled]

    with st.sidebar:
        st.header("BOX 一覧")
        profile_frame = pd.DataFrame(_profile_summary_rows(profiles))
        st.dataframe(
            _rename_columns(profile_frame, PROFILE_COLUMNS_JA),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("batch 候補抽出は通常、有効 profile だけを対象にします。")

    board_tab, watchlist_tab, resolve_tab = st.tabs(
        ["予定ボード", "翌日候補抽出", "直前判定"]
    )

    with board_tab:
        st.subheader("予定ボード")
        with st.form("board_form"):
            board_start_date = st.date_input("開始日", value=date.today())
            board_days = st.slider("表示日数", min_value=7, max_value=31, value=14)
            board_submitted = st.form_submit_button("予定ボードを作成")

        if board_submitted:
            try:
                with st.spinner("予定ボードを作成中..."):
                    outputs = build_logic_board(
                        start_date=board_start_date.isoformat(),
                        days=int(board_days),
                        profiles=profiles,
                        output_dir=PLANS_ROOT,
                        raw_root=RAW_ROOT,
                        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                    )
                st.session_state["board_html_path"] = str(outputs["logic_board_html"])
                st.session_state["board_md_path"] = str(outputs["logic_board_md"])
            except Exception as exc:
                _render_exception("予定ボードの作成に失敗しました。", exc)

        board_html_path = Path(st.session_state.get("board_html_path", ""))
        board_md_path = Path(st.session_state.get("board_md_path", ""))
        if board_html_path.exists():
            st.success(f"出力先: {board_html_path}")
            st_html(board_html_path.read_text(encoding="utf-8"), height=1200, scrolling=True)
        else:
            st.info("まず上のボタンで予定ボードを作成してください。")
        if board_md_path.exists():
            with st.expander("Markdown 表示"):
                st.code(board_md_path.read_text(encoding="utf-8"), language="markdown")

    with watchlist_tab:
        st.subheader("翌日候補抽出")
        with st.form("watchlist_form"):
            watchlist_date = st.date_input("対象日", value=date.today())
            selected_labels = st.multiselect(
                "使う profile",
                options=list(label_to_profile.keys()),
                default=enabled_labels,
            )
            watchlist_name = st.text_input("出力ファイル名", value=_default_watchlist_name(watchlist_date))
            watchlist_submitted = st.form_submit_button("候補を抽出")

        if watchlist_submitted:
            selected_profiles = [label_to_profile[label] for label in selected_labels]
            if not selected_profiles:
                st.warning("最低1つは profile を選んでください。")
            else:
                output_path = WATCHLIST_ROOT / watchlist_name
                try:
                    with st.spinner("候補抽出中..."):
                        row_count, path = build_watchlist_for_profiles(
                            race_date=watchlist_date.strftime("%Y%m%d"),
                            profiles=selected_profiles,
                            output_path=output_path,
                            raw_root=RAW_ROOT,
                            max_race_no=DEFAULT_MAX_RACE_NO,
                            sleep_seconds=DEFAULT_SLEEP_SECONDS,
                            timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                        )
                    st.session_state["watchlist_path"] = str(path)
                    st.session_state["watchlist_count"] = row_count
                except Exception as exc:
                    _render_exception("翌日候補抽出に失敗しました。", exc)

        watchlist_path = Path(st.session_state.get("watchlist_path", ""))
        if watchlist_path.exists():
            row_count = st.session_state.get("watchlist_count", 0)
            st.success(f"出力先: {watchlist_path} / {row_count}件")
            frame = _watchlist_frame(watchlist_path)
            if frame.empty:
                st.info("今回の条件では候補は 0 件でした。")
            else:
                st.dataframe(
                    _rename_columns(frame, WATCHLIST_COLUMNS_JA),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("ここで翌日候補を作ると、watchlist CSV が保存されます。")

    with resolve_tab:
        st.subheader("直前判定")
        watchlist_files = _available_watchlists()
        if not watchlist_files:
            st.info("まだ watchlist CSV がありません。先に『翌日候補抽出』を実行してください。")
            return

        default_index = 0
        current_watchlist = st.session_state.get("watchlist_path")
        if current_watchlist:
            current_path = Path(current_watchlist)
            if current_path in watchlist_files:
                default_index = watchlist_files.index(current_path)

        with st.form("resolve_form"):
            selected_watchlist = st.selectbox(
                "watchlist ファイル",
                options=watchlist_files,
                index=default_index,
                format_func=lambda path: path.name,
            )
            resolve_name = st.text_input("出力ファイル名", value=f"{selected_watchlist.stem}_ready.csv")
            resolve_submitted = st.form_submit_button("beforeinfo を見て判定")

        if resolve_submitted:
            ready_path = READY_ROOT / resolve_name
            try:
                with st.spinner("直前判定中..."):
                    changed_rows, ready_count = resolve_watchlist_for_profiles(
                        watchlist_path=selected_watchlist,
                        profiles=profiles,
                        raw_root=RAW_ROOT,
                        ready_output_path=ready_path,
                        sleep_seconds=DEFAULT_SLEEP_SECONDS,
                        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                    )
                st.session_state["ready_path"] = str(ready_path)
                st.session_state["resolve_changed_rows"] = changed_rows
                st.session_state["resolve_ready_count"] = ready_count
            except Exception as exc:
                _render_exception("直前判定に失敗しました。", exc)

        ready_path = Path(st.session_state.get("ready_path", ""))
        if ready_path.exists():
            changed_rows = st.session_state.get("resolve_changed_rows", 0)
            ready_count = st.session_state.get("resolve_ready_count", 0)
            st.success(f"出力先: {ready_path} / trigger_ready {ready_count}件 / 更新 {changed_rows}件")
            frame = _watchlist_frame(ready_path)
            if frame.empty:
                st.info("trigger_ready の行はまだありません。")
            else:
                st.dataframe(
                    _rename_columns(frame, WATCHLIST_COLUMNS_JA),
                    use_container_width=True,
                    hide_index=True,
                )


if __name__ == "__main__":
    if get_script_run_ctx() is None:
        sys.stderr.write(
            "このアプリは Streamlit で起動してください。\n"
            "  cd C:\\CODEX_WORK\\boat_clone\n"
            "  .\\.venv\\Scripts\\streamlit.exe run live_trigger\\app.py\n"
            "または\n"
            "  live_trigger\\run_app.cmd\n"
        )
        raise SystemExit(1)
    main()
