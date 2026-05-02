import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Financial Dashboard",
  description: "個人金融儀表板 — 台股 / 美股 / 回測"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body className="min-h-screen bg-bg text-text">{children}</body>
    </html>
  );
}
