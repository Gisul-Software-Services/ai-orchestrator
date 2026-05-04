"use client";

import { usePathname, useRouter } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";
import { useHealthQuery } from "@/hooks/useMetrics";
import { cn } from "@/lib/utils";
import { LogOut } from "lucide-react";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Overview",
  "/playground": "Playground",
  "/monitoring": "Monitoring",
  "/usage": "Usage & Billing",
  "/orgs": "Orgs & Keys",
  "/rag": "RAG Management",
  "/history": "History",
  "/settings": "Settings",
  "/model": "Model",
  "/catalog": "Catalog",
};

function titleFromPath(pathname: string): string {
  const clean = pathname.split("?")[0].split("#")[0];
  // Exact match
  if (PAGE_TITLES[clean]) return PAGE_TITLES[clean];
  // Prefix match
  for (const [key, val] of Object.entries(PAGE_TITLES)) {
    if (clean.startsWith(key + "/")) return val;
  }
  const seg = clean.split("/")[1];
  if (!seg) return "Dashboard";
  return seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, " ");
}

export function TopBar() {
  const pathname = usePathname();
  const router = useRouter();
  const title = titleFromPath(pathname);
  const health = useHealthQuery();

  const modelLoaded = health.data?.model_loaded;
  const unreachable = health.isError;

  async function handleLogout() {
    await fetch("/api/admin/auth", { method: "DELETE" });
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-zinc-800/60 bg-zinc-950/90 px-6 backdrop-blur-md sm:px-8">
      {/* Left — title */}
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold tracking-tight text-zinc-50">
          {title}
        </h1>
        {/* Live model status pill */}
        <div
          className={cn(
            "hidden items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium sm:flex",
            unreachable
              ? "border-zinc-700/60 bg-zinc-900 text-zinc-500"
              : modelLoaded
                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                : health.isLoading
                  ? "border-zinc-700/60 bg-zinc-900 text-zinc-500"
                  : "border-red-500/20 bg-red-500/10 text-red-400"
          )}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              unreachable
                ? "bg-zinc-500"
                : modelLoaded
                  ? "bg-emerald-400 animate-pulse"
                  : health.isLoading
                    ? "bg-zinc-500 animate-pulse"
                    : "bg-red-400"
            )}
          />
          {unreachable
            ? "Offline"
            : health.isLoading
              ? "Connecting"
              : modelLoaded
                ? "Loaded"
                : "Not loaded"}
        </div>
      </div>

      {/* Right — user + theme */}
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 sm:flex">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/30 to-violet-500/30 ring-1 ring-zinc-700/60 text-xs font-bold text-zinc-200">
            A
          </div>
          <span className="text-xs text-zinc-400">
            <span className="font-medium text-zinc-200">admin</span>
          </span>
        </div>
        <div className="h-4 w-px bg-zinc-800" />
        <ThemeToggle />
        <div className="h-4 w-px bg-zinc-800" />
        <button
          onClick={handleLogout}
          title="Sign out"
          className="flex items-center justify-center rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
        >
          <LogOut className="h-4 w-4" strokeWidth={1.75} />
        </button>
      </div>
    </header>
  );
}
