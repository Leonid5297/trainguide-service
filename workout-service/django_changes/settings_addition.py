# ── Добавь в settings.py ──────────────────────────────────────────────────────

# Redis
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379')

# URL микросервиса генерации тренировок
WORKOUT_SERVICE_URL = env('WORKOUT_SERVICE_URL', default='http://localhost:8001')
