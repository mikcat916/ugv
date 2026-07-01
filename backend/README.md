# 机器人巡检平台

这是一个基于 `FastAPI + Jinja2 + MySQL + 高德地图` 的机器人巡检管理后台，提供登录认证、任务管理、机器人状态查看、告警和报告管理、区域绘制、设备与点位维护，以及实时仪表盘能力。

## 功能概览

- 中文管理界面
- Session 登录认证
- MySQL 自动建库、建表和管理员初始化
- 总览、任务、报告、机器人、维护、区域等页面
- 用户、设备、区域、点位、路线管理
- REST API 与 WebSocket 实时更新
- 高德地图接入与浏览器定位
- 区域地图点选绘制
- 基础测试与健康检查

## 技术栈

- Python
- FastAPI
- Jinja2
- PyMySQL
- Uvicorn
- MySQL 8
- AMap Web JS API

## 目录结构

```text
backend/
|-- db/
|   `-- mysql_schema.sql
|-- static/
|   |-- dashboard.css
|   |-- dashboard.js
|   `-- login.js
|-- templates/
|   |-- app.html
|   `-- login.html
|-- tests/
|   |-- test_auth_ui.py
|   `-- test_robot_discovery.py
|-- .env
|-- main.py
|-- requirements.txt
`-- README.md
```

## 环境要求

- Python 3.11（推荐）
- MySQL 8.0+
- Windows PowerShell 或 Linux Shell

## 安装依赖

```powershell
cd E:\Code\Project4\backend
python -m pip install -r requirements.txt
```

## 环境变量

项目默认读取根目录或 `backend` 目录下的 `.env` 文件。

示例：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=robot_monitor
MYSQL_CHARSET=utf8mb4

SESSION_SECRET=dev-local-secret

ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_DISPLAY_NAME=系统管理员
AMAP_WEB_KEY=你的高德WebJSKey
ALLOW_SELF_REGISTER=0
```

说明：

- 首次启动会自动创建数据库和数据表。
- 如果管理员账号不存在，会自动初始化。
- `SESSION_SECRET=dev-local-secret` 和默认管理员账号仅限本地自用。
- 高德地图必须使用 `Web 端 JS API` 对应的 Key。
- `ALLOW_SELF_REGISTER=1` 时允许注册；默认关闭。

## 启动项目

推荐从仓库根目录启动：

```powershell
cd E:\Code\Project4
.\start-dev.ps1
```

手动启动：

```powershell
cd E:\Code\Project4\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

启动后访问：

- 本机访问：[http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- 健康检查：[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- 短健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- 调试配置（仅 `DEBUG=1`）：[http://127.0.0.1:8000/debug/config](http://127.0.0.1:8000/debug/config)

说明：

- 本地开发默认只监听 `127.0.0.1`。
- 需要局域网访问时再显式使用 `--host 0.0.0.0`。

## 本地数据库重置与测试数据

清空本地开发数据：

```powershell
mysql -u root -p robot_monitor < db\reset-db-dev.sql
python ..\scripts\create_database.py --with-device-pin
```

导入测试数据：

```powershell
mysql -u root -p robot_monitor < db\seed-dev.sql
```

## 默认账号

- 用户名：`admin`
- 密码：`admin123`

如果你已经在 `.env` 中修改过管理员配置，以 `.env` 为准。

## 页面路由

- `/overview`：总览
- `/tasks`：任务管理
- `/reports`：历史报告
- `/robots`：机器人状态
- `/maintenance`：设备维护
- `/zones`：区域控制
- `/users`：用户管理
- `/devices`：设备管理
- `/areas`：巡检区域
- `/points`：巡检点
- `/routes`：巡检路线
- `/login`：登录页

兼容旧路由：

- `/` -> `/overview`
- `/_3` -> `/tasks`
- `/_1` -> `/reports`
- `/monitoring_dashboard` -> `/robots`
- `/zone_control` -> `/zones`

## API 概览

### 认证

- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/register`

### 仪表盘

- `GET /api/dashboard`
- `GET /api/health`
- `WS /ws/dashboard`

### 业务对象

- `GET /api/tasks`
- `POST /api/tasks`
- `DELETE /api/tasks/{task_id}`
- `GET /api/robots`
- `POST /api/robots`
- `DELETE /api/robots/{robot_id}`
- `GET /api/alerts`
- `POST /api/alerts`
- `DELETE /api/alerts/{alert_id}`
- `GET /api/reports`
- `POST /api/reports`
- `DELETE /api/reports/{report_id}`
- `GET /api/zones`
- `POST /api/zones`

### 管理页

- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{user_id}`
- `PATCH /api/users/{user_id}/status`
- `GET /api/devices`
- `POST /api/devices`
- `PUT /api/devices/{device_id}`
- `DELETE /api/devices/{device_id}`
- `GET /api/areas`
- `POST /api/areas`
- `PUT /api/areas/{area_id}`
- `DELETE /api/areas/{area_id}`
- `GET /api/points`
- `POST /api/points`
- `PUT /api/points/{point_id}`
- `DELETE /api/points/{point_id}`
- `GET /api/routes`
- `POST /api/routes`
- `PUT /api/routes/{route_id}`
- `DELETE /api/routes/{route_id}`
- `GET /api/routes/{route_id}/points`
- `PUT /api/routes/{route_id}/points`

## 登录与权限

- 页面和 API 默认都要求登录。
- 未登录访问业务页面会重定向到 `/login`。
- 未登录访问业务 API 会返回 `401`。
- WebSocket `/ws/dashboard` 同样要求登录状态。
- 当 `ALLOW_SELF_REGISTER=0` 时，登录页不会显示注册入口。

## 区域绘制说明

区域控制页新增区域时，可直接在地图中绘制多边形：

- 单击地图：添加一个点
- 双击地图：完成绘制
- 右键地图：撤销最后一个点
- `清空绘制`：重置当前草稿
- 调色板：选择边框颜色，系统会自动生成半透明填充色

提交规则：

- 少于 3 个点不能提交
- 未双击完成绘制时不能提交

## ID 边界规则

所有删除接口和关键外键都使用统一的 ID 校验规则：

- 最小值：`1`
- 最大值：`2147483647`

错误语义：

- 非法 ID：返回 `422`
- ID 合法但记录不存在：返回 `404`

## 健康检查

`GET /api/health` 返回：

- `status`
- `mysqlConfigured`
- `mysqlReady`
- `detail`
- `timestamp`

数据库不可用时会返回 `503`。

## 实时更新

`WS /ws/dashboard` 支持：

- 首次连接推送仪表盘快照
- `ping` / `heartbeat`
- `refresh`
- 任务、机器人、告警、报告、区域变更后的广播刷新

## 测试

运行核心测试：

```powershell
cd E:\Code\Project4\backend
python -m pytest -q tests/test_auth_ui.py tests/test_robot_discovery.py tests/test_iot_auth.py tests/test_schema_migration.py
```

当前重点覆盖：

- 登录页可访问
- 登录、登出与页面保护
- 注册开关行为
- 仪表盘 API 与 WebSocket
- 健康检查接口
- 机器人发现与添加
- ID 边界的 `422/404` 语义

## 常见问题

### 1. 地图不显示

优先检查：

- `.env` 中是否配置了正确的 `AMAP_WEB_KEY`
- Key 是否属于高德 `Web 端 JS API`
- 浏览器是否拦截了定位权限
- 是否还在使用 `HTTP` 且不是 `localhost`

### 2. 登录失败

优先检查：

- MySQL 是否已启动
- `.env` 中的 MySQL 配置是否正确
- 管理员账号是否被 `.env` 覆盖

### 3. 服务启动后提示数据库错误

优先检查：

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

## 开发入口

- [main.py](/E:/Code/Project4/backend/main.py)
- [dashboard.js](/E:/Code/Project4/backend/static/dashboard.js)
- [app.html](/E:/Code/Project4/backend/templates/app.html)
- [mysql_schema.sql](/E:/Code/Project4/backend/db/mysql_schema.sql)
