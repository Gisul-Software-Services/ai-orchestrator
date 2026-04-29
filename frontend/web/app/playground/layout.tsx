"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Brain, Cloud, Code2, Database,
  FileQuestion, Hash, MessageSquare, Server, Tag,
} from "lucide-react";

const TABS = [
  { href: "/playground",             label: "All",            icon: Brain },
  { href: "/playground/mcq",         label: "MCQ",            icon: FileQuestion },
  { href: "/playground/subjective",  label: "Subjective",     icon: MessageSquare },
  { href: "/playground/coding",      label: "Coding",         icon: Code2 },
  { href: "/playground/sql",         label: "SQL",            icon: Database },
  { href: "/playground/topics",      label: "Topics",         icon: Tag },
  { href: "/playground/aiml",        label: "AIML",           icon: Brain },
  { href: "/playground/dsa",         label: "DSA",            icon: Hash },
  { href: "/playground/devops",      label: "DevOps",         icon: Server },
  { href: "/playground/cloud",       label: "Cloud (AWS)",    icon: Cloud },
];

export default function PlaygroundLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <div className="text-2xl font-bold tracking-tight text-zinc-50">Playground</div>
        <div className="mt-1 text-sm text-zinc-500">
          Test all generation endpoints — results are not stored
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active =
            t.href === "/playground"
              ? pathname === "/playground"
              : pathname === t.href || pathname.startsWith(t.href + "/");
          return (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition-all",
                active
                  ? "border-cyan-500/40 bg-cyan-500/15 text-cyan-300"
                  : "border-zinc-800/60 bg-zinc-900/40 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
              )}
            >
              <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
              {t.label}
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}
