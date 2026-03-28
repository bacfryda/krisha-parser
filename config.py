"""Управление конфигурацией."""
import json
import os
from app_paths import APP_DIR

CONFIG_PATH = os.path.join(APP_DIR, "config.json")

REGIONS = {
    "": "Весь Казахстан",
    "almaty": "Алматы",
    "astana": "Астана",
    "shymkent": "Шымкент",
    "abay-oblast": "Абай обл.",
    "akmolinskaja-oblast": "Акмолинская обл.",
    "aktjubinskaja-oblast": "Актюбинская обл.",
    "almatinskaja-oblast": "Алматинская обл.",
    "atyrauskaja-oblast": "Атырауская обл.",
    "vostochno-kazahstanskaja-oblast": "Восточно-Казахстанская обл.",
    "zhambylskaja-oblast": "Жамбылская обл.",
    "jetisyskaya-oblast": "Жетысу обл.",
    "zapadno-kazahstanskaja-oblast": "Западно-Казахстанская обл.",
    "karagandinskaja-oblast": "Карагандинская обл.",
    "kostanajskaja-oblast": "Костанайская обл.",
    "kyzylordinskaja-oblast": "Кызылординская обл.",
    "mangistauskaja-oblast": "Мангистауская обл.",
    "pavlodarskaja-oblast": "Павлодарская обл.",
    "severo-kazahstanskaja-oblast": "Северо-Казахстанская обл.",
    "juzhno-kazahstanskaja-oblast": "Туркестанская обл.",
    "ulitayskay-oblast": "Улытау обл.",
}

BUILDING_TYPES = {
    "1": "кирпичный",
    "2": "панельный",
    "3": "монолитный",
    "0": "иной",
}

TOILET_TYPES = {
    "1": "раздельный",
    "2": "совмещенный",
    "3": "2 с/у и более",
    "4": "нет",
}

PHONE_LINE_TYPES = {
    "1": "отдельный",
    "2": "блокиратор",
    "3": "есть возможность подключения",
    "4": "нет",
}

MORTGAGE_OPTIONS = {
    "": "Не важно",
    "1": "да",
    "0": "нет",
}

PRIV_DORM_OPTIONS = {
    "": "Не важно",
    "1": "да",
    "2": "нет",
}

DEFAULT_CONFIG = {
    "krisha": {
        "deal_type": "sale",
        "region": "",
        "region_alias": "",
        "rooms": [],
        "price_from": "",
        "price_to": "",
        "has_photo": False,
        "novostroiki": False,
        "from_owner": False,
        "from_agent": False,
        "building_type": [],
        "floor_from": "",
        "floor_to": "",
        "house_floors_from": "",
        "house_floors_to": "",
        "year_from": "",
        "year_to": "",
        "not_last_floor": False,
        "not_first_floor": False,
        "square_from": "",
        "square_to": "",
        "kitchen_from": "",
        "kitchen_to": "",
        "mortgage": "",
        "priv_dorm": "",
        "has_change": False,
        "toilet": [],
        "phone_line": [],
        "text_search": "",
        "max_listings": 60,
    },
    "whatsapp": {
        "phone_number": "",
        "message_delay_seconds": 30,
        "daily_limit": 50,
        "first_message": "Здравствуйте! Увидел ваше объявление на Крыше. Могу помочь с продажей/арендой вашей недвижимости быстрее и выгоднее. Интересно?",
    },
    "captcha": {
        "anticaptcha_api_key": "",
    },
    "deepseek": {
        "api_key": "",
        "model": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 300,
        "system_prompt": "Ты — опытный риелтор с 10-летним стажем работы на рынке недвижимости Казахстана.\nТебя зовут Асхат. Ты работаешь в агентстве недвижимости.\n\nТвоя задача — вести диалог с потенциальными клиентами, которые разместили объявления на Крыше.\nТы пишешь первым, предлагая свои услуги. Твоя цель — договориться о встрече или звонке.\n\nПравила общения:\n- Пиши коротко, по делу, как в WhatsApp (не длинные простыни текста)\n- Будь вежливым, но не навязчивым\n- Используй разговорный стиль, без канцеляризмов\n- Если человек отказывается — вежливо попрощайся, не дави\n- Если человек интересуется — расскажи о преимуществах работы с риелтором:\n  * Бесплатная оценка недвижимости\n  * Профессиональные фото и описание\n  * Размещение на всех площадках\n  * Проверка документов и юридическое сопровождение\n  * Быстрая продажа/сдача по лучшей цене\n- Не выдумывай конкретные цифры и адреса\n- Если спрашивают про комиссию — скажи что обсудите при встрече, всё индивидуально\n- Отвечай ТОЛЬКО на русском языке\n- Максимум 2-3 предложения в сообщении",
    },
}


def _migrate_max_pages(cfg: dict):
    """Миграция max_pages → max_listings."""
    k = cfg.get("krisha", {})
    if "max_pages" in k and "max_listings" not in k:
        k["max_listings"] = k.pop("max_pages") * 20
    elif "max_pages" in k:
        del k["max_pages"]


def load_config() -> dict:
    cfg = _deep_copy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Deep merge — saved values override defaults, but missing keys get defaults
            _deep_merge(cfg, saved)
        except (json.JSONDecodeError, IOError):
            pass
    _migrate_max_pages(cfg)
    return cfg


def _deep_copy(d):
    return json.loads(json.dumps(d))


def _deep_merge(base: dict, override: dict):
    """Merge override into base recursively. Modifies base in-place."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
