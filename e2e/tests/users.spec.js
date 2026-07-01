const { test, expect } = require("@playwright/test");
const { gotoPage } = require("../fixtures/auth");

test.describe("users 页面", () => {
  test("新增用户弹窗可以不填必填项直接取消", async ({ page }) => {
    await gotoPage(page, "/users", "用户管理");
    await page.getByRole("button", { name: "新增用户" }).click();
    await expect(page.locator("#crud-modal")).toBeVisible();

    await page.locator('#crud-modal button[type="submit"][formnovalidate]').last().click();
    await expect(page.locator("#crud-modal")).not.toBeVisible();
  });

  test("新增用户弹窗可以通过右上角关闭按钮直接关闭", async ({ page }) => {
    await gotoPage(page, "/users", "用户管理");
    await page.getByRole("button", { name: "新增用户" }).click();
    await expect(page.locator("#crud-modal")).toBeVisible();

    await page.locator('.modal-header button[formnovalidate]').click();
    await expect(page.locator("#crud-modal")).not.toBeVisible();
  });
});
