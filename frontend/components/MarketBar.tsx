"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, Clock3, RefreshCw } from "lucide-react";
import { api, type MarketOverview, type Quote } from "@/lib/api";
import { formatNumber, formatPct, priceColor } from "@/lib/utils";

const REFRESH_MS = 60_000;

const LABELS: Record<string, string> = {
  "^TWII": "台股加權",
  "^GSPC": "S&P 500",
  "^IXIC": "NASDAQ",
  "^DJI": "Dow Jones",
  VT: "全市場",
  VOO: "美股大盤",
  QQQ: "科技權重",
  IWM: "小型股",
  TLT: "長天期美債",
  GLD: "黃金",
  UUP: "美元",
  USO: "原油",
};

function MarketTile({ quote, compact = false }: { quote: Quote; compact?: boolean }) {
  return (
    <div
      className={`rounded-2xl border border-border bg-surface2/80 ${
        compact ? "px-4 py-3" : "px-4 py-4"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-muted">{quote.symbol}</div>
          <div className="mt-1 text-xs text-muted">{LABELS[quote.symbol] ?? quote.symbol}</div>
        </div>
        <div className={`text-right font-mono ${compact ? "text-sm" : "text-base"} font-semibold`}>
          <div className="text-text">{formatNumber(quote.price)}</div>
          <div className={`mt-1 text-xs ${priceColor(quote.change ?? quote.change_pct ?? null)}`}>
            {quote.change === null || quote.change === undefined
              ? "—"
              : `${quote.change >= 0 ? "+" : ""}${formatNumber(quote.change)}`}
          </div>
        </div>
      </div>
      <div className={`mt-3 flex items-center justify-between ${compact ? "text-[11px]" : "text-xs"}`}>
        <span className={priceColor(quote.change_pct ?? quote.change ?? null)}>{formatPct(quote.change_pct)}</span>
        <span className="text-muted">{quote.currency ?? "—"}</span>
      </div>
    </div>
  );
}

export default function MarketBar() {
  const [data, setData] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<string | null>(null);

  const load = async () => {
    try {
      const overview = await api.market.overview();
      setData(overview);
      setError(null);
      setLastFetchedAt(new Date().toLocaleTimeString("zh-TW", { hour12: false }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(id);
  }, []);

  const featured = useMemo<Quote[]>(
    () =>
      data?.groups
        .flatMap((group) => group.items)
        .filter((quote) => ["^TWII", "VT", "QQQ", "GLD"].includes(quote.symbol)) ?? [],
    [data]
  );

  const featuredSlots: Array<Quote | null> = featured.length ? featured : Array.from({ length: 4 }, () => null);

  return (
    <section className="border-b border-border bg-surface">
      <div className="px-6 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-text">
              <Activity className="h-4 w-4 text-accent" />
              市場資訊
            </div>
            <div className="mt-1 text-xs text-muted">
              主要指數、核心 ETF 與宏觀資產，每 60 秒自動更新
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="inline-flex items-center gap-1.5">
              <Clock3 className="h-3.5 w-3.5" />
              {lastFetchedAt ? `上次更新 ${lastFetchedAt}` : "正在載入"}
            </span>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 transition hover:border-accent/40 hover:text-text"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              立即更新
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {featuredSlots.map((quote, index) =>
            quote ? (
              <MarketTile key={quote.symbol} quote={quote} compact />
            ) : (
              <div
                key={index}
                className="h-[104px] animate-pulse rounded-2xl border border-border bg-surface2/70"
              />
            )
          )}
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {(data?.groups ?? []).map((group) => (
            <div key={group.id} className="rounded-2xl border border-border bg-black/10 p-4">
              <div className="mb-3">
                <div className="text-sm font-semibold text-text">{group.title}</div>
                <div className="mt-1 text-xs text-muted">{group.description}</div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                {group.items.map((quote) => (
                  <MarketTile key={`${group.id}-${quote.symbol}`} quote={quote} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-up/30 bg-up/5 px-3 py-2 text-xs text-up">
            市場資訊更新失敗：{error}
          </div>
        )}
      </div>
    </section>
  );
}
