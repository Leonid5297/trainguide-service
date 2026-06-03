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

from database import create_tables, get_db, Notification
from consumer import start_consumer_thread, process_event

load_dotenv()
logging.basicConfig(level=logging.INFO)

REDIS_URL           = os.getenv("REDIS_URL", "redis://localhost:6379")
NOTIFICATIONS_QUEUE = "notifications_queue"

app = FastAPI(
    title="Notification Service",
    description="Микросервис уведомлений TrainGuide",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic схемы ─────────────────────────────────────────────────────────────

class NotificationEvent(BaseModel):
    event:   str
    user_id: int
    message: str


class NotificationOut(BaseModel):
    id:         int
    user_id:    int
    event_type: str
    message:    str
    is_read:    bool
    created_at: datetime


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
        "service": "notification-service",
        "version": "1.0.0",
        "status":  "running",
        "queue":   NOTIFICATIONS_QUEUE,
    }


@app.get("/notifications/{user_id}/", summary="Список уведомлений пользователя")
def get_notifications(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Возвращает уведомления пользователя, новые сверху."""
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()

    return [
        {
            "id":         n.id,
            "event_type": n.event_type,
            "message":    n.message,
            "is_read":    n.is_read,
            "created_at": n.created_at,
        }
        for n in notifications
    ]


@app.get("/notifications/{user_id}/unread-count/", summary="Счётчик непрочитанных")
def unread_count(user_id: int, db: Session = Depends(get_db)):
    """Возвращает количество непрочитанных уведомлений — для бейджа в навбаре."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).count()
    return {"user_id": user_id, "unread_count": count}


@app.post("/notifications/{user_id}/read/", summary="Отметить все прочитанными")
def mark_all_read(user_id: int, db: Session = Depends(get_db)):
    """Помечает все уведомления пользователя прочитанными."""
    updated = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"user_id": user_id, "marked_read": updated}


@app.post("/notifications/{notification_id}/read-one/", summary="Прочитать одно уведомление")
def mark_one_read(notification_id: int, db: Session = Depends(get_db)):
    """Помечает одно конкретное уведомление прочитанным."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    notification.is_read = True
    db.commit()
    return {"id": notification_id, "is_read": True}


@app.post("/event/", summary="Создать уведомление напрямую (для Postman)")
def send_event(payload: NotificationEvent, db: Session = Depends(get_db)):
    """Синхронно создаёт уведомление без Redis — для тестирования."""
    process_event(payload.model_dump())
    return {"detail": "Уведомление создано", "user_id": payload.user_id}


@app.get("/queue/info/", summary="Состояние очереди Redis")
def queue_info():
    r = redis.from_url(REDIS_URL)
    return {"queue": NOTIFICATIONS_QUEUE, "count": r.llen(NOTIFICATIONS_QUEUE)}


@app.post("/queue/push/", summary="Добавить событие в очередь вручную")
def push_event(payload: NotificationEvent):
    """Для демонстрации асинхронного потока через Postman."""
    r = redis.from_url(REDIS_URL)
    r.rpush(NOTIFICATIONS_QUEUE, json.dumps(payload.model_dump()))
    return {
        "detail":     "Событие добавлено в очередь",
        "queue_size": r.llen(NOTIFICATIONS_QUEUE),
    }


@app.delete("/notifications/{user_id}/", summary="Удалить все уведомления пользователя")
def delete_all(user_id: int, db: Session = Depends(get_db)):
    deleted = db.query(Notification).filter(
        Notification.user_id == user_id
    ).delete()
    db.commit()
    return {"user_id": user_id, "deleted": deleted}
