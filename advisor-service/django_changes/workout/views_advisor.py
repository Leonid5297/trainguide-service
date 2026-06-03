# ════════════════════════════════════════════════════════════════════════════
# ДОБАВИТЬ В workout/views.py
# ════════════════════════════════════════════════════════════════════════════
#
# 1. Добавь константу рядом с другими SERVICE_URL:
#
#    ADVISOR_SERVICE_URL = getattr(settings, 'ADVISOR_SERVICE_URL', 'http://localhost:8005')
#
# 2. Добавь два view:

@login_required
def advisor(request):
    """
    Страница AI-советника.
    GET  — показывает форму и историю диалогов.
    """
    history = []
    try:
        resp = requests.get(
            f"{ADVISOR_SERVICE_URL}/history/{request.user.pk}/?limit=10",
            timeout=3,
        )
        if resp.status_code == 200:
            history = resp.json()
    except requests.RequestException:
        pass

    return render(request, 'workout/advisor.html', {
        'history': history,
    })


@login_required
@require_POST
def advisor_ask(request):
    """
    POST — AJAX-запрос с вопросом.
    Проксирует запрос к advisor-service и возвращает ответ JSON.
    """
    try:
        body     = json.loads(request.body)
        question = body.get('question', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)

    if not question:
        return JsonResponse({'error': 'Вопрос не может быть пустым'}, status=400)

    try:
        resp = requests.post(
            f"{ADVISOR_SERVICE_URL}/ask/",
            json={
                'user_id':  request.user.pk,
                'question': question,
            },
            timeout=30,   # Claude может думать до 15-20 сек
        )
        if resp.status_code == 200:
            data = resp.json()
            return JsonResponse({
                'answer':   data['answer'],
                'saved_id': data['saved_id'],
            })
        else:
            return JsonResponse({'error': 'Ошибка сервиса советника'}, status=500)

    except requests.Timeout:
        return JsonResponse({'error': 'Сервис не ответил вовремя'}, status=504)
    except requests.RequestException as e:
        logger.error(f"Advisor service error: {e}")
        return JsonResponse({'error': 'Сервис советника недоступен'}, status=503)
