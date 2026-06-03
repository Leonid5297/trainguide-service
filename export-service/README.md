# export-service — Микросервис экспорта тренировок в PDF

FastAPI-микросервис на порту **8004**.
Принимает данные тренировки через Redis, генерирует красивый PDF через ReportLab
и отдаёт его на скачивание.

---

## Структура

```
export-service/
├── main.py              ← FastAPI + HTTP endpoints
├── database.py          ← SQLAlchemy: модель ExportJob
├── consumer.py          ← Redis consumer
├── pdf_generator.py     ← Генерация PDF через reportlab
├── files/               ← Папка с готовыми PDF файлами
├── requirements.txt
├── .env.example
├── README.md
└── django_changes/
    ├── workout/
    │   ├── services.py          → заменить (добавлен publish_export_job)
    │   ├── views_export.py      → добавить 3 view в views.py
    │   └── urls_additions.py    → добавить 3 маршрута в urls.py
    ├── export_button_patch.html → кнопка + JS для detail.html
    └── settings_addition.py     → добавить EXPORT_SERVICE_URL в settings.py
```

---

## Как запустить

### 1. Создай БД
```sql
CREATE DATABASE exportdb;
-- юзер exportdb / пароль exportdb
```

### 2. Настрой .env и запусти
```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload --port 8004
```

---

## Как это работает

```
Пользователь нажал «Скачать PDF» на странице тренировки
        ↓
JS → POST /workout/export/{pk}/request/  (Django)
        ↓
Django публикует в Redis:
export_queue → { workout_id, user_id, result: {...данные тренировки...} }
        ↓
Consumer микросервиса забирает задание
Генерирует PDF через reportlab → сохраняет в ./files/
Обновляет ExportJob(status='done', file_path=...)
        ↓
JS поллит каждые 1.5 сек:
GET /workout/export/status/{job_id}/  (Django)
        ↓
Django спрашивает микросервис:
GET http://localhost:8004/export/{job_id}/status/
        ↓
Когда status=done → JS делает window.location.href = download_url
        ↓
GET /workout/export/download/{job_id}/  (Django)
        ↓
Django проксирует файл от микросервиса к браузеру
        ↓
Браузер скачивает PDF
```

---

## Пять терминалов для запуска

```
Терминал 1: python manage.py runserver 8000        ← Django
Терминал 2: uvicorn main:app --reload --port 8001   ← workout-service
Терминал 3: uvicorn main:app --reload --port 8002   ← analytics-service
Терминал 4: uvicorn main:app --reload --port 8003   ← notification-service
Терминал 5: uvicorn main:app --reload --port 8004   ← export-service
```

---

## HTTP API (для Postman)

| Метод  | URL                            | Описание                          |
|--------|--------------------------------|-----------------------------------|
| GET    | `/`                            | Статус сервиса                    |
| POST   | `/export/`                     | Создать PDF синхронно (без Redis) |
| GET    | `/export/{job_id}/status/`     | Статус задания                    |
| GET    | `/export/{job_id}/download/`   | Скачать PDF                       |
| GET    | `/jobs/`                       | Список заданий                    |
| GET    | `/jobs/?status=done`           | Фильтр по статусу                 |
| GET    | `/queue/info/`                 | Состояние очереди                 |
| POST   | `/queue/push/`                 | Добавить в очередь вручную        |
| DELETE | `/export/{job_id}/`            | Удалить задание и файл            |

---

## Пример для Postman — POST /export/

```json
{
  "workout_id": 1,
  "user_id": 1,
  "result": {
    "title": "Силовая тренировка — Верх тела",
    "meta": {
      "duration": 60,
      "level": "Средний",
      "goal": "Набор мышечной массы",
      "location": "Тренажерный зал",
      "calories": 420
    },
    "warmup": [
      { "name": "Круговые вращения руками", "duration": "2 мин", "description": "Разогрев плечевых суставов" }
    ],
    "blocks": [
      {
        "name": "Грудь и трицепс",
        "exercises": [
          {
            "name": "Жим штанги лёжа",
            "sets": 4,
            "reps": "8-10",
            "rest": "90 сек",
            "weight": "70% от 1ПМ",
            "tip": "Лопатки сведены, спина слегка в арке",
            "muscles": ["Грудь", "Трицепс"]
          }
        ]
      }
    ],
    "cooldown": [
      { "name": "Растяжка грудных", "duration": "1 мин", "description": "Стоя в дверном проёме" }
    ],
    "tips": ["Пейте воду между подходами"]
  }
}
```

После выполнения → `GET /export/{job_id}/download/` → сохрани как `.pdf`

Документация: **http://localhost:8004/docs**
