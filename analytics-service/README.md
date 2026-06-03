# analytics-service — Микросервис аналитики тренировок

FastAPI-микросервис на порту **8002**.
Слушает Redis-очередь `analytics_queue`, считает статистику пользователей
и отдаёт её Django по HTTP при открытии профиля.

---

## Структура

```
analytics-service/
├── main.py              ← FastAPI приложение, все HTTP endpoints
├── database.py          ← SQLAlchemy: analytics_events + user_stats
├── consumer.py          ← Redis consumer + пересчёт агрегатов
├── requirements.txt
├── .env.example
├── README.md
└── django_changes/      ← Только изменённые файлы Django
    ├── workout/
    │   ├── services.py  → заменить workout/services.py
    │   └── views.py     → заменить workout/views.py
    └── account/
        ├── views.py     → заменить account/views.py
        └── profile_stats_patch.html → заменить блок статистики в profile.html
```

---

## Как запустить

### 1. Создай базу данных
```sql
CREATE DATABASE analyticsdb;
-- создай юзера analyticsdb с паролем analyticsdb и дай права на базу
```

### 2. Настрой .env
```bash
cp .env.example .env
```

### 3. Установи зависимости и запусти
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

---

## Добавь в Django settings.py

```python
ANALYTICS_SERVICE_URL = 'http://localhost:8002'
```

---

## Три терминала для запуска всего проекта

```
Терминал 1: python manage.py runserver 8000       ← Django
Терминал 2: uvicorn main:app --reload --port 8001  ← workout-service
Терминал 3: uvicorn main:app --reload --port 8002  ← analytics-service
```

---

## Как это работает

```
1. Пользователь создал тренировку
   Django → rpush analytics_queue → { event: workout_generated, user_id, goal, ... }

2. Пользователь нажал «Завершить тренировку»
   Django → rpush analytics_queue → { event: workout_completed, user_id, exercises_done, ... }

3. Consumer микросервиса забирает событие из Redis
   Сохраняет в analytics_events (сырые данные)
   Пересчитывает user_stats (агрегаты)

4. Пользователь открывает профиль
   Django → GET http://localhost:8002/stats/{user_id}/
   Микросервис читает user_stats и возвращает JSON
   Django передаёт stats в шаблон профиля
```

---

## HTTP API (для Postman)

| Метод  | URL                      | Описание                              |
|--------|--------------------------|---------------------------------------|
| GET    | `/`                      | Статус сервиса                        |
| GET    | `/stats/{user_id}/`      | Статистика пользователя               |
| GET    | `/stats/`                | Статистика всех пользователей         |
| GET    | `/events/{user_id}/`     | История сырых событий пользователя    |
| POST   | `/event/`                | Отправить событие напрямую (Postman)  |
| GET    | `/queue/info/`           | Состояние очереди Redis               |
| POST   | `/queue/push/`           | Добавить событие в очередь вручную    |
| DELETE | `/stats/{user_id}/`      | Сбросить статистику пользователя      |

---

## Примеры запросов для Postman

### POST /event/ — напрямую без Redis
```json
{
    "event": "workout_generated",
    "user_id": 1,
    "workout_id": 42,
    "goal": "Набор мышечной массы",
    "duration": "45-60 минут"
}
```

```json
{
    "event": "workout_completed",
    "user_id": 1,
    "workout_id": 42,
    "exercises_done": 8,
    "exercises_total": 10
}
```

### POST /queue/push/ — через Redis (демонстрация асинхронности)
```json
{
    "event": "workout_generated",
    "user_id": 1,
    "workout_id": 99,
    "goal": "Похудение",
    "duration": "30-45 минут"
}
```

### GET /stats/1/ — получить статистику пользователя
Ответ:
```json
{
    "user_id": 1,
    "total_generated": 5,
    "total_completed": 3,
    "completion_rate": 60.0,
    "avg_exercises_done": 80.0,
    "favorite_goal": "Набор мышечной массы",
    "current_streak": 2,
    "updated_at": "2026-05-18T14:00:00"
}
```

Интерактивная документация: **http://localhost:8002/docs**
