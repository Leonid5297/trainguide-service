import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/workout_service")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class GenerationJob(Base):
    """
    Хранит задания на генерацию тренировок и их результаты.
    workout_id соответствует Workout.pk в Django.
    """
    __tablename__ = "generation_jobs"

    id          = Column(Integer, primary_key=True, index=True)
    workout_id  = Column(Integer, unique=True, index=True, nullable=False)
    user_id     = Column(Integer, nullable=False)

    # Статус: pending / processing / done / error
    status      = Column(String(20), default="pending", nullable=False)

    # Данные формы (промпт уже собранный)
    prompt      = Column(Text, nullable=False)

    # Результат от Claude (JSON)
    result      = Column(JSON, nullable=True)
    error_msg   = Column(Text, nullable=True)

    created_at  = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
