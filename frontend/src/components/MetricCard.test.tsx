import { render, screen } from "@testing-library/react";
import { Layers3 } from "lucide-react";
import { describe, expect, it } from "vitest";

import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("renders a metric value with its explanation", () => {
    render(<MetricCard label="Total issues" value={20} detail="19 currently open" icon={Layers3} />);

    expect(screen.getByText("Total issues")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("19 currently open")).toBeInTheDocument();
  });
});
