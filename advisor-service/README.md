# advisor-service — AI-советник по тренировкам

FastAPI-микросервис на порту **8005**.
Принимает вопросы пользователей, отправляет их в Claude API
и сохраняет историю диалогов в свою БД.

> ⚡ В отличие от других микросервисов — **без Redis**.
> Взаимодействие только синхронное через HTTP, потому что пользователь ждёт ответа здесь и сейчас.

---

## Структура

```
advisor-service/
├── main.py              ← FastAPI + HTTP endpoints
├── database.py          ← SQLAlchemy: модель Conversation
├── requirements.txt
├── .env.example
├── README.md
└── django_changes/
    ├── workout/
    │   ├── views_advisor.py     → добавить 2 view в views.py
    │   ├── urls_advisor.py      → добавить 2 маршрута в urls.py
    │   └── settings_addition.py → добавить ADVISOR_SERVICE_URL
    └── templates/workout/
        └── advisor.html         → новая страница чата
```

---

## Как запустить

### 1. Создай БД
```sql
CREATE DATABASE advisordb;
-- юзер advisordb / пароль advisordb
```

### 2. Настрой .env и запусти
```bash
cp .env.example .env
# Впиши DATABASE_URL и ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload --port 8005
```

---

## Изменения в Django (по шагам)

1. **`workout/views.py`** — добавить константу и 2 view из `views_advisor.py`
2. **`workout/urls.py`** — добавить 2 маршрута из `urls_advisor.py`
3. **`settings.py`** — добавить `ADVISOR_SERVICE_URL`
4. **`workout/templates/workout/advisor.html`** — создать новый файл
5. **Навбар** — добавить ссылку «AI-советник» (опционально)

---

## Почему без Redis

```
Пользователь написал вопрос
        ↓
JS → POST /workout/advisor/ask/  (Django, AJAX)
        ↓
Django → POST http://localhost:8005/ask/  (синхронно, timeout=30)
        ↓
Микросервис → Claude API (5-15 сек)
        ↓
Ответ возвращается по той же цепочке обратно
        ↓
JS показывает ответ в чате
```

Redis здесь не нужен — пользователь смотрит на анимацию точек и ждёт ответа.
Асинхронность здесь не даёт выигрыша: результат нужен немедленно.

---

## HTTP API (для Postman)

| Метод  | URL                      | Описание                         |
|--------|--------------------------|----------------------------------|
| GET    | `/`                      | Статус сервиса                   |
| POST   | `/ask/`                  | Задать вопрос (основной endpoint)|
| GET    | `/history/{user_id}/`    | История диалогов пользователя    |
| GET    | `/history/`              | Все диалоги всех пользователей   |
| DELETE | `/history/{user_id}/`    | Очистить историю пользователя    |

---

## Пример для Postman — POST /ask/

```json
{
    "user_id": 1,
    "question": "Болит колено после приседаний. Что делать и можно ли продолжать тренировки?"
}
```

Ответ:
```json
{
    "user_id": 1,
    "question": "Болит колено после приседаний...",
    "answer": "При боли в колене после приседаний рекомендую...",
    "saved_id": 7
}
```

Документация: **http://localhost:8005/docs**
