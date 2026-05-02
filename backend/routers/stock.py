"""股價 / 即時 / 三大法人 API."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from services import data_router

router = APIRouter(tags=["stock"])

MARKET_GROUPS = [
    {
        "id": "major_indices",
        "title": "主要指數",
        "description": "掌握台股與美股大盤方向",
        "symbols": ["^TWII", "^GSPC", "^IXIC", "^DJI"],
    },
    {
        "id": "core_etfs",
        "title": "核心 ETF",
        "description": "長期配置常用的全市場與科技 ETF",
        "symbols": ["VT", "VOO", "QQQ", "IWM"],
    },
    {
        "id": "macro_assets",
        "title": "宏觀資產",
        "description": "利率、黃金與原油的風險情緒觀察",
        "symbols": ["TLT", "GLD", "UUP", "USO"],
    },
]


@router.get("/stock/{symbol}/daily")
def stock_daily(
    symbol: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict:
    today = date.today()
    if not end_date:
        end_date = today.strftime("%Y-%m-%d")
    if not start_date:
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")

    df = data_router.get_price(symbol.upper(), start_date, end_date)
    if df is None or df.empty:
        return {"symbol": symbol.upper(), "data": []}
    return {
        "symbol": symbol.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "data": df.to_dict(orient="records"),
    }


@router.get("/stock/{symbol}/realtime")
def stock_realtime(symbol: str) -> dict:
    quotes = data_router.get_realtime_all([symbol.upper()])
    if not quotes:
        raise HTTPException(status_code=404, detail=f"No realtime data for {symbol}")
    return quotes[0]


@router.get("/stock/{symbol}/institutional")
def stock_institutional(
    symbol: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict:
    if not data_router.is_taiwan_stock(symbol):
        return {"symbol": symbol.upper(), "available": False, "data": []}

    today = date.today()
    if not end_date:
        end_date = today.strftime("%Y-%m-%d")
    if not start_date:
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")

    df = data_router.get_institutional(symbol, start_date, end_date)
    return {
        "symbol": symbol.upper(),
        "available": True,
        "start_date": start_date,
        "end_date": end_date,
        "data": df.to_dict(orient="records") if df is not None and not df.empty else [],
    }


@router.get("/market/overview")
def market_overview() -> dict:
    symbols = [symbol for group in MARKET_GROUPS for symbol in group["symbols"]]
    quotes = data_router.get_realtime_all(symbols)
    by_symbol = {quote["symbol"].upper(): quote for quote in quotes}

    groups = []
    for group in MARKET_GROUPS:
        items = []
        for symbol in group["symbols"]:
            quote = by_symbol.get(symbol.upper(), {})
            items.append(
                {
                    "symbol": symbol,
                    "price": quote.get("price"),
                    "change": quote.get("change"),
                    "change_pct": quote.get("change_pct"),
                    "currency": quote.get("currency"),
                    "updated_at": quote.get("updated_at"),
                }
            )
        groups.append(
            {
                "id": group["id"],
                "title": group["title"],
                "description": group["description"],
                "items": items,
            }
        )

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "groups": groups,
    }
