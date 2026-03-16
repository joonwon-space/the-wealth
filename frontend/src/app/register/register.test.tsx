import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

import RegisterPage from "./page";

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders register form with email and password fields", () => {
    render(<RegisterPage />);
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("8자 이상")).toBeInTheDocument();
    expect(screen.getByText("회원가입")).toBeInTheDocument();
  });

  it("shows THE WEALTH branding", () => {
    render(<RegisterPage />);
    expect(screen.getByText("THE WEALTH")).toBeInTheDocument();
  });

  it("has a link to login page", () => {
    render(<RegisterPage />);
    const link = screen.getByText("로그인");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/login");
  });

  it("password field has minLength of 8", () => {
    render(<RegisterPage />);
    const passwordInput = screen.getByPlaceholderText("8자 이상") as HTMLInputElement;
    expect(passwordInput.minLength).toBe(8);
  });
});
