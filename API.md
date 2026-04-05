# API Reference — AI Stock Analyzer

Base URL (dev): `https://6df8-31-171-168-220.ngrok-free.app`

> **Required header on every request (dev only):**
> `ngrok-skip-browser-warning: true`

---

## Authentication

JWT Bearer token. Include in every protected request:

```
Authorization: Bearer <token>
```

Token TTL: **24 hours**. After expiry, call `/auth/refresh` or re-login.

---

## Endpoints

### POST `/auth/register`

Register a new account. Plan defaults to `free`.

**Request**
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**Response `201`**
```json
{
  "token": "eyJhbG...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "plan": "free",
    "daily_usage": 0,
    "daily_limit": 3
  }
}
```

**Errors**

| Status | Body | Reason |
|--------|------|--------|
| 400 | `{"error": "emailTaken"}` | Email already registered |
| 400 | `{"error": "invalidEmail"}` | Bad email format |
| 400 | `{"error": "weakPassword"}` | Password shorter than 3 characters |

---

### POST `/auth/login`

**Request**
```json
{
  "email": "user@example.com",
  "password": "mypassword"
}
```

**Response `200`**
```json
{
  "token": "eyJhbG...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "plan": "pro",
    "daily_usage": 5,
    "daily_limit": 30
  }
}
```

**Errors**

| Status | Body | Reason |
|--------|------|--------|
| 400 | `{"error": "accountNotFound"}` | Email not registered |
| 400 | `{"error": "wrongPassword"}` | Incorrect password |

---

### GET `/auth/refresh` 🔒

Returns a new token. Call this before expiry to keep the session alive.

**Response `200`**
```json
{
  "token": "eyJhbG_new..."
}
```

---

### GET `/user/profile` 🔒

Returns current user info. Use after app launch to restore session state.

**Response `200`**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "plan": "pro",
  "daily_usage": 12,
  "daily_limit": 30
}
```

> `daily_limit: -1` means **unlimited** (Premium plan).

---

### GET `/analyze/{ticker}` 🔒

Main analysis endpoint.

**Path param:** `ticker` — stock symbol, 1–10 uppercase letters (`AAPL`, `TSLA`, `GOOGL`)

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `full` | Analysis mode (see table below) |
| `context` | string | `""` | Optional extra context passed to AI |

**Available modes:**

| `mode` | Description | Plans |
|--------|-------------|-------|
| `full` | Full report — all methodologies | pro, premium |
| `technical` | Technical analysis (Citadel) | free, pro, premium |
| `screener` | Stock screening (Goldman Sachs) | pro, premium |
| `risk` | Risk assessment (Bridgewater) | pro, premium |
| `dcf` | DCF valuation (Morgan Stanley) | pro, premium |
| `earnings` | Earnings analysis (JPMorgan) | pro, premium |
| `portfolio` | Portfolio analysis (BlackRock + Bridgewater + Goldman) | pro, premium |
| `dividends` | Dividend analysis (Harvard) | pro, premium |
| `competitors` | Competitive analysis (Bain) | pro, premium |

**Response `200`**
```json
{
  "ticker": "AAPL",
  "mode": "technical",
  "mode_description": "Только технический анализ (Citadel)",
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
  "analysis": "## Technical Overview\n\n..."
}
```

**Field reference:**

| Field | Type | Description |
|-------|------|-------------|
| `price` | float | Current price in USD |
| `change_1m` | float | 1-month price change, % (e.g. `5.3` or `-2.1`) |
| `rsi` | float | RSI(14), range 0–100 |
| `sma20` / `sma50` | float | Simple moving averages |
| `macd` / `macd_signal` | float | MACD line and signal line |
| `bb_upper` / `bb_lower` | float | Bollinger Bands |
| `atr` | float | Average True Range |
| `trend` | string | `"Bullish"` or `"Bearish"` |
| `score` | int | Investment score 0–100 |
| `analysis` | string | **Markdown** AI report, split on `##` sections |

**Score → Signal mapping (do this on frontend):**

| Score | Signal |
|-------|--------|
| ≥ 65 | BUY |
| 45–64 | HOLD |
| < 45 | SELL |

**Errors:**

| Status | Body | Reason |
|--------|------|--------|
| 400 | `{"error": "invalidTicker"}` | Ticker format invalid |
| 400 | `{"error": "invalidMode"}` | Unknown mode value |
| 401 | `{"error": "invalidToken"}` | Missing or expired token |
| 403 | `{"error": "planUpgradeRequired"}` | Mode not available on current plan |
| 404 | `{"error": "tickerNotFound", "message": "..."}` | Ticker not found on Yahoo Finance |
| 429 | `{"error": "dailyLimitReached"}` | Daily request limit exhausted |

---

### POST `/analyze/portfolio-builder` 🔒

Builds an optimal stock portfolio from scratch. Claude selects **individual stocks only** (no ETFs) using BlackRock methodology and provides approximate prices from its own knowledge. The backend calculates `amount` and `shares` locally — no external price API is called. Requires `pro` or `premium` plan.

**Request**
```json
{
  "amount": 10000,
  "risk_strategy": "moderate"
}
```

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `amount` | float | `> 0` | Total investment amount in USD |
| `risk_strategy` | string | `conservative` \| `moderate` \| `aggressive` | Portfolio risk profile |

**Response `200`**
```json
{
  "strategy": "moderate",
  "total_amount": 10000.00,
  "expected_return_min": 8,
  "expected_return_max": 12,
  "max_drawdown": 25,
  "rebalancing_frequency": "quarterly",
  "allocations": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "asset_class": "Tech",
      "percentage": 10.0,
      "amount": 1000.00,
      "shares": 5.2743,
      "price": 189.60
    },
    {
      "ticker": "JNJ",
      "name": "Johnson & Johnson",
      "asset_class": "Healthcare",
      "percentage": 8.0,
      "amount": 800.00,
      "shares": 5.0314,
      "price": 158.99
    },
    {
      "ticker": "TSM",
      "name": "Taiwan Semiconductor Mfg.",
      "asset_class": "International",
      "percentage": 7.0,
      "amount": 700.00,
      "shares": 5.7377,
      "price": 122.00
    }
  ],
  "analysis": "## Обзор портфеля\n\n..."
}
```

**Response field reference:**

| Field | Type | Description |
|-------|------|-------------|
| `strategy` | string | Risk strategy used |
| `total_amount` | float | Total invested amount in USD |
| `expected_return_min` / `expected_return_max` | float | Expected annual return range, % |
| `max_drawdown` | float | Max historical drawdown for this strategy, % |
| `rebalancing_frequency` | string | `quarterly` or `semi-annual` |
| `allocations` | array | List of positions (see below) |
| `allocations[].ticker` | string | Stock ticker (common stocks only — no ETFs) |
| `allocations[].name` | string | Full company name |
| `allocations[].asset_class` | string | Sector (Tech, Healthcare, Financials, Consumer, Energy, International, Materials…) |
| `allocations[].percentage` | float | Allocation weight, % |
| `allocations[].amount` | float | Dollar amount (`percentage × total_amount / 100`) |
| `allocations[].shares` | float | Number of shares to buy (`amount / price`) |
| `allocations[].price` | float | Approximate price from Claude's knowledge (±5% accuracy) |
| `analysis` | string | **Markdown** AI report with position rationale, risk coverage, rebalancing guide, bull/base/bear scenarios |

**Strategy profiles (from BlackRock methodology):**

| Strategy | Expected return | Max drawdown | Rebalancing |
|----------|----------------|--------------|-------------|
| `conservative` | 5–8% | 15% | semi-annual |
| `moderate` | 8–12% | 25% | quarterly |
| `aggressive` | 12–18% | 40% | quarterly |

**Errors:**

| Status | Body | Reason |
|--------|------|--------|
| 400 | `{"error": "invalidAmount"}` | `amount` is zero or negative |
| 401 | `{"error": "invalidToken"}` | Missing or expired token |
| 403 | `{"error": "planUpgradeRequired"}` | Free plan cannot access this endpoint |
| 429 | `{"error": "dailyLimitReached"}` | Daily request limit exhausted |
| 500 | `{"error": "parseError", "message": "..."}` | Claude response could not be parsed |
| 503 | `{"error": "aiUnavailable", "message": "..."}` | Anthropic API error |

---

### POST `/analyze/portfolio` 🔒

Portfolio analysis. Requires `pro` or `premium` plan.

**Request**
```json
{
  "positions": [
    { "ticker": "AAPL", "shares": 10, "market_value": 1950.00, "pnl": 200.00 },
    { "ticker": "NVDA", "shares": 5,  "market_value": 3500.00, "pnl": -150.00 }
  ],
  "context": "Горизонт инвестирования 2 года"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Stock symbol |
| `shares` | float | Number of shares held |
| `market_value` | float | Current market value in USD |
| `pnl` | float | Profit/loss in USD (negative = loss) |
| `context` | string | Optional extra context for the AI |

**Response `200`**
```json
{
  "mode": "portfolio",
  "mode_description": "Анализ портфеля пользователя (BlackRock + Bridgewater + Goldman)",
  "total_value": 5450.00,
  "total_pnl": 50.00,
  "positions_count": 2,
  "profitable_positions": 1,
  "analysis": "## Executive Summary\n\n..."
}
```

---

### GET `/analyze/{ticker}/history` 🔒

Returns past analyses for a ticker (most recent first).

**Query param:** `limit` — default `10`

**Response `200`**
```json
[
  {
    "id": 1,
    "ticker": "AAPL",
    "mode": "technical",
    "score": 72,
    "trend": "Bullish",
    "price": 189.50,
    "created_at": "2026-03-24T10:00:00"
  }
]
```

---

### GET `/modes`

Returns all available modes (no auth required).

**Response `200`**
```json
{
  "full": "Полный инвестиционный отчёт (все 8 методологий)",
  "technical": "Только технический анализ (Citadel)",
  "screener": "Скрининг акции (Goldman Sachs)",
  ...
}
```

---

### GET `/health`

Server health check (no auth required).

**Response `200`**
```json
{
  "status": "ok",
  "knowledge_chunks": 87
}
```

---

## Plans

| Plan | Daily limit | Accessible modes |
|------|-------------|-----------------|
| `free` | 3 | `technical` only |
| `pro` | 30 | all 10 modes |
| `premium` | unlimited | all 10 modes |

Daily counter resets at **00:00 UTC**.

---

## Test Accounts

| Email | Password | Plan |
|-------|----------|------|
| `free@test.com` | `123` | free |
| `pro@test.com` | `123` | pro |
| `premium@test.com` | `123` | premium |

---

## Quick Start (curl)

```bash
# 1. Login
TOKEN=$(curl -s -X POST <BASE_URL>/auth/login \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{"email":"pro@test.com","password":"123"}' | jq -r '.token')

# 2. Analyze
curl "<BASE_URL>/analyze/AAPL?mode=technical" \
  -H "Authorization: Bearer $TOKEN" \
  -H "ngrok-skip-browser-warning: true"
```
