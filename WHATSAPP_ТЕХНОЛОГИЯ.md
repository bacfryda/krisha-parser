# 📱 Технология WhatsApp в Krisha Parser Bot

## Общая архитектура

Программа использует **двухкомпонентную архитектуру** для работы с WhatsApp:

1. **Python GUI** (PyQt6) — основной интерфейс программы
2. **Node.js сервер** (Express + WhatsApp Web.js) — обработка WhatsApp протокола

Компоненты общаются через **HTTP REST API** на локальном порту `3457`.

---

## Основная технология: WhatsApp Web.js

### Что это?

**whatsapp-web.js** — это Node.js библиотека для работы с WhatsApp через реверс-инжиниринг протокола WhatsApp Web.

- **GitHub**: https://github.com/pedroslopez/whatsapp-web.js
- **npm**: https://www.npmjs.com/package/whatsapp-web.js
- **Версия**: 1.26.0
- **Лицензия**: Apache-2.0

### Как работает?

1. Запускает **Puppeteer** (headless Chrome браузер)
2. Открывает WhatsApp Web (web.whatsapp.com) внутри браузера
3. Эмулирует действия пользователя через браузер
4. Перехватывает WebSocket протокол WhatsApp
5. Предоставляет JavaScript API для отправки/получения сообщений

### Преимущества

✅ Не требует официального WhatsApp Business API (платный)  
✅ Работает с обычным WhatsApp аккаунтом  
✅ Бесплатный и open-source  
✅ Поддерживает все функции WhatsApp Web  
✅ Автоматическое сохранение сессии (не нужно сканировать QR каждый раз)

### Недостатки

⚠️ Использует неофициальный протокол (может сломаться при обновлениях WhatsApp)  
⚠️ Требует Node.js и npm  
⚠️ Потребляет больше ресурсов (запускает Chrome)  
⚠️ Нарушает Terms of Service WhatsApp (риск бана при массовой рассылке)

---

## Зависимости Node.js

### package.json

```json
{
  "dependencies": {
    "whatsapp-web.js": "^1.26.0",  // Основная библиотека
    "express": "^4.21.0",           // HTTP сервер для API
    "qrcode-terminal": "^0.12.0",   // QR-код в консоли
    "qrcode": "^1.5.4"              // QR-код в base64 для GUI
  }
}
```

### Установка

```bash
cd wa-server
npm install
```

Это скачает:
- `whatsapp-web.js` + все его зависимости (включая Puppeteer)
- `express` для HTTP сервера
- `qrcode` и `qrcode-terminal` для генерации QR-кодов

---

## Архитектура сервера (server.js)

### 1. Инициализация WhatsApp клиента

```javascript
const { Client, LocalAuth } = require('whatsapp-web.js');

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './wa_auth_data'  // Сохранение сессии
    }),
    puppeteer: {
        headless: true,  // Без GUI браузера
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--disable-gpu'
        ]
    }
});
```

**LocalAuth** — сохраняет сессию в папку `wa_auth_data`, чтобы не сканировать QR при каждом запуске.

### 2. События WhatsApp

```javascript
client.on('qr', (qr) => {
    // Генерируется QR-код для первой авторизации
    // Конвертируется в base64 PNG для отображения в GUI
});

client.on('ready', () => {
    // WhatsApp подключён, можно отправлять сообщения
});

client.on('message', async (msg) => {
    // Входящее сообщение
});

client.on('disconnected', (reason) => {
    // Переподключение при разрыве связи
});
```

### 3. Агрессивный Polling входящих сообщений

WhatsApp Web.js иногда **пропускает события** `message`, поэтому реализован **polling**:

```javascript
async function pollAllChats() {
    const chats = await client.getChats();
    
    for (const chat of chats) {
        if (chat.lastMessage) {
            const msgTs = chat.lastMessage.timestamp;
            const prevTs = lastSeenTimestamp.get(chat.id);
            
            if (msgTs > prevTs) {
                // Новое сообщение! Обрабатываем
                const msgs = await chat.fetchMessages({ limit: 5 });
                // Фильтруем только новые входящие
            }
        }
    }
}

// Запускается каждые 5 секунд
setInterval(pollAllChats, 5000);
```

Это гарантирует, что **ни одно сообщение не будет пропущено**.

### 4. Решение проблемы @lid номеров

WhatsApp использует два типа ID:
- `77001234567@c.us` — обычные номера
- `1234567890abcdef@lid` — новые "Link ID" (скрытые номера)

Для @lid номеров **невозможно узнать реальный номер телефона** напрямую.

**Решение**: Сохраняем `chatIdMap`:

```javascript
const chatIdMap = new Map();  // phone -> rawFrom

// При получении сообщения
chatIdMap.set('+77001234567', '1234567890abcdef@lid');

// При отправке ответа
const rawChatId = chatIdMap.get(phone);
if (rawChatId) {
    await client.sendMessage(rawChatId, message);
}
```

Это позволяет **отвечать на входящие** даже от @lid номеров.

### 5. Имитация "печатает..."

```javascript
async function sendWithTyping(chatId, message) {
    const chat = await client.getChatById(chatId);
    await chat.sendStateTyping();  // Показать "печатает..."
    await new Promise(r => setTimeout(r, 2000 + Math.random() * 2000));
    await chat.clearState();
    await client.sendMessage(chatId, message);
}
```

Делает рассылку **более человечной** (2-4 сек задержка).

---

## HTTP API эндпоинты

Python GUI общается с сервером через эти эндпоинты:

### GET /status
Проверка подключения и получение QR-кода.

**Ответ**:
```json
{
  "ready": true,
  "qr": null,
  "qr_base64": "data:image/png;base64,...",
  "phone": "77001234567",
  "name": "Имя пользователя"
}
```

### POST /send
Отправка сообщения.

**Запрос**:
```json
{
  "phone": "+77001234567",
  "message": "Привет!"
}
```

**Ответ**:
```json
{
  "success": true,
  "phone": "+77001234567",
  "delivered": true
}
```

### GET /unread
Получить непрочитанные входящие сообщения.

**Ответ**:
```json
{
  "+77001234567": [
    {
      "from": "+77001234567",
      "body": "Здравствуйте",
      "timestamp": 1709380800,
      "isRead": false
    }
  ]
}
```

### POST /mark-read
Пометить чат прочитанным (удаляет из буфера).

**Запрос**:
```json
{
  "phone": "+77001234567"
}
```

### GET /chat/:phone
История чата (последние 20 сообщений).

### POST /restart
Перезагрузить WA-клиент без удаления сессии.

### POST /reset-session
Полный сброс — удаляет авторизацию, потребуется новый QR.

### POST /shutdown
Корректное завершение с сохранением сессии.

---

## Интеграция с Python GUI

### Запуск сервера из Python

```python
import subprocess
import os

# Запуск Node.js сервера
wa_server_path = os.path.join(os.path.dirname(__file__), 'wa-server')
self.wa_process = subprocess.Popen(
    ['node', 'server.js'],
    cwd=wa_server_path,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    creationflags=subprocess.CREATE_NO_WINDOW  # Скрыть консоль
)
```

### HTTP запросы из Python

```python
import requests

# Проверка статуса
response = requests.get('http://localhost:3457/status', timeout=5)
data = response.json()

if data['ready']:
    print(f"WhatsApp подключён: {data['phone']}")
elif data['qr_base64']:
    # Показать QR-код в GUI
    qr_image = QPixmap()
    qr_image.loadFromData(base64.b64decode(data['qr_base64'].split(',')[1]))
```

### Отправка сообщения

```python
response = requests.post('http://localhost:3457/send', json={
    'phone': '+77001234567',
    'message': 'Привет!'
}, timeout=30)

result = response.json()
if result['success']:
    print("Отправлено!")
```

### Polling входящих сообщений

```python
# QTimer каждые 3 секунды
self.wa_poll_timer = QTimer()
self.wa_poll_timer.timeout.connect(self.poll_wa_messages)
self.wa_poll_timer.start(3000)

def poll_wa_messages(self):
    response = requests.get('http://localhost:3457/unread', timeout=5)
    unread = response.json()
    
    for phone, messages in unread.items():
        for msg in messages:
            # Обработать входящее сообщение
            self.handle_incoming(phone, msg['body'])
```

---

## Безопасность и ограничения

### ⚠️ Риски

1. **Нарушение ToS WhatsApp** — использование неофициального API может привести к бану аккаунта
2. **Массовая рассылка** — WhatsApp детектирует спам и блокирует номера
3. **Нестабильность** — протокол может измениться в любой момент

### ✅ Рекомендации

- Не отправлять больше **50-100 сообщений в день**
- Делать **задержки 2-5 секунд** между сообщениями
- Использовать **имитацию "печатает..."**
- Не рассылать одинаковый текст всем
- Использовать **отдельный номер** для бота (не основной)

---

## Альтернативы

### 1. WhatsApp Business API (официальный)
- **Плюсы**: Официальный, стабильный, без риска бана
- **Минусы**: Платный ($0.005-0.09 за сообщение), требует бизнес-верификации
- **Ссылка**: https://developers.facebook.com/docs/whatsapp

### 2. Baileys (Node.js)
- **Плюсы**: Не использует браузер, быстрее
- **Минусы**: Сложнее в настройке, менее стабильный
- **GitHub**: https://github.com/WhiskeySockets/Baileys

### 3. PyWhatKit (Python)
- **Плюсы**: Простой Python API
- **Минусы**: Открывает WhatsApp Web в реальном браузере (не headless)
- **GitHub**: https://github.com/Ankit404butfound/PyWhatKit

---

## Структура файлов

```
krisha-bot/
├── wa-server/
│   ├── server.js           # Основной сервер
│   ├── package.json        # npm зависимости
│   ├── node_modules/       # Установленные пакеты (после npm install)
│   └── wa_auth_data/       # Сохранённая сессия WhatsApp
│       ├── session-Default/
│       └── ...
├── gui.py                  # Python GUI (запускает wa-server)
└── ...
```

---

## Логи и отладка

### Логи сервера

Сервер выводит подробные логи в консоль:

```
🚀 WA-сервер запущен на http://localhost:3457
📱 QR-код для авторизации:
█████████████████████████████
█████████████████████████████
...
✅ WhatsApp подключён! Номер: 77001234567
🔄 Polling запущен (каждые 5 сек)
📨 [event:message] от 77001234567@c.us
✅ Resolved: +77001234567 (method: contact.number)
📩 Входящее от +77001234567: Привет!
```

### Диагностика

```bash
# Проверить статус
curl http://localhost:3457/status

# Посмотреть все чаты
curl http://localhost:3457/debug/chats

# Перезагрузить сервер
curl -X POST http://localhost:3457/restart
```

---

## Заключение

Технология основана на **whatsapp-web.js** — реверс-инжиниринге WhatsApp Web протокола. Это позволяет бесплатно отправлять и получать сообщения через обычный WhatsApp аккаунт, но требует осторожности из-за риска бана.

Архитектура с **Node.js сервером + Python GUI** обеспечивает:
- Стабильную работу с WhatsApp
- Удобный интерфейс на PyQt6
- Автоматическое сохранение сессии
- Надёжный polling входящих сообщений
- Поддержку @lid номеров

**Основные ссылки**:
- whatsapp-web.js: https://github.com/pedroslopez/whatsapp-web.js
- Puppeteer: https://github.com/puppeteer/puppeteer
- Express.js: https://expressjs.com
