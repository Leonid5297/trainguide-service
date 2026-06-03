import json
import threading
import logging
import os
import redis
from datetime import datetime
from dotenv import load_dotenv

from database import SessionLocal, GenerationJob
from generator import call_claude

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL        = os.getenv("REDIS_URL", "redis://localhost:6379")
GENERATE_QUEUE   = "workout_generate_queue"   # Django → микросервис
RESULT_QUEUE     = "workout_result_queue"     # микросервис → Django


def process_job(job_data: dict):
    """Обрабатывает одно задание из очереди."""
    workout_id = job_data["workout_id"]
    prompt     = job_data["prompt"]
    user_id    = job_data["user_id"]

    db = SessionLocal()
    try:
        # Создаём запись в своей БД
        job = GenerationJob(
            workout_id=workout_id,
            user_id=user_id,
            prompt=prompt,
            status="processing",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"[consumer] Обрабатываю задание workout_id={workout_id}")

        # Вызываем Claude API
        result = call_claude(prompt)

        # Сохраняем результат
        job.result      = result
        job.status      = "done"
        job.finished_at = datetime.utcnow()
        db.commit()

        logger.info(f"[consumer] Задание workout_id={workout_id} выполнено")

        # Публикуем результат обратно в Redis для Django
        r = redis.from_url(REDIS_URL)
        r.rpush(RESULT_QUEUE, json.dumps({
            "workout_id": workout_id,
            "status":     "done",
            "result":     result,
        }))

    except Exception as e:
        logger.error(f"[consumer] Ошибка workout_id={workout_id}: {e}")
        if 'job' in locals():
            job.status    = "error"
            job.error_msg = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()

        # Сообщаем Django об ошибке
        r = redis.from_url(REDIS_URL)
        r.rpush(RESULT_QUEUE, json.dumps({
            "workout_id": workout_id,
            "status":     "error",
            "error":      str(e),
        }))
    finally:
        db.close()


def run_consumer():
    """Бесконечный цикл — слушает очередь и обрабатывает задания."""
    r = redis.from_url(REDIS_URL)
    logger.info(f"[consumer] Слушаю очередь '{GENERATE_QUEUE}'...")

    while True:
        try:
            # blpop блокирует до появления сообщения (таймаут 5 сек)
            item = r.blpop(GENERATE_QUEUE, timeout=5)
            if item is None:
                continue

            _, raw = item
            job_data = json.loads(raw)
            process_job(job_data)

        except Exception as e:
            logger.error(f"[consumer] Ошибка в цикле: {e}")


def start_consumer_thread():
    """Запускает consumer в фоновом daemon-потоке."""
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()
    logger.info("[consumer] Фоновый поток запущен")
    return thread
