# Logging Guidelines

> Current logging and diagnostic behavior in the repository.

## Current Pattern

The backend currently relies mainly on Uvicorn/FastAPI output and explicit
diagnostic responses. Device and deployment tools print short progress or
failure messages and write diagnostic files under `logs/` when the tool
supports it. There is no project-wide structured logging wrapper yet.

## Rules for New Code

- Prefer the standard `logging` module for long-running backend or device
  services. Use a module logger rather than `print()` in request or service
  code.
- Keep messages short and include the operation, robot/device identifier when
  useful, and the failure reason.
- Never log passwords, session tokens, MySQL passwords, or full request bodies
  that may contain credentials.
- Do not put runtime logs in the source directories. Use `logs/` for local
  files, which is ignored by Git.
- API responses should contain a safe short detail; troubleshooting context
  belongs in server/tool logs.

## Diagnostic Output

- `tools/dev/local_release_smoke.py` prints named checks and their result.
- `tools/dev/test_mysql_connection.py` writes MySQL diagnostics under `logs/`.
- `tools/device/iot_client.py` includes diagnostic information in telemetry
  fields such as GPS attempts, but should not include secrets.

## Levels

- `DEBUG`: local troubleshooting details, such as selected device probes.
- `INFO`: successful startup, check-in, migration, or major state changes.
- `WARNING`: recoverable missing data, fallback behavior, or stale device data.
- `ERROR`: failed database, network, or device operations that need attention.

## Examples

- Runtime diagnostics: `logs/backend-8000.log`
- MySQL diagnostic tool: `tools/dev/test_mysql_connection.py`
- Release check output: `tools/dev/local_release_smoke.py`
