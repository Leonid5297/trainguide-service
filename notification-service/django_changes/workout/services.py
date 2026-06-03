import json
import logging
import redis
from django.conf import settings

from .claude_api import build_prompt

logger = logging.getLogger(__name__)

REDIS_URL           = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
GENERATE_QUEUE      = 'workout_generate_queue'
ANALYTICS_QUEUE     = 'analytics_queue'
NOTIFICATIONS_QUEUE = 'notifications_queue'


def push_generate_job(workout_id: int, user_id: int, form_data: dict):
    """Публикует задание на генерацию в очередь микросервиса генерации."""
    prompt = build_prompt(form_data)
    r = redis.from_url(REDIS_URL)
    r.rpush(GENERATE_QUEUE, json.dumps({
        'workout_id': workout_id,
        'user_id':    user_id,
        'prompt':     prompt,
    }))
    logger.info(f"[services] workout_id={workout_id} → {GENERATE_QUEUE}")


def publish_analytics_event(event: str, user_id: int, **kwargs):
    """Публикует аналитическое событие в очередь микросервиса аналитики."""
    try:
        payload = {'event': event, 'user_id': user_id, **kwargs}
        r = redis.from_url(REDIS_URL)
        r.rpush(ANALYTICS_QUEUE, json.dumps(payload))
        logger.info(f"[analytics] event={event} user_id={user_id} → {ANALYTICS_QUEUE}")
    except Exception as e:
        logger.warning(f"[analytics] Не удалось опубликовать событие: {e}")


def publish_notification(event: str, user_id: int, message: str):
    """
    Публикует уведомление в очередь микросервиса уведомлений.

    Примеры вызова:
        publish_notification('workout_ready', user_id=7,
                             message='Ваш план тренировок готов!')

        publish_notification('workout_completed', user_id=7,
                             message='Тренировка завершена! Отличная работа 🎉')
    """
    try:
        payload = {'event': event, 'user_id': user_id, 'message': message}
        r = redis.from_url(REDIS_URL)
        r.rpush(NOTIFICATIONS_QUEUE, json.dumps(payload))
        logger.info(f"[notif] event={event} user_id={user_id} → {NOTIFICATIONS_QUEUE}")
    except Exception as e:
        logger.warning(f"[notif] Не удалось опубликовать уведомление: {e}")
