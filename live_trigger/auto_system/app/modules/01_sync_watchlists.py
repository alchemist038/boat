from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal, TargetRace, initialize_database, json_dumps, log_event
from app.core.settings import WATCHLIST_ROOT, bootstrap_runtime_path
from app.core.time_utils import parse_watch_datetime

bootstrap_runtime_path()

from boat_race_data.live_trigger import read_watchlist


def _target_key(row: dict[str, object]) -> str:
    return f"{row.get('race_id', '')}::{row.get('profile_id', '')}"


def main() -> None:
    initialize_database()
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")
    watchlist_files = sorted(WATCHLIST_ROOT.glob("*.csv")) if WATCHLIST_ROOT.exists() else []
    imported = 0
    updated = 0

    session = SessionLocal()
    try:
        for watchlist_path in watchlist_files:
            for row in read_watchlist(watchlist_path):
                if str(row.get("race_date", "")) != today_iso:
                    continue
                if not row.get("race_id") or not row.get("profile_id"):
                    continue

                deadline_at = parse_watch_datetime(f"{row.get('race_date', '')} {row.get('deadline_time', '')}")
                if deadline_at is None:
                    continue
                watch_start_at = parse_watch_datetime(str(row.get("watch_start_time", "")))

                target_key = _target_key(row)
                target = session.query(TargetRace).filter(TargetRace.target_key == target_key).first()
                if target is None:
                    target = TargetRace(
                        target_key=target_key,
                        race_id=str(row.get("race_id", "")),
                        race_date=str(row.get("race_date", "")),
                        stadium_code=str(row.get("stadium_code", "")),
                        stadium_name=str(row.get("stadium_name", "")),
                        race_no=int(row.get("race_no", 0) or 0),
                        profile_id=str(row.get("profile_id", "")),
                        strategy_id=str(row.get("strategy_id", "")),
                        source_watchlist_file=watchlist_path.name,
                        deadline_at=deadline_at,
                        watch_start_at=watch_start_at,
                        status="imported",
                        row_status=str(row.get("status", "")),
                        last_reason=str(row.get("pre_reason", "")),
                        payload_json=json_dumps(row),
                    )
                    session.add(target)
                    log_event(
                        session,
                        target=target,
                        event_type="watchlist_imported",
                        message=f"{watchlist_path.name} から取り込み",
                    )
                    imported += 1
                    continue

                target.race_id = str(row.get("race_id", ""))
                target.race_date = str(row.get("race_date", ""))
                target.stadium_code = str(row.get("stadium_code", ""))
                target.stadium_name = str(row.get("stadium_name", ""))
                target.race_no = int(row.get("race_no", 0) or 0)
                target.profile_id = str(row.get("profile_id", ""))
                target.strategy_id = str(row.get("strategy_id", ""))
                target.source_watchlist_file = watchlist_path.name
                target.deadline_at = deadline_at
                target.watch_start_at = watch_start_at
                target.row_status = str(row.get("status", ""))
                target.payload_json = json_dumps(row)
                if target.status in {"imported", "monitoring", "checked_waiting"}:
                    target.last_reason = str(row.get("final_reason") or row.get("pre_reason") or "")
                updated += 1

        session.commit()
        print(
            f"[{now:%Y-%m-%d %H:%M:%S}] sync_watchlists completed: imported={imported} updated={updated} files={len(watchlist_files)}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
