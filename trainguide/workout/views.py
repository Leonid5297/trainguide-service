import json
import requests
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings

from .forms import WorkoutForm
from .models import Workout, WorkoutSession
from .services import push_generate_job, publish_analytics_event, publish_notification, publish_export_job
logger = logging.getLogger(__name__)

WORKOUT_SERVICE_URL = getattr(settings, 'WORKOUT_SERVICE_URL', 'http://localhost:8001')

EXPORT_SERVICE_URL = getattr(settings, 'EXPORT_SERVICE_URL', 'http://localhost:8004')

ADVISOR_SERVICE_URL = getattr(settings, 'ADVISOR_SERVICE_URL', 'http://localhost:8005')

SCHEDULE_SERVICE_URL = getattr(settings, 'SCHEDULE_SERVICE_URL', 'http://localhost:8006')



@login_required
def generate(request):
    if request.method == 'POST':
        form = WorkoutForm(request.POST, request=request)
        if form.is_valid():
            data = form.cleaned_data

            workout = Workout.objects.create(
                user=request.user,
                experience=data['experience'],   frequency=data['frequency'],
                duration=data['duration'],       location=data['location'],
                equipment=data['equipment'],     goal=data['goal'],
                workout_types=data.get('workout_types', []),
                focus=data.get('focus', ''),
                muscles=data.get('muscles', []), intensity=data['intensity'],
                body_type=data['body_type'],     gender=data['gender'],
                age=data.get('age'),             weight=data.get('weight'),
                height=data.get('height'),
                injuries=data.get('injuries', []),
                notes=data.get('notes', ''),
                status=Workout.Status.PENDING,
            )

            try:
                push_generate_job(
                    workout_id=workout.pk,
                    user_id=request.user.pk,
                    form_data=data,
                )

                # ── Публикуем аналитическое событие ──────────────────────────
                publish_analytics_event(
                    event='workout_generated',
                    user_id=request.user.pk,
                    workout_id=workout.pk,
                    goal=data.get('goal', ''),
                    duration=data.get('duration', ''),
                )

            except Exception as e:
                logger.error(f"Ошибка отправки задания: {e}")
                workout.status    = Workout.Status.ERROR
                workout.error_msg = str(e)
                workout.save()
                messages.error(request, 'Ошибка подключения к сервису генерации.')
                return redirect('workout:generate')

            return redirect('workout:detail', pk=workout.pk)
    else:
        form = WorkoutForm(request=request)

    return render(request, 'workout/generate.html', {'form': form})


@login_required
def workout_status(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)

    if workout.status in (Workout.Status.DONE, Workout.Status.ERROR):
        return JsonResponse({'status': workout.status, 'workout_id': pk})

    try:
        resp = requests.get(f"{WORKOUT_SERVICE_URL}/job/{pk}/", timeout=3)
        if resp.status_code == 200:
            data = resp.json()

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

            elif data['status'] == 'error':
                workout.status    = Workout.Status.ERROR
                workout.error_msg = data.get('error_msg', 'Неизвестная ошибка')
                workout.save()
                
                return JsonResponse({'status': 'error', 'workout_id': pk})

        return JsonResponse({'status': 'pending', 'workout_id': pk})

    except requests.RequestException:
        return JsonResponse({'status': 'pending', 'workout_id': pk})


@login_required
def detail(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    session = None
    if workout.status == Workout.Status.DONE and workout.result:
        session, _ = WorkoutSession.objects.get_or_create(
            workout=workout,
            defaults={
                'user': request.user,
                'total_exercises': workout.count_total_exercises(),
            }
        )
    return render(request, 'workout/detail.html', {'workout': workout, 'session': session})


@login_required
def my_workouts(request):
    filter_by = request.GET.get('filter', 'all')
    workouts = Workout.objects.filter(
        user=request.user,
        status=Workout.Status.DONE,
    ).prefetch_related('session')

    if filter_by == 'active':
        workouts = [w for w in workouts if not hasattr(w, 'session') or not w.session.is_completed]
    elif filter_by == 'completed':
        workouts = [w for w in workouts if hasattr(w, 'session') and w.session.is_completed]

    return render(request, 'workout/list.html', {'workouts': workouts, 'filter_by': filter_by})


# ── AJAX WorkoutSession ────────────────────────────────────────────────────────

@login_required
def session_status(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    session, _ = WorkoutSession.objects.get_or_create(
        workout=workout,
        defaults={'user': request.user, 'total_exercises': workout.count_total_exercises()}
    )
    return JsonResponse({
        'completed_exercises': session.completed_exercises,
        'total':    session.total_exercises,
        'done':     session.done_count,
        'progress': session.progress,
        'is_completed': session.is_completed,
    })


@login_required
@require_POST
def toggle_exercise(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    session, _ = WorkoutSession.objects.get_or_create(
        workout=workout,
        defaults={'user': request.user, 'total_exercises': workout.count_total_exercises()}
    )

    if session.is_completed:
        return JsonResponse({'error': 'Тренировка уже завершена'}, status=400)

    try:
        body = json.loads(request.body)
        key  = str(body.get('key', ''))
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)

    completed = list(session.completed_exercises)
    if key in completed:
        completed.remove(key)
        checked = False
    else:
        completed.append(key)
        checked = True

    session.completed_exercises = completed
    session.save(update_fields=['completed_exercises'])

    return JsonResponse({
        'key':      key,
        'checked':  checked,
        'done':     session.done_count,
        'total':    session.total_exercises,
        'progress': session.progress,
    })


@login_required
@require_POST
def complete_session(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    session = get_object_or_404(WorkoutSession, workout=workout, user=request.user)

    session.is_completed = True
    session.completed_at = timezone.now()
    session.save(update_fields=['is_completed', 'completed_at'])

    # ── Публикуем аналитическое событие ──────────────────────────────────────
    publish_analytics_event(
        event='workout_completed',
        user_id=request.user.pk,
        workout_id=workout.pk,
        exercises_done=session.done_count,
        exercises_total=session.total_exercises,
    )
    
    # ── Публикуем уведомление  ─────────────────────────────────────
    publish_notification(
        event='workout_completed',
        user_id=request.user.pk,
        message='Тренировка завершена! Отличная работа 🎉',
    )

    return JsonResponse({
        'is_completed': True,
        'completed_at': session.completed_at.strftime('%d.%m.%Y %H:%M'),
    })



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


# advisor view
@login_required
def advisor(request):
    """
    Страница AI-советника.
    GET  — показывает форму и историю диалогов.
    """
    history = []
    try:
        resp = requests.get(
            f"{ADVISOR_SERVICE_URL}/history/{request.user.pk}/?limit=10",
            timeout=3,
        )
        if resp.status_code == 200:
            history = resp.json()
    except requests.RequestException:
        pass

    return render(request, 'workout/advisor.html', {
    'history': history,
    'example_questions': [
        'Как правильно делать становую тягу?',
        'Сколько белка нужно в день?',
        'Болит колено после приседаний',
        'Как восстановиться после тренировки?',
        'Какие упражнения на пресс самые эффективные?',
    ],
})


@login_required
@require_POST
def advisor_ask(request):
    """
    POST — AJAX-запрос с вопросом.
    Проксирует запрос к advisor-service и возвращает ответ JSON.
    """
    try:
        body     = json.loads(request.body)
        question = body.get('question', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)

    if not question:
        return JsonResponse({'error': 'Вопрос не может быть пустым'}, status=400)

    try:
        resp = requests.post(
            f"{ADVISOR_SERVICE_URL}/ask/",
            json={
                'user_id':  request.user.pk,
                'question': question,
            },
            timeout=30,   # Claude может думать до 15-20 сек
        )
        if resp.status_code == 200:
            data = resp.json()
            return JsonResponse({
                'answer':   data['answer'],
                'saved_id': data['saved_id'],
            })
        else:
            return JsonResponse({'error': 'Ошибка сервиса советника'}, status=500)

    except requests.Timeout:
        return JsonResponse({'error': 'Сервис не ответил вовремя'}, status=504)
    except requests.RequestException as e:
        logger.error(f"Advisor service error: {e}")
        return JsonResponse({'error': 'Сервис советника недоступен'}, status=503)

# schedule views 



DAYS_RU = {
    'mon': 'Пн', 'tue': 'Вт', 'wed': 'Ср',
    'thu': 'Чт', 'fri': 'Пт', 'sat': 'Сб', 'sun': 'Вс',
}

ALL_DAYS = [
    {'key': 'mon', 'label': 'Пн'},
    {'key': 'tue', 'label': 'Вт'},
    {'key': 'wed', 'label': 'Ср'},
    {'key': 'thu', 'label': 'Чт'},
    {'key': 'fri', 'label': 'Пт'},
    {'key': 'sat', 'label': 'Сб'},
    {'key': 'sun', 'label': 'Вс'},
]


@login_required
def schedule(request):
    current_schedule = None

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
                messages.error(request, resp.json().get('detail', 'Ошибка сохранения'))
        except requests.RequestException:
            messages.error(request, 'Сервис расписания недоступен.')

        return redirect('workout:schedule')

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
        'all_days':         ALL_DAYS,
    })


@login_required
@require_POST
def schedule_toggle(request):
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