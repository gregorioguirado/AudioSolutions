import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PricingTeaser from "../../src/components/PricingTeaser";

describe("PricingTeaser", () => {
  it("renders exactly 3 tiers with names Free / Pro / Team", () => {
    const { container } = render(<PricingTeaser />);

    // Exactly the three tier names — no Credits, no extra tiers.
    expect(screen.getByText(/^Free$/i)).toBeInTheDocument();
    expect(screen.getByText(/^Pro$/i)).toBeInTheDocument();
    expect(screen.getByText(/^Team$/i)).toBeInTheDocument();

    // No killed tier names anywhere in the rendered output.
    expect(screen.queryByText(/credits/i)).toBeNull();
    expect(screen.queryByText(/single credit/i)).toBeNull();
    expect(screen.queryByText(/credit pack/i)).toBeNull();
    expect(screen.queryByText(/enterprise/i)).toBeNull();

    // No killed price points / limits.
    expect(container.textContent).not.toMatch(/\$5\b/);
    expect(container.textContent).not.toMatch(/\$45\b/);
    expect(container.textContent).not.toMatch(/\$80\b/);
    expect(container.textContent).not.toMatch(/30 translations/i);

    // Exactly three tier cards: count tier-name labels in the grid.
    const tierLabels = screen.getAllByText(/^(Free|Pro|Team)$/i);
    expect(tierLabels).toHaveLength(3);
  });

  it("includes the new tier copy: $19/mo Pro, Contact us Team, 1 lifetime translation Free", () => {
    const { container } = render(<PricingTeaser />);

    expect(container.textContent).toMatch(/\$0/);
    expect(container.textContent).toMatch(/\$19\/mo/);
    expect(container.textContent).toMatch(/contact us/i);
    expect(container.textContent).toMatch(/1 lifetime translation/i);
    expect(container.textContent).toMatch(/unlimited translations/i);
    expect(container.textContent).toMatch(/multi-seat/i);
  });
});
