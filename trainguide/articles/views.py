from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from taggit.models import Tag

from .models import Article
from .forms import SearchForm


def article_list(request, tag_slug=None):
    """
    Список опубликованных статей.
    Поддерживает полнотекстовый поиск и фильтрацию по тегу.
    """
    articles = Article.published.all()
    tag = None
    form = SearchForm(request.GET or None)
    query = None

    # ── Фильтр по тегу ────────────────────────────────────────────────────────
    if tag_slug:
        tag      = get_object_or_404(Tag, slug=tag_slug)
        articles = articles.filter(tags__in=[tag])

    # ── Полнотекстовый поиск ──────────────────────────────────────────────────
    if form.is_valid():
        query = form.cleaned_data['query']
        if query:
            search_vector = (
                SearchVector('title', weight='A') +
                SearchVector('body',  weight='B')
            )
            search_query = SearchQuery(query)
            articles = (
                Article.published
                .annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query),
                )
                .filter(search=search_query)
                .order_by('-rank')
            )

    # ── Пагинация ─────────────────────────────────────────────────────────────
    paginator = Paginator(articles, 8)
    page_num  = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'articles/list.html', {
        'articles': page_obj,
        'page_obj': page_obj,
        'form':     form,
        'query':    query,
        'tag':      tag,
    })


def article_detail(request, year, month, day, slug):
    """
    Детальная страница статьи.
    """
    article = get_object_or_404(
        Article,
        status=Article.Status.PUBLISHED,
        slug=slug,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    return render(request, 'articles/detail.html', {
        'article': article,
    })
