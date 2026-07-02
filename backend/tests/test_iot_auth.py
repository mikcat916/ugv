from fastapi.testclient import TestClient

import app_core as app_module


async def fake_ws_broadcast(event: str):
    return None


def mock_startup(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "ensure_database", lambda: None)
    monkeypatch.setattr(app_module, "execute_schema", lambda: None)
    monkeypatch.setattr(app_module, "ensure_iot_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_device_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)


def test_iot_tokens_require_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.get("/api/iot/tokens")

    assert response.status_code == 403


def test_iot_tokens_allow_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "admin", "display_name": "Admin"})
    monkeypatch.setattr(app_module, "query_all", lambda sql, params=None: [])

    with TestClient(app_module.app) as client:
        response = client.get("/api/iot/tokens")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_lidar_payload_can_be_written(monkeypatch):
    mock_startup(monkeypatch)
    captured = {}

    monkeypatch.setattr(app_module, "iot_ingest_throttle_interval", lambda request: None)
    monkeypatch.setattr(app_module, "require_device_token", lambda request: 2)
    monkeypatch.setattr(app_module, "ws_broadcast", fake_ws_broadcast)
    monkeypatch.setattr(
        app_module,
        "execute_insert",
        lambda sql, params=None: captured.update(sql=sql, params=params) or 10,
    )

    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/iot/sensor/data",
            json={
                "sensorType": "lidar",
                "channel": "scan",
                "data": {
                    "ranges": [1.0, None, 2.5],
                    "angleMin": 0,
                    "angleIncrement": 0.1,
                    "rangeMin": 0.12,
                    "rangeMax": 12.0,
                },
                "extra": {"sourceTopic": "/scan"},
            },
        )

    assert response.status_code == 200
    assert response.json()["sensorType"] == "lidar"
    assert captured["params"][0] == 2
    assert captured["params"][1] == "lidar"
    assert captured["params"][2] == "scan"
    assert '"ranges": [1.0, null, 2.5]' in captured["params"][3]


def test_lidar_payload_rejects_invalid_ranges(monkeypatch):
    mock_startup(monkeypatch)

    monkeypatch.setattr(app_module, "iot_ingest_throttle_interval", lambda request: None)
    monkeypatch.setattr(app_module, "require_device_token", lambda request: 2)
    monkeypatch.setattr(app_module, "execute_insert", lambda *args, **kwargs: None)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/iot/sensor/data",
            json={
                "sensorType": "lidar",
                "channel": "scan",
                "data": {"ranges": [1.0, 0, 2.5], "angleMin": 0, "angleIncrement": 0.1},
            },
        )

    assert response.status_code == 422
    assert "ranges[1]" in response.json()["detail"]


def test_lidar_payload_rejects_oversized_json(monkeypatch):
    mock_startup(monkeypatch)

    monkeypatch.setattr(app_module, "iot_ingest_throttle_interval", lambda request: None)
    monkeypatch.setattr(app_module, "require_device_token", lambda request: 2)
    monkeypatch.setattr(app_module, "execute_insert", lambda *args, **kwargs: None)

    with TestClient(app_module.app) as client:
        response = client.post(
            "/api/iot/sensor/data",
            json={
                "sensorType": "lidar",
                "channel": "scan",
                "data": {
                    "ranges": [1.0],
                    "angleMin": 0,
                    "angleIncrement": 0.1,
                    "debugBlob": "x" * (1024 * 1024 + 1),
                },
            },
        )

    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]
