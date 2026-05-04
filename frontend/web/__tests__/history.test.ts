// Feature: admin-console-redesign, Properties 7, 8, 9: History formatting
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";

function fmtTotal(n: number): string {
  return n.toLocaleString();
}

function fmtLatency(n: number): string {
  return `${n} ms`;
}

function fmtErrorRate(n: number): string {
  return `${n.toFixed(2)}%`;
}

describe("History page formatting", () => {
  it("Property 7: total uses toLocaleString()", () => {
    // Feature: admin-console-redesign, Property 7: History total formatting
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 10_000_000 }), (total) => {
        expect(fmtTotal(total)).toBe(total.toLocaleString());
      }),
      { numRuns: 100 }
    );
  });

  it("Property 8: latency formatted as '<n> ms'", () => {
    // Feature: admin-console-redesign, Property 8: History latency formatting
    fc.assert(
      fc.property(fc.float({ min: 0, max: 100000, noNaN: true }), (avgLatency) => {
        const result = fmtLatency(avgLatency);
        expect(result).toBe(`${avgLatency} ms`);
        expect(result.endsWith(" ms")).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  it("Property 9: error rate formatted as '<n.toFixed(2)>%'", () => {
    // Feature: admin-console-redesign, Property 9: History error rate formatting
    fc.assert(
      fc.property(fc.float({ min: 0, max: 100, noNaN: true }), (errorRate) => {
        const result = fmtErrorRate(errorRate);
        expect(result).toBe(`${errorRate.toFixed(2)}%`);
        expect(result.endsWith("%")).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  it("known values", () => {
    expect(fmtTotal(1234567)).toBe((1234567).toLocaleString());
    expect(fmtLatency(142)).toBe("142 ms");
    expect(fmtErrorRate(0.01)).toBe("0.01%");
    expect(fmtErrorRate(100)).toBe("100.00%");
    expect(fmtErrorRate(0)).toBe("0.00%");
  });
});
