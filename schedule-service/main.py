import os
import json
import logging
import redis
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import create_tables, get_db, WorkoutSchedule, ReminderLog
from scheduler import start_scheduler_thread, check_and_send_reminders

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL           = os.getenv("REDIS_URL", "redis://localhost:6379")
NOTIFICATIONS_QUEUE = "notifications_queue"

app = FastAPI(
    title="Schedule Service",
    description="Микросервис расписания тренировок TrainGuide",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


# ── Pydantic схемы ─────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    user_id:     int
    days:        List[str]        # ["mon", "wed", "fri"]
    remind_time: str = "08:00"   # "HH:MM"
    is_active:   bool = True


class ScheduleOut(BaseModel):
    id:          int
    user_id:     int
    days:        List[str]
    remind_time: str
    is_active:   bool
    created_at:  datetime
    updated_at:  datetime


# ── Старт ──────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    create_tables()
    start_scheduler_thread()
    logger.info("[schedule] Сервис запущен")


# ── Валидация ─────────────────────────────────────────────────────────────────

def validate_schedule(days: List[str], remind_time: str):
    invalid_days = [d for d in days if d not in VALID_DAYS]
    if invalid_days:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимые дни: {invalid_days}. Допустимые: {sorted(VALID_DAYS)}"
        )
    try:
        h, m = remind_time.split(":")
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Время должно быть в формате HH:MM, например '08:00'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# HTTP ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "service":     "schedule-service",
        "version":     "1.0.0",
        "status":      "running",
        "description": "Сервис расписания тренировок с напоминаниями",
    }


@app.post("/schedule/", response_model=ScheduleOut,
          summary="Создать или обновить расписание")
def create_or_update_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
):
    """
    Создаёт новое расписание или обновляет существующее для пользователя.
    У каждого пользователя одно расписание (upsert по user_id).
    """
    validate_schedule(payload.days, payload.remind_time)

    existing = db.query(WorkoutSchedule).filter(
        WorkoutSchedule.user_id == payload.user_id
    ).first()

    if existing:
        existing.days        = payload.days
        existing.remind_time = payload.remind_time
        existing.is_active   = payload.is_active
        existing.updated_at  = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        schedule = WorkoutSchedule(
            user_id=payload.user_id,
            days=payload.days,
            remind_time=payload.remind_time,
            is_active=payload.is_active,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule


@app.get("/schedule/{user_id}/", response_model=ScheduleOut,
         summary="Получить расписание пользователя")
def get_schedule(user_id: int, db: Session = Depends(get_db)):
    """Django запрашивает при открытии страницы расписания."""
    s = db.query(WorkoutSchedule).filter(
        WorkoutSchedule.user_id == user_id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    return s


@app.patch("/schedule/{user_id}/toggle/", summary="Включить/выключить расписание")
def toggle_schedule(user_id: int, db: Session = Depends(get_db)):
    """Переключает активность расписания."""
    s = db.query(WorkoutSchedule).filter(
        WorkoutSchedule.user_id == user_id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Расписание не найдено")

    s.is_active  = not s.is_active
    s.updated_at = datetime.utcnow()
    db.commit()
    return {"user_id": user_id, "is_active": s.is_active}


@app.delete("/schedule/{user_id}/", summary="Удалить расписание")
def delete_schedule(user_id: int, db: Session = Depends(get_db)):
    s = db.query(WorkoutSchedule).filter(
        WorkoutSchedule.user_id == user_id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Расписание не найдено")
    db.delete(s)
    db.commit()
    return {"user_id": user_id, "deleted": True}


@app.get("/schedules/", summary="Все расписания (для Postman)")
def list_schedules(db: Session = Depends(get_db)):
    """Список всех расписаний — для демонстрации в Postman."""
    schedules = db.query(WorkoutSchedule).all()
    return [
        {
            "user_id":     s.user_id,
            "days":        s.days,
            "remind_time": s.remind_time,
            "is_active":   s.is_active,
        }
        for s in schedules
    ]


@app.post("/remind/send-now/", summary="Отправить напоминание немедленно (для теста)")
def send_now(user_id: int):
    """
    Немедленно отправляет напоминание пользователю в notifications_queue.
    Используется для тестирования без ожидания нужного времени.
    """
    try:
        r = redis.from_url(REDIS_URL)
        r.rpush(NOTIFICATIONS_QUEUE, json.dumps({
            "event":   "workout_reminder",
            "user_id": user_id,
            "message": "Тестовое напоминание: не забудь про тренировку сегодня! 💪",
        }))
        return {
            "detail":  "Напоминание отправлено в очередь",
            "user_id": user_id,
            "queue":   NOTIFICATIONS_QUEUE,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scheduler/run-now/", summary="Запустить проверку расписаний немедленно")
def run_check_now():
    """
    Запускает проверку всех расписаний прямо сейчас.
    Полезно для демонстрации в Postman — не нужно ждать нужного времени.
    """
    check_and_send_reminders()
    return {"detail": "Проверка расписаний выполнена"}


@app.get("/logs/{user_id}/", summary="Лог напоминаний пользователя")
def get_logs(user_id: int, db: Session = Depends(get_db)):
    """История отправленных напоминаний."""
    logs = db.query(ReminderLog).filter(
        ReminderLog.user_id == user_id
    ).order_by(ReminderLog.created_at.desc()).all()
    return [
        {"id": l.id, "sent_date": l.sent_date, "created_at": l.created_at}
        for l in logs
    ]
