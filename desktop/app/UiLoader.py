from __future__ import annotations

from pathlib import Path
from PyQt5 import uic


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resource_path(relative_path: str) -> str:
    """Resolve a resource path relative to the project root."""
    return str((_project_root() / relative_path).resolve())


def load_ui(widget, ui_relative_path: str) -> None:
    """Load a .ui file into the widget, resolving from the project root."""
    root = _project_root()
    ui_path = root / ui_relative_path

    # Handle common case mismatch: "ui/" vs "UI/"
    if not ui_path.exists() and ui_relative_path.startswith("ui/"):
        ui_path = root / ("UI/" + ui_relative_path[3:])

    if not ui_path.exists():
        raise FileNotFoundError(f"UI file not found: {ui_path}")

    uic.loadUi(str(ui_path), widget)
