from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.models import Strategy
from app.repositories.base import BaseRepository


class StrategyRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(
        self,
        user_id: str,
        name: str,
        description: str = "",
        icon: str = "pie_chart",
        color: str = "#6366F1",
        symbols: list[str] | None = None,
    ) -> Strategy:
        if symbols:
            self._remove_symbols_from_others(user_id=user_id, exclude_id=None, symbols=symbols)
        strategy = Strategy(
            user_id=user_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            symbols=symbols or [],
        )
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)
        return strategy

    def get_by_user(self, user_id: str) -> list[Strategy]:
        return (
            self.db.query(Strategy)
            .filter(Strategy.user_id == user_id)
            .order_by(Strategy.created_at.asc())
            .all()
        )

    def get_by_id(self, strategy_id: str) -> Strategy | None:
        return self.db.query(Strategy).filter(Strategy.id == strategy_id).first()

    def update(self, strategy: Strategy, **kwargs) -> Strategy:
        symbols = kwargs.get("symbols")
        if symbols is not None:
            self._remove_symbols_from_others(
                user_id=strategy.user_id,
                exclude_id=strategy.id,
                symbols=symbols,
            )
        for field, value in kwargs.items():
            setattr(strategy, field, value)
        strategy.updated_at = datetime.utcnow()
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)
        return strategy

    def delete(self, strategy: Strategy) -> None:
        self.db.delete(strategy)
        self.db.commit()

    def assign_symbols_exclusive(
        self, user_id: str, target_id: str, symbols: list[str]
    ) -> None:
        self._remove_symbols_from_others(user_id=user_id, exclude_id=target_id, symbols=symbols)
        target = self.get_by_id(target_id)
        if target is None:
            return
        existing = list(target.symbols or [])
        for s in symbols:
            if s not in existing:
                existing.append(s)
        target.symbols = existing
        target.updated_at = datetime.utcnow()
        self.db.add(target)
        self.db.commit()

    def _remove_symbols_from_others(
        self, user_id: str, exclude_id: str | None, symbols: list[str]
    ) -> None:
        query = self.db.query(Strategy).filter(Strategy.user_id == user_id)
        if exclude_id:
            query = query.filter(Strategy.id != exclude_id)
        for strategy in query.all():
            current = list(strategy.symbols or [])
            new_symbols = [s for s in current if s not in symbols]
            if new_symbols != current:
                strategy.symbols = new_symbols
                strategy.updated_at = datetime.utcnow()
                self.db.add(strategy)
        self.db.commit()
