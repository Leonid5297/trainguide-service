from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    # Список статей
    path('', views.article_list, name='list'),

    # Фильтр по тегу
    path('tag/<slug:tag_slug>/', views.article_list, name='list_by_tag'),

    # Детальная страница статьи
    path(
        '<int:year>/<int:month>/<int:day>/<slug:slug>/',
        views.article_detail,
        name='detail',
    ),
]
