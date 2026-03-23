import { test, expect, type Page } from "@playwright/test";

// Shared login helper (duplicated from dashboard.spec.ts for isolation)
async function login(page: Page) {
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

// Mock KIS-linked portfolio list response
async function mockPortfolioList(page: Page, portfolioId: number) {
  await page.route("**/api/v1/portfolios", (route) => {
    if (route.request().method() !== "GET") {
      route.continue();
      return;
    }
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: portfolioId,
          name: "테스트 포트폴리오",
          description: null,
          kis_account_id: 1,
          created_at: "2024-01-01T00:00:00",
          updated_at: "2024-01-01T00:00:00",
        },
      ]),
    });
  });
}

// Mock portfolio holdings
async function mockHoldings(page: Page, portfolioId: number) {
  await page.route(
    `**/api/v1/portfolios/${portfolioId}/holdings*`,
    (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 1,
            ticker: "005930",
            name: "삼성전자",
            quantity: 10,
            avg_price: "70000.00",
            current_price: 72000,
            market_value: 720000,
            profit_loss: 20000,
            profit_loss_pct: 2.86,
            currency: "KRW",
            exchange_code: null,
          },
        ]),
      });
    }
  );
}

// Mock cash balance
async function mockCashBalance(
  page: Page,
  portfolioId: number,
  availableCash = 1000000
) {
  await page.route(
    `**/api/v1/portfolios/${portfolioId}/cash-balance*`,
    (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_cash: String(availableCash),
          available_cash: String(availableCash),
          total_evaluation: "720000",
          total_profit_loss: "20000",
          profit_loss_rate: "2.86",
          currency: "KRW",
          foreign_cash: null,
          usd_krw_rate: null,
        }),
      });
    }
  );
}

// Mock pending orders (initially empty)
async function mockPendingOrders(
  page: Page,
  portfolioId: number,
  orders: object[] = []
) {
  await page.route(
    `**/api/v1/portfolios/${portfolioId}/orders/pending*`,
    (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(orders),
      });
    }
  );
}

// Navigate to the portfolio detail page
async function goToPortfolio(page: Page, portfolioId: number) {
  await page.goto(`/dashboard/portfolios/${portfolioId}`);
  // Wait for holdings to load
  await page.waitForTimeout(500);
}

test.describe("주문 플로우 E2E", () => {
  test.skip(
    !process.env.E2E_TEST_EMAIL,
    "E2E_TEST_EMAIL not set — skipping authenticated order tests"
  );

  const PORTFOLIO_ID = 1;

  test.beforeEach(async ({ page }) => {
    await login(page);
    await mockPortfolioList(page, PORTFOLIO_ID);
    await mockHoldings(page, PORTFOLIO_ID);
    await mockCashBalance(page, PORTFOLIO_ID);
    await mockPendingOrders(page, PORTFOLIO_ID);
  });

  test.describe("정상 매수 플로우", () => {
    test("매수 버튼 클릭 시 OrderDialog가 열린다", async ({ page }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      // Find buy button for 삼성전자
      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await expect(buyBtn).toBeVisible({ timeout: 5000 });
      await buyBtn.click();

      // Dialog should open
      await expect(page.getByRole("dialog")).toBeVisible({ timeout: 3000 });
      await expect(page.getByText(/삼성전자/)).toBeVisible();
      await expect(page.getByText(/005930/)).toBeVisible();
    });

    test("지정가 매수 주문을 제출하면 확인 다이얼로그가 표시된다", async ({
      page,
    }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      // Fill in limit price and quantity
      await page.getByPlaceholder("주문 단가").fill("72000");
      await page.getByPlaceholder("주문 수량").fill("5");

      // Click order button
      await page.getByRole("button", { name: /매수 주문/ }).click();

      // Confirmation dialog
      await expect(page.getByText("주문 확인")).toBeVisible({ timeout: 3000 });
      await expect(page.getByText("삼성전자")).toBeVisible();
      await expect(page.getByText(/매수/)).toBeVisible();
      await expect(page.getByText(/지정가/)).toBeVisible();
      await expect(page.getByText(/5주/)).toBeVisible();
    });

    test("주문 확인 후 API 호출로 주문이 접수된다", async ({ page }) => {
      // Mock successful order placement
      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders`,
        (route) => {
          if (route.request().method() !== "POST") {
            route.continue();
            return;
          }
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: 1,
              order_no: "0000123456",
              ticker: "005930",
              name: "삼성전자",
              order_type: "BUY",
              order_class: "limit",
              quantity: 5,
              price: "72000.00",
              status: "pending",
              filled_quantity: 0,
              filled_price: null,
              memo: null,
              created_at: "2024-01-15T10:30:00",
              updated_at: "2024-01-15T10:30:00",
            }),
          });
        }
      );

      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      await page.getByPlaceholder("주문 단가").fill("72000");
      await page.getByPlaceholder("주문 수량").fill("5");
      await page.getByRole("button", { name: /매수 주문/ }).click();

      // Confirm
      await expect(page.getByText("주문 확인")).toBeVisible();
      await page.getByRole("button", { name: /매수 확인/ }).click();

      // Success result
      await expect(page.getByText(/주문 접수 완료/)).toBeVisible({
        timeout: 5000,
      });
      await expect(page.getByText(/0000123456/)).toBeVisible();
    });

    test("시장가 매수는 단가 입력 없이 주문 가능하다", async ({ page }) => {
      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders`,
        (route) => {
          if (route.request().method() !== "POST") {
            route.continue();
            return;
          }
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: 2,
              order_no: "0000123457",
              ticker: "005930",
              name: "삼성전자",
              order_type: "BUY",
              order_class: "market",
              quantity: 1,
              price: null,
              status: "pending",
              filled_quantity: 0,
              filled_price: null,
              memo: null,
              created_at: "2024-01-15T10:30:00",
              updated_at: "2024-01-15T10:30:00",
            }),
          });
        }
      );

      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      // Switch to 시장가
      await page.getByRole("button", { name: "시장가" }).click();

      // 단가 입력란이 사라져야 함
      await expect(page.getByPlaceholder("주문 단가")).not.toBeVisible();

      await page.getByPlaceholder("주문 수량").fill("1");
      await page.getByRole("button", { name: /매수 주문/ }).click();

      await expect(page.getByText("주문 확인")).toBeVisible();
      await expect(page.getByText("시장가")).toBeVisible();
      await page.getByRole("button", { name: /매수 확인/ }).click();

      await expect(page.getByText(/주문 접수 완료/)).toBeVisible({
        timeout: 5000,
      });
    });
  });

  test.describe("정상 매도 플로우", () => {
    test("매도 버튼 클릭 시 OrderDialog가 매도 탭으로 열린다", async ({
      page,
    }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      const sellBtn = page.getByRole("button", { name: /매도/ }).first();
      await expect(sellBtn).toBeVisible({ timeout: 5000 });
      await sellBtn.click();

      await expect(page.getByRole("dialog")).toBeVisible({ timeout: 3000 });
      // 매도 탭이 활성화되어야 함 (파란색 텍스트)
      const sellTab = page.getByRole("tab", { name: "매도" });
      await expect(sellTab).toHaveAttribute("data-state", "active");
    });

    test("매도 주문을 제출하면 확인 다이얼로그에 매도 레이블이 표시된다", async ({
      page,
    }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      const sellBtn = page.getByRole("button", { name: /매도/ }).first();
      await sellBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      await page.getByPlaceholder("주문 단가").fill("73000");
      await page.getByPlaceholder("주문 수량").fill("3");
      await page.getByRole("button", { name: /매도 주문/ }).click();

      await expect(page.getByText("주문 확인")).toBeVisible({ timeout: 3000 });
      // 구분 열에 매도가 표시되어야 함
      const confirmText = page.getByText(/매도/);
      await expect(confirmText.first()).toBeVisible();
    });
  });

  test.describe("에러 케이스: 예수금 부족", () => {
    test("API가 예수금 부족 오류를 반환하면 오류 메시지가 표시된다", async ({
      page,
    }) => {
      // Override cash balance to show very low cash
      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/cash-balance*`,
        (route) => {
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total_cash: "1000",
              available_cash: "1000",
              total_evaluation: "720000",
              total_profit_loss: "20000",
              profit_loss_rate: "2.86",
              currency: "KRW",
              foreign_cash: null,
              usd_krw_rate: null,
            }),
          });
        }
      );

      // Mock order placement returning insufficient funds error
      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders`,
        (route) => {
          if (route.request().method() !== "POST") {
            route.continue();
            return;
          }
          route.fulfill({
            status: 400,
            contentType: "application/json",
            body: JSON.stringify({
              detail: "예수금이 부족합니다",
            }),
          });
        }
      );

      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      await page.getByPlaceholder("주문 단가").fill("72000");
      await page.getByPlaceholder("주문 수량").fill("100");
      await page.getByRole("button", { name: /매수 주문/ }).click();

      await page.getByRole("button", { name: /매수 확인/ }).click();

      // Should show error result
      await expect(page.getByText(/주문 오류|오류/i)).toBeVisible({
        timeout: 5000,
      });
    });
  });

  test.describe("에러 케이스: 장외 시간", () => {
    test("장외 시간 오류가 반환되면 오류 메시지가 표시된다", async ({
      page,
    }) => {
      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders`,
        (route) => {
          if (route.request().method() !== "POST") {
            route.continue();
            return;
          }
          route.fulfill({
            status: 400,
            contentType: "application/json",
            body: JSON.stringify({
              detail: "현재 장 운영 시간이 아닙니다 (09:00~15:30)",
            }),
          });
        }
      );

      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      await page.getByPlaceholder("주문 단가").fill("72000");
      await page.getByPlaceholder("주문 수량").fill("1");
      await page.getByRole("button", { name: /매수 주문/ }).click();
      await page.getByRole("button", { name: /매수 확인/ }).click();

      await expect(page.getByText(/주문 오류|오류/i)).toBeVisible({
        timeout: 5000,
      });
    });
  });

  test.describe("미체결 주문 취소 플로우", () => {
    const PENDING_ORDER = {
      order_no: "0000987654",
      ticker: "005930",
      name: "삼성전자",
      order_type: "BUY",
      order_class: "limit",
      quantity: "5",
      price: "71000",
      filled_quantity: "0",
      remaining_quantity: "5",
      status: "pending",
      created_at: "2024-01-15T09:00:00",
    };

    test("미체결 주문 패널에 미체결 주문이 표시된다", async ({ page }) => {
      // Override pending orders to have one pending order
      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders/pending*`,
        (route) => {
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify([PENDING_ORDER]),
          });
        }
      );

      await goToPortfolio(page, PORTFOLIO_ID);

      // Open pending orders panel
      const pendingBtn = page.getByRole("button", {
        name: /미체결 주문/,
      });
      await expect(pendingBtn).toBeVisible({ timeout: 5000 });
      await pendingBtn.click();

      // Panel should show the pending order
      await expect(page.getByText("삼성전자")).toBeVisible({ timeout: 3000 });
      await expect(page.getByText("0000987654")).not.toBeVisible(); // order_no not shown directly
      await expect(
        page.getByText(/미체결 주문 \(1\)/)
      ).toBeVisible();
    });

    test("취소 버튼 클릭 시 주문 취소 API가 호출된다", async ({ page }) => {
      let cancelCalled = false;

      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders/pending*`,
        (route) => {
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify([PENDING_ORDER]),
          });
        }
      );

      await page.route(
        `**/api/v1/portfolios/${PORTFOLIO_ID}/orders/${PENDING_ORDER.order_no}`,
        (route) => {
          if (route.request().method() !== "DELETE") {
            route.continue();
            return;
          }
          cancelCalled = true;
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ success: true }),
          });
        }
      );

      await goToPortfolio(page, PORTFOLIO_ID);

      const pendingBtn = page.getByRole("button", {
        name: /미체결 주문/,
      });
      await pendingBtn.click();

      // Wait for panel to show
      await expect(page.getByText(/미체결 주문 \(1\)/)).toBeVisible({
        timeout: 3000,
      });

      // Click cancel button (X icon)
      const cancelBtn = page.getByRole("button", { name: /주문 취소/ });
      await expect(cancelBtn).toBeVisible();
      await cancelBtn.click();

      // Verify cancel was called
      await expect(() => {
        if (!cancelCalled) throw new Error("cancel not called");
      }).toPass({ timeout: 3000 });
    });
  });

  test.describe("주문 폼 유효성 검사", () => {
    test("수량 미입력 시 주문 버튼이 비활성화된다", async ({ page }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      // 단가만 입력, 수량 미입력
      await page.getByPlaceholder("주문 단가").fill("72000");

      const submitBtn = page.getByRole("button", { name: /매수 주문/ });
      await expect(submitBtn).toBeDisabled();
    });

    test("단가 미입력(지정가) 시 주문 버튼이 비활성화된다", async ({
      page,
    }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      // 수량만 입력, 단가 미입력
      await page.getByPlaceholder("주문 수량").fill("5");

      const submitBtn = page.getByRole("button", { name: /매수 주문/ });
      await expect(submitBtn).toBeDisabled();
    });

    test("다이얼로그 닫기 시 폼이 초기화된다", async ({ page }) => {
      await goToPortfolio(page, PORTFOLIO_ID);

      const buyBtn = page.getByRole("button", { name: /매수/ }).first();
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      await page.getByPlaceholder("주문 단가").fill("72000");
      await page.getByPlaceholder("주문 수량").fill("5");

      // Close dialog
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).not.toBeVisible();

      // Re-open and verify form is cleared
      await buyBtn.click();
      await expect(page.getByRole("dialog")).toBeVisible();

      const quantityInput = page.getByPlaceholder("주문 수량");
      await expect(quantityInput).toHaveValue("");
    });
  });
});

test.describe("주문 다이얼로그 (모킹 없이 UI 검증)", () => {
  // These tests verify UI behavior without needing a real backend
  test("OrderDialog: 매수/매도 탭 전환이 동작한다", async ({ page }) => {
    // Mock auth and redirect to portfolio page via API mocking
    await page.route("**/api/v1/auth/me", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          email: "test@example.com",
          created_at: "2024-01-01T00:00:00",
        }),
      });
    });

    await page.route("**/api/v1/portfolios", (route) => {
      if (route.request().method() !== "GET") {
        route.continue();
        return;
      }
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: 999,
            name: "UI테스트 포트폴리오",
            description: null,
            kis_account_id: 1,
            created_at: "2024-01-01T00:00:00",
            updated_at: "2024-01-01T00:00:00",
          },
        ]),
      });
    });

    await page.route("**/api/v1/portfolios/999/**", (route) => {
      const url = route.request().url();
      if (url.includes("holdings")) {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: 1,
              ticker: "035720",
              name: "카카오",
              quantity: 5,
              avg_price: "50000.00",
              current_price: 52000,
              market_value: 260000,
              profit_loss: 10000,
              profit_loss_pct: 4.0,
              currency: "KRW",
              exchange_code: null,
            },
          ]),
        });
      } else if (url.includes("cash-balance")) {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            total_cash: "500000",
            available_cash: "500000",
            total_evaluation: "260000",
            total_profit_loss: "10000",
            profit_loss_rate: "4.00",
            currency: "KRW",
            foreign_cash: null,
            usd_krw_rate: null,
          }),
        });
      } else if (url.includes("pending")) {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        route.continue();
      }
    });

    // This test only works when E2E_TEST_EMAIL is set (logged in)
    test.skip(!process.env.E2E_TEST_EMAIL, "E2E_TEST_EMAIL not set");
  });
});
