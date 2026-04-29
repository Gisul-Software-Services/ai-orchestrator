"use client";

import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Activity,
  BarChart3,
  Database,
  History,
  LayoutDashboard,
  Play,
  Settings,
  Users,
  Cpu,
} from "lucide-react";
import { useHealthQuery } from "@/hooks/useMetrics";
import Link from "next/link";

/** Pure helper — exported for testing */
export function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}

const NAV_SECTIONS = [
  {
    label: "Platform",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/monitoring", label: "Monitoring", icon: Activity },
    ],
  },
  {
    label: "Generation",
    items: [
      { href: "/playground", label: "Playground", icon: Play },
      { href: "/rag", label: "RAG Management", icon: Database },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/usage", label: "Usage & Billing", icon: BarChart3 },
      { href: "/orgs", label: "Orgs & Keys", icon: Users },
      { href: "/history", label: "History", icon: History },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const health = useHealthQuery();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-zinc-800/60 bg-zinc-950 md:flex">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-zinc-800/60 px-4 py-4">
        <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/30 to-violet-500/30 ring-1 ring-zinc-700/60">
          <Cpu className="h-4 w-4 text-console-accent" strokeWidth={1.75} />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-console-accent shadow-glow-cyan" />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight text-zinc-50">
            Gisul Admin
          </div>
          <div className="text-[10px] font-medium uppercase tracking-widest text-zinc-600">
            AI Platform
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-3 py-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
              {section.label}
            </div>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isNavItemActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-150",
                      active
                        ? "bg-zinc-800/80 text-zinc-50"
                        : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200"
                    )}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r-full bg-console-accent shadow-glow-cyan" />
                    )}
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        active ? "text-console-accent" : "text-zinc-600 group-hover:text-zinc-400"
                      )}
                      strokeWidth={1.75}
                    />
                    <span>{item.label}</span>
                    {active && (
                      <span className="ml-auto h-1.5 w-1.5 rounded-full bg-console-accent shadow-glow-cyan" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer — model status */}
      <div className="border-t border-zinc-800/60 px-4 py-3">
        <ModelStatusRow
          modelLoaded={health.data?.model_loaded}
          unreachable={health.isError}
          loading={health.isLoading}
        />
      </div>
    </aside>
  );
}

function ModelStatusRow({
  modelLoaded,
  unreachable,
  loading,
}: {
  modelLoaded?: boolean;
  unreachable?: boolean;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-zinc-700 animate-pulse" />
        <span className="text-xs text-zinc-600">Connecting…</span>
      </div>
    );
  }

  const dotClass = unreachable
    ? "dot-zinc"
    : modelLoaded
      ? "dot-emerald"
      : "dot-red";

  const label = unreachable
    ? "Unreachable"
    : modelLoaded
      ? "Model loaded"
      : "Model not loaded";

  const labelClass = unreachable
    ? "text-zinc-500"
    : modelLoaded
      ? "text-emerald-400"
      : "text-red-400";

  return (
    <div className="flex items-center gap-2">
      <span className={dotClass} />
      <span className={cn("text-xs font-medium", labelClass)}>{label}</span>
    </div>
  );
}
