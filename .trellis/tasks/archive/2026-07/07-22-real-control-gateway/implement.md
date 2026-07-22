# 真实控制网关实施计划

## 1. 后端协议与配置

- [x] 在 `config.py` 增加网关 URL、Token 和超时读取函数。
- [x] 在 `app_core.py` 增加集群节点目标查询，返回机器人 ID、IP 和控制端口。
- [x] 增加受支持目标和命令的白名单校验。
- [x] 使用 `httpx.AsyncClient` 调用网关，限制连接、读取超时和响应体大小。
- [x] 验证响应必须是 JSON 对象，并包含布尔类型的 `ok`、`executed`。
- [x] 将 `create_control_command()` 调整为异步流程，同时保持单机器人行为不变。
- [x] `executed=true` 时记录 `success` 并执行副作用；`executed=false` 时记录 `simulated` 且不执行副作用。

## 2. 最小控制网关

- [x] 新增 `tools/device/control_gateway.py`。
- [x] 提供 `GET /health` 和 `POST /v1/commands`。
- [x] 校验 Bearer Token、请求结构、目标类型和命令类型。
- [x] 默认 `dry_run`，只返回模拟结果，不创建 TCP 连接。
- [x] `live` 模式下，`connectivity_test` 发送 `ping` 并等待 `pong`。
- [x] `live` 模式下，`node_exit` 发送 `stop` 并检查 `ack.ok`。
- [x] 对连接失败、超时、断开、错误 JSON 和设备拒绝返回稳定错误。
- [x] 不在输出中打印 Token 或完整敏感配置。

## 3. 测试

- [x] 扩展 `tests/backend/test_management_system_api.py`，覆盖网关成功、模拟、拒绝、超时、异常 JSON、未配置和不支持命令。
- [x] 验证 `node_exit` 只有在真实执行成功后才更新节点状态。
- [x] 新增 `tests/tools/test_control_gateway.py`，使用假 socket 覆盖 dry-run、ping、stop、认证和失败路径。
- [x] 确认测试不会连接真实网络或车辆。

## 4. 文档

- [x] 更新 `.env.example`。
- [x] 更新 `apps/backend/README.md`，加入启动网关、模拟测试和 live 模式说明。
- [x] 更新 `docs/guides/remote-control.md`，说明网关与单机器人直连的边界。

## 5. 验证命令

```powershell
python -m pytest tests/backend/test_management_system_api.py tests/tools/test_control_gateway.py -q
python -m pytest tests/backend tests/tools -q
python tools/dev/local_release_smoke.py --static
git diff --check
```

## 6. 风险与检查点

- 修改 `create_control_command()` 的同步/异步关系后，检查所有调用位置。
- 任何失败都必须把命令从 `pending` 更新为 `failed`。
- 模拟结果不能触发 `node_exit` 数据库副作用。
- live 模式的停车确认必须先于节点状态修改。
- 网关响应和错误文本写库前必须限制大小。
