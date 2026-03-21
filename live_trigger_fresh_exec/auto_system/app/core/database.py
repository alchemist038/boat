from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship, sessionmaker

from .settings import DATA_DIR, DB_PATH

DATA_DIR.mkdir(parents=True, exist_ok=True)

Base = declarative_base()


class TargetRace(Base):
    __tablename__ = "target_races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    race_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    race_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    stadium_code: Mapped[str] = mapped_column(String(4), nullable=False)
    stadium_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    race_no: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_watchlist_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    watch_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    monitoring_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    beforeinfo_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    go_decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    air_bet_executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="imported", nullable=False)
    row_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    intents: Mapped[list["BetIntent"]] = relationship("BetIntent", back_populates="target", cascade="all, delete-orphan")
    executions: Mapped[list["BetExecution"]] = relationship("BetExecution", back_populates="target", cascade="all, delete-orphan")
    events: Mapped[list["ExecutionEvent"]] = relationship("ExecutionEvent", back_populates="target", cascade="all, delete-orphan")
    air_audits: Mapped[list["AirBetAudit"]] = relationship("AirBetAudit", back_populates="target", cascade="all, delete-orphan")


class BetIntent(Base):
    __tablename__ = "bet_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_race_id: Mapped[int] = mapped_column(ForeignKey("target_races.id"), index=True, nullable=False)
    intent_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), default="air", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending", nullable=False)
    bet_type: Mapped[str] = mapped_column(String(32), nullable=False)
    combo: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    target: Mapped[TargetRace] = relationship("TargetRace", back_populates="intents")
    executions: Mapped[list["BetExecution"]] = relationship("BetExecution", back_populates="intent", cascade="all, delete-orphan")
    events: Mapped[list["ExecutionEvent"]] = relationship("ExecutionEvent", back_populates="intent", cascade="all, delete-orphan")
    air_audits: Mapped[list["AirBetAudit"]] = relationship("AirBetAudit", back_populates="intent", cascade="all, delete-orphan")


class BetExecution(Base):
    __tablename__ = "bet_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intent_id: Mapped[int] = mapped_column(ForeignKey("bet_intents.id"), index=True, nullable=False)
    target_race_id: Mapped[int] = mapped_column(ForeignKey("target_races.id"), index=True, nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    seconds_before_deadline: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    intent: Mapped[BetIntent] = relationship("BetIntent", back_populates="executions")
    target: Mapped[TargetRace] = relationship("TargetRace", back_populates="executions")


class AirBetAudit(Base):
    __tablename__ = "air_bet_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_race_id: Mapped[int] = mapped_column(ForeignKey("target_races.id"), index=True, nullable=False)
    intent_id: Mapped[int] = mapped_column(ForeignKey("bet_intents.id"), index=True, nullable=False)
    target_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    race_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    race_date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    stadium_code: Mapped[str] = mapped_column(String(4), nullable=False)
    stadium_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    race_no: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bet_type: Mapped[str] = mapped_column(String(32), nullable=False)
    combo: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    air_bet_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    seconds_before_deadline: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_watchlist_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    target: Mapped[TargetRace] = relationship("TargetRace", back_populates="air_audits")
    intent: Mapped[BetIntent] = relationship("BetIntent", back_populates="air_audits")


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_race_id: Mapped[int | None] = mapped_column(ForeignKey("target_races.id"), index=True, nullable=True)
    intent_id: Mapped[int | None] = mapped_column(ForeignKey("bet_intents.id"), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    target: Mapped[TargetRace | None] = relationship("TargetRace", back_populates="events")
    intent: Mapped[BetIntent | None] = relationship("BetIntent", back_populates="events")


class SessionEvent(Base):
    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def json_dumps(payload: dict[str, Any] | list[Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def log_event(
    session,
    *,
    event_type: str,
    message: str | None = None,
    target: TargetRace | None = None,
    intent: BetIntent | None = None,
    details: dict[str, Any] | None = None,
) -> ExecutionEvent:
    event = ExecutionEvent(
        target=target,
        intent=intent,
        event_type=event_type,
        message=message,
        details_json=json_dumps(details),
    )
    session.add(event)
    return event


def log_session_event(
    session,
    *,
    event_type: str,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> SessionEvent:
    event = SessionEvent(
        event_type=event_type,
        message=message,
        details_json=json_dumps(details),
    )
    session.add(event)
    return event


def latest_execution_for_target(session, target_id: int) -> BetExecution | None:
    stmt = (
        select(BetExecution)
        .where(BetExecution.target_race_id == target_id)
        .order_by(BetExecution.executed_at.desc(), BetExecution.id.desc())
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


initialize_database()
