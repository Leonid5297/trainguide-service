from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Workout(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Генерируется'
        DONE    = 'done',    'Готова'
        ERROR   = 'error',   'Ошибка'

    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workouts', verbose_name='Пользователь')
    experience  = models.CharField('Тренировочный стаж', max_length=100)
    frequency   = models.CharField('Частота в неделю', max_length=50)
    duration    = models.CharField('Длительность тренировки', max_length=50)
    location    = models.CharField('Место тренировок', max_length=100)
    equipment   = models.CharField('Инвентарь', max_length=100)
    goal        = models.CharField('Основная цель', max_length=100)
    workout_types = models.JSONField('Виды нагрузки', default=list)
    focus         = models.CharField('Акцент', max_length=255, blank=True)
    muscles       = models.JSONField('Группы мышц', default=list)
    intensity     = models.CharField('Интенсивность', max_length=100)
    body_type     = models.CharField('Тип телосложения', max_length=100)
    gender      = models.CharField('Пол', max_length=20)
    age         = models.PositiveIntegerField('Возраст', null=True, blank=True)
    weight      = models.FloatField('Вес (кг)', null=True, blank=True)
    height      = models.FloatField('Рост (см)', null=True, blank=True)
    injuries    = models.JSONField('Травмы', default=list)
    notes       = models.TextField('Доп. информация', blank=True)
    result      = models.JSONField('Результат (JSON)', null=True, blank=True)
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error_msg   = models.TextField('Ошибка', blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Тренировка'
        verbose_name_plural = 'Тренировки'
        ordering            = ['-created_at']

    def __str__(self):
        title = self.result.get('title', '—') if self.result else '—'
        return f'{self.user.username} — {title}'

    def get_absolute_url(self):
        return reverse('workout:detail', args=[self.pk])

    def count_total_exercises(self):
        """Считает общее кол-во упражнений во всех основных блоках."""
        if not self.result:
            return 0
        return sum(len(b.get('exercises', [])) for b in self.result.get('blocks', []))


class WorkoutSession(models.Model):
    """
    Сессия выполнения тренировки.
    Ключ упражнения: "block_index-exercise_index" (строка).
    """
    workout     = models.OneToOneField(Workout, on_delete=models.CASCADE, related_name='session', verbose_name='Тренировка')
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_sessions', verbose_name='Пользователь')
    completed_exercises = models.JSONField('Выполненные упражнения', default=list)
    total_exercises     = models.PositiveIntegerField('Всего упражнений', default=0)
    is_completed        = models.BooleanField('Завершена', default=False)
    started_at          = models.DateTimeField('Начата', auto_now_add=True)
    completed_at        = models.DateTimeField('Завершена в', null=True, blank=True)

    class Meta:
        verbose_name        = 'Сессия тренировки'
        verbose_name_plural = 'Сессии тренировок'

    def __str__(self):
        return f'Сессия: {self.workout}'

    @property
    def progress(self):
        if not self.total_exercises:
            return 0
        return round(len(self.completed_exercises) / self.total_exercises * 100)

    @property
    def done_count(self):
        return len(self.completed_exercises)
