import json
import threading
import logging
import os
import redis
from datetime import datetime, date
from collections import Counter
from dotenv import load_dotenv

from database import SessionLocal, AnalyticsEvent, UserStats

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL       = os.getenv("REDIS_URL", "redis://localhost:6379")
ANALYTICS_QUEUE = "analytics_queue"


def get_or_create_stats(db, user_id: int) -> UserStats:
    """Возвращает или создаёт агрегат для пользователя."""
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def recalculate_stats(db, user_id: int):
    """Пересчитывает агрегаты пользователя из сырых событий."""
    events = db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user_id).all()

    generated_events = [e for e in events if e.event == "workout_generated"]
    completed_events = [e for e in events if e.event == "workout_completed"]

    total_generated = len(generated_events)
    total_completed = len(completed_events)

    # Процент завершения
    completion_rate = 0.0
    if total_generated > 0:
        completion_rate = round(total_completed / total_generated * 100, 1)

    # Средний % выполненных упражнений
    avg_exercises = 0.0
    ex_ratios = []
    for e in completed_events:
        payload = e.payload or {}
        done  = payload.get("exercises_done", 0)
        total = payload.get("exercises_total", 0)
        if total > 0:
            ex_ratios.append(done / total * 100)
    if ex_ratios:
        avg_exercises = round(sum(ex_ratios) / len(ex_ratios), 1)

    # Любимая цель (самая частая)
    goals = [e.payload.get("goal") for e in generated_events if e.payload and e.payload.get("goal")]
    favorite_goal = Counter(goals).most_common(1)[0][0] if goals else None

    # Streak — дней подряд с завершёнными тренировками
    streak        = 0
    last_completed = None
    if completed_events:
        completed_dates = sorted(set(
            e.created_at.date() for e in completed_events
        ), reverse=True)

        streak = 1
        for i in range(1, len(completed_dates)):
            delta = (completed_dates[i - 1] - completed_dates[i]).days
            if delta == 1:
                streak += 1
            else:
                break

        last_completed = datetime.combine(completed_dates[0], datetime.min.time())

    # Сохраняем
    stats = get_or_create_stats(db, user_id)
    stats.total_generated    = total_generated
    stats.total_completed    = total_completed
    stats.completion_rate    = completion_rate
    stats.avg_exercises_done = avg_exercises
    stats.favorite_goal      = favorite_goal
    stats.current_streak     = streak
    stats.last_completed_at  = last_completed
    stats.updated_at         = datetime.utcnow()
    db.commit()

    logger.info(
        f"[analytics] user_id={user_id}: "
        f"generated={total_generated}, completed={total_completed}, "
        f"streak={streak}, favorite={favorite_goal}"
    )


def process_event(event_data: dict):
    """Сохраняет сырое событие и пересчитывает агрегаты."""
    event     = event_data.get("event")
    user_id   = event_data.get("user_id")
    workout_id = event_data.get("workout_id")

    if not event or not user_id:
        logger.warning(f"[analytics] Пропускаю событие без event/user_id: {event_data}")
        return

    db = SessionLocal()
    try:
        # Сохраняем сырое событие
        raw = AnalyticsEvent(
            event=event,
            user_id=user_id,
            workout_id=workout_id,
            payload=event_data,
        )
        db.add(raw)
        db.commit()

        # Пересчитываем агрегаты
        recalculate_stats(db, user_id)

    except Exception as e:
        logger.error(f"[analytics] Ошибка обработки события: {e}")
    finally:
        db.close()


def run_consumer():
    r = redis.from_url(REDIS_URL)
    logger.info(f"[analytics] Слушаю очередь '{ANALYTICS_QUEUE}'...")

    while True:
        try:
            item = r.blpop(ANALYTICS_QUEUE, timeout=5)
            if item is None:
                continue
            _, raw = item
            event_data = json.loads(raw)
            logger.info(f"[analytics] Получил событие: {event_data.get('event')}")
            process_event(event_data)
        except Exception as e:
            logger.error(f"[analytics] Ошибка в цикле: {e}")


def start_consumer_thread():
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()
    logger.info("[analytics] Фоновый поток запущен")
    return thread
