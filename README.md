# Project4

Project4 is a web backend and robot-device tooling project. The repository now contains the backend, device tools, deployment helpers, tests, documentation, and runtime data.

## Features

- FastAPI and Jinja2 web management pages
- Session login and administrator accounts
- MySQL schema setup, diagnostics, and local seed data
- Robot, device, sensor, map, and remote-control pages
- WebSocket dashboard updates
- IoT check-in, telemetry, and autopilot status reporting
- Device-side ROS and robot-control tools
- Deployment helpers, backend tests, tool tests, and browser tests

## Project Structure

```text
Project4/
|-- apps/backend/              Backend source, pages, static files, and SQL
|-- tools/dev/                 Local setup, database, diagnostics, and release tools
|-- tools/device/              Device reporting, LiDAR, and control tools
|-- tools/deploy/              Remote deployment helpers
|-- tools/perception/          Perception and target-following tools
|-- tests/backend/             Backend API and page tests
|-- tests/tools/               Tool tests
|-- tests/e2e/                 Browser flow tests
|-- docs/checklists/           Local verification checklists
|-- docs/guides/               Feature guides
|-- docs/planning/             Plans and task lists
|-- docs/releases/             Release notes
|-- logs/                      Local runtime logs
|-- var/                       Uploads and runtime data
|-- .env.example               Configuration example
|-- requirements.txt           Runtime dependency entry point
|-- requirements-dev.txt       Development and test dependencies
|-- start-dev.ps1              Local development launcher
|-- start.ps1 / start.bat      Backend launchers
|-- create_database.bat        Database initialization launcher
`-- test_mysql_connection.bat  MySQL connection diagnostic launcher
```

## Requirements

- Python 3.11 recommended
- MySQL 8.0 or newer
- Windows PowerShell for the local launchers

## Quick Start

```powershell
cd E:/Code/Project4
Copy-Item .env.example .env
notepad .env
python -m pip install -r requirements.txt
./start-dev.ps1
```

Open these local endpoints after startup:

- Login: http://127.0.0.1:8000/login
- Health check: http://127.0.0.1:8000/api/health
- Short health check: http://127.0.0.1:8000/health

The default local administrator is `admin / admin123`. Change it in `.env` for any shared environment.

## Configuration

The backend reads the repository root `.env`. Common settings are:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=robot_monitor
MYSQL_CHARSET=utf8mb4
SESSION_SECRET=dev-local-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_DISPLAY_NAME=Administrator
ALLOW_SELF_REGISTER=0
AMAP_WEB_KEY=your_amap_web_js_key
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

## Database

Initialize the database:

```powershell
python tools/dev/create_database.py
```

Preview the resolved settings without connecting:

```powershell
python tools/dev/create_database.py --dry-run
```

Reset local development data and seed test data:

```powershell
mysql -u root -p robot_monitor < apps/backend/db/reset-db-dev.sql
python tools/dev/create_database.py
mysql -u root -p robot_monitor < apps/backend/db/seed-dev.sql
```

## Backend Startup

Recommended:

```powershell
./start-dev.ps1
```

Manual startup:

```powershell
python -m uvicorn ugv_backend.main:app --app-dir apps/backend/src --host 127.0.0.1 --port 8000 --reload
```

## Device and Deployment Tools

| Path | Purpose |
| --- | --- |
| `tools/dev/bootstrap_iot_backend.py` | Create IoT tables and device tokens |
| `tools/dev/test_mysql_connection.py` | Diagnose MySQL connectivity |
| `tools/dev/local_release_smoke.py` | Run local release checks |
| `tools/device/iot_client.py` | Send device check-ins and telemetry |
| `tools/device/robot_control_server.py` | Run the device-side control service |
| `tools/deploy/deploy_iot_client.py` | Deploy the IoT client remotely |
| `tools/deploy/setup_pi_iot.sh` | Set up the Linux device client |

## Tests

Install development dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run backend and tool tests:

```powershell
python -m pytest tests/backend tests/tools -q
```

Run static release checks:

```powershell
python tools/dev/local_release_smoke.py --static
```

Run web checks after starting the backend:

```powershell
python tools/dev/local_release_smoke.py --web --backend-url http://127.0.0.1:8000
```

## Documentation

- Backend details: `apps/backend/README.md`
- Remote control guide: `docs/guides/remote-control.md`
- Local release checklist: `docs/checklists/local-release-checklist.md`
- Autopilot local test: `docs/checklists/autopilot-local-test.md`
- Planning files: `docs/planning/`

## Common Problems

### MySQL cannot connect

- Confirm the MySQL service is running.
- Check `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` in `.env`.
- Run `python tools/dev/create_database.py --dry-run` to verify the values being read.

### Port already in use

The default port is `8000`. Use another port temporarily:

```powershell
./start-dev.ps1 -Port 8001
```

### Dependency installation fails

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```
