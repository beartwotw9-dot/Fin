"""FinMind 資料服務 — 台股 OHLCV / 三大法人 / 融資融券."""
from __future__ import annotations

import os
import time
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

try:
    from FinMind.data import DataLoader
except ImportError:  # pragma: no cover
    DataLoader = None  # type: ignore

load_dotenv()


class FinMindService:
    """封裝 FinMind API 並做 5 分鐘 TTL cache，統一輸出欄位."""

    _CACHE_TTL = 300  # 秒

    def __init__(self) -> None:
        self.token: Optional[str] = os.getenv("FINMIND_TOKEN") or None
        self._cache: dict[str, tuple[float, pd.DataFrame]] = {}
        self.api: Optional[DataLoader] = None
        if DataLoader is not None:
            try:
                self.api = DataLoader()
                if self.token:
                    self.api.login_by_token(api_token=self.token)
            except Exception as exc:  # pragma: no cover
                print(f"[FinMind] login failed, falling back to anonymous: {exc}")
                self.api = DataLoader()

    # ------------------------------------------------------------------
    # cache helpers
    # ------------------------------------------------------------------
    def _cache_get(self, key: str) -> Optional[pd.DataFrame]:
        record = self._cache.get(key)
        if record is None:
            return None
        ts, df = record
        if time.time() - ts > self._CACHE_TTL:
            self._cache.pop(key, None)
            return None
        return df.copy()

    def _cache_put(self, key: str, df: pd.DataFrame) -> None:
        self._cache[key] = (time.time(), df.copy())

    # ------------------------------------------------------------------
    # daily OHLCV
    # ------------------------------------------------------------------
    def get_daily(self, stock_id: str, start: str, end: str) -> pd.DataFrame:
        """回傳統一欄位的日 K：date, open, high, low, close, volume."""
        key = f"daily_{stock_id}_{start}_{end}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        if self.api is None:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        try:
            df = self.api.taiwan_stock_daily(
                stock_id=stock_id, start_date=start, end_date=end
            )
            if df is None or df.empty:
                return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

            # FinMind 台股欄位：date, stock_id, Trading_Volume, Trading_money,
            # open, max, min, close, spread, Trading_turnover
            df = df.rename(columns={"max": "high", "min": "low", "Trading_Volume": "volume"})
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            cols = ["date", "open", "high", "low", "close", "volume"]
            df = df[[c for c in cols if c in df.columns]].reset_index(drop=True)
            self._cache_put(key, df)
            return df
        except Exception as exc:
            print(f"[FinMind] get_daily error for {stock_id}: {exc}")
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    # ------------------------------------------------------------------
    # 三大法人
    # ------------------------------------------------------------------
    def get_institutional(self, stock_id: str, start: str, end: str) -> pd.DataFrame:
        """三大法人買賣超：date, name, buy, sell, diff."""
        key = f"inst_{stock_id}_{start}_{end}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        if self.api is None:
            return pd.DataFrame(columns=["date", "name", "buy", "sell", "diff"])

        try:
            df = self.api.taiwan_stock_institutional_investors(
                stock_id=stock_id, start_date=start, end_date=end
            )
            if df is None or df.empty:
                return pd.DataFrame(columns=["date", "name", "buy", "sell", "diff"])
            df["diff"] = df["buy"] - df["sell"]
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df = df[["date", "name", "buy", "sell", "diff"]].reset_index(drop=True)
            self._cache_put(key, df)
            return df
        except Exception as exc:
            print(f"[FinMind] get_institutional error for {stock_id}: {exc}")
            return pd.DataFrame(columns=["date", "name", "buy", "sell", "diff"])

    # ------------------------------------------------------------------
    # 融資融券
    # ------------------------------------------------------------------
    def get_margin(self, stock_id: str, start: str, end: str) -> pd.DataFrame:
        """融資融券餘額."""
        key = f"margin_{stock_id}_{start}_{end}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        if self.api is None:
            return pd.DataFrame()

        try:
            df = self.api.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_id, start_date=start, end_date=end
            )
            if df is None or df.empty:
                return pd.DataFrame()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df = df.reset_index(drop=True)
            self._cache_put(key, df)
            return df
        except Exception as exc:
            print(f"[FinMind] get_margin error for {stock_id}: {exc}")
            return pd.DataFrame()

    # ------------------------------------------------------------------
    # 即時最新一筆
    # ------------------------------------------------------------------
    def get_latest(self, stock_id: str) -> Optional[dict]:
        """最後一個交易日 K 棒，當作即時報價."""
        from datetime import date, timedelta

        end = date.today()
        start = end - timedelta(days=10)
        df = self.get_daily(stock_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df.empty:
            return None
        last = df.iloc[-1]
        prev_close = float(df.iloc[-2]["close"]) if len(df) >= 2 else float(last["close"])
        price = float(last["close"])
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        return {
            "symbol": stock_id,
            "price": round(price, 4),
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "currency": "TWD",
            "updated_at": last["date"],
        }
