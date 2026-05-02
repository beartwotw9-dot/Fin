"""投資組合分析 / 回測 API."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.portfolio_service import HoldingInput, analyze_portfolio, backtest_portfolio

router = APIRouter(tags=["portfolio"])


class PortfolioHoldingBody(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    shares: float = Field(..., gt=0)
    avg_cost: float | None = Field(default=None, ge=0)


class PortfolioAnalyzeBody(BaseModel):
    cash: float = Field(default=0, ge=0)
    holdings: list[PortfolioHoldingBody]


class PortfolioBacktestBody(PortfolioAnalyzeBody):
    start_date: str = Field(..., min_length=10, max_length=10)
    end_date: str = Field(..., min_length=10, max_length=10)
    benchmark: str | None = Field(default=None, min_length=1, max_length=16)


@router.post("/portfolio/analyze")
def portfolio_analyze(body: PortfolioAnalyzeBody) -> dict:
    holdings = [
        HoldingInput(symbol=item.symbol, shares=item.shares, avg_cost=item.avg_cost)
        for item in body.holdings
    ]
    return analyze_portfolio(holdings=holdings, cash=body.cash)


@router.post("/portfolio/backtest")
def portfolio_backtest(body: PortfolioBacktestBody) -> dict:
    holdings = [
        HoldingInput(symbol=item.symbol, shares=item.shares, avg_cost=item.avg_cost)
        for item in body.holdings
    ]
    return backtest_portfolio(
        holdings=holdings,
        cash=body.cash,
        start_date=body.start_date,
        end_date=body.end_date,
        benchmark=body.benchmark,
    )
