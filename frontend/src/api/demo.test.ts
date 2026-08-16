import { afterEach, describe, expect, it } from "vitest";

import { DEMO_MODE_KEY, DEMO_UNHANDLED, getDemoResponse } from "./demo";

describe("safe demo mode", () => {
  afterEach(() => localStorage.removeItem(DEMO_MODE_KEY));

  it("returns synthetic project data only when explicitly enabled", async () => {
    expect(await getDemoResponse("/api/stored/issues/DEMO", {})).toBe(DEMO_UNHANDLED);
    localStorage.setItem(DEMO_MODE_KEY, "true");
    const issues = await getDemoResponse("/api/stored/issues/DEMO", {});
    expect(Array.isArray(issues)).toBe(true);
    expect(JSON.stringify(issues)).toContain("safe demonstration issue");
    expect(JSON.stringify(issues)).not.toContain("T1-");
  });

  it("returns centralized demo risks and answer-bound evidence", async () => {
    localStorage.setItem(DEMO_MODE_KEY, "true");
    const risks = await getDemoResponse("/api/stored/analytics/projects/DEMO/risks", {});
    const answer = await getDemoResponse("/api/rag/projects/DEMO/ask", {
      method: "POST",
      body: JSON.stringify({ question: "Which issue covers pagination?" }),
    });

    expect(JSON.stringify(risks)).toContain("blocked_work");
    expect(JSON.stringify(answer)).toContain("demo-chunk-DEMO-105");
  });
});
