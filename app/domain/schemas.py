from __future__ import annotations

import enum
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


class RiskStrategy(str, enum.Enum):
    conservative = "conservative"
    moderate     = "moderate"
    aggressive   = "aggressive"


class PortfolioBuilderRequest(BaseModel):
    amount: float
    risk_strategy: RiskStrategy


class ETFAllocation(BaseModel):
    ticker: str
    name: str
    asset_class: str
    percentage: float
    amount: float
    shares: float
    price: float


class PortfolioBuilderResponse(BaseModel):
    strategy: str
    total_amount: float
    expected_return_min: float
    expected_return_max: float
    max_drawdown: float
    rebalancing_frequency: str
    allocations: list[ETFAllocation]
    analysis: str


class StrategyCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "pie_chart"
    color: str = "#6366F1"
    symbols: list[str] = []


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    symbols: list[str] | None = None


class StrategyResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    icon: str
    color: str
    symbols: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisHistoryItem(BaseModel):
    id: int
    ticker: str
    mode: str
    score: int | None
    trend: str | None
    price: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
