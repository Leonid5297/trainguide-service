from django.contrib import admin
from .models import Workout


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display  = ['user', 'goal', 'duration', 'status', 'created_at']
    list_filter   = ['status', 'goal', 'location']
    search_fields = ['user__username', 'goal']
    readonly_fields = ['result', 'error_msg', 'created_at']
    ordering      = ['-created_at']
