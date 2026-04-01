/**
 * Admin-side fetch wrapper that always talks to Next.js API routes under /api/admin/*.
 * These server routes attach X-Api-Key from process.env.ADMIN_API_KEY and call
 * the backend gateway on port 7000. The raw key never leaves the server.
 */

export async function adminFetchJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  if (!path.startsWith("/api/admin/")) {
    throw new Error("adminFetchJson must be called with /api/admin/* paths only");
  }
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `${res.status} ${res.statusText}: ${text.slice(0, 400) || "request failed"}`
    );
  }
  return res.json() as Promise<T>;
}

export async function adminPostJson<T>(
  path: string,
  body: unknown
): Promise<T> {
  return adminFetchJson<T>(path, {
    method: "POST",
    body: JSON.stringify(body ?? {}),
  });
}

