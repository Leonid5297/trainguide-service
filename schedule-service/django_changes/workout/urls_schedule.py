# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/urls.py
# ════════════════════════════════════════════════════════════════════════════

path('schedule/',        views.schedule,        name='schedule'),
path('schedule/toggle/', views.schedule_toggle, name='schedule_toggle'),
