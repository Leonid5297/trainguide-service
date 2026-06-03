# notification-service — Микросервис уведомлений

FastAPI-микросервис на порту **8003**.
Слушает Redis-очередь `notifications_queue`, сохраняет уведомления в свою БД,
Django показывает их в колокольчике навбара.

---

## Структура

```
notification-service/
├── main.py              ← FastAPI + HTTP endpoints
├── database.py          ← SQLAlchemy: модель Notification
├── consumer.py          ← Redis consumer
├── requirements.txt
├── .env.example
├── README.md
└── django_changes/
    ├── workout/
    │   ├── services.py                      → заменить (добавлен publish_notification)
    │   ├── views_changes.py                 → точечные правки views.py
    │   ├── views_notifications_endpoint.py  → добавить эндпоинт mark_notifications_read
    │   └── context_processors.py            → новый файл workout/context_processors.py
    ├── templates/
    │   └── navbar_bell.html                 → вставить колокольчик в base.html
    └── settings_changes.py                  → правки settings.py
```

---

## Как запустить

### 1. Создай БД
```sql
CREATE DATABASE notifdb;
-- юзер notifdb / пароль notifdb / все права
```

### 2. Настрой .env и запусти
```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload --port 8003
```

---

## Изменения в Django (по шагам)

1. **`workout/services.py`** — замени на новый (добавлена функция `publish_notification`)
2. **`workout/context_processors.py`** — создай новый файл (из `django_changes/workout/`)
3. **`workout/views.py`** — внеси правки из `views_changes.py` и добавь эндпоинт из `views_notifications_endpoint.py`
4. **`workout/urls.py`** — добавь маршрут:
   ```python
   path('notifications/read/', views.mark_notifications_read, name='notifications_read'),
   ```
5. **`settings.py`** — добавь `NOTIFICATION_SERVICE_URL` и context processor (см. `settings_changes.py`)
6. **`templates/base.html`** — вставь колокольчик из `navbar_bell.html`

---

## Четыре терминала для запуска всего проекта

```
Терминал 1: python manage.py runserver 8000        ← Django
Терминал 2: uvicorn main:app --reload --port 8001   ← workout-service
Терминал 3: uvicorn main:app --reload --port 8002   ← analytics-service
Терминал 4: uvicorn main:app --reload --port 8003   ← notification-service
```

---

## HTTP API (для Postman)

| Метод  | URL                                        | Описание                       |
|--------|--------------------------------------------|--------------------------------|
| GET    | `/`                                        | Статус сервиса                 |
| GET    | `/notifications/{user_id}/`                | Список уведомлений             |
| GET    | `/notifications/{user_id}/unread-count/`   | Счётчик непрочитанных          |
| POST   | `/notifications/{user_id}/read/`           | Отметить все прочитанными      |
| POST   | `/notifications/{id}/read-one/`            | Прочитать одно                 |
| POST   | `/event/`                                  | Создать напрямую (Postman)     |
| GET    | `/queue/info/`                             | Состояние очереди              |
| POST   | `/queue/push/`                             | Добавить в очередь вручную     |
| DELETE | `/notifications/{user_id}/`                | Удалить все уведомления        |

---

## Примеры для Postman

### POST /event/ — создать напрямую
```json
{
    "event": "workout_ready",
    "user_id": 1,
    "message": "Ваш план «Силовая тренировка» готов!"
}
```

### POST /queue/push/ — через Redis (демо асинхронности)
```json
{
    "event": "workout_completed",
    "user_id": 1,
    "message": "Тренировка завершена! Отличная работа 🎉"
}
```

### GET /notifications/1/ — список
Ответ:
```json
[
    {
        "id": 2,
        "event_type": "workout_completed",
        "message": "Тренировка завершена! Отличная работа 🎉",
        "is_read": false,
        "created_at": "2026-05-24T12:30:00"
    }
]
```

Документация: **http://localhost:8003/docs**
