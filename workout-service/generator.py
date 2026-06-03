import json
import re
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

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


def build_prompt(form_data: dict) -> str:
    injuries = ', '.join(form_data.get('injuries', [])) or 'Нет'
    muscles  = ', '.join(form_data.get('muscles', []))  or 'Всё тело'
    types    = ', '.join(form_data.get('workout_types', [])) or 'Не указано'

    return f"""Составь план тренировки по следующим параметрам пользователя:

ПАРАМЕТРЫ ПОЛЬЗОВАТЕЛЯ:
- Тренировочный стаж: {form_data.get('experience')}
- Частота тренировок: {form_data.get('frequency')} в неделю
- Длительность тренировки: {form_data.get('duration')}
- Место тренировок: {form_data.get('location')}
- Доступный инвентарь: {form_data.get('equipment')}
- Основная цель: {form_data.get('goal')}
- Предпочтительные виды нагрузки: {types}
- Акцент на упражнениях: {form_data.get('focus') or 'Не указано'}
- Целевые группы мышц: {muscles}
- Интенсивность: {form_data.get('intensity')}
- Тип телосложения: {form_data.get('body_type')}
- Пол: {form_data.get('gender')}
- Возраст: {form_data.get('age')} лет
- Вес: {form_data.get('weight')} кг
- Рост: {form_data.get('height')} см
- Травмы / ограничения: {injuries}
- Дополнительная информация: {form_data.get('notes') or 'Нет'}

Верни ТОЛЬКО JSON строго по этой схеме:
{JSON_SCHEMA}"""


def call_claude(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()

    # Прямой парсинг
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Из markdown-блока
    match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Первый JSON-объект в тексте
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Claude вернул невалидный JSON: {text[:300]}")
