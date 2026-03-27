import json
import logging
import re

from app.domain.schemas import ETFAllocation
from app.infrastructure.vector_store import rag_store

logger = logging.getLogger(__name__)

STRATEGY_METRICS: dict[str, dict] = {
    "conservative": {"return_min": 5,  "return_max": 8,  "max_drawdown": 15, "rebalancing": "semi-annual"},
    "moderate":     {"return_min": 8,  "return_max": 12, "max_drawdown": 25, "rebalancing": "quarterly"},
    "aggressive":   {"return_min": 12, "return_max": 18, "max_drawdown": 40, "rebalancing": "quarterly"},
}


def _position_count_rule(amount: float) -> str:
    if amount < 5_000:
        return "5-8 акций"
    if amount > 50_000:
        return "15-20 акций"
    return "10-15 акций"


def _strategy_composition(strategy: str) -> str:
    compositions = {
        "conservative": (
            "60-70% дивидендные/защитные (JNJ, PG, KO, PEP, WMT, MCD), "
            "20-30% голубые фишки (AAPL, MSFT, BRK-B), "
            "10% золотодобытчики (NEM, GOLD)"
        ),
        "moderate": (
            "40-50% growth blue-chips (AAPL, MSFT, GOOGL, AMZN), "
            "20-30% value/дивидендные (JNJ, PG, JPM), "
            "10-20% international ADR (TSM, ASML, NVO), "
            "5-10% defensive (WMT, KO)"
        ),
        "aggressive": (
            "50-60% tech growth (NVDA, META, AVGO, AMD), "
            "20-30% blue-chips (AAPL, MSFT, AMZN), "
            "10-20% momentum/mid-cap (CRWD, PANW, MELI)"
        ),
    }
    return compositions.get(strategy, "диверсифицированный портфель акций")


def build_builder_prompt(amount: float, strategy: str, rag_context: str) -> str:
    count_rule = _position_count_rule(amount)
    composition = _strategy_composition(strategy)
    metrics = STRATEGY_METRICS[strategy]

    return f"""Ты — старший портфельный управляющий BlackRock с 25-летним опытом. Используй методологию из базы знаний ниже.

=== БАЗА ЗНАНИЙ (методология BlackRock) ===
{rag_context}
=== КОНЕЦ БАЗЫ ЗНАНИЙ ===

=== ЗАДАЧА ===
Стратегия инвестора: {strategy}
Сумма инвестиций: ${amount:,.2f}

КРИТИЧНЫЕ ПРАВИЛА (нарушение недопустимо):
1. ⛔ ЗАПРЕЩЕНО использовать ETF (VOO, QQQ, BND, VTI, VXUS, SPY, GLD, VNQ и любые другие ETF)
2. ✅ ТОЛЬКО обычные акции компаний (common stocks)
3. Вместо ETF выбирай топ-акции соответствующего индекса:
   • Вместо VOO/SPY/VTI → AAPL, MSFT, GOOGL, AMZN, NVDA, JPM, BRK-B, UNH, V
   • Вместо QQQ → NVDA, META, AVGO, AMD, ADBE, CRM, NFLX
   • Вместо BND/AGG → JNJ, PG, KO, PEP, MCD, WMT, CL, MMM (дивидендные защитные)
   • Вместо VXUS/EFA → TSM, ASML, NVO, SAP, TM, SONY, MELI (international ADR)
   • Вместо GLD → NEM, GOLD, AEM, FNV, WPM (золотодобытчики)
   • Вместо VNQ → AMT, PLD, EQIX, SPG, O (REIT-акции)
   • Вместо XLF → JPM, GS, MS, BAC, BLK
   • Вместо XLV → UNH, JNJ, LLY, PFE, ABT, TMO

Обязательные правила:
4. Количество позиций: {count_rule}
5. Состав для стратегии {strategy}: {composition}
6. Международные активы: минимум 10% через international ADR (TSM, ASML, NVO, SAP, MELI)
7. Максимум 10% на одну акцию; максимум 30% на один сектор
8. Минимум 4 разных сектора (Tech, Healthcare, Financials, Consumer, Energy, International)
9. Сумма всех percentage должна быть ровно 100
10. Для каждой акции указать примерную текущую цену из своих знаний (точность ±5% достаточна)

КРИТИЧНО: верни ТОЛЬКО чистый JSON без markdown, без ```json блоков, без пояснений до или после.

Формат ответа:
{{
  "strategy": "{strategy}",
  "expected_return_min": {metrics['return_min']},
  "expected_return_max": {metrics['return_max']},
  "max_drawdown": {metrics['max_drawdown']},
  "rebalancing_frequency": "{metrics['rebalancing']}",
  "allocations": [
    {{"ticker": "AAPL", "name": "Apple Inc.", "asset_class": "Tech", "percentage": 12.0, "price": 189.50}},
    {{"ticker": "JNJ", "name": "Johnson & Johnson", "asset_class": "Healthcare", "percentage": 8.0, "price": 156.30}}
  ],
  "analysis": "## Обзор портфеля\\n\\n...полный анализ на русском языке: обоснование каждой позиции, защита от рисков (инфляция, рецессия, геополитика), рекомендации по ребалансировке, сценарный анализ (bull/base/bear), секторальная разбивка..."
}}
"""


def parse_claude_response(response_text: str) -> dict:
    """Extract and parse the JSON object from Claude's response.

    Strips markdown code fences if Claude added them despite instructions.
    """
    text = re.sub(r"```json\s*", "", response_text)
    text = re.sub(r"```\s*", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("JSON объект не найден в ответе Claude")
    return json.loads(match.group(0))


def build_allocations(raw_allocs: list[dict], amount: float) -> list[ETFAllocation]:
    """Build ETFAllocation list using prices provided by Claude — no external API needed."""
    allocations: list[ETFAllocation] = []
    for entry in raw_allocs:
        ticker = str(entry["ticker"]).upper().replace(".", "-")
        percentage = float(entry["percentage"])
        price = float(entry.get("price") or 0)
        if price <= 0:
            logger.warning("Цена для %s отсутствует или равна 0, пропускаем", ticker)
            continue
        dollar_amount = percentage * amount / 100
        shares = dollar_amount / price
        allocations.append(ETFAllocation(
            ticker=ticker,
            name=str(entry.get("name", ticker)),
            asset_class=str(entry.get("asset_class", "Unknown")),
            percentage=round(percentage, 2),
            amount=round(dollar_amount, 2),
            shares=round(shares, 4),
            price=round(price, 2),
        ))
    return allocations


def get_rag_context() -> str:
    chunks = rag_store.search_multi(
        query="портфель акции распределение активов стратегия BlackRock дивидендные blue-chips",
        categories=["blackrock_portfolio"],
        n_per_cat=6,
    )
    return "\n\n---\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
