"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/admin/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Invalid token");
      }
      router.replace("/dashboard");
    } catch (err) {
      setError((err as Error).message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm rounded-xl border border-zinc-800 bg-zinc-900/80 p-6 shadow-lg">
        <h1 className="mb-2 text-lg font-semibold text-zinc-50">
          Gisul Admin Login
        </h1>
        <p className="mb-4 text-xs text-zinc-400">
          Enter the internal admin token to access the console.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label
              htmlFor="token"
              className="block text-xs font-medium text-zinc-300"
            >
              Admin token
            </label>
            <input
              id="token"
              type="password"
              className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-console-accent focus:ring-1 focus:ring-cyan-400/70"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="off"
              required
            />
          </div>
          {error && (
            <p className="text-xs text-red-400" role="alert">
              {error}
            </p>
          )}
          <Button
            type="submit"
            className="mt-1 w-full"
            disabled={loading || !token}
          >
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}

