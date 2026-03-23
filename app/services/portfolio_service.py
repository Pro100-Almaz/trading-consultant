from app.domain.schemas import Position
from app.infrastructure.vector_store import rag_store
from app.services.analysis_service import ANALYSIS_MODES


def build_portfolio_rag_prompt(positions: list[Position], context: str = "") -> str:
    config = ANALYSIS_MODES["portfolio"]
    chunks = rag_store.search_multi(
        query="анализ портфеля пользователя диверсификация риски рекомендации",
        categories=config["categories"],
        n_per_cat=3,
    )
    rag_context = "\n\n---\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)

    total_value = sum(p.market_value for p in positions)
    total_pnl = sum(p.pnl for p in positions)

    positions_text = "\n".join(
        f"- {p.ticker}: {p.shares:.0f} акций, стоимость ${p.market_value:,.2f} "
        f"({p.market_value / total_value * 100:.1f}%), P&L ${p.pnl:+,.2f}"
        for p in positions
    )

    return f"""Ты — персональный инвестиционный советник уровня Private Banking.
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
