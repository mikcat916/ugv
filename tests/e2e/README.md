# Playwright E2E 骨架

这套骨架用于测试 Project4 的 Web 后台界面，默认目标是本地 FastAPI 服务：

`http://127.0.0.1:8000`

## 目录

- `playwright.config.js`：Playwright 主配置
- `fixtures/auth.js`：登录与页面导航辅助函数
- `tests/auth.setup.spec.js`：预登录并生成 `storageState`
- `tests/*.spec.js`：按业务页面划分的骨架用例

## 运行前提

1. 启动后端服务
2. 保证可用账号存在
3. 如需改地址或账号，使用环境变量覆盖

## 支持的环境变量

- `E2E_BASE_URL`
  默认：`http://127.0.0.1:8000`
- `E2E_USERNAME`
  默认：`admin`
- `E2E_PASSWORD`
  默认：`admin123`
- `E2E_ALLOW_DESTRUCTIVE`
  设为 `1` 时才执行创建、删除、批量删除等破坏性骨架用例

## 安装

```powershell
cd E:\Code\Project4\tests\e2e
npm install
npx playwright install
```

## 运行

```powershell
cd E:\Code\Project4\tests\e2e
npm test
```

只跑冒烟：

```powershell
npm run test:smoke
```

有头模式：

```powershell
npm run test:headed
```

## 设计说明

- 选择器优先使用 `getByRole`、`getByLabel`、`getByPlaceholder`
- 需要真实测试数据的用例默认不执行，只保留骨架
- 登录通过 `setup project` 统一生成会话，避免每条用例重复登录
