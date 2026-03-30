import Link from "next/link";

export default function ModelPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50">
          Model
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">
          The inference model runs in the FastAPI process, not in Next.js. Use the API
          for health and the monitoring UI for live load.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-5">
          <h2 className="text-sm font-semibold text-zinc-200">Health</h2>
          <p className="mt-2 text-xs leading-relaxed text-zinc-500">
            <code className="rounded bg-zinc-950 px-1 text-zinc-400">GET /health</code> on
            your API base (same host as{" "}
            <code className="text-zinc-400">NEXT_PUBLIC_API_BASE</code>).
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 p-5">
          <h2 className="text-sm font-semibold text-zinc-200">Live metrics</h2>
          <p className="mt-2 text-xs leading-relaxed text-zinc-500">
            GPU, queues, and request counters from{" "}
            <code className="rounded bg-zinc-950 px-1 text-zinc-400">
              GET /api/v1/metrics/overview
            </code>
            .
          </p>
          <Link
            href="/monitoring"
            className="mt-3 inline-block text-sm text-console-accent hover:underline"
          >
            Open Monitoring →
          </Link>
        </div>
      </div>
    </div>
  );
}
