# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/views.py
# ════════════════════════════════════════════════════════════════════════════
#
# 1. Добавь импорт в начало файла:
#    from .services import ..., publish_export_job
#
# 2. Добавь константу рядом с другими SERVICE_URL:
#    EXPORT_SERVICE_URL = getattr(settings, 'EXPORT_SERVICE_URL', 'http://localhost:8004')
#
# 3. Добавь два view ниже:

@login_required
@require_POST
def request_export(request, pk):
    """
    POST — пользователь нажал «Скачать PDF» на странице тренировки.
    Публикует задание в Redis и возвращает job_id для поллинга.
    """
    workout = get_object_or_404(Workout, pk=pk, user=request.user)

    if workout.status != Workout.Status.DONE or not workout.result:
        return JsonResponse({'error': 'Тренировка ещё не готова'}, status=400)

    # Публикуем в Redis → export-service сгенерирует PDF
    publish_export_job(
        workout_id=workout.pk,
        user_id=request.user.pk,
        result=workout.result,
    )

    # Узнаём job_id у микросервиса (он только что создал запись)
    # Небольшая задержка чтобы consumer успел создать запись
    import time
    time.sleep(0.3)

    try:
        resp = requests.get(
            f"{EXPORT_SERVICE_URL}/jobs/?workout_id={workout.pk}&limit=1",
            timeout=3,
        )
        if resp.status_code == 200:
            jobs = resp.json()
            if jobs:
                job_id = jobs[0]['id']
                return JsonResponse({'job_id': job_id, 'status': 'pending'})
    except requests.RequestException:
        pass

    return JsonResponse({'error': 'Не удалось создать задание'}, status=500)


@login_required
def export_status(request, job_id):
    """
    GET — JS поллит этот endpoint пока PDF не готов.
    Когда status=done — возвращает ссылку на скачивание.
    """
    try:
        resp = requests.get(
            f"{EXPORT_SERVICE_URL}/export/{job_id}/status/",
            timeout=3,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = {
                'status':    data['status'],
                'job_id':    job_id,
            }
            if data['status'] == 'done':
                # Прямая ссылка на скачивание через Django (проксируем)
                result['download_url'] = f"/workout/export/{job_id}/download/"
            return JsonResponse(result)

    except requests.RequestException:
        pass

    return JsonResponse({'status': 'pending', 'job_id': job_id})


@login_required
def download_export(request, job_id):
    """
    GET — проксирует скачивание PDF от микросервиса к браузеру пользователя.
    """
    import io
    from django.http import HttpResponse

    try:
        resp = requests.get(
            f"{EXPORT_SERVICE_URL}/export/{job_id}/download/",
            timeout=10,
            stream=True,
        )
        if resp.status_code == 200:
            response = HttpResponse(
                resp.content,
                content_type='application/pdf',
            )
            response['Content-Disposition'] = f'attachment; filename="workout_{job_id}.pdf"'
            return response

    except requests.RequestException:
        pass

    from django.contrib import messages
    messages.error(request, 'Не удалось скачать файл.')
    return redirect('workout:my_workouts')
