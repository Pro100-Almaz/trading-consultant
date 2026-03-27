import ta
import pandas as pd

from app.infrastructure.vector_store import rag_store

ANALYSIS_MODES: dict[str, dict] = {
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
    "portfolio_builder": {
        "categories": ["blackrock_portfolio"],
        "description": "Построение портфеля по методологии BlackRock",
    },
}


def calc_indicators(df: pd.DataFrame) -> dict:
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    macd_obj = ta.trend.MACD(close)
    bb = ta.volatility.BollingerBands(close)

    price = float(close.iloc[-1])
    price_1m_ago = float(close.iloc[-21]) if len(close) > 21 else price

    return {
        "price": price,
        "change_1m": ((price - price_1m_ago) / price_1m_ago) * 100,
        "rsi": float(ta.momentum.rsi(close, window=14).iloc[-1]),
        "sma20": float(ta.trend.sma_indicator(close, window=20).iloc[-1]),
        "sma50": float(ta.trend.sma_indicator(close, window=50).iloc[-1]),
        "ema12": float(ta.trend.ema_indicator(close, window=12).iloc[-1]),
        "macd": float(macd_obj.macd().iloc[-1]),
        "macd_signal": float(macd_obj.macd_signal().iloc[-1]),
        "bb_upper": float(bb.bollinger_hband().iloc[-1]),
        "bb_lower": float(bb.bollinger_lband().iloc[-1]),
        "atr": float(ta.volatility.average_true_range(high, low, close, window=14).iloc[-1]),
        "avg_vol": float(volume.rolling(20).mean().iloc[-1]),
    }


def calc_score(ind: dict) -> int:
    score = 50
    if ind["rsi"] < 30:
        score += 15
    elif ind["rsi"] < 45:
        score += 8
    elif ind["rsi"] > 70:
        score -= 15
    elif ind["rsi"] > 55:
        score -= 5
    if ind["sma20"] > ind["sma50"]:
        score += 10
    else:
        score -= 10
    if ind["macd"] > ind["macd_signal"]:
        score += 10
    else:
        score -= 10
    bb_range = ind["bb_upper"] - ind["bb_lower"]
    if bb_range > 0:
        bb_pos = (ind["price"] - ind["bb_lower"]) / bb_range
        if bb_pos < 0.2:
            score += 10
        elif bb_pos > 0.8:
            score -= 10
    return max(5, min(95, score))


def build_rag_prompt(ticker: str, indicators: dict, mode: str, user_context: str = "") -> str:
    config = ANALYSIS_MODES.get(mode, ANALYSIS_MODES["full"])
    chunks = rag_store.search_multi(
        query=f"анализ акции {ticker} {config['description']}",
        categories=config["categories"],
        n_per_cat=3,
    )
    context = "\n\n---\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)

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

    return f"""Ты — профессиональный финансовый аналитик. Ниже — твоя база знаний и методологии.
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
