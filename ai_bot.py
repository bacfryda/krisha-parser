"""AI бот на DeepSeek API для ведения диалогов."""
from openai import OpenAI
from database import get_conversation, add_conversation, mark_replied

DEFAULT_SYSTEM_PROMPT = """Ты — опытный риелтор с 10-летним стажем работы на рынке недвижимости Казахстана. 
Тебя зовут Асхат. Ты работаешь в агентстве недвижимости.

Твоя задача — вести диалог с потенциальными клиентами, которые разместили объявления на Крыше.
Ты пишешь первым, предлагая свои услуги. Твоя цель — договориться о встрече или звонке.

Правила общения:
- Пиши коротко, по делу, как в WhatsApp (не длинные простыни текста)
- Будь вежливым, но не навязчивым
- Используй разговорный стиль, без канцеляризмов
- Если человек отказывается — вежливо попрощайся, не дави
- Если человек интересуется — расскажи о преимуществах работы с риелтором
- Не выдумывай конкретные цифры и адреса
- Отвечай ТОЛЬКО на русском языке
- Максимум 2-3 предложения в сообщении"""


def _norm(phone: str) -> str:
    """Нормализует номер — всегда с +."""
    phone = phone.strip()
    if phone and not phone.startswith('+'):
        phone = '+' + phone
    return phone


def get_ai_response(phone: str, user_message: str, cfg: dict) -> str:
    """Получить ответ AI на сообщение пользователя."""
    phone = _norm(phone)
    ds = cfg.get("deepseek", {})
    api_key = ds.get("api_key", "")
    model = ds.get("model", "deepseek-chat")
    temperature = ds.get("temperature", 0.7)
    max_tokens = ds.get("max_tokens", 300)
    system_prompt = ds.get("system_prompt", "").strip() or DEFAULT_SYSTEM_PROMPT

    if not api_key:
        return "[Ошибка: API ключ DeepSeek не настроен]"

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # Сообщение пользователя и mark_replied уже сохранены в sync
    # Собираем историю диалога
    history = get_conversation(phone)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["message"]})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        # deepseek-reasoner может вернуть content=None
        reply = content.strip() if content else "[AI не вернул ответ]"
    except Exception as e:
        reply = f"[Ошибка AI: {e}]"

    # Сохраняем ответ бота
    add_conversation(phone, "assistant", reply)
    return reply


def generate_first_message(listing_title: str, price: str, cfg: dict) -> str:
    """Генерирует персонализированное первое сообщение."""
    ds = cfg.get("deepseek", {})
    api_key = ds.get("api_key", "")
    model = ds.get("model", "deepseek-chat")
    temperature = ds.get("temperature", 0.8)
    system_prompt = ds.get("system_prompt", "").strip() or DEFAULT_SYSTEM_PROMPT

    if not api_key:
        return cfg["whatsapp"]["first_message"]

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    prompt = f"""Напиши короткое первое сообщение в WhatsApp человеку, который разместил объявление:
Заголовок: {listing_title}
Цена: {price}

Сообщение должно быть:
- 1-2 предложения максимум
- Упомянуть что видел объявление
- Предложить помощь как риелтор
- Звучать естественно, не как спам"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        # deepseek-reasoner может вернуть content=None (ответ в reasoning_content)
        if content and content.strip():
            return content.strip()
        return cfg["whatsapp"]["first_message"]
    except Exception:
        return cfg["whatsapp"]["first_message"]
