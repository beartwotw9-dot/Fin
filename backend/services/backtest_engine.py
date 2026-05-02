"""回測引擎：4 種策略 + 篩選門檻 + Walk-Forward + 穩健性測試.

防過度擬合的核心：
1. 五大必過門檻 (Sharpe / MDD / Win rate / Trades / Profit factor)
2. Walk-Forward：60% IS 找參數 → 20% OOS 跑同參數
3. 參數穩健性：±10% 各跑一遍，比較 Sharpe 標準差
"""
from __future__ import annotations

import math
import warnings
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover

from . import data_router

# ----------------------------------------------------------------------
# 篩選門檻（5 大必過）
# ----------------------------------------------------------------------
FILTER_THRESHOLDS: list[dict[str, Any]] = [
    {"key": "sharpe", "label": "Sharpe Ratio", "op": ">=", "value": 0.75},
    {"key": "max_drawdown", "label": "Max Drawdown", "op": ">=", "value": -30.0},
    {"key": "win_rate", "label": "Win Rate (%)", "op": ">=", "value": 40.0},
    {"key": "total_trades", "label": "Total Trades", "op": ">=", "value": 10},
    {"key": "profit_factor", "label": "Profit Factor", "op": ">=", "value": 1.2},
]

WF_VERDICT_ROBUST = 0.7
WF_VERDICT_MARGINAL = 0.3


# ----------------------------------------------------------------------
# 指標小工具（不依賴 ta-lib）
# ----------------------------------------------------------------------
def _SMA(values: pd.Series, window: int) -> pd.Series:
    return pd.Series(values).rolling(window).mean()


def _RSI(values: pd.Series, window: int = 14) -> pd.Series:
    s = pd.Series(values)
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / window, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / window, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _BB(values: pd.Series, window: int, std_dev: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    s = pd.Series(values)
    mid = s.rolling(window).mean()
    std = s.rolling(window).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def _MACD(values: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series]:
    s = pd.Series(values)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig


# ----------------------------------------------------------------------
# 策略定義
# ----------------------------------------------------------------------
class SmaCrossStrategy(Strategy):
    fast_period = 20
    slow_period = 60

    def init(self) -> None:
        close = self.data.Close
        self.fast = self.I(_SMA, pd.Series(close), self.fast_period)
        self.slow = self.I(_SMA, pd.Series(close), self.slow_period)

    def next(self) -> None:
        if crossover(self.fast, self.slow):
            self.position.close()
            self.buy()
        elif crossover(self.slow, self.fast):
            self.position.close()


class RsiStrategy(Strategy):
    period = 14
    oversold = 30
    overbought = 70

    def init(self) -> None:
        close = self.data.Close
        self.rsi = self.I(_RSI, pd.Series(close), self.period)

    def next(self) -> None:
        rsi = self.rsi[-1]
        if not self.position and rsi < self.oversold:
            self.buy()
        elif self.position and rsi > self.overbought:
            self.position.close()


class BollingerStrategy(Strategy):
    period = 20
    std_dev = 2.0

    def init(self) -> None:
        close = self.data.Close
        upper, mid, lower = _BB(pd.Series(close), self.period, self.std_dev)
        self.upper = self.I(lambda: upper.values, name="upper")
        self.mid = self.I(lambda: mid.values, name="mid")
        self.lower = self.I(lambda: lower.values, name="lower")

    def next(self) -> None:
        price = self.data.Close[-1]
        if not self.position and price < self.lower[-1]:
            self.buy()
        elif self.position and price > self.upper[-1]:
            self.position.close()


class MacdStrategy(Strategy):
    fast = 12
    slow = 26
    signal = 9

    def init(self) -> None:
        close = self.data.Close
        macd, sig = _MACD(pd.Series(close), self.fast, self.slow, self.signal)
        self.macd = self.I(lambda: macd.values, name="macd")
        self.signal_line = self.I(lambda: sig.values, name="signal")

    def next(self) -> None:
        if crossover(self.macd, self.signal_line):
            self.position.close()
            self.buy()
        elif crossover(self.signal_line, self.macd):
            self.position.close()


STRATEGY_REGISTRY: dict[str, dict[str, Any]] = {
    "sma_cross": {
        "cls": SmaCrossStrategy,
        "name": "均線交叉",
        "params": [
            {"key": "fast_period", "default": 20, "min": 5, "max": 100},
            {"key": "slow_period", "default": 60, "min": 10, "max": 250},
        ],
    },
    "rsi": {
        "cls": RsiStrategy,
        "name": "RSI 反轉",
        "params": [
            {"key": "period", "default": 14, "min": 5, "max": 30},
            {"key": "oversold", "default": 30, "min": 10, "max": 40},
            {"key": "overbought", "default": 70, "min": 60, "max": 90},
        ],
    },
    "bollinger": {
        "cls": BollingerStrategy,
        "name": "布林通道",
        "params": [
            {"key": "period", "default": 20, "min": 10, "max": 60},
            {"key": "std_dev", "default": 2.0, "min": 1.0, "max": 3.0},
        ],
    },
    "macd": {
        "cls": MacdStrategy,
        "name": "MACD",
        "params": [
            {"key": "fast", "default": 12, "min": 5, "max": 20},
            {"key": "slow", "default": 26, "min": 15, "max": 60},
            {"key": "signal", "default": 9, "min": 5, "max": 20},
        ],
    },
}


def list_strategies() -> list[dict[str, Any]]:
    return [
        {"id": sid, "name": meta["name"], "params": meta["params"]}
        for sid, meta in STRATEGY_REGISTRY.items()
    ]


# ----------------------------------------------------------------------
# 共用：跑一次 Backtest，回傳 stats 與 equity 序列
# ----------------------------------------------------------------------
def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """轉為 backtesting.py 需要的格式：DatetimeIndex + Open/High/Low/Close/Volume."""
    if df.empty:
        return df
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.set_index("date").sort_index()
    out = out.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    out[["Open", "High", "Low", "Close", "Volume"]] = out[
        ["Open", "High", "Low", "Close", "Volume"]
    ].astype(float)
    return out[["Open", "High", "Low", "Close", "Volume"]].dropna()


def _run_one(
    data: pd.DataFrame,
    strategy_id: str,
    params: dict[str, Any],
    commission: float,
    slippage: float,
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """執行回測，回傳 (stats, equity_curve_df, trades_df)."""
    meta = STRATEGY_REGISTRY[strategy_id]
    cls = meta["cls"]

    # 動態子類別，注入參數
    attrs = {k: v for k, v in params.items() if hasattr(cls, k)}
    SubCls = type(f"_Tuned_{cls.__name__}", (cls,), attrs)

    bt = Backtest(
        data,
        SubCls,
        cash=1_000_000,
        commission=commission + slippage,
        exclusive_orders=True,
    )
    stats = bt.run()
    return stats, stats["_equity_curve"], stats["_trades"]


# ----------------------------------------------------------------------
# 績效指標計算（從 backtesting stats 萃取，補上 Sortino / Profit Factor / Recovery）
# ----------------------------------------------------------------------
def _compute_metrics(stats: pd.Series, equity: pd.DataFrame, trades: pd.DataFrame) -> dict[str, float]:
    def _f(key: str, default: float = 0.0) -> float:
        v = stats.get(key, default)
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return default
        return float(v)

    return_pct = _f("Return [%]")
    return_ann = _f("Return (Ann.) [%]")
    sharpe = _f("Sharpe Ratio")
    sortino = _f("Sortino Ratio")
    calmar = _f("Calmar Ratio")
    max_dd = _f("Max. Drawdown [%]")
    max_dd_dur = stats.get("Max. Drawdown Duration")
    if hasattr(max_dd_dur, "days"):
        max_dd_dur = int(max_dd_dur.days)
    else:
        max_dd_dur = int(_f("Max. Drawdown Duration", 0))
    win_rate = _f("Win Rate [%]")
    total_trades = int(_f("# Trades"))
    avg_trade = _f("Avg. Trade [%]")
    best_trade = _f("Best Trade [%]")
    worst_trade = _f("Worst Trade [%]")

    # Profit factor
    if trades is not None and not trades.empty and "PnL" in trades.columns:
        gain = trades.loc[trades["PnL"] > 0, "PnL"].sum()
        loss = -trades.loc[trades["PnL"] < 0, "PnL"].sum()
        pf = float(gain / loss) if loss > 0 else (float("inf") if gain > 0 else 0.0)
        if math.isinf(pf):
            pf = 999.0
    else:
        pf = 0.0

    # Recovery factor = Net profit / |MaxDD|（用百分比近似）
    rec = float(return_pct / abs(max_dd)) if max_dd < 0 else 0.0

    return {
        "return_pct": round(return_pct, 4),
        "return_ann": round(return_ann, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "calmar": round(calmar, 4),
        "max_drawdown": round(max_dd, 4),
        "max_drawdown_duration": max_dd_dur,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(pf, 4),
        "total_trades": total_trades,
        "avg_trade_pct": round(avg_trade, 4),
        "best_trade_pct": round(best_trade, 4),
        "worst_trade_pct": round(worst_trade, 4),
        "recovery_factor": round(rec, 4),
    }


def _evaluate_filter(metrics: dict[str, float]) -> dict[str, Any]:
    details = []
    score = 0
    for rule in FILTER_THRESHOLDS:
        value = metrics.get(rule["key"], 0)
        threshold = rule["value"]
        op = rule["op"]
        if op == ">=":
            passed = value >= threshold
        elif op == "<=":
            passed = value <= threshold
        else:
            passed = False
        score += int(bool(passed))
        details.append(
            {
                "metric": rule["label"],
                "value": value,
                "threshold": f"{op} {threshold}",
                "passed": bool(passed),
            }
        )
    return {
        "passed": score == len(FILTER_THRESHOLDS),
        "score": score,
        "max_score": len(FILTER_THRESHOLDS),
        "details": details,
    }


# ----------------------------------------------------------------------
# Walk-Forward
# ----------------------------------------------------------------------
def _grid_for(strategy_id: str, base_params: dict[str, Any]) -> list[dict[str, Any]]:
    """回傳給 IS 找最佳參數的 grid（精簡版避免太慢）."""
    meta = STRATEGY_REGISTRY[strategy_id]
    grids: dict[str, list[Any]] = {}
    for spec in meta["params"]:
        key = spec["key"]
        base = base_params.get(key, spec["default"])
        if isinstance(base, float):
            grids[key] = [round(base * f, 3) for f in (0.7, 1.0, 1.3)]
        else:
            lo = max(int(spec["min"]), int(round(base * 0.7)))
            hi = min(int(spec["max"]), int(round(base * 1.3)))
            grids[key] = sorted({lo, int(base), hi})
    keys = list(grids.keys())
    combos: list[dict[str, Any]] = []
    for combo in product(*[grids[k] for k in keys]):
        d = dict(zip(keys, combo))
        # SMA 強制 fast < slow
        if strategy_id == "sma_cross" and d.get("fast_period", 0) >= d.get("slow_period", 0):
            continue
        if strategy_id == "macd" and d.get("fast", 0) >= d.get("slow", 0):
            continue
        if strategy_id == "rsi" and d.get("oversold", 0) >= d.get("overbought", 0):
            continue
        combos.append(d)
    return combos


def _walk_forward(
    full_data: pd.DataFrame,
    strategy_id: str,
    base_params: dict[str, Any],
    commission: float,
    slippage: float,
) -> dict[str, Any]:
    """切 60/20/20，IS 找最佳，OOS 套用，計算 WF Efficiency."""
    n = len(full_data)
    if n < 100:
        return {
            "is_return": 0.0,
            "oos_return": 0.0,
            "wf_efficiency": 0.0,
            "verdict": "INSUFFICIENT_DATA",
            "best_params": base_params,
        }

    is_end = int(n * 0.6)
    oos_start = int(n * 0.8)
    is_data = full_data.iloc[:is_end]
    oos_data = full_data.iloc[oos_start:]

    # IS：在 grid 上找出 Sharpe 最高的參數組
    best_params = base_params
    best_sharpe = -1e9
    best_is_return = 0.0
    grid = _grid_for(strategy_id, base_params)
    for params in grid:
        try:
            stats, _, _ = _run_one(is_data, strategy_id, params, commission, slippage)
            sharpe = stats.get("Sharpe Ratio", -1e9)
            if sharpe is None or (isinstance(sharpe, float) and math.isnan(sharpe)):
                continue
            if sharpe > best_sharpe:
                best_sharpe = float(sharpe)
                best_params = params
                best_is_return = float(stats.get("Return [%]", 0.0))
        except Exception:
            continue

    # OOS：用最佳參數
    try:
        oos_stats, _, _ = _run_one(oos_data, strategy_id, best_params, commission, slippage)
        oos_return = float(oos_stats.get("Return [%]", 0.0))
    except Exception:
        oos_return = 0.0

    if best_is_return == 0:
        wf_eff = 0.0
    elif best_is_return > 0 and oos_return > 0:
        wf_eff = oos_return / best_is_return
    elif best_is_return > 0 and oos_return <= 0:
        wf_eff = 0.0
    else:
        wf_eff = 0.0

    if wf_eff >= WF_VERDICT_ROBUST:
        verdict = "ROBUST"
    elif wf_eff >= WF_VERDICT_MARGINAL:
        verdict = "MARGINAL"
    else:
        verdict = "OVERFIT"

    return {
        "is_return": round(best_is_return, 4),
        "oos_return": round(oos_return, 4),
        "wf_efficiency": round(wf_eff, 4),
        "verdict": verdict,
        "best_params": best_params,
    }


# ----------------------------------------------------------------------
# 參數穩健性：±10% 各一次
# ----------------------------------------------------------------------
def _robustness(
    data: pd.DataFrame,
    strategy_id: str,
    params: dict[str, Any],
    commission: float,
    slippage: float,
) -> dict[str, Any]:
    sharpes: list[float] = []
    for factor in (0.9, 1.0, 1.1):
        tweaked = {}
        for k, v in params.items():
            if isinstance(v, float):
                tweaked[k] = round(v * factor, 3)
            else:
                tweaked[k] = max(1, int(round(v * factor)))
        try:
            stats, _, _ = _run_one(data, strategy_id, tweaked, commission, slippage)
            s = stats.get("Sharpe Ratio")
            if s is not None and not (isinstance(s, float) and math.isnan(s)):
                sharpes.append(float(s))
        except Exception:
            continue
    if len(sharpes) < 2:
        return {"sharpe_std": None, "sharpes": sharpes, "stable": False}
    std = float(np.std(sharpes, ddof=0))
    return {
        "sharpe_std": round(std, 4),
        "sharpes": [round(x, 4) for x in sharpes],
        "stable": std < 0.3,
    }


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------
def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    strategy: str,
    params: dict[str, Any] | None = None,
    commission: float = 0.001425,
    slippage: float = 0.001,
) -> dict[str, Any]:
    """執行完整回測 + 篩選 + Walk-Forward + 穩健性測試."""
    if strategy not in STRATEGY_REGISTRY:
        return {"error": f"Unknown strategy: {strategy}", "passed": False}

    params = params or {}
    # 補上預設值
    for spec in STRATEGY_REGISTRY[strategy]["params"]:
        params.setdefault(spec["key"], spec["default"])

    raw = data_router.get_price(symbol, start_date, end_date)
    if raw is None or raw.empty:
        return {"error": f"No data for {symbol} between {start_date} ~ {end_date}", "passed": False}

    data = _prepare_data(raw)
    if len(data) < 30:
        return {"error": "資料筆數過少（< 30），無法進行回測", "passed": False}

    try:
        stats, equity_df, trades_df = _run_one(data, strategy, params, commission, slippage)
    except Exception as exc:
        return {"error": f"回測執行失敗：{exc}", "passed": False}

    metrics = _compute_metrics(stats, equity_df, trades_df)
    filt = _evaluate_filter(metrics)

    # 權益曲線 / 回撤曲線
    equity_curve = []
    drawdown_curve = []
    if equity_df is not None and not equity_df.empty:
        eq = equity_df["Equity"].astype(float)
        peak = eq.cummax()
        dd = (eq - peak) / peak * 100.0
        for ts, val in eq.items():
            equity_curve.append({"date": pd.Timestamp(ts).strftime("%Y-%m-%d"), "value": round(float(val), 2)})
        for ts, val in dd.items():
            drawdown_curve.append({"date": pd.Timestamp(ts).strftime("%Y-%m-%d"), "value": round(float(val), 4)})

    # 交易紀錄
    trade_list = []
    if trades_df is not None and not trades_df.empty:
        for _, r in trades_df.iterrows():
            entry = r.get("EntryTime")
            exit_ = r.get("ExitTime")
            entry_date = pd.Timestamp(entry).strftime("%Y-%m-%d") if entry is not None else ""
            exit_date = pd.Timestamp(exit_).strftime("%Y-%m-%d") if exit_ is not None else ""
            try:
                duration_days = (pd.Timestamp(exit_) - pd.Timestamp(entry)).days
            except Exception:
                duration_days = None
            trade_list.append(
                {
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "duration_days": duration_days,
                    "pnl_pct": round(float(r.get("ReturnPct", 0)) * 100, 4),
                    "type": "LONG" if float(r.get("Size", 1)) >= 0 else "SHORT",
                }
            )

    walk_forward = _walk_forward(data, strategy, params, commission, slippage)
    robustness = _robustness(data, strategy, params, commission, slippage)

    return {
        "symbol": symbol,
        "strategy": strategy,
        "params": params,
        "period": {"start": start_date, "end": end_date},
        "metrics": metrics,
        "walk_forward": walk_forward,
        "robustness": robustness,
        "filter": filt,
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "trades": trade_list,
        "passed": filt["passed"],
    }
