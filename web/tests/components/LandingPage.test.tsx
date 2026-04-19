import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HowItWorks from "../../src/components/HowItWorks";
import WhatTranslates from "../../src/components/WhatTranslates";
import PricingTeaser from "../../src/components/PricingTeaser";
import FAQ from "../../src/components/FAQ";
import Footer from "../../src/components/Footer";

describe("HowItWorks", () => {
  it("renders the three steps", () => {
    render(<HowItWorks />);
    expect(screen.getByText(/1\. Drop/)).toBeInTheDocument();
    expect(screen.getByText(/2\. Translate/)).toBeInTheDocument();
    expect(screen.getByText(/3\. Download/)).toBeInTheDocument();
  });
});

describe("WhatTranslates", () => {
  it("renders both columns", () => {
    render(<WhatTranslates />);
    expect(screen.getByText(/what translates/i)).toBeInTheDocument();
    expect(screen.getByText(/what doesn't/i)).toBeInTheDocument();
  });
});

describe("PricingTeaser", () => {
  it("renders three tiers", () => {
    render(<PricingTeaser />);
    expect(screen.getByText(/free/i)).toBeInTheDocument();
    expect(screen.getByText(/pro/i)).toBeInTheDocument();
    expect(screen.getByText(/team/i)).toBeInTheDocument();
  });
});

describe("FAQ", () => {
  it("renders all six questions", () => {
    render(<FAQ />);
    expect(screen.getByText(/safe to load/i)).toBeInTheDocument();
    expect(screen.getByText(/consoles are supported/i)).toBeInTheDocument();
    expect(screen.getByText(/premium rack/i)).toBeInTheDocument();
    expect(screen.getByText(/file stored/i)).toBeInTheDocument();
    expect(screen.getByText(/try it before/i)).toBeInTheDocument();
    expect(screen.getByText(/who built/i)).toBeInTheDocument();
  });
});

describe("Footer", () => {
  it("renders the brand and copyright links", () => {
    render(<Footer />);
    expect(screen.getByText(/showfier/i)).toBeInTheDocument();
    expect(screen.getByText(/privacy/i)).toBeInTheDocument();
  });
});
