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
    
    # Notifications
    path('notifications/read/', views.mark_notifications_read, name='notifications_read'),
    
    # Export
    path('export/<int:pk>/request/',      views.request_export,  name='export_request'),
    path('export/<int:job_id>/status/',   views.export_status,   name='export_status'),
    path('export/<int:job_id>/download/', views.download_export, name='export_download'),

    # Advisor AI
    path('advisor/',     views.advisor,     name='advisor'),
    path('advisor/ask/', views.advisor_ask, name='advisor_ask'),

    # Schedule
    path('schedule/',        views.schedule,        name='schedule'),
    path('schedule/toggle/', views.schedule_toggle, name='schedule_toggle'),
]
