"use client";
import { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Area,
  ComposedChart
} from "recharts";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { BacktestResult } from "@/lib/api";
import { formatNumber, formatPct } from "@/lib/utils";

export default function BacktestResultPanel({ result }: { result: BacktestResult }) {
  const { metrics, walk_forward: wf, robustness, filter, equity_curve, drawdown_curve, trades } = result;

  const merged = equity_curve.map((p, i) => ({
    date: p.date,
    equity: p.value,
    drawdown: drawdown_curve[i]?.value ?? 0
  }));

  return (
    <div className="space-y-4">
      {/* 篩選燈號 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>策略篩選</CardTitle>
          {filter.passed ? (
            <Badge tone="success" className="text-sm px-3 py-1">PASSED ✓ ({filter.score}/{filter.max_score})</Badge>
          ) : (
            <Badge tone="danger" className="text-sm px-3 py-1">FAILED ✗ ({filter.score}/{filter.max_score})</Badge>
          )}
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <tbody>
              {filter.details.map((d) => (
                <tr key={d.metric} className="border-b border-border/50 last:border-0">
                  <td className="px-4 py-2 text-muted">{d.metric}</td>
                  <td className="px-4 py-2 text-right font-mono">{formatNumber(d.value, 3)}</td>
                  <td className="px-4 py-2 text-right text-xs text-muted font-mono">{d.threshold}</td>
                  <td className="px-4 py-2 text-right">
                    {d.passed ? <span className="text-down">✓</span> : <span className="text-up">✗</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Walk-Forward */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Walk-Forward 驗證</CardTitle>
          <VerdictBadge verdict={wf.verdict} />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="In-Sample 報酬" value={formatPct(wf.is_return)} />
            <Stat label="Out-of-Sample 報酬" value={formatPct(wf.oos_return)} />
            <Stat
              label="WF Efficiency"
              value={formatNumber(wf.wf_efficiency, 3)}
              hint={wf.wf_efficiency >= 0.7 ? ">= 0.7 強健" : wf.wf_efficiency >= 0.3 ? "0.3 ~ 0.7 邊界" : "< 0.3 高度過擬合"}
            />
          </div>
          <div className="mt-3 text-xs text-muted">
            最佳參數：<span className="font-mono text-text">{JSON.stringify(wf.best_params)}</span>
          </div>
          <div className="mt-2 text-xs text-muted">
            穩健性：±10% 三組 Sharpe = {robustness.sharpes.map((s) => formatNumber(s, 2)).join(" / ")}
            ，標準差 = {formatNumber(robustness.sharpe_std, 3)}（{robustness.stable ? "穩健" : "敏感"}）
          </div>
        </CardContent>
      </Card>

      {/* 績效指標 grid */}
      <Card>
        <CardHeader><CardTitle>績效指標</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="總報酬率" value={formatPct(metrics.return_pct)} />
            <Stat label="年化報酬" value={formatPct(metrics.return_ann)} />
            <Stat label="Sharpe" value={formatNumber(metrics.sharpe, 3)} />
            <Stat label="Sortino" value={formatNumber(metrics.sortino, 3)} />
            <Stat label="Calmar" value={formatNumber(metrics.calmar, 3)} />
            <Stat label="Max Drawdown" value={formatPct(metrics.max_drawdown)} />
            <Stat label="勝率" value={formatPct(metrics.win_rate)} />
            <Stat label="Profit Factor" value={formatNumber(metrics.profit_factor, 3)} />
            <Stat label="交易次數" value={String(metrics.total_trades)} />
            <Stat label="平均單筆" value={formatPct(metrics.avg_trade_pct)} />
            <Stat label="最佳單筆" value={formatPct(metrics.best_trade_pct)} />
            <Stat label="最差單筆" value={formatPct(metrics.worst_trade_pct)} />
          </div>
        </CardContent>
      </Card>

      {/* 權益曲線 + 回撤 */}
      <Card>
        <CardHeader><CardTitle>權益曲線（疊加回撤）</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={merged} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#2a3350" strokeDasharray="2 4" />
              <XAxis dataKey="date" stroke="#6b7a99" tick={{ fontSize: 11 }} minTickGap={48} />
              <YAxis yAxisId="left" stroke="#6b7a99" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" stroke="#6b7a99" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#161b27", border: "1px solid #2a3350", borderRadius: 6, fontSize: 12 }}
              />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="drawdown"
                stroke="#f0406066"
                fill="#f0406022"
                isAnimationActive={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="equity"
                stroke="#00d4aa"
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 交易紀錄 */}
      <TradesTable trades={trades} />
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded border border-border bg-surface2 p-3">
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div className="font-mono text-base text-text mt-0.5">{value}</div>
      {hint ? <div className="text-[10px] text-muted mt-0.5">{hint}</div> : null}
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  if (verdict === "ROBUST") return <Badge tone="success">ROBUST</Badge>;
  if (verdict === "MARGINAL") return <Badge tone="warning">MARGINAL</Badge>;
  if (verdict === "OVERFIT") return <Badge tone="danger">OVERFIT</Badge>;
  return <Badge>—</Badge>;
}

function TradesTable({ trades }: { trades: BacktestResult["trades"] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between p-4 border-b border-border hover:bg-surface2 transition"
      >
        <CardTitle>交易紀錄（{trades.length} 筆）</CardTitle>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open && (
        <CardContent className="p-0">
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-muted text-xs uppercase sticky top-0 bg-surface">
                <tr className="border-b border-border">
                  <th className="text-left font-medium px-4 py-2">進場</th>
                  <th className="text-left font-medium px-4 py-2">出場</th>
                  <th className="text-right font-medium px-4 py-2">天數</th>
                  <th className="text-right font-medium px-4 py-2">損益%</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {trades.map((t, i) => (
                  <tr key={i} className="border-b border-border/40">
                    <td className="px-4 py-1.5">{t.entry_date}</td>
                    <td className="px-4 py-1.5">{t.exit_date}</td>
                    <td className="px-4 py-1.5 text-right">{t.duration_days ?? "—"}</td>
                    <td className={"px-4 py-1.5 text-right " + (t.pnl_pct >= 0 ? "text-up" : "text-down")}>
                      {formatPct(t.pnl_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
