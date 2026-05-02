"""統一資料路由：依 symbol 判斷台股 / 美股，呼叫對應服務."""
from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from .finmind_service import FinMindService
from .yfinance_service import YFinanceService


_TW_PATTERN = re.compile(r"^\d{4,6}$")


def is_taiwan_stock(symbol: str) -> bool:
    """純 4~6 碼數字視為台股代號."""
    if not symbol:
        return False
    s = symbol.strip().upper()
    if s.startswith("^"):
        return False
    return bool(_TW_PATTERN.match(s))


@lru_cache(maxsize=1)
def _finmind() -> FinMindService:
    return FinMindService()


@lru_cache(maxsize=1)
def _yf() -> YFinanceService:
    return YFinanceService()


def get_price(symbol: str, start: str, end: str) -> pd.DataFrame:
    """統一介面：取得日 K OHLCV."""
    if is_taiwan_stock(symbol):
        return _finmind().get_daily(symbol, start, end)
    return _yf().get_daily(symbol, start, end)


def get_realtime_all(symbols: list[str]) -> list[dict]:
    """混合台股 + 美股一次取得即時報價."""
    out: list[dict] = []
    yf_tickers: list[str] = []
    for sym in symbols:
        if is_taiwan_stock(sym):
            quote = _finmind().get_latest(sym)
            if quote is not None:
                out.append(quote)
        else:
            yf_tickers.append(sym)
    if yf_tickers:
        out.extend(_yf().get_realtime(yf_tickers))
    return out


def get_institutional(symbol: str, start: str, end: str) -> pd.DataFrame:
    if not is_taiwan_stock(symbol):
        return pd.DataFrame()
    return _finmind().get_institutional(symbol, start, end)
