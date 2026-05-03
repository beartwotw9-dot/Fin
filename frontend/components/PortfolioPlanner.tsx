"use client";

import { useMemo, useState } from "react";
import { Plus, Sparkles, Trash2, History, Target } from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, type PortfolioAnalysis, type PortfolioBacktestResult } from "@/lib/api";
import { formatNumber, formatPct } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Row = {
  symbol: string;
  shares: string;
  avg_cost: string;
};

const defaultRows: Row[] = [
  { symbol: "0050", shares: "387", avg_cost: "76.33" },
  { symbol: "00931B", shares: "100", avg_cost: "15.12" },
  { symbol: "1519", shares: "2", avg_cost: "911.5" },
  { symbol: "QQQ", shares: "0.20654", avg_cost: "629.902198" },
  { symbol: "VOO", shares: "1.45486", avg_cost: "592.221932" },
  { symbol: "VT", shares: "2.22789", avg_cost: "143.723433" },
];

const today = () => new Date().toISOString().slice(0, 10);
const yearsAgo = (n: number) => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d.toISOString().slice(0, 10);
};

export default function PortfolioPlanner() {
  const [rows, setRows] = useState<Row[]>(defaultRows);
  const [cash, setCash] = useState("0");
  const [benchmark, setBenchmark] = useState("");
  const [startDate, setStartDate] = useState(yearsAgo(3));
  const [endDate, setEndDate] = useState(today());
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [backtest, setBacktest] = useState<PortfolioBacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const payload = useMemo(
    () => ({
      cash: Number(cash || 0),
      holdings: rows
        .filter((row) => row.symbol.trim() && Number(row.shares) > 0)
        .map((row) => ({
          symbol: row.symbol.trim().toUpperCase(),
          shares: Number(row.shares),
          avg_cost: row.avg_cost === "" ? null : Number(row.avg_cost),
        })),
    }),
    [cash, rows]
  );

  const runAnalysis = async () => {
    setLoadingAnalyze(true);
    setError(null);
    try {
      const response = await api.portfolio.analyze(payload);
      setAnalysis(response);
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : "分析失敗");
    } finally {
      setLoadingAnalyze(false);
    }
  };

  const runBacktest = async () => {
    setLoadingBacktest(true);
    setError(null);
    try {
      const response = await api.portfolio.backtest({
        ...payload,
        start_date: startDate,
        end_date: endDate,
        benchmark: benchmark.trim() || undefined,
      });
      if (response.error) {
        setError(response.error);
      } else {
        setBacktest(response);
      }
    } catch (backtestError) {
      setError(backtestError instanceof Error ? backtestError.message : "回測失敗");
    } finally {
      setLoadingBacktest(false);
    }
  };

  const updateRow = (index: number, key: keyof Row, value: string) => {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, [key]: value } : row)));
  };

  const addRow = () => {
    setRows((current) => [...current, { symbol: "", shares: "", avg_cost: "" }]);
  };

  const removeRow = (index: number) => {
    setRows((current) => current.filter((_, rowIndex) => rowIndex !== index));
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle>投資組合輸入</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="cash">現金部位</Label>
            <Input id="cash" type="number" value={cash} onChange={(e) => setCash(e.target.value)} />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label htmlFor="start">回測起始日</Label>
              <Input id="start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="end">回測結束日</Label>
              <Input id="end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="benchmark">比較基準（可留空）</Label>
            <Input
              id="benchmark"
              value={benchmark}
              onChange={(e) => setBenchmark(e.target.value)}
              placeholder="例如 VT、0050"
            />
          </div>

          <div className="space-y-3">
            {rows.map((row, index) => (
              <div key={index} className="space-y-2 rounded-lg border border-border bg-surface2 p-3">
                <div className="grid grid-cols-[1.2fr_1fr_1fr_auto] items-end gap-2">
                  <div className="space-y-1">
                    <Label>代碼</Label>
                    <Input value={row.symbol} onChange={(e) => updateRow(index, "symbol", e.target.value)} placeholder="VT" />
                  </div>
                  <div className="space-y-1">
                    <Label>股數</Label>
                    <Input type="number" value={row.shares} onChange={(e) => updateRow(index, "shares", e.target.value)} placeholder="10" />
                  </div>
                  <div className="space-y-1">
                    <Label>成本</Label>
                    <Input type="number" value={row.avg_cost} onChange={(e) => updateRow(index, "avg_cost", e.target.value)} placeholder="145" />
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => removeRow(index)} aria-label="remove">
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={addRow}>
              <Plus size={14} className="mr-1" />
              新增持股
            </Button>
            <Button variant="outline" onClick={runAnalysis} disabled={loadingAnalyze}>
              <Sparkles size={14} className="mr-1" />
              {loadingAnalyze ? "分析中…" : "分析組合"}
            </Button>
            <Button onClick={runBacktest} disabled={loadingBacktest}>
              <History size={14} className="mr-1" />
              {loadingBacktest ? "回測中…" : "組合回測"}
            </Button>
          </div>

          {error && <div className="text-xs text-up">{error}</div>}
          <div className="text-[11px] leading-relaxed text-muted">
            回測假設：以你目前輸入的股數回推歷史，期間不加減碼。建議區會直接給出較可執行的買賣金額與方向。
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {!analysis && !backtest ? (
          <Card>
            <CardContent className="py-16 text-center text-muted">
              輸入持股、股數與成本後，這裡會顯示實際配置分析、回測結果與下一步調整建議。
            </CardContent>
          </Card>
        ) : (
          <>
            {analysis && (
              <>
                <div className="grid gap-3 md:grid-cols-4">
                  <StatCard label="總市值" value={formatNumber(analysis.summary.total_market_value)} />
                  <StatCard label="含現金總資產" value={formatNumber(analysis.summary.portfolio_value)} />
                  <StatCard label="未實現損益" value={formatNumber(analysis.summary.unrealized_pnl)} />
                  <StatCard label="現金比重" value={formatPct(analysis.summary.cash_weight)} />
                </div>

                <Card>
                  <CardHeader><CardTitle>配置摘要</CardTitle></CardHeader>
                  <CardContent className="grid gap-3 md:grid-cols-3">
                    <StatCard label="核心 ETF" value={formatPct(analysis.allocation.core)} small />
                    <StatCard label="衛星部位" value={formatPct(analysis.allocation.satellite)} small />
                    <StatCard label="台股曝險" value={formatPct(analysis.allocation.taiwan)} small />
                    <StatCard label="美股曝險" value={formatPct(analysis.allocation.us)} small />
                    <StatCard label="債券" value={formatPct(analysis.allocation.bond)} small />
                    <StatCard label="黃金" value={formatPct(analysis.allocation.gold)} small />
                  </CardContent>
                </Card>

                <ActionPlanCard title="可執行建議" items={analysis.action_plan} />
                <BudgetPlansCard plans={analysis.budget_plans} />
                <RecommendationCard items={analysis.recommended_products} />

                <Card>
                  <CardHeader><CardTitle>規劃觀察</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    {analysis.risk_flags.length > 0 && (
                      <div className="space-y-2">
                        {analysis.risk_flags.map((flag, index) => (
                          <div key={index} className="rounded-lg border border-border bg-surface2 p-3">
                            <div className="flex items-center gap-2">
                              <Badge tone={flag.level === "high" ? "danger" : flag.level === "medium" ? "warning" : "info"}>
                                {flag.level.toUpperCase()}
                              </Badge>
                              <div className="font-medium text-text">{flag.title}</div>
                            </div>
                            <div className="mt-2 text-sm text-muted">{flag.message}</div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="space-y-2">
                      {analysis.suggestions.map((item, index) => (
                        <div key={index} className="rounded-lg border border-border bg-surface2 p-3">
                          <div className="font-medium text-text">{item.title}</div>
                          <div className="mt-1 text-sm text-muted">{item.detail}</div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader><CardTitle>持股明細</CardTitle></CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="text-xs uppercase text-muted">
                          <tr className="border-b border-border">
                            <th className="px-4 py-2 text-left font-medium">代碼</th>
                            <th className="px-4 py-2 text-right font-medium">價格</th>
                            <th className="px-4 py-2 text-right font-medium">市值</th>
                            <th className="px-4 py-2 text-right font-medium">權重</th>
                            <th className="px-4 py-2 text-right font-medium">損益</th>
                          </tr>
                        </thead>
                        <tbody className="font-mono">
                          {analysis.holdings.map((holding) => (
                            <tr key={holding.symbol} className="border-b border-border/40">
                              <td className="px-4 py-2">{holding.symbol}</td>
                              <td className="px-4 py-2 text-right">{formatNumber(holding.price)}</td>
                              <td className="px-4 py-2 text-right">{formatNumber(holding.market_value)}</td>
                              <td className="px-4 py-2 text-right">{formatPct(holding.weight_pct)}</td>
                              <td className={`px-4 py-2 text-right ${holding.unrealized_pnl !== null && holding.unrealized_pnl >= 0 ? "text-up" : "text-down"}`}>
                                {holding.unrealized_pnl === null ? "—" : `${formatNumber(holding.unrealized_pnl)} / ${formatPct(holding.unrealized_pnl_pct)}`}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {backtest && (
              <>
                <div className="grid gap-3 md:grid-cols-4">
                  <StatCard label="組合報酬" value={formatPct(backtest.metrics.return_pct)} />
                  <StatCard label="年化報酬" value={formatPct(backtest.metrics.annual_return)} />
                  <StatCard label="最大回撤" value={formatPct(backtest.metrics.max_drawdown)} />
                  <StatCard label="對基準 Alpha" value={formatPct(backtest.benchmark.alpha_pct)} />
                </div>

                <Card>
                  <CardHeader><CardTitle>回測摘要</CardTitle></CardHeader>
                  <CardContent className="grid gap-3 md:grid-cols-3">
                    <StatCard label="Sharpe" value={formatNumber(backtest.metrics.sharpe)} small />
                    <StatCard label="年化波動" value={formatPct(backtest.metrics.annual_volatility)} small />
                    <StatCard label={`基準 (${backtest.benchmark.symbol})`} value={formatPct(backtest.benchmark.return_pct)} small />
                    <StatCard label="期初資產" value={formatNumber(backtest.summary.initial_value)} small />
                    <StatCard label="期末資產" value={formatNumber(backtest.summary.final_value)} small />
                    <StatCard label="相關性" value={formatNumber(backtest.benchmark.correlation)} small />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader><CardTitle>組合回測曲線</CardTitle></CardHeader>
                  <CardContent>
                    <div className="mb-3 text-xs text-muted">
                      {backtest.period.start} 至 {backtest.period.end}。{backtest.assumption}
                    </div>
                    <ResponsiveContainer width="100%" height={320}>
                      <LineChart data={backtest.equity_curve.map((point, index) => ({
                        date: point.date,
                        equity: point.value,
                        drawdown: backtest.drawdown_curve[index]?.value ?? 0,
                      }))}>
                        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                        <XAxis dataKey="date" tick={{ fill: "#6b7a99", fontSize: 11 }} />
                        <YAxis yAxisId="left" tick={{ fill: "#6b7a99", fontSize: 11 }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fill: "#6b7a99", fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ background: "#161b27", border: "1px solid #2a3350" }}
                          labelStyle={{ color: "#e8edf5" }}
                        />
                        <Legend />
                        <Line yAxisId="left" type="monotone" dataKey="equity" stroke="#00d4aa" dot={false} strokeWidth={2} name="組合淨值" />
                        <Line yAxisId="right" type="monotone" dataKey="drawdown" stroke="#f59e0b" dot={false} strokeWidth={1.5} name="回撤 (%)" />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <ActionPlanCard title="依回測調整的下一步" items={backtest.action_plan} />
                <BudgetPlansCard plans={backtest.budget_plans} />

                <FutureOutlookCard outlook={backtest.future_outlook} />
                <RecommendationCard items={backtest.recommended_products} />

                <Card>
                  <CardHeader><CardTitle>回測後建議</CardTitle></CardHeader>
                  <CardContent className="space-y-2">
                    {backtest.advice.map((item, index) => (
                      <div key={index} className="rounded-lg border border-border bg-surface2 p-3">
                        <div className="flex items-center gap-2 font-medium text-text">
                          <Target size={14} className="text-accent" />
                          {item.title}
                        </div>
                        <div className="mt-1 text-sm text-muted">{item.detail}</div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, small = false }: { label: string; value: string; small?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div className={`${small ? "text-base" : "text-lg"} mt-1 font-mono text-text`}>{value}</div>
    </div>
  );
}

function ActionPlanCard({
  title,
  items,
}: {
  title: string;
  items: Array<{
    priority: string;
    action: string;
    symbol: string | null;
    amount: number;
    estimated_shares: number | null;
    reason: string;
  }>;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {items.map((item, index) => (
          <div key={index} className="rounded-lg border border-border bg-surface2 p-3">
            <div className="flex items-center gap-2">
              <Badge tone={item.priority === "high" ? "danger" : item.priority === "medium" ? "warning" : "info"}>
                {item.priority.toUpperCase()}
              </Badge>
              <div className="font-medium text-text">{formatActionTitle(item.action, item.symbol)}</div>
            </div>
            <div className="mt-2 text-sm leading-relaxed text-muted">{item.reason}</div>
            {item.amount > 0 && (
              <div className="mt-2 font-mono text-sm text-text">
                約 {formatNumber(item.amount)}
                {item.estimated_shares ? ` / 約 ${formatNumber(item.estimated_shares, 4)} 股` : ""}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function BudgetPlansCard({
  plans,
}: {
  plans: Array<{
    budget: number;
    summary: string;
    items: Array<{
      symbol: string;
      amount: number;
      estimated_shares: number | null;
      reason: string;
    }>;
  }>;
}) {
  if (!plans.length) return null;

  return (
    <Card>
      <CardHeader><CardTitle>如果你現在想再投入一筆錢</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {plans.map((plan) => (
          <div key={plan.budget} className="rounded-lg border border-border bg-surface2 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="info">預算 {formatNumber(plan.budget)}</Badge>
              <div className="text-sm text-text">{plan.summary}</div>
            </div>
            <div className="mt-3 space-y-2">
              {plan.items.map((item, index) => (
                <div key={`${plan.budget}-${item.symbol}-${index}`} className="rounded-md border border-border/70 bg-surface px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-medium text-text">
                      {item.symbol === "CASH" ? "先保留現金" : `優先買進 ${item.symbol}`}
                    </div>
                    <div className="font-mono text-sm text-accent">
                      {formatNumber(item.amount)}
                      {item.estimated_shares ? ` / 約 ${formatNumber(item.estimated_shares, 4)} 股` : ""}
                    </div>
                  </div>
                  <div className="mt-1 text-sm text-muted">{item.reason}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

const ACTION_LABELS: Record<string, string> = {
  buy: "建議買進",
  sell: "建議減碼",
  hold_cash: "保留現金",
  hold: "維持配置",
};

function formatActionTitle(action: string, symbol: string | null) {
  if (action === "buy") return `下一筆資金優先補 ${symbol}`;
  if (action === "sell") return `先分批減碼 ${symbol}`;
  if (action === "hold_cash") return "先保留現金，不急著全數投入";
  if (action === "hold") return "目前先維持配置";
  return `${ACTION_LABELS[action] ?? action}${symbol ? ` · ${symbol}` : ""}`;
}

function FutureOutlookCard({
  outlook,
}: {
  outlook: PortfolioBacktestResult["future_outlook"];
}) {
  return (
    <Card>
      <CardHeader><CardTitle>未來情境預估</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={outlook.signal === "BULLISH" ? "info" : outlook.signal === "BEARISH" ? "danger" : "warning"}>
            {outlook.signal}
          </Badge>
          <Badge tone="info">信心 {outlook.confidence}</Badge>
          <div className="text-xs text-muted">比較基準：{outlook.benchmark}</div>
        </div>
        <div className="text-sm text-text">{outlook.summary}</div>
        <div className="grid gap-3 md:grid-cols-3">
          {outlook.scenarios.map((scenario) => (
            <div key={scenario.name} className="rounded-lg border border-border bg-surface2 p-3">
              <div className="text-sm font-medium text-text">{scenario.name}</div>
              <div className="mt-1 font-mono text-lg text-accent">
                {formatPct(scenario.expected_return_pct)}
              </div>
              <div className="text-[11px] text-muted">{scenario.horizon}</div>
              <div className="mt-2 text-sm text-muted">{scenario.message}</div>
            </div>
          ))}
        </div>
        <div className="rounded-lg border border-border bg-surface2 p-3">
          <div className="mb-2 text-sm font-medium text-text">判斷依據</div>
          <div className="flex flex-wrap gap-2">
            {outlook.drivers.map((driver) => (
              <span key={driver} className="rounded-full border border-border px-2 py-1 text-xs text-muted">
                {driver}
              </span>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RecommendationCard({
  items,
}: {
  items: Array<{
    symbol: string;
    stance: string;
    title: string;
    reason: string;
  }>;
}) {
  if (!items.length) return null;

  return (
    <Card>
      <CardHeader><CardTitle>推薦商品與原因</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {items.map((item, index) => (
          <div key={`${item.symbol}-${index}`} className="rounded-lg border border-border bg-surface2 p-3">
            <div className="flex items-center gap-2">
              <Badge tone={item.stance === "RECOMMEND" ? "info" : item.stance === "AVOID" ? "danger" : "warning"}>
                {item.stance}
              </Badge>
              <div className="font-medium text-text">
                {item.title}
                {item.symbol ? ` · ${item.symbol}` : ""}
              </div>
            </div>
            <div className="mt-2 text-sm text-muted">{item.reason}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
