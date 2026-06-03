import json
import logging
import os
import threading
import time
import redis
import schedule as schedule_lib
from datetime import datetime, date
from dotenv import load_dotenv

from database import SessionLocal, WorkoutSchedule, ReminderLog

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL           = os.getenv("REDIS_URL", "redis://localhost:6379")
NOTIFICATIONS_QUEUE = "notifications_queue"

# Соответствие номера дня недели Python (0=пн) и нашего кода
WEEKDAY_MAP = {
    0: "mon", 1: "tue", 2: "wed",
    3: "thu", 4: "fri", 5: "sat", 6: "sun",
}

DAY_NAMES_RU = {
    "mon": "Понедельник", "tue": "Вторник", "wed": "Среда",
    "thu": "Четверг",     "fri": "Пятница", "sat": "Суббота", "sun": "Воскресенье",
}


def check_and_send_reminders():
    """
    Проверяет все активные расписания и отправляет напоминания
    пользователям у которых сегодня день тренировки и ещё не было напоминания.
    """
    now       = datetime.now()
    today_str = date.today().isoformat()         # "2026-05-27"
    today_day = WEEKDAY_MAP[now.weekday()]       # "tue"
    now_time  = now.strftime("%H:%M")            # "08:03"

    db = SessionLocal()
    try:
        schedules = db.query(WorkoutSchedule).filter(
            WorkoutSchedule.is_active == True
        ).all()

        for s in schedules:
            # Проверяем: сегодня есть в расписании?
            if today_day not in (s.days or []):
                continue

            # Проверяем: время напоминания совпадает с текущим временем (с точностью до минуты)?
            if s.remind_time != now_time:
                continue

            # Проверяем: уже отправляли сегодня?
            already_sent = db.query(ReminderLog).filter(
                ReminderLog.user_id  == s.user_id,
                ReminderLog.sent_date == today_str,
            ).first()
            if already_sent:
                continue

            # Отправляем уведомление в Redis
            try:
                r = redis.from_url(REDIS_URL)
                r.rpush(NOTIFICATIONS_QUEUE, json.dumps({
                    "event":   "workout_reminder",
                    "user_id": s.user_id,
                    "message": f"Сегодня {DAY_NAMES_RU.get(today_day,'')} — день тренировки! Не забудь позаниматься 💪",
                }))
                logger.info(f"[scheduler] Напоминание отправлено user_id={s.user_id}")

                # Записываем в лог чтобы не отправлять повторно
                log = ReminderLog(user_id=s.user_id, sent_date=today_str)
                db.add(log)
                db.commit()

            except Exception as e:
                logger.error(f"[scheduler] Ошибка отправки user_id={s.user_id}: {e}")

    except Exception as e:
        logger.error(f"[scheduler] Ошибка проверки расписаний: {e}")
    finally:
        db.close()


def run_scheduler():
    """
    Запускает проверку каждую минуту.
    schedule_lib.every(1).minutes.do() — стандартный паттерн для cron-подобных задач.
    """
    logger.info("[scheduler] Планировщик запущен — проверка каждую минуту")
    schedule_lib.every(1).minutes.do(check_and_send_reminders)

    while True:
        schedule_lib.run_pending()
        time.sleep(30)  # Спим 30 сек между проверками pending задач


def start_scheduler_thread():
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    logger.info("[scheduler] Фоновый поток запущен")
    return thread
