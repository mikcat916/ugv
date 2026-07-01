const path = require("path");
const { defineConfig, devices } = require("@playwright/test");

const baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:8000";

module.exports = defineConfig({
  testDir: path.join(__dirname, "tests"),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ["list"],
    ["html", { outputFolder: path.join(__dirname, "playwright-report"), open: "never" }],
  ],
  use: {
    baseURL,
    viewport: { width: 1440, height: 960 },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.spec\.js/,
    },
    {
      name: "chromium",
      testIgnore: /auth\.setup\.spec\.js/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: path.join(__dirname, ".auth", "admin.json"),
      },
      dependencies: ["setup"],
    },
  ],
});
