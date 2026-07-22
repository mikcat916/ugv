# 2026-05-27 稳定化发布记录

## 发布范围

- 管理端能力收口：用户、设备、区域、区域控制、点位、路线、报告、设备管理、集群管理。
- 控制端能力收口：远程遥控、设备控制、集群控制、统一控制命令记录。
- 前端体验收口：导航分组、移动端折叠、管理页列表优先、控制页真实目标提示。
- 树莓派侧脚本补充：IoT 客户端 TLS 调试开关、TCP 控制服务脚本。

## 验证结果

- 后端核心回归：`156 passed`。
- 前端静态检查：`node --check apps/backend/static/dashboard.js` 通过。
- Playwright E2E：`12 passed, 3 skipped`，目标环境为 `https://192.168.31.169`。
- 远端服务：`project4-backend.service` 为 `active`，`mysql.service` 为 `active`。
- 远端页面：登录页返回 `200`，登录后 `/overview`、`/device-management`、`/cluster-management`、`/control`、`/device-control`、`/cluster-control` 均返回 `200`。

## 部署信息

- 服务器：`oneday@192.168.31.169`
- 部署目录：`/home/oneday/project4`
- 后端服务：`project4-backend.service`
- 备份目录：`/home/oneday/project4/.codex-backup-stabilization-20260527-105355`
- 依赖检查：`apps/backend/requirements.txt` 已在远端虚拟环境安装确认。

## 已知边界

- 本次只验收 Web 管理层到真实控制服务的链路，不把物理底盘运动作为发布通过条件。
- 控制服务不可达、车辆离线、目标缺失时必须暴露明确失败，不允许模拟成功。
- 远端 HTTPS 使用内网自签证书，自动化测试通过 `ignoreHTTPSErrors` 或禁用证书校验完成访问。
