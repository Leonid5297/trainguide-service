from django.urls import path
from . import views

app_name = 'workout'

urlpatterns = [
    path('generate/',                    views.generate,         name='generate'),
    path('detail/<int:pk>/',             views.detail,           name='detail'),
    path('my/',                          views.my_workouts,      name='my_workouts'),

    # Поллинг статуса генерации (JS опрашивает пока status != done)
    path('status/<int:pk>/',             views.workout_status,   name='status'),

    # AJAX WorkoutSession
    path('session/<int:pk>/status/',     views.session_status,   name='session_status'),
    path('session/<int:pk>/toggle/',     views.toggle_exercise,  name='toggle_exercise'),
    path('session/<int:pk>/complete/',   views.complete_session, name='complete_session'),
]
