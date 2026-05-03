"""投資組合分析、回測與可執行建議服務."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from . import data_router


CORE_ETFS = {"VT", "VTI", "VOO", "IVV", "SPY", "QQQ", "0050", "006208"}
BOND_ETFS = {"BND", "AGG", "TLT", "IEF", "LQD"}
GOLD_ETFS = {"GLD", "IAU"}
BENCHMARK_BY_REGION = {"taiwan": "0050", "us": "VT"}

TARGETS = {
    "core": 60.0,
    "satellite": 25.0,
    "defensive": 10.0,
    "cash": 5.0,
}


@dataclass
class HoldingInput:
    symbol: str
    shares: float
    avg_cost: float | None = None


def analyze_portfolio(holdings: list[HoldingInput], cash: float = 0.0) -> dict[str, Any]:
    cleaned = [item for item in holdings if item.symbol.strip() and item.shares > 0]
    if not cleaned:
        return {
            "holdings": [],
            "summary": {
                "total_market_value": 0.0,
                "cash": cash,
                "portfolio_value": cash,
                "unrealized_pnl": 0.0,
                "cash_weight": 100.0 if cash > 0 else 0.0,
            },
            "allocation": {},
            "risk_flags": [],
            "suggestions": [],
            "action_plan": [],
            "budget_plans": [],
            "recommended_products": [],
        }

    rows, allocation, summary = _build_portfolio_snapshot(cleaned, cash)
    risk_flags = _build_risk_flags(rows, allocation, summary["cash_weight"])
    suggestions = _build_suggestions(rows, allocation, summary["cash_weight"])
    action_plan = _build_action_plan(rows, allocation, summary, cash)
    budget_plans = _build_budget_plans(rows, allocation, summary, action_plan)
    recommended_products = _build_recommended_products(rows, allocation, summary, action_plan)

    rows.sort(key=lambda item: item["market_value"], reverse=True)
    return {
        "holdings": rows,
        "summary": summary,
        "allocation": allocation,
        "risk_flags": risk_flags,
        "suggestions": suggestions,
        "action_plan": action_plan,
        "budget_plans": budget_plans,
        "recommended_products": recommended_products,
    }


def backtest_portfolio(
    holdings: list[HoldingInput],
    cash: float,
    start_date: str,
    end_date: str,
    benchmark: str | None = None,
) -> dict[str, Any]:
    cleaned = [item for item in holdings if item.symbol.strip() and item.shares > 0]
    if not cleaned:
        return {"error": "請至少輸入一筆持股", "passed": False}

    rows, allocation, summary = _build_portfolio_snapshot(cleaned, cash)
    benchmark_symbol = (benchmark or _pick_benchmark(allocation)).upper()

    series_map: dict[str, pd.Series] = {}
    first_valid_dates: list[pd.Timestamp] = []

    for item in cleaned:
        df = data_router.get_price(item.symbol.strip().upper(), start_date, end_date)
        if df is None or df.empty:
            continue
        price_series = (
            df.assign(date=pd.to_datetime(df["date"]))[["date", "close"]]
            .dropna()
            .drop_duplicates(subset=["date"])
            .set_index("date")["close"]
            .astype(float)
            .sort_index()
        )
        if price_series.empty:
            continue
        series_map[item.symbol.strip().upper()] = price_series
        first_valid_dates.append(price_series.index.min())

    if not series_map:
        return {"error": "查無足夠歷史資料，無法回測此投資組合", "passed": False}

    start_anchor = max(first_valid_dates)
    aligned = pd.concat(series_map, axis=1).sort_index()
    aligned = aligned[aligned.index >= start_anchor].ffill().dropna(how="any")
    if aligned.empty or len(aligned) < 30:
        return {"error": "可用的共同歷史區間太短，至少需要約 30 個交易日", "passed": False}

    portfolio_series = pd.Series(index=aligned.index, dtype=float)
    for item in cleaned:
        symbol = item.symbol.strip().upper()
        if symbol not in aligned.columns:
            continue
        component = aligned[symbol] * float(item.shares)
        portfolio_series = component if portfolio_series.isna().all() else portfolio_series.add(component, fill_value=0.0)
    portfolio_series = portfolio_series.add(float(cash), fill_value=0.0)

    benchmark_df = data_router.get_price(benchmark_symbol, start_date, end_date)
    benchmark_series = _prepare_benchmark_series(benchmark_df, portfolio_series.index, portfolio_series.iloc[0])

    metrics = _calc_curve_metrics(portfolio_series)
    benchmark_metrics = _calc_curve_metrics(benchmark_series)
    drawdown_series = _drawdown_series(portfolio_series)
    benchmark_return = benchmark_metrics["return_pct"]
    alpha_pct = metrics["return_pct"] - benchmark_return
    correlation = _calc_correlation(portfolio_series, benchmark_series)

    action_plan = _build_action_plan(rows, allocation, summary, cash)
    budget_plans = _build_budget_plans(rows, allocation, summary, action_plan)
    backtest_advice = _build_backtest_advice(metrics, benchmark_metrics, alpha_pct, allocation, action_plan)
    future_outlook = _build_future_outlook(portfolio_series, metrics, benchmark_symbol)
    recommended_products = _build_recommended_products(rows, allocation, summary, action_plan, future_outlook)

    return {
        "period": {
            "start": aligned.index.min().strftime("%Y-%m-%d"),
            "end": aligned.index.max().strftime("%Y-%m-%d"),
        },
        "summary": {
            "initial_value": round(float(portfolio_series.iloc[0]), 2),
            "final_value": round(float(portfolio_series.iloc[-1]), 2),
            "cash": round(float(cash), 2),
            "holdings_count": len(cleaned),
        },
        "metrics": metrics,
        "benchmark": {
            "symbol": benchmark_symbol,
            "return_pct": benchmark_return,
            "annual_return": benchmark_metrics["annual_return"],
            "alpha_pct": round(alpha_pct, 2),
            "correlation": correlation,
        },
        "equity_curve": [
            {"date": idx.strftime("%Y-%m-%d"), "value": round(float(value), 2)}
            for idx, value in portfolio_series.items()
        ],
        "drawdown_curve": [
            {"date": idx.strftime("%Y-%m-%d"), "value": round(float(value), 2)}
            for idx, value in drawdown_series.items()
        ],
        "action_plan": action_plan,
        "budget_plans": budget_plans,
        "advice": backtest_advice,
        "future_outlook": future_outlook,
        "recommended_products": recommended_products,
        "assumption": "以目前持股股數回推歷史，假設回測期間不再加減碼，現金部位固定不動。",
        "passed": True,
    }


def _build_portfolio_snapshot(holdings: list[HoldingInput], cash: float) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, float]]:
    symbols = [item.symbol.strip().upper() for item in holdings]
    quotes = data_router.get_realtime_all(symbols)
    quote_map = {item["symbol"].upper(): item for item in quotes}

    rows: list[dict[str, Any]] = []
    total_market_value = 0.0
    total_cost = 0.0
    allocation_values = {
        "core": 0.0,
        "satellite": 0.0,
        "taiwan": 0.0,
        "us": 0.0,
        "bond": 0.0,
        "gold": 0.0,
        "defensive": 0.0,
    }

    for item in holdings:
        symbol = item.symbol.strip().upper()
        quote = quote_map.get(symbol, {})
        price = _float_or_none(quote.get("price")) or 0.0
        market_value = price * item.shares
        cost_basis = (item.avg_cost or 0.0) * item.shares if item.avg_cost is not None else None
        pnl = market_value - cost_basis if cost_basis is not None else None
        pnl_pct = ((pnl / cost_basis) * 100) if pnl is not None and cost_basis not in (None, 0) else None

        total_market_value += market_value
        if cost_basis is not None:
            total_cost += cost_basis

        bucket = _classify_symbol(symbol)
        allocation_values[bucket["style"]] += market_value
        allocation_values[bucket["region"]] += market_value
        if bucket["defensive"] == "bond":
            allocation_values["bond"] += market_value
            allocation_values["defensive"] += market_value
        if bucket["defensive"] == "gold":
            allocation_values["gold"] += market_value
            allocation_values["defensive"] += market_value

        rows.append(
            {
                "symbol": symbol,
                "shares": round(item.shares, 4),
                "avg_cost": round(item.avg_cost, 4) if item.avg_cost is not None else None,
                "price": round(price, 4),
                "market_value": round(market_value, 2),
                "cost_basis": round(cost_basis, 2) if cost_basis is not None else None,
                "unrealized_pnl": round(pnl, 2) if pnl is not None else None,
                "unrealized_pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
                "currency": quote.get("currency"),
                "style": bucket["style"],
                "region": bucket["region"],
            }
        )

    portfolio_value = total_market_value + cash
    for row in rows:
        row["weight_pct"] = round((row["market_value"] / portfolio_value) * 100, 2) if portfolio_value else 0.0

    allocation = {
        key: round((value / portfolio_value) * 100, 2) if portfolio_value else 0.0
        for key, value in allocation_values.items()
    }
    cash_weight = round((cash / portfolio_value) * 100, 2) if portfolio_value else 0.0

    summary = {
        "total_market_value": round(total_market_value, 2),
        "cash": round(cash, 2),
        "portfolio_value": round(portfolio_value, 2),
        "unrealized_pnl": round(total_market_value - total_cost, 2) if total_cost else 0.0,
        "cash_weight": cash_weight,
    }
    return rows, allocation, summary


def _build_risk_flags(rows: list[dict[str, Any]], allocation: dict[str, float], cash_weight: float) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    if not rows:
        return flags

    largest = max(rows, key=lambda item: item["weight_pct"])
    if largest["weight_pct"] > 35:
        flags.append(
            {
                "level": "high",
                "title": "單一持股過度集中",
                "message": f"{largest['symbol']} 目前佔比 {largest['weight_pct']}%，波動會明顯主導整體績效。",
            }
        )

    if allocation.get("taiwan", 0) > 75:
        flags.append(
            {
                "level": "medium",
                "title": "台股曝險偏高",
                "message": "投資組合大多集中在台股市場，建議搭配全球或美股 ETF 分散區域風險。",
            }
        )
    if allocation.get("us", 0) > 85:
        flags.append(
            {
                "level": "medium",
                "title": "美股曝險偏高",
                "message": "目前大多押注美股，若你的生活支出與收入在台灣，可保留部分台幣資產平衡。",
            }
        )
    if allocation.get("defensive", 0) < 5 and cash_weight < 5:
        flags.append(
            {
                "level": "medium",
                "title": "緩衝資產偏低",
                "message": "現金、債券、黃金合計太低，若遇到大波動，組合承受度會比較差。",
            }
        )
    if cash_weight < 3:
        flags.append(
            {
                "level": "low",
                "title": "現金緩衝偏低",
                "message": "若市場回檔，現在可用來加碼的彈性較少。",
            }
        )
    return flags


def _build_suggestions(rows: list[dict[str, Any]], allocation: dict[str, float], cash_weight: float) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    holding_count = len(rows)
    largest_weight = max((row["weight_pct"] for row in rows), default=0.0)

    if holding_count < 3:
        suggestions.append(
            {
                "title": "先建立核心底倉",
                "detail": "持股數偏少，建議先用 VT / VOO / 0050 / 006208 這類核心 ETF 建底，再決定衛星配置。",
            }
        )
    if allocation.get("core", 0) < 40:
        suggestions.append(
            {
                "title": "提高核心 ETF 比重",
                "detail": f"核心資產目前約 {allocation.get('core', 0):.1f}%。若想讓組合更穩，建議逐步拉到 50%~70%。",
            }
        )
    if largest_weight > 35:
        suggestions.append(
            {
                "title": "考慮分批再平衡",
                "detail": f"最大持股約 {largest_weight:.1f}%。若不是刻意重壓單一主題，可分批移到核心 ETF 或現金。",
            }
        )
    if allocation.get("bond", 0) < 5 and allocation.get("gold", 0) < 5 and cash_weight < 10:
        suggestions.append(
            {
                "title": "增加緩衝資產",
                "detail": "如果你希望下跌時更穩，可以預留 5%~10% 現金，或少量配置債券 ETF / 黃金。",
            }
        )
    if allocation.get("satellite", 0) > 45:
        suggestions.append(
            {
                "title": "衛星部位偏重",
                "detail": "若目標是長期穩定累積，建議讓題材型或高波動部位低於整體的 30%~45%。",
            }
        )
    if not suggestions:
        suggestions.append(
            {
                "title": "配置結構相對平衡",
                "detail": "目前沒有明顯集中風險，可以持續定期再平衡與分批加碼維持紀律。",
            }
        )
    return suggestions


def _build_action_plan(
    rows: list[dict[str, Any]],
    allocation: dict[str, float],
    summary: dict[str, float],
    cash: float,
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    if not rows or summary["portfolio_value"] <= 0:
        return plan

    portfolio_value = float(summary["portfolio_value"])
    spendable_cash = max(float(cash), 0.0)
    forbidden_buys: set[str] = set()
    largest = max(rows, key=lambda item: item["weight_pct"])
    if largest["weight_pct"] > 35 and largest["price"] > 0:
        target_value = portfolio_value * 0.3
        sell_amount = max(largest["market_value"] - target_value, 0.0)
        est_shares = sell_amount / largest["price"] if largest["price"] else 0.0
        if sell_amount > 0:
            forbidden_buys.add(largest["symbol"])
            spendable_cash += sell_amount
            plan.append(
                {
                    "priority": "high",
                    "action": "sell",
                    "symbol": largest["symbol"],
                    "amount": round(sell_amount, 2),
                    "estimated_shares": round(est_shares, 4),
                    "reason": f"{largest['symbol']} 目前佔比 {largest['weight_pct']}%，先分批降到接近 30% 左右，避免單一標的主導整體波動。",
                }
            )

    core_gap_pct = max(TARGETS["core"] - allocation.get("core", 0), 0.0)
    if core_gap_pct > 0 and spendable_cash > 0:
        preferred_core = _select_core_symbol(allocation, forbidden_buys)
        target_amount = min(portfolio_value * (core_gap_pct / 100), spendable_cash * 0.7)
        price = _holding_price(rows, preferred_core)
        est_shares = target_amount / price if price else None
        if target_amount > 0:
            spendable_cash -= target_amount
            plan.append(
                {
                    "priority": "high" if core_gap_pct > 15 else "medium",
                    "action": "buy",
                    "symbol": preferred_core,
                    "amount": round(target_amount, 2),
                    "estimated_shares": round(est_shares, 4) if est_shares is not None else None,
                    "reason": f"核心配置距離目標仍少 {core_gap_pct:.1f}%，這筆資金優先補到 {preferred_core}，會比繼續加碼題材股更穩。",
                }
            )

    defensive_gap_pct = max(TARGETS["defensive"] - allocation.get("defensive", 0), 0.0)
    if defensive_gap_pct > 0 and spendable_cash > 0:
        symbol = "TLT" if allocation.get("us", 0) >= allocation.get("taiwan", 0) else "GLD"
        if symbol in forbidden_buys:
            symbol = "GLD" if symbol == "TLT" else "TLT"
        target_amount = min(portfolio_value * (defensive_gap_pct / 100), spendable_cash)
        price = _holding_price(rows, symbol)
        est_shares = target_amount / price if price else None
        if target_amount > 0:
            spendable_cash -= target_amount
            plan.append(
                {
                    "priority": "medium",
                    "action": "buy",
                    "symbol": symbol,
                    "amount": round(target_amount, 2),
                    "estimated_shares": round(est_shares, 4) if est_shares is not None else None,
                    "reason": f"補一點 {symbol} 這類防禦資產，讓回檔時不必完全靠現金或高波動持股硬扛。",
                }
            )

    desired_cash = portfolio_value * (TARGETS["cash"] / 100)
    if cash < desired_cash and spendable_cash <= 0:
        gap = desired_cash - cash
        plan.append(
            {
                "priority": "low",
                "action": "hold_cash",
                "symbol": None,
                "amount": round(gap, 2),
                "estimated_shares": None,
                "reason": f"現金緩衝仍比目標少約 {gap:.0f}，下一筆資金先留著，等回檔或再平衡時會更好用。",
            }
        )

    if not plan:
        plan.append(
            {
                "priority": "low",
                "action": "hold",
                "symbol": None,
                "amount": 0.0,
                "estimated_shares": None,
                "reason": "目前配置接近目標，維持定期投入與半年一次再平衡即可。",
            }
        )

    return plan


def _select_core_symbol(allocation: dict[str, float], forbidden_buys: set[str] | None = None) -> str:
    forbidden = forbidden_buys or set()
    primary = "0050" if allocation.get("taiwan", 0) >= allocation.get("us", 0) else "VT"
    if primary not in forbidden:
        return primary
    fallback = "VT" if primary == "0050" else "0050"
    if fallback not in forbidden:
        return fallback
    return primary


def _build_budget_plans(
    rows: list[dict[str, Any]],
    allocation: dict[str, float],
    summary: dict[str, float],
    action_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    portfolio_value = float(summary.get("portfolio_value", 0.0))
    if portfolio_value <= 0:
        return []

    dominant_region = "taiwan" if allocation.get("taiwan", 0) >= allocation.get("us", 0) else "us"
    primary_core = _select_core_symbol(allocation)
    global_symbol = "VT" if primary_core != "VT" else "0050"
    defensive_symbol = "GLD" if dominant_region == "taiwan" else "TLT"

    weights: list[tuple[str, float, str]] = []
    if allocation.get("core", 0) < 50:
        weights.append((primary_core, 0.55, "先補核心底倉，讓整體報酬來源更穩。"))
    else:
        weights.append((primary_core, 0.4, "維持核心資產為主，避免新增資金太分散。"))

    if dominant_region == "taiwan" and allocation.get("us", 0) < 25:
        weights.append((global_symbol, 0.3, "補一點全球曝險，降低只押單一市場的風險。"))
    elif dominant_region == "us" and allocation.get("taiwan", 0) < 15:
        weights.append((global_symbol, 0.2, "保留一部分台幣核心資產，讓生活幣別與資產更一致。"))
    else:
        weights.append((global_symbol, 0.2, "用第二核心標的分散單一 ETF 的集中度。"))

    if allocation.get("defensive", 0) < 8:
        weights.append((defensive_symbol, 0.15, "補少量防禦資產，讓組合回檔時不要太痛。"))

    if action_plan and action_plan[0].get("action") == "sell":
        weights.append(("CASH", 0.1, "先留一些現金，等減碼完成後再分批投入更順。"))
    else:
        weights.append(("CASH", 0.1, "預留一點現金，之後加碼會比較有彈性。"))

    normalized_total = sum(weight for _, weight, _ in weights)
    budgets = [10_000, 50_000, 100_000]
    current_cash = float(summary.get("cash", 0.0))
    if current_cash >= 5_000:
        budgets.insert(0, int(round(current_cash, -3)))

    plans: list[dict[str, Any]] = []
    seen_budgets: set[int] = set()
    for budget in budgets:
        if budget in seen_budgets:
            continue
        seen_budgets.add(budget)
        entries: list[dict[str, Any]] = []
        for symbol, weight, reason in weights:
            amount = round(budget * (weight / normalized_total), 2)
            if amount <= 0:
                continue
            if symbol == "CASH":
                entries.append(
                    {
                        "symbol": "CASH",
                        "amount": amount,
                        "estimated_shares": None,
                        "reason": reason,
                    }
                )
                continue
            price = _holding_price(rows, symbol)
            est_shares = amount / price if price and price > 0 else None
            entries.append(
                {
                    "symbol": symbol,
                    "amount": amount,
                    "estimated_shares": round(est_shares, 4) if est_shares is not None else None,
                    "reason": reason,
                }
            )
        plans.append(
            {
                "budget": budget,
                "summary": f"如果你現在多投入 {budget:,.0f}，建議先照這個順序分批配置。",
                "items": entries,
            }
        )
    return plans


def _holding_price(rows: list[dict[str, Any]], symbol: str) -> float | None:
    for row in rows:
        if row["symbol"] == symbol and row["price"] > 0:
            return float(row["price"])
    quotes = data_router.get_realtime_all([symbol])
    if quotes:
        return _float_or_none(quotes[0].get("price"))
    return None


def _pick_benchmark(allocation: dict[str, float]) -> str:
    region = "taiwan" if allocation.get("taiwan", 0) >= allocation.get("us", 0) else "us"
    return BENCHMARK_BY_REGION[region]


def _prepare_benchmark_series(df: pd.DataFrame, index: pd.Index, initial_value: float) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(initial_value, index=index, dtype=float)
    series = (
        df.assign(date=pd.to_datetime(df["date"]))[["date", "close"]]
        .dropna()
        .drop_duplicates(subset=["date"])
        .set_index("date")["close"]
        .astype(float)
        .sort_index()
    )
    if series.empty:
        return pd.Series(initial_value, index=index, dtype=float)
    series = series.reindex(index).ffill().dropna()
    if series.empty:
        return pd.Series(initial_value, index=index, dtype=float)
    normalized = series / float(series.iloc[0]) * float(initial_value)
    return normalized


def _calc_curve_metrics(series: pd.Series) -> dict[str, float]:
    series = series.dropna()
    if len(series) < 2:
        return {
            "return_pct": 0.0,
            "annual_return": 0.0,
            "annual_volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }

    returns = series.pct_change().dropna()
    total_return = (float(series.iloc[-1]) / float(series.iloc[0]) - 1) * 100
    days = max((series.index[-1] - series.index[0]).days, 1)
    years = days / 365.25
    annual_return = ((float(series.iloc[-1]) / float(series.iloc[0])) ** (1 / years) - 1) * 100 if years > 0 else total_return
    annual_vol = float(returns.std() * np.sqrt(252) * 100) if not returns.empty else 0.0
    sharpe = (annual_return / annual_vol) if annual_vol > 0 else 0.0
    max_drawdown = float(_drawdown_series(series).min()) if not series.empty else 0.0

    return {
        "return_pct": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "annual_volatility": round(annual_vol, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 2),
    }


def _drawdown_series(series: pd.Series) -> pd.Series:
    rolling_max = series.cummax()
    return (series / rolling_max - 1) * 100


def _calc_correlation(lhs: pd.Series, rhs: pd.Series) -> float:
    joined = pd.concat([lhs.pct_change(), rhs.pct_change()], axis=1).dropna()
    if joined.empty:
        return 0.0
    corr = joined.iloc[:, 0].corr(joined.iloc[:, 1])
    if corr is None or math.isnan(corr):
        return 0.0
    return round(float(corr), 2)


def _build_backtest_advice(
    metrics: dict[str, float],
    benchmark_metrics: dict[str, float],
    alpha_pct: float,
    allocation: dict[str, float],
    action_plan: list[dict[str, Any]],
) -> list[dict[str, str]]:
    advice: list[dict[str, str]] = []

    if alpha_pct < -10:
        advice.append(
            {
                "title": "組合明顯落後基準",
                "detail": f"這段期間落後基準約 {abs(alpha_pct):.1f}%。若不是刻意押題材，建議把部分資金移回核心 ETF。",
            }
        )
    elif alpha_pct > 10:
        advice.append(
            {
                "title": "組合跑贏基準",
                "detail": f"這段期間多賺約 {alpha_pct:.1f}%，但仍要確認不是靠單一集中部位硬撐出來的超額報酬。",
            }
        )

    if metrics["max_drawdown"] < -25:
        advice.append(
            {
                "title": "回撤偏深",
                "detail": f"最大回撤 {metrics['max_drawdown']:.1f}%。如果這個波動你睡不好，先降低高波動持股比率會比繼續硬抱更實際。",
            }
        )

    if metrics["annual_volatility"] > benchmark_metrics["annual_volatility"] + 5:
        advice.append(
            {
                "title": "波動顯著高於基準",
                "detail": "你的組合比基準更晃，代表你承擔了額外風險。若報酬沒有同步提高，這個風險不一定值得。",
            }
        )

    if allocation.get("core", 0) < 50:
        advice.append(
            {
                "title": "先用核心資產穩住底盤",
                "detail": "若你想讓回測曲線更平滑、把回撤壓下來，優先把核心 ETF 補到一半以上通常比挑下一檔飆股更有效。",
            }
        )

    if action_plan:
        top_action = action_plan[0]
        symbol = top_action.get("symbol") or "現金部位"
        advice.append(
            {
                "title": "下一步怎麼做",
                "detail": f"優先動作可先處理 {symbol}，大約金額 {top_action.get('amount', 0):,.0f}。這會比只看建議文字更容易真的執行。",
            }
        )

    if not advice:
        advice.append(
            {
                "title": "目前回測與配置大致合理",
                "detail": "可以維持定期投入與再平衡，重點是不要因短期漲跌頻繁改策略。",
            }
        )
    return advice


def _build_future_outlook(
    portfolio_series: pd.Series,
    metrics: dict[str, float],
    benchmark_symbol: str,
) -> dict[str, Any]:
    returns = portfolio_series.pct_change().dropna()
    recent_1m = _window_return(portfolio_series, 21)
    recent_3m = _window_return(portfolio_series, 63)
    sma20 = portfolio_series.rolling(20).mean().iloc[-1] if len(portfolio_series) >= 20 else float(portfolio_series.iloc[-1])
    sma60 = portfolio_series.rolling(60).mean().iloc[-1] if len(portfolio_series) >= 60 else sma20
    last_price = float(portfolio_series.iloc[-1])

    if last_price > sma20 > sma60 and recent_3m > 0:
        regime = "BULLISH"
        summary = "目前趨勢偏多，短中期仍有續強空間，但更適合分批布局而不是一次重壓。"
    elif last_price < sma20 < sma60 and recent_3m < 0:
        regime = "BEARISH"
        summary = "目前偏弱勢，短線先求穩比追價重要，若要加碼建議先補核心或保留現金。"
    else:
        regime = "RANGE"
        summary = "目前較像震盪整理，適合用分批、再平衡或定期定額，不適合用單次重押賭方向。"

    half_year_return = metrics["annual_return"] * 0.5
    half_year_vol = metrics["annual_volatility"] * math.sqrt(0.5)
    optimistic = round(half_year_return + half_year_vol * 0.7, 2)
    base = round(half_year_return, 2)
    conservative = round(half_year_return - half_year_vol * 0.7, 2)
    confidence = "MEDIUM"
    if metrics["annual_volatility"] < 12 and abs(recent_3m) > 2:
        confidence = "MEDIUM_HIGH"
    elif metrics["annual_volatility"] > 20:
        confidence = "LOW"

    return {
        "benchmark": benchmark_symbol,
        "signal": regime,
        "confidence": confidence,
        "summary": summary,
        "drivers": [
            f"近 1 個月報酬 {recent_1m:.2f}%",
            f"近 3 個月報酬 {recent_3m:.2f}%",
            f"年化波動 {metrics['annual_volatility']:.2f}%",
            f"最大回撤 {metrics['max_drawdown']:.2f}%",
        ],
        "scenarios": [
            {"name": "樂觀", "horizon": "6M", "expected_return_pct": optimistic, "message": "若風險偏好延續、核心資產續強，組合有機會穩步墊高。"},
            {"name": "基準", "horizon": "6M", "expected_return_pct": base, "message": "較合理的預期是跟著基本趨勢緩步推進，報酬不一定爆發但可持續。"},
            {"name": "保守", "horizon": "6M", "expected_return_pct": conservative, "message": "若市場回檔或高波動資產失速，組合仍可能先經歷一段修正。"},
        ],
    }


def _build_recommended_products(
    rows: list[dict[str, Any]],
    allocation: dict[str, float],
    summary: dict[str, float],
    action_plan: list[dict[str, Any]],
    future_outlook: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    holdings = {row["symbol"] for row in rows}
    dominant_region = "taiwan" if allocation.get("taiwan", 0) >= allocation.get("us", 0) else "us"
    regime = (future_outlook or {}).get("signal", "RANGE")

    if allocation.get("core", 0) < 50:
        core_symbol = "0050" if dominant_region == "taiwan" else "VT"
        recommendations.append(
            {
                "symbol": core_symbol,
                "stance": "RECOMMEND",
                "title": f"優先補核心資產 {core_symbol}",
                "reason": f"你目前核心配置只有 {allocation.get('core', 0):.1f}%，先提高到底倉比再追題材更能穩住整體波動。",
            }
        )

    if allocation.get("defensive", 0) < 8 and summary.get("cash_weight", 0) < 10:
        defensive_symbol = "TLT" if dominant_region == "us" else "GLD"
        recommendations.append(
            {
                "symbol": defensive_symbol,
                "stance": "RECOMMEND",
                "title": f"補一點防禦資產 {defensive_symbol}",
                "reason": "你的現金與防禦資產偏少，補一些債券或黃金能讓回撤沒那麼傷。",
            }
        )

    if dominant_region == "taiwan" and allocation.get("us", 0) < 25:
        recommendations.append(
            {
                "symbol": "VT",
                "stance": "RECOMMEND",
                "title": "加一點全球曝險",
                "reason": "目前組合偏台股，VT 能一次補全球分散，不需要你自己挑每個國家。",
            }
        )

    if dominant_region == "us" and allocation.get("taiwan", 0) < 15:
        recommendations.append(
            {
                "symbol": "0050",
                "stance": "OPTIONAL",
                "title": "保留部分台幣核心資產",
                "reason": "如果你的生活與支出在台灣，留一部分台股核心 ETF 會讓資產與負債幣別更一致。",
            }
        )

    if "QQQ" in holdings or allocation.get("satellite", 0) > 40:
        recommendations.append(
            {
                "symbol": "QQQ",
                "stance": "AVOID",
                "title": "暫時不建議再加碼 QQQ",
                "reason": "你現在的衛星或科技曝險已經不低，再疊上去容易把波動拉得太高。",
            }
        )

    if regime == "BEARISH":
        recommendations.append(
            {
                "symbol": "CASH",
                "stance": "AVOID",
                "title": "弱勢時先保留現金",
                "reason": "目前訊號偏弱，與其急著追進，不如保留子彈等更好的風險報酬比。",
            }
        )

    if not recommendations and action_plan:
        first = action_plan[0]
        recommendations.append(
            {
                "symbol": first.get("symbol") or "CURRENT",
                "stance": "RECOMMEND",
                "title": "先照目前調整計畫執行",
                "reason": first["reason"],
            }
        )

    return recommendations[:5]


def _window_return(series: pd.Series, window: int) -> float:
    if len(series) <= window:
        return (float(series.iloc[-1]) / float(series.iloc[0]) - 1) * 100 if len(series) > 1 else 0.0
    recent = series.iloc[-window - 1 :]
    return (float(recent.iloc[-1]) / float(recent.iloc[0]) - 1) * 100


def _classify_symbol(symbol: str) -> dict[str, str]:
    is_tw = data_router.is_taiwan_stock(symbol)
    region = "taiwan" if is_tw or symbol == "^TWII" else "us"

    if symbol in CORE_ETFS:
        style = "core"
    else:
        style = "satellite"

    if symbol in BOND_ETFS:
        defensive = "bond"
    elif symbol in GOLD_ETFS:
        defensive = "gold"
    else:
        defensive = "none"

    return {"style": style, "region": region, "defensive": defensive}


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
