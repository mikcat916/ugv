# Project Structure Cleanup Design

Date: 2026-07-22

## Goal

Remove the desktop application and every related entry point, test, document, and setting. Finish the directory migration that is already in progress. The final project contains only the web backend, device tools, tests, documentation, and runtime data.

## Final Structure

```text
project4/
|-- apps/
|   `-- backend/       Web backend
|-- tools/             Development, device, perception, and deployment tools
|-- tests/             Backend, tool, and browser tests
|-- docs/              Guides, checklists, plans, and release notes
|-- logs/              Local runtime logs
|-- var/               Uploads and other runtime data
|-- .env               Local settings
|-- .env.example       Settings example
|-- requirements.txt   Shared runtime dependencies
|-- requirements-dev.txt
|-- start-dev.ps1      Backend development launcher
|-- start.ps1          Backend launcher
|-- start.bat          Backend launcher
`-- README.md          Main project guide
```

## Remove

- Remove `apps/desktop/` and all of its contents.
- Remove `start-desktop.ps1`.
- Remove desktop-only tests, database aliases, and settings documentation.
- Remove desktop installation, startup, troubleshooting, and module documentation.
- Remove unused desktop paths and names from code, scripts, and settings.
- Remove old duplicate files already migrated into `apps/backend/`, `tools/`, `tests/`, and `docs/`.

## Keep

- Keep `apps/backend/` as the only backend source directory.
- Keep development, device, deployment, and perception tools under `tools/`.
- Keep backend and tool tests under `tests/`.
- Keep relevant guides and plans under `docs/`.
- Keep `logs/` and `var/`; do not remove user data or runtime records.
- Keep root backend launchers and database helper launchers.

## Canonical Paths

- Backend source: `apps/backend/src/ugv_backend/`.
- Database files: `apps/backend/db/`.
- Development tools: `tools/dev/`.
- Device tools: `tools/device/`.
- Deployment tools: `tools/deploy/`.
- Perception tools: `tools/perception/`.
- Tests: `tests/`.

## Documentation Changes

- Update the feature list, directory tree, installation, startup, testing, and troubleshooting sections in `README.md`.
- Remove all desktop sections and broken desktop links.
- Update example commands to use the new paths.
- Review planning and release documents, removing only desktop text that would mislead users.

## Verification

1. Search for `desktop`, old `backend/` paths, and old `scripts/` paths to find stale references.
2. Confirm root launchers use only the new structure.
3. Run backend and tool tests.
4. Check that Python modules load successfully.
5. Review Git changes and confirm that logs, uploads, and local settings were not removed by mistake.

## Completion Criteria

- No desktop source, test, launcher, or user documentation remains.
- No migrated duplicate source or script remains at the project root.
- Every backend launcher points to the new paths.
- `README.md` matches the actual directory tree.
- Backend and tool tests pass. Unrelated existing failures are recorded separately.
