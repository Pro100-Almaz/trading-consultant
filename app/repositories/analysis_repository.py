from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import AnalysisHistory
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def save(
        self,
        ticker: str,
        mode: str,
        analysis: str,
        score: int | None = None,
        trend: str | None = None,
        price: float | None = None,
        user_id: int | None = None,
    ) -> AnalysisHistory:
        record = AnalysisHistory(
            user_id=user_id,
            ticker=ticker,
            mode=mode,
            score=score,
            trend=trend,
            price=price,
            analysis=analysis,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_ticker(self, ticker: str, limit: int = 10) -> list[AnalysisHistory]:
        return (
            self.db.query(AnalysisHistory)
            .filter(AnalysisHistory.ticker == ticker)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent(self, limit: int = 20) -> list[AnalysisHistory]:
        return (
            self.db.query(AnalysisHistory)
            .order_by(AnalysisHistory.created_at.desc())
            .limit(limit)
            .all()
        )
