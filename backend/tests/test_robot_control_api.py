import re

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main as app_module


def fake_admin():
    return {
        "id": 1,
        "username": "admin",
        "password_hash": "hash",
        "display_name": "Admin",
        "status": "active",
        "created_at": "2026-03-10T12:00",
    }


def login(client: TestClient):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123", "loginToken": login_token(client)})
    assert response.status_code == 200


def login_token(client: TestClient) -> str:
    response = client.get("/login")
    match = re.search(r'loginToken:\s*"([^"]+)"', response.text)
    assert match
    return match.group(1)


def mock_auth(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "ensure_database", lambda: None)
    monkeypatch.setattr(app_module, "execute_schema", lambda: None)
    monkeypatch.setattr(app_module, "ensure_iot_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: fake_admin())
    monkeypatch.setattr(app_module, "verify_password", lambda password, password_hash: True)


@pytest.fixture(autouse=True)
def reset_control_state(monkeypatch):
    monkeypatch.delenv("ROBOT_CONTROL_HOST", raising=False)
    monkeypatch.delenv("ROBOT_CONTROL_PORT", raising=False)
    monkeypatch.delenv("CONTROL_GATEWAY_URL", raising=False)
    app_module.close_robot_control_socket()
    yield
    app_module.close_robot_control_socket()


def robot_row(ip_address="192.168.31.198"):
    return {"id": 4, "model": "巡检机器人-02", "ip_address": ip_address}


def test_control_status_requires_selected_robot_without_env(monkeypatch):
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robot-control/status")

    assert response.status_code == 422
    assert "请选择要控制的机器人" in response.json()["detail"]


def test_control_status_uses_robot_ip_target(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}
    monkeypatch.setenv("ROBOT_CONTROL_PORT", "9100")
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())

    def fake_send(target, payload, expected_type):
        captured.update({"target": target, "payload": payload, "expected": expected_type})
        return {"type": "pong", "ok": True}

    monkeypatch.setattr(app_module, "send_robot_control_message", fake_send)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robot-control/status?robotId=4")

    assert response.status_code == 200
    assert captured["target"]["host"] == "192.168.31.198"
    assert captured["target"]["port"] == 9100
    assert captured["payload"] == {"type": "ping"}
    assert response.json()["target"]["robotId"] == 4


def test_control_status_allows_explicit_env_target(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}
    monkeypatch.setenv("ROBOT_CONTROL_HOST", "192.168.31.200")

    def fake_send(target, payload, expected_type):
        captured.update({"target": target, "payload": payload, "expected": expected_type})
        return {"type": "pong", "ok": True}

    monkeypatch.setattr(app_module, "send_robot_control_message", fake_send)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robot-control/status")

    assert response.status_code == 200
    assert captured["target"]["robotId"] is None
    assert captured["target"]["host"] == "192.168.31.200"


def test_control_unknown_robot_returns_404(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: None)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robot-control/status?robotId=999")

    assert response.status_code == 404
    assert "未找到对应机器人" in response.json()["detail"]


def test_control_robot_without_ip_returns_422(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row(""))

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robot-control/status?robotId=4")

    assert response.status_code == 422
    assert "未配置 IP" in response.json()["detail"]


def test_cmd_vel_clamps_speed_and_forwards_robot_id(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())

    def fake_send(target, payload, expected_type):
        captured.update({"target": target, "payload": payload, "expected": expected_type})
        return {"type": "ack", "ok": True}

    monkeypatch.setattr(app_module, "send_robot_control_message", fake_send)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/robot-control/cmd_vel",
            json={"robotId": 4, "linear": 9, "angular": -9},
        )

    assert response.status_code == 200
    assert captured["payload"] == {"type": "cmd_vel", "v": 0.4, "w": -1.2}
    assert response.json()["linear"] == 0.4
    assert response.json()["angular"] == -1.2


def test_stop_forwards_selected_robot(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())

    def fake_send(target, payload, expected_type):
        captured.update({"target": target, "payload": payload, "expected": expected_type})
        return {"type": "ack", "ok": True}

    monkeypatch.setattr(app_module, "send_robot_control_message", fake_send)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robot-control/stop", json={"robotId": 4})

    assert response.status_code == 200
    assert captured["payload"] == {"type": "stop"}
    assert response.json()["target"]["ipAddress"] == "192.168.31.198"


def test_control_service_unavailable_returns_502(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())

    def raise_connect_error(address, timeout):
        raise OSError("refused")

    monkeypatch.setattr(app_module.socket, "create_connection", raise_connect_error)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robot-control/status?robotId=4")

    assert response.status_code == 502
    assert "不可达" in response.json()["detail"]


def test_control_reconnects_when_cached_socket_is_stale(monkeypatch):
    target = {"host": "192.168.31.198", "port": 9000}
    key = app_module.robot_control_target_key(target)

    class StaleSocket:
        closed = False

        def sendall(self, payload):
            raise BrokenPipeError("stale")

        def close(self):
            self.closed = True

    class FreshSocket:
        closed = False
        payload = b""

        def settimeout(self, timeout):
            self.timeout = timeout

        def sendall(self, payload):
            self.payload = payload

        def recv(self, size):
            return b'{"type":"pong","ok":true}\n'

        def close(self):
            self.closed = True

    stale_socket = StaleSocket()
    fresh_socket = FreshSocket()
    app_module.ROBOT_CONTROL_STATE["connections"][key] = {"socket": stale_socket, "buffer": b""}
    monkeypatch.setattr(app_module.socket, "create_connection", lambda address, timeout: fresh_socket)

    response = app_module.send_robot_control_message(target, {"type": "ping"}, "pong")

    assert response == {"type": "pong", "ok": True}
    assert stale_socket.closed is True
    assert fresh_socket.payload == b'{"type":"ping"}\n'


def test_control_timeout_raises_504(monkeypatch):
    monkeypatch.setenv("ROBOT_CONTROL_HOST", "192.168.31.200")

    class FakeSocket:
        def sendall(self, payload):
            self.payload = payload

        def close(self):
            self.closed = True

    ticks = [0]

    def fake_time():
        ticks[0] += 3
        return ticks[0]

    monkeypatch.setattr(app_module, "get_robot_control_socket", lambda config: FakeSocket())
    monkeypatch.setattr(app_module.time, "time", fake_time)

    with pytest.raises(HTTPException) as exc_info:
        app_module.send_robot_control_message(app_module.env_robot_control_target(), {"type": "ping"}, "pong")

    assert exc_info.value.status_code == 504


def test_cmd_vel_keeps_control_socket_open(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())
    target = {"host": "192.168.31.198", "port": 9000}
    key = app_module.robot_control_target_key(target)

    class FakeSocket:
        closed = False
        payload = b""

        def settimeout(self, timeout):
            self.timeout = timeout

        def sendall(self, payload):
            self.payload = payload

        def recv(self, size):
            return b'{"type":"ack","ok":true,"rosOk":true,"cmdVelSubscribers":1}\n'

        def close(self):
            self.closed = True

    fake_socket = FakeSocket()
    monkeypatch.setattr(app_module.socket, "create_connection", lambda address, timeout: fake_socket)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/robot-control/cmd_vel",
            json={"robotId": 4, "linear": 0.1, "angular": 0.2},
        )

    assert response.status_code == 200
    assert fake_socket.closed is False
    assert app_module.ROBOT_CONTROL_STATE["connections"][key]["socket"] is fake_socket


def test_stop_closes_control_socket(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())
    target = {"host": "192.168.31.198", "port": 9000}
    key = app_module.robot_control_target_key(target)

    class FakeSocket:
        closed = False

        def sendall(self, payload):
            self.payload = payload

        def recv(self, size):
            return b'{"type":"ack","ok":true}\n'

        def close(self):
            self.closed = True

    fake_socket = FakeSocket()
    app_module.ROBOT_CONTROL_STATE["connections"][key] = {"socket": fake_socket, "buffer": b""}

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robot-control/stop", json={"robotId": 4})

    assert response.status_code == 200
    assert fake_socket.closed is True
    assert key not in app_module.ROBOT_CONTROL_STATE["connections"]


def test_cmd_vel_rejected_by_robot_returns_502(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())

    def fake_send(target, payload, expected_type, close_after=True):
        return {"type": "ack", "ok": False, "err": "cmd_vel_no_subscriber"}

    monkeypatch.setattr(app_module, "send_robot_control_message", fake_send)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/robot-control/cmd_vel",
            json={"robotId": 4, "linear": 0.1, "angular": 0.2},
        )

    assert response.status_code == 502
    assert "/cmd_vel" in response.json()["detail"]


def test_non_admin_cannot_control_robot(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator"})

    with TestClient(app_module.app) as client:
        response = client.get("/api/robot-control/status?robotId=4")

    assert response.status_code == 403


def test_unified_control_command_forwards_robot_motion(monkeypatch):
    mock_auth(monkeypatch)
    writes = []
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: robot_row())
    monkeypatch.setattr(app_module, "execute_insert", lambda sql, params=None: 77)
    monkeypatch.setattr(app_module, "execute_write", lambda sql, params=None: writes.append((sql, params)) or 1)

    def fake_send(target, payload, expected_type):
        assert target["host"] == "192.168.31.198"
        assert payload == {"type": "cmd_vel", "v": 0.1, "w": 0.0}
        assert expected_type == "ack"
        return {"type": "ack", "ok": True}

    monkeypatch.setattr(app_module, "send_robot_control_message", fake_send)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={
                "scope": "device",
                "targetType": "robot",
                "targetId": 4,
                "commandType": "cmd_vel",
                "params": {"linear": 0.1, "angular": 0},
            },
        )

    assert response.status_code == 200
    assert response.json()["commandId"] == 77
    assert any(params and params[0] == "success" for _, params in writes)


def test_unified_control_gateway_missing_returns_502_and_failed_record(monkeypatch):
    mock_auth(monkeypatch)
    writes = []
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"id": 1})
    monkeypatch.setattr(app_module, "execute_insert", lambda sql, params=None: 88)
    monkeypatch.setattr(app_module, "execute_write", lambda sql, params=None: writes.append((sql, params)) or 1)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={
                "scope": "device",
                "targetType": "sensor",
                "targetId": 1,
                "commandType": "sensor_control",
                "params": {"enabled": True},
            },
        )

    assert response.status_code == 502
    assert "真实控制网关未配置" in response.json()["detail"]
    assert any(params and params[0] == "failed" for _, params in writes)


def test_unified_control_missing_gateway_target_returns_404(monkeypatch):
    mock_auth(monkeypatch)
    writes = []
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: None)
    monkeypatch.setattr(app_module, "execute_insert", lambda sql, params=None: 89)
    monkeypatch.setattr(app_module, "execute_write", lambda sql, params=None: writes.append((sql, params)) or 1)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={
                "scope": "device",
                "targetType": "network",
                "targetId": 404,
                "commandType": "network_control",
                "params": {"enabled": True},
            },
        )

    assert response.status_code == 404
    assert "未找到对应控制目标" in response.json()["detail"]
    assert any(params and params[0] == "failed" for _, params in writes)


def test_non_admin_cannot_create_unified_control_command(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator"})

    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/control/commands",
            json={
                "scope": "device",
                "targetType": "robot",
                "targetId": 4,
                "commandType": "stop",
                "params": {},
            },
        )

    assert response.status_code == 403
