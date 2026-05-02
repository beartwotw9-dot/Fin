import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number | null | undefined, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

export function formatPct(n: number | null | undefined, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const v = Number(n);
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

/** 台股慣例：漲紅 / 跌綠. */
export function priceColor(change: number | null | undefined): string {
  if (change === null || change === undefined || Number.isNaN(change)) return "text-muted";
  if (change > 0) return "text-up";
  if (change < 0) return "text-down";
  return "text-text";
}
