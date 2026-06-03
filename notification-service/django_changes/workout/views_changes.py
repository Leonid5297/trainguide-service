# ════════════════════════════════════════════════════════════════════════════
# ИЗМЕНЕНИЯ В workout/views.py
# ════════════════════════════════════════════════════════════════════════════
#
# Это НЕ полный файл — только точечные правки. Внеси их в свой views.py.

# ── ПРАВКА 1: импорт ──────────────────────────────────────────────────────────
# Было:
from .services import push_generate_job, publish_analytics_event
# Стало:
from .services import push_generate_job, publish_analytics_event, publish_notification


# ── ПРАВКА 2: в workout_status, когда тренировка СГЕНЕРИРОВАНА ────────────────
# Найди этот блок в функции workout_status():
#
#     if data['status'] == 'done' and data.get('result'):
#         workout.result = data['result']
#         workout.status = Workout.Status.DONE
#         workout.save()
#         return JsonResponse({'status': 'done', 'workout_id': pk})
#
# И добавь публикацию уведомления ПЕРЕД return:

            if data['status'] == 'done' and data.get('result'):
                workout.result = data['result']
                workout.status = Workout.Status.DONE
                workout.save()

                # ── Уведомление: план готов ──────────────────────────────────
                title = data['result'].get('title', 'тренировка')
                publish_notification(
                    event='workout_ready',
                    user_id=request.user.pk,
                    message=f'Ваш план «{title}» готов!',
                )

                return JsonResponse({'status': 'done', 'workout_id': pk})


# ── ПРАВКА 3: в complete_session, когда тренировка ЗАВЕРШЕНА ──────────────────
# Найди функцию complete_session() и добавь публикацию уведомления
# рядом с уже существующим publish_analytics_event:

    # ── Публикуем аналитическое событие (уже есть) ───────────────────────────
    publish_analytics_event(
        event='workout_completed',
        user_id=request.user.pk,
        workout_id=workout.pk,
        exercises_done=session.done_count,
        exercises_total=session.total_exercises,
    )

    # ── Публикуем уведомление (ДОБАВИТЬ) ─────────────────────────────────────
    publish_notification(
        event='workout_completed',
        user_id=request.user.pk,
        message='Тренировка завершена! Отличная работа 🎉',
    )
