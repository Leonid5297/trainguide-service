import os
import json
import logging
import redis
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import create_tables, get_db, ExportJob
from consumer import start_consumer_thread, process_job

load_dotenv()
logging.basicConfig(level=logging.INFO)

REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379")
EXPORT_QUEUE = "export_queue"
FILES_DIR    = os.getenv("FILES_DIR", "./files")

app = FastAPI(
    title="Export Service",
    description="Микросервис экспорта тренировок в PDF — TrainGuide",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic схемы ─────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    workout_id: int
    user_id:    int
    result:     dict


class QueueRequest(BaseModel):
    workout_id: int
    user_id:    int
    result:     dict


class JobStatusResponse(BaseModel):
    id:          int
    workout_id:  int
    user_id:     int
    status:      str
    file_name:   Optional[str] = None
    error_msg:   Optional[str] = None
    created_at:  datetime
    finished_at: Optional[datetime] = None


# ── Старт ──────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    os.makedirs(FILES_DIR, exist_ok=True)
    create_tables()
    start_consumer_thread()


# ══════════════════════════════════════════════════════════════════════════════
# HTTP ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "service": "export-service",
        "version": "1.0.0",
        "status":  "running",
        "queue":   EXPORT_QUEUE,
    }


@app.post("/export/", summary="Создать PDF синхронно (для Postman)")
def export_sync(payload: ExportRequest, db: Session = Depends(get_db)):
    """
    Синхронно генерирует PDF без Redis.
    Отлично для демонстрации в Postman — сразу возвращает job_id.
    """
    job_data = {
        "workout_id": payload.workout_id,
        "user_id":    payload.user_id,
        "result":     payload.result,
    }
    process_job(job_data)

    job = db.query(ExportJob).filter(
        ExportJob.workout_id == payload.workout_id
    ).order_by(ExportJob.created_at.desc()).first()

    if not job:
        raise HTTPException(status_code=500, detail="Ошибка создания задания")

    return {
        "job_id":     job.id,
        "workout_id": job.workout_id,
        "status":     job.status,
        "file_name":  job.file_name,
        "message":    "PDF сгенерирован. Скачай через GET /export/{job_id}/download/",
    }


@app.get("/export/{job_id}/status/", response_model=JobStatusResponse,
         summary="Статус задания на экспорт")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """
    Django поллит этот endpoint пока status != done.
    """
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    return JobStatusResponse(
        id=job.id,
        workout_id=job.workout_id,
        user_id=job.user_id,
        status=job.status,
        file_name=job.file_name,
        error_msg=job.error_msg,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@app.get("/export/{job_id}/download/", summary="Скачать PDF")
def download_pdf(job_id: int, db: Session = Depends(get_db)):
    """
    Отдаёт PDF-файл на скачивание.
    В Postman: нажми Send → файл появится в ответе → Save Response → сохрани как .pdf
    """
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"PDF ещё не готов, статус: {job.status}")
    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на диске")

    return FileResponse(
        path=job.file_path,
        media_type="application/pdf",
        filename=job.file_name,
    )


@app.get("/jobs/", summary="Список всех заданий")
def list_jobs(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    limit:  int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(ExportJob)
    if status:
        query = query.filter(ExportJob.status == status)
    if user_id:
        query = query.filter(ExportJob.user_id == user_id)

    jobs = query.order_by(ExportJob.created_at.desc()).limit(limit).all()
    return [
        {
            "id":          j.id,
            "workout_id":  j.workout_id,
            "user_id":     j.user_id,
            "status":      j.status,
            "file_name":   j.file_name,
            "created_at":  j.created_at,
            "finished_at": j.finished_at,
        }
        for j in jobs
    ]


@app.get("/queue/info/", summary="Состояние очереди Redis")
def queue_info():
    r = redis.from_url(REDIS_URL)
    return {"queue": EXPORT_QUEUE, "count": r.llen(EXPORT_QUEUE)}


@app.post("/queue/push/", summary="Добавить задание в очередь вручную")
def push_to_queue(payload: QueueRequest):
    """Для демонстрации асинхронного потока через Postman."""
    r = redis.from_url(REDIS_URL)
    r.rpush(EXPORT_QUEUE, json.dumps({
        "workout_id": payload.workout_id,
        "user_id":    payload.user_id,
        "result":     payload.result,
    }))
    return {
        "detail":     "Задание добавлено в очередь",
        "workout_id": payload.workout_id,
        "queue_size": r.llen(EXPORT_QUEUE),
    }


@app.delete("/export/{job_id}/", summary="Удалить задание и файл")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # Удаляем файл с диска
    if job.file_path and os.path.exists(job.file_path):
        os.remove(job.file_path)

    db.delete(job)
    db.commit()
    return {"detail": f"Задание {job_id} и файл удалены"}
