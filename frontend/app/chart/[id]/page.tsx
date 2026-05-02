"use client";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid
} from "recharts";
import { api, type Candle, type Quote } from "@/lib/api";
import Chart from "@/components/Chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatPct, priceColor } from "@/lib/utils";

const RANGES = [
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "6M", days: 180 },
  { label: "1Y", days: 365 },
  { label: "3Y", days: 365 * 3 }
] as const;

type RangeKey = (typeof RANGES)[number]["label"];

export default function ChartPage() {
  const params = useParams<{ id: string }>();
  const symbol = (params?.id ?? "").toString().toUpperCase();
  const [range, setRange] = useState<RangeKey>("1Y");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [inst, setInst] = useState<{ date: string; name: string; diff: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dateRange = useMemo(() => {
    const days = RANGES.find((r) => r.label === range)?.days ?? 365;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days);
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    return { start: fmt(start), end: fmt(end) };
  }, [range]);

  // 取 K 線
  useEffect(() => {
    let cancel = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await api.stock.daily(symbol, dateRange.start, dateRange.end);
        if (!cancel) setCandles(r.data);
      } catch (e) {
        if (!cancel) setError((e as Error).message);
      } finally {
        if (!cancel) setLoading(false);
      }
    };
    load();
    return () => {
      cancel = true;
    };
  }, [symbol, dateRange.start, dateRange.end]);

  // 取即時報價
  useEffect(() => {
    let cancel = false;
    const load = async () => {
      try {
        const nextQuote = await api.stock.realtime(symbol);
        if (!cancel) setQuote(nextQuote);
      } catch {
        if (!cancel) setQuote(null);
      }
    };
    load();
    const id = window.setInterval(load, 60_000);
    return () => {
      cancel = true;
      window.clearInterval(id);
    };
  }, [symbol]);

  // 三大法人（台股才回真實資料）
  useEffect(() => {
    api.stock.institutional(symbol).then((r) => {
      if (!r.available) return setInst([]);
      const recent = r.data.slice(-5).map((d) => ({
        date: d.date,
        name: d.name,
        diff: Number((d.diff / 1000).toFixed(0))
      }));
      setInst(recent);
    }).catch(() => setInst([]));
  }, [symbol]);

  const stats = useMemo(() => {
    if (candles.length === 0) return null;
    const highs = candles.map((c) => c.high);
    const lows = candles.map((c) => c.low);
    const vols = candles.map((c) => c.volume);
    return {
      max52: Math.max(...highs),
      min52: Math.min(...lows),
      avgVol: vols.reduce((a, b) => a + b, 0) / vols.length
    };
  }, [candles]);

  const onAddWatch = async () => {
    setAdding(true);
    try {
      await api.watchlist.add(symbol);
      alert(`已加入自選股：${symbol}`);
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-surface px-6 py-4 flex items-center justify-between">
        <div className="flex items-baseline gap-4">
          <h1 className="text-2xl font-semibold font-mono text-text">{symbol}</h1>
          <div className={"font-mono text-lg " + priceColor(quote?.change ?? 0)}>
            {formatNumber(quote?.price ?? null)}
          </div>
          <div className={"font-mono text-sm " + priceColor(quote?.change ?? 0)}>
            {quote?.change == null ? "—" : (quote.change >= 0 ? "+" : "") + Number(quote.change).toFixed(2)}{" "}
            ({formatPct(quote?.change_pct ?? null)})
          </div>
        </div>
        <Button size="sm" onClick={onAddWatch} disabled={adding}>+ 加入自選股</Button>
      </div>

      <div className="flex-1 grid lg:grid-cols-[1fr_360px] gap-4 p-6">
        {/* Chart 區 */}
        <div className="space-y-3 min-w-0">
          <div className="flex items-center gap-2">
            {RANGES.map((r) => (
              <Button
                key={r.label}
                size="sm"
                variant={r.label === range ? "default" : "outline"}
                onClick={() => setRange(r.label)}
              >
                {r.label}
              </Button>
            ))}
            {loading && <span className="text-xs text-muted">載入中…</span>}
            {error && <span className="text-xs text-up">⚠ {error}</span>}
          </div>
          <Card className="overflow-hidden">
            <Chart data={candles} height={520} />
          </Card>
        </div>

        {/* 資訊區 */}
        <div className="space-y-3">
          <Card>
            <CardHeader><CardTitle>基本資訊</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm font-mono">
              <Row label="期間最高" value={stats ? formatNumber(stats.max52) : "—"} />
              <Row label="期間最低" value={stats ? formatNumber(stats.min52) : "—"} />
              <Row label="平均成交量" value={stats ? formatNumber(stats.avgVol, 0) : "—"} />
              <Row label="幣別" value={quote?.currency ?? "—"} />
            </CardContent>
          </Card>

          {inst.length > 0 && (
            <Card>
              <CardHeader><CardTitle>三大法人 (近 5 日，千股)</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={inst}>
                    <CartesianGrid stroke="#2a3350" strokeDasharray="2 4" />
                    <XAxis dataKey="date" stroke="#6b7a99" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#6b7a99" tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: "#161b27", border: "1px solid #2a3350", fontSize: 12 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="diff" name="買賣超" fill="#4f8ef7" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
      <span className="text-muted text-xs uppercase tracking-wider">{label}</span>
      <span className="text-text">{value}</span>
    </div>
  );
}
