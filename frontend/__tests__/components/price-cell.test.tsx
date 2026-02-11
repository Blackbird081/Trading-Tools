import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceCell } from "@/components/price-cell";

describe("PriceCell", () => {
  it("renders price with 2 decimal places", () => {
    render(<PriceCell value={98.5} />);
    expect(screen.getByText("98.50")).toBeInTheDocument();
  });

  it("applies green class for positive change", () => {
    render(<PriceCell value={98.5} change={1.2} />);
    const el = screen.getByText("98.50");
    expect(el).toHaveClass("text-emerald-400");
  });

  it("applies red class for negative change", () => {
    render(<PriceCell value={72.0} change={-0.5} />);
    const el = screen.getByText("72.00");
    expect(el).toHaveClass("text-rose-400");
  });

  it("applies fuchsia class for ceiling price", () => {
    render(<PriceCell value={105.4} isCeiling />);
    const el = screen.getByText("105.40");
    expect(el).toHaveClass("text-fuchsia-400");
  });

  it("applies cyan class for floor price", () => {
    render(<PriceCell value={86.8} isFloor />);
    const el = screen.getByText("86.80");
    expect(el).toHaveClass("text-cyan-400");
  });

  it("renders dash for null value", () => {
    render(<PriceCell value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders dash for undefined value", () => {
    render(<PriceCell value={undefined} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
