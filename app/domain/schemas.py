from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.domain.models import Plan


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    plan: Plan
    daily_usage: int
    created_at: datetime

    model_config = {"from_attributes": True}


class Position(BaseModel):
    ticker: str
    shares: float
    market_value: float
    pnl: float


class PortfolioRequest(BaseModel):
    positions: list[Position]
    context: str = ""


class AnalysisResponse(BaseModel):
    ticker: str
    mode: str
    mode_description: str
    price: float
    change_1m: float
    rsi: float
    sma20: float
    sma50: float
    macd: float
    macd_signal: float
    bb_upper: float
    bb_lower: float
    atr: float
    trend: str
    score: int
    analysis: str


class PortfolioResponse(BaseModel):
    mode: str
    mode_description: str
    total_value: float
    total_pnl: float
    positions_count: int
    profitable_positions: int
    analysis: str


class AnalysisHistoryItem(BaseModel):
    id: int
    ticker: str
    mode: str
    score: int | None
    trend: str | None
    price: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
