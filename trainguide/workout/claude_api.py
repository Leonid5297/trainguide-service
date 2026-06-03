import json
import re
import anthropic
from django.conf import settings


SYSTEM_PROMPT = """Ты — профессиональный персональный тренер с опытом более 10 лет.
Твоя задача — составить персонализированный план тренировки на основе параметров пользователя.

КРИТИЧЕСКИ ВАЖНО:
- Верни ТОЛЬКО валидный JSON без каких-либо пояснений
- Без markdown-блоков (без ```json)
- Без текста до или после JSON
- Строго соблюдай указанную схему
- Все текстовые значения на русском языке"""

JSON_SCHEMA = """
{
  "title": "Название тренировки (краткое, ёмкое)",
  "meta": {
    "duration": "Длительность в минутах (число)",
    "level": "Уровень сложности",
    "goal": "Основная цель",
    "location": "Место тренировки",
    "calories": "Примерный расход калорий (число)"
  },
  "warmup": [
    {
      "name": "Название упражнения",
      "duration": "Длительность или повторения",
      "description": "Краткое описание техники"
    }
  ],
  "blocks": [
    {
      "name": "Название блока (группа мышц или тип нагрузки)",
      "exercises": [
        {
          "name": "Название упражнения",
          "sets": 3,
          "reps": "10-12",
          "rest": "60 сек",
          "weight": "Рекомендация по весу или 'собственный вес'",
          "tip": "Важный совет по технике",
          "muscles": ["Мышца 1", "Мышца 2"]
        }
      ]
    }
  ],
  "cooldown": [
    {
      "name": "Название упражнения",
      "duration": "Длительность",
      "description": "Краткое описание"
    }
  ],
  "tips": [
    "Совет 1 по данной тренировке",
    "Совет 2"
  ]
}"""


def build_prompt(data: dict) -> str:
    """Формирует промпт из данных формы."""

    injuries = ', '.join(data.get('injuries', [])) or 'Нет'
    muscles  = ', '.join(data.get('muscles', []))  or 'Всё тело'
    types    = ', '.join(data.get('workout_types', [])) or 'Не указано'
    focus    = data.get('focus') or 'Не указано'
    notes    = data.get('notes') or 'Нет'

    prompt = f"""Составь план тренировки по следующим параметрам пользователя:

ПАРАМЕТРЫ ПОЛЬЗОВАТЕЛЯ:
- Тренировочный стаж: {data.get('experience')}
- Частота тренировок: {data.get('frequency')} в неделю
- Длительность тренировки: {data.get('duration')}
- Место тренировок: {data.get('location')}
- Доступный инвентарь: {data.get('equipment')}
- Основная цель: {data.get('goal')}
- Предпочтительные виды нагрузки: {types}
- Акцент на упражнениях: {focus}
- Целевые группы мышц: {muscles}
- Интенсивность: {data.get('intensity')}
- Тип телосложения: {data.get('body_type')}
- Пол: {data.get('gender')}
- Возраст: {data.get('age')} лет
- Вес: {data.get('weight')} кг
- Рост: {data.get('height')} см
- Травмы / ограничения: {injuries}
- Дополнительная информация: {notes}

Верни ТОЛЬКО JSON строго по этой схеме:
{JSON_SCHEMA}"""

    return prompt


def call_claude(prompt: str) -> dict:
    """
    Вызывает Claude API и возвращает распарсенный JSON-словарь.
    При ошибке парсинга пробует извлечь JSON из ответа.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {'role': 'user', 'content': prompt}
        ],
    )

    response_text = message.content[0].text.strip()

    # Пробуем распарсить напрямую
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Если в ответе есть markdown-блок — вытаскиваем JSON из него
    match = re.search(r'```(?:json)?\s*([\s\S]+?)```', response_text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Ищем первый JSON-объект в тексте
    match = re.search(r'\{[\s\S]+\}', response_text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f'Claude вернул невалидный JSON: {response_text[:300]}')
