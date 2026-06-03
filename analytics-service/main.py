import os
import json
import logging
import redis
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import create_tables, get_db, AnalyticsEvent, UserStats
from consumer import start_consumer_thread, process_event

load_dotenv()
logging.basicConfig(level=logging.INFO)

REDIS_URL       = os.getenv("REDIS_URL", "redis://localhost:6379")
ANALYTICS_QUEUE = "analytics_queue"

app = FastAPI(
    title="Analytics Service",
    description="Микросервис аналитики тренировок TrainGuide",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic схемы ─────────────────────────────────────────────────────────────

class EventRequest(BaseModel):
    event:      str
    user_id:    int
    workout_id: Optional[int] = None
    goal:       Optional[str] = None
    duration:   Optional[str] = None
    exercises_done:  Optional[int] = None
    exercises_total: Optional[int] = None


class StatsResponse(BaseModel):
    user_id:            int
    total_generated:    int
    total_completed:    int
    completion_rate:    float
    avg_exercises_done: float
    favorite_goal:      Optional[str]
    current_streak:     int
    updated_at:         Optional[datetime]


# ── Старт ──────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    create_tables()
    start_consumer_thread()


# ══════════════════════════════════════════════════════════════════════════════
# HTTP ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "service": "analytics-service",
        "version": "1.0.0",
        "status":  "running",
        "queue":   ANALYTICS_QUEUE,
    }


@app.get("/stats/{user_id}/", response_model=StatsResponse,
         summary="Получить статистику пользователя")
def get_stats(user_id: int, db: Session = Depends(get_db)):
    """
    Главный endpoint — Django вызывает его при открытии страницы профиля.
    Возвращает агрегированную статистику пользователя.
    """
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        # Возвращаем пустую статистику если данных ещё нет
        return StatsResponse(
            user_id=user_id,
            total_generated=0,
            total_completed=0,
            completion_rate=0.0,
            avg_exercises_done=0.0,
            favorite_goal=None,
            current_streak=0,
            updated_at=None,
        )
    return StatsResponse(
        user_id=stats.user_id,
        total_generated=stats.total_generated,
        total_completed=stats.total_completed,
        completion_rate=stats.completion_rate,
        avg_exercises_done=stats.avg_exercises_done,
        favorite_goal=stats.favorite_goal,
        current_streak=stats.current_streak,
        updated_at=stats.updated_at,
    )


@app.get("/stats/", summary="Статистика всех пользователей")
def get_all_stats(limit: int = 20, db: Session = Depends(get_db)):
    """Список статистики всех пользователей — для демонстрации."""
    all_stats = db.query(UserStats).order_by(
        UserStats.total_completed.desc()
    ).limit(limit).all()
    return [
        {
            "user_id":         s.user_id,
            "total_generated": s.total_generated,
            "total_completed": s.total_completed,
            "completion_rate": s.completion_rate,
            "current_streak":  s.current_streak,
            "favorite_goal":   s.favorite_goal,
        }
        for s in all_stats
    ]


@app.get("/events/{user_id}/", summary="История событий пользователя")
def get_events(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Возвращает сырые события пользователя."""
    events = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.user_id == user_id
    ).order_by(AnalyticsEvent.created_at.desc()).limit(limit).all()

    return [
        {
            "id":         e.id,
            "event":      e.event,
            "workout_id": e.workout_id,
            "payload":    e.payload,
            "created_at": e.created_at,
        }
        for e in events
    ]


@app.post("/event/", summary="Отправить событие напрямую (для Postman)")
def send_event(payload: EventRequest, db: Session = Depends(get_db)):
    """
    Синхронно обрабатывает событие без Redis.
    Удобно для тестирования в Postman.
    """
    process_event(payload.model_dump())
    return {"detail": "Событие обработано", "event": payload.event, "user_id": payload.user_id}


@app.get("/queue/info/", summary="Состояние очереди Redis")
def queue_info():
    r = redis.from_url(REDIS_URL)
    return {
        "queue": ANALYTICS_QUEUE,
        "count": r.llen(ANALYTICS_QUEUE),
    }


@app.post("/queue/push/", summary="Добавить событие в очередь вручную")
def push_event(payload: EventRequest):
    """Для демонстрации асинхронного потока через Postman."""
    r = redis.from_url(REDIS_URL)
    r.rpush(ANALYTICS_QUEUE, json.dumps(payload.model_dump()))
    return {
        "detail":     "Событие добавлено в очередь",
        "event":      payload.event,
        "user_id":    payload.user_id,
        "queue_size": r.llen(ANALYTICS_QUEUE),
    }


@app.delete("/stats/{user_id}/", summary="Сбросить статистику пользователя")
def reset_stats(user_id: int, db: Session = Depends(get_db)):
    """Удаляет все события и статистику пользователя."""
    db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user_id).delete()
    db.query(UserStats).filter(UserStats.user_id == user_id).delete()
    db.commit()
    return {"detail": f"Статистика user_id={user_id} сброшена"}
