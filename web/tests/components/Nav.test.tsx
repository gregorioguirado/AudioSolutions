import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Nav from "../../src/components/Nav";

describe("Nav", () => {
  it("renders the Showfier brand mark", () => {
    render(<Nav />);
    expect(screen.getByText(/showfier/i)).toBeInTheDocument();
  });

  it("renders Login and Sign up links", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign up/i })).toBeInTheDocument();
  });

  it("renders anchor links for How it works, Pricing, FAQ", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /how it works/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pricing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /faq/i })).toBeInTheDocument();
  });
});
