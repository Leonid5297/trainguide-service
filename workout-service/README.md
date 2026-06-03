# workout-service — Микросервис генерации тренировок

FastAPI-микросервис на порту **8001**, который принимает задания из Redis,
вызывает Claude API и возвращает готовый JSON тренировки.

---

## Структура

```
workout-service/
├── main.py            ← FastAPI приложение, все HTTP endpoints
├── database.py        ← SQLAlchemy модель GenerationJob
├── generator.py       ← build_prompt() + call_claude()
├── consumer.py        ← Redis consumer в фоновом потоке
├── requirements.txt
├── .env.example
├── README.md
└── django_changes/    ← Только изменённые файлы для Django
    ├── services.py    → заменить workout/services.py (новый файл)
    ├── views.py       → заменить workout/views.py
    ├── urls.py        → заменить workout/urls.py
    ├── detail.html    → заменить workout/templates/workout/detail.html
    └── settings_addition.py  → добавить строки в settings.py
```

---

## Как запустить

### 1. Создай .env файл
```bash
cp .env.example .env
# Отредактируй .env — впиши DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY
```

### 2. Создай базу данных микросервиса
```sql
CREATE DATABASE workout_service;
```

### 3. Установи зависимости и запусти
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Таблицы создадутся автоматически при старте.

### 4. Добавь в Django settings.py
```python
REDIS_URL           = 'redis://localhost:6379'
WORKOUT_SERVICE_URL = 'http://localhost:8001'
```

### 5. Установи redis в Django-проекте
```bash
pip install redis requests
```

---

## Как это работает

```
Пользователь отправляет форму
        ↓
Django создаёт Workout(status='pending') в своей БД
Django публикует задание в Redis: workout_generate_queue
Django редиректит на detail.html (показывает спиннер)
        ↓
[фоновый поток микросервиса]
consumer.py забирает задание из Redis
Вызывает Claude API (5-10 сек)
Сохраняет результат в свою БД (generation_jobs)
Публикует результат в Redis: workout_result_queue
        ↓
JS на detail.html каждые 2 сек опрашивает:
GET /workout/status/<pk>/  (Django endpoint)
        ↓
Django спрашивает микросервис:
GET http://localhost:8001/job/<workout_id>/
        ↓
Когда status == 'done':
Django сохраняет result в свою Workout модель
JS перезагружает страницу → пользователь видит тренировку
```

---

## HTTP API (для Postman)

| Метод | URL | Описание |
|-------|-----|----------|
| GET  | `/` | Статус сервиса |
| POST | `/generate/` | Сгенерировать синхронно (без Redis) |
| GET  | `/job/{workout_id}/` | Статус/результат задания |
| GET  | `/jobs/` | Список всех заданий |
| GET  | `/jobs/?status=done` | Фильтр по статусу |
| DELETE | `/job/{workout_id}/` | Удалить задание |
| GET  | `/queue/info/` | Состояние очередей Redis |
| POST | `/queue/push/` | Добавить задание в очередь вручную |

### Пример запроса для Postman — POST /generate/
```json
{
  "workout_id": 999,
  "user_id": 1,
  "form_data": {
    "experience": "Средний (6-12 месяцев)",
    "frequency": "3 раза",
    "duration": "45-60 минут",
    "location": "Тренажерный зал",
    "equipment": "Полный зал",
    "goal": "Набор мышечной массы",
    "workout_types": ["Силовые тренировки"],
    "muscles": ["Грудь", "Трицепс"],
    "intensity": "Высокая (интенсивная)",
    "body_type": "Мезоморф (атлетичный)",
    "gender": "Мужской",
    "age": 25,
    "weight": 80,
    "height": 180,
    "injuries": ["Без травм"],
    "focus": "",
    "notes": ""
  }
}
```

### Интерактивная документация
После запуска доступна по адресу: **http://localhost:8001/docs**
