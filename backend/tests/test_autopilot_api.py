import re

from fastapi.testclient import TestClient

import app_core as app_module


def fake_admin():
    return {
        "id": 1,
        "username": "admin",
        "password_hash": "hash",
        "display_name": "Admin",
        "status": "active",
        "created_at": "2026-03-10T12:00",
    }


def login_token(client: TestClient) -> str:
    response = client.get("/login")
    match = re.search(r'loginToken:\s*"([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client: TestClient):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123", "loginToken": login_token(client)})
    assert response.status_code == 200


def mock_auth(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "ensure_database", lambda: None)
    monkeypatch.setattr(app_module, "execute_schema", lambda: None)
    monkeypatch.setattr(app_module, "ensure_iot_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_autonomy_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_device_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: fake_admin())
    monkeypatch.setattr(app_module, "verify_password", lambda password, password_hash: True)


def reset_runtime():
    app_module.AUTOPILOT_RUNTIME.reset()
    app_module.AUTOPILOT_RUNTIME.configure_persistence(None, None)


def test_autopilot_status_returns_state_without_login():
    reset_runtime()

    with TestClient(app_module.app) as client:
        response = client.get("/api/autopilot/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "manual"
    assert payload["estop"] is False
    assert payload["lidar"]["online"] is False


def test_start_without_fresh_lidar_stays_auto_ready(monkeypatch):
    reset_runtime()
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/autopilot/start", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "auto_ready"
    assert payload["reason"] == "lidar_timeout"
    assert payload["mode"] != "auto_running"


def test_estop_blocks_start_until_cleared(monkeypatch):
    reset_runtime()
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        estop = client.post("/api/autopilot/estop", json={})
        blocked = client.post("/api/autopilot/start", json={})
        blocked_resume = client.post("/api/autopilot/resume", json={})
        cleared = client.post("/api/autopilot/clear-estop", json={})

    assert estop.status_code == 200
    assert estop.json()["mode"] == "estop"
    assert blocked.status_code == 409
    assert blocked_resume.status_code == 409
    assert cleared.status_code == 200
    assert cleared.json()["mode"] == "manual"


def test_fresh_lidar_allows_auto_running(monkeypatch):
    reset_runtime()
    mock_auth(monkeypatch)
    app_module.AUTOPILOT_RUNTIME.update_report(
        {
            "mode": "auto_ready",
            "lidar": {
                "online": True,
                "ageSeconds": 0.0,
                "frontMin": 1.5,
                "leftFrontMin": 1.2,
                "rightFrontMin": 1.4,
                "obstacleStatus": "front_clear",
            },
        }
    )

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/autopilot/start", json={})

    assert response.status_code == 200
    assert response.json()["mode"] == "auto_running"


def test_pause_resume_stop_endpoints(monkeypatch):
    reset_runtime()
    mock_auth(monkeypatch)
    app_module.AUTOPILOT_RUNTIME.update_report(
        {
            "mode": "auto_ready",
            "lidar": {
                "online": True,
                "ageSeconds": 0.0,
                "frontMin": 1.5,
                "leftFrontMin": 1.2,
                "rightFrontMin": 1.4,
                "obstacleStatus": "front_clear",
            },
        }
    )
    monkeypatch.setattr(app_module, "robot_control_stop_result", lambda payload: {"ok": True})

    with TestClient(app_module.app) as client:
        login(client)
        started = client.post("/api/autopilot/start", json={})
        paused = client.post("/api/autopilot/pause", json={})
        resumed = client.post("/api/autopilot/resume", json={})
        stopped = client.post("/api/autopilot/stop", json={})

    assert started.status_code == 200
    assert started.json()["mode"] == "auto_running"
    assert paused.status_code == 200
    assert paused.json()["mode"] == "paused"
    assert resumed.status_code == 200
    assert resumed.json()["mode"] == "auto_running"
    assert stopped.status_code == 200
    assert stopped.json()["mode"] == "manual"


def test_manual_cmd_vel_pauses_running_autopilot(monkeypatch):
    reset_runtime()
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"id": 4, "model": "R1", "ip_address": "192.168.1.10"})
    monkeypatch.setattr(app_module, "send_robot_control_message", lambda *args, **kwargs: {"type": "ack", "ok": True})

    app_module.AUTOPILOT_RUNTIME.update_report(
        {
            "mode": "auto_ready",
            "lidar": {
                "online": True,
                "ageSeconds": 0.0,
                "frontMin": 1.5,
                "leftFrontMin": 1.2,
                "rightFrontMin": 1.4,
                "obstacleStatus": "front_clear",
            },
        }
    )
    app_module.AUTOPILOT_RUNTIME.start(robot_id=4)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/robot-control/cmd_vel", json={"robotId": 4, "linear": 0.1, "angular": 0.0})

    assert response.status_code == 200
    status = app_module.AUTOPILOT_RUNTIME.status(include_events=False)
    assert status["mode"] == "paused"
    assert status["manualOverride"] is True
    assert status["reason"] == "manual_override"
