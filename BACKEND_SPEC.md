# Backend Specification — AI Stock Analyzer

> ТЗ для бэкенд-разработчика. Фронтенд: Flutter Web.

---

## 1. Общая архитектура

| Параметр | Значение |
|----------|----------|
| Протокол | REST API, JSON |
| Авторизация | JWT (Bearer token) |
| Текущий Base URL (dev) | `https://6df8-31-171-168-220.ngrok-free.app` |
| Таймауты фронта | connect 30s, receive 60s |
| Обязательный header (dev) | `ngrok-skip-browser-warning: true` |
| CORS | Разрешить `*` (dev), потом только домен фронта |

---

## 2. Модель пользователя

```
User {
  id:          string (UUID)
  email:       string (unique, lowercase)
  password:    string (bcrypt hash)
  plan:        enum("free", "pro", "premium")  // default: "free"
  daily_usage: int                              // сброс в 00:00 UTC
  created_at:  datetime
}
```

### Тарифные планы

| План | `plan` value | Лимит/день | Доступные режимы | Цена |
|------|-------------|------------|------------------|------|
| Free | `free` | 3 | только `technical` | $0 |
| Pro | `pro` | 30 | все 9 | $9/мес |
| Premium | `premium` | безлимит (-1) | все 9 | $29/мес |

### Доступные режимы по плану

```
free    → ["technical"]
pro     → ["full","technical","screener","risk","dcf","earnings","portfolio","dividends","competitors"]
premium → ["full","technical","screener","risk","dcf","earnings","portfolio","dividends","competitors"]
```

---

## 3. Эндпоинты

### 3.1 Авторизация

> Сейчас на фронте мок. Нужна реальная реализация.

---

#### `POST /auth/register`

Регистрация нового пользователя. Plan = `free` по умолчанию.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**Response 201:**
```json
{
  "token": "eyJhbG...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "plan": "free",
    "daily_usage": 0,
    "daily_limit": 3
  }
}
```

**Ошибки:**

| HTTP | Body | Когда | Фронт покажет |
|------|------|-------|---------------|
| 400 | `{"error": "emailTaken"}` | Email уже зарегистрирован | "Email already registered" |
| 400 | `{"error": "invalidEmail"}` | Невалидный email | generic error |
| 400 | `{"error": "weakPassword"}` | Пароль < 3 символов | generic error |

---

#### `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**Response 200:**
```json
{
  "token": "eyJhbG...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "plan": "pro",
    "daily_usage": 5,
    "daily_limit": 30
  }
}
```

**Ошибки:**

| HTTP | Body | Когда | Фронт покажет |
|------|------|-------|---------------|
| 400 | `{"error": "accountNotFound"}` | Email не найден | "Account not found" |
| 400 | `{"error": "wrongPassword"}` | Неверный пароль | "Wrong password" |

---

#### `POST /auth/refresh` (опционально)

Обновление JWT токена.

**Request:**
```
Authorization: Bearer <expired_token>
```

**Response 200:**
```json
{
  "token": "eyJhbG_new..."
}
```

---

### 3.2 Профиль пользователя

#### `GET /user/profile`

Получить текущего юзера (план, использование).

**Request:**
```
Authorization: Bearer <token>
```

**Response 200:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "plan": "pro",
  "daily_usage": 12,
  "daily_limit": 30
}
```

> Фронт использует `plan` чтобы определить доступные режимы и показать лимиты.

---

### 3.3 Анализ акций

#### `GET /analyze/{ticker}?mode={mode}`

**Основной эндпоинт.** Уже работает на текущем бэке, нужно расширить.

**Request:**
```
GET /analyze/AAPL?mode=technical
Authorization: Bearer <token>
```

**Headers:**
- `Authorization: Bearer <token>` — обязательный (для учёта лимитов)
- `ngrok-skip-browser-warning: true` — dev only

**Path params:**
- `ticker` — тикер акции (AAPL, TSLA, GOOGL и т.д.), uppercase

**Query params:**
- `mode` — один из 9 режимов (см. таблицу ниже)

**Режимы анализа:**

| `mode` | Название | Методология | Описание |
|--------|----------|-------------|----------|
| `full` | Full Report | Все методологии | Комплексный анализ по всем 9 методологиям |
| `technical` | Technical Analysis | Citadel | RSI, MACD, Bollinger Bands, скользящие средние |
| `screener` | Screening | Goldman Sachs | Фундаментальный скрининг — мультипликаторы, рентабельность |
| `risk` | Risk Assessment | Bridgewater | Рыночные, секторальные, специфические риски |
| `dcf` | DCF Valuation | Morgan Stanley | Оценка справедливой стоимости, прогноз 5 лет |
| `earnings` | Earnings | JPMorgan | Анализ перед отчётностью — ожидания, сюрпризы |
| `portfolio` | Portfolio | BlackRock | Построение портфеля — диверсификация, корреляции |
| `dividends` | Dividends | Harvard | Дивидендная доходность, история, прогноз |
| `competitors` | Competitors | Bain | Конкурентный анализ — доля рынка, маржинальность |

---

**Response 200:**

```json
{
  "ticker": "AAPL",
  "mode": "technical",
  "mode_description": "Технический анализ",
  "price": 189.50,
  "change_1m": 5.3,
  "rsi": 45.2,
  "sma20": 185.30,
  "sma50": 180.10,
  "macd": 0.0052,
  "macd_signal": 0.0031,
  "bb_upper": 195.40,
  "bb_lower": 175.20,
  "atr": 3.45,
  "trend": "Bullish",
  "score": 72,
  "analysis": "## Technical Overview\n\nMarkdown formatted analysis...\n\n## Key Levels\n\n- Support: $180\n- Resistance: $195\n\n## Recommendation\n\nBased on..."
}
```

**Описание полей ответа:**

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `ticker` | string | Тикер акции | `"AAPL"` |
| `mode` | string | Использованный режим | `"technical"` |
| `mode_description` | string | Описание режима (RU) | `"Технический анализ"` |
| `price` | float | Текущая цена в USD | `189.50` |
| `change_1m` | float | Изменение за месяц, % | `5.3` или `-2.1` |
| `rsi` | float | Relative Strength Index (0–100) | `45.2` |
| `sma20` | float | 20-дневная SMA | `185.30` |
| `sma50` | float | 50-дневная SMA | `180.10` |
| `macd` | float | MACD значение | `0.0052` |
| `macd_signal` | float | MACD signal line | `0.0031` |
| `bb_upper` | float | Bollinger Bands верх | `195.40` |
| `bb_lower` | float | Bollinger Bands низ | `175.20` |
| `atr` | float | Average True Range | `3.45` |
| `trend` | string | Тренд | `"Bullish"` или `"Bearish"` |
| `score` | int | Инвестиционный скор 0–100 | `72` |
| `analysis` | string | **Markdown** текст AI-анализа | см. ниже |

---

**Формат поля `analysis` (ВАЖНО):**

Поле `analysis` — это **Markdown-текст** с секциями. Фронт парсит его по заголовкам `##` / `###` и разбивает на карточки.

Пример структуры:
```markdown
## Technical Overview

The stock shows bullish momentum with RSI at 45.2...

## Key Indicators

- **RSI (45.2):** Neutral zone, approaching oversold territory
- **MACD:** Positive crossover indicates potential upward movement
- **Bollinger Bands:** Price near middle band, $175–$195 range

## Support & Resistance

| Level | Price |
|-------|-------|
| Support 1 | $180.00 |
| Support 2 | $175.20 |
| Resistance 1 | $195.40 |

## Risk Assessment

Moderate risk profile. Key concerns:
1. Sector rotation risk
2. Earnings volatility

## Recommendation

**Score: 72/100 — BUY**

Based on technical analysis, the stock demonstrates...
```

**Требования к `analysis`:**
- Использовать `##` для основных секций (фронт делит по ним на карточки)
- Можно `###` для подсекций внутри
- Поддерживается: bold, italic, списки (- и 1.), таблицы, code blocks
- Длина: 500–3000 слов в зависимости от режима
- Режим `full` — самый длинный (все методологии)
- Режим `technical` — средний (индикаторы + рекомендация)

---

**Ошибки `/analyze`:**

| HTTP | Когда | Фронт покажет |
|------|-------|---------------|
| 400 | Невалидный тикер | "Server error (400)" |
| 401 | Невалидный/просроченный токен | "Server error (401)" |
| 403 | Режим недоступен на плане юзера | "Server error (403)" |
| 404 | Тикер не найден | "Server error (404)" |
| 429 | Дневной лимит исчерпан | "Server error (429)" |
| 500 | Внутренняя ошибка | "Server error (500)" |

---

### 3.4 SWOT анализ (расширение — v2)

Сейчас SWOT данные захардкожены на фронте. В будущем нужно добавить в ответ `/analyze`:

```json
{
  "...все текущие поля...",
  "swot": {
    "strengths": ["Stable revenue growth", "Strong brand", "Large cash reserves"],
    "weaknesses": ["High P/E ratio", "Market dependency"],
    "opportunities": ["AI segment expansion", "New markets"],
    "threats": ["Intense competition", "Regulatory risks"]
  }
}
```

> Пока не блокер — фронт покажет заглушку. Но желательно добавить сразу.

---

## 4. Бизнес-логика на бэкенде

### 4.1 Проверка лимитов (на каждый `/analyze` запрос)

```
1. Проверить JWT токен → получить user_id
2. Загрузить user из БД
3. Если user.plan == "free" && mode != "technical" → 403
4. Если user.plan != "premium":
   a. Проверить daily_usage >= daily_limit → 429
   b. Инкрементировать daily_usage += 1
5. Выполнить анализ
6. Вернуть результат
```

### 4.2 Сброс дневных лимитов

**Cron-задача: каждый день в 00:00 UTC**
```sql
UPDATE users SET daily_usage = 0;
```

Или ленивый сброс — хранить `last_usage_date`, при запросе проверять:
```
if user.last_usage_date < today:
    user.daily_usage = 0
    user.last_usage_date = today
```

### 4.3 Score → Signal маппинг

Фронт сам определяет сигнал по score:
- `>= 65` → BUY / ПОКУПКА
- `45–64` → HOLD / ЖДАТЬ
- `< 45` → SELL / ПРОДАЖА

Бэкенду не нужно возвращать signal — только `score` (int, 0–100).

---

## 5. Тестовые аккаунты

Для тестирования создать в БД (или seed):

| Email | Пароль | План |
|-------|--------|------|
| `free@test.com` | `123` | free |
| `pro@test.com` | `123` | pro |
| `premium@test.com` | `123` | premium |

---

## 6. Технические требования

### CORS
```
Access-Control-Allow-Origin: *          (dev)
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, ngrok-skip-browser-warning
```

### JWT
- Алгоритм: HS256 или RS256
- Payload: `{ "user_id": "uuid", "email": "...", "plan": "pro", "exp": ... }`
- TTL: 24 часа (или 7 дней + refresh)

### Валидация
- Email: стандартный формат, привести к lowercase
- Password: минимум 3 символа (для dev), потом можно усилить
- Ticker: 1–10 символов, uppercase, латиница
- Mode: один из 9 значений (см. таблицу)

---

## 7. Данные для анализа

### Откуда брать рыночные данные
- **Цена, change_1m:** Yahoo Finance API / Alpha Vantage / Finnhub
- **RSI, SMA, MACD, Bollinger, ATR:** Рассчитывать из исторических цен или использовать TA-Lib
- **Trend:** Определять по SMA20 vs SMA50 + направление цены
- **Score:** Алгоритм на основе совокупности индикаторов (можно AI)
- **Analysis (markdown):** OpenAI / Claude API — генерировать на основе данных

### Примерный алгоритм score

```python
score = 50  # базовый

# RSI
if rsi < 30: score += 10      # перепродано
elif rsi > 70: score -= 10    # перекуплено

# SMA тренд
if price > sma20 > sma50: score += 10   # бычий
elif price < sma20 < sma50: score -= 10  # медвежий

# MACD
if macd > macd_signal: score += 5
else: score -= 5

# Bollinger
if price < bb_lower: score += 5   # вблизи нижней, потенциал роста
elif price > bb_upper: score -= 5  # вблизи верхней, перекуплено

score = clamp(score, 0, 100)
```

---

## 8. Приоритеты реализации

### MVP (фаза 1)
1. `POST /auth/register` + `POST /auth/login` — реальная авторизация с JWT
2. `GET /analyze/{ticker}?mode=...` — с авторизацией, лимитами, проверкой плана
3. Тестовые аккаунты (free/pro/premium)
4. Дневной сброс лимитов

### Фаза 2
5. `GET /user/profile` — для восстановления сессии
6. SWOT в ответе `/analyze`
7. Refresh token
8. История анализов в БД (сейчас in-memory на фронте)

### Фаза 3
9. Stripe интеграция (оплата Pro/Premium)
10. Вебхук от Stripe → обновление `user.plan`
11. Email верификация
12. Password reset

---

## 9. Примеры запросов (curl)

### Регистрация
```bash
curl -X POST https://api.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@mail.com", "password": "123456"}'
```

### Логин
```bash
curl -X POST https://api.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "pro@test.com", "password": "123"}'
```

### Анализ
```bash
curl https://api.example.com/analyze/AAPL?mode=technical \
  -H "Authorization: Bearer eyJhbG..." \
  -H "ngrok-skip-browser-warning: true"
```

---

## 10. Что НЕ нужно делать бэкенду

- **Не определять signal (BUY/HOLD/SELL)** — фронт делает сам по score
- **Не переводить строки** — фронт имеет i18n (RU/EN), бэкенд отдаёт `mode_description` на русском
- **Не управлять темой/языком** — это чисто фронтовая логика
- **Не хранить историю пока** — фронт хранит in-memory (фаза 2)
- **Не блокировать покупку тарифов** — фронт показывает "Coming soon" для апгрейда
