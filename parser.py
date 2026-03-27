"""Парсер krisha.kz через undetected_chromedriver."""
import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich.console import Console

from browser import get_driver

console = Console()

BASE_URL = "https://krisha.kz"


def build_search_url(cfg: dict, page: int = 1) -> str:
    """Собирает URL поиска из конфига со всеми фильтрами."""
    k = cfg["krisha"]
    deal = k.get("deal_type", "sale")
    region_alias = k.get("region_alias", "")

    # Базовый путь
    if deal == "rent":
        path = "/arenda/kvartiry/"
    else:
        path = "/prodazha/kvartiry/"

    # Добавляем регион в путь
    if region_alias:
        path += f"{region_alias}/"

    params = []

    # Комнаты (множественный выбор)
    rooms = k.get("rooms", [])
    if rooms:
        for r in rooms:
            params.append(f"das[live.rooms]={r}")

    # Цена
    if k.get("price_from"):
        params.append(f"das[price][from]={k['price_from']}")
    if k.get("price_to"):
        params.append(f"das[price][to]={k['price_to']}")

    # Чекбоксы
    if k.get("has_photo"):
        params.append("das[_sys.hasphoto]=1")
    if k.get("novostroiki"):
        params.append("das[novostroiki]=1")
    if k.get("from_owner"):
        params.append("das[who]=1")
    if k.get("from_agent"):
        params.append("das[_sys.fromAgent]=1")

    # Тип дома (множественный)
    for bt in k.get("building_type", []):
        params.append(f"das[flat.building]={bt}")

    # Этаж
    if k.get("floor_from"):
        params.append(f"das[flat.floor][from]={k['floor_from']}")
    if k.get("floor_to"):
        params.append(f"das[flat.floor][to]={k['floor_to']}")

    # Этажей в доме
    if k.get("house_floors_from"):
        params.append(f"das[house.floor_num][from]={k['house_floors_from']}")
    if k.get("house_floors_to"):
        params.append(f"das[house.floor_num][to]={k['house_floors_to']}")

    # Год постройки
    if k.get("year_from"):
        params.append(f"das[house.year][from]={k['year_from']}")
    if k.get("year_to"):
        params.append(f"das[house.year][to]={k['year_to']}")

    # Не последний / не первый этаж
    if k.get("not_last_floor"):
        params.append("das[floor_not_last]=1")
    if k.get("not_first_floor"):
        params.append("das[floor_not_first]=1")

    # Площадь общая
    if k.get("square_from"):
        params.append(f"das[live.square][from]={k['square_from']}")
    if k.get("square_to"):
        params.append(f"das[live.square][to]={k['square_to']}")

    # Площадь кухни
    if k.get("kitchen_from"):
        params.append(f"das[live.square_k][from]={k['kitchen_from']}")
    if k.get("kitchen_to"):
        params.append(f"das[live.square_k][to]={k['kitchen_to']}")

    # В залоге
    if k.get("mortgage"):
        params.append(f"das[mortgage]={k['mortgage']}")

    # Бывшее общежитие
    if k.get("priv_dorm"):
        params.append(f"das[flat.priv_dorm]={k['priv_dorm']}")

    # Возможен обмен
    if k.get("has_change"):
        params.append("das[has_change]=1")

    # Санузел (множественный)
    for t in k.get("toilet", []):
        params.append(f"das[flat.toilet]={t}")

    # Телефон в квартире (множественный)
    for p in k.get("phone_line", []):
        params.append(f"das[flat.phone]={p}")

    # Поиск по тексту
    if k.get("text_search"):
        params.append(f"_txt_={k['text_search']}")

    # Страница
    if page > 1:
        params.append(f"page={page}")

    url = BASE_URL + path
    if params:
        url += "?" + "&".join(params)
    return url


def get_listing_urls(cfg: dict) -> list[dict]:
    """Собирает ссылки на объявления со страниц поиска через Selenium."""
    driver = get_driver()
    max_pages = cfg["krisha"].get("max_pages", 3)
    listings = []

    for page in range(1, max_pages + 1):
        url = build_search_url(cfg, page)
        console.print(f"[cyan]Страница {page}:[/] {url}")

        driver.get(url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Карточки объявлений
        cards = soup.select("a.a-card__title")
        if not cards:
            cards = soup.select("div[data-id] a[href*='/a/show/']")
        if not cards:
            console.print("[yellow]Объявления не найдены на странице.[/]")
            break

        for card in cards:
            href = card.get("href", "")
            title = card.get_text(strip=True)
            if href:
                full_url = BASE_URL + href if href.startswith("/") else href
                listings.append({"url": full_url, "title": title})

        console.print(f"  [green]Найдено {len(cards)} карточек[/]")
        time.sleep(2)

    console.print(f"\n[green]Итого объявлений: {len(listings)}[/]")
    return listings


def extract_phone_from_listing(listing_url: str) -> str | None:
    """Извлекает номер телефона со страницы объявления через Selenium."""
    driver = get_driver()

    try:
        driver.get(listing_url)
        time.sleep(2)

        # Ищем и кликаем кнопку "Показать телефон"
        try:
            show_phone_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    ".offer__contacts-phones__btn, "
                    "[data-id='show-phone'], "
                    ".show-phones, "
                    "button.phone-button, "
                    ".offer__advert-short-info__button"
                ))
            )
            show_phone_btn.click()
            time.sleep(2)
        except Exception:
            pass  # Кнопка может отсутствовать, номер уже виден

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Ищем телефон в ссылках tel:
        tel_links = soup.select("a[href^='tel:']")
        for link in tel_links:
            raw = link.get("href", "").replace("tel:", "").strip()
            phone = normalize_phone(raw)
            if phone and len(phone) == 12:  # +7XXXXXXXXXX
                return phone

        # Ищем в data-атрибутах
        phone_els = soup.select("[data-phone]")
        for el in phone_els:
            raw = el.get("data-phone", "")
            if raw:
                return normalize_phone(raw)

        # Ищем в тексте страницы
        text = soup.get_text()
        phones = re.findall(
            r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
            text,
        )
        if phones:
            return normalize_phone(phones[0])

    except Exception as e:
        console.print(f"  [red]Ошибка: {e}[/]")

    return None


def extract_price_from_listing(listing_url: str) -> str:
    """Извлекает цену из уже загруженной страницы."""
    driver = get_driver()
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        price_el = soup.select_one(".offer__price, .a-card__price")
        if price_el:
            return price_el.get_text(strip=True)
    except Exception:
        pass
    return ""


def normalize_phone(raw: str) -> str:
    """Приводит номер к формату +7XXXXXXXXXX."""
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    if not digits.startswith("7"):
        # Не казахстанский номер — возвращаем как есть с +
        return "+" + digits
    return "+" + digits[:11]
