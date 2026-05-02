import Link from "next/link";
import { ArrowRight, PieChart } from "lucide-react";
import AppSidebar from "@/components/AppSidebar";
import MarketOverviewPanel from "@/components/MarketOverviewPanel";
import WatchlistTable from "@/components/WatchlistTable";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  return (
    <div className="min-h-screen grid grid-cols-[72px_1fr]">
      <AppSidebar active="home" />
      <div className="flex min-h-screen flex-col">
        <MarketOverviewPanel />
        <div className="px-6 py-6 space-y-6 max-w-7xl w-full">
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-xl font-semibold text-text">總覽</h1>
              <p className="text-sm text-muted">自選股即時報價、指數動態、回測入口</p>
            </div>
          </div>
          <WatchlistTable />
          <div className="rounded-lg border border-border bg-surface p-5 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-text">投資組合規劃</div>
              <div className="text-xs text-muted mt-1">
                輸入你的持股與股數，快速看權重、損益、核心 / 衛星配置與再平衡建議
              </div>
            </div>
            <Link href="/portfolio">
              <Button variant="outline">
                <PieChart size={16} className="mr-1" />
                前往規劃
              </Button>
            </Link>
          </div>
          <div className="rounded-lg border border-border bg-surface p-5 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-text">策略回測</div>
              <div className="text-xs text-muted mt-1">
                支援 4 種策略 + 5 大篩選門檻 + Walk-Forward 防過擬合驗證
              </div>
            </div>
            <Link href="/backtest">
              <Button>
                開始回測 <ArrowRight size={16} className="ml-1" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
