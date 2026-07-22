const fs = require("fs");
const path = require("path");
const { test } = require("@playwright/test");
const { loginAsAdmin, storageStatePath } = require("../fixtures/auth");

test("login and persist storage state", async ({ page }) => {
  fs.mkdirSync(path.dirname(storageStatePath), { recursive: true });
  await loginAsAdmin(page);
  await page.context().storageState({ path: storageStatePath });
});
