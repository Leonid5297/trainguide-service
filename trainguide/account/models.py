from django.db import models
from django.conf import settings

# Create your models here.
class Profile(models.Model):
    class Gender(models.TextChoices):
        NOT_SPECIFIED = '', 'Не указан'
        MALE = 'male', 'Мужской'
        FEMALE = 'female', 'Женский'
        OTHER = 'other', 'Другое'
        
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    
    age = models.IntegerField(
        verbose_name='Возраст',
        blank=True,
        null=True,
    )
    weight = models.DecimalField(
        verbose_name='Вес (кг)',
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
    )
    height = models.IntegerField(
        verbose_name='Рост (см)',
        blank=True,
        null=True,
    )
    gender = models.CharField(
        verbose_name='Пол',
        max_length=10,
        choices=Gender.choices,
        blank=True,
        default='',
    )
    avatar = models.ImageField(
        verbose_name='Фото профиля',
        upload_to='avatars/',
        blank=True,
        null=True,
    )
    

    def __str__(self):
        return f'Profile of {self.user.username}'
