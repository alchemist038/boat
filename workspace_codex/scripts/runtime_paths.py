from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CANONICAL_ROOT = Path(r"C:\boat")


def _canonical_root_from_env() -> Path | None:
    explicit = os.environ.get("BOAT_CANONICAL_ROOT")
    if explicit:
        return Path(explicit)
    data_root = os.environ.get("BOAT_DATA_ROOT")
    if not data_root:
        return None
    data_path = Path(data_root)
    return data_path.parent if data_path.name.lower() == "data" else data_path


def _repo_canonical_root() -> Path | None:
    db_path = REPO_ROOT / "data" / "silver" / "boat_race.duckdb"
    if db_path.exists():
        return REPO_ROOT
    return None


def _local_canonical_root() -> Path | None:
    db_path = LOCAL_CANONICAL_ROOT / "data" / "silver" / "boat_race.duckdb"
    if db_path.exists():
        return LOCAL_CANONICAL_ROOT
    return None


def default_canonical_root() -> Path:
    return _canonical_root_from_env() or _repo_canonical_root() or _local_canonical_root() or REPO_ROOT


def default_results_db_path() -> Path:
    explicit = os.environ.get("BOAT_DB_PATH")
    if explicit:
        return Path(explicit)
    data_root = os.environ.get("BOAT_DATA_ROOT")
    if data_root:
        return Path(data_root) / "silver" / "boat_race.duckdb"
    return default_canonical_root() / "data" / "silver" / "boat_race.duckdb"


def default_reports_root() -> Path:
    explicit = os.environ.get("BOAT_REPORTS_ROOT")
    if explicit:
        return Path(explicit)
    return default_canonical_root() / "reports" / "strategies"


def default_workspace_script_path(filename: str) -> Path:
    repo_candidate = REPO_ROOT / "workspace_codex" / "scripts" / filename
    if repo_candidate.exists():
        return repo_candidate
    return default_canonical_root() / "workspace_codex" / "scripts" / filename
