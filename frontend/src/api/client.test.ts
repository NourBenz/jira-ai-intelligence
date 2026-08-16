import { afterEach, describe, expect, it } from "vitest";

import { clearStoredToken, getStoredToken, storeToken } from "./client";

describe("API token storage", () => {
  afterEach(clearStoredToken);

  it("keeps the access token in session storage", () => {
    storeToken("signed-token");
    expect(getStoredToken()).toBe("signed-token");
  });
});
