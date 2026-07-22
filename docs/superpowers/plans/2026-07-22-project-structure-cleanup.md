# Project Structure Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the complete desktop application and finish the existing migration into `apps/`, `tools/`, `tests/`, and `docs/` without breaking the web backend.

**Architecture:** `apps/backend/` becomes the only application source tree. Operational scripts live under purpose-based `tools/` folders, tests live under `tests/`, and maintained documents live under categorized `docs/` folders. Root files are limited to configuration, dependency entry points, launchers, and the main README.

**Tech Stack:** Python 3.11, FastAPI, PyMySQL, PowerShell, Windows batch, pytest, Playwright, Markdown.

## Global Constraints

- Remove all desktop source, launchers, tests, settings, and user documentation.
- Preserve `logs/`, `var/`, `.env`, and user-generated data.
- Keep `apps/backend/src/ugv_backend/` as the only backend source directory.
- Do not add new dependencies.
- Do not create a Git commit unless the user explicitly requests one.
- Keep changes focused on structure cleanup and stale path removal.

---

## File Map

- Delete application tree: `apps/desktop/`.
- Delete obsolete launcher: `start-desktop.ps1`.
- Delete legacy compatibility trees: `backend/`, `scripts/`.
- Delete duplicate documents: `docs/autopilot-local-test.md`, `docs/local-release-checklist.md`, `docs/remote-control.md`, `todolist_0.2.2.md`, `v0.3_todolist.md`.
- Modify root configuration: `.env.example`, `.gitignore`, `requirements.txt`, `create_database.bat`.
- Modify backend configuration: `apps/backend/src/ugv_backend/config.py`, `apps/backend/README.md`, `apps/backend/db/seed-dev.sql`.
- Modify development tools: `tools/dev/agent_setup.ps1`, `tools/dev/create_database.py`, `tools/dev/bootstrap_iot_backend.py`, `tools/dev/test_mysql_connection.py`.
- Modify maintained documentation: `README.md`, `docs/checklists/autopilot-local-test.md`.
- Verify tests: `tests/backend/`, `tests/tools/`, `tests/e2e/`.

---

### Task 1: Record the Safe Baseline

**Files:**
- Read: `pytest.ini`
- Read: `start-dev.ps1`
- Read: `tests/backend/`
- Read: `tests/tools/`

**Interfaces:**
- Consumes: Current uncommitted migration state.
- Produces: A baseline test result and an exact deletion inventory.

- [x] **Step 1: Capture the current Git state**

Run:

```powershell
git status --short
```

Expected: Existing moved files appear as deleted old paths and untracked new paths. Save the output for comparison; do not reset or restore it.

- [x] **Step 2: Confirm protected runtime paths exist**

Run:

```powershell
Get-Item .env, logs, var | Select-Object FullName
```

Expected: All three paths resolve inside the repository.

- [x] **Step 3: Run focused backend and tool tests before cleanup**

Run:

```powershell
python -m pytest tests/backend tests/tools -q
```

Expected: Tests pass, or any pre-existing failures are recorded before file removal.

---

### Task 2: Remove Desktop Application and Settings

**Files:**
- Delete: `apps/desktop/`
- Delete: `start-desktop.ps1`
- Modify: `.env.example`
- Modify: `.gitignore`
- Modify: `requirements.txt`
- Modify: `create_database.bat`
- Modify: `tools/dev/agent_setup.ps1`
- Modify: `tools/dev/create_database.py`
- Modify: `tools/dev/bootstrap_iot_backend.py`
- Modify: `tools/dev/test_mysql_connection.py`
- Modify: `apps/backend/src/ugv_backend/config.py`

**Interfaces:**
- Consumes: Root `MYSQL_*` settings and `apps/backend/requirements.txt`.
- Produces: Backend-only setup and database tools with no desktop aliases or desktop schema option.

- [x] **Step 1: Delete desktop source and launcher**

Verify both resolved targets are inside the repository, then remove only:

```powershell
apps\desktop
start-desktop.ps1
```

Expected: Neither path exists afterward.

- [x] **Step 2: Remove desktop-only environment aliases**

Edit `.env.example` so it keeps `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`, but removes the `UAV_DB_*` block and its desktop heading.

Edit `apps/backend/src/ugv_backend/config.py`, `tools/dev/create_database.py`, `tools/dev/bootstrap_iot_backend.py`, and `tools/dev/test_mysql_connection.py` so they load only the root `.env` or an explicitly supplied environment file. Remove fallback reads from `backend/.env` and remove `UAV_DB_*` fallback keys.

- [x] **Step 3: Remove the desktop database table option**

In `tools/dev/create_database.py`, remove:

```python
DEVICE_PIN_SQL
--with-device-pin
config["with_device_pin"]
```

Keep normal schema creation unchanged. Update `create_database.bat` to call:

```bat
%PYTHON% "%ROOT%tools\dev\create_database.py" %*
```

- [x] **Step 4: Make dependency setup backend-only**

Set `requirements.txt` to:

```text
# Root dependency entrypoint for the Project4 repository.
-r apps/backend/requirements.txt
```

Update `tools/dev/agent_setup.ps1` to install only `apps/backend/requirements.txt`; remove the PyQt import check and desktop dependency installation.

- [x] **Step 5: Remove obsolete ignore rules**

Delete desktop rules, old `backend/` upload/cache rules, and old root `e2e/` report rules from `.gitignore`. Keep `var/uploads/`, `tests/e2e/`, Python cache, local environment, log, and database-file rules.

- [x] **Step 6: Verify desktop settings are gone**

Run:

```powershell
rg -n -i --hidden --glob '!.git/**' --glob '!docs/superpowers/**' --glob '!logs/**' --glob '!var/**' "apps/desktop|start-desktop|PyQt|UAV_DB|device_pin"
```

Expected: No project configuration or source matches. Playwright's `Desktop Chrome` label is not part of this search and remains valid.

---

### Task 3: Finish Source and Tool Migration

**Files:**
- Delete: `backend/`
- Delete: `scripts/`
- Delete: `docs/autopilot-local-test.md`
- Delete: `docs/local-release-checklist.md`
- Delete: `docs/remote-control.md`
- Delete: `todolist_0.2.2.md`
- Delete: `v0.3_todolist.md`
- Modify: `apps/backend/README.md`
- Modify: `apps/backend/db/seed-dev.sql`

**Interfaces:**
- Consumes: Working replacements under `apps/backend/`, `tools/`, `tests/`, `docs/checklists/`, `docs/guides/`, and `docs/planning/`.
- Produces: One canonical location for each maintained file.

- [x] **Step 1: Confirm replacements exist before deletion**

Run:

```powershell
Get-Item apps/backend/src/ugv_backend/main.py, tools/dev/create_database.py, tests/backend, docs/checklists/local-release-checklist.md, docs/guides/remote-control.md, docs/planning/todolist-v0.2.2.md, docs/planning/todolist-v0.3-simulator.md
```

Expected: Every replacement path exists.

- [x] **Step 2: Delete legacy compatibility trees**

Verify the resolved paths remain inside the repository, then recursively delete `backend/` and `scripts/`. These contain compatibility wrappers, old environment files, cached bytecode, and duplicate tool files.

- [x] **Step 3: Delete duplicate documents**

Delete the two old root todo files and the three uncategorized documents listed in this task. Keep their categorized replacements under `docs/planning/`, `docs/checklists/`, and `docs/guides/`.

- [x] **Step 4: Remove legacy path promises from backend docs**

Update `apps/backend/README.md` so it no longer says `backend/` compatibility entry points or `backend/.env` are supported. Keep commands using `apps/backend/src` and `apps/backend/requirements.txt`.

- [x] **Step 5: Correct the seed file comment**

Change the first comment in `apps/backend/db/seed-dev.sql` from the old `backend/db/mysql_schema.sql` path to `apps/backend/db/mysql_schema.sql`.

- [x] **Step 6: Verify no legacy tree is required**

Run:

```powershell
rg -n --hidden --glob '!.git/**' --glob '!docs/superpowers/**' --glob '!logs/**' --glob '!var/**' "backend[/\\](requirements|db|static|templates|tests)|scripts[/\\]"
```

Expected: No maintained command points to root `backend/` or `scripts/`. References to `apps/backend/` are valid.

---

### Task 4: Rewrite Maintained Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/checklists/autopilot-local-test.md`
- Review: `docs/checklists/local-release-checklist.md`
- Review: `docs/guides/remote-control.md`

**Interfaces:**
- Consumes: Final paths from Tasks 2 and 3.
- Produces: User instructions matching the actual repository tree.

- [x] **Step 1: Rewrite the root directory overview**

Update `README.md` to show only:

```text
apps/backend/
tools/dev/
tools/device/
tools/deploy/
tools/perception/
tests/backend/
tests/tools/
tests/e2e/
docs/
logs/
var/
```

Remove every desktop feature, technology, installation, startup, troubleshooting, and module section.

- [x] **Step 2: Update all root README commands**

Use these canonical examples:

```powershell
python -m pip install -r appsackend
equirements.txt
python tools\dev\create_database.py
python tools\dev\local_release_smoke.py --static
python -m pytest testsackend tests	ools -q
python -m uvicorn ugv_backend.main:app --app-dir appsackend\src --host 127.0.0.1 --port 8000 --reload
```

Use `tools/device/` for robot-side commands and `tools/deploy/` for deployment commands.

- [x] **Step 3: Make the autopilot checklist web-only**

Delete the desktop client section from `docs/checklists/autopilot-local-test.md`. Renumber later sections and change `Web/Desktop panel` to `Web panel`. Keep the robot safety steps unchanged.

- [x] **Step 4: Check maintained guides for old paths**

Run:

```powershell
rg -n "backend[/\\]|scripts[/\\]|desktop|UAV_DB|device_pin" README.md docs/checklists docs/guides apps/backend/README.md
```

Expected: Matches use `apps/backend/`, `tools/`, or intentional plain-language terms only. No removed path remains.

---

### Task 5: Validate the Clean Repository

**Files:**
- Test: `tests/backend/`
- Test: `tests/tools/`
- Test: `tests/e2e/`
- Inspect: all changed files

**Interfaces:**
- Consumes: Backend-only organized repository.
- Produces: Evidence that imports, tests, launchers, and documentation remain usable.

- [x] **Step 1: Check Python syntax and imports**

Run:

```powershell
python -m compileall -q apps/backend/src tools
python -c "import sys; sys.path.insert(0, 'apps/backend/src'); import ugv_backend.main; print('backend import ok')"
```

Expected: Exit code `0` and `backend import ok`.

- [x] **Step 2: Run backend and tool tests**

Run:

```powershell
python -m pytest tests/backend tests/tools -q
```

Expected: All tests pass. If a failure existed in Task 1, confirm it is unchanged and record it as unrelated.

- [x] **Step 3: Run static release checks**

Run:

```powershell
python tools/dev/local_release_smoke.py --static
```

Expected: Static backend files and required paths pass the smoke check.

- [x] **Step 4: Check root launchers without starting a long-running server**

Run:

```powershell
Select-String -Path start-dev.ps1,start.ps1,start.bat,create_database.bat,test_mysql_connection.bat -Pattern 'apps\backend|tools\dev|backend\|scripts\|desktop' -CaseSensitive:$false
```

Expected: Valid matches use `appsackend` or `tools\dev`; no removed root path or desktop launcher remains.

- [x] **Step 5: Run final stale-reference scan**

Run:

```powershell
rg -n -i --hidden --glob '!.git/**' --glob '!docs/superpowers/**' --glob '!logs/**' --glob '!var/**' "apps/desktop|start-desktop|PyQt|UAV_DB|device_pin|backend/requirements|backend/db|scripts/"
```

Expected: No stale project reference. Generic phrases such as Playwright `Desktop Chrome` or a physical desktop computer preview may remain because they do not refer to the removed application.

- [x] **Step 6: Review the final tree and Git diff**

Run:

```powershell
Get-ChildItem -Force | Select-Object Mode,Name
git diff --check
git status --short
```

Expected: Root structure matches the design, whitespace checks pass, `.env`, `logs/`, and `var/` remain, and changes are limited to the approved cleanup.

> Browser smoke testing remains pending because the local Playwright Chromium download timed out on 2026-07-22. Backend and tool tests, static checks, syntax checks, and the running `/api/health` check are complete.
