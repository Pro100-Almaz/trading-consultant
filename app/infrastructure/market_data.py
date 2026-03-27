import pandas as pd

from app.infrastructure.fmp_client import get_ohlcv

_PERIOD_DAYS: dict[str, int] = {
    "1mo": 35,
    "3mo": 90,
    "6mo": 185,
    "1y":  370,
}


def fetch_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch historical OHLCV via FMP. Raises ValueError if data is unavailable."""
    days = _PERIOD_DAYS.get(period, 90)
    return get_ohlcv(ticker, days=days)
