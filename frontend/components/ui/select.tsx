"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/** 簡化版原生 select，深色 UI 風格. */
export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-9 w-full rounded-md border border-border bg-surface2 px-3 text-sm text-text",
      "focus:outline-none focus:ring-2 focus:ring-accent",
      className
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
