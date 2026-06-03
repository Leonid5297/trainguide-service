from django.contrib import admin
from .models import Article
from markdownx.admin import MarkdownxModelAdmin



@admin.register(Article)
class ArticleAdmin(MarkdownxModelAdmin):
    list_display   = ['title', 'author', 'category', 'publish', 'status']
    list_filter    = ['status', 'category', 'publish', 'author']
    search_fields  = ['title', 'body']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields  = ['author']
    date_hierarchy = 'publish'
    ordering       = ['status', '-publish']




    