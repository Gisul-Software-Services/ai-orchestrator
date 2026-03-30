export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50">
          Settings
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-400">
          This UI is static; configuration is via environment variables at build and
          runtime.
        </p>
      </header>

      <div className="max-w-2xl space-y-6 rounded-xl border border-zinc-800/80 bg-zinc-900/25 p-6 text-sm">
        <section>
          <h2 className="font-semibold text-zinc-200">Frontend (.env.local)</h2>
          <ul className="mt-2 list-inside list-disc space-y-1 text-zinc-500">
            <li>
              <code className="text-zinc-400">NEXT_PUBLIC_API_BASE</code> — FastAPI URL
              (e.g. <code className="text-zinc-400">http://127.0.0.1:9000</code>)
            </li>
            <li>
              <code className="text-zinc-400">NEXT_PUBLIC_PLAYGROUND_ORG_ID</code> —
              default org when the playground field is empty (sent as{" "}
              <code className="text-zinc-400">org_id</code> and{" "}
              <code className="text-zinc-400">X-Org-Id</code>); required in practice — set this or
              type an Org ID in the UI
            </li>
            <li>
              <code className="text-zinc-400">NEXT_PUBLIC_BILLING_DEFAULT_ORG</code> — optional
              default org on the usage page when no <code className="text-zinc-400">?org=</code> is
              present
            </li>
            <li>
              <code className="text-zinc-400">NEXT_PUBLIC_ORG_MONTHLY_TOKEN_BUDGET</code> —
              optional number; when set, the org dashboard shows a utilization bar vs this cap
            </li>
          </ul>
        </section>
        <section>
          <h2 className="font-semibold text-zinc-200">Backend (`backend/.env`)</h2>
          <ul className="mt-2 list-inside list-disc space-y-1 text-zinc-500">
            <li>
              <code className="text-zinc-400">REQUIRE_VERIFIED_ORG_FOR_GENERATION</code> —
              production: only registered orgs may POST generation / AIML catalog preview
            </li>
            <li>
              <code className="text-zinc-400">MONGODB_URI</code>,{" "}
              <code className="text-zinc-400">BILLING_DB_NAME</code>,{" "}
              <code className="text-zinc-400">ORGANIZATION_DB_NAME</code>
            </li>
            <li>
              <code className="text-zinc-400">ASSETS_DIR</code> — root containing{" "}
              <code className="text-zinc-400">dsa-coding/</code> and{" "}
              <code className="text-zinc-400">aiml-data/</code>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
