import { describe, expect, it } from "vitest";

import { hasNewCompletedSync } from "./syncFreshness";

describe("sync freshness detection", () => {
  it("does not announce the initial state or an unchanged sync", () => {
    expect(hasNewCompletedSync(undefined, 7)).toBe(false);
    expect(hasNewCompletedSync(7, 7)).toBe(false);
  });

  it("detects a newly completed shared synchronization", () => {
    expect(hasNewCompletedSync(7, 8)).toBe(true);
  });
});
