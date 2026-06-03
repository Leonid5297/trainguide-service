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
EXPORT_QUEUE        = 'export_queue'


def push_generate_job(workout_id: int, user_id: int, form_data: dict):
    prompt = build_prompt(form_data)
    r = redis.from_url(REDIS_URL)
    r.rpush(GENERATE_QUEUE, json.dumps({
        'workout_id': workout_id,
        'user_id':    user_id,
        'prompt':     prompt,
    }))
    logger.info(f"[services] workout_id={workout_id} → {GENERATE_QUEUE}")


def publish_analytics_event(event: str, user_id: int, **kwargs):
    try:
        payload = {'event': event, 'user_id': user_id, **kwargs}
        r = redis.from_url(REDIS_URL)
        r.rpush(ANALYTICS_QUEUE, json.dumps(payload))
        logger.info(f"[analytics] event={event} user_id={user_id} → {ANALYTICS_QUEUE}")
    except Exception as e:
        logger.warning(f"[analytics] Не удалось опубликовать событие: {e}")


def publish_notification(event: str, user_id: int, message: str):
    try:
        payload = {'event': event, 'user_id': user_id, 'message': message}
        r = redis.from_url(REDIS_URL)
        r.rpush(NOTIFICATIONS_QUEUE, json.dumps(payload))
        logger.info(f"[notif] event={event} user_id={user_id} → {NOTIFICATIONS_QUEUE}")
    except Exception as e:
        logger.warning(f"[notif] Не удалось опубликовать уведомление: {e}")


def publish_export_job(workout_id: int, user_id: int, result: dict):
    """
    Публикует задание на генерацию PDF в очередь микросервиса экспорта.
    Передаёт полный JSON тренировки чтобы микросервис не ходил в Django за данными.
    """
    try:
        r = redis.from_url(REDIS_URL)
        r.rpush(EXPORT_QUEUE, json.dumps({
            'workout_id': workout_id,
            'user_id':    user_id,
            'result':     result,
        }))
        logger.info(f"[export] workout_id={workout_id} → {EXPORT_QUEUE}")
    except Exception as e:
        logger.warning(f"[export] Не удалось опубликовать задание: {e}")
