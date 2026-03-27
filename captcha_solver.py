"""
Решение CAPTCHA для krisha.kz.

Стратегия решения reCAPTCHA v2:
  1. playwright-recaptcha (бесплатно, аудио speech-to-text)
  2. Anti-Captcha API (платно, fallback)

Cloudflare Turnstile — только через Anti-Captcha.

Адаптировано для Playwright (sync API).
"""
import time
import re

# Кулдаун между решениями капчи (защита от блокировки Google)
_last_captcha_solve_time = 0.0
_CAPTCHA_COOLDOWN_SEC = 60  # минимум 60 сек между попытками

# Rate-limit: макс N решений за период (защита от бана Google)
_MAX_SOLVES_PER_WINDOW = 3       # макс 3 решения
_RATE_WINDOW_SEC = 5 * 60        # за 5 минут
_RATE_LIMIT_PAUSE_SEC = 120      # пауза после rate limit
_solve_timestamps: list[float] = []  # история решений


def solve_captcha(page, api_key: str = "", log_fn=None) -> bool:
    """
    Определяет тип капчи и решает.
    Встроен кулдаун 60 сек + лимит 3 решения за 5 мин (защита от бана Google).
    """
    global _last_captcha_solve_time, _solve_timestamps

    # Rate-limit и кулдаун перенесены в extract_phone (перед кликом)
    captcha_type = detect_captcha_type(page)

    if log_fn:
        log_fn(f"  -- Тип капчи: {captcha_type or 'не определён'}")

    result = False

    if captcha_type == "recaptcha":
        if log_fn:
            log_fn("  -- Пробую бесплатный метод...")
        result = _solve_recaptcha_free(page, log_fn)

    elif captcha_type == "turnstile":
        if log_fn:
            log_fn("  -- Turnstile: бесплатный метод не поддерживает")

    else:
        if log_fn:
            log_fn("  -- Тип капчи не определён, пропуск")

    _last_captcha_solve_time = time.time()
    if result:
        _solve_timestamps.append(time.time())
    return result


# ─── Бесплатный reCAPTCHA v2 (playwright-recaptcha) ─────────────

def _solve_recaptcha_free(page, log_fn=None) -> bool:
    """Решает reCAPTCHA v2 бесплатно через аудио challenge.
    Пытается решить любую рекапчу (и visible, и invisible).
    """
    try:
        from playwright_recaptcha import recaptchav2
    except ImportError:
        if log_fn:
            log_fn("  -- playwright-recaptcha не установлен")
        return False

    if log_fn:
        log_fn("  -- Решаю reCAPTCHA v2 (бесплатно, аудио)...")

    try:
        solver = recaptchav2.SyncSolver(page)
        token = solver.solve_recaptcha(attempts=1, wait=True, wait_timeout=15)

        if token:
            if log_fn:
                log_fn("  -- reCAPTCHA решена (бесплатно) ✅")
            time.sleep(1.5)
            return True
        return False

    except Exception as e:
        err_msg = str(e)
        # Если Google забанил — длинная пауза
        if "rate limit" in err_msg.lower():
            if log_fn:
                log_fn(f"  -- Бесплатный метод: rate limit! Пауза {_RATE_LIMIT_PAUSE_SEC} сек...")
            time.sleep(_RATE_LIMIT_PAUSE_SEC)
        else:
            if log_fn:
                if len(err_msg) > 100:
                    err_msg = err_msg[:100] + "..."
                log_fn(f"  -- Бесплатный метод: {err_msg}")
        return False


# ─── Anti-Captcha reCAPTCHA v2 (платный fallback) ───────────────

def _solve_recaptcha_anticaptcha(page, api_key: str, log_fn=None) -> bool:
    """Решает reCAPTCHA v2 через Anti-Captcha API (платно)."""
    try:
        from python3_anticaptcha.recaptcha_v2 import ReCaptchaV2
        from python3_anticaptcha.core.enum import CaptchaTypeEnm
    except Exception as imp_err:
        if log_fn:
            log_fn(f"  -- python3-anticaptcha import error: {imp_err}")
        return False

    sitekey = _find_recaptcha_sitekey(page)
    if not sitekey:
        if log_fn:
            log_fn("  -- reCAPTCHA sitekey не найден")
        return False

    page_url = page.url
    if log_fn:
        log_fn(f"  -- Anti-Captcha: решаю reCAPTCHA v2 (sitekey: {sitekey[:20]}...)")

    try:
        result = ReCaptchaV2(
            api_key=api_key,
            captcha_type=CaptchaTypeEnm.RecaptchaV2TaskProxyless,
            websiteURL=page_url,
            websiteKey=sitekey,
        ).captcha_handler()

        if result.get("errorId"):
            if log_fn:
                log_fn(f"  -- Anti-Captcha ошибка: {result.get('errorDescription', result)}")
            return False

        token = result.get("solution", {}).get("gRecaptchaResponse", "")
        if not token:
            if log_fn:
                log_fn("  -- Anti-Captcha не вернул токен")
            return False

        _inject_recaptcha_token(page, token)
        if log_fn:
            log_fn("  -- reCAPTCHA решена (Anti-Captcha) ✅")
        time.sleep(1.5)
        return True

    except Exception as e:
        if log_fn:
            log_fn(f"  -- Anti-Captcha ошибка: {e}")
        return False


# ─── Anti-Captcha Turnstile (платный) ───────────────────────────

def _solve_turnstile_anticaptcha(page, api_key: str, log_fn=None) -> bool:
    """Решает Cloudflare Turnstile через Anti-Captcha API."""
    try:
        from python3_anticaptcha.turnstile import Turnstile
        from python3_anticaptcha.core.enum import CaptchaTypeEnm
    except Exception as imp_err:
        if log_fn:
            log_fn(f"  -- python3-anticaptcha import error: {imp_err}")
        return False

    sitekey = _find_turnstile_sitekey(page)
    if not sitekey:
        if log_fn:
            log_fn("  -- Turnstile sitekey не найден")
        return False

    page_url = page.url
    if log_fn:
        log_fn(f"  -- Anti-Captcha: решаю Turnstile (sitekey: {sitekey[:20]}...)")

    try:
        result = Turnstile(
            api_key=api_key,
            captcha_type=CaptchaTypeEnm.TurnstileTaskProxyless,
            websiteURL=page_url,
            websiteKey=sitekey,
        ).captcha_handler()

        if result.get("errorId"):
            if log_fn:
                log_fn(f"  -- Anti-Captcha ошибка: {result.get('errorDescription', result)}")
            return False

        token = result.get("solution", {}).get("token", "")
        if not token:
            if log_fn:
                log_fn("  -- Anti-Captcha не вернул токен Turnstile")
            return False

        _inject_turnstile_token(page, token)
        if log_fn:
            log_fn("  -- Turnstile решена ✅")
        time.sleep(1.5)
        return True

    except Exception as e:
        if log_fn:
            log_fn(f"  -- Anti-Captcha Turnstile ошибка: {e}")
        return False


# ─── Детекция типа капчи ────────────────────────────────────────

def detect_captcha_type(page) -> str | None:
    """Определяет тип ВИДИМОЙ капчи: 'turnstile', 'recaptcha' или None.
    Скрытые/невидимые рекапчи (для форм обратного звонка и т.п.) игнорируются.
    """
    try:
        # Turnstile — проверяем видимые элементы
        turnstile = page.query_selector_all(
            '.cf-turnstile, [data-sitekey][class*="turnstile"], '
            'iframe[src*="challenges.cloudflare.com"]'
        )
        for el in turnstile:
            try:
                if el.is_visible():
                    return "turnstile"
            except Exception:
                pass

        cf_input = page.query_selector('input[name="cf-turnstile-response"]')
        if cf_input:
            return "turnstile"

        # reCAPTCHA — проверяем ВИДИМЫЕ iframe/элементы
        recaptcha_els = page.query_selector_all(
            'iframe[src*="recaptcha"], .g-recaptcha, #recaptcha'
        )
        has_visible_recaptcha = False
        for el in recaptcha_els:
            try:
                if el.is_visible():
                    # Дополнительно: проверяем что iframe не внутри скрытого контейнера
                    # (попапы "Заказать звонок" содержат скрытую рекапчу)
                    parent_hidden = page.evaluate("""(el) => {
                        var p = el;
                        while (p && p !== document.body) {
                            var s = window.getComputedStyle(p);
                            if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return true;
                            // Проверяем что не внутри модалки/попапа
                            var cls = (p.className || '').toLowerCase();
                            if (cls.indexOf('modal') !== -1 || cls.indexOf('popup') !== -1 || cls.indexOf('dialog') !== -1) {
                                if (s.display === 'none' || p.offsetHeight === 0) return true;
                            }
                            p = p.parentElement;
                        }
                        return false;
                    }""", el)
                    if not parent_hidden:
                        has_visible_recaptcha = True
                        break
            except Exception:
                pass

        if has_visible_recaptcha:
            return "recaptcha"

        # Fallback: проверяем HTML только для Turnstile (менее ложных срабатываний)
        html = page.content()
        if "challenges.cloudflare.com" in html or "cf-turnstile" in html:
            return "turnstile"

        # НЕ проверяем HTML на "recaptcha" — слишком много ложных срабатываний
        # (скрытые рекапчи в формах обратного звонка и т.п.)

    except Exception:
        pass
    return None


def detect_captcha(page) -> bool:
    """Проверяет наличие любой капчи на странице."""
    ctype = detect_captcha_type(page)
    if ctype:
        return True
    try:
        body_text = page.evaluate("document.body.textContent")
        if "Я не робот" in body_text or "not a robot" in body_text:
            return True
        if "Verify you are human" in body_text:
            return True
    except Exception:
        pass
    return False


# ─── Поиск sitekey ──────────────────────────────────────────────

def _find_turnstile_sitekey(page) -> str | None:
    """Извлекает sitekey Cloudflare Turnstile."""
    try:
        els = page.query_selector_all(".cf-turnstile[data-sitekey]")
        for el in els:
            key = el.get_attribute("data-sitekey")
            if key:
                return key

        els = page.query_selector_all("[data-sitekey]")
        for el in els:
            key = el.get_attribute("data-sitekey")
            if key and key.startswith("0x"):
                return key

        iframes = page.query_selector_all('iframe[src*="challenges.cloudflare.com"]')
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            match = re.search(r"k=([A-Za-z0-9_-]+)", src)
            if match:
                return match.group(1)

        html = page.content()
        match = re.search(r'sitekey["\s:=]+["\'](0x[A-Za-z0-9_-]{20,})["\']', html)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def _find_recaptcha_sitekey(page) -> str | None:
    """Извлекает sitekey reCAPTCHA."""
    try:
        els = page.query_selector_all(".g-recaptcha[data-sitekey]")
        for el in els:
            key = el.get_attribute("data-sitekey")
            if key:
                return key

        iframes = page.query_selector_all('iframe[src*="recaptcha"]')
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            match = re.search(r"k=([A-Za-z0-9_-]+)", src)
            if match:
                return match.group(1)

        page_source = page.content()
        match = re.search(r'sitekey["\s:]+["\']([A-Za-z0-9_-]{20,})["\']', page_source)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


# ─── Инъекция токенов ────────────────────────────────────────────

def _inject_turnstile_token(page, token: str):
    """Вставляет решённый токен Turnstile и вызывает callback."""
    page.evaluate("""(token) => {
        var inputs = document.querySelectorAll(
            'input[name="cf-turnstile-response"], [name="cf-turnstile-response"]'
        );
        inputs.forEach(function(inp) { inp.value = token; });

        var els = document.querySelectorAll('[data-callback]');
        els.forEach(function(el) {
            var cbName = el.getAttribute('data-callback');
            if (cbName && typeof window[cbName] === 'function') {
                try { window[cbName](token); } catch(e) {}
            }
        });

        var form = document.querySelector('form');
        if (form) { try { form.submit(); } catch(e) {} }
    }""", token)


def _inject_recaptcha_token(page, token: str):
    """Вставляет решённый токен reCAPTCHA в форму и сабмитит."""
    page.evaluate("""(token) => {
        var ta = document.getElementById('g-recaptcha-response');
        if (!ta) ta = document.querySelector('[name="g-recaptcha-response"]');
        if (ta) { ta.style.display = 'block'; ta.value = token; }

        if (typeof ___grecaptcha_cfg !== 'undefined') {
            var keys = Object.keys(___grecaptcha_cfg.clients);
            for (var i = 0; i < keys.length; i++) {
                var client = ___grecaptcha_cfg.clients[keys[i]];
                try {
                    var findCb = function(obj) {
                        if (!obj || typeof obj !== 'object') return null;
                        if (typeof obj.callback === 'function') return obj.callback;
                        for (var k in obj) { var r = findCb(obj[k]); if (r) return r; }
                        return null;
                    };
                    var cb = findCb(client);
                    if (cb) cb(token);
                } catch(e) {}
            }
        }
    }""", token)
