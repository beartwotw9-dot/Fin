const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
    ...init
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export type Quote = {
  symbol: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  currency?: string | null;
  note?: string;
  updated_at?: string | null;
};

export type MarketOverview = {
  updated_at: string;
  groups: Array<{
    id: string;
    title: string;
    description: string;
    items: Quote[];
  }>;
};

export type Candle = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type StrategyMeta = {
  id: string;
  name: string;
  params: { key: string; default: number; min: number; max: number }[];
};

export type BacktestResult = {
  symbol: string;
  strategy: string;
  params: Record<string, number>;
  period: { start: string; end: string };
  metrics: Record<string, number>;
  walk_forward: {
    is_return: number;
    oos_return: number;
    wf_efficiency: number;
    verdict: "ROBUST" | "MARGINAL" | "OVERFIT" | "INSUFFICIENT_DATA";
    best_params: Record<string, number>;
  };
  robustness: { sharpe_std: number | null; sharpes: number[]; stable: boolean };
  filter: {
    passed: boolean;
    score: number;
    max_score: number;
    details: { metric: string; value: number; threshold: string; passed: boolean }[];
  };
  equity_curve: { date: string; value: number }[];
  drawdown_curve: { date: string; value: number }[];
  trades: {
    entry_date: string;
    exit_date: string;
    duration_days: number | null;
    pnl_pct: number;
    type: string;
  }[];
  passed: boolean;
};

export type PortfolioHolding = {
  symbol: string;
  shares: number;
  avg_cost?: number | null;
};

export type PortfolioAnalysis = {
  holdings: Array<{
    symbol: string;
    shares: number;
    avg_cost: number | null;
    price: number;
    market_value: number;
    cost_basis: number | null;
    unrealized_pnl: number | null;
    unrealized_pnl_pct: number | null;
    currency: string | null;
    style: string;
    region: string;
    weight_pct: number;
  }>;
  summary: {
    total_market_value: number;
    cash: number;
    portfolio_value: number;
    unrealized_pnl: number;
    cash_weight: number;
  };
  allocation: Record<string, number>;
  risk_flags: Array<{ level: string; title: string; message: string }>;
  suggestions: Array<{ title: string; detail: string }>;
  action_plan: Array<{
    priority: string;
    action: string;
    symbol: string | null;
    amount: number;
    estimated_shares: number | null;
    reason: string;
  }>;
  recommended_products: Array<{
    symbol: string;
    stance: string;
    title: string;
    reason: string;
  }>;
};

export type PortfolioBacktestResult = {
  period: { start: string; end: string };
  summary: {
    initial_value: number;
    final_value: number;
    cash: number;
    holdings_count: number;
  };
  metrics: {
    return_pct: number;
    annual_return: number;
    annual_volatility: number;
    sharpe: number;
    max_drawdown: number;
  };
  benchmark: {
    symbol: string;
    return_pct: number;
    annual_return: number;
    alpha_pct: number;
    correlation: number;
  };
  equity_curve: { date: string; value: number }[];
  drawdown_curve: { date: string; value: number }[];
  action_plan: Array<{
    priority: string;
    action: string;
    symbol: string | null;
    amount: number;
    estimated_shares: number | null;
    reason: string;
  }>;
  advice: Array<{ title: string; detail: string }>;
  future_outlook: {
    benchmark: string;
    signal: string;
    confidence: string;
    summary: string;
    drivers: string[];
    scenarios: Array<{
      name: string;
      horizon: string;
      expected_return_pct: number;
      message: string;
    }>;
  };
  recommended_products: Array<{
    symbol: string;
    stance: string;
    title: string;
    reason: string;
  }>;
  assumption: string;
  passed: boolean;
  error?: string;
};

export const api = {
  watchlist: {
    get: () => request<{ symbols: Quote[] }>("/api/watchlist"),
    add: (symbol: string, note?: string) =>
      request<{ symbols: Quote[] }>("/api/watchlist", {
        method: "POST",
        body: JSON.stringify({ symbol, note: note ?? "" })
      }),
    remove: (symbol: string) =>
      request<{ symbols: Quote[] }>(`/api/watchlist/${encodeURIComponent(symbol)}`, {
        method: "DELETE"
      })
  },
  stock: {
    daily: (symbol: string, start: string, end: string) =>
      request<{ symbol: string; data: Candle[] }>(
        `/api/stock/${encodeURIComponent(symbol)}/daily?start_date=${start}&end_date=${end}`
      ),
    realtime: (symbol: string) =>
      request<Quote>(`/api/stock/${encodeURIComponent(symbol)}/realtime`),
    institutional: (symbol: string) =>
      request<{ symbol: string; available: boolean; data: { date: string; name: string; buy: number; sell: number; diff: number }[] }>(
        `/api/stock/${encodeURIComponent(symbol)}/institutional`
      )
  },
  market: {
    overview: () => request<MarketOverview>("/api/market/overview")
  },
  backtest: {
    strategies: () => request<StrategyMeta[]>("/api/backtest/strategies"),
    run: (body: {
      symbol: string;
      start_date: string;
      end_date: string;
      strategy: string;
      params: Record<string, number>;
      commission?: number;
      slippage?: number;
    }) =>
      request<BacktestResult>("/api/backtest", {
        method: "POST",
        body: JSON.stringify(body)
      })
  },
  portfolio: {
    analyze: (body: { cash: number; holdings: PortfolioHolding[] }) =>
      request<PortfolioAnalysis>("/api/portfolio/analyze", {
        method: "POST",
        body: JSON.stringify(body)
      }),
    backtest: (body: {
      cash: number;
      holdings: PortfolioHolding[];
      start_date: string;
      end_date: string;
      benchmark?: string;
    }) =>
      request<PortfolioBacktestResult>("/api/portfolio/backtest", {
        method: "POST",
        body: JSON.stringify(body)
      })
  }
};
