#!/usr/bin/env python3
"""Poll Project4 queued control commands and execute them on the robot."""

from __future__ import annotations

import argparse
import configparser
import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CONFIG_FILE = Path(__file__).resolve().parent / "iot_client.conf"
HTTP_TIMEOUT_SEC = 10
CONTROL_TIMEOUT_SEC = 3
LOCAL_CONTROL_HOST = "127.0.0.1"
LOCAL_CONTROL_PORT = 9000
LOCAL_CONTROL_IDLE_CLOSE_SEC = 1.0


class LocalControlBridge:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.active_socket: socket.socket | None = None
        self.buffer = b""
        self.last_used_at = 0.0

    def send(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            active_socket = self.open_socket()
            active_socket.sendall((json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8"))
            response = self.read_response()
            self.last_used_at = time.time()
            return response
        except Exception:
            self.close()
            raise

    def open_socket(self) -> socket.socket:
        if self.active_socket is None:
            self.active_socket = socket.create_connection((self.host, self.port), timeout=CONTROL_TIMEOUT_SEC)
            self.active_socket.settimeout(CONTROL_TIMEOUT_SEC)
        return self.active_socket

    def read_response(self) -> dict[str, Any]:
        while True:
            payload = json.loads(self.read_line().decode("utf-8"))
            if payload.get("type") != "status":
                return payload

    def read_line(self) -> bytes:
        active_socket = self.open_socket()
        while b"\n" not in self.buffer:
            chunk = active_socket.recv(4096)
            if not chunk:
                raise RuntimeError("local control bridge closed the connection")
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line

    def close(self) -> None:
        if self.active_socket is None:
            return
        self.active_socket.close()
        self.active_socket = None
        self.buffer = b""
        self.last_used_at = 0.0

    def close_if_idle(self, now: float) -> None:
        if self.active_socket is None or self.last_used_at <= 0:
            return
        if now - self.last_used_at >= LOCAL_CONTROL_IDLE_CLOSE_SEC:
            self.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project4 queued control poller")
    parser.add_argument("--config", default=str(CONFIG_FILE))
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--control-host", default=LOCAL_CONTROL_HOST)
    parser.add_argument("--control-port", type=int, default=LOCAL_CONTROL_PORT)
    return parser.parse_args()


def load_config(path: str) -> dict[str, str]:
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    server = cfg.get("client", "server", fallback="").strip().rstrip("/")
    token = cfg.get("client", "token", fallback="").strip()
    if not server:
        raise RuntimeError("missing server in config")
    if not token:
        raise RuntimeError("missing token in config")
    return {"server": server, "token": token}


def request_json(config: dict[str, str], path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict:
    data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8") if method != "GET" else None
    request = urllib.request.Request(
        config["server"] + path,
        data=data,
        headers={"Content-Type": "application/json", "X-Device-Token": config["token"]},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc


def next_command(config: dict[str, str]) -> dict[str, Any] | None:
    payload = request_json(config, "/api/iot/control/commands")
    return payload.get("command")


def ack_command(config: dict[str, str], command_id: int, ok: bool, response: Any = None, error: str = "") -> None:
    request_json(
        config,
        f"/api/iot/control/commands/{command_id}/ack",
        method="POST",
        body={"ok": ok, "response": response, "error": error},
    )


def execute_command(command: dict[str, Any], bridge: LocalControlBridge) -> dict[str, Any]:
    command_type = str(command.get("type") or "")
    params = command.get("params") or {}
    if command_type == "stop":
        return bridge.send({"type": "stop"})
    if command_type == "cmd_vel":
        return bridge.send({"type": "cmd_vel", "v": float(params.get("linear", 0.0)), "w": float(params.get("angular", 0.0))})
    if command_type == "connectivity_test":
        return bridge.send({"type": "ping"})
    raise RuntimeError(f"unsupported command type: {command_type}")


def send_control_message(message: dict[str, Any], host: str, port: int) -> dict[str, Any]:
    bridge = LocalControlBridge(host, port)
    try:
        return bridge.send(message)
    finally:
        bridge.close()


def read_json_line(active_socket: socket.socket) -> dict[str, Any]:
    buffer = b""
    while b"\n" not in buffer:
        chunk = active_socket.recv(4096)
        if not chunk:
            raise RuntimeError("local control bridge closed the connection")
        buffer += chunk
    line = buffer.split(b"\n", 1)[0]
    return json.loads(line.decode("utf-8"))


def run_once(config: dict[str, str], bridge: LocalControlBridge) -> None:
    command = next_command(config)
    if not command:
        bridge.close_if_idle(time.time())
        return
    command_id = int(command["id"])
    try:
        response = execute_command(command, bridge)
        ack_command(config, command_id, bool(response.get("ok", response.get("type") == "pong")), response=response)
        print(f"command {command_id} executed: {response}", flush=True)
    except Exception as exc:
        ack_command(config, command_id, False, error=str(exc))
        print(f"command {command_id} failed: {exc}", flush=True)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    bridge = LocalControlBridge(args.control_host, args.control_port)
    while True:
        try:
            run_once(config, bridge)
        except Exception as exc:
            print(f"poll failed: {exc}", flush=True)
        time.sleep(max(0.1, args.interval))


if __name__ == "__main__":
    main()
