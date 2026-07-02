# 机器人巡检平台

这是一个基于 `FastAPI + Jinja2 + MySQL + 高德地图` 的机器人巡检管理后台，提供登录认证、任务管理、机器人状态查看、告警和报告管理、区域绘制、设备与点位维护，以及实时仪表盘能力。

## 功能概览

- 中文管理界面
- Session 登录认证
- MySQL 自动建库、建表和管理员初始化
- 总览、任务、报告、机器人、维护、区域等页面
- 用户、设备体系、机器人、地图、传感器和远程控制管理
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
|   |-- api.js
|   |-- dashboard.css
|   |-- dashboard.js
|   |-- ui.js
|   |-- websocket.js
|   `-- login.js
|-- templates/
|   |-- app.html
|   `-- login.html
|-- tests/
|   |-- test_auth_ui.py
|   `-- test_robot_discovery.py
|-- config.py
|-- auth.py
|-- app_core.py
|-- db.py
|-- iot.py
|-- main.py              # uvicorn main:app 兼容入口
|-- robot_control.py
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

## 自动驾驶 API

自动驾驶页使用后端内存状态机协调 Web 控制、机器人侧 ROS 节点和安全事件日志。LiDAR 安全默认超时为 `2` 秒，可通过 `AUTOPILOT_LIDAR_TIMEOUT_SECONDS` 覆盖；控制指令超时默认 `10` 秒，可通过 `AUTOPILOT_CONTROL_TIMEOUT_SECONDS` 覆盖。

常用接口：

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/autopilot/status` | `GET` | 查询模式、LiDAR、急停、人工接管和事件概览 |
| `/api/autopilot/events` | `GET` | 查询自动驾驶事件，需要登录 |
| `/api/autopilot/start` | `POST` | 启动自动驾驶；LiDAR 不新鲜时停在 `auto_ready` |
| `/api/autopilot/pause` | `POST` | 暂停自动驾驶并向机器人发送停止 |
| `/api/autopilot/resume` | `POST` | 继续自动驾驶；急停未解除时返回 `409` |
| `/api/autopilot/stop` | `POST` | 停止自动驾驶并清零速度 |
| `/api/autopilot/estop` | `POST` | 触发急停并清零速度 |
| `/api/autopilot/clear-estop` | `POST` | 解除急停，回到手动模式 |
| `/api/iot/autopilot/status` | `POST` | 机器人侧上报自动驾驶状态，需要设备 Token |

安全规则：

- LiDAR 缺失或超过超时阈值时，状态切为不安全并清零 `linearX` / `angularZ`。
- `frontMin < 0.5m` 或前方阻塞状态会清零速度；运行中会降到 `paused`，等待人工确认后恢复。
- `estop=true` 永远优先，后端快照强制为 `mode=estop` 且速度为零。

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
- `/robots`：机器人状态
- `/video`：实时画面
- `/perception`：智能感知
- `/sensors`：传感器数据
- `/maps`：地图展示
- `/control`：远程遥控
- `/device-management`：设备体系管理
- `/devices`：旧设备页
- `/login`：登录页

兼容旧路由：

- `/` -> `/overview`
- `/monitoring_dashboard` -> `/robots`

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

- `GET /api/robots`
- `POST /api/robots`
- `DELETE /api/robots/{robot_id}`
- `GET /api/alerts`
- `POST /api/alerts`
- `DELETE /api/alerts/{alert_id}`

### 管理页

- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{user_id}`
- `PATCH /api/users/{user_id}/status`
- `GET /api/devices`
- `POST /api/devices`
- `PUT /api/devices/{device_id}`
- `DELETE /api/devices/{device_id}`
- `GET /api/device-categories`
- `POST /api/device-categories`
- `PUT /api/device-categories/{category_id}`
- `DELETE /api/device-categories/{category_id}`
- `GET /api/onboard-units`
- `POST /api/onboard-units`
- `PUT /api/onboard-units/{unit_id}`
- `DELETE /api/onboard-units/{unit_id}`
- `GET /api/network-channels`
- `POST /api/network-channels`
- `PUT /api/network-channels/{channel_id}`
- `DELETE /api/network-channels/{channel_id}`

## 登录与权限

- 页面和 API 默认都要求登录。
- 未登录访问业务页面会重定向到 `/login`。
- 未登录访问业务 API 会返回 `401`。
- WebSocket `/ws/dashboard` 同样要求登录状态。
- `/control`、`/users`、`/clusters`、`/formations` 仅管理员可访问。
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
- 机器人、告警、IoT 遥测、传感器和设备管理变更后的广播刷新

## 测试

运行核心测试：

```powershell
cd E:\Code\Project4
python -m pytest backend\tests -q
```

Web 本地发布验收：

```powershell
python scripts\local_release_smoke.py --static
# 启动后端后
python scripts\local_release_smoke.py --web --backend-url http://127.0.0.1:8000
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

### 4. 端口被占用

默认端口是 `8000`。本地临时换端口：

```powershell
cd E:\Code\Project4
.\start-dev.ps1 -Port 8001
```

也可以在根目录 `.env` 中设置：

```env
BACKEND_PORT=8001
```

## 开发入口

- [main.py](/E:/Code/Project4/backend/main.py)
- [dashboard.js](/E:/Code/Project4/backend/static/dashboard.js)
- [app.html](/E:/Code/Project4/backend/templates/app.html)
- [mysql_schema.sql](/E:/Code/Project4/backend/db/mysql_schema.sql)
