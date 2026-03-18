import { test, expect } from "@playwright/test";

const TEST_EMAIL = process.env.E2E_TEST_EMAIL ?? "e2e@example.com";
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD ?? "TestPass123!";

test.describe("Authentication flow", () => {
  test("login page loads correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveTitle(/THE WEALTH/i);
    await expect(page.getByLabel(/이메일/i)).toBeVisible();
    await expect(page.getByLabel(/비밀번호/i)).toBeVisible();
  });

  test("shows error on invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/이메일/i).fill("wrong@example.com");
    await page.getByLabel(/비밀번호/i).fill("wrongpassword");
    await page.getByRole("button", { name: /로그인/i }).click();
    await expect(page.getByText(/로그인에 실패|이메일 또는 비밀번호|오류/i)).toBeVisible({ timeout: 5000 });
  });

  test("register page loads correctly", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByLabel(/이메일/i)).toBeVisible();
    await expect(page.getByLabel(/비밀번호/i)).toBeVisible();
  });

  test("redirects to login when accessing protected route", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});
