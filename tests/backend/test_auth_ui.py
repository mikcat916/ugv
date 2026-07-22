import hashlib
import re

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
    monkeypatch.setattr(app_module, "ensure_robot_device_column", lambda: None)
    monkeypatch.setattr(app_module, "ensure_management_system_tables", lambda: None)
    monkeypatch.setattr(app_module, "ensure_admin_user", lambda: None)
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: fake_user())
    monkeypatch.setattr(app_module, "verify_password", lambda password, password_hash: True)


def test_login_page_available_without_mysql():
    with TestClient(app_module.app) as client:
        response = client.get("/login")
    assert response.status_code == 200
    assert "机器人巡检平台" in response.text
    assert "注册并进入" not in response.text


def test_login_page_disables_registration_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_SELF_REGISTER", raising=False)
    with TestClient(app_module.app) as client:
        response = client.get("/login")
    assert response.status_code == 200
    assert "allowSelfRegister: false" in response.text


def test_page_requires_login_redirect():
    with TestClient(app_module.app) as client:
        response = client.get("/overview", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_login_success_and_page_access(monkeypatch):
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/overview")

    assert response.status_code == 200
    assert "退出登录" in response.text


def test_login_requires_page_token(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)

    with TestClient(app_module.app) as client:
        response = client.post("/auth/login", json={"username": "admin", "password": "admin123"})

    assert response.status_code == 403
    assert "登录令牌无效" in response.json()["detail"]


def test_login_rejects_wrong_password(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    monkeypatch.setattr(app_module, "verify_password", lambda password, password_hash: False)

    with TestClient(app_module.app) as client:
        response = client.post("/auth/login", json={"username": "admin", "password": "wrong-pass", "loginToken": login_token(client)})

    assert response.status_code == 401
    assert "用户名或密码错误" in response.json()["detail"]


def test_session_token_signature_changes_with_user_state(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    user = fake_user()
    token = app_module.create_session_auth_token(user)

    assert app_module.verify_session_auth_token(user, token) is True

    user["status"] = "disabled"
    assert app_module.verify_session_auth_token(user, token) is False


def test_session_token_invalidates_disabled_user(monkeypatch):
    mock_auth(monkeypatch)
    user = fake_user()

    def fake_get_user(username):
        return user

    monkeypatch.setattr(app_module, "get_user_by_username", fake_get_user)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)

    with TestClient(app_module.app) as client:
        login(client)
        user["status"] = "disabled"
        response = client.get("/api/dashboard")

    assert response.status_code == 401


def test_video_page_includes_novnc_bootstrap_config(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setenv("ROBOT_CAMERA_LABEL", "Front camera")
    monkeypatch.setenv("ROBOT_CAMERA_STATUS", "ready")
    monkeypatch.setenv("ROBOT_CAMERA_STATUS_TEXT", "stream ready")
    monkeypatch.setenv("ROBOT_CAMERA_MJPEG_URL", "https://192.168.31.198:8080/stream.mjpg")
    monkeypatch.setenv("ROBOT_CAMERA_STATUS_REASON", "camera connected")
    monkeypatch.setenv("ROBOT_VNC_HOST", "192.168.31.198")
    monkeypatch.setenv("ROBOT_VNC_PORT", "5900")
    monkeypatch.setenv("NOVNC_PROXY_HOST", "192.168.31.169")
    monkeypatch.setenv("NOVNC_PROXY_PORT", "6080")
    monkeypatch.setenv("NOVNC_VIEW_ONLY", "1")
    monkeypatch.setenv("NOVNC_PASSWORD", "123456")

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/video")

    assert response.status_code == 200
    assert 'pageId: "video"' in response.text
    assert '"label": "Front camera"' in response.text
    assert '"mjpegUrl": "https://192.168.31.198:8080/stream.mjpg"' in response.text
    assert '"statusText": "stream ready"' in response.text
    assert '"reason": "camera connected"' in response.text
    assert 'video: {"camera":' in response.text
    assert '"targetHost": "192.168.31.198"' in response.text
    assert '"proxyHost": "192.168.31.169"' in response.text
    assert '"proxyPort": 6080' in response.text
    assert '"password": "123456"' in response.text


def test_camera_snapshot_requires_login(monkeypatch):
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        response = client.get("/api/robots/4/camera/snapshot")

    assert response.status_code == 401


def test_camera_snapshot_unknown_robot_returns_404(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "query_one", lambda sql, params=None: None)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/999/camera/snapshot")

    assert response.status_code == 404


def test_camera_snapshot_proxies_registered_robot(monkeypatch):
    mock_auth(monkeypatch)
    captured = {}

    def fake_query_one(sql, params=None):
        if "FROM robots" in sql:
            return {"id": 4, "model": "巡检机器人-02", "ip_address": "192.168.31.198"}
        return None

    async def fake_snapshot(ip_address):
        captured["ip"] = ip_address
        return b"jpeg-bytes", "image/jpeg"

    monkeypatch.setattr(app_module, "query_one", fake_query_one)
    monkeypatch.setattr(app_module, "fetch_robot_camera_snapshot", fake_snapshot)
    monkeypatch.setattr(app_module, "_fallback_iot_snapshot", lambda robot_id, ip_address: None)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/4/camera/snapshot")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content == b"jpeg-bytes"
    assert captured["ip"] == "192.168.31.198"


def test_camera_snapshot_upstream_failure_returns_502(monkeypatch):
    mock_auth(monkeypatch)

    def fake_query_one(sql, params=None):
        if "FROM robots" in sql:
            return {"id": 4, "model": "巡检机器人-02", "ip_address": "192.168.31.198"}
        return None

    async def fake_snapshot(ip_address):
        raise HTTPException(status_code=502, detail="摄像头快照不可达。")

    monkeypatch.setattr(app_module, "query_one", fake_query_one)
    monkeypatch.setattr(app_module, "fetch_robot_camera_snapshot", fake_snapshot)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/api/robots/4/camera/snapshot")

    assert response.status_code == 502
    assert "没有新鲜" in response.json()["detail"]


def test_non_admin_cannot_open_users_page(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.get("/users")

    assert response.status_code == 403
    assert "仅管理员可访问当前管理页面" in response.text


def test_non_admin_navigation_hides_users_page(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "current_user", lambda request: {"username": "operator", "display_name": "Operator"})

    with TestClient(app_module.app) as client:
        response = client.get("/overview")

    assert response.status_code == 200
    assert "用户管理" not in response.text


def test_admin_management_nav_pages_load(monkeypatch):
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        for path, page_id in [
            ("/users", "users"),
            ("/clusters", "clusters"),
            ("/formations", "formations"),
        ]:
            response = client.get(path)
            assert response.status_code == 200
            assert f'pageId: "{page_id}"' in response.text


def test_simulator_page_loads_for_authenticated_user(monkeypatch):
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        response = client.get("/simulator")

    assert response.status_code == 200
    assert 'pageId: "simulator"' in response.text
    assert "仿真" in response.text


def test_api_requires_login():
    with TestClient(app_module.app) as client:
        response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_authenticated_dashboard_and_logout(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(
        app_module,
        "build_dashboard_payload",
        lambda: {
            "site": app_module.DEFAULT_SITE,
            "counts": {"robots": 1, "tasks": 2, "alerts": 3, "reports": 4},
            "robots": [],
            "tasks": [],
            "alerts": [],
            "reports": [],
            "maintenance": [],
            "generatedAt": "2026-03-10T12:00",
        },
    )

    with TestClient(app_module.app) as client:
        login(client)
        dashboard_response = client.get("/api/dashboard")
        logout_response = client.post("/auth/logout")
        after_logout = client.get("/api/dashboard")

    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["data"]["counts"]["robots"] == 1
    assert logout_response.status_code == 200
    assert after_logout.status_code == 401


def test_register_rejected_when_disabled(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    monkeypatch.setenv("ALLOW_SELF_REGISTER", "0")

    with TestClient(app_module.app) as client:
        response = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "secret123", "displayName": "New User"},
        )

    assert response.status_code == 403


def test_register_success_and_dashboard_access(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    monkeypatch.setattr(app_module, "hash_password", lambda password: f"hashed:{password}")
    monkeypatch.setenv("ALLOW_SELF_REGISTER", "1")

    users = {}

    def fake_get_user(username):
        return users.get(username)

    def fake_execute_write(sql, params=None):
        username, password_hash, display_name, created_at = params
        users[username] = {
            "id": len(users) + 1,
            "username": username,
            "password_hash": password_hash,
            "display_name": display_name,
            "status": "active",
            "created_at": created_at,
        }
        return 1

    monkeypatch.setattr(app_module, "get_user_by_username", fake_get_user)
    monkeypatch.setattr(app_module, "execute_write", fake_execute_write)
    monkeypatch.setattr(
        app_module,
        "build_dashboard_payload",
        lambda: {
            "site": app_module.DEFAULT_SITE,
            "counts": {"robots": 0, "tasks": 0, "alerts": 0, "reports": 0},
            "robots": [],
            "tasks": [],
            "alerts": [],
            "reports": [],
            "maintenance": [],
            "generatedAt": "2026-03-10T12:00",
        },
    )

    with TestClient(app_module.app) as client:
        token = login_token(client)
        response = client.post(
            "/auth/register",
            json={"username": "newuser", "password": "secret123", "displayName": "New User", "loginToken": token},
        )
        dashboard_response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "newuser"
    assert dashboard_response.status_code == 200


def test_login_migrates_legacy_sha256_hash(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)

    legacy_hash = hashlib.sha256("admin123".encode("utf-8")).hexdigest()
    user = {
        "id": 1,
        "username": "admin",
        "password_hash": legacy_hash,
        "display_name": "Admin User",
        "status": "active",
        "created_at": "2026-03-10T12:00",
    }
    writes = []

    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: user)
    monkeypatch.setattr(
        app_module,
        "execute_write",
        lambda sql, params=None: (writes.append({"sql": sql, "params": params}), 1)[1],
    )

    with TestClient(app_module.app) as client:
        response = client.post("/auth/login", json={"username": "admin", "password": "admin123", "loginToken": login_token(client)})

    assert response.status_code == 200
    assert len(writes) == 1
    assert "UPDATE users SET password_hash" in writes[0]["sql"]
    assert writes[0]["params"][1] == 1
    assert writes[0]["params"][0].startswith("$2")


def test_login_with_bcrypt_hash_does_not_rehash(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)

    user = {
        "id": 1,
        "username": "admin",
        "password_hash": app_module.hash_password("admin123"),
        "display_name": "Admin User",
        "status": "active",
        "created_at": "2026-03-10T12:00",
    }
    writes = []

    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: user)
    monkeypatch.setattr(
        app_module,
        "execute_write",
        lambda sql, params=None: (writes.append({"sql": sql, "params": params}), 1)[1],
    )

    with TestClient(app_module.app) as client:
        response = client.post("/auth/login", json={"username": "admin", "password": "admin123", "loginToken": login_token(client)})

    assert response.status_code == 200
    assert writes == []


def test_ensure_admin_user_stores_bcrypt_hash(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: None)
    captured = {}

    def fake_execute_write(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return 1

    monkeypatch.setattr(app_module, "execute_write", fake_execute_write)

    app_module.ensure_admin_user()

    assert "INSERT INTO users" in captured["sql"]
    assert captured["params"][1].startswith("$2")


def test_register_rejects_duplicate_username(monkeypatch):
    mock_auth(monkeypatch)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    monkeypatch.setenv("ALLOW_SELF_REGISTER", "1")
    monkeypatch.setattr(app_module, "get_user_by_username", lambda username: fake_user())

    with TestClient(app_module.app) as client:
        token = login_token(client)
        response = client.post(
            "/auth/register",
            json={"username": "admin", "password": "secret123", "displayName": "Admin User", "loginToken": token},
        )

    assert response.status_code == 409


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(app_module, "mysql_configured", lambda: True)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: True)
    app_module.APP_STATE["db_error"] = ""
    with TestClient(app_module.app) as client:
        response = client.get("/api/health")
        short_response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mysqlConfigured"] is True
    assert payload["mysqlReady"] is True
    assert short_response.status_code == 200
    assert short_response.json()["status"] == "ok"


def test_debug_config_requires_debug_mode(monkeypatch):
    monkeypatch.setenv("DEBUG", "0")
    monkeypatch.setattr(app_module, "mysql_configured", lambda: False)

    with TestClient(app_module.app) as client:
        response = client.get("/debug/config")

    assert response.status_code == 404


def test_debug_config_redacts_sensitive_values(monkeypatch):
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("MYSQL_PASSWORD", "super-secret-db-password")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-session")
    monkeypatch.setattr(app_module, "mysql_configured", lambda: False)
    monkeypatch.setattr(app_module, "mysql_ready", lambda: False)

    with TestClient(app_module.app) as client:
        response = client.get("/debug/config")

    assert response.status_code == 200
    body = response.text
    payload = response.json()
    assert payload["debug"] is True
    assert payload["mysql"]["passwordConfigured"] is True
    assert payload["auth"]["sessionSecretConfigured"] is True
    assert "super-secret-db-password" not in body
    assert "super-secret-session" not in body


def test_websocket_dashboard_connected(monkeypatch):
    mock_auth(monkeypatch)

    with TestClient(app_module.app) as client:
        login(client)
        with client.websocket_connect("/ws/dashboard") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "dashboard_update"
            assert message["event"] == "connected"
