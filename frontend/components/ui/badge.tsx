import * as React from "react";
import { cn } from "@/lib/utils";

type Tone = "default" | "success" | "warning" | "danger" | "info";

export function Badge({
  className,
  tone = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  const tones: Record<Tone, string> = {
    default: "bg-surface2 text-text border-border",
    success: "bg-down/15 text-down border-down/40",
    warning: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    danger: "bg-up/15 text-up border-up/40",
    info: "bg-accent2/15 text-accent2 border-accent2/40"
  };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
