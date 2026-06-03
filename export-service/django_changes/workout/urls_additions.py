# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/urls.py
# ════════════════════════════════════════════════════════════════════════════

# Добавь эти три маршрута в urlpatterns:

path('export/<int:pk>/request/',        views.request_export,  name='export_request'),
path('export/status/<int:job_id>/',     views.export_status,   name='export_status'),
path('export/download/<int:job_id>/',   views.download_export, name='export_download'),
