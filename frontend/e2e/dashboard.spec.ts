import { test, expect } from "@playwright/test";

// Shared login helper
async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/이메일/i).fill(
    process.env.E2E_TEST_EMAIL ?? "e2e@example.com"
  );
  await page.getByLabel(/비밀번호/i).fill(
    process.env.E2E_TEST_PASSWORD ?? "TestPass123!"
  );
  await page.getByRole("button", { name: /로그인/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 10000 });
}

test.describe("Dashboard", () => {
  test.skip(!process.env.E2E_TEST_EMAIL, "E2E_TEST_EMAIL not set — skipping authenticated tests");

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("dashboard loads with summary cards", async ({ page }) => {
    await expect(page).toHaveURL(/\/dashboard/);
    // 총 자산 카드가 존재해야 함
    await expect(page.getByText(/총 자산|Total/i)).toBeVisible({ timeout: 10000 });
  });

  test("sidebar navigation works", async ({ page }) => {
    // 분석 링크 클릭
    await page.getByRole("link", { name: /분석|Analytics/i }).first().click();
    await expect(page).toHaveURL(/\/analytics/);
  });

  test("stock search modal opens with Cmd+K", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 3000 });
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });
});

test.describe("Dashboard (unauthenticated)", () => {
  test("redirects to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects analytics to login", async ({ page }) => {
    await page.goto("/dashboard/analytics");
    await expect(page).toHaveURL(/\/login/);
  });
});
