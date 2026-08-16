/** Verifies keyboard and button dismissal for focused modal workflows. */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Modal } from "./Modal";

describe("Modal", () => {
  it("renders an accessible dialog and closes from its close button", () => {
    const onClose = vi.fn();
    render(<Modal open title="Synchronization details" onClose={onClose}>Run details</Modal>);

    expect(screen.getByRole("dialog", { name: "Synchronization details" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close window" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes when Escape is pressed", () => {
    const onClose = vi.fn();
    render(<Modal open title="Team members" onClose={onClose}>Member list</Modal>);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });
});
