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
      generatedAt: "2026-05-21T10:00",
      counts: { robots: robots.length, tasks: 0, alerts: 0, reports: 0 },
      robots,
      tasks: [],
      alerts: [],
      reports: [],
      maintenance: [],
    },
  };
}

async function mockDashboard(page, robots) {
  await page.route("**/api/dashboard", async (route) => {
    await route.fulfill({ json: dashboardPayload(robots) });
  });
}

test.describe("control 页面", () => {
  test("默认选择在线且有 IP 的机器人，并在检测连接时携带 robotId", async ({ page }) => {
    const requests = [];
    await mockDashboard(page, [
      { id: 1, model: "巡检机器人-01", ipAddress: "192.168.31.198", networkStatus: "online", lastSeenAt: "2026-05-21T09:58" },
      { id: 2, model: "巡检机器人-02", ipAddress: "192.168.31.199", networkStatus: "offline", lastSeenAt: "2026-05-21T09:50" },
    ]);
    await page.route("**/api/robot-control/status**", async (route) => {
      requests.push(route.request().url());
      await route.fulfill({ json: { ok: true, target: { robotId: 1 }, response: { type: "pong", ok: true } } });
    });

    await gotoPage(page, "/control", "远程遥控");
    await expect(page.locator("#control-robot")).toHaveValue("1");
    await page.getByRole("button", { name: "检测连接" }).click();

    await expect.poll(() => requests.at(-1) || "").toContain("robotId=1");
    await expect(page.locator("#control-status")).toContainText("控制服务连接正常");
  });

  test("没有可控机器人时禁用运动和急停按钮", async ({ page }) => {
    await mockDashboard(page, [
      { id: 1, model: "未配置 IP 机器人", ipAddress: "", networkStatus: "online" },
    ]);

    await gotoPage(page, "/control", "远程遥控");

    await expect(page.locator("#control-robot")).toBeDisabled();
    await expect(page.getByRole("button", { name: "前进" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "急停" })).toBeDisabled();
  });

  test("切换机器人后，急停和方向指令使用新的 robotId", async ({ page }) => {
    const commandBodies = [];
    const stopBodies = [];
    await mockDashboard(page, [
      { id: 1, model: "巡检机器人-01", ipAddress: "192.168.31.198", networkStatus: "online" },
      { id: 2, model: "巡检机器人-02", ipAddress: "192.168.31.199", networkStatus: "online" },
    ]);
    await page.route("**/api/robot-control/cmd_vel", async (route) => {
      commandBodies.push(route.request().postDataJSON());
      await route.fulfill({ json: { ok: true, target: { robotId: 2 }, response: { type: "ack", ok: true } } });
    });
    await page.route("**/api/robot-control/stop", async (route) => {
      stopBodies.push(route.request().postDataJSON());
      await route.fulfill({ json: { ok: true, target: { robotId: 2 }, response: { type: "ack", ok: true } } });
    });

    await gotoPage(page, "/control", "远程遥控");
    await page.locator("#control-robot").selectOption("2");
    await page.getByRole("button", { name: "前进" }).dispatchEvent("pointerdown");
    await expect.poll(() => commandBodies.at(-1)?.robotId || "").toBe("2");
    await page.getByRole("button", { name: "前进" }).dispatchEvent("pointerup");
    await expect.poll(() => stopBodies.at(-1)?.robotId || "").toBe("2");

    await page.getByRole("button", { name: "急停" }).click();
    await expect.poll(() => stopBodies.at(-1)?.robotId || "").toBe("2");
  });
});
