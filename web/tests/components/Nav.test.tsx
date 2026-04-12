import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Nav from "../../src/components/Nav";

vi.mock("../../src/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: null } }),
    },
  }),
}));

describe("Nav", () => {
  it("renders the Showfier brand mark", () => {
    render(<Nav />);
    expect(screen.getByText(/showfier/i)).toBeInTheDocument();
  });

  it("renders Login and Sign up links when logged out", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign up/i })).toBeInTheDocument();
  });

  it("renders anchor links for How it works, Pricing, FAQ when logged out", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /how it works/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pricing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /faq/i })).toBeInTheDocument();
  });
});
