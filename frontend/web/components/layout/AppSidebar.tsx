"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Cpu,
  FlaskConical,
  History,
  LayoutDashboard,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/playground", label: "Playground", icon: FlaskConical },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/usage", label: "Org usage", icon: BarChart3 },
  { href: "/history", label: "History", icon: History },
  { href: "/model", label: "Model", icon: Cpu },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 flex-col border-r border-zinc-800/80 bg-zinc-950/95 shadow-panel backdrop-blur-sm">
      <div className="flex items-center gap-2 border-b border-zinc-800/80 px-4 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/20 to-violet-500/20 ring-1 ring-zinc-700/80">
          <LayoutDashboard className="h-5 w-5 text-console-accent" strokeWidth={1.75} />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight text-zinc-50">
            Model Console
          </div>
          <div className="text-[10px] font-medium uppercase tracking-widest text-zinc-500">
            Operations
          </div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {nav.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                active
                  ? "bg-zinc-800/90 text-white shadow-sm ring-1 ring-zinc-700/60"
                  : "text-zinc-400 hover:bg-zinc-900/80 hover:text-zinc-100"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-colors",
                  active
                    ? "text-console-accent"
                    : "text-zinc-600 group-hover:text-zinc-400"
                )}
                strokeWidth={1.75}
              />
              {item.label}
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-console-accent shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
              )}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-zinc-800/80 p-4">
        <p className="text-[10px] leading-relaxed text-zinc-600">
          Live metrics poll the API. Ensure{" "}
          <code className="rounded bg-zinc-900 px-1 text-zinc-500">
            NEXT_PUBLIC_API_BASE
          </code>{" "}
          matches your backend.
        </p>
      </div>
    </aside>
  );
}
