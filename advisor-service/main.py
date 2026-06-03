import os
import logging
import anthropic
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import create_tables, get_db, Conversation

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Ты — профессиональный фитнес-тренер и диетолог платформы TrainGuide.
Твоя задача — давать конкретные, полезные и безопасные советы по тренировкам, питанию и восстановлению.

Правила:
- Отвечай ТОЛЬКО на вопросы о тренировках, фитнесе, питании, восстановлении и здоровом образе жизни
- Давай конкретные практические советы, а не общие фразы
- Если вопрос связан с травмой или болью — рекомендуй обратиться к врачу
- Отвечай на русском языке
- Отвечай кратко — не более 150 слов
- НЕ используй markdown-форматирование: никаких ##, **, --, *курсив*, заголовков
- Пиши обычным текстом, разбивай на абзацы через перенос строки
- Если вопрос не по теме фитнеса — вежливо перенаправь к теме тренировок"""

app = FastAPI(
    title="Advisor Service",
    description="AI-советник по тренировкам TrainGuide на базе Claude",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic схемы ─────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    user_id:  int
    question: str


class AskResponse(BaseModel):
    user_id:  int
    question: str
    answer:   str
    saved_id: int


class ConversationOut(BaseModel):
    id:         int
    question:   str
    answer:     str
    created_at: datetime


# ── Старт ──────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    create_tables()
    logger.info("[advisor] Сервис запущен")


# ── Вспомогательная функция ────────────────────────────────────────────────────

def ask_claude(question: str) -> str:
    """Отправляет вопрос в Claude и возвращает текстовый ответ."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY не задан в .env")

    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    return message.content[0].text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# HTTP ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "service":     "advisor-service",
        "version":     "1.0.0",
        "status":      "running",
        "description": "AI-советник по тренировкам на базе Claude",
    }


@app.post("/ask/", response_model=AskResponse,
          summary="Задать вопрос AI-советнику")
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    """
    Главный endpoint — принимает вопрос, вызывает Claude API,
    сохраняет диалог в БД и возвращает ответ.

    Django вызывает его синхронно — без Redis, пользователь ждёт ответа.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Вопрос не может быть пустым")

    if len(payload.question) > 1000:
        raise HTTPException(status_code=400, detail="Вопрос слишком длинный (макс. 1000 символов)")

    logger.info(f"[advisor] user_id={payload.user_id} вопрос: {payload.question[:80]}...")

    try:
        answer = ask_claude(payload.question)
    except Exception as e:
        logger.error(f"[advisor] Ошибка Claude API: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка AI-советника: {str(e)}")

    # Сохраняем в БД
    conv = Conversation(
        user_id=payload.user_id,
        question=payload.question,
        answer=answer,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    logger.info(f"[advisor] Сохранён диалог id={conv.id}")

    return AskResponse(
        user_id=payload.user_id,
        question=payload.question,
        answer=answer,
        saved_id=conv.id,
    )


@app.get("/history/{user_id}/", summary="История диалогов пользователя")
def get_history(
    user_id: int,
    limit:   int = 20,
    db:      Session = Depends(get_db),
):
    """Возвращает историю вопросов и ответов пользователя."""
    convs = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.created_at.desc()).limit(limit).all()

    return [
        ConversationOut(
            id=c.id,
            question=c.question,
            answer=c.answer,
            created_at=c.created_at,
        )
        for c in convs
    ]


@app.get("/history/", summary="История всех диалогов")
def get_all_history(limit: int = 50, db: Session = Depends(get_db)):
    """Все диалоги всех пользователей — для администратора и Postman."""
    convs = db.query(Conversation).order_by(
        Conversation.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "id":         c.id,
            "user_id":    c.user_id,
            "question":   c.question[:100] + "..." if len(c.question) > 100 else c.question,
            "answer":     c.answer[:100]   + "..." if len(c.answer)   > 100 else c.answer,
            "created_at": c.created_at,
        }
        for c in convs
    ]


@app.delete("/history/{user_id}/", summary="Очистить историю пользователя")
def clear_history(user_id: int, db: Session = Depends(get_db)):
    deleted = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).delete()
    db.commit()
    return {"user_id": user_id, "deleted": deleted}
