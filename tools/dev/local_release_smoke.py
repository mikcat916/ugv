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


ROOT_DIR = Path(__file__).resolve().parents[2]
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
    py_files = sorted(glob.glob(str(ROOT_DIR / "apps" / "backend" / "src" / "ugv_backend" / "*.py")))
    py_files.append(str(ROOT_DIR / "tools" / "device" / "control_gateway.py"))
    if not py_files:
        raise SystemExit("[ERR] No backend Python files found.")
    js_files = [
        "apps/backend/static/api.js",
        "apps/backend/static/ui.js",
        "apps/backend/static/websocket.js",
        "apps/backend/static/sim_autopilot.js",
        "apps/backend/static/sim_safety.js",
        "apps/backend/static/simulator.js",
        "apps/backend/static/dashboard.js",
    ]
    js_files = [item for item in js_files if (ROOT_DIR / item).exists()]
    run_command([sys.executable, "-m", "py_compile", *py_files])
    run_command(["node", "--check", *js_files])
    run_command([sys.executable, "-m", "pytest", "tests/backend", "-q"])
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


def autopilot_smoke(opener: urllib.request.OpenerDirector, backend_url: str) -> None:
    _, body, _ = request(opener, "GET", f"{backend_url}/api/autopilot/status")
    status = json.loads(body)
    for key in ("mode", "safe", "reason", "lidar", "manualOverride", "estop"):
        if key not in status:
            raise SystemExit(f"[ERR] /api/autopilot/status did not contain {key!r}.")

    request(opener, "POST", f"{backend_url}/api/autopilot/clear-estop", {})
    _, body, _ = request(opener, "POST", f"{backend_url}/api/autopilot/start", {})
    started = json.loads(body)
    if started.get("mode") not in {"auto_ready", "auto_running"}:
        raise SystemExit(f"[ERR] /api/autopilot/start returned unexpected mode: {started.get('mode')!r}")
    request(opener, "POST", f"{backend_url}/api/autopilot/deadman", {"source": "smoke"})
    request(opener, "POST", f"{backend_url}/api/autopilot/pause", {})
    request(opener, "POST", f"{backend_url}/api/autopilot/resume", {})
    request(opener, "POST", f"{backend_url}/api/autopilot/stop", {})
    request(opener, "POST", f"{backend_url}/api/autopilot/estop", {})
    request(opener, "POST", f"{backend_url}/api/autopilot/clear-estop", {})
    _, debug_body, _ = request(opener, "GET", f"{backend_url}/api/autopilot/debug-log")
    debug_payload = json.loads(debug_body)
    if "status" not in debug_payload or "cmdVelLog" not in debug_payload:
        raise SystemExit("[ERR] /api/autopilot/debug-log did not contain status/cmdVelLog.")
    print("[ OK ] Autopilot API smoke checks passed.")


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
        ("/autopilot", "autopilot"),
        ("/device-management", "device_management"),
        ("/users", "users"),
        ("/clusters", "clusters"),
        ("/formations", "formations"),
    ]:
        assert_page(opener, backend_url, path, page_id)
    autopilot_smoke(opener, backend_url)
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
