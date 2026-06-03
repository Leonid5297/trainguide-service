import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_URL = getattr(
    settings, 'NOTIFICATION_SERVICE_URL', 'http://localhost:8003'
)


def notifications(request):
    """
    Context processor — добавляет счётчик непрочитанных уведомлений
    и список последних уведомлений во ВСЕ шаблоны (для навбара).

    Подключается в settings.py → TEMPLATES → OPTIONS → context_processors.
    """
    if not request.user.is_authenticated:
        return {}

    unread_count  = 0
    notifications_list = []

    try:
        # Счётчик непрочитанных
        resp = requests.get(
            f"{NOTIFICATION_SERVICE_URL}/notifications/{request.user.pk}/unread-count/",
            timeout=1.5,
        )
        if resp.status_code == 200:
            unread_count = resp.json().get('unread_count', 0)

        # Последние 5 уведомлений
        resp2 = requests.get(
            f"{NOTIFICATION_SERVICE_URL}/notifications/{request.user.pk}/?limit=5",
            timeout=1.5,
        )
        if resp2.status_code == 200:
            notifications_list = resp2.json()

    except requests.RequestException as e:
        # Сервис недоступен — навбар просто не покажет уведомления
        logger.warning(f"Сервис уведомлений недоступен: {e}")

    return {
        'notif_unread_count': unread_count,
        'notif_list':         notifications_list,
    }
