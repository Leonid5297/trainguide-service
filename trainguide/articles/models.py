from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from taggit.managers import TaggableManager
import re
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify



class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Article.Status.PUBLISHED)


class Article(models.Model):

    class Status(models.TextChoices):
        DRAFT     = 'DF', 'Draft'
        PUBLISHED = 'PB', 'Published'

    title   = models.CharField('Заголовок', max_length=250)
    slug    = models.SlugField('Slug', max_length=250, unique_for_date='publish')
    author  = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name='Автор',
    )
    cover   = models.URLField('URL обложки', max_length=500, blank=True, null=True)
    category = models.CharField('Категория', max_length=100, blank=True)
    body = MarkdownxField('Текст статьи')
    publish = models.DateTimeField('Дата публикации', default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status  = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус',
    )

    objects   = models.Manager()       # менеджер по умолчанию
    published = PublishedManager()     # только опубликованные
    tags = TaggableManager()

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-publish']
        indexes = [
            models.Index(fields=['-publish']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            'articles:detail',
            args=[
                self.publish.year,
                self.publish.month,
                self.publish.day,
                self.slug,
            ],
        )
        
    def get_excerpt(self, length=120):
    # Убираем markdown-символы для чистого превью
        clean = re.sub(r'[#*_`\[\]>]', '', self.body)
        if len(clean) <= length:
            return clean
        return clean[:length].rsplit(' ', 1)[0] + '...'
    
    @property
    def body_as_html(self):
        return markdownify(self.body)
