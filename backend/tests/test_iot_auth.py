from fastapi.testclient import TestClient

import main as app_module


def mock_startup(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "ensure_database", lambda: None)
    monkeypatch.setattr(app_module, "execute_schema", lambda: None)
    monkeypatch.setattr(app_module, "ensure_iot_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
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
