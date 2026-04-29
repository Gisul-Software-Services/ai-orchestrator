import { cn } from "@/lib/utils";

// Standard shimmer skeleton
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-zinc-800/60",
        className
      )}
    >
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_infinite] bg-gradient-to-r from-transparent via-zinc-700/40 to-transparent" />
    </div>
  );
}

// Pulse dot — for "connecting" states
export function PulseDot({ color = "cyan" }: { color?: "cyan" | "emerald" | "amber" | "red" }) {
  const cls = {
    cyan:    "bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]",
    emerald: "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]",
    amber:   "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]",
    red:     "bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.8)]",
  }[color];
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", cls)} />
      <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", cls)} />
    </span>
  );
}

// Full-page loading overlay for initial data fetch
export function PageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6">
      {/* Animated rings */}
      <div className="relative flex h-20 w-20 items-center justify-center">
        <div className="absolute h-20 w-20 animate-[spin_3s_linear_infinite] rounded-full border border-transparent border-t-cyan-500/60" />
        <div className="absolute h-14 w-14 animate-[spin_2s_linear_infinite_reverse] rounded-full border border-transparent border-t-violet-500/60" />
        <div className="absolute h-8 w-8 animate-[spin_1.5s_linear_infinite] rounded-full border border-transparent border-t-emerald-500/60" />
        <div className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.9)]" />
      </div>
      <div className="space-y-1 text-center">
        <div className="text-sm font-medium text-zinc-300">{label}</div>
        <div className="text-xs text-zinc-600">Connecting to model service…</div>
      </div>
    </div>
  );
}

// Dashboard-specific skeleton that mirrors the actual layout
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Hero banner skeleton */}
      <div className="relative overflow-hidden rounded-2xl border border-zinc-800/60 bg-zinc-900/60 p-6">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-zinc-700/50 to-transparent" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-14 w-14 rounded-2xl" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-24 rounded" />
            <Skeleton className="h-9 w-40 rounded-lg" />
            <Skeleton className="h-3 w-28 rounded" />
          </div>
          <div className="ml-auto flex gap-3">
            {[1,2,3].map(i => <Skeleton key={i} className="h-16 w-24 rounded-xl" />)}
          </div>
        </div>
      </div>

      {/* GPU row skeleton */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[1,2,3,4].map(i => (
          <div key={i} className="rounded-2xl border border-zinc-800/60 bg-zinc-900/60 p-4">
            <div className="mb-3 flex items-center justify-between">
              <Skeleton className="h-3 w-20 rounded" />
              <Skeleton className="h-4 w-4 rounded" />
            </div>
            <Skeleton className="h-8 w-28 rounded-lg" />
            <Skeleton className="mt-2 h-3 w-16 rounded" />
          </div>
        ))}
      </div>

      {/* 3-panel row skeleton */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {[1,2,3].map(i => (
          <div key={i} className="rounded-2xl border border-zinc-800/60 bg-zinc-900/60">
            <div className="border-b border-zinc-800/60 px-5 py-3.5">
              <Skeleton className="h-4 w-32 rounded" />
              <Skeleton className="mt-1 h-3 w-24 rounded" />
            </div>
            <div className="space-y-3 p-5">
              <div className="grid grid-cols-3 gap-2">
                {[1,2,3].map(j => <Skeleton key={j} className="h-16 rounded-xl" />)}
              </div>
              {[1,2,3].map(j => <Skeleton key={j} className="h-9 rounded-lg" />)}
            </div>
          </div>
        ))}
      </div>

      {/* Endpoint chart skeleton */}
      <div className="rounded-2xl border border-zinc-800/60 bg-zinc-900/60">
        <div className="border-b border-zinc-800/60 px-5 py-3.5">
          <Skeleton className="h-4 w-40 rounded" />
          <Skeleton className="mt-1 h-3 w-28 rounded" />
        </div>
        <div className="p-5">
          <Skeleton className="h-[280px] w-full rounded-xl" />
        </div>
      </div>
    </div>
  );
}
