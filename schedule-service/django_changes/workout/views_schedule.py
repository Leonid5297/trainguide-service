# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/views.py
# ════════════════════════════════════════════════════════════════════════════
#
# 1. Добавь константу:
#    SCHEDULE_SERVICE_URL = getattr(settings, 'SCHEDULE_SERVICE_URL', 'http://localhost:8006')
#
# 2. Добавь два view:

DAYS_RU = {
    'mon': 'Пн', 'tue': 'Вт', 'wed': 'Ср',
    'thu': 'Чт', 'fri': 'Пт', 'sat': 'Сб', 'sun': 'Вс',
}
DAYS_ORDER = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


@login_required
def schedule(request):
    """
    GET  — показывает текущее расписание пользователя.
    POST — сохраняет новое расписание через микросервис.
    """
    current_schedule = None
    error = None

    if request.method == 'POST':
        days        = request.POST.getlist('days')
        remind_time = request.POST.get('remind_time', '08:00')
        is_active   = request.POST.get('is_active') == 'on'

        try:
            resp = requests.post(
                f"{SCHEDULE_SERVICE_URL}/schedule/",
                json={
                    'user_id':     request.user.pk,
                    'days':        days,
                    'remind_time': remind_time,
                    'is_active':   is_active,
                },
                timeout=5,
            )
            if resp.status_code == 200:
                messages.success(request, 'Расписание сохранено!')
            else:
                error = resp.json().get('detail', 'Ошибка сохранения')
                messages.error(request, error)

        except requests.RequestException:
            messages.error(request, 'Сервис расписания недоступен.')

        return redirect('workout:schedule')

    # GET — загружаем текущее расписание
    try:
        resp = requests.get(
            f"{SCHEDULE_SERVICE_URL}/schedule/{request.user.pk}/",
            timeout=3,
        )
        if resp.status_code == 200:
            current_schedule = resp.json()
    except requests.RequestException:
        pass

    return render(request, 'workout/schedule.html', {
        'current_schedule': current_schedule,
        'days_ru':          DAYS_RU,
        'days_order':       DAYS_ORDER,
    })


@login_required
@require_POST
def schedule_toggle(request):
    """AJAX — включить/выключить расписание."""
    try:
        resp = requests.patch(
            f"{SCHEDULE_SERVICE_URL}/schedule/{request.user.pk}/toggle/",
            timeout=3,
        )
        if resp.status_code == 200:
            return JsonResponse(resp.json())
    except requests.RequestException:
        pass
    return JsonResponse({'error': 'Сервис недоступен'}, status=503)
