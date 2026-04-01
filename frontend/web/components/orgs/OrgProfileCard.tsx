"use client";

function renderValue(v: unknown) {
  if (v == null) return "—";
  if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
    return String(v);
  }
  return JSON.stringify(v);
}

export function OrgProfileCard({
  profile,
}: {
  profile: Record<string, unknown> | null;
}) {
  const entries = profile ? Object.entries(profile) : [];

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="text-sm font-medium text-zinc-200">Organisation Profile</div>
      {entries.length === 0 ? (
        <div className="mt-3 text-sm text-zinc-500">No profile fields available.</div>
      ) : (
        <div className="mt-3 overflow-auto">
          <table className="w-full min-w-[500px] text-left text-sm">
            <thead className="text-xs text-zinc-500">
              <tr className="border-b border-white/10">
                <th className="py-2 pr-3">Field</th>
                <th className="py-2">Value</th>
              </tr>
            </thead>
            <tbody className="text-zinc-200">
              {entries.map(([k, v]) => (
                <tr key={k} className="border-b border-white/5">
                  <td className="py-2 pr-3 font-mono text-xs text-zinc-400">{k}</td>
                  <td className="py-2 break-all">{renderValue(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

