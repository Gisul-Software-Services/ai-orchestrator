"use client";

import Link from "next/link";
import { useStatsQuery } from "@/hooks/useMetrics";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const CARDS = [
  {
    href: "/playground/topics",
    title: "Topics",
    desc: "Generate assessment topics",
    statKey: "topics",
  },
  { href: "/playground/mcq", title: "MCQ", desc: "Multiple choice questions", statKey: "mcq" },
  {
    href: "/playground/subjective",
    title: "Subjective",
    desc: "Subjective questions",
    statKey: "subjective",
  },
  { href: "/playground/coding", title: "Coding", desc: "Coding problems", statKey: "coding" },
  { href: "/playground/sql", title: "SQL", desc: "SQL problems", statKey: "sql" },
  { href: "/playground/aiml", title: "AIML (synthetic)", desc: "Synthetic AIML problems", statKey: "aiml" },
  { href: "/playground/aiml-library", title: "AIML (library)", desc: "Library dataset AIML problems", statKey: "aiml" },
  { href: "/playground/dsa", title: "DSA question", desc: "FAISS/keyword DSA generator", statKey: "dsa" },
  { href: "/playground/dsa-enrich", title: "DSA enrich", desc: "Enrich a DSA problem payload", statKey: "dsa" },
];

export default function PlaygroundIndexPage() {
  const statsQ = useStatsQuery();
  const counts = (statsQ.data?.requests_by_endpoint ?? {}) as Record<string, number>;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {CARDS.map((c) => {
        const n = counts?.[c.statKey] ?? 0;
        return (
          <Link
            key={c.href}
            href={c.href}
            className={cn(
              "group rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 shadow-panel hover:border-cyan-500/40 hover:bg-zinc-950/80"
            )}
          >
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-zinc-50">{c.title}</div>
                <div className="mt-1 text-xs text-zinc-400">{c.desc}</div>
              </div>
              <div className="rounded-full border border-zinc-800 bg-zinc-900/40 px-2 py-1 text-xs text-zinc-300">
                {statsQ.isLoading ? <Skeleton className="h-3 w-10" /> : `${n} req`}
              </div>
            </div>
            <div className="text-xs text-cyan-300/80 opacity-0 transition-opacity group-hover:opacity-100">
              Open →
            </div>
          </Link>
        );
      })}
    </div>
  );
}
