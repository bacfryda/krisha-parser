"""
Контроллер WhatsApp Web — работает через JS-инъекции в QWebEngineView.

Стратегия работы:
1. Отправка: открываем wa.me/PHONE?text=MSG — WhatsApp сам открывает чат с текстом
2. Клик отправки: ищем кнопку send по data-icon="send" (стабильный атрибут)
3. Чтение ответов: парсим DOM открытого чата, ищем входящие сообщения
4. Мониторинг: периодически проверяем непрочитанные чаты
"""

# JS-скрипты для работы с WhatsApp Web

JS_CHECK_AUTH = """
(function() {
    var side = document.querySelector('#side');
    var pane = document.querySelector('#pane-side');
    var search = document.querySelector('div[data-tab="3"]');
    if (side || pane || search) return 'authorized';
    var qr = document.querySelector('canvas[aria-label], div[data-ref]');
    if (qr) return 'qr_visible';
    return 'loading';
})();
"""

JS_CLICK_SEND = """
(function() {
    // Способ 1: кнопка с иконкой send
    var sendIcon = document.querySelector('span[data-icon="send"]');
    if (sendIcon) {
        var btn = sendIcon.closest('button') || sendIcon.closest('[role="button"]') || sendIcon.parentElement;
        if (btn) { btn.click(); return 'clicked_send'; }
    }
    // Способ 2: кнопка в footer чата
    var footer = document.querySelector('footer');
    if (footer) {
        var btns = footer.querySelectorAll('button, [role="button"]');
        for (var b of btns) {
            var icon = b.querySelector('span[data-icon="send"]');
            if (icon) { b.click(); return 'clicked_footer_send'; }
        }
    }
    return 'send_not_found';
})();
"""

JS_CHECK_INVALID_PHONE = """
(function() {
    // Проверяем popup "Номер не зарегистрирован"
    var popups = document.querySelectorAll('[data-animate-modal-popup], ._3J6wB, .overlay');
    for (var p of popups) {
        var text = p.innerText || '';
        if (text.includes('invalid') || text.includes('не существует') ||
            text.includes('not on WhatsApp') || text.includes('Phone number shared')) {
            // Закрываем popup
            var okBtn = p.querySelector('div[role="button"]');
            if (okBtn) okBtn.click();
            return 'invalid_phone';
        }
    }
    return 'ok';
})();
"""

JS_READ_LAST_MESSAGES = """
(function() {
    // Читаем последние сообщения из открытого чата
    var messages = [];
    // Ищем контейнер сообщений
    var msgContainer = document.querySelector('#main div[role="application"]')
        || document.querySelector('#main .copyable-area');
    if (!msgContainer) return JSON.stringify({error: 'no_chat_open'});

    // Все блоки сообщений
    var rows = msgContainer.querySelectorAll('div.message-in, div.message-out, div[data-id]');
    var lastMessages = Array.from(rows).slice(-10);

    for (var row of lastMessages) {
        var textEl = row.querySelector('.selectable-text span, .copyable-text span');
        var text = textEl ? textEl.innerText : '';
        if (!text) continue;

        // Определяем входящее или исходящее
        var isIncoming = row.classList.contains('message-in')
            || row.closest('.message-in') !== null
            || (row.getAttribute('data-id') && row.getAttribute('data-id').startsWith('false'));

        // Время
        var timeEl = row.querySelector('.copyable-text[data-pre-plain-text]');
        var time = timeEl ? timeEl.getAttribute('data-pre-plain-text') : '';

        messages.push({
            text: text,
            incoming: isIncoming,
            time: time
        });
    }
    return JSON.stringify({messages: messages});
})();
"""

JS_GET_UNREAD_CHATS = """
(function() {
    // Ищем чаты с непрочитанными сообщениями
    var unread = [];
    var chatItems = document.querySelectorAll('#pane-side div[data-id], #pane-side [role="listitem"]');

    for (var chat of chatItems) {
        // Бейдж с количеством непрочитанных
        var badge = chat.querySelector('span[data-icon="unread-count"], .aumms1qt, span.x1rg5ohu');
        if (!badge) continue;

        var count = parseInt(badge.innerText) || 0;
        if (count === 0) continue;

        // Имя/номер контакта
        var nameEl = chat.querySelector('span[dir="auto"][title], span._11JPr');
        var name = nameEl ? (nameEl.getAttribute('title') || nameEl.innerText) : 'Unknown';

        unread.push({name: name, count: count});
    }
    return JSON.stringify(unread);
})();
"""

JS_OPEN_CHAT_BY_PHONE = """
(function(phone) {
    // Кликаем на поле поиска
    var searchBox = document.querySelector('div[data-tab="3"]');
    if (!searchBox) return 'search_not_found';

    searchBox.click();
    searchBox.focus();

    // Вводим номер
    var input = document.querySelector('div[data-tab="3"] div[contenteditable="true"]')
        || document.querySelector('div[data-tab="3"] input');
    if (!input) return 'input_not_found';

    // Очищаем и вводим
    input.textContent = phone;
    input.dispatchEvent(new Event('input', {bubbles: true}));

    return 'searching';
})('%PHONE%');
"""

JS_GET_CHAT_PHONE = """
(function() {
    // Получаем номер/имя текущего открытого чата
    var header = document.querySelector('#main header');
    if (!header) return '';
    var nameEl = header.querySelector('span[dir="auto"][title], span._11JPr');
    return nameEl ? (nameEl.getAttribute('title') || nameEl.innerText) : '';
})();
"""
