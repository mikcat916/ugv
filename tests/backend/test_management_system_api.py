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


def mock_control_gateway_dependencies(monkeypatch, *, gateway_url="http://gateway.test", token="test-token"):
    mock_auth(monkeypatch)
    command_updates = []
    node_updates = []

    def fake_update_control_command(command_id, status, response=None, error="", completed=True):
        command_updates.append({"command_id": command_id, "status": status, "response": response, "error": error})
        return 1

    def fake_execute_write(sql, params=None):
        if "UPDATE cluster_nodes SET status = 'disconnected'" in sql:
            node_updates.append((sql, params))
        return 1

    monkeypatch.setattr(app_module, "insert_control_command", lambda record: 101)
    monkeypatch.setattr(app_module, "update_control_command", fake_update_control_command)
    monkeypatch.setattr(app_module, "execute_write", fake_execute_write)
    monkeypatch.setattr(
        app_module,
        "query_one",
        lambda sql, params=None: {"id": 7, "cluster_id": 3, "robot_id": 9, "ip_address": "192.0.2.10"},
    )
    monkeypatch.setattr(app_module, "robot_control_port", lambda: 9000)
    monkeypatch.setattr(app_module, "control_gateway_url", lambda: gateway_url)
    monkeypatch.setattr(app_module, "control_gateway_token", lambda: token)
    monkeypatch.setattr(app_module, "control_gateway_timeout_seconds", lambda: 5.0)
    return command_updates, node_updates


def mock_gateway_http(monkeypatch, *, response=None, error=None):
    calls = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, **kwargs):
            calls.append({"url": url, **kwargs, "client": self.kwargs})
            if error is not None:
                raise error
            return response

    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeAsyncClient)
    return calls


def forbid_gateway_http(monkeypatch):
    class ForbiddenAsyncClient:
        def __init__(self, **kwargs):
            pytest.fail("gateway HTTP client must not be created")

    monkeypatch.setattr(app_module.httpx, "AsyncClient", ForbiddenAsyncClient)


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


def test_create_control_command_executes_node_exit_and_updates_node_after_gateway_confirmation(monkeypatch):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    gateway_response = {
        "ok": True,
        "executed": True,
        "mode": "live",
        "commandId": 101,
        "message": "node stopped",
    }
    calls = mock_gateway_http(monkeypatch, response=app_module.httpx.Response(200, json=gateway_response))

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "commandId": 101, "response": gateway_response}
    assert command_updates == [
        {"command_id": 101, "status": "success", "response": gateway_response, "error": ""}
    ]
    assert node_updates == [
        ("UPDATE cluster_nodes SET status = 'disconnected', joined_at = NULL WHERE id = %s", (7,))
    ]
    assert calls[0]["url"] == "http://gateway.test/v1/commands"
    assert calls[0]["headers"] == {"Authorization": "Bearer test-token"}
    assert calls[0]["json"] == {
        "commandId": 101,
        "targetType": "cluster_node",
        "targetId": 7,
        "commandType": "node_exit",
        "params": {},
        "target": {"clusterNodeId": 7, "clusterId": 3, "robotId": 9, "host": "192.0.2.10", "port": 9000},
    }


def test_create_control_command_dry_run_does_not_update_node(monkeypatch):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    gateway_response = {
        "ok": True,
        "executed": False,
        "mode": "dry_run",
        "commandId": 101,
        "message": "simulated",
    }
    mock_gateway_http(monkeypatch, response=app_module.httpx.Response(200, json=gateway_response))

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"},
        )

    assert response.status_code == 200
    assert response.json()["simulated"] is True
    assert command_updates == [
        {"command_id": 101, "status": "simulated", "response": gateway_response, "error": ""}
    ]
    assert node_updates == []


def test_create_control_command_gateway_rejection_marks_failed_without_updating_node(monkeypatch):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    mock_gateway_http(
        monkeypatch,
        response=app_module.httpx.Response(409, json={"ok": False, "executed": False, "detail": "stop rejected"}),
    )

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"},
        )

    assert response.status_code == 502
    assert "stop rejected" in response.json()["detail"]
    assert command_updates == [
        {"command_id": 101, "status": "failed", "response": None, "error": "控制网关拒绝命令：stop rejected"}
    ]
    assert node_updates == []


def test_create_control_command_gateway_timeout_marks_failed_without_updating_node(monkeypatch):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    mock_gateway_http(monkeypatch, error=app_module.httpx.ReadTimeout("gateway timeout"))

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"},
        )

    assert response.status_code == 504
    assert response.json()["detail"] == "控制网关响应超时。"
    assert command_updates == [
        {"command_id": 101, "status": "failed", "response": None, "error": "控制网关响应超时。"}
    ]
    assert node_updates == []


def test_create_control_command_invalid_gateway_json_marks_failed_without_updating_node(monkeypatch):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    mock_gateway_http(monkeypatch, response=app_module.httpx.Response(200, content=b"not-json"))

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "控制网关返回了无效 JSON。"
    assert command_updates == [
        {"command_id": 101, "status": "failed", "response": None, "error": "控制网关返回了无效 JSON。"}
    ]
    assert node_updates == []


@pytest.mark.parametrize(
    ("gateway_url", "token", "expected_status", "expected_detail"),
    [
        ("", "test-token", 502, "真实控制网关未配置，无法下发该控制命令。"),
        ("http://gateway.test", "", 500, "控制网关 Token 未配置。"),
    ],
)
def test_create_control_command_rejects_missing_gateway_configuration(
    monkeypatch, gateway_url, token, expected_status, expected_detail
):
    command_updates, node_updates = mock_control_gateway_dependencies(
        monkeypatch, gateway_url=gateway_url, token=token
    )
    forbid_gateway_http(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"},
        )

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail
    assert command_updates == [
        {"command_id": 101, "status": "failed", "response": None, "error": expected_detail}
    ]
    assert node_updates == []


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        (
            {"targetType": "device", "targetId": 7, "commandType": "node_exit"},
            "第一版控制网关仅支持集群节点。",
        ),
        (
            {"targetType": "cluster_node", "targetId": 7, "commandType": "restart"},
            "控制网关仅支持连通性检测和节点退出命令。",
        ),
    ],
)
def test_create_control_command_rejects_unsupported_gateway_target_or_command(monkeypatch, payload, expected_detail):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    forbid_gateway_http(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post("/api/control/commands", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail
    assert command_updates == [
        {"command_id": 101, "status": "failed", "response": None, "error": expected_detail}
    ]
    assert node_updates == []


@pytest.mark.parametrize(
    ("gateway_response", "expected_detail"),
    [
        (
            {"ok": True, "executed": True, "mode": "live"},
            "控制网关返回了不匹配的命令编号。",
        ),
        (
            {"ok": True, "executed": True, "mode": "dry_run", "commandId": 101},
            "控制网关真实执行结果缺少 live 模式标记。",
        ),
        (
            {"ok": True, "executed": False, "mode": "live", "commandId": 101},
            "控制网关模拟结果缺少 dry_run 模式标记。",
        ),
    ],
)
def test_create_control_command_rejects_inconsistent_gateway_success_response(
    monkeypatch, gateway_response, expected_detail
):
    command_updates, node_updates = mock_control_gateway_dependencies(monkeypatch)
    mock_gateway_http(monkeypatch, response=app_module.httpx.Response(200, json=gateway_response))

    with TestClient(app_module.app) as client:
        login(client)
        response = client.post(
            "/api/control/commands",
            json={"targetType": "cluster_node", "targetId": 7, "commandType": "node_exit"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == expected_detail
    assert command_updates == [
        {"command_id": 101, "status": "failed", "response": None, "error": expected_detail}
    ]
    assert node_updates == []
