const { test, expect } = require("@playwright/test");
const { gotoPage } = require("../fixtures/auth");

function dashboardPayload(robots) {
  return {
    data: {
      site: {
        name: "机器人巡检指挥中心",
        city: "测试园区",
        center: [113.584411, 22.349433],
        zoom: 17.2,
      },
      generatedAt: "2026-07-06T10:00",
      counts: { robots: robots.length, tasks: 0, alerts: 0, reports: 0 },
      robots,
      tasks: [],
      alerts: [],
      reports: [],
      maintenance: [],
    },
  };
}

test.describe("autopilot 页面", () => {
  test("有 IP 的离线机器人仍可下发自动驾驶动作", async ({ page }) => {
    const requests = [];
    await page.route("**/api/dashboard", async (route) => {
      await route.fulfill({
        json: dashboardPayload([
          {
            id: 4,
            model: "巡检机器人-02",
            ipAddress: "192.168.31.198",
            networkStatus: "offline",
            telemetryStatus: "online",
          },
        ]),
      });
    });
    await page.route("**/api/autopilot/status**", async (route) => {
      await route.fulfill({
        json: {
          ok: true,
          mode: "manual",
          safe: true,
          reason: "manual_control",
          linearX: 0,
          angularZ: 0,
          manualOverride: false,
          estop: false,
          lidar: { online: false },
          safety: {},
          deadman: {},
          events: [],
        },
      });
    });
    await page.route("**/api/autopilot/start", async (route) => {
      requests.push(route.request().postDataJSON());
      await route.fulfill({
        json: {
          ok: true,
          mode: "auto_ready",
          safe: false,
          reason: "lidar_timeout",
          linearX: 0,
          angularZ: 0,
          manualOverride: false,
          estop: false,
          robotId: 4,
          lidar: { online: false },
          safety: {},
          deadman: {},
          events: [],
        },
      });
    });

    await gotoPage(page, "/autopilot", "自动驾驶");
    await expect(page.getByRole("button", { name: "启动自动驾驶", exact: true })).toBeEnabled();
    await expect(page.getByRole("button", { name: "急停", exact: true })).toBeEnabled();

    await page.getByRole("button", { name: "启动自动驾驶", exact: true }).click();
    await expect.poll(() => requests.at(-1)?.robotId).toBe("4");
    await expect(page.locator(".autopilot-banner")).toContainText("LiDAR");
  });
});
