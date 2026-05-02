import AppSidebar from "@/components/AppSidebar";
import PortfolioPlanner from "@/components/PortfolioPlanner";

export default function PortfolioPage() {
  return (
    <div className="min-h-screen grid grid-cols-[72px_1fr]">
      <AppSidebar active="portfolio" />
      <div className="px-6 py-6 space-y-6">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold text-text">投資組合規劃</h1>
          <p className="text-sm text-muted">
            輸入你現有的股票、股數與成本，系統會自動估算權重、未實現損益，並給出簡單的配置建議。
          </p>
        </div>
        <PortfolioPlanner />
      </div>
    </div>
  );
}
