import Link from "next/link";
import { BarChart3, LineChart, House, PieChart } from "lucide-react";

type Props = {
  active: "home" | "backtest" | "portfolio";
};

const items = [
  { key: "home", href: "/", label: "總覽", icon: House },
  { key: "backtest", href: "/backtest", label: "回測", icon: BarChart3 },
  { key: "portfolio", href: "/portfolio", label: "組合", icon: PieChart },
];

export default function AppSidebar({ active }: Props) {
  return (
    <aside className="flex flex-col items-center gap-5 border-r border-border bg-black/15 py-8">
      <Link
        href="/"
        className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent/15 text-accent"
        aria-label="Financial Dashboard Home"
      >
        FN
      </Link>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = active === item.key;
        return (
          <Link
            key={item.key}
            href={item.href}
            aria-label={item.label}
            title={item.label}
            className={`flex h-11 w-11 items-center justify-center rounded-2xl border transition ${
              isActive
                ? "border-accent/40 bg-accent/15 text-accent"
                : "border-transparent bg-surface/40 text-muted hover:border-border hover:text-text"
            }`}
          >
            <Icon className="h-5 w-5" />
          </Link>
        );
      })}
      <Link
        href="/chart/QQQ"
        aria-label="K線"
        title="K 線"
        className="mt-2 flex h-11 w-11 items-center justify-center rounded-2xl border border-transparent bg-surface/40 text-muted transition hover:border-border hover:text-text"
      >
        <LineChart className="h-5 w-5" />
      </Link>
    </aside>
  );
}
