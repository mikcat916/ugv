from __future__ import annotations

import importlib.util
import socket
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "device" / "control_gateway.py"
SPEC = importlib.util.spec_from_file_location("control_gateway_module", SCRIPT_PATH)
control_gateway = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(control_gateway)

TOKEN = "test-control-gateway-token"


class FakeSocket:
    def __init__(self, responses: list[bytes | BaseException]):
        self.responses = list(responses)
        self.sent: list[bytes] = []
        self.timeouts: list[float] = []
        self.closed = False

    def settimeout(self, timeout: float) -> None:
        self.timeouts.append(timeout)

    def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    def recv(self, _size: int) -> bytes:
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def close(self) -> None:
        self.closed = True


def command_payload(command_type: str = "connectivity_test") -> dict[str, Any]:
    return {
        "commandId": 123,
        "targetType": "cluster_node",
        "targetId": 7,
        "commandType": command_type,
        "params": {},
        "target": {
            "clusterNodeId": 7,
            "clusterId": 2,
            "robotId": 4,
            "host": "192.0.2.10",
            "port": 9000,
        },
    }


def auth_headers(token: str = TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def isolated_gateway(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_TOKEN", TOKEN)
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "dry_run")
    monkeypatch.setenv("ROBOT_CONTROL_TIMEOUT_SECONDS", "2")

    def reject_real_network(*_args, **_kwargs):
        raise AssertionError("Unit tests must not access the real network")

    monkeypatch.setattr(control_gateway.socket, "create_connection", reject_real_network)


def install_fake_socket(monkeypatch, fake_socket: FakeSocket) -> list[tuple[tuple[str, int], float]]:
    calls: list[tuple[tuple[str, int], float]] = []

    def create_connection(address: tuple[str, int], timeout: float):
        calls.append((address, timeout))
        return fake_socket

    monkeypatch.setattr(control_gateway.socket, "create_connection", create_connection)
    return calls


def test_health_reports_mode_and_token_configuration(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")

    with TestClient(control_gateway.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "live", "tokenConfigured": True}


@pytest.mark.parametrize("headers", [{}, auth_headers("wrong-token")])
def test_command_rejects_missing_or_wrong_token(headers):
    with TestClient(control_gateway.app) as client:
        response = client.post("/v1/commands", headers=headers, json=command_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "\u63a7\u5236\u7f51\u5173\u8eab\u4efd\u9a8c\u8bc1\u5931\u8d25\u3002"}


def test_dry_run_accepts_correct_token_without_opening_socket():
    with TestClient(control_gateway.app) as client:
        response = client.post("/v1/commands", headers=auth_headers(), json=command_payload())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "executed": False,
        "mode": "dry_run",
        "commandId": 123,
        "message": "\u6a21\u62df\u6a21\u5f0f\uff1a\u547d\u4ee4\u5df2\u9a8c\u8bc1\uff0c\u4f46\u6ca1\u6709\u8fde\u63a5\u771f\u5b9e\u673a\u5668\u4eba\u3002",
        "data": {"commandType": "connectivity_test"},
    }


def test_live_connectivity_test_sends_ping_and_accepts_pong(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")
    fake_socket = FakeSocket([b'{"type":"pong"}\n'])
    calls = install_fake_socket(monkeypatch, fake_socket)

    with TestClient(control_gateway.app) as client:
        response = client.post("/v1/commands", headers=auth_headers(), json=command_payload())

    assert response.status_code == 200
    assert response.json()["executed"] is True
    assert response.json()["data"] == {"robotResponseType": "pong"}
    assert calls == [(("192.0.2.10", 9000), 2.0)]
    assert fake_socket.sent == [b'{"type":"ping"}\n']
    assert fake_socket.timeouts == [2.0]
    assert fake_socket.closed is True


def test_live_node_exit_sends_stop_and_accepts_ack(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")
    fake_socket = FakeSocket([b'{"type":"ack","ok":true}\n'])
    install_fake_socket(monkeypatch, fake_socket)

    with TestClient(control_gateway.app) as client:
        response = client.post(
            "/v1/commands",
            headers=auth_headers(),
            json=command_payload("node_exit"),
        )

    assert response.status_code == 200
    assert response.json()["executed"] is True
    assert response.json()["message"] == "\u8282\u70b9\u5df2\u505c\u8f66\uff0c\u53ef\u4ee5\u9000\u51fa\u96c6\u7fa4\u3002"
    assert response.json()["data"] == {"robotResponseType": "ack"}
    assert fake_socket.sent == [b'{"type":"stop"}\n']
    assert fake_socket.closed is True


def test_live_node_exit_rejects_failed_stop_ack(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")
    fake_socket = FakeSocket([b'{"type":"ack","ok":false}\n'])
    install_fake_socket(monkeypatch, fake_socket)

    with TestClient(control_gateway.app) as client:
        response = client.post(
            "/v1/commands",
            headers=auth_headers(),
            json=command_payload("node_exit"),
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "\u673a\u5668\u4eba\u63a7\u5236\u670d\u52a1\u62d2\u7edd\u505c\u8f66\uff0c\u8282\u70b9\u4e0d\u80fd\u9000\u51fa\u3002"}
    assert fake_socket.closed is True


def test_live_connection_failure_returns_502(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")

    def raise_connect_error(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(control_gateway.socket, "create_connection", raise_connect_error)

    with TestClient(control_gateway.app) as client:
        response = client.post("/v1/commands", headers=auth_headers(), json=command_payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "\u673a\u5668\u4eba\u63a7\u5236\u670d\u52a1\u4e0d\u53ef\u8fbe\u3002"}


def test_live_timeout_returns_504_and_closes_socket(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")
    fake_socket = FakeSocket([socket.timeout("timed out")])
    install_fake_socket(monkeypatch, fake_socket)

    with TestClient(control_gateway.app) as client:
        response = client.post("/v1/commands", headers=auth_headers(), json=command_payload())

    assert response.status_code == 504
    assert response.json() == {"detail": "\u673a\u5668\u4eba\u63a7\u5236\u670d\u52a1\u54cd\u5e94\u8d85\u65f6\u3002"}
    assert fake_socket.closed is True


def test_live_invalid_json_returns_502_and_closes_socket(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")
    fake_socket = FakeSocket([b'not-json\n'])
    install_fake_socket(monkeypatch, fake_socket)

    with TestClient(control_gateway.app) as client:
        response = client.post("/v1/commands", headers=auth_headers(), json=command_payload())

    assert response.status_code == 502
    assert response.json() == {"detail": "\u673a\u5668\u4eba\u63a7\u5236\u670d\u52a1\u8fd4\u56de\u683c\u5f0f\u9519\u8bef\u3002"}
    assert fake_socket.closed is True


def test_unsupported_command_returns_422_without_opening_socket(monkeypatch):
    monkeypatch.setenv("CONTROL_GATEWAY_MODE", "live")

    with TestClient(control_gateway.app) as client:
        response = client.post(
            "/v1/commands",
            headers=auth_headers(),
            json=command_payload("reboot"),
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "\u63a7\u5236\u7f51\u5173\u4ec5\u652f\u6301\u8fde\u901a\u6027\u68c0\u6d4b\u548c\u8282\u70b9\u9000\u51fa\u547d\u4ee4\u3002"}
