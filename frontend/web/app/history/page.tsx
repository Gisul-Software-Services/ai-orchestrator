import { HistoryClient } from "@/components/history/HistoryClient";

export default function HistoryPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50">
          Run history
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">
          Recent playground runs stored in this browser&apos;s session storage. Open the{" "}
          <a href="/playground" className="text-console-accent hover:underline">
            Playground
          </a>{" "}
          to generate and record new runs.
        </p>
      </header>
      <HistoryClient />
    </div>
  );
}
