import os
import json
import logging
import redis
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import create_tables, get_db, GenerationJob
from generator import build_prompt, call_claude
from consumer import start_consumer_thread

load_dotenv()
logging.basicConfig(level=logging.INFO)

REDIS_URL      = os.getenv("REDIS_URL", "redis://localhost:6379")
GENERATE_QUEUE = "workout_generate_queue"
RESULT_QUEUE   = "workout_result_queue"

app = FastAPI(
    title="Workout Generation Service",
    description="Микросервис генерации тренировок TrainGuide через Claude API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic схемы ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Запрос на генерацию — принимается напрямую по HTTP (для Postman)."""
    workout_id: int
    user_id:    int
    form_data:  dict


class QueueRequest(BaseModel):
    """Принимает готовый промпт от Django через очередь."""
    workout_id: int
    user_id:    int
    prompt:     str


class JobStatusResponse(BaseModel):
    workout_id:  int
    user_id:     int
    status:      str
    result:      Optional[dict] = None
    error_msg:   Optional[str]  = None
    created_at:  datetime
    finished_at: Optional[datetime] = None


# ── Старт приложения ───────────────────────────────────────────────────────────

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
        "service": "workout-generation-service",
        "version": "1.0.0",
        "status":  "running",
        "queue":   GENERATE_QUEUE,
    }


@app.post("/generate/", summary="Сгенерировать тренировку (синхронно, для Postman)")
def generate_sync(payload: GenerateRequest, db: Session = Depends(get_db)):
    """
    Принимает form_data → формирует промпт → вызывает Claude API → возвращает результат.
    Используется для прямого тестирования через Postman без Redis.
    """
    # Проверяем нет ли уже задания с таким workout_id
    existing = db.query(GenerationJob).filter(
        GenerationJob.workout_id == payload.workout_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Задание для workout_id={payload.workout_id} уже существует"
        )

    prompt = build_prompt(payload.form_data)

    job = GenerationJob(
        workout_id=payload.workout_id,
        user_id=payload.user_id,
        prompt=prompt,
        status="processing",
    )
    db.add(job)
    db.commit()

    try:
        result = call_claude(prompt)
        job.result      = result
        job.status      = "done"
        job.finished_at = datetime.utcnow()
        db.commit()
        return {
            "workout_id": payload.workout_id,
            "status":     "done",
            "result":     result,
        }
    except Exception as e:
        job.status    = "error"
        job.error_msg = str(e)
        job.finished_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job/{workout_id}/", response_model=JobStatusResponse,
         summary="Получить статус/результат задания")
def get_job(workout_id: int, db: Session = Depends(get_db)):
    """
    Возвращает статус и результат генерации по workout_id.
    Django поллит этот endpoint каждые 2 сек пока статус != done/error.
    """
    job = db.query(GenerationJob).filter(
        GenerationJob.workout_id == workout_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    return JobStatusResponse(
        workout_id=job.workout_id,
        user_id=job.user_id,
        status=job.status,
        result=job.result,
        error_msg=job.error_msg,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@app.get("/jobs/", summary="Список всех заданий")
def list_jobs(
    status: Optional[str] = None,
    limit:  int = 20,
    db: Session = Depends(get_db),
):
    """Список заданий с опциональной фильтрацией по статусу."""
    query = db.query(GenerationJob)
    if status:
        query = query.filter(GenerationJob.status == status)
    jobs = query.order_by(GenerationJob.created_at.desc()).limit(limit).all()

    return [
        {
            "workout_id":  j.workout_id,
            "user_id":     j.user_id,
            "status":      j.status,
            "created_at":  j.created_at,
            "finished_at": j.finished_at,
        }
        for j in jobs
    ]


@app.delete("/job/{workout_id}/", summary="Удалить задание")
def delete_job(workout_id: int, db: Session = Depends(get_db)):
    """Удаляет задание из БД микросервиса."""
    job = db.query(GenerationJob).filter(
        GenerationJob.workout_id == workout_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    db.delete(job)
    db.commit()
    return {"detail": f"Задание workout_id={workout_id} удалено"}


@app.get("/queue/info/", summary="Информация об очередях Redis")
def queue_info():
    """Показывает количество сообщений в очередях."""
    r = redis.from_url(REDIS_URL)
    return {
        "generate_queue": {
            "name":  GENERATE_QUEUE,
            "count": r.llen(GENERATE_QUEUE),
        },
        "result_queue": {
            "name":  RESULT_QUEUE,
            "count": r.llen(RESULT_QUEUE),
        },
    }


@app.post("/queue/push/", summary="Вручную добавить задание в очередь Redis")
def push_to_queue(payload: QueueRequest):
    """
    Добавляет задание в Redis-очередь вручную (для тестирования).
    В реальной работе это делает Django автоматически.
    """
    r = redis.from_url(REDIS_URL)
    r.rpush(GENERATE_QUEUE, json.dumps({
        "workout_id": payload.workout_id,
        "user_id":    payload.user_id,
        "prompt":     payload.prompt,
    }))
    return {
        "detail":     "Задание добавлено в очередь",
        "workout_id": payload.workout_id,
        "queue":      GENERATE_QUEUE,
        "queue_size": r.llen(GENERATE_QUEUE),
    }
