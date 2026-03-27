"""WhatsApp отправка через undetected_chromedriver."""
import time
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich.console import Console

from browser import get_driver

console = Console()

_wa_ready = False


def init_whatsapp() -> bool:
    """Открывает WhatsApp Web и ждёт сканирования QR-кода."""
    global _wa_ready
    driver = get_driver()

    try:
        driver.get("https://web.whatsapp.com")
        console.print("[yellow]Отсканируйте QR-код в WhatsApp Web...[/]")
        console.print("[yellow]Ожидание авторизации (до 90 сек)...[/]")

        # Ждём пока загрузится основной интерфейс
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "div[data-tab='3'], "
                "div[contenteditable='true'][data-tab='3'], "
                "header span[data-icon='back-light']"
            ))
        )
        _wa_ready = True
        console.print("[green]WhatsApp Web подключён![/]")
        return True
    except Exception as e:
        console.print(f"[red]Ошибка подключения WhatsApp: {e}[/]")
        return False


def send_message(phone: str, message: str) -> bool:
    """Отправляет сообщение на номер через WhatsApp Web."""
    global _wa_ready
    if not _wa_ready:
        console.print("[red]WhatsApp не инициализирован![/]")
        return False

    driver = get_driver()

    try:
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        encoded_msg = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"

        driver.get(url)
        time.sleep(5)

        # Проверяем нет ли ошибки "номер не зарегистрирован"
        try:
            error = driver.find_element(By.CSS_SELECTOR, "div._2jGOb, div[data-animate-modal-popup='true']")
            if error:
                console.print(f"  [yellow]⚠ Номер {phone} не в WhatsApp[/]")
                return False
        except Exception:
            pass

        # Ждём кнопку отправки
        send_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "span[data-icon='send'], "
                "button[aria-label='Send'], "
                "button[aria-label='Отправить']"
            ))
        )
        send_btn.click()
        time.sleep(2)

        console.print(f"  [green]✓ Отправлено: {phone}[/]")
        return True
    except Exception as e:
        console.print(f"  [red]✗ Ошибка отправки {phone}: {e}[/]")
        return False
