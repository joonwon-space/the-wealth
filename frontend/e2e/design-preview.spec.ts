import { test, expect } from "@playwright/test";

// design-preview는 dev/test 환경에서만 접근 가능 (production은 middleware에서 404).
// 디자인 프리미티브 회귀 방지를 위한 라이트/다크 스크린샷 비교.
//
// 첫 실행 시 baseline이 자동 생성되며, 이후 실행에서 diff가 발생하면 fail한다.
// baseline 갱신: `npx playwright test --update-snapshots`

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/이메일/i).fill(
    process.env.E2E_TEST_EMAIL ?? "e2e@example.com",
  );
  await page.getByLabel(/비밀번호/i).fill(
    process.env.E2E_TEST_PASSWORD ?? "TestPass123!",
  );
  await page.getByRole("button", { name: /로그인/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 10000 });
}

test.describe("Design preview screenshot", () => {
  test.skip(
    !process.env.E2E_TEST_EMAIL,
    "E2E_TEST_EMAIL not set — skipping authenticated tests",
  );

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("light variant matches baseline", async ({ page }) => {
    await page.goto("/dashboard/design-preview");
    // light 모드 강제: html.dark 클래스 제거
    await page.evaluate(() => {
      document.documentElement.classList.remove("dark");
      document.documentElement.style.colorScheme = "light";
    });
    // 차트 애니메이션이 정착할 시간을 둔다
    await page.waitForTimeout(800);
    await expect(page).toHaveScreenshot("design-preview-light.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
      animations: "disabled",
    });
  });

  test("dark variant matches baseline", async ({ page }) => {
    await page.goto("/dashboard/design-preview");
    await page.evaluate(() => {
      document.documentElement.classList.add("dark");
      document.documentElement.style.colorScheme = "dark";
    });
    await page.waitForTimeout(800);
    await expect(page).toHaveScreenshot("design-preview-dark.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
      animations: "disabled",
    });
  });
});
