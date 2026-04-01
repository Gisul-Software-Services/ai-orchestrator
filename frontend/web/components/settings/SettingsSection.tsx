"use client";

import type { ReactNode } from "react";

export function SettingsSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-white/10 bg-zinc-950/40 p-4">
      <div className="mb-2 text-sm font-medium text-zinc-200">{title}</div>
      <div>{children}</div>
    </section>
  );
}

