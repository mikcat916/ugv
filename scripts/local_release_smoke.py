from __future__ import annotations

import argparse
import glob
import http.cookiejar
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def run_command(args: list[str], cwd: Path = ROOT_DIR) -> None:
    print(f"[RUN] {' '.join(args)}")
    try:
        subprocess.run(args, cwd=str(cwd), check=True)
    except FileNotFoundError as exc:
        raise SystemExit(f"[ERR] Command not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"[ERR] Command failed with exit code {exc.returncode}: {' '.join(args)}") from exc


def static_checks() -> None:
    py_files = sorted(glob.glob(str(ROOT_DIR / "backend" / "*.py")))
    if not py_files:
        raise SystemExit("[ERR] No backend Python files found.")
    run_command([sys.executable, "-m", "py_compile", *py_files])
    run_command([
        "node",
        "--check",
        "backend/static/api.js",
        "backend/static/ui.js",
        "backend/static/websocket.js",
        "backend/static/dashboard.js",
    ])
    run_command([sys.executable, "-m", "pytest", "backend/tests", "-q"])
    run_command(["git", "diff", "--check"])
    print("[ OK ] Static checks passed.")


def build_opener() -> urllib.request.OpenerDirector:
    cookie_jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def request(
    opener: urllib.request.OpenerDirector,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> tuple[int, str, dict[str, str]]:
    data = None
    headers = {"Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
            response_headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
        response_headers = dict(exc.headers.items())
    if status != expected_status:
        raise SystemExit(f"[ERR] {method} {url} returned {status}, expected {expected_status}.\n{body[:500]}")
    return status, body, response_headers


def wait_for_backend(opener: urllib.request.OpenerDirector, backend_url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            _, body, _ = request(opener, "GET", f"{backend_url}/health")
            payload = json.loads(body)
            if payload.get("status") == "ok":
                print(f"[ OK ] Backend is healthy: {backend_url}")
                return
            last_error = f"status={payload.get('status')} detail={payload.get('detail')}"
        except (OSError, urllib.error.URLError, ValueError, SystemExit) as exc:
            last_error = str(exc)
        time.sleep(1)
    raise SystemExit(f"[ERR] Backend did not become healthy within {timeout_seconds}s: {last_error}")


def login(opener: urllib.request.OpenerDirector, backend_url: str, username: str, password: str) -> None:
    _, login_html, _ = request(opener, "GET", f"{backend_url}/login")
    match = re.search(r'loginToken:\s*"([^"]+)"', login_html)
    if not match:
        raise SystemExit("[ERR] Could not find loginToken on /login page.")
    _, body, _ = request(
        opener,
        "POST",
        f"{backend_url}/auth/login",
        {"username": username, "password": password, "loginToken": match.group(1)},
    )
    payload = json.loads(body)
    if not payload.get("ok"):
        raise SystemExit(f"[ERR] Login response did not contain ok=true: {body[:500]}")
    print(f"[ OK ] Logged in as {username}.")


def assert_page(opener: urllib.request.OpenerDirector, backend_url: str, path: str, page_id: str) -> None:
    _, body, _ = request(opener, "GET", f"{backend_url}{path}")
    if f'pageId: "{page_id}"' not in body:
        raise SystemExit(f"[ERR] {path} loaded but did not contain pageId {page_id!r}.")
    print(f"[ OK ] Page loaded: {path}")


def web_checks(backend_url: str, username: str, password: str, timeout_seconds: int) -> None:
    backend_url = backend_url.rstrip("/")
    opener = build_opener()
    wait_for_backend(opener, backend_url, timeout_seconds)
    login(opener, backend_url, username, password)

    _, dashboard_body, _ = request(opener, "GET", f"{backend_url}/api/dashboard")
    dashboard = json.loads(dashboard_body)
    if "data" not in dashboard or "counts" not in dashboard["data"]:
        raise SystemExit("[ERR] /api/dashboard did not return data.counts.")
    print("[ OK ] Dashboard API loaded.")

    for path, page_id in [
        ("/overview", "overview"),
        ("/device-management", "device_management"),
        ("/users", "users"),
        ("/clusters", "clusters"),
        ("/formations", "formations"),
    ]:
        assert_page(opener, backend_url, path, page_id)
    print("[ OK ] Web smoke checks passed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Web release smoke checks.")
    parser.add_argument("--static", action="store_true", help="Run static checks and backend tests.")
    parser.add_argument("--web", action="store_true", help="Run Web checks against a running backend.")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--timeout", type=int, default=30, help="Seconds to wait for backend health.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.static and not args.web:
        raise SystemExit("Choose at least one mode: --static and/or --web")
    if args.static:
        static_checks()
    if args.web:
        web_checks(args.backend_url, args.username, args.password, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
