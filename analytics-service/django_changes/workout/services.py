import json
import logging
import redis
from django.conf import settings

from .claude_api import build_prompt

logger = logging.getLogger(__name__)

REDIS_URL       = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
GENERATE_QUEUE  = 'workout_generate_queue'
ANALYTICS_QUEUE = 'analytics_queue'


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
    """
    Публикует аналитическое событие в очередь микросервиса аналитики.

    Примеры вызова:
        publish_analytics_event('workout_generated', user_id=7,
                                workout_id=42, goal='Похудение', duration='45-60 минут')

        publish_analytics_event('workout_completed', user_id=7,
                                workout_id=42, exercises_done=8, exercises_total=10)
    """
    try:
        payload = {'event': event, 'user_id': user_id, **kwargs}
        r = redis.from_url(REDIS_URL)
        r.rpush(ANALYTICS_QUEUE, json.dumps(payload))
        logger.info(f"[analytics] event={event} user_id={user_id} → {ANALYTICS_QUEUE}")
    except Exception as e:
        # Не ломаем основной поток если Redis недоступен
        logger.warning(f"[analytics] Не удалось опубликовать событие: {e}")
