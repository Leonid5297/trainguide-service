import json
import os
import threading
import logging
import redis
from datetime import datetime
from dotenv import load_dotenv

from database import SessionLocal, ExportJob
from pdf_generator import build_pdf

load_dotenv()

logger      = logging.getLogger(__name__)
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
EXPORT_QUEUE = "export_queue"
FILES_DIR   = os.getenv("FILES_DIR", "./files")

# Создаём папку для файлов если не существует
os.makedirs(FILES_DIR, exist_ok=True)


def process_job(job_data: dict):
    """Обрабатывает одно задание: генерирует PDF и сохраняет путь."""
    workout_id = job_data.get("workout_id")
    user_id    = job_data.get("user_id")
    result     = job_data.get("result")

    if not workout_id or not result:
        logger.warning(f"[export] Некорректные данные задания: {job_data}")
        return

    db = SessionLocal()
    try:
        # Создаём запись в БД
        job = ExportJob(
            workout_id=workout_id,
            user_id=user_id,
            status="processing",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"[export] Генерирую PDF для workout_id={workout_id}")

        # Имя файла
        file_name = f"workout_{workout_id}_user_{user_id}.pdf"
        file_path = os.path.join(FILES_DIR, file_name)

        # Генерируем PDF
        build_pdf(result, workout_id, file_path)

        # Обновляем запись
        job.status      = "done"
        job.file_path   = file_path
        job.file_name   = file_name
        job.finished_at = datetime.utcnow()
        db.commit()

        logger.info(f"[export] PDF готов: {file_path}")

    except Exception as e:
        logger.error(f"[export] Ошибка генерации PDF: {e}")
        if 'job' in locals():
            job.status    = "error"
            job.error_msg = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def run_consumer():
    r = redis.from_url(REDIS_URL)
    logger.info(f"[export] Слушаю очередь '{EXPORT_QUEUE}'...")

    while True:
        try:
            item = r.blpop(EXPORT_QUEUE, timeout=5)
            if item is None:
                continue
            _, raw    = item
            job_data  = json.loads(raw)
            logger.info(f"[export] Получил задание workout_id={job_data.get('workout_id')}")
            process_job(job_data)
        except Exception as e:
            logger.error(f"[export] Ошибка в цикле: {e}")


def start_consumer_thread():
    thread = threading.Thread(target=run_consumer, daemon=True)
    thread.start()
    logger.info("[export] Фоновый поток запущен")
    return thread
