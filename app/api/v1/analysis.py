import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.domain.models import Plan, User
from app.domain.schemas import AnalysisHistoryItem, AnalysisResponse, PortfolioRequest, PortfolioResponse
from app.infrastructure.claude_client import complete
from app.infrastructure.market_data import fetch_ohlcv
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import ANALYSIS_MODES, build_rag_prompt, calc_indicators, calc_score
from app.services.auth_service import PLAN_LIMITS
from app.services.portfolio_service import build_portfolio_rag_prompt

router = APIRouter()

_TICKER_RE = re.compile(r"^[A-Z]{1,10}$")


def _apply_limits(user: User, mode: str, db: Session) -> None:
    """Lazy daily reset + plan/limit enforcement. Mutates user and commits."""
    today = date.today()
    if user.last_usage_date != today:
        user.daily_usage = 0
        user.last_usage_date = today

    plan_cfg = PLAN_LIMITS[user.plan]

    if mode not in plan_cfg["modes"]:
        raise HTTPException(status_code=403, detail={"error": "planUpgradeRequired"})

    if user.plan != Plan.premium and user.daily_usage >= plan_cfg["daily_limit"]:
        raise HTTPException(status_code=429, detail={"error": "dailyLimitReached"})

    user.daily_usage += 1
    UserRepository(db).save(user)


@router.post("/portfolio", response_model=PortfolioResponse)
async def analyze_portfolio(
    req: PortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.positions:
        raise HTTPException(status_code=400, detail="Список позиций пуст")

    _apply_limits(current_user, "portfolio", db)

    total_value = sum(p.market_value for p in req.positions)
    total_pnl = sum(p.pnl for p in req.positions)
    profitable = sum(1 for p in req.positions if p.pnl > 0)

    try:
        prompt = build_portfolio_rag_prompt(req.positions, req.context)
        analysis = complete(prompt)
    except Exception as e:
        analysis = f"AI анализ временно недоступен: {str(e)}"

    AnalysisRepository(db).save(
        ticker="PORTFOLIO",
        mode="portfolio",
        analysis=analysis,
        user_id=current_user.id,
    )

    return PortfolioResponse(
        mode="portfolio",
        mode_description=ANALYSIS_MODES["portfolio"]["description"],
        total_value=round(total_value, 2),
        total_pnl=round(total_pnl, 2),
        positions_count=len(req.positions),
        profitable_positions=profitable,
        analysis=analysis,
    )


@router.get("/{ticker}", response_model=AnalysisResponse)
async def analyze(
    ticker: str,
    mode: str = "full",
    context: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper().strip()

    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail={"error": "invalidTicker"})
    if mode not in ANALYSIS_MODES:
        raise HTTPException(status_code=400, detail={"error": "invalidMode"})

    _apply_limits(current_user, mode, db)

    try:
        df = fetch_ohlcv(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"error": "tickerNotFound", "message": str(e)})

    ind = calc_indicators(df)
    score = calc_score(ind)
    trend = "Bullish" if ind["sma20"] > ind["sma50"] else "Bearish"

    try:
        prompt = build_rag_prompt(ticker, ind, mode, context)
        analysis = complete(prompt)
    except Exception as e:
        analysis = f"AI анализ временно недоступен: {str(e)}"

    AnalysisRepository(db).save(
        ticker=ticker,
        mode=mode,
        analysis=analysis,
        score=score,
        trend=trend,
        price=ind["price"],
        user_id=current_user.id,
    )

    return AnalysisResponse(
        ticker=ticker,
        mode=mode,
        mode_description=ANALYSIS_MODES[mode]["description"],
        price=round(ind["price"], 2),
        change_1m=round(ind["change_1m"], 1),
        rsi=round(ind["rsi"], 1),
        sma20=round(ind["sma20"], 2),
        sma50=round(ind["sma50"], 2),
        macd=round(ind["macd"], 4),
        macd_signal=round(ind["macd_signal"], 4),
        bb_upper=round(ind["bb_upper"], 2),
        bb_lower=round(ind["bb_lower"], 2),
        atr=round(ind["atr"], 2),
        trend=trend,
        score=score,
        analysis=analysis,
    )


@router.get("/{ticker}/history", response_model=list[AnalysisHistoryItem])
async def get_history(
    ticker: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper().strip()
    return AnalysisRepository(db).get_by_ticker(ticker, limit=limit)
