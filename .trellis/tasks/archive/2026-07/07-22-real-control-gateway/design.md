# 真实控制网关技术设计

## 1. 总体结构

新增独立 FastAPI 服务 `tools/device/control_gateway.py`。Web 后端继续负责权限、命令记录和管理数据；控制网关负责验证命令并与机器人 TCP 控制服务通信。

```text
管理员页面
  -> POST /api/control/commands
  -> Web 后端记录 pending
  -> POST CONTROL_GATEWAY_URL/v1/commands
  -> 控制网关
  -> 机器人 TCP 控制服务 :9000
  -> 控制网关返回执行结果
  -> Web 后端记录 success / simulated / failed
```

## 2. 支持范围

第一版只支持：

| 目标 | 命令 | 实际动作 |
| --- | --- | --- |
| `cluster_node` | `connectivity_test` | 向节点关联机器人发送 `ping`，等待 `pong` |
| `cluster_node` | `node_exit` | 向节点关联机器人发送 `stop`，等待成功 `ack` |

其他目标或命令由 Web 后端在调用网关前拒绝，网关也进行第二次校验。

## 3. 后端到网关协议

请求：

```json
{
  commandId: 123,
  targetType: cluster_node,
  targetId: 7,
  commandType: node_exit,
  params: {},
  target: {
    clusterId: 2,
    robotId: 4,
    host: 192.168.1.20,
    port: 9000
  }
}
```

执行成功响应：

```json
{
  ok: true,
  executed: true,
  mode: live,
  commandId: 123,
  message: 节点已停车，可以退出集群。,
  data: {robotResponseType: ack}
}
```

模拟响应使用 `ok=true`、`executed=false`、`mode=dry_run`。拒绝响应使用 `ok=false`，并提供简短错误码和说明。

## 4. 安全与认证

- 后端使用 `Authorization: Bearer <token>` 调用网关。
- Token 来自 `CONTROL_GATEWAY_TOKEN`，不写入日志或 API 响应。
- 网关的 `CONTROL_GATEWAY_MODE` 默认为 `dry_run`；只有设置为 `live` 才建立 TCP 连接。
- 网关仅接受目标 IP、端口等由后端数据库解析后的字段，不接受浏览器直接指定地址。
- 后端和网关均限制命令类型、响应 JSON 类型和响应体大小。
- 状态改变命令不自动重试，防止重复执行。
- `node_exit` 必须先确认停车；失败时不修改 `cluster_nodes`。

## 5. 配置

Web 后端：

```env
CONTROL_GATEWAY_URL=http://127.0.0.1:9100
CONTROL_GATEWAY_TOKEN=replace-with-a-long-random-token
CONTROL_GATEWAY_TIMEOUT_SECONDS=5
```

网关：

```env
CONTROL_GATEWAY_HOST=127.0.0.1
CONTROL_GATEWAY_PORT=9100
CONTROL_GATEWAY_TOKEN=replace-with-a-long-random-token
CONTROL_GATEWAY_MODE=dry_run
ROBOT_CONTROL_PORT=9000
ROBOT_CONTROL_TIMEOUT_SECONDS=2
```

## 6. 数据状态

- 创建命令：`pending`。
- 网关真实执行成功：`success`，保存有限大小的响应，并执行既有副作用。
- 网关模拟确认：`simulated`，保存模拟结果，不执行副作用。
- 配置、网络、认证、协议或设备失败：`failed`，保存安全的错误说明。

不修改数据库表结构，现有 `VARCHAR(32)` 状态字段可容纳 `simulated`。

## 7. 兼容性

- 单机器人命令继续走现有 TCP 直连逻辑。
- `/api/robot-control/*` 行为不变。
- 原有管理员权限和 `control_commands` 记录保留。
- 未配置网关时继续返回明确失败，不降级为假成功。

## 8. 回退方式

删除或留空 `CONTROL_GATEWAY_URL` 即可停止网关调用。代码回退时只需恢复 `create_control_command()` 的非机器人分支并删除新网关工具，不涉及数据库迁移。
