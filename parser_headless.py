"""Headless парсер krisha.kz через requests + BS4 для фонового парсинга."""
import re
import time
import requests
from bs4 import BeautifulSoup

from parser import build_search_url, normalize_phone

BASE_URL = "https://krisha.kz"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://krisha.kz/",
}


def get_listing_urls_headless(cfg: dict) -> list[dict]:
    """Собирает ссылки на объявления через requests."""
    max_pages = cfg["krisha"].get("max_pages", 3)
    listings = []

    for page in range(1, max_pages + 1):
        url = build_search_url(cfg, page)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("a.a-card__title")
        if not cards:
            cards = soup.select("div[data-id] a[href*='/a/show/']")
        if not cards:
            break

        for card in cards:
            href = card.get("href", "")
            title = card.get_text(strip=True)
            # Пробуем достать цену из карточки
            parent = card.find_parent("div", {"data-id": True})
            price = ""
            if parent:
                price_el = parent.select_one(".a-card__price")
                if price_el:
                    price = price_el.get_text(strip=True)
            if href:
                full_url = BASE_URL + href if href.startswith("/") else href
                listings.append({"url": full_url, "title": title, "price": price})

        time.sleep(2)

    return listings


def extract_phone_headless(listing_url: str) -> str | None:
    """Извлекает номер телефона через requests."""
    try:
        resp = requests.get(listing_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # tel: ссылки
    for link in soup.select("a[href^='tel:']"):
        raw = link.get("href", "").replace("tel:", "").strip()
        phone = normalize_phone(raw)
        if phone and len(phone) == 12:
            return phone

    # Текст страницы
    text = soup.get_text()
    phones = re.findall(
        r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", text
    )
    if phones:
        return normalize_phone(phones[0])

    # API endpoint
    match = re.search(r"/a/show/(\d+)", listing_url) or re.search(r"/(\d+)/?$", listing_url)
    if match:
        ad_id = match.group(1)
        try:
            r = requests.get(f"{BASE_URL}/a/show/{ad_id}/phone", headers=HEADERS, timeout=10)
            if r.ok and "application/json" in r.headers.get("content-type", ""):
                phone_val = r.json().get("phone", "")
                if phone_val:
                    return normalize_phone(phone_val)
        except Exception:
            pass

    return None
