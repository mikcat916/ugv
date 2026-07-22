const { test, expect } = require("@playwright/test");
const { destructiveTestsEnabled, gotoPage } = require("../fixtures/auth");

test.describe("reports 页面", () => {
  test("展示报告列表和分页器", async ({ page }) => {
    await gotoPage(page, "/reports", "历史报告");
    await expect(page.locator("#page-content h2").filter({ hasText: "历史报告" })).toBeVisible();
    await expect(page.getByRole("button", { name: "上一页" })).toBeVisible();
    await expect(page.getByRole("button", { name: "下一页" })).toBeVisible();
  });

  test("创建报告骨架", async ({ page }) => {
    test.skip(!destructiveTestsEnabled(), "会写入报告数据，需要单独测试数据。");
    await gotoPage(page, "/reports", "历史报告");
    await page.locator('#report-form input[name="title"]').fill(`E2E 报告 ${Date.now()}`);
    await page.locator('#report-form input[name="value"]').fill("99%");
    await expect(page.locator('#report-form button[type="submit"]')).toBeVisible();
  });
});
