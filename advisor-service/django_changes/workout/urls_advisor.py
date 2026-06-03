# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/urls.py
# ════════════════════════════════════════════════════════════════════════════

path('advisor/',     views.advisor,     name='advisor'),
path('advisor/ask/', views.advisor_ask, name='advisor_ask'),
