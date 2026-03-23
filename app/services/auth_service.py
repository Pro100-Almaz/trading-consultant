from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.domain.models import Plan, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PLAN_LIMITS: dict[Plan, dict] = {
    Plan.free:    {"daily_limit": 3,  "modes": {"technical"}},
    Plan.pro:     {"daily_limit": 30, "modes": {
        "full", "technical", "screener", "risk", "dcf",
        "earnings", "portfolio", "dividends", "competitors",
    }},
    Plan.premium: {"daily_limit": -1, "modes": {
        "full", "technical", "screener", "risk", "dcf",
        "earnings", "portfolio", "dividends", "competitors",
    }},
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "plan": user.plan.value,
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])


def daily_limit_for(plan: Plan) -> int:
    return PLAN_LIMITS[plan]["daily_limit"]


def user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "plan": user.plan.value,
        "daily_usage": user.daily_usage,
        "daily_limit": daily_limit_for(user.plan),
    }
