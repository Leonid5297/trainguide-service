import requests
import logging
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .forms import UserRegistrationForm, UserEditForm, ProfileEditForm
from .models import Profile

logger = logging.getLogger(__name__)

ANALYTICS_SERVICE_URL = getattr(settings, 'ANALYTICS_SERVICE_URL', 'http://localhost:8002')


def get_user_stats(user_id: int) -> dict:
    """
    Запрашивает статистику у микросервиса аналитики.
    При недоступности — возвращает нули, профиль всё равно откроется.
    """
    try:
        resp = requests.get(
            f"{ANALYTICS_SERVICE_URL}/stats/{user_id}/",
            timeout=2,
        )
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        logger.warning(f"Микросервис аналитики недоступен: {e}")

    return {
        'total_generated':    0,
        'total_completed':    0,
        'completion_rate':    0,
        'avg_exercises_done': 0,
        'favorite_goal':      None,
        'current_streak':     0,
    }


def home(request):
    return render(request, 'base.html', {})


def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(data=request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            Profile.objects.create(user=new_user)
            return render(request, 'account/register_done.html', {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()

    return render(request, 'account/register.html', {'user_form': user_form})


@login_required
def profile(request):
    if request.method == 'POST':
        user_form    = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлён.')
        else:
            messages.error(request, 'Ошибка редактирования профиля.')
    else:
        user_form    = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)

    # Получаем реальную статистику из микросервиса аналитики
    stats = get_user_stats(request.user.pk)

    return render(request, 'account/profile.html', {
        'user_form':    user_form,
        'profile_form': profile_form,
        'stats':        stats,
    })
