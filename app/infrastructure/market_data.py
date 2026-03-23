import yfinance as yf
import pandas as pd


def fetch_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """Downloads OHLCV data from Yahoo Finance with up to 3 retries."""
    last_error: str | None = None
    for _ in range(3):
        try:
            df = yf.download(ticker, period=period, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty and len(df) >= 50:
                return df
            last_error = "Недостаточно данных"
        except Exception as e:
            last_error = str(e)
    raise ValueError(last_error or "Не удалось загрузить данные")
