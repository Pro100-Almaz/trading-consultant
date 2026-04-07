from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_investlink_user_id
from app.domain.schemas import StrategyCreate, StrategyResponse, StrategyUpdate
from app.repositories.strategy_repository import StrategyRepository

router = APIRouter()


@router.post("", response_model=StrategyResponse, status_code=201)
def create_strategy(
    body: StrategyCreate,
    user_id: str = Depends(get_investlink_user_id),
    db: Session = Depends(get_db),
):
    if len(body.name) > 100:
        raise HTTPException(status_code=400, detail={"error": "nameTooLong"})
    repo = StrategyRepository(db)
    strategy = repo.create(
        user_id=user_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        color=body.color,
        symbols=body.symbols,
    )
    return strategy


@router.get("", response_model=list[StrategyResponse])
def list_strategies(
    user_id: str = Depends(get_investlink_user_id),
    db: Session = Depends(get_db),
):
    return StrategyRepository(db).get_by_user(user_id)


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: str,
    body: StrategyUpdate,
    user_id: str = Depends(get_investlink_user_id),
    db: Session = Depends(get_db),
):
    repo = StrategyRepository(db)
    strategy = repo.get_by_id(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail={"error": "notFound"})
    if strategy.user_id != user_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})

    updates = body.model_dump(exclude_unset=True)
    return repo.update(strategy, **updates)


@router.delete("/{strategy_id}", status_code=204)
def delete_strategy(
    strategy_id: str,
    user_id: str = Depends(get_investlink_user_id),
    db: Session = Depends(get_db),
):
    repo = StrategyRepository(db)
    strategy = repo.get_by_id(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail={"error": "notFound"})
    if strategy.user_id != user_id:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})
    repo.delete(strategy)
    return Response(status_code=204)
