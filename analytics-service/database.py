import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://analyticsdb:analyticsdb@localhost:5432/analyticsdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AnalyticsEvent(Base):
    """Сырые события — каждое действие пользователя."""
    __tablename__ = "analytics_events"

    id         = Column(Integer, primary_key=True, index=True)
    event      = Column(String(50), nullable=False, index=True)
    user_id    = Column(Integer, nullable=False, index=True)
    workout_id = Column(Integer, nullable=True)
    payload    = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserStats(Base):
    """Агрегированная статистика по каждому пользователю."""
    __tablename__ = "user_stats"

    id                 = Column(Integer, primary_key=True, index=True)
    user_id            = Column(Integer, unique=True, nullable=False, index=True)
    total_generated    = Column(Integer, default=0)
    total_completed    = Column(Integer, default=0)
    completion_rate    = Column(Float, default=0.0)
    avg_exercises_done = Column(Float, default=0.0)
    favorite_goal      = Column(String(100), nullable=True)
    current_streak     = Column(Integer, default=0)
    last_completed_at  = Column(DateTime, nullable=True)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
