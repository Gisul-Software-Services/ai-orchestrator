"use client";

import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Activity, BarChart3, History, LayoutDashboard, Layers, Play, Settings, Users } from "lucide-react";
import { useHealthQuery } from "@/hooks/useMetrics";
import Link from "next/link";

const SECTIONS = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/playground", label: "Playground", icon: Play },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/usage", label: "Usage & Billing", icon: BarChart3 },
  { href: "/orgs", label: "Orgs & Keys", icon: Users },
  { href: "/catalog", label: "Dataset Catalog", icon: Layers },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const health = useHealthQuery();

  return (
    <aside className="hidden w-64 shrink-0 border-r border-zinc-200 bg-white/95 p-4 md:flex md:flex-col dark:border-zinc-800 dark:bg-zinc-950/95">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Gisul Admin
          </div>
          <div className="text-xs text-zinc-500 dark:text-zinc-400">AI Platform Console</div>
        </div>
        <ModelStatusDot
          modelLoaded={health.data?.model_loaded}
          unreachable={health.isError}
        />
      </div>
      <nav className="flex-1 space-y-1 text-sm">
        {SECTIONS.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-2 py-1.5 text-zinc-700 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-900 dark:hover:text-zinc-50",
                active && "bg-zinc-100 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-4 text-xs text-zinc-500 dark:text-zinc-500">
        Internal use only. Model status may be delayed by a few seconds.
      </div>
    </aside>
  );
}

function ModelStatusDot({
  modelLoaded,
  unreachable,
}: {
  modelLoaded?: boolean;
  unreachable?: boolean;
}) {
  const color = unreachable
    ? "bg-zinc-500"
    : modelLoaded
      ? "bg-emerald-400"
      : "bg-red-400";
  const label = unreachable ? "Unreachable" : modelLoaded ? "Loaded" : "Not loaded";

  return (
    <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400">
      <span className={cn("inline-block h-2 w-2 rounded-full", color)} />
      <span>{label}</span>
    </div>
  );
}

