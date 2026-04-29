"use client";

import { Building2, Calendar, Hash, Users } from "lucide-react";

function renderValue(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "string" || typeof v === "number") return String(v);
  if (typeof v === "object") return JSON.stringify(v, null, 2);
  return String(v);
}

function extractOrgFields(profile: Record<string, unknown> | null): Record<string, unknown> {
  if (!profile) return {};
  // Some backends wrap in { org: { ... } }
  const inner = (profile.org as Record<string, unknown> | undefined) ?? profile;
  return inner;
}

export function OrgProfileCard({
  profile,
}: {
  profile: Record<string, unknown> | null;
}) {
  const fields = extractOrgFields(profile);
  const entries = Object.entries(fields).filter(
    ([k]) => !["_id", "__v"].includes(k)
  );

  // Extract key fields for the hero row
  const name =
    (fields.name as string | undefined) ??
    (fields.orgName as string | undefined) ??
    null;
  const orgId =
    (fields.orgId as string | undefined) ??
    (fields.org_id as string | undefined) ??
    null;
  const employeeCount =
    (fields.employeeCounter as number | undefined) ??
    (fields.employee_count as number | undefined) ??
    null;
  const createdAt =
    (fields.createdAt as string | undefined) ??
    (fields.created_at as string | undefined) ??
    null;

  return (
    <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-5 backdrop-blur-sm">
      <div className="mb-4 text-sm font-semibold text-zinc-100">Organisation Profile</div>

      {/* Hero row */}
      {(name || orgId || employeeCount != null || createdAt) && (
        <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {name && (
            <div className="flex items-start gap-2 rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2.5">
              <Building2 className="mt-0.5 h-4 w-4 shrink-0 text-console-accent" strokeWidth={1.5} />
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-600">Name</div>
                <div className="mt-0.5 text-sm font-medium text-zinc-100">{name}</div>
              </div>
            </div>
          )}
          {orgId && (
            <div className="flex items-start gap-2 rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2.5">
              <Hash className="mt-0.5 h-4 w-4 shrink-0 text-console-violet" strokeWidth={1.5} />
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-600">Org ID</div>
                <div className="mt-0.5 font-mono text-xs text-zinc-200">{orgId}</div>
              </div>
            </div>
          )}
          {employeeCount != null && (
            <div className="flex items-start gap-2 rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2.5">
              <Users className="mt-0.5 h-4 w-4 shrink-0 text-console-emerald" strokeWidth={1.5} />
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-600">Employees</div>
                <div className="mt-0.5 text-sm font-medium text-zinc-100">{employeeCount}</div>
              </div>
            </div>
          )}
          {createdAt && (
            <div className="flex items-start gap-2 rounded-lg border border-zinc-800/60 bg-zinc-950/40 px-3 py-2.5">
              <Calendar className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500" strokeWidth={1.5} />
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-600">Created</div>
                <div className="mt-0.5 text-xs text-zinc-300">
                  {String(createdAt).replace("T", " ").slice(0, 10)}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* All fields table */}
      {entries.length === 0 ? (
        <div className="text-sm text-zinc-600">No profile fields available.</div>
      ) : (
        <div className="overflow-auto rounded-lg border border-zinc-800/60">
          <table className="w-full min-w-[400px] text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800/60">
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-600">Field</th>
                <th className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-600">Value</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([k, v]) => (
                <tr key={k} className="border-b border-zinc-800/40 hover:bg-zinc-800/20">
                  <td className="px-3 py-2 font-mono text-xs text-zinc-500">{k}</td>
                  <td className="px-3 py-2 break-all text-zinc-200">{renderValue(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
