import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://exportdb:exportdb@localhost:5432/exportdb")

engine      = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class ExportJob(Base):
    """Задание на генерацию PDF."""
    __tablename__ = "export_jobs"

    id         = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, nullable=False, index=True)
    user_id    = Column(Integer, nullable=False, index=True)

    # pending / processing / done / error
    status     = Column(String(20), default="pending", nullable=False)
    file_path  = Column(String(500), nullable=True)
    file_name  = Column(String(255), nullable=True)
    error_msg  = Column(Text, nullable=True)

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
