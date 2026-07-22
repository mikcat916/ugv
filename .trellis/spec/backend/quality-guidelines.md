# Quality Guidelines

> Practical quality rules based on the current Project4 codebase.

## Required Checks

Before considering a backend change complete, run:

```powershell
python -m pytest tests/backend tests/tools -q
python tools/dev/local_release_smoke.py --static
git diff --check
```

For changes to browser behavior, also run the Playwright tests from
`tests/e2e/` after the backend is running.

## Testing Style

- Use `pytest` for Python tests and `TestClient` for FastAPI routes.
- Keep tests focused on one behavior and use clear `test_` names.
- Use `monkeypatch` to replace database, authentication, device, or startup
  boundaries instead of requiring real hardware in unit tests.
- Test both successful behavior and important rejection paths, especially for
  login, permissions, robot control, autopilot, and database setup.
- Tool tests may load a device module directly with `importlib` when the tool is
  not installed as a package.

Examples:

- API behavior and mocked startup: `tests/backend/test_schema_migration.py`
- Authentication and page behavior: `tests/backend/test_auth_ui.py`
- Device parsing without hardware: `tests/tools/test_iot_client.py`

## Code Review Checklist

- Does the change use the canonical path under `apps/backend/`, `tools/`, or
  `tests/` rather than an old root directory?
- Are request values validated and SQL values parameterized?
- Are permissions checked before changing users, robots, or control state?
- Are device failures converted to understandable status codes?
- Are database writes tested for both success and failure?
- Are secrets absent from source, logs, tests, and responses?
- Are existing tests still passing, including static path checks?
- Are docs and `.env.example` updated when a setting or command changes?

## Forbidden Patterns

- Do not commit `.env`, passwords, tokens, private keys, runtime logs, or user
  uploads.
- Do not use raw SQL string interpolation for external values.
- Do not bypass shared authentication or database helpers for convenience.
- Do not send real robot movement commands from unit tests.
- Do not add a second legacy backend or desktop application tree.
