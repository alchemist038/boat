import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "system.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base = declarative_base()

class TargetRace(Base):
    __tablename__ = 'target_races'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)
    stadium_code = Column(String, nullable=False)
    race_no = Column(Integer, nullable=False)
    logic_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class BetHistory(Base):
    __tablename__ = 'bet_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_race_id = Column(Integer, nullable=False, unique=True)
    status = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    bet_type = Column(String, nullable=True)
    combo = Column(String, nullable=True)
    amount = Column(Integer, nullable=True)
    is_air_bet = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
