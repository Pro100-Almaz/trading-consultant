import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import yfinance as yf
import ta
import anthropic
import pandas as pd
from vector_store import store

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

# --- Маршрутизатор запросов ---
# Определяет какие методологии нужны для запроса

ANALYSIS_MODES = {
    "full": {
        "categories": ["master", "technical", "screener", "risk", "dcf", "earnings", "dividends", "competitors"],
        "description": "Полный инвестиционный отчёт (все 8 методологий)",
    },
    "technical": {
        "categories": ["technical"],
        "description": "Только технический анализ (Citadel)",
    },
    "screener": {
        "categories": ["screener"],
        "description": "Скрининг акции (Goldman Sachs)",
    },
    "risk": {
        "categories": ["risk"],
        "description": "Оценка рисков (Bridgewater)",
    },
    "dcf": {
        "categories": ["dcf"],
        "description": "DCF оценка (Morgan Stanley)",
    },
    "earnings": {
        "categories": ["earnings"],
        "description": "Анализ перед отчётностью (JPMorgan)",
    },
    "portfolio": {
        "categories": ["portfolio", "user_portfolio", "risk"],
        "description": "Анализ портфеля пользователя (BlackRock + Bridgewater + Goldman)",
    },
    "dividends": {
        "categories": ["dividends"],
        "description": "Дивидендный анализ (Гарвард)",
    },
    "competitors": {
        "categories": ["competitors"],
        "description": "Конкурентный анализ (Bain)",
    },
}


class Position(BaseModel):
    ticker: str
    shares: float
    market_value: float
    pnl: float


class PortfolioRequest(BaseModel):
    positions: list[Position]
    context: str = ""


def build_portfolio_rag_prompt(positions: list[Position], context: str = "") -> str:
    """Собирает промпт для анализа портфеля пользователя."""
    config = ANALYSIS_MODES["portfolio"]
    categories = config["categories"]

    query = f"анализ портфеля пользователя диверсификация риски рекомендации"
    knowledge_chunks = store.search_multi(query, categories=categories, n_per_cat=3)

    context_parts = []
    for chunk in knowledge_chunks:
        context_parts.append(f"[{chunk['source']}]\n{chunk['text']}")
    rag_context = "\n\n---\n\n".join(context_parts)

    total_value = sum(p.market_value for p in positions)
    total_pnl = sum(p.pnl for p in positions)

    positions_text = "\n".join(
        f"- {p.ticker}: {p.shares:.0f} акций, стоимость ${p.market_value:,.2f} "
        f"({p.market_value / total_value * 100:.1f}%), P&L ${p.pnl:+,.2f}"
        for p in positions
    )

    prompt = f"""Ты — персональный инвестиционный советник уровня Private Banking.
Ниже — твоя методология анализа портфеля. СТРОГО следуй ей.

=== МЕТОДОЛОГИЯ ===
{rag_context}
=== КОНЕЦ МЕТОДОЛОГИИ ===

=== ПОРТФЕЛЬ ПОЛЬЗОВАТЕЛЯ ===
Позиций: {len(positions)}
Общая стоимость: ${total_value:,.2f}
Суммарный P&L: ${total_pnl:+,.2f}

{positions_text}
=== КОНЕЦ ПОРТФЕЛЯ ===

{f"Дополнительный контекст: {context}" if context else ""}

Задача: {config['description']}.

Правила:
1. Строго следуй методологии из базы знаний
2. Используй конкретные числа из данных портфеля
3. Давай конкретные рекомендации с тикерами и суммами
4. Отвечай на русском языке
5. Формат — структурированный markdown-отчёт по пунктам методологии
"""
    return prompt


def build_rag_prompt(ticker: str, indicators: dict, mode: str, user_context: str = "") -> str:
    """Собирает промпт с контекстом из RAG базы."""

    config = ANALYSIS_MODES.get(mode, ANALYSIS_MODES["full"])
    categories = config["categories"]

    # Ищем релевантные знания
    query = f"анализ акции {ticker} {config['description']}"
    knowledge_chunks = store.search_multi(query, categories=categories, n_per_cat=3)

    # Собираем контекст из найденных чанков
    context_parts = []
    for chunk in knowledge_chunks:
        context_parts.append(f"[{chunk['source']}]\n{chunk['text']}")
    context = "\n\n---\n\n".join(context_parts)

    # Данные индикаторов
    indicators_text = f"""
Тикер: {ticker}
Цена: ${indicators['price']:.2f}
Изменение за месяц: {indicators['change_1m']:+.1f}%
RSI(14): {indicators['rsi']:.1f}
SMA 20: ${indicators['sma20']:.2f}
SMA 50: ${indicators['sma50']:.2f}
EMA 12: ${indicators['ema12']:.2f}
MACD: {indicators['macd']:.4f}
MACD Signal: {indicators['macd_signal']:.4f}
Bollinger Upper: ${indicators['bb_upper']:.2f}
Bollinger Lower: ${indicators['bb_lower']:.2f}
ATR(14): {indicators['atr']:.2f}
Объём (среднее 20д): {indicators['avg_vol']:.0f}
"""

    prompt = f"""Ты — профессиональный финансовый аналитик. Ниже — твоя база знаний и методологии. 
СТРОГО используй ТОЛЬКО эти методологии для анализа. Не отклоняйся от контекста.

=== БАЗА ЗНАНИЙ (методологии анализа) ===
{context}
=== КОНЕЦ БАЗЫ ЗНАНИЙ ===

=== РЫНОЧНЫЕ ДАННЫЕ ===
{indicators_text}
=== КОНЕЦ ДАННЫХ ===

{f"Дополнительный контекст от пользователя: {user_context}" if user_context else ""}

Задача: проведи {config['description']} для {ticker}.

Правила:
1. Отвечай ТОЛЬКО на основе методологий из базы знаний выше
2. Используй конкретные числа из рыночных данных
3. Если данных недостаточно для какого-то пункта методологии — явно укажи это
4. Отвечай на русском языке
5. Формат — структурированный отчёт по пунктам методологии
6. Максимум 500 слов
"""
    return prompt


def calc_indicators(df: pd.DataFrame) -> dict:
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    rsi = ta.momentum.rsi(close, window=14).iloc[-1]
    sma20 = ta.trend.sma_indicator(close, window=20).iloc[-1]
    sma50 = ta.trend.sma_indicator(close, window=50).iloc[-1]
    ema12 = ta.trend.ema_indicator(close, window=12).iloc[-1]

    macd_obj = ta.trend.MACD(close)
    macd = macd_obj.macd().iloc[-1]
    macd_signal = macd_obj.macd_signal().iloc[-1]

    bb = ta.volatility.BollingerBands(close)
    bb_upper = bb.bollinger_hband().iloc[-1]
    bb_lower = bb.bollinger_lband().iloc[-1]

    atr = ta.volatility.average_true_range(high, low, close, window=14).iloc[-1]
    avg_vol = volume.rolling(20).mean().iloc[-1]

    price = float(close.iloc[-1])
    price_1m_ago = float(close.iloc[-21]) if len(close) > 21 else price
    change_1m = ((price - price_1m_ago) / price_1m_ago) * 100

    return {
        "price": price, "change_1m": change_1m,
        "rsi": float(rsi), "sma20": float(sma20), "sma50": float(sma50),
        "ema12": float(ema12), "macd": float(macd), "macd_signal": float(macd_signal),
        "bb_upper": float(bb_upper), "bb_lower": float(bb_lower),
        "atr": float(atr), "avg_vol": float(avg_vol),
    }


def calc_score(ind: dict) -> int:
    score = 50
    if ind["rsi"] < 30: score += 15
    elif ind["rsi"] < 45: score += 8
    elif ind["rsi"] > 70: score -= 15
    elif ind["rsi"] > 55: score -= 5
    if ind["sma20"] > ind["sma50"]: score += 10
    else: score -= 10
    if ind["macd"] > ind["macd_signal"]: score += 10
    else: score -= 10
    bb_range = ind["bb_upper"] - ind["bb_lower"]
    if bb_range > 0:
        bb_pos = (ind["price"] - ind["bb_lower"]) / bb_range
        if bb_pos < 0.2: score += 10
        elif bb_pos > 0.8: score -= 10
    return max(5, min(95, score))


# --- Загрузка RAG при старте ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load_knowledge()
    print(f"[RAG] База знаний загружена: {store.collection.count()} чанков")
    yield

app = FastAPI(title="Stock Analysis RAG API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/analyze/{ticker}")
async def analyze(ticker: str, mode: str = "full", context: str = ""):
    """
    Анализ акции с RAG контекстом.
    mode: full, technical, screener, risk, dcf, earnings, portfolio, dividends, competitors
    context: дополнительная информация от пользователя
    """
    ticker = ticker.upper().strip()

    if ticker == "PORTFOLIO":
        raise HTTPException(status_code=400, detail="Для анализа портфеля используйте POST /analyze/portfolio")

    if mode not in ANALYSIS_MODES:
        raise HTTPException(status_code=400, detail=f"Неизвестный mode. Доступные: {list(ANALYSIS_MODES.keys())}")

    # 1. Данные
    df = None
    last_error = None
    for attempt in range(3):
        try:
            df = yf.download(ticker, period="3mo", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty and len(df) >= 50:
                break
            last_error = "Недостаточно данных"
            df = None
        except Exception as e:
            last_error = str(e)
    if df is None:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки {ticker}: {last_error}")

    # 2. Индикаторы + скоринг
    ind = calc_indicators(df)
    score = calc_score(ind)
    trend = "Бычий" if ind["sma20"] > ind["sma50"] else "Медвежий"

    # 3. RAG + Claude
    try:
        prompt = build_rag_prompt(ticker, ind, mode, context)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = response.content[0].text
    except Exception as e:
        analysis = f"AI анализ временно недоступен: {str(e)}"

    # 4. JSON
    return {
        "ticker": ticker,
        "mode": mode,
        "mode_description": ANALYSIS_MODES[mode]["description"],
        "price": round(ind["price"], 2),
        "change_1m": round(ind["change_1m"], 1),
        "rsi": round(ind["rsi"], 1),
        "sma20": round(ind["sma20"], 2),
        "sma50": round(ind["sma50"], 2),
        "macd": round(ind["macd"], 4),
        "macd_signal": round(ind["macd_signal"], 4),
        "bb_upper": round(ind["bb_upper"], 2),
        "bb_lower": round(ind["bb_lower"], 2),
        "atr": round(ind["atr"], 2),
        "trend": trend,
        "score": score,
        "analysis": analysis,
    }


@app.post("/analyze/portfolio")
async def analyze_portfolio(req: PortfolioRequest):
    """
    Анализ портфеля пользователя.
    Принимает список позиций с тикером, количеством акций, стоимостью и P&L.
    """
    if not req.positions:
        raise HTTPException(status_code=400, detail="Список позиций пуст")

    total_value = sum(p.market_value for p in req.positions)
    total_pnl = sum(p.pnl for p in req.positions)
    profitable = sum(1 for p in req.positions if p.pnl > 0)

    try:
        prompt = build_portfolio_rag_prompt(req.positions, req.context)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = response.content[0].text
    except Exception as e:
        analysis = f"AI анализ временно недоступен: {str(e)}"

    return {
        "mode": "portfolio",
        "mode_description": ANALYSIS_MODES["portfolio"]["description"],
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "positions_count": len(req.positions),
        "profitable_positions": profitable,
        "analysis": analysis,
    }


@app.get("/modes")
async def get_modes():
    """Список доступных режимов анализа."""
    return {k: v["description"] for k, v in ANALYSIS_MODES.items()}


@app.get("/health")
async def health():
    return {"status": "ok", "knowledge_chunks": store.collection.count()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)