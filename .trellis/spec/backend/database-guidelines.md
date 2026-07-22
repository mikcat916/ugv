# Database Guidelines

> Current MySQL access patterns used by Project4.

## Overview

The backend uses PyMySQL directly. There is no ORM and no separate migration
framework. The canonical schema is `apps/backend/db/mysql_schema.sql`; startup
helpers add or repair a small number of later tables and columns when needed.

## Connection and Queries

- Read MySQL settings through `config.mysql_settings()` and check readiness
  with `mysql_configured()`.
- Use the shared helpers in `apps/backend/src/ugv_backend/db.py`:
  `query_all()` for lists, `query_one()` for one record, `execute_write()` for
  updates/deletes, and `execute_insert()` for inserts.
- Pass values through the `params` argument. Do not build SQL by concatenating
  user input.
- Use `DictCursor` so application code receives dictionaries with column names.
- Shared helpers commit successful writes and roll back failures.

Example:

```python
user = query_one(
    "SELECT * FROM users WHERE username = %s LIMIT 1",
    (username,),
)
```

## Schema Changes

- Put the base schema in `apps/backend/db/mysql_schema.sql`.
- Add repeatable startup checks in `db.py` when a deployed database may already
  exist. Existing examples include `ensure_iot_tables()`,
  `ensure_autonomy_tables()`, `ensure_management_system_tables()`,
  `ensure_robot_ip_column()`, and `ensure_robot_device_column()`.
- Keep development reset and seed data in `apps/backend/db/reset-db-dev.sql`
  and `apps/backend/db/seed-dev.sql`.
- Do not remove user data from startup code. Destructive resets belong in an
  explicit development SQL file or command.

## Naming and Safety

- Use lowercase snake_case table and column names, matching the existing SQL.
- Keep SQL parameters separate from SQL text.
- Close connections in `finally` blocks or use the existing helper functions.
- Do not add a new connection style beside `db.py` without a clear reason.

## Examples

- Connection boundary: `apps/backend/src/ugv_backend/db.py:12`
- Read helper: `apps/backend/src/ugv_backend/db.py:312`
- Write helper: `apps/backend/src/ugv_backend/db.py:334`
- Startup schema setup: `apps/backend/src/ugv_backend/db.py:85`
