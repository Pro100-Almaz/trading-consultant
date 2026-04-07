import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy import JSON

from app.infrastructure.database import Base


class Plan(str, enum.Enum):
    free = "free"
    pro = "pro"
    premium = "premium"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # bcrypt hash
    plan = Column(Enum(Plan), nullable=False, default=Plan.free)
    daily_usage = Column(Integer, nullable=False, default=0)
    last_usage_date = Column(Date, nullable=True)  # for lazy daily reset at 00:00 UTC
    created_at = Column(DateTime, default=datetime.utcnow)

    analyses = relationship("AnalysisHistory", back_populates="user")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False, default="")
    icon = Column(String(50), nullable=False, default="pie_chart")
    color = Column(String(7), nullable=False, default="#6366F1")
    symbols = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # nullable until auth is added
    ticker = Column(String, nullable=False, index=True)
    mode = Column(String, nullable=False)
    score = Column(Integer, nullable=True)
    trend = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    analysis = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="analyses")
