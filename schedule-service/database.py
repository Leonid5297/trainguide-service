import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://scheduledb:scheduledb@localhost:5432/scheduledb"
)

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class WorkoutSchedule(Base):
    """
    Расписание тренировок пользователя.
    days — список дней недели: ["mon","tue","wed","thu","fri","sat","sun"]
    remind_time — время напоминания в формате "HH:MM", например "08:00"
    """
    __tablename__ = "workout_schedules"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=False, unique=True, index=True)
    days        = Column(JSON, default=list)    # ["mon", "wed", "fri"]
    remind_time = Column(String(5), default="08:00")  # "08:00"
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReminderLog(Base):
    """
    Лог отправленных напоминаний — чтобы не отправлять дважды в один день.
    """
    __tablename__ = "reminder_logs"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, nullable=False, index=True)
    sent_date  = Column(String(10), nullable=False)  # "2026-05-27"
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
