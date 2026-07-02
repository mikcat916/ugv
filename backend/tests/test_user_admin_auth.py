from fastapi.testclient import TestClient

import app_core as app_module


def mock_startup(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "ensure_database", lambda: None)
    monkeypatch.setattr(app_module, "execute_schema", lambda: None)
    monkeypatch.setattr(app_module, "ensure_iot_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_device_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)


def test_users_list_requires_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.get("/api/users")

    assert response.status_code == 403


def test_users_list_allows_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "admin", "display_name": "Admin"})
    monkeypatch.setattr(app_module, "load_users", lambda page, size: {"items": [], "total": 0, "page": page, "size": size})

    with TestClient(app_module.app) as client:
        response = client.get("/api/users")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_create_user_requires_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.post("/api/users", json={"username": "alice", "password": "secret123", "displayName": "Alice"})

    assert response.status_code == 403


def test_update_user_requires_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.put("/api/users/1", json={"displayName": "Alice 2"})

    assert response.status_code == 403


def test_update_user_status_requires_admin(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.patch("/api/users/1/status", json={"status": "disabled"})

    assert response.status_code == 403


def test_update_missing_user_returns_404(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "admin", "display_name": "Admin"})
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: None)

    with TestClient(app_module.app) as client:
        response = client.put("/api/users/999", json={"displayName": "Nobody"})

    assert response.status_code == 404
    assert response.json()["detail"] == "未找到对应用户。"


def test_update_user_rejects_short_password(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "admin", "display_name": "Admin"})

    with TestClient(app_module.app) as client:
        response = client.put("/api/users/1", json={"password": "12345"})

    assert response.status_code == 422
    assert response.json()["detail"] == "密码长度至少为 6 位。"


def test_update_user_rejects_too_long_display_name(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "admin", "display_name": "Admin"})

    with TestClient(app_module.app) as client:
        response = client.put("/api/users/1", json={"displayName": "A" * 129})

    assert response.status_code == 422
    assert response.json()["detail"] == "显示名称长度不能超过 128 个字符。"


def test_update_user_password_stores_bcrypt_hash(monkeypatch):
    mock_startup(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "admin", "display_name": "Admin"})
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"id": 1})
    writes = []

    monkeypatch.setattr(
        app_module,
        "execute_write",
        lambda sql, params=None: (writes.append({"sql": sql, "params": params}), 1)[1],
    )

    with TestClient(app_module.app) as client:
        response = client.put("/api/users/1", json={"password": "secret123"})

    assert response.status_code == 200
    assert len(writes) == 1
    assert "UPDATE users SET password_hash" in writes[0]["sql"]
    assert writes[0]["params"][1] == 1
    assert writes[0]["params"][0].startswith("$2")
