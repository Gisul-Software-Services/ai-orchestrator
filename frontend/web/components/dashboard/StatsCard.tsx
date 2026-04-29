"use client";

import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

type Color = "emerald" | "red" | "amber" | "cyan" | "violet" | "zinc";

const colorMap: Record<Color, { dot: string; border: string; glow: string; text: string }> = {
  emerald: {
    dot: "dot-emerald",
    border: "border-emerald-500/20",
    glow: "shadow-glow-emerald",
    text: "text-emerald-400",
  },
  red: {
    dot: "dot-red",
    border: "border-red-500/20",
    glow: "shadow-glow-red",
    text: "text-red-400",
  },
  amber: {
    dot: "dot-amber",
    border: "border-amber-500/20",
    glow: "shadow-glow-amber",
    text: "text-amber-400",
  },
  cyan: {
    dot: "live-dot",
    border: "border-cyan-500/20",
    glow: "shadow-glow-cyan",
    text: "text-console-accent",
  },
  violet: {
    dot: "bg-console-violet",
    border: "border-violet-500/20",
    glow: "shadow-glow-violet",
    text: "text-console-violet",
  },
  zinc: {
    dot: "dot-zinc",
    border: "border-zinc-700/40",
    glow: "",
    text: "text-zinc-400",
  },
};

export function StatsCard({
  title,
  value,
  subtitle,
  indicatorColor = "zinc",
  loading = false,
  trend,
  icon,
}: {
  title: string;
  value?: string;
  subtitle?: string;
  indicatorColor?: Color;
  loading?: boolean;
  trend?: ReactNode;
  icon?: ReactNode;
}) {
  const c = colorMap[indicatorColor];

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border bg-zinc-900/60 p-4 backdrop-blur-sm transition-all duration-200",
        "hover:bg-zinc-900/80",
        c.border,
        indicatorColor !== "zinc" && c.glow
      )}
    >
      {/* Subtle gradient top edge */}
      <div
        className={cn(
          "absolute inset-x-0 top-0 h-px opacity-60",
          indicatorColor === "emerald" && "bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent",
          indicatorColor === "cyan" && "bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent",
          indicatorColor === "red" && "bg-gradient-to-r from-transparent via-red-500/50 to-transparent",
          indicatorColor === "amber" && "bg-gradient-to-r from-transparent via-amber-500/50 to-transparent",
          indicatorColor === "violet" && "bg-gradient-to-r from-transparent via-violet-500/50 to-transparent",
        )}
      />

      <div className="flex items-start justify-between gap-2">
        <div className="text-xs font-medium text-zinc-500">{title}</div>
        <div className="flex items-center gap-1.5">
          {icon}
          <span className={cn("h-2 w-2 rounded-full", c.dot)} />
        </div>
      </div>

      {loading ? (
        <div className="mt-3 space-y-2">
          <div className="skeleton-shimmer h-8 w-32 rounded-md" />
          <div className="skeleton-shimmer h-3 w-20 rounded-md" />
        </div>
      ) : (
        <>
          <div className={cn("mt-2 text-2xl font-bold tracking-tight", c.text)}>
            {value ?? "—"}
          </div>
          {subtitle && (
            <div className="mt-1 text-xs text-zinc-500">{subtitle}</div>
          )}
          {trend && <div className="mt-2">{trend}</div>}
        </>
      )}
    </div>
  );
}
