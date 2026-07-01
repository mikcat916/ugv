# Project4

机器人巡检监控系统，面向“后台管理 + 桌面控制 + IoT 设备上报”的一体化场景。

项目当前包含三个主要部分：

- `backend/`：基于 FastAPI 的 Web 管理后台，负责业务页面、CRUD 接口、登录鉴权、实时看板和 IoT 接口。
- `desktop/`：基于 PyQt 的桌面端，提供登录、主控界面、任务管理、状态监控和资产管理等能力。
- `scripts/`：数据库初始化、MySQL 诊断、树莓派 IoT 客户端和远程部署脚本。

## 功能概览

- 用户、设备、巡检区域、巡检点、巡检路线管理
- FastAPI + Jinja2 一体化 Web 页面
- Session 登录鉴权和基础健康检查
- WebSocket 实时看板数据推送
- 设备 IoT 打卡与遥测上报接口
- PyQt 桌面端任务执行和状态监控界面
- MySQL 建库、建表、诊断和部署辅助脚本

## 项目结构

```text
Project4/
├── backend/                 # Web 后端与页面模板
├── desktop/                 # PyQt 桌面端
├── docs/
│   └── planning/            # 项目规划与阶段待办
├── logs/                    # 诊断脚本输出日志
├── scripts/                 # 建库、诊断、IoT 与部署脚本
├── .conda/                  # 本地 Python 环境（如果已创建）
├── create_database.bat      # 一键建库建表
├── start.bat                # 一键启动后端
├── start.ps1                # 后端启动脚本
├── test_mysql_connection.bat# 一键诊断 MySQL 连接
└── README.md
```

## 技术栈

### Web 端

- Python
- FastAPI
- Jinja2
- PyMySQL
- Uvicorn
- MySQL 8
- 原生 JavaScript

### 桌面端

- Python
- PyQt5 / PyQtWebEngine
- PyQt-Fluent-Widgets
- PyMySQL / mysql-connector-python

## 当前进度

根据 [docs/planning/todolist.md](./docs/planning/todolist.md) 当前状态如下：

- 阶段一到阶段四已基本完成，包括数据库建模、后端 CRUD、Web 页面和 IoT 通信能力。
- 阶段五仍在进行中，主要是前后端联调、设备模拟和端到端流程测试。

如果你是第一次接手这个仓库，可以优先从 Web 后端启动和数据库连通性检查开始。

## 仓库整理说明

当前仓库按“源码 + 文档规划 + 本地产物”划分：

- `backend/`、`desktop/`、`scripts/` 仍是主要源码目录，保持现有运行路径不变。
- `docs/planning/` 用于放置阶段规划和待办文档，当前 `todolist.md` 已移动到这里。
- `.conda/`、`logs/`、`test-results/`、`.claude/` 等目录属于本地环境、调试或生成产物，不作为主结构的一部分。


## 环境要求

- Windows + PowerShell（当前脚本优先按 Windows 开发环境组织）
- Python 3.11 推荐用于后端和桌面端
- MySQL 8.0+

建议为 `backend` 和 `desktop` 分别准备独立 Python 环境，避免桌面依赖与后端依赖互相影响。

## 本地启动

最短流程：

```text
1. 复制 .env.example 为 .env，并按本机 MySQL 修改账号密码
2. 启动 MySQL
3. 运行 .\start-dev.ps1
4. 打开 http://127.0.0.1:8000
```

PowerShell 示例：

```powershell
cd E:\Code\Project4
Copy-Item .env.example .env
notepad .env
.\start-dev.ps1
```

`start-dev.ps1` 会自动检查 Python、后端依赖、MySQL 连接和数据库表；数据库不存在时会尝试初始化。

默认本地地址：

- 后端：<http://127.0.0.1:8000>
- 登录页：<http://127.0.0.1:8000/login>
- 健康检查：<http://127.0.0.1:8000/api/health>
- 短健康检查：<http://127.0.0.1:8000/health>
- 调试配置（仅 `DEBUG=1`）：<http://127.0.0.1:8000/debug/config>

默认本地管理员账号仅限本地自用：

- 用户名：`admin`
- 密码：`admin123`

## 配置说明

根目录 `.env` 是共享数据库配置入口，`backend` 和 `desktop` 都会读取这里的配置。建议先从 `.env.example` 复制。

示例：

```env
# Web 后端数据库
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=robot_monitor
MYSQL_CHARSET=utf8mb4

# 桌面端数据库别名
UAV_DB_HOST=127.0.0.1
UAV_DB_PORT=3306
UAV_DB_USER=your_mysql_user
UAV_DB_PASSWORD=your_mysql_password
UAV_DB_NAME=robot_monitor

# 后端可选配置（仅限本地自用默认值）
SESSION_SECRET=dev-local-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_DISPLAY_NAME=系统管理员
ALLOW_SELF_REGISTER=0
AMAP_WEB_KEY=your_amap_web_js_key
```

说明：

- 后端启动时会优先读取根目录 `.env`，同时兼容 `backend/.env`。
- 桌面端数据库配置读取 `UAV_DB_*` 变量；未提供时会回退到默认值。
- `AMAP_WEB_KEY` 仅在需要地图功能时配置。
- `ALLOW_SELF_REGISTER=0` 表示默认不开放注册；本地需要临时注册时可以改成 `1`。
- 默认管理员账号和 `dev-local-secret` 仅限本地自用。

## 快速开始

### 1. 安装依赖

后端：

```powershell
cd E:\Code\Project4\backend
python -m pip install -r requirements.txt
```

桌面端：

```powershell
cd E:\Code\Project4\desktop
python -m pip install -r requirements.txt
```

### 2. 初始化数据库

推荐直接使用根目录脚本：

```powershell
cd E:\Code\Project4
.\create_database.bat
```

等价命令：

```powershell
cd E:\Code\Project4
python scripts\create_database.py --with-device-pin
```

这个步骤会：

- 创建目标数据库
- 执行 `backend/db/mysql_schema.sql`
- 可选创建桌面端使用的 `device_pin` 表

本地清库重来：

```powershell
mysql -u root -p robot_monitor < backend\db\reset-db-dev.sql
python scripts\create_database.py --with-device-pin
```

导入本地测试数据：

```powershell
mysql -u root -p robot_monitor < backend\db\seed-dev.sql
```

### 3. 启动 Web 后端

最省事的方式：

```powershell
cd E:\Code\Project4
.\start-dev.ps1
```

或手动启动：

```powershell
cd E:\Code\Project4\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

启动后可访问：

- 本机直连登录页：<http://127.0.0.1:8000/login>
- 本机直连健康检查：<http://127.0.0.1:8000/api/health>

说明：

- 本地开发默认只绑定 `127.0.0.1`，避免无意暴露到局域网。
- 如果确实需要局域网访问，可以运行 `.\start-dev.ps1 -HostName 0.0.0.0`。

如果没有在环境变量中覆盖管理员账号，默认登录信息为：

- 用户名：`admin`
- 密码：`admin123`

### 4. 启动桌面端

```powershell
cd E:\Code\Project4\desktop
python main.py
```

也可以从根目录运行：

```powershell
.\start-desktop.ps1
```

桌面端会读取根目录 `.env` 中的 `UAV_DB_*` 配置连接数据库。

## IoT 相关脚本

仓库已经包含设备侧接入的基础脚本，适合做本地联调或树莓派部署。

### 初始化 IoT 后端表并生成设备 Token

```powershell
cd E:\Code\Project4
python scripts\bootstrap_iot_backend.py --device-id 2
```

该脚本会补充创建：

- `device_tokens`
- `device_checkins`
- `device_telemetry`

如果目标设备存在，还会为该设备生成或复用一个可用 Token。

### 本地运行 IoT 客户端

```powershell
cd E:\Code\Project4\scripts
python iot_client.py --server http://127.0.0.1:8000 --token <DEVICE_TOKEN>
```

如果要单独诊断树莓派 GPS，可执行：

```powershell
cd E:\Code\Project4\scripts
python iot_client.py --server http://127.0.0.1:8000 --token <DEVICE_TOKEN> --gps-diagnose
```

如果 GPS 模块走固定串口，也可以显式指定：

```powershell
python iot_client.py --server http://127.0.0.1:8000 --token <DEVICE_TOKEN> --gps-diagnose --gps-serial-device /dev/ttyAMA0 --gps-serial-baud 9600
```

诊断输出会优先检查：

- `gpspipe -w` 是否能返回 `TPV`
- `gpspipe -r` 是否能读到原始 NMEA
- 指定串口或常见串口设备是否有原始输出

遥测上报时，`extra.gps` 里也会带上当前 GPS 状态摘要，便于在服务端排查“未安装 gpspipe / 有 NMEA 但无 fix / 串口完全无输出”等问题。

如果设备没有 GPS，也可以启用“网络定位 fallback”：

- 当前脚本支持 `Google Geolocation API`
- 有 Wi-Fi 扫描权限时会优先上传附近热点信息
- 扫描不到热点时，可按配置退回到公网 IP 粗定位

示例配置：

```ini
network_locate_enabled = 1
network_provider = google
network_api_key = <YOUR_GOOGLE_GEOLOCATION_API_KEY>
network_api_url = https://www.googleapis.com/geolocation/v1/geolocate
network_timeout = 10
network_interface = wlan0
network_consider_ip = 1
```

说明：

- 网络定位精度通常明显弱于 GPS，建议只作为兜底方案。
- `network_consider_ip = 1` 时，即使没有 Wi-Fi 扫描结果，也可能返回一个较粗的 IP 定位。
- 若设备侧没有开启扫描权限，脚本仍会继续工作，只是会更依赖 IP 粗定位。

### 当前设备现状

基于 `192.168.31.200` 这台树莓派设备的实际排查结果，当前状态如下：

- 后端遥测上报正常，来源 IP 为 `192.168.31.200`
- 当前稳定上报字段包括：
  - `status`
  - `signal`
  - `extra.cpu_temp_c`
  - `reportedAt`
  - `extra.gps.status / source / message`
  - `extra.locationSource`
- 当前未产生巡检打卡记录，因为配置仍是 `point_id = 0`、`route_id = 0`

### GPS 现状

当前设备没有产出可用 GPS 坐标，已经确认的现象包括：

- `gpsd` 和 `gpspipe` 已安装并可运行
- `gpspipe -w` 只能返回 `VERSION / DEVICES / WATCH`
- `gpspipe -r` 没有返回任何 NMEA 数据
- `/dev/ttyAMA0`、`/dev/ttyS0` 在多轮诊断和多波特率扫描下都没有输出
- 已移除 `/boot/cmdline.txt` 中的 `console=serial0,115200`
- 已禁用 `serial-getty@ttyS0.service`

结论：

- 当前更像是“设备没有接入可工作的 GPS 模块”或“GPS 模块没有向树莓派串口输出数据”
- 如果后续需要位置能力，优先级建议为：
  1. 接入真实 GPS 模块
  2. 或启用网络定位 fallback

### 电池信息现状

当前设备还不能上传电池信息，已确认：

- `/sys/class/power_supply` 为空，没有 `BAT0`
- 没发现 `INA219 / INA226 / MAX17040 / BQ*` 等常见电量采集芯片或驱动
- I2C 总线上的 `0x40` 设备更像 `PCA9685` PWM 控制器，而不是电池计量芯片

结论：

- 目前系统里没有发现可直接读取的电池信息源
- 如果后续需要电池百分比，需要额外接入：
  - UPS / BMS / fuel gauge 芯片
  - 或者由下位控制板通过串口 / I2C / HTTP 回传电压与电量

### 部署到树莓派

Linux 侧脚本：

```bash
bash scripts/setup_pi_iot.sh <SERVER_URL> <DEVICE_TOKEN> [INTERVAL] [POINT_ID] [ROUTE_ID] [GPS_SERIAL_DEVICE] [GPS_SERIAL_BAUD]
```

Windows 远程部署脚本：

```powershell
python scripts\deploy_iot_client.py --host <PI_HOST> --password <PI_PASSWORD> --server <SERVER_URL> --token <DEVICE_TOKEN> --gps-serial-device /dev/ttyAMA0 --network-locate-enabled --network-api-key <GOOGLE_API_KEY>
```

## 常用脚本

| 脚本 | 作用 |
| --- | --- |
| `start.bat` / `start.ps1` | 启动 Web 后端 |
| `create_database.bat` | 初始化数据库和表结构 |
| `test_mysql_connection.bat` | 诊断本地 MySQL 连通性 |
| `scripts/create_database.py` | 命令行建库建表 |
| `scripts/test_mysql_connection.py` | 输出详细诊断日志到 `logs/` |
| `scripts/bootstrap_iot_backend.py` | 初始化 IoT 表并生成设备 Token |
| `scripts/iot_client.py` | 设备侧打卡与遥测上报客户端 |
| `scripts/deploy_iot_client.py` | 将 IoT 客户端远程部署到树莓派 |

## 测试与排查

后端基础测试：

```powershell
cd E:\Code\Project4\backend
python -m pytest -q tests\test_auth_ui.py
```

数据库连通性诊断：

```powershell
cd E:\Code\Project4
.\test_mysql_connection.bat
```

诊断日志会输出到根目录 `logs/`。

## 子模块文档

- Web 端说明见 [backend/README.md](./backend/README.md)
- 桌面端说明见 [desktop/README.md](./desktop/README.md)

## 开发备注

- 根目录 `README.md` 负责项目总览与启动入口。
- `backend/README.md` 更适合写 API、页面路由和后端细节。
- `desktop/README.md` 更适合写桌面端 UI、环境和模块说明。
- 当前仓库仍处于联调阶段，文档会随着阶段五测试推进继续补充。
