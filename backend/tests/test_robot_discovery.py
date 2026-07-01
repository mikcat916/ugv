import re
from datetime import datetime, timedelta

from fastapi import HTTPException
from fastapi.testclient import TestClient

import main as app_module


def fake_user():
    return {
        "id": 1,
        "username": "admin",
        "password_hash": "hash",
        "display_name": "Admin User",
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
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: fake_user())
    monkeypatch.setattr(app_module, "verify_password", lambda password, password_hash: True)


async def fake_ws_broadcast(event: str):
    return None


def test_robot_discovery_endpoint_returns_candidates(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(
        app_module,
        "discover_robot_candidates",
        lambda force=False: {
            "items": [
                {
                    "ipAddress": "192.168.31.101",
                    "hostName": "raspberrypi",
                    "macAddress": "2C:CF:67:06:98:4C",
                    "openPorts": [22],
                    "confirmed": True,
                    "summary": "hostname=raspberrypi, mac=2C:CF:67:06:98:4C, ssh",
                }
            ],
            "scannedAt": "2026-03-30T10:00:00",
            "expiresAt": "2026-03-30T10:05:00",
            "subnets": ["192.168.31.0/24"],
        },
    )

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/discovery?refresh=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["ipAddress"] == "192.168.31.101"
    assert payload["items"][0]["confirmed"] is True


def test_create_robot_rejects_undiscovered_ip(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "get_discovered_robot", lambda ip_address: None)

    payload = {
        "model": "巡检机器人01",
        "ipAddress": "192.168.31.101",
        "status": "idle",
        "health": 92,
        "battery": 78,
        "speed": 1.2,
        "signal": 88,
        "latency": 28,
        "lng": 121.81742,
        "lat": 31.09161,
        "heading": 0,
    }

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robots", json=payload)

    assert response.status_code == 422
    assert "扫描" in response.json()["detail"]


def test_create_robot_accepts_confirmed_discovered_ip(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}

    def fake_execute_write(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return 1

    monkeypatch.setattr(
        app_module,
        "get_discovered_robot",
        lambda ip_address: {"ipAddress": ip_address, "confirmed": True, "hostName": "raspberrypi"},
    )
    monkeypatch.setattr(app_module, "execute_write", fake_execute_write)
    monkeypatch.setattr(app_module, "ws_broadcast", fake_ws_broadcast)

    payload = {
        "model": "巡检机器人01",
        "ipAddress": "192.168.31.101",
        "status": "idle",
        "health": 92,
        "battery": 78,
        "speed": 1.2,
        "signal": 88,
        "latency": 28,
        "lng": 121.81742,
        "lat": 31.09161,
        "heading": 0,
    }

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robots", json=payload)

    assert response.status_code == 200
    assert captured["params"][1] == "192.168.31.101"


def test_wheeltec_hostname_with_ssh_is_confirmed():
    confirmed, summary = app_module.classify_robot_candidate("wheeltec", "", [22], None)

    assert confirmed is True
    assert "hostname=wheeltec" in summary


def test_create_robot_accepts_manual_confirmed_candidate(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}

    def fake_execute_write(sql, params=None):
        captured["params"] = params
        return 1

    monkeypatch.setattr(
        app_module,
        "get_discovered_robot",
        lambda ip_address: {"ipAddress": ip_address, "confirmed": False, "hostName": "unknown"},
    )
    monkeypatch.setattr(app_module, "execute_write", fake_execute_write)
    monkeypatch.setattr(app_module, "ws_broadcast", fake_ws_broadcast)

    payload = {
        "model": "人工确认机器人",
        "ipAddress": "192.168.31.88",
        "manualConfirm": True,
        "lng": 121.81742,
        "lat": 31.09161,
    }

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robots", json=payload)

    assert response.status_code == 200
    assert captured["params"][1] == "192.168.31.88"


def test_iot_telemetry_persists_source_ip(monkeypatch):
    captured = {}

    def fake_execute_insert(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return 1

    monkeypatch.setattr(app_module, "require_device_token", lambda request: 2)
    monkeypatch.setattr(app_module, "execute_insert", fake_execute_insert)
    monkeypatch.setattr(app_module, "execute_write", lambda *args, **kwargs: 1)
    monkeypatch.setattr(app_module, "ws_broadcast", fake_ws_broadcast)

    payload = {
        "battery": 85,
        "signal": 72,
        "status": "online",
        "lat": 31.09161,
        "lng": 121.81742,
        "reportedAt": "2026-03-30T10:00:00",
    }

    with TestClient(app_module.app) as client:
        response = client.post("/api/iot/telemetry", json=payload)

    assert response.status_code == 200
    assert captured["params"][6] == "testclient"


def test_iot_camera_snapshot_upload_saves_robot_frame(monkeypatch, tmp_path):
    jpeg = b"\xff\xd8\xff\xe0real-camera-frame"

    monkeypatch.setattr(app_module, "require_device_token", lambda request: 2)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"robot_id": 6})
    monkeypatch.setattr(app_module, "robot_camera_upload_path", lambda robot_id: tmp_path / f"{robot_id}.jpg")
    monkeypatch.setattr(app_module, "ws_broadcast", fake_ws_broadcast)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/iot/camera/snapshot",
            files={"file": ("snapshot.jpg", jpeg, "image/jpeg")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["robotId"] == 6
    assert payload["size"] == len(jpeg)
    assert (tmp_path / "6.jpg").read_bytes() == jpeg


def test_robot_camera_snapshot_uses_fresh_uploaded_when_live_unavailable(monkeypatch):
    jpeg = b"\xff\xd8\xff\xe0uploaded-camera-frame"

    mock_auth(monkeypatch)
    monkeypatch.setattr(
        app_module,
        "load_robot_camera_target",
        lambda robot_id: {"id": robot_id, "model": "Wheeltec", "ip_address": "192.168.31.88"},
    )
    monkeypatch.setattr(
        app_module,
        "latest_uploaded_camera_snapshot",
        lambda robot_id: {
            "content": jpeg,
            "contentType": "image/jpeg",
            "reportedAt": datetime.now(),
            "stale": False,
            "source": "uploaded",
        },
    )

    async def fake_snapshot(ip_address):
        raise HTTPException(status_code=502, detail="摄像头快照不可达。")

    monkeypatch.setattr(app_module, "fetch_robot_camera_snapshot", fake_snapshot)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/6/camera/snapshot")

    assert response.status_code == 200
    assert response.headers["x-camera-source"] == "uploaded"
    assert response.headers["x-camera-stale"] == "0"
    assert response.content == jpeg


def test_robot_camera_snapshot_prefers_live_over_uploaded(monkeypatch):
    jpeg = b"\xff\xd8\xff\xe0live-camera-frame"

    mock_auth(monkeypatch)
    monkeypatch.setattr(
        app_module,
        "load_robot_camera_target",
        lambda robot_id: {"id": robot_id, "model": "Wheeltec", "ip_address": "192.168.31.88"},
    )
    monkeypatch.setattr(
        app_module,
        "latest_uploaded_camera_snapshot",
        lambda robot_id: {
            "content": b"uploaded",
            "contentType": "image/jpeg",
            "reportedAt": datetime.now(),
            "stale": False,
            "source": "uploaded",
        },
    )

    async def fake_snapshot(ip_address):
        return jpeg, "image/jpeg"

    monkeypatch.setattr(app_module, "fetch_robot_camera_snapshot", fake_snapshot)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/6/camera/snapshot")

    assert response.status_code == 200
    assert response.headers["x-camera-source"] == "live"
    assert response.content == jpeg


def test_robot_camera_snapshot_rejects_stale_uploaded_frame(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(
        app_module,
        "load_robot_camera_target",
        lambda robot_id: {"id": robot_id, "model": "Wheeltec", "ip_address": "192.168.31.88"},
    )
    monkeypatch.setattr(
        app_module,
        "latest_uploaded_camera_snapshot",
        lambda robot_id: {
            "content": b"old",
            "contentType": "image/jpeg",
            "reportedAt": datetime.now() - timedelta(seconds=30),
            "stale": True,
            "source": "uploaded",
        },
    )
    monkeypatch.setattr(app_module, "_fallback_iot_snapshot", lambda ip_address: None)

    async def fake_snapshot(ip_address):
        raise HTTPException(status_code=502, detail="摄像头快照不可达。")

    monkeypatch.setattr(app_module, "fetch_robot_camera_snapshot", fake_snapshot)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/6/camera/snapshot")

    assert response.status_code == 502
    assert "没有新鲜" in response.json()["detail"]


def test_robot_sensors_latest_marks_stale_items(monkeypatch):
    mock_auth(monkeypatch)
    now = datetime.now()

    def fake_query_one(sql, params=None):
        if "SELECT ip_address FROM robots" in sql:
            return {"ip_address": "192.168.31.88"}
        if "SELECT device_id FROM device_telemetry" in sql:
            return {"device_id": 2}
        return None

    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    monkeypatch.setattr(app_module, "query_one", fake_query_one)
    monkeypatch.setattr(
        app_module,
        "query_all",
        lambda sql, params=None: [
            {
                "sensor_type": "camera",
                "channel": "mono",
                "file_path": "/static/uploads/cameras/new.jpg",
                "data_json": None,
                "content_type": "image/jpeg",
                "size_bytes": 10,
                "extra_json": None,
                "reported_at": now,
            },
            {
                "sensor_type": "lidar",
                "channel": "scan",
                "file_path": None,
                "data_json": '{"ranges":[1.0],"angleMin":0,"angleIncrement":0.1}',
                "content_type": "application/json",
                "size_bytes": 20,
                "extra_json": None,
                "reported_at": now - timedelta(seconds=30),
            },
        ],
    )

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/6/sensors/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["staleAfterSeconds"] == app_module.camera_stale_seconds()
    assert payload["sensors"][0]["stale"] is False
    assert payload["sensors"][0]["ageSeconds"] <= 5
    assert payload["sensors"][1]["stale"] is True
    assert payload["sensors"][1]["ageSeconds"] >= 30


def test_robot_control_queue_mode_enqueues_cmd_vel(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}

    def fake_insert(payload):
        captured["payload"] = payload
        return 42

    monkeypatch.setattr(app_module, "ROBOT_CONTROL_MODE", "queue")
    monkeypatch.setattr(
        app_module,
        "load_robot_control_target",
        lambda robot_id: {
            "robotId": int(robot_id),
            "model": "Wheeltec",
            "ipAddress": "192.168.31.88",
            "host": "192.168.31.88",
            "port": 9000,
            "maxLinear": 0.4,
            "maxAngular": 1.2,
        },
    )
    monkeypatch.setattr(app_module, "insert_control_command", fake_insert)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robot-control/cmd_vel", json={"robotId": 6, "linear": 9, "angular": -9})

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued"] is True
    assert payload["commandId"] == 42
    assert payload["linear"] == 0.4
    assert payload["angular"] == -1.2
    assert captured["payload"]["targetId"] == 6
    assert captured["payload"]["commandType"] == "cmd_vel"


def test_iot_control_command_poll_and_ack(monkeypatch):
    updates = []

    def fake_query_one(sql, params=None):
        if "SELECT robot_id FROM devices" in sql:
            return {"robot_id": 6}
        if "FROM control_commands" in sql and "JOIN devices" not in sql:
            return {"id": 42, "command_type": "stop", "params_json": "{}"}
        if "JOIN devices" in sql:
            return {"id": 42}
        return None

    def fake_update(command_id, status, response=None, error="", completed=True):
        updates.append((command_id, status, response, error, completed))

    monkeypatch.setattr(app_module, "require_device_token", lambda request: 2)
    monkeypatch.setattr(app_module, "query_one", fake_query_one)
    monkeypatch.setattr(app_module, "update_control_command", fake_update)

    with TestClient(app_module.app) as client:
        poll_response = client.get("/api/iot/control/commands")
        ack_response = client.post(
            "/api/iot/control/commands/42/ack",
            json={"ok": True, "response": {"type": "ack"}},
        )

    assert poll_response.status_code == 200
    assert poll_response.json()["command"] == {"id": 42, "type": "stop", "params": {}}
    assert ack_response.status_code == 200
    assert updates[0] == (42, app_module.CONTROL_COMMAND_DELIVERED_STATUS, None, "", False)
    assert updates[1] == (42, app_module.CONTROL_COMMAND_SUCCESS_STATUS, {"type": "ack"}, "", True)


def test_recent_iot_log_identity_map_falls_back_from_journal(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    monkeypatch.setattr(
        app_module,
        "query_all",
        lambda sql, params=None: [
            {
                "device_id": 2,
                "device_name": "Raspberry Car",
                "device_model": "Pi Robot",
                "reported_at": "2026-03-31T10:51:53",
            }
        ],
    )
    monkeypatch.setattr(
        app_module.subprocess,
        "check_output",
        lambda *args, **kwargs: 'Mar 31 10:51:53 host python[1]: INFO:     192.168.31.200:0 - "POST /api/iot/telemetry HTTP/1.1" 200 OK',
    )

    result = app_module.load_recent_iot_log_identity_map()

    assert result["192.168.31.200"]["deviceId"] == 2
    assert result["192.168.31.200"]["deviceName"] == "Raspberry Car"
