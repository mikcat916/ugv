# 远程控制树莓派小车开发过程笔记

本文记录远程控制树莓派小车的开发思路、模块分工、部署步骤和联调检查点。控制链路以真实设备为目标：控制失败时应暴露明确错误，不做模拟成功或静默降级。

远端 Ubuntu 开发机：`oneday@192.168.31.169`。认证信息不写入仓库文档，部署时使用本机 SSH 配置或受控环境变量。

## 目标

- 管理员可以在 Web 后台选择机器人并发送前进、后退、转向、停止、急停指令。
- 后端根据机器人 IP 建立到树莓派的 TCP 连接。
- 树莓派上的控制服务把后端指令转换为底盘串口控制包。
- IoT 遥测客户端持续上报设备状态，辅助页面判断车辆是否在线。
- 所有控制入口只允许管理员使用，避免普通用户误触真实车辆。

## 总体链路

```mermaid
flowchart LR
    A["Web 后台控制页"] --> B["FastAPI 控制接口"]
    B --> C["TCP 长连接"]
    C --> D["树莓派控制服务 :9000"]
    D --> E["串口 /dev/ttyACM0"]
    E --> F["底盘电机控制板"]

    G["树莓派 IoT 客户端"] --> H["/api/iot/telemetry"]
    H --> A
```

控制指令和遥测上报是两条不同链路：

- 控制链路：`Web 页面 -> /api/robot-control/* -> 树莓派 TCP 控制服务 -> 串口电机板`
- 遥测链路：`tools/device/iot_client.py -> /api/iot/telemetry -> Web 看板`

管理后台里的非单机器人命令还多一层控制网关：

```text
Web 管理后台 -> POST /api/control/commands -> Web 后端 -> 控制网关 :9100 -> 机器人 TCP 控制服务 :9000
```

两条控制路径不要混淆：

- 单机器人控制和 `/api/robot-control/*` 继续由 Web 后端直接连接机器人，不经过控制网关。
- 控制网关第一版只处理 `cluster_node`，并且只支持 `connectivity_test` 和 `node_exit`。

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `apps/backend/src/ugv_backend/app_core.py` | 提供控制接口、目标解析、TCP 转发和控制命令记录 |
| `apps/backend/static/dashboard.js` | 渲染远程遥控页面，处理按住方向键持续发送指令 |
| `tools/device/control_gateway.py` | 运行独立 HTTP 控制网关，校验并转发集群节点命令 |
| `tools/device/robot_control_server.py` | 运行在树莓派上的 TCP 控制服务 |
| `tools/device/iot_client.py` | 运行在树莓派上的遥测和打卡上报客户端 |
| `tools/dev/bootstrap_iot_backend.py` | 初始化 IoT 表并生成设备 Token |
| `tools/deploy/deploy_iot_client.py` | 从 Windows 远程部署 IoT 客户端到树莓派 |
| `tests/backend/test_robot_control_api.py` | 覆盖控制目标解析、权限、速度限幅和异常响应 |

## 开发步骤

### 1. 明确控制协议

后端和树莓派控制服务之间使用按行分隔的 JSON 消息，每条消息以换行符结束。

后端发送：

```json
{"type":"ping"}
```

```json
{"type":"cmd_vel","v":0.1,"w":0.0}
```

```json
{"type":"stop"}
```

树莓派返回：

```json
{"type":"pong","ts":1779850000}
```

```json
{"type":"ack","ok":true,"ts":1779850000}
```

协议设计保持简单：只传递连接检测、速度控制和停车。未知消息类型返回明确失败，不伪造成功。

### 2. 开发树莓派控制服务

树莓派侧脚本是 `tools/device/robot_control_server.py`，核心职责如下：

- 监听 `0.0.0.0:9000`
- 接收后端发来的 `ping`、`cmd_vel`、`stop`
- 把 `cmd_vel` 中的线速度 `v` 和角速度 `w` 转换为底盘串口数据包
- 写入 `/dev/ttyACM0`，波特率 `115200`
- 在指令超时后主动停车

本地调试时先在树莓派前台运行：

```bash
python3 robot_control_server.py
```

如果缺少串口库，安装：

```bash
python3 -m pip install pyserial
```

从树莓派本机验证 TCP 服务：

```bash
printf '{"type":"ping"}\n' | nc 127.0.0.1 9000
```

预期返回 `pong`。如果串口设备不是 `/dev/ttyACM0`，应先确认实际设备名，再修改脚本中的 `SERIAL_PORT` 常量。

### 3. 配置后端控制目标

后端控制目标有两种来源：

- 推荐方式：在机器人表中配置 `ip_address`，页面选择机器人后使用该 IP。
- 调试方式：通过环境变量 `ROBOT_CONTROL_HOST` 指定固定控制目标。

控制端口默认是 `9000`，可通过环境变量覆盖：

```env
ROBOT_CONTROL_PORT=9000
ROBOT_CONTROL_HOST=192.168.31.200
```

如果页面传入 `robotId`，后端会查询机器人 IP，并连接 `<机器人 IP>:<ROBOT_CONTROL_PORT>`。如果没有传入 `robotId`，后端才使用 `ROBOT_CONTROL_HOST`。

### 4. 开发后端控制接口

后端提供三类直接控制接口：

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/api/robot-control/status` | `GET` | 向树莓派发送 `ping`，检查控制服务是否可达 |
| `/api/robot-control/cmd_vel` | `POST` | 发送线速度和角速度 |
| `/api/robot-control/stop` | `POST` | 发送停车指令 |

接口行为：

- 所有接口都要求管理员登录。
- 线速度由 `ROBOT_CONTROL_MAX_LINEAR` 限幅，当前为 `0.4`。
- 角速度由 `ROBOT_CONTROL_MAX_ANGULAR` 限幅，当前为 `1.2`。
- TCP 连接失败返回 `502`。
- 控制服务响应超时返回 `504`。
- 机器人未配置 IP 返回 `422`。

这种处理方式让故障直接暴露在页面和测试中，便于定位真实问题。

### 4.1 配置并启动真实控制网关

控制网关脚本是 `tools/device/control_gateway.py`。它会读取仓库根目录 `.env`，默认监听 `127.0.0.1:9100`。

建议先使用下面的安全配置：

```env
CONTROL_GATEWAY_URL=http://127.0.0.1:9100
CONTROL_GATEWAY_HOST=127.0.0.1
CONTROL_GATEWAY_PORT=9100
CONTROL_GATEWAY_TOKEN=replace-with-a-long-random-token
CONTROL_GATEWAY_TIMEOUT_SECONDS=5
CONTROL_GATEWAY_MODE=dry_run
ROBOT_CONTROL_PORT=9000
ROBOT_CONTROL_TIMEOUT_SECONDS=2
```

说明：

- `CONTROL_GATEWAY_URL` 是 Web 后端访问网关的地址。
- `CONTROL_GATEWAY_HOST` 和 `CONTROL_GATEWAY_PORT` 是网关自己的监听地址和端口。
- 后端和网关读取同一个 `CONTROL_GATEWAY_TOKEN`。后端请求时会发送 `Authorization: Bearer <Token>`；Token 为空、不同或请求未携带 Token 时，命令不会执行。
- `CONTROL_GATEWAY_TIMEOUT_SECONDS` 是后端等待网关的时间，默认 `5` 秒。
- `ROBOT_CONTROL_TIMEOUT_SECONDS` 是网关等待机器人 TCP 控制服务的时间，默认 `2` 秒。

在仓库根目录启动网关：

```powershell
cd E:\Code\Project4
python tools\device\control_gateway.py
```

健康检查地址是 `http://127.0.0.1:9100/health`。它只报告当前模式和 Token 是否已配置，不会返回 Token 内容。

#### `dry_run` 默认安全模式

未设置 `CONTROL_GATEWAY_MODE` 时，网关默认使用 `dry_run`。在这个模式下：

- 网关会检查 Token、请求内容、目标类型和命令类型。
- 网关返回 `ok=true`、`executed=false` 和 `mode=dry_run`。
- 不会建立机器人 TCP 连接，不会发送 `ping` 或 `stop`。
- 后端把命令记录为 `simulated`，不会更新集群节点状态。

#### `live` 真实执行模式

只有明确设置下面的值并重启网关后，才会连接真实机器人：

```env
CONTROL_GATEWAY_MODE=live
```

`live` 模式当前仅支持：

| 目标类型 | 命令 | 实际动作 |
| --- | --- | --- |
| `cluster_node` | `connectivity_test` | 向关联机器人的 IPv4 地址和 `ROBOT_CONTROL_PORT` 发送 `ping`，收到 `pong` 后成功 |
| `cluster_node` | `node_exit` | 先发送 `stop`，收到类型为 `ack` 且 `ok=true` 后成功 |

任何其他目标或命令都会返回错误，不会伪造成功。机器人 IP 缺失、连接失败、超时、返回格式错误或拒绝停车时，后端把命令记录为 `failed`。

`node_exit` 必须按这个顺序执行：

1. 网关向节点关联机器人发送 `stop`。
2. 网关确认收到 `ok=true` 的 `ack`。
3. 网关向后端返回 `executed=true`。
4. 后端才把该节点状态更新为 `disconnected`，并清空 `joined_at`。

只要停车没有确认成功，或者网关处于 `dry_run`，第 4 步就不会发生。

### 5. 开发 Web 控制页面

远程控制页面位于 Web 后台的“设备与机器人 / 远程遥控无人车”相关入口，前端逻辑在 `apps/backend/static/dashboard.js`。

页面行为：

- 从在线或可控机器人列表中选择控制目标。
- 点击“检测连接”调用 `/api/robot-control/status`。
- 按住方向键时，每 `180ms` 发送一次 `cmd_vel`。
- 松开、取消、鼠标离开按钮或离开页面时，发送 `stop`。
- “停止”和“急停”都调用 `/api/robot-control/stop`。
- 目标离线或没有可控车辆时禁用运动按钮。

速度计算方式：

- 方向按钮给出线速度和角速度方向。
- 页面滑块给出倍率。
- 前端根据后端注入的 `maxLinear`、`maxAngular` 计算最终值。
- 后端再次限幅，防止异常请求绕过页面限制。

### 6. 部署 IoT 遥测客户端

遥测不是运动控制的必要条件，但建议同时部署，用来在页面上显示车辆在线状态、信号、CPU 温度、GPS 状态等信息。

先初始化 IoT 后端表并生成设备 Token：

```powershell

python tools\dev\bootstrap_iot_backend.py --device-id 2
```

再从 Windows 远程部署到树莓派：

```powershell
python tools\deploy\deploy_iot_client.py --host <PI_HOST> --password <PI_PASSWORD> --server <SERVER_URL> --token <DEVICE_TOKEN>
```

部署完成后，树莓派会运行 `project4-iot.service`，定期向后端上报遥测。

### 7. 部署树莓派控制服务

当前仓库已有控制服务脚本，但没有单独的控制服务部署脚本。可按下面方式在树莓派上注册 systemd 服务。

复制脚本到树莓派：

```bash
mkdir -p /home/pi/project4-control
cp robot_control_server.py /home/pi/project4-control/robot_control_server.py
```

创建服务文件：

```ini
[Unit]
Description=Project4 Robot Control Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/pi/project4-control
ExecStart=/usr/bin/python3 /home/pi/project4-control/robot_control_server.py
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable project4-control.service
sudo systemctl restart project4-control.service
sudo systemctl status project4-control.service --no-pager
```

查看日志：

```bash
journalctl -u project4-control.service -f
```

### 8. 联调顺序

1. 先确认树莓派和后端服务器在同一局域网内，且后端可以访问树莓派 `9000` 端口。
2. 在树莓派本机运行 `python3 robot_control_server.py`，确认服务已经监听。
3. 在数据库或管理页面中配置机器人 IP，然后登录 Web 后台并进入远程遥控页。
4. 点击“检测连接”，再短按方向键、松开按键、最后点“急停”，验证底盘能正确响应。
5. 如果页面同时显示在线状态和最近上报时间，说明遥测链路也已经正常。

## 验证

后端测试：

```powershell

python -m pytest -q tests\test_robot_control_api.py
```

重点验证项：

- 未登录或非管理员不能控制车辆。
- 没有选择机器人且未配置 `ROBOT_CONTROL_HOST` 时返回错误。
- 选择机器人后使用机器人 IP 作为控制目标。
- 速度参数会被后端限幅。
- 控制服务不可达时返回 `502`。
- 控制服务响应超时时返回 `504`。
- 缓存 TCP 连接失效后会重新连接一次。

## 常见问题

### 控制服务不可达

检查项：

- 树莓派控制服务是否正在运行。
- 后端服务器能否访问树莓派 IP。
- 防火墙是否放行 `9000` 端口。
- 页面选择的机器人 IP 是否正确。
- `ROBOT_CONTROL_PORT` 是否和树莓派监听端口一致。

### 串口没有输出

检查项：

- `/dev/ttyACM0` 是否存在。
- 当前用户是否有串口权限。
- 底盘控制板波特率是否为 `115200`。
- 电机控制板协议是否和 `motor_packet()` 中的数据包格式一致。

### 页面提示车辆离线

检查项：

- `project4-iot.service` 是否正常运行。
- 设备 Token 是否正确。
- `iot_client.conf` 中的 `server` 是否指向后端地址。
- 后端 `/api/iot/telemetry` 是否能收到上报。

### 按键后小车持续运动

检查项：

- 浏览器松开按键时是否触发了 `/api/robot-control/stop`。
- 树莓派日志中是否出现停车指令。
- `watchdog_loop()` 是否正常运行。
- `CMD_TIMEOUT_SEC` 是否被改得过大。

## 安全约束

- 控制接口只允许管理员访问，页面也会明确提示“真实车辆控制”。
- 后端和树莓派两侧都保留速度限幅，松开按钮、切换目标、离开页面时都会发送停车指令。
- 控制服务异常时返回明确错误，不返回假成功；首次联调应让轮子离地或在空旷环境低速测试。
