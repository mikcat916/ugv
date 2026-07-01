const path = require("path");
const { expect } = require("@playwright/test");

const credentials = {
  username: process.env.E2E_USERNAME || "admin",
  password: process.env.E2E_PASSWORD || "admin123",
};

const storageStatePath = path.join(__dirname, "..", ".auth", "admin.json");

async function loginAsAdmin(page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "机器人巡检平台" })).toBeVisible();
  await page.getByLabel("用户名").fill(credentials.username);
  await page.getByLabel("密码").fill(credentials.password);
  await page.locator('#login-form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/overview$/);
  await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
}

async function gotoPage(page, route, expectedHeading) {
  await page.goto(route, { waitUntil: "domcontentloaded" });
  await expect(page.locator("h1").filter({ hasText: expectedHeading })).toBeVisible();
}

function destructiveTestsEnabled() {
  return process.env.E2E_ALLOW_DESTRUCTIVE === "1";
}

module.exports = {
  credentials,
  destructiveTestsEnabled,
  gotoPage,
  loginAsAdmin,
  storageStatePath,
};
