import re

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ugv_backend import app_core as app_module


def fake_user():
    return {
        "id": 1,
        "username": "admin",
        "password_hash": "hash",
        "display_name": "Admin User",
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
    monkeypatch.setattr(app_module, "ensure_robot_ip_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_robot_device_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: fake_user())
    monkeypatch.setattr(app_module, "verify_password", lambda password, password_hash: True)


def test_duplicate_device_category_name_returns_409(monkeypatch):
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"id": 1})

    with pytest.raises(HTTPException) as exc_info:
        app_module.ensure_unique_table_name("device_categories", " Camera ", "设备类别")

    assert exc_info.value.status_code == 409
    assert "设备类别" in exc_info.value.detail


def test_related_records_block_delete(monkeypatch):
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"cnt": 2})

    with pytest.raises(HTTPException) as exc_info:
        app_module.ensure_no_related_records("devices", "category_id = %s", (3,), "该设备类别下还有设备，不能删除。")

    assert exc_info.value.status_code == 409
    assert "不能删除" in exc_info.value.detail


def test_onboard_unit_keyword_search_joins_devices(monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, "normalize_pagination", lambda page, size: (page, size, 0))
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: calls.append((sql, params)) or {"cnt": 0})
    monkeypatch.setattr(app_module, "query_all", lambda sql, params=None: calls.append((sql, params)) or [])

    payload = app_module.load_onboard_units_page(page=1, size=10, keyword="gps")

    assert payload["total"] == 0
    assert "JOIN devices d" in calls[0][0]
    assert "d.name LIKE" in calls[0][0]
    assert calls[0][1] == ("%gps%", "%gps%", "%gps%", "%gps%", "%gps%", "%gps%")


def test_cluster_node_duplicate_returns_409(monkeypatch):
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: {"id": 5})

    with pytest.raises(HTTPException) as exc_info:
        app_module.ensure_unique_cluster_node(1, 2)

    assert exc_info.value.status_code == 409
    assert "已接入当前集群" in exc_info.value.detail


def test_build_formation_member_record_rejects_robot_outside_cluster(monkeypatch):
    def fake_query_one(sql, params=None):
        if "FROM formations" in sql:
            return {"cluster_id": 7}
        if "FROM robots" in sql:
            return {"id": 2}
        if "FROM cluster_nodes" in sql:
            return None
        return None

    monkeypatch.setattr(app_module, "query_one", fake_query_one)

    with pytest.raises(HTTPException) as exc_info:
        app_module.build_formation_member_record({"formationId": 1, "robotId": 2})

    assert exc_info.value.status_code == 409
    assert "编队所属集群" in exc_info.value.detail


def test_update_device_category_allows_noop_write(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "execute_write", lambda sql, params=None: 0)

    def fake_query_one(sql, params=None):
        if "LOWER(TRIM(name))" in sql:
            return None
        if "SELECT id FROM device_categories WHERE id =" in sql:
            return {"id": 1}
        return None

    monkeypatch.setattr(app_module, "query_one", fake_query_one)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.put("/api/device-categories/1", json={"name": "Camera", "description": "", "status": "active"})

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_delete_cluster_node_rejects_when_used_by_formation(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "clear_table", lambda *args, **kwargs: pytest.fail("should not delete bound cluster node"))

    def fake_query_one(sql, params=None):
        if "FROM cluster_nodes WHERE id =" in sql:
            return {"cluster_id": 1, "robot_id": 2}
        if "FROM formation_members fm" in sql:
            return {"id": 9}
        return None

    monkeypatch.setattr(app_module, "query_one", fake_query_one)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.delete("/api/cluster-nodes/10")

    assert response.status_code == 409
    assert "编队成员引用" in response.json()["detail"]


def test_update_cluster_node_rejects_migration_when_used_by_formation(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "execute_write", lambda *args, **kwargs: pytest.fail("should not update bound cluster node"))

    def fake_query_one(sql, params=None):
        if "FROM cluster_nodes WHERE id =" in sql:
            return {"cluster_id": 1, "robot_id": 2}
        if "SELECT id FROM clusters" in sql:
            return {"id": 3}
        if "SELECT id FROM robots" in sql:
            return {"id": 4}
        if "FROM cluster_nodes WHERE cluster_id =" in sql and "robot_id =" in sql:
            return None
        if "FROM formation_members fm" in sql:
            return {"id": 9}
        return None

    monkeypatch.setattr(app_module, "query_one", fake_query_one)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.put(
            "/api/cluster-nodes/10",
            json={"clusterId": 3, "robotId": 4, "role": "member", "status": "standby"},
        )

    assert response.status_code == 409
    assert "不能迁移" in response.json()["detail"]


def test_update_formation_rejects_cluster_change_when_members_not_joined(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "execute_write", lambda *args, **kwargs: pytest.fail("should not update invalid formation"))

    def fake_query_one(sql, params=None):
        if "SELECT id FROM clusters" in sql:
            return {"id": 6}
        if "SELECT id FROM formations WHERE id =" in sql:
            return {"id": 1}
        if "FROM formations WHERE cluster_id =" in sql:
            return None
        if "LEFT JOIN cluster_nodes cn" in sql:
            return {"robot_id": 2}
        return None

    monkeypatch.setattr(app_module, "query_one", fake_query_one)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.put(
            "/api/formations/1",
            json={"clusterId": 6, "name": "楔形编队", "formationType": "wedge", "status": "draft", "description": ""},
        )

    assert response.status_code == 409
    assert "目标集群" in response.json()["detail"]


def test_formation_members_requires_existing_formation(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: None)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/formation-members?formationId=99")

    assert response.status_code == 404
    assert response.json()["detail"] == "未找到对应编队。"


def test_update_formation_member_endpoint_supports_noop_write(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "execute_write", lambda sql, params=None: 0)

    def fake_query_one(sql, params=None):
        if "SELECT cluster_id FROM formations" in sql:
            return {"cluster_id": 1}
        if "SELECT id FROM robots" in sql:
            return {"id": 2}
        if "FROM cluster_nodes WHERE cluster_id =" in sql and "robot_id =" in sql:
            return {"id": 4}
        if "FROM formation_members WHERE formation_id =" in sql:
            return None
        if "SELECT id FROM formation_members WHERE id =" in sql:
            return {"id": 8}
        return None

    monkeypatch.setattr(app_module, "query_one", fake_query_one)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.put(
            "/api/formation-members/8",
            json={"formationId": 1, "robotId": 2, "slotIndex": 1, "role": "member", "offsetX": 0, "offsetY": 0, "offsetYaw": 0},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_apply_control_success_side_effect_clears_joined_at_on_exit(monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, "execute_write", lambda sql, params=None: calls.append((sql, params)) or 1)

    app_module.apply_control_success_side_effect({"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"})

    assert calls == [("UPDATE cluster_nodes SET status = 'disconnected', joined_at = NULL WHERE id = %s", (7,))]
