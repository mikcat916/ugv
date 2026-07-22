from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime
from typing import Any, Callable

import bcrypt
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import PAGES, admin_username, mysql_configured, session_secret


LEGACY_PASSWORD_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
LOGIN_TOKEN_BYTES = 32
SESSION_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_legacy_password_hash(password_hash: Any) -> bool:
    return bool(LEGACY_PASSWORD_HASH_RE.fullmatch(str(password_hash or "").strip()))


def verify_password(password: str, password_hash: str) -> bool:
    normalized_hash = str(password_hash or "").strip()
    if is_legacy_password_hash(normalized_hash):
        return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), normalized_hash.lower())
    try:
        return bcrypt.checkpw(password.encode("utf-8"), normalized_hash.encode("utf-8"))
    except ValueError:
        return False


def get_user_by_username(
    query_one: Callable[[str, tuple[Any, ...] | None], dict[str, Any] | None],
    username: str,
) -> dict[str, Any] | None:
    return query_one(
        """
        SELECT id, username, password_hash, display_name, status, created_at
        FROM users
        WHERE username = %s
        LIMIT 1
        """,
        (username,),
    )


def validate_auth_user_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    display_name = str(payload.get("displayName", username)).strip() or username
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空。")
    if len(username) > 64:
        raise HTTPException(status_code=422, detail="用户名长度不能超过 64 个字符。")
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="密码长度至少为 6 位。")
    if len(display_name) > 128:
        raise HTTPException(status_code=422, detail="显示名称长度不能超过 128 个字符。")
    return username, password, display_name


def ensure_admin_user(
    get_user_by_username_fn: Callable[[str], dict[str, Any] | None],
    execute_write: Callable[[str, tuple[Any, ...] | None], int],
    hash_password_fn: Callable[[str], str] = hash_password,
) -> None:
    if not mysql_configured():
        return
    username = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
    password = os.getenv("ADMIN_PASSWORD", "admin123").strip() or "admin123"
    display_name = os.getenv("ADMIN_DISPLAY_NAME", "系统管理员").strip() or "系统管理员"
    if get_user_by_username_fn(username):
        return
    execute_write(
        """
        INSERT INTO users (username, password_hash, display_name, status, created_at)
        VALUES (%s, %s, %s, 'active', %s)
        """,
        (username, hash_password_fn(password), display_name, datetime.now()),
    )


def template_user(user: dict[str, Any] | None) -> dict[str, str] | None:
    if not user:
        return None
    return {
        "username": str(user.get("username", "")),
        "display_name": str(user.get("display_name", "") or user.get("username", "")),
    }


def user_session_signature(user: dict[str, Any]) -> str:
    identity = "|".join(
        [
            str(user.get("username", "")),
            str(user.get("password_hash", "")),
            str(user.get("status", "")),
        ]
    )
    return hmac.new(session_secret().encode("utf-8"), identity.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_auth_token(user: dict[str, Any]) -> str:
    return f"{secrets.token_urlsafe(SESSION_TOKEN_BYTES)}.{user_session_signature(user)}"


def verify_session_auth_token(user: dict[str, Any], token: str) -> bool:
    parts = str(token or "").split(".", 1)
    if len(parts) != 2 or not parts[0]:
        return False
    return hmac.compare_digest(parts[1], user_session_signature(user))


def issue_login_token(request: Request) -> str:
    token = secrets.token_urlsafe(LOGIN_TOKEN_BYTES)
    request.session["login_token"] = token
    return token


def verify_login_token(request: Request, payload: dict[str, Any]) -> None:
    expected = str(request.session.get("login_token") or "")
    provided = str(payload.get("loginToken") or request.headers.get("X-Login-Token") or "")
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="登录令牌无效，请刷新页面后重试。")


def establish_user_session(
    request: Request,
    user: dict[str, Any],
    create_session_auth_token_fn: Callable[[dict[str, Any]], str] = create_session_auth_token,
) -> None:
    request.session["username"] = user["username"]
    request.session["auth_token"] = create_session_auth_token_fn(user)
    request.session.pop("login_token", None)


def current_user(
    request: Request,
    mysql_ready: Callable[[], bool],
    get_user_by_username_fn: Callable[[str], dict[str, Any] | None],
    verify_session_auth_token_fn: Callable[[dict[str, Any], str], bool] = verify_session_auth_token,
) -> dict[str, Any] | None:
    username = request.session.get("username")
    if not username:
        return None
    session_token = str(request.session.get("auth_token") or "")
    if not session_token:
        return None
    if not mysql_ready():
        return {"username": username, "display_name": username}
    user = get_user_by_username_fn(username)
    if not user:
        request.session.clear()
        return None
    if str(user.get("status", "active")).strip().lower() == "disabled":
        request.session.clear()
        return None
    if not verify_session_auth_token_fn(user, session_token):
        request.session.clear()
        return None
    return user


def is_admin_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return str(user.get("username", "")).strip() == admin_username()


def visible_pages_for_user(user: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    if is_admin_user(user):
        return dict(PAGES)
    admin_only_pages = {"control", "autopilot", "users", "clusters", "formations"}
    return {key: value for key, value in PAGES.items() if key not in admin_only_pages}


def forbidden_page(detail: str = "仅管理员可访问当前页面。") -> HTMLResponse:
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>403 | 机器人巡检平台</title>
</head>
<body>
  <main style="max-width:640px;margin:64px auto;padding:0 24px;font-family:'Noto Sans SC','Segoe UI',sans-serif;">
    <h1 style="font-size:32px;margin-bottom:12px;">403</h1>
    <p style="font-size:16px;line-height:1.7;">{detail}</p>
  </main>
</body>
</html>""",
        status_code=403,
    )


def require_page_login(request: Request, current_user_fn: Callable[[Request], dict[str, Any] | None]):
    user = current_user_fn(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return user


def require_api_login(request: Request, current_user_fn: Callable[[Request], dict[str, Any] | None]) -> dict[str, Any]:
    user = current_user_fn(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录。")
    return user
