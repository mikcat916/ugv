const { test, expect } = require("@playwright/test");
const { gotoPage } = require("../fixtures/auth");

function dashboardPayload() {
  return {
    data: {
      site: {
        name: "机器人巡检指挥中心",
        city: "测试园区",
        center: [113.584411, 22.349433],
        zoom: 17.2,
      },
      generatedAt: "2026-07-06T10:00",
      counts: { robots: 0, tasks: 0, alerts: 0, reports: 0 },
      robots: [],
      tasks: [],
      alerts: [],
      reports: [],
      maintenance: [],
    },
  };
}

async function canvasPositionForWorld(page, x, y) {
  return page.locator("#simulator-canvas").evaluate((canvas, point) => {
    const rect = canvas.getBoundingClientRect();
    const field = { width: 10, height: 7 };
    const pad = 24;
    const scale = Math.min((rect.width - pad * 2) / field.width, (rect.height - pad * 2) / field.height);
    return {
      x: (rect.width - field.width * scale) / 2 + point.x * scale,
      y: (rect.height - field.height * scale) / 2 + point.y * scale,
    };
  }, { x, y });
}

async function clickWorld(page, x, y) {
  const position = await canvasPositionForWorld(page, x, y);
  await page.locator("#simulator-canvas").click({ position });
}

test.describe("simulator 页面", () => {
  test("按钮操作会更新状态和重绘画布", async ({ page }) => {
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await page.route("**/api/dashboard", async (route) => {
      await route.fulfill({ json: dashboardPayload() });
    });

    await gotoPage(page, "/simulator", "仿真");
    const canvas = page.locator("#simulator-canvas");
    await expect(canvas).toBeVisible();
    const before = await canvas.evaluate((node) => node.toDataURL());

    await page.getByRole("button", { name: "添加矩形障碍物" }).click();
    await expect.poll(() => canvas.evaluate((node) => node.toDataURL())).not.toBe(before);
    await expect(page.locator("#sim-events")).toContainText("添加矩形障碍物");

    await clickWorld(page, 2.2, 3.5);
    await expect(page.locator("#sim-live-strip")).toContainText("路径可用");

    await page.getByRole("button", { name: "开始仿真" }).click();
    await expect(page.locator("#sim-status-grid")).toContainText("auto_running");
    await expect(page.locator("#sim-events")).toContainText("开始仿真");
    expect(pageErrors).toEqual([]);
  });

  test("点击目标点后规划路径并到达目标", async ({ page }) => {
    await page.route("**/api/dashboard", async (route) => {
      await route.fulfill({ json: dashboardPayload() });
    });

    await gotoPage(page, "/simulator", "仿真");
    await clickWorld(page, 2.05, 3.5);

    await expect(page.locator("#sim-live-strip")).toContainText("路径可用");
    await page.getByRole("button", { name: "开始仿真" }).click();
    await expect(page.locator("#sim-status-grid")).toContainText("auto_running");
    await expect(page.locator("#sim-status-grid")).toContainText("已到达", { timeout: 12000 });
    await expect(page.locator("#sim-events")).toContainText("已到达目标点");
  });

  test("目标落在障碍物膨胀区时显示不可达", async ({ page }) => {
    await page.route("**/api/dashboard", async (route) => {
      await route.fulfill({ json: dashboardPayload() });
    });

    await gotoPage(page, "/simulator", "仿真");
    await clickWorld(page, 4.2, 3.5);

    await expect(page.locator("#sim-live-strip")).toContainText("目标不可达");
    await expect(page.locator("#sim-target-card")).toContainText("目标点位于障碍物膨胀区");
  });
});
