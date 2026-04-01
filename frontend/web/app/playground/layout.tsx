"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/playground", label: "All" },
  { href: "/playground/mcq", label: "MCQ" },
  { href: "/playground/subjective", label: "Subjective" },
  { href: "/playground/coding", label: "Coding" },
  { href: "/playground/sql", label: "SQL" },
  { href: "/playground/topics", label: "Topics" },
  { href: "/playground/aiml", label: "AIML (synthetic)" },
  { href: "/playground/aiml-library", label: "AIML (library)" },
  { href: "/playground/dsa", label: "DSA" },
  { href: "/playground/dsa-enrich", label: "DSA enrich" },
];

export default function PlaygroundLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="space-y-4">
      <div>
        <div className="text-lg font-semibold text-zinc-50">Playground</div>
        <div className="text-sm text-zinc-400">
          Test all generation endpoints
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => {
          const active =
            t.href === "/playground"
              ? pathname === "/playground"
              : pathname === t.href || pathname.startsWith(t.href + "/");
          return (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                "rounded-full border border-zinc-800 bg-zinc-950/40 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-900 hover:text-zinc-50",
                active && "border-cyan-500/40 bg-cyan-500/10 text-zinc-50"
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}

