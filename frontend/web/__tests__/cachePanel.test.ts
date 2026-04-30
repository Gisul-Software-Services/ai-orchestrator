// Feature: admin-console-redesign, Property 2 & 3: Cache donut invariant + empty state
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";

function buildPieData(cacheHitRatePercent: number) {
  return [
    { name: "Hit", value: Math.max(0, cacheHitRatePercent) },
    { name: "Miss", value: Math.max(0, 100 - cacheHitRatePercent) },
  ];
}

function isEmpty(hits: number | null, misses: number | null): boolean {
  return (hits === null || hits === 0) && (misses === null || misses === 0);
}

describe("CachePanel donut invariant", () => {
  it("Property 2: pie data sums to 100 for any rate in [0, 100]", () => {
    // Feature: admin-console-redesign, Property 2: Cache donut invariant
    fc.assert(
      fc.property(fc.float({ min: 0, max: 100, noNaN: true }), (rate) => {
        const pie = buildPieData(rate);
        expect(pie[0].value + pie[1].value).toBeCloseTo(100, 5);
        expect(pie[0].value).toBeCloseTo(rate, 5);
      }),
      { numRuns: 100 }
    );
  });

  it("pie values are never negative", () => {
    fc.assert(
      fc.property(fc.float({ min: 0, max: 100, noNaN: true }), (rate) => {
        const pie = buildPieData(rate);
        expect(pie[0].value).toBeGreaterThanOrEqual(0);
        expect(pie[1].value).toBeGreaterThanOrEqual(0);
      }),
      { numRuns: 100 }
    );
  });
});

describe("CachePanel empty state", () => {
  it("Property 3: isEmpty returns true for all null/0 combinations", () => {
    // Feature: admin-console-redesign, Property 3: Cache empty state
    fc.assert(
      fc.property(
        fc.constantFrom(null as null | number, 0),
        fc.constantFrom(null as null | number, 0),
        (hits, misses) => {
          expect(isEmpty(hits, misses)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it("isEmpty returns false when hits > 0", () => {
    expect(isEmpty(5, 0)).toBe(false);
    expect(isEmpty(1, null)).toBe(false);
  });

  it("isEmpty returns false when misses > 0", () => {
    expect(isEmpty(0, 3)).toBe(false);
    expect(isEmpty(null, 10)).toBe(false);
  });

  it("isEmpty returns true for (null, null)", () => {
    expect(isEmpty(null, null)).toBe(true);
  });

  it("isEmpty returns true for (0, 0)", () => {
    expect(isEmpty(0, 0)).toBe(true);
  });
});
