"use client";

import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";

function titleFromPath(pathname: string): string {
  const path = pathname.split("?")[0].split("#")[0];
  if (path === "/" || path === "") return "Dashboard";
  const [, segment] = path.split("/");
  if (!segment) return "Dashboard";
  return (
    segment.charAt(0).toUpperCase() +
    segment.slice(1).replace(/-/g, " ")
  );
}

export function TopBar() {
  const pathname = usePathname();
  const title = titleFromPath(pathname);

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between border-b border-zinc-800 bg-zinc-950/80 px-6 py-3 backdrop-blur sm:px-8">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-zinc-50">
          {title}
        </h1>
        <p className="text-xs text-zinc-400">
          Internal admin console — authenticated staff only
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="hidden text-xs text-zinc-400 sm:inline">
          Signed in as <span className="font-medium text-zinc-100">admin</span>
        </span>
        <ThemeToggle />
      </div>
    </header>
  );
}

