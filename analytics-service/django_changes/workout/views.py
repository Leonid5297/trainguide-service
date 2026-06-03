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
from .services import push_generate_job, publish_analytics_event

logger = logging.getLogger(__name__)

WORKOUT_SERVICE_URL = getattr(settings, 'WORKOUT_SERVICE_URL', 'http://localhost:8001')


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

    return JsonResponse({
        'is_completed': True,
        'completed_at': session.completed_at.strftime('%d.%m.%Y %H:%M'),
    })
