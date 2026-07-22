import hmac
import ipaddress
import json
import os
import socket
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[2]
MAX_ROBOT_RESPONSE_BYTES = 65_536
SUPPORTED_COMMANDS = {"connectivity_test", "node_exit"}


def load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env(ROOT_DIR / ".env")


class GatewayTarget(BaseModel):
    clusterNodeId: int = Field(gt=0)
    clusterId: int = Field(gt=0)
    robotId: int = Field(gt=0)
    host: str
    port: int = Field(gt=0, le=65_535)


class GatewayCommand(BaseModel):
    commandId: int = Field(gt=0)
    targetType: str
    targetId: int = Field(gt=0)
    commandType: str
    params: dict[str, Any] = Field(default_factory=dict)
    target: GatewayTarget


app = FastAPI(title="Project4 Control Gateway", version="0.1.0")


def gateway_mode() -> str:
    mode = os.getenv("CONTROL_GATEWAY_MODE", "dry_run").strip().lower() or "dry_run"
    if mode not in {"dry_run", "live"}:
        raise HTTPException(status_code=500, detail="CONTROL_GATEWAY_MODE 只能是 dry_run 或 live。")
    return mode


def gateway_token() -> str:
    return os.getenv("CONTROL_GATEWAY_TOKEN", "").strip()


def robot_timeout_seconds() -> float:
    raw_value = os.getenv("ROBOT_CONTROL_TIMEOUT_SECONDS", "2").strip() or "2"
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="ROBOT_CONTROL_TIMEOUT_SECONDS 必须是数字。") from exc
    if value <= 0 or value > 30:
        raise HTTPException(status_code=500, detail="ROBOT_CONTROL_TIMEOUT_SECONDS 必须大于 0 且不超过 30。")
    return value


def require_gateway_token(request: Request) -> None:
    expected = gateway_token()
    if not expected:
        raise HTTPException(status_code=503, detail="控制网关 Token 未配置。")
    authorization = request.headers.get("authorization", "")
    scheme, _, provided = authorization.partition(" ")
    if scheme.lower() != "bearer" or not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="控制网关身份验证失败。")


def validate_command(command: GatewayCommand) -> None:
    if command.targetType != "cluster_node":
        raise HTTPException(status_code=422, detail="第一版控制网关仅支持集群节点。")
    if command.commandType not in SUPPORTED_COMMANDS:
        raise HTTPException(status_code=422, detail="控制网关仅支持连通性检测和节点退出命令。")
    if command.targetId != command.target.clusterNodeId:
        raise HTTPException(status_code=422, detail="集群节点编号不匹配。")
    try:
        address = ipaddress.ip_address(command.target.host)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="机器人 IP 地址无效。") from exc
    if address.version != 4:
        raise HTTPException(status_code=422, detail="机器人控制服务目前只支持 IPv4。")


def send_robot_message(target: GatewayTarget, payload: dict[str, Any], expected_type: str) -> dict[str, Any]:
    encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
    active_socket: socket.socket | None = None
    try:
        active_socket = socket.create_connection((target.host, target.port), timeout=robot_timeout_seconds())
        active_socket.settimeout(robot_timeout_seconds())
        active_socket.sendall(encoded)
        buffer = b""
        while b"\n" not in buffer:
            chunk = active_socket.recv(4096)
            if not chunk:
                raise ConnectionError("机器人控制连接已断开。")
            buffer += chunk
            if len(buffer) > MAX_ROBOT_RESPONSE_BYTES:
                raise ValueError("机器人控制服务响应内容过大。")
        line = buffer.split(b"\n", 1)[0]
        response = json.loads(line.decode("utf-8"))
    except socket.timeout as exc:
        raise HTTPException(status_code=504, detail="机器人控制服务响应超时。") from exc
    except (ConnectionError, OSError) as exc:
        raise HTTPException(status_code=502, detail="机器人控制服务不可达。") from exc
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="机器人控制服务返回格式错误。") from exc
    finally:
        if active_socket is not None:
            active_socket.close()
    if not isinstance(response, dict) or response.get("type") != expected_type:
        raise HTTPException(status_code=502, detail="机器人控制服务返回了意外响应。")
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    mode = gateway_mode()
    return {"status": "ok", "mode": mode, "tokenConfigured": bool(gateway_token())}


@app.post("/v1/commands")
def execute_command(command: GatewayCommand, request: Request) -> dict[str, Any]:
    require_gateway_token(request)
    validate_command(command)
    mode = gateway_mode()
    if mode == "dry_run":
        return {
            "ok": True,
            "executed": False,
            "mode": mode,
            "commandId": command.commandId,
            "message": "模拟模式：命令已验证，但没有连接真实机器人。",
            "data": {"commandType": command.commandType},
        }
    if command.commandType == "connectivity_test":
        response = send_robot_message(command.target, {"type": "ping"}, "pong")
        message = "集群节点关联机器人控制服务连接正常。"
    else:
        response = send_robot_message(command.target, {"type": "stop"}, "ack")
        if response.get("ok") is not True:
            raise HTTPException(status_code=502, detail="机器人控制服务拒绝停车，节点不能退出。")
        message = "节点已停车，可以退出集群。"
    return {
        "ok": True,
        "executed": True,
        "mode": mode,
        "commandId": command.commandId,
        "message": message,
        "data": {"robotResponseType": response.get("type")},
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("CONTROL_GATEWAY_HOST", "127.0.0.1"),
        port=int(os.getenv("CONTROL_GATEWAY_PORT", "9100") or "9100"),
    )
