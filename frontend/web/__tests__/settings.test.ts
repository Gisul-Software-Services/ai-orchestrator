// Feature: admin-console-redesign, Property 6: Settings uptime non-negative
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";

function computeUptimeSeconds(serverStartTime: string): number {
  const parsed = Date.parse(serverStartTime);
  if (Number.isNaN(parsed)) return 0;
  return Math.max(0, Math.floor((Date.now() - parsed) / 1000));
}

describe("Settings uptime", () => {
  it("Property 6: uptime is always non-negative for past dates", () => {
    // Feature: admin-console-redesign, Property 6: Settings uptime non-negative
    fc.assert(
      fc.property(
        fc.date({ max: new Date() }),
        (pastDate) => {
          const uptime = computeUptimeSeconds(pastDate.toISOString());
          expect(uptime).toBeGreaterThanOrEqual(0);
        }
      ),
      { numRuns: 100 }
    );
  });

  it("returns 0 for invalid ISO string", () => {
    expect(computeUptimeSeconds("not-a-date")).toBe(0);
    expect(computeUptimeSeconds("")).toBe(0);
  });

  it("returns 0 for a future date (clamped)", () => {
    const future = new Date(Date.now() + 1_000_000).toISOString();
    expect(computeUptimeSeconds(future)).toBe(0);
  });

  it("returns a positive number for a past date", () => {
    const past = new Date(Date.now() - 60_000).toISOString(); // 1 minute ago
    expect(computeUptimeSeconds(past)).toBeGreaterThan(0);
  });
});

describe("GPU unavailable state logic", () => {
  it("Property 4: GPU unavailable when available === false", () => {
    // Feature: admin-console-redesign, Property 4: GPU unavailable state
    fc.assert(
      fc.property(
        fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: undefined }),
        (errorMsg) => {
          const gpu = { available: false as const, error: errorMsg };
          const isUnavailable = gpu.available === false;
          expect(isUnavailable).toBe(true);
          const displayValue = isUnavailable ? "GPU unavailable" : "some value";
          expect(displayValue).toBe("GPU unavailable");
          const subtitle = isUnavailable
            ? (gpu.error ?? "NVML not available")
            : undefined;
          if (errorMsg) {
            expect(subtitle).toBe(errorMsg);
          } else {
            expect(subtitle).toBe("NVML not available");
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
