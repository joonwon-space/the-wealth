import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// Mock api
vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

// Mock auth store
const mockLogin = vi.fn();
vi.mock("@/store/auth", () => ({
  useAuthStore: (selector: (s: { login: typeof mockLogin }) => unknown) =>
    selector({ login: mockLogin }),
}));

import LoginPage from "./page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form with email and password fields", () => {
    render(<LoginPage />);
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
    expect(screen.getByText("로그인")).toBeInTheDocument();
  });

  it("shows THE WEALTH branding", () => {
    render(<LoginPage />);
    expect(screen.getByText("THE WEALTH")).toBeInTheDocument();
  });

  it("has a link to register page", () => {
    render(<LoginPage />);
    const link = screen.getByText("회원가입");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/register");
  });

  it("updates input values on change", () => {
    render(<LoginPage />);
    const emailInput = screen.getByPlaceholderText("you@example.com") as HTMLInputElement;
    const passwordInput = screen.getByPlaceholderText("••••••••") as HTMLInputElement;

    fireEvent.change(emailInput, { target: { value: "test@test.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    expect(emailInput.value).toBe("test@test.com");
    expect(passwordInput.value).toBe("password123");
  });
});
