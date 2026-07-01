const { test, expect } = require("@playwright/test");

test.describe("基础冒烟", () => {
  test("未登录访问 overview 会跳转到登录页", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/overview", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "机器人巡检平台" })).toBeVisible();
  });

  test("已登录后可以看到核心导航", async ({ page }) => {
    await page.goto("/overview", { waitUntil: "domcontentloaded" });
    await expect(page.locator('[data-page-link="overview"]')).toBeVisible();
    await expect(page.locator('[data-page-link="reports"]')).toBeVisible();
    await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
  });
});
