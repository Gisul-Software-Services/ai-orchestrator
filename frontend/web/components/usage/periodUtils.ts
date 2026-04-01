export function currentUtcMonth() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function isValidPeriod(p: string) {
  return /^\d{4}-\d{2}$/.test(p);
}

export function buildRecentMonths(count: number) {
  const out: string[] = [];
  const d = new Date();
  d.setUTCDate(1);
  for (let i = 0; i < count; i++) {
    out.push(
      `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`
    );
    d.setUTCMonth(d.getUTCMonth() - 1);
  }
  return out;
}

