import json
import threading
import logging
import os
import redis
from dotenv import load_dotenv

from database import SessionLocal, Notification

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL          = os.getenv("REDIS_URL", "redis://localhost:6379")
NOTIFICATIONS_QUEUE = "notifications_queue"


def process_event(event_data: dict):
    """Создаёт уведомление из события."""
    user_id    = event_data.get("user_id")
    event_type = event_data.get("event", "info")
    message    = event_data.get("message", "")

    if not user_id or not message:
        logger.warning(f"[notif] Пропускаю некорректное событие: {event_data}")
        return

    db = SessionLocal()
    try:
        notification = Notification(
            user_id=user_id,
            event_type=event_type,
            message=message,
        )
        db.add(notification)
        db.commit()
        logger.info(f"[notif] Создано уведомление для user_id={user_id}: {event_type}")
    except Exception as e:
        logger.error(f"[notif] Ошибка создания уведомления: {e}")
    finally:
        db.close()


def run_consumer():
    r = redis.from_url(REDIS_URL)
    logger.info(f"[notif] Слушаю очередь '{NOTIFICATIONS_QUEUE}'...")

    while True:
        try:
            item = r.blpop(NOTIFICATIONS_QUEUE, timeout=5)
            if item is None:
                continue
            _, raw = item
            event_data = json.loads(raw)
            logger.info(f"[notif] Получил событие: {event_data.get('event')}")
            process_event(event_data)
        except Exception as e:
            logger.error(f"[notif] Ошибка в цикле: {e}")


def start_consumer_thread():
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()
    logger.info("[notif] Фоновый поток запущен")
    return thread
