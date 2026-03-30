import { MonitoringClient } from "@/components/dashboard/MonitoringClient";

export default function MonitoringPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50">
          Monitoring
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">
          Live GPU, batch queues, and inference counters from your API process. Charts
          build a short rolling window while you stay on this page.
        </p>
      </header>
      <MonitoringClient />
    </div>
  );
}
