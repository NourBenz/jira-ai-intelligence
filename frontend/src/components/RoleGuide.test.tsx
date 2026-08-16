/** Verifies that account guidance reflects effective project permissions. */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "../api/types";
import { RoleGuide } from "./RoleGuide";

describe("RoleGuide", () => {
  it("explains project-administrator actions and the read-only Jira boundary", () => {
    const user: CurrentUser = {
      id: 4,
      username: "t1-admin",
      role: "viewer",
      administered_project_keys: ["T1"],
    };

    render(<RoleGuide open projectKey="T1" user={user} welcome onClose={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: "Keep this project current" })).toBeInTheDocument();
    expect(screen.getByText("Project Administrator")).toBeInTheDocument();
    expect(screen.getByText("This platform is read-only.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open my workspace/i })).toBeInTheDocument();
  });
});
