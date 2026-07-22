# Directory Structure

> Actual layout and placement rules for the Project4 backend.

## Overview

The repository is a single Python project. The web backend is the only
application source tree. It is a FastAPI application that serves both JSON
APIs and Jinja2 HTML pages.

## Directory Layout

```text
apps/backend/
├── src/ugv_backend/       Python application package
│   ├── main.py             Small ASGI entrypoint
│   ├── app_core.py         App creation, route handlers, startup hooks
│   ├── auth.py             Passwords, sessions, permissions
│   ├── config.py           Environment values and repository paths
│   ├── db.py               MySQL connection and query helpers
│   ├── iot.py              IoT check-in and telemetry helpers
│   ├── autopilot.py        Autopilot state and safety logic
│   └── robot_control.py    Robot control gateway client
├── templates/              Jinja2 HTML pages
├── static/                 Browser JavaScript and CSS
└── db/                     Schema and development SQL scripts
tools/
├── dev/                    Local setup, diagnostics, smoke checks
├── device/                 Robot-side services and device clients
├── deploy/                 Remote deployment helpers
└── perception/             Perception and target-following tools
tests/
├── backend/                FastAPI and database behavior tests
├── tools/                  Device/tool unit tests
└── e2e/                    Playwright browser tests
```

## Module Organization

- Add web routes and route-specific orchestration to `app_core.py` until a
  future split is intentionally designed. Do not create a second backend
  package or a root-level `backend/` compatibility tree.
- Put reusable authentication behavior in `auth.py`, database access in
  `db.py`, autopilot state transitions in `autopilot.py`, and robot gateway
  communication in `robot_control.py`.
- Keep environment parsing and repository paths in `config.py`.
- Put new pages in `apps/backend/templates/` and browser assets in
  `apps/backend/static/`.
- Put local-only setup code in `tools/dev/`; do not import development tools
  into the web application.

## Naming Conventions

- Python files and functions use `snake_case`.
- Constants use `UPPER_SNAKE_CASE`.
- API paths use lowercase words with hyphens where needed, for example
  `/api/robot-control/status`.
- Keep database helper names explicit: `query_all`, `query_one`,
  `execute_write`, and `execute_insert`.

## Examples

- ASGI entrypoint: `apps/backend/src/ugv_backend/main.py`
- Shared configuration: `apps/backend/src/ugv_backend/config.py`
- Database boundary: `apps/backend/src/ugv_backend/db.py`
- Page and API registration: `apps/backend/src/ugv_backend/app_core.py`
- Device tool: `tools/device/iot_client.py`
