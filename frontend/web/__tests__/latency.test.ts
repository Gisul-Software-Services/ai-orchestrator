// Feature: admin-console-redesign, Property 1: Latency unit correctness
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";

function fmtMs(n: number | null): string {
  return typeof n === "number" ? `${n.toFixed(0)} ms` : "—";
}

function computeAvgLatencyMs(
  totalGenSeconds: number,
  totalRequests: number
): number | null {
  if (totalRequests <= 0) return null;
  return (totalGenSeconds / totalRequests) * 1000;
}

describe("Latency unit correctness", () => {
  it("Property 1: avgLatencyMs is always positive and ends with ' ms'", () => {
    // Feature: admin-console-redesign, Property 1: Latency unit correctness
    fc.assert(
      fc.property(
        fc.float({ min: 0.001, max: 1000, noNaN: true }),
        fc.integer({ min: 1, max: 100000 }),
        (totalGenSeconds, totalRequests) => {
          const ms = computeAvgLatencyMs(totalGenSeconds, totalRequests);
          expect(ms).not.toBeNull();
          expect(ms!).toBeGreaterThan(0);
          const formatted = fmtMs(ms);
          expect(formatted.endsWith(" ms")).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it("returns null and '—' when totalRequests is 0", () => {
    const ms = computeAvgLatencyMs(5.0, 0);
    expect(ms).toBeNull();
    expect(fmtMs(ms)).toBe("—");
  });

  it("formula: (totalGenSeconds / totalRequests) * 1000", () => {
    expect(computeAvgLatencyMs(1.0, 1)).toBeCloseTo(1000);
    expect(computeAvgLatencyMs(0.5, 2)).toBeCloseTo(250);
    expect(computeAvgLatencyMs(10, 100)).toBeCloseTo(100);
  });

  it("fmtMs returns '—' for null", () => {
    expect(fmtMs(null)).toBe("—");
  });
});
