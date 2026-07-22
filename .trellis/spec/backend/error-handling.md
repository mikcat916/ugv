# Error Handling

> Current error behavior for API, database, authentication, and device paths.

## General Rules

- Use FastAPI `HTTPException` for expected API failures. Include the correct
  HTTP status and a short user-facing `detail` message.
- Validate request data before database or device work. Authentication
  validation in `auth.py` returns `422` for empty or invalid fields.
- Do not expose passwords, session secrets, SQL credentials, or raw stack traces
  in API responses.
- Let unexpected programming errors remain visible in server logs during
  development rather than silently converting every error into success.

## Status Code Conventions

- `401` or the existing login response: the user is not logged in.
- `403`: the session or permission is not sufficient.
- `404`: the requested robot, user, alert, or management record does not exist.
- `422`: request values fail validation, for example a non-numeric control value.
- `502`: a robot or external service is unreachable or returns an invalid reply.
- `504`: a robot control service did not respond before the timeout.

## Database Errors

Database access should go through `db.py`. Its write helpers roll back failed
transactions and re-raise the error. Route handlers may turn a known missing
record into a `404`, but should not hide database failures as a successful
response.

## Device and Control Errors

`robot_control.py` translates socket failures into stable API responses. It
closes broken sockets, retries one time, and distinguishes unreachable service
(`502`) from response timeout (`504`). Control values are parsed and limited by
`normalize_control_value()` before being sent to the robot.

Example:

```python
try:
    response = send_robot_control_message(target, payload, "ack")
except OSError as exc:
    raise HTTPException(status_code=502, detail="无人车控制服务不可达。") from exc
```

## Examples

- Input validation: `apps/backend/src/ugv_backend/auth.py:56`
- Permission response: `apps/backend/src/ugv_backend/auth.py:186`
- Socket failure mapping: `apps/backend/src/ugv_backend/robot_control.py`
- Route-level missing record handling: `apps/backend/src/ugv_backend/app_core.py`
