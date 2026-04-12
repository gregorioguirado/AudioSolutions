import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import LoginForm from "../../src/components/LoginForm";

describe("LoginForm", () => {
  it("renders email and password fields", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<LoginForm />);
    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
  });

  it("renders a link to signup", () => {
    render(<LoginForm />);
    expect(screen.getByRole("link", { name: /sign up/i })).toBeInTheDocument();
  });
});
