"""自選股管理：CRUD + 即時報價 join."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import data_router

router = APIRouter(tags=["watchlist"])

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "watchlist.json"

_VALID = re.compile(r"^[\^A-Z0-9.\-]{1,12}$")


class WatchAddBody(BaseModel):
    symbol: str
    note: str | None = ""


def _load() -> tuple[list[str], dict[str, str]]:
    if not DATA_FILE.exists():
        return [], {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            d = json.load(f)
            symbols = [s.upper() for s in d.get("symbols", [])]
            notes = {str(k).upper(): str(v) for k, v in d.get("notes", {}).items()}
            return symbols, notes
    except Exception:
        return [], {}


def _save(symbols: list[str], notes: dict[str, str]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump({"symbols": symbols, "notes": notes}, f, ensure_ascii=False, indent=2)


def _enrich(symbols: list[str], notes: dict[str, str]) -> dict:
    quotes = data_router.get_realtime_all(symbols) if symbols else []
    by_symbol = {q["symbol"].upper(): q for q in quotes}
    enriched = []
    for sym in symbols:
        q = by_symbol.get(sym.upper(), {})
        enriched.append(
            {
                "symbol": sym,
                "price": q.get("price"),
                "change": q.get("change"),
                "change_pct": q.get("change_pct"),
                "currency": q.get("currency"),
                "note": notes.get(sym.upper(), ""),
            }
        )
    return {"symbols": enriched}


@router.get("/watchlist")
def get_watchlist() -> dict:
    symbols, notes = _load()
    return _enrich(symbols, notes)


@router.post("/watchlist")
def add_watchlist(body: WatchAddBody) -> dict:
    symbol = body.symbol.strip().upper()
    if not _VALID.match(symbol):
        raise HTTPException(status_code=400, detail="symbol 格式不合法")
    symbols, notes = _load()
    if symbol in symbols:
        raise HTTPException(status_code=409, detail=f"{symbol} 已在自選股中")
    symbols.append(symbol)
    notes[symbol] = (body.note or "").strip()
    _save(symbols, notes)
    return _enrich(symbols, notes)


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str) -> dict:
    symbol = symbol.strip().upper()
    symbols, notes = _load()
    if symbol not in symbols:
        raise HTTPException(status_code=404, detail=f"{symbol} 不在自選股中")
    symbols = [s for s in symbols if s != symbol]
    notes.pop(symbol, None)
    _save(symbols, notes)
    return _enrich(symbols, notes)
