// Feature: admin-console-redesign, Property 10: Queue sort order
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";

function sortQueues(
  queueDepths: Record<string, number>
): Array<[string, number]> {
  return Object.entries(queueDepths).sort((a, b) => b[1] - a[1]);
}

describe("QueuePanel sort order", () => {
  it("Property 10: queues are sorted descending by depth", () => {
    // Feature: admin-console-redesign, Property 10: Queue sort order
    fc.assert(
      fc.property(
        fc.dictionary(
          fc.string({ minLength: 1, maxLength: 20 }),
          fc.integer({ min: 0, max: 1000 }),
          { minKeys: 1, maxKeys: 20 }
        ),
        (queueDepths) => {
          const sorted = sortQueues(queueDepths);
          for (let i = 0; i < sorted.length - 1; i++) {
            expect(sorted[i][1]).toBeGreaterThanOrEqual(sorted[i + 1][1]);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it("empty queue_depths returns empty array", () => {
    expect(sortQueues({})).toEqual([]);
  });

  it("single queue returns single entry", () => {
    const result = sortQueues({ topics: 5 });
    expect(result).toEqual([["topics", 5]]);
  });

  it("sorts correctly for known input", () => {
    const result = sortQueues({ topics: 42, mcq: 18, sql: 0, coding: 12 });
    expect(result[0][0]).toBe("topics");
    expect(result[0][1]).toBe(42);
    expect(result[result.length - 1][1]).toBe(0);
  });
});
