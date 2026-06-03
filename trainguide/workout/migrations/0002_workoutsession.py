from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workout', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkoutSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed_exercises', models.JSONField(default=list, verbose_name='Выполненные упражнения')),
                ('total_exercises', models.PositiveIntegerField(default=0, verbose_name='Всего упражнений')),
                ('is_completed', models.BooleanField(default=False, verbose_name='Завершена')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='Начата')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Завершена в')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='workout_sessions',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Пользователь',
                )),
                ('workout', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='session',
                    to='workout.workout',
                    verbose_name='Тренировка',
                )),
            ],
            options={
                'verbose_name': 'Сессия тренировки',
                'verbose_name_plural': 'Сессии тренировок',
            },
        ),
    ]
