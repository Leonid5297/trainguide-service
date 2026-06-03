# ════════════════════════════════════════════════════════════════════════════
# ИЗМЕНЕНИЯ В settings.py
# ════════════════════════════════════════════════════════════════════════════

# ── ПРАВКА 1: добавь URL микросервиса (рядом с другими SERVICE_URL) ──────────
NOTIFICATION_SERVICE_URL = os.getenv('NOTIFICATION_SERVICE_URL', default='http://localhost:8003')


# ── ПРАВКА 2: подключи context processor ─────────────────────────────────────
# Найди TEMPLATES → 'OPTIONS' → 'context_processors' и добавь последней строкой:

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'workout.context_processors.notifications',   # ← ДОБАВИТЬ ЭТУ СТРОКУ
            ],
        },
    },
]
