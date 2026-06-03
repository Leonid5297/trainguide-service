from django import forms

# ── Общие стили ────────────────────────────────────────────────────────────────
SELECT_CLASS = (
    'w-full p-3.5 bg-white border border-slate-200 rounded-xl text-sm '
    'font-medium outline-none appearance-none cursor-pointer text-slate-500 '
    'transition-all hover:border-slate-300 focus:ring-2 focus:ring-[#0088CC]/20'
)
INPUT_CLASS = (
    'w-full p-3.5 bg-white border border-slate-200 rounded-xl text-sm '
    'font-medium outline-none placeholder:text-slate-300 transition-all '
    'hover:border-slate-300 focus:ring-2 focus:ring-[#0088CC]/20'
)
TEXTAREA_CLASS = (
    'w-full p-4 bg-white border border-slate-200 rounded-xl text-sm '
    'font-medium outline-none h-32 resize-none placeholder:text-slate-300 '
    'transition-all hover:border-slate-300 focus:ring-2 focus:ring-[#0088CC]/20'
)

# ── Варианты выбора ────────────────────────────────────────────────────────────
EXPERIENCE_CHOICES = [
    ('', 'Выберите стаж'),
    ('Новичок (0–6 месяцев)', 'Новичок (0–6 месяцев)'),
    ('Средний (6–12 месяцев)', 'Средний (6–12 месяцев)'),
    ('Продвинутый (1–3 года)', 'Продвинутый (1–3 года)'),
    ('Профи (3+ года)', 'Профи (3+ года)'),
]
FREQUENCY_CHOICES = [
    ('', 'Сколько раз?'),
    ('1 раз', '1 раз'), ('2 раза', '2 раза'), ('3 раза', '3 раза'),
    ('4 раза', '4 раза'), ('5 раз', '5 раз'), ('6 раз', '6 раз'),
    ('Ежедневно', 'Ежедневно'),
]
DURATION_CHOICES = [
    ('', 'Сколько минут?'),
    ('15–30 минут', '15–30 минут'), ('30–45 минут', '30–45 минут'),
    ('45–60 минут', '45–60 минут'), ('60–90 минут', '60–90 минут'),
    ('90+ минут', '90+ минут'),
]
LOCATION_CHOICES = [
    ('', 'Место тренировок'),
    ('Тренажерный зал', 'Тренажерный зал'),
    ('Дома', 'Дома'),
    ('Уличная площадка (Воркаут)', 'Уличная площадка (Воркаут)'),
    ('Студия йоги/пилатеса', 'Студия йоги/пилатеса'),
]
EQUIPMENT_CHOICES = [
    ('', 'Что есть под рукой?'),
    ('Полный зал', 'Полный зал'),
    ('Только гантели', 'Только гантели'),
    ('Турник и брусья', 'Турник и брусья'),
    ('Без инвентаря (собственный вес)', 'Без инвентаря (собственный вес)'),
    ('Резинки/эспандеры', 'Резинки/эспандеры'),
]
GOAL_CHOICES = [
    ('', 'Чего хотите достичь?'),
    ('Похудение', 'Похудение'), ('Набор мышечной массы', 'Набор мышечной массы'),
    ('Увеличение силы', 'Увеличение силы'), ('Выносливость', 'Выносливость'),
    ('Рельеф', 'Рельеф'), ('Поддержание формы', 'Поддержание формы'),
    ('Гибкость', 'Гибкость'),
]
WORKOUT_TYPE_CHOICES = [
    ('Силовые тренировки', 'Силовые тренировки'),
    ('Кардио', 'Кардио'),
    ('Кроссфит', 'Кроссфит'),
    ('Калистеника', 'Калистеника'),
    ('Растяжка и МФР', 'Растяжка и МФР'),
    ('Йога', 'Йога'),
]
MUSCLE_CHOICES = [
    ('Грудь', 'Грудь'), ('Спина', 'Спина'), ('Ноги', 'Ноги'),
    ('Плечи', 'Плечи'), ('Руки', 'Руки'), ('Пресс и кор', 'Пресс и кор'),
]
INTENSITY_CHOICES = [
    ('', 'Выберите уровень'),
    ('Низкая (оздоровительная)', 'Низкая (оздоровительная)'),
    ('Умеренная', 'Умеренная'),
    ('Высокая (интенсивная)', 'Высокая (интенсивная)'),
    ('Максимальная (отказная)', 'Максимальная (отказная)'),
]
BODY_TYPE_CHOICES = [
    ('', 'Ваш тип'),
    ('Эктоморф (худощавый)', 'Эктоморф (худощавый)'),
    ('Мезоморф (атлетичный)', 'Мезоморф (атлетичный)'),
    ('Эндоморф (склонный к полноте)', 'Эндоморф (склонный к полноте)'),
]
GENDER_CHOICES = [
    ('', 'Выберите вариант'),
    ('male',   'Мужской'),
    ('female', 'Женский'),
    ('other',  'Другое'),
]
INJURY_CHOICES = [
    ('Без травм', 'Без травм'), ('Поясница', 'Поясница'),
    ('Колено', 'Колено'), ('Плечо', 'Плечо'), ('Шея', 'Шея'),
]


class WorkoutForm(forms.Form):
    # workout/forms.py

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.is_authenticated:
            user = self.request.user

            # Базовые поля из User
            if user.profile.gender:
                self.initial['gender'] = user.profile.gender
            if user.profile.age:
                self.initial['age'] = user.profile.age
            if user.profile.weight:
                self.initial['weight'] = user.profile.weight
            if user.profile.height:
                self.initial['height'] = user.profile.height
        

    # ── Шаг 1 — Цели ──────────────────────────────────────────────────────────
    experience = forms.ChoiceField(
        label='Ваш тренировочный стаж',
        choices=EXPERIENCE_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    frequency = forms.ChoiceField(
        label='Частота тренировок в неделю',
        choices=FREQUENCY_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    duration = forms.ChoiceField(
        label='Длительность одной тренировки',
        choices=DURATION_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    location = forms.ChoiceField(
        label='Где вы планируете тренироваться?',
        choices=LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    equipment = forms.ChoiceField(
        label='Доступный инвентарь',
        choices=EQUIPMENT_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    goal = forms.ChoiceField(
        label='Основная цель',
        choices=GOAL_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    # ── Шаг 2 — Детали ────────────────────────────────────────────────────────
    workout_types = forms.MultipleChoiceField(
        label='Предпочтительные виды нагрузки',
        choices=WORKOUT_TYPE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )
    focus = forms.CharField(
        label='Упражнения, на которых стоит сделать акцент',
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Например: подтягивания, жим, присед',
        }),
    )
    muscles = forms.MultipleChoiceField(
        label='Целевые группы мышц',
        choices=MUSCLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )
    intensity = forms.ChoiceField(
        label='Желаемая интенсивность',
        choices=INTENSITY_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    body_type = forms.ChoiceField(
        label='Тип телосложения',
        choices=BODY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    # ── Шаг 3 — Профиль ───────────────────────────────────────────────────────
    gender = forms.ChoiceField(
        label='Пол',
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    age = forms.IntegerField(
        label='Возраст',
        required=False,
        min_value=10, max_value=100,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Введите свой возраст',
        }),
    )
    weight = forms.FloatField(
        label='Текущий вес (кг)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Введите вес в кг',
        }),
    )
    height = forms.FloatField(
        label='Текущая высота (см)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Введите высоту в см',
        }),
    )
    injuries = forms.MultipleChoiceField(
        label='Травмы / заболевания',
        choices=INJURY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )
    notes = forms.CharField(
        label='Дополнительная информация',
        required=False,
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASS,
            'placeholder': 'Введите любую дополнительную информацию, укажите свои опасения или цели...',
        }),
    )
