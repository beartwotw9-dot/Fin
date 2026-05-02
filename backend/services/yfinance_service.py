"""yfinance 資料服務 — 美股 / ETF / 指數."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import quote
from typing import Iterable

import httpx
import pandas as pd
import yfinance as yf


def _normalize_ticker(ticker: str) -> str:
    """台股代號（純數字 4~6 位）自動補 .TW."""
    t = ticker.strip().upper()
    if t.startswith("^"):
        return t  # 指數
    if t.isdigit() and 4 <= len(t) <= 6:
        return f"{t}.TW"
    return t


class YFinanceService:
    """yfinance 包裝，輸出與 FinMindService 相同欄位."""

    _quote_client = httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=10.0,
        follow_redirects=True,
    )

    # ------------------------------------------------------------------
    # 日 K
    # ------------------------------------------------------------------
    def get_daily(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """回傳：date, open, high, low, close, volume."""
        tk = _normalize_ticker(ticker)
        try:
            df = self._standardize_daily_frame(
                yf.download(
                    tickers=tk,
                    start=start,
                    end=end,
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
            )
            if df is not None and not df.empty:
                return df

            # fallback: 部分 ticker 在 download(start/end) 失敗時，history(period=max) 仍可取得資料
            history = yf.Ticker(tk).history(period="10y", auto_adjust=False)
            df = self._standardize_daily_frame(history)
            if df is not None and not df.empty:
                filtered = df[(df["date"] >= start) & (df["date"] <= end)].reset_index(drop=True)
                if not filtered.empty:
                    return filtered
                return df.reset_index(drop=True)

            chart_df = self._fetch_chart_daily(tk, start, end)
            if chart_df is not None and not chart_df.empty:
                return chart_df.reset_index(drop=True)

            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        except Exception as exc:
            print(f"[yfinance] get_daily error for {tk}: {exc}")
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    def _standardize_daily_frame(self, df: pd.DataFrame | None) -> pd.DataFrame | None:
        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

        out = df.reset_index()
        out = out.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        if "date" not in out.columns:
            return None
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        cols = ["date", "open", "high", "low", "close", "volume"]
        out = out[[c for c in cols if c in out.columns]].dropna().reset_index(drop=True)
        return out

    def _fetch_chart_daily(self, ticker: str, start: str, end: str) -> pd.DataFrame | None:
        """Yahoo chart endpoint fallback for daily candles."""
        period1 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
        # include end day
        period2 = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()) + 86400
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}"
            f"?period1={period1}&period2={period2}&interval=1d&includePrePost=false&events=div%2Csplits"
        )
        try:
            response = self._quote_client.get(url)
            response.raise_for_status()
            payload = response.json()
            result = ((payload or {}).get("chart") or {}).get("result") or []
            if not result:
                return None

            node = result[0]
            timestamps = node.get("timestamp") or []
            indicators = node.get("indicators") or {}
            quotes = (indicators.get("quote") or [{}])[0]
            opens = quotes.get("open") or []
            highs = quotes.get("high") or []
            lows = quotes.get("low") or []
            closes = quotes.get("close") or []
            volumes = quotes.get("volume") or []

            rows = []
            for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
                if None in (o, h, l, c):
                    continue
                rows.append(
                    {
                        "date": datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d"),
                        "open": float(o),
                        "high": float(h),
                        "low": float(l),
                        "close": float(c),
                        "volume": float(v or 0),
                    }
                )
            if not rows:
                return None
            return pd.DataFrame(rows)
        except Exception as exc:
            print(f"[yfinance] chart fallback error for {ticker}: {exc}")
            return None

    # ------------------------------------------------------------------
    # 即時報價
    # ------------------------------------------------------------------
    def get_realtime(self, tickers: Iterable[str]) -> list[dict]:
        out: list[dict] = []
        for raw in tickers:
            tk = _normalize_ticker(raw)
            try:
                t = yf.Ticker(tk)
                info = t.fast_info if hasattr(t, "fast_info") else {}
                price = float(info.get("last_price") or info.get("lastPrice") or 0)
                prev_close = float(
                    info.get("previous_close")
                    or info.get("previousClose")
                    or 0
                )
                if not price or not prev_close:
                    hist = t.history(period="5d", auto_adjust=False)
                    if hist is None or hist.empty:
                        continue
                    price = float(hist["Close"].iloc[-1])
                    prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0.0
                currency = (
                    info.get("currency")
                    or ("TWD" if tk.endswith(".TW") else "USD")
                )
                out.append(
                    {
                        "symbol": raw.upper(),
                        "price": round(price, 4),
                        "change": round(change, 4),
                        "change_pct": round(change_pct, 4),
                        "currency": currency,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            except Exception as exc:
                print(f"[yfinance] get_realtime error for {tk}: {exc}")
                fallback = self._scrape_quote_page(raw)
                if fallback is not None:
                    out.append(fallback)
        return out

    def _scrape_quote_page(self, ticker: str) -> dict | None:
        """Yahoo quote page fallback.

        When unofficial Yahoo APIs are rate-limited or blocked, the public quote
        page still exposes delayed price/change values in HTML spans.
        """
        normalized = ticker.strip().upper()
        url = f"https://finance.yahoo.com/quote/{quote(normalized)}"

        try:
            response = self._quote_client.get(url)
            response.raise_for_status()
            html = response.text

            price_match = re.search(r'data-testid="qsp-price"[^>]*>(.*?)</span>', html)
            change_match = re.search(r'data-testid="qsp-price-change"[^>]*>(.*?)</span>', html)
            pct_match = re.search(r'data-testid="qsp-price-change-percent"[^>]*>(.*?)</span>', html)

            if not price_match:
                return None

            price = _parse_number(price_match.group(1))
            change = _parse_number(change_match.group(1)) if change_match else 0.0
            change_pct = _parse_number(pct_match.group(1)) if pct_match else 0.0

            if price is None:
                return None

            currency = "TWD" if normalized == "^TWII" or normalized.endswith(".TW") else "USD"
            return {
                "symbol": normalized,
                "price": round(price, 4),
                "change": round(change or 0.0, 4),
                "change_pct": round(change_pct or 0.0, 4),
                "currency": currency,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as exc:
            print(f"[yfinance] scrape fallback error for {normalized}: {exc}")
            return None


def _parse_number(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = (
        value.replace(",", "")
        .replace("%", "")
        .replace("(", "")
        .replace(")", "")
        .replace("+", "")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None
