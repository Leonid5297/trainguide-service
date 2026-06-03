# ── Добавь в settings.py ──────────────────────────────────────────────────────

REDIS_URL             = env('REDIS_URL', default='redis://localhost:6379')
WORKOUT_SERVICE_URL   = env('WORKOUT_SERVICE_URL',   default='http://localhost:8001')
ANALYTICS_SERVICE_URL = env('ANALYTICS_SERVICE_URL', default='http://localhost:8002')
