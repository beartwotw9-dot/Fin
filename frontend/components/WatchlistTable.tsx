"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Trash2, Plus, RefreshCw } from "lucide-react";
import { api, type Quote } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatNumber, formatPct, priceColor } from "@/lib/utils";

export default function WatchlistTable() {
  const [items, setItems] = useState<Quote[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [newSym, setNewSym] = useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.watchlist.get();
      setItems(r.symbols);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = window.setInterval(load, 60_000);
    return () => window.clearInterval(id);
  }, []);

  const onAdd = async () => {
    const s = newSym.trim().toUpperCase();
    if (!s) return;
    try {
      const r = await api.watchlist.add(s);
      setItems(r.symbols);
      setNewSym("");
      setOpen(false);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const onRemove = async (sym: string) => {
    try {
      const r = await api.watchlist.remove(sym);
      setItems(r.symbols);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <div className="text-sm font-semibold text-text">自選股</div>
          <div className="text-xs text-muted">點代碼跳轉至 K 線；漲紅跌綠 (台股慣例)；每 60 秒自動更新</div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span className="ml-1.5">重新載入</span>
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus size={14} className="mr-1" /> 新增
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>新增自選股</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor="sym">股票代碼</Label>
                  <Input
                    id="sym"
                    placeholder="例：0050、TSLA、^TWII"
                    value={newSym}
                    onChange={(e) => setNewSym(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && onAdd()}
                  />
                  <div className="text-[11px] text-muted">
                    台股填純數字（自動補 .TW），美股填代號，指數加 ^ 前綴
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <DialogClose asChild>
                    <Button variant="ghost" size="sm">取消</Button>
                  </DialogClose>
                  <Button size="sm" onClick={onAdd}>新增</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-muted text-xs uppercase">
            <tr className="border-b border-border">
              <th className="text-left font-medium px-4 py-2">代碼</th>
              <th className="text-right font-medium px-4 py-2">最新價</th>
              <th className="text-right font-medium px-4 py-2">漲跌</th>
              <th className="text-right font-medium px-4 py-2">漲跌%</th>
              <th className="w-12"></th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {items === null
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/50 animate-pulse">
                    <td className="px-4 py-3"><div className="h-3 w-16 bg-surface2 rounded" /></td>
                    <td className="px-4 py-3 text-right"><div className="h-3 w-12 bg-surface2 rounded ml-auto" /></td>
                    <td className="px-4 py-3 text-right"><div className="h-3 w-12 bg-surface2 rounded ml-auto" /></td>
                    <td className="px-4 py-3 text-right"><div className="h-3 w-10 bg-surface2 rounded ml-auto" /></td>
                    <td></td>
                  </tr>
                ))
              : items.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="text-center text-muted py-8">尚未加入任何股票</td>
                </tr>
              )
              : items.map((q) => (
                  <tr key={q.symbol} className="border-b border-border/50 hover:bg-surface2/50 transition">
                    <td className="px-4 py-3">
                      <Link
                        href={`/chart/${encodeURIComponent(q.symbol)}`}
                        className="text-text hover:text-accent transition"
                      >
                        {q.symbol}
                      </Link>
                    </td>
                    <td className={"px-4 py-3 text-right " + priceColor(q.change ?? 0)}>
                      {formatNumber(q.price)}
                    </td>
                    <td className={"px-4 py-3 text-right " + priceColor(q.change ?? 0)}>
                      {q.change === null || q.change === undefined ? "—" : (q.change >= 0 ? "+" : "") + Number(q.change).toFixed(2)}
                    </td>
                    <td className={"px-4 py-3 text-right " + priceColor(q.change_pct ?? 0)}>
                      {formatPct(q.change_pct)}
                    </td>
                    <td className="px-2 py-3 text-right">
                      <button
                        onClick={() => onRemove(q.symbol)}
                        className="text-muted hover:text-up transition p-1"
                        title="移除"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      {error && (
        <div className="px-4 py-2 text-xs text-up border-t border-border">⚠ {error}</div>
      )}
    </div>
  );
}
