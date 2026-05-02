"use client";
import { useEffect, useMemo, useState } from "react";
import { Loader2, Play } from "lucide-react";
import type { ReactNode } from "react";
import { api, type BacktestResult, type StrategyMeta } from "@/lib/api";
import AppSidebar from "@/components/AppSidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import BacktestResultPanel from "@/components/BacktestResult";

const today = () => new Date().toISOString().slice(0, 10);
const yearsAgo = (n: number) => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d.toISOString().slice(0, 10);
};

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<StrategyMeta[]>([]);
  const [strategyId, setStrategyId] = useState<string>("");
  const [symbol, setSymbol] = useState("0050");
  const [startDate, setStartDate] = useState(yearsAgo(3));
  const [endDate, setEndDate] = useState(today());
  const [params, setParams] = useState<Record<string, number>>({});
  const [commission, setCommission] = useState(0.001425);
  const [slippage, setSlippage] = useState(0.001);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const currentStrategy = useMemo(
    () => strategies.find((s) => s.id === strategyId) ?? null,
    [strategies, strategyId]
  );

  // 載入策略清單
  useEffect(() => {
    api.backtest.strategies().then((list) => {
      setStrategies(list);
      if (list.length > 0) {
        setStrategyId(list[0].id);
        const init: Record<string, number> = {};
        list[0].params.forEach((p) => (init[p.key] = p.default));
        setParams(init);
      }
    }).catch((e) => setError((e as Error).message));
  }, []);

  // 切換策略時重置參數
  useEffect(() => {
    if (!currentStrategy) return;
    const init: Record<string, number> = {};
    currentStrategy.params.forEach((p) => (init[p.key] = p.default));
    setParams(init);
  }, [currentStrategy]);

  const onRun = async () => {
    if (!strategyId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.backtest.run({
        symbol,
        start_date: startDate,
        end_date: endDate,
        strategy: strategyId,
        params,
        commission,
        slippage
      });
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-[72px_1fr]">
      <AppSidebar active="backtest" />
      <div className="min-h-screen p-6">
        <div className="grid lg:grid-cols-[340px_1fr] gap-4">
          {/* 設定面板 */}
          <Card className="h-fit sticky top-6">
            <CardHeader>
              <CardTitle>策略回測</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Field label="股票代碼">
                <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
              </Field>

              <div className="grid grid-cols-2 gap-2">
                <Field label="起始日">
                  <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                </Field>
                <Field label="結束日">
                  <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                </Field>
              </div>

              <Field label="策略">
                <Select value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
                  {strategies.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </Select>
              </Field>

              {currentStrategy?.params.map((p) => (
                <Field key={p.key} label={p.key}>
                  <Input
                    type="number"
                    value={params[p.key] ?? p.default}
                    min={p.min}
                    max={p.max}
                    step={Number.isInteger(p.default) ? 1 : 0.1}
                    onChange={(e) =>
                      setParams((s) => ({ ...s, [p.key]: Number(e.target.value) }))
                    }
                  />
                </Field>
              ))}

              <Field label="手續費（買賣單邊）">
                <Input
                  type="number"
                  step={0.0001}
                  value={commission}
                  onChange={(e) => setCommission(Number(e.target.value))}
                />
              </Field>

              <Field label="滑價">
                <Input
                  type="number"
                  step={0.0001}
                  value={slippage}
                  onChange={(e) => setSlippage(Number(e.target.value))}
                />
              </Field>

              <div className="text-[11px] text-muted leading-relaxed pt-1 border-t border-border/50">
                台股股票費率參考：手續費 0.001425 + 證交稅 0.003。<br />
                台股 ETF（0050/006208）：0.001425 + 0.001。
              </div>

              <Button className="w-full" onClick={onRun} disabled={loading || !strategyId}>
                {loading ? <Loader2 size={16} className="animate-spin mr-1.5" /> : <Play size={14} className="mr-1.5" />}
                {loading ? "執行中…" : "執行回測"}
              </Button>
              {error && <div className="text-xs text-up pt-2">⚠ {error}</div>}
            </CardContent>
          </Card>

          {/* 結果區 */}
          <div>
            {!result && !loading && (
              <Card>
                <CardContent className="py-16 text-center text-muted">
                  <div className="text-3xl mb-3">📈</div>
                  <div className="text-sm">設定左側參數後點「執行回測」</div>
                  <div className="text-xs mt-2 max-w-md mx-auto leading-relaxed">
                    系統會跑完整回測 + Walk-Forward 驗證 + 參數穩健性測試，
                    並用五大門檻（Sharpe / MDD / 勝率 / 交易數 / Profit Factor）打 PASS / FAIL。
                  </div>
                </CardContent>
              </Card>
            )}
            {loading && (
              <Card>
                <CardContent className="py-16 text-center text-muted">
                  <Loader2 size={28} className="animate-spin mx-auto mb-3 text-accent" />
                  <div className="text-sm">執行中：主回測 → Walk-Forward → 穩健性測試…</div>
                  <div className="text-xs mt-1">資料量大時可能需 10~30 秒</div>
                </CardContent>
              </Card>
            )}
            {result && <BacktestResultPanel result={result} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
