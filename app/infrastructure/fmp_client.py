from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import httpx
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://financialmodelingprep.com/stable"
_RETRY_DELAYS = [2, 5]


def get_ohlcv(ticker: str, days: int = 90) -> pd.DataFrame:
    """Fetch daily OHLCV from FMP historical endpoint.

    Returns a DataFrame with columns Open/High/Low/Close/Volume sorted by date
    ascending, compatible with calc_indicators(). Requires at least 50 rows.
    """
    to_date = date.today()
    from_date = to_date - timedelta(days=days)

    last_error: str | None = None
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            resp = httpx.get(
                f"{_BASE}/historical-price-eod/full",
                params={
                    "symbol": ticker,
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                    "apikey": settings.fmp_api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                last_error = "Нет данных от FMP"
            else:
                df = _records_to_df(data)
                if len(df) >= 50:
                    return df
                last_error = f"Недостаточно данных: {len(df)} строк"
        except Exception as e:
            last_error = str(e)
        if attempt < len(_RETRY_DELAYS):
            time.sleep(delay)

    raise ValueError(last_error or f"Не удалось загрузить данные для {ticker}")


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    df = df.rename(columns={
        "open":   "Open",
        "high":   "High",
        "low":    "Low",
        "close":  "Close",
        "volume": "Volume",
    })
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
