// Feature: admin-console-redesign, Property 5: Sidebar active state uniqueness
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";

const NAV_HREFS = [
  "/dashboard",
  "/playground",
  "/monitoring",
  "/usage",
  "/orgs",
  "/rag",
  "/history",
  "/settings",
];

function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}

function getActiveHrefs(pathname: string, hrefs: string[]): string[] {
  return hrefs.filter((href) => isNavItemActive(pathname, href));
}

describe("Sidebar active state", () => {
  it("exactly one nav item is active for each exact nav href", () => {
    // Feature: admin-console-redesign, Property 5: Sidebar active state uniqueness
    fc.assert(
      fc.property(fc.constantFrom(...NAV_HREFS), (pathname) => {
        const active = getActiveHrefs(pathname, NAV_HREFS);
        expect(active.length).toBe(1);
        expect(active[0]).toBe(pathname);
      }),
      { numRuns: 100 }
    );
  });

  it("sub-paths activate the correct parent nav item", () => {
    const subPaths = NAV_HREFS.map((h) => `${h}/sub/page`);
    fc.assert(
      fc.property(fc.constantFrom(...subPaths), (pathname) => {
        const active = getActiveHrefs(pathname, NAV_HREFS);
        // At least one item should be active (the parent)
        expect(active.length).toBeGreaterThanOrEqual(1);
        // The active item must be a prefix of the pathname
        active.forEach((href) => {
          expect(pathname.startsWith(href)).toBe(true);
        });
      }),
      { numRuns: 100 }
    );
  });

  it("isNavItemActive returns false for unrelated paths", () => {
    expect(isNavItemActive("/dashboard", "/settings")).toBe(false);
    expect(isNavItemActive("/playground/sql", "/settings")).toBe(false);
    expect(isNavItemActive("/dashboardextra", "/dashboard")).toBe(false);
  });

  it("isNavItemActive returns true for exact match", () => {
    NAV_HREFS.forEach((href) => {
      expect(isNavItemActive(href, href)).toBe(true);
    });
  });

  it("isNavItemActive returns true for sub-path", () => {
    expect(isNavItemActive("/playground/sql", "/playground")).toBe(true);
    expect(isNavItemActive("/orgs/org-123", "/orgs")).toBe(true);
    expect(isNavItemActive("/rag/dsa", "/rag")).toBe(true);
  });
});
