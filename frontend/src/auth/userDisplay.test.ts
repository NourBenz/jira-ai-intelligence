import { describe, expect, it } from "vitest";

import { canAdministerProject, effectiveInterfaceRole, userDisplayName, userInitials, userRoleLabel } from "./userDisplay";

describe("user display helpers", () => {
  it("uses a person's profile while preserving the internal role value", () => {
    const user = { id: 1, username: "nbenzarti", first_name: "Nour", last_name: "Benzarti", email: "nour@example.com", role: "viewer" as const, administered_project_keys: [] };

    expect(userDisplayName(user)).toBe("Nour Benzarti");
    expect(userInitials(user)).toBe("NB");
    expect(userRoleLabel(user, "T1")).toBe("Team Member");
    expect(effectiveInterfaceRole(user, "T1")).toBe("team_member");
    expect(canAdministerProject(user, "T1")).toBe(false);
  });

  it("falls back to the username and labels administrators clearly", () => {
    const user = { id: 2, username: "admin-demo", role: "admin" as const, administered_project_keys: [] };

    expect(userDisplayName(user)).toBe("admin-demo");
    expect(userInitials(user)).toBe("AD");
    expect(userRoleLabel(user, "T1")).toBe("Company Administrator");
    expect(canAdministerProject(user, "T1")).toBe(true);
  });

  it("derives project administration from the selected project", () => {
    const user = { id: 3, username: "t1-admin", role: "viewer" as const, administered_project_keys: ["T1"] };

    expect(userRoleLabel(user, "T1")).toBe("Project Administrator");
    expect(canAdministerProject(user, "T1")).toBe(true);
    expect(userRoleLabel(user, "T2")).toBe("Team Member");
    expect(canAdministerProject(user, "T2")).toBe(false);
  });
});
