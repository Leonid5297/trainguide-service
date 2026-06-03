# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/views.py
# ════════════════════════════════════════════════════════════════════════════

import requests  # уже импортирован в твоём views.py

NOTIFICATION_SERVICE_URL = getattr(
    settings, 'NOTIFICATION_SERVICE_URL', 'http://localhost:8003'
)


@login_required
@require_POST
def mark_notifications_read(request):
    """
    Отмечает все уведомления пользователя прочитанными.
    Вызывается AJAX-запросом когда пользователь открыл колокольчик.
    """
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notifications/{request.user.pk}/read/",
            timeout=2,
        )
    except requests.RequestException:
        pass
    return JsonResponse({'status': 'ok'})


# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/urls.py
# ════════════════════════════════════════════════════════════════════════════
#
#   path('notifications/read/', views.mark_notifications_read, name='notifications_read'),
