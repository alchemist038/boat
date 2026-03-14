from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

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


def _profile_label(profile) -> str:
    status = "enabled" if profile.enabled else "disabled"
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


def main() -> None:
    st.set_page_config(
        page_title="BOAT Live Trigger",
        page_icon="boat",
        layout="wide",
    )
    st.title("BOAT Live Trigger")
    st.caption("Schedule board, next-day watchlist, and final beforeinfo resolution in one app.")

    profiles = load_trigger_profiles(PROFILE_ROOT, include_disabled=True)
    label_to_profile = {_profile_label(profile): profile for profile in profiles}
    enabled_labels = [label for label, profile in label_to_profile.items() if profile.enabled]

    with st.sidebar:
        st.header("Boxes")
        st.dataframe(pd.DataFrame(_profile_summary_rows(profiles)), use_container_width=True, hide_index=True)

    board_tab, watchlist_tab, resolve_tab = st.tabs(
        ["Schedule Board", "Next-Day Watchlist", "Final Resolve"]
    )

    with board_tab:
        st.subheader("Schedule Board")
        with st.form("board_form"):
            board_start_date = st.date_input("Start date", value=date.today())
            board_days = st.slider("Days", min_value=7, max_value=31, value=14)
            board_submitted = st.form_submit_button("Build board")

        if board_submitted:
            with st.spinner("Building logic board..."):
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

        board_html_path = Path(st.session_state.get("board_html_path", ""))
        board_md_path = Path(st.session_state.get("board_md_path", ""))
        if board_html_path.exists():
            st.success(f"Board ready: {board_html_path}")
            st_html(board_html_path.read_text(encoding="utf-8"), height=1200, scrolling=True)
        else:
            st.info("Build the board to display the current 2-week to 1-month calendar view.")
        if board_md_path.exists():
            with st.expander("Board markdown"):
                st.code(board_md_path.read_text(encoding="utf-8"), language="markdown")

    with watchlist_tab:
        st.subheader("Next-Day Watchlist")
        with st.form("watchlist_form"):
            watchlist_date = st.date_input("Race date", value=date.today())
            selected_labels = st.multiselect(
                "Profiles to run",
                options=list(label_to_profile.keys()),
                default=enabled_labels,
            )
            watchlist_name = st.text_input("Output file name", value=_default_watchlist_name(watchlist_date))
            watchlist_submitted = st.form_submit_button("Build watchlist")

        if watchlist_submitted:
            selected_profiles = [label_to_profile[label] for label in selected_labels]
            if not selected_profiles:
                st.warning("Select at least one profile.")
            else:
                output_path = WATCHLIST_ROOT / watchlist_name
                with st.spinner("Building watchlist..."):
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

        watchlist_path = Path(st.session_state.get("watchlist_path", ""))
        if watchlist_path.exists():
            row_count = st.session_state.get("watchlist_count", 0)
            st.success(f"Watchlist ready: {watchlist_path} ({row_count} rows)")
            frame = _watchlist_frame(watchlist_path)
            if frame.empty:
                st.info("No candidates matched on this run.")
            else:
                st.dataframe(frame, use_container_width=True, hide_index=True)
        else:
            st.info("Build a watchlist to inspect next-day candidates.")

    with resolve_tab:
        st.subheader("Final Resolve")
        watchlist_files = _available_watchlists()
        if not watchlist_files:
            st.info("No watchlist CSV files found yet.")
            return

        default_index = 0
        current_watchlist = st.session_state.get("watchlist_path")
        if current_watchlist:
            current_path = Path(current_watchlist)
            if current_path in watchlist_files:
                default_index = watchlist_files.index(current_path)

        with st.form("resolve_form"):
            selected_watchlist = st.selectbox(
                "Watchlist file",
                options=watchlist_files,
                index=default_index,
                format_func=lambda path: path.name,
            )
            resolve_name = st.text_input("Ready file name", value=f"{selected_watchlist.stem}_ready.csv")
            resolve_submitted = st.form_submit_button("Resolve beforeinfo")

        if resolve_submitted:
            ready_path = READY_ROOT / resolve_name
            with st.spinner("Resolving beforeinfo..."):
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

        ready_path = Path(st.session_state.get("ready_path", ""))
        if ready_path.exists():
            changed_rows = st.session_state.get("resolve_changed_rows", 0)
            ready_count = st.session_state.get("resolve_ready_count", 0)
            st.success(
                f"Resolve complete: {ready_path} ({ready_count} ready rows, {changed_rows} changed rows)"
            )
            frame = _watchlist_frame(ready_path)
            if frame.empty:
                st.info("No trigger-ready rows yet.")
            else:
                st.dataframe(frame, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
