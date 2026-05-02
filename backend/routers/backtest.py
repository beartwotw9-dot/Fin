"""回測 API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services import backtest_engine

router = APIRouter(tags=["backtest"])


class BacktestBody(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    strategy: str
    params: dict[str, Any] = Field(default_factory=dict)
    commission: float = 0.001425
    slippage: float = 0.001


@router.get("/backtest/strategies")
def list_strategies() -> list[dict]:
    return backtest_engine.list_strategies()


@router.post("/backtest")
def run_backtest(body: BacktestBody) -> dict:
    result = backtest_engine.run_backtest(
        symbol=body.symbol.strip().upper(),
        start_date=body.start_date,
        end_date=body.end_date,
        strategy=body.strategy,
        params=body.params,
        commission=body.commission,
        slippage=body.slippage,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result
