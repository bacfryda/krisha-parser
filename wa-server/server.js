/**
 * WhatsApp Web.js сервер
 * 
 * Работает через реверс-инжиниренный протокол WhatsApp Web.
 * Предоставляет HTTP API для Python GUI.
 * 
 * Эндпоинты:
 *   GET  /status        — статус подключения + QR-код
 *   POST /send          — отправить сообщение {phone, message}
 *   GET  /unread        — получить непрочитанные сообщения
 *   GET  /chat/:phone   — история чата с номером
 *   POST /mark-read     — пометить чат прочитанным {phone}
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');

const app = express();
app.use(express.json());

const PORT = 3457;

// Состояние
let currentQR = null;
let currentQRBase64 = null;
let isReady = false;
let clientInfo = null;

// Хранилище входящих сообщений (phone -> messages[])
const incomingMessages = new Map();
// Хранилище оригинальных chatId для ответа (phone -> rawFrom)
const chatIdMap = new Map();
// Множество уже обработанных message id (защита от дубликатов)
const processedMsgIds = new Set();
// Timestamp момента ready — игнорируем все сообщения старше этого
let readyTimestamp = 0;

// ─── Автоопределение пути к Chrome ─────────────────────────────
function findChromePath() {
    if (process.platform !== 'win32') return undefined;
    const fs = require('fs');
    const candidates = [
        process.env.CHROME_PATH,
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        process.env.LOCALAPPDATA && (process.env.LOCALAPPDATA + '\\Google\\Chrome\\Application\\chrome.exe'),
        process.env.PROGRAMFILES && (process.env.PROGRAMFILES + '\\Google\\Chrome\\Application\\chrome.exe'),
        process.env['PROGRAMFILES(X86)'] && (process.env['PROGRAMFILES(X86)'] + '\\Google\\Chrome\\Application\\chrome.exe'),
    ];
    for (const p of candidates) {
        if (p && fs.existsSync(p)) return p;
    }
    return undefined;
}

const chromePath = findChromePath();
if (chromePath) {
    console.log('Chrome найден:', chromePath);
} else {
    console.log('⚠️ Chrome не найден, Puppeteer попробует встроенный');
}

// ─── WhatsApp клиент ───────────────────────────────────────────

const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './wa_auth_data'
    }),
    puppeteer: {
        headless: true,
        executablePath: chromePath,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--disable-gpu'
        ]
    },
    // Получаем все сообщения включая те что уже были до подключения
    syncFullHistory: false,
});

client.on('qr', (qr) => {
    currentQR = qr;
    currentQRBase64 = null;
    isReady = false;
    console.log('\n📱 QR-код для авторизации:');
    qrcode.generate(qr, { small: true });
    console.log('Отсканируйте QR-код в WhatsApp на телефоне\n');
    // Генерируем base64 PNG для GUI (синхронно ждём)
    QRCode.toDataURL(qr, { width: 300, margin: 2 }).then(url => {
        currentQRBase64 = url;
        console.log('✅ QR base64 готов для GUI (' + url.length + ' символов)');
    }).catch((err) => {
        console.error('❌ Ошибка генерации QR base64:', err.message);
    });
});

client.on('ready', () => {
    isReady = true;
    currentQR = null;
    currentQRBase64 = null;
    clientInfo = client.info;
    readyTimestamp = Math.floor(Date.now() / 1000);
    console.log(`✅ WhatsApp подключён! Номер: ${client.info.wid.user}`);
    console.log(`   readyTimestamp: ${readyTimestamp} — сообщения старше этого игнорируются`);
    startPolling();
});

client.on('authenticated', () => {
    console.log('🔐 Авторизация успешна, сессия сохранена');
});

client.on('auth_failure', (msg) => {
    console.error('❌ Ошибка авторизации:', msg);
    isReady = false;
});

client.on('disconnected', (reason) => {
    console.log('🔌 Отключён:', reason);
    isReady = false;
    // Переподключаемся
    client.initialize();
});

// Логируем изменения состояния
client.on('change_state', (state) => {
    console.log(`🔄 WA состояние: ${state}`);
});

// Логируем появление новых чатов
client.on('chat', (chat) => {
    console.log(`💬 [event:chat] Новый чат: ${chat.name || chat.id._serialized}`);
});

// Логируем ВСЕ события для диагностики
client.on('message_ack', (msg, ack) => {
    // ack: 0=pending, 1=sent, 2=received, 3=read, 4=played
    if (!msg.fromMe && ack >= 1) {
        console.log(`📨 [ack] ${msg.from} ack=${ack}`);
    }
});

client.on('message_revoke_everyone', (after, before) => {
    console.log(`🗑️ [revoke] сообщение удалено`);
});

// Очистка processedMsgIds каждые 30 мин (защита от утечки памяти)
setInterval(() => {
    if (processedMsgIds.size > 5000) {
        processedMsgIds.clear();
        console.log('🧹 Очистка processedMsgIds');
    }
}, 30 * 60 * 1000);

// Слушаем входящие сообщения
client.on('message', async (msg) => {
    console.log(`📨 [event:message] raw: from=${msg.from} fromMe=${msg.fromMe} body="${(msg.body || '').substring(0, 30)}"`);
    if (msg.fromMe) return;
    if (msg.from.includes('@g.us') || msg.from === 'status@broadcast') return;

    const msgId = msg.id._serialized;
    if (processedMsgIds.has(msgId)) return;
    processedMsgIds.add(msgId);

    console.log(`📨 [event:message] от ${msg.from}`);
    await handleIncomingMessage(msg);
});

// message_create как backup
client.on('message_create', async (msg) => {
    if (msg.fromMe) return;
    if (msg.from.includes('@g.us') || msg.from === 'status@broadcast') return;

    const msgId = msg.id._serialized;
    if (processedMsgIds.has(msgId)) return;
    processedMsgIds.add(msgId);

    console.log(`📨 [event:message_create] от ${msg.from}`);
    await handleIncomingMessage(msg);
});

// ─── Polling: агрессивный мониторинг ВСЕХ чатов ────────────────

// Храним последний timestamp для каждого чата
const lastSeenTimestamp = new Map();

// Основной polling — проверяет ВСЕ чаты, логирует всё
async function pollAllChats() {
    if (!isReady) return;
    
    try {
        const chats = await client.getChats();
        const nonGroupChats = chats.filter(c => !c.isGroup);
        
        console.log(`🔍 [poll] Проверяю ${nonGroupChats.length} чатов...`);
        
        for (const chat of nonGroupChats) {
            const chatId = chat.id._serialized;
            const chatName = chat.name || chatId;
            
            if (chat.lastMessage) {
                const lm = chat.lastMessage;
                const msgTs = lm.timestamp || 0;
                const prevTs = lastSeenTimestamp.get(chatId) || 0;
                
                // Если timestamp изменился — это потенциально новое сообщение
                if (msgTs > prevTs) {
                    console.log(`  💬 ${chatName}: lastMsg ts=${msgTs} fromMe=${lm.fromMe} body="${(lm.body || '').substring(0, 30)}" (prev=${prevTs})`);
                    console.log(`    ✨ НОВЫЙ timestamp! Обрабатываю...`);
                    
                    // Проверяем fromMe — но НЕ доверяем ему полностью
                    if (!lm.fromMe) {
                        console.log(`    ✅ fromMe=false, точно входящее`);
                    } else {
                        console.log(`    ⚠️ fromMe=true, но проверяю через fetchMessages...`);
                    }
                    
                    // Всегда fetchMessages для проверки
                    try {
                        const msgs = await chat.fetchMessages({ limit: 5 });
                        
                        // Фильтруем только новые сообщения (timestamp > prevTs)
                        const newMsgs = msgs.filter(m => {
                            if (m.fromMe) return false;
                            if (!m.body) return false;
                            if (!m.timestamp || m.timestamp <= prevTs) return false;
                            if (processedMsgIds.has(m.id._serialized)) return false;
                            return true;
                        });
                        
                        // Сортируем по timestamp (старые → новые)
                        newMsgs.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
                        
                        console.log(`      📦 Найдено ${newMsgs.length} новых сообщений`);
                        
                        // Обрабатываем по порядку
                        for (const msg of newMsgs) {
                            const msgId = msg.id._serialized;
                            processedMsgIds.add(msgId);
                            console.log(`      📩 ВХОДЯЩЕЕ! ts=${msg.timestamp} от ${msg.from}: "${(msg.body || '').substring(0, 50)}"`);
                            await handleIncomingMessage(msg);
                            
                            // Обновляем lastSeenTimestamp после каждого сообщения
                            if (msg.timestamp && msg.timestamp > (lastSeenTimestamp.get(chatId) || 0)) {
                                lastSeenTimestamp.set(chatId, msg.timestamp);
                            }
                        }
                    } catch (e) {
                        console.log(`      ❌ fetchMessages ошибка: ${e.message}`);
                        // Если fetchMessages не сработал, обновляем timestamp на основе lastMessage
                        lastSeenTimestamp.set(chatId, msgTs);
                    }
                }
            } else {
                // Нет lastMessage — пустой чат, пропускаем
            }
        }
        
        console.log(`✅ [poll] Проверка завершена (буфер: ${incomingMessages.size} чатов)\n`);
    } catch (e) {
        console.log(`❌ [poll] Ошибка: ${e.message}`);
    }
}

// Запускаем polling после ready
function startPolling() {
    // Инициализация — запоминаем текущие lastMessage.timestamp всех чатов
    // чтобы не обрабатывать старые сообщения как новые
    setTimeout(async () => {
        try {
            console.log('🔧 Инициализация lastSeenTimestamp...');
            const chats = await client.getChats();
            for (const chat of chats.filter(c => !c.isGroup)) {
                if (chat.lastMessage && chat.lastMessage.timestamp) {
                    lastSeenTimestamp.set(chat.id._serialized, chat.lastMessage.timestamp);
                }
            }
            console.log(`✅ Инициализировано ${lastSeenTimestamp.size} чатов`);
        } catch (e) {
            console.log(`⚠️ Ошибка инициализации: ${e.message}`);
        }
    }, 1000);
    
    // Агрессивный poll каждые 5 секунд
    setInterval(pollAllChats, 5000);
    console.log('🔄 Polling запущен (каждые 5 сек, проверяет ВСЕ чаты)');
    // Первый poll через 3 сек (после инициализации)
    setTimeout(pollAllChats, 3000);
}

// ─── Общая обработка входящего сообщения ───────────────────────

// Проверяет, похож ли номер на реальный телефон (10-13 цифр)
function isRealPhone(num) {
    return /^\d{10,13}$/.test(num);
}

async function handleIncomingMessage(msg) {
    const rawFrom = msg.from;

    // НЕ фильтруем по readyTimestamp — иначе после перезапуска ничего не придёт
    // Вместо этого полагаемся на processedMsgIds

    const isLid = rawFrom.endsWith('@lid');
    let phone = '';
    let resolveMethod = '';

    console.log(`\n🔍 handleIncomingMessage: from=${rawFrom}`);

    // 1. Пробуем получить реальный номер через контакт
    try {
        const contact = await msg.getContact();
        if (contact) {
            console.log(`  contact: number=${contact.number}, id.user=${contact.id ? contact.id.user : 'null'}`);
            // contact.number — самый надёжный источник
            if (contact.number) {
                const num = contact.number.replace(/\D/g, '');
                if (isRealPhone(num)) {
                    phone = num;
                    resolveMethod = 'contact.number';
                }
            }
            // contact.id.user для @c.us контактов
            if (!phone && contact.id && contact.id.user) {
                const user = contact.id.user;
                if (isRealPhone(user)) {
                    phone = user;
                    resolveMethod = 'contact.id.user';
                }
            }
        }
    } catch (e) {
        console.log(`  contact ошибка: ${e.message}`);
    }

    // 2. Для @c.us — номер прямо в from
    if (!phone && !isLid) {
        const stripped = rawFrom.replace(/@c\.us$/, '').replace(/@s\.whatsapp\.net$/, '');
        if (isRealPhone(stripped)) {
            phone = stripped;
            resolveMethod = 'from@c.us';
        }
    }

    // 3. Пробуем через chat.name — содержит номер типа "+7 705 446 2896"
    if (!phone) {
        try {
            const chat = await msg.getChat();
            if (chat && chat.name) {
                console.log(`  chat.name="${chat.name}"`);
                const digits = chat.name.replace(/\D/g, '');
                if (isRealPhone(digits)) {
                    phone = digits;
                    resolveMethod = 'chat.name';
                }
            }
        } catch (e) {
            console.log(`  chat ошибка: ${e.message}`);
        }
    }

    // 4. Пробуем getNumberId
    if (!phone && isLid) {
        try {
            const rawId = rawFrom.replace(/@.*$/, '');
            const numId = await client.getNumberId(rawId);
            if (numId && numId.user && isRealPhone(numId.user)) {
                phone = numId.user;
                resolveMethod = 'getNumberId';
            }
        } catch (e) {}
    }

    // 5. Пробуем chat.contact
    if (!phone) {
        try {
            const chat = await msg.getChat();
            if (chat && chat.contact && chat.contact.number) {
                const num = chat.contact.number.replace(/\D/g, '');
                if (isRealPhone(num)) {
                    phone = num;
                    resolveMethod = 'chat.contact.number';
                }
            }
        } catch (e) {}
    }

    // 6. Fallback — используем LID ID как ключ
    if (!phone) {
        try {
            const chat = await msg.getChat();
            const name = chat ? chat.name : '';
            console.log(`  ⚠️ Не удалось определить номер для ${rawFrom} (name="${name}")`);
            // Используем LID ID как временный ключ
            if (isLid) {
                phone = rawFrom.replace(/@lid$/, '');
                resolveMethod = 'lid-fallback';
                console.log(`  → Используем LID как ключ: ${phone}`);
            }
        } catch (e) {}
    }

    if (!phone) {
        console.log(`  ❌ Не удалось определить номер, пропуск\n`);
        return;
    }

    const formatted = resolveMethod === 'lid-fallback' ? `lid:${phone}` : '+' + phone;

    console.log(`✅ Resolved: ${formatted} (method: ${resolveMethod})`);
    console.log(`📩 Входящее от ${formatted}: ${(msg.body || '').substring(0, 80)}\n`);

    // Сохраняем chatId для ответа
    chatIdMap.set(formatted, rawFrom);

    if (!incomingMessages.has(formatted)) {
        incomingMessages.set(formatted, []);
    }
    incomingMessages.get(formatted).push({
        from: formatted,
        rawFrom: rawFrom,
        body: msg.body || '',
        timestamp: msg.timestamp,
        isRead: false
    });
}

// ─── Хелпер: "печатает..." перед отправкой ─────────────────────

async function sendWithTyping(chatId, message) {
    try {
        const chat = await client.getChatById(chatId);
        await chat.sendStateTyping();
        // Задержка 2-4 сек — имитация набора текста
        const delay = 2000 + Math.floor(Math.random() * 2000);
        await new Promise(r => setTimeout(r, delay));
        await chat.clearState();
    } catch (e) {
        // Если не удалось показать typing — не страшно, отправляем как есть
        console.log(`  ⌨️ typing не удался: ${e.message}`);
    }
    await client.sendMessage(chatId, message);
}

// ─── HTTP API ──────────────────────────────────────────────────

// Статус подключения
app.get('/status', (req, res) => {
    res.json({
        ready: isReady,
        qr: currentQR,
        qr_base64: currentQRBase64,
        phone: isReady && clientInfo ? clientInfo.wid.user : null,
        name: isReady && clientInfo ? clientInfo.pushname : null
    });
});

// Отправить сообщение
app.post('/send', async (req, res) => {
    const { phone, message } = req.body;

    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не подключён' });
    }
    if (!phone || !message) {
        return res.status(400).json({ error: 'Нужны phone и message' });
    }

    try {
        // Сначала проверяем — есть ли сохранённый chatId для этого номера
        // Это нужно для ответа на входящие (особенно @lid номера)
        const rawChatId = chatIdMap.get(phone);

        if (rawChatId) {
            // Отвечаем через оригинальный chatId (работает и для @lid и для @c.us)
            console.log(`📱 Отправляю через rawFrom: ${rawChatId}`);
            await sendWithTyping(rawChatId, message);
            console.log(`✅ Отправлено → ${phone}: ${message.substring(0, 40)}...`);
            return res.json({ success: true, phone, delivered: true });
        }

        // Форматируем номер: +77001234567 -> 77001234567
        const rawNum = phone.replace('+', '').replace(/\D/g, '');
        
        console.log(`📱 Проверяю номер: ${rawNum}`);

        // Пробуем getNumberId с разными форматами
        let numberId = await client.getNumberId(rawNum);
        
        if (!numberId && rawNum.startsWith('8')) {
            // 87001234567 -> 77001234567
            numberId = await client.getNumberId('7' + rawNum.substring(1));
            if (numberId) console.log(`  → Найден как 7${rawNum.substring(1)}`);
        }

        console.log(`  → getNumberId результат:`, numberId ? JSON.stringify(numberId) : 'null');

        if (!numberId) {
            // Последняя попытка — отправляем напрямую через @c.us
            const chatId = rawNum + '@c.us';
            console.log(`  → Пробую отправить напрямую на ${chatId}...`);
            try {
                await sendWithTyping(chatId, message);
                console.log(`✅ Отправлено напрямую → ${phone}`);
                return res.json({ success: true, phone, delivered: true });
            } catch (directErr) {
                console.log(`  → Прямая отправка не удалась: ${directErr.message}`);
                return res.json({
                    success: false,
                    error: 'not_registered',
                    message: `Номер ${phone} не в WhatsApp`
                });
            }
        }

        await sendWithTyping(numberId._serialized, message);
        console.log(`✅ Отправлено → ${phone}: ${message.substring(0, 40)}...`);
        res.json({ success: true, phone, delivered: true });
    } catch (err) {
        console.error(`❌ Ошибка ${phone}:`, err.message);
        res.json({ success: false, error: err.message });
    }
});

// Получить непрочитанные сообщения
app.get('/unread', (req, res) => {
    const unread = {};
    for (const [phone, messages] of incomingMessages) {
        const unreadMsgs = messages.filter(m => !m.isRead);
        if (unreadMsgs.length > 0) {
            unread[phone] = unreadMsgs;
        }
    }
    const count = Object.keys(unread).length;
    if (count > 0) {
        console.log(`📬 /unread → ${count} чатов с непрочитанными`);
    }
    res.json(unread);
});

// История чата
app.get('/chat/:phone', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не подключён' });
    }

    try {
        const phone = req.params.phone;
        const chatId = phone.replace('+', '').replace(/\D/g, '') + '@c.us';
        const chat = await client.getChatById(chatId);
        const messages = await chat.fetchMessages({ limit: 20 });

        const result = messages.map(m => ({
            from: m.fromMe ? 'me' : phone,
            body: m.body,
            timestamp: m.timestamp,
            fromMe: m.fromMe
        }));

        res.json(result);
    } catch (err) {
        res.json({ error: err.message });
    }
});

// Пометить прочитанным
app.post('/mark-read', (req, res) => {
    const { phone } = req.body;
    if (incomingMessages.has(phone)) {
        // Удаляем все прочитанные сообщения (а не просто помечаем)
        incomingMessages.delete(phone);
    }
    res.json({ success: true });
});

// Проверить номер
app.get('/check/:phone', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не подключён' });
    }
    try {
        const chatId = req.params.phone.replace('+', '').replace(/\D/g, '') + '@c.us';
        const isRegistered = await client.isRegisteredUser(chatId);
        res.json({ phone: req.params.phone, registered: isRegistered });
    } catch (err) {
        res.json({ error: err.message });
    }
});

// Диагностика — показать все чаты с непрочитанными
app.get('/debug/chats', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не подключён' });
    }
    try {
        const chats = await client.getChats();
        const result = [];
        for (const c of chats.slice(0, 20)) {
            const info = {
                name: c.name,
                id: c.id._serialized,
                isGroup: c.isGroup,
                unreadCount: c.unreadCount,
                lastMessage: c.lastMessage ? {
                    body: (c.lastMessage.body || '').substring(0, 50),
                    fromMe: c.lastMessage.fromMe,
                    from: c.lastMessage.from,
                    timestamp: c.lastMessage.timestamp,
                } : null,
            };
            // Для LID чатов — пробуем определить реальный номер
            if (c.id._serialized.endsWith('@lid')) {
                try {
                    const contact = await c.getContact();
                    info.contactNumber = contact ? contact.number : null;
                } catch (e) {
                    info.contactNumber = null;
                }
            }
            result.push(info);
        }
        res.json({
            totalChats: chats.length,
            incomingBuffer: incomingMessages.size,
            processedIds: processedMsgIds.size,
            readyTimestamp,
            chatIdMapSize: chatIdMap.size,
            chats: result,
        });
    } catch (err) {
        res.json({ error: err.message });
    }
});

// Перезагрузить WA-сессию (без удаления авторизации)
app.all('/restart', async (req, res) => {
    console.log('🔄 Перезагрузка WA-клиента...');
    isReady = false;
    readyTimestamp = 0;
    processedMsgIds.clear();
    incomingMessages.clear();
    lastSeenTimestamp.clear();
    chatIdMap.clear();
    res.json({ success: true, message: 'Перезагрузка...' });
    try {
        await client.destroy();
    } catch (e) {}
    setTimeout(() => {
        client.initialize();
    }, 2000);
});

// Полный сброс сессии — удаляет авторизацию, потребуется новый QR
app.post('/reset-session', async (req, res) => {
    console.log('🗑️ Полный сброс сессии...');
    isReady = false;
    readyTimestamp = 0;
    processedMsgIds.clear();
    incomingMessages.clear();
    lastSeenTimestamp.clear();
    chatIdMap.clear();
    res.json({ success: true, message: 'Сессия сброшена, ожидайте QR...' });
    try {
        await client.logout();
    } catch (e) {
        console.log('  logout ошибка:', e.message);
    }
    try {
        await client.destroy();
    } catch (e) {}
    // Удаляем данные сессии
    const fs = require('fs');
    const path = require('path');
    const authDir = path.join(__dirname, 'wa_auth_data');
    try {
        fs.rmSync(authDir, { recursive: true, force: true });
        console.log('  ✅ wa_auth_data удалена');
    } catch (e) {
        console.log('  ⚠️ Не удалось удалить wa_auth_data:', e.message);
    }
    setTimeout(() => {
        client.initialize();
    }, 3000);
});

// Graceful shutdown — корректно закрывает WA-клиент и сохраняет сессию
app.post('/shutdown', async (req, res) => {
    console.log('🛑 Получен запрос на завершение, сохраняю сессию...');
    res.json({ success: true });
    try {
        await client.destroy();
        console.log('✅ WA-клиент закрыт, сессия сохранена');
    } catch (err) {
        console.error('⚠️ Ошибка при закрытии:', err.message);
    }
    process.exit(0);
});

// Обработка сигналов завершения
process.on('SIGTERM', async () => {
    console.log('🛑 SIGTERM — закрываю WA-клиент...');
    try { await client.destroy(); } catch (e) {}
    process.exit(0);
});
process.on('SIGINT', async () => {
    console.log('🛑 SIGINT — закрываю WA-клиент...');
    try { await client.destroy(); } catch (e) {}
    process.exit(0);
});

// ─── Запуск ────────────────────────────────────────────────────

app.listen(PORT, () => {
    console.log(`\n🚀 WA-сервер запущен на http://localhost:${PORT}`);
    console.log('Инициализация WhatsApp...\n');
    client.initialize();
});
