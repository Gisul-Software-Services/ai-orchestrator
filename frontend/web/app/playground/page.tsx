"use client";

import Link from "next/link";
import { useStatsQuery } from "@/hooks/useMetrics";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  Code2,
  Database,
  FileQuestion,
  FlaskConical,
  Hash,
  Layers,
  MessageSquare,
  Sparkles,
  Tag,
  Wand2,
} from "lucide-react";

const CARDS = [
  {
    href: "/playground/topics",
    title: "Topics",
    desc: "Generate assessment topics",
    statKey: "topics",
    icon: Tag,
    accent: "cyan",
  },
  {
    href: "/playground/mcq",
    title: "MCQ",
    desc: "Multiple choice questions",
    statKey: "mcq",
    icon: FileQuestion,
    accent: "violet",
  },
  {
    href: "/playground/subjective",
    title: "Subjective",
    desc: "Open-ended questions",
    statKey: "subjective",
    icon: MessageSquare,
    accent: "emerald",
  },
  {
    href: "/playground/coding",
    title: "Coding",
    desc: "Coding problems",
    statKey: "coding",
    icon: Code2,
    accent: "cyan",
  },
  {
    href: "/playground/sql",
    title: "SQL",
    desc: "SQL problems (RAG + reword)",
    statKey: "sql",
    icon: Database,
    accent: "violet",
  },
  {
    href: "/playground/aiml",
    title: "AIML (synthetic)",
    desc: "Synthetic AIML problems",
    statKey: "aiml",
    icon: Sparkles,
    accent: "emerald",
  },
  {
    href: "/playground/aiml-library",
    title: "AIML (library)",
    desc: "Library dataset AIML problems",
    statKey: "aiml",
    icon: Layers,
    accent: "cyan",
  },
  {
    href: "/playground/dsa",
    title: "DSA question",
    desc: "FAISS/keyword DSA generator",
    statKey: "dsa",
    icon: Hash,
    accent: "violet",
  },
  {
    href: "/playground/dsa-enrich",
    title: "DSA enrich",
    desc: "Enrich a DSA problem payload",
    statKey: "dsa",
    icon: Wand2,
    accent: "emerald",
  },
];

const accentMap = {
  cyan: {
    icon: "text-console-accent",
    border: "hover:border-cyan-500/40",
    badge: "border-cyan-500/20 bg-cyan-500/10 text-cyan-400",
    glow: "hover:shadow-glow-cyan",
    arrow: "text-console-accent",
  },
  violet: {
    icon: "text-console-violet",
    border: "hover:border-violet-500/40",
    badge: "border-violet-500/20 bg-violet-500/10 text-violet-400",
    glow: "hover:shadow-glow-violet",
    arrow: "text-console-violet",
  },
  emerald: {
    icon: "text-console-emerald",
    border: "hover:border-emerald-500/40",
    badge: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    glow: "hover:shadow-glow-emerald",
    arrow: "text-console-emerald",
  },
};

export default function PlaygroundIndexPage() {
  const statsQ = useStatsQuery();
  const counts = (statsQ.data?.requests_by_endpoint ?? {}) as Record<string, number>;

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-zinc-600">
            {CARDS.length} endpoints available
          </div>
        </div>
        {statsQ.dataUpdatedAt && (
          <div className="text-[11px] text-zinc-600">
            Stats updated {new Date(statsQ.dataUpdatedAt).toLocaleTimeString()}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {CARDS.map((c) => {
          const n = counts?.[c.statKey] ?? 0;
          const a = accentMap[c.accent as keyof typeof accentMap];
          const Icon = c.icon;

          return (
            <Link
              key={c.href}
              href={c.href}
              className={cn(
                "group relative overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 backdrop-blur-sm",
                "transition-all duration-200",
                a.border,
                a.glow
              )}
            >
              {/* Top gradient line */}
              <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-zinc-700/50 to-transparent transition-all duration-200 group-hover:via-current" />

              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-zinc-800/60 bg-zinc-950/60">
                    <Icon className={cn("h-4 w-4", a.icon)} strokeWidth={1.75} />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-zinc-100">{c.title}</div>
                    <div className="mt-0.5 text-xs text-zinc-500">{c.desc}</div>
                  </div>
                </div>

                <div className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium tabular-nums", a.badge)}>
                  {statsQ.isLoading ? (
                    <Skeleton className="h-3 w-8" />
                  ) : statsQ.isError ? (
                    <span className="text-zinc-600">—</span>
                  ) : (
                    `${n.toLocaleString()}`
                  )}
                </div>
              </div>

              <div className={cn(
                "mt-3 flex items-center gap-1 text-xs font-medium opacity-0 transition-opacity duration-200 group-hover:opacity-100",
                a.arrow
              )}>
                Open playground
                <span className="transition-transform duration-200 group-hover:translate-x-0.5">→</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
