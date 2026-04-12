import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import SignupForm from "../../src/components/SignupForm";

describe("SignupForm", () => {
  it("renders email and password fields", () => {
    render(<SignupForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<SignupForm />);
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("renders a link to login", () => {
    render(<SignupForm />);
    expect(screen.getByRole("link", { name: /log in/i })).toBeInTheDocument();
  });
});
