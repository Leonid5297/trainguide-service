# schedule-service — Сервис расписания тренировок

FastAPI-микросервис на порту **8006**.
Хранит расписания тренировок пользователей и автоматически отправляет
напоминания через Redis в нужное время.

> ⚡ Ключевое отличие: этот сервис сам **инициирует события** по расписанию,
> а не реагирует на чужие. Использует библиотеку `schedule` для cron-подобной логики.

---

## Структура

```
schedule-service/
├── main.py              ← FastAPI + HTTP endpoints
├── database.py          ← SQLAlchemy: WorkoutSchedule + ReminderLog
├── scheduler.py         ← Фоновый поток с проверкой расписаний каждую минуту
├── requirements.txt
├── .env.example
├── README.md
└── django_changes/
    ├── workout/
    │   ├── views_schedule.py    → добавить 2 view в views.py
    │   ├── urls_schedule.py     → добавить 2 маршрута в urls.py
    │   └── settings_addition.py → добавить SCHEDULE_SERVICE_URL
    └── templates/workout/
        └── schedule.html        → новая страница расписания
```

---

## Как запустить

### 1. Создай БД
```sql
CREATE DATABASE scheduledb;
-- юзер scheduledb / пароль scheduledb
```

### 2. Настрой .env и запусти
```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload --port 8006
```

---

## Как это работает

```
Пользователь настроил расписание: пн/ср/пт в 08:00
        ↓
POST /schedule/ → сохранено в scheduledb
        ↓
Фоновый поток (scheduler.py) проверяет каждую минуту:
  - Сегодня пятница? ✓
  - Сейчас 08:00? ✓
  - Уже отправляли сегодня? ✗
        ↓
rpush notifications_queue → { event: "workout_reminder", user_id, message }
        ↓
notification-service забирает из очереди
Сохраняет уведомление в notifdb
        ↓
Пользователь видит уведомление в колокольчике навбара
```

---

## Как протестировать без ожидания нужного времени

```
POST /remind/send-now/?user_id=1     ← сразу отправляет напоминание в очередь
POST /scheduler/run-now/             ← запускает проверку всех расписаний прямо сейчас
```

---

## Шесть терминалов

```
Терминал 1: python manage.py runserver 8000        ← Django
Терминал 2: uvicorn main:app --reload --port 8001   ← workout-service
Терминал 3: uvicorn main:app --reload --port 8002   ← analytics-service
Терминал 4: uvicorn main:app --reload --port 8003   ← notification-service
Терминал 5: uvicorn main:app --reload --port 8004   ← export-service
Терминал 6: uvicorn main:app --reload --port 8005   ← advisor-service
Терминал 7: uvicorn main:app --reload --port 8006   ← schedule-service
```

---

## HTTP API (для Postman)

| Метод  | URL                              | Описание                            |
|--------|----------------------------------|-------------------------------------|
| GET    | `/`                              | Статус сервиса                      |
| POST   | `/schedule/`                     | Создать/обновить расписание         |
| GET    | `/schedule/{user_id}/`           | Получить расписание пользователя    |
| PATCH  | `/schedule/{user_id}/toggle/`    | Включить/выключить                  |
| DELETE | `/schedule/{user_id}/`           | Удалить расписание                  |
| GET    | `/schedules/`                    | Все расписания                      |
| POST   | `/remind/send-now/?user_id=1`    | Отправить напоминание сейчас        |
| POST   | `/scheduler/run-now/`            | Проверить все расписания сейчас     |
| GET    | `/logs/{user_id}/`               | Лог напоминаний                     |

---

## Пример для Postman — POST /schedule/

```json
{
    "user_id": 1,
    "days": ["mon", "wed", "fri"],
    "remind_time": "08:00",
    "is_active": true
}
```

Документация: **http://localhost:8006/docs**
